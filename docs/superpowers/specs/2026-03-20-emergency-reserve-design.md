# Emergency Reserve Asset Class

## Summary

Add a special "Emergency Reserve" asset class category that is excluded from portfolio weight calculations. It appears as a separate row above the totals in the class summary table, showing only its current value with no target weight.

## Constraints

- Only one emergency reserve per user
- No target weight — displays current value only
- Excluded from grand total used for percentage calculations of regular asset classes
- Can hold any type of asset (stocks, crypto, fixed income)

## Backend Changes

### Model (`backend/app/models/asset_class.py`)

Add `is_emergency_reserve` boolean column:

```python
is_emergency_reserve = Column(Boolean, default=False, nullable=False)
```

### Schemas (`backend/app/schemas/asset_class.py`)

- `AssetClassCreate`: Add optional `is_emergency_reserve: bool = False`
- `AssetClassUpdate`: Add optional `is_emergency_reserve: bool | None = None`
- `AssetClassResponse`: Add `is_emergency_reserve: bool`

### Validation (`backend/app/routers/asset_classes.py`)

- On create: if `is_emergency_reserve=True`, check no other emergency reserve exists for the user. Return 400 if one already exists.
- On update: if setting `is_emergency_reserve=True`, same uniqueness check.
- When creating an emergency reserve, `target_weight` should default to 0 and be ignored.

## Frontend Changes

### Types (`frontend/src/types/index.ts`)

Add `is_emergency_reserve: boolean` to `AssetClass` interface.

### Weight Calculation (`ClassSummaryTable.tsx` — `computeClassSummaries()`)

- Separate holdings into two groups: regular and emergency reserve
- Compute `grandTotalBRL` using only regular holdings
- Compute percentages for regular classes against the regular-only grand total
- Compute emergency reserve value separately (no percentage, no target weight)

### Table Rendering (`ClassSummaryTable.tsx`)

- Render regular asset class rows as today
- Before the totals row, render the emergency reserve row:
  - Visually distinct (e.g., subtle separator line above it)
  - Shows: name ("Emergency Reserve"), total value, total value in BRL
  - No actual %, no target %, no diff column
- The totals row continues to show only the regular asset classes total
- Optionally show a "Portfolio + Reserve" grand total below

### Create Form

- Add a way to create the emergency reserve (e.g., a toggle or dedicated button)
- Once created, hide the option to create another one

### "Where to Invest" calculation

- Exclude emergency reserve from the `computeWhereToInvest()` function

### Edit Target Weights

- Emergency reserve should not appear in the target weight editing mode

## Testing

- Backend: test uniqueness constraint, test that emergency reserve is returned with flag
- Frontend: test that weight calculations exclude emergency reserve, test rendering
