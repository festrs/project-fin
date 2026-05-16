"""Tests for the rewired ``/api/stocks/search`` route.

The route delegates to ``MarketDataService.search_stocks``, which fans
out to yfinance + Brapi (or CoinGecko for crypto). We mock the providers
at the service layer so tests stay hermetic.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_search_returns_yfinance_results_for_us_class():
    yfin_results = [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "type": "common stock",
            "sector": "Technology",
            "industry": "Consumer Electronics",
        }
    ]
    with patch("app.routers.stocks.get_market_data_service") as mock_get:
        mds = MagicMock()
        mds.search_stocks = AsyncMock(return_value=yfin_results)
        mock_get.return_value = mds
        resp = client.get("/api/stocks/search?q=AAPL&asset_class=usStocks")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "AAPL"
    assert data[0]["type"] == "common stock"
    assert data[0]["sector"] == "Technology"
    # Asset_class is forwarded to the service so it can scope the search.
    mds.search_stocks.assert_awaited_once_with("AAPL", asset_class="usStocks")


def test_search_includes_brapi_enrichment_fields_when_present():
    """The service is responsible for enrichment; the route just forwards
    whatever fields the service emits — including price/logo/change."""
    enriched = [{
        "symbol": "PETR4.SA",
        "name": "Petrobras",
        "type": "stock",
        "sector": "Energy",
        "industry": "Oil & Gas Integrated",
        "price": {"amount": "49.08", "currency": "BRL"},
        "currency": "BRL",
        "change": 0.25,
        "logo": "https://icons.brapi.dev/icons/PETR4.svg",
    }]
    with patch("app.routers.stocks.get_market_data_service") as mock_get:
        mds = MagicMock()
        mds.search_stocks = AsyncMock(return_value=enriched)
        mock_get.return_value = mds
        resp = client.get("/api/stocks/search?q=PETR4&asset_class=acoesBR")

    assert resp.status_code == 200
    item = resp.json()[0]
    assert item["price"] == {"amount": "49.08", "currency": "BRL"}
    assert item["logo"].endswith("PETR4.svg")
    assert item["change"] == 0.25


def test_search_without_asset_class_passes_none_to_service():
    with patch("app.routers.stocks.get_market_data_service") as mock_get:
        mds = MagicMock()
        mds.search_stocks = AsyncMock(return_value=[])
        mock_get.return_value = mds
        resp = client.get("/api/stocks/search?q=anything")

    assert resp.status_code == 200
    mds.search_stocks.assert_awaited_once_with("anything", asset_class=None)


def test_search_dedupes_and_sorts_results():
    raw = [
        {"symbol": "AAPL", "name": "Apple Inc.", "type": "common stock"},
        {"symbol": "AAPL", "name": "Apple Inc. (dup)", "type": "common stock"},
        {"symbol": "MSFT", "name": "Microsoft Corp", "type": "common stock"},
    ]
    with patch("app.routers.stocks.get_market_data_service") as mock_get:
        mds = MagicMock()
        mds.search_stocks = AsyncMock(return_value=raw)
        mock_get.return_value = mds
        resp = client.get("/api/stocks/search?q=foo")

    data = resp.json()
    # Dedupe keeps the first occurrence; alphabetical-by-name sort puts
    # "Apple Inc." before "Microsoft Corp".
    assert [r["symbol"] for r in data] == ["AAPL", "MSFT"]


def test_search_renda_fixa_returns_empty():
    with patch("app.routers.stocks.get_market_data_service") as mock_get:
        mds = MagicMock()
        mds.search_stocks = AsyncMock(return_value=[])
        mock_get.return_value = mds
        resp = client.get("/api/stocks/search?q=CDB&asset_class=rendaFixa")

    assert resp.status_code == 200
    assert resp.json() == []
    mds.search_stocks.assert_awaited_once_with("CDB", asset_class="rendaFixa")


def test_search_requires_query_param():
    resp = client.get("/api/stocks/search")
    assert resp.status_code == 422  # FastAPI validation: q is required


def test_search_rejects_empty_query():
    resp = client.get("/api/stocks/search?q=")
    assert resp.status_code == 422  # Query(min_length=1) rejects empty
