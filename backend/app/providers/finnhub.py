from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx

from app.money import Money, Currency

PERIOD_DAYS = {
    "1mo": 30,
    "3mo": 90,
    "1y": 365,
}


class FinnhubProvider:
    def __init__(self, api_key: str, base_url: str = "https://finnhub.io/api/v1"):
        self._api_key = api_key
        self._base_url = base_url

    def search(self, query: str) -> list[dict]:
        resp = httpx.get(
            f"{self._base_url}/search",
            params={"q": query, "token": self._api_key},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("result", [])
        return [
            {
                "symbol": r["symbol"],
                "name": r.get("description", ""),
                "type": r.get("type", ""),
            }
            for r in results
            if "." not in r.get("symbol", "")  # filter out foreign exchanges
        ][:10]

    def get_quote(self, symbol: str) -> dict:
        quote_resp = httpx.get(
            f"{self._base_url}/quote",
            params={"symbol": symbol, "token": self._api_key},
        )
        quote_resp.raise_for_status()
        quote_data = quote_resp.json()

        profile_resp = httpx.get(
            f"{self._base_url}/stock/profile2",
            params={"symbol": symbol, "token": self._api_key},
        )
        profile_resp.raise_for_status()
        profile_data = profile_resp.json()

        currency = Currency.from_code(profile_data.get("currency", "USD"))
        return {
            "symbol": symbol,
            "name": profile_data.get("name", ""),
            "current_price": Money(Decimal(str(quote_data.get("c", 0))), currency),
            "currency": currency,
            "market_cap": Money(Decimal(str(profile_data.get("marketCapitalization", 0))) * Decimal("1000000"), currency),
        }

    def get_splits(self, symbol: str, from_date: str, to_date: str) -> list[dict]:
        """GET /stock/split for a symbol within a date range."""
        resp = httpx.get(
            f"{self._base_url}/stock/split",
            params={"symbol": symbol, "from": from_date, "to": to_date, "token": self._api_key},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_history(self, symbol: str, period: str = "1mo") -> list[dict]:
        now = datetime.now(timezone.utc)
        days = PERIOD_DAYS.get(period, 30)
        from_ts = int((now - timedelta(days=days)).timestamp())
        to_ts = int(now.timestamp())

        resp = httpx.get(
            f"{self._base_url}/stock/candle",
            params={
                "symbol": symbol,
                "resolution": "D",
                "from": from_ts,
                "to": to_ts,
                "token": self._api_key,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("s") != "ok":
            return []

        return [
            {
                "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                "close": Decimal(str(close)),
                "volume": int(volume),
            }
            for ts, close, volume in zip(data["t"], data["c"], data["v"])
        ]
