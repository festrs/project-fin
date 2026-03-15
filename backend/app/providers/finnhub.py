from datetime import datetime, timedelta, timezone

import httpx

PERIOD_DAYS = {
    "1mo": 30,
    "3mo": 90,
    "1y": 365,
}


class FinnhubProvider:
    def __init__(self, api_key: str, base_url: str = "https://finnhub.io/api/v1"):
        self._api_key = api_key
        self._base_url = base_url

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

        return {
            "symbol": symbol,
            "name": profile_data.get("name", ""),
            "current_price": quote_data.get("c", 0.0),
            "currency": profile_data.get("currency", "USD"),
            "market_cap": profile_data.get("marketCapitalization", 0) * 1_000_000,
        }

    def get_dividend_metric(self, symbol: str) -> dict:
        """Get annual dividend info from basic financials."""
        resp = httpx.get(
            f"{self._base_url}/stock/metric",
            params={"symbol": symbol, "metric": "all", "token": self._api_key},
            timeout=10,
        )
        resp.raise_for_status()
        metric = resp.json().get("metric", {})
        return {
            "symbol": symbol,
            "dividend_per_share_annual": metric.get("dividendPerShareAnnual", 0) or 0,
            "dividend_yield_annual": metric.get("dividendYieldIndicatedAnnual", 0) or 0,
        }

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
                "close": close,
                "volume": int(volume),
            }
            for ts, close, volume in zip(data["t"], data["c"], data["v"])
        ]
