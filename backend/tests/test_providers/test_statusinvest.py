"""Tests for StatusInvestProvider — the single BR data source.

The provider hits two Status Invest URLs:
  • dividends: /fii/companytickerprovents?ticker={SYM}&chartProventsType=2
    (path works for stocks, FIIs, and BDRs — single endpoint)
  • quotes:    /acoes/{ticker_lower}  (HTML scrape of indicator cards)

Tests use captured PoC fixtures to verify:
  - full dividend history is parsed (186 records for ITUB3)
  - .SA suffix is stripped before the URL is built
  - PT-BR labels (Dividendo / JCP / Rendimento) pass through unchanged
  - future-projected payments are preserved
  - parsing is idempotent
  - quote HTML extraction returns price + computed dividend_yield
  - 404 raises an httpx error
  - in-memory TTL cache short-circuits repeated calls
  - the request includes a real User-Agent (not python-httpx)
  - 429 triggers a single retry then surfaces the error
"""
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch, MagicMock

import httpx
import pytest

from app.providers.statusinvest import StatusInvestProvider
from app.providers.common import DividendRecord


FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text()


def _mock_resp(*, json_payload=None, text=None, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    if json_payload is not None:
        resp.json.return_value = json_payload
    if text is not None:
        resp.text = text
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"{status_code}", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# get_dividends
# ---------------------------------------------------------------------------

class TestGetDividends:
    def test_parses_full_history_for_itub3(self):
        provider = StatusInvestProvider()
        import json
        payload = json.loads(_load("statusinvest_itub3.json"))

        with patch("app.providers.statusinvest.httpx.get",
                   return_value=_mock_resp(json_payload=payload)):
            records = provider.get_dividends("ITUB3.SA")

        assert len(records) == 186, "ITUB3 fixture has 186 records since 2007"
        # All records are DividendRecord instances with BRL values.
        assert all(isinstance(r, DividendRecord) for r in records)
        # Types preserved as PT-BR labels (no normalization layer).
        types = {r.dividend_type for r in records}
        assert "JCP" in types
        assert "Dividendo" in types or "Dividend" in types
        # All values positive Decimals.
        assert all(isinstance(r.value, Decimal) and r.value > 0 for r in records)

    def test_includes_future_projected_payments(self):
        """Status Invest publishes upcoming payments — ex_date can be > today."""
        provider = StatusInvestProvider()
        import json
        payload = json.loads(_load("statusinvest_itub3.json"))

        with patch("app.providers.statusinvest.httpx.get",
                   return_value=_mock_resp(json_payload=payload)):
            records = provider.get_dividends("ITUB3.SA")

        # The fixture contains a 2026-11-30 JCP that hasn't been paid yet.
        future = [r for r in records if r.ex_date >= date(2026, 11, 1)]
        assert len(future) >= 1, "Expected at least one future-projected entry"

    def test_strips_sa_suffix_in_request(self):
        provider = StatusInvestProvider()
        with patch("app.providers.statusinvest.httpx.get",
                   return_value=_mock_resp(json_payload={"assetEarningsModels": []})) as mock_get:
            provider.get_dividends("ITUB3.SA")

        # Ticker travels via params (not the URL path), but either way it
        # must be the bare form — Status Invest 404s on .SA-suffixed lookups.
        call = mock_get.call_args
        url = call.args[0]
        params = call.kwargs.get("params") or {}
        sent_ticker = params.get("ticker", "")
        assert sent_ticker == "ITUB3"
        assert ".SA" not in url
        assert ".SA" not in sent_ticker

    def test_idempotent_on_repeat_parse(self):
        """Parsing the same payload twice must yield identical record lists.

        A non-deterministic parser would collide with the dedup-on-write logic
        downstream and leak duplicates into the dividend_history table.
        """
        provider = StatusInvestProvider()
        import json
        payload = json.loads(_load("statusinvest_itub3.json"))

        # Two providers (separate caches) parsing the same payload must agree.
        with patch("app.providers.statusinvest.httpx.get",
                   return_value=_mock_resp(json_payload=payload)):
            first = StatusInvestProvider().get_dividends("ITUB3.SA")
            second = StatusInvestProvider().get_dividends("ITUB3.SA")

        as_tuple = lambda rs: tuple((r.ex_date, r.dividend_type, r.value) for r in rs)
        assert as_tuple(first) == as_tuple(second)

    def test_returns_empty_list_when_payload_is_null(self):
        """Status Invest serves `null` (not an object) for unknown tickers
        — fixed-income notes, fractional shares (PETR4F.SA), BDRs it doesn't
        recognize. The scheduler runs symbol-by-symbol so one bad ticker must
        not crash the rest of the run.
        """
        provider = StatusInvestProvider()
        with patch("app.providers.statusinvest.httpx.get",
                   return_value=_mock_resp(json_payload=None)):
            records = provider.get_dividends("CDB-C6-2028")
        assert records == []

    def test_works_for_fii_btlg11(self):
        provider = StatusInvestProvider()
        import json
        payload = json.loads(_load("statusinvest_btlg11.json"))

        with patch("app.providers.statusinvest.httpx.get",
                   return_value=_mock_resp(json_payload=payload)):
            records = provider.get_dividends("BTLG11.SA")

        assert len(records) >= 119
        # FIIs pay "Rendimento", not "Dividendo"/"JCP".
        types = {r.dividend_type for r in records}
        assert "Rendimento" in types or "Dividend" in types


# ---------------------------------------------------------------------------
# get_quote
# ---------------------------------------------------------------------------

class TestGetQuote:
    # Minimal HTML matching Status Invest's indicator-card structure.
    _STOCK_HTML = """
    <html>
    <div title="Valor atual do ativo">
        <h3 class="title">Valor atual</h3>
        <strong class="value">41,39</strong>
    </div>
    <div title="DY últimos 12 meses">
        <h3 class="title">D.Y</h3>
        <strong class="value">7,61%</strong>
    </div>
    </html>
    """

    def test_extracts_price_and_yield(self):
        provider = StatusInvestProvider()
        with patch("app.providers.statusinvest.httpx.get",
                   return_value=_mock_resp(text=self._STOCK_HTML)):
            quote = provider.get_quote("ITUB3.SA")

        assert quote["symbol"] == "ITUB3.SA"
        assert quote["currency"] == "BRL"
        assert quote["current_price"] == Decimal("41.39")
        assert quote["dividend_yield"] == Decimal("7.61")

    def test_404_raises_http_error(self):
        provider = StatusInvestProvider()
        with patch("app.providers.statusinvest.httpx.get",
                   return_value=_mock_resp(text="Not found", status_code=404)):
            with pytest.raises(httpx.HTTPStatusError):
                provider.get_quote("DOESNOTEXIST")


# ---------------------------------------------------------------------------
# Cache + UA + 429 retry
# ---------------------------------------------------------------------------

class TestPolitenessAndCache:
    def test_cache_short_circuits_repeated_calls(self):
        """Second get_dividends call within TTL must not hit httpx."""
        provider = StatusInvestProvider()
        with patch("app.providers.statusinvest.httpx.get",
                   return_value=_mock_resp(json_payload={"assetEarningsModels": []})) as mock_get:
            provider.get_dividends("ITUB3.SA")
            provider.get_dividends("ITUB3.SA")

        assert mock_get.call_count == 1, "Second call should hit cache, not network"

    def test_request_uses_browser_user_agent(self):
        provider = StatusInvestProvider()
        with patch("app.providers.statusinvest.httpx.get",
                   return_value=_mock_resp(json_payload={"assetEarningsModels": []})) as mock_get:
            provider.get_dividends("ITUB3.SA")

        kwargs = mock_get.call_args.kwargs
        headers = kwargs.get("headers", {})
        ua = headers.get("User-Agent", "")
        assert "Mozilla" in ua, f"Expected browser UA, got {ua!r}"
        assert "python-httpx" not in ua

    def test_429_retries_once_then_succeeds(self):
        """First 429, second OK — provider should silently retry."""
        provider = StatusInvestProvider()
        ok_resp = _mock_resp(json_payload={"assetEarningsModels": []})
        rate_limited = _mock_resp(text="rate limited", status_code=429)

        with patch("app.providers.statusinvest.httpx.get",
                   side_effect=[rate_limited, ok_resp]) as mock_get:
            records = provider.get_dividends("ITUB3.SA")

        assert mock_get.call_count == 2
        assert records == []

    def test_429_twice_raises(self):
        """Two consecutive 429 responses must surface the error (no infinite retry)."""
        provider = StatusInvestProvider()
        rate_limited_a = _mock_resp(text="rate limited", status_code=429)
        rate_limited_b = _mock_resp(text="rate limited", status_code=429)

        with patch("app.providers.statusinvest.httpx.get",
                   side_effect=[rate_limited_a, rate_limited_b]):
            with pytest.raises(httpx.HTTPStatusError):
                provider.get_dividends("ITUB3.SA")
