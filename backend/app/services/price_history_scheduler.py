"""
Scheduled job to refresh price history for all tracked symbols.

Processes symbols one at a time (pipeline/queue style) with a delay
between each to respect API rate limits.
"""

import logging
import time
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.price_history import PriceHistory
from app.models.tracked_symbol import TrackedSymbol
from app.providers.yfinance import YFinanceProvider
from app.repositories.price_history_repo import store_history

logger = logging.getLogger(__name__)

DEFAULT_DELAY = 1.5  # seconds between each symbol fetch


class PriceHistoryScheduler:
    def __init__(self, yfinance_provider: YFinanceProvider, delay: float = DEFAULT_DELAY):
        self._yfinance = yfinance_provider
        self._delay = delay

    def refresh_all(self, db: Session) -> None:
        """Fetch latest prices for all tracked symbols, one at a time."""
        symbols = self._collect_symbols(db)
        logger.info("Price history refresh: %d symbols queued", len(symbols))

        for symbol, currency in symbols:
            self._refresh_one(db, symbol, currency)
            if self._delay > 0:
                time.sleep(self._delay)

        logger.info("Price history refresh complete")

    def _collect_symbols(self, db: Session) -> list[tuple[str, str]]:
        """Collect all tracked symbols with their currency."""
        rows = db.query(TrackedSymbol.symbol, TrackedSymbol.country).all()
        seen: set[str] = set()
        result: list[tuple[str, str]] = []
        for symbol, country in rows:
            if symbol not in seen:
                seen.add(symbol)
                currency = "BRL" if country == "BR" else "USD"
                result.append((symbol, currency))
        return result

    def _refresh_one(self, db: Session, symbol: str, currency: str) -> None:
        """Fetch recent prices for a single symbol and store in DB."""
        try:
            period = self._pick_period(db, symbol)
            data = self._yfinance.get_history(symbol, period)
            if data:
                store_history(db, symbol, data, currency)
                logger.info("Refreshed %s: %d points (period=%s)", symbol, len(data), period)
            else:
                logger.warning("No data from yfinance for %s", symbol)
        except Exception:
            logger.exception("Failed to refresh price history for %s", symbol)

    def _pick_period(self, db: Session, symbol: str) -> str:
        """Pick the smallest period needed based on existing DB data.

        - No data at all → fetch 5y for a good baseline
        - Has data but stale (>3 days) → fetch 1mo to catch up
        - Has recent data → fetch 5d for just the latest
        """
        latest = (
            db.query(PriceHistory.date)
            .filter(PriceHistory.symbol == symbol)
            .order_by(PriceHistory.date.desc())
            .first()
        )
        if latest is None:
            return "5y"

        gap = (date.today() - latest.date).days
        if gap > 30:
            return "3mo"
        if gap > 3:
            return "1mo"
        return "5d"
