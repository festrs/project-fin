from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.providers.yfinance import YFinanceProvider


class TestGetDividends:
    def test_returns_dividend_records(self):
        provider = YFinanceProvider()

        index = pd.DatetimeIndex([pd.Timestamp("2025-02-07"), pd.Timestamp("2025-05-09")])
        mock_dividends = pd.Series([0.25, 0.25], index=index)

        with patch("app.providers.yfinance.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.dividends = mock_dividends
            mock_yf.Ticker.return_value = mock_ticker

            records = provider.get_dividends("AAPL")

        assert len(records) == 2
        assert records[0].dividend_type == "Dividend"
        assert records[0].value == 0.25
        assert records[0].ex_date == date(2025, 2, 7)
        assert records[0].record_date == date(2025, 2, 7)
        assert records[0].payment_date is None

    def test_returns_empty_on_error(self):
        provider = YFinanceProvider()

        with patch("app.providers.yfinance.yf") as mock_yf:
            mock_yf.Ticker.side_effect = Exception("Network error")
            records = provider.get_dividends("BAD")

        assert records == []

    def test_returns_empty_for_no_dividends(self):
        provider = YFinanceProvider()

        with patch("app.providers.yfinance.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.dividends = pd.Series([], dtype=float)
            mock_yf.Ticker.return_value = mock_ticker

            records = provider.get_dividends("BRK-B")

        assert records == []


class TestGetFundamentals:
    def _make_mock_ticker(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"firstTradeDateEpochUtc": 1072915200}  # 2004-01-01

        dates = pd.DatetimeIndex([
            pd.Timestamp("2024-12-31"),
            pd.Timestamp("2023-12-31"),
            pd.Timestamp("2022-12-31"),
        ])
        mock_ticker.financials = pd.DataFrame({
            dates[0]: {"Diluted EPS": 6.0, "Net Income": 95000, "EBITDA": 130000},
            dates[1]: {"Diluted EPS": 5.0, "Net Income": 80000, "EBITDA": 120000},
            dates[2]: {"Diluted EPS": 4.0, "Net Income": 70000, "EBITDA": 110000},
        })
        mock_ticker.balance_sheet = pd.DataFrame({
            dates[0]: {"Long Term Debt": 100000},
            dates[1]: {"Long Term Debt": 95000},
            dates[2]: {"Long Term Debt": 90000},
        })
        return mock_ticker

    def test_returns_fundamentals_dict(self):
        provider = YFinanceProvider()

        with patch("app.providers.yfinance.yf") as mock_yf:
            mock_yf.Ticker.return_value = self._make_mock_ticker()
            result = provider.get_fundamentals("AAPL")

        assert result["ipo_years"] is not None
        assert result["ipo_years"] > 20
        assert len(result["eps_history"]) == 3
        assert result["eps_history"] == [4.0, 5.0, 6.0]  # chronological
        assert len(result["net_income_history"]) == 3
        assert len(result["debt_history"]) == 3
        assert result["current_net_debt_ebitda"] is not None
        assert len(result["raw_data"]) == 3

    def test_returns_empty_on_error(self):
        provider = YFinanceProvider()

        with patch("app.providers.yfinance.yf") as mock_yf:
            mock_yf.Ticker.side_effect = Exception("Network error")
            result = provider.get_fundamentals("BAD")

        assert result["ipo_years"] is None
        assert result["eps_history"] == []
        assert result["net_income_history"] == []
        assert result["debt_history"] == []
        assert result["current_net_debt_ebitda"] is None
        assert result["raw_data"] == []

    def test_fallback_ipo_key(self):
        """Uses firstTradeDate when firstTradeDateEpochUtc missing."""
        provider = YFinanceProvider()

        with patch("app.providers.yfinance.yf") as mock_yf:
            mock_ticker = self._make_mock_ticker()
            mock_ticker.info = {"firstTradeDate": 1072915200}
            mock_yf.Ticker.return_value = mock_ticker

            result = provider.get_fundamentals("AAPL")

        assert result["ipo_years"] is not None
        assert result["ipo_years"] > 20

    def test_fallback_row_labels(self):
        """Uses Basic EPS when Diluted EPS missing, Total Debt when Long Term Debt missing."""
        provider = YFinanceProvider()
        dates = pd.DatetimeIndex([pd.Timestamp("2024-12-31")])

        with patch("app.providers.yfinance.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.info = {"firstTradeDateEpochUtc": 1072915200}
            mock_ticker.financials = pd.DataFrame({
                dates[0]: {"Basic EPS": 5.0, "Net Income": 80000, "Operating Income": 100000},
            })
            mock_ticker.balance_sheet = pd.DataFrame({
                dates[0]: {"Total Debt": 90000},
            })
            mock_yf.Ticker.return_value = mock_ticker

            result = provider.get_fundamentals("TEST")

        assert result["eps_history"] == [5.0]
        assert result["debt_history"][0] == pytest.approx(90000 / 100000, rel=1e-3)
