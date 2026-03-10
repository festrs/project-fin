# Project Fin — Design Document

## Overview

Personal financial dashboard web application for tracking investments across US stocks, BR stocks, and crypto (Bitcoin + stablecoins). Features portfolio management, an investment ledger, target weight-based rebalancing recommendations, and a quarantine system to prevent over-investing in single assets.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy + SQLite |
| Frontend | React 18 + TypeScript + Vite + Recharts + TailwindCSS |
| Market Data (Stocks) | yfinance (US + BR stocks) |
| Market Data (Crypto) | CoinGecko free API |
| Hosting | Render (Web Service + Static Site) |

## Architecture

Monorepo with separate backend and frontend builds.

```
project-fin/
├── backend/          # FastAPI API server
├── frontend/         # React SPA (Vite)
├── docker-compose.yml
└── README.md
```

- Backend serves API only (`/api/*`)
- Frontend is a Vite React app, deployed as Render Static Site
- On Render: 1 Web Service (backend) + 1 Static Site (frontend)

## Data Model

### User

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| name | string | |
| email | string | unique |
| created_at | datetime | |
| updated_at | datetime | |

### AssetClass

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → User |
| name | string | e.g., "US Stocks", "BR Stocks", "Crypto", "Stablecoins" |
| target_weight | float | Macro weight, defaults to 100/N (equal) |
| created_at | datetime | |
| updated_at | datetime | |

### AssetWeight

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| asset_class_id | UUID | FK → AssetClass |
| symbol | string | e.g., "AAPL", "PETR4.SA", "BTC-USD" |
| target_weight | float | Weight within class, defaults to 100/N (equal) |
| created_at | datetime | |
| updated_at | datetime | |

### Transaction

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → User |
| asset_class_id | UUID | FK → AssetClass |
| asset_symbol | string | Matches AssetWeight.symbol |
| type | enum | buy / sell / dividend |
| quantity | float | 0 for dividends |
| unit_price | float | 0 for dividends |
| total_value | float | Total cost/received/dividend amount |
| currency | enum | BRL / USD (auto-set by market) |
| tax_amount | float | Manual input |
| date | date | Transaction date |
| notes | string | Optional |
| created_at | datetime | |
| updated_at | datetime | |

### QuarantineConfig

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → User |
| threshold | int | Default 2 (buys before quarantine triggers) |
| period_days | int | Default 180 (6 months) |
| created_at | datetime | |
| updated_at | datetime | |

### QuarantineStatus (computed, not stored)

Calculated on the fly from transactions:
- `asset_symbol`: the asset
- `buy_count_in_period`: number of buys within the rolling period window
- `is_quarantined`: true if buy_count >= threshold
- `quarantine_ends_at`: date of Nth buy + period_days

## Weight & Recommendation System

Two-level weight system:
1. **Macro level**: `AssetClass.target_weight` — e.g., US Stocks 40%, BR Stocks 30%, Crypto 30%
2. **Asset level**: `AssetWeight.target_weight` — e.g., AAPL 50% of US Stocks

**Effective target per asset** = `class_weight × asset_weight`

**Recommendation engine:**
1. Calculate effective target weight for each asset
2. Calculate actual weight from portfolio holdings (current market value)
3. Compute diff (target - actual) for each asset
4. Exclude quarantined assets (soft block)
5. Return top N most underweight assets (default N=2)

All weights default to equal distribution. User can customize via inline editing on Portfolio page.

## API Design

### Market Data
```
GET  /api/stocks/{symbol}          # Price, info (yfinance)
GET  /api/stocks/{symbol}/history  # Historical prices (yfinance)
GET  /api/crypto/{symbol}          # Price, info (CoinGecko)
GET  /api/crypto/{symbol}/history  # Historical prices (CoinGecko)
```

### Asset Classes & Weights
```
GET    /api/asset-classes              # List all classes + weights
POST   /api/asset-classes              # Create class
PUT    /api/asset-classes/{id}         # Update class (name, target_weight)
DELETE /api/asset-classes/{id}         # Remove class
GET    /api/asset-classes/{id}/assets  # List assets in class
POST   /api/asset-classes/{id}/assets  # Add asset to class
PUT    /api/asset-weights/{id}         # Update asset target_weight
DELETE /api/asset-weights/{id}         # Remove asset from class
```

### Transactions (Ledger)
```
GET    /api/transactions               # List all (filterable by type, symbol, date range)
POST   /api/transactions               # Record buy/sell/dividend
PUT    /api/transactions/{id}          # Edit transaction
DELETE /api/transactions/{id}          # Delete transaction
```

### Portfolio
```
GET    /api/portfolio/summary          # Current holdings, values, allocation %
GET    /api/portfolio/performance      # Portfolio value over time (chart data)
GET    /api/portfolio/allocation       # Target vs actual weights (chart data)
```

### Recommendations
```
GET    /api/recommendations            # Top N underweight assets (default N=2)
GET    /api/recommendations?count=3    # Custom N
```

### Quarantine
```
GET    /api/quarantine/status          # All assets quarantine status
GET    /api/quarantine/config          # Current config
PUT    /api/quarantine/config          # Update threshold + period
```

### Rate Limits
- Market data endpoints: 30 req/min
- CRUD endpoints: 60 req/min
- Response headers: X-RateLimit-Limit, X-RateLimit-Remaining

## Security

- CORS configured to allow only the frontend origin
- Input validation via Pydantic schemas on all endpoints
- SQL injection prevention via SQLAlchemy ORM (no raw queries)
- Rate limiting via `slowapi` middleware
- User-scoped queries (all data filtered by user_id)

## Frontend Pages

### Dashboard (/)
- Portfolio performance line chart (value over time)
- Target vs actual allocation bar chart
- Recommendation card (top N assets to invest)

### Portfolio (/portfolio)
- **Asset Classes table**: class name, target weight (editable inline), actual weight, diff. Add/remove class.
- **Holdings table** (per class, expandable/tabbed): symbol, qty, avg price, current price, gain/loss, target weight (editable inline), actual weight, diff. Quarantine badge on quarantined assets. Add asset button. Buy/Sell buttons per asset. Expand row → transaction history for that asset.
- **Dividends table**: symbol, date, amount, currency, tax, notes. Filterable by asset/date range. Add dividend button.
- **Portfolio composition donut chart** (by class + by asset)

### Settings (/settings)
- Quarantine config (threshold + period)
- Recommendation count (default 2)

### Market (/market)
- Search & view stock/crypto prices and info

## Caching Strategy

| Data | TTL | Implementation |
|---|---|---|
| Stock quotes | 5 min | cachetools TTLCache |
| Historical data | 15 min | cachetools TTLCache |
| Crypto prices | 2 min | cachetools TTLCache |

No Redis needed for single-user. In-memory cache is sufficient.

## External API Protection

- yfinance: batch requests when possible, cache aggressively
- CoinGecko: respect 30 req/min free tier limit

## Testing Strategy (TDD)

### Backend (pytest)
- **Unit tests**: recommendation engine (weight calculations, quarantine logic), portfolio service (allocation math, performance), model validation
- **Integration tests**: API endpoint behavior, database transaction CRUD and queries
- **Fixtures**: SQLite in-memory test DB, mocked yfinance/CoinGecko responses

### Frontend (Vitest + React Testing Library)
- **Component tests**: tables (render, inline edit, filtering), charts (render with mock data), forms (validation, submission)
- **Hook tests**: API hooks with mocked axios responses

## Deployment (Render)

| Service | Type | Tier |
|---|---|---|
| Backend | Web Service (Dockerfile) | Free (sleeps after 15 min) |
| Frontend | Static Site (Vite build) | Free (no sleep) |

Environment variables:
- `DATABASE_URL` (SQLite path)
- `CORS_ORIGIN` (frontend URL)
- `COINGECKO_API_URL`
