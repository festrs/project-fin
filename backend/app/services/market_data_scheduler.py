import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.market_quote import MarketQuote
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
        symbols = (
            db.query(Transaction.asset_symbol, AssetClass.country)
            .join(AssetClass, Transaction.asset_class_id == AssetClass.id)
            .filter(AssetClass.name.notin_(list(CRYPTO_CLASS_NAMES)))
            .distinct()
            .all()
        )

        for symbol, country in symbols:
            try:
                provider = self._get_provider(country)
                quote_data = provider.get_quote(symbol)

                quote = db.query(MarketQuote).filter_by(symbol=symbol).first()
                if quote is None:
                    quote = MarketQuote(symbol=symbol)
                    db.add(quote)

                quote.name = quote_data["name"]
                quote.current_price = quote_data["current_price"]
                quote.currency = quote_data["currency"]
                quote.market_cap = quote_data.get("market_cap", 0)
                quote.country = country
                quote.updated_at = datetime.now(timezone.utc)
                db.commit()

                logger.info(f"Updated quote for {symbol}: {quote_data['current_price']}")
            except Exception:
                logger.exception(f"Failed to fetch quote for {symbol}")
                db.rollback()
