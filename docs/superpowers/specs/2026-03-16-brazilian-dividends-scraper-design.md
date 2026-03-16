# Brazilian Dividends Scraper — Design Spec

## Summary

Scrape Brazilian stock dividend history from [dadosdemercado.com.br](https://www.dadosdemercado.com.br) and store it in a dedicated `DividendHistory` table. Runs as an independent APScheduler job, 2x/week (Tuesday and Friday at 6 UTC).

## Motivation

The current Brapi provider only returns ~12 months of dividend data. dadosdemercado.com.br has full history back to 2013+ with richer detail (type, record date, ex-date, payment date). Since the site's API requires CPF registration, we scrape the server-rendered HTML tables instead.

## Components

### 1. New Model: `DividendHistory`

Location: `backend/app/models/dividend_history.py`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| symbol | str | Indexed, e.g. `AGRO3.SA` |
| dividend_type | str | "Dividendo", "JCP" |
| value | float | BRL per share |
| record_date | date | |
| ex_date | date | |
| payment_date | date | |
| created_at | datetime | Auto-set |
| updated_at | datetime | Auto-set on update |

Unique constraint: `(symbol, record_date, dividend_type, value)` — prevents duplicate inserts.

### 2. New Provider: `DadosDeMercadoProvider`

Location: `backend/app/providers/dados_de_mercado.py`

- Uses `httpx` for HTTP requests (consistent with existing providers)
- Uses `beautifulsoup4` for HTML parsing
- URL pattern: `https://www.dadosdemercado.com.br/acoes/{ticker}/dividendos`
- Strips `.SA` suffix from symbol for URL construction
- Method: `scrape_dividends(symbol: str) -> list[DividendRecord]`
- Polite delay between requests (configurable, default 2s)

### 3. New Scheduler: `DividendScraperScheduler`

Location: `backend/app/services/dividend_scraper_scheduler.py`

- Independent APScheduler cron job (separate from quote fetching)
- Queries distinct BR symbols from `transactions` table
- For each symbol: scrape → upsert into `DividendHistory` → sleep
- Individual symbol failures are logged but don't block other symbols

### 4. Configuration Additions

Location: `backend/app/config.py`

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_dividend_scraper` | bool | `True` | Enable/disable the scraper |
| `dividend_scraper_days` | str | `"tue,fri"` | Days of week to run |
| `dividend_scraper_hour` | int | `6` | Hour (UTC) to run |
| `dividend_scraper_delay` | float | `2.0` | Delay between requests in seconds |

### 5. New Dependency

Add `beautifulsoup4` to `backend/requirements.txt`.

## Data Flow

```
APScheduler (tue,fri @ 6 UTC)
  → DividendScraperScheduler.scrape_all(db)
    → query distinct BR symbols from transactions table
    → for each symbol:
      → DadosDeMercadoProvider.scrape_dividends(symbol)
        → GET dadosdemercado.com.br/acoes/{ticker}/dividendos
        → parse HTML table → list[DividendRecord]
      → upsert into DividendHistory (skip duplicates)
      → sleep(2s)
```

## Integration Points

- Registered in `backend/app/main.py` lifespan alongside existing scheduler
- Shares the same pattern: BackgroundScheduler, cron trigger, configurable via env vars
- Queries BR symbols using same approach as `MarketDataScheduler` (distinct symbols from transactions where country="BR")

## Error Handling

- Individual symbol failures: logged, continue to next symbol
- HTTP errors (timeouts, 4xx/5xx): caught and logged per symbol
- HTML parse errors: caught and logged per symbol
- No retries — next scheduled run catches up

## Files to Create/Modify

**New files:**
- `backend/app/models/dividend_history.py`
- `backend/app/providers/dados_de_mercado.py`
- `backend/app/services/dividend_scraper_scheduler.py`
- `backend/tests/test_providers/test_dados_de_mercado.py`
- `backend/tests/test_services/test_dividend_scraper_scheduler.py`

**Modified files:**
- `backend/app/models/__init__.py` — export DividendHistory
- `backend/app/config.py` — add scraper settings
- `backend/app/main.py` — register scraper in lifespan
- `backend/requirements.txt` — add beautifulsoup4
