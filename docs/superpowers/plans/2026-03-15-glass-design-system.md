# Glass Design System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Project Fin frontend with a minimal glassmorphism aesthetic — Apple-inspired indigo accent, Plus Jakarta Sans typography, left sidebar navigation, barely-there glass cards, and borderless alternating-row tables.

**Architecture:** Pure styling migration. Replace the top navbar with a fixed left sidebar (`Sidebar.tsx`), update `App.tsx` layout to flex, then systematically restyle every component using Tailwind v4 design tokens defined in `index.css` via `@theme`. No logic changes — only class names and visual properties.

**Tech Stack:** React 19, TypeScript, Tailwind CSS v4 (Vite plugin), Recharts, Lucide React (new), Plus Jakarta Sans via Google Fonts (new)

**Spec:** `docs/superpowers/specs/2026-03-14-glass-design-system.md`

---

## Chunk 1: Foundation — Design Tokens, Font, Dependencies, Sidebar, Layout

### Task 1: Install new dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install lucide-react**

Run:
```bash
cd frontend && npm install lucide-react
```

- [ ] **Step 2: Verify install**

Run:
```bash
cd frontend && npm ls lucide-react
```
Expected: `lucide-react@x.x.x`

- [ ] **Step 3: Commit**

```bash
cd frontend && git add package.json package-lock.json && git commit -m "chore: add lucide-react icon library"
```

---

### Task 2: Add Google Fonts and design tokens

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Add Plus Jakarta Sans font link to index.html**

In `frontend/index.html`, add inside `<head>` before `<title>`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />
```

- [ ] **Step 2: Add design tokens to index.css**

Replace the entire content of `frontend/src/index.css` with:
```css
@import "tailwindcss";

@theme {
  --color-primary: #4f46e5;
  --color-primary-hover: #4338ca;
  --color-positive: #10b981;
  --color-negative: #ef4444;
  --color-warning: #f59e0b;
  --color-text-primary: #0f172a;
  --color-text-secondary: #334155;
  --color-text-tertiary: #64748b;
  --color-text-muted: #94a3b8;
  --color-bg-page: #f8f9fb;
  --font-family-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

:root {
  --glass-card-bg: rgba(255,255,255,0.7);
  --glass-sidebar-bg: rgba(255,255,255,0.85);
  --glass-border: rgba(0,0,0,0.04);
  --glass-border-input: rgba(0,0,0,0.08);
  --glass-row-alt: rgba(0,0,0,0.015);
  --glass-hover: rgba(0,0,0,0.03);
  --glass-primary-soft: rgba(79,70,229,0.08);
  --glass-primary-ring: rgba(79,70,229,0.15);
  --glass-positive-soft: rgba(16,185,129,0.08);
  --glass-negative-soft: rgba(239,68,68,0.08);
}

/* Tabular numbers for all financial data */
.tabular-nums {
  font-variant-numeric: tabular-nums;
}
```

Note: Solid colors go in `@theme` so Tailwind generates utilities (e.g., `text-primary`, `bg-bg-page`). Alpha/rgba values go in `:root` and are referenced via arbitrary values (e.g., `bg-[var(--glass-card-bg)]`), since Tailwind v4's `@theme` does not support `rgba()` directly.

**Important:** When rendering financial values (prices, totals, percentages), add the class `tabular-nums` to the element for proper number alignment.

- [ ] **Step 3: Verify the app still builds**

Run:
```bash
cd frontend && npm run build
```
Expected: Build succeeds with no errors.

- [ ] **Step 4: Commit**

```bash
cd frontend && git add index.html src/index.css && git commit -m "feat: add Plus Jakarta Sans font and glass design tokens"
```

---

### Task 3: Create Sidebar component

**Files:**
- Create: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Create Sidebar.tsx**

```tsx
import { Link, useLocation } from "react-router-dom";
import { LayoutGrid, Wallet, TrendingUp, Settings } from "lucide-react";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutGrid },
  { to: "/portfolio", label: "Portfolio", icon: Wallet },
  { to: "/market", label: "Market", icon: TrendingUp },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <nav className="fixed left-0 top-0 w-[220px] min-h-screen bg-[rgba(255,255,255,0.85)] border-r border-[rgba(0,0,0,0.04)] p-6 flex flex-col gap-1">
      <Link to="/" className="text-2xl font-bold text-text-primary px-3 mb-6 tracking-tight">
        Project <span className="text-primary">Fin</span>
      </Link>
      {links.map((link) => {
        const isActive = location.pathname === link.to;
        return (
          <Link
            key={link.to}
            to={link.to}
            className={`flex items-center gap-2.5 px-3 py-2.5 rounded-[10px] text-base font-medium transition-colors ${
              isActive
                ? "bg-[rgba(79,70,229,0.08)] text-primary font-semibold"
                : "text-text-tertiary hover:bg-[rgba(0,0,0,0.03)] hover:text-text-primary"
            }`}
          >
            <link.icon size={18} strokeWidth={1.8} />
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 2: Verify the app builds**

Run:
```bash
cd frontend && npm run build
```
Expected: Build succeeds (Sidebar not yet used).

- [ ] **Step 3: Commit**

```bash
cd frontend && git add src/components/Sidebar.tsx && git commit -m "feat: create Sidebar component with glass design"
```

---

### Task 4: Update App.tsx layout and remove Navbar

**Files:**
- Modify: `frontend/src/App.tsx`
- Delete: `frontend/src/components/Navbar.tsx`

- [ ] **Step 1: Update App.tsx**

Replace the entire content of `frontend/src/App.tsx` with:
```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Portfolio from "./pages/Portfolio";
import Settings from "./pages/Settings";
import Market from "./pages/Market";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-bg-page flex">
        <Sidebar />
        <main className="ml-[220px] w-[calc(100%-220px)] px-10 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/market" element={<Market />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
```

- [ ] **Step 2: Delete Navbar.tsx**

Run:
```bash
rm frontend/src/components/Navbar.tsx
```

- [ ] **Step 3: Verify the app builds**

Run:
```bash
cd frontend && npm run build
```
Expected: Build succeeds. No import errors (Navbar was only imported in App.tsx).

- [ ] **Step 4: Verify in browser**

Run:
```bash
cd frontend && npm run dev
```
Open `http://localhost:5173`. Verify:
- Left sidebar visible with "Project Fin" logo
- Navigation links work
- Active state highlights current page
- Main content fills remaining width

- [ ] **Step 5: Commit**

```bash
cd frontend && git add -A && git commit -m "feat: replace top navbar with glass sidebar layout"
```

---

## Chunk 2: Shared Components — ChartCard, DataTable, Badges

### Task 5: Update ChartCard

**Files:**
- Modify: `frontend/src/components/ChartCard.tsx`

- [ ] **Step 1: Update ChartCard styling**

Replace the entire content of `frontend/src/components/ChartCard.tsx` with:
```tsx
interface ChartCardProps {
  title: string;
  children: React.ReactNode;
}

export function ChartCard({ title, children }: ChartCardProps) {
  return (
    <div className="bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.04)] rounded-[14px] p-6">
      <h3 className="text-base font-semibold text-text-primary mb-4">{title}</h3>
      {children}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd frontend && git add src/components/ChartCard.tsx && git commit -m "style: update ChartCard with glass design"
```

---

### Task 6: Update DataTable

**Files:**
- Modify: `frontend/src/components/DataTable.tsx`

- [ ] **Step 1: Update DataTable styling**

Apply these class changes in `frontend/src/components/DataTable.tsx`:

Filter input (line ~99): Change
```
className="mb-3 w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
```
to:
```
className="mb-3 w-full bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.08)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-[rgba(79,70,229,0.15)] focus:border-primary"
```

Table element (line ~105): Change
```
className="w-full text-sm text-left"
```
to:
```
className="w-full text-base text-left"
```

Thead (line ~106): Change
```
className="bg-gray-50 text-gray-600 uppercase text-xs"
```
to:
```
className="text-text-muted uppercase text-base tracking-wide"
```

Th (line ~111): Change
```
className={`px-4 py-3 ${col.sortable ? "cursor-pointer select-none" : ""}`}
```
to:
```
className={`px-4 pb-3 font-semibold ${col.sortable ? "cursor-pointer select-none" : ""}`}
```

Tbody (line ~122): Change
```
className="divide-y divide-gray-200"
```
to:
```
className=""
```

Tr (line ~126): Change
```
className="even:bg-gray-50"
```
to:
```
className="even:bg-[rgba(0,0,0,0.015)] rounded-lg"
```

Td (line ~135): Change
```
className={`px-4 py-3 ${onRowClick ? "cursor-pointer" : ""}`}
```
to:
```
className={`px-4 py-3.5 text-text-secondary ${onRowClick ? "cursor-pointer" : ""}`}
```

Editing input (line ~142): Change
```
className="border border-blue-400 rounded px-1 py-0.5 text-sm w-full"
```
to:
```
className="border border-primary rounded-[10px] px-2.5 py-1.5 text-base w-full focus:outline-none focus:ring-2 focus:ring-[rgba(79,70,229,0.15)]"
```

Expanded row div (line ~171): Change
```
className="px-4 py-3 bg-gray-50 border-t"
```
to:
```
className="px-4 py-3 bg-[rgba(0,0,0,0.015)] rounded-lg"
```

- [ ] **Step 2: Verify build**

Run:
```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
cd frontend && git add src/components/DataTable.tsx && git commit -m "style: update DataTable with glass design"
```

---

### Task 7: Update QuarantineBadge

**Files:**
- Modify: `frontend/src/components/QuarantineBadge.tsx`

- [ ] **Step 1: Update badge styling**

In `frontend/src/components/QuarantineBadge.tsx`, change the className on the `<span>` (line ~15):
```
className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full text-xs font-medium"
```
to:
```
className="bg-[rgba(245,158,11,0.1)] text-amber-700 px-2.5 py-1 rounded-md text-base font-semibold"
```

- [ ] **Step 2: Commit**

```bash
cd frontend && git add src/components/QuarantineBadge.tsx && git commit -m "style: update QuarantineBadge with glass design"
```

---

### Task 8: Update RecommendationCard

**Files:**
- Modify: `frontend/src/components/RecommendationCard.tsx`

- [ ] **Step 1: Update RecommendationCard styling**

Replace the entire content of `frontend/src/components/RecommendationCard.tsx` with:
```tsx
import type { Recommendation } from "../types";

interface RecommendationCardProps {
  recommendations: Recommendation[];
}

export function RecommendationCard({ recommendations }: RecommendationCardProps) {
  if (recommendations.length === 0) {
    return (
      <div className="bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.04)] rounded-[14px] p-6">
        <h3 className="text-lg font-semibold text-text-primary tracking-[-0.3px] mb-4">Recommendations</h3>
        <p className="text-text-muted text-base">No recommendations available</p>
      </div>
    );
  }

  return (
    <div className="bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.04)] rounded-[14px] p-6">
      <h3 className="text-lg font-semibold text-text-primary tracking-[-0.3px] mb-4">Recommendations</h3>
      <ul className="space-y-2">
        {recommendations.map((rec) => (
          <li
            key={rec.symbol}
            className="flex items-center justify-between p-3 rounded-lg even:bg-[rgba(0,0,0,0.015)]"
          >
            <div>
              <span className="font-semibold text-text-primary">{rec.symbol}</span>
              <span className="text-text-muted text-base ml-2">{rec.class_name}</span>
            </div>
            <div className="flex items-center gap-1">
              {rec.diff > 0 ? (
                <span className="text-positive font-semibold text-base flex items-center">
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                  </svg>
                  +{rec.diff.toFixed(1)}%
                </span>
              ) : (
                <span className="text-negative font-semibold text-base">
                  {rec.diff.toFixed(1)}%
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd frontend && git add src/components/RecommendationCard.tsx && git commit -m "style: update RecommendationCard with glass design"
```

---

## Chunk 3: Chart Components

### Task 9: Update PerformanceChart

**Files:**
- Modify: `frontend/src/components/PerformanceChart.tsx`

- [ ] **Step 1: Update colors and text styling**

In `frontend/src/components/PerformanceChart.tsx`:

Change loading text (line ~37):
```
<p className="text-gray-500 text-sm">Loading...</p>
```
to:
```
<p className="text-text-muted text-base">Loading...</p>
```

Change empty state text (line ~39):
```
<p className="text-gray-500 text-sm">No performance data available</p>
```
to:
```
<p className="text-text-muted text-base">No performance data available</p>
```

Change Line stroke (line ~50):
```
stroke="#3B82F6"
```
to:
```
stroke="#4f46e5"
```

- [ ] **Step 2: Commit**

```bash
cd frontend && git add src/components/PerformanceChart.tsx && git commit -m "style: update PerformanceChart with indigo accent"
```

---

### Task 10: Update AllocationChart

**Files:**
- Modify: `frontend/src/components/AllocationChart.tsx`

- [ ] **Step 1: Update colors and text**

In `frontend/src/components/AllocationChart.tsx`:

Change empty state text (line ~27):
```
<p className="text-gray-500 text-sm">No allocation data available</p>
```
to:
```
<p className="text-text-muted text-base">No allocation data available</p>
```

Change Target bar fill (line ~47):
```
<Bar dataKey="Target" fill="#3B82F6" />
```
to:
```
<Bar dataKey="Target" fill="#4f46e5" />
```

- [ ] **Step 2: Commit**

```bash
cd frontend && git add src/components/AllocationChart.tsx && git commit -m "style: update AllocationChart with indigo accent"
```

---

### Task 11: Update PortfolioCompositionChart

**Files:**
- Modify: `frontend/src/components/PortfolioCompositionChart.tsx`

- [ ] **Step 1: Update color palette and text**

In `frontend/src/components/PortfolioCompositionChart.tsx`:

Change COLORS array (line ~15-18):
```tsx
const COLORS = [
  "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
  "#EC4899", "#14B8A6", "#F97316", "#6366F1", "#84CC16",
];
```
to:
```tsx
const COLORS = [
  "#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16",
];
```

Change empty state text (line ~40):
```
<p className="text-gray-500 text-sm">No allocation data available</p>
```
to:
```
<p className="text-text-muted text-base">No allocation data available</p>
```

Change Legend formatter (line ~88):
```
formatter={(value) => <span className="text-xs">{value}</span>}
```
to:
```
formatter={(value) => <span className="text-base text-text-tertiary">{value}</span>}
```

Change bottom label (line ~92):
```
<div className="text-center text-xs text-gray-500 -mt-2">
```
to:
```
<div className="text-center text-base text-text-muted -mt-2">
```

- [ ] **Step 2: Commit**

```bash
cd frontend && git add src/components/PortfolioCompositionChart.tsx && git commit -m "style: update PortfolioCompositionChart with new color palette"
```

---

## Chunk 4: Table Components — ClassSummaryTable, HoldingsTable

### Task 12: Update ClassSummaryTable

**Files:**
- Modify: `frontend/src/components/ClassSummaryTable.tsx`

- [ ] **Step 1: Update all card containers**

In `frontend/src/components/ClassSummaryTable.tsx`, apply these replacements throughout the file:

All instances of `bg-white rounded-lg shadow p-4` → `bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.04)] rounded-[14px] p-6`

All instances of `text-gray-500 text-sm` → `text-text-muted text-base`

All instances of `text-lg font-semibold` → `text-lg font-semibold text-text-primary tracking-[-0.3px]`

- [ ] **Step 2: Update table header row**

Change (line ~256):
```
<tr className="text-gray-500 border-b">
```
to:
```
<tr className="text-text-muted uppercase text-base tracking-wide">
```

- [ ] **Step 3: Update table body rows**

Change (line ~313):
```
<tr key={s.classId} className="border-b hover:bg-gray-50">
```
to:
```
<tr key={s.classId} className="even:bg-[rgba(0,0,0,0.015)] rounded-lg">
```

- [ ] **Step 4: Update cell text colors**

Change `text-blue-600` → `text-primary` (class name cell, line ~314)

Change `text-blue-500 hover:text-blue-700` → `text-primary hover:text-primary-hover` (edit button, line ~267)

Change `text-gray-500` → `text-text-muted` (all muted text instances)

Change `text-gray-400` → `text-text-muted` (all lighter text instances)

Change `text-xs` → `text-base` for body text (not icons)

- [ ] **Step 5: Update footer row**

Change (line ~401):
```
<tr className="font-semibold bg-blue-50">
```
to:
```
<tr className="font-semibold bg-[rgba(79,70,229,0.04)]">
```

- [ ] **Step 6: Update buttons**

Change save button (line ~387):
```
className="bg-green-600 text-white px-3 py-1 rounded text-xs hover:bg-green-700 disabled:opacity-50"
```
to:
```
className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover disabled:opacity-50"
```

Change cancel button (line ~392):
```
className="text-gray-500 hover:text-gray-700 px-2 py-1 text-xs"
```
to:
```
className="text-text-tertiary hover:text-text-primary px-4 py-2 text-base"
```

- [ ] **Step 7: Update invest input**

Change (line ~247):
```
className="border rounded px-2 py-1 text-sm w-28"
```
to:
```
className="bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.08)] rounded-[10px] px-3.5 py-2.5 text-base w-28 focus:outline-none focus:ring-2 focus:ring-[rgba(79,70,229,0.15)] focus:border-primary"
```

- [ ] **Step 8: Update inline edit inputs**

Change target weight input (line ~329):
```
className="border rounded px-1.5 py-0.5 text-sm w-16 text-right"
```
to:
```
className="bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.08)] rounded-[10px] px-2.5 py-1.5 text-base w-20 text-right focus:outline-none focus:ring-2 focus:ring-[rgba(79,70,229,0.15)] focus:border-primary"
```

- [ ] **Step 9: Verify build**

Run:
```bash
cd frontend && npm run build
```

- [ ] **Step 10: Commit**

```bash
cd frontend && git add src/components/ClassSummaryTable.tsx && git commit -m "style: update ClassSummaryTable with glass design"
```

---

### Task 13: Update HoldingsTable

**Files:**
- Modify: `frontend/src/components/HoldingsTable.tsx`

- [ ] **Step 1: Update card container**

Change (line ~124):
```
className="bg-white rounded-lg shadow p-4"
```
to:
```
className="bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.04)] rounded-[14px] p-6"
```

- [ ] **Step 2: Update heading and button**

Change heading (line ~126):
```
className="text-lg font-semibold"
```
to:
```
className="text-lg font-semibold text-text-primary tracking-[-0.3px]"
```

Change "Add Asset" button (line ~129):
```
className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
```
to:
```
className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover"
```

- [ ] **Step 3: Update table header**

Change (line ~186):
```
className="bg-gray-50 text-gray-600 uppercase text-xs"
```
to:
```
className="text-text-muted uppercase text-base tracking-wide"
```

- [ ] **Step 4: Update group header rows**

Change (line ~288):
```
className="bg-blue-50 cursor-pointer hover:bg-blue-100"
```
to:
```
className="bg-[rgba(79,70,229,0.04)] cursor-pointer hover:bg-[rgba(79,70,229,0.08)]"
```

Change `text-blue-700` → `text-primary` (line ~291, ~299)

Change `text-gray-500` → `text-text-muted` (line ~294)

- [ ] **Step 5: Update holding rows**

Change (line ~376):
```
className="border-b hover:bg-gray-50 cursor-pointer"
```
to:
```
className="even:bg-[rgba(0,0,0,0.015)] hover:bg-[rgba(0,0,0,0.03)] cursor-pointer rounded-lg"
```

- [ ] **Step 6: Update gain/loss colors**

Change `text-green-600` → `text-positive` (lines ~400, ~448)
Change `text-red-600` → `text-negative` (lines ~402, ~458)

- [ ] **Step 7: Update expanded transaction section**

Change (line ~472):
```
className="px-4 py-3 bg-gray-50 border-t"
```
to:
```
className="px-4 py-3 bg-[rgba(0,0,0,0.015)] rounded-lg"
```

Change `font-semibold text-sm` → `font-semibold text-base text-text-primary` (line ~473)

Change inner transaction table `text-gray-500` → `text-text-muted` (line ~479)

- [ ] **Step 8: Update Buy/Sell buttons**

Change Buy button (line ~448):
```
className="text-green-600 hover:text-green-800 text-xs px-1"
```
to:
```
className="text-positive hover:opacity-80 text-base px-2 font-medium"
```

Change Sell button (line ~458):
```
className="text-red-600 hover:text-red-800 text-xs px-1"
```
to:
```
className="text-negative hover:opacity-80 text-base px-2 font-medium"
```

- [ ] **Step 9: Update form inputs**

All instances of:
```
className="border rounded px-2 py-1 text-sm"
```
to:
```
className="bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.08)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[rgba(79,70,229,0.15)] focus:border-primary"
```

Change inline weight edit input `border-blue-400` → `border-primary` (line ~427)

Change `text-xs text-gray-600` → `text-base text-text-muted` for labels

- [ ] **Step 10: Update Add Asset form button**

Change (line ~160):
```
className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
```
to:
```
className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover"
```

- [ ] **Step 11: Verify build**

Run:
```bash
cd frontend && npm run build
```

- [ ] **Step 12: Commit**

```bash
cd frontend && git add src/components/HoldingsTable.tsx && git commit -m "style: update HoldingsTable with glass design"
```

---

## Chunk 5: Form Components & Remaining Tables

### Task 14: Update TransactionForm

**Files:**
- Modify: `frontend/src/components/TransactionForm.tsx`

- [ ] **Step 1: Update form container**

Change (line ~60):
```
className="space-y-3 p-4 bg-gray-50 rounded border"
```
to:
```
className="space-y-4 p-6 bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.04)] rounded-[14px]"
```

- [ ] **Step 2: Update form title**

Change (line ~61):
```
className="font-semibold text-sm"
```
to:
```
className="font-semibold text-base text-text-primary"
```

- [ ] **Step 3: Update all form inputs**

All instances of:
```
className="border rounded px-2 py-1 text-sm w-28"
```
to:
```
className="bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.08)] rounded-[10px] px-3.5 py-2.5 text-base w-28 focus:outline-none focus:ring-2 focus:ring-[rgba(79,70,229,0.15)] focus:border-primary"
```

Change select elements:
```
className="ml-1 border rounded px-2 py-1 text-sm"
```
and:
```
className="border rounded px-2 py-1 text-sm"
```
to:
```
className="bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.08)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[rgba(79,70,229,0.15)] focus:border-primary"
```

Change readonly total input (line ~108):
```
className="border rounded px-2 py-1 text-sm w-28 bg-gray-100"
```
to:
```
className="bg-[rgba(0,0,0,0.03)] border border-[rgba(0,0,0,0.04)] rounded-[10px] px-3.5 py-2.5 text-base w-28 text-text-muted"
```

Change full-width notes input (line ~168):
```
className="border rounded px-2 py-1 text-sm w-full"
```
to:
```
className="bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.08)] rounded-[10px] px-3.5 py-2.5 text-base w-full focus:outline-none focus:ring-2 focus:ring-[rgba(79,70,229,0.15)] focus:border-primary"
```

- [ ] **Step 4: Update labels**

All instances of `text-xs text-gray-600` → `text-base text-text-muted`

- [ ] **Step 5: Update buttons**

Change submit button (line ~179):
```
className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
```
to:
```
className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover disabled:opacity-50"
```

Change cancel button (line ~186):
```
className="text-gray-500 px-3 py-1 rounded text-sm hover:text-gray-700"
```
to:
```
className="bg-[rgba(0,0,0,0.03)] border border-[rgba(0,0,0,0.04)] text-text-secondary px-4 py-2 rounded-[10px] text-base font-medium hover:bg-[rgba(0,0,0,0.06)]"
```

- [ ] **Step 6: Commit**

```bash
cd frontend && git add src/components/TransactionForm.tsx && git commit -m "style: update TransactionForm with glass design"
```

---

### Task 15: Update DividendsTable

**Files:**
- Modify: `frontend/src/components/DividendsTable.tsx`

- [ ] **Step 1: Update container and heading**

Change (line ~82):
```
className="bg-white rounded-lg shadow p-4"
```
to:
```
className="bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.04)] rounded-[14px] p-6"
```

Change heading `text-lg font-semibold` → `text-lg font-semibold text-text-primary tracking-[-0.3px]`

- [ ] **Step 2: Update button**

Change (line ~86):
```
className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
```
to:
```
className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover"
```

- [ ] **Step 3: Update filter inputs and labels**

All `text-xs text-gray-600` → `text-base text-text-muted`

All filter inputs `border rounded px-2 py-1 text-sm` → `bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.08)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[rgba(79,70,229,0.15)] focus:border-primary`

- [ ] **Step 4: Commit**

```bash
cd frontend && git add src/components/DividendsTable.tsx && git commit -m "style: update DividendsTable with glass design"
```

---

### Task 16: Update AssetClassesTable

**Files:**
- Modify: `frontend/src/components/AssetClassesTable.tsx`

- [ ] **Step 1: Update container**

Change (line ~106):
```
className="bg-white rounded-lg shadow p-4"
```
to:
```
className="bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.04)] rounded-[14px] p-6"
```

- [ ] **Step 2: Update heading and buttons**

Change heading `text-lg font-semibold` → `text-lg font-semibold text-text-primary tracking-[-0.3px]`

Change "Add Class" button (line ~110):
```
className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
```
to:
```
className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover"
```

Change delete button (line ~80):
```
className="text-red-500 hover:text-red-700 text-sm"
```
to:
```
className="bg-[rgba(239,68,68,0.08)] text-negative px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-[rgba(239,68,68,0.15)]"
```

Change save button (line ~140):
```
className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
```
to:
```
className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover"
```

Change cancel button (line ~146):
```
className="text-gray-500 px-3 py-1 rounded text-sm hover:text-gray-700"
```
to:
```
className="bg-[rgba(0,0,0,0.03)] border border-[rgba(0,0,0,0.04)] text-text-secondary px-4 py-2 rounded-[10px] text-base font-medium hover:bg-[rgba(0,0,0,0.06)]"
```

- [ ] **Step 3: Update form inputs and labels**

All `text-xs text-gray-600` → `text-base text-text-muted`

All form inputs `border rounded px-2 py-1 text-sm` → `bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.08)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[rgba(79,70,229,0.15)] focus:border-primary`

- [ ] **Step 4: Update diff column colors**

Change `text-green-600` → `text-positive` (line ~71)
Change `text-red-600` → `text-negative` (line ~71)

- [ ] **Step 5: Commit**

```bash
cd frontend && git add src/components/AssetClassesTable.tsx && git commit -m "style: update AssetClassesTable with glass design"
```

---

### Task 17: Update MarketSearch

**Files:**
- Modify: `frontend/src/components/MarketSearch.tsx`

- [ ] **Step 1: Update search input**

Change (line ~55):
```
className="w-full border border-gray-300 rounded px-3 py-2"
```
to:
```
className="w-full bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.08)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-[rgba(79,70,229,0.15)] focus:border-primary"
```

- [ ] **Step 2: Update label and radio text**

Change label (line ~46):
```
className="block text-sm font-medium text-gray-700 mb-1"
```
to:
```
className="block text-base font-medium text-text-secondary mb-1"
```

Change radio labels `text-sm` → `text-base`

- [ ] **Step 3: Update search button**

Change (line ~81):
```
className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
```
to:
```
className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover disabled:opacity-50"
```

- [ ] **Step 4: Update error text**

Change (line ~89):
```
className="text-red-600 text-sm"
```
to:
```
className="text-negative text-base bg-[rgba(239,68,68,0.08)] rounded-[10px] px-4 py-3"
```

- [ ] **Step 5: Update quote card**

Change (line ~92):
```
className="bg-white rounded-lg shadow p-4"
```
to:
```
className="bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.04)] rounded-[14px] p-6"
```

Change all `text-sm text-gray-500` → `text-base text-text-muted`

- [ ] **Step 6: Update line chart stroke**

Change (line ~123):
```
stroke="#3B82F6"
```
to:
```
stroke="#4f46e5"
```

- [ ] **Step 7: Commit**

```bash
cd frontend && git add src/components/MarketSearch.tsx && git commit -m "style: update MarketSearch with glass design"
```

---

## Chunk 6: Pages

### Task 18: Update all page headers

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/Portfolio.tsx`
- Modify: `frontend/src/pages/Market.tsx`
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Update Dashboard page header, grid gaps, and loading text**

In `frontend/src/pages/Dashboard.tsx`:

Change (line ~85):
```
<h1 className="text-2xl font-bold">Dashboard</h1>
```
to:
```
<h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">Dashboard</h1>
```

Change grid gaps from `gap-6` to `gap-4` (lines ~84, ~88)

Change loading text (line ~115):
```
<p className="text-gray-500 text-sm">Loading recommendations...</p>
```
to:
```
<p className="text-text-muted text-base">Loading recommendations...</p>
```

- [ ] **Step 2: Update Portfolio page header and grid gaps**

In `frontend/src/pages/Portfolio.tsx`:

Change (line ~71):
```
<h1 className="text-2xl font-bold">Portfolio</h1>
```
to:
```
<h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">Portfolio</h1>
```

Change grid gaps from `gap-6` to `gap-4` (lines ~70, ~73)

- [ ] **Step 3: Update Market page header**

In `frontend/src/pages/Market.tsx`:

Change (line ~6):
```
<h1 className="text-2xl font-bold">Market</h1>
```
to:
```
<h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">Market</h1>
```

- [ ] **Step 4: Update Settings page**

In `frontend/src/pages/Settings.tsx`:

Change (line ~48):
```
<h1 className="text-2xl font-bold">Settings</h1>
```
to:
```
<h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">Settings</h1>
```

Change success message (line ~51):
```
<p className="text-green-600 text-sm">Settings saved successfully</p>
```
to:
```
<p className="text-positive text-base">Settings saved successfully</p>
```

Change loading text (line ~43):
```
<p className="text-gray-500 text-sm">Loading settings...</p>
```
to:
```
<p className="text-text-muted text-base">Loading settings...</p>
```

Change all card containers:
```
className="bg-white rounded-lg shadow p-6"
```
to:
```
className="bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.04)] rounded-[14px] p-6"
```

Change section headings:
```
className="text-lg font-semibold mb-4"
```
to:
```
className="text-lg font-semibold text-text-primary tracking-[-0.3px] mb-4"
```

Change labels:
```
className="block text-sm font-medium text-gray-700 mb-1"
```
to:
```
className="block text-base font-medium text-text-secondary mb-1"
```

Change form inputs:
```
className="w-full border border-gray-300 rounded px-3 py-2"
```
to:
```
className="w-full bg-[rgba(255,255,255,0.7)] border border-[rgba(0,0,0,0.08)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary focus:outline-none focus:ring-2 focus:ring-[rgba(79,70,229,0.15)] focus:border-primary"
```

Change buttons:
```
className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
```
to:
```
className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover disabled:opacity-50"
```

And the second button without `disabled:opacity-50`:
```
className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
```
to:
```
className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover"
```

- [ ] **Step 5: Verify full build**

Run:
```bash
cd frontend && npm run build
```
Expected: Build succeeds with zero errors.

- [ ] **Step 6: Visual verification**

Run:
```bash
cd frontend && npm run dev
```
Open `http://localhost:5173` and check all 4 pages:
- Dashboard: glass cards, indigo charts, new typography
- Portfolio: glass tables, indigo accents, updated buttons
- Market: glass search card, indigo chart line
- Settings: glass form cards, indigo buttons

- [ ] **Step 7: Commit**

```bash
cd frontend && git add src/pages/ && git commit -m "style: update all pages with glass design system"
```

---

## Chunk 7: Final Verification & Cleanup

### Task 19: Run tests and fix any issues

- [ ] **Step 1: Run existing tests**

Run:
```bash
cd frontend && npx vitest run
```
Expected: All tests pass. Since changes are CSS-only, no logic tests should break. If snapshot tests exist, update them.

- [ ] **Step 2: Build production bundle**

Run:
```bash
cd frontend && npm run build
```
Expected: Clean build with no errors.

- [ ] **Step 3: Final commit if any fixes needed**

```bash
cd frontend && git add -A && git commit -m "fix: resolve any test/build issues from glass redesign"
```
(Only if changes were needed)

---

## Future Enhancement (Out of Scope for This Plan)

**Dashboard Stat Cards:** The design spec describes stat cards (Total Value, Monthly Dividends, Total Invested) as top-of-page summary widgets on the Dashboard. The current Dashboard uses `ClassSummaryTable` which serves a similar purpose. Creating dedicated stat card components would require new data aggregation logic (not just styling), so this is deferred to a follow-up task. The mockup at `.superpowers/brainstorm/44702-1773508733/full-design-preview.html` shows the intended stat card design.
