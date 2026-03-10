from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from app.services.market_data import MarketDataService


@pytest.fixture
def service():
    svc = MarketDataService()
    svc._stock_quote_cache.clear()
    svc._stock_history_cache.clear()
    svc._crypto_quote_cache.clear()
    svc._crypto_history_cache.clear()
    return svc


class TestGetStockQuote:
    @patch("app.services.market_data.yfinance.Ticker")
    def test_returns_correct_structure(self, mock_ticker_cls, service):
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "shortName": "Apple Inc.",
            "currentPrice": 175.50,
            "currency": "USD",
            "marketCap": 2_800_000_000_000,
        }
        mock_ticker_cls.return_value = mock_ticker

        result = service.get_stock_quote("AAPL")

        assert result["symbol"] == "AAPL"
        assert result["name"] == "Apple Inc."
        assert result["current_price"] == 175.50
        assert result["currency"] == "USD"
        assert result["market_cap"] == 2_800_000_000_000
        mock_ticker_cls.assert_called_once_with("AAPL")


class TestGetStockHistory:
    @patch("app.services.market_data.yfinance.Ticker")
    def test_returns_correct_structure(self, mock_ticker_cls, service):
        mock_ticker = MagicMock()
        df = pd.DataFrame(
            {
                "Close": [170.0, 175.0],
                "Volume": [1_000_000, 1_200_000],
            },
            index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
        )
        mock_ticker.history.return_value = df
        mock_ticker_cls.return_value = mock_ticker

        result = service.get_stock_history("AAPL", period="1mo")

        assert len(result) == 2
        assert result[0]["date"] == "2024-01-01"
        assert result[0]["close"] == 170.0
        assert result[0]["volume"] == 1_000_000
        assert result[1]["date"] == "2024-01-02"
        mock_ticker.history.assert_called_once_with(period="1mo")


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
        assert result["current_price"] == 65000.0
        assert result["currency"] == "USD"
        assert result["market_cap"] == 1_200_000_000_000
        assert result["change_24h"] == 2.5


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
        assert result[0]["price"] == 42000.0
        assert "date" in result[0]
        assert result[1]["price"] == 43000.0
