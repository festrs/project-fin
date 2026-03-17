# Add Asset Form

## Problem

Users cannot add a new asset (e.g. BBSA3) to their portfolio. The `HoldingsTable` component has `onAddAsset` infrastructure but `Portfolio.tsx` never passes it, so the "Add Asset" button is hidden. The only way to create transactions is via Buy/Sell buttons on existing holdings — a chicken-and-egg problem for new symbols.

## Solution

A single inline form in the Holdings section that lets the user search for a symbol (with autocomplete), pick an asset class, and record their first buy transaction in one step.

## Backend: Stock Search Endpoint

**New endpoint:** `GET /api/stocks/search?q=<query>`

- Calls Finnhub `/search` for US symbols and Brapi `/api/available` for BR symbols
- Returns: `[{ symbol: string, name: string, type: string }]`
- Rate-limited with `MARKET_DATA_LIMIT`

**Provider changes:**
- `FinnhubProvider.search(query)` — calls `GET /search?q={query}&token={key}`, maps `result` array to `[{symbol, name, type}]`
- `BrapiProvider.search(query)` — calls `GET /api/available?search={query}&token={key}`, maps results to `[{symbol, name, type}]` with `.SA` suffix

The endpoint merges both provider results and returns them.

## Frontend: AddAssetForm Component

**Location:** `frontend/src/components/AddAssetForm.tsx`

**Props:**
- `assetClasses: AssetClass[]`
- `onSubmit: (data) => Promise<void>` — creates the transaction
- `onCancel: () => void`

**Fields:**
1. **Symbol search** — text input with debounced (300ms) calls to `/api/stocks/search?q=...`. Shows dropdown with matching results `[symbol — name]`. Selecting a result fills the symbol and auto-sets currency (BRL for `.SA` suffix, USD otherwise).
2. **Asset class** — `<select>` dropdown populated from `assetClasses` prop.
3. **Buy transaction fields** — quantity, unit price, computed total (read-only), date (defaults to today), currency (auto-set but editable), tax amount, notes. Same layout as existing `TransactionForm`.

**Submit behavior:** Calls `onSubmit` with a transaction payload `{ asset_class_id, asset_symbol, type: "buy", quantity, unit_price, total_value, currency, tax_amount, date, notes }`.

## Wiring in Portfolio.tsx / HoldingsTable

- `HoldingsTable` already has `showAddAsset` state and `onAddAsset` prop. Replace the existing raw-input form (lines 146-175) with `<AddAssetForm>`.
- Change the `onAddAsset` prop type: instead of `(symbol, classId) => Promise`, it becomes a boolean flag to show/hide the form. The form's `onSubmit` calls `onCreateTransaction` directly.
- `Portfolio.tsx` passes `onShowAddAsset` (or simply a flag) and `onCreateTransaction` to `HoldingsTable`, which renders `AddAssetForm` when active.

## What stays the same

- `TransactionForm` — unchanged, still used for Buy/Sell/Dividend on existing holdings
- `POST /api/transactions` — no changes, handles creation as-is
- All existing holding display, grouping, and expansion logic
