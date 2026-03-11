# Market Data Provider Migration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace yfinance with Finnhub (US stocks) and brapi (BR stocks) using a provider strategy pattern, backed by a scheduled data pipeline that stores quotes in the database.

**Architecture:** Provider protocol with FinnhubProvider and BrapiProvider implementations, routed by country. MarketDataService reads from a `market_quotes` DB table populated by a twice-daily APScheduler job. On-demand fallback for cache misses. Stock API routes split by country (`/us/`, `/br/`).

**Tech Stack:** FastAPI, SQLAlchemy, httpx, APScheduler, cachetools

**Spec:** `docs/superpowers/specs/2026-03-11-yfinance-to-finnhub-brapi-design.md`

---

## Chunk 1: Provider Interface + FinnhubProvider

### Task 1: Provider Protocol (base.py)

**Files:**
- Create: `backend/app/providers/__init__.py`
- Create: `backend/app/providers/base.py`
- Test: `backend/tests/test_providers/test_base.py`

- [ ] **Step 1: Create the providers package**

```bash
mkdir -p backend/app/providers
touch backend/app/providers/__init__.py
```

- [ ] **Step 2: Write the failing test for the protocol**

Create `backend/tests/test_providers/__init__.py` and `backend/tests/test_providers/test_base.py`:

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_providers/test_base.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write the protocol**

Create `backend/app/providers/base.py`:

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class MarketDataProvider(Protocol):
    def get_quote(self, symbol: str) -> dict:
        """Returns: {symbol, name, current_price, currency, market_cap}"""
        ...

    def get_history(self, symbol: str, period: str) -> list[dict]:
        """Returns: [{date, close, volume}, ...]"""
        ...
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_providers/test_base.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/providers/ backend/tests/test_providers/
git commit -m "feat: add MarketDataProvider protocol"
```

---

### Task 2: Configuration (API keys)

**Files:**
- Modify: `backend/app/config.py:4-11`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_config.py`:

```python
import os
from unittest.mock import patch


def test_settings_has_finnhub_api_key():
    with patch.dict(os.environ, {"FINNHUB_API_KEY": "test-key", "BRAPI_API_KEY": "test-key2"}):
        from importlib import reload
        import app.config
        reload(app.config)
        assert app.config.settings.finnhub_api_key == "test-key"


def test_settings_has_brapi_api_key():
    with patch.dict(os.environ, {"FINNHUB_API_KEY": "test-key", "BRAPI_API_KEY": "test-key2"}):
        from importlib import reload
        import app.config
        reload(app.config)
        assert app.config.settings.brapi_api_key == "test-key2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: FAIL with `AttributeError`

- [ ] **Step 3: Add API key settings**

Edit `backend/app/config.py` — add to the `Settings` class after `coingecko_api_url`:

```python
    finnhub_api_key: str = ""
    brapi_api_key: str = ""
    finnhub_base_url: str = "https://finnhub.io/api/v1"
    brapi_base_url: str = "https://brapi.dev"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/tests/test_config.py
git commit -m "feat: add Finnhub and brapi API key config"
```

---

### Task 3: FinnhubProvider

**Files:**
- Create: `backend/app/providers/finnhub.py`
- Test: `backend/tests/test_providers/test_finnhub.py`

- [ ] **Step 1: Write the failing test for get_quote**

Create `backend/tests/test_providers/test_finnhub.py`:

```python
from unittest.mock import patch, MagicMock

from app.providers.finnhub import FinnhubProvider


class TestFinnhubGetQuote:
    def test_returns_correct_structure(self):
        provider = FinnhubProvider(api_key="test-key", base_url="https://finnhub.io/api/v1")

        mock_quote_resp = MagicMock()
        mock_quote_resp.json.return_value = {
            "c": 175.50,  # current price
            "h": 176.0,
            "l": 174.0,
            "o": 175.0,
            "pc": 174.50,
        }
        mock_quote_resp.raise_for_status = MagicMock()

        mock_profile_resp = MagicMock()
        mock_profile_resp.json.return_value = {
            "name": "Apple Inc",
            "currency": "USD",
            "marketCapitalization": 2800000.0,  # Finnhub returns in millions
        }
        mock_profile_resp.raise_for_status = MagicMock()

        with patch("app.providers.finnhub.httpx.get") as mock_get:
            mock_get.side_effect = [mock_quote_resp, mock_profile_resp]
            result = provider.get_quote("AAPL")

        assert result["symbol"] == "AAPL"
        assert result["name"] == "Apple Inc"
        assert result["current_price"] == 175.50
        assert result["currency"] == "USD"
        assert result["market_cap"] == 2_800_000_000_000  # converted from millions

    def test_passes_api_key(self):
        provider = FinnhubProvider(api_key="my-key", base_url="https://finnhub.io/api/v1")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"c": 100.0}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.finnhub.httpx.get", return_value=mock_resp) as mock_get:
            try:
                provider.get_quote("AAPL")
            except Exception:
                pass
            # Verify token param was passed in first call
            call_args = mock_get.call_args_list[0]
            assert call_args[1]["params"]["token"] == "my-key"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_providers/test_finnhub.py::TestFinnhubGetQuote -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement FinnhubProvider.get_quote**

Create `backend/app/providers/finnhub.py`:

```python
import httpx


class FinnhubProvider:
    def __init__(self, api_key: str, base_url: str = "https://finnhub.io/api/v1"):
        self._api_key = api_key
        self._base_url = base_url

    def get_quote(self, symbol: str) -> dict:
        quote_resp = httpx.get(
            f"{self._base_url}/quote",
            params={"symbol": symbol, "token": self._api_key},
        )
        quote_resp.raise_for_status()
        quote_data = quote_resp.json()

        profile_resp = httpx.get(
            f"{self._base_url}/stock/profile2",
            params={"symbol": symbol, "token": self._api_key},
        )
        profile_resp.raise_for_status()
        profile_data = profile_resp.json()

        return {
            "symbol": symbol,
            "name": profile_data.get("name", ""),
            "current_price": quote_data.get("c", 0.0),
            "currency": profile_data.get("currency", "USD"),
            "market_cap": profile_data.get("marketCapitalization", 0) * 1_000_000,
        }

    def get_history(self, symbol: str, period: str = "1mo") -> list[dict]:
        raise NotImplementedError
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_providers/test_finnhub.py::TestFinnhubGetQuote -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for get_history**

Add to `backend/tests/test_providers/test_finnhub.py`:

```python
from datetime import datetime, timedelta


class TestFinnhubGetHistory:
    def test_returns_correct_structure(self):
        provider = FinnhubProvider(api_key="test-key", base_url="https://finnhub.io/api/v1")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "c": [170.0, 175.0],
            "v": [1000000, 1200000],
            "t": [1704067200, 1704153600],  # 2024-01-01 and 2024-01-02 UTC
            "s": "ok",
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.finnhub.httpx.get", return_value=mock_resp):
            result = provider.get_history("AAPL", period="1mo")

        assert len(result) == 2
        assert result[0]["date"] == "2024-01-01"
        assert result[0]["close"] == 170.0
        assert result[0]["volume"] == 1000000
        assert result[1]["date"] == "2024-01-02"

    def test_no_data_returns_empty(self):
        provider = FinnhubProvider(api_key="test-key", base_url="https://finnhub.io/api/v1")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"s": "no_data"}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.finnhub.httpx.get", return_value=mock_resp):
            result = provider.get_history("INVALID", period="1mo")

        assert result == []
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_providers/test_finnhub.py::TestFinnhubGetHistory -v`
Expected: FAIL with `NotImplementedError`

- [ ] **Step 7: Implement FinnhubProvider.get_history**

Replace the `get_history` method and add the import for `datetime` in `backend/app/providers/finnhub.py`:

```python
import time
from datetime import datetime, timedelta, timezone

import httpx

PERIOD_DAYS = {
    "1mo": 30,
    "3mo": 90,
    "1y": 365,
}


class FinnhubProvider:
    def __init__(self, api_key: str, base_url: str = "https://finnhub.io/api/v1"):
        self._api_key = api_key
        self._base_url = base_url

    def get_quote(self, symbol: str) -> dict:
        quote_resp = httpx.get(
            f"{self._base_url}/quote",
            params={"symbol": symbol, "token": self._api_key},
        )
        quote_resp.raise_for_status()
        quote_data = quote_resp.json()

        profile_resp = httpx.get(
            f"{self._base_url}/stock/profile2",
            params={"symbol": symbol, "token": self._api_key},
        )
        profile_resp.raise_for_status()
        profile_data = profile_resp.json()

        return {
            "symbol": symbol,
            "name": profile_data.get("name", ""),
            "current_price": quote_data.get("c", 0.0),
            "currency": profile_data.get("currency", "USD"),
            "market_cap": profile_data.get("marketCapitalization", 0) * 1_000_000,
        }

    def get_history(self, symbol: str, period: str = "1mo") -> list[dict]:
        now = datetime.now(timezone.utc)
        days = PERIOD_DAYS.get(period, 30)
        from_ts = int((now - timedelta(days=days)).timestamp())
        to_ts = int(now.timestamp())

        resp = httpx.get(
            f"{self._base_url}/stock/candle",
            params={
                "symbol": symbol,
                "resolution": "D",
                "from": from_ts,
                "to": to_ts,
                "token": self._api_key,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("s") != "ok":
            return []

        return [
            {
                "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                "close": close,
                "volume": int(volume),
            }
            for ts, close, volume in zip(data["t"], data["c"], data["v"])
        ]
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_providers/test_finnhub.py -v`
Expected: ALL PASS

- [ ] **Step 9: Verify FinnhubProvider satisfies the protocol**

Add to `backend/tests/test_providers/test_finnhub.py`:

```python
from app.providers.base import MarketDataProvider


def test_finnhub_satisfies_protocol():
    provider = FinnhubProvider(api_key="test")
    assert isinstance(provider, MarketDataProvider)
```

Run: `cd backend && python -m pytest tests/test_providers/test_finnhub.py::test_finnhub_satisfies_protocol -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/providers/finnhub.py backend/tests/test_providers/test_finnhub.py
git commit -m "feat: add FinnhubProvider for US stock data"
```

---

### Task 4: BrapiProvider

**Files:**
- Create: `backend/app/providers/brapi.py`
- Test: `backend/tests/test_providers/test_brapi.py`

- [ ] **Step 1: Write the failing test for get_quote**

Create `backend/tests/test_providers/test_brapi.py`:

```python
from unittest.mock import patch, MagicMock

from app.providers.brapi import BrapiProvider


class TestBrapiGetQuote:
    def test_returns_correct_structure(self):
        provider = BrapiProvider(api_key="test-key", base_url="https://brapi.dev")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [
                {
                    "shortName": "PETROBRAS PN",
                    "regularMarketPrice": 38.50,
                    "currency": "BRL",
                    "marketCap": 500_000_000_000,
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp) as mock_get:
            result = provider.get_quote("PETR4.SA")

        assert result["symbol"] == "PETR4.SA"
        assert result["name"] == "PETROBRAS PN"
        assert result["current_price"] == 38.50
        assert result["currency"] == "BRL"
        assert result["market_cap"] == 500_000_000_000

    def test_strips_sa_suffix_for_api_call(self):
        provider = BrapiProvider(api_key="test-key", base_url="https://brapi.dev")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [{"shortName": "X", "regularMarketPrice": 10.0, "currency": "BRL", "marketCap": 0}]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp) as mock_get:
            provider.get_quote("PETR4.SA")

        # Verify the URL uses the stripped symbol
        call_url = mock_get.call_args[0][0]
        assert "PETR4" in call_url
        assert ".SA" not in call_url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_providers/test_brapi.py::TestBrapiGetQuote -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement BrapiProvider.get_quote**

Create `backend/app/providers/brapi.py`:

```python
import httpx


def _strip_sa(symbol: str) -> str:
    return symbol.removesuffix(".SA")


class BrapiProvider:
    def __init__(self, api_key: str, base_url: str = "https://brapi.dev"):
        self._api_key = api_key
        self._base_url = base_url

    def get_quote(self, symbol: str) -> dict:
        ticker = _strip_sa(symbol)
        resp = httpx.get(
            f"{self._base_url}/api/quote/{ticker}",
            params={"token": self._api_key},
        )
        resp.raise_for_status()
        data = resp.json()["results"][0]

        return {
            "symbol": symbol,
            "name": data.get("shortName", ""),
            "current_price": data.get("regularMarketPrice", 0.0),
            "currency": data.get("currency", "BRL"),
            "market_cap": data.get("marketCap", 0),
        }

    def get_history(self, symbol: str, period: str = "1mo") -> list[dict]:
        raise NotImplementedError
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_providers/test_brapi.py::TestBrapiGetQuote -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for get_history**

Add to `backend/tests/test_providers/test_brapi.py`:

```python
class TestBrapiGetHistory:
    def test_returns_correct_structure(self):
        provider = BrapiProvider(api_key="test-key", base_url="https://brapi.dev")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [
                {
                    "historicalDataPrice": [
                        {"date": 1704067200, "close": 35.0, "volume": 5000000},
                        {"date": 1704153600, "close": 36.0, "volume": 6000000},
                    ]
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp):
            result = provider.get_history("PETR4.SA", period="1mo")

        assert len(result) == 2
        assert result[0]["date"] == "2024-01-01"
        assert result[0]["close"] == 35.0
        assert result[0]["volume"] == 5000000

    def test_strips_sa_suffix_for_history(self):
        provider = BrapiProvider(api_key="test-key", base_url="https://brapi.dev")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [{"historicalDataPrice": []}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.brapi.httpx.get", return_value=mock_resp) as mock_get:
            provider.get_history("VALE3.SA", period="1mo")

        call_url = mock_get.call_args[0][0]
        assert "VALE3" in call_url
        assert ".SA" not in call_url
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_providers/test_brapi.py::TestBrapiGetHistory -v`
Expected: FAIL with `NotImplementedError`

- [ ] **Step 7: Implement BrapiProvider.get_history**

Update `backend/app/providers/brapi.py` — replace the `get_history` method and add the datetime import:

```python
from datetime import datetime, timezone

import httpx


def _strip_sa(symbol: str) -> str:
    return symbol.removesuffix(".SA")


class BrapiProvider:
    def __init__(self, api_key: str, base_url: str = "https://brapi.dev"):
        self._api_key = api_key
        self._base_url = base_url

    def get_quote(self, symbol: str) -> dict:
        ticker = _strip_sa(symbol)
        resp = httpx.get(
            f"{self._base_url}/api/quote/{ticker}",
            params={"token": self._api_key},
        )
        resp.raise_for_status()
        data = resp.json()["results"][0]

        return {
            "symbol": symbol,
            "name": data.get("shortName", ""),
            "current_price": data.get("regularMarketPrice", 0.0),
            "currency": data.get("currency", "BRL"),
            "market_cap": data.get("marketCap", 0),
        }

    def get_history(self, symbol: str, period: str = "1mo") -> list[dict]:
        ticker = _strip_sa(symbol)
        resp = httpx.get(
            f"{self._base_url}/api/quote/{ticker}",
            params={
                "range": period,
                "interval": "1d",
                "token": self._api_key,
            },
        )
        resp.raise_for_status()
        data = resp.json()["results"][0]
        history = data.get("historicalDataPrice", [])

        return [
            {
                "date": datetime.fromtimestamp(item["date"], tz=timezone.utc).strftime("%Y-%m-%d"),
                "close": item["close"],
                "volume": int(item.get("volume", 0)),
            }
            for item in history
        ]
```

- [ ] **Step 8: Run all provider tests**

Run: `cd backend && python -m pytest tests/test_providers/ -v`
Expected: ALL PASS

- [ ] **Step 9: Verify BrapiProvider satisfies protocol**

Add to `backend/tests/test_providers/test_brapi.py`:

```python
from app.providers.base import MarketDataProvider


def test_brapi_satisfies_protocol():
    provider = BrapiProvider(api_key="test")
    assert isinstance(provider, MarketDataProvider)
```

Run: `cd backend && python -m pytest tests/test_providers/test_brapi.py::test_brapi_satisfies_protocol -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/providers/brapi.py backend/tests/test_providers/test_brapi.py
git commit -m "feat: add BrapiProvider for BR stock data"
```

---

## Chunk 2: Data Model + MarketDataService Refactor

### Task 5: MarketQuote Model + AssetClass Country Column

**Files:**
- Create: `backend/app/models/market_quote.py`
- Modify: `backend/app/models/asset_class.py:10-20`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/seed.py:18-21`

- [ ] **Step 1: Write the failing test for MarketQuote model**

Create `backend/tests/test_models/test_market_quote.py`:

```python
from datetime import datetime, timezone

from app.models.market_quote import MarketQuote


def test_market_quote_has_correct_columns():
    quote = MarketQuote(
        symbol="AAPL",
        name="Apple Inc",
        current_price=175.50,
        currency="USD",
        market_cap=2_800_000_000_000,
        country="US",
    )
    assert quote.symbol == "AAPL"
    assert quote.name == "Apple Inc"
    assert quote.current_price == 175.50
    assert quote.currency == "USD"
    assert quote.market_cap == 2_800_000_000_000
    assert quote.country == "US"


def test_market_quote_persists(db):
    quote = MarketQuote(
        symbol="PETR4.SA",
        name="Petrobras",
        current_price=38.50,
        currency="BRL",
        market_cap=500_000_000_000,
        country="BR",
    )
    db.add(quote)
    db.commit()

    loaded = db.query(MarketQuote).filter_by(symbol="PETR4.SA").first()
    assert loaded is not None
    assert loaded.current_price == 38.50
    assert loaded.country == "BR"
    assert loaded.updated_at is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_models/test_market_quote.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create the MarketQuote model**

Create `backend/tests/test_models/__init__.py` (empty) and `backend/app/models/market_quote.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MarketQuote(Base):
    __tablename__ = "market_quotes"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    current_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    market_cap: Mapped[float] = mapped_column(Float, default=0)
    country: Mapped[str] = mapped_column(String(2), default="US")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 4: Register in models __init__**

Edit `backend/app/models/__init__.py` to add the import:

```python
from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction
from app.models.quarantine_config import QuarantineConfig
from app.models.market_quote import MarketQuote

__all__ = ["User", "AssetClass", "AssetWeight", "Transaction", "QuarantineConfig", "MarketQuote"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_models/test_market_quote.py -v`
Expected: PASS

- [ ] **Step 6: Add country column to AssetClass**

Edit `backend/app/models/asset_class.py` — add after the `name` field (line 15):

```python
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
```

- [ ] **Step 7: Update seed data to set country for BR classes**

Edit `backend/app/seed.py` — replace the class creation loop (lines 18-21):

```python
        class_configs = [
            ("US Stocks", "US"),
            ("BR Stocks", "BR"),
            ("Crypto", "US"),
            ("Stablecoins", "US"),
        ]
        for name, country in class_configs:
            ac = AssetClass(user_id=user.id, name=name, target_weight=25.0, country=country)
            db.add(ac)
```

- [ ] **Step 8: Run full test suite to verify nothing breaks**

Run: `cd backend && python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/market_quote.py backend/app/models/__init__.py backend/app/models/asset_class.py backend/app/seed.py backend/tests/test_models/
git commit -m "feat: add MarketQuote model and country column to AssetClass"
```

---

### Task 6: Consolidate CRYPTO maps into market_data.py

**Files:**
- Modify: `backend/app/services/market_data.py:1-5` (add constants)
- Modify: `backend/app/services/portfolio.py:11-18` (remove constants, import)
- Modify: `backend/app/services/recommendation.py:9-16` (remove constants, import)

- [ ] **Step 1: Add CRYPTO maps to market_data.py**

Edit `backend/app/services/market_data.py` — add after the imports (before the class):

```python
CRYPTO_COINGECKO_MAP = {
    "BTC": "bitcoin", "BTC-USD": "bitcoin",
    "ETH": "ethereum", "ETH-USD": "ethereum",
    "USDT": "tether", "USDT-USD": "tether",
    "USDC": "usd-coin", "USDC-USD": "usd-coin",
    "DAI": "dai", "DAI-USD": "dai",
}
CRYPTO_CLASS_NAMES = {"Crypto", "Cryptos", "Stablecoins"}
```

- [ ] **Step 2: Update portfolio.py to import from market_data**

Replace lines 11-18 of `backend/app/services/portfolio.py`:

```python
from app.services.market_data import MarketDataService, CRYPTO_COINGECKO_MAP, CRYPTO_CLASS_NAMES
```

Remove the duplicate `CRYPTO_COINGECKO_MAP` and `CRYPTO_CLASS_NAMES` definitions (lines 11-18).

- [ ] **Step 3: Update recommendation.py to import from market_data**

Replace lines 5 and 9-16 of `backend/app/services/recommendation.py`:

```python
from app.services.market_data import MarketDataService, CRYPTO_COINGECKO_MAP, CRYPTO_CLASS_NAMES
```

Remove the duplicate definitions (lines 9-16).

- [ ] **Step 4: Run full test suite**

Run: `cd backend && python -m pytest -v`
Expected: ALL PASS (behavior unchanged, just moved constants)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/market_data.py backend/app/services/portfolio.py backend/app/services/recommendation.py
git commit -m "refactor: consolidate CRYPTO maps into market_data.py"
```

---

### Task 7: Refactor MarketDataService to use providers + DB

**Files:**
- Modify: `backend/app/services/market_data.py`
- Modify: `backend/tests/test_services/test_market_data.py`

- [ ] **Step 1: Write failing tests for the new MarketDataService**

Replace `backend/tests/test_services/test_market_data.py` with:

```python
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from app.models.market_quote import MarketQuote
from app.services.market_data import MarketDataService


@pytest.fixture
def service():
    svc = MarketDataService()
    svc._quote_cache.clear()
    svc._history_cache.clear()
    svc._crypto_quote_cache.clear()
    svc._crypto_history_cache.clear()
    return svc


class TestGetStockQuote:
    def test_returns_from_db_when_present(self, service, db):
        quote = MarketQuote(
            symbol="AAPL",
            name="Apple Inc",
            current_price=175.50,
            currency="USD",
            market_cap=2_800_000_000_000,
            country="US",
        )
        db.add(quote)
        db.commit()

        result = service.get_stock_quote("AAPL", country="US", db=db)

        assert result["symbol"] == "AAPL"
        assert result["current_price"] == 175.50

    def test_falls_back_to_provider_when_not_in_db(self, service, db):
        mock_provider = MagicMock()
        mock_provider.get_quote.return_value = {
            "symbol": "AAPL",
            "name": "Apple Inc",
            "current_price": 175.50,
            "currency": "USD",
            "market_cap": 2_800_000_000_000,
        }
        service._finnhub = mock_provider

        result = service.get_stock_quote("AAPL", country="US", db=db)

        assert result["current_price"] == 175.50
        mock_provider.get_quote.assert_called_once_with("AAPL")
        # Verify it was stored in DB
        stored = db.query(MarketQuote).filter_by(symbol="AAPL").first()
        assert stored is not None
        assert stored.current_price == 175.50

    def test_routes_br_to_brapi(self, service, db):
        mock_provider = MagicMock()
        mock_provider.get_quote.return_value = {
            "symbol": "PETR4.SA",
            "name": "Petrobras",
            "current_price": 38.50,
            "currency": "BRL",
            "market_cap": 500_000_000_000,
        }
        service._brapi = mock_provider

        result = service.get_stock_quote("PETR4.SA", country="BR", db=db)

        assert result["current_price"] == 38.50
        mock_provider.get_quote.assert_called_once_with("PETR4.SA")


class TestGetStockHistory:
    def test_routes_us_to_finnhub(self, service):
        mock_provider = MagicMock()
        mock_provider.get_history.return_value = [
            {"date": "2024-01-01", "close": 170.0, "volume": 1000000},
        ]
        service._finnhub = mock_provider

        result = service.get_stock_history("AAPL", period="1mo", country="US")

        assert len(result) == 1
        mock_provider.get_history.assert_called_once_with("AAPL", "1mo")

    def test_routes_br_to_brapi(self, service):
        mock_provider = MagicMock()
        mock_provider.get_history.return_value = [
            {"date": "2024-01-01", "close": 35.0, "volume": 5000000},
        ]
        service._brapi = mock_provider

        result = service.get_stock_history("PETR4.SA", period="1mo", country="BR")

        assert len(result) == 1
        mock_provider.get_history.assert_called_once_with("PETR4.SA", "1mo")


class TestGetQuoteSafe:
    def test_passes_country_to_get_stock_quote(self, service, db):
        quote = MarketQuote(
            symbol="PETR4.SA",
            name="Petrobras",
            current_price=38.50,
            currency="BRL",
            market_cap=500_000_000_000,
            country="BR",
        )
        db.add(quote)
        db.commit()

        result = service.get_quote_safe("PETR4.SA", is_crypto=False, country="BR", db=db)
        assert result == 38.50

    def test_returns_none_on_error(self, service, db):
        service._finnhub = MagicMock()
        service._finnhub.get_quote.side_effect = Exception("network error")

        result = service.get_quote_safe("INVALID", is_crypto=False, country="US", db=db)
        assert result is None


class TestGetCryptoQuote:
    @patch("app.services.market_data.httpx.get")
    def test_returns_correct_structure(self, mock_get, service):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "bitcoin": {
                    "usd": 65000.0,
                    "usd_market_cap": 1_200_000_000_000,
                    "usd_24h_change": 2.5,
                }
            },
        )

        result = service.get_crypto_quote("bitcoin")

        assert result["coin_id"] == "bitcoin"
        assert result["current_price"] == 65000.0


class TestGetCryptoHistory:
    @patch("app.services.market_data.httpx.get")
    def test_returns_correct_structure(self, mock_get, service):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "prices": [
                    [1704067200000, 42000.0],
                    [1704153600000, 43000.0],
                ]
            },
        )

        result = service.get_crypto_history("bitcoin", days=30)

        assert len(result) == 2
        assert result[0]["price"] == 42000.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_services/test_market_data.py -v`
Expected: FAIL (new signatures don't match old implementation)

- [ ] **Step 3: Rewrite MarketDataService**

Replace `backend/app/services/market_data.py`:

```python
import logging
from datetime import datetime, timezone

import httpx
from cachetools import TTLCache
from sqlalchemy.orm import Session

from app.config import settings
from app.models.market_quote import MarketQuote
from app.providers.finnhub import FinnhubProvider
from app.providers.brapi import BrapiProvider

logger = logging.getLogger(__name__)

CRYPTO_COINGECKO_MAP = {
    "BTC": "bitcoin", "BTC-USD": "bitcoin",
    "ETH": "ethereum", "ETH-USD": "ethereum",
    "USDT": "tether", "USDT-USD": "tether",
    "USDC": "usd-coin", "USDC-USD": "usd-coin",
    "DAI": "dai", "DAI-USD": "dai",
}
CRYPTO_CLASS_NAMES = {"Crypto", "Cryptos", "Stablecoins"}


class MarketDataService:
    def __init__(self):
        self._finnhub = FinnhubProvider(
            api_key=settings.finnhub_api_key,
            base_url=settings.finnhub_base_url,
        )
        self._brapi = BrapiProvider(
            api_key=settings.brapi_api_key,
            base_url=settings.brapi_base_url,
        )
        self._quote_cache: TTLCache = TTLCache(maxsize=256, ttl=300)
        self._history_cache: TTLCache = TTLCache(maxsize=256, ttl=900)
        self._crypto_quote_cache: TTLCache = TTLCache(maxsize=256, ttl=120)
        self._crypto_history_cache: TTLCache = TTLCache(maxsize=256, ttl=900)

    def _get_provider(self, country: str):
        return self._brapi if country == "BR" else self._finnhub

    def get_stock_quote(self, symbol: str, country: str = "US", db: Session | None = None) -> dict:
        if symbol in self._quote_cache:
            return self._quote_cache[symbol]

        # Try DB first
        if db is not None:
            stored = db.query(MarketQuote).filter_by(symbol=symbol).first()
            if stored is not None:
                # Warn if data is stale (>24h)
                age = datetime.now(timezone.utc) - stored.updated_at.replace(tzinfo=timezone.utc)
                if age.total_seconds() > 86400:
                    logger.warning(f"Stale quote for {symbol}: last updated {stored.updated_at}")
                result = {
                    "symbol": stored.symbol,
                    "name": stored.name,
                    "current_price": stored.current_price,
                    "currency": stored.currency,
                    "market_cap": stored.market_cap,
                }
                self._quote_cache[symbol] = result
                return result

        # Fallback to live provider
        provider = self._get_provider(country)
        result = provider.get_quote(symbol)
        self._quote_cache[symbol] = result

        # Store in DB for future reads
        if db is not None:
            quote = db.query(MarketQuote).filter_by(symbol=symbol).first()
            if quote is None:
                quote = MarketQuote(symbol=symbol, country=country)
                db.add(quote)
            quote.name = result["name"]
            quote.current_price = result["current_price"]
            quote.currency = result["currency"]
            quote.market_cap = result["market_cap"]
            quote.country = country
            quote.updated_at = datetime.now(timezone.utc)
            db.commit()

        return result

    def get_stock_history(self, symbol: str, period: str = "1mo", country: str = "US") -> list[dict]:
        cache_key = f"{symbol}:{period}"
        if cache_key in self._history_cache:
            return self._history_cache[cache_key]

        provider = self._get_provider(country)
        result = provider.get_history(symbol, period)
        self._history_cache[cache_key] = result
        return result

    def get_quote_safe(
        self, symbol_or_coin_id: str, is_crypto: bool = False, country: str = "US", db: Session | None = None
    ) -> float | None:
        try:
            if is_crypto:
                quote = self.get_crypto_quote(symbol_or_coin_id)
            else:
                quote = self.get_stock_quote(symbol_or_coin_id, country=country, db=db)
            return quote.get("current_price")
        except Exception:
            return None

    def get_crypto_quote(self, coin_id: str) -> dict:
        if coin_id in self._crypto_quote_cache:
            return self._crypto_quote_cache[coin_id]

        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_market_cap": "true",
            "include_24hr_change": "true",
        }
        resp = httpx.get(url, params=params)
        data = resp.json()[coin_id]
        result = {
            "coin_id": coin_id,
            "current_price": data["usd"],
            "currency": "USD",
            "market_cap": data["usd_market_cap"],
            "change_24h": data["usd_24h_change"],
        }
        self._crypto_quote_cache[coin_id] = result
        return result

    def get_crypto_history(self, coin_id: str, days: int = 30) -> list[dict]:
        cache_key = f"{coin_id}:{days}"
        if cache_key in self._crypto_history_cache:
            return self._crypto_history_cache[cache_key]

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": days}
        resp = httpx.get(url, params=params)
        data = resp.json()
        result = [
            {
                "date": datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                "price": price,
            }
            for ts, price in data["prices"]
        ]
        self._crypto_history_cache[cache_key] = result
        return result


_instance: MarketDataService | None = None


def get_market_data_service() -> MarketDataService:
    global _instance
    if _instance is None:
        _instance = MarketDataService()
    return _instance
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_services/test_market_data.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/market_data.py backend/tests/test_services/test_market_data.py
git commit -m "refactor: MarketDataService to use providers + DB reads"
```

---

## Chunk 3: Route Changes + Caller Updates

### Task 8: Split Stock Routes by Country

**Files:**
- Modify: `backend/app/routers/stocks.py`
- Modify: `backend/tests/test_routers/test_stocks.py`

- [ ] **Step 1: Write the failing tests for new routes**

Replace `backend/tests/test_routers/test_stocks.py`:

```python
from unittest.mock import patch, MagicMock


@patch("app.routers.stocks.get_market_data_service")
def test_get_us_stock_quote(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_stock_quote.return_value = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "current_price": 175.0,
        "currency": "USD",
        "market_cap": 2800000000000,
    }
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/stocks/us/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["price"] == 175.0


@patch("app.routers.stocks.get_market_data_service")
def test_get_us_stock_history(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_stock_history.return_value = [
        {"date": "2025-01-01", "close": 170.0, "volume": 1000000},
    ]
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/stocks/us/AAPL/history?period=1mo")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["price"] == 170.0
    mock_md.get_stock_history.assert_called_once_with("AAPL", "1mo", country="US")


@patch("app.routers.stocks.get_market_data_service")
def test_get_br_stock_quote(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_stock_quote.return_value = {
        "symbol": "PETR4.SA",
        "name": "Petrobras",
        "current_price": 38.50,
        "currency": "BRL",
        "market_cap": 500000000000,
    }
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/stocks/br/PETR4.SA")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "PETR4.SA"
    assert data["price"] == 38.50


@patch("app.routers.stocks.get_market_data_service")
def test_get_br_stock_history(mock_get_mds, client):
    mock_md = MagicMock()
    mock_md.get_stock_history.return_value = [
        {"date": "2025-01-01", "close": 35.0, "volume": 5000000},
    ]
    mock_get_mds.return_value = mock_md
    resp = client.get("/api/stocks/br/PETR4.SA/history?period=1mo")
    assert resp.status_code == 200
    mock_md.get_stock_history.assert_called_once_with("PETR4.SA", "1mo", country="BR")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_routers/test_stocks.py -v`
Expected: FAIL (404 on `/api/stocks/us/...`)

- [ ] **Step 3: Rewrite the stocks router**

Replace `backend/app/routers/stocks.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import limiter, MARKET_DATA_LIMIT
from app.services.market_data import get_market_data_service

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/us/{symbol}")
@limiter.limit(MARKET_DATA_LIMIT)
def get_us_stock_quote(request: Request, symbol: str, db: Session = Depends(get_db)):
    market_data = get_market_data_service()
    try:
        quote = market_data.get_stock_quote(symbol, country="US", db=db)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch quote for {symbol}")
    return {
        "symbol": quote["symbol"],
        "name": quote["name"],
        "price": quote["current_price"],
        "currency": quote["currency"],
        "market_cap": quote["market_cap"],
    }


@router.get("/us/{symbol}/history")
@limiter.limit(MARKET_DATA_LIMIT)
def get_us_stock_history(request: Request, symbol: str, period: str = Query("1mo")):
    market_data = get_market_data_service()
    try:
        history = market_data.get_stock_history(symbol, period, country="US")
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch history for {symbol}")
    return [{"date": h["date"], "price": h["close"]} for h in history]


@router.get("/br/{symbol}")
@limiter.limit(MARKET_DATA_LIMIT)
def get_br_stock_quote(request: Request, symbol: str, db: Session = Depends(get_db)):
    market_data = get_market_data_service()
    try:
        quote = market_data.get_stock_quote(symbol, country="BR", db=db)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch quote for {symbol}")
    return {
        "symbol": quote["symbol"],
        "name": quote["name"],
        "price": quote["current_price"],
        "currency": quote["currency"],
        "market_cap": quote["market_cap"],
    }


@router.get("/br/{symbol}/history")
@limiter.limit(MARKET_DATA_LIMIT)
def get_br_stock_history(request: Request, symbol: str, period: str = Query("1mo")):
    market_data = get_market_data_service()
    try:
        history = market_data.get_stock_history(symbol, period, country="BR")
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch history for {symbol}")
    return [{"date": h["date"], "price": h["close"]} for h in history]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_routers/test_stocks.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/stocks.py backend/tests/test_routers/test_stocks.py
git commit -m "feat: split stock routes into /us/ and /br/ paths"
```

---

### Task 9: Update Portfolio Enrichment to Pass Country

**Files:**
- Modify: `backend/app/services/portfolio.py:135-152`
- Modify: `backend/app/routers/portfolio.py:24-35`
- Modify: `backend/tests/test_portfolio_enriched.py`

- [ ] **Step 1: Update enrich_holdings to pass country**

Edit `backend/app/services/portfolio.py` — modify the `fetch_price` inner function (lines 144-152) to look up country from class_map and pass it:

```python
    @staticmethod
    def enrich_holdings(
        holdings: list[dict],
        class_map: dict[str, dict],
        weight_map: dict[str, float],
        market_data: MarketDataService,
        db: Session | None = None,
    ) -> list[dict]:
        """Enrich holdings with current prices, values, gain/loss, and weights."""

        def fetch_price(holding: dict) -> tuple[str, float | None]:
            symbol = holding["symbol"]
            class_info = class_map.get(holding["asset_class_id"], {})
            class_name = class_info.get("name", "")
            country = class_info.get("country", "US")
            if class_name in CRYPTO_CLASS_NAMES:
                coin_id = CRYPTO_COINGECKO_MAP.get(symbol)
                if coin_id:
                    return symbol, market_data.get_quote_safe(coin_id, is_crypto=True)
            return symbol, market_data.get_quote_safe(symbol, is_crypto=False, country=country, db=db)
```

Note: The `Session` import is already present. Add `db` parameter to the function signature.

- [ ] **Step 2: Update portfolio router to pass country in class_map and db**

Edit `backend/app/routers/portfolio.py` — update `portfolio_summary` (lines 25-35):

```python
    class_map = {}
    weight_map = {}
    for ac in asset_classes:
        class_map[ac.id] = {"name": ac.name, "target_weight": ac.target_weight, "country": ac.country}
        weights = db.query(AssetWeight).filter(AssetWeight.asset_class_id == ac.id).all()
        for aw in weights:
            weight_map[aw.symbol] = aw.target_weight

    market_data = get_market_data_service()
    enriched = PortfolioService.enrich_holdings(holdings, class_map, weight_map, market_data, db=db)
```

- [ ] **Step 3: Update enrichment tests**

Edit `backend/tests/test_portfolio_enriched.py` — update `mock_safe` functions to accept the new `country` and `db` kwargs:

In `test_enrich_holdings_adds_current_price` (line 41):
```python
    def mock_safe(symbol, is_crypto=False, country="US", db=None):
        prices = {"AAPL": 150.0, "GOOG": 300.0}
        return prices.get(symbol)
```

In `test_enrich_holdings_handles_failed_price_fetch` (line 65):
Change `patch.object(market_data, "get_quote_safe", return_value=None)` — this still works since MagicMock accepts extra kwargs.

In `test_enrich_holdings_calculates_weights` (line 81):
```python
    def mock_safe(symbol, is_crypto=False, country="US", db=None):
        return 100.0
```

- [ ] **Step 4: Run the enrichment tests**

Run: `cd backend && python -m pytest tests/test_portfolio_enriched.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `cd backend && python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/portfolio.py backend/app/routers/portfolio.py backend/tests/test_portfolio_enriched.py
git commit -m "feat: thread country through portfolio enrichment"
```

---

### Task 10: Update Recommendation Service to Pass Country

**Files:**
- Modify: `backend/app/services/recommendation.py:26-33`
- Modify: `backend/tests/test_services/test_recommendation.py`

- [ ] **Step 1: Update _get_current_price to accept country**

Edit `backend/app/services/recommendation.py` — update `_get_current_price` (lines 26-33):

```python
    def _get_current_price(self, symbol: str, class_name: str, country: str = "US", db: Session | None = None) -> float:
        if class_name in CRYPTO_CLASS_NAMES:
            coin_id = CRYPTO_COINGECKO_MAP.get(symbol)
            if coin_id:
                quote = self.market_data.get_crypto_quote(coin_id)
                return quote["current_price"]
        quote = self.market_data.get_stock_quote(symbol, country=country, db=db)
        return quote["current_price"]
```

- [ ] **Step 2: Update the caller in get_recommendations**

Edit `backend/app/services/recommendation.py` — update the call at line 73:

```python
            price = self._get_current_price(h["symbol"], class_name, country=ac.country, db=self.db)
```

This requires `ac` (the AssetClass object) to be available. Update the loop (lines 70-74) to get it:

```python
        for h in holdings:
            ac = class_map.get(h["asset_class_id"])
            class_name = ac.name if ac else ""
            country = ac.country if ac else "US"
            price = self._get_current_price(h["symbol"], class_name, country=country, db=self.db)
            asset_values[h["symbol"]] = h["quantity"] * price
```

- [ ] **Step 3: Update recommendation tests**

Edit `backend/tests/test_services/test_recommendation.py`:

First, update the `_mock_market_data` helper to accept `country` and `db` kwargs:

```python
def _mock_market_data():
    """Return a mock MarketDataService that returns predictable prices."""
    mock = MagicMock()

    def stock_quote(symbol, country="US", db=None):
        prices = {"AAPL": 150.0, "GOOG": 200.0, "PETR4.SA": 40.0}
        return {"symbol": symbol, "current_price": prices.get(symbol, 100.0)}

    def crypto_quote(coin_id):
        prices = {"bitcoin": 50000.0}
        return {"coin_id": coin_id, "current_price": prices.get(coin_id, 100.0)}

    mock.get_stock_quote.side_effect = stock_quote
    mock.get_crypto_quote.side_effect = crypto_quote
    return mock
```

Then add a new test after `test_quarantined_asset_excluded`:

```python
    def test_recommend_with_br_stocks(self, db):
        """BR stock should route through brapi (country=BR)."""
        user = _create_user(db)

        ac_br = _create_asset_class(db, user.id, "BR Stocks", 100.0)
        ac_br.country = "BR"
        db.commit()

        _create_asset_weight(db, ac_br.id, "PETR4.SA", 100.0)
        _create_buy(db, user.id, ac_br.id, "PETR4.SA", 100, 38.0)

        mock_market = MagicMock()
        mock_market.get_stock_quote.return_value = {"current_price": 40.0}

        svc = RecommendationService(db, market_data_service=mock_market)
        recs = svc.get_recommendations(user.id, count=1)

        mock_market.get_stock_quote.assert_called_with("PETR4.SA", country="BR")
```

- [ ] **Step 4: Run recommendation tests**

Run: `cd backend && python -m pytest tests/test_services/test_recommendation.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `cd backend && python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/recommendation.py backend/tests/test_services/test_recommendation.py
git commit -m "feat: thread country through recommendation service"
```

---

## Chunk 4: Scheduler + Cleanup

### Task 11: MarketDataScheduler

**Files:**
- Create: `backend/app/services/market_data_scheduler.py`
- Test: `backend/tests/test_services/test_market_data_scheduler.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_services/test_market_data_scheduler.py`:

```python
from unittest.mock import patch, MagicMock, call

import pytest

from app.models.market_quote import MarketQuote
from app.models.asset_class import AssetClass
from app.models.transaction import Transaction
from app.models.user import User
from app.services.market_data_scheduler import MarketDataScheduler


@pytest.fixture
def scheduler():
    finnhub = MagicMock()
    brapi = MagicMock()
    return MarketDataScheduler(finnhub_provider=finnhub, brapi_provider=brapi)


def _setup_user_with_holdings(db):
    user = User(name="Test", email="test@test.com")
    db.add(user)
    db.flush()

    ac_us = AssetClass(user_id=user.id, name="US Stocks", target_weight=50.0, country="US")
    ac_br = AssetClass(user_id=user.id, name="BR Stocks", target_weight=50.0, country="BR")
    db.add_all([ac_us, ac_br])
    db.flush()

    from datetime import date
    tx1 = Transaction(
        user_id=user.id, asset_class_id=ac_us.id, asset_symbol="AAPL",
        type="buy", quantity=10, unit_price=150.0, total_value=1500.0,
        currency="USD", date=date(2025, 1, 1),
    )
    tx2 = Transaction(
        user_id=user.id, asset_class_id=ac_br.id, asset_symbol="PETR4.SA",
        type="buy", quantity=100, unit_price=38.0, total_value=3800.0,
        currency="BRL", date=date(2025, 1, 1),
    )
    db.add_all([tx1, tx2])
    db.commit()
    return user


class TestFetchAllQuotes:
    def test_fetches_and_stores_quotes(self, scheduler, db):
        _setup_user_with_holdings(db)

        scheduler._finnhub.get_quote.return_value = {
            "symbol": "AAPL", "name": "Apple", "current_price": 175.0,
            "currency": "USD", "market_cap": 2_800_000_000_000,
        }
        scheduler._brapi.get_quote.return_value = {
            "symbol": "PETR4.SA", "name": "Petrobras", "current_price": 40.0,
            "currency": "BRL", "market_cap": 500_000_000_000,
        }

        scheduler.fetch_all_quotes(db)

        aapl = db.query(MarketQuote).filter_by(symbol="AAPL").first()
        assert aapl is not None
        assert aapl.current_price == 175.0
        assert aapl.country == "US"

        petr = db.query(MarketQuote).filter_by(symbol="PETR4.SA").first()
        assert petr is not None
        assert petr.current_price == 40.0
        assert petr.country == "BR"

    def test_continues_on_individual_failure(self, scheduler, db):
        _setup_user_with_holdings(db)

        scheduler._finnhub.get_quote.side_effect = Exception("Finnhub down")
        scheduler._brapi.get_quote.return_value = {
            "symbol": "PETR4.SA", "name": "Petrobras", "current_price": 40.0,
            "currency": "BRL", "market_cap": 500_000_000_000,
        }

        scheduler.fetch_all_quotes(db)

        # AAPL should not be stored
        aapl = db.query(MarketQuote).filter_by(symbol="AAPL").first()
        assert aapl is None

        # PETR4.SA should still be stored
        petr = db.query(MarketQuote).filter_by(symbol="PETR4.SA").first()
        assert petr is not None

    def test_upserts_existing_quotes(self, scheduler, db):
        _setup_user_with_holdings(db)

        # Pre-existing quote
        old = MarketQuote(symbol="AAPL", name="Apple", current_price=170.0, currency="USD", country="US")
        db.add(old)
        db.commit()

        scheduler._finnhub.get_quote.return_value = {
            "symbol": "AAPL", "name": "Apple Inc", "current_price": 175.0,
            "currency": "USD", "market_cap": 2_800_000_000_000,
        }
        scheduler._brapi.get_quote.return_value = {
            "symbol": "PETR4.SA", "name": "Petrobras", "current_price": 40.0,
            "currency": "BRL", "market_cap": 500_000_000_000,
        }

        scheduler.fetch_all_quotes(db)

        aapl = db.query(MarketQuote).filter_by(symbol="AAPL").first()
        assert aapl.current_price == 175.0
        assert aapl.name == "Apple Inc"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_services/test_market_data_scheduler.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement MarketDataScheduler**

Create `backend/app/services/market_data_scheduler.py`:

```python
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.market_quote import MarketQuote
from app.models.transaction import Transaction
from app.services.market_data import CRYPTO_CLASS_NAMES

logger = logging.getLogger(__name__)


class MarketDataScheduler:
    def __init__(self, finnhub_provider, brapi_provider):
        self._finnhub = finnhub_provider
        self._brapi = brapi_provider

    def _get_provider(self, country: str):
        return self._brapi if country == "BR" else self._finnhub

    def fetch_all_quotes(self, db: Session) -> None:
        symbols = (
            db.query(Transaction.asset_symbol, AssetClass.country)
            .join(AssetClass, Transaction.asset_class_id == AssetClass.id)
            .filter(AssetClass.name.notin_(list(CRYPTO_CLASS_NAMES)))
            .distinct()
            .all()
        )

        for symbol, country in symbols:
            try:
                provider = self._get_provider(country)
                quote_data = provider.get_quote(symbol)

                quote = db.query(MarketQuote).filter_by(symbol=symbol).first()
                if quote is None:
                    quote = MarketQuote(symbol=symbol)
                    db.add(quote)

                quote.name = quote_data["name"]
                quote.current_price = quote_data["current_price"]
                quote.currency = quote_data["currency"]
                quote.market_cap = quote_data.get("market_cap", 0)
                quote.country = country
                quote.updated_at = datetime.now(timezone.utc)
                db.commit()

                logger.info(f"Updated quote for {symbol}: {quote_data['current_price']}")
            except Exception:
                logger.exception(f"Failed to fetch quote for {symbol}")
                db.rollback()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_services/test_market_data_scheduler.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/market_data_scheduler.py backend/tests/test_services/test_market_data_scheduler.py
git commit -m "feat: add MarketDataScheduler for periodic quote fetching"
```

---

### Task 12: Wire Scheduler into FastAPI Lifespan

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add APScheduler to requirements**

Edit `backend/requirements.txt` — replace `yfinance==0.2.51` with:

```
apscheduler==3.10.4
```

- [ ] **Step 2: Install dependencies**

Run: `cd backend && pip install -r requirements.txt`

- [ ] **Step 3: Update main.py with lifespan and scheduler**

First, add the scheduler toggle to config. Edit `backend/app/config.py` — add to the `Settings` class:

```python
    enable_scheduler: bool = True
    scheduler_hours: str = "9,17"
```

Then replace `backend/app/main.py`:

```python
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)


def _run_scheduled_fetch():
    from app.database import SessionLocal
    from app.services.market_data import get_market_data_service

    service = get_market_data_service()
    from app.services.market_data_scheduler import MarketDataScheduler
    scheduler = MarketDataScheduler(
        finnhub_provider=service._finnhub,
        brapi_provider=service._brapi,
    )

    db = SessionLocal()
    try:
        scheduler.fetch_all_quotes(db)
    except Exception:
        logger.exception("Scheduled market data fetch failed")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)
    from app.seed import seed_data
    seed_data()

    bg_scheduler = None
    if settings.enable_scheduler:
        from apscheduler.schedulers.background import BackgroundScheduler
        bg_scheduler = BackgroundScheduler()
        bg_scheduler.add_job(
            _run_scheduled_fetch, "cron",
            hour=settings.scheduler_hours,
            id="market_data_fetch",
        )
        bg_scheduler.start()
        logger.info(f"Market data scheduler started (runs at {settings.scheduler_hours})")

        _run_scheduled_fetch()

    yield

    if bg_scheduler is not None:
        bg_scheduler.shutdown()
        logger.info("Market data scheduler stopped")


app = FastAPI(title="Project Fin", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from app.routers import (
    asset_classes, asset_weights, transactions,
    stocks, crypto, portfolio, recommendations, quarantine,
)

app.include_router(asset_classes.router)
app.include_router(asset_weights.router)
app.include_router(transactions.router)
app.include_router(stocks.router)
app.include_router(crypto.router)
app.include_router(portfolio.router)
app.include_router(recommendations.router)
app.include_router(quarantine.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

Then update `backend/tests/conftest.py` to disable the scheduler during tests — add at the top before imports:

```python
import os
os.environ["ENABLE_SCHEDULER"] = "false"
```

- [ ] **Step 4: Run full test suite**

Run: `cd backend && python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/requirements.txt
git commit -m "feat: wire APScheduler for twice-daily market data fetch"
```

---

### Task 13: Update Remaining Test Files

**Files:**
- Modify: `backend/tests/test_routers/test_portfolio.py`
- Modify: `backend/tests/test_routers/test_recommendations.py`

- [ ] **Step 1: Run all tests to see what's broken**

Run: `cd backend && python -m pytest -v`
Look at failures — these tests may still pass since they use mocks, but verify.

- [ ] **Step 2: Fix any failing tests**

If `test_routers/test_portfolio.py` or `test_routers/test_recommendations.py` fail due to the `country` column or changed signatures, update the test fixtures to include `country` in AssetClass creation.

For `test_routers/test_portfolio.py` — `_setup_portfolio` (line 9) creates an `AssetClass` without `country`. Since the default is `"US"`, this should still work. Verify.

For `test_routers/test_recommendations.py` — `_setup` (line 9) also uses default. Should work. Verify.

- [ ] **Step 3: Run full test suite one final time**

Run: `cd backend && python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 4: Commit any fixes**

```bash
git add -u
git commit -m "fix: update remaining tests for provider migration"
```

---

### Task 14: Remove yfinance + Final Cleanup

**Files:**
- Verify: `backend/requirements.txt` (yfinance already removed in Task 12)

- [ ] **Step 1: Verify no remaining yfinance imports**

Run: `cd backend && grep -r "yfinance" --include="*.py" .`
Expected: No matches

- [ ] **Step 2: Verify no remaining pandas imports (was a yfinance dependency)**

Run: `cd backend && grep -r "import pandas" --include="*.py" .`
Expected: No matches (unless used elsewhere). If found only in old test, remove.

- [ ] **Step 3: Remove pandas from test dependencies if present**

Check if `pandas` is in `requirements.txt` — it's not explicitly listed (was a transitive dep of yfinance). No action needed.

- [ ] **Step 4: Run full test suite**

Run: `cd backend && python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 5: Final commit**

```bash
git add -u
git commit -m "chore: remove yfinance dependency, cleanup"
```

---

## Summary

| Task | Description | Key Files |
|------|-------------|-----------|
| 1 | Provider Protocol | `providers/base.py` |
| 2 | Config (API keys) | `config.py` |
| 3 | FinnhubProvider | `providers/finnhub.py` |
| 4 | BrapiProvider | `providers/brapi.py` |
| 5 | MarketQuote model + country column | `models/market_quote.py`, `models/asset_class.py` |
| 6 | Consolidate CRYPTO maps | `services/market_data.py` |
| 7 | Refactor MarketDataService | `services/market_data.py` |
| 8 | Split stock routes | `routers/stocks.py` |
| 9 | Update portfolio enrichment | `services/portfolio.py`, `routers/portfolio.py` |
| 10 | Update recommendations | `services/recommendation.py` |
| 11 | MarketDataScheduler | `services/market_data_scheduler.py` |
| 12 | Wire scheduler + remove yfinance | `main.py`, `requirements.txt` |
| 13 | Fix remaining tests | test files |
| 14 | Final cleanup | verify no yfinance remnants |
