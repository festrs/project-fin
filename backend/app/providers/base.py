from typing import Protocol, runtime_checkable


@runtime_checkable
class MarketDataProvider(Protocol):
    def get_quote(self, symbol: str) -> dict:
        """Returns: {symbol, name, current_price, currency, market_cap}"""
        ...

    def get_history(self, symbol: str, period: str) -> list[dict]:
        """Returns: [{date, close, volume}, ...]"""
        ...
