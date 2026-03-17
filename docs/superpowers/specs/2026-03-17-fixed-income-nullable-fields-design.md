# Fixed Income: Nullable Transaction Fields

## Problem

Fixed income assets (CDBs, LCIs, Tesouro Direto, etc.) only need total value and date — they have no meaningful quantity, unit price, or tax per transaction. Currently all three fields are required (NOT NULL) on the Transaction model, forcing artificial values.

## Solution

Make `quantity`, `unit_price`, and `tax_amount` nullable across the stack. Fixed income transactions store `None` for these fields and only provide `total_value`, `date`, and `currency`. The portfolio service branches on whether a holding has quantity-based or value-based transactions.

## Identifying Fixed Income

Use the asset class name to detect fixed income. Check with case-insensitive `includes`/`in` matching against known terms: `"renda fixa"`, `"fixed income"`. This handles names like "Renda Fixa BR" or "Fixed Income - CDB". The frontend `TransactionForm` and `AddAssetForm` perform this check on the asset class name. No new columns on `AssetClass`.

## Database Migration

The project uses `Base.metadata.create_all()` which only creates tables that don't exist — it won't alter existing columns. Since this is a dev/personal project using SQLite, the migration approach is: delete the existing `portfolio.db` file and let it be recreated on next startup. Seed data will repopulate. If preserving data is needed, use a one-off script to recreate the table with the new schema and copy data.

## Backend: Model Changes

**`backend/app/models/transaction.py`**

```python
quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
tax_amount: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
```

All three fields become nullable. Existing transactions retain their values. New fixed income transactions store `None`. `total_value` remains required (NOT NULL) — it is the single source of truth for fixed income.

## Backend: Schema Changes

**`backend/app/schemas/transaction.py`**

`TransactionCreate`:
- `quantity: Optional[float] = None`
- `unit_price: Optional[float] = None`
- `tax_amount: Optional[float] = None`

Add a `model_validator` to enforce consistency: either all three of `quantity`, `unit_price`, `tax_amount` are provided (stock/crypto), or all three are `None` (fixed income). Reject mixed states.

```python
@model_validator(mode="after")
def validate_field_consistency(self):
    fields = [self.quantity, self.unit_price]
    all_set = all(f is not None for f in fields)
    none_set = all(f is None for f in fields)
    if not (all_set or none_set):
        raise ValueError("quantity and unit_price must be all provided or all None")
    return self
```

`TransactionResponse`:
- `quantity: float | None`
- `unit_price: float | None`
- `tax_amount: float | None`

`TransactionUpdate` — already `Optional`, no structural change. Note: cross-type updates (setting quantity on a fixed income tx) are allowed — validation is on create only.

## Backend: Portfolio Service Changes

**`backend/app/services/portfolio.py` — `get_holdings()`**

The current code does `buy_qty = buy_agg.total_qty or 0` which masks `None` as `0`. This must change to branch before the fallback:

```python
buy_qty = buy_agg.total_qty  # Do NOT default to 0

if buy_qty is None:
    # Value-based (fixed income): sum total_value only
    buy_value = buy_agg.total_value or 0
    sell_value_agg = (
        self.db.query(func.sum(Transaction.total_value))
        .filter(..., Transaction.type == "sell")
        .scalar()
    ) or 0
    net_value = buy_value - sell_value_agg
    if net_value <= 0:
        continue
    holdings.append({
        "symbol": symbol,
        "asset_class_id": asset_class_id,
        "quantity": None,
        "avg_price": None,
        "total_cost": net_value,
    })
else:
    # Quantity-based (existing logic, unchanged)
    buy_qty = buy_qty or 0
    buy_value = buy_agg.total_value or 0
    # ... rest of existing logic
```

**`enrich_holdings()`**

Guard all arithmetic on `quantity` and `avg_price`:

```python
if h["quantity"] is None:
    # Fixed income — no market price lookup
    current_value = h["total_cost"]
    gain_loss = 0
    price = None
else:
    # Existing logic: fetch price, compute current_value = quantity * price
    ...
```

Total portfolio value calculation must also handle this:
```python
for h in holdings:
    if h["quantity"] is None:
        total_value += h["total_cost"]
    else:
        price = prices.get(h["symbol"])
        if price is not None:
            total_value += h["quantity"] * price
```

## Backend: Dividends Endpoint

**`backend/app/routers/portfolio.py` — `fetch_dividend()`**

Add early return for fixed income holdings at the top of `fetch_dividend`:

```python
if holding["quantity"] is None:
    return None  # Fixed income — no dividend calculation
```

This prevents `TypeError` from `dps * holding["quantity"]` when quantity is `None`.

## Frontend: Type Changes

**`frontend/src/types/index.ts`**

```typescript
export interface Transaction {
  // ...
  quantity: number | null;
  unit_price: number | null;
  tax_amount: number | null;
  // ...
}

export interface Holding {
  // ...
  quantity: number | null;
  avg_price: number | null;
  // ...
}
```

Both interfaces must allow null for these fields.

## Frontend: TransactionForm Changes

**`frontend/src/components/TransactionForm.tsx`**

Add a prop or derive from asset class whether this is a fixed income transaction. When it is:

- Hide quantity, unit price, and tax amount fields
- Show only: total value, date, currency, notes
- Type selector shows only "buy" and "sell" (no dividend)
- Submit sends `quantity: null`, `unit_price: null`, `tax_amount: null`

The existing `isDividend` pattern (which already hides quantity/unit_price) serves as a template. Fixed income behaves similarly but also hides tax.

## Frontend: AddAssetForm Changes

If `AddAssetForm` is wired up, it should also respect this behavior — when the selected asset class is fixed income, show the simplified field set.

## Frontend: HoldingsTable / Portfolio Display

Holdings with `quantity: null` display differently:
- Show total invested value instead of quantity × price
- Hide "Avg Price" and "Quantity" columns for these rows (or show "—")
- Gain/loss shows as "—" or 0 since there's no market price

Transaction history rows in the expanded view must also handle null fields:
- `t.unit_price?.toFixed(2) ?? "—"` instead of `t.unit_price.toFixed(2)`
- `(t.tax_amount ?? 0) > 0` instead of `t.tax_amount > 0`

## Frontend: ClassSummaryTable

**`frontend/src/components/ClassSummaryTable.tsx`**

Already uses `h.current_value ?? h.total_cost` which handles value-based holdings correctly. No changes needed, but confirm during implementation that null quantities don't cause issues in any aggregation logic.

## What Stays the Same

- `AssetClass` model — no changes
- `AssetWeight` model — no changes
- Transaction router (`POST /api/transactions`) — no logic changes, just passes through nullable fields
- Dividend calculations — fixed income holdings are skipped via early `quantity is None` check
- Quarantine rules — only apply to quantity-based buy transactions
