from unittest.mock import MagicMock, patch

from app.providers.brapi import BrapiProvider


class TestBrapiGetFundamentals:
    def setup_method(self):
        self.provider = BrapiProvider(api_key="test-key", base_url="https://brapi.dev")

    def _make_mock_resp(self):
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
        return mock_resp

    def test_returns_standard_shape_keys(self):
        mock_resp = self._make_mock_resp()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp):
            result = self.provider.get_fundamentals("PETR4.SA")

        assert "ipo_years" in result
        assert "eps_history" in result
        assert "net_income_history" in result
        assert "debt_history" in result
        assert "current_net_debt_ebitda" in result
        assert "raw_data" in result

    def test_eps_history_is_list(self):
        mock_resp = self._make_mock_resp()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp):
            result = self.provider.get_fundamentals("PETR4.SA")

        assert isinstance(result["eps_history"], list)

    def test_net_income_history_is_list(self):
        mock_resp = self._make_mock_resp()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp):
            result = self.provider.get_fundamentals("PETR4.SA")

        assert isinstance(result["net_income_history"], list)

    def test_debt_history_is_list(self):
        mock_resp = self._make_mock_resp()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp):
            result = self.provider.get_fundamentals("PETR4.SA")

        assert isinstance(result["debt_history"], list)

    def test_raw_data_is_list(self):
        mock_resp = self._make_mock_resp()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp):
            result = self.provider.get_fundamentals("PETR4.SA")

        assert isinstance(result["raw_data"], list)

    def test_ipo_years_is_none(self):
        mock_resp = self._make_mock_resp()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp):
            result = self.provider.get_fundamentals("PETR4.SA")

        assert result["ipo_years"] is None

    def test_current_net_debt_ebitda_is_none(self):
        mock_resp = self._make_mock_resp()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp):
            result = self.provider.get_fundamentals("PETR4.SA")

        assert result["current_net_debt_ebitda"] is None

    def test_strips_sa_suffix_in_url(self):
        mock_resp = self._make_mock_resp()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp) as mock_get:
            self.provider.get_fundamentals("PETR4.SA")

        call_url = mock_get.call_args[0][0]
        assert "PETR4" in call_url
        assert ".SA" not in call_url

    def test_sends_fundamental_param(self):
        mock_resp = self._make_mock_resp()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp) as mock_get:
            self.provider.get_fundamentals("PETR4.SA")

        call_kwargs = mock_get.call_args[1]
        params = call_kwargs.get("params", {})
        assert params.get("fundamental") == "true"
