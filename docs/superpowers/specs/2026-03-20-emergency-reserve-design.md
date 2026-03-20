# Emergency Reserve Asset Class

## Summary

Add a special "Emergency Reserve" asset class category that is excluded from portfolio weight calculations. It appears as a separate row above the totals in the class summary table, showing only its current value with no target weight.

## Constraints

- Only one emergency reserve per user
- No target weight — displays current value only (API silently overrides `target_weight` to 0)
- Excluded from grand total used for percentage calculations of regular asset classes
- Can hold any type of asset (stocks, crypto, fixed income)
- Uses `type: "fixed_income"` as default when created, but user can choose any type

## Backend Changes

### Model (`backend/app/models/asset_class.py`)

Add `is_emergency_reserve` boolean column using SQLAlchemy 2.0 style:

```python
is_emergency_reserve: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

### Database Migration

Since the project uses `Base.metadata.create_all()` (which only creates new tables, not columns), add explicit migration logic at startup:

```python
ALTER TABLE asset_classes ADD COLUMN is_emergency_reserve BOOLEAN NOT NULL DEFAULT 0
```

Wrap in try/except to be idempotent (column already exists case).

### Schemas (`backend/app/schemas/asset_class.py`)

- `AssetClassCreate`: Add optional `is_emergency_reserve: bool = False`
- `AssetClassUpdate`: Add optional `is_emergency_reserve: bool | None = None`
- `AssetClassResponse`: Add `is_emergency_reserve: bool`

### Validation (`backend/app/routers/asset_classes.py`)

- On create: if `is_emergency_reserve=True`, check no other emergency reserve exists for the user. Return 400 if one already exists.
- On update: if setting `is_emergency_reserve=True`, same uniqueness check.
- When creating an emergency reserve, silently set `target_weight = 0` regardless of input.
- Add `is_emergency_reserve=body.is_emergency_reserve` to the `AssetClass()` constructor call.
- On delete: no special handling — user can delete and re-create later.

### Recommendation Service (`backend/app/services/recommendation.py`)

- Exclude emergency reserve holdings from `total_value` calculation.
- Filter out emergency reserve asset class when computing recommendations.

### Portfolio Endpoints (`backend/app/routers/portfolio.py`)

- `/portfolio/summary` — `enrich_holdings()`: exclude emergency reserve holdings from the total used for `actual_weight` calculations. Emergency reserve holdings should have `actual_weight: None` or `0`.
- `/portfolio/dividends` — include emergency reserve dividends in the per-class breakdown but exclude from `total_annual_income` aggregate (show separately).

## Frontend Changes

### Types (`frontend/src/types/index.ts`)

Add `is_emergency_reserve: boolean` to `AssetClass` interface.

### Weight Calculation (`ClassSummaryTable.tsx` — `computeClassSummaries()`)

- Change return type to `{ regular: ClassSummary[], reserve: ClassSummary | null }`
- Compute `grandTotalBRL` using only regular holdings
- Compute percentages for regular classes against the regular-only grand total
- Compute emergency reserve value separately (no percentage, no target weight)
- Update all callers (`Dashboard.tsx`) to destructure the new return shape

### Charts (`PortfolioCompositionChart.tsx`, `AllocationChart.tsx`)

- Pass only `regular` summaries to these chart components
- Emergency reserve must not appear in pie charts or allocation bar charts

### Table Rendering (`ClassSummaryTable.tsx`)

- Render regular asset class rows as today
- Before the totals row, render the emergency reserve row:
  - Visually distinct (subtle separator line above it)
  - Shows: name ("Emergency Reserve"), total value, total value in BRL
  - No actual %, no target %, no diff column
- The totals row shows only the regular asset classes total
- Show a "Portfolio + Reserve" grand total row below the regular totals

### AssetClassHoldings Detail Page

- When navigating to the emergency reserve detail page, hide the percentage/weight columns
- Show the same holdings table but without allocation-related data

### Create Form

- Add a dedicated button/toggle to create the emergency reserve
- Once created, hide the option to create another one
- Reappears if the user deletes the existing emergency reserve
- Update `onCreateClass` callback signature to accept `is_emergency_reserve` parameter

### "Where to Invest" calculation

- Exclude emergency reserve from the `computeWhereToInvest()` function

### Edit Target Weights

- Emergency reserve should not appear in the target weight editing mode

## Testing

### Backend
- Uniqueness constraint: creating two emergency reserves returns 400
- Emergency reserve returned with `is_emergency_reserve: true` flag
- `target_weight` forced to 0 on create/update
- Recommendation service excludes emergency reserve from calculations
- Portfolio summary `actual_weight` excludes emergency reserve from total
- Delete and re-create works

### Frontend
- `computeClassSummaries` excludes emergency reserve from `grandTotalBRL`
- Regular class percentages calculated against regular-only total
- Emergency reserve row renders above totals with correct value
- Charts do not include emergency reserve
- Create button hidden when emergency reserve exists
- Target weight editing excludes emergency reserve
