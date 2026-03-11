from datetime import datetime, timezone

import httpx


def _strip_sa(symbol: str) -> str:
    return symbol.removesuffix(".SA")


class BrapiProvider:
    def __init__(self, api_key: str, base_url: str = "https://brapi.dev"):
        self._api_key = api_key
        self._base_url = base_url

    def get_quote(self, symbol: str) -> dict:
        ticker = _strip_sa(symbol)
        resp = httpx.get(
            f"{self._base_url}/api/quote/{ticker}",
            params={"token": self._api_key},
        )
        resp.raise_for_status()
        data = resp.json()["results"][0]

        return {
            "symbol": symbol,
            "name": data.get("shortName", ""),
            "current_price": data.get("regularMarketPrice", 0.0),
            "currency": data.get("currency", "BRL"),
            "market_cap": data.get("marketCap", 0),
        }

    def get_history(self, symbol: str, period: str = "1mo") -> list[dict]:
        ticker = _strip_sa(symbol)
        resp = httpx.get(
            f"{self._base_url}/api/quote/{ticker}",
            params={
                "range": period,
                "interval": "1d",
                "token": self._api_key,
            },
        )
        resp.raise_for_status()
        data = resp.json()["results"][0]
        history = data.get("historicalDataPrice", [])

        return [
            {
                "date": datetime.fromtimestamp(item["date"], tz=timezone.utc).strftime("%Y-%m-%d"),
                "close": item["close"],
                "volume": int(item.get("volume", 0)),
            }
            for item in history
        ]
