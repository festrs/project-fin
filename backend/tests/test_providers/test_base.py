from typing import runtime_checkable
from app.providers.base import MarketDataProvider


def test_protocol_has_get_quote():
    assert hasattr(MarketDataProvider, "get_quote")


def test_protocol_has_get_history():
    assert hasattr(MarketDataProvider, "get_history")


def test_class_implementing_protocol_is_recognized():
    class FakeProvider:
        def get_quote(self, symbol: str) -> dict:
            return {}

        def get_history(self, symbol: str, period: str) -> list[dict]:
            return []

    assert isinstance(FakeProvider(), MarketDataProvider)
