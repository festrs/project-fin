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
