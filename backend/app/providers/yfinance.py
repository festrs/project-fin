import logging

import yfinance as yf

from app.providers.common import DividendRecord

logger = logging.getLogger(__name__)


class YFinanceProvider:
    def get_dividends(self, symbol: str) -> list[DividendRecord]:
        """Fetch full dividend history for a US stock."""
        try:
            ticker = yf.Ticker(symbol)
            dividends = ticker.dividends

            if dividends.empty:
                return []

            records = []
            for ts, amount in dividends.items():
                ex_date = ts.date()
                records.append(DividendRecord(
                    dividend_type="Dividend",
                    value=round(float(amount), 6),
                    record_date=ex_date,
                    ex_date=ex_date,
                    payment_date=None,
                ))
            return records
        except Exception:
            logger.warning("Failed to fetch dividends for %s", symbol, exc_info=True)
            return []
