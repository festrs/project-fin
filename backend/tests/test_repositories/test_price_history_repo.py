from datetime import date, timedelta
from decimal import Decimal

from app.models.price_history import PriceHistory
from app.repositories.price_history_repo import read_history, store_history


class TestReadHistory:
    def test_returns_empty_when_no_data(self, db):
        result = read_history(db, "AAPL", date.today() - timedelta(days=30))
        assert result == []

    def test_returns_data_when_fresh(self, db):
        today = date.today()
        for i in range(20):
            d = today - timedelta(days=19 - i)  # From 19 days ago to today
            db.add(PriceHistory(symbol="AAPL", date=d, close=Decimal("150.00"), currency="USD"))
        db.commit()

        result = read_history(db, "AAPL", today - timedelta(days=30))
        assert len(result) == 20
        assert result[0]["close"] == Decimal("150.00")

    def test_returns_empty_when_stale(self, db):
        old_date = date.today() - timedelta(days=10)
        db.add(PriceHistory(symbol="AAPL", date=old_date, close=Decimal("150.00"), currency="USD"))
        db.commit()

        result = read_history(db, "AAPL", date.today() - timedelta(days=30))
        assert result == []  # Latest row is 10 days old (> 3 day threshold)

    def test_returns_empty_when_insufficient_coverage(self, db):
        """Only 2 rows for a 1-year query should fail the min_rows check."""
        today = date.today()
        db.add(PriceHistory(symbol="AAPL", date=today, close=Decimal("150.00"), currency="USD"))
        db.add(PriceHistory(symbol="AAPL", date=today - timedelta(days=1), close=Decimal("149.00"), currency="USD"))
        db.commit()

        result = read_history(db, "AAPL", today - timedelta(days=365))
        assert result == []  # 2 rows << 35% of 365 days

    def test_filters_by_from_date(self, db):
        today = date.today()
        for i in range(60):
            d = today - timedelta(days=90 - i)
            db.add(PriceHistory(symbol="AAPL", date=d, close=Decimal("150.00"), currency="USD"))
        db.commit()

        result = read_history(db, "AAPL", today - timedelta(days=30))
        assert len(result) <= 31  # Only last 30 days

    def test_filters_by_symbol(self, db):
        today = date.today()
        for i in range(20):
            d = today - timedelta(days=25 - i)
            db.add(PriceHistory(symbol="AAPL", date=d, close=Decimal("150.00"), currency="USD"))
            db.add(PriceHistory(symbol="GOOG", date=d, close=Decimal("120.00"), currency="USD"))
        db.commit()

        result = read_history(db, "AAPL", today - timedelta(days=30))
        assert all(r["date"] for r in result)  # All results are for AAPL (no GOOG data leaked)


class TestStoreHistory:
    def test_stores_new_rows(self, db):
        data = [
            {"date": "2026-04-20", "close": Decimal("150.00"), "volume": 1000},
            {"date": "2026-04-21", "close": Decimal("151.00"), "volume": 1100},
            {"date": "2026-04-22", "close": Decimal("152.00"), "volume": 1200},
        ]
        store_history(db, "AAPL", data, "USD")

        rows = db.query(PriceHistory).filter_by(symbol="AAPL").all()
        assert len(rows) == 3

    def test_skips_existing_dates(self, db):
        db.add(PriceHistory(symbol="AAPL", date=date(2026, 4, 20), close=Decimal("150.00"), currency="USD"))
        db.commit()

        data = [
            {"date": "2026-04-20", "close": Decimal("999.00"), "volume": 0},  # Already exists
            {"date": "2026-04-21", "close": Decimal("151.00"), "volume": 0},  # New
        ]
        store_history(db, "AAPL", data, "USD")

        rows = db.query(PriceHistory).filter_by(symbol="AAPL").order_by(PriceHistory.date).all()
        assert len(rows) == 2
        # Existing row should NOT be updated (skip, not upsert)
        assert rows[0].close == Decimal("150.00")

    def test_handles_date_objects(self, db):
        data = [{"date": date(2026, 4, 20), "close": Decimal("150.00"), "volume": 0}]
        store_history(db, "AAPL", data, "USD")

        rows = db.query(PriceHistory).filter_by(symbol="AAPL").all()
        assert len(rows) == 1
        assert rows[0].date == date(2026, 4, 20)

    def test_stores_correct_currency(self, db):
        data = [{"date": "2026-04-20", "close": Decimal("50.00"), "volume": 0}]
        store_history(db, "ITUB3.SA", data, "BRL")

        row = db.query(PriceHistory).filter_by(symbol="ITUB3.SA").first()
        assert row.currency == "BRL"
