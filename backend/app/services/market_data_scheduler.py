import logging
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.market_quote import MarketQuote
from app.models.tracked_symbol import TrackedSymbol
from app.models.transaction import Transaction
from app.services.market_data import CRYPTO_CLASS_NAMES

logger = logging.getLogger(__name__)


class MarketDataScheduler:
    def __init__(self, finnhub_provider, brapi_provider):
        self._finnhub = finnhub_provider
        self._brapi = brapi_provider

    def _get_provider(self, country: str):
        return self._brapi if country == "BR" else self._finnhub

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

        # Merge and deduplicate
        seen: set[str] = set()
        symbols: list[tuple[str, str]] = []
        for symbol, country in list(tx_symbols) + list(tracked):
            if symbol not in seen:
                seen.add(symbol)
                symbols.append((symbol, country))

        for symbol, country in symbols:
            try:
                provider = self._get_provider(country)
                quote_data = provider.get_quote(symbol)

                quote = db.query(MarketQuote).filter_by(symbol=symbol).first()
                if quote is None:
                    quote = MarketQuote(symbol=symbol)
                    db.add(quote)

                quote.name = quote_data["name"]
                price_amount, price_currency = quote_data["current_price"].to_db()
                quote.current_price = price_amount
                quote.currency = price_currency
                mcap_amount, _ = quote_data["market_cap"].to_db()
                quote.market_cap = mcap_amount
                quote.country = country
                quote.updated_at = datetime.now(timezone.utc)
                db.commit()

                logger.info(f"Updated quote for {symbol}: {quote_data['current_price']}")
            except Exception:
                logger.exception(f"Failed to fetch quote for {symbol}")
                db.rollback()
            finally:
                # Finnhub free tier: 60 req/min, each US quote uses 2 calls → rate limit to ~25/min
                if country != "BR":
                    time.sleep(1.5)
