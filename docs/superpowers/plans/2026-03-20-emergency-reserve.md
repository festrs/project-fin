# Emergency Reserve Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a special "Emergency Reserve" asset class excluded from portfolio weight calculations, displayed as a separate row above totals in the summary table.

**Architecture:** Add `is_emergency_reserve` boolean to the AssetClass model with a migration. Backend validates uniqueness (one per user) and forces `target_weight=0`. Frontend splits `computeClassSummaries` return into regular + reserve, excludes reserve from charts and weight calculations.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, SQLite, React 19, TypeScript

---

### Task 1: Backend — Database migration

**Files:**
- Modify: `backend/app/migrations/__init__.py:138-141`

- [ ] **Step 1: Add migration function**

Add after `_001_decimal_money` (line 136):

```python
def _002_emergency_reserve_flag(cur: sqlite3.Cursor) -> None:
    """Add is_emergency_reserve boolean column to asset_classes."""
    if not _table_exists(cur, "asset_classes"):
        return
    columns = _get_columns(cur, "asset_classes")
    if "is_emergency_reserve" not in columns:
        cur.execute("ALTER TABLE asset_classes ADD COLUMN is_emergency_reserve BOOLEAN NOT NULL DEFAULT 0")
```

Update `_MIGRATIONS` list:

```python
_MIGRATIONS = [
    _001_decimal_money,
    _002_emergency_reserve_flag,
]
```

- [ ] **Step 2: Verify migration runs**

Run: `cd backend && python -c "from app.migrations import run_all; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/migrations/__init__.py
git commit -m "feat: add migration for is_emergency_reserve column"
```

---

### Task 2: Backend — Model and schemas

**Files:**
- Modify: `backend/app/models/asset_class.py:4,18`
- Modify: `backend/app/schemas/asset_class.py`

- [ ] **Step 1: Update AssetClass model**

In `backend/app/models/asset_class.py`, add `Boolean` to the import on line 4:

```python
from sqlalchemy import String, Float, DateTime, ForeignKey, Boolean
```

Add after `target_weight` (line 18):

```python
is_emergency_reserve: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

- [ ] **Step 2: Update schemas**

In `backend/app/schemas/asset_class.py`:

`AssetClassCreate` — add field:
```python
is_emergency_reserve: bool = False
```

`AssetClassUpdate` — add field:
```python
is_emergency_reserve: Optional[bool] = None
```

`AssetClassResponse` — add field (after `type`):
```python
is_emergency_reserve: bool
```

- [ ] **Step 3: Verify imports work**

Run: `cd backend && python -c "from app.models.asset_class import AssetClass; from app.schemas.asset_class import AssetClassCreate, AssetClassResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/asset_class.py backend/app/schemas/asset_class.py
git commit -m "feat: add is_emergency_reserve to model and schemas"
```

---

### Task 3: Backend — Router validation (uniqueness + target_weight override)

**Files:**
- Modify: `backend/app/routers/asset_classes.py:24-34,39-63`

- [ ] **Step 1: Update create endpoint (lines 24-34)**

Replace the `create_asset_class` function body:

```python
@router.post("", response_model=AssetClassResponse, status_code=201)
@limiter.limit(CRUD_LIMIT)
def create_asset_class(
    request: Request,
    body: AssetClassCreate,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    if body.is_emergency_reserve:
        existing = (
            db.query(AssetClass)
            .filter(AssetClass.user_id == x_user_id, AssetClass.is_emergency_reserve == True)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Emergency reserve already exists")
        body.target_weight = 0.0

    ac = AssetClass(
        user_id=x_user_id,
        name=body.name,
        target_weight=body.target_weight,
        country=body.country,
        type=body.type,
        is_emergency_reserve=body.is_emergency_reserve,
    )
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac
```

- [ ] **Step 2: Update update endpoint (lines 39-63)**

Add validation in `update_asset_class` after the 404 check (line 52):

```python
    if body.is_emergency_reserve is True and not ac.is_emergency_reserve:
        existing = (
            db.query(AssetClass)
            .filter(
                AssetClass.user_id == x_user_id,
                AssetClass.is_emergency_reserve == True,
                AssetClass.id != ac_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Emergency reserve already exists")
    if body.is_emergency_reserve is not None:
        ac.is_emergency_reserve = body.is_emergency_reserve
    # Force target_weight to 0 for emergency reserve
    if ac.is_emergency_reserve:
        ac.target_weight = 0.0
        body.target_weight = None  # prevent overwrite below
```

- [ ] **Step 3: Run backend to verify**

Run: `cd backend && python -c "from app.routers.asset_classes import router; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/asset_classes.py
git commit -m "feat: add emergency reserve validation in asset class router"
```

---

### Task 4: Backend — Exclude emergency reserve from recommendation service

**Files:**
- Modify: `backend/app/services/recommendation.py:40-45,62-75`

- [ ] **Step 1: Filter out emergency reserve asset classes and holdings**

In `get_recommendations` method, after querying asset_classes (line 40-44), add a filter:

```python
        asset_classes = (
            self.db.query(AssetClass)
            .filter(AssetClass.user_id == user_id, AssetClass.is_emergency_reserve == False)
            .all()
        )
```

Also, in the asset_values loop (lines 63-73), add a guard to skip holdings whose class is not in `class_map` (which now excludes reserve):

```python
        # Calculate current values using market prices
        asset_values: dict[str, Decimal] = {}
        for h in holdings:
            ac = class_map.get(h["asset_class_id"])
            if not ac:
                continue  # skip holdings in emergency reserve (filtered out of class_map)
            class_name = ac.name
            country = ac.country
```

This ensures reserve holdings are excluded from both `asset_values` and `total_value`.

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/recommendation.py
git commit -m "feat: exclude emergency reserve from recommendations"
```

---

### Task 5: Backend — Exclude emergency reserve from portfolio enrich_holdings total

**Files:**
- Modify: `backend/app/routers/portfolio.py:47-52`

- [ ] **Step 1: Pass emergency reserve flag through class_map**

In `portfolio_summary` (line 47-55), add the flag to `class_map`:

```python
    for ac in asset_classes:
        class_map[ac.id] = {
            "name": ac.name,
            "target_weight": ac.target_weight,
            "country": ac.country,
            "is_emergency_reserve": ac.is_emergency_reserve,
        }
```

- [ ] **Step 2: Update enrich_holdings to exclude emergency reserve from total_value**

In `backend/app/services/portfolio.py`, in `enrich_holdings` method, change the total_value calculation (lines 268-275):

Replace:
```python
        # Calculate total portfolio value
        total_value = Decimal("0")
        for h in qty_holdings:
            price = prices.get(h["symbol"])
            if price is not None:
                total_value += price.amount * Decimal(str(h["quantity"]))
        for h in val_holdings:
            total_value += h["total_cost"].amount
```

With:
```python
        # Calculate total portfolio value (excluding emergency reserve)
        total_value = Decimal("0")
        for h in qty_holdings:
            if class_map.get(h["asset_class_id"], {}).get("is_emergency_reserve"):
                continue
            price = prices.get(h["symbol"])
            if price is not None:
                total_value += price.amount * Decimal(str(h["quantity"]))
        for h in val_holdings:
            if class_map.get(h["asset_class_id"], {}).get("is_emergency_reserve"):
                continue
            total_value += h["total_cost"].amount
```

- [ ] **Step 3: Set actual_weight to 0 for reserve holdings in enrich_holdings**

In the enrichment loop (lines 278-319), add a check at the top of the loop body. After `class_info = class_map.get(...)` (line 280), add:

```python
            is_reserve = class_info.get("is_emergency_reserve", False)
```

Then in both the `if h["quantity"] is None` branch (line 287) and the quantity-based branches (lines 301, 306), override `actual_weight` for reserve holdings:

```python
                actual_weight = 0.0 if is_reserve else actual_weight
```

This prevents reserve holdings from getting incorrect weight percentages computed against the non-reserve total.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/portfolio.py backend/app/services/portfolio.py
git commit -m "feat: exclude emergency reserve from portfolio weight calculations"
```

---

### Task 6: Backend — Exclude emergency reserve from allocation and dividends

**Files:**
- Modify: `backend/app/services/portfolio.py:186-232` (get_allocation)
- Modify: `backend/app/routers/portfolio.py:136-243` (dividends endpoint)

- [ ] **Step 1: Filter emergency reserve from get_allocation**

In `backend/app/services/portfolio.py`, in `get_allocation` method (line 199), add a filter to skip emergency reserve classes:

```python
        for ac in asset_classes:
            if ac.is_emergency_reserve:
                continue
            class_holdings = holdings_by_class.get(ac.id, [])
```

This ensures the AllocationChart never receives emergency reserve data.

- [ ] **Step 2: Exclude emergency reserve from dividends total_annual_income**

In `backend/app/routers/portfolio.py`, in `portfolio_dividends` (lines 235-238), exclude emergency reserve from the total:

Replace:
```python
    total_annual = sum(
        (Decimal(ct["annual_income"]["amount"]) for ct in class_totals.values()),
        Decimal("0"),
    )
```

With:
```python
    total_annual = sum(
        (
            Decimal(ct["annual_income"]["amount"])
            for cid, ct in class_totals.items()
            if not (class_map.get(cid) and class_map[cid].is_emergency_reserve)
        ),
        Decimal("0"),
    )
```

Emergency reserve dividends will still appear in the per-class breakdown (`dividends` list) but are excluded from the aggregate total.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/portfolio.py backend/app/routers/portfolio.py
git commit -m "feat: exclude emergency reserve from allocation and dividend totals"
```

---

### Task 7: Frontend — Types and hook

**Files:**
- Modify: `frontend/src/types/index.ts:8-17`
- Modify: `frontend/src/hooks/useAssetClasses.ts:30-37`

- [ ] **Step 1: Add is_emergency_reserve to AssetClass interface**

In `frontend/src/types/index.ts`, add to the `AssetClass` interface (after `type` on line 14):

```typescript
is_emergency_reserve: boolean;
```

- [ ] **Step 2: Update createClass in useAssetClasses hook**

In `frontend/src/hooks/useAssetClasses.ts`, update the `createClass` callback (line 30):

```typescript
const createClass = useCallback(async (
    name: string,
    targetWeight: number,
    type: "stock" | "crypto" | "fixed_income" = "stock",
    isEmergencyReserve: boolean = false
  ) => {
    const res = await api.post<AssetClass>("/asset-classes", {
      name,
      target_weight: targetWeight,
      type,
      is_emergency_reserve: isEmergencyReserve,
    });
    setAssetClasses((prev) => { _cache = [...prev, res.data]; return _cache; });
    return res.data;
  }, []);
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/hooks/useAssetClasses.ts
git commit -m "feat: add is_emergency_reserve to frontend types and hook"
```

---

### Task 8: Frontend — Update computeClassSummaries to separate reserve

**Files:**
- Modify: `frontend/src/components/ClassSummaryTable.tsx:7-16,51-113`

- [ ] **Step 1: Update return type**

Change the `ClassSummary` export and add a result type (lines 7-16):

```typescript
export interface ClassSummary {
  classId: string;
  className: string;
  totalValue: number;
  totalValueBRL: number;
  percentage: number;
  targetWeight: number;
  diff: number;
  currency: string;
  isEmergencyReserve: boolean;
}

export interface ClassSummaryResult {
  regular: ClassSummary[];
  reserve: ClassSummary | null;
  grandTotalBRL: number;
}
```

- [ ] **Step 2: Rewrite computeClassSummaries**

Replace the function (lines 51-113):

```typescript
export function computeClassSummaries(
  holdings: Holding[],
  assetClasses: AssetClass[],
  usdToBrl: number
): ClassSummaryResult {
  const classMap = new Map(assetClasses.map((ac) => [ac.id, ac]));

  const totals = new Map<string, { value: number; currency: string }>();
  for (const h of holdings.filter((h) => classMap.has(h.asset_class_id))) {
    const val = moneyToNumber(h.current_value ?? h.total_cost);
    const cur = h.total_cost.currency;
    const existing = totals.get(h.asset_class_id) ?? { value: 0, currency: cur };
    existing.value += val;
    totals.set(h.asset_class_id, existing);
  }

  // Separate regular and reserve values
  let grandTotalBRL = 0;
  const classValues: { classId: string; value: number; valueBRL: number; currency: string }[] = [];
  let reserveValue: { classId: string; value: number; valueBRL: number; currency: string } | null = null;

  for (const [classId, { value, currency }] of totals) {
    const ac = classMap.get(classId);
    const valueBRL = currency === "USD" ? value * usdToBrl : value;
    if (ac?.is_emergency_reserve) {
      reserveValue = { classId, value, valueBRL, currency };
    } else {
      grandTotalBRL += valueBRL;
      classValues.push({ classId, value, valueBRL, currency });
    }
  }

  const regular: ClassSummary[] = [];
  const seenClassIds = new Set<string>();

  for (const { classId, value, valueBRL, currency } of classValues) {
    const ac = classMap.get(classId);
    const percentage = grandTotalBRL > 0 ? (valueBRL / grandTotalBRL) * 100 : 0;
    const targetWeight = ac?.target_weight ?? 0;
    regular.push({
      classId,
      className: ac?.name ?? classId,
      totalValue: value,
      totalValueBRL: valueBRL,
      percentage,
      targetWeight,
      diff: percentage - targetWeight,
      currency,
      isEmergencyReserve: false,
    });
    seenClassIds.add(classId);
  }

  // Include asset classes with no holdings yet (excluding reserve)
  for (const ac of assetClasses) {
    if (!seenClassIds.has(ac.id) && !ac.is_emergency_reserve) {
      regular.push({
        classId: ac.id,
        className: ac.name,
        totalValue: 0,
        totalValueBRL: 0,
        percentage: 0,
        targetWeight: ac.target_weight,
        diff: -ac.target_weight,
        currency: "BRL",
        isEmergencyReserve: false,
      });
    }
  }

  regular.sort((a, b) => b.totalValueBRL - a.totalValueBRL);

  // Build reserve summary
  let reserve: ClassSummary | null = null;
  const reserveClass = assetClasses.find((ac) => ac.is_emergency_reserve);
  if (reserveClass) {
    reserve = {
      classId: reserveClass.id,
      className: reserveClass.name,
      totalValue: reserveValue?.value ?? 0,
      totalValueBRL: reserveValue?.valueBRL ?? 0,
      percentage: 0,
      targetWeight: 0,
      diff: 0,
      currency: reserveValue?.currency ?? "BRL",
      isEmergencyReserve: true,
    };
  }

  return { regular, reserve, grandTotalBRL };
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ClassSummaryTable.tsx
git commit -m "feat: separate emergency reserve from regular summaries"
```

---

### Task 9: Frontend — Update ClassSummaryTable rendering

**Files:**
- Modify: `frontend/src/components/ClassSummaryTable.tsx:179-610`

- [ ] **Step 1: Update component body to use new return type**

Replace the `summaries` and `grandTotalBRL` lines (around lines 211-212):

```typescript
  const { regular: summaries, reserve: reserveSummary, grandTotalBRL } = computeClassSummaries(holdings, assetClasses, usdToBrl);
```

Remove the old `grandTotalBRL` calculation (the line `const grandTotalBRL = summaries.reduce(...)` around line 212).

- [ ] **Step 2: Verify implicit exclusions (no code changes needed)**

The following are automatically handled because `summaries` is now regular-only:
- `handleStartEditing` (lines 258-264) — only initializes weights for regular classes
- `totalTargetWeight` (lines 245-248) — sums only regular target weights
- `computeWhereToInvest` (line 241) — called with `summaries` which excludes reserve
- `computeTopUnderweightClasses` (line 242) — same, excludes reserve

- [ ] **Step 3: Add reserve row before totals in tfoot**

In the `<tfoot>` section (line 540), add the reserve row before the totals row (before line 579):

```tsx
            {reserveSummary && (
              <tr className="border-t border-[var(--glass-border)]">
                <td
                  className="py-2 px-2 font-medium text-text-secondary cursor-pointer hover:text-primary transition-colors"
                  onClick={() => navigate(`/portfolio/${reserveSummary.classId}`)}
                >
                  {reserveSummary.className}
                </td>
                <td className="py-2 px-2 text-right text-text-secondary">
                  {formatValue(reserveSummary.totalValue, reserveSummary.currency)}
                </td>
                <td className="py-2 px-2 text-right text-text-muted">
                  {reserveSummary.currency === "USD"
                    ? formatValue(reserveSummary.totalValueBRL, "BRL")
                    : ""}
                </td>
                <td className="py-2 px-2 text-right text-text-muted">-</td>
                <td className="py-2 px-2 text-right text-text-muted">-</td>
                <td className="py-2 px-2 text-center text-text-muted">-</td>
                <td className="py-2 px-2 text-right text-text-muted">-</td>
                {onDeleteClass && (
                  <td className="py-2 px-2 text-center">
                    <button
                      className="text-text-muted hover:text-negative transition-colors"
                      title="Delete emergency reserve"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm('Delete emergency reserve?')) {
                          onDeleteClass(reserveSummary.classId);
                        }
                      }}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </td>
                )}
              </tr>
            )}
```

- [ ] **Step 4: Add "Portfolio + Reserve" total row after the regular totals row**

After the existing totals `<tr>` (around line 596), add:

```tsx
            {reserveSummary && reserveSummary.totalValueBRL > 0 && (
              <tr className="font-semibold text-text-secondary">
                <td className="py-2 px-2">Total + Reserve</td>
                <td className="py-2 px-2" />
                <td className="py-2 px-2 text-right">
                  {formatValue(grandTotalBRL + reserveSummary.totalValueBRL, "BRL")}
                </td>
                <td colSpan={onDeleteClass ? 5 : 4} className="py-2 px-2" />
              </tr>
            )}
```

- [ ] **Step 5: Update the create form to support emergency reserve**

Add state for tracking if reserve exists. Near the other state declarations (line 201), add:

```typescript
  const hasEmergencyReserve = assetClasses.some((ac) => ac.is_emergency_reserve);
```

After the existing create form's Cancel button (around line 381), add a dedicated "Add Emergency Reserve" button. Place it inside the header `div` next to the existing "+" button (line 304-314):

```tsx
          {onCreateClass && !hasEmergencyReserve && (
            <button
              onClick={async () => {
                if (window.confirm('Create Emergency Reserve class?')) {
                  await onCreateClass("Emergency Reserve", 0, "fixed_income", true);
                }
              }}
              className="text-xs text-text-muted hover:text-primary transition-colors border border-[var(--glass-border)] rounded-lg px-2 py-1"
              title="Add emergency reserve"
            >
              + Reserve
            </button>
          )}
```

- [ ] **Step 6: Update onCreateClass prop type**

Update the `ClassSummaryTableProps` interface (line 40):

```typescript
  onCreateClass?: (name: string, targetWeight: number, type: "stock" | "crypto" | "fixed_income", isEmergencyReserve?: boolean) => Promise<unknown>;
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ClassSummaryTable.tsx
git commit -m "feat: render emergency reserve row and create button in summary table"
```

---

### Task 10: Frontend — Update Dashboard to use new return type

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx:74-78,125-133`

- [ ] **Step 1: Update classSummaries for chart**

Replace lines 74-78:

```typescript
  const { regular: regularSummaries } = computeClassSummaries(holdings, assetClasses, usdToBrl);
  const classSummaries = regularSummaries.map((s) => ({
    className: s.className,
    percentage: s.percentage,
    targetWeight: s.targetWeight,
  }));
```

- [ ] **Step 2: Update onCreateClass callback**

Replace the `onCreateClass` prop (lines 125-128):

```typescript
            onCreateClass={async (name, weight, type, isEmergencyReserve) => {
              await createClass(name, weight, type, isEmergencyReserve);
              refreshPortfolio();
            }}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: update dashboard to use new class summary return type"
```

---

### Task 11: Frontend — AssetClassHoldings page for emergency reserve

**Files:**
- Modify: `frontend/src/pages/AssetClassHoldings.tsx:166-171`

- [ ] **Step 1: Conditionally hide weight-related info for emergency reserve**

In `AssetClassHoldings.tsx`, the `assetClass` is already resolved on line 31. Add a check after line 33:

```typescript
  const isReserve = assetClass?.is_emergency_reserve ?? false;
```

Then in the header area (line 169-171), conditionally hide the "Total" label or add a "(Reserve)" indicator:

```tsx
        <span className="ml-auto text-text-muted text-base">
          Total: R${totalValueBRL.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          {isReserve && <span className="ml-2 text-xs bg-[var(--glass-primary-soft)] px-2 py-0.5 rounded">(Emergency Reserve)</span>}
        </span>
```

No further changes needed — the HoldingsTable already shows holdings without percentage columns by default for the detail view.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/AssetClassHoldings.tsx
git commit -m "feat: show emergency reserve indicator on detail page"
```

---

### Task 12: Frontend — Verify build and manual test

- [ ] **Step 1: Run TypeScript check and build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no type errors

- [ ] **Step 2: Fix any type errors**

If there are type errors from other files importing `ClassSummary` or calling `computeClassSummaries`, fix them to use the new `ClassSummaryResult` return type.

- [ ] **Step 3: Run frontend tests**

Run: `cd frontend && npm run test`
Expected: Existing tests pass (or update tests that reference old return type)

- [ ] **Step 4: Run backend tests**

Run: `cd backend && pytest`
Expected: All tests pass

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve type errors and test failures for emergency reserve"
```
