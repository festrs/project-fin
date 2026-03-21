# Design Spec: Apply "The Financial Editorial" Design System

**Date:** 2026-03-21
**Status:** Approved
**Scope:** Full redesign — all components and pages
**Dark mode:** Out of scope for this migration. The `:root` variable architecture supports adding `[data-theme="dark"]` overrides later.

---

## 1. Goal

Migrate the frontend from the current indigo/Plus Jakarta Sans glassmorphic design to the new "Financial Editorial" design system defined in `DESIGN_SYSTEM.md`. Simultaneously, introduce a **themeable architecture** so future design system changes require editing only a single `theme.css` file.

---

## 2. Theme Architecture

### File Structure

```
frontend/src/
  styles/
    theme.css          ← All CSS variables (single source of truth for theming)
    components.css     ← Semantic component classes (.card, .btn-primary, etc.)
  index.css            ← Imports theme + tailwind + @theme bridge + components + base resets
```

### Critical: Tailwind v4 @theme Integration

Tailwind v4's `@theme` block must live in the same file as `@import 'tailwindcss'` (or after it) to be processed correctly. Additionally, `var()` references inside `@theme` may not resolve at build time since Tailwind statically evaluates theme values.

**Solution:** Keep `@theme` in `index.css` with hardcoded hex values (matching `theme.css`). Components and `components.css` use `var()` references from `theme.css` for runtime theming. The `@theme` block serves only as the Tailwind utility bridge.

**To change a theme:** Update both `theme.css` (runtime CSS variables) and the `@theme` block in `index.css` (Tailwind utilities). This is two edits in two files, but both are centralized and clearly marked.

> **Implementation note:** Before full migration, create a minimal proof-of-concept with the proposed CSS structure to confirm the Tailwind v4 Vite plugin resolves everything correctly. If `var()` inside `@theme` does work, consolidate into `theme.css` only.

### theme.css — Design Tokens

All visual values live here. Components reference these via `var()`.

```css
:root {
  /* ── Colors (from DESIGN_SYSTEM.md) ── */
  --color-primary: #004E59;
  --color-primary-container: #006876;
  --color-primary-fixed: #a2efff;
  --color-tertiary: #1d4f40;
  --color-outline-variant: #bec8cb;

  /* ── Colors (supplementary — not in design system, retained for app needs) ── */
  --color-secondary: #10b981;
  --color-secondary-container: #d5e3fd;
  --color-error: #ba1a1a;
  --color-warning: #f59e0b;

  /* ── Text ── */
  --color-on-surface: #191c1e;
  --color-on-surface-variant: #3f484b;
  --color-text-muted: #94a3b8;  /* supplementary — not in design system */

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

### index.css — Orchestrator + Tailwind Bridge

```css
@import './styles/theme.css';
@import 'tailwindcss';

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
  --font-sans: 'Manrope Variable', 'Manrope', sans-serif;
  --radius-DEFAULT: 1rem;
  --radius-sm: 0.5rem;
}

@import './styles/components.css';

/* ── Base resets ── */
.tabular-nums { font-variant-numeric: tabular-nums; }
```

### components.css — Semantic Classes

Components reference these classes instead of inline Tailwind for visual styling.

| Class | Purpose |
|---|---|
| `.card` | Standard content card (glass bg, border, radius, padding) |
| `.card-elevated` | Floating card (adds shadow for modals/dropdowns) |
| `.surface-base` | Page background |
| `.surface-mid` | Section grouping background |
| `.btn-primary` | Gradient CTA (primary → primary-container, 135°) |
| `.btn-ghost` | Ghost/secondary button |
| `.input-field` | Text inputs and selects |
| `.text-display` | Hero numbers (display-lg, tight tracking) |
| `.text-heading` | Section headings (title-lg) |
| `.text-label` | Metadata labels (label-md, uppercase, muted) |
| `.table-row` | Row with hover and zebra striping |
| `.insight-ribbon` | Non-critical notification banner |
| `.badge` | Status chips (rounded, compact) |

**Example — `.card` class:**

```css
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
```

---

## 3. Font Migration

- Add Manrope variable font via Google Fonts `<link>` in `frontend/index.html`
- Remove Plus Jakarta Sans reference from `index.html`
- `theme.css` sets `--font-family: 'Manrope Variable', 'Manrope', sans-serif`

---

## 4. Component Migration Map

All components swap inline visual Tailwind for semantic classes. Layout utilities (`flex`, `grid`, `gap-*`, `mt-*`) stay as Tailwind.

**Migration strategy:** File-by-file manual migration. For each component:
1. Replace visual class strings (`bg-[var(--glass-card-bg)]`, `border border-[...]`, `rounded-[14px]`) with semantic classes (`.card`, `.btn-primary`, etc.)
2. Replace hardcoded color references with CSS variable or Tailwind token equivalents
3. Keep all layout utilities as-is
4. Update corresponding test file if it asserts on class names or snapshots

### App.tsx
- `ProtectedRoute` wrapper: `bg-bg-page` → `.surface-base` or `bg-surface`

### Sidebar.tsx
- Glass nav: `.card` + backdrop-filter
- Logo accent: `var(--color-primary-container)`
- Active nav: `var(--color-primary-fixed)` background tint

### Dashboard.tsx
- Portfolio balance: `.text-display`
- Section margins: `--space-section` / `--space-section-lg`
- Chart wrappers: `.card`

### ClassSummaryTable.tsx / HoldingsTable.tsx / DataTable.tsx
- Remove inline border/bg → `.table-row`
- Zebra striping: `--glass-row-alt`
- Positive values: `var(--color-tertiary)` (#1d4f40)
- Negative values: `var(--color-error)` (#ba1a1a)
- Icon colors inherit from parent `color` — verified via `on-surface` / `on-surface-variant` tokens

### AddAssetForm.tsx / TransactionForm.tsx
- Inputs → `.input-field`
- Submit → `.btn-primary`
- Cancel → `.btn-ghost`

### AllocationChart.tsx / PerformanceChart.tsx / PortfolioCompositionChart.tsx
- Chart colors read from CSS variables (primary, secondary, tertiary)
- Wrapper: `.card`

### ChartCard.tsx
- Simplifies to `.card` + title slot

### Login.tsx
- Primary button: `.btn-primary` (gets gradient)
- Inputs: `.input-field` with bottom-stroke focus

### Settings.tsx
- Inputs → `.input-field`
- Buttons → `.btn-primary` / `.btn-ghost`

### QuarantineBadge.tsx
- Uses `.badge` with warning variant

### Fundamentals.tsx / Invest.tsx / AssetClassHoldings.tsx
- Same pattern: `.card`, `.text-heading`, `.table-row`, spacing tokens

### DividendHistoryModal.tsx
- Modal overlay: `.card-elevated`
- Content follows standard card/table patterns

### Test Files
- `DataTable.test.tsx`, `QuarantineBadge.test.tsx`, `HoldingsTable.test.tsx`, `Settings.test.tsx` — update any class-based assertions or snapshots after migration

---

## 5. New Component: Insight Ribbon

A full-width `--secondary-container` (#d5e3fd) banner for non-critical notifications. Defined in `components.css` as `.insight-ribbon`. Can be dropped into any page layout.

---

## 6. Design System Rules Enforced

- **No-Line Rule:** No `border` for sectioning — only tonal transitions between surfaces
- **Depth Rule:** Lighter surfaces stack on top of darker ones, never reversed
- **No pure black:** All text uses `--color-on-surface` (#191c1e)
- **No pill buttons:** `--radius-default` (1rem) only, no `rounded-full` on buttons
- **No standard shadows on cards:** Elevation through tonal layering only
- **Ghost Border:** `--color-outline-variant` at 15% opacity where accessibility requires a boundary
- **Tabular nums:** Financial data elements use `font-variant-numeric: tabular-nums` (carried forward from current system)

---

## 7. What Stays the Same

- Recharts as charting library
- Tailwind CSS v4 with Vite plugin
- Component file structure (no new component files except potential InsightRibbon)
- All hooks, API layer, routing, state management
- Layout utilities remain as Tailwind classes
- `lucide-react` icons inherit text color from parent — no icon-specific changes needed
