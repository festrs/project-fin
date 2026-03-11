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
    with patch("app.routers.stocks.get_market_data_service") as mock_get:
        mock_mds = MagicMock()
        mock_mds.get_stock_quote.return_value = mock_quote
        mock_get.return_value = mock_mds
        resp = client.get("/api/stocks/AAPL", headers={"X-User-Id": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "price" in data
        assert "current_price" not in data
        assert data["price"] == 150.0
        assert data["symbol"] == "AAPL"
        assert data["name"] == "Apple Inc."


def test_crypto_quote_returns_price_and_name_fields():
    mock_quote = {
        "coin_id": "bitcoin",
        "current_price": 95000.0,
        "currency": "USD",
        "market_cap": 1_800_000_000_000,
        "change_24h": 2.5,
    }
    with patch("app.routers.crypto.get_market_data_service") as mock_get:
        mock_mds = MagicMock()
        mock_mds.get_crypto_quote.return_value = mock_quote
        mock_get.return_value = mock_mds
        resp = client.get("/api/crypto/bitcoin", headers={"X-User-Id": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "price" in data
        assert "name" in data
        assert "current_price" not in data
        assert data["price"] == 95000.0
        assert data["name"] == "bitcoin"
        assert data["coin_id"] == "bitcoin"


def test_crypto_class_names_includes_cryptos():
    from app.services.recommendation import CRYPTO_CLASS_NAMES
    assert "Cryptos" in CRYPTO_CLASS_NAMES
    assert "Crypto" in CRYPTO_CLASS_NAMES
