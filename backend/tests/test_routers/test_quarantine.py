from datetime import date, timedelta

from app.models.asset_class import AssetClass
from app.models.transaction import Transaction


def test_get_quarantine_status(client, default_user, db):
    ac = AssetClass(user_id=default_user.id, name="Stocks", target_weight=60.0)
    db.add(ac)
    db.flush()

    today = date.today()
    # Add 2 buys for AAPL within the period window (default threshold is 2, so should be quarantined)
    for i in range(2):
        tx = Transaction(
            user_id=default_user.id,
            asset_class_id=ac.id,
            asset_symbol="AAPL",
            type="buy",
            quantity=10,
            unit_price=150.0,
            total_value=1500.0,
            currency="USD",
            date=today - timedelta(days=10 + i),
        )
        db.add(tx)
    db.commit()

    headers = {"X-User-Id": default_user.id}
    resp = client.get("/api/quarantine/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["asset_symbol"] == "AAPL"
    assert data[0]["is_quarantined"] is True


def test_get_quarantine_config(client, default_user):
    headers = {"X-User-Id": default_user.id}
    resp = client.get("/api/quarantine/config", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["threshold"] == 2
    assert data["period_days"] == 180


def test_update_quarantine_config(client, default_user):
    headers = {"X-User-Id": default_user.id}
    resp = client.put(
        "/api/quarantine/config",
        json={"threshold": 5, "period_days": 365},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["threshold"] == 5
    assert data["period_days"] == 365
