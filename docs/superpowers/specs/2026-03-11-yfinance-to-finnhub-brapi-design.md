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
MarketDataService (facade, unchanged public interface)
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

Routing is determined by the `country` field on `AssetClass`:
- `country == "BR"` -> BrapiProvider
- `country == "US"` -> FinnhubProvider
- Crypto routing unchanged (by asset class name)

## FinnhubProvider

**Endpoints used:**
- `GET /quote?symbol=X&token=KEY` -> current price (`c`), open (`o`), high (`h`), low (`l`), previous close (`pc`)
- `GET /stock/profile2?symbol=X&token=KEY` -> `name`, `currency`, `marketCapitalization`
- `GET /stock/candle?symbol=X&resolution=D&from=T1&to=T2&token=KEY` -> close prices (`c`), volumes (`v`), timestamps (`t`)

**Quote mapping:** Combines `/quote` + `/stock/profile2` (2 API calls).

**History period translation:**

| App period | Finnhub |
|---|---|
| "1mo" | from = now - 30 days, to = now |
| "3mo" | from = now - 90 days, to = now |
| "1y" | from = now - 365 days, to = now |

Candle endpoints use UNIX timestamps.

## BrapiProvider

**Endpoints used:**
- `GET /api/quote/{symbol}?token=KEY` -> `shortName`, `regularMarketPrice`, `currency`, `marketCap`
- `GET /api/quote/{symbol}?range=1mo&interval=1d&token=KEY` -> candle data

**History period translation:** brapi uses the same period strings as yfinance (`1mo`, `3mo`, `1y`), so no conversion needed.

## Scheduled Data Pipeline

### MarketDataScheduler

- Runs inside the FastAPI app using APScheduler
- Triggers twice daily (configurable schedule)
- Also runs once on app startup to ensure fresh data

**Fetch flow:**
1. Query all distinct stock symbols from transactions, joined with asset_classes for country
2. Route each symbol to the correct provider based on country
3. Fetch quotes in batches (respecting rate limits)
4. Upsert results into `market_quotes` table

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

1. Check in-memory TTL cache (60s TTL, avoids repeated DB hits)
2. Read from `market_quotes` table
3. If symbol missing (new holding), live fetch from provider, store result, return

## Data Model Changes

### AssetClass: Add country column

```python
country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
```

Values: ISO 3166-1 alpha-2 (`"US"`, `"BR"`).

Migration: Alembic migration adds column with default `"US"`. Existing BR asset classes updated via data migration.

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

Public interface stays the same. Internal changes:

```python
class MarketDataService:
    def __init__(self):
        self._finnhub = FinnhubProvider(api_key=settings.finnhub_api_key)
        self._brapi = BrapiProvider(api_key=settings.brapi_api_key)
        self._scheduler = MarketDataScheduler(...)
        self._quote_cache = TTLCache(maxsize=256, ttl=60)

    def get_stock_quote(self, symbol: str, country: str = "US") -> dict:
        # 1. Check TTL cache
        # 2. Read from market_quotes table
        # 3. If missing, live fetch via provider, store, return

    def get_stock_history(self, symbol: str, period: str, country: str = "US") -> list[dict]:
        # Live call to provider (not stored in DB)

    def _get_provider(self, country: str) -> MarketDataProvider:
        return self._brapi if country == "BR" else self._finnhub
```

Callers with asset class context (portfolio enrichment, recommendations) pass country. Stock routes determine country from the URL path.

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
- Alembic migration for market_quotes table + country column

### Modified files
- `backend/app/services/market_data.py` — use providers + DB reads
- `backend/app/routers/stocks.py` — split into /us/ and /br/ routes
- `backend/app/config.py` — add API keys and scheduler settings
- `backend/app/main.py` — start/stop scheduler on app lifecycle
- `backend/app/models/__init__.py` — register MarketQuote
- `backend/app/models/asset_class.py` — add country column
- `backend/requirements.txt` — add APScheduler, remove yfinance

### Modified tests
- `backend/tests/test_services/test_market_data.py` — mock providers + DB
- `backend/tests/test_routers/test_stocks.py` — update for new routes
- New tests for FinnhubProvider, BrapiProvider, MarketDataScheduler

### Unchanged
- `backend/app/routers/crypto.py`
- `backend/app/routers/portfolio.py` (minor update to pass country)
- `backend/app/services/portfolio.py` (minor update to pass country)
- `backend/app/services/recommendation.py` (minor update to pass country)
