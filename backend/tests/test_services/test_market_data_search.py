"""Tests for ``MarketDataService.search_stocks`` orchestration.

Covers the routing decisions (crypto → CoinGecko, rendaFixa → empty,
others → yfinance + Brapi enrichment) and the graceful-degrade path
when Brapi enrichment fails.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.market_data import MarketDataService


@pytest.mark.asyncio
async def test_search_crypto_calls_coingecko_only():
    svc = MarketDataService()
    crypto_results = [
        {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "type": "crypto",
         "logo": "x", "currency": "USD"},
    ]
    with patch.object(svc, "search_crypto", return_value=crypto_results) as mock_crypto, \
         patch.object(svc._yfinance, "search") as mock_yf, \
         patch.object(svc._brapi, "enrich_one") as mock_brapi:
        out = await svc.search_stocks("BTC", asset_class="crypto")

    assert out == crypto_results
    mock_crypto.assert_called_once_with("BTC", 15)
    mock_yf.assert_not_called()
    mock_brapi.assert_not_called()


@pytest.mark.asyncio
async def test_search_renda_fixa_returns_empty_no_provider_calls():
    svc = MarketDataService()
    with patch.object(svc._yfinance, "search") as mock_yf, \
         patch.object(svc, "search_crypto") as mock_crypto:
        out = await svc.search_stocks("CDB", asset_class="rendaFixa")

    assert out == []
    mock_yf.assert_not_called()
    mock_crypto.assert_not_called()


@pytest.mark.asyncio
async def test_search_us_class_skips_brapi_enrichment():
    svc = MarketDataService()
    yfin = [{"symbol": "AAPL", "name": "Apple Inc.", "type": "common stock",
             "sector": "Technology", "industry": "Consumer Electronics"}]
    with patch.object(svc._yfinance, "search", return_value=yfin), \
         patch.object(svc._brapi, "enrich_one") as mock_brapi:
        out = await svc.search_stocks("AAPL", asset_class="usStocks")

    assert out[0]["symbol"] == "AAPL"
    assert "price" not in out[0]
    mock_brapi.assert_not_called()


@pytest.mark.asyncio
async def test_search_br_class_enriches_top_sa_results():
    svc = MarketDataService()
    yfin = [
        {"symbol": "PETR4.SA", "name": "Petrobras", "type": "stock",
         "sector": "Energy", "industry": "Oil & Gas"},
        {"symbol": "PETR3.SA", "name": "Petrobras ON", "type": "stock",
         "sector": "Energy", "industry": "Oil & Gas"},
    ]
    enrichment = {
        "PETR4.SA": {"price": {"amount": "49.08", "currency": "BRL"},
                     "currency": "BRL", "change": 0.25,
                     "logo": "https://icons.brapi.dev/PETR4.svg"},
        "PETR3.SA": {"price": {"amount": "47.50", "currency": "BRL"},
                     "currency": "BRL"},
    }

    def fake_enrich(sym):
        return enrichment.get(sym, {})

    with patch.object(svc._yfinance, "search", return_value=yfin), \
         patch.object(svc._brapi, "enrich_one", side_effect=fake_enrich) as mock_brapi:
        out = await svc.search_stocks("PETR", asset_class="acoesBR")

    by_symbol = {r["symbol"]: r for r in out}
    assert by_symbol["PETR4.SA"]["price"]["amount"] == "49.08"
    assert by_symbol["PETR4.SA"]["logo"].endswith("PETR4.svg")
    assert by_symbol["PETR3.SA"]["price"]["amount"] == "47.50"
    assert mock_brapi.call_count == 2


@pytest.mark.asyncio
async def test_search_brapi_failure_degrades_gracefully():
    """If Brapi returns {} for every ticker, we still return yfinance
    results — just without price/logo."""
    svc = MarketDataService()
    yfin = [{"symbol": "PETR4.SA", "name": "Petrobras", "type": "stock",
             "sector": "Energy", "industry": "Oil & Gas"}]
    with patch.object(svc._yfinance, "search", return_value=yfin), \
         patch.object(svc._brapi, "enrich_one", return_value={}):
        out = await svc.search_stocks("PETR4", asset_class="acoesBR")

    assert len(out) == 1
    assert out[0]["symbol"] == "PETR4.SA"
    assert "price" not in out[0]


@pytest.mark.asyncio
async def test_search_caches_results_by_query_and_class():
    """The 60s in-memory cache should suppress duplicate provider calls
    when the iOS debouncer fires the same query twice."""
    svc = MarketDataService()
    yfin = [{"symbol": "AAPL", "name": "Apple Inc.", "type": "common stock"}]
    with patch.object(svc._yfinance, "search", return_value=yfin) as mock_yf:
        out1 = await svc.search_stocks("AAPL", asset_class="usStocks")
        out2 = await svc.search_stocks("AAPL", asset_class="usStocks")

    assert out1 == out2
    mock_yf.assert_called_once()


@pytest.mark.asyncio
async def test_search_cache_key_distinguishes_class():
    """Same query under different asset classes must NOT share a cache
    entry — the class scopes the result set."""
    svc = MarketDataService()
    with patch.object(svc._yfinance, "search", return_value=[]) as mock_yf:
        await svc.search_stocks("foo", asset_class="usStocks")
        await svc.search_stocks("foo", asset_class="reits")

    assert mock_yf.call_count == 2


@pytest.mark.asyncio
async def test_search_only_enriches_top_three_sa_results():
    """Brapi free plan caps us; the orchestrator must not call enrich
    more than 3 times per search regardless of how many SA results
    yfinance returns."""
    svc = MarketDataService()
    yfin = [
        {"symbol": f"SYM{i}.SA", "name": f"Issuer {i}", "type": "stock"}
        for i in range(8)
    ]
    with patch.object(svc._yfinance, "search", return_value=yfin), \
         patch.object(svc._brapi, "enrich_one", return_value={}) as mock_brapi:
        await svc.search_stocks("foo", asset_class="acoesBR")

    assert mock_brapi.call_count == 3
