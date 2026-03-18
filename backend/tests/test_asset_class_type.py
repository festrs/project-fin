def test_create_asset_class_with_type(client):
    res = client.post(
        "/api/asset-classes",
        json={"name": "Test Crypto", "target_weight": 10, "country": "US", "type": "crypto"},
        headers={"X-User-Id": "default-user-id"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["type"] == "crypto"


def test_create_asset_class_default_type(client):
    res = client.post(
        "/api/asset-classes",
        json={"name": "Test Default", "target_weight": 5},
        headers={"X-User-Id": "default-user-id"},
    )
    assert res.status_code == 201
    assert res.json()["type"] == "stock"


def test_update_asset_class_type(client):
    create_res = client.post(
        "/api/asset-classes",
        json={"name": "Changeable", "target_weight": 5},
        headers={"X-User-Id": "default-user-id"},
    )
    ac_id = create_res.json()["id"]

    update_res = client.put(
        f"/api/asset-classes/{ac_id}",
        json={"type": "fixed_income"},
        headers={"X-User-Id": "default-user-id"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["type"] == "fixed_income"


def test_list_asset_classes_includes_type(client):
    client.post(
        "/api/asset-classes",
        json={"name": "Listed", "type": "crypto"},
        headers={"X-User-Id": "default-user-id"},
    )
    res = client.get(
        "/api/asset-classes",
        headers={"X-User-Id": "default-user-id"},
    )
    assert res.status_code == 200
    for ac in res.json():
        assert "type" in ac


def test_create_asset_class_invalid_type(client):
    res = client.post(
        "/api/asset-classes",
        json={"name": "Bad", "type": "invalid_type"},
        headers={"X-User-Id": "default-user-id"},
    )
    assert res.status_code == 422
