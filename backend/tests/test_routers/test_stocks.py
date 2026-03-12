from unittest.mock import patch, MagicMock


@patch("app.routers.stocks.get_market_data_service")
def test_get_us_stock_quote(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_stock_quote.return_value = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "current_price": 175.0,
        "currency": "USD",
        "market_cap": 2800000000000,
    }
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/stocks/us/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["price"] == 175.0


@patch("app.routers.stocks.get_market_data_service")
def test_get_us_stock_history(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_stock_history.return_value = [
        {"date": "2025-01-01", "close": 170.0, "volume": 1000000},
    ]
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/stocks/us/AAPL/history?period=1mo")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["price"] == 170.0
    mock_md.get_stock_history.assert_called_once_with("AAPL", "1mo", country="US")


@patch("app.routers.stocks.get_market_data_service")
def test_get_br_stock_quote(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_stock_quote.return_value = {
        "symbol": "PETR4.SA",
        "name": "Petrobras",
        "current_price": 38.50,
        "currency": "BRL",
        "market_cap": 500000000000,
    }
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/stocks/br/PETR4.SA")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "PETR4.SA"
    assert data["price"] == 38.50


@patch("app.routers.stocks.get_market_data_service")
def test_get_br_stock_history(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_stock_history.return_value = [
        {"date": "2025-01-01", "close": 35.0, "volume": 5000000},
    ]
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/stocks/br/PETR4.SA/history?period=1mo")
    assert resp.status_code == 200
    mock_md.get_stock_history.assert_called_once_with("PETR4.SA", "1mo", country="BR")
