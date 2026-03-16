from unittest.mock import patch, MagicMock

from app.providers.finnhub import FinnhubProvider


def _make_mock_resp(data):
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


def _make_report(year, eps, net_income, ebitda, total_debt):
    return {
        "year": year,
        "report": {
            "ic": [
                {"concept": "us-gaap_EarningsPerShareDiluted", "label": "Diluted EPS", "value": eps},
                {"concept": "us-gaap_NetIncomeLoss", "label": "Net Income", "value": net_income},
                {"concept": "us-gaap_OperatingIncomeLoss", "label": "Operating Income", "value": ebitda},
            ],
            "bs": [
                {"concept": "us-gaap_LongTermDebt", "label": "Long Term Debt", "value": total_debt},
            ],
        },
    }


class TestGetFundamentals:
    def _provider(self):
        return FinnhubProvider(api_key="test-key", base_url="https://finnhub.io/api/v1")

    def test_extracts_ipo_date_and_computes_years(self):
        provider = self._provider()

        profile_data = {"ipo": "2010-06-29", "name": "SomeCompany"}
        financials_data = {
            "data": [
                _make_report(2023, 5.0, 1_000_000, 2_000_000, 4_000_000),
                _make_report(2019, 1.0, 200_000, 500_000, 1_000_000),
                _make_report(2021, 3.0, 600_000, 1_200_000, 2_400_000),
                _make_report(2020, 2.0, 400_000, 800_000, 1_600_000),
                _make_report(2022, 4.0, 800_000, 1_600_000, 3_200_000),
            ]
        }

        with patch("app.providers.finnhub.httpx.get") as mock_get:
            mock_get.side_effect = [
                _make_mock_resp(profile_data),
                _make_mock_resp(financials_data),
            ]
            result = provider.get_fundamentals("AAPL")

        assert result["ipo_years"] is not None
        assert result["ipo_years"] >= 15

        # Should be sorted chronologically (oldest first)
        assert len(result["eps_history"]) == 5
        assert result["eps_history"] == [1.0, 2.0, 3.0, 4.0, 5.0]

        assert len(result["net_income_history"]) == 5
        assert result["net_income_history"] == [200_000, 400_000, 600_000, 800_000, 1_000_000]

        assert len(result["debt_history"]) == 5
        # last year: totalDebt=4_000_000, ebitda=2_000_000 → ratio = 2.0
        assert result["current_net_debt_ebitda"] == 2.0

        assert len(result["raw_data"]) == 5
        assert result["raw_data"][0]["year"] == 2019
        assert result["raw_data"][-1]["year"] == 2023

    def test_handles_missing_ipo_date(self):
        provider = self._provider()

        profile_data = {"name": "NoIPO Inc"}
        financials_data = {"data": []}

        with patch("app.providers.finnhub.httpx.get") as mock_get:
            mock_get.side_effect = [
                _make_mock_resp(profile_data),
                _make_mock_resp(financials_data),
            ]
            result = provider.get_fundamentals("NIPO")

        assert result["ipo_years"] is None
        assert result["eps_history"] == []
        assert result["net_income_history"] == []
        assert result["debt_history"] == []
        assert result["current_net_debt_ebitda"] is None
        assert result["raw_data"] == []

    def test_handles_missing_financial_fields(self):
        provider = self._provider()

        profile_data = {"ipo": "2005-01-15"}
        # Reports with empty ic/bs dicts
        financials_data = {
            "data": [
                {"year": 2021, "report": {"ic": [], "bs": []}},
                {"year": 2022, "report": {"ic": [], "bs": []}},
                {"year": 2023, "report": {"ic": [], "bs": []}},
                {"year": 2024, "report": {"ic": [], "bs": []}},
                {"year": 2025, "report": {"ic": [], "bs": []}},
            ]
        }

        with patch("app.providers.finnhub.httpx.get") as mock_get:
            mock_get.side_effect = [
                _make_mock_resp(profile_data),
                _make_mock_resp(financials_data),
            ]
            result = provider.get_fundamentals("MISS")

        assert len(result["eps_history"]) == 5
        assert all(v == 0 for v in result["eps_history"])
        assert all(v == 0 for v in result["net_income_history"])
        assert all(v == 0 for v in result["debt_history"])
        assert result["current_net_debt_ebitda"] == 0.0
