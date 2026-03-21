# Design System Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the entire frontend from the current indigo/Plus Jakarta Sans design to "The Financial Editorial" design system with a themeable CSS variable architecture.

**Architecture:** Create a centralized `theme.css` with all CSS variables, bridge to Tailwind via `@theme` in `index.css`, define semantic component classes in `components.css`, then migrate each component file-by-file to use semantic classes instead of inline visual Tailwind.

**Tech Stack:** React 19, Tailwind CSS v4 (Vite plugin), Manrope font (Google Fonts), CSS custom properties

**Spec:** `docs/superpowers/specs/2026-03-21-design-system-migration-design.md`
**Design System:** `DESIGN_SYSTEM.md`

**Safety strategy:** The `@theme` block includes backward-compatible aliases for old token names (`text-primary`, `text-secondary`, `positive`, `negative`, `bg-page`, etc.) so old Tailwind classes continue to work during the migration. Task 16 removes these aliases after all files have been migrated.

---

## File Structure

### New Files
- `frontend/src/styles/theme.css` — All CSS variables (single source of truth)
- `frontend/src/styles/components.css` — Semantic component classes

### Modified Files
- `frontend/index.html` — Swap Plus Jakarta Sans → Manrope font link
- `frontend/src/index.css` — Rewrite: import theme, tailwind, @theme bridge, components, base resets
- `frontend/src/App.tsx:15` — Update `bg-bg-page` to `bg-surface`
- `frontend/src/components/Sidebar.tsx:22-50` — Use theme variables and semantic classes
- `frontend/src/components/ChartCard.tsx:8` — Replace inline glass styles with `.card` class
- `frontend/src/components/QuarantineBadge.tsx:15` — Use `.badge` class
- `frontend/src/components/PerformanceChart.tsx:50` — Update chart stroke color
- `frontend/src/components/AllocationChart.tsx:47-48` — Update bar fill colors
- `frontend/src/components/PortfolioCompositionChart.tsx:15-18` — Update color palette
- `frontend/src/components/DividendHistoryModal.tsx:46-51` — Use `.card-elevated` class
- `frontend/src/components/DataTable.tsx` — Update table row and card styles
- `frontend/src/components/HoldingsTable.tsx` — Update card, button, input, table styles
- `frontend/src/components/ClassSummaryTable.tsx` — Update card, button, input, table styles
- `frontend/src/components/AddAssetForm.tsx` — Update input, button, card styles
- `frontend/src/components/TransactionForm.tsx` — Update input, button styles
- `frontend/src/pages/Login.tsx:28-62` — Use semantic classes
- `frontend/src/pages/Dashboard.tsx:106,147-177` — Use semantic classes, update spacing
- `frontend/src/pages/Settings.tsx:38-81` — Use semantic classes
- `frontend/src/pages/Invest.tsx:29-173` — Use semantic classes
- `frontend/src/pages/Fundamentals.tsx:69-74,164-173,182-197` — Use semantic classes
- `frontend/src/pages/AssetClassHoldings.tsx:151-191` — Use semantic classes

---

## Task 1: Create theme.css — Design Token Foundation

**Files:**
- Create: `frontend/src/styles/theme.css`

- [ ] **Step 1: Create the styles directory and theme.css**

Create `frontend/src/styles/theme.css` with all CSS custom properties:

```css
:root {
  /* ── Colors (from DESIGN_SYSTEM.md) ── */
  --color-primary: #004E59;
  --color-primary-container: #006876;
  --color-primary-fixed: #a2efff;
  --color-tertiary: #1d4f40;
  --color-outline-variant: #bec8cb;

  /* ── Colors (supplementary — app needs beyond design system) ── */
  --color-secondary: #10b981;
  --color-secondary-container: #d5e3fd;
  --color-error: #ba1a1a;
  --color-warning: #f59e0b;

  /* ── Text ── */
  --color-on-surface: #191c1e;
  --color-on-surface-variant: #3f484b;
  --color-text-muted: #94a3b8;

  /* ── Surfaces ── */
  --surface: #f7f9fb;
  --surface-container-low: #f2f4f6;
  --surface-container-lowest: #ffffff;
  --surface-container-high: #e6e8ea;

  /* ── Typography ── */
  --font-family: 'Manrope Variable', 'Manrope', sans-serif;
  --display-lg: 3.5rem;
  --display-lg-tracking: -0.02em;
  --title-lg: 1.375rem;
  --title-lg-tracking: -0.01em;
  --body-md: 0.875rem;
  --body-md-lh: 1.5;
  --label-md: 0.75rem;
  --label-md-tracking: 0.05em;

  /* ── Spacing ── */
  --space-section: 5.5rem;
  --space-section-lg: 7rem;
  --space-card-padding: 1.5rem;
  --space-list-gap: 1rem;

  /* ── Radii ── */
  --radius-default: 1rem;
  --radius-sm: 0.5rem;

  /* ── Elevation ── */
  --shadow-floating: 0px 12px 40px rgba(25, 28, 30, 0.12);

  /* ── Glass ── */
  --glass-bg: rgba(255, 255, 255, 0.8);
  --glass-blur: 20px;
  --glass-border: rgba(190, 200, 203, 0.15);
  --glass-border-input: rgba(190, 200, 203, 0.3);
  --glass-row-alt: rgba(242, 244, 246, 0.5);
  --glass-hover: rgba(0, 0, 0, 0.03);
  --glass-primary-soft: rgba(0, 78, 89, 0.08);
  --glass-primary-ring: rgba(0, 78, 89, 0.15);
  --glass-positive-soft: rgba(16, 185, 129, 0.08);
  --glass-negative-soft: rgba(186, 26, 26, 0.08);
}
```

- [ ] **Step 2: Verify file exists**

Run: `cat frontend/src/styles/theme.css | head -5`
Expected: Shows the `:root {` block opening with the first color variables.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/styles/theme.css
git commit -m "feat(design-system): add theme.css with all design tokens"
```

---

## Task 2: Create components.css — Semantic Component Classes

**Files:**
- Create: `frontend/src/styles/components.css`

- [ ] **Step 1: Create components.css**

Create `frontend/src/styles/components.css` with all semantic classes:

```css
/* ── Cards ── */
.card {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-default);
  padding: var(--space-card-padding);
}

.card-elevated {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-default);
  padding: var(--space-card-padding);
  box-shadow: var(--shadow-floating);
}

/* ── Surfaces ── */
.surface-base {
  background-color: var(--surface);
}

.surface-mid {
  background-color: var(--surface-container-low);
}

/* ── Buttons ── */
.btn-primary {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-container));
  color: white;
  border-radius: var(--radius-default);
  padding: 0.625rem 1.5rem;
  font-size: var(--body-md);
  font-weight: 600;
  transition: opacity 0.15s ease;
  cursor: pointer;
  border: none;
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-ghost {
  background: transparent;
  color: var(--color-primary);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-default);
  padding: 0.625rem 1.5rem;
  font-size: var(--body-md);
  font-weight: 500;
  transition: background-color 0.15s ease;
  cursor: pointer;
}

.btn-ghost:hover {
  background-color: var(--surface-container-high);
}

/* ── Inputs ── */
.input-field {
  width: 100%;
  background: var(--surface-container-high);
  border: none;
  border-bottom: 2px solid transparent;
  border-radius: var(--radius-sm);
  padding: 0.625rem 0.875rem;
  font-size: var(--body-md);
  color: var(--color-on-surface);
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.input-field::placeholder {
  color: var(--color-text-muted);
}

.input-field:focus {
  border-bottom-color: var(--color-primary);
  box-shadow: 0 2px 0 0 var(--glass-primary-ring);
}

/* ── Typography ── */
.text-display {
  font-size: var(--display-lg);
  font-weight: 700;
  letter-spacing: var(--display-lg-tracking);
  color: var(--color-on-surface);
  line-height: 1.1;
}

.text-heading {
  font-size: var(--title-lg);
  font-weight: 600;
  letter-spacing: var(--title-lg-tracking);
  color: var(--color-on-surface);
}

.text-label {
  font-size: var(--label-md);
  font-weight: 500;
  letter-spacing: var(--label-md-tracking);
  text-transform: uppercase;
  color: var(--color-on-surface-variant);
}

/* ── Table ── */
.table-row {
  transition: background-color 0.1s ease;
}

.table-row:nth-child(even) {
  background-color: var(--glass-row-alt);
}

.table-row:hover {
  background-color: var(--glass-hover);
}

/* ── Insight Ribbon ── */
.insight-ribbon {
  width: 100%;
  background-color: var(--color-secondary-container);
  padding: 0.75rem var(--space-card-padding);
  font-size: var(--body-md);
  color: var(--color-on-surface);
  border-radius: var(--radius-sm);
}

/* ── Badge ── */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.625rem;
  border-radius: var(--radius-sm);
  font-size: var(--label-md);
  font-weight: 600;
}

.badge-warning {
  background-color: rgba(245, 158, 11, 0.1);
  color: #b45309;
}
```

- [ ] **Step 2: Verify file exists**

Run: `cat frontend/src/styles/components.css | head -5`
Expected: Shows the `/* ── Cards ── */` comment and `.card` class.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/styles/components.css
git commit -m "feat(design-system): add components.css with semantic classes"
```

---

## Task 3: Swap Font and Rewrite index.css

**Files:**
- Modify: `frontend/index.html:7-9`
- Modify: `frontend/src/index.css:1-33` (full rewrite)

- [ ] **Step 1: Update index.html — swap font**

In `frontend/index.html`, replace lines 7-9:

Old:
```html
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />
```

New:
```html
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet" />
```

- [ ] **Step 2: Rewrite index.css**

Replace entire `frontend/src/index.css` with:

```css
@import './styles/theme.css';
@import "tailwindcss";

/* ── Tailwind theme bridge (hardcoded to match theme.css) ── */
@theme {
  --color-primary: #004E59;
  --color-primary-container: #006876;
  --color-primary-fixed: #a2efff;
  --color-secondary: #10b981;
  --color-tertiary: #1d4f40;
  --color-error: #ba1a1a;
  --color-warning: #f59e0b;
  --color-on-surface: #191c1e;
  --color-on-surface-variant: #3f484b;
  --color-text-muted: #94a3b8;
  --color-surface: #f7f9fb;
  --color-surface-low: #f2f4f6;
  --color-surface-lowest: #ffffff;
  --color-surface-high: #e6e8ea;
  --color-outline-variant: #bec8cb;
  --font-sans: 'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --radius-DEFAULT: 1rem;
  --radius-sm: 0.5rem;

  /* ── Backward-compatible aliases (removed in Task 16 after full migration) ── */
  --color-primary-hover: #003d45;
  --color-positive: #10b981;
  --color-negative: #ba1a1a;
  --color-text-primary: #191c1e;
  --color-text-secondary: #3f484b;
  --color-text-tertiary: #3f484b;
  --color-bg-page: #f7f9fb;
}

@import './styles/components.css';

/* ── Base resets ── */
.tabular-nums {
  font-variant-numeric: tabular-nums;
}
```

Note: The backward-compatible aliases ensure that any `text-text-primary`, `text-text-secondary`, `text-positive`, `text-negative`, `bg-bg-page`, etc. classes in files not yet migrated still resolve correctly. They will be removed in Task 16 after all files are migrated.

- [ ] **Step 3: Verify the dev server starts without errors**

Run: `cd frontend && npm run dev -- --host 2>&1 | head -20`
Expected: Vite dev server starts successfully. Look for "Local:" URL in output. If there are CSS parse errors, they will show here.

Press Ctrl+C to stop after verifying.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html frontend/src/index.css
git commit -m "feat(design-system): swap font to Manrope, rewrite index.css with theme bridge"
```

---

## Task 4: Migrate App.tsx and Sidebar.tsx

**Files:**
- Modify: `frontend/src/App.tsx:15`
- Modify: `frontend/src/components/Sidebar.tsx:22-49`

- [ ] **Step 1: Update App.tsx — ProtectedRoute background**

In `frontend/src/App.tsx`, line 15, replace:

```tsx
    <div className="min-h-screen bg-bg-page flex">
```

With:
```tsx
    <div className="min-h-screen bg-surface flex">
```

- [ ] **Step 2: Update Sidebar.tsx — nav container**

In `frontend/src/components/Sidebar.tsx`, line 22, replace the `<nav>` className:

Old:
```tsx
    <nav className="fixed left-0 top-0 w-[220px] min-h-screen bg-[var(--glass-sidebar-bg)] border-r border-[var(--glass-border)] p-6 flex flex-col gap-1">
```

New:
```tsx
    <nav className="fixed left-0 top-0 w-[220px] min-h-screen bg-surface-low p-6 flex flex-col gap-1" style={{ backdropFilter: `blur(var(--glass-blur))` }}>
```

Note: We use `bg-surface-low` (tonal transition, no border) per the "No-Line Rule".

- [ ] **Step 3: Update Sidebar.tsx — logo accent**

In `frontend/src/components/Sidebar.tsx`, line 23, replace:

Old:
```tsx
      <Link to="/" className="text-2xl font-bold text-text-primary px-3 mb-6 tracking-[-0.3px]">
        Project <span className="text-primary">Fin</span>
```

New:
```tsx
      <Link to="/" className="text-2xl font-bold text-on-surface px-3 mb-6 tracking-[-0.3px]">
        Project <span className="text-primary-container">Fin</span>
```

- [ ] **Step 4: Update Sidebar.tsx — nav links**

In `frontend/src/components/Sidebar.tsx`, lines 32-36, replace the link className:

Old:
```tsx
            className={`flex items-center gap-2.5 px-3 py-2.5 rounded-[10px] text-base font-medium transition-colors ${
              isActive
                ? "bg-[var(--glass-primary-soft)] text-primary font-semibold"
                : "text-text-tertiary hover:bg-[var(--glass-hover)] hover:text-text-primary"
            }`}
```

New:
```tsx
            className={`flex items-center gap-2.5 px-3 py-2.5 rounded-DEFAULT text-base font-medium transition-colors ${
              isActive
                ? "bg-primary-fixed/10 text-primary font-semibold"
                : "text-on-surface-variant hover:bg-[var(--glass-hover)] hover:text-on-surface"
            }`}
```

- [ ] **Step 5: Update Sidebar.tsx — logout button**

In `frontend/src/components/Sidebar.tsx`, line 45, replace:

Old:
```tsx
        className="flex items-center gap-2.5 px-3 py-2.5 rounded-[10px] text-base font-medium text-text-tertiary hover:bg-[var(--glass-hover)] hover:text-text-primary transition-colors mt-auto"
```

New:
```tsx
        className="flex items-center gap-2.5 px-3 py-2.5 rounded-DEFAULT text-base font-medium text-on-surface-variant hover:bg-[var(--glass-hover)] hover:text-on-surface transition-colors mt-auto"
```

- [ ] **Step 6: Verify sidebar renders**

Run: `cd frontend && npx vite build 2>&1 | tail -10`
Expected: Build succeeds with no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Sidebar.tsx
git commit -m "feat(design-system): migrate App.tsx and Sidebar.tsx to new theme"
```

---

## Task 5: Migrate ChartCard and Chart Components

**Files:**
- Modify: `frontend/src/components/ChartCard.tsx:8-9`
- Modify: `frontend/src/components/PerformanceChart.tsx:50`
- Modify: `frontend/src/components/AllocationChart.tsx:47-48`
- Modify: `frontend/src/components/PortfolioCompositionChart.tsx:15-18,88,92`

- [ ] **Step 1: Update ChartCard.tsx**

In `frontend/src/components/ChartCard.tsx`, replace lines 8-9:

Old:
```tsx
    <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
      <h3 className="text-base font-semibold text-text-primary mb-4">{title}</h3>
```

New:
```tsx
    <div className="card">
      <h3 className="text-heading mb-4" style={{ fontSize: '1rem' }}>{title}</h3>
```

- [ ] **Step 2: Update PerformanceChart.tsx — line color**

In `frontend/src/components/PerformanceChart.tsx`, line 50, replace:

Old:
```tsx
              stroke="#4f46e5"
```

New:
```tsx
              stroke="#004E59"
```

- [ ] **Step 3: Update AllocationChart.tsx — bar colors**

In `frontend/src/components/AllocationChart.tsx`, lines 47-48, replace:

Old:
```tsx
          <Bar dataKey="Target" fill="#4f46e5" />
          <Bar dataKey="Actual" fill="#10B981" />
```

New:
```tsx
          <Bar dataKey="Target" fill="#004E59" />
          <Bar dataKey="Actual" fill="#10B981" />
```

- [ ] **Step 4: Update PortfolioCompositionChart.tsx — color palette**

In `frontend/src/components/PortfolioCompositionChart.tsx`, lines 15-18, replace:

Old:
```tsx
const COLORS = [
  "#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16",
];
```

New:
```tsx
const COLORS = [
  "#004E59", "#10b981", "#f59e0b", "#006876", "#8b5cf6",
  "#ec4899", "#14b8a6", "#f97316", "#1d4f40", "#84cc16",
];
```

- [ ] **Step 5: Update PortfolioCompositionChart.tsx — legend and footer text**

In `frontend/src/components/PortfolioCompositionChart.tsx`, line 88, replace:

Old:
```tsx
            formatter={(value) => <span className="text-base text-text-tertiary">{value}</span>}
```

New:
```tsx
            formatter={(value) => <span className="text-base text-on-surface-variant">{value}</span>}
```

Line 92, replace:

Old:
```tsx
      <div className="text-center text-base text-text-muted -mt-2">
```

New:
```tsx
      <div className="text-center text-base text-text-muted -mt-2 tabular-nums">
```

- [ ] **Step 6: Verify build**

Run: `cd frontend && npx vite build 2>&1 | tail -5`
Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ChartCard.tsx frontend/src/components/PerformanceChart.tsx frontend/src/components/AllocationChart.tsx frontend/src/components/PortfolioCompositionChart.tsx
git commit -m "feat(design-system): migrate chart components to new theme"
```

---

## Task 6: Migrate QuarantineBadge and DividendHistoryModal

**Files:**
- Modify: `frontend/src/components/QuarantineBadge.tsx:14-16`
- Modify: `frontend/src/components/DividendHistoryModal.tsx:46-51,54,89,99`

- [ ] **Step 1: Update QuarantineBadge.tsx**

In `frontend/src/components/QuarantineBadge.tsx`, lines 14-16, replace:

Old:
```tsx
    <span
      className="bg-[rgba(245,158,11,0.1)] text-amber-700 px-2.5 py-1 rounded-md text-base font-semibold"
      title={title}
```

New:
```tsx
    <span
      className="badge badge-warning"
      title={title}
```

- [ ] **Step 2: Update DividendHistoryModal.tsx — overlay and card**

In `frontend/src/components/DividendHistoryModal.tsx`, lines 46-51, replace:

Old:
```tsx
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
```

New:
```tsx
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="card-elevated w-full max-w-lg max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
```

- [ ] **Step 3: Update DividendHistoryModal.tsx — heading**

Line 54, replace:

Old:
```tsx
          <h3 className="text-lg font-semibold text-text-primary">
```

New:
```tsx
          <h3 className="text-heading">
```

- [ ] **Step 4: Update DividendHistoryModal.tsx — table header**

Line 89, replace:

Old:
```tsx
                      <tr className="text-text-muted text-xs uppercase tracking-wide">
```

New:
```tsx
                      <tr className="text-label">
```

- [ ] **Step 5: Update DividendHistoryModal.tsx — table rows**

Line 99, replace:

Old:
```tsx
                        <tr key={i} className="even:bg-[var(--glass-row-alt)]">
```

New:
```tsx
                        <tr key={i} className="table-row">
```

- [ ] **Step 6: Update DividendHistoryModal.tsx — remaining old token references**

Line 59: Replace `hover:text-text-primary` with `hover:text-on-surface`
Line 83: Replace `text-text-primary` with `text-on-surface` in `<span className="text-base font-semibold text-text-primary">`
Line 100: Replace `text-text-secondary` with `text-on-surface-variant` in `<td className="py-1 px-1 text-text-secondary">`

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/QuarantineBadge.tsx frontend/src/components/DividendHistoryModal.tsx
git commit -m "feat(design-system): migrate QuarantineBadge and DividendHistoryModal"
```

---

## Task 7: Migrate Login.tsx

**Files:**
- Modify: `frontend/src/pages/Login.tsx:28-62`

- [ ] **Step 1: Update Login.tsx**

Replace lines 28-62:

Old:
```tsx
    <div className="min-h-screen bg-bg-page flex items-center justify-center">
      <div className="glass-card p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-text-primary mb-6 text-center">
          Project <span className="text-primary">Fin</span>
        </h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="glass-input px-3 py-2 rounded-lg text-text-primary bg-[var(--glass-input-bg)] border border-[var(--glass-border)] outline-none focus:border-primary"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="glass-input px-3 py-2 rounded-lg text-text-primary bg-[var(--glass-input-bg)] border border-[var(--glass-border)] outline-none focus:border-primary"
          />
          {error && (
            <p className="text-red-400 text-sm text-center">{error}</p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="bg-primary text-white py-2 rounded-lg font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
```

New:
```tsx
    <div className="min-h-screen bg-surface flex items-center justify-center">
      <div className="card w-full max-w-sm" style={{ padding: '2rem' }}>
        <h1 className="text-2xl font-bold text-on-surface mb-6 text-center">
          Project <span className="text-primary-container">Fin</span>
        </h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="input-field"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="input-field"
          />
          {error && (
            <p className="text-error text-sm text-center">{error}</p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="btn-primary"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Login.tsx
git commit -m "feat(design-system): migrate Login.tsx to new theme"
```

---

## Task 8: Migrate Settings.tsx

**Files:**
- Modify: `frontend/src/pages/Settings.tsx:33,38,41,45-46,49,52-58,62,65-71,74-78`

- [ ] **Step 1: Update Settings.tsx**

Replace the loading text (line 33):

Old: `<p className="text-text-muted text-base">Loading settings...</p>`
New: `<p className="text-text-muted text-base">Loading settings...</p>` (no change needed — `text-muted` stays)

Replace heading (line 38):

Old: `<h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">Settings</h1>`
New: `<h1 className="text-display" style={{ fontSize: '2rem' }}>Settings</h1>`

Replace success message (line 41):

Old: `<p className="text-positive text-base">Settings saved successfully</p>`
New: `<p className="text-secondary text-base">Settings saved successfully</p>`

Replace card container (line 45):

Old: `<div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">`
New: `<div className="card">`

Replace section heading (line 46):

Old: `<h2 className="text-lg font-semibold text-text-primary tracking-[-0.3px] mb-4">Quarantine Settings</h2>`
New: `<h2 className="text-heading mb-4">Quarantine Settings</h2>`

Replace label class (lines 49, 62):

Old: `className="block text-base font-medium text-text-secondary mb-1"`
New: `className="block text-base font-medium text-on-surface-variant mb-1"`

Replace both input classes (lines 58, 71):

Old: `className="w-full bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"`
New: `className="input-field"`

Replace button (lines 74-78):

Old:
```tsx
            className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover disabled:opacity-50"
```

New:
```tsx
            className="btn-primary"
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat(design-system): migrate Settings.tsx to new theme"
```

---

## Task 9: Migrate Invest.tsx

**Files:**
- Modify: `frontend/src/pages/Invest.tsx:29-173`

- [ ] **Step 1: Update page heading**

Line 30, replace:

Old: `<h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">Where to Invest</h1>`
New: `<h1 className="text-display" style={{ fontSize: '2rem' }}>Where to Invest</h1>`

- [ ] **Step 2: Update input bar card**

Line 33, replace:

Old: `<div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">`
New: `<div className="card">`

- [ ] **Step 3: Update all label classes**

Lines 36, 52, 66 — replace each:

Old: `className="block text-base font-medium text-text-secondary mb-1"`
New: `className="block text-base font-medium text-on-surface-variant mb-1"`

- [ ] **Step 4: Update all input/select classes**

Lines 48, 59, 75 — replace each input/select className:

Old: `className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary ... focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"`
New: `className="input-field"`

Note: For the amount input (line 48), keep the `w-40` by adding it: `className="input-field w-40"`
For the count input (line 75), keep `w-24`: `className="input-field w-24"`

- [ ] **Step 5: Update calculate button**

Line 81, replace:

Old: `className="bg-primary text-white px-6 py-2.5 rounded-[10px] text-base font-semibold hover:bg-primary-hover disabled:opacity-50 transition-colors"`
New: `className="btn-primary"`

- [ ] **Step 6: Update error card**

Line 90, replace:

Old: `<div className="bg-negative/10 border border-negative/30 rounded-[14px] p-4">`
New: `<div className="bg-error/10 border border-error/30 rounded-DEFAULT p-4">`

Line 91, replace:

Old: `<p className="text-negative text-base">{error}</p>`
New: `<p className="text-error text-base">{error}</p>`

- [ ] **Step 7: Update result/empty/loading cards**

Lines 97, 103, 109 — replace each:

Old: `<div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">`
New: `<div className="card">`

- [ ] **Step 8: Update results heading**

Line 110, replace:

Old: `<h2 className="text-lg font-semibold text-text-primary tracking-[-0.3px] mb-4">Investment Plan</h2>`
New: `<h2 className="text-heading mb-4">Investment Plan</h2>`

- [ ] **Step 9: Update table header and rows**

Line 126, replace:

Old: `<tr className="text-text-muted text-left border-b border-[var(--glass-border)]">`
New: `<tr className="text-label text-left">`

Line 139, replace:

Old: `<tr key={rec.symbol} className="border-b border-[var(--glass-border)] last:border-0 even:bg-[var(--glass-row-alt)]">`
New: `<tr key={rec.symbol} className="table-row">`

Line 144, replace:

Old: `<td className="py-2.5 px-2 text-right text-positive">+{rec.diff.toFixed(1)}%</td>`
New: `<td className="py-2.5 px-2 text-right text-tertiary">+{rec.diff.toFixed(1)}%</td>`

Line 152, replace:

Old: `<tr className="border-t-2 border-[var(--glass-border)] font-bold">`
New: `<tr className="border-t-2 border-outline-variant/15 font-bold">`

- [ ] **Step 10: Update text color references**

Replace all remaining `text-text-primary` with `text-on-surface`, `text-text-muted` stays as `text-text-muted` (mapped in @theme), `text-text-secondary` with `text-on-surface-variant`.

- [ ] **Step 11: Commit**

```bash
git add frontend/src/pages/Invest.tsx
git commit -m "feat(design-system): migrate Invest.tsx to new theme"
```

---

## Task 10: Migrate Dashboard.tsx

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx:105-188`

- [ ] **Step 1: Update page heading**

Line 106, replace:

Old: `<h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">Dashboard</h1>`
New: `<h1 className="text-display" style={{ fontSize: '2rem' }}>Dashboard</h1>`

- [ ] **Step 2: Update pending splits section**

Line 147, replace:

Old: `<h2 className="text-lg font-semibold text-text-primary">Pending Corporate Events</h2>`
New: `<h2 className="text-heading">Pending Corporate Events</h2>`

Line 151, replace:

Old: `<div key={split.id} className={`glass-card p-4 border border-yellow-500/30 bg-yellow-500/5 ${isLoading ? "opacity-60" : ""}`}>`
New: `<div key={split.id} className={`card border border-warning/30 bg-warning/5 ${isLoading ? "opacity-60" : ""}`}>`

Line 154, replace:

Old: `<p className="text-text-primary font-medium">`
New: `<p className="text-on-surface font-medium">`

Line 170, replace:

Old: `className="px-3 py-1.5 text-sm rounded-lg bg-accent/20 text-accent hover:bg-accent/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"`
New: `className="btn-primary px-3 py-1.5 text-sm"`

Line 177, replace:

Old: `className="px-3 py-1.5 text-sm rounded-lg bg-surface-card text-text-muted hover:text-text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"`
New: `className="btn-ghost px-3 py-1.5 text-sm"`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat(design-system): migrate Dashboard.tsx to new theme"
```

---

## Task 11: Migrate Fundamentals.tsx

**Files:**
- Modify: `frontend/src/pages/Fundamentals.tsx:69-74,106,115,117-123,133,164-173,182-197,206,228-229,261-262,283`

- [ ] **Step 1: Update ScoreBreakdownCard styles**

Lines 69-74, replace:

Old:
```tsx
    <div
      className="p-6 rounded-[14px]"
      style={{
        background: "var(--glass-card-bg)",
        border: "1px solid var(--glass-border)",
      }}
    >
```

New:
```tsx
    <div className="card">
```

Line 77, replace:

Old: `<h2 className="text-primary text-lg font-semibold">Score Breakdown</h2>`
New: `<h2 className="text-heading text-primary">Score Breakdown</h2>`

Line 89, replace:

Old: `<span className="text-secondary text-sm">{c.label}</span>`
New: `<span className="text-on-surface-variant text-sm">{c.label}</span>`

- [ ] **Step 2: Update loading/error/empty states**

Line 106, replace:

Old: `<div className="text-primary text-center mt-20">`
New: `<div className="text-primary text-center mt-20">`

(This one stays the same.)

Line 115, replace:

Old: `<p className="text-red-400 mb-4">{error}</p>`
New: `<p className="text-error mb-4">{error}</p>`

Lines 117-123, replace:

Old:
```tsx
          <button
            onClick={refresh}
            className="px-4 py-2 rounded-lg text-sm"
            style={{
              background: "var(--glass-card-bg)",
              border: "1px solid var(--glass-border)",
              color: "var(--color-text-primary)",
            }}
          >
```

New:
```tsx
          <button onClick={refresh} className="btn-ghost px-4 py-2 text-sm">
```

Line 133, replace:

Old: `<div className="text-muted text-center mt-20">No data available.</div>`
New: `<div className="text-text-muted text-center mt-20">No data available.</div>`

- [ ] **Step 3: Update axisStyle — fix removed variable reference**

Line 164, replace:

Old: `const axisStyle = { stroke: "var(--color-text-secondary)", fontSize: 12 };`
New: `const axisStyle = { stroke: "var(--color-on-surface-variant)", fontSize: 12 };`

- [ ] **Step 4: Update cardStyle and chart cards**

Lines 170-173, replace:

Old:
```tsx
  const cardStyle: React.CSSProperties = {
    background: "var(--glass-card-bg)",
    border: "1px solid var(--glass-border)",
  };
```

Remove this `cardStyle` variable entirely.

Lines 182-184, replace:

Old:
```tsx
          <button
            onClick={() => navigate(-1)}
            className="px-3 py-1.5 rounded-lg text-sm"
            style={cardStyle}
```

New:
```tsx
          <button
            onClick={() => navigate(-1)}
            className="btn-ghost px-3 py-1.5 text-sm"
```

Line 187, replace:

Old: `<h1 className="text-primary text-2xl font-bold">`
New: `<h1 className="text-primary text-2xl font-bold">`

(Stays the same.)

Lines 192-194, replace:

Old:
```tsx
          <button
            onClick={refresh}
            className="px-4 py-2 rounded-lg text-sm font-medium"
            style={cardStyle}
```

New:
```tsx
          <button
            onClick={refresh}
            className="btn-ghost px-4 py-2 text-sm font-medium"
```

Lines 205, 227, 261 — replace all `<div className="p-6 rounded-[14px]" style={cardStyle}>` with:
```tsx
        <div className="card">
```

Lines 206, 228, 262 — replace all `<h2 className="text-primary text-lg font-semibold mb-4">` with:
```tsx
          <h2 className="text-heading text-primary mb-4">
```

Line 283, replace:

Old: `<p className="text-muted text-xs text-right">`
New: `<p className="text-text-muted text-xs text-right">`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Fundamentals.tsx
git commit -m "feat(design-system): migrate Fundamentals.tsx to new theme"
```

---

## Task 12: Migrate AssetClassHoldings.tsx

**Files:**
- Modify: `frontend/src/pages/AssetClassHoldings.tsx:152-191`

- [ ] **Step 1: Update breadcrumb links**

Lines 152, 163, replace:

Old: `className="text-primary hover:text-primary-hover text-base"`
New: `className="text-primary hover:opacity-80 text-base"`

- [ ] **Step 2: Update page heading**

Line 167, replace:

Old: `<h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">`
New: `<h1 className="text-display" style={{ fontSize: '2rem' }}>`

- [ ] **Step 3: Update emergency reserve badge**

Line 172, replace:

Old: `<span className="ml-2 text-xs bg-[var(--glass-primary-soft)] px-2 py-0.5 rounded">`
New: `<span className="ml-2 badge" style={{ backgroundColor: 'var(--glass-primary-soft)' }}>`

- [ ] **Step 4: Update fundamentals loading indicator**

Line 184, replace:

Old: `<div className="flex items-center gap-2 px-4 py-3 bg-[var(--glass-primary-soft)] border border-[var(--glass-border)] rounded-[10px] text-base text-primary">`
New: `<div className="insight-ribbon flex items-center gap-2" style={{ backgroundColor: 'var(--glass-primary-soft)', color: 'var(--color-primary)' }}>`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/AssetClassHoldings.tsx
git commit -m "feat(design-system): migrate AssetClassHoldings.tsx to new theme"
```

---

## Task 13: Migrate DataTable.tsx

**Files:**
- Modify: `frontend/src/components/DataTable.tsx`

**Migration pattern reference (applies to Tasks 13-17):**
- `bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6` → `card` class
- Inline input classes → `input-field` class
- Inline button classes → `btn-primary` or `btn-ghost` class
- `text-text-primary` → `text-on-surface`
- `text-text-secondary` → `text-on-surface-variant`
- `text-text-tertiary` → `text-on-surface-variant`
- `text-positive` → `text-tertiary` (for gains)
- `text-negative` → `text-error` (for losses)
- `even:bg-[var(--glass-row-alt)]` → `table-row` class
- `bg-primary text-white ... rounded-[10px]` → `btn-primary` class
- `rounded-[14px]` → `rounded-DEFAULT`
- `rounded-[10px]` → `rounded-sm`
- `hover:bg-primary-hover` → (handled by btn-primary)
- `focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary` → (handled by input-field)

- [ ] **Step 1: Read DataTable.tsx and identify all visual class strings**

Read `frontend/src/components/DataTable.tsx` (179 lines). Search for all occurrences of: `glass-card-bg`, `glass-border`, `rounded-[14px]`, `rounded-[10px]`, `text-text-primary`, `text-text-secondary`, `text-text-tertiary`, `text-positive`, `text-negative`, `bg-primary`, `glass-row-alt`, `glass-hover`, `glass-primary-ring`.

- [ ] **Step 2: Apply all replacements per migration pattern**

For each match found in Step 1, apply the corresponding replacement from the migration pattern above. Key areas:
- Card wrappers → `card`
- Filter/sort input styling → `input-field`
- Table row classes → `table-row`
- Header text → `text-on-surface`, `text-on-surface-variant`

- [ ] **Step 3: Verify build**

Run: `cd frontend && npx vite build 2>&1 | tail -5`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/DataTable.tsx
git commit -m "feat(design-system): migrate DataTable.tsx to new theme"
```

---

## Task 14: Migrate AddAssetForm.tsx

**Files:**
- Modify: `frontend/src/components/AddAssetForm.tsx` (363 lines)

- [ ] **Step 1: Read AddAssetForm.tsx and identify all visual class strings**

Read `frontend/src/components/AddAssetForm.tsx`. This file has ~15 form fields. Search for all occurrences of the old tokens listed in the migration pattern.

- [ ] **Step 2: Replace all input/select classes**

Every `<input>` and `<select>` element: replace the long inline className with `input-field`. Preserve any width overrides (e.g., `w-full`, `w-40`) by appending them: `className="input-field w-40"`.

- [ ] **Step 3: Replace all button classes**

- Submit button → `btn-primary`
- Cancel/secondary buttons → `btn-ghost`

- [ ] **Step 4: Replace card wrapper and text tokens**

- Card wrapper → `card`
- Labels: `text-text-secondary` → `text-on-surface-variant`
- Values: `text-text-primary` → `text-on-surface`
- `text-negative` → `text-error`
- Search dropdown floating menu → `card-elevated`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/AddAssetForm.tsx
git commit -m "feat(design-system): migrate AddAssetForm.tsx to new theme"
```

---

## Task 15: Migrate TransactionForm.tsx

**Files:**
- Modify: `frontend/src/components/TransactionForm.tsx` (201 lines)

- [ ] **Step 1: Read TransactionForm.tsx and identify all visual class strings**

Read `frontend/src/components/TransactionForm.tsx`. Search for old tokens.

- [ ] **Step 2: Replace all input/select classes → `input-field`**

Preserve width overrides where present.

- [ ] **Step 3: Replace button and text token classes**

- Submit → `btn-primary`
- Cancel → `btn-ghost`
- Labels: `text-text-secondary` → `text-on-surface-variant`
- Text: `text-text-primary` → `text-on-surface`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/TransactionForm.tsx
git commit -m "feat(design-system): migrate TransactionForm.tsx to new theme"
```

---

## Task 16: Migrate HoldingsTable.tsx

**Files:**
- Modify: `frontend/src/components/HoldingsTable.tsx` (750 lines)

- [ ] **Step 1: Read HoldingsTable.tsx and inventory all visual class strings**

Read `frontend/src/components/HoldingsTable.tsx`. This is the largest component. Systematically search for every old token. Create a list of all line numbers and old → new replacements.

- [ ] **Step 2: Replace card and container classes**

All instances of `bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px]` → `card`
Dropdown menus → `card-elevated`

- [ ] **Step 3: Replace input classes → `input-field`**

All inline input classNames → `input-field` (with width overrides preserved).

- [ ] **Step 4: Replace button classes**

- Primary action buttons → `btn-primary`
- Secondary/ghost buttons → `btn-ghost`

- [ ] **Step 5: Replace table row and text color tokens**

- `even:bg-[var(--glass-row-alt)]` → `table-row`
- `text-text-primary` → `text-on-surface`
- `text-text-secondary` → `text-on-surface-variant`
- `text-text-tertiary` → `text-on-surface-variant`
- `text-positive` → `text-tertiary`
- `text-negative` → `text-error`

- [ ] **Step 6: Verify build**

Run: `cd frontend && npx vite build 2>&1 | tail -5`
Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/HoldingsTable.tsx
git commit -m "feat(design-system): migrate HoldingsTable.tsx to new theme"
```

---

## Task 17: Migrate ClassSummaryTable.tsx

**Files:**
- Modify: `frontend/src/components/ClassSummaryTable.tsx` (613 lines)

- [ ] **Step 1: Read ClassSummaryTable.tsx and inventory all visual class strings**

Read `frontend/src/components/ClassSummaryTable.tsx`. Systematically search for every old token.

- [ ] **Step 2: Replace card, input, button, and table row classes**

Same migration pattern as HoldingsTable:
- Card wrappers → `card`
- Inputs → `input-field`
- Buttons → `btn-primary` / `btn-ghost`
- Table rows → `table-row`
- Progress bar: `bg-primary` stays (now maps to #004E59)

- [ ] **Step 3: Replace text color tokens**

- `text-text-primary` → `text-on-surface`
- `text-text-secondary` → `text-on-surface-variant`
- `text-text-tertiary` → `text-on-surface-variant`
- `text-positive` → `text-tertiary`
- `text-negative` → `text-error`

- [ ] **Step 4: Verify full build**

Run: `cd frontend && npx vite build 2>&1 | tail -10`
Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ClassSummaryTable.tsx
git commit -m "feat(design-system): migrate ClassSummaryTable.tsx to new theme"
```

---

## Task 18: Update Tests

**Files:**
- Modify: `frontend/src/components/__tests__/DataTable.test.tsx`
- Modify: `frontend/src/components/__tests__/QuarantineBadge.test.tsx`
- Modify: `frontend/src/components/__tests__/HoldingsTable.test.tsx`
- Modify: `frontend/src/components/__tests__/Settings.test.tsx`

- [ ] **Step 1: Read each test file to identify class-name assertions**

Read all 4 test files and identify any assertions that reference old class names (e.g., `bg-[var(--glass-card-bg)]`, `rounded-[14px]`, `text-text-primary`, `text-positive`, `text-negative`, color hex values, etc.).

- [ ] **Step 2: Update class-name assertions**

For each assertion found:
- Replace old class references with new semantic class names
- Replace old color token references with new tokens
- If tests use snapshots, update the snapshots

- [ ] **Step 3: Run tests**

Run: `cd frontend && npm run test -- --run 2>&1`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/__tests__/
git commit -m "test(design-system): update test assertions for new class names"
```

---

## Task 19: Final Verification and Alias Cleanup

- [ ] **Step 1: Full build check**

Run: `cd frontend && npm run build 2>&1`
Expected: TypeScript check passes, Vite build succeeds.

- [ ] **Step 2: Run all tests**

Run: `cd frontend && npm run test -- --run 2>&1`
Expected: All tests pass.

- [ ] **Step 3: Run linter**

Run: `cd frontend && npm run lint 2>&1`
Expected: No errors.

- [ ] **Step 4: Remove backward-compatible aliases from @theme**

After confirming all files are migrated, remove the alias block from `frontend/src/index.css`:

Remove these lines from the `@theme` block:
```css
  /* ── Backward-compatible aliases (removed in Task 16 after full migration) ── */
  --color-primary-hover: #003d45;
  --color-positive: #10b981;
  --color-negative: #ba1a1a;
  --color-text-primary: #191c1e;
  --color-text-secondary: #3f484b;
  --color-text-tertiary: #3f484b;
  --color-bg-page: #f7f9fb;
```

- [ ] **Step 5: Verify no remaining references to old tokens**

Run these searches to confirm no old tokens remain in source files:

```bash
cd frontend/src && grep -r "text-text-primary\|text-text-secondary\|text-text-tertiary\|text-positive\|text-negative\|bg-bg-page\|hover:bg-primary-hover\|glass-card-bg\|glass-sidebar-bg\|glass-input-bg\|glass-border-input\|rounded-\[14px\]\|rounded-\[10px\]" --include="*.tsx" --include="*.ts" -l
```

Expected: No files returned. If any files still reference old tokens, update them before proceeding.

- [ ] **Step 6: Full build + tests after alias removal**

Run: `cd frontend && npm run build 2>&1 && npm run test -- --run 2>&1`
Expected: Build and all tests pass with no errors.

- [ ] **Step 7: Visual check list**

Start dev server and verify in browser:
- [ ] Font is Manrope (not Plus Jakarta Sans)
- [ ] Primary color is deep teal (#004E59), not indigo
- [ ] Cards use glass effect with rounded-DEFAULT (1rem)
- [ ] Buttons have gradient (primary → primary-container)
- [ ] Inputs have bottom-stroke focus effect
- [ ] No hard borders between sections (tonal transitions only)
- [ ] Sidebar uses surface-low background (no border-right line)
- [ ] Charts use teal/green palette
- [ ] Positive values show in tertiary (#1d4f40), negative in error (#ba1a1a)

- [ ] **Step 8: Final commit**

```bash
git add -A
git commit -m "feat(design-system): remove backward-compatible aliases, migration complete"
```
