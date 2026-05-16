from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from app.providers.brapi import BrapiProvider, BrapiFeatureUnavailable
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

        with patch("app.providers.brapi.brapi_client.get", return_value=mock_resp) as mock_get:
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

        with patch("app.providers.brapi.brapi_client.get", return_value=mock_resp) as mock_get:
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

        with patch("app.providers.brapi.brapi_client.get", return_value=mock_resp):
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

        with patch("app.providers.brapi.brapi_client.get", return_value=mock_resp) as mock_get:
            provider.get_history("VALE3.SA", period="1mo")

        call_url = mock_get.call_args[0][0]
        assert "VALE3" in call_url
        assert ".SA" not in call_url


def test_brapi_satisfies_protocol():
    provider = BrapiProvider(api_key="test")
    assert isinstance(provider, MarketDataProvider)


class TestBrapiGetDividends:
    """Pin specific code paths that mutation testing flagged.

    - Plan-gated `FEATURE_NOT_AVAILABLE` must surface as the typed exception.
    - Records with neither ex_date nor payment_date are skipped (they're
      placeholder rows from Brapi without resolvable dates).
    """

    def test_feature_unavailable_raises_typed_exception(self):
        provider = BrapiProvider(api_key="test", base_url="https://brapi.dev")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": "FEATURE_NOT_AVAILABLE",
            "error": True,
            "message": "Dividends not in plan",
        }
        with patch("app.providers.brapi.brapi_client.get", return_value=mock_resp):
            with pytest.raises(BrapiFeatureUnavailable):
                provider.get_dividends("PETR4.SA")

    def test_records_without_any_date_are_skipped(self):
        provider = BrapiProvider(api_key="test", base_url="https://brapi.dev")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [{
                "dividendsData": {"cashDividends": [
                    {"rate": 1.0, "label": "JCP", "lastDatePrior": None, "paymentDate": None},
                    {"rate": 2.0, "label": "Dividend", "lastDatePrior": "2025-01-15", "paymentDate": None},
                ]}
            }]
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("app.providers.brapi.brapi_client.get", return_value=mock_resp):
            records = provider.get_dividends("PETR4.SA")
        # Only the second record has a resolvable date.
        assert len(records) == 1
        assert records[0].dividend_type == "Dividend"
