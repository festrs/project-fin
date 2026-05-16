"""Tests for POST /api/mobile/redeem.

The endpoint reads valid codes from `settings.mobile_redeem_codes`
(comma-separated). When the env is empty, every code is rejected.
"""

import pytest

from app.config import settings


HEADERS = {"X-API-Key": "test-mobile-key"}


@pytest.fixture
def configured_codes():
    """Configure two valid codes for the duration of a single test."""
    original = settings.mobile_redeem_codes
    settings.mobile_redeem_codes = "GROVE-UNLIMITED, GROVE-FRIENDS-FAMILY"
    yield
    settings.mobile_redeem_codes = original


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
        original = settings.mobile_redeem_codes
        settings.mobile_redeem_codes = ""
        try:
            resp = client.post("/api/mobile/redeem",
                               params={"code": "GROVE-UNLIMITED"}, headers=HEADERS)
            assert resp.status_code == 200
            assert resp.json()["valid"] is False
        finally:
            settings.mobile_redeem_codes = original
