from unittest.mock import patch, MagicMock


@patch("app.routers.crypto.get_market_data_service")
def test_get_crypto_quote(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_crypto_quote.return_value = {
        "coin_id": "bitcoin",
        "current_price": 65000.0,
        "currency": "USD",
        "market_cap": 1200000000000,
        "change_24h": 2.5,
    }
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/crypto/bitcoin")
    assert resp.status_code == 200
    data = resp.json()
    assert data["coin_id"] == "bitcoin"
    assert data["price"] == 65000.0
    assert data["name"] == "bitcoin"
    mock_md.get_crypto_quote.assert_called_once_with("bitcoin")


@patch("app.routers.crypto.get_market_data_service")
def test_get_crypto_history(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_crypto_history.return_value = [
        {"date": "2025-01-01", "price": 64000.0},
        {"date": "2025-01-02", "price": 65000.0},
    ]
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/crypto/bitcoin/history?days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    mock_md.get_crypto_history.assert_called_once_with("bitcoin", 30)
