# Stock Split Tracking Design Spec

## Problem

When a stock split occurs (e.g., FAST 1:2 on 2025-05-22), the portfolio app continues showing pre-split quantities and average prices. This makes holdings data incorrect — the displayed quantity, average cost, and gain/loss are all wrong until manually corrected.

## Goals

- Automatically detect stock splits for held symbols via existing API providers
- Notify the user of pending splits via a dashboard banner
- Allow user to confirm or dismiss detected splits
- Create synthetic `split` transactions that naturally correct holdings math
- Preserve original transaction history untouched

## Non-Goals

- Reverse splits (can be added later with same mechanism)
- Split-adjusted historical price charts
- Automatic detection for symbols not currently held
- Full notifications system (banner is sufficient)

## Data Model

### New Table: `stock_split`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| symbol | String | Ticker symbol (e.g., `FAST`, `PETR4.SA`) |
| split_date | Date | Date the split took effect |
| from_factor | Integer | Original share count (e.g., 1) |
| to_factor | Integer | New share count (e.g., 2) |
| status | String | `pending`, `applied`, `dismissed` |
| detected_at | DateTime | When the scheduler found it |
| resolved_at | DateTime | When user confirmed/dismissed (nullable) |
| asset_class_id | UUID | FK to asset_class (to find related transactions) |

### New Transaction Type: `split`

Extend the existing `type` field on `Transaction` to accept `"split"` in addition to `"buy"`, `"sell"`, `"dividend"`.

A split transaction has:
- `quantity` = extra shares gained (e.g., for 100 shares with 1:2 split, quantity = 100)
- `unit_price` = 0
- `total_value` = 0
- `notes` = auto-generated description (e.g., "Stock split 1:2 on 2025-05-22")
- `date` = split effective date

### Holdings Calculation Impact

No changes needed to `get_holdings()`. The existing logic:
- Sums all buy + split quantities → correct post-split total
- `avg_price = total_buy_value / total_buy_qty` → since split adds qty at $0 value, this isn't affected
- Wait — the split transaction is type `split`, not `buy`. Need to verify how `get_holdings()` filters.

**Correction:** `get_holdings()` currently filters by `type == "buy"` and `type == "sell"`. The split transaction type needs to be included in the buy-side query. Specifically:
- Buy-side query: `type IN ("buy", "split")` — sums quantity from both buys and splits
- Sell-side query: unchanged (`type == "sell"`)
- `avg_price = total_buy_value / total_buy_qty` — since split has `total_value = 0`, this correctly reduces the average price

Example: 100 shares bought at $60 ($6,000 total). After 1:2 split, split transaction adds 100 shares at $0.
- total_buy_qty = 100 + 100 = 200
- total_buy_value = $6,000 + $0 = $6,000
- avg_price = $6,000 / 200 = $30

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

Extend existing `BrapiProvider.get_quote()` or add new method:
```python
def get_splits(self, symbol: str) -> list[dict]:
    """GET /api/quote/{symbol}?dividends=true, filter stockDividends for DESDOBRAMENTO"""
    # Returns: [{"symbol": "PETR4.SA", "date": "2008-03-24", "fromFactor": 1, "toFactor": 2}]
```

#### Scheduler Logic

1. Query all asset classes with type `stock`
2. For each, get current holdings (symbols with positive quantity)
3. For each symbol, call the appropriate provider's `get_splits()`:
   - Finnhub for US stocks (no `.SA` suffix)
   - Brapi for BR stocks (`.SA` suffix)
4. For each split returned, check if a `stock_split` record already exists for that symbol + date
5. If not, insert a new `StockSplit` with status `pending`

#### Configuration

New settings in `config.py`:
```python
enable_split_checker: bool = True
split_checker_hour: int = 10  # Run daily at 10:00 UTC
```

#### API Budget

- Finnhub: ~1 call per US stock holding per day. 20 holdings = 20 calls/day. Free tier allows 60/min.
- Brapi: Uses existing quote endpoint with `dividends=true`. No additional API calls if we batch with existing quote fetches, or minimal extra calls if separate.

## Backend API Endpoints

### GET `/api/splits/pending`

Returns all splits with status `pending`.

Response:
```json
[
  {
    "id": "uuid",
    "symbol": "FAST",
    "split_date": "2025-05-22",
    "from_factor": 1,
    "to_factor": 2,
    "detected_at": "2025-05-23T10:00:00Z",
    "current_quantity": 100,
    "new_quantity": 200
  }
]
```

The `current_quantity` and `new_quantity` are computed from current holdings to show the user what will change.

### POST `/api/splits/{split_id}/apply`

Confirms a pending split:
1. Calculates extra shares: `current_qty * (to_factor / from_factor) - current_qty`
2. Creates a synthetic `split` transaction with that quantity
3. Updates the `StockSplit` status to `applied`, sets `resolved_at`

### POST `/api/splits/{split_id}/dismiss`

Dismisses a pending split:
1. Updates status to `dismissed`, sets `resolved_at`

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

Split transactions appear in the transaction history with:
- Type badge: "Split" (distinct color from Buy/Sell/Dividend)
- Quantity: "+100" (the extra shares)
- Value: "$0.00"
- Notes: "Stock split 1:2 on 2025-05-22"

## File Changes Summary

### New Files
- `backend/app/models/stock_split.py` — StockSplit SQLAlchemy model
- `backend/app/schemas/stock_split.py` — Pydantic schemas
- `backend/app/routers/splits.py` — API endpoints
- `backend/app/services/split_checker_scheduler.py` — Detection scheduler
- `backend/app/providers/finnhub.py` — Add `get_splits()` method
- `backend/app/providers/brapi.py` — Add `get_splits()` method

### Modified Files
- `backend/app/models/__init__.py` — Register StockSplit model
- `backend/app/main.py` — Add split checker scheduler to lifespan
- `backend/app/config.py` — Add split checker settings
- `backend/app/services/portfolio.py` — Include `split` type in buy-side query
- `backend/app/schemas/transaction.py` — Allow `"split"` in type enum
- `frontend/src/types/index.ts` — Add StockSplit type, update Transaction type
- `frontend/src/pages/Dashboard.tsx` — Add pending split banner
- `frontend/src/hooks/` — Add `useSplits` hook
- `frontend/src/services/api.ts` — Add split API calls

## Testing

### Backend
- Unit tests for `get_splits()` on both providers (mock API responses)
- Unit test for split checker scheduler (mock providers, verify StockSplit records created)
- Unit test for apply/dismiss endpoints (verify transaction created, status updated)
- Integration test: full flow from detection to application, verify holdings recalculation

### Frontend
- Test pending split banner renders with mock data
- Test apply/dismiss button interactions
- Test split transaction displays correctly in transaction list
