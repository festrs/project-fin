import logging
import math
from decimal import Decimal

import yfinance as yf

from app.providers.common import DividendRecord

logger = logging.getLogger(__name__)


class YFinanceProvider:
    def get_splits(self, symbol: str, from_date: str, to_date: str) -> list[dict]:
        """Fetch stock split history for a symbol within a date range.

        Returns list of dicts with keys: date, fromFactor, toFactor.
        """
        try:
            from datetime import date

            start = date.fromisoformat(from_date)
            end = date.fromisoformat(to_date)
            ticker = yf.Ticker(symbol)
            splits = ticker.splits

            if splits.empty:
                return []

            results = []
            for ts, ratio in splits.items():
                split_date = ts.date()
                if split_date < start or split_date > end:
                    continue
                results.append({
                    "date": split_date.isoformat(),
                    "fromFactor": 1,
                    "toFactor": float(ratio),
                })
            return results
        except Exception:
            logger.warning("Failed to fetch splits for %s", symbol, exc_info=True)
            return []

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
                    value=Decimal(str(amount)).quantize(Decimal("0.000001")),
                    record_date=ex_date,
                    ex_date=ex_date,
                    payment_date=None,
                ))
            return records
        except Exception:
            logger.warning("Failed to fetch dividends for %s", symbol, exc_info=True)
            return []

    def get_fundamentals(self, symbol: str) -> dict:
        """Fetch fundamental financial data for scoring."""
        empty = {
            "ipo_years": None,
            "eps_history": [],
            "net_income_history": [],
            "debt_history": [],
            "current_net_debt_ebitda": None,
            "raw_data": [],
        }
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # IPO years
            from datetime import datetime, timezone
            epoch = info.get("firstTradeDateEpochUtc") or info.get("firstTradeDate")
            epoch_ms = info.get("firstTradeDateMilliseconds")
            if epoch:
                ipo_date = datetime.fromtimestamp(epoch, tz=timezone.utc)
                ipo_years = (datetime.now(timezone.utc) - ipo_date).days // 365
            elif epoch_ms:
                ipo_date = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
                ipo_years = (datetime.now(timezone.utc) - ipo_date).days // 365
            else:
                ipo_years = None

            financials = ticker.financials
            balance_sheet = ticker.balance_sheet

            if financials is None or financials.empty:
                empty["ipo_years"] = ipo_years
                return empty

            # Sort columns chronologically (oldest first)
            sorted_cols = sorted(financials.columns)

            def _get_row(df, *labels):
                """Get row values for first matching label."""
                if df is None or df.empty:
                    return {}
                for label in labels:
                    if label in df.index:
                        return {col: df.loc[label, col] for col in sorted_cols if col in df.columns}
                return {}

            eps_row = _get_row(financials, "Diluted EPS", "Basic EPS")
            ni_row = _get_row(financials, "Net Income")
            ebitda_row = _get_row(financials, "EBITDA", "Operating Income")
            debt_row = _get_row(balance_sheet, "Long Term Debt", "Total Debt")

            def _safe_float(val: object) -> float:
                """Convert to float, treating NaN/None as 0."""
                if val is None:
                    return 0.0
                f = float(val)
                return 0.0 if math.isnan(f) else f

            eps_history = []
            net_income_history = []
            debt_history = []
            raw_data = []

            for col in sorted_cols:
                eps = _safe_float(eps_row.get(col))
                ni = _safe_float(ni_row.get(col))
                ebitda = _safe_float(ebitda_row.get(col))
                debt = _safe_float(debt_row.get(col))
                debt_ratio = (debt / ebitda) if ebitda != 0 else 0.0

                eps_history.append(eps)
                net_income_history.append(ni)
                debt_history.append(debt_ratio)

                year = col.year if hasattr(col, "year") else None
                raw_data.append({
                    "year": year,
                    "eps": eps,
                    "net_income": ni,
                    "net_debt_ebitda": round(debt_ratio, 4),
                })

            current_net_debt_ebitda = debt_history[-1] if debt_history else None

            return {
                "ipo_years": ipo_years,
                "eps_history": eps_history,
                "net_income_history": net_income_history,
                "debt_history": debt_history,
                "current_net_debt_ebitda": current_net_debt_ebitda,
                "raw_data": raw_data,
            }
        except Exception:
            logger.warning("Failed to fetch fundamentals for %s", symbol, exc_info=True)
            return empty
