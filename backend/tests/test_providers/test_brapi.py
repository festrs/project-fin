from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.providers.brapi import BrapiProvider
from app.providers.base import MarketDataProvider
from app.money import Money, Currency


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
        assert result["current_price"] == Money(Decimal("38.5"), Currency.BRL)
        assert result["currency"] == Currency.BRL
        assert result["market_cap"] == Money(Decimal("500000000000"), Currency.BRL)

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
        assert result[0]["close"] == Decimal("35.0")
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


class TestBrapiSearch:
    def test_classifies_fii_and_stock_by_ticker_suffix(self):
        # The brapi /api/available endpoint doesn't expose asset class, so we
        # infer it from the ticker: "11" suffix is a FII, otherwise a BR
        # equity. Without this, every BR ticker reached the iOS client tagged
        # "Common Stock" and was misclassified as a US stock.
        provider = BrapiProvider(api_key="test-key", base_url="https://brapi.dev")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "stocks": ["ITUB3", "KNRI11", "PETR4", "BCFF11", "VALE3"],
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.brapi.brapi_client.get", return_value=mock_resp):
            results = provider.search("any")

        by_symbol = {r["symbol"]: r["type"] for r in results}
        assert by_symbol["ITUB3.SA"] == "stock"
        assert by_symbol["PETR4.SA"] == "stock"
        assert by_symbol["VALE3.SA"] == "stock"
        assert by_symbol["KNRI11.SA"] == "fund"
        assert by_symbol["BCFF11.SA"] == "fund"


def test_brapi_satisfies_protocol():
    provider = BrapiProvider(api_key="test")
    assert isinstance(provider, MarketDataProvider)
