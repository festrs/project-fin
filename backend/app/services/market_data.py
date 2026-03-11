from datetime import datetime

import httpx
import yfinance
from cachetools import TTLCache


class MarketDataService:
    def __init__(self):
        self._stock_quote_cache: TTLCache = TTLCache(maxsize=256, ttl=300)
        self._stock_history_cache: TTLCache = TTLCache(maxsize=256, ttl=900)
        self._crypto_quote_cache: TTLCache = TTLCache(maxsize=256, ttl=120)
        self._crypto_history_cache: TTLCache = TTLCache(maxsize=256, ttl=900)

    def get_stock_quote(self, symbol: str) -> dict:
        if symbol in self._stock_quote_cache:
            return self._stock_quote_cache[symbol]

        ticker = yfinance.Ticker(symbol)
        info = ticker.info
        result = {
            "symbol": symbol,
            "name": info.get("shortName", ""),
            "current_price": info.get("currentPrice", 0.0),
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("marketCap", 0),
        }
        self._stock_quote_cache[symbol] = result
        return result

    def get_stock_history(self, symbol: str, period: str = "1mo") -> list[dict]:
        cache_key = f"{symbol}:{period}"
        if cache_key in self._stock_history_cache:
            return self._stock_history_cache[cache_key]

        ticker = yfinance.Ticker(symbol)
        df = ticker.history(period=period)
        result = [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "close": row["Close"],
                "volume": int(row["Volume"]),
            }
            for idx, row in df.iterrows()
        ]
        self._stock_history_cache[cache_key] = result
        return result

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
            "current_price": data["usd"],
            "currency": "USD",
            "market_cap": data["usd_market_cap"],
            "change_24h": data["usd_24h_change"],
        }
        self._crypto_quote_cache[coin_id] = result
        return result

    def get_quote_safe(self, symbol_or_coin_id: str, is_crypto: bool = False) -> float | None:
        """Return current price or None if fetch fails."""
        try:
            if is_crypto:
                quote = self.get_crypto_quote(symbol_or_coin_id)
            else:
                quote = self.get_stock_quote(symbol_or_coin_id)
            return quote.get("current_price")
        except Exception:
            return None

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
                "date": datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d"),
                "price": price,
            }
            for ts, price in data["prices"]
        ]
        self._crypto_history_cache[cache_key] = result
        return result
