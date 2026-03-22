# Apple Dark Redesign — Design Spec

**Date:** 2026-03-22
**Status:** Draft
**Mockups:** `.superpowers/brainstorm/41781-1774175502/` (dashboard-mockup.html, detail-and-fundamentals.html)

---

## Overview

Redesign Project Fin's UI to adopt an Apple Stocks-inspired dark aesthetic with cinematic ambient glows, dramatic typography hierarchy, and a top tab navigation replacing the current sidebar. The goal is a premium, data-dense financial app that feels like Apple TV+ meets Apple Stocks — adapted for web.

## Design Decisions (User-Validated)

- **Dark Gradient Depth** approach — near-black base with subtle ambient glow orbs
- **Top tab bar** navigation (segmented pill control) — sidebar removed entirely
- **No gradients** on any UI elements (text, buttons, cards, backgrounds) — only ambient glow orbs use color
- **No cyan/teal colors** — replaced with blue-500 (`#3b82f6`)
- **No realistic icons** — text/letter-based asset icons, simple line icons (Lucide React)
- **Pie chart colors kept** — blue (`#0a84ff`), blue-500 (`#3b82f6`), purple (`#bf5af2`), orange (`#ff9f0a`)
- **Secondary (ghost) button** for "View Analysis" in recommendation card
- **Card title labels** always use tertiary gray, never colored
- **Settings icon** minimum 44x44px touch target

---

## 1. Color Tokens

### Base Palette

| Token | Value | Usage |
|-------|-------|-------|
| `--black` | `#0a0a0a` | Page background |
| `--surface` | `#1c1c1e` | Card/container backgrounds |
| `--surface-hover` | `#2c2c2e` | Hovered cards/rows |
| `--border` | `rgba(255,255,255,0.08)` | Card borders, dividers |
| `--border-hover` | `rgba(255,255,255,0.14)` | Hovered borders |
| `--text-primary` | `#f5f5f7` | Headings, values, primary text |
| `--text-secondary` | `rgba(255,255,255,0.55)` | Body text, descriptions |
| `--text-tertiary` | `rgba(255,255,255,0.35)` | Labels, captions, timestamps |

### Semantic Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--green` | `#34c759` | Positive values, gains |
| `--red` | `#ff3b30` | Negative values, losses |
| `--blue` | `#0a84ff` | Primary actions, links, active states |
| `--orange` | `#ff9f0a` | Warnings, "Hold" badges |
| `--purple` | `#bf5af2` | Crypto asset class |

### Chart/Asset Class Colors

| Class | Color |
|-------|-------|
| US Stocks | `#0a84ff` (blue) |
| BR Stocks | `#3b82f6` (blue-500) |
| Crypto | `#bf5af2` (purple) |
| Fixed Income | `#ff9f0a` (orange) |

### Removed

- No `--teal` / `#64d2ff` / cyan anywhere
- No gradient values on any token
- No glass-morphism tokens (`--glass-*`)

---

## 2. Typography Scale

Font: Inter (already loaded). No additional fonts.

| Level | Size | Weight | Tracking | Usage |
|-------|------|--------|----------|-------|
| Hero value | 56px | 700 | -0.03em | Portfolio total value |
| Page title | 40px | 700 | -0.03em | Asset class value headers |
| Section title | 32px | 700 | -0.02em | Page headings (Fundamentals) |
| Card stat | 24-28px | 700 | -0.02em | KPI values, dividend totals |
| Score large | 36px | 700 | -0.02em | Fundamentals score number |
| Body large | 18px | 700 | -0.01em | Stat cell values |
| Asset symbol | 15-16px | 600 | -0.01em | Ticker symbols, row primary text |
| Body | 14px | 400-600 | normal | General text, table cells |
| Body small | 13px | 500 | normal | Descriptions, news headlines |
| Caption | 12px | 500 | normal | Secondary data, price changes |
| Label | 11px | 600 | 0.06-0.08em | Uppercase card titles, section labels |

All numeric values use `font-variant-numeric: tabular-nums` for alignment.

---

## 3. Navigation

### Top Tab Bar (replaces Sidebar + TopAppBar)

- **Position:** sticky top, 52px height
- **Background:** `rgba(10,10,10,0.85)` with `backdrop-filter: blur(20px)`
- **Border:** 1px bottom `var(--border)`
- **Layout:** Logo | Segmented Tabs | Right Icons

### Segmented Tabs

- Container: `rgba(255,255,255,0.06)` background, pill-shaped (`border-radius: 100px`), 3px padding
- Tab: 13px font, 500 weight, `6px 18px` padding, pill-shaped
- Active tab: `rgba(255,255,255,0.12)` background, `--text-primary` color
- Inactive: `--text-secondary` color, transparent background

### Tabs (mapped to existing routes)

- Portfolio → `/` (Dashboard, default/home)
- Fundamentals → `/fundamentals` (new index route, see Section 7)
- Market → `/market` (new page — shows news feed and market overview, out of scope for this spec — tab renders but links to placeholder)
- Invest → `/invest` (existing Invest page)

### Right Section

- Settings icon: 44x44px circle, `rgba(255,255,255,0.06)` background, simple line icon
- Notifications icon: same size, simple line icon (Lucide `Bell`)
- Avatar: 28px circle, solid `--blue` background, initials text

---

## 4. Layout

### Removed

- `Sidebar` component — deleted entirely
- `TopAppBar` component — replaced by new top nav

### Page Container

- Max width: 1400px, centered
- Padding: 32px
- Content is full-width below the top nav (no `ml-64` offset)

### Grid System

- 2-column: `grid-template-columns: 1fr 1fr; gap: 16px`
- 3-column: `grid-template-columns: 1fr 1fr 1fr; gap: 16px`
- Cards stack vertically within columns with 16px gap

---

## 5. Components

### Cards

- Background: `var(--surface)` (`#1c1c1e`)
- Border: 1px `var(--border)`
- Border-radius: 12px
- Padding: 20px
- Hover: border shifts to `var(--border-hover)`
- Title: 11px, 600 weight, uppercase, `0.08em` tracking, `--text-tertiary` color — always gray, never colored

### Buttons

**Primary (`.btn-primary`):**
- Background: `var(--blue)` (`#0a84ff`)
- Color: white
- Border-radius: 100px (pill)
- Padding: 10px 24px
- Font: 14px, 600 weight
- Hover: slightly darker blue, subtle scale(1.02)

**Ghost/Secondary (`.btn-ghost`):**
- Background: `rgba(255,255,255,0.06)`
- Color: `--text-secondary`
- Border-radius: 100px (pill)
- Padding: 8px 18px
- Font: 13px, 500 weight
- Hover: `rgba(255,255,255,0.1)`, color shifts to `--text-primary`

**Icon Button (`.btn-icon`):**
- 36px circle (44px for nav icons)
- Background: `rgba(255,255,255,0.06)`
- Color: `--text-secondary`
- Hover: same as ghost

### Period Selector

- Pills: 12px font, 500 weight, `5px 14px` padding, pill-shaped
- Active: `rgba(255,255,255,0.1)` background, `--text-primary` color
- Used for chart time periods (1D, 1W, 1M, 3M, 1Y, ALL)

### Badges

| Variant | Background | Text Color |
|---------|-----------|------------|
| Green (Strong Buy, Buy, Dividend) | `rgba(52,199,89,0.15)` | `--green` |
| Red (Sell) | `rgba(255,59,48,0.15)` | `--red` |
| Orange (Hold) | `rgba(255,159,10,0.15)` | `--orange` |
| Blue (JCP, info) | `rgba(10,132,255,0.15)` | `--blue` |

Pill-shaped, 11px font, 600 weight, `3px 10px` padding.

### Asset Row (Holdings List)

- Flex layout: Icon | Info | Sparkline | Price
- Icon: 36px square, 8px radius, colored background at 15% opacity, letter-based text
- Sparkline: 64x28px inline SVG polyline
- Price change: green/red based on positive/negative
- Row divider: 1px `var(--border)` bottom border
- Hover: subtle `rgba(255,255,255,0.02)` background with row padding expansion

### Tables

- Header: 11px uppercase, `0.06em` tracking, `--text-tertiary`, bottom border
- Rows: 14px, 14px vertical padding, bottom border, hover background
- Grid columns defined per table context
- All numbers: `font-variant-numeric: tabular-nums`

### Score Bars (Fundamentals)

- Track: 6px height, `rgba(255,255,255,0.06)` background, 3px radius
- Fill: colored by threshold — green (>7), orange (5-7), red (<5)
- Label alongside: 13px, 600 weight

### Charts

- Line stroke: `var(--green)` for positive performance, `var(--red)` for negative
- Area fill: solid color at 10% opacity (no gradient)
- Glow effect: duplicate path with 4px stroke, `blur(8px)`, 40% opacity
- Sparklines: 1.5px stroke polyline, colored by gain/loss

---

## 6. Ambient Glow System

Three fixed-position blurred orbs that create subtle cinematic depth:

| Glow | Position | Color | Size | Blur | Opacity |
|------|----------|-------|------|------|---------|
| 1 | top: -100px, right: -100px | `--blue` | 600px | 120px | 0.07 |
| 2 | bottom: -200px, left: -100px | `--green` | 600px | 120px | 0.07 |
| 3 | top: 40%, left: 50% | `--purple` | 600px | 120px | 0.04 |

- `position: fixed`, `pointer-events: none`, `z-index: 0`
- Content sits at `z-index: 1` above the glows
- Glows are global — rendered once in the app shell, not per-page

---

## 7. Page-Specific Layouts

### Dashboard

1. Hero section: label (11px) + value (56px) + change (17px green/red) + subtitle (13px) + period selector
2. Chart area: 180px height, glow line effect
3. Stats row: 3-column grid of stat cards (label + large value)
4. Main content: 2-column grid — Holdings list (left) | Allocation donut + Buy recommendation + News (right, stacked)

### Asset Class Holdings

1. Breadcrumb: Portfolio > Class Name
2. Class hero: label + 40px value + change + action buttons (Export ghost, Add Asset primary)
3. Allocation bar: horizontal progress bar with target vs actual
4. Holdings table: 6-column grid (Asset, Price, Shares, Value, Return, Weight)
5. Bottom 2-column: Recent dividends list | Dividend summary (YTD total, yield, next ex-date)

### Fundamentals

The current route is `/fundamentals/:symbol` (per-asset detail). This redesign adds a new **Fundamentals index page** at `/fundamentals` that lists all scored assets. The existing per-symbol detail page remains but is restyled. The tab links to the new index.

1. Page header: label + 32px title + segmented filter tabs (All/US/BR)
2. Score cards: 3-column grid, each with ticker, badge, large score, 4 score bars
3. Rankings table: 5-column grid (#/Asset, Score, Rating, Profitability, Growth)
4. Clicking a score card or ranking row navigates to `/fundamentals/:symbol` (existing detail page, restyled)

### Login

- Dark background (`--black`), centered card with logo, email/password fields, primary button
- Follows same card + input + button styles — no special layout needed
- Auth context unchanged

### Settings

- Follows same card pattern
- **Theme toggle removed** — app is dark-only, `ThemeContext` and toggle control deleted
- Quarantine configuration remains with same card + input patterns

### Invest

- Calculator layout using same card + stat patterns
- No structural changes, only restyled with new tokens

### Responsive / Mobile

- Out of scope for this phase. Current responsive breakpoints preserved as-is.

---

## 8. Removed Patterns

- **Sidebar component** — deleted, replaced by top tab nav
- **TopAppBar component** — merged into new top nav
- **Glass-morphism** — all `backdrop-filter: blur()`, transparency effects removed from cards and content. **Exception:** the TopNav uses `backdrop-filter: blur(20px)` as an intentional frosted-bar effect (Apple-standard for sticky navigation)
- **Gradients** — no `linear-gradient` or `radial-gradient` on any UI element
- **Cyan/teal** — `#64d2ff` and all cyan variants eliminated from palette
- **Manrope font** — already removed in previous refactor
- **BackgroundGradients component** — already removed in previous refactor
- **Light theme** — this redesign is dark-only (single theme)

---

## 9. Migration Summary

### Files to Modify

| File | Change |
|------|--------|
| `styles/theme.css` | Complete rewrite — new dark-only token set |
| `styles/components.css` | Rewrite — new card, button, badge, table classes |
| `index.css` | Update Tailwind @theme tokens for dark palette |
| `App.tsx` | Remove Sidebar/TopAppBar, add new TopNav, restructure layout |
| `components/Sidebar.tsx` | Delete |
| `components/TopAppBar.tsx` | Delete |
| `contexts/ThemeContext.tsx` | Delete — dark-only, no toggle needed |
| `pages/Settings.tsx` | Remove theme toggle control |
| `pages/Login.tsx` | Restyle with dark tokens |
| All page components | Remove `ml-64`/`pt-24` layout offsets, update to full-width |
| All chart components | Update colors to new palette, remove gradient fills |
| All table/card components | Update to new token names |

### New Components

| Component | Purpose |
|-----------|---------|
| `TopNav.tsx` | Sticky top bar with logo, segmented tabs, icons, avatar |
| `AmbientGlows.tsx` | Three fixed blurred orbs for cinematic depth |
| `FundamentalsIndex.tsx` | New index page at `/fundamentals` listing all scored assets |

### Dependencies

- No new dependencies needed
- Lucide React already installed for icons
- Inter font already loaded

---

## 10. Icons Strategy

- **Navigation icons:** Lucide React — `Settings`, `Bell` (simple line style)
- **Asset icons:** Letter-based text in colored square (e.g., "AAPL" in blue-tinted 36px square)
- **No realistic/emoji icons** anywhere in the UI
- **Action icons:** Lucide React line icons where needed (+, chevrons, arrows)
