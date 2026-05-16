from app.models.asset_class import AssetClass
from app.services.auth import create_access_token


def _setup(db, user_id):
    ac = AssetClass(user_id=user_id, name="Stocks", target_weight=60.0)
    db.add(ac)
    db.commit()
    return ac


def _tx_body(asset_class_id):
    return {
        "asset_class_id": asset_class_id,
        "asset_symbol": "AAPL",
        "type": "buy",
        "quantity": 10,
        "unit_price": {"amount": "150.0", "currency": "USD"},
        "total_value": {"amount": "1500.0", "currency": "USD"},
        "tax_amount": {"amount": "0.0", "currency": "USD"},
        "date": "2025-06-01",
    }


def test_create_buy(client, default_user, db):
    ac = _setup(db, default_user.id)
    token = create_access_token(default_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/api/transactions", json=_tx_body(ac.id), headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "buy"
    assert data["asset_symbol"] == "AAPL"
    assert data["quantity"] == "10.00000000"
    assert data["total_value"]["amount"] == "1500.00000000"
    assert data["total_value"]["currency"] == "USD"
    assert data["unit_price"]["amount"] == "150.00000000"
    assert data["unit_price"]["currency"] == "USD"


def test_list_with_filter(client, default_user, db):
    ac = _setup(db, default_user.id)
    token = create_access_token(default_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/transactions", json=_tx_body(ac.id), headers=headers)
    sell_body = _tx_body(ac.id)
    sell_body["type"] = "sell"
    sell_body["quantity"] = 5
    sell_body["total_value"] = {"amount": "750.0", "currency": "USD"}
    client.post("/api/transactions", json=sell_body, headers=headers)

    # Filter by type=buy
    resp = client.get("/api/transactions?type=buy", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["type"] == "buy"


def test_update(client, default_user, db):
    ac = _setup(db, default_user.id)
    token = create_access_token(default_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    create_resp = client.post("/api/transactions", json=_tx_body(ac.id), headers=headers)
    tx_id = create_resp.json()["id"]
    resp = client.put(f"/api/transactions/{tx_id}", json={"quantity": 20}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["quantity"] == "20.00000000"


def test_delete(client, default_user, db):
    ac = _setup(db, default_user.id)
    token = create_access_token(default_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    create_resp = client.post("/api/transactions", json=_tx_body(ac.id), headers=headers)
    tx_id = create_resp.json()["id"]
    resp = client.delete(f"/api/transactions/{tx_id}", headers=headers)
    assert resp.status_code == 204
    list_resp = client.get("/api/transactions", headers=headers)
    assert len(list_resp.json()) == 0
