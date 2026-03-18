# Asset Class Holdings: Per-Type Screens Design

## Problem

The current Portfolio page displays all holdings in a single table with a fixed set of columns. This causes issues:

1. **Irrelevant columns** — Fixed income shows "—" for Qty, Avg Price, Current Price, Score, Div
2. **Add form placement** — New assets always appear at the top of the page, even when the target asset class is scrolled far down
3. **No type awareness** — Asset class type is guessed by keyword matching on the name, which is fragile

## Solution

Introduce an explicit `type` field on asset classes and a drill-down navigation pattern: tapping an asset class on the Portfolio page navigates to a dedicated holdings screen with type-specific columns and an always-visible add form.

## Data Model Change

### AssetClass.type field

- New column: `type` (string, not null, database-level default `"stock"`)
- Allowed values: `"stock"`, `"crypto"`, `"fixed_income"` — validated as a `Literal` type in Pydantic schemas
- Set when creating an asset class (required dropdown in the create form)
- The `country` field remains unchanged — it's still relevant for stocks (US vs BR) and fixed income (BR). For crypto it's not meaningful but harmless; no changes needed.

### Migration strategy

On startup, backfill any rows where `type` is the default `"stock"` using name keyword matching:
- Names containing crypto-related terms (from existing `CRYPTO_CLASS_NAMES`) → `"crypto"`
- Names containing "fixed income" or "renda fixa" → `"fixed_income"`
- Everything else stays `"stock"` (the database default ensures safety even if backfill doesn't run)

### Backend scope note

The existing `CRYPTO_CLASS_NAMES` checks in backend services (`market_data.py`, `portfolio.py`, `fundamentals_scheduler.py`, etc.) remain as-is for now. Migrating those to use the `type` field is a follow-up task — it's orthogonal to the frontend drill-down work and can be done independently.

### Cleanup

Remove `isFixedIncomeClass()` utility from `frontend/src/utils/assetClass.ts` — replaced by `assetClass.type` check.

## Routing & Navigation

### New route

`/portfolio/:assetClassId` → `AssetClassHoldings` page. Added in `App.tsx` (or wherever routes are defined).

### Portfolio page changes

- Remove `HoldingsTable` usage from `Portfolio.tsx` (the component itself is kept and reused in the new page)
- Make asset class rows in `AssetClassesTable` clickable — clicking navigates to `/portfolio/:assetClassId`
- Add a chevron (`›`) indicator on each row to signal it's tappable
- Keep the composition chart and dividends table on the main page

### AssetClassHoldings page

- Header: back link (`‹ Portfolio`), class name, total value
- Always-visible add form with type-specific fields
- Holdings table with type-specific columns
- Expandable transaction history per holding (same as today)
- Buy/Sell/Delete/Change Asset Class actions per holding (same as today — moving a holding to a different class removes it from the current view)

### Data fetching strategy

The existing `GET /api/portfolio/summary` returns all holdings. The new page filters client-side by `asset_class_id`. No new backend endpoint needed.

## Type-Specific Columns

### Holdings table columns by type

| Column | stock | crypto | fixed_income |
|---|---|---|---|
| Symbol | yes | yes | yes (as "Name") |
| Qty | yes | yes | no |
| Avg Price | yes | yes | no |
| Current Price | yes | yes | no |
| Current Value | yes | yes | yes (as "Total Value") |
| Gain/Loss | yes | yes | no |
| Target % | yes | yes | yes |
| Actual % | yes | yes | yes |
| Div (year) | yes | no | no |
| Score | yes | no | no |

For fixed income, the `Holding.symbol` field is reused to display the name (e.g. "CDB IPCA+ 2029"). The column header just renders as "Name" instead of "Symbol".

### Add form fields by type

| Field | stock | crypto | fixed_income |
|---|---|---|---|
| Symbol (search) | yes | yes | no |
| Name (free text) | no | no | yes |
| Qty | yes | yes | no |
| Unit Price | yes | yes | no |
| Total Value | no (auto-calc) | no (auto-calc) | yes |
| Currency | yes | yes | yes |
| Date | yes | yes | yes |
| Tax | yes | yes | no |
| Notes | yes | yes | yes |

## Component Architecture

### New files

- `pages/AssetClassHoldings.tsx` — new page component; filters holdings by asset class from the existing portfolio data, renders type-specific table and form

### Modified files

- `App.tsx` (or router config) — add `/portfolio/:assetClassId` route
- `AssetClassesTable.tsx` — rows become clickable links, add `type` dropdown to create form, show type on each row
- `AddAssetForm.tsx` — simplify by receiving `type` prop directly instead of guessing from class name; remove asset class dropdown (already known from context)
- `HoldingsTable.tsx` — refactor to accept a `type` prop that controls which columns render; remove grouping logic (one class per page)
- `TransactionForm.tsx` — replace `isFixedIncome` boolean prop with `type` prop to derive behavior from asset class type
- `types/index.ts` — add `type: "stock" | "crypto" | "fixed_income"` to `AssetClass` interface
- `Portfolio.tsx` — remove `HoldingsTable` usage; `onCreateClass` signature updated to include `type` parameter
- `hooks/useAssetClasses.ts` — update `createClass` to accept and forward `type` parameter to API

### Backend modified files

- `models/asset_class.py` — add `type` column (string, not null, default `"stock"`)
- `schemas/asset_class.py` — add `type` field (`Literal["stock", "crypto", "fixed_income"]`) to create/update/response schemas
- `routers/asset_classes.py` — accept `type` in create endpoint
- Startup backfill logic in `main.py` or `seed_data()` to migrate existing classes

### Removed

- `utils/assetClass.ts` (`isFixedIncomeClass`) — replaced by `type` field
- Grouping logic in `HoldingsTable` (`groupByAssetClass`, `GroupSection`) — no longer needed since each page shows one class
