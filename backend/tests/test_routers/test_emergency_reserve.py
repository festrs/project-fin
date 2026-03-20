"""Tests for the Emergency Reserve asset class feature."""


def test_create_emergency_reserve(client, default_user):
    """Emergency reserve is created with is_emergency_reserve=True and target_weight forced to 0."""
    headers = {"X-User-Id": default_user.id}
    resp = client.post(
        "/api/asset-classes",
        json={"name": "Emergency Reserve", "target_weight": 50.0, "type": "fixed_income", "is_emergency_reserve": True},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_emergency_reserve"] is True
    assert data["target_weight"] == 0.0  # forced to 0 regardless of input


def test_create_emergency_reserve_uniqueness(client, default_user):
    """Only one emergency reserve per user."""
    headers = {"X-User-Id": default_user.id}
    resp1 = client.post(
        "/api/asset-classes",
        json={"name": "Emergency Reserve", "type": "fixed_income", "is_emergency_reserve": True},
        headers=headers,
    )
    assert resp1.status_code == 201

    resp2 = client.post(
        "/api/asset-classes",
        json={"name": "Another Reserve", "type": "fixed_income", "is_emergency_reserve": True},
        headers=headers,
    )
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]


def test_create_regular_class_still_works(client, default_user):
    """Creating a regular class with is_emergency_reserve=False works normally."""
    headers = {"X-User-Id": default_user.id}
    resp = client.post(
        "/api/asset-classes",
        json={"name": "Stocks", "target_weight": 60.0},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_emergency_reserve"] is False
    assert data["target_weight"] == 60.0


def test_update_emergency_reserve_keeps_target_weight_zero(client, default_user):
    """Updating emergency reserve always keeps target_weight at 0."""
    headers = {"X-User-Id": default_user.id}
    create_resp = client.post(
        "/api/asset-classes",
        json={"name": "Emergency Reserve", "type": "fixed_income", "is_emergency_reserve": True},
        headers=headers,
    )
    ac_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/asset-classes/{ac_id}",
        json={"target_weight": 25.0, "name": "My Reserve"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_weight"] == 0.0  # still forced to 0
    assert data["name"] == "My Reserve"  # name update works


def test_update_promote_to_reserve_uniqueness(client, default_user):
    """Cannot promote a regular class to emergency reserve if one already exists."""
    headers = {"X-User-Id": default_user.id}
    # Create emergency reserve
    client.post(
        "/api/asset-classes",
        json={"name": "Reserve", "type": "fixed_income", "is_emergency_reserve": True},
        headers=headers,
    )
    # Create regular class
    regular_resp = client.post(
        "/api/asset-classes",
        json={"name": "Stocks", "target_weight": 60.0},
        headers=headers,
    )
    regular_id = regular_resp.json()["id"]

    # Try to promote regular to reserve
    resp = client.put(
        f"/api/asset-classes/{regular_id}",
        json={"is_emergency_reserve": True},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"]


def test_delete_and_recreate_reserve(client, default_user):
    """Can delete emergency reserve and create a new one."""
    headers = {"X-User-Id": default_user.id}
    create_resp = client.post(
        "/api/asset-classes",
        json={"name": "Reserve", "type": "fixed_income", "is_emergency_reserve": True},
        headers=headers,
    )
    ac_id = create_resp.json()["id"]

    # Delete
    del_resp = client.delete(f"/api/asset-classes/{ac_id}", headers=headers)
    assert del_resp.status_code == 204

    # Re-create
    resp = client.post(
        "/api/asset-classes",
        json={"name": "New Reserve", "type": "fixed_income", "is_emergency_reserve": True},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["is_emergency_reserve"] is True


def test_reserve_returned_in_list(client, default_user):
    """Emergency reserve is included in the list response with the flag."""
    headers = {"X-User-Id": default_user.id}
    client.post(
        "/api/asset-classes",
        json={"name": "Stocks", "target_weight": 60.0},
        headers=headers,
    )
    client.post(
        "/api/asset-classes",
        json={"name": "Reserve", "type": "fixed_income", "is_emergency_reserve": True},
        headers=headers,
    )

    resp = client.get("/api/asset-classes", headers=headers)
    assert resp.status_code == 200
    classes = resp.json()
    assert len(classes) == 2
    reserve = [c for c in classes if c["is_emergency_reserve"]]
    regular = [c for c in classes if not c["is_emergency_reserve"]]
    assert len(reserve) == 1
    assert len(regular) == 1
