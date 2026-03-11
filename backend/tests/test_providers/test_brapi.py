from unittest.mock import patch, MagicMock

from app.providers.brapi import BrapiProvider
from app.providers.base import MarketDataProvider


class TestBrapiGetQuote:
    def test_returns_correct_structure(self):
        provider = BrapiProvider(api_key="test-key", base_url="https://brapi.dev")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [
                {
                    "shortName": "PETROBRAS PN",
                    "regularMarketPrice": 38.50,
                    "currency": "BRL",
                    "marketCap": 500_000_000_000,
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp) as mock_get:
            result = provider.get_quote("PETR4.SA")

        assert result["symbol"] == "PETR4.SA"
        assert result["name"] == "PETROBRAS PN"
        assert result["current_price"] == 38.50
        assert result["currency"] == "BRL"
        assert result["market_cap"] == 500_000_000_000

    def test_strips_sa_suffix_for_api_call(self):
        provider = BrapiProvider(api_key="test-key", base_url="https://brapi.dev")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [{"shortName": "X", "regularMarketPrice": 10.0, "currency": "BRL", "marketCap": 0}]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp) as mock_get:
            provider.get_quote("PETR4.SA")

        # Verify the URL uses the stripped symbol
        call_url = mock_get.call_args[0][0]
        assert "PETR4" in call_url
        assert ".SA" not in call_url


class TestBrapiGetHistory:
    def test_returns_correct_structure(self):
        provider = BrapiProvider(api_key="test-key", base_url="https://brapi.dev")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [
                {
                    "historicalDataPrice": [
                        {"date": 1704067200, "close": 35.0, "volume": 5000000},
                        {"date": 1704153600, "close": 36.0, "volume": 6000000},
                    ]
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp):
            result = provider.get_history("PETR4.SA", period="1mo")

        assert len(result) == 2
        assert result[0]["date"] == "2024-01-01"
        assert result[0]["close"] == 35.0
        assert result[0]["volume"] == 5000000

    def test_strips_sa_suffix_for_history(self):
        provider = BrapiProvider(api_key="test-key", base_url="https://brapi.dev")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [{"historicalDataPrice": []}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp) as mock_get:
            provider.get_history("VALE3.SA", period="1mo")

        call_url = mock_get.call_args[0][0]
        assert "VALE3" in call_url
        assert ".SA" not in call_url


def test_brapi_satisfies_protocol():
    provider = BrapiProvider(api_key="test")
    assert isinstance(provider, MarketDataProvider)
