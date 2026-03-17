# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Portfolio management SPA for tracking stocks (US/BR), crypto, with fundamentals analysis, dividend tracking, rebalancing recommendations, and trading quarantine rules.

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy + SQLite (Python 3.12)
- **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS + Recharts
- **External APIs:** Finnhub (US stocks), Brapi (BR stocks), DadosDeMercado (BR dividends via scraping)
- **Background Jobs:** APScheduler for market data, dividends, and fundamentals scoring

## Commands

### Backend

```bash
cd backend
python -m uvicorn app.main:app --reload          # Dev server on :8000
pytest                                             # Run all tests
pytest tests/test_routers/test_portfolio.py        # Single test file
pytest -k "test_name"                              # Single test by name
```

Requires `FINNHUB_API_KEY` and `BRAPI_API_KEY` in `backend/.env`.

### Frontend

```bash
cd frontend
npm run dev       # Vite dev server on :5173, proxies /api to localhost:8000
npm run build     # TypeScript check + Vite build to dist/
npm run lint      # ESLint
npm run test      # Vitest with happy-dom
```

### Docker

```bash
docker-compose up   # Backend on :8000, frontend on :3000 (nginx)
```

## Architecture

### Backend (`backend/app/`)

- **Routers** (`routers/`) — FastAPI endpoints. Rate-limited via SlowAPI.
- **Services** (`services/`) — Business logic. `market_data.py` is a singleton with TTL caching (5min quotes, 15min history). `fundamentals_scorer.py` has pure scoring functions.
- **Providers** (`providers/`) — External API abstraction: `finnhub.py` for US stocks, `brapi.py` for BR stocks, `dados_de_mercado.py` for BR dividend scraping.
- **Models** (`models/`) — SQLAlchemy ORM. All use UUIDs as primary keys.
- **Schemas** (`schemas/`) — Pydantic request/response models.
- **Schedulers** (`services/*_scheduler.py`) — APScheduler jobs configured in `main.py` lifespan. Timing controlled via `config.py` settings.

Database tables are auto-created on startup via `Base.metadata.create_all()`. Seeding runs on startup via `seed_data()`.

### Frontend (`frontend/src/`)

- **Pages** (`pages/`) — Route-level components: Dashboard, Portfolio, Fundamentals, Market, Settings.
- **Hooks** (`hooks/`) — Custom hooks encapsulate all API calls and state management (one hook per domain).
- **Components** (`components/`) — Reusable UI: tables, charts, forms, cards.
- **Services** (`services/api.ts`) — Single Axios instance with `/api` base URL and default `X-User-Id` header.
- **Types** (`types/index.ts`) — All TypeScript interfaces for API contracts.

### Data Flow

Frontend hooks → Axios (`/api/*`) → FastAPI routers → Services → DB or Providers → Response

### Key Patterns

- **Provider pattern:** External APIs abstracted behind provider classes; BR stocks use `.SA` suffix convention.
- **Singleton service:** `get_market_data_service()` returns a cached instance.
- **Dependency injection:** FastAPI `Depends()` for DB sessions and services.
- **Glass-morphism UI:** Custom Tailwind theme with CSS variables defined in `index.css`.

## Testing

- **Backend:** pytest + pytest-asyncio. Tests in `backend/tests/` with subdirs for routers, providers, models, services, and e2e. Uses separate `test.db`.
- **Frontend:** Vitest + @testing-library/react with happy-dom environment. Setup in `src/test/setup.ts`.

## Configuration

All backend settings in `backend/app/config.py` (Pydantic BaseSettings, reads from `.env`):
- `enable_scheduler`, `scheduler_hours` — Market data fetch timing
- `enable_dividend_scraper`, `dividend_scraper_days` — Dividend scraping schedule
- `enable_fundamentals_scorer`, `fundamentals_scorer_day` — Fundamentals scoring schedule
- `database_url` — Defaults to SQLite
- `cors_origin` — Defaults to `http://localhost:5173`
