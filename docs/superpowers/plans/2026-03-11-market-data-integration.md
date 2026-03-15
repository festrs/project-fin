# Market Data Integration Fix — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix market search and enrich portfolio holdings with live market prices.

**Architecture:** Three independent fixes: (1) Fix API field name mismatches between backend and frontend for market search, (2) Add a new enriched portfolio summary endpoint that fetches current prices via MarketDataService with parallel fetching, (3) Fix the crypto class name detection bug. The backend already has all the market data infrastructure (yfinance, CoinGecko, TTL caching) — we just need to wire it correctly.

**Tech Stack:** FastAPI, yfinance, CoinGecko API, cachetools TTL caching, concurrent.futures for parallel price fetching, React/TypeScript frontend.

---

## Constraints & Rate Limits

- **yfinance**: Free, no API key. Each call ~1-2s. No official rate limit but avoid burst. TTL cache: 5min.
- **CoinGecko free tier**: ~10-30 calls/min. TTL cache: 2min.
- **Backend rate limit**: 30 req/min for market data endpoints, 60 req/min for CRUD.
- **Portfolio has 46 assets** — fetching all prices serially would take ~60-90s. Must parallelize.
- **Caching saves us**: After first load, subsequent calls within TTL are instant from cache.

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/services/market_data.py` | Modify | Add error handling, add `get_stock_quote_safe` wrapper |
| `backend/app/services/portfolio.py` | Modify | Add `get_enriched_holdings` method with parallel price fetching |
| `backend/app/services/recommendation.py` | Modify | Fix `CRYPTO_CLASS_NAMES` to include "Cryptos" |
| `backend/app/routers/stocks.py` | Modify | Normalize response field names (`current_price` → `price`) |
| `backend/app/routers/crypto.py` | Modify | Normalize response field names, add `name` field |
| `backend/app/routers/portfolio.py` | Modify | Wire enriched holdings into `/summary` endpoint |
| `frontend/src/hooks/useMarketData.ts` | Verify only | Already expects `price` — no changes needed after backend fix |
| `frontend/src/hooks/usePortfolio.ts` | Modify | Handle new enriched fields from backend |
| `backend/tests/test_market_search.py` | Create | Tests for normalized market search responses |
| `backend/tests/test_portfolio_enriched.py` | Create | Tests for enriched holdings |

---

## Chunk 1: Fix Market Search API Mismatch

### Task 1: Fix stock quote response field names

**Files:**
- Modify: `backend/app/routers/stocks.py`
- Create: `backend/tests/test_market_search.py`

The backend `get_stock_quote` returns `{"current_price": ...}` but the frontend `StockQuote` interface expects `{"price": ...}`. Fix at the router level so the service layer stays generic.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_market_search.py
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_stock_quote_returns_price_field():
    mock_quote = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "current_price": 150.0,
        "currency": "USD",
        "market_cap": 2_500_000_000_000,
    }
    with patch("app.routers.stocks.market_data.get_stock_quote", return_value=mock_quote):
        resp = client.get("/api/stocks/AAPL", headers={"X-User-Id": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "price" in data
        assert "current_price" not in data
        assert data["price"] == 150.0
        assert data["symbol"] == "AAPL"
        assert data["name"] == "Apple Inc."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_market_search.py::test_stock_quote_returns_price_field -v`
Expected: FAIL — response still has `current_price` instead of `price`

- [ ] **Step 3: Implement the fix in the router**

```python
# backend/app/routers/stocks.py
from fastapi import APIRouter, Query, Request

from app.middleware.rate_limit import limiter, MARKET_DATA_LIMIT
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

market_data = MarketDataService()


@router.get("/{symbol}")
@limiter.limit(MARKET_DATA_LIMIT)
def get_stock_quote(request: Request, symbol: str):
    quote = market_data.get_stock_quote(symbol)
    return {
        "symbol": quote["symbol"],
        "name": quote["name"],
        "price": quote["current_price"],
        "currency": quote["currency"],
        "market_cap": quote["market_cap"],
    }


@router.get("/{symbol}/history")
@limiter.limit(MARKET_DATA_LIMIT)
def get_stock_history(request: Request, symbol: str, period: str = Query("1mo")):
    history = market_data.get_stock_history(symbol, period)
    return [{"date": h["date"], "price": h["close"]} for h in history]
```

Note: History also needs normalization — backend returns `close` but frontend expects `price`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_market_search.py::test_stock_quote_returns_price_field -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/stocks.py backend/tests/test_market_search.py
git commit -m "fix: normalize stock quote response fields (current_price → price, close → price)"
```

### Task 2: Fix crypto quote response field names

**Files:**
- Modify: `backend/app/routers/crypto.py`
- Modify: `backend/tests/test_market_search.py`

The crypto backend returns `{"coin_id": ..., "current_price": ...}` without a `name` field. Frontend expects `{"coin_id": ..., "name": ..., "price": ...}`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_market_search.py`:

```python
def test_crypto_quote_returns_price_and_name_fields():
    mock_quote = {
        "coin_id": "bitcoin",
        "current_price": 95000.0,
        "currency": "USD",
        "market_cap": 1_800_000_000_000,
        "change_24h": 2.5,
    }
    with patch("app.routers.crypto.market_data.get_crypto_quote", return_value=mock_quote):
        resp = client.get("/api/crypto/bitcoin", headers={"X-User-Id": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "price" in data
        assert "name" in data
        assert "current_price" not in data
        assert data["price"] == 95000.0
        assert data["name"] == "bitcoin"
        assert data["coin_id"] == "bitcoin"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_market_search.py::test_crypto_quote_returns_price_and_name_fields -v`
Expected: FAIL

- [ ] **Step 3: Implement the fix**

```python
# backend/app/routers/crypto.py
from fastapi import APIRouter, Query, Request

from app.middleware.rate_limit import limiter, MARKET_DATA_LIMIT
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/api/crypto", tags=["crypto"])

market_data = MarketDataService()


@router.get("/{coin_id}")
@limiter.limit(MARKET_DATA_LIMIT)
def get_crypto_quote(request: Request, coin_id: str):
    quote = market_data.get_crypto_quote(coin_id)
    return {
        "coin_id": quote["coin_id"],
        "name": coin_id,
        "price": quote["current_price"],
        "currency": quote["currency"],
        "market_cap": quote["market_cap"],
        "change_24h": quote.get("change_24h"),
    }


@router.get("/{coin_id}/history")
@limiter.limit(MARKET_DATA_LIMIT)
def get_crypto_history(request: Request, coin_id: str, days: int = Query(30)):
    return market_data.get_crypto_history(coin_id, days)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_market_search.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/crypto.py backend/tests/test_market_search.py
git commit -m "fix: normalize crypto quote response fields and add name"
```

### Task 3: Fix crypto class name detection bug

**Files:**
- Modify: `backend/app/services/recommendation.py`

The import script created asset class `"Cryptos"` but `CRYPTO_CLASS_NAMES = {"Crypto", "Stablecoins"}`. The set check fails, so BTC/USDC/etc. fall through to yfinance (which will fail or return wrong data).

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_market_search.py`:

```python
def test_crypto_class_names_includes_cryptos():
    from app.services.recommendation import CRYPTO_CLASS_NAMES
    assert "Cryptos" in CRYPTO_CLASS_NAMES
    assert "Crypto" in CRYPTO_CLASS_NAMES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_market_search.py::test_crypto_class_names_includes_cryptos -v`
Expected: FAIL — `"Cryptos"` not in set

- [ ] **Step 3: Fix the constant**

In `backend/app/services/recommendation.py`, change line 16:

```python
CRYPTO_CLASS_NAMES = {"Crypto", "Cryptos", "Stablecoins"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_market_search.py::test_crypto_class_names_includes_cryptos -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/recommendation.py backend/tests/test_market_search.py
git commit -m "fix: add 'Cryptos' to CRYPTO_CLASS_NAMES for correct CoinGecko routing"
```

---

## Chunk 2: Enrich Portfolio Holdings with Live Prices

### Task 4: Add error-safe price fetching to MarketDataService

**Files:**
- Modify: `backend/app/services/market_data.py`

yfinance and CoinGecko can fail (network, bad symbol, rate limit). We need a safe wrapper that returns `None` on failure instead of crashing the whole portfolio load.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_portfolio_enriched.py
from unittest.mock import patch, MagicMock
from app.services.market_data import MarketDataService


def test_get_quote_safe_returns_none_on_error():
    service = MarketDataService()
    with patch.object(service, "get_stock_quote", side_effect=Exception("network error")):
        result = service.get_quote_safe("INVALID", is_crypto=False)
        assert result is None


def test_get_quote_safe_returns_price_for_stock():
    service = MarketDataService()
    mock_quote = {"current_price": 150.0}
    with patch.object(service, "get_stock_quote", return_value=mock_quote):
        result = service.get_quote_safe("AAPL", is_crypto=False)
        assert result == 150.0


def test_get_quote_safe_returns_price_for_crypto():
    service = MarketDataService()
    mock_quote = {"current_price": 95000.0}
    with patch.object(service, "get_crypto_quote", return_value=mock_quote):
        result = service.get_quote_safe("bitcoin", is_crypto=True)
        assert result == 95000.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_portfolio_enriched.py -v -k "get_quote_safe"`
Expected: FAIL — `get_quote_safe` does not exist

- [ ] **Step 3: Add `get_quote_safe` method**

Add to `backend/app/services/market_data.py`:

```python
def get_quote_safe(self, symbol_or_coin_id: str, is_crypto: bool = False) -> float | None:
    """Return current price or None if fetch fails."""
    try:
        if is_crypto:
            quote = self.get_crypto_quote(symbol_or_coin_id)
        else:
            quote = self.get_stock_quote(symbol_or_coin_id)
        return quote.get("current_price")
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_portfolio_enriched.py -v -k "get_quote_safe"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/market_data.py backend/tests/test_portfolio_enriched.py
git commit -m "feat: add get_quote_safe method for error-tolerant price fetching"
```

### Task 5: Add enriched holdings to PortfolioService

**Files:**
- Modify: `backend/app/services/portfolio.py`
- Modify: `backend/tests/test_portfolio_enriched.py`

Add a `get_enriched_holdings` method that takes existing holdings and enriches them with current prices, current value, gain/loss, and weight calculations. Use `concurrent.futures.ThreadPoolExecutor` to fetch prices in parallel (46 assets serially would take ~60-90s).

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_portfolio_enriched.py`:

```python
from unittest.mock import patch, MagicMock
from app.services.portfolio import PortfolioService
from app.services.market_data import MarketDataService


def test_enrich_holdings_adds_current_price():
    holdings = [
        {"symbol": "AAPL", "asset_class_id": "cls-1", "quantity": 10, "avg_price": 100.0, "total_cost": 1000.0},
        {"symbol": "GOOG", "asset_class_id": "cls-1", "quantity": 5, "avg_price": 200.0, "total_cost": 1000.0},
    ]
    class_map = {
        "cls-1": {"name": "Stocks US", "target_weight": 50.0},
    }
    weight_map = {"AAPL": 50.0, "GOOG": 50.0}

    def mock_safe(symbol, is_crypto=False):
        prices = {"AAPL": 150.0, "GOOG": 300.0}
        return prices.get(symbol)

    market_data = MarketDataService()
    with patch.object(market_data, "get_quote_safe", side_effect=mock_safe):
        result = PortfolioService.enrich_holdings(holdings, class_map, weight_map, market_data)

    assert result[0]["current_price"] == 150.0
    assert result[0]["current_value"] == 1500.0
    assert result[0]["gain_loss"] == 500.0  # (150 - 100) * 10
    assert result[1]["current_price"] == 300.0
    assert result[1]["current_value"] == 1500.0
    assert result[1]["gain_loss"] == 500.0


def test_enrich_holdings_handles_failed_price_fetch():
    holdings = [
        {"symbol": "INVALID", "asset_class_id": "cls-1", "quantity": 10, "avg_price": 100.0, "total_cost": 1000.0},
    ]
    class_map = {"cls-1": {"name": "Stocks US", "target_weight": 50.0}}
    weight_map = {"INVALID": 100.0}

    market_data = MarketDataService()
    with patch.object(market_data, "get_quote_safe", return_value=None):
        result = PortfolioService.enrich_holdings(holdings, class_map, weight_map, market_data)

    assert result[0]["current_price"] is None
    assert result[0]["current_value"] is None
    assert result[0]["gain_loss"] is None


def test_enrich_holdings_calculates_weights():
    holdings = [
        {"symbol": "AAPL", "asset_class_id": "cls-1", "quantity": 10, "avg_price": 100.0, "total_cost": 1000.0},
        {"symbol": "GOOG", "asset_class_id": "cls-1", "quantity": 10, "avg_price": 100.0, "total_cost": 1000.0},
    ]
    class_map = {"cls-1": {"name": "Stocks US", "target_weight": 50.0}}
    weight_map = {"AAPL": 60.0, "GOOG": 40.0}

    def mock_safe(symbol, is_crypto=False):
        return 100.0  # same price for both → each is 50% actual

    market_data = MarketDataService()
    with patch.object(market_data, "get_quote_safe", side_effect=mock_safe):
        result = PortfolioService.enrich_holdings(holdings, class_map, weight_map, market_data)

    # target_weight = class_weight * asset_weight / 100 = 50 * 60 / 100 = 30
    assert result[0]["target_weight"] == 30.0
    assert result[1]["target_weight"] == 20.0
    # actual_weight = (current_value / total_portfolio_value) * 100 = (1000 / 2000) * 100 = 50
    assert result[0]["actual_weight"] == 50.0
    assert result[1]["actual_weight"] == 50.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_portfolio_enriched.py -v -k "enrich_holdings"`
Expected: FAIL — `enrich_holdings` does not exist

- [ ] **Step 3: Implement `enrich_holdings` static method**

Add imports and method to `backend/app/services/portfolio.py`:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.market_data import MarketDataService

# Add CRYPTO_COINGECKO_MAP and CRYPTO_CLASS_NAMES at module level
CRYPTO_COINGECKO_MAP = {
    "BTC": "bitcoin", "BTC-USD": "bitcoin",
    "ETH": "ethereum", "ETH-USD": "ethereum",
    "USDT": "tether", "USDT-USD": "tether",
    "USDC": "usd-coin", "USDC-USD": "usd-coin",
    "DAI": "dai", "DAI-USD": "dai",
}
CRYPTO_CLASS_NAMES = {"Crypto", "Cryptos", "Stablecoins"}
```

Add static method to `PortfolioService`:

```python
@staticmethod
def enrich_holdings(
    holdings: list[dict],
    class_map: dict[str, dict],  # {class_id: {"name": str, "target_weight": float}}
    weight_map: dict[str, float],  # {symbol: asset_target_weight}
    market_data: MarketDataService,
) -> list[dict]:
    """Enrich holdings with current prices, values, gain/loss, and weights."""

    def fetch_price(holding: dict) -> tuple[str, float | None]:
        symbol = holding["symbol"]
        class_info = class_map.get(holding["asset_class_id"], {})
        class_name = class_info.get("name", "")
        if class_name in CRYPTO_CLASS_NAMES:
            coin_id = CRYPTO_COINGECKO_MAP.get(symbol)
            if coin_id:
                return symbol, market_data.get_quote_safe(coin_id, is_crypto=True)
        return symbol, market_data.get_quote_safe(symbol, is_crypto=False)

    # Fetch prices in parallel
    prices: dict[str, float | None] = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_price, h): h for h in holdings}
        for future in as_completed(futures):
            symbol, price = future.result()
            prices[symbol] = price

    # Calculate total portfolio value (only from assets with known prices)
    total_value = 0.0
    for h in holdings:
        price = prices.get(h["symbol"])
        if price is not None:
            total_value += h["quantity"] * price

    # Enrich each holding
    enriched = []
    for h in holdings:
        price = prices.get(h["symbol"])
        class_info = class_map.get(h["asset_class_id"], {})
        class_target = class_info.get("target_weight", 0.0)
        asset_target = weight_map.get(h["symbol"], 0.0)
        effective_target = class_target * asset_target / 100

        if price is not None:
            current_value = h["quantity"] * price
            gain_loss = (price - h["avg_price"]) * h["quantity"]
            actual_weight = (current_value / total_value * 100) if total_value > 0 else 0.0
        else:
            current_value = None
            gain_loss = None
            actual_weight = None

        enriched.append({
            **h,
            "current_price": price,
            "current_value": current_value,
            "gain_loss": gain_loss,
            "target_weight": effective_target,
            "actual_weight": actual_weight,
        })

    return enriched
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_portfolio_enriched.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/portfolio.py backend/tests/test_portfolio_enriched.py
git commit -m "feat: add enrich_holdings with parallel price fetching"
```

### Task 6: Wire enriched holdings into the portfolio summary endpoint

**Files:**
- Modify: `backend/app/routers/portfolio.py`

Update the `/api/portfolio/summary` endpoint to return enriched holdings with market data.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_portfolio_enriched.py`:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_portfolio_summary_returns_enriched_holdings(tmp_path):
    """Integration test: summary endpoint returns current_price field."""
    # This test verifies the endpoint shape. Mock market data to avoid real API calls.
    with patch("app.routers.portfolio.MarketDataService") as MockMDS:
        mock_instance = MockMDS.return_value
        mock_instance.get_quote_safe.return_value = 150.0

        resp = client.get("/api/portfolio/summary", headers={"X-User-Id": "default-user-id"})
        assert resp.status_code == 200
        data = resp.json()
        assert "holdings" in data
        # If there are holdings, they should have the enriched fields
        for h in data["holdings"]:
            assert "current_price" in h
            assert "current_value" in h
            assert "gain_loss" in h
            assert "target_weight" in h
            assert "actual_weight" in h
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_portfolio_enriched.py::test_portfolio_summary_returns_enriched_holdings -v`
Expected: FAIL — holdings don't have `current_price` field

- [ ] **Step 3: Update the portfolio router**

```python
# backend/app/routers/portfolio.py
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.services.market_data import MarketDataService
from app.services.portfolio import PortfolioService

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/summary")
@limiter.limit(CRUD_LIMIT)
def portfolio_summary(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    service = PortfolioService(db)
    holdings = service.get_holdings(x_user_id)

    # Build class_map and weight_map for enrichment
    asset_classes = db.query(AssetClass).filter(AssetClass.user_id == x_user_id).all()
    class_map = {}
    weight_map = {}
    for ac in asset_classes:
        class_map[ac.id] = {"name": ac.name, "target_weight": ac.target_weight}
        weights = db.query(AssetWeight).filter(AssetWeight.asset_class_id == ac.id).all()
        for aw in weights:
            weight_map[aw.symbol] = aw.target_weight

    market_data = MarketDataService()
    enriched = PortfolioService.enrich_holdings(holdings, class_map, weight_map, market_data)
    return {"holdings": enriched}


@router.get("/performance")
@limiter.limit(CRUD_LIMIT)
def portfolio_performance(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    service = PortfolioService(db)
    holdings = service.get_holdings(x_user_id)
    total_cost = sum(h["total_cost"] for h in holdings)
    return {"holdings": holdings, "total_cost": total_cost}


@router.get("/allocation")
@limiter.limit(CRUD_LIMIT)
def portfolio_allocation(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    service = PortfolioService(db)
    allocation = service.get_allocation(x_user_id)
    return {"allocation": allocation}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_portfolio_enriched.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/portfolio.py backend/tests/test_portfolio_enriched.py
git commit -m "feat: wire enriched holdings with market data into /portfolio/summary"
```

### Task 7: Share MarketDataService singleton across routers

**Files:**
- Modify: `backend/app/services/market_data.py`

Currently each router creates its own `MarketDataService()` instance, each with separate caches. The portfolio enrichment creates yet another instance. This means the same stock quote is fetched multiple times. Fix by using a module-level singleton so all caches are shared.

- [ ] **Step 1: Add singleton accessor**

Add to bottom of `backend/app/services/market_data.py`:

```python
_instance: MarketDataService | None = None


def get_market_data_service() -> MarketDataService:
    global _instance
    if _instance is None:
        _instance = MarketDataService()
    return _instance
```

- [ ] **Step 2: Update all consumers to use shared instance**

In `backend/app/routers/stocks.py`:
```python
from app.services.market_data import get_market_data_service
# Replace: market_data = MarketDataService()
# With usage: get_market_data_service() in each endpoint
```

In `backend/app/routers/crypto.py`:
```python
from app.services.market_data import get_market_data_service
# Same pattern
```

In `backend/app/routers/portfolio.py`:
```python
from app.services.market_data import get_market_data_service
# Replace: market_data = MarketDataService()
# With: market_data = get_market_data_service()
```

- [ ] **Step 3: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/market_data.py backend/app/routers/stocks.py backend/app/routers/crypto.py backend/app/routers/portfolio.py
git commit -m "refactor: share MarketDataService singleton for unified caching"
```

---

## Chunk 3: Frontend Updates

### Task 8: Verify frontend works with normalized API responses

**Files:**
- Verify: `frontend/src/hooks/useMarketData.ts` — already expects `price` field, should work now
- Verify: `frontend/src/hooks/usePortfolio.ts` — already unwraps `res.data.holdings`, enriched fields are optional in `Holding` type
- Verify: `frontend/src/components/HoldingsTable.tsx` — already handles `current_price`, `gain_loss`, `target_weight`, `actual_weight` with null checks

- [ ] **Step 1: Check that frontend types match**

The `Holding` interface in `frontend/src/types/index.ts` already has all optional fields:
```typescript
export interface Holding {
  symbol: string;
  asset_class_id: string;
  quantity: number;
  avg_price: number;
  total_cost: number;
  current_price?: number;   // ✓ populated by enriched endpoint
  current_value?: number;   // ✓ populated by enriched endpoint
  gain_loss?: number;       // ✓ populated by enriched endpoint
  target_weight?: number;   // ✓ populated by enriched endpoint
  actual_weight?: number;   // ✓ populated by enriched endpoint
}
```

No frontend changes needed — the types and components already handle these optional fields.

- [ ] **Step 2: Rebuild Docker and test end-to-end**

```bash
docker-compose down
docker-compose up --build -d
```

- [ ] **Step 3: Verify market search works**

Navigate to Market Search page, search for "AAPL" (stock) and "bitcoin" (crypto). Both should show price, name, market cap, and chart.

- [ ] **Step 4: Verify holdings show current prices**

Navigate to Portfolio page. Holdings table should now show:
- Current Price column with live prices
- Gain/Loss column with color-coded values
- Target Weight and Actual Weight columns with percentages

- [ ] **Step 5: Commit any fixes**

Only if needed based on e2e testing.

---

## Summary of Changes

| Problem | Root Cause | Fix |
|---------|-----------|-----|
| Market search blank/error | Backend returns `current_price`, frontend expects `price`. History returns `close`, frontend expects `price`. Crypto missing `name`. | Normalize field names in routers |
| Holdings show "-" for prices | `/portfolio/summary` only returns DB data, no market enrichment | Add `enrich_holdings` with parallel price fetching via ThreadPoolExecutor |
| Crypto prices wrong | `CRYPTO_CLASS_NAMES` missing `"Cryptos"` | Add to set |
| Duplicate API calls across features | Each router creates separate `MarketDataService` with own cache | Singleton pattern |

**Performance note:** First portfolio load with 46 assets will take ~5-10s (parallel fetch with 10 workers). Subsequent loads within cache TTL (5min stocks, 2min crypto) will be near-instant.
