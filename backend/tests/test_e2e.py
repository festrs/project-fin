from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from app.money import Money, Currency
from app.models.user import User
from app.models.quarantine_config import QuarantineConfig


def test_full_investment_flow(client, db):
    # 1. Create user
    user = User(name="E2E User", email="e2e@projectfin.com")
    db.add(user)
    db.commit()
    headers = {"X-User-Id": user.id}

    # Create quarantine config (threshold=2, period_days=180)
    config = QuarantineConfig(user_id=user.id, threshold=2, period_days=180)
    db.add(config)
    db.commit()

    # 2. Create asset classes (US Stocks 50%, Crypto 50%)
    resp = client.post(
        "/api/asset-classes",
        json={"name": "US Stocks", "target_weight": 50.0},
        headers=headers,
    )
    assert resp.status_code == 201
    us_stocks = resp.json()

    resp = client.post(
        "/api/asset-classes",
        json={"name": "Crypto", "target_weight": 50.0},
        headers=headers,
    )
    assert resp.status_code == 201
    crypto = resp.json()

    # 3. Add assets (AAPL to US Stocks, BTC to Crypto)
    resp = client.post(
        f"/api/asset-classes/{us_stocks['id']}/assets",
        json={"symbol": "AAPL", "target_weight": 100.0},
        headers=headers,
    )
    assert resp.status_code == 201

    resp = client.post(
        f"/api/asset-classes/{crypto['id']}/assets",
        json={"symbol": "BTC", "target_weight": 100.0},
        headers=headers,
    )
    assert resp.status_code == 201

    # 4. Record buy transactions (using MoneyInput format)
    today = date.today().isoformat()

    resp = client.post(
        "/api/transactions",
        json={
            "asset_class_id": us_stocks["id"],
            "asset_symbol": "AAPL",
            "type": "buy",
            "quantity": 10,
            "unit_price": {"amount": "150.0", "currency": "USD"},
            "total_value": {"amount": "1500.0", "currency": "USD"},
            "tax_amount": {"amount": "0.0", "currency": "USD"},
            "date": today,
        },
        headers=headers,
    )
    assert resp.status_code == 201

    resp = client.post(
        "/api/transactions",
        json={
            "asset_class_id": crypto["id"],
            "asset_symbol": "BTC",
            "type": "buy",
            "quantity": 0.01,
            "unit_price": {"amount": "65000.0", "currency": "USD"},
            "total_value": {"amount": "650.0", "currency": "USD"},
            "tax_amount": {"amount": "0.0", "currency": "USD"},
            "date": today,
        },
        headers=headers,
    )
    assert resp.status_code == 201

    # 5. Get portfolio summary — verify 2 holdings
    resp = client.get("/api/portfolio/summary", headers=headers)
    assert resp.status_code == 200
    summary = resp.json()
    assert len(summary["holdings"]) == 2

    # 6. Get allocation — verify 2 classes
    resp = client.get("/api/portfolio/allocation", headers=headers)
    assert resp.status_code == 200
    allocation = resp.json()
    assert len(allocation["allocation"]) == 2

    # 7. Record 2nd BTC buy — should trigger quarantine (threshold=2)
    resp = client.post(
        "/api/transactions",
        json={
            "asset_class_id": crypto["id"],
            "asset_symbol": "BTC",
            "type": "buy",
            "quantity": 0.005,
            "unit_price": {"amount": "66000.0", "currency": "USD"},
            "total_value": {"amount": "330.0", "currency": "USD"},
            "tax_amount": {"amount": "0.0", "currency": "USD"},
            "date": today,
        },
        headers=headers,
    )
    assert resp.status_code == 201

    # 8. Get quarantine status — verify BTC is quarantined
    resp = client.get("/api/quarantine/status", headers=headers)
    assert resp.status_code == 200
    statuses = resp.json()
    btc_status = [s for s in statuses if s["asset_symbol"] == "BTC"]
    assert len(btc_status) == 1
    assert btc_status[0]["is_quarantined"] is True
    assert btc_status[0]["buy_count_in_period"] == 2

    # AAPL should not be quarantined (only 1 buy)
    aapl_status = [s for s in statuses if s["asset_symbol"] == "AAPL"]
    assert len(aapl_status) == 1
    assert aapl_status[0]["is_quarantined"] is False

    # 9. Get recommendations (mock market data) — verify BTC is excluded
    with patch("app.services.recommendation.MarketDataService") as MockMarketData:
        mock_instance = MockMarketData.return_value
        mock_instance.get_stock_quote.return_value = {"current_price": Money(Decimal("175"), Currency.USD)}
        mock_instance.get_crypto_quote.return_value = {"current_price": Money(Decimal("67000"), Currency.USD)}

        resp = client.get(
            "/api/recommendations?count=5", headers=headers
        )
        assert resp.status_code == 200
        recs = resp.json()["recommendations"]

        # BTC is quarantined, so it should be excluded from recommendations
        rec_symbols = [r["symbol"] for r in recs]
        assert "BTC" not in rec_symbols
        # AAPL should be present
        assert "AAPL" in rec_symbols
