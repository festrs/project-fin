"""Tests for exchange rate service — Decimal return type, caching, fallback."""

import time
from decimal import Decimal
from unittest.mock import patch, MagicMock

import httpx
import pytest

import app.services.exchange_rate as fx_module
from app.services.exchange_rate import fetch_exchange_rate


@pytest.fixture(autouse=True)
def clear_cache():
    fx_module._fx_cache.clear()
    yield
    fx_module._fx_cache.clear()


def _mock_resp(bid: str, pair: str = "USD-BRL") -> MagicMock:
    key = pair.replace("-", "")
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {key: {"bid": bid}}
    return mock


class TestDecimalReturnType:
    def test_returns_decimal(self):
        with patch("httpx.get", return_value=_mock_resp("5.1234")):
            rate = fetch_exchange_rate("USD-BRL")
        assert isinstance(rate, Decimal)

    def test_exact_value_no_float_loss(self):
        with patch("httpx.get", return_value=_mock_resp("5.1234567890")):
            rate = fetch_exchange_rate("USD-BRL")
        assert rate == Decimal("5.1234567890")

    def test_fallback_is_decimal(self):
        with patch("httpx.get", side_effect=Exception("network error")):
            rate = fetch_exchange_rate("USD-BRL")
        assert isinstance(rate, Decimal)
        assert rate == Decimal("5.15")


class TestCaching:
    def test_cache_hit_skips_http(self):
        with patch("httpx.get", return_value=_mock_resp("5.00")) as mock_get:
            fetch_exchange_rate("USD-BRL")
            fetch_exchange_rate("USD-BRL")
        assert mock_get.call_count == 1

    def test_cache_stores_decimal(self):
        with patch("httpx.get", return_value=_mock_resp("5.20")):
            fetch_exchange_rate("USD-BRL")
        cached_value, _ = fx_module._fx_cache["USD-BRL"]
        assert isinstance(cached_value, Decimal)
        assert cached_value == Decimal("5.20")

    def test_cache_expires_after_ttl(self):
        with patch("httpx.get", return_value=_mock_resp("5.00")) as mock_get:
            fetch_exchange_rate("USD-BRL")
            # Manually expire the cache entry
            rate, _ = fx_module._fx_cache["USD-BRL"]
            fx_module._fx_cache["USD-BRL"] = (rate, time.time() - fx_module._FX_CACHE_TTL - 1)
            fetch_exchange_rate("USD-BRL")
        assert mock_get.call_count == 2

    def test_fallback_returns_cached_on_error_after_first_success(self):
        with patch("httpx.get", return_value=_mock_resp("4.80")):
            first = fetch_exchange_rate("USD-BRL")

        # Expire the cache, then simulate error
        rate, _ = fx_module._fx_cache["USD-BRL"]
        fx_module._fx_cache["USD-BRL"] = (rate, time.time() - fx_module._FX_CACHE_TTL - 1)

        with patch("httpx.get", side_effect=httpx.RequestError("timeout")):
            second = fetch_exchange_rate("USD-BRL")

        assert second == Decimal("4.80")


class TestFallback:
    def test_default_fallback_when_no_cache(self):
        with patch("httpx.get", side_effect=Exception("down")):
            rate = fetch_exchange_rate("USD-BRL")
        assert rate == Decimal("5.15")
