from decimal import Decimal
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from app.providers.finnhub import FinnhubProvider
from app.providers.base import MarketDataProvider
from app.money import Money, Currency


class TestFinnhubGetQuote:
    def test_returns_correct_structure(self):
        provider = FinnhubProvider(api_key="test-key", base_url="https://finnhub.io/api/v1")

        mock_quote_resp = MagicMock()
        mock_quote_resp.json.return_value = {
            "c": 175.50,  # current price
            "h": 176.0,
            "l": 174.0,
            "o": 175.0,
            "pc": 174.50,
        }
        mock_quote_resp.raise_for_status = MagicMock()

        mock_profile_resp = MagicMock()
        mock_profile_resp.json.return_value = {
            "name": "Apple Inc",
            "currency": "USD",
            "marketCapitalization": 2800000.0,  # Finnhub returns in millions
        }
        mock_profile_resp.raise_for_status = MagicMock()

        with patch("app.providers.finnhub.httpx.get") as mock_get:
            mock_get.side_effect = [mock_quote_resp, mock_profile_resp]
            result = provider.get_quote("AAPL")

        assert result["symbol"] == "AAPL"
        assert result["name"] == "Apple Inc"
        assert result["current_price"] == Money(Decimal("175.5"), Currency.USD)
        assert result["currency"] == Currency.USD
        assert result["market_cap"] == Money(Decimal("2800000000000.0"), Currency.USD)

    def test_passes_api_key(self):
        provider = FinnhubProvider(api_key="my-key", base_url="https://finnhub.io/api/v1")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"c": 100.0}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.finnhub.httpx.get", return_value=mock_resp) as mock_get:
            try:
                provider.get_quote("AAPL")
            except Exception:
                pass
            # Verify token param was passed in first call
            call_args = mock_get.call_args_list[0]
            assert call_args[1]["params"]["token"] == "my-key"


class TestFinnhubGetHistory:
    def test_returns_correct_structure(self):
        provider = FinnhubProvider(api_key="test-key", base_url="https://finnhub.io/api/v1")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "c": [170.0, 175.0],
            "v": [1000000, 1200000],
            "t": [1704067200, 1704153600],  # 2024-01-01 and 2024-01-02 UTC
            "s": "ok",
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.finnhub.httpx.get", return_value=mock_resp):
            result = provider.get_history("AAPL", period="1mo")

        assert len(result) == 2
        assert result[0]["date"] == "2024-01-01"
        assert result[0]["close"] == Decimal("170.0")
        assert result[0]["volume"] == 1000000
        assert result[1]["date"] == "2024-01-02"

    def test_no_data_returns_empty(self):
        provider = FinnhubProvider(api_key="test-key", base_url="https://finnhub.io/api/v1")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"s": "no_data"}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.finnhub.httpx.get", return_value=mock_resp):
            result = provider.get_history("INVALID", period="1mo")

        assert result == []


def test_finnhub_satisfies_protocol():
    provider = FinnhubProvider(api_key="test")
    assert isinstance(provider, MarketDataProvider)
