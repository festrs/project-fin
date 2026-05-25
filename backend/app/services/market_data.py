import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx

from app.money import Money, Currency
from cachetools import TTLCache
from sqlalchemy.orm import Session

from app.config import settings
from app.models.dividend_history import DividendHistory
from app.models.market_quote import MarketQuote
from app.providers._http import coingecko_client
from app.providers.finnhub import FinnhubProvider
from app.providers.brapi import BrapiProvider
from app.providers.yfinance import YFinanceProvider

logger = logging.getLogger(__name__)

#: Symbol → CoinGecko coin_id. Single source of truth shared by the
#: stocks router (`/api/stocks/{symbol}` + `/history`) and the mobile
#: router (`/api/mobile/quotes` batch). Without this, single-quote and
#: history calls fall through to yfinance, which returns a small-cap
#: stock literally named "BTC" (~$30) instead of Bitcoin.
CRYPTO_COINGECKO_MAP: dict[str, str] = {
    "BTC": "bitcoin", "BTC-USD": "bitcoin",
    "ETH": "ethereum", "ETH-USD": "ethereum",
    "SOL": "solana", "SOL-USD": "solana",
    "ADA": "cardano", "ADA-USD": "cardano",
    "DOT": "polkadot", "DOT-USD": "polkadot",
    "AVAX": "avalanche-2", "AVAX-USD": "avalanche-2",
    "MATIC": "matic-network", "MATIC-USD": "matic-network",
    "LINK": "chainlink", "LINK-USD": "chainlink",
    "UNI": "uniswap", "UNI-USD": "uniswap",
    "USDT": "tether", "USDT-USD": "tether",
    "USDC": "usd-coin", "USDC-USD": "usd-coin",
    "DAI": "dai", "DAI-USD": "dai",
}
#: Display names for the canonical coin_ids — used to populate the
#: `name` field on a crypto quote response (the CoinGecko simple-price
#: endpoint doesn't return one).
CRYPTO_DISPLAY_NAMES: dict[str, str] = {
    "bitcoin": "Bitcoin",
    "ethereum": "Ethereum",
    "solana": "Solana",
    "cardano": "Cardano",
    "polkadot": "Polkadot",
    "avalanche-2": "Avalanche",
    "matic-network": "Polygon",
    "chainlink": "Chainlink",
    "uniswap": "Uniswap",
    "tether": "Tether",
    "usd-coin": "USD Coin",
    "dai": "Dai",
}
CRYPTO_CLASS_NAMES = {"Crypto", "Cryptos", "Stablecoins"}


def compute_yield_from_history(
    db: Session, symbol: str, current_price: Decimal
) -> Decimal | None:
    """Trailing-12m dividend yield computed from `DividendHistory`.

    Replaces the broken yfinance/Brapi `dividend_yield` field for BR tickers:
    yfinance reports ITUB3 at 0.53% (only the latest JCP), real ~7.6%. By
    summing recorded payments ourselves we get the same number Status Invest's
    page shows and match the iOS Dashboard's TTM-based monthly income card.

    Returns None when there are no recent payments or the price is zero —
    callers should leave the existing yield in place rather than overwrite
    with garbage.
    """
    if current_price is None or current_price <= 0:
        return None
    cutoff = date.today() - timedelta(days=365)
    rows = (
        db.query(DividendHistory)
        .filter(
            DividendHistory.symbol == symbol,
            DividendHistory.payment_date >= cutoff,
        )
        .all()
    )
    if not rows:
        return None
    total = sum((Decimal(r.value) for r in rows), Decimal("0"))
    return (total / current_price * Decimal("100")).quantize(Decimal("0.01"))


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
        self._yfinance = YFinanceProvider()
        self._quote_cache: TTLCache = TTLCache(maxsize=256, ttl=300)
        self._history_cache: TTLCache = TTLCache(maxsize=256, ttl=900)
        self._crypto_quote_cache: TTLCache = TTLCache(maxsize=256, ttl=120)
        self._crypto_history_cache: TTLCache = TTLCache(maxsize=256, ttl=900)
        # Short TTL: shields Yahoo from hammering during the iOS debouncer's
        # rapid-fire calls but stays fresh enough to not feel stale.
        self._search_cache: TTLCache = TTLCache(maxsize=256, ttl=60)

    def _get_provider(self, country: str):
        return self._brapi if country == "BR" else self._finnhub

    def fetch_live_quote(self, symbol: str, country: str = "US") -> dict:
        """Hit yfinance first, fall back to Finnhub/Brapi on failure.

        Always reaches a live provider — no TTL or DB lookup. Used by the cron
        path that needs fresh data and as the cold-fetch arm of
        ``get_stock_quote``. yfinance is queried with the `.SA`-suffixed form
        for BR tickers (Yahoo only knows them that way); fallback providers
        don't expose dividend_yield, so the field will be None when the chain
        falls through to Finnhub/Brapi.
        """
        from app.providers.common import Symbol as _Symbol

        yf_symbol = _Symbol.with_sa(symbol) if country == "BR" else symbol
        try:
            quote = self._yfinance.get_quote(yf_symbol)
            # Echo the input symbol back so storage/cache keys stay consistent
            # — callers track by the canonical (no-suffix-stripping) form.
            quote["symbol"] = symbol
            return quote
        except Exception:
            logger.warning("yfinance quote failed for %s (yf=%s), falling back", symbol, yf_symbol, exc_info=True)
        fallback = self._get_provider(country).get_quote(symbol)
        fallback.setdefault("dividend_yield", None)
        return fallback

    def get_stock_quote(self, symbol: str, country: str = "US", db: Session | None = None, db_only: bool = False) -> dict:
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
                    "dividend_yield": stored.dividend_yield,
                }
                self._quote_cache[symbol] = result
                return result

        # In db_only mode, don't call live providers
        if db_only:
            raise LookupError(f"No cached quote for {symbol}")

        result = self.fetch_live_quote(symbol, country=country)
        self._quote_cache[symbol] = result

        # Store in DB for future reads
        if db is not None:
            self._upsert_quote(db, symbol, country, result)

        return result

    @staticmethod
    def _upsert_quote(db: Session, symbol: str, country: str, result: dict) -> None:
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
        # For BR tickers, recompute the yield from records — yfinance/Brapi
        # report only the latest payment for B3 stocks (e.g. ITUB3 = 0.53%).
        # When we have history we trust the records; otherwise keep the
        # provider value so brand-new positions still show *something*.
        provider_yield = result.get("dividend_yield")
        if country == "BR":
            computed = compute_yield_from_history(db, symbol, price_amount)
            quote.dividend_yield = computed if computed is not None else provider_yield
        else:
            quote.dividend_yield = provider_yield
        quote.country = country
        quote.updated_at = datetime.now(timezone.utc)
        db.commit()

    PERIOD_DAYS = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "5y": 1825}

    def get_stock_history(
        self, symbol: str, period: str = "1mo", country: str = "US", db: Session | None = None
    ) -> list[dict]:
        cache_key = f"{symbol}:{period}"
        if cache_key in self._history_cache:
            return self._history_cache[cache_key]

        result = self._try_db_history(db, symbol, period)
        if not result:
            result = self._fetch_from_providers(symbol, period, country)
        if result and db is not None:
            from app.repositories.price_history_repo import store_history
            store_history(db, symbol, result, "BRL" if country == "BR" else "USD")

        self._history_cache[cache_key] = result
        return result

    def _try_db_history(self, db: Session | None, symbol: str, period: str) -> list[dict]:
        if db is None or period == "max":
            return []
        days = self.PERIOD_DAYS.get(period, 0)
        if not days:
            return []
        from datetime import timedelta
        from_date = (datetime.now(timezone.utc) - timedelta(days=days)).date()
        from app.repositories.price_history_repo import read_history
        return read_history(db, symbol, from_date)

    def _fetch_from_providers(self, symbol: str, period: str, country: str) -> list[dict]:
        from app.providers.common import Symbol

        if country == "BR":
            try:
                result = self._brapi.get_history(symbol, period)
            except Exception:
                logger.warning("Brapi history failed for %s period=%s", symbol, period)
                result = []
            if not result:
                logger.info("Falling back to yfinance for %s period=%s", symbol, period)
                result = self._yfinance.get_history(Symbol.with_sa(symbol), period)
            return result

        return self._yfinance.get_history(symbol, period)

    def get_quote_safe(
        self, symbol_or_coin_id: str, is_crypto: bool = False, country: str = "US",
        db: Session | None = None, db_only: bool = False,
    ) -> "Money | None":
        try:
            if is_crypto:
                if db_only:
                    return None
                quote = self.get_crypto_quote(symbol_or_coin_id)
            else:
                quote = self.get_stock_quote(symbol_or_coin_id, country=country, db=db, db_only=db_only)
            return quote.get("current_price")
        except Exception:
            return None

    async def search_stocks(
        self,
        query: str,
        asset_class: str | None = None,
        max_results: int = 15,
    ) -> list[dict]:
        """Class-aware unified search.

        Routes by ``asset_class`` (iOS ``AssetClassType.rawValue``):
          - ``"crypto"`` → CoinGecko only.
          - ``"rendaFixa"`` → ``[]`` (manual entry only).
          - any other / ``None`` → yfinance + best-effort Brapi enrichment
            on the top SAO results.

        Cached for 60 s by ``(query.lower(), asset_class)`` so the iOS
        debouncer's rapid-fire calls don't hammer Yahoo.
        """
        import asyncio

        cache_key = f"{(query or '').strip().lower()}::{asset_class or ''}"
        cached = self._search_cache.get(cache_key)
        if cached is not None:
            return cached

        if asset_class == "rendaFixa":
            self._search_cache[cache_key] = []
            return []

        if asset_class == "crypto":
            results = await asyncio.to_thread(self.search_crypto, query, max_results)
            self._search_cache[cache_key] = results
            return results

        yfin = await asyncio.to_thread(
            self._yfinance.search, query, max_results, asset_class
        )

        # Enrich the top BR results with Brapi price/logo. Cap at 3 to stay
        # within Brapi free-plan budgets while covering the most likely picks.
        sa_targets = [r["symbol"] for r in yfin if r["symbol"].endswith(".SA")][:3]
        if sa_targets:
            enrichments = await asyncio.gather(*[
                asyncio.to_thread(self._brapi.enrich_one, sym) for sym in sa_targets
            ])
            enrichment_map = dict(zip(sa_targets, enrichments))
            for r in yfin:
                e = enrichment_map.get(r["symbol"])
                if e:
                    r.update(e)

        self._search_cache[cache_key] = yfin
        return yfin

    def search_crypto(self, query: str, limit: int = 10) -> list[dict]:
        """Search CoinGecko coins by name/symbol. Returns lightweight matches.

        Output shape mirrors stock-search results so the iOS client can render
        a single unified list:
            {id, symbol, name, type: "crypto", logo}
        Where `id` is the CoinGecko coin id (e.g. "bitcoin"), and `symbol` is
        the trading code shown to the user (e.g. "BTC").
        """
        try:
            resp = coingecko_client.get(
                "https://api.coingecko.com/api/v3/search",
                params={"query": query},
                timeout=8,
            )
            resp.raise_for_status()
            coins = resp.json().get("coins", [])
        except Exception:
            logger.warning("CoinGecko search failed for %s", query, exc_info=True)
            return []

        results = []
        for c in coins[:limit]:
            symbol = (c.get("symbol") or "").upper()
            if not symbol:
                continue
            results.append({
                "id": c.get("id") or symbol,
                "symbol": symbol,
                "name": c.get("name") or symbol,
                "type": "crypto",
                "logo": c.get("thumb") or c.get("large"),
                "currency": "USD",
            })
        return results

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
        resp = coingecko_client.get(url, params=params)
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

    def get_crypto_quote_for_symbol(self, symbol: str) -> dict | None:
        """Resolve a ticker (e.g. ``BTC``) to a quote dict shaped like
        ``get_stock_quote``. Returns ``None`` if the symbol isn't in
        :data:`CRYPTO_COINGECKO_MAP`, so callers can fall through to the
        stock provider without a try/except dance.
        """
        coin_id = CRYPTO_COINGECKO_MAP.get(symbol.upper())
        if not coin_id:
            return None
        base = self.get_crypto_quote(coin_id)
        # Stock-quote consumers (`_quote_to_response` in routers/stocks.py
        # and `_fetch_one_quote` in routers/mobile.py) read `symbol` and
        # `name` directly. CoinGecko returns neither, so augment here.
        return {
            **base,
            "symbol": symbol.upper(),
            "name": CRYPTO_DISPLAY_NAMES.get(coin_id, symbol.upper()),
        }

    def get_crypto_history_for_symbol(
        self, symbol: str, days: int = 30
    ) -> list[dict] | None:
        """Same routing as :meth:`get_crypto_quote_for_symbol`, for the
        chart endpoint. Returns ``None`` for non-crypto symbols.
        """
        coin_id = CRYPTO_COINGECKO_MAP.get(symbol.upper())
        if not coin_id:
            return None
        return self.get_crypto_history(coin_id, days)

    def get_crypto_history(self, coin_id: str, days: int = 30) -> list[dict]:
        cache_key = f"{coin_id}:{days}"
        if cache_key in self._crypto_history_cache:
            return self._crypto_history_cache[cache_key]

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": days}
        resp = coingecko_client.get(url, params=params)
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
