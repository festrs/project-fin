"""Repository for price history database operations."""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.price_history import PriceHistory

logger = logging.getLogger(__name__)


def read_history(db: Session, symbol: str, from_date: date) -> list[dict]:
    """Read cached price history from DB.

    Returns empty if data is stale (>3 days old) or has too few rows
    relative to the expected trading days for the requested range.
    """
    rows = (
        db.query(PriceHistory)
        .filter(PriceHistory.symbol == symbol, PriceHistory.date >= from_date)
        .order_by(PriceHistory.date)
        .all()
    )
    if not rows:
        return []

    if (date.today() - rows[-1].date).days > 3:
        return []  # Stale — refetch

    # Expect ~70% of calendar days as trading days; require at least half
    expected_days = (date.today() - from_date).days
    min_rows = max(5, int(expected_days * 0.35))
    if len(rows) < min_rows:
        return []  # Insufficient coverage — refetch

    return [
        {"date": r.date.isoformat(), "close": r.close, "volume": 0}
        for r in rows
    ]


def store_history(db: Session, symbol: str, data: list[dict], currency: str) -> None:
    """Bulk upsert price history rows into the DB."""
    existing_dates = _get_existing_dates(db, symbol)
    new_rows = _build_new_rows(data, symbol, currency, existing_dates)

    if not new_rows:
        return

    db.add_all(new_rows)
    try:
        db.commit()
        logger.info("Stored %d price history rows for %s", len(new_rows), symbol)
    except Exception:
        logger.warning("Failed to store price history for %s", symbol, exc_info=True)
        db.rollback()


def _get_existing_dates(db: Session, symbol: str) -> set[date]:
    """Get all dates already stored for a symbol."""
    rows = db.query(PriceHistory.date).filter(PriceHistory.symbol == symbol).all()
    return {r.date for r in rows}


def _build_new_rows(
    data: list[dict], symbol: str, currency: str, existing_dates: set[date]
) -> list[PriceHistory]:
    """Build PriceHistory objects for dates not yet in DB."""
    new_rows = []
    for item in data:
        d = item["date"]
        if isinstance(d, str):
            d = date.fromisoformat(d)
        if d in existing_dates:
            continue
        new_rows.append(PriceHistory(
            symbol=symbol, date=d, close=item["close"], currency=currency,
        ))
    return new_rows
