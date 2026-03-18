# Stock Split Tracking Design Spec

## Problem

When a stock split occurs (e.g., FAST 1:2 on 2025-05-22), the portfolio app continues showing pre-split quantities and average prices. This makes holdings data incorrect — the displayed quantity, average cost, and gain/loss are all wrong until manually corrected.

## Goals

- Automatically detect stock splits for held symbols via existing API providers
- Notify the user of pending splits via a dashboard banner
- Allow user to confirm or dismiss detected splits
- Correctly adjust holdings calculations for applied splits
- Preserve original transaction history untouched

## Non-Goals

- Reverse splits (can be added later with same mechanism)
- Split-adjusted historical price charts
- Automatic detection for symbols not currently held
- Full notifications system (banner is sufficient)

## Design Decision: Split-Aware Calculation vs Synthetic Transactions

The original plan was to create synthetic `split` transactions (type `"split"`, quantity = extra shares, value = $0). However, this approach has a **fundamental math problem when sells occur before a split:**

**Example:** Buy 200 shares @ $60 ($12,000). Sell 100 shares. Split 1:2.
- Pre-split net: 100 shares, cost basis $6,000, avg $60
- Post-split should be: 200 shares, cost basis $6,000, avg $30

With synthetic transaction (split adds 100 shares at $0):
- buy_qty = 200 + 100 = 300, buy_value = $12,000, sell_qty = 100
- avg_price = $12,000 / 300 = **$40** (WRONG, should be $30)
- total_cost = $40 * 200 = **$8,000** (WRONG, should be $6,000)

**Chosen approach: Split-aware holdings calculation.** Instead of synthetic transactions, store split records and make `get_holdings()` multiply all transaction quantities by cumulative split ratios. This is mathematically correct for all cases (sells before split, sells after split, multiple splits).

## Data Model

### New Table: `stock_split`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | String | FK to user (splits are per-user for apply/dismiss state) |
| symbol | String | Ticker symbol (e.g., `FAST`, `PETR4.SA`) |
| split_date | Date | Date the split took effect |
| from_factor | Float | Original share count (e.g., 1) |
| to_factor | Float | New share count (e.g., 2) |
| status | String | `pending`, `applied`, `dismissed` |
| detected_at | DateTime | When the scheduler found it |
| resolved_at | DateTime | When user confirmed/dismissed (nullable) |
| asset_class_id | UUID | FK to asset_class (to find related transactions) |

**Notes:**
- `from_factor` and `to_factor` are Float (not Integer) to handle fractional splits like 3:2
- `user_id` scoping ensures each user independently confirms/dismisses splits
- Unique constraint on `(user_id, symbol, split_date)` to prevent duplicate detection

### No Transaction Type Changes

The `Transaction` model, schema, and enum remain unchanged. No synthetic transactions are created. Holdings math is handled purely through the split-aware calculation.

### Holdings Calculation Changes

`get_holdings()` is modified to apply split adjustments to transaction quantities:

```python
def get_holdings(self, user_id: str) -> list[dict]:
    # For each symbol, get applied splits
    # For each transaction, compute adjusted_qty:
    #   adjusted_qty = original_qty * product(to_factor/from_factor for each split after tx.date)
    # Then:
    #   adjusted_buy_qty = sum of adjusted buy quantities
    #   adjusted_buy_value = sum of buy total_values (value doesn't change — you paid what you paid)
    #   adjusted_sell_qty = sum of adjusted sell quantities
    #   net_qty = adjusted_buy_qty - adjusted_sell_qty
    #   avg_price = adjusted_buy_value / adjusted_buy_qty
    #   total_cost = avg_price * net_qty
```

**Verification with the problematic scenario:**

Buy 200 @ $60 ($12,000). Sell 100. Split 1:2 on later date.

- Buy tx (before split): adjusted_qty = 200 * 2 = 400, value = $12,000
- Sell tx (before split): adjusted_qty = 100 * 2 = 200
- net_qty = 400 - 200 = **200** (correct)
- avg_price = $12,000 / 400 = **$30** (correct)
- total_cost = $30 * 200 = **$6,000** (correct)

**Simple case (no sells):**

Buy 100 @ $60. Split 1:2.
- adjusted_buy_qty = 100 * 2 = 200, value = $6,000
- avg_price = $6,000 / 200 = **$30** (correct)
- net_qty = **200** (correct)

**Sells after split:**

Buy 100 @ $60. Split 1:2. Sell 50 (post-split).
- Buy (before split): adjusted_qty = 100 * 2 = 200, value = $6,000
- Sell (after split): adjusted_qty = 50 * 1 = 50 (no splits after this tx)
- net_qty = 200 - 50 = **150** (correct)
- avg_price = $6,000 / 200 = **$30** (correct)
- total_cost = $30 * 150 = **$4,500** (correct)

## Detection: Split Checker Scheduler

### New Service: `SplitCheckerScheduler`

Runs as a separate APScheduler job (daily), following the existing scheduler pattern.

#### Finnhub (US Stocks)

New method on `FinnhubProvider`:
```python
def get_splits(self, symbol: str, from_date: str, to_date: str) -> list[dict]:
    """GET /stock/split?symbol={symbol}&from={from_date}&to={to_date}"""
    # Returns: [{"symbol": "FAST", "date": "2025-05-22", "fromFactor": 1, "toFactor": 2}]
```

#### Brapi (BR Stocks)

New method on `BrapiProvider`:
```python
def get_splits(self, symbol: str) -> list[dict]:
    """GET /api/quote/{symbol}?dividends=true, filter stockDividends for DESDOBRAMENTO"""
    # Response includes dividendsData.stockDividends array
    # Filter entries where label == "DESDOBRAMENTO"
    # Extract: factor (split ratio), approvedOn (date), lastDatePrior (effective date)
    # Returns normalized: [{"symbol": "PETR4.SA", "date": "2008-03-24", "fromFactor": 1, "toFactor": 2}]
```

**Note:** The exact Brapi response structure for `stockDividends` should be verified with a real API call during implementation, as documentation may differ from actual responses.

#### Scheduler Logic

1. Query all asset classes with type `stock` for the user
2. For each, get current holdings (symbols with positive quantity)
3. For each symbol, call the appropriate provider's `get_splits()`:
   - Finnhub for US stocks (no `.SA` suffix)
   - Brapi for BR stocks (`.SA` suffix)
4. For each split returned, check if a `stock_split` record already exists for that `(user_id, symbol, split_date)`
5. If not, insert a new `StockSplit` with status `pending`
6. **Error handling:** Catch exceptions per-symbol and continue processing remaining symbols. Log errors.
7. **Rate limiting:** Add a small delay (0.5s) between Finnhub API calls to stay well within the 60 calls/min free tier limit.

#### Configuration

New settings in `config.py`:
```python
enable_split_checker: bool = True
split_checker_hour: int = 10  # Run daily at 10:00 UTC
```

#### API Budget

- Finnhub: ~1 call per US stock holding per day. 20 holdings = 20 calls/day. Free tier allows 60/min.
- Brapi: Uses existing quote endpoint with `dividends=true`. Minimal additional calls.

## Backend API Endpoints

### GET `/api/splits/pending`

Returns all splits with status `pending` for the current user.

Response:
```json
[
  {
    "id": "uuid",
    "symbol": "FAST",
    "split_date": "2025-05-22",
    "from_factor": 1.0,
    "to_factor": 2.0,
    "detected_at": "2025-05-23T10:00:00Z",
    "current_quantity": 100.0,
    "new_quantity": 200.0
  }
]
```

The `current_quantity` and `new_quantity` are computed from current holdings to show the user what will change.

### POST `/api/splits/{split_id}/apply`

Confirms a pending split:
1. Verify `status == "pending"` — return 400 if already applied/dismissed (idempotency guard)
2. Update the `StockSplit` status to `applied`, set `resolved_at`
3. Holdings will automatically reflect the split on next calculation

### POST `/api/splits/{split_id}/dismiss`

Dismisses a pending split:
1. Verify `status == "pending"` — return 400 if already applied/dismissed
2. Update status to `dismissed`, set `resolved_at`

## Frontend

### Dashboard Banner

When there are pending splits, show a banner at the top of the Dashboard:

```
[!] Stock split detected: FAST (1:2 on May 22, 2025)
    Your 100 shares will become 200 shares. Average cost adjusts from $60.00 to $30.00.
    [Apply] [Dismiss]
```

- Multiple pending splits show as stacked banners or a list
- Banner disappears after user applies or dismisses
- Uses existing glass-morphism card styling

### Transaction List

No changes needed — splits don't create transactions. The transaction history shows only real buys, sells, and dividends.

## File Changes Summary

### New Files
- `backend/app/models/stock_split.py` — StockSplit SQLAlchemy model
- `backend/app/schemas/stock_split.py` — Pydantic schemas for split endpoints
- `backend/app/routers/splits.py` — API endpoints (pending, apply, dismiss)
- `backend/app/services/split_checker_scheduler.py` — Detection scheduler

### Modified Files
- `backend/app/models/__init__.py` — Register StockSplit model
- `backend/app/main.py` — Add split checker scheduler to lifespan, new config
- `backend/app/config.py` — Add `enable_split_checker`, `split_checker_hour` settings
- `backend/app/services/portfolio.py` — Make `get_holdings()` split-aware (query applied splits, adjust transaction quantities)
- `backend/app/providers/finnhub.py` — Add `get_splits()` method
- `backend/app/providers/brapi.py` — Add `get_splits()` method
- `frontend/src/types/index.ts` — Add `StockSplit` type
- `frontend/src/pages/Dashboard.tsx` — Add pending split banner
- `frontend/src/hooks/` — Add `useSplits` hook
- `frontend/src/services/api.ts` — Add split API calls

## Testing

### Backend
- Unit tests for `get_splits()` on both providers (mock API responses)
- Unit test for split checker scheduler (mock providers, verify StockSplit records created)
- Unit test for apply/dismiss endpoints (verify status changes, idempotency guard)
- **Unit tests for split-aware holdings calculation:**
  - Simple split (no sells): verify quantity doubles, avg_price halves
  - Split with pre-split sells: verify correct cost basis
  - Split with post-split sells: verify correct cost basis
  - Multiple splits on same symbol: verify cumulative adjustment
  - No splits: verify no regression to existing behavior

### Frontend
- Test pending split banner renders with mock data
- Test apply/dismiss button interactions
