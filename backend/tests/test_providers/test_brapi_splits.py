from unittest.mock import patch, MagicMock

from app.providers.brapi import BrapiProvider


class TestBrapiSplits:
    def test_get_splits_filters_desdobramento(self):
        provider = BrapiProvider(api_key="test", base_url="http://fake")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [{
                "dividendsData": {
                    "stockDividends": [
                        {"label": "DESDOBRAMENTO", "factor": 2, "lastDatePrior": "2008-03-24T00:00:00.000Z"},
                        {"label": "BONIFICACAO", "factor": 0.1, "lastDatePrior": "2010-01-15T00:00:00.000Z"},
                    ]
                }
            }]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_resp):
            result = provider.get_splits("PETR4.SA")

        assert len(result) == 1
        assert result[0]["symbol"] == "PETR4.SA"
        assert result[0]["date"] == "2008-03-24"
        assert result[0]["fromFactor"] == 1
        assert result[0]["toFactor"] == 2

    def test_get_splits_empty_dividends(self):
        provider = BrapiProvider(api_key="test", base_url="http://fake")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [{"dividendsData": {"stockDividends": []}}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_resp):
            result = provider.get_splits("VALE3.SA")

        assert result == []

    def test_get_splits_no_dividends_data(self):
        provider = BrapiProvider(api_key="test", base_url="http://fake")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [{}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_resp):
            result = provider.get_splits("VALE3.SA")

        assert result == []
