from unittest.mock import patch


@patch("app.routers.stocks.market_data")
def test_get_stock_quote(mock_md, client):
    mock_md.get_stock_quote.return_value = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "current_price": 175.0,
        "currency": "USD",
        "market_cap": 2800000000000,
    }
    resp = client.get("/api/stocks/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["current_price"] == 175.0
    mock_md.get_stock_quote.assert_called_once_with("AAPL")


@patch("app.routers.stocks.market_data")
def test_get_stock_history(mock_md, client):
    mock_md.get_stock_history.return_value = [
        {"date": "2025-01-01", "close": 170.0, "volume": 1000000},
        {"date": "2025-01-02", "close": 172.0, "volume": 1100000},
    ]
    resp = client.get("/api/stocks/AAPL/history?period=1mo")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    mock_md.get_stock_history.assert_called_once_with("AAPL", "1mo")
