from unittest.mock import patch, MagicMock

from app.providers.finnhub import FinnhubProvider


class TestFinnhubSplits:
    def test_get_splits_returns_normalized(self):
        provider = FinnhubProvider(api_key="test", base_url="http://fake")
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"symbol": "FAST", "date": "2025-05-22", "fromFactor": 1, "toFactor": 2},
        ]
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_resp) as mock_get:
            result = provider.get_splits("FAST", "2025-01-01", "2025-12-31")

        assert len(result) == 1
        assert result[0]["symbol"] == "FAST"
        assert result[0]["date"] == "2025-05-22"
        assert result[0]["fromFactor"] == 1
        assert result[0]["toFactor"] == 2
        mock_get.assert_called_once()

    def test_get_splits_empty(self):
        provider = FinnhubProvider(api_key="test", base_url="http://fake")
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_resp):
            result = provider.get_splits("AAPL", "2025-01-01", "2025-12-31")

        assert result == []
