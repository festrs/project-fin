from datetime import date
from decimal import Decimal

from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction


def _setup_portfolio(db, user_id):
    ac = AssetClass(user_id=user_id, name="Stocks", target_weight=60.0)
    db.add(ac)
    db.flush()

    aw = AssetWeight(asset_class_id=ac.id, symbol="AAPL", target_weight=50.0)
    db.add(aw)

    tx = Transaction(
        user_id=user_id,
        asset_class_id=ac.id,
        asset_symbol="AAPL",
        type="buy",
        quantity=10,
        unit_price=Decimal("150.0"),
        total_value=Decimal("1500.0"),
        currency="USD",
        tax_amount=Decimal("0.0"),
        date=date(2025, 6, 1),
    )
    db.add(tx)
    db.commit()
    return ac


def test_portfolio_summary(client, default_user, db):
    _setup_portfolio(db, default_user.id)
    headers = {"X-User-Id": default_user.id}
    resp = client.get("/api/portfolio/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["holdings"]) == 1
    assert data["holdings"][0]["symbol"] == "AAPL"
    assert data["holdings"][0]["quantity"] == 10
    # Money fields are now nested dicts
    assert "amount" in data["holdings"][0]["total_cost"]
    assert "currency" in data["holdings"][0]["total_cost"]


def test_portfolio_performance(client, default_user, db):
    _setup_portfolio(db, default_user.id)
    headers = {"X-User-Id": default_user.id}
    resp = client.get("/api/portfolio/performance", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cost"] == "1500.00000000"


def test_portfolio_allocation(client, default_user, db):
    _setup_portfolio(db, default_user.id)
    headers = {"X-User-Id": default_user.id}
    resp = client.get("/api/portfolio/allocation", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["allocation"]) == 1
    assert data["allocation"][0]["class_name"] == "Stocks"
    assert data["allocation"][0]["assets"][0]["symbol"] == "AAPL"
    # total_cost is now a nested dict
    assert "amount" in data["allocation"][0]["assets"][0]["total_cost"]
