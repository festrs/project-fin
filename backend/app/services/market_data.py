import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx

from app.money import Money, Currency
from cachetools import TTLCache
from sqlalchemy.orm import Session

from app.config import settings
from app.models.market_quote import MarketQuote
from app.providers.finnhub import FinnhubProvider
from app.providers.brapi import BrapiProvider

logger = logging.getLogger(__name__)

CRYPTO_COINGECKO_MAP = {
    "BTC": "bitcoin", "BTC-USD": "bitcoin",
    "ETH": "ethereum", "ETH-USD": "ethereum",
    "USDT": "tether", "USDT-USD": "tether",
    "USDC": "usd-coin", "USDC-USD": "usd-coin",
    "DAI": "dai", "DAI-USD": "dai",
}
CRYPTO_CLASS_NAMES = {"Crypto", "Cryptos", "Stablecoins"}


class MarketDataService:
    def __init__(self):
        self._finnhub = FinnhubProvider(
            api_key=settings.finnhub_api_key,
            base_url=settings.finnhub_base_url,
        )
        self._brapi = BrapiProvider(
            api_key=settings.brapi_api_key,
            base_url=settings.brapi_base_url,
        )
        self._quote_cache: TTLCache = TTLCache(maxsize=256, ttl=300)
        self._history_cache: TTLCache = TTLCache(maxsize=256, ttl=900)
        self._crypto_quote_cache: TTLCache = TTLCache(maxsize=256, ttl=120)
        self._crypto_history_cache: TTLCache = TTLCache(maxsize=256, ttl=900)

    def _get_provider(self, country: str):
        return self._brapi if country == "BR" else self._finnhub

    def get_stock_quote(self, symbol: str, country: str = "US", db: Session | None = None) -> dict:
        if symbol in self._quote_cache:
            return self._quote_cache[symbol]

        # Try DB first
        if db is not None:
            stored = db.query(MarketQuote).filter_by(symbol=symbol).first()
            if stored is not None:
                # Warn if data is stale (>24h)
                age = datetime.now(timezone.utc) - stored.updated_at.replace(tzinfo=timezone.utc)
                if age.total_seconds() > 86400:
                    logger.warning(f"Stale quote for {symbol}: last updated {stored.updated_at}")
                result = {
                    "symbol": stored.symbol,
                    "name": stored.name,
                    "current_price": Money.from_db(stored.current_price, stored.currency),
                    "currency": Currency.from_code(stored.currency),
                    "market_cap": Money.from_db(stored.market_cap, stored.currency),
                }
                self._quote_cache[symbol] = result
                return result

        # Fallback to live provider
        provider = self._get_provider(country)
        result = provider.get_quote(symbol)
        self._quote_cache[symbol] = result

        # Store in DB for future reads
        if db is not None:
            quote = db.query(MarketQuote).filter_by(symbol=symbol).first()
            if quote is None:
                quote = MarketQuote(symbol=symbol, country=country)
                db.add(quote)
            quote.name = result["name"]
            price_amount, price_currency = result["current_price"].to_db()
            quote.current_price = price_amount
            quote.currency = price_currency
            mcap_amount, _ = result["market_cap"].to_db()
            quote.market_cap = mcap_amount
            quote.country = country
            quote.updated_at = datetime.now(timezone.utc)
            db.commit()

        return result

    def get_stock_history(self, symbol: str, period: str = "1mo", country: str = "US") -> list[dict]:
        cache_key = f"{symbol}:{period}"
        if cache_key in self._history_cache:
            return self._history_cache[cache_key]

        provider = self._get_provider(country)
        result = provider.get_history(symbol, period)
        self._history_cache[cache_key] = result
        return result

    def get_quote_safe(
        self, symbol_or_coin_id: str, is_crypto: bool = False, country: str = "US", db: Session | None = None
    ) -> "Money | None":
        try:
            if is_crypto:
                quote = self.get_crypto_quote(symbol_or_coin_id)
            else:
                quote = self.get_stock_quote(symbol_or_coin_id, country=country, db=db)
            return quote.get("current_price")
        except Exception:
            return None

    def get_crypto_quote(self, coin_id: str) -> dict:
        if coin_id in self._crypto_quote_cache:
            return self._crypto_quote_cache[coin_id]

        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_market_cap": "true",
            "include_24hr_change": "true",
        }
        resp = httpx.get(url, params=params)
        data = resp.json()[coin_id]
        result = {
            "coin_id": coin_id,
            "current_price": Money(Decimal(str(data["usd"])), Currency.USD),
            "currency": Currency.USD,
            "market_cap": Money(Decimal(str(data["usd_market_cap"])), Currency.USD),
            "change_24h": data["usd_24h_change"],
        }
        self._crypto_quote_cache[coin_id] = result
        return result

    def get_crypto_history(self, coin_id: str, days: int = 30) -> list[dict]:
        cache_key = f"{coin_id}:{days}"
        if cache_key in self._crypto_history_cache:
            return self._crypto_history_cache[cache_key]

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": days}
        resp = httpx.get(url, params=params)
        data = resp.json()
        result = [
            {
                "date": datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                "price": Decimal(str(price)),
            }
            for ts, price in data["prices"]
        ]
        self._crypto_history_cache[cache_key] = result
        return result


_instance: MarketDataService | None = None


def get_market_data_service() -> MarketDataService:
    global _instance
    if _instance is None:
        _instance = MarketDataService()
    return _instance
