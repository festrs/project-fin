# Portfolio Improvements — Design Spec

**Date:** 2026-04-10
**Scope:** Four features — Portfolio Performance Chart, Market Overview Page, Asset Detail Page, Tax Report (DARF)
**Build order:** A1 → C1 → A2 → D2

---

## Feature 1: Portfolio Performance Chart (A1)

### Goal

Replace the placeholder hero card chart with real portfolio value history. Daily snapshots power 1W/1M/1Y/ALL line charts. 1D shows today's change as a number (no intraday chart).

### Backend

**New model — `PortfolioSnapshot`:**
- `id` (UUID PK), `user_id` (FK → User), `date` (Date), `total_value_brl` (Numeric 19,8), `created_at`
- Unique constraint on `(user_id, date)`

**New scheduler — `PortfolioSnapshotScheduler`:**
- Runs once daily, configurable hour (default 18:00 UTC — after BR and US market close)
- For each user: calls `PortfolioService.get_holdings()`, enriches with current prices, sums total BRL value, inserts snapshot
- Skips if today's snapshot already exists for that user

**New endpoint — `GET /api/portfolio/history?period=1W|1M|1Y|ALL`:**
- Returns `[{ date, total_value_brl }]` filtered by period
- 1W = last 7 days, 1M = last 30, 1Y = last 365, ALL = all snapshots

**New endpoint — `GET /api/portfolio/snapshot/latest`:**
- Returns yesterday's closing snapshot for 1D delta calculation

### Frontend

**PortfolioHeroCard changes:**
- Enable all period tabs (1D, 1W, 1M, 1Y, ALL)
- 1D tab: display `current_value - yesterday_snapshot` as number with percentage, no chart
- 1W/1M/1Y/ALL tabs: fetch `/api/portfolio/history?period=X`, render as Recharts `AreaChart` with gradient fill
- Chart line color: green if period gain positive, red if negative
- Tooltip on hover showing date + value

**New hook — `usePortfolioHistory(period)`:**
- Fetches `/api/portfolio/history?period=X`
- Caches per period
- Fetches latest snapshot for 1D delta

---

## Feature 2: Market Overview Page (C1)

### Goal

Replace the "coming soon" Market page with index tickers, portfolio top movers, and news feed.

### Backend

**New endpoint — `GET /api/market/indices`:**
- Returns current values for IBOV, S&P500, USD/BRL
- IBOV via Brapi (`^BVSP` or equivalent), S&P500 via Finnhub (SPY as proxy), USD/BRL via existing exchange rate logic
- Each entry: `{ symbol, name, value, change_pct }`
- 5min TTL cache (same as quotes)

**New endpoint — `GET /api/market/movers`:**
- Fetches live prices for user's current holdings, computes daily change %
- Returns top 3 gainers + top 3 losers: `{ symbol, name, change_pct, current_price }`
- Reuses `PortfolioService.get_holdings()` + `MarketDataService`

### Frontend

**Market page — three sections:**
1. **Index cards** — row of 3 cards (IBOV, S&P500, USD/BRL) with value + change %
2. **Top Movers** — split into Gainers and Losers, 3 each, symbol + change %
3. **News Feed** — reuse `NewsCard` component, full list (no limit)

**New hooks:**
- `useMarketIndices()` — fetches `/api/market/indices`, 5min cache
- `useMarketMovers()` — fetches `/api/market/movers`, same cache pattern

**Dashboard:** Keep existing `NewsCard` as-is (compact, max 4 items). Market page shows the full feed.

---

## Feature 3: Asset Detail Page (A2)

### Goal

Dedicated page for viewing a single holding with price chart, stats, transactions, dividends, and fundamentals.

### Backend

No new endpoints. All data available from existing APIs:
- Price history: `GET /api/stocks/{country}/{symbol}/history` or `GET /api/crypto/{coin_id}/history`
- Holding data: from `GET /api/portfolio/summary`
- Transactions: `GET /api/transactions?symbol=X`
- Dividends: `GET /api/dividends/history?asset_class_id=X`
- Fundamentals: `GET /api/fundamentals/{symbol}`

### Frontend

**New route — `/portfolio/:assetClassId/:symbol`**

**Page layout (top to bottom):**
1. **Header bar** — back arrow to holdings page, symbol + company name, current price + daily change %
2. **Price chart** — Recharts `AreaChart` with period selector (1W/1M/3M/1Y/ALL). Green/red gradient based on period performance. Same style as portfolio hero chart.
3. **Key stats row** — 4 stat cards: quantity held, avg cost, total gain/loss (value + %), fundamentals score (colored badge)
4. **Transactions list** — chronological buy/sell/dividend transactions for this symbol. Reuse `TransactionHistoryModal` content rendered inline.
5. **Dividend history** — if applicable, dividend payments list. Reuse `DividendHistoryModal` content inline.

**New hook — `useAssetDetail(symbol, country, assetClassId)`:**
- Parallel fetches: price history, holding info (from cached portfolio), transactions, dividends, fundamentals
- Period state for chart (default 1M)

**Navigation change:**
- Clicking a holding row in `HoldingsTable` navigates to this page instead of opening the transaction form modal
- Buy/Sell action moves to the asset detail page (header button or floating action)

---

## Feature 4: Tax Report — DARF (D2)

### Goal

Monthly capital gains summary for BR stocks and FIIs, showing exempt vs taxable gains and DARF amount due.

### Backend

**New service — `TaxService`:**

`get_monthly_report(user_id, year)`:
1. Find all **sell** transactions in that year, grouped by month
2. Group by asset type (stocks vs FIIs)
3. For each sell: compute gain = `(sell_price - avg_cost) * quantity` using average cost basis method (weighted average from all prior buys)
4. **Stocks**: if total monthly sell volume < R$20k, gains are exempt. If >= R$20k, tax = 15% of net gain
5. **FIIs**: no exemption. Tax = 20% of net gain always
6. Subtract IRRF already withheld (from `transaction.tax_amount`)
7. Return monthly summaries

**Tax rules:**
- Average cost basis: weighted average of all prior buy transactions
- R$20k/month exemption: applies to total sell volume of common stocks only (not FIIs)
- Stock swing trade rate: 15%
- FII rate: 20%
- Day trade: NOT in scope

**New endpoint — `GET /api/tax/report?year=2026`:**
- Returns `[{ month, stocks: { total_sales, total_gain, exempt, tax_due }, fiis: { total_sales, total_gain, tax_due }, total_tax_due }]`
- Defaults to current year

### Frontend

**New route — `/tax`**

**Page layout:**
1. **Header** — "Tax Report (DARF)" + year selector dropdown
2. **Year summary cards** — total gains, total tax due, months with DARF obligation (count)
3. **Monthly table** — one row per month: stocks sales/gain/exempt/tax, FIIs sales/gain/tax, total DARF due (red when > 0)
4. **Empty state** — "No sell transactions in {year}"

**New hook — `useTaxReport(year)`:**
- Fetches `/api/tax/report?year=X`
- Year state defaults to current year

**Navigation:** Add "Tax" tab to TopNav and MobileNav.

---

## Implementation Order

1. **A1 — Portfolio Performance Chart**: new model, scheduler, endpoint, hero card upgrade
2. **C1 — Market Overview Page**: new endpoints for indices/movers, full Market page build
3. **A2 — Asset Detail Page**: frontend-only, new route composing existing APIs
4. **D2 — Tax Report (DARF)**: new service with tax logic, endpoint, new page + nav entry
