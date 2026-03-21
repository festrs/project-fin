import pytest
from app.models.user import User
from app.services.auth import hash_password, create_access_token


@pytest.fixture
def auth_user(db):
    user = User(
        name="Type Test User",
        email="typetestuser@example.com",
        password_hash=hash_password("testpass"),
    )
    db.add(user)
    db.commit()
    return user


def test_create_asset_class_with_type(client, auth_user):
    token = create_access_token(auth_user.id)
    res = client.post(
        "/api/asset-classes",
        json={"name": "Test Crypto", "target_weight": 10, "country": "US", "type": "crypto"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["type"] == "crypto"


def test_create_asset_class_default_type(client, auth_user):
    token = create_access_token(auth_user.id)
    res = client.post(
        "/api/asset-classes",
        json={"name": "Test Default", "target_weight": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    assert res.json()["type"] == "stock"


def test_update_asset_class_type(client, auth_user):
    token = create_access_token(auth_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    create_res = client.post(
        "/api/asset-classes",
        json={"name": "Changeable", "target_weight": 5},
        headers=headers,
    )
    ac_id = create_res.json()["id"]

    update_res = client.put(
        f"/api/asset-classes/{ac_id}",
        json={"type": "fixed_income"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["type"] == "fixed_income"


def test_list_asset_classes_includes_type(client, auth_user):
    token = create_access_token(auth_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        "/api/asset-classes",
        json={"name": "Listed", "type": "crypto"},
        headers=headers,
    )
    res = client.get(
        "/api/asset-classes",
        headers=headers,
    )
    assert res.status_code == 200
    for ac in res.json():
        assert "type" in ac


def test_create_asset_class_invalid_type(client, auth_user):
    token = create_access_token(auth_user.id)
    res = client.post(
        "/api/asset-classes",
        json={"name": "Bad", "type": "invalid_type"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422
