# Fixed Income Nullable Fields Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `quantity`, `unit_price`, and `tax_amount` nullable so fixed income transactions only need `total_value` and `date`.

**Architecture:** Three nullable fields on Transaction model/schema. Portfolio service branches on `buy_qty is None` to handle value-based holdings differently from quantity-based ones. Frontend forms hide irrelevant fields when asset class name contains "renda fixa" or "fixed income".

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, TypeScript

**Spec:** `docs/superpowers/specs/2026-03-17-fixed-income-nullable-fields-design.md`

---

## Chunk 1: Backend Model, Schema, and Validation

### Task 1: Make Transaction model fields nullable

**Files:**
- Modify: `backend/app/models/transaction.py:18-22`

- [ ] **Step 1: Update the model fields**

Change lines 18-22 from:
```python
quantity: Mapped[float] = mapped_column(Float, nullable=False)
unit_price: Mapped[float] = mapped_column(Float, nullable=False)
total_value: Mapped[float] = mapped_column(Float, nullable=False)
currency: Mapped[str] = mapped_column(String(10), nullable=False)
tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
```

To:
```python
quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
total_value: Mapped[float] = mapped_column(Float, nullable=False)
currency: Mapped[str] = mapped_column(String(10), nullable=False)
tax_amount: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
```

- [ ] **Step 2: Delete the SQLite database so it gets recreated with the new schema**

Run: `rm -f backend/portfolio.db backend/test.db`

- [ ] **Step 3: Verify existing tests still pass**

Run: `cd backend && python -m pytest tests/test_models/test_transaction.py -v`
Expected: PASS

### Task 2: Update Pydantic schemas with validation

**Files:**
- Modify: `backend/app/schemas/transaction.py`

- [ ] **Step 1: Update TransactionCreate schema**

Replace the full file content with:
```python
import datetime as dt
from typing import Literal, Optional

from pydantic import BaseModel, model_validator


class TransactionCreate(BaseModel):
    asset_class_id: str
    asset_symbol: str
    type: Literal["buy", "sell", "dividend"]
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_value: float
    currency: str
    tax_amount: Optional[float] = 0.0
    date: dt.date
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_field_consistency(self):
        # Only validate quantity/unit_price pair. tax_amount is independent:
        # it defaults to 0.0 for stock/crypto and can be explicitly set to None for fixed income.
        fields = [self.quantity, self.unit_price]
        all_set = all(f is not None for f in fields)
        none_set = all(f is None for f in fields)
        if not (all_set or none_set):
            raise ValueError("quantity and unit_price must be all provided or all None")
        return self


class TransactionUpdate(BaseModel):
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_value: Optional[float] = None
    tax_amount: Optional[float] = None
    date: Optional[dt.date] = None
    notes: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    user_id: str
    asset_class_id: str
    asset_symbol: str
    type: str
    quantity: float | None
    unit_price: float | None
    total_value: float
    currency: str
    tax_amount: float | None
    date: dt.date
    notes: Optional[str]
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Run transaction router tests to verify existing behavior**

Run: `cd backend && python -m pytest tests/test_routers/test_transactions.py -v`
Expected: PASS

### Task 3: Write tests for fixed income transactions

**Files:**
- Modify: `backend/tests/test_services/test_portfolio.py`

- [ ] **Step 1: Add a helper for fixed income transactions**

Add after the existing `_create_tx` function (line 50):

```python
def _create_fixed_income_tx(db, user_id, asset_class_id, symbol, tx_type, total_value, tx_date=None):
    if tx_date is None:
        tx_date = date.today()
    tx = Transaction(
        user_id=user_id,
        asset_class_id=asset_class_id,
        asset_symbol=symbol,
        type=tx_type,
        quantity=None,
        unit_price=None,
        total_value=total_value,
        currency="BRL",
        date=tx_date,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx
```

- [ ] **Step 2: Add test for fixed income holdings**

Add at the end of `TestGetHoldings` class:

```python
    def test_get_holdings_fixed_income(self, db):
        user = _create_user(db)
        ac = _create_asset_class(db, user.id, "Renda Fixa", 20.0)
        _create_fixed_income_tx(db, user.id, ac.id, "CDB Banco X", "buy", 10000.0)
        _create_fixed_income_tx(db, user.id, ac.id, "CDB Banco X", "buy", 5000.0)

        svc = PortfolioService(db)
        holdings = svc.get_holdings(user.id)

        assert len(holdings) == 1
        cdb = holdings[0]
        assert cdb["symbol"] == "CDB Banco X"
        assert cdb["quantity"] is None
        assert cdb["avg_price"] is None
        assert cdb["total_cost"] == 15000.0

    def test_get_holdings_mixed_stock_and_fixed_income(self, db):
        user = _create_user(db)
        ac_stocks = _create_asset_class(db, user.id, "Stocks", 60.0)
        ac_fi = _create_asset_class(db, user.id, "Renda Fixa", 20.0)
        _create_tx(db, user.id, ac_stocks.id, "AAPL", "buy", 10, 150.0)
        _create_fixed_income_tx(db, user.id, ac_fi.id, "CDB Banco X", "buy", 10000.0)

        svc = PortfolioService(db)
        holdings = svc.get_holdings(user.id)

        assert len(holdings) == 2
        symbols = {h["symbol"] for h in holdings}
        assert symbols == {"AAPL", "CDB Banco X"}

        aapl = next(h for h in holdings if h["symbol"] == "AAPL")
        assert aapl["quantity"] == 10

        cdb = next(h for h in holdings if h["symbol"] == "CDB Banco X")
        assert cdb["quantity"] is None
        assert cdb["total_cost"] == 10000.0

    def test_get_holdings_fixed_income_with_sell(self, db):
        user = _create_user(db)
        ac = _create_asset_class(db, user.id, "Renda Fixa", 20.0)
        _create_fixed_income_tx(db, user.id, ac.id, "CDB Banco X", "buy", 10000.0)
        _create_fixed_income_tx(db, user.id, ac.id, "CDB Banco X", "sell", 3000.0)

        svc = PortfolioService(db)
        holdings = svc.get_holdings(user.id)

        assert len(holdings) == 1
        cdb = holdings[0]
        assert cdb["total_cost"] == 7000.0

    def test_get_holdings_fixed_income_fully_sold(self, db):
        user = _create_user(db)
        ac = _create_asset_class(db, user.id, "Renda Fixa", 20.0)
        _create_fixed_income_tx(db, user.id, ac.id, "CDB Banco X", "buy", 10000.0)
        _create_fixed_income_tx(db, user.id, ac.id, "CDB Banco X", "sell", 10000.0)

        svc = PortfolioService(db)
        holdings = svc.get_holdings(user.id)

        assert len(holdings) == 0
```

- [ ] **Step 3: Run the new tests (expect failures since service not updated yet)**

Run: `cd backend && python -m pytest tests/test_services/test_portfolio.py -v -k "fixed_income"`
Expected: FAIL (service logic not yet updated)

### Task 4: Update PortfolioService.get_holdings()

**Files:**
- Modify: `backend/app/services/portfolio.py:16-76`

- [ ] **Step 1: Update get_holdings to handle nullable quantity**

Replace the `get_holdings` method (lines 16-76) with:

```python
    def get_holdings(self, user_id: str) -> list[dict]:
        # Get all distinct symbols with their asset_class_id
        symbols = (
            self.db.query(Transaction.asset_symbol, Transaction.asset_class_id)
            .filter(Transaction.user_id == user_id)
            .distinct()
            .all()
        )

        holdings = []
        for symbol, asset_class_id in symbols:
            # Sum buys
            buy_agg = (
                self.db.query(
                    func.sum(Transaction.quantity).label("total_qty"),
                    func.sum(Transaction.total_value).label("total_value"),
                )
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.asset_symbol == symbol,
                    Transaction.type == "buy",
                )
                .first()
            )

            buy_qty = buy_agg.total_qty  # Do NOT default to 0

            if buy_qty is None:
                # Value-based (fixed income): no quantity, just total_value
                buy_value = buy_agg.total_value or 0
                sell_value = (
                    self.db.query(func.sum(Transaction.total_value))
                    .filter(
                        Transaction.user_id == user_id,
                        Transaction.asset_symbol == symbol,
                        Transaction.type == "sell",
                    )
                    .scalar()
                ) or 0
                net_value = buy_value - sell_value
                if net_value <= 0:
                    continue
                holdings.append(
                    {
                        "symbol": symbol,
                        "asset_class_id": asset_class_id,
                        "quantity": None,
                        "avg_price": None,
                        "total_cost": net_value,
                    }
                )
            else:
                # Quantity-based (stocks/crypto): existing logic
                buy_qty = buy_qty or 0
                buy_value = buy_agg.total_value or 0

                sell_agg = (
                    self.db.query(
                        func.sum(Transaction.quantity).label("total_qty"),
                    )
                    .filter(
                        Transaction.user_id == user_id,
                        Transaction.asset_symbol == symbol,
                        Transaction.type == "sell",
                    )
                    .first()
                )

                sell_qty = sell_agg.total_qty or 0
                net_qty = buy_qty - sell_qty

                if net_qty <= 0:
                    continue

                avg_price = buy_value / buy_qty if buy_qty > 0 else 0
                total_cost = avg_price * net_qty

                holdings.append(
                    {
                        "symbol": symbol,
                        "asset_class_id": asset_class_id,
                        "quantity": net_qty,
                        "avg_price": avg_price,
                        "total_cost": total_cost,
                    }
                )

        return holdings
```

- [ ] **Step 2: Run fixed income tests**

Run: `cd backend && python -m pytest tests/test_services/test_portfolio.py -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/transaction.py backend/app/schemas/transaction.py backend/app/services/portfolio.py backend/tests/test_services/test_portfolio.py
git commit -m "feat: make quantity/unit_price/tax_amount nullable for fixed income"
```

### Task 5: Update enrich_holdings for nullable quantity

**Files:**
- Modify: `backend/app/services/portfolio.py:126-193`

- [ ] **Step 1: Update enrich_holdings to handle null quantity**

Replace the `enrich_holdings` method (lines 126-193) with:

```python
    @staticmethod
    def enrich_holdings(
        holdings: list[dict],
        class_map: dict[str, dict],
        weight_map: dict[str, float],
        market_data: MarketDataService,
        db: Session | None = None,
    ) -> list[dict]:
        """Enrich holdings with current prices, values, gain/loss, and weights."""

        # Separate quantity-based and value-based holdings
        qty_holdings = [h for h in holdings if h["quantity"] is not None]
        val_holdings = [h for h in holdings if h["quantity"] is None]

        def fetch_price(holding: dict) -> tuple[str, float | None]:
            symbol = holding["symbol"]
            class_info = class_map.get(holding["asset_class_id"], {})
            class_name = class_info.get("name", "")
            country = class_info.get("country", "US")
            if class_name in CRYPTO_CLASS_NAMES:
                coin_id = CRYPTO_COINGECKO_MAP.get(symbol)
                if coin_id:
                    return symbol, market_data.get_quote_safe(coin_id, is_crypto=True)
            return symbol, market_data.get_quote_safe(symbol, is_crypto=False, country=country, db=db)

        # Fetch prices in parallel (only for quantity-based holdings)
        prices: dict[str, float | None] = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_price, h): h for h in qty_holdings}
            for future in as_completed(futures):
                symbol, price = future.result()
                prices[symbol] = price

        # Calculate total portfolio value
        total_value = 0.0
        for h in qty_holdings:
            price = prices.get(h["symbol"])
            if price is not None:
                total_value += h["quantity"] * price
        for h in val_holdings:
            total_value += h["total_cost"]

        # Enrich each holding
        enriched = []
        for h in holdings:
            class_info = class_map.get(h["asset_class_id"], {})
            class_target = class_info.get("target_weight", 0.0)
            asset_target = weight_map.get(h["symbol"], 0.0)
            effective_target = class_target * asset_target / 100
            country = class_info.get("country", "US")
            currency = "BRL" if country == "BR" else "USD"

            if h["quantity"] is None:
                # Fixed income: no market price, gain_loss=None renders as "—" in frontend
                current_value = h["total_cost"]
                actual_weight = (current_value / total_value * 100) if total_value > 0 else 0.0
                enriched.append({
                    **h,
                    "current_price": None,
                    "current_value": current_value,
                    "gain_loss": None,
                    "target_weight": effective_target,
                    "actual_weight": actual_weight,
                    "currency": currency,
                })
            else:
                price = prices.get(h["symbol"])
                if price is not None:
                    current_value = h["quantity"] * price
                    gain_loss = (price - h["avg_price"]) * h["quantity"]
                    actual_weight = (current_value / total_value * 100) if total_value > 0 else 0.0
                else:
                    current_value = None
                    gain_loss = None
                    actual_weight = None

                enriched.append({
                    **h,
                    "current_price": price,
                    "current_value": current_value,
                    "gain_loss": gain_loss,
                    "target_weight": effective_target,
                    "actual_weight": actual_weight,
                    "currency": currency,
                })

        return enriched
```

- [ ] **Step 2: Run all portfolio tests**

Run: `cd backend && python -m pytest tests/test_services/test_portfolio.py tests/test_routers/test_portfolio.py tests/test_portfolio_enriched.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/portfolio.py
git commit -m "feat: handle nullable quantity in enrich_holdings"
```

### Task 6: Guard dividends endpoint against null quantity

**Files:**
- Modify: `backend/app/routers/portfolio.py:148-156`

- [ ] **Step 1: Add early return for fixed income in fetch_dividend**

In `portfolio.py`, inside the `fetch_dividend` function (line 148), add after line 152 (`if not ac: return None`):

```python
        if holding["quantity"] is None:
            return None  # Fixed income — no dividend calculation
```

- [ ] **Step 2: Run dividend-related tests**

Run: `cd backend && python -m pytest tests/test_routers/test_portfolio.py -v`
Expected: PASS

- [ ] **Step 3: Run full backend test suite**

Run: `cd backend && python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/portfolio.py
git commit -m "fix: guard dividends endpoint against null quantity holdings"
```

## Chunk 2: Frontend Changes

### Task 7: Verify quarantine and get_allocation handle null quantity

**Files:**
- Read: `backend/app/services/quarantine.py` (or wherever quarantine logic lives)
- Read: `backend/app/services/portfolio.py` (`get_allocation` method)

- [ ] **Step 1: Verify quarantine logic**

Check quarantine service/router. It counts buy transactions by symbol — it does not use `quantity` for counting, so null quantity is safe. Confirm by reading the code.

- [ ] **Step 2: Verify get_allocation**

`get_allocation()` calls `get_holdings()` and passes `h["quantity"]` at line 109. This will now be `None` for fixed income. The allocation endpoint consumers (frontend `ClassSummaryTable`) use `total_cost` for value calculations, not `quantity`, so this is safe. Confirm by reading the code.

### Task 8: Update frontend TypeScript types

**Files:**
- Modify: `frontend/src/types/index.ts:20-49`

- [ ] **Step 1: Update Transaction and Holding interfaces**

Change the `Transaction` interface (lines 20-35):

```typescript
export interface Transaction {
  id: string;
  user_id: string;
  asset_class_id: string;
  asset_symbol: string;
  type: "buy" | "sell" | "dividend";
  quantity: number | null;
  unit_price: number | null;
  total_value: number;
  currency: string;
  tax_amount: number | null;
  date: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}
```

Change the `Holding` interface (lines 37-49):

```typescript
export interface Holding {
  symbol: string;
  asset_class_id: string;
  quantity: number | null;
  avg_price: number | null;
  total_cost: number;
  current_price?: number;
  current_value?: number;
  gain_loss?: number;
  target_weight?: number;
  actual_weight?: number;
  currency?: string;
}
```

- [ ] **Step 2: Run TypeScript check to see what breaks**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -50`
Expected: Type errors in components using `quantity`, `unit_price`, `tax_amount`, `avg_price` without null checks

### Task 9: Update HoldingsTable for null-safe rendering

**Files:**
- Modify: `frontend/src/components/HoldingsTable.tsx`

- [ ] **Step 1: Fix holding row display (line 522-523)**

Change:
```tsx
<td className="px-3 py-2 text-right">{h.quantity}</td>
<td className="px-3 py-2 text-right">{formatCurrency(h.avg_price, cur)}</td>
```

To:
```tsx
<td className="px-3 py-2 text-right">{h.quantity != null ? h.quantity : "—"}</td>
<td className="px-3 py-2 text-right">{h.avg_price != null ? formatCurrency(h.avg_price, cur) : "—"}</td>
```

- [ ] **Step 2: Fix transaction history display (lines 817-827)**

Change line 817:
```tsx
<td className="py-1 px-2 text-right">{t.quantity}</td>
```
To:
```tsx
<td className="py-1 px-2 text-right">{t.quantity != null ? t.quantity : "—"}</td>
```

Change lines 818-821:
```tsx
<td className="py-1 px-2 text-right">
  {CURRENCY_SYMBOLS[t.currency] ?? `${t.currency} `}
  {t.unit_price.toFixed(2)}
</td>
```
To:
```tsx
<td className="py-1 px-2 text-right">
  {t.unit_price != null
    ? `${CURRENCY_SYMBOLS[t.currency] ?? `${t.currency} `}${t.unit_price.toFixed(2)}`
    : "—"}
</td>
```

Change lines 826-827:
```tsx
<td className="py-1 px-2 text-right text-text-muted">
  {t.tax_amount > 0 ? formatCurrency(t.tax_amount, t.currency) : "-"}
</td>
```
To:
```tsx
<td className="py-1 px-2 text-right text-text-muted">
  {t.tax_amount != null && t.tax_amount > 0 ? formatCurrency(t.tax_amount, t.currency) : "-"}
</td>
```

- [ ] **Step 3: Fix startEditTx for null fields (lines 473-477)**

Change:
```tsx
setEditTxData({
  quantity: String(t.quantity),
  unit_price: String(t.unit_price),
  total_value: String(t.total_value),
  tax_amount: String(t.tax_amount),
  date: t.date,
  notes: t.notes ?? "",
});
```
To:
```tsx
setEditTxData({
  quantity: t.quantity != null ? String(t.quantity) : "",
  unit_price: t.unit_price != null ? String(t.unit_price) : "",
  total_value: String(t.total_value),
  tax_amount: t.tax_amount != null ? String(t.tax_amount) : "",
  date: t.date,
  notes: t.notes ?? "",
});
```

- [ ] **Step 4: Fix edit row rendering for fixed income transactions (lines 736-786)**

The edit form rows for quantity, unit_price, and tax should also handle the case where the transaction is fixed income (quantity is null). The existing `t.type === "dividend"` checks should be extended to also cover fixed income. Replace the condition `t.type === "dividend"` with `t.type === "dividend" || t.quantity == null` in the edit row JSX (lines 737, 750).

- [ ] **Step 5: Fix saveEditTx for fixed income (lines 483-500)**

Change the `saveEditTx` function:
```tsx
const saveEditTx = async (t: Transaction) => {
  if (!onUpdateTransaction) return;
  const isValueBased = t.quantity == null;
  const qty = isValueBased ? null : (parseFloat(editTxData.quantity) || 0);
  const price = isValueBased ? null : (parseFloat(editTxData.unit_price) || 0);
  const total = isValueBased
    ? parseFloat(editTxData.total_value) || 0
    : t.type === "dividend"
    ? parseFloat(editTxData.total_value) || 0
    : (qty ?? 0) * (price ?? 0);
  await onUpdateTransaction(t.id, {
    quantity: qty,
    unit_price: price,
    total_value: total,
    tax_amount: isValueBased ? null : (parseFloat(editTxData.tax_amount) || 0),
    date: editTxData.date,
    notes: editTxData.notes || null,
  });
  setEditingTx(null);
  await onFetchTransactions(h.symbol);
};
```

- [ ] **Step 6: Run TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/components/HoldingsTable.tsx
git commit -m "feat: null-safe rendering for fixed income holdings and transactions"
```

### Task 10: Update TransactionForm for fixed income

**Files:**
- Modify: `frontend/src/components/TransactionForm.tsx`

- [ ] **Step 1: Add isFixedIncome prop and logic**

Update the props interface and component to accept an `isFixedIncome` prop:

```tsx
interface TransactionFormProps {
  symbol: string;
  assetClassId: string;
  isFixedIncome?: boolean;
  initialType?: TransactionType;
  onSubmit: (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => Promise<unknown>;
  onCancel: () => void;
}

export function TransactionForm({
  symbol,
  assetClassId,
  isFixedIncome = false,
  initialType = "buy",
  onSubmit,
  onCancel,
}: TransactionFormProps) {
```

- [ ] **Step 2: Update form visibility and submit logic**

Change `isDividend` usage to also account for fixed income. Add after `const isDividend = type === "dividend";`:

```tsx
const hideQuantityFields = isDividend || isFixedIncome;
```

Replace all `isDividend` references in the JSX conditionals with `hideQuantityFields` (for showing/hiding quantity, unit_price fields).

For the type selector, when `isFixedIncome` is true, only show "buy" and "sell":
```tsx
<select ...>
  <option value="buy">Buy</option>
  <option value="sell">Sell</option>
  {!isFixedIncome && <option value="dividend">Dividend</option>}
</select>
```

Hide the tax amount field when `isFixedIncome`:
```tsx
{!isFixedIncome && (
  <div>
    <label className="block text-base text-text-muted mb-1">Tax Amount</label>
    ...
  </div>
)}
```

Update `handleSubmit` to send null for fixed income:
```tsx
await onSubmit({
  asset_class_id: assetClassId,
  asset_symbol: symbol,
  type,
  quantity: hideQuantityFields ? null : parseFloat(quantity) || 0,
  unit_price: hideQuantityFields ? null : parseFloat(unitPrice) || 0,
  total_value: hideQuantityFields ? parseFloat(totalValue) || 0 : parseFloat(computedTotal) || 0,
  currency,
  tax_amount: isFixedIncome ? null : parseFloat(taxAmount) || 0,
  date,
  notes: notes || null,
});
```

- [ ] **Step 3: Run TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/TransactionForm.tsx
git commit -m "feat: TransactionForm supports fixed income mode"
```

### Task 11: Create shared isFixedIncomeClass utility and wire into HoldingsTable

**Files:**
- Create: `frontend/src/utils/assetClass.ts`
- Modify: `frontend/src/components/HoldingsTable.tsx`

- [ ] **Step 1: Create shared utility**

Create `frontend/src/utils/assetClass.ts`:
```tsx
const FIXED_INCOME_TERMS = ["renda fixa", "fixed income"];

export function isFixedIncomeClass(className: string): boolean {
  const lower = className.toLowerCase();
  return FIXED_INCOME_TERMS.some((term) => lower.includes(term));
}
```

- [ ] **Step 2: Import and use in HoldingsTable**

Add import at top of `HoldingsTable.tsx`:
```tsx
import { isFixedIncomeClass } from "../utils/assetClass";
```

- [ ] **Step 3: Pass isFixedIncome to TransactionForm in HoldingsTable**

In the `HoldingsTable` component where `TransactionForm` is rendered (line 167), update to pass `isFixedIncome`:

```tsx
<TransactionForm
  symbol={transactionForm.symbol}
  assetClassId={transactionForm.assetClassId}
  isFixedIncome={isFixedIncomeClass(
    assetClasses.find((ac) => ac.id === transactionForm.assetClassId)?.name ?? ""
  )}
  initialType={transactionForm.type}
  onSubmit={...}
  onCancel={...}
/>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/HoldingsTable.tsx
git commit -m "feat: wire isFixedIncome detection into HoldingsTable"
```

### Task 12: Update AddAssetForm for fixed income

**Files:**
- Modify: `frontend/src/components/AddAssetForm.tsx`

- [ ] **Step 1: Add fixed income detection and conditional fields**

Import from the shared utility:
```tsx
import { isFixedIncomeClass } from "../utils/assetClass";
```

Add a `totalValue` state variable. Derive `isFixedIncome` from the selected asset class:

```tsx
const [totalValue, setTotalValue] = useState("");

const selectedClass = assetClasses.find((ac) => ac.id === assetClassId);
const isFixedIncome = isFixedIncomeClass(selectedClass?.name ?? "");
```

- [ ] **Step 2: Conditionally show fields**

Replace the buy transaction fields section (lines 224-288) to conditionally show:
- When `isFixedIncome`: show only Total Value, Currency, Date
- Otherwise: show Quantity, Unit Price, Total (computed), Currency, Tax, Date (existing)

```tsx
{isFixedIncome ? (
  <div className="flex gap-3 flex-wrap items-end">
    <div>
      <label className="block text-base text-text-muted mb-1">Total Value</label>
      <input
        type="number"
        step="any"
        className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary w-36"
        value={totalValue}
        onChange={(e) => setTotalValue(e.target.value)}
        required
      />
    </div>
    <div>
      <label className="block text-base text-text-muted mb-1">Currency</label>
      <select ... />
    </div>
    <div>
      <label className="block text-base text-text-muted mb-1">Date</label>
      <input type="date" ... />
    </div>
  </div>
) : (
  /* existing quantity/unit_price/total/currency/tax/date fields */
  <div className="flex gap-3 flex-wrap items-end">
    ...existing fields...
  </div>
)}
```

- [ ] **Step 3: Update handleSubmit to send null for fixed income**

```tsx
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  if (!selectedSymbol || !assetClassId) return;
  setSubmitting(true);
  try {
    if (isFixedIncome) {
      await onSubmit({
        asset_class_id: assetClassId,
        asset_symbol: selectedSymbol,
        type: "buy",
        quantity: null,
        unit_price: null,
        total_value: parseFloat(totalValue) || 0,
        currency,
        tax_amount: null,
        date,
        notes: notes || null,
      });
    } else {
      await onSubmit({
        asset_class_id: assetClassId,
        asset_symbol: selectedSymbol,
        type: "buy",
        quantity: parseFloat(quantity) || 0,
        unit_price: parseFloat(unitPrice) || 0,
        total_value: parseFloat(computedTotal) || 0,
        currency,
        tax_amount: parseFloat(taxAmount) || 0,
        date,
        notes: notes || null,
      });
    }
  } finally {
    setSubmitting(false);
  }
};
```

- [ ] **Step 4: Run TypeScript check and build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/AddAssetForm.tsx
git commit -m "feat: AddAssetForm supports fixed income with simplified fields"
```

### Task 13: Final verification

- [ ] **Step 1: Run full backend test suite**

Run: `cd backend && python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 3: Run frontend tests**

Run: `cd frontend && npm run test -- --run`
Expected: PASS
