import logging
import time

from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.tracked_symbol import TrackedSymbol
from app.models.transaction import Transaction
from app.providers.common import Symbol
from app.services.market_data import CRYPTO_CLASS_NAMES

logger = logging.getLogger(__name__)


class MarketDataScheduler:
    def __init__(self, market_data_service):
        self._service = market_data_service

    def fetch_all_quotes(self, db: Session) -> None:
        # Symbols from web app transactions
        tx_symbols = (
            db.query(Transaction.asset_symbol, AssetClass.country)
            .join(AssetClass, Transaction.asset_class_id == AssetClass.id)
            .filter(AssetClass.name.notin_(list(CRYPTO_CLASS_NAMES)))
            .distinct()
            .all()
        )

        # Symbols tracked by iOS app
        tracked = (
            db.query(TrackedSymbol.symbol, TrackedSymbol.country)
            .filter(TrackedSymbol.asset_class != "crypto")
            .all()
        )

        # Merge, canonicalize (`.SA`-suffix BR tickers), and deduplicate so a
        # mixed-form DB during the migration window doesn't trigger two
        # provider calls for the same asset.
        seen: set[str] = set()
        symbols: list[tuple[str, str]] = []
        for symbol, country in list(tx_symbols) + list(tracked):
            canonical = Symbol.canonicalize(symbol)
            if canonical in seen:
                continue
            seen.add(canonical)
            symbols.append((canonical, country))

        for symbol, country in symbols:
            try:
                # Live fetch: bypasses TTL cache so the daily cron writes
                # genuinely fresh data into market_quotes.
                quote_data = self._service.fetch_live_quote(symbol, country=country)
                self._service._upsert_quote(db, symbol, country, quote_data)
                logger.info(f"Updated quote for {symbol}: {quote_data['current_price']}")
            except Exception:
                logger.exception(f"Failed to fetch quote for {symbol}")
                db.rollback()
            finally:
                # Pace yfinance against Yahoo's opaque rate limiter.
                time.sleep(1.5)
