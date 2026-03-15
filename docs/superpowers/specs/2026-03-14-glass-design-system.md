# Glass Design System — Project Fin

## Overview

Redesign the Project Fin web application with a minimal glassmorphism aesthetic inspired by Apple's recent iOS/macOS design language. The goal is to make the interface more vivid, polished, and easier to read while maintaining a professional finance-app feel.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Style | Minimal Glass | Clean white/gray base with barely-there frosted panels. Professional, calm, Apple iOS-like. |
| Navigation | Left sidebar | Icon + label navigation. More app-like feel, room for future nav items. Replaces current top navbar. |
| Accent color | Indigo `#4f46e5` | Sophisticated, Apple-like. Replaces current blue-600. |
| Typography | Plus Jakarta Sans | Geometric, friendly, professional. Loaded via Google Fonts. |
| Card style | Barely-there | Subtle border `rgba(0,0,0,0.04)`, almost no shadow, `rgba(255,255,255,0.7)` background. |
| Table style | Borderless rows | Alternating subtle background tints (`rgba(0,0,0,0.015)`), generous spacing, no grid lines. |
| Layout | Full-width | Content fills entire screen width. No max-width constraint on main area. |

## Design Tokens

### Colors

```
# Primary
--color-primary: #4f46e5          (indigo — accent, active states, primary buttons)
--color-primary-hover: #4338ca    (indigo-700 — hover states)
--color-primary-soft: rgba(79,70,229,0.08)  (indigo tint — active nav bg, subtle highlights)

# Semantic
--color-positive: #10b981        (green — gains, buy actions)
--color-positive-soft: rgba(16,185,129,0.08)
--color-negative: #ef4444        (red — losses, sell actions)
--color-negative-soft: rgba(239,68,68,0.08)
--color-warning: #f59e0b         (amber — warnings, quarantine)

# Neutrals
--color-text-primary: #0f172a    (headings, tickers, strong text)
--color-text-secondary: #334155  (body text, mono values)
--color-text-tertiary: #64748b   (nav items, legend text, descriptions)
--color-text-muted: #94a3b8      (labels, table headers, subtitles)

# Surfaces
--color-bg-page: #f8f9fb         (page background)
--color-bg-card: rgba(255,255,255,0.7)   (card/panel background)
--color-bg-sidebar: rgba(255,255,255,0.85)  (sidebar background)
--color-bg-row-alt: rgba(0,0,0,0.015)    (alternating table rows)
--color-bg-hover: rgba(0,0,0,0.03)       (hover states)

# Borders
--color-border-card: rgba(0,0,0,0.04)    (card borders)
--color-border-sidebar: rgba(0,0,0,0.04) (sidebar right border)
```

### Typography

**Font family:** `'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`

**Type scale (multiples of 8, starting at 16):**

| Token | Size | Weight | Usage |
|-------|------|--------|-------|
| `text-base` | 16px | 400–600 | All body text, labels, nav items, card titles, table rows, badges, legend, stat changes, table headers (uppercase variant), ticker subtitles |
| `text-lg` | 24px | 600–700 | Sidebar logo, section labels |
| `text-xl` | 32px | 700 | Page titles, stat values |

**Additional typography rules:**
- Uppercase labels: `text-transform: uppercase; letter-spacing: 0.8px; font-weight: 600; color: var(--color-text-muted)`
- Tabular numbers for financial data: `font-variant-numeric: tabular-nums`
- Heading letter-spacing: `-0.5px` for 32px, `-0.3px` for 24px

### Spacing

All spacing uses multiples of 8:
- Card padding: 24px
- Page padding: 40px horizontal, 32px vertical
- Grid gaps: 16px
- Sidebar width: 220px (fixed)
- Border radius — cards: 14px, badges: 6px, nav items: 10px, table rows: 8px

### Badges

```
# Positive badge
background: rgba(16,185,129,0.08)
color: #059669
padding: 4px 10px
border-radius: 6px
font-size: 16px
font-weight: 600

# Negative badge
background: rgba(239,68,68,0.08)
color: #dc2626
```

## Layout Structure

### Before (current)
```
┌─────────────────────────────────────────┐
│  Top Navbar (Project Fin | links)       │
├─────────────────────────────────────────┤
│                                         │
│   container mx-auto (max-width capped)  │
│                                         │
└─────────────────────────────────────────┘
```

### After (new)
```
┌──────┬──────────────────────────────────┐
│      │                                  │
│  S   │   Full-width main content        │
│  I   │   padding: 32px 40px             │
│  D   │                                  │
│  E   │   ┌────────┬────────┬────────┐   │
│  B   │   │ Stat 1 │ Stat 2 │ Stat 3 │   │
│  A   │   └────────┴────────┴────────┘   │
│  R   │                                  │
│      │   ┌──────────────┬──────────┐    │
│ 220  │   │ Performance  │Allocation│    │
│  px  │   │ Chart        │ Donut    │    │
│      │   └──────────────┴──────────┘    │
│      │                                  │
│      │   ┌──────────────────────────┐   │
│      │   │ Holdings Table           │   │
│      │   │ (borderless alt rows)    │   │
│      │   └──────────────────────────┘   │
│      │                                  │
└──────┴──────────────────────────────────┘
```

### Sidebar Navigation

- Fixed left, full viewport height
- Background: `rgba(255,255,255,0.85)` with right border `rgba(0,0,0,0.04)`
- Logo: "Project **Fin**" — "Fin" in indigo accent
- Nav items: Lucide React icons (18x18, stroke-width 1.8) + label
  - Dashboard: `LayoutGrid`
  - Portfolio: `Wallet`
  - Market: `TrendingUp`
  - Settings: `Settings`
- Active state: `rgba(79,70,229,0.08)` background, indigo text, font-weight 600
- Hover state: `rgba(0,0,0,0.03)` background
- Pages: Dashboard, Portfolio, Market, Settings

### Main Content Area

- `margin-left: 220px` to account for fixed sidebar
- `width: calc(100% - 220px)` — fills remaining screen
- `padding: 32px 40px`
- No max-width constraint

## Component Specifications

### Stat Cards

Top-of-page summary cards in a 3-column grid:
- Background: `rgba(255,255,255,0.7)`
- Border: `1px solid rgba(0,0,0,0.04)`
- Border-radius: 14px
- Padding: 24px
- Label: 16px uppercase muted
- Value: 32px bold
- Change indicator: 16px semibold, green/red

### Chart Cards

Container for Recharts visualizations:
- Same card styling as stat cards
- Title: 16px semibold
- Chart area with subtle indigo gradient background for line charts
- Donut chart with legend beside it (16px, with 8px colored dots)

### Data Tables

Borderless design with alternating row tints:
- Header row: 16px uppercase muted, no border, bottom padding 12px
- Data rows: 16px, padding 14px vertical
- Even rows: `rgba(0,0,0,0.015)` background
- Row border-radius: 8px
- Ticker: 16px bold primary text
- Ticker subtitle: 16px muted
- Values: tabular-nums, secondary text color
- Return badges: soft colored background with semibold text

### Buttons

```
# Primary button
background: #4f46e5
color: white
padding: 8px 16px
border-radius: 10px
font-size: 16px
font-weight: 600
hover: #4338ca
disabled: opacity 0.5

# Secondary button
background: rgba(0,0,0,0.03)
color: #334155
border: 1px solid rgba(0,0,0,0.04)
padding: 8px 16px
border-radius: 10px
font-size: 16px
font-weight: 500
hover: rgba(0,0,0,0.06)

# Destructive button
background: rgba(239,68,68,0.08)
color: #dc2626
padding: 8px 16px
border-radius: 10px
font-size: 16px
font-weight: 600
hover: rgba(239,68,68,0.15)
```

### Form Inputs

```
background: rgba(255,255,255,0.7)
border: 1px solid rgba(0,0,0,0.08)
border-radius: 10px
padding: 10px 14px
font-size: 16px
color: #0f172a
placeholder-color: #94a3b8
focus: border-color #4f46e5, ring 2px rgba(79,70,229,0.15)
```

### Loading, Empty, and Error States

- Loading: 16px muted text, centered in card
- Empty: 16px muted text with subtle icon, centered in card
- Error: 16px `#dc2626` text with `rgba(239,68,68,0.08)` background, 10px border-radius, 16px padding

### Chart Colors

Palette for pie/donut/bar charts (ordered). Line charts always use `#4f46e5` (primary indigo):
```
["#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16"]
```

## Scope

### Pages to update
1. **Dashboard** — stat cards, performance chart, allocation donut, holdings summary, recommendation cards
2. **Portfolio** — asset classes table, holdings table, dividends table, composition chart
3. **Market** — search interface, price history chart
4. **Settings** — form inputs, configuration panels

### Shared components to update
1. **Navbar.tsx** → **Sidebar.tsx** — complete replacement from top nav to left sidebar
2. **App.tsx** — layout structure change (flex with sidebar + main)
3. **ChartCard.tsx** — new card styling
4. **DataTable.tsx** — borderless alternating row style
5. **HoldingsTable.tsx** — new table styling
6. **AllocationChart.tsx** — updated colors and styling
7. **PortfolioCompositionChart.tsx** — updated colors
8. **ClassSummaryTable.tsx** — new table styling
9. **RecommendationCard.tsx** — new card styling
10. **TransactionForm.tsx** — updated form input styling
11. **QuarantineBadge.tsx** — updated badge styling
12. **DividendsTable.tsx** — new table styling, updated buttons
13. **AssetClassesTable.tsx** — new table styling, updated buttons and form inputs
14. **MarketSearch.tsx** — new card styling, updated buttons and form inputs
15. **PerformanceChart.tsx** — update line stroke from `#3B82F6` to `#4f46e5`

### New dependencies
- Google Fonts: Plus Jakarta Sans (loaded via `<link>` in `index.html`)
- `lucide-react` — icon library for sidebar navigation

### Files to create
- `Sidebar.tsx` — new left sidebar navigation component

### Files to delete
- `Navbar.tsx` (replaced by `Sidebar.tsx`)

## Technical Approach

### CSS Strategy
- Continue using Tailwind CSS utility classes
- Add custom CSS variables in `index.css` via `@theme` or `:root` for design tokens
- Use Tailwind's arbitrary value syntax for glass-specific values (e.g., `bg-[rgba(255,255,255,0.7)]`)
- Add Plus Jakarta Sans to Tailwind's font family configuration

### Tailwind Configuration
Since the project uses Tailwind v4 with the Vite plugin (no config file), custom values will be added in `index.css`. All design tokens from the Design Tokens section should be translated into this `@theme` block:
```css
@import "tailwindcss";

@theme {
  --color-primary: #4f46e5;
  --color-primary-hover: #4338ca;
  --color-primary-soft: rgba(79,70,229,0.08);
  --color-positive: #10b981;
  --color-positive-soft: rgba(16,185,129,0.08);
  --color-negative: #ef4444;
  --color-negative-soft: rgba(239,68,68,0.08);
  --color-warning: #f59e0b;
  --color-text-primary: #0f172a;
  --color-text-secondary: #334155;
  --color-text-tertiary: #64748b;
  --color-text-muted: #94a3b8;
  --color-bg-page: #f8f9fb;
  --color-bg-card: rgba(255,255,255,0.7);
  --color-bg-sidebar: rgba(255,255,255,0.85);
  --color-bg-row-alt: rgba(0,0,0,0.015);
  --color-bg-hover: rgba(0,0,0,0.03);
  --color-border-card: rgba(0,0,0,0.04);
  --font-family-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
```

### Migration Path
1. Set up design tokens and font in `index.css` and `index.html`
2. Create `Sidebar.tsx`, update `App.tsx` layout
3. Update shared components (ChartCard, DataTable)
4. Update each page one at a time
5. Remove old `Navbar.tsx`

## Out of Scope

- Dark mode (light theme only for this iteration)
- `backdrop-filter: blur()` on cards — the "glass" effect is achieved purely via semi-transparent `rgba` backgrounds, not blur. This keeps performance simple.
- Accessibility audit (ARIA roles, contrast ratios) — to be addressed in a follow-up
- `prefers-reduced-motion` handling

## Reference Mockup

The approved design mockup is at:
`.superpowers/brainstorm/44702-1773508733/full-design-preview.html`
