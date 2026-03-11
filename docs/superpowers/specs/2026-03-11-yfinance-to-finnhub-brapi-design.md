# Market Data Provider Migration: yfinance to Finnhub + brapi

## Problem

yfinance is scraping-based and unreliable. We need proper API-backed providers with clear rate limits and guarantees.

## Solution

Replace yfinance with two providers:
- **Finnhub** (free tier, 60 calls/min) for US stocks
- **brapi** (free tier) for BR stocks
- **CoinGecko** remains unchanged for crypto

Add a scheduled data pipeline that fetches quotes twice daily and stores them in the database, with API endpoints serving from DB instead of live calls.

## Architecture

### Provider Strategy Pattern

```
MarketDataService (facade)
  ├── FinnhubProvider (US stocks)
  ├── BrapiProvider (BR stocks)
  ├── CoinGecko (crypto, unchanged)
  ├── MarketDataScheduler (twice-daily fetch)
  └── market_quotes table (persistent storage)
```

### Provider Interface

```python
class MarketDataProvider(Protocol):
    def get_quote(self, symbol: str) -> dict:
        """Returns: {symbol, name, current_price, currency, market_cap}"""
        ...

    def get_history(self, symbol: str, period: str) -> list[dict]:
        """Returns: [{date, close, volume}, ...]"""
        ...
```

### Provider Routing

Two routing mechanisms depending on context:

1. **Stock API routes:** Country determined by URL path (`/api/stocks/us/...` vs `/api/stocks/br/...`)
2. **Portfolio/recommendation flows:** Country determined by `AssetClass.country` field, joined from transactions

Both resolve to: `country == "BR"` -> BrapiProvider, `country == "US"` -> FinnhubProvider.
Crypto routing unchanged (by asset class name).

## FinnhubProvider

**Endpoints used:**
- `GET /quote?symbol=X&token=KEY` -> current price (`c`), open (`o`), high (`h`), low (`l`), previous close (`pc`)
- `GET /stock/profile2?symbol=X&token=KEY` -> `name`, `currency`, `marketCapitalization`
- `GET /stock/candle?symbol=X&resolution=D&from=T1&to=T2&token=KEY` -> close prices (`c`), volumes (`v`), timestamps (`t`)

**Quote mapping:** Combines `/quote` + `/stock/profile2` (2 API calls per symbol).

**History period translation:**

| App period | Finnhub |
|---|---|
| "1mo" | from = now - 30 days, to = now |
| "3mo" | from = now - 90 days, to = now |
| "1y" | from = now - 365 days, to = now |

Candle endpoints use UNIX timestamps.

**Rate limit strategy:** Since each quote requires 2 calls, the scheduler must batch US stock fetches at ~25 symbols per minute (50 calls), leaving headroom for on-demand requests. Use a simple delay between batches (e.g., 1.5s per symbol).

## BrapiProvider

**Endpoints used:**
- `GET /api/quote/{symbol}?token=KEY` -> `shortName`, `regularMarketPrice`, `currency`, `marketCap`
- `GET /api/quote/{symbol}?range=1mo&interval=1d&token=KEY` -> candle data

**Symbol normalization:** Existing transaction data may store BR symbols with `.SA` suffix (e.g., `PETR4.SA`). BrapiProvider strips the `.SA` suffix before calling the API, since brapi expects bare tickers (e.g., `PETR4`).

**History period translation:** brapi uses the same period strings as yfinance (`1mo`, `3mo`, `1y`), so no conversion needed.

## Scheduled Data Pipeline

### MarketDataScheduler

- Runs inside the FastAPI app using APScheduler
- Triggers twice daily (configurable schedule)
- Also runs once on app startup to ensure fresh data
- Uses the FastAPI lifespan context manager (not deprecated `on_event`)

**Fetch flow:**
1. Query all distinct stock symbols from transactions, joined with asset_classes for country
2. Route each symbol to the correct provider based on country
3. Fetch quotes in batches, respecting rate limits (see Finnhub rate limit strategy above)
4. Upsert results into `market_quotes` table
5. Log failures per symbol; continue fetching remaining symbols on individual failures

**Failure handling:**
- If a scheduler run fails entirely, log an error. Stale data remains in `market_quotes` and continues to be served.
- If `market_quotes.updated_at` is older than 24 hours for a symbol, log a warning on read (but still serve the data).
- No automatic fallback to yfinance — if providers are down, stale data is served until next successful run.

### market_quotes Table

| Column | Type | Notes |
|---|---|---|
| symbol | String(20) | Primary key |
| name | String(200) | Company name |
| current_price | Float | Latest price |
| currency | String(3) | USD, BRL |
| market_cap | Float | Market capitalization |
| country | String(2) | US, BR |
| updated_at | DateTime | Last fetch time |

### Read Path

1. Check in-memory TTL cache (300s TTL for quotes, 900s for history — matching current behavior)
2. Read from `market_quotes` table
3. If symbol missing (new holding), live fetch from provider, store result, return

## Data Model Changes

### AssetClass: Add country column

```python
country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
```

Values: ISO 3166-1 alpha-2 (`"US"`, `"BR"`).

**Migration strategy:** Alembic migration adds column with default `"US"`. A data migration step updates asset classes whose name contains "BR" or "Brasil" or "Brazil" to `country="BR"`. Users with custom class names may need manual adjustment — the migration should log any classes it cannot auto-classify.

### Consolidate CRYPTO_COINGECKO_MAP

`CRYPTO_COINGECKO_MAP` and `CRYPTO_CLASS_NAMES` are currently duplicated in `portfolio.py` and `recommendation.py`. Move them to `market_data.py` as the single source of truth. Both callers import from there.

## API Route Changes

**Before:**
```
/api/stocks/{symbol}          -> yfinance
/api/stocks/{symbol}/history  -> yfinance
```

**After:**
```
/api/stocks/us/{symbol}          -> Finnhub (quote from DB)
/api/stocks/us/{symbol}/history  -> Finnhub (live call)
/api/stocks/br/{symbol}          -> brapi (quote from DB)
/api/stocks/br/{symbol}/history  -> brapi (live call)
/api/crypto/{coin_id}            -> CoinGecko (unchanged)
```

## MarketDataService Changes

The public interface gains a `country` parameter on stock methods (defaulting to `"US"` for backward compatibility during transition):

```python
class MarketDataService:
    def __init__(self):
        self._finnhub = FinnhubProvider(api_key=settings.finnhub_api_key)
        self._brapi = BrapiProvider(api_key=settings.brapi_api_key)
        self._scheduler = MarketDataScheduler(...)
        self._quote_cache = TTLCache(maxsize=256, ttl=300)   # DB read cache
        self._history_cache = TTLCache(maxsize=256, ttl=900)  # history cache

    def get_stock_quote(self, symbol: str, country: str = "US") -> dict:
        # 1. Check TTL cache
        # 2. Read from market_quotes table
        # 3. If missing, live fetch via provider, store, return

    def get_stock_history(self, symbol: str, period: str, country: str = "US") -> list[dict]:
        # 1. Check history cache
        # 2. Live call to provider (not stored in DB)

    def get_quote_safe(self, symbol_or_coin_id: str, is_crypto: bool, country: str = "US") -> float | None:
        # Updated to accept and pass country to get_stock_quote
        # Returns price or None on error (unchanged behavior)

    def _get_provider(self, country: str) -> MarketDataProvider:
        return self._brapi if country == "BR" else self._finnhub
```

### Impact on callers

- **Stock routes:** Country determined from URL path, passed directly
- **`portfolio.py` `enrich_holdings`:** Must join holdings with `AssetClass` to get `country`, pass it to `get_quote_safe`. The `enrich_holdings` function signature changes to accept country info per holding.
- **`recommendation.py` `_get_current_price`:** Must receive country from the asset class context and pass to `get_quote_safe`
- **Crypto callers:** Unaffected (is_crypto=True path unchanged)

## Configuration

New environment variables via pydantic-settings:
- `FINNHUB_API_KEY` (required)
- `BRAPI_API_KEY` (required)
- `MARKET_DATA_SCHEDULE` (optional, default: twice daily)

## File Changes

### New files
- `backend/app/providers/__init__.py`
- `backend/app/providers/base.py` — MarketDataProvider protocol
- `backend/app/providers/finnhub.py` — FinnhubProvider
- `backend/app/providers/brapi.py` — BrapiProvider
- `backend/app/services/market_data_scheduler.py` — APScheduler logic
- `backend/app/models/market_quote.py` — MarketQuote model
- Alembic migration for market_quotes table + country column on asset_classes

### Modified files
- `backend/app/services/market_data.py` — use providers + DB reads, consolidate CRYPTO maps here
- `backend/app/routers/stocks.py` — split into /us/ and /br/ routes
- `backend/app/config.py` — add API keys and scheduler settings
- `backend/app/main.py` — start/stop scheduler via lifespan context manager
- `backend/app/models/__init__.py` — register MarketQuote
- `backend/app/models/asset_class.py` — add country column
- `backend/app/services/portfolio.py` — thread country through enrich_holdings, import CRYPTO maps from market_data
- `backend/app/services/recommendation.py` — thread country through _get_current_price, import CRYPTO maps from market_data
- `backend/app/routers/portfolio.py` — pass DB session context for country lookups
- `backend/requirements.txt` — add APScheduler, remove yfinance

### Modified tests
- `backend/tests/test_services/test_market_data.py` — mock providers + DB instead of yfinance
- `backend/tests/test_routers/test_stocks.py` — update for new route structure
- `backend/tests/test_services/test_recommendation.py` — update for country parameter
- `backend/tests/test_portfolio_enriched.py` — update for country in enrichment flow
- `backend/tests/test_routers/test_portfolio.py` — update mocks
- `backend/tests/test_routers/test_recommendations.py` — update mocks
- New tests for FinnhubProvider, BrapiProvider, MarketDataScheduler

### Unchanged
- `backend/app/routers/crypto.py`
