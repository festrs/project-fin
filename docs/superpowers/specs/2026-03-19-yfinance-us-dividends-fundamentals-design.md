# YFinance Integration for US Stock Dividends & Fundamentals

**Date:** 2026-03-19
**Status:** Draft

## Goal

Replace Finnhub as the data source for US stock dividends and fundamentals with yfinance. Keep Finnhub only for real-time prices, search, history, and splits. This removes API key dependency and rate-limit pressure for dividend/fundamentals data, and unifies the dividend storage model across US and BR stocks.

## Decisions

- **Finnhub stays for:** `search()`, `get_quote()`, `get_history()`, `get_splits()`
- **yfinance replaces Finnhub for:** dividends (historical) and fundamentals (EPS, debt, profitability, IPO age)
- **US dividends stored in `dividend_history` table** — same as BR, with `dividend_type="Dividend"`
- **Unified dividend scheduler** handles both BR (DadosDeMercado) and US (yfinance) on the same schedule
- **Same 4 scoring dimensions** for fundamentals — only the data source changes
- **Small delay (1.0s) between yfinance calls** to avoid hammering Yahoo Finance

## Architecture

### New Provider: `providers/yfinance.py`

```python
class YFinanceProvider:
    def get_dividends(self, symbol: str) -> list[DividendRecord]
    def get_fundamentals(self, symbol: str) -> dict
```

**`get_dividends(symbol)`**
- Uses `yf.Ticker(symbol).dividends` for full dividend history
- Returns `list[DividendRecord]` — the `DividendRecord` dataclass is extracted from `providers/dados_de_mercado.py` to `providers/common.py` (shared between DadosDeMercado and YFinance providers). This ensures the scheduler's dedup code works unchanged (it uses attribute access: `rec.record_date`, `rec.value`, etc.)
- On error (network failure, missing ticker), returns empty list and logs warning (matches DadosDeMercado pattern)
- Each record: `DividendRecord(dividend_type="Dividend", value=amount, ex_date=date, record_date=date, payment_date=None)`
- yfinance index date = ex-dividend date; used as both `ex_date` and `record_date`
- `payment_date` is `None` (not available from yfinance)

**`get_fundamentals(symbol)`**
- Uses `yf.Ticker(symbol)` with `.info`, `.financials`, `.balance_sheet`
- Returns same dict shape as the old `FinnhubProvider.get_fundamentals()`:
  ```python
  {
      "ipo_years": int | None,
      "eps_history": list[float],
      "net_income_history": list[float],
      "debt_history": list[float],        # long_term_debt / ebitda ratio per year
      "current_net_debt_ebitda": float | None,
      "raw_data": list[dict],             # year-by-year breakdown
  }
  ```
- **IPO date:** fallback chain on `.info` keys: `firstTradeDateEpochUtc` → `firstTradeDate` (epoch seconds). Convert to years since IPO. If neither present, `ipo_years = None`.
- **Financial data from `.financials` (income statement) and `.balance_sheet`:**
  - EPS: row labels `"Diluted EPS"` → fallback `"Basic EPS"`
  - Net Income: row label `"Net Income"`
  - EBITDA: row label `"EBITDA"` → fallback `"Operating Income"`
  - Long Term Debt: row label `"Long Term Debt"` → fallback `"Total Debt"`
  - **Debt ratio:** `long_term_debt / ebitda` (matches current Finnhub behavior, which uses `LongTermDebt / EBITDA`, not true net debt)
- DataFrames have columns as dates (one per fiscal year), sorted chronologically
- On error (network failure, missing ticker), returns empty dict with `None`/empty-list values and logs warning (callers already handle missing data gracefully)

### Modified: `services/dividend_scraper_scheduler.py`

- **Rename class:** `DividendScraperScheduler` → `DividendScheduler`
- **Constructor:** `__init__(self, dados_provider, yfinance_provider, br_delay=2.0, us_delay=1.0)`
- **`scrape_all(db)`:** Queries all distinct stock symbols (BR + US, excluding crypto)
  - BR symbols → `dados_provider.scrape_dividends(symbol)`, delay `br_delay`
  - US symbols → `yfinance_provider.get_dividends(symbol)`, delay `us_delay`
- Same dedup logic: check `(symbol, record_date, dividend_type, value)` against DB before insert

### Modified: `services/fundamentals_scheduler.py`

- **Constructor:** `__init__(self, yfinance_provider, brapi_provider, dados_provider, delay=1.0)`
  - Replaces `finnhub_provider` with `yfinance_provider`
- **`_fetch_fundamentals(symbol, country)`:**
  - US → `yfinance_provider.get_fundamentals(symbol)` (was Finnhub)
  - BR → unchanged (Brapi → fallback to DadosDeMercado)
- Delay between US calls applies to yfinance now

### Modified: `routers/portfolio.py` — Dividends Endpoint

- **Remove:** `finnhub.get_dividend_metric()` call for US stocks
- **Remove:** `_div_cache` dict and `_DIV_CACHE_TTL` constant (no longer needed)
- **Remove:** `ThreadPoolExecutor` pattern — was justified for parallel external API calls, but now both US and BR read from DB
- **US stocks now query `dividend_history`** table, same as BR stocks
- **Simplify to single batch DB query:** query `dividend_history` for all stock symbols (BR + US) grouped by symbol. Replace the per-holding `fetch_dividend()` + executor pattern with a single query similar to the existing BR batch query (lines 134-146)
- **Filter column change:** Current BR query filters on `payment_date`. Since US dividends from yfinance have `payment_date=None`, the unified query must filter on `ex_date` instead (available for both BR and US records). Use `ex_date >= year_start AND ex_date <= year_end`.
- Both BR and US aggregated the same way — no country-specific branching for data source

### Modified: `routers/fundamentals.py` — Refresh Endpoints

- `_refresh_score()`: Use `YFinanceProvider` instead of `FinnhubProvider` for US symbols
- `refresh_all_scores()`: Instantiate `YFinanceProvider` instead of `FinnhubProvider`

### Modified: `providers/finnhub.py`

**Remove methods:**
- `get_dividend_metric()`
- `get_dividends_for_year()`
- `get_fundamentals()`

**Keep methods:**
- `search()`
- `get_quote()`
- `get_history()`
- `get_splits()`

### Modified: `main.py`

- `_run_dividend_scrape()`: Instantiate `YFinanceProvider`, pass to `DividendScheduler` alongside `DadosDeMercadoProvider`
- `_run_fundamentals_score()`: Instantiate `YFinanceProvider` instead of `FinnhubProvider`

### Modified: `config.py`

- Add: `dividend_us_delay: float = 1.0`

### Dependencies

- Add `yfinance` to `requirements.txt` / `pyproject.toml`

### New: `providers/common.py`

- Extract `DividendRecord` dataclass from `providers/dados_de_mercado.py` into shared module
- Both `dados_de_mercado.py` and `yfinance.py` import from here

### Modified: `providers/dados_de_mercado.py`

- Remove `DividendRecord` class definition, import from `providers/common.py` instead

## What Doesn't Change

- **`models/dividend_history.py`** — US dividends fit existing schema (`dividend_type="Dividend"`)
- **`services/fundamentals_scorer.py`** — pure scoring logic, data-source agnostic
- **`services/market_data.py`** — still uses Finnhub for prices (`get_quote`, `get_history`), Brapi for BR. Does not use any of the removed Finnhub methods.
- **`services/split_checker_scheduler.py`** — still uses Finnhub `get_splits()` for US splits (unchanged)
- **Frontend** — no API contract changes
- **Brapi / DadosDeMercado providers** — unchanged

## Testing

- **`tests/test_providers/test_yfinance.py`** — unit tests for `get_dividends()` and `get_fundamentals()` with mocked yfinance responses
- **Update `tests/test_services/test_dividend_scraper_scheduler.py`** — rename class references (`DividendScraperScheduler` → `DividendScheduler`), update to test both US and BR flow. Note: existing test asserts `"AAPL" not in scraped_symbols` — this must flip to assert US symbols ARE processed now.
- **Update `tests/test_services/test_fundamentals_scheduler.py`** (if exists) — swap Finnhub mock for yfinance mock
- No existing `tests/test_routers/test_portfolio.py` — dividend endpoint validation covered by scheduler + DB tests

## Data Flow (After)

```
Dividend Scheduler (Tue/Fri)
├── BR stocks → DadosDeMercado.scrape_dividends() → dividend_history table
└── US stocks → YFinanceProvider.get_dividends()   → dividend_history table

Fundamentals Scheduler (Sunday)
├── US stocks → YFinanceProvider.get_fundamentals() → score → fundamentals_scores table
└── BR stocks → Brapi / DadosDeMercado (unchanged) → score → fundamentals_scores table

Portfolio Dividends Endpoint
└── All stocks → query dividend_history table (unified)

Prices (unchanged)
├── US → Finnhub.get_quote()
└── BR → Brapi.get_quote()
```
