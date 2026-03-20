from unittest.mock import patch, MagicMock
from decimal import Decimal

from app.money import Money, Currency


@patch("app.routers.crypto.get_market_data_service")
def test_get_crypto_quote(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_crypto_quote.return_value = {
        "coin_id": "bitcoin",
        "current_price": Money(Decimal("65000"), Currency.USD),
        "currency": Currency.USD,
        "market_cap": Money(Decimal("1200000000000"), Currency.USD),
        "change_24h": 2.5,
    }
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/crypto/bitcoin")
    assert resp.status_code == 200
    data = resp.json()
    assert data["coin_id"] == "bitcoin"
    assert data["price"]["amount"] == "65000"
    assert data["price"]["currency"] == "USD"
    assert data["name"] == "bitcoin"
    mock_md.get_crypto_quote.assert_called_once_with("bitcoin")


@patch("app.routers.crypto.get_market_data_service")
def test_get_crypto_history(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_crypto_history.return_value = [
        {"date": "2025-01-01", "price": Decimal("64000.0")},
        {"date": "2025-01-02", "price": Decimal("65000.0")},
    ]
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/crypto/bitcoin/history?days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["price"]["amount"] == "64000.0"
    assert data[0]["price"]["currency"] == "USD"
    mock_md.get_crypto_history.assert_called_once_with("bitcoin", 30)
