# Asset Class Holdings Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit `type` field to asset classes and create drill-down pages with type-specific columns/forms.

**Architecture:** Backend gets a new `type` column on `asset_classes` table with startup backfill. Frontend gets a new `/portfolio/:assetClassId` route rendering an `AssetClassHoldings` page that filters holdings client-side and shows type-specific columns and an always-visible add form. The existing `HoldingsTable` is refactored to accept a `type` prop; grouping logic is removed.

**Tech Stack:** FastAPI + SQLAlchemy (backend), React 19 + TypeScript + React Router (frontend), Vitest (tests)

**Spec:** `docs/superpowers/specs/2026-03-18-asset-class-holdings-design.md`

---

## Chunk 1: Backend — `type` Field on AssetClass

### Task 1: Add `type` column to AssetClass model

**Files:**
- Modify: `backend/app/models/asset_class.py`

- [ ] **Step 1: Add `type` column to the model**

In `backend/app/models/asset_class.py`, add a `type` column after the `country` column:

```python
type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="stock")
```

Import note: `String` is already imported.

- [ ] **Step 2: Verify the app starts and table is updated**

Run: `cd backend && python -c "from app.database import Base, engine; from app.models import AssetClass; Base.metadata.create_all(bind=engine); print('OK')"`
Expected: `OK` (SQLite will add the column via `create_all` since it uses `CREATE TABLE IF NOT EXISTS` — for existing tables, SQLite won't add the column automatically. We'll handle migration via seed backfill.)

Note: Since SQLite `create_all` won't add columns to existing tables, we need to handle this. Add a manual column-add in the backfill step (Task 3).

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/asset_class.py
git commit -m "feat: add type column to AssetClass model"
```

### Task 2: Add `type` to Pydantic schemas

**Files:**
- Modify: `backend/app/schemas/asset_class.py`

- [ ] **Step 1: Update schemas**

In `backend/app/schemas/asset_class.py`:

1. Add import: `from typing import Literal` (add to existing `from typing import Optional` line)
2. Add to `AssetClassCreate`: `type: Literal["stock", "crypto", "fixed_income"] = "stock"`
3. Add to `AssetClassUpdate`: `type: Literal["stock", "crypto", "fixed_income"] | None = None`
4. Add to `AssetClassResponse`: `type: str`

Full file after changes:

```python
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class AssetClassCreate(BaseModel):
    name: str
    target_weight: float = 0.0
    country: str = "US"
    type: Literal["stock", "crypto", "fixed_income"] = "stock"


class AssetClassUpdate(BaseModel):
    name: Optional[str] = None
    target_weight: Optional[float] = None
    country: Optional[str] = None
    type: Literal["stock", "crypto", "fixed_income"] | None = None


class AssetClassResponse(BaseModel):
    id: str
    user_id: str
    name: str
    target_weight: float
    country: str
    type: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/asset_class.py
git commit -m "feat: add type field to asset class schemas"
```

### Task 3: Update router to accept `type` + add `type` to update logic

**Files:**
- Modify: `backend/app/routers/asset_classes.py`

- [ ] **Step 1: Update create endpoint to forward `type`**

In `create_asset_class`, add `type=body.type` to the `AssetClass()` constructor call on line 30:

```python
ac = AssetClass(user_id=x_user_id, name=body.name, target_weight=body.target_weight, country=body.country, type=body.type)
```

- [ ] **Step 2: Update update endpoint to handle `type`**

In `update_asset_class`, add after the `country` check (after line 58):

```python
    if body.type is not None:
        ac.type = body.type
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/asset_classes.py
git commit -m "feat: accept type in asset class create/update endpoints"
```

### Task 4: Startup backfill for existing asset classes

**Files:**
- Modify: `backend/app/seed.py`

- [ ] **Step 1: Add backfill logic to `seed_data()`**

The backfill needs to:
1. Ensure the `type` column exists (for existing SQLite databases)
2. Set `type` based on name keyword matching for existing rows

Add this function and call it from `seed_data()`:

```python
from sqlalchemy import text, inspect


def _backfill_asset_class_types(db):
    """Ensure type column exists and backfill based on name keywords."""
    # Add column if missing (SQLite create_all won't add to existing tables)
    inspector = inspect(db.bind)
    columns = [c["name"] for c in inspector.get_columns("asset_classes")]
    if "type" not in columns:
        db.execute(text("ALTER TABLE asset_classes ADD COLUMN type VARCHAR(20) NOT NULL DEFAULT 'stock'"))
        db.commit()

    # Backfill crypto
    crypto_names = {"Crypto", "Cryptos", "Criptomoedas"}
    classes = db.query(AssetClass).filter(AssetClass.type == "stock").all()
    for ac in classes:
        if ac.name in crypto_names or ac.name == "Stablecoins":
            ac.type = "crypto"
        elif any(term in ac.name.lower() for term in ["renda fixa", "fixed income"]):
            ac.type = "fixed_income"
    db.commit()
```

Update `seed_data()` to call the backfill unconditionally (before the early return):

```python
def seed_data():
    db = SessionLocal()
    try:
        _backfill_asset_class_types(db)

        user_count = db.query(User).count()
        if user_count > 0:
            return
        # ... rest unchanged
```

Also update the seed class_configs to include type for new installs:

```python
        class_configs = [
            ("US Stocks", "US", "stock"),
            ("BR Stocks", "BR", "stock"),
            ("Crypto", "US", "crypto"),
            ("Stablecoins", "US", "crypto"),
            ("FIIs", "BR", "stock"),
            ("REITs", "US", "stock"),
        ]
        for name, country, type_ in class_configs:
            ac = AssetClass(user_id=user.id, name=name, target_weight=25.0, country=country, type=type_)
            db.add(ac)
```

- [ ] **Step 2: Test backfill manually**

Run: `cd backend && python -c "from app.seed import seed_data, _backfill_asset_class_types; from app.database import SessionLocal; db = SessionLocal(); _backfill_asset_class_types(db); from app.models.asset_class import AssetClass; classes = db.query(AssetClass).all(); print([(c.name, c.type) for c in classes]); db.close()"`

Expected: Each class should have appropriate type (Crypto → crypto, Stablecoins → crypto, others → stock).

- [ ] **Step 3: Commit**

```bash
git add backend/app/seed.py
git commit -m "feat: backfill asset class types on startup"
```

### Task 5: Backend test for type field

**Files:**
- Create: `backend/tests/test_asset_class_type.py`

- [ ] **Step 1: Write test**

```python
import pytest
from fastapi.testclient import TestClient


def test_create_asset_class_with_type(client):
    res = client.post(
        "/api/asset-classes",
        json={"name": "Test Crypto", "target_weight": 10, "country": "US", "type": "crypto"},
        headers={"X-User-Id": "default-user-id"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["type"] == "crypto"


def test_create_asset_class_default_type(client):
    res = client.post(
        "/api/asset-classes",
        json={"name": "Test Default", "target_weight": 5},
        headers={"X-User-Id": "default-user-id"},
    )
    assert res.status_code == 201
    assert res.json()["type"] == "stock"


def test_update_asset_class_type(client):
    # Create first
    create_res = client.post(
        "/api/asset-classes",
        json={"name": "Changeable", "target_weight": 5},
        headers={"X-User-Id": "default-user-id"},
    )
    ac_id = create_res.json()["id"]

    # Update type
    update_res = client.put(
        f"/api/asset-classes/{ac_id}",
        json={"type": "fixed_income"},
        headers={"X-User-Id": "default-user-id"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["type"] == "fixed_income"


def test_list_asset_classes_includes_type(client):
    res = client.get(
        "/api/asset-classes",
        headers={"X-User-Id": "default-user-id"},
    )
    assert res.status_code == 200
    for ac in res.json():
        assert "type" in ac


def test_create_asset_class_invalid_type(client):
    res = client.post(
        "/api/asset-classes",
        json={"name": "Bad", "type": "invalid_type"},
        headers={"X-User-Id": "default-user-id"},
    )
    assert res.status_code == 422
```

Note: This test file uses the existing `client` fixture from `conftest.py`. Check if `backend/tests/conftest.py` exists and provides a `client` fixture. If not, add one.

- [ ] **Step 2: Run tests**

Run: `cd backend && pytest tests/test_asset_class_type.py -v`
Expected: All 5 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_asset_class_type.py
git commit -m "test: add tests for asset class type field"
```

---

## Chunk 2: Frontend — Type System & Hook Updates

### Task 6: Add `type` to TypeScript `AssetClass` interface

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add type field to AssetClass interface**

Add `type: "stock" | "crypto" | "fixed_income";` after the `country` field in the `AssetClass` interface (after line 6):

```typescript
export interface AssetClass {
  id: string;
  user_id: string;
  name: string;
  target_weight: number;
  country: string;
  type: "stock" | "crypto" | "fixed_income";
  created_at: string;
  updated_at: string;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add type to AssetClass TypeScript interface"
```

### Task 7: Update `useAssetClasses` hook to accept `type`

**Files:**
- Modify: `frontend/src/hooks/useAssetClasses.ts`

- [ ] **Step 1: Update `createClass` to accept and forward `type`**

Change the `createClass` signature and body:

```typescript
const createClass = useCallback(async (name: string, targetWeight: number, type: "stock" | "crypto" | "fixed_income" = "stock") => {
    const res = await api.post<AssetClass>("/asset-classes", {
      name,
      target_weight: targetWeight,
      type,
    });
    setAssetClasses((prev) => [...prev, res.data]);
    return res.data;
  }, []);
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useAssetClasses.ts
git commit -m "feat: update useAssetClasses to accept type parameter"
```

### Task 8: Update `AssetClassesTable` — clickable rows, type dropdown, navigation

**Files:**
- Modify: `frontend/src/components/AssetClassesTable.tsx`

- [ ] **Step 1: Add navigation import and update props**

Add `useNavigate` import and update `onCreateClass` signature:

```typescript
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { DataTable, type Column } from "./DataTable";
import type { AssetClass } from "../types";
```

Update `AssetClassesTableProps`:

```typescript
interface AssetClassesTableProps {
  assetClasses: AssetClass[];
  loading: boolean;
  allocationMap?: Record<string, AllocationInfo>;
  onUpdateClass: (id: string, data: Partial<AssetClass>) => Promise<unknown>;
  onCreateClass: (name: string, targetWeight: number, type: "stock" | "crypto" | "fixed_income") => Promise<unknown>;
  onDeleteClass: (id: string) => Promise<unknown>;
}
```

- [ ] **Step 2: Add navigate hook, type state, and update form**

Inside the component, add:

```typescript
const navigate = useNavigate();
const [newType, setNewType] = useState<"stock" | "crypto" | "fixed_income">("stock");
```

- [ ] **Step 3: Add type column and chevron to name column**

Update the `columns` array. Replace the `name` column render to include a chevron, and add a `type` column after `name`:

```typescript
const columns: Column<AssetClassRow>[] = [
    {
      key: "name",
      header: "Name",
      sortable: true,
      render: (row) => (
        <span className="flex items-center gap-1">
          <span>{row.name}</span>
          <span className="text-text-muted text-xs">›</span>
        </span>
      ),
    },
    {
      key: "type",
      header: "Type",
      sortable: true,
      render: (row) => (
        <span className="text-text-muted capitalize">{row.type.replace("_", " ")}</span>
      ),
    },
    // ... rest of columns unchanged
```

- [ ] **Step 4: Add onRowClick to DataTable for navigation**

Pass `onRowClick` to the `DataTable`:

```typescript
<DataTable
  columns={columns}
  data={rows}
  getRowId={(r) => r.id}
  onRowClick={(row) => navigate(`/portfolio/${row.id}`)}
/>
```

- [ ] **Step 5: Update the create form to include type dropdown**

In the form JSX, add a type dropdown between the name and weight inputs:

```tsx
<div>
  <label className="block text-base text-text-muted mb-1">Type</label>
  <select
    className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
    value={newType}
    onChange={(e) => setNewType(e.target.value as "stock" | "crypto" | "fixed_income")}
  >
    <option value="stock">Stock</option>
    <option value="crypto">Crypto</option>
    <option value="fixed_income">Fixed Income</option>
  </select>
</div>
```

Update `handleSubmit` to pass `newType`:

```typescript
const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    await onCreateClass(newName.trim(), parseFloat(newWeight) || 0, newType);
    setNewName("");
    setNewWeight("");
    setNewType("stock");
    setShowForm(false);
  };
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/AssetClassesTable.tsx
git commit -m "feat: make asset class rows clickable with navigation and type dropdown"
```

### Task 9: Update `Portfolio.tsx` — remove HoldingsTable, update createClass signature

**Files:**
- Modify: `frontend/src/pages/Portfolio.tsx`

- [ ] **Step 1: Remove HoldingsTable import and usage**

1. Remove the import: `import { HoldingsTable } from "../components/HoldingsTable";`
2. Remove unused imports that were only needed for HoldingsTable: `useTransactions`, `useFundamentals`, `QuarantineStatus`, `Transaction` (if no longer used by remaining code)
3. Remove the entire `<HoldingsTable ... />` block (lines 166-188)
4. Remove state/callbacks that only served HoldingsTable: `quarantineStatuses`, `allTransactions`, `dividendsBySymbol`, `fetchQuarantineStatuses`, `fetchAllTransactions`, `fetchDividends`, and the handler functions (`handleCreateTransaction`, `handleUpdateTransaction`, `handleDeleteTransaction`, `handleDeleteHolding`, `handleChangeAssetClass`, `handleFetchTransactions`)

**However**, `DividendsTable` still uses `handleCreateTransaction`, `allTransactions` (for dividends filter), and `fetchAllTransactions`. Keep what `DividendsTable` needs. Specifically keep:
- `useTransactions` (for `createTransaction`)
- `allTransactions` + `fetchAllTransactions` (for dividend filtering)
- `handleCreateTransaction` (simplified — only needs `createTransaction` + `refreshPortfolio` + `fetchAllTransactions`)
- The `Transaction` type import

Remove:
- `useFundamentals` import and usage
- `QuarantineStatus` type import
- `quarantineStatuses` state + `fetchQuarantineStatuses`
- `dividendsBySymbol` state + `fetchDividends`
- `handleUpdateTransaction`, `handleDeleteTransaction`, `handleDeleteHolding`, `handleChangeAssetClass`, `handleFetchTransactions`
- `HoldingsTable` import and JSX

5. Update `onCreateClass` to pass type:

```tsx
onCreateClass={async (name, weight, type) => {
  await createClass(name, weight, type);
}}
```

- [ ] **Step 2: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors (there will be errors from tests referencing old interfaces — those are fixed in later tasks)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Portfolio.tsx
git commit -m "feat: remove HoldingsTable from Portfolio page, update createClass signature"
```

---

## Chunk 3: Frontend — Refactor HoldingsTable & Forms

### Task 10: Refactor `HoldingsTable` — accept `type` prop, remove grouping

**Files:**
- Modify: `frontend/src/components/HoldingsTable.tsx`

- [ ] **Step 1: Update props interface**

Replace `HoldingsTableProps` — remove `assetClasses` (no longer needed for grouping), add `type` and `assetClassId`:

```typescript
type AssetClassType = "stock" | "crypto" | "fixed_income";

interface HoldingsTableProps {
  holdings: Holding[];
  assetClassId: string;
  assetClasses: AssetClass[];
  type: AssetClassType;
  loading: boolean;
  quarantineStatuses?: QuarantineStatus[];
  transactions: Transaction[];
  dividendsBySymbol?: Map<string, { income: number; currency: string }>;
  fundamentalsScores?: FundamentalsScore[];
  onRefreshAllScores?: () => Promise<void>;
  onFetchTransactions: (symbol: string) => Promise<void>;
  onCreateTransaction: (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => Promise<unknown>;
  onUpdateTransaction?: (id: string, data: Partial<Transaction>) => Promise<unknown>;
  onDeleteTransaction?: (id: string) => Promise<unknown>;
  onDeleteHolding?: (symbol: string) => Promise<unknown>;
  onChangeAssetClass?: (symbol: string, assetClassId: string) => Promise<unknown>;
  onUpdateWeight?: (symbol: string, targetWeight: number) => Promise<unknown>;
}
```

- [ ] **Step 2: Remove grouping logic**

Delete the `GroupedHoldings` interface (line 44-48), `groupByAssetClass` function (lines 50-71), and the `GroupSection` component (lines 272-400). Also remove `collapsedGroups` state and `toggleGroup` function.

- [ ] **Step 3: Replace the table header with type-specific columns**

Replace the fixed 10-column header with dynamic columns based on `type`:

```typescript
const isFixedIncome = type === "fixed_income";
const isCrypto = type === "crypto";
const showQty = !isFixedIncome;
const showAvgPrice = !isFixedIncome;
const showCurrentPrice = !isFixedIncome;
const showGainLoss = !isFixedIncome;
const showDiv = !isFixedIncome && !isCrypto;
const showScore = !isFixedIncome && !isCrypto;
```

Update `<thead>`:

```tsx
<thead>
  <tr className="text-text-muted uppercase text-base tracking-wide">
    <th className="text-left px-3 py-2">{isFixedIncome ? "Name" : "Symbol"}</th>
    {showQty && <th className="text-right px-3 py-2">Qty</th>}
    {showAvgPrice && <th className="text-right px-3 py-2">Avg Price</th>}
    {showCurrentPrice && <th className="text-right px-3 py-2">Current Price</th>}
    <th className="text-right px-3 py-2">{isFixedIncome ? "Total Value" : "Current Value"}</th>
    {showGainLoss && <th className="text-right px-3 py-2">Gain/Loss</th>}
    <th className="text-right px-3 py-2">Target %</th>
    <th className="text-right px-3 py-2">Actual %</th>
    {showDiv && (
      <th className="text-right px-3 py-2">Div ({new Date().getFullYear()})</th>
    )}
    {showScore && (
      <th className="text-right px-3 py-2">
        <span className="flex items-center justify-end gap-1">
          Score
          {onRefreshAllScores && (
            <button
              className="text-[10px] text-text-muted hover:text-primary ml-1"
              title="Fetch scores for all stocks"
              onClick={onRefreshAllScores}
            >
              ↻
            </button>
          )}
        </span>
      </th>
    )}
    <th className="text-center px-3 py-2"></th>
  </tr>
</thead>
```

- [ ] **Step 4: Replace tbody — render holdings directly (no groups)**

Replace the grouped rendering with a flat list:

```tsx
<tbody>
  {holdings.map((h) => {
    const q = quarantineMap.get(h.symbol);
    const isExpanded = expandedRow === h.symbol;
    const isEditingThis = editingWeight?.symbol === h.symbol;

    return (
      <HoldingRows
        key={h.symbol}
        holding={h}
        type={type}
        quarantine={q}
        isExpanded={isExpanded}
        transactions={transactions}
        classId={assetClassId}
        isEditingWeight={isEditingThis}
        editWeightValue={isEditingThis ? editingWeight!.value : undefined}
        dividendData={dividendsBySymbol.get(h.symbol)}
        score={scoreMap.get(h.symbol)}
        assetClasses={assetClasses}
        onUpdateTransaction={onUpdateTransaction}
        onDeleteTransaction={onDeleteTransaction}
        onDeleteHolding={onDeleteHolding}
        onChangeAssetClass={onChangeAssetClass}
        onFetchTransactions={onFetchTransactions}
        onNavigateScore={() => navigate(`/fundamentals/${h.symbol}`)}
        onRowClick={() => handleRowClick(h.symbol)}
        onBuy={() => setTransactionForm({ symbol: h.symbol, assetClassId, type: "buy" })}
        onSell={() => setTransactionForm({ symbol: h.symbol, assetClassId, type: "sell" })}
        onStartEditWeight={
          onUpdateWeight
            ? () => setEditingWeight({ symbol: h.symbol, value: String(h.target_weight ?? 0) })
            : undefined
        }
        onWeightChange={(value) => setEditingWeight((prev) => (prev ? { ...prev, value } : null))}
        onCommitWeight={commitWeightEdit}
        onCancelWeight={() => setEditingWeight(null)}
      />
    );
  })}
</tbody>
```

- [ ] **Step 5: Update `HoldingRows` to accept and use `type` prop**

Add `type: AssetClassType` to `HoldingRowsProps`. Use the same column-visibility flags (`showQty`, `showAvgPrice`, etc.) to conditionally render `<td>` cells:

```tsx
// Inside HoldingRows, derive flags from type prop
const isFixedIncome = type === "fixed_income";
const isCrypto = type === "crypto";
const showQty = !isFixedIncome;
const showAvgPrice = !isFixedIncome;
const showCurrentPrice = !isFixedIncome;
const showGainLoss = !isFixedIncome;
const showDiv = !isFixedIncome && !isCrypto;
const showScore = !isFixedIncome && !isCrypto;
```

Conditionally render each `<td>`:
- Wrap Qty cell: `{showQty && <td>...</td>}`
- Wrap Avg Price cell: `{showAvgPrice && <td>...</td>}`
- Wrap Current Price cell: `{showCurrentPrice && <td>...</td>}`
- Current Value cell: always shown (use `h.current_value ?? h.total_cost` for fixed income)
- Wrap Gain/Loss cell: `{showGainLoss && <td>...</td>}`
- Target % and Actual %: always shown
- Wrap Div cell: `{showDiv && <td>...</td>}`
- Wrap Score cell: `{showScore && <td>...</td>}`

Update the expanded transaction row `colSpan` dynamically:

```tsx
const colCount = 4 + (showQty ? 1 : 0) + (showAvgPrice ? 1 : 0) + (showCurrentPrice ? 1 : 0) + (showGainLoss ? 1 : 0) + (showDiv ? 1 : 0) + (showScore ? 1 : 0);
// Use colCount for the colSpan in the expanded row
```

- [ ] **Step 6: Update `TransactionForm` usage — pass `type` prop**

In the `HoldingsTable` component where `TransactionForm` is rendered, pass the `type` prop (this will compile after Task 12 refactors TransactionForm):

```tsx
<TransactionForm
  symbol={transactionForm.symbol}
  assetClassId={transactionForm.assetClassId}
  type={type}
  initialType={transactionForm.type}
  onSubmit={...}
  onCancel={...}
/>
```

- [ ] **Step 7: Remove `isFixedIncomeClass` import**

Remove `import { isFixedIncomeClass } from "../utils/assetClass";` from `HoldingsTable.tsx`.

- [ ] **Step 8: Remove the `showAddAsset` prop and AddAssetForm from HoldingsTable**

The add form will live in the new `AssetClassHoldings` page, not inside `HoldingsTable`. Remove:
- `showAddAsset` / `enableAddAsset` prop and state
- The "Add Asset" button in the header
- The `<AddAssetForm>` rendering
- The `AddAssetForm` import

- [ ] **Step 9: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors (may have test failures — fixed in later tasks)

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/HoldingsTable.tsx
git commit -m "feat: refactor HoldingsTable with type-specific columns, remove grouping"
```

### Task 11: Update `AddAssetForm` — accept `type` + `assetClassId` props

**Files:**
- Modify: `frontend/src/components/AddAssetForm.tsx`

- [ ] **Step 1: Update props interface**

Replace `assetClasses` prop with `type` and `assetClassId`:

```typescript
type AssetClassType = "stock" | "crypto" | "fixed_income";

interface AddAssetFormProps {
  type: AssetClassType;
  assetClassId: string;
  onSubmit: (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => Promise<unknown>;
  onCancel: () => void;
}
```

- [ ] **Step 2: Simplify the component**

1. Remove `assetClassId` state (now a prop)
2. Remove the `selectedClass` and `isFixedIncomeClass` logic — replace with `const isFixedIncome = type === "fixed_income";`
3. Remove the asset class dropdown from the form
4. Remove `isFixedIncomeClass` import
5. For fixed income, default to `useCustomSymbol = true` mode (free text name input)
6. Update `handleSubmit` to use `assetClassId` prop directly

For fixed income type, initialize `useCustomSymbol` to `true`:

```typescript
const [useCustomSymbol, setUseCustomSymbol] = useState(type === "fixed_income");
```

And hide the "Use custom name" / "Search market" toggle for fixed income (it should always be custom).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/AddAssetForm.tsx
git commit -m "feat: simplify AddAssetForm to accept type prop directly"
```

### Task 12: Refactor `TransactionForm` — accept `type` prop instead of `isFixedIncome`

**Files:**
- Modify: `frontend/src/components/TransactionForm.tsx`

- [ ] **Step 1: Replace `isFixedIncome` prop with `type` prop**

Update the interface and component:

```typescript
type AssetClassType = "stock" | "crypto" | "fixed_income";

interface TransactionFormProps {
  symbol: string;
  assetClassId: string;
  type: AssetClassType;
  initialType?: TransactionType;
  onSubmit: (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => Promise<unknown>;
  onCancel: () => void;
}
```

Inside the component, derive the boolean:

```typescript
const isFixedIncome = type === "fixed_income";
```

The rest of the component logic stays the same since it already uses `isFixedIncome` internally.

- [ ] **Step 2: Update callers**

In `HoldingsTable.tsx` (Task 10), where `TransactionForm` is rendered, change:

```tsx
// Before:
isFixedIncome={type === "fixed_income"}
// After:
type={type}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/TransactionForm.tsx
git commit -m "feat: replace isFixedIncome with type prop in TransactionForm"
```

### Task 13: Remove `isFixedIncomeClass` utility

**Files:**
- Delete: `frontend/src/utils/assetClass.ts`

- [ ] **Step 1: Verify no remaining imports**

Run: `grep -r "isFixedIncomeClass\|utils/assetClass" frontend/src/ --include="*.ts" --include="*.tsx"`
Expected: No results (after previous tasks removed all usages)

- [ ] **Step 2: Delete the file**

```bash
rm frontend/src/utils/assetClass.ts
```

- [ ] **Step 3: Commit**

```bash
git add -u frontend/src/utils/assetClass.ts
git commit -m "chore: remove isFixedIncomeClass utility, replaced by type field"
```

---

## Chunk 4: Frontend — New AssetClassHoldings Page & Route

### Task 14: Create `AssetClassHoldings` page

**Files:**
- Create: `frontend/src/pages/AssetClassHoldings.tsx`

- [ ] **Step 1: Write the page component**

```tsx
import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { useAssetClasses } from "../hooks/useAssetClasses";
import { usePortfolio } from "../hooks/usePortfolio";
import { useTransactions } from "../hooks/useTransactions";
import { useFundamentals } from "../hooks/useFundamentals";
import { HoldingsTable } from "../components/HoldingsTable";
import { AddAssetForm } from "../components/AddAssetForm";
import type { QuarantineStatus, Transaction } from "../types";
import api from "../services/api";

export default function AssetClassHoldings() {
  const { assetClassId } = useParams<{ assetClassId: string }>();
  const { assetClasses } = useAssetClasses();
  const { holdings, loading: portfolioLoading, refresh: refreshPortfolio } = usePortfolio();
  const {
    transactions,
    fetchTransactions,
    createTransaction,
    updateTransaction,
    deleteTransaction,
  } = useTransactions();
  const { scores: fundamentalsScores, refreshAll: refreshAllScores, refresh: refreshScores } = useFundamentals();

  const [quarantineStatuses, setQuarantineStatuses] = useState<QuarantineStatus[]>([]);
  const [dividendsBySymbol, setDividendsBySymbol] = useState<Map<string, { income: number; currency: string }>>(new Map());

  const assetClass = assetClasses.find((ac) => ac.id === assetClassId);
  const classHoldings = holdings.filter((h) => h.asset_class_id === assetClassId);
  const type = assetClass?.type ?? "stock";

  const totalValue = classHoldings.reduce(
    (sum, h) => sum + (h.current_value ?? h.total_cost),
    0
  );
  const currency = classHoldings[0]?.currency ?? "USD";

  const fetchQuarantineStatuses = useCallback(async () => {
    try {
      const res = await api.get<QuarantineStatus[]>("/quarantine/status");
      setQuarantineStatuses(res.data);
    } catch {
      // silently fail
    }
  }, []);

  const fetchDividends = useCallback(async () => {
    try {
      const res = await api.get<{ dividends: Array<{ assets: Array<{ symbol: string; annual_income: number; currency: string }> }> }>("/portfolio/dividends");
      const map = new Map<string, { income: number; currency: string }>();
      for (const cls of res.data.dividends) {
        for (const asset of cls.assets) {
          map.set(asset.symbol, { income: asset.annual_income, currency: asset.currency });
        }
      }
      setDividendsBySymbol(map);
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    fetchQuarantineStatuses();
    fetchDividends();
  }, [fetchQuarantineStatuses, fetchDividends]);

  const handleCreateTransaction = async (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => {
    await createTransaction(data);
    refreshPortfolio();
    fetchQuarantineStatuses();
  };

  const handleUpdateTransaction = async (id: string, data: Partial<Transaction>) => {
    await updateTransaction(id, data);
    refreshPortfolio();
  };

  const handleDeleteTransaction = async (id: string) => {
    await deleteTransaction(id);
    refreshPortfolio();
    fetchQuarantineStatuses();
  };

  const handleDeleteHolding = async (symbol: string) => {
    await api.delete(`/transactions/by-symbol/${symbol}`);
    refreshPortfolio();
    fetchQuarantineStatuses();
  };

  const handleChangeAssetClass = async (symbol: string, newAssetClassId: string) => {
    await api.put(`/transactions/by-symbol/${symbol}/asset-class`, null, {
      params: { asset_class_id: newAssetClassId },
    });
    refreshPortfolio();
  };

  const CURRENCY_SYMBOLS: Record<string, string> = {
    BRL: "R$",
    USD: "$",
    EUR: "€",
    GBP: "£",
  };
  const currencySymbol = CURRENCY_SYMBOLS[currency] ?? `${currency} `;

  if (!assetClass) {
    return (
      <div className="space-y-4">
        <Link to="/portfolio" className="text-primary hover:text-primary-hover text-base">
          ‹ Portfolio
        </Link>
        <p className="text-text-muted">Asset class not found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link to="/portfolio" className="text-primary hover:text-primary-hover text-base">
          ‹ Portfolio
        </Link>
        <span className="text-text-muted">/</span>
        <h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">
          {assetClass.name}
        </h1>
        <span className="ml-auto text-text-muted text-base">
          Total: {currencySymbol}{totalValue.toFixed(2)}
        </span>
      </div>

      {/* Always visible — no cancel action needed */}
      <AddAssetForm
        type={type}
        assetClassId={assetClassId!}
        onSubmit={handleCreateTransaction}
        onCancel={() => {/* no-op: form is always visible */}}
      />

      <HoldingsTable
        holdings={classHoldings}
        assetClassId={assetClassId!}
        assetClasses={assetClasses}
        type={type}
        loading={portfolioLoading}
        quarantineStatuses={quarantineStatuses}
        transactions={transactions}
        dividendsBySymbol={dividendsBySymbol}
        fundamentalsScores={fundamentalsScores}
        onRefreshAllScores={async () => {
          await refreshAllScores();
          setTimeout(() => refreshScores(), 5000);
          setTimeout(() => refreshScores(), 15000);
          setTimeout(() => refreshScores(), 30000);
        }}
        onFetchTransactions={fetchTransactions}
        onCreateTransaction={handleCreateTransaction}
        onUpdateTransaction={handleUpdateTransaction}
        onDeleteTransaction={handleDeleteTransaction}
        onDeleteHolding={handleDeleteHolding}
        onChangeAssetClass={handleChangeAssetClass}
      />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/AssetClassHoldings.tsx
git commit -m "feat: create AssetClassHoldings drill-down page"
```

### Task 15: Add route in `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add import and route**

Add import:

```typescript
import AssetClassHoldings from "./pages/AssetClassHoldings";
```

Add route after the `/portfolio` route:

```tsx
<Route path="/portfolio/:assetClassId" element={<AssetClassHoldings />} />
```

Full routes section:

```tsx
<Routes>
  <Route path="/" element={<Dashboard />} />
  <Route path="/portfolio" element={<Portfolio />} />
  <Route path="/portfolio/:assetClassId" element={<AssetClassHoldings />} />
  <Route path="/settings" element={<Settings />} />
  <Route path="/market" element={<Market />} />
  <Route path="/fundamentals/:symbol" element={<Fundamentals />} />
</Routes>
```

- [ ] **Step 2: Verify app compiles and runs**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: add /portfolio/:assetClassId route"
```

---

## Chunk 5: Fix Tests & Final Polish

### Task 16: Update existing tests for new interfaces

**Files:**
- Modify: `frontend/src/components/__tests__/AssetClassesTable.test.tsx`
- Modify: `frontend/src/components/__tests__/HoldingsTable.test.tsx`

- [ ] **Step 1: Update AssetClassesTable test mock data**

Add `type` and `country` to mock classes:

```typescript
const mockClasses: AssetClass[] = [
  {
    id: "1",
    user_id: "u1",
    name: "Stocks",
    target_weight: 60,
    country: "US",
    type: "stock",
    created_at: "2024-01-01",
    updated_at: "2024-01-01",
  },
  {
    id: "2",
    user_id: "u1",
    name: "Bonds",
    target_weight: 40,
    country: "US",
    type: "fixed_income",
    created_at: "2024-01-01",
    updated_at: "2024-01-01",
  },
];
```

Also wrap the `AssetClassesTable` render in `MemoryRouter` (needed now that it uses `useNavigate`):

```typescript
import { MemoryRouter } from "react-router-dom";

// In each render call:
render(
  <MemoryRouter>
    <AssetClassesTable ... />
  </MemoryRouter>
);
```

- [ ] **Step 2: Update HoldingsTable test mock data and props**

Add `type` and `country` to mock asset classes. Add `type` and `assetClassId` props:

```typescript
const mockAssetClasses: AssetClass[] = [
  { id: "c1", user_id: "u1", name: "Stocks", target_weight: 60, country: "US", type: "stock", created_at: "2024-01-01", updated_at: "2024-01-01" },
];
```

Update all render calls to include the new required props:

```tsx
<HoldingsTable
  holdings={mockHoldings}
  assetClasses={mockAssetClasses}
  assetClassId="c1"
  type="stock"
  loading={false}
  ...
/>
```

Wrap in `MemoryRouter` since `HoldingsTable` uses `useNavigate`.

- [ ] **Step 3: Run all frontend tests**

Run: `cd frontend && npm run test`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/__tests__/AssetClassesTable.test.tsx frontend/src/components/__tests__/HoldingsTable.test.tsx
git commit -m "test: update tests for new type prop and interfaces"
```

### Task 17: Run full test suite and fix any remaining issues

- [ ] **Step 1: Run backend tests**

Run: `cd backend && pytest -v`
Expected: All pass

- [ ] **Step 2: Run frontend tests**

Run: `cd frontend && npm run test`
Expected: All pass

- [ ] **Step 3: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: No errors

- [ ] **Step 5: Fix any issues found, commit**

If any tests fail or build errors occur, fix them and commit:

```bash
git add -A
git commit -m "fix: resolve remaining test/build issues from asset class holdings refactor"
```

### Task 18: Manual smoke test

- [ ] **Step 1: Start backend**

Run: `cd backend && python -m uvicorn app.main:app --reload`
Check: Server starts, backfill runs (check logs for type assignments)

- [ ] **Step 2: Start frontend**

Run: `cd frontend && npm run dev`
Check:
- Portfolio page shows asset classes with Type column and chevrons
- Clicking an asset class navigates to `/portfolio/:id`
- Detail page shows correct header, always-visible add form, type-specific columns
- Fixed income page hides Qty/Price/Score/Div columns
- Crypto page hides Score/Div columns
- Add form fields match the type
- Can add a new asset, expand transaction history, buy/sell
- Back link returns to Portfolio page

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: smoke test fixes for asset class holdings"
```
