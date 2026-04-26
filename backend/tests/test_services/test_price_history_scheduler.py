from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.models.price_history import PriceHistory
from app.models.tracked_symbol import TrackedSymbol
from app.services.price_history_scheduler import PriceHistoryScheduler


class TestPickPeriod:
    def test_returns_5y_when_no_data(self, db):
        provider = MagicMock()
        scheduler = PriceHistoryScheduler(yfinance_provider=provider, delay=0)

        period = scheduler._pick_period(db, "AAPL")
        assert period == "5y"

    def test_returns_5d_when_data_is_fresh(self, db):
        db.add(PriceHistory(symbol="AAPL", date=date.today(), close=Decimal("150"), currency="USD"))
        db.commit()

        provider = MagicMock()
        scheduler = PriceHistoryScheduler(yfinance_provider=provider, delay=0)

        period = scheduler._pick_period(db, "AAPL")
        assert period == "5d"

    def test_returns_1mo_when_stale_few_days(self, db):
        stale = date.today() - timedelta(days=5)
        db.add(PriceHistory(symbol="AAPL", date=stale, close=Decimal("150"), currency="USD"))
        db.commit()

        provider = MagicMock()
        scheduler = PriceHistoryScheduler(yfinance_provider=provider, delay=0)

        period = scheduler._pick_period(db, "AAPL")
        assert period == "1mo"

    def test_returns_3mo_when_very_stale(self, db):
        stale = date.today() - timedelta(days=60)
        db.add(PriceHistory(symbol="AAPL", date=stale, close=Decimal("150"), currency="USD"))
        db.commit()

        provider = MagicMock()
        scheduler = PriceHistoryScheduler(yfinance_provider=provider, delay=0)

        period = scheduler._pick_period(db, "AAPL")
        assert period == "3mo"


class TestCollectSymbols:
    def test_collects_from_tracked_symbols(self, db):
        db.add(TrackedSymbol(symbol="AAPL", country="US", asset_class="usStocks"))
        db.add(TrackedSymbol(symbol="ITUB3.SA", country="BR", asset_class="acoesBR"))
        db.commit()

        provider = MagicMock()
        scheduler = PriceHistoryScheduler(yfinance_provider=provider, delay=0)

        symbols = scheduler._collect_symbols(db)
        assert len(symbols) == 2
        tickers = {s[0] for s in symbols}
        assert "AAPL" in tickers
        assert "ITUB3.SA" in tickers

    def test_returns_empty_for_no_tracked(self, db):
        provider = MagicMock()
        scheduler = PriceHistoryScheduler(yfinance_provider=provider, delay=0)

        symbols = scheduler._collect_symbols(db)
        assert len(symbols) == 0

    def test_maps_currency_from_country(self, db):
        db.add(TrackedSymbol(symbol="ITUB3.SA", country="BR", asset_class="acoesBR"))
        db.add(TrackedSymbol(symbol="AAPL", country="US", asset_class="usStocks"))
        db.commit()

        provider = MagicMock()
        scheduler = PriceHistoryScheduler(yfinance_provider=provider, delay=0)

        symbols = scheduler._collect_symbols(db)
        currencies = {s[0]: s[1] for s in symbols}
        assert currencies["ITUB3.SA"] == "BRL"
        assert currencies["AAPL"] == "USD"


class TestRefreshAll:
    def test_processes_all_tracked_symbols(self, db):
        db.add(TrackedSymbol(symbol="AAPL", country="US", asset_class="usStocks"))
        db.add(TrackedSymbol(symbol="ITUB3.SA", country="BR", asset_class="acoesBR"))
        db.commit()

        mock_provider = MagicMock()
        mock_provider.get_history.return_value = [
            {"date": date.today().isoformat(), "close": Decimal("150"), "volume": 0}
        ]
        scheduler = PriceHistoryScheduler(yfinance_provider=mock_provider, delay=0)

        scheduler.refresh_all(db)

        assert mock_provider.get_history.call_count == 2
        rows = db.query(PriceHistory).count()
        assert rows == 2

    def test_continues_on_single_symbol_failure(self, db):
        db.add(TrackedSymbol(symbol="BAD", country="US", asset_class="usStocks"))
        db.add(TrackedSymbol(symbol="AAPL", country="US", asset_class="usStocks"))
        db.commit()

        mock_provider = MagicMock()
        mock_provider.get_history.side_effect = [
            Exception("API error"),  # BAD fails
            [{"date": date.today().isoformat(), "close": Decimal("150"), "volume": 0}],  # AAPL succeeds
        ]
        scheduler = PriceHistoryScheduler(yfinance_provider=mock_provider, delay=0)

        scheduler.refresh_all(db)

        rows = db.query(PriceHistory).count()
        assert rows == 1  # Only AAPL stored
