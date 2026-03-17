# Fixed Income: Nullable Transaction Fields

## Problem

Fixed income assets (CDBs, LCIs, Tesouro Direto, etc.) only need total value and date — they have no meaningful quantity, unit price, or tax per transaction. Currently all three fields are required (NOT NULL) on the Transaction model, forcing artificial values.

## Solution

Make `quantity`, `unit_price`, and `tax_amount` nullable across the stack. Fixed income transactions store `None` for these fields and only provide `total_value`, `date`, and `currency`. The portfolio service branches on whether a holding has quantity-based or value-based transactions.

## Identifying Fixed Income

Use the asset class name to detect fixed income. The frontend `TransactionForm` and `AddAssetForm` check if the selected asset class name matches a known set (e.g. "Renda Fixa", "Fixed Income"). This keeps the data model unchanged — no new columns on `AssetClass`.

## Backend: Model Changes

**`backend/app/models/transaction.py`**

```python
quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
tax_amount: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
```

All three fields become nullable. Existing transactions retain their values. New fixed income transactions store `None`.

## Backend: Schema Changes

**`backend/app/schemas/transaction.py`**

`TransactionCreate`:
- `quantity: Optional[float] = None`
- `unit_price: Optional[float] = None`
- `tax_amount: Optional[float] = None`

`TransactionResponse`:
- `quantity: float | None`
- `unit_price: float | None`
- `tax_amount: float | None`

`TransactionUpdate` — these fields are already `Optional`, no change needed.

## Backend: Portfolio Service Changes

**`backend/app/services/portfolio.py` — `get_holdings()`**

After computing buy/sell aggregates for a symbol, check if `buy_qty` is `None` (all transactions have `quantity=None`):

- **Quantity-based (stocks/crypto):** Current logic unchanged — `net_qty = buy_qty - sell_qty`, `avg_price = buy_value / buy_qty`.
- **Value-based (fixed income):** `net_value = buy_total_value - sell_total_value`. Return holding with `quantity: None`, `avg_price: None`, `total_cost: net_value`.

The SQL aggregates (`func.sum(Transaction.quantity)`) naturally return `None` when all quantity values are `None`, so the branch condition is simply `if buy_qty is None`.

**`enrich_holdings()`**

When `quantity is None` on a holding:
- Skip market price lookup — fixed income has no ticker price
- `current_value = total_cost` (the invested amount)
- `gain_loss = 0` (no market-based gain/loss)
- Weight calculations use `total_cost` as the current value

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
```

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

## What Stays the Same

- `AssetClass` model — no changes
- `AssetWeight` model — no changes
- Transaction router (`POST /api/transactions`) — no logic changes, just passes through nullable fields
- Dividend calculations — fixed income holdings are skipped (no dividend_per_share concept)
- Quarantine rules — only apply to quantity-based buy transactions
