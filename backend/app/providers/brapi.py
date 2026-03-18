from datetime import datetime, timedelta, timezone

import httpx


def _strip_sa(symbol: str) -> str:
    return symbol.removesuffix(".SA")


class BrapiProvider:
    def __init__(self, api_key: str, base_url: str = "https://brapi.dev"):
        self._api_key = api_key
        self._base_url = base_url

    def search(self, query: str) -> list[dict]:
        resp = httpx.get(
            f"{self._base_url}/api/available",
            params={"search": query, "token": self._api_key},
            timeout=10,
        )
        resp.raise_for_status()
        stocks = resp.json().get("stocks", [])
        return [
            {"symbol": f"{s}.SA", "name": s, "type": "Common Stock"}
            for s in stocks
        ][:10]

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

    def get_dividend_data(self, symbol: str) -> dict:
        """Get annual dividend info from brapi fundamentals.

        Sums cashDividends rate for payments in the last 12 months.
        """
        ticker = _strip_sa(symbol)
        resp = httpx.get(
            f"{self._base_url}/api/quote/{ticker}",
            params={
                "token": self._api_key,
                "fundamental": "true",
                "dividends": "true",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()["results"][0]

        price = data.get("regularMarketPrice", 0)
        dividends_data = data.get("dividendsData", {})
        cash_dividends = dividends_data.get("cashDividends", [])

        # Sum dividends paid in the last 12 months
        cutoff = datetime.now(timezone.utc) - timedelta(days=365)
        annual_dps = 0.0
        for d in cash_dividends:
            payment_date_str = d.get("paymentDate", "")
            if not payment_date_str:
                continue
            try:
                payment_date = datetime.fromisoformat(payment_date_str.replace("Z", "+00:00"))
                if payment_date >= cutoff:
                    annual_dps += d.get("rate", 0)
            except (ValueError, TypeError):
                continue

        dividend_yield = (annual_dps / price * 100) if price > 0 and annual_dps > 0 else 0

        return {
            "symbol": symbol,
            "dividend_per_share_annual": round(annual_dps, 6),
            "dividend_yield_annual": round(dividend_yield, 4),
        }

    def get_fundamentals(self, symbol: str) -> dict:
        ticker = _strip_sa(symbol)
        resp = httpx.get(
            f"{self._base_url}/api/quote/{ticker}",
            params={"token": self._api_key, "fundamental": "true"},
            timeout=15,
        )
        resp.raise_for_status()
        resp.json()["results"][0]
        # Minimal stub — real Brapi may not have multi-year data
        return {
            "ipo_years": None,
            "eps_history": [],
            "net_income_history": [],
            "debt_history": [],
            "current_net_debt_ebitda": None,
            "raw_data": [],
        }

    def get_splits(self, symbol: str) -> list[dict]:
        """Get stock splits from quote endpoint with dividends=true."""
        ticker = _strip_sa(symbol)
        resp = httpx.get(
            f"{self._base_url}/api/quote/{ticker}",
            params={"token": self._api_key, "dividends": "true"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()["results"][0]
        dividends_data = data.get("dividendsData", {})
        stock_dividends = dividends_data.get("stockDividends", [])

        splits = []
        for entry in stock_dividends:
            if entry.get("label") == "DESDOBRAMENTO":
                date_str = entry.get("lastDatePrior", "")
                if date_str:
                    splits.append({
                        "symbol": symbol,
                        "date": date_str[:10],
                        "fromFactor": 1,
                        "toFactor": entry.get("factor", 1),
                    })
        return splits

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
