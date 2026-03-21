# Where to Invest — Dedicated Page

## Summary

Replace the simple recommendation card on the Dashboard with a dedicated "Where to Invest" page accessible from the sidebar. The page accepts an investment amount and currency, calculates which specific assets to buy, how many shares/units, and the amount per asset — giving the user an actionable investment plan.

## Motivation

The current system shows a small card on the Dashboard with the top N underweight assets and their percentage gap. It does not tell the user *how much* to invest in each asset or *how many shares* to buy. The recommendation count setting is buried in the Settings page. Users need an actionable, self-contained page to answer: "I have R$5,000 — what exactly should I buy?"

## Page Design

### Sidebar Navigation

Add "Where to Invest" entry between Dashboard and Settings in `Sidebar.tsx`, using `TrendingUp` icon from lucide-react. Route: `/invest`.

### Input Bar

A single horizontal row inside a glass card at the top of the page:

| Field | Type | Details |
|-------|------|---------|
| Amount | Numeric input | Required. The total amount the user wants to invest |
| Currency | Dropdown | BRL or USD |
| # of Recommendations | Numeric input | How many assets to recommend (default: 3). Moved here from Settings page |
| Calculate button | Button | Triggers the API call |

### Results Table — "Investment Plan"

Displayed inside a glass card below the input bar.

| Column | Description |
|--------|-------------|
| Asset | Symbol (e.g., AAPL, PETR4) |
| Class | Asset class name (e.g., US Stocks, BR Stocks) |
| Target % | Effective target allocation (class weight × asset weight / 100) |
| Actual % | Current portfolio weight |
| Gap % | Target − Actual (positive = underweight, shown in green) |
| Price | Current price in native currency (USD for US, BRL for BR) |
| Qty | Number of shares/units to buy |
| Amount | Cost in the user's selected currency |

**Footer row:** Total amount (should equal or be very close to the input amount).

**Empty state:** "Enter an amount and click Calculate" when no calculation has been performed yet.

### Quantity Calculation Rules

- **Stocks (US and BR):** Round down to whole shares.
- **Crypto:** Allow fractional quantities.
- **Fixed income:** Treat as lump-sum allocation — quantity is always 1, amount is the allocated value. Fixed income assets don't have market prices or tradeable shares; they represent value-based holdings.
- **Remainder redistribution:** When rounding down creates a remainder, redistribute it to the next asset in the sorted list (by gap descending). Continue until the remainder is less than any single share price or all assets have been processed.

### Currency Handling

- User selects input currency (BRL or USD).
- Asset prices are fetched in their native currency.
- When input currency differs from asset currency, convert using the exchange rate (existing `/api/portfolio/exchange-rate` endpoint).
- The "Amount" column in the results table is always in the user's selected currency.
- The "Price" column shows the native currency of each asset.

## Backend Changes

### New Endpoint

```
POST /api/recommendations/invest
```

**Request body (JSON):**
```json
{
  "amount": "5000.00",
  "currency": "BRL",
  "count": 3
}
```

**Validation:** `amount` must be a positive decimal string, `currency` must be "BRL" or "USD", `count` >= 1 (default: 3).

**Response:**
```json
{
  "recommendations": [
    {
      "symbol": "AAPL",
      "class_name": "US Stocks",
      "effective_target": 15.0,
      "actual_weight": 10.2,
      "diff": 4.8,
      "price": { "amount": "178.50", "currency": "USD" },
      "quantity": 10,
      "invest_amount": { "amount": "1785.00", "currency": "BRL" }
    }
  ],
  "total_invested": { "amount": "5000.00", "currency": "BRL" },
  "exchange_rate": 5.15,
  "exchange_rate_pair": "USD-BRL",
  "remainder": { "amount": "0.00", "currency": "BRL" }
}
```

Monetary fields use the existing `MoneyResponse` schema (`amount` as string, `currency` as string) for consistency with the rest of the API.

**Pydantic schemas:** Add `InvestmentPlanRequest`, `InvestmentRecommendationResponse`, and `InvestmentPlanResponse` to `backend/app/schemas/recommendation.py` (new file).

### Service Logic

Extend `RecommendationService` with a new method `get_investment_plan(user_id, amount, currency, count)`:

1. Get top N underweight assets. **Note:** The existing `get_recommendations` only considers assets the user already holds. This is intentional — the invest plan recommends buying more of assets you already own, not new assets. Users must first buy an asset manually before it appears in recommendations.
2. Distribute the input `amount` proportionally across assets based on their gap weight (each asset's `diff` / sum of all `diff` values).
3. Fetch current price for each asset (existing `_get_current_price` method).
4. If needed, fetch exchange rate (USD↔BRL) for cross-currency conversion.
5. Calculate raw quantity: `allocated_amount / price` (converting currencies as needed).
6. For stocks: round down to whole shares. For crypto: keep fractional.
7. Redistribute remainders: iterate through assets by gap (descending), try to buy one more share of each until remainder < cheapest share price.
8. Return the investment plan with quantities, amounts, and metadata.

### Determining Asset Type for Rounding

Use the `type` field from `AssetClass` model. If `type == "crypto"`, allow fractional quantities. Otherwise, round to whole shares.

## Frontend Changes

### New Files

- `src/pages/Invest.tsx` — The page component with input bar and results table
- `src/hooks/useInvest.ts` — Hook that calls the new API endpoint

### Modified Files

- `src/App.tsx` — Add route `/invest` → `Invest` page
- `src/components/Sidebar.tsx` — Add "Where to Invest" nav entry with `TrendingUp` icon
- `src/types/index.ts` — Add `InvestmentPlan` and `InvestmentRecommendation` interfaces
- `src/pages/Settings.tsx` — Remove recommendation count setting
- `src/pages/Dashboard.tsx` — Remove `RecommendationCard` usage and related imports/state
- `src/components/ClassSummaryTable.tsx` — Remove `getRecommendationCount()` helper and its usage (the "where to invest" column in the class summary table). This class-level recommendation is superseded by the new asset-level page.

### Files to Delete

- `src/components/RecommendationCard.tsx` — Replaced by the new Invest page
- `src/components/__tests__/RecommendationCard.test.tsx` (if exists) — Test for deleted component
- `src/hooks/useRecommendations.ts` — Replaced by `useInvest.ts`

### Type Definitions

```typescript
interface MoneyResponse {
  amount: string;
  currency: string;
}

interface InvestmentRecommendation {
  symbol: string;
  class_name: string;
  effective_target: number;
  actual_weight: number;
  diff: number;
  price: MoneyResponse;
  quantity: number;
  invest_amount: MoneyResponse;
}

interface InvestmentPlan {
  recommendations: InvestmentRecommendation[];
  total_invested: MoneyResponse;
  exchange_rate: number | null;
  exchange_rate_pair: string | null;
  remainder: MoneyResponse;
}
```

### UI States

- **Empty:** "Enter an amount and click Calculate" (before first calculation)
- **Loading:** Spinner/loading indicator while API call is in flight
- **Results:** The investment plan table
- **Error states:** See Edge Cases section

## What Does NOT Change

- Dashboard retains: allocation charts, performance chart, class summary table, splits, dividends
- Quarantine logic: quarantined assets remain excluded from recommendations (existing behavior)
- Settings page: keeps quarantine threshold and period settings
- Existing `GET /api/recommendations` endpoint: remains available (old API is not deleted, but frontend no longer calls it)
- Asset class/weight CRUD: unchanged
- Recommendation ranking algorithm: purely allocation-based, most underweight first

## Edge Cases

- **Amount too small:** If the input amount can't buy a single share of any recommended asset, show "Amount too low to purchase any recommended assets."
- **All assets quarantined:** If all top N candidates are quarantined, show "No recommendations available — all top candidates are in quarantine."
- **No holdings:** If the portfolio is empty, show "Add holdings to your portfolio first."
- **Exchange rate unavailable:** Fall back to a reasonable default (currently 5.15) and show a warning indicator.
