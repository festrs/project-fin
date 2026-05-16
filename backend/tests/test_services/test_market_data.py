from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from app.models.market_quote import MarketQuote
from app.money import Money, Currency
from app.services.market_data import MarketDataService


@pytest.fixture
def service():
    svc = MarketDataService()
    svc._quote_cache.clear()
    svc._history_cache.clear()
    svc._crypto_quote_cache.clear()
    svc._crypto_history_cache.clear()
    return svc


class TestGetStockQuote:
    def test_returns_from_db_when_present(self, service, db):
        quote = MarketQuote(
            symbol="AAPL",
            name="Apple Inc",
            current_price=Decimal("175.50"),
            currency="USD",
            market_cap=Decimal("2800000000000"),
            country="US",
        )
        db.add(quote)
        db.commit()

        result = service.get_stock_quote("AAPL", country="US", db=db)

        assert result["symbol"] == "AAPL"
        assert result["current_price"] == Money(Decimal("175.50"), Currency.USD)
        assert result["currency"] == Currency.USD

    def test_falls_back_to_yfinance_when_not_in_db(self, service, db):
        mock_yf = MagicMock()
        mock_yf.get_quote.return_value = {
            "symbol": "AAPL",
            "name": "Apple Inc",
            "current_price": Money(Decimal("175.50"), Currency.USD),
            "currency": Currency.USD,
            "market_cap": Money(Decimal("2800000000000"), Currency.USD),
            "dividend_yield": Decimal("0.39"),
        }
        service._yfinance = mock_yf

        result = service.get_stock_quote("AAPL", country="US", db=db)

        assert result["current_price"] == Money(Decimal("175.50"), Currency.USD)
        assert result["dividend_yield"] == Decimal("0.39")
        mock_yf.get_quote.assert_called_once_with("AAPL")
        stored = db.query(MarketQuote).filter_by(symbol="AAPL").first()
        assert stored is not None
        assert stored.current_price == Decimal("175.50")
        assert stored.dividend_yield == Decimal("0.39")

    def test_falls_back_to_finnhub_when_yfinance_fails(self, service, db):
        service._yfinance = MagicMock()
        service._yfinance.get_quote.side_effect = Exception("yahoo down")

        mock_finnhub = MagicMock()
        mock_finnhub.get_quote.return_value = {
            "symbol": "AAPL",
            "name": "Apple Inc",
            "current_price": Money(Decimal("175.50"), Currency.USD),
            "currency": Currency.USD,
            "market_cap": Money(Decimal("2800000000000"), Currency.USD),
        }
        service._finnhub = mock_finnhub

        result = service.get_stock_quote("AAPL", country="US", db=db)

        assert result["dividend_yield"] is None
        mock_finnhub.get_quote.assert_called_once_with("AAPL")

    def test_falls_back_to_brapi_for_br_when_yfinance_fails(self, service, db):
        service._yfinance = MagicMock()
        service._yfinance.get_quote.side_effect = Exception("yahoo down")

        mock_brapi = MagicMock()
        mock_brapi.get_quote.return_value = {
            "symbol": "PETR4.SA",
            "name": "Petrobras",
            "current_price": Money(Decimal("38.50"), Currency.BRL),
            "currency": Currency.BRL,
            "market_cap": Money(Decimal("500000000000"), Currency.BRL),
        }
        service._brapi = mock_brapi

        result = service.get_stock_quote("PETR4.SA", country="BR", db=db)

        assert result["current_price"] == Money(Decimal("38.50"), Currency.BRL)
        mock_brapi.get_quote.assert_called_once_with("PETR4.SA")


class TestGetStockHistory:
    def test_routes_us_to_yfinance(self, service):
        mock_provider = MagicMock()
        mock_provider.get_history.return_value = [
            {"date": "2024-01-01", "close": Decimal("170.0"), "volume": 1000000},
        ]
        service._yfinance = mock_provider

        result = service.get_stock_history("AAPL", period="1mo", country="US")

        assert len(result) == 1
        mock_provider.get_history.assert_called_once_with("AAPL", "1mo")

    def test_routes_br_to_brapi(self, service):
        mock_provider = MagicMock()
        mock_provider.get_history.return_value = [
            {"date": "2024-01-01", "close": Decimal("35.0"), "volume": 5000000},
        ]
        service._brapi = mock_provider

        result = service.get_stock_history("PETR4.SA", period="1mo", country="BR")

        assert len(result) == 1
        mock_provider.get_history.assert_called_once_with("PETR4.SA", "1mo")


class TestGetQuoteSafe:
    def test_passes_country_to_get_stock_quote(self, service, db):
        quote = MarketQuote(
            symbol="PETR4.SA",
            name="Petrobras",
            current_price=Decimal("38.50"),
            currency="BRL",
            market_cap=Decimal("500000000000"),
            country="BR",
        )
        db.add(quote)
        db.commit()

        result = service.get_quote_safe("PETR4.SA", is_crypto=False, country="BR", db=db)
        assert result == Money(Decimal("38.50"), Currency.BRL)

    def test_returns_none_on_error(self, service, db):
        service._finnhub = MagicMock()
        service._finnhub.get_quote.side_effect = Exception("network error")

        result = service.get_quote_safe("INVALID", is_crypto=False, country="US", db=db)
        assert result is None


class TestGetCryptoQuote:
    @patch("app.services.market_data.httpx.get")
    def test_returns_correct_structure(self, mock_get, service):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "bitcoin": {
                    "usd": 65000.0,
                    "usd_market_cap": 1_200_000_000_000,
                    "usd_24h_change": 2.5,
                }
            },
        )

        result = service.get_crypto_quote("bitcoin")

        assert result["coin_id"] == "bitcoin"
        assert result["current_price"] == Money(Decimal("65000.0"), Currency.USD)


class TestGetCryptoHistory:
    @patch("app.services.market_data.httpx.get")
    def test_returns_correct_structure(self, mock_get, service):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "prices": [
                    [1704067200000, 42000.0],
                    [1704153600000, 43000.0],
                ]
            },
        )

        result = service.get_crypto_history("bitcoin", days=30)

        assert len(result) == 2
        assert result[0]["price"] == Decimal("42000.0")


class TestComputeYieldFromHistory:
    """For BR tickers we ignore whatever yield a provider reports and compute
    it ourselves: sum(last 12mo dividend_history.value) / current_price * 100.

    This makes the iOS Dashboard's "Gross Income" card numerically consistent
    with the gauge — both flow from the same DividendHistory rows.
    """
    def test_sums_trailing_year_and_divides_by_price(self, db):
        from app.services.market_data import compute_yield_from_history
        from app.models.dividend_history import DividendHistory
        from datetime import date, timedelta

        # 12 monthly payments of R$0.25/share — annual = R$3 — at price R$50 → 6%.
        today = date.today()
        for offset in range(1, 13):
            db.add(DividendHistory(
                symbol="ITUB3.SA", dividend_type="JCP", value=Decimal("0.25"),
                record_date=today - timedelta(days=30 * offset),
                ex_date=today - timedelta(days=30 * offset),
                payment_date=today - timedelta(days=30 * offset - 5),
                currency="BRL",
            ))
        db.commit()

        result = compute_yield_from_history(db, "ITUB3.SA", Decimal("50"))
        assert result is not None
        # 3.00 / 50 * 100 = 6.0
        assert result == Decimal("6.00")

    def test_excludes_payments_older_than_one_year(self, db):
        from app.services.market_data import compute_yield_from_history
        from app.models.dividend_history import DividendHistory
        from datetime import date, timedelta

        today = date.today()
        # Two recent + one ancient (2 years ago) payment.
        for offset in (10, 90):
            db.add(DividendHistory(
                symbol="ITUB3.SA", dividend_type="JCP", value=Decimal("1"),
                record_date=today - timedelta(days=offset),
                ex_date=today - timedelta(days=offset),
                payment_date=today - timedelta(days=offset),
                currency="BRL",
            ))
        db.add(DividendHistory(
            symbol="ITUB3.SA", dividend_type="JCP", value=Decimal("99"),
            record_date=today - timedelta(days=730),
            ex_date=today - timedelta(days=730),
            payment_date=today - timedelta(days=730),
            currency="BRL",
        ))
        db.commit()

        # Only the 2 recent payments count: 2.00 / 100 * 100 = 2.0
        result = compute_yield_from_history(db, "ITUB3.SA", Decimal("100"))
        assert result == Decimal("2.00")

    def test_returns_none_when_no_records(self, db):
        from app.services.market_data import compute_yield_from_history
        result = compute_yield_from_history(db, "NEWIPO.SA", Decimal("50"))
        assert result is None

    def test_returns_none_when_price_is_zero(self, db):
        from app.services.market_data import compute_yield_from_history
        from app.models.dividend_history import DividendHistory
        from datetime import date

        db.add(DividendHistory(
            symbol="ITUB3.SA", dividend_type="JCP", value=Decimal("1"),
            record_date=date.today(), ex_date=date.today(),
            payment_date=date.today(), currency="BRL",
        ))
        db.commit()
        result = compute_yield_from_history(db, "ITUB3.SA", Decimal("0"))
        assert result is None


class TestUpsertQuoteOverridesBRYield:
    """When upserting a BR quote, MarketDataService must overwrite the
    provider-supplied dividend_yield with the one computed from records.

    This is the seam that prevents broken yfinance numbers (ITUB3 = 0.53%)
    from leaking through to iOS clients.
    """
    def test_br_yield_replaced_by_computed_from_history(self, service, db):
        from app.models.dividend_history import DividendHistory
        from datetime import date, timedelta

        today = date.today()
        for offset in range(1, 13):
            db.add(DividendHistory(
                symbol="ITUB3.SA", dividend_type="JCP", value=Decimal("0.25"),
                record_date=today - timedelta(days=30 * offset),
                ex_date=today - timedelta(days=30 * offset),
                payment_date=today - timedelta(days=30 * offset - 5),
                currency="BRL",
            ))
        db.commit()

        # Provider returns a deliberately wrong yield (0.53 — yfinance's bug).
        provider_payload = {
            "symbol": "ITUB3.SA", "name": "Itaú",
            "current_price": Money(Decimal("50"), Currency.BRL),
            "currency": Currency.BRL,
            "market_cap": Money(Decimal("0"), Currency.BRL),
            "dividend_yield": Decimal("0.53"),
        }

        service._upsert_quote(db, "ITUB3.SA", "BR", provider_payload)

        from app.models.market_quote import MarketQuote
        stored = db.query(MarketQuote).filter_by(symbol="ITUB3.SA").one()
        # 12 × 0.25 = 3.00 / 50 × 100 = 6.00
        assert stored.dividend_yield == Decimal("6.00")

    def test_us_yield_left_untouched(self, service, db):
        # No DividendHistory rows for US tickers in this test — provider value
        # must be preserved (we trust yfinance for US dividend yields).
        provider_payload = {
            "symbol": "AAPL", "name": "Apple",
            "current_price": Money(Decimal("200"), Currency.USD),
            "currency": Currency.USD,
            "market_cap": Money(Decimal("0"), Currency.USD),
            "dividend_yield": Decimal("0.40"),
        }
        service._upsert_quote(db, "AAPL", "US", provider_payload)

        from app.models.market_quote import MarketQuote
        stored = db.query(MarketQuote).filter_by(symbol="AAPL").one()
        assert stored.dividend_yield == Decimal("0.40")

    def test_br_yield_falls_back_when_no_history(self, service, db):
        # Brand-new BR ticker with no recorded dividends — keep provider value.
        provider_payload = {
            "symbol": "NEWIPO.SA", "name": "New Co",
            "current_price": Money(Decimal("10"), Currency.BRL),
            "currency": Currency.BRL,
            "market_cap": Money(Decimal("0"), Currency.BRL),
            "dividend_yield": Decimal("3.5"),
        }
        service._upsert_quote(db, "NEWIPO.SA", "BR", provider_payload)

        from app.models.market_quote import MarketQuote
        stored = db.query(MarketQuote).filter_by(symbol="NEWIPO.SA").one()
        assert stored.dividend_yield == Decimal("3.5")
