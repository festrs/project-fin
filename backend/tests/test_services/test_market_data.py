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

    def test_falls_back_to_provider_when_not_in_db(self, service, db):
        mock_provider = MagicMock()
        mock_provider.get_quote.return_value = {
            "symbol": "AAPL",
            "name": "Apple Inc",
            "current_price": Money(Decimal("175.50"), Currency.USD),
            "currency": Currency.USD,
            "market_cap": Money(Decimal("2800000000000"), Currency.USD),
        }
        service._finnhub = mock_provider

        result = service.get_stock_quote("AAPL", country="US", db=db)

        assert result["current_price"] == Money(Decimal("175.50"), Currency.USD)
        mock_provider.get_quote.assert_called_once_with("AAPL")
        # Verify it was stored in DB
        stored = db.query(MarketQuote).filter_by(symbol="AAPL").first()
        assert stored is not None
        assert stored.current_price == Decimal("175.50")

    def test_routes_br_to_brapi(self, service, db):
        mock_provider = MagicMock()
        mock_provider.get_quote.return_value = {
            "symbol": "PETR4.SA",
            "name": "Petrobras",
            "current_price": Money(Decimal("38.50"), Currency.BRL),
            "currency": Currency.BRL,
            "market_cap": Money(Decimal("500000000000"), Currency.BRL),
        }
        service._brapi = mock_provider

        result = service.get_stock_quote("PETR4.SA", country="BR", db=db)

        assert result["current_price"] == Money(Decimal("38.50"), Currency.BRL)
        mock_provider.get_quote.assert_called_once_with("PETR4.SA")


class TestGetStockHistory:
    def test_routes_us_to_finnhub(self, service):
        mock_provider = MagicMock()
        mock_provider.get_history.return_value = [
            {"date": "2024-01-01", "close": Decimal("170.0"), "volume": 1000000},
        ]
        service._finnhub = mock_provider

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
