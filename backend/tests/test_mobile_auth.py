"""Tests for mobile API key authentication and input validation."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi import Header

from app.database import Base, get_db
from app.dependencies_mobile import verify_mobile_api_key
from app.main import app

TEST_DB = "sqlite:///./test_mobile_auth.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

API_KEY = "test-mobile-key-abc123"


def _require_key(x_api_key: str = Header(default="")):
    """Test-local dependency that enforces a known API key."""
    import hmac
    from fastapi import HTTPException as Exc

    if not x_api_key or not hmac.compare_digest(x_api_key, API_KEY):
        raise Exc(status_code=403, detail="Invalid API key")


HEADERS = {"X-API-Key": API_KEY}


@pytest.fixture(autouse=True)
def db():
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[verify_mobile_api_key] = _require_key
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── API Key Authentication ──


class TestAPIKeyAuth:
    def test_no_key_returns_403(self, client):
        resp = client.get("/api/mobile/exchange-rate", params={"pair": "USD-BRL"})
        assert resp.status_code == 403

    def test_wrong_key_returns_403(self, client):
        resp = client.get(
            "/api/mobile/exchange-rate",
            params={"pair": "USD-BRL"},
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 403

    def test_correct_key_passes(self, client):
        resp = client.get(
            "/api/mobile/exchange-rate",
            params={"pair": "USD-BRL"},
            headers=HEADERS,
        )
        # May fail due to external API, but should NOT be 403
        assert resp.status_code != 403

    def test_key_required_on_quotes(self, client):
        resp = client.get("/api/mobile/quotes", params={"symbols": "ITUB3.SA"})
        assert resp.status_code == 403

    def test_key_required_on_dividends(self, client):
        resp = client.get("/api/mobile/dividends", params={"symbols": "ITUB3.SA"})
        assert resp.status_code == 403

    def test_key_required_on_track(self, client):
        resp = client.post(
            "/api/mobile/track",
            params={"symbol": "ITUB3.SA", "asset_class": "acoesBR"},
        )
        assert resp.status_code == 403

    def test_key_required_on_sync(self, client):
        resp = client.post(
            "/api/mobile/track/sync",
            params={"symbols": "ITUB3.SA:acoesBR"},
        )
        assert resp.status_code == 403


# ── Input Validation ──


class TestInputValidation:
    def test_invalid_pair_format(self, client):
        resp = client.get(
            "/api/mobile/exchange-rate",
            params={"pair": "invalid"},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_valid_pair_format(self, client):
        resp = client.get(
            "/api/mobile/exchange-rate",
            params={"pair": "USD-BRL"},
            headers=HEADERS,
        )
        assert resp.status_code != 422

    def test_invalid_symbol_format(self, client):
        resp = client.get(
            "/api/mobile/quotes",
            params={"symbols": "ITUB3.SA,<script>alert(1)</script>"},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_too_many_symbols(self, client):
        symbols = ",".join([f"SYM{i}" for i in range(51)])
        resp = client.get(
            "/api/mobile/quotes",
            params={"symbols": symbols},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_invalid_asset_class_on_track(self, client):
        resp = client.post(
            "/api/mobile/track",
            params={"symbol": "ITUB3.SA", "asset_class": "invalid"},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_valid_track(self, client):
        resp = client.post(
            "/api/mobile/track",
            params={"symbol": "ITUB3.SA", "asset_class": "acoesBR"},
            headers=HEADERS,
        )
        assert resp.status_code == 201

    def test_invalid_symbol_on_track(self, client):
        resp = client.post(
            "/api/mobile/track",
            params={"symbol": "DROP TABLE;", "asset_class": "acoesBR"},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_invalid_asset_class_on_sync(self, client):
        resp = client.post(
            "/api/mobile/track/sync",
            params={"symbols": "ITUB3.SA:invalid"},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_valid_sync(self, client):
        resp = client.post(
            "/api/mobile/track/sync",
            params={"symbols": "ITUB3.SA:acoesBR,HGLG11.SA:fiis"},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_too_many_symbols_on_sync(self, client):
        symbols = ",".join([f"SYM{i}:acoesBR" for i in range(51)])
        resp = client.post(
            "/api/mobile/track/sync",
            params={"symbols": symbols},
            headers=HEADERS,
        )
        assert resp.status_code == 422
