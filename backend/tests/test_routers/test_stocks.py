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
    mock_md.get_stock_history.assert_called_once_with("AAPL", "1mo", country="US")


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
    mock_md.get_stock_history.assert_called_once_with("PETR4.SA", "1mo", country="BR")


# ──────────────────────────────────────────────
# Search — crypto + stocks merged into one list
# ──────────────────────────────────────────────


@patch("app.routers.stocks.get_market_data_service")
def test_search_includes_crypto_results_first(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.search_crypto.return_value = [
        {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin",
         "type": "crypto", "currency": "USD", "logo": "logo-url"},
    ]
    mock_md._finnhub.search.return_value = [
        {"symbol": "GBTC", "name": "Grayscale Bitcoin Trust", "type": "Common Stock"},
    ]
    mock_md._brapi.search.return_value = []
    mock_get_mds.return_value = mock_md

    resp = client.get("/api/stocks/search?q=btc")
    assert resp.status_code == 200
    results = resp.json()

    # Crypto must lead the list so popular tokens beat the unrelated ETFs
    assert results[0]["symbol"] == "BTC"
    assert results[0]["type"] == "crypto"
    assert results[0]["name"] == "Bitcoin"
    # Logo flows through so the iOS row can render the token thumbnail
    assert results[0]["logo"] == "logo-url"
    # Stock results still appear after crypto
    assert any(r["symbol"] == "GBTC" for r in results)


@patch("app.routers.stocks.get_market_data_service")
def test_search_dedups_by_symbol(mock_get_mds, client):
    # CoinGecko + Brapi both return BTC-like entries — first occurrence wins,
    # so the crypto row keeps its `type: "crypto"` even if a stock provider
    # also returns the same symbol.
    mock_md = MagicMock()
    mock_md.search_crypto.return_value = [
        {"id": "BTC", "symbol": "BTC", "name": "Bitcoin", "type": "crypto"},
    ]
    mock_md._finnhub.search.return_value = [
        {"symbol": "BTC", "name": "Some BTC ETF", "type": "Common Stock"},
    ]
    mock_md._brapi.search.return_value = []
    mock_get_mds.return_value = mock_md

    resp = client.get("/api/stocks/search?q=btc")
    assert resp.status_code == 200
    results = resp.json()
    btc_rows = [r for r in results if r["symbol"] == "BTC"]
    assert len(btc_rows) == 1, "Duplicate symbols must dedup to a single row"
    assert btc_rows[0]["type"] == "crypto", "Crypto wins over duplicates from other providers"


@patch("app.routers.stocks.get_market_data_service")
def test_search_tolerates_crypto_failure(mock_get_mds, client):
    # If CoinGecko fails (rate-limit, network), the search must still return stocks.
    mock_md = MagicMock()
    mock_md.search_crypto.side_effect = RuntimeError("coingecko down")
    mock_md._finnhub.search.return_value = [
        {"symbol": "AAPL", "name": "Apple Inc.", "type": "Common Stock"},
    ]
    mock_md._brapi.search.return_value = []
    mock_get_mds.return_value = mock_md

    resp = client.get("/api/stocks/search?q=apple")
    assert resp.status_code == 200
    results = resp.json()
    assert any(r["symbol"] == "AAPL" for r in results)


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
