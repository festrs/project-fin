# Fundamentals Score

A per-stock scoring system that evaluates 4 fundamental criteria and produces a composite percentage score (0-100%). Visible in the HoldingsTable and on a dedicated analysis page with historical data.

## Scope

- US stocks (via Finnhub) and BR stocks (via Brapi, fallback to DadosDeMercado scraping)
- Excludes crypto, FIIs, REITs

## Scoring Criteria

Each criterion is rated green, yellow, or red.

| Criterion | Green (25%) | Yellow (15%) | Red (0%) |
|-----------|-------------|--------------|----------|
| IPO (Company Age) | +10 years as public company | 5-10 years | 0-5 years |
| EPS Growth | YoY EPS growth in >50% of years | 40-50% of years | <40% of years |
| Net Debt/EBITDA | Current ratio <3 AND ratio >3 in ≤30% of years | Only one condition met | Neither condition met |
| Profitability | Profit in all years or profit in past 15 consecutive years | Profit in ≥80% of years | Profit in <80% of years |

### Composite Score

Sum of individual criterion points. Range 0-100%.

- All green = 100%
- 3 green + 1 yellow = 90%
- All yellow = 60%
- All red = 0%

Score ≥90% indicates excellent fundamentals.

## Data Layer

### Data Sources

**US stocks — Finnhub:**
- IPO date: `/stock/profile2` endpoint (already called in `get_quote`, `ipo` field not currently extracted)
- EPS, net income, net debt/EBITDA: `/stock/metric?metric=all` (already called in `get_dividend_metric`, only dividend fields extracted) + `/stock/financials-reported` for annual financial statements

**BR stocks — Brapi (primary):**
- `fundamental=true` parameter on `/api/quote/{ticker}` (already used for dividends, may contain more data)

**BR stocks — DadosDeMercado (fallback):**
- Scrape financial data pages if Brapi does not provide sufficient EPS/debt/profit history

### New Provider Methods

- `FinnhubProvider.get_fundamentals(symbol) -> dict` — extracts IPO date, annual EPS history, net debt/EBITDA history, net income history
- `BrapiProvider.get_fundamentals(symbol) -> dict` — same shape, from Brapi fundamentals
- `DadosDeMercadoProvider.scrape_fundamentals(symbol) -> dict` — fallback scraper for BR stocks if Brapi data is insufficient

### New DB Model — `FundamentalsScore`

| Column | Type | Description |
|--------|------|-------------|
| `symbol` | String (PK) | Stock ticker |
| `ipo_years` | Integer | Years since IPO |
| `ipo_rating` | String | green/yellow/red |
| `eps_growth_pct` | Float | % of years with YoY EPS growth |
| `eps_rating` | String | green/yellow/red |
| `current_net_debt_ebitda` | Float | Current Net Debt/EBITDA ratio |
| `high_debt_years_pct` | Float | % of years with ratio >3 |
| `debt_rating` | String | green/yellow/red |
| `profitable_years_pct` | Float | % of years with positive net income |
| `profit_rating` | String | green/yellow/red |
| `composite_score` | Float | 0-100% composite score |
| `raw_data` | JSON | Yearly EPS, debt, profit values for charts |
| `updated_at` | DateTime | Last computation timestamp |

## Scoring Engine

`FundamentalsScorer` service that takes raw financial data and produces ratings.

Each criterion is implemented as a separate evaluator function following a common interface: `evaluate(data) -> (rating, points)`. This makes adding a 5th criterion straightforward.

The scorer orchestrates all evaluators, sums points, and returns the full score breakdown.

## Background Job

**`FundamentalsScoreScheduler`** — a new APScheduler job, separate from existing market data and dividend scraper jobs.

- Schedule: weekly (fundamentals change slowly)
- Iterates all US and BR stock symbols in the user's portfolio
- Fetches fundamentals from providers → runs scorer → upserts `FundamentalsScore` in DB
- Respects API rate limits (Finnhub: 60 calls/min)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/fundamentals/scores` | All scores for portfolio stocks (HoldingsTable) |
| `GET` | `/api/fundamentals/{symbol}` | Score + raw historical data (analysis page) |
| `POST` | `/api/fundamentals/{symbol}/refresh` | Manual recalculation trigger |

## Frontend

### HoldingsTable Changes

New column: composite score percentage with color coding.
- Green text: ≥90%
- Yellow text: 60-89%
- Red text: <60%

Clicking the score navigates to the analysis page for that stock.

### New Analysis Page (`/fundamentals`)

**Score breakdown card:**
- 4 criteria with traffic-light dots (green/yellow/red circles)
- Composite percentage score

**Historical data sections:**
- EPS Growth: bar chart — YoY EPS values, green bars for growth years, red for decline
- Net Debt/EBITDA: line chart over time with red threshold line at 3.0
- Profitability: bar chart — net income per year, green (profit) / red (loss) bars
- IPO info: company age and IPO date as text

### New Hook

`useFundamentals()` — fetches scores and raw data from the API endpoints.
