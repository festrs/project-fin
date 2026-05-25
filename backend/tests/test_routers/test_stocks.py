from unittest.mock import patch, MagicMock
from decimal import Decimal

from app.money import Money, Currency


@patch("app.routers.stocks.get_market_data_service")
def test_get_us_stock_quote(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_stock_quote.return_value = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "current_price": Money(Decimal("175"), Currency.USD),
        "currency": Currency.USD,
        "market_cap": Money(Decimal("2800000000000"), Currency.USD),
    }
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/stocks/us/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["price"]["amount"] == "175"
    assert data["price"]["currency"] == "USD"
    assert data["currency"] == "USD"
    assert data["market_cap"]["amount"] == "2800000000000"


@patch("app.routers.stocks.get_market_data_service")
def test_get_us_stock_history(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_stock_history.return_value = [
        {"date": "2025-01-01", "close": Decimal("170.0"), "volume": 1000000},
    ]
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/stocks/us/AAPL/history?period=1mo")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["price"]["amount"] == "170.0"
    assert data[0]["price"]["currency"] == "USD"
    args, kwargs = mock_md.get_stock_history.call_args
    assert args == ("AAPL", "1mo")
    assert kwargs["country"] == "US"


@patch("app.routers.stocks.get_market_data_service")
def test_get_br_stock_quote(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_stock_quote.return_value = {
        "symbol": "PETR4.SA",
        "name": "Petrobras",
        "current_price": Money(Decimal("38.50"), Currency.BRL),
        "currency": Currency.BRL,
        "market_cap": Money(Decimal("500000000000"), Currency.BRL),
    }
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/stocks/br/PETR4.SA")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "PETR4.SA"
    assert data["price"]["amount"] == "38.50"
    assert data["price"]["currency"] == "BRL"


@patch("app.routers.stocks.get_market_data_service")
def test_get_br_stock_history(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_stock_history.return_value = [
        {"date": "2025-01-01", "close": Decimal("35.0"), "volume": 5000000},
    ]
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/stocks/br/PETR4.SA/history?period=1mo")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["price"]["amount"] == "35.0"
    assert data[0]["price"]["currency"] == "BRL"
    args, kwargs = mock_md.get_stock_history.call_args
    assert args == ("PETR4.SA", "1mo")
    assert kwargs["country"] == "BR"


# ──────────────────────────────────────────────
# Crypto routing on the generic /{symbol} + /{symbol}/history endpoints.
# Previously these fell through to yfinance and returned a small-cap
# stock named "BTC" (~$30). Now they delegate to CoinGecko first.
# ──────────────────────────────────────────────


@patch("app.routers.stocks.get_market_data_service")
def test_get_stock_quote_routes_btc_to_crypto(mock_get_mds, client):
    """The bug: /api/stocks/BTC used to fall through to yfinance which
    returned a small-cap stock named BTC. Crypto routing now intercepts
    before country detection."""
    mock_md = MagicMock()
    mock_md.get_crypto_quote_for_symbol.return_value = {
        "coin_id": "bitcoin",
        "symbol": "BTC",
        "name": "Bitcoin",
        "current_price": Money(Decimal("67500"), Currency.USD),
        "currency": Currency.USD,
        "market_cap": Money(Decimal("1300000000000"), Currency.USD),
    }
    mock_get_mds.return_value = mock_md

    resp = client.get("/api/stocks/BTC")

    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "BTC"
    assert data["name"] == "Bitcoin"
    assert data["price"]["amount"] == "67500"
    assert data["price"]["currency"] == "USD"
    # Crucial: yfinance was never asked. If get_stock_quote had been
    # called, the small-cap "BTC" stock would have been returned.
    mock_md.get_stock_quote.assert_not_called()


@patch("app.routers.stocks.get_market_data_service")
def test_get_stock_quote_passes_through_for_non_crypto(mock_get_mds, client):
    """AAPL is not in CRYPTO_COINGECKO_MAP, so the generic endpoint
    falls through to country-based stock routing."""
    mock_md = MagicMock()
    mock_md.get_crypto_quote_for_symbol.return_value = None
    mock_md.get_stock_quote.return_value = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "current_price": Money(Decimal("175"), Currency.USD),
        "currency": Currency.USD,
        "market_cap": Money(Decimal("2800000000000"), Currency.USD),
    }
    mock_get_mds.return_value = mock_md

    resp = client.get("/api/stocks/AAPL")

    assert resp.status_code == 200
    assert resp.json()["symbol"] == "AAPL"
    mock_md.get_stock_quote.assert_called_once()


@patch("app.routers.stocks.get_market_data_service")
def test_get_stock_history_routes_btc_to_crypto(mock_get_mds, client):
    """Same routing as the quote endpoint — chart for BTC must use
    CoinGecko market_chart, not yfinance daily bars."""
    mock_md = MagicMock()
    mock_md.get_crypto_history_for_symbol.return_value = [
        {"date": "2026-01-01", "price": Decimal("65000")},
        {"date": "2026-01-02", "price": Decimal("66500")},
    ]
    mock_get_mds.return_value = mock_md

    resp = client.get("/api/stocks/BTC/history?period=1mo")

    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 2
    assert rows[0]["price"]["amount"] == "65000"
    assert rows[0]["price"]["currency"] == "USD"
    # Verify the period→days translation reached the service.
    args, _ = mock_md.get_crypto_history_for_symbol.call_args
    assert args == ("BTC", 30)
    mock_md.get_stock_history.assert_not_called()


@patch("app.routers.stocks.get_market_data_service")
def test_get_stock_history_passes_through_for_non_crypto(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_crypto_history_for_symbol.return_value = None
    mock_md.get_stock_history.return_value = [
        {"date": "2025-01-01", "close": Decimal("170"), "volume": 1000000},
    ]
    mock_get_mds.return_value = mock_md

    resp = client.get("/api/stocks/AAPL/history?period=1mo")

    assert resp.status_code == 200
    assert resp.json()[0]["price"]["amount"] == "170"
    mock_md.get_stock_history.assert_called_once()


# ──────────────────────────────────────────────
# Search — coverage moved to tests/test_routers/test_search_route.py
# (the route now delegates to MarketDataService.search_stocks; the old
# multi-provider fan-out was replaced by yfinance + class-aware filter).
# ──────────────────────────────────────────────


# ──────────────────────────────────────────────
# search_crypto provider method
# ──────────────────────────────────────────────


@patch("app.services.market_data.coingecko_client.get")
def test_search_crypto_normalizes_coingecko_payload(mock_httpx):
    from app.services.market_data import MarketDataService

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "coins": [
            {"id": "bitcoin", "name": "Bitcoin", "symbol": "btc", "thumb": "thumb-url"},
            {"id": "bitcoin-cash", "name": "Bitcoin Cash", "symbol": "BCH", "thumb": "bch-thumb"},
        ]
    }
    mock_resp.raise_for_status.return_value = None
    mock_httpx.return_value = mock_resp

    results = MarketDataService().search_crypto("btc")

    assert len(results) == 2
    # Symbols are normalized to uppercase for consistent display
    assert results[0]["symbol"] == "BTC"
    assert results[0]["id"] == "bitcoin"  # CoinGecko id preserved for quote lookups
    assert results[0]["type"] == "crypto"
    assert results[0]["currency"] == "USD"
    assert results[0]["logo"] == "thumb-url"
    # Coins with symbols already uppercase still work
    assert results[1]["symbol"] == "BCH"


@patch("app.services.market_data.coingecko_client.get")
def test_search_crypto_returns_empty_on_failure(mock_httpx):
    from app.services.market_data import MarketDataService

    mock_httpx.side_effect = RuntimeError("network")
    results = MarketDataService().search_crypto("btc")
    assert results == []


@patch("app.services.market_data.coingecko_client.get")
def test_search_crypto_skips_entries_without_symbol(mock_httpx):
    # CoinGecko occasionally returns malformed entries — drop them.
    from app.services.market_data import MarketDataService

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "coins": [
            {"id": "good", "name": "Good", "symbol": "GOOD"},
            {"id": "bad", "name": "Bad"},  # no symbol
            {"id": "empty", "name": "Empty", "symbol": ""},
        ]
    }
    mock_resp.raise_for_status.return_value = None
    mock_httpx.return_value = mock_resp

    results = MarketDataService().search_crypto("x")
    assert len(results) == 1
    assert results[0]["symbol"] == "GOOD"
