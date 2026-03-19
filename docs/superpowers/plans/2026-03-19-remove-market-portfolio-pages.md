# Remove Market & Portfolio Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove Market and Portfolio pages, making Dashboard the single entry point with clickable asset class rows that navigate to the existing AssetClassHoldings drill-down page. Add create/delete asset class actions to the ClassSummaryTable.

**Architecture:** The ClassSummaryTable gains `useNavigate` for row clicks and new props for create/delete. The Sidebar shrinks to Dashboard + Settings. Files for Market, Portfolio, MarketSearch, useMarketData, DividendsTable, and AssetClassesTable are deleted. AssetClassHoldings breadcrumb updates to point to `/` ("Dashboard").

**Tech Stack:** React 19, TypeScript, React Router, Tailwind CSS

---

### Task 1: Make ClassSummaryTable rows clickable (navigate to asset class)

**Files:**
- Modify: `frontend/src/components/ClassSummaryTable.tsx`

- [ ] **Step 1: Add useNavigate import and row click handler**

In `ClassSummaryTable.tsx`, add `useNavigate` from react-router-dom. Add `onClick` to each `<tr>` in the summaries map to navigate to `/portfolio/${s.classId}`. Add `cursor-pointer hover:bg-[var(--glass-hover)]` to the row className. Exclude clicks on interactive elements (inputs, buttons, dividend cell).

```tsx
// Add import at top:
import { useNavigate } from "react-router-dom";

// Inside the component function, before the if (loading) check:
const navigate = useNavigate();

// Replace the <tr> in the summaries.map:
<tr
  key={s.classId}
  className="even:bg-[var(--glass-row-alt)] rounded-lg cursor-pointer hover:bg-[var(--glass-hover)] transition-colors"
  onClick={() => navigate(`/portfolio/${s.classId}`)}
>
```

The dividend `<td>` already has its own `onClick` — add `e.stopPropagation()` there to prevent row navigation when clicking dividends:

```tsx
onClick={(e) => {
  e.stopPropagation();
  if (divDisplay !== "-") {
    setDividendModal({ classId: s.classId, className: s.className, currency: s.currency });
  }
}}
```

Also stop propagation on the target weight input when editing (wrap the input onChange area).

- [ ] **Step 2: Verify row click navigates correctly**

Run: `npm run dev` and click on an asset class row in the Dashboard table.
Expected: Navigates to `/portfolio/:assetClassId` showing that class's holdings.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ClassSummaryTable.tsx
git commit -m "feat: make ClassSummaryTable rows clickable for asset class navigation"
```

---

### Task 2: Add create/delete asset class actions to ClassSummaryTable

**Files:**
- Modify: `frontend/src/components/ClassSummaryTable.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Add create/delete props to ClassSummaryTable**

Add new props to `ClassSummaryTableProps`:

```tsx
onCreateClass?: (name: string, targetWeight: number, type: "stock" | "crypto" | "fixed_income") => Promise<unknown>;
onDeleteClass?: (classId: string) => Promise<unknown>;
```

- [ ] **Step 2: Add inline create form (toggled by "+" button)**

Add state for the form (`showCreateForm`, `newName`, `newWeight`, `newType`) similar to `AssetClassesTable.tsx`. Add a "+" button next to the "Consolidated Portfolio" header. When toggled, show a compact inline form row above the table with name, type select, target weight, Save, and Cancel buttons. Follow the same styling as `AssetClassesTable`'s form.

- [ ] **Step 3: Add delete button per row**

Add a small delete icon button (X or trash) as the last cell in each row. Use `e.stopPropagation()` to prevent row navigation. Show confirmation via `window.confirm()`. Style it with `text-negative` and only show on hover (use group/group-hover pattern or always-visible small icon).

```tsx
<td className="py-2 px-2 text-right">
  {onDeleteClass && (
    <button
      onClick={(e) => {
        e.stopPropagation();
        if (window.confirm(`Delete class "${s.className}"?`)) {
          onDeleteClass(s.classId);
        }
      }}
      className="text-text-muted hover:text-negative transition-colors"
      title="Delete class"
    >
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
      </svg>
    </button>
  )}
</td>
```

Update the `<thead>` to include an empty header cell for the delete column, and update `tfoot` colSpan values from 7 to 8.

- [ ] **Step 4: Wire up Dashboard to pass create/delete props**

In `Dashboard.tsx`, destructure `createClass` and `deleteClass` from `useAssetClasses()` (they're already returned by the hook but not currently used in Dashboard). Pass them to `ClassSummaryTable`:

```tsx
const { assetClasses, loading: classesLoading, updateClass, createClass, deleteClass } = useAssetClasses();

// In JSX:
<ClassSummaryTable
  ...existing props...
  onCreateClass={async (name, weight, type) => {
    await createClass(name, weight, type);
    refreshPortfolio();
  }}
  onDeleteClass={async (classId) => {
    await deleteClass(classId);
    refreshPortfolio();
  }}
/>
```

- [ ] **Step 5: Verify create and delete work**

Run: `npm run dev`, test creating a new asset class from Dashboard, and deleting one.
Expected: Both operations work, table updates immediately.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ClassSummaryTable.tsx frontend/src/pages/Dashboard.tsx
git commit -m "feat: add create/delete asset class actions to ClassSummaryTable"
```

---

### Task 3: Update AssetClassHoldings breadcrumb to point to Dashboard

**Files:**
- Modify: `frontend/src/pages/AssetClassHoldings.tsx`

- [ ] **Step 1: Change breadcrumb links from /portfolio to /**

In `AssetClassHoldings.tsx`, change both `<Link to="/portfolio">` instances (lines 125 and 136) to `<Link to="/">` and change the text from "Portfolio" to "Dashboard":

```tsx
// Line 125 (not found state):
<Link to="/" className="text-primary hover:text-primary-hover text-base">
  &lsaquo; Dashboard
</Link>

// Line 136 (normal state):
<Link to="/" className="text-primary hover:text-primary-hover text-base">
  &lsaquo; Dashboard
</Link>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/AssetClassHoldings.tsx
git commit -m "fix: update AssetClassHoldings breadcrumb to link to Dashboard"
```

---

### Task 4: Remove Market and Portfolio routes and nav links

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Remove routes and imports from App.tsx**

Remove the `Portfolio` and `Market` imports (lines 4, 6) and their `<Route>` elements (lines 18, 21). Keep the `/portfolio/:assetClassId` route.

Updated `App.tsx`:

```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";
import Fundamentals from "./pages/Fundamentals";
import AssetClassHoldings from "./pages/AssetClassHoldings";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-bg-page flex">
        <Sidebar />
        <main className="ml-[220px] w-[calc(100%-220px)] px-10 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/portfolio/:assetClassId" element={<AssetClassHoldings />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/fundamentals/:symbol" element={<Fundamentals />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
```

- [ ] **Step 2: Remove Portfolio and Market links from Sidebar**

Remove the `Wallet` and `TrendingUp` imports from lucide-react. Remove the two entries from the `links` array. The sidebar should only have Dashboard and Settings:

```tsx
import { Link, useLocation } from "react-router-dom";
import { LayoutGrid, Settings } from "lucide-react";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutGrid },
  { to: "/settings", label: "Settings", icon: Settings },
];
```

- [ ] **Step 3: Verify navigation works**

Run: `npm run dev`. Sidebar should show only Dashboard and Settings. Dashboard loads correctly. Clicking an asset class row navigates to holdings. Back link returns to Dashboard.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Sidebar.tsx
git commit -m "feat: remove Market and Portfolio routes and nav links"
```

---

### Task 5: Delete unused files

**Files:**
- Delete: `frontend/src/pages/Market.tsx`
- Delete: `frontend/src/pages/Portfolio.tsx`
- Delete: `frontend/src/components/MarketSearch.tsx`
- Delete: `frontend/src/components/AssetClassesTable.tsx`
- Delete: `frontend/src/components/DividendsTable.tsx`
- Delete: `frontend/src/hooks/useMarketData.ts`
- Delete: `frontend/src/components/__tests__/AssetClassesTable.test.tsx`
- Delete: `frontend/src/components/__tests__/DividendsTable.test.tsx`

- [ ] **Step 1: Delete all unused files**

```bash
rm frontend/src/pages/Market.tsx
rm frontend/src/pages/Portfolio.tsx
rm frontend/src/components/MarketSearch.tsx
rm frontend/src/components/AssetClassesTable.tsx
rm frontend/src/components/DividendsTable.tsx
rm frontend/src/hooks/useMarketData.ts
rm frontend/src/components/__tests__/AssetClassesTable.test.tsx
rm frontend/src/components/__tests__/DividendsTable.test.tsx
```

- [ ] **Step 2: Verify build passes**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors. If there are unused import warnings, fix them.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove unused Market, Portfolio, and related files"
```

---

### Task 6: Run tests and final verification

**Files:** None (verification only)

- [ ] **Step 1: Run frontend tests**

Run: `cd frontend && npm run test -- --run`
Expected: All tests pass. Some tests for deleted components were removed in Task 5.

- [ ] **Step 2: Run lint**

Run: `cd frontend && npm run lint`
Expected: No errors.

- [ ] **Step 3: Manual smoke test**

Run: `npm run dev` and verify:
1. Dashboard loads with ClassSummaryTable showing all asset classes
2. Clicking an asset class row navigates to `/portfolio/:id` with correct holdings
3. "+" button opens inline form to create a new asset class
4. Delete button removes an asset class (with confirmation)
5. Back breadcrumb in AssetClassHoldings says "Dashboard" and links to `/`
6. Sidebar shows only Dashboard and Settings
7. Dividend click still opens DividendHistoryModal (doesn't trigger row navigation)
8. Edit targets mode still works
