"""Tests for POST /api/mobile/redeem.

The endpoint reads valid codes from `settings.mobile_redeem_codes`
(comma-separated). When the env is empty, every code is rejected.
"""

import pytest

import app.config


HEADERS = {"X-API-Key": "test-mobile-key"}


def _current_settings():
    """Return the live `settings` instance.

    `tests/test_config.py` reloads `app.config`, which replaces the module-
    level `settings` singleton. A `from app.config import settings` at
    test-module load time captures the pre-reload instance, but the router's
    runtime `from app.config import settings as _settings` (called per
    request) sees the post-reload one. Reading through `app.config.settings`
    at fixture-execution time keeps both views consistent.
    """
    return app.config.settings


@pytest.fixture(autouse=True)
def isolate_redeem_codes(monkeypatch):
    """Force a known-empty starting state so each test mutates from `""`."""
    monkeypatch.setattr(_current_settings(), "mobile_redeem_codes", "")


@pytest.fixture
def configured_codes(monkeypatch):
    """Configure two valid codes for the duration of a single test."""
    monkeypatch.setattr(
        _current_settings(),
        "mobile_redeem_codes",
        "GROVE-UNLIMITED, GROVE-FRIENDS-FAMILY",
    )


class TestRedeemCode:
    def test_valid_code_returns_unlock(self, client, configured_codes):
        resp = client.post("/api/mobile/redeem",
                           params={"code": "GROVE-UNLIMITED"}, headers=HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"valid": True, "unlocks": ["unlimited_assets"]}

    def test_second_configured_code_works(self, client, configured_codes):
        resp = client.post("/api/mobile/redeem",
                           params={"code": "GROVE-FRIENDS-FAMILY"}, headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_invalid_code_returns_valid_false(self, client, configured_codes):
        resp = client.post("/api/mobile/redeem",
                           params={"code": "NOT-A-REAL-CODE"}, headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json() == {"valid": False, "unlocks": []}

    def test_codes_are_case_sensitive(self, client, configured_codes):
        resp = client.post("/api/mobile/redeem",
                           params={"code": "grove-unlimited"}, headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["valid"] is False

    def test_whitespace_is_trimmed(self, client, configured_codes):
        resp = client.post("/api/mobile/redeem",
                           params={"code": "  GROVE-UNLIMITED  "}, headers=HEADERS)
        assert resp.json()["valid"] is True

    def test_empty_code_is_422(self, client, configured_codes):
        resp = client.post("/api/mobile/redeem",
                           params={"code": "   "}, headers=HEADERS)
        assert resp.status_code == 422

    def test_oversized_code_is_422(self, client, configured_codes):
        resp = client.post("/api/mobile/redeem",
                           params={"code": "x" * 200}, headers=HEADERS)
        assert resp.status_code == 422

    def test_no_codes_configured_rejects_everything(self, client):
        # `isolate_redeem_codes` autouse already sets the env to "" — this
        # test just asserts the resulting behavior.
        resp = client.post("/api/mobile/redeem",
                           params={"code": "GROVE-UNLIMITED"}, headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["valid"] is False
