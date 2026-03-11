# backend/tests/test_market_search.py
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_stock_quote_returns_price_field():
    mock_quote = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "current_price": 150.0,
        "currency": "USD",
        "market_cap": 2_500_000_000_000,
    }
    with patch("app.routers.stocks.market_data.get_stock_quote", return_value=mock_quote):
        resp = client.get("/api/stocks/AAPL", headers={"X-User-Id": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "price" in data
        assert "current_price" not in data
        assert data["price"] == 150.0
        assert data["symbol"] == "AAPL"
        assert data["name"] == "Apple Inc."
