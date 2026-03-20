from datetime import date
from decimal import Decimal

from app.models.dividend_history import DividendHistory


class TestDividendHistoryModel:
    def test_create_dividend_history(self, db):
        record = DividendHistory(
            symbol="PETR4.SA",
            dividend_type="Dividendo",
            value=Decimal("1.50"),
            record_date=date(2025, 10, 22),
            ex_date=date(2025, 10, 23),
            payment_date=date(2025, 11, 28),
        )
        db.add(record)
        db.commit()

        saved = db.query(DividendHistory).filter_by(symbol="PETR4.SA").first()
        assert saved is not None
        assert saved.dividend_type == "Dividendo"
        assert saved.value == Decimal("1.50")
        assert saved.record_date == date(2025, 10, 22)
        assert saved.ex_date == date(2025, 10, 23)
        assert saved.payment_date == date(2025, 11, 28)
        assert saved.id is not None
        assert saved.created_at is not None
        assert saved.updated_at is not None

    def test_payment_date_nullable(self, db):
        record = DividendHistory(
            symbol="VALE3.SA",
            dividend_type="JCP",
            value=Decimal("0.75"),
            record_date=date(2025, 6, 15),
            ex_date=date(2025, 6, 16),
            payment_date=None,
        )
        db.add(record)
        db.commit()

        saved = db.query(DividendHistory).filter_by(symbol="VALE3.SA").first()
        assert saved.payment_date is None

    def test_unique_constraint_prevents_duplicates(self, db):
        from sqlalchemy.exc import IntegrityError
        import pytest

        record1 = DividendHistory(
            symbol="PETR4.SA",
            dividend_type="Dividendo",
            value=Decimal("1.50"),
            record_date=date(2025, 10, 22),
            ex_date=date(2025, 10, 23),
        )
        db.add(record1)
        db.commit()

        record2 = DividendHistory(
            symbol="PETR4.SA",
            dividend_type="Dividendo",
            value=Decimal("1.50"),
            record_date=date(2025, 10, 22),
            ex_date=date(2025, 10, 24),
        )
        db.add(record2)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_currency_default(self, db):
        record = DividendHistory(
            symbol="AAPL",
            dividend_type="Dividend",
            value=Decimal("0.25"),
            record_date=date(2025, 1, 10),
            ex_date=date(2025, 1, 11),
        )
        db.add(record)
        db.commit()

        saved = db.query(DividendHistory).filter_by(symbol="AAPL").first()
        assert saved.currency == "USD"

    def test_currency_custom(self, db):
        record = DividendHistory(
            symbol="PETR4.SA",
            dividend_type="Dividendo",
            value=Decimal("1.50"),
            currency="BRL",
            record_date=date(2025, 3, 10),
            ex_date=date(2025, 3, 11),
        )
        db.add(record)
        db.commit()

        saved = db.query(DividendHistory).filter_by(symbol="PETR4.SA").first()
        assert saved.currency == "BRL"
