# Apple Dark Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate Project Fin's frontend from a light/dark sidebar layout to an Apple Stocks-inspired dark-only aesthetic with ambient glows, dramatic typography, and top tab navigation.

**Architecture:** CSS-variable-first approach — rewrite `theme.css` with dark-only tokens, rewrite `components.css` with new Apple-style component classes, replace Sidebar+TopAppBar with a single TopNav component, add ambient glow orbs to the app shell. All existing components updated to reference new tokens. ThemeContext deleted (dark-only).

**Tech Stack:** CSS custom properties, Tailwind CSS v4, React 19, TypeScript, Lucide React icons, Recharts

**Spec:** `docs/superpowers/specs/2026-03-22-apple-dark-redesign.md`

---

### Task 1: Rewrite CSS design tokens for dark-only theme (theme.css)

**Files:**
- Modify: `frontend/src/styles/theme.css`

- [ ] **Step 1: Replace entire theme.css with dark-only tokens**

```css
/* ══════════════════════════════════════
   Project Fin — Apple Dark Theme Tokens
   ══════════════════════════════════════ */

:root {
  /* ── Base palette ── */
  --black: #0a0a0a;
  --surface: #1c1c1e;
  --surface-hover: #2c2c2e;
  --border: rgba(255, 255, 255, 0.08);
  --border-hover: rgba(255, 255, 255, 0.14);

  /* ── Text ── */
  --text-primary: #f5f5f7;
  --text-secondary: rgba(255, 255, 255, 0.55);
  --text-tertiary: rgba(255, 255, 255, 0.35);

  /* ── Semantic ── */
  --green: #34c759;
  --red: #ff3b30;
  --blue: #0a84ff;
  --orange: #ff9f0a;
  --purple: #bf5af2;

  /* ── Surfaces ── */
  --card-bg: #1c1c1e;
  --card-border: rgba(255, 255, 255, 0.08);
  --card-bg-hover: #2c2c2e;
  --row-alt: rgba(255, 255, 255, 0.02);
  --row-hover: rgba(255, 255, 255, 0.04);
  --primary-soft: rgba(10, 132, 255, 0.08);
  --primary-ring: rgba(10, 132, 255, 0.25);
  --positive-soft: rgba(52, 199, 89, 0.08);
  --negative-soft: rgba(255, 59, 48, 0.08);

  /* ── Typography ── */
  --font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;

  /* ── Spacing ── */
  --radius: 12px;
  --radius-sm: 8px;
  --radius-pill: 100px;

  /* ── Elevation ── */
  --shadow-floating: 0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.2);

  /* ── Chart ── */
  --chart-line-stroke: #34c759;
  --chart-gradient-start: #34c759;

  /* ── Asset class colors ── */
  --class-us: #0a84ff;
  --class-br: #3b82f6;
  --class-crypto: #bf5af2;
  --class-fixed-income: #ff9f0a;
  --class-emergency: #fbbf24;
}
```

Note: The old `[data-theme="dark"]` block and all `--color-*` prefixed tokens are removed. The new tokens use shorter names matching the spec.

- [ ] **Step 2: Verify no syntax errors**

Run: `cd frontend && npx vite build --mode development 2>&1 | head -20`
Expected: No CSS parse errors (component rendering errors are expected at this stage)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/styles/theme.css
git commit -m "refactor: rewrite theme.css with dark-only Apple tokens"
```

---

### Task 2: Rewrite component CSS classes (components.css)

**Files:**
- Modify: `frontend/src/styles/components.css`

- [ ] **Step 1: Replace entire components.css with new Apple-style classes**

```css
/* ══════════════════════════════════════
   Project Fin — Apple Dark Component Classes
   ══════════════════════════════════════ */

/* ── Cards ── */
.card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius);
  padding: 20px;
  transition: border-color 0.2s;
}

.card:hover {
  border-color: var(--border-hover);
}

.card-elevated {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow-floating);
}

.card-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
  margin-bottom: 16px;
}

/* ── Buttons ── */
.btn-primary {
  background: var(--blue);
  color: white;
  border-radius: var(--radius-pill);
  padding: 10px 24px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover {
  filter: brightness(0.9);
  transform: scale(1.02);
}

.btn-ghost {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-secondary);
  border-radius: var(--radius-pill);
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.btn-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-secondary);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

/* ── Inputs ── */
.input-field {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  font-size: 14px;
  color: var(--text-primary);
  transition: border-color 0.2s;
  width: 100%;
}

.input-field:focus {
  outline: none;
  border-color: var(--blue);
  box-shadow: 0 0 0 2px var(--primary-ring);
}

.input-field::placeholder {
  color: var(--text-tertiary);
}

/* ── Tables ── */
.table-header {
  display: grid;
  padding: 10px 20px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-tertiary);
  border-bottom: 1px solid var(--border);
}

.table-row {
  display: grid;
  padding: 14px 20px;
  font-size: 14px;
  border-bottom: 1px solid var(--border);
  align-items: center;
  cursor: pointer;
  transition: background 0.15s;
}

.table-row:hover {
  background: var(--row-hover);
}

.table-row:nth-child(even) {
  background: var(--row-alt);
}

/* ── Badges ── */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: 11px;
  font-weight: 600;
}

.badge-green {
  background: rgba(52, 199, 89, 0.15);
  color: var(--green);
}

.badge-red {
  background: rgba(255, 59, 48, 0.15);
  color: var(--red);
}

.badge-orange {
  background: rgba(255, 159, 10, 0.15);
  color: var(--orange);
}

.badge-blue {
  background: rgba(10, 132, 255, 0.15);
  color: var(--blue);
}

.badge-warning {
  background: rgba(255, 159, 10, 0.15);
  color: var(--orange);
}

/* ── Period selector pills ── */
.period-btn {
  padding: 5px 14px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: none;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.period-btn:hover {
  color: var(--text-primary);
}

.period-btn.active {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

/* ── Typography utility classes ── */
.text-display {
  font-size: 56px;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1;
  color: var(--text-primary);
}

.text-heading {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.text-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
}

/* ── Semantic text colors ── */
.text-positive {
  color: var(--green);
}

.text-negative {
  color: var(--red);
}

/* ── Score bars ── */
.score-bar {
  height: 6px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  overflow: hidden;
}

.score-bar-fill {
  height: 100%;
  border-radius: 3px;
}

/* ── Tabular numbers ── */
.tabular-nums {
  font-variant-numeric: tabular-nums;
}

/* ── Insight ribbon (kept for compatibility) ── */
.insight-ribbon {
  background: var(--primary-soft);
  border: 1px solid var(--blue);
  border-radius: var(--radius);
  padding: 12px 16px;
  font-size: 13px;
  color: var(--text-secondary);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/styles/components.css
git commit -m "refactor: rewrite components.css with Apple dark component classes"
```

---

### Task 3: Update Tailwind tokens and global styles (index.css)

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Replace index.css with new dark-only Tailwind bridge**

```css
@import "tailwindcss";
@import "./styles/theme.css";
@import "./styles/components.css";

@theme {
  --color-black: #0a0a0a;
  --color-surface: #1c1c1e;
  --color-surface-hover: #2c2c2e;
  --color-text-primary: #f5f5f7;
  --color-text-secondary: rgba(255, 255, 255, 0.55);
  --color-text-tertiary: rgba(255, 255, 255, 0.35);
  --color-green: #34c759;
  --color-red: #ff3b30;
  --color-blue: #0a84ff;
  --color-orange: #ff9f0a;
  --color-purple: #bf5af2;
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

@layer base {
  body {
    background-color: var(--black);
    color: var(--text-primary);
    font-family: var(--font-family);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  * {
    font-variant-numeric: tabular-nums;
  }

  .material-symbols-outlined {
    font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/index.css
git commit -m "refactor: update index.css with dark-only Tailwind tokens"
```

---

### Task 4: Create TopNav component

**Files:**
- Create: `frontend/src/components/TopNav.tsx`

- [ ] **Step 1: Create the TopNav component**

```tsx
import { useLocation, useNavigate, Link } from "react-router-dom";
import { Settings, Bell } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

const TABS = [
  { label: "Portfolio", path: "/" },
  { label: "Fundamentals", path: "/fundamentals" },
  { label: "Market", path: "/market" },
  { label: "Invest", path: "/invest" },
];

export default function TopNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "??";

  const isActive = (path: string) => {
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path);
  };

  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 100,
        background: "rgba(10, 10, 10, 0.85)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderBottom: "1px solid var(--border)",
        padding: "0 32px",
      }}
    >
      <div
        style={{
          maxWidth: 1400,
          margin: "0 auto",
          display: "flex",
          alignItems: "center",
          height: 52,
          gap: 32,
        }}
      >
        {/* Logo */}
        <Link
          to="/"
          style={{
            fontSize: 18,
            fontWeight: 600,
            letterSpacing: "-0.02em",
            color: "var(--text-primary)",
            textDecoration: "none",
            whiteSpace: "nowrap",
          }}
        >
          Fin
        </Link>

        {/* Segmented Tabs */}
        <div
          style={{
            display: "flex",
            gap: 4,
            background: "rgba(255, 255, 255, 0.06)",
            borderRadius: "var(--radius-pill)",
            padding: 3,
          }}
        >
          {TABS.map((tab) => (
            <button
              key={tab.path}
              onClick={() => navigate(tab.path)}
              style={{
                padding: "6px 18px",
                borderRadius: "var(--radius-pill)",
                fontSize: 13,
                fontWeight: 500,
                color: isActive(tab.path)
                  ? "var(--text-primary)"
                  : "var(--text-secondary)",
                background: isActive(tab.path)
                  ? "rgba(255, 255, 255, 0.12)"
                  : "transparent",
                border: "none",
                cursor: "pointer",
                transition: "all 0.2s",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Right Section */}
        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            alignItems: "center",
            gap: 16,
          }}
        >
          <button
            onClick={() => navigate("/settings")}
            style={{
              width: 44,
              height: 44,
              borderRadius: "50%",
              background: "rgba(255, 255, 255, 0.06)",
              border: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-secondary)",
              transition: "all 0.2s",
            }}
          >
            <Settings size={20} />
          </button>
          <button
            style={{
              width: 44,
              height: 44,
              borderRadius: "50%",
              background: "rgba(255, 255, 255, 0.06)",
              border: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-secondary)",
              transition: "all 0.2s",
            }}
          >
            <Bell size={20} />
          </button>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              background: "var(--blue)",
              fontSize: 11,
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "white",
            }}
          >
            {initials}
          </div>
        </div>
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TopNav.tsx
git commit -m "feat: create TopNav component with segmented tabs and frosted blur"
```

---

### Task 5: Create AmbientGlows component

**Files:**
- Create: `frontend/src/components/AmbientGlows.tsx`

- [ ] **Step 1: Create the AmbientGlows component**

```tsx
export default function AmbientGlows() {
  const baseStyle: React.CSSProperties = {
    position: "fixed",
    width: 600,
    height: 600,
    borderRadius: "50%",
    filter: "blur(120px)",
    pointerEvents: "none",
    zIndex: 0,
  };

  return (
    <>
      <div
        style={{
          ...baseStyle,
          top: -100,
          right: -100,
          background: "var(--blue)",
          opacity: 0.07,
        }}
      />
      <div
        style={{
          ...baseStyle,
          bottom: -200,
          left: -100,
          background: "var(--green)",
          opacity: 0.07,
        }}
      />
      <div
        style={{
          ...baseStyle,
          top: "40%",
          left: "50%",
          background: "var(--purple)",
          opacity: 0.04,
        }}
      />
    </>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/AmbientGlows.tsx
git commit -m "feat: create AmbientGlows component for cinematic depth"
```

---

### Task 6: Create Market placeholder page

**Files:**
- Create: `frontend/src/pages/Market.tsx`

- [ ] **Step 1: Create minimal placeholder**

```tsx
export default function Market() {
  return (
    <div>
      <div className="text-label" style={{ marginBottom: 8 }}>
        Market
      </div>
      <h1
        style={{
          fontSize: 32,
          fontWeight: 700,
          letterSpacing: "-0.02em",
          color: "var(--text-primary)",
          marginBottom: 16,
        }}
      >
        Market Overview
      </h1>
      <div className="card">
        <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
          Market data and news feed coming soon.
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Market.tsx
git commit -m "feat: add Market placeholder page"
```

---

### Task 7: Create FundamentalsIndex page

**Files:**
- Create: `frontend/src/pages/FundamentalsIndex.tsx`

This page needs to list all scored assets. It uses the existing `useFundamentals` hook to fetch scores and displays them in score cards + rankings table.

- [ ] **Step 1: Read the useFundamentals hook to understand the API**

Run: `cat frontend/src/hooks/useFundamentals.ts`

Check what endpoints and data shapes are available for listing all fundamentals scores. The new index page will call the list endpoint.

- [ ] **Step 2: Create FundamentalsIndex component**

Create `frontend/src/pages/FundamentalsIndex.tsx`. The component should:

- Fetch all fundamentals scores (use the existing hook or call `/fundamentals/scores` directly)
- Display a page header with "Fundamentals" title and "Stock Scores" heading
- Add a segmented filter (All / US / BR) using inline pill buttons
- Render score cards in a 3-column grid showing: symbol, name, badge (Strong Buy/Buy/Hold/Sell), large score number, and 4 score bars (Profitability, Growth, Valuation, Dividend)
- Score bar color thresholds (0-10 scale): green (>7), orange (5-7), red (<5) — match the spec exactly
- Badge mapping (based on composite_score, 0-10 scale): ≥8 → "Strong Buy" (badge-green), ≥6.5 → "Buy" (badge-green), ≥5 → "Hold" (badge-orange), <5 → "Sell" (badge-red)
- **Important:** Read the useFundamentals hook first (Step 1) to confirm the score scale. The existing Fundamentals detail page uses thresholds ≥90/≥60/<60 — adapt if the API returns 0-100 instead of 0-10.
- Each card clickable, navigates to `/fundamentals/:symbol`
- Below the cards, a rankings table sorted by composite_score descending

Style everything with the new token variables and CSS classes from components.css. Follow the patterns in the mockup at `.superpowers/brainstorm/41781-1774175502/detail-and-fundamentals.html` (Section: "Page: Fundamentals Analysis").

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/FundamentalsIndex.tsx
git commit -m "feat: create FundamentalsIndex page with score cards and rankings"
```

---

### Task 8: Restructure App.tsx — replace layout, update routes

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Read current App.tsx**

Run: `cat frontend/src/App.tsx`

- [ ] **Step 2: Rewrite App.tsx**

Replace the `ProtectedLayout` to:
- Remove `Sidebar` and `TopAppBar` imports and usage
- Remove `ThemeProvider` wrapper (dark-only, no context needed)
- Add `TopNav` and `AmbientGlows` to the protected layout
- Change the main content wrapper from `ml-64 w-[calc(100%-16rem)] pt-24 pb-12 px-8` to `max-w-[1400px] mx-auto px-8 py-8` (full-width, centered)
- Content wrapper should have `position: relative; z-index: 1` to sit above ambient glows
- Add route for `/fundamentals` → `FundamentalsIndex`
- Add route for `/market` → `Market`
- Keep existing `/fundamentals/:symbol` → `Fundamentals`

New imports needed:
```tsx
import TopNav from "./components/TopNav";
import AmbientGlows from "./components/AmbientGlows";
import FundamentalsIndex from "./pages/FundamentalsIndex";
import Market from "./pages/Market";
```

Remove imports:
```tsx
// Delete these:
import Sidebar from "./components/Sidebar";
import TopAppBar from "./components/TopAppBar";
import { ThemeProvider } from "./contexts/ThemeContext";
```

The ProtectedLayout should render:
```tsx
<>
  <AmbientGlows />
  <TopNav />
  <main style={{ position: "relative", zIndex: 1, maxWidth: 1400, margin: "0 auto", padding: 32 }}>
    <Outlet />
  </main>
</>
```

- [ ] **Step 3: Verify the app compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -30`
Expected: May have type errors in pages that still reference old tokens — that's OK, we'll fix those next.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "refactor: replace sidebar layout with TopNav + AmbientGlows shell"
```

---

### Task 9: Delete Sidebar, TopAppBar, and ThemeContext

**Files:**
- Delete: `frontend/src/components/Sidebar.tsx`
- Delete: `frontend/src/components/TopAppBar.tsx`
- Delete: `frontend/src/contexts/ThemeContext.tsx`
- Delete: `frontend/src/components/__tests__/ThemeContext.test.tsx` (if exists)

- [ ] **Step 1: Remove the files**

```bash
rm frontend/src/components/Sidebar.tsx frontend/src/components/TopAppBar.tsx frontend/src/contexts/ThemeContext.tsx
# Also remove any test files for deleted components:
find frontend/src -name "*ThemeContext*" -o -name "*Sidebar.test*" -o -name "*TopAppBar.test*" | xargs rm -f
```

- [ ] **Step 2: Remove all ThemeContext imports across the codebase**

Search for any remaining imports of `useTheme` or `ThemeProvider` or `ThemeContext`:

```bash
cd frontend && grep -rn "ThemeContext\|useTheme\|ThemeProvider" src/ --include="*.tsx" --include="*.ts"
```

Fix each file found — remove the import and any usage of `useTheme()`. The main files will be:
- `frontend/src/pages/Settings.tsx` — remove the theme toggle section entirely
- `frontend/src/App.tsx` — should already be fixed in Task 8
- `frontend/src/main.tsx` — remove ThemeProvider wrapper if present

- [ ] **Step 3: Verify no broken imports**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -i "cannot find\|no exported"`
Expected: No errors related to Sidebar, TopAppBar, or ThemeContext

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Sidebar.tsx frontend/src/components/TopAppBar.tsx frontend/src/contexts/ThemeContext.tsx frontend/src/pages/Settings.tsx frontend/src/App.tsx frontend/src/main.tsx
# Also stage any deleted test files:
git add -u frontend/src/
git commit -m "refactor: delete Sidebar, TopAppBar, and ThemeContext (dark-only)"
```

---

### Task 10: Update Settings page — remove theme toggle

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Read current Settings.tsx**

Run: `cat frontend/src/pages/Settings.tsx`

- [ ] **Step 2: Remove the Appearance/theme section**

Remove the entire "Appearance" card that contains the light/dark toggle. Keep only the Quarantine Settings section. Remove the `useTheme` import.

Update the page styling to use new tokens:
- Page heading: use `text-label` class for the label, inline style for the 32px title
- Card backgrounds: use `card` class (already maps to new tokens)
- Input fields: use `input-field` class
- Button: use `btn-primary` class
- All text colors reference new `--text-*` variables

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "refactor: remove theme toggle from Settings, restyle with dark tokens"
```

---

### Task 11: Update Login page for dark theme

**Files:**
- Modify: `frontend/src/pages/Login.tsx`

- [ ] **Step 1: Read current Login.tsx**

Run: `cat frontend/src/pages/Login.tsx`

- [ ] **Step 2: Update Login styling**

Change the login page to:
- Background: `var(--black)` instead of `bg-surface`
- Card: use `card` class for the centered container
- Input fields: use `input-field` class with new dark tokens
- Button: use `btn-primary` class
- Error text: use `var(--red)` color
- Logo text "Fin": use `var(--text-primary)`, 24px, font-weight 600
- All text: reference `--text-primary`, `--text-secondary`, `--text-tertiary`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Login.tsx
git commit -m "refactor: restyle Login page with dark theme tokens"
```

---

### Task 12: Update Dashboard page for new layout and tokens

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Read current Dashboard.tsx**

Run: `cat frontend/src/pages/Dashboard.tsx`

- [ ] **Step 2: Update Dashboard**

Changes needed:
- Remove any layout offset classes (`ml-64`, `pt-24`, etc.) — App.tsx now handles the container
- Update `CLASS_COLORS` map to use new asset class colors:
  ```typescript
  const CLASS_COLORS: Record<string, string> = {
    us_stocks: "#0a84ff",
    br_stocks: "#3b82f6",
    crypto: "#bf5af2",
    fixed_income: "#ff9f0a",
    emergency_reserve: "#fbbf24",
  };
  ```
- Replace any old color variable references (`--color-primary`, `--color-on-surface`, etc.) with new tokens (`--text-primary`, `--blue`, etc.)
- Replace any Tailwind classes that reference old theme colors (e.g., `text-primary`, `bg-surface`) with new equivalents or inline styles using new CSS variables
- Ensure grid layouts use the spec's gap (16px)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "refactor: update Dashboard with dark theme tokens and new class colors"
```

---

### Task 13: Update PortfolioHeroCard for new typography and chart style

**Files:**
- Modify: `frontend/src/components/PortfolioHeroCard.tsx`

- [ ] **Step 1: Read current PortfolioHeroCard.tsx**

Run: `cat frontend/src/components/PortfolioHeroCard.tsx`

- [ ] **Step 2: Update the hero card**

Changes:
- Background: `var(--surface)` instead of `bg-surface-low`
- Border: `1px solid var(--border)`
- Border-radius: `var(--radius)` (12px)
- Label "Portfolio Value": use `text-label` class (11px, uppercase, tertiary)
- Value: 56px, weight 700, tracking -0.03em, color `var(--text-primary)`
- Period buttons: use `period-btn` CSS class
- Chart SVG: replace gradient fill with solid fill at 10% opacity (`rgba(52, 199, 89, 0.1)`), line stroke `var(--green)`, add glow path (duplicate line with 4px stroke, `blur(8px)`, 40% opacity)
- Loading skeleton: pulse animation with `var(--surface-hover)` background

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PortfolioHeroCard.tsx
git commit -m "refactor: restyle PortfolioHeroCard with dark theme and glow chart"
```

---

### Task 14: Update chart components — colors and fills

**Files:**
- Modify: `frontend/src/components/PerformanceChart.tsx`
- Modify: `frontend/src/components/AllocationDonutChart.tsx`

- [ ] **Step 1: Update PerformanceChart.tsx**

Read the file, then:
- Change line stroke color from `#1e3a5f` to `var(--green)` (or `#34c759`)
- Replace any gradient fill with solid fill at 10% opacity
- Update CartesianGrid stroke to `var(--border)`
- Update axis tick colors to `var(--text-tertiary)`
- Tooltip: background `var(--surface)`, border `var(--border)`, text `var(--text-primary)`

- [ ] **Step 2: Update AllocationDonutChart.tsx**

Read the file, then:
- Colors are passed as props from Dashboard — they'll already be correct from Task 12
- Update tooltip styling: background `var(--surface)`, border `var(--border)`
- Update legend text colors to `var(--text-secondary)`
- Center label text: `var(--text-primary)` for the count, `var(--text-tertiary)` for "classes"

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PerformanceChart.tsx frontend/src/components/AllocationDonutChart.tsx
git commit -m "refactor: update chart colors and fills to dark theme palette"
```

---

### Task 15: Update table components — HoldingsTable, AssetDistributionTable, DataTable

**Files:**
- Modify: `frontend/src/components/HoldingsTable.tsx`
- Modify: `frontend/src/components/AssetDistributionTable.tsx`
- Modify: `frontend/src/components/DataTable.tsx`

- [ ] **Step 1: Read and update HoldingsTable.tsx**

Search and replace across the file:
- `var(--card-border)` → already correct (same token name)
- `var(--row-alt)` → already correct
- `var(--row-hover)` → already correct
- `var(--primary-soft)` → already correct
- Any old `--color-*` references → replace with new equivalents
- Tailwind color classes: `text-on-surface` → use `var(--text-primary)` inline, `text-on-surface-variant` → `var(--text-secondary)`, etc.
- Currency formatting colors: green/red → use `var(--green)` / `var(--red)`
- Any `bg-surface-*` Tailwind classes → replace with inline `var(--surface)` or `var(--black)`

- [ ] **Step 2: Read and update AssetDistributionTable.tsx**

Same token replacements plus:
- Replace `text-cyan-400` → use `var(--blue)` or `color: var(--class-br)`
- Replace `bg-cyan-500/10` → use `rgba(59, 130, 246, 0.1)`
- Replace any `--color-primary-container` → `var(--blue)`
- Replace class icon color mappings to new palette:
  - Emergency reserve: `var(--class-emergency)`
  - Crypto: `var(--class-crypto)`
  - Fixed income: `var(--class-fixed-income)`
  - US stocks: `var(--class-us)`
  - BR stocks: `var(--class-br)`

- [ ] **Step 3: Read and update DataTable.tsx**

Replace old token references with new ones. This is a generic table component — focus on:
- Row alternating colors
- Hover states
- Border colors
- Text colors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/HoldingsTable.tsx frontend/src/components/AssetDistributionTable.tsx frontend/src/components/DataTable.tsx
git commit -m "refactor: update table components with dark theme tokens"
```

---

### Task 16: Update remaining components — NewsCard, BuyRecommendationCard, forms, modals

**Files:**
- Modify: `frontend/src/components/NewsCard.tsx`
- Modify: `frontend/src/components/BuyRecommendationCard.tsx`
- Modify: `frontend/src/components/CorporateEventAlert.tsx`
- Modify: `frontend/src/components/AddAssetForm.tsx`
- Modify: `frontend/src/components/TransactionForm.tsx`
- Modify: `frontend/src/components/DividendHistoryModal.tsx`
- Modify: `frontend/src/components/QuarantineBadge.tsx`
- Modify: `frontend/src/components/ChartCard.tsx`
- Modify: `frontend/src/components/ClassSummaryTable.tsx`

- [ ] **Step 1: Read and update each component**

For each file, apply token replacements:
- Old `--color-*` variables → new `--text-*`, `--blue`, `--green`, `--red`, `--surface`, `--border` variables
- Old `--glass-*` variables → new `--card-bg`, `--border`, `--row-hover` variables (should already be done from previous refactor, but verify)
- Old `--card-bg-hover` → `var(--surface-hover)`
- Tailwind classes: replace any that reference old theme colors
- `backdrop-blur-sm` on modals → replace with solid `background: rgba(0, 0, 0, 0.7)` overlay
- News source badge: use `var(--text-tertiary)` for muted text
- BuyRecommendationCard: card title must be `var(--text-tertiary)` (not green), "View Analysis" button use `btn-ghost` class with small padding

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/NewsCard.tsx frontend/src/components/BuyRecommendationCard.tsx frontend/src/components/CorporateEventAlert.tsx frontend/src/components/AddAssetForm.tsx frontend/src/components/TransactionForm.tsx frontend/src/components/DividendHistoryModal.tsx frontend/src/components/QuarantineBadge.tsx frontend/src/components/ChartCard.tsx frontend/src/components/ClassSummaryTable.tsx
git commit -m "refactor: update remaining components with dark theme tokens"
```

---

### Task 17: Update remaining pages — AssetClassHoldings, Fundamentals detail, Invest

**Files:**
- Modify: `frontend/src/pages/AssetClassHoldings.tsx`
- Modify: `frontend/src/pages/Fundamentals.tsx`
- Modify: `frontend/src/pages/Invest.tsx`

- [ ] **Step 1: Read and update AssetClassHoldings.tsx**

- Remove any layout offset classes
- Replace old color tokens with new ones
- Breadcrumb: use `var(--blue)` for link, `var(--text-tertiary)` for separator and current page
- Action buttons: "Export" = `btn-ghost`, "Add Asset" = `btn-primary`

- [ ] **Step 2: Read and update Fundamentals.tsx (detail page)**

- Remove layout offsets
- Replace chart colors: axis ticks → `var(--text-tertiary)`, grid → `var(--border)`
- Score colors: green → `var(--green)`, yellow → `var(--orange)`, red → `var(--red)`
- Rating dots: same color mapping
- Back button: `btn-ghost`
- Card backgrounds: `card` class

- [ ] **Step 3: Read and update Invest.tsx**

- Remove layout offsets
- Replace color tokens
- Apply card and button classes

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/AssetClassHoldings.tsx frontend/src/pages/Fundamentals.tsx frontend/src/pages/Invest.tsx
git commit -m "refactor: update remaining pages with dark theme tokens"
```

---

### Task 18: Update index.html — remove theme attribute, clean up

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Read index.html**

Run: `cat frontend/index.html`

- [ ] **Step 2: Update**

- Remove `data-theme` attribute from `<html>` tag if present (dark-only, no attribute needed)
- Ensure Inter font link includes weight 700: `family=Inter:wght@400;500;600;700`
- Ensure no Manrope references remain

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "chore: clean up index.html for dark-only theme"
```

---

### Task 19: Build verification and visual check

- [ ] **Step 1: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No type errors. Fix any that appear.

- [ ] **Step 2: Run the build**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 3: Run frontend tests**

```bash
cd frontend && npm run test
```

Expected: All tests pass. Fix any failures — most will be snapshot or DOM-related from the layout change.

- [ ] **Step 4: Run lint**

```bash
cd frontend && npm run lint
```

Expected: No errors. Fix any that appear.

- [ ] **Step 5: Commit any fixes**

```bash
git add -A frontend/
git commit -m "fix: resolve build and test issues from dark theme migration"
```

---

### Task 20: Final visual verification

- [ ] **Step 1: Start the dev server**

```bash
cd frontend && npm run dev
```

- [ ] **Step 2: Verify each page visually**

Check these in the browser at `http://localhost:5173`:

1. **Login** — dark background, centered card, blue primary button
2. **Dashboard** — hero with 56px value, ambient glows visible, donut chart with correct colors, news cards, holdings list
3. **Portfolio detail** — click an asset class, verify breadcrumb, table, dividends
4. **Fundamentals index** — `/fundamentals` shows score cards in grid, rankings table
5. **Fundamentals detail** — click a stock, verify charts render with correct colors
6. **Invest** — calculator works with dark styling
7. **Settings** — no theme toggle, quarantine settings only
8. **Market** — placeholder page renders
9. **TopNav** — segmented tabs highlight correctly, settings/bell icons at 44px, avatar shows initials

Verify:
- No cyan/teal colors anywhere
- No gradients on buttons, cards, or text
- Ambient glows visible behind content
- All text readable (proper contrast on dark backgrounds)
- Charts render with green/red for gains/losses

- [ ] **Step 3: Fix any visual issues found and commit**

```bash
git add -A frontend/
git commit -m "fix: visual polish for Apple dark theme"
```
