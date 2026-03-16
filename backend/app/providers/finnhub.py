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

    def get_dividends_for_year(self, symbol: str, year: int) -> dict:
        """Get dividends with payment date in the given year."""
        resp = httpx.get(
            f"{self._base_url}/stock/dividend",
            params={
                "symbol": symbol,
                "from": f"{year}-01-01",
                "to": f"{year}-12-31",
                "token": self._api_key,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        # Sum dividends where payDate falls in the target year
        total_dps = 0.0
        for d in data:
            pay_date = d.get("payDate", "")
            if pay_date and pay_date.startswith(str(year)):
                total_dps += d.get("amount", 0)

        return {
            "symbol": symbol,
            "dividend_per_share_annual": round(total_dps, 6),
            "dividend_yield_annual": 0,
        }

    def get_fundamentals(self, symbol: str) -> dict:
        """Get fundamental financial data for scoring."""
        profile_resp = httpx.get(
            f"{self._base_url}/stock/profile2",
            params={"symbol": symbol, "token": self._api_key},
        )
        profile_resp.raise_for_status()
        profile_data = profile_resp.json()

        ipo_str = profile_data.get("ipo")
        if ipo_str:
            ipo_date = datetime.strptime(ipo_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            ipo_years = (datetime.now(timezone.utc) - ipo_date).days // 365
        else:
            ipo_years = None

        fin_resp = httpx.get(
            f"{self._base_url}/stock/financials-reported",
            params={"symbol": symbol, "freq": "annual", "token": self._api_key},
        )
        fin_resp.raise_for_status()
        fin_data = fin_resp.json()

        reports = sorted(fin_data.get("data", []), key=lambda r: r.get("year", 0))

        eps_history = []
        net_income_history = []
        debt_history = []
        raw_data = []

        for entry in reports:
            year = entry.get("year")
            report = entry.get("report", {})
            ic = report.get("ic", {})
            bs = report.get("bs", {})

            eps = (ic.get("dilutedEPS") or {}).get("value", 0) or 0
            net_income = (ic.get("netIncome") or {}).get("value", 0) or 0
            ebitda = (ic.get("ebitda") or {}).get("value", 0) or 0
            total_debt = (bs.get("totalDebt") or {}).get("value", 0) or 0

            net_debt_ebitda = (total_debt / ebitda) if ebitda != 0 else 0

            eps_history.append(float(eps))
            net_income_history.append(float(net_income))
            debt_history.append(float(net_debt_ebitda))
            raw_data.append({
                "year": year,
                "eps": float(eps),
                "net_income": float(net_income),
                "net_debt_ebitda": float(net_debt_ebitda),
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
