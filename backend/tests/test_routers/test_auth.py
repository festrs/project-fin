from app.models.user import User
from app.services.auth import hash_password


def test_login_success(client, db):
    user = User(
        name="Test User",
        email="test@example.com",
        password_hash=hash_password("testpass"),
    )
    db.add(user)
    db.commit()

    resp = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "testpass",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["name"] == "Test User"


def test_login_wrong_password(client, db):
    user = User(
        name="Test User",
        email="test@example.com",
        password_hash=hash_password("testpass"),
    )
    db.add(user)
    db.commit()

    resp = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpass",
    })
    assert resp.status_code == 401


def test_login_unknown_email(client, db):
    resp = client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "testpass",
    })
    assert resp.status_code == 401
