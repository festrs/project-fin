from app.models.asset_class import AssetClass
from app.services.auth import create_access_token


def _create_asset_class(db, user_id):
    ac = AssetClass(user_id=user_id, name="Stocks", target_weight=60.0)
    db.add(ac)
    db.commit()
    return ac


def test_add_asset(client, default_user, db):
    ac = _create_asset_class(db, default_user.id)
    token = create_access_token(default_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        f"/api/asset-classes/{ac.id}/assets",
        json={"symbol": "AAPL", "target_weight": 50.0},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["target_weight"] == "50.0000"


def test_list_assets(client, default_user, db):
    ac = _create_asset_class(db, default_user.id)
    token = create_access_token(default_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    client.post(f"/api/asset-classes/{ac.id}/assets", json={"symbol": "AAPL", "target_weight": 50.0}, headers=headers)
    client.post(f"/api/asset-classes/{ac.id}/assets", json={"symbol": "MSFT", "target_weight": 50.0}, headers=headers)
    resp = client.get(f"/api/asset-classes/{ac.id}/assets", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_weight(client, default_user, db):
    ac = _create_asset_class(db, default_user.id)
    token = create_access_token(default_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    create_resp = client.post(
        f"/api/asset-classes/{ac.id}/assets",
        json={"symbol": "AAPL", "target_weight": 50.0},
        headers=headers,
    )
    aw_id = create_resp.json()["id"]
    resp = client.put(f"/api/asset-weights/{aw_id}", json={"target_weight": 70.0}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["target_weight"] == "70.0000"


def test_delete_asset(client, default_user, db):
    ac = _create_asset_class(db, default_user.id)
    token = create_access_token(default_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    create_resp = client.post(
        f"/api/asset-classes/{ac.id}/assets",
        json={"symbol": "AAPL", "target_weight": 50.0},
        headers=headers,
    )
    aw_id = create_resp.json()["id"]
    resp = client.delete(f"/api/asset-weights/{aw_id}", headers=headers)
    assert resp.status_code == 204
    list_resp = client.get(f"/api/asset-classes/{ac.id}/assets", headers=headers)
    assert len(list_resp.json()) == 0
