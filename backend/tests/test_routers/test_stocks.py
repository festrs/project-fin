from unittest.mock import patch, MagicMock


@patch("app.routers.stocks.get_market_data_service")
def test_get_stock_quote(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_stock_quote.return_value = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "current_price": 175.0,
        "currency": "USD",
        "market_cap": 2800000000000,
    }
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/stocks/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["price"] == 175.0
    mock_md.get_stock_quote.assert_called_once_with("AAPL")


@patch("app.routers.stocks.get_market_data_service")
def test_get_stock_history(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_stock_history.return_value = [
        {"date": "2025-01-01", "close": 170.0, "volume": 1000000},
        {"date": "2025-01-02", "close": 172.0, "volume": 1100000},
    ]
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/stocks/AAPL/history?period=1mo")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["price"] == 170.0
    mock_md.get_stock_history.assert_called_once_with("AAPL", "1mo")
