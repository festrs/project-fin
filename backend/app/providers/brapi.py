import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx

from app.money import Money, Currency
from app.providers._http import brapi_client
from app.providers.common import DividendRecord, Symbol

logger = logging.getLogger(__name__)


class BrapiFeatureUnavailable(Exception):
    """Raised when the Brapi free plan blocks a feature (e.g. dividends)."""


def _parse_brapi_date(value):
    if not value:
        return None
    try:
        s = value.replace("Z", "+00:00") if isinstance(value, str) else value
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError, AttributeError):
        return None


class BrapiProvider:
    def __init__(self, api_key: str, base_url: str = "https://brapi.dev"):
        self._api_key = api_key
        self._base_url = base_url

    def search(self, query: str) -> list[dict]:
        resp = brapi_client.get(
            f"{self._base_url}/api/available",
            params={"search": query, "token": self._api_key},
        )
        resp.raise_for_status()
        stocks = resp.json().get("stocks", [])
        return [
            {"symbol": f"{s}.SA", "name": s, "type": "Common Stock"}
            for s in stocks
        ][:10]

    def get_quote(self, symbol: str) -> dict:
        ticker = Symbol.strip_sa(symbol)
        resp = brapi_client.get(
            f"{self._base_url}/api/quote/{ticker}",
            params={"token": self._api_key},
        )
        resp.raise_for_status()
        data = resp.json()["results"][0]

        currency = Currency.from_code(data.get("currency", "BRL"))
        return {
            "symbol": symbol,
            "name": data.get("shortName", ""),
            "current_price": Money(Decimal(str(data.get("regularMarketPrice", 0))), currency),
            "currency": currency,
            "market_cap": Money(Decimal(str(data["marketCap"])) if data.get("marketCap") else Decimal("0"), currency),
        }

    def get_dividend_data(self, symbol: str) -> dict:
        """Get annual dividend info from brapi fundamentals.

        Sums cashDividends rate for payments in the last 12 months.
        """
        ticker = Symbol.strip_sa(symbol)
        resp = brapi_client.get(
            f"{self._base_url}/api/quote/{ticker}",
            params={
                "token": self._api_key,
                "fundamental": "true",
                "dividends": "true",
            },
        )
        resp.raise_for_status()
        data = resp.json()["results"][0]

        price = Decimal(str(data.get("regularMarketPrice", 0)))
        dividends_data = data.get("dividendsData", {})
        cash_dividends = dividends_data.get("cashDividends", [])

        # Sum dividends paid in the last 12 months
        cutoff = datetime.now(timezone.utc) - timedelta(days=365)
        annual_dps = Decimal("0")
        for d in cash_dividends:
            payment_date_str = d.get("paymentDate", "")
            if not payment_date_str:
                continue
            try:
                payment_date = datetime.fromisoformat(payment_date_str.replace("Z", "+00:00"))
                if payment_date >= cutoff:
                    annual_dps += Decimal(str(d.get("rate", 0)))
            except (ValueError, TypeError):
                continue

        dividend_yield = (annual_dps / price * 100) if price > 0 and annual_dps > 0 else Decimal("0")

        return {
            "symbol": symbol,
            "dividend_per_share_annual": annual_dps,
            "dividend_yield_annual": dividend_yield,
        }

    def get_dividends(self, symbol: str) -> list[DividendRecord]:
        """Fetch full dividend history (past + announced upcoming) from Brapi.

        Brapi's `cashDividends` includes announced upcoming payments with a
        future `paymentDate`, which is what powers the upcoming-dividends view.

        Raises BrapiFeatureUnavailable if the plan doesn't include dividends.
        """
        ticker = Symbol.strip_sa(symbol)
        resp = brapi_client.get(
            f"{self._base_url}/api/quote/{ticker}",
            params={"token": self._api_key, "dividends": "true"},
        )
        try:
            payload = resp.json()
        except ValueError:
            resp.raise_for_status()
            raise

        if isinstance(payload, dict) and payload.get("error"):
            if payload.get("code") == "FEATURE_NOT_AVAILABLE":
                raise BrapiFeatureUnavailable(payload.get("message", "Dividends not in plan"))
            raise httpx.HTTPError(payload.get("message", "Brapi error"))

        results = payload.get("results", [])
        if not results:
            return []

        cash_dividends = results[0].get("dividendsData", {}).get("cashDividends", [])
        records: list[DividendRecord] = []
        for d in cash_dividends:
            rate = d.get("rate")
            if rate is None:
                continue
            ex_date = _parse_brapi_date(d.get("lastDatePrior") or d.get("lastDatePriorEx"))
            payment_date = _parse_brapi_date(d.get("paymentDate"))
            if ex_date is None and payment_date is None:
                continue
            label = (d.get("label") or "Dividend").strip()
            records.append(DividendRecord(
                dividend_type=label,
                value=Decimal(str(rate)).quantize(Decimal("0.000001")),
                record_date=ex_date or payment_date,
                ex_date=ex_date or payment_date,
                payment_date=payment_date,
            ))
        return records

    def get_fundamentals(self, symbol: str) -> dict:
        ticker = Symbol.strip_sa(symbol)
        resp = brapi_client.get(
            f"{self._base_url}/api/quote/{ticker}",
            params={"token": self._api_key, "fundamental": "true"},
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
        ticker = Symbol.strip_sa(symbol)
        resp = brapi_client.get(
            f"{self._base_url}/api/quote/{ticker}",
            params={"token": self._api_key, "dividends": "true"},
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
        ticker = Symbol.strip_sa(symbol)
        resp = brapi_client.get(
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
                "close": Decimal(str(item["close"])),
                "volume": int(item.get("volume", 0)),
            }
            for item in history
        ]
