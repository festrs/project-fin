# Project Fin

Portfolio management SPA for tracking stocks (US/BR), crypto, with fundamentals analysis, dividend tracking, rebalancing recommendations, and trading quarantine rules.

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy + SQLite (Python 3.12)
- **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS + Recharts
- **External APIs:** Finnhub (US stocks), Brapi (BR stocks), DadosDeMercado (BR dividends)
- **Background Jobs:** APScheduler for market data, dividends, and fundamentals scoring

## Quick Start

### Backend

```bash
cd backend
cp .env.example .env  # Add FINNHUB_API_KEY and BRAPI_API_KEY
python -m uvicorn app.main:app --reload  # Dev server on :8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev  # Vite dev server on :5173, proxies /api to localhost:8000
```

### Docker

```bash
docker-compose up  # Backend on :8000, frontend on :3000 (nginx)
```

## Testing

```bash
cd backend && pytest           # Backend tests
cd frontend && npm run test    # Frontend tests
```
