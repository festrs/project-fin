"""Status Invest scraper — single source of truth for BR (.SA) market data.

Why this provider exists:
  Status Invest aggregates B3 dividend history (stocks, FIIs, BDRs) into a
  single endpoint with PT-BR labels (`Dividendo`, `JCP`, `Rendimento`) and
  computes a trailing-12m yield identical to what Brazilian retail investors
  expect. It replaces the previous Brapi + yfinance + DadosDeMercado fan-out,
  whose mismatched labels and partial coverage caused duplicate dividend rows
  and broken yield numbers (yfinance reported ITUB3 at 0.53% — actual ~7.6%).

Endpoints scraped:
  /fii/companytickerprovents?ticker={X}&chartProventsType=2
        — JSON list of every dividend payment, past + projected. The /fii/
          path serves stocks, FIIs, and BDRs equally.
  /acoes/{ticker_lower}  (or /fundos-imobiliarios/...)
        — HTML page with indicator cards (price, D.Y, P/L, P/VP, ...).

Politeness:
  - 24h in-memory TTL cache per (method, symbol) — typical scrape only fires
    once per ticker per day.
  - Browser User-Agent + matching Referer; Status Invest sees us as a normal
    visitor.
  - Single retry on 429 with a short backoff. Two 429s in a row surface as an
    HTTPStatusError so the scheduler can mark the symbol failed and move on.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import httpx
from cachetools import TTLCache

from .common import DividendRecord, Symbol


logger = logging.getLogger(__name__)


_BASE_URL = "https://statusinvest.com.br"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_TIMEOUT = 10.0
_CACHE_TTL_SECONDS = 86400  # 24h
_CACHE_MAX = 1024
_RETRY_BACKOFF_SECONDS = 2.0

# Indicator-card regex: Status Invest emits each metric as a small block with
# `<h3 class="title">NAME</h3> ... <strong class="value">VALUE</strong>`.
_CARD_RE = re.compile(
    r'<h3[^>]*class="title[^"]*"[^>]*>([^<]+)</h3>\s*'
    r'(?:(?!</h3>).)*?'
    r'<strong[^>]*class="value[^"]*"[^>]*>([^<]*)</strong>',
    re.DOTALL,
)


def _parse_pt_br_decimal(raw: str) -> Decimal | None:
    """Convert "41,39" → Decimal('41.39'); strip percent / whitespace."""
    if not raw:
        return None
    cleaned = raw.replace("%", "").replace(".", "").replace(",", ".").strip()
    if not cleaned or cleaned == "-":
        return None
    try:
        return Decimal(cleaned)
    except (ValueError, ArithmeticError):
        return None


class StatusInvestProvider:
    """One scraper for every BR ticker — dividends + quotes."""

    def __init__(self, base_url: str = _BASE_URL):
        self._base_url = base_url
        self._cache: TTLCache = TTLCache(maxsize=_CACHE_MAX, ttl=_CACHE_TTL_SECONDS)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_dividends(self, symbol: str) -> list[DividendRecord]:
        cache_key = ("dividends", Symbol.canonicalize(symbol))
        if cache_key in self._cache:
            return self._cache[cache_key]

        bare = Symbol.strip_sa(symbol).upper()
        url = f"{self._base_url}/fii/companytickerprovents"
        params = {"ticker": bare, "chartProventsType": "2"}
        referer = f"{self._base_url}/acoes/{bare.lower()}"

        payload = self._get_with_retry(url, params=params, referer=referer).json()
        records = self._parse_dividends_payload(payload)
        self._cache[cache_key] = records
        return records

    def get_quote(self, symbol: str) -> dict[str, Any]:
        cache_key = ("quote", Symbol.canonicalize(symbol))
        if cache_key in self._cache:
            return self._cache[cache_key]

        bare = Symbol.strip_sa(symbol).upper()
        # FIIs live on a different path. We try /acoes/ first; on 404 the
        # caller can retry with /fundos-imobiliarios/. For now we rely on the
        # /acoes/ path serving both — Status Invest historically renders the
        # same indicator block at both URLs.
        url = f"{self._base_url}/acoes/{bare.lower()}"
        resp = self._get_with_retry(url, referer=url)
        cards = _CARD_RE.findall(resp.text)
        result = self._parse_quote_cards(cards, canonical=Symbol.canonicalize(symbol))
        self._cache[cache_key] = result
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_with_retry(self, url: str, *, params: dict | None = None,
                        referer: str | None = None) -> httpx.Response:
        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/json, text/html;q=0.9",
        }
        if referer:
            headers["Referer"] = referer

        for attempt in (1, 2):
            resp = httpx.get(url, params=params, headers=headers, timeout=_TIMEOUT)
            if resp.status_code == 429 and attempt == 1:
                logger.warning("Status Invest rate-limited %s; retrying in %.1fs", url, _RETRY_BACKOFF_SECONDS)
                time.sleep(_RETRY_BACKOFF_SECONDS)
                continue
            resp.raise_for_status()
            return resp
        # Second 429 — surface to caller.
        resp.raise_for_status()
        return resp  # unreachable; keeps mypy happy

    @staticmethod
    def _parse_dividends_payload(payload: dict | None) -> list[DividendRecord]:
        # Status Invest returns `null` (not a JSON object) for invalid tickers
        # — fixed-income notes, fractional shares, BDRs unknown to it. Treat
        # any non-dict response as "no records" rather than crashing the
        # scheduler's per-symbol loop.
        if not isinstance(payload, dict):
            return []
        rows = payload.get("assetEarningsModels", []) or []
        records: list[DividendRecord] = []
        for r in rows:
            ed = StatusInvestProvider._parse_date(r.get("ed"))
            pd = StatusInvestProvider._parse_date(r.get("pd"))
            if ed is None:
                continue
            try:
                value = Decimal(str(r["v"]))
            except (KeyError, ValueError, ArithmeticError):
                continue
            records.append(
                DividendRecord(
                    dividend_type=r.get("et", "Dividend"),
                    value=value,
                    record_date=ed,
                    ex_date=ed,
                    payment_date=pd,
                )
            )
        return records

    @staticmethod
    def _parse_quote_cards(cards: list[tuple[str, str]], canonical: str) -> dict[str, Any]:
        # Build a name→value lookup, then pick out the few cards we care about.
        # html.unescape() is unnecessary for plain ASCII metric names ("Valor atual",
        # "D.Y"), and Status Invest reliably emits them ASCII-clean.
        index = {name.strip(): val.strip() for name, val in cards}
        price = _parse_pt_br_decimal(index.get("Valor atual", ""))
        yld = _parse_pt_br_decimal(index.get("D.Y", ""))
        return {
            "symbol": canonical,
            "name": canonical,
            "current_price": price,
            "currency": "BRL",
            "market_cap": None,
            "dividend_yield": yld,
        }

    @staticmethod
    def _parse_date(raw: str | None) -> date | None:
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%d/%m/%Y").date()
        except ValueError:
            return None
