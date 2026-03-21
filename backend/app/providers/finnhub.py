import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx

from app.money import Money, Currency

logger = logging.getLogger(__name__)

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

    def get_fundamentals(self, symbol: str) -> dict:
        """Fetch fundamentals from SEC filings via /stock/financials-reported."""
        empty = {
            "ipo_years": None,
            "eps_history": [],
            "net_income_history": [],
            "debt_history": [],
            "current_net_debt_ebitda": None,
            "raw_data": [],
        }
        try:
            # IPO years from profile
            profile_resp = httpx.get(
                f"{self._base_url}/stock/profile2",
                params={"symbol": symbol, "token": self._api_key},
                timeout=10,
            )
            profile_resp.raise_for_status()
            profile = profile_resp.json()
            ipo_str = profile.get("ipo")
            if ipo_str:
                ipo_date = datetime.strptime(ipo_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                ipo_years = (datetime.now(timezone.utc) - ipo_date).days // 365
            else:
                ipo_years = None

            # Financial statements from SEC filings
            resp = httpx.get(
                f"{self._base_url}/stock/financials-reported",
                params={"symbol": symbol, "token": self._api_key, "freq": "annual"},
                timeout=15,
            )
            resp.raise_for_status()
            filings = resp.json().get("data", [])

            if not filings:
                empty["ipo_years"] = ipo_years
                return empty

            # Sort by year ascending
            filings.sort(key=lambda f: f.get("year", 0))

            eps_history = []
            net_income_history = []
            debt_history = []
            raw_data = []

            for filing in filings:
                year = filing.get("year")
                report = filing.get("report", {})

                eps = self._extract_field(report, "ic", [
                    "earningspersharediluted",
                    "earningspersharebasicanddiluted",
                    "earningspersharebasic",
                ])
                net_income = self._extract_field(report, "ic", [
                    "netincome",
                    "netincomeloss",
                    "profitloss",
                ])
                operating_income = self._extract_field(report, "ic", [
                    "operatingincome",
                    "operatingincomeloss",
                ])
                total_debt = self._extract_field(report, "bs", [
                    "longtermdebt",
                    "longtermdebtnoncurrent",
                    "totaldebt",
                ])

                eps_val = eps if eps is not None else 0.0
                ni_val = net_income if net_income is not None else 0.0
                oi_val = operating_income if operating_income is not None else 0.0
                debt_val = total_debt if total_debt is not None else 0.0
                debt_ratio = (debt_val / oi_val) if oi_val != 0 else 0.0

                eps_history.append(eps_val)
                net_income_history.append(ni_val)
                debt_history.append(debt_ratio)
                raw_data.append({
                    "year": year,
                    "eps": eps_val,
                    "net_income": ni_val,
                    "net_debt_ebitda": round(debt_ratio, 4),
                })

            current_net_debt_ebitda = debt_history[-1] if debt_history else None

            return {
                "ipo_years": ipo_years,
                "eps_history": eps_history,
                "net_income_history": net_income_history,
                "debt_history": debt_history,
                "current_net_debt_ebitda": current_net_debt_ebitda,
                "raw_data": raw_data,
            }
        except Exception:
            logger.warning("Failed to fetch fundamentals for %s", symbol, exc_info=True)
            return empty

    @staticmethod
    def _extract_field(report: dict, section: str, concept_keywords: list[str]) -> float | None:
        """Extract a value from a SEC filing report section by matching concept keywords."""
        items = report.get(section, [])
        for keyword in concept_keywords:
            for item in items:
                concept = (item.get("concept") or "").lower().replace("-", "").replace("_", "")
                if keyword in concept:
                    val = item.get("value")
                    if val is not None:
                        return float(val)
        return None

    def get_market_news(self, category: str = "general") -> list[dict]:
        """Fetch market news from Finnhub. Returns up to 10 items."""
        resp = httpx.get(
            f"{self._base_url}/news",
            params={"category": category, "minId": 0, "token": self._api_key},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json()
        return [
            {
                "id": item.get("id", 0),
                "category": item.get("category", ""),
                "headline": item.get("headline", ""),
                "summary": item.get("summary", ""),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "datetime": item.get("datetime", 0),
                "image": item.get("image", ""),
            }
            for item in items[:10]
        ]

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
