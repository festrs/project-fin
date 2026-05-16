from app.services.auth import create_access_token


def test_create_asset_class(client, default_user):
    token = create_access_token(default_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/asset-classes",
        json={"name": "Stocks", "target_weight": 60.0},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Stocks"
    assert data["target_weight"] == "60.0000"
    assert data["user_id"] == default_user.id


def test_list_asset_classes(client, default_user):
    token = create_access_token(default_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/asset-classes", json={"name": "Stocks", "target_weight": 60.0}, headers=headers)
    client.post("/api/asset-classes", json={"name": "Crypto", "target_weight": 40.0}, headers=headers)
    resp = client.get("/api/asset-classes", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_asset_class(client, default_user):
    token = create_access_token(default_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    create_resp = client.post("/api/asset-classes", json={"name": "Stocks", "target_weight": 60.0}, headers=headers)
    ac_id = create_resp.json()["id"]
    resp = client.put(f"/api/asset-classes/{ac_id}", json={"target_weight": 70.0}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["target_weight"] == "70.0000"


def test_delete_asset_class(client, default_user):
    token = create_access_token(default_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    create_resp = client.post("/api/asset-classes", json={"name": "Stocks", "target_weight": 60.0}, headers=headers)
    ac_id = create_resp.json()["id"]
    resp = client.delete(f"/api/asset-classes/{ac_id}", headers=headers)
    assert resp.status_code == 204
    list_resp = client.get("/api/asset-classes", headers=headers)
    assert len(list_resp.json()) == 0
