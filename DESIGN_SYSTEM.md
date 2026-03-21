# Design System Strategy: The Financial Editorial

## 1. Overview & Creative North Star
**The Creative North Star: "The Modern Archivist"**
This design system moves away from the sterile, "SaaS-blue" aesthetics of traditional fintech. Instead, it adopts the persona of a high-end financial journal. By utilizing **The Modern Archivist** approach, we prioritize expansive white space, intentional asymmetry, and a sophisticated "Decomposed Teal" palette.

The system breaks the "template" look by rejecting rigid grid lines in favor of **Tonal Layering**. We treat the screen as a series of premium paper stocks—layered, weighted, and tactile. High-contrast typography scales and overlapping containers create a signature depth that feels both authoritative and breathable.

---

## 2. Color Theory & Surface Logic
The palette transitions from a high-energy cyan to a grounded, professional `primary` (#004E59). This shift allows financial indicators (Red/Green) to sit within the layout without competing for the user's optical attention.

### The "No-Line" Rule
**Standard borders are prohibited for sectioning.** Boundaries must be defined solely through background color shifts or subtle tonal transitions.
* **Implementation:** Use `surface_container_low` (#f2f4f6) for secondary content areas sitting on a `surface` (#f7f9fb) base. The change in hex value is the "border."

### Surface Hierarchy & Nesting
Treat the UI as a physical stack.
* **Base Layer:** `surface` (#f7f9fb)
* **Mid Layer (Sections):** `surface_container_low` (#f2f4f6)
* **Top Layer (Interactive Cards):** `surface_container_lowest` (#ffffff)
* **The Depth Rule:** Never place a darker surface on top of a lighter one. Content must "rise" toward the user by getting progressively lighter/whiter.

### The Glass & Gradient Rule
To move beyond a "flat" feel, use **Glassmorphism** for floating navigation or overlay modals.
* **Value:** Use `surface_container_lowest` at 80% opacity with a `20px` backdrop-blur.
* **Signature Textures:** Apply a linear gradient from `primary` (#004e59) to `primary_container` (#006876) at a 135° angle for hero CTAs to add a "silken" finish.

---

## 3. Typography: Editorial Authority
We use **Manrope** as a variable font to bridge the gap between technical precision and human-centric design.

* **Display & Headline (The Lead):** Use `display-lg` (3.5rem) with tight tracking (-0.02em) for hero data points. This creates an "Impact Statement" aesthetic common in financial reporting.
* **Title (The Sub-Head):** `title-lg` (1.375rem) serves as the primary anchor for data widgets, providing a clear entry point.
* **Body (The Narrative):** `body-md` (0.875rem) is the workhorse. Ensure line-height is generous (1.5) to maintain the "light editorial" feel.
* **Labels (The Metadata):** `label-md` (0.75rem) should be used sparingly for secondary data labels, often paired with `on_surface_variant` (#3f484b) to reduce visual noise.

---

## 4. Elevation & Depth
In this design system, shadows are an admission of failure in tonal layering. Use them only when an element is "detached" from the page (e.g., a floating action button).

* **The Layering Principle:** Depth is achieved by stacking. A `surface_container_lowest` (#ffffff) card sitting on a `surface_container_low` (#f2f4f6) background provides a soft, natural lift.
* **Ambient Shadows:** If a floating effect is required, use a `12%` opacity shadow using the `on_surface` (#191c1e) color, with a `40px` blur and `12px` Y-offset. No harsh edges.
* **The "Ghost Border" Fallback:** If accessibility requires a container boundary, use `outline_variant` (#bec8cb) at **15% opacity**. It should be felt, not seen.

---

## 5. Component Guidelines

### Buttons (The Statement Actions)
* **Primary:** Fill with the `primary` (#004e59) to `primary_container` (#006876) gradient. Radius: `DEFAULT` (1rem).
* **Secondary:** No fill. Use a `Ghost Border` and `primary` text.
* **Padding:** Use `3` (1rem) vertical and `6` (2rem) horizontal to give the button a wide, premium footprint.

### Input Fields (The Data Entry)
* **Style:** Forgo the 4-sided box. Use a subtle `surface_container_high` (#e6e8ea) fill with a 2px bottom-stroke of `primary` only upon focus.
* **Radius:** `sm` (0.5rem) to keep them distinct from rounded cards.

### Cards & Lists (The Financial Ledger)
* **Forbid Dividers:** Do not use 1px lines between list items. Use the `Spacing Scale`: a `3` (1rem) gap between items is the preferred separator.
* **The Financial Balance:** Use `tertiary` (#1d4f40) for positive growth and `error` (#ba1a1a) for losses. Ensure these sit against `surface_container_lowest` to maximize legibility.

### Specialized Component: The Insight Ribbon
* A slim, full-width `secondary_container` (#d5e3fd) banner used for non-critical notifications. It breaks the vertical flow and acts as a visual "bookmark" in the editorial layout.

---

## 6. Do's and Don'ts

### Do
* **Do** embrace asymmetry. Align a headline to the left but place the supporting data card slightly offset to the right.
* **Do** use `16` (5.5rem) and `20` (7rem) spacing tokens for top-level section margins to let the design "breathe."
* **Do** use `primary_fixed` (#a2efff) as a very subtle background tint for highlighted data rows.

### Don't
* **Don't** use pure black (#000000) for text. Use `on_surface` (#191c1e) to maintain the soft editorial tone.
* **Don't** use the `full` (9999px) roundness for buttons; it feels too "consumer-app." Stick to `DEFAULT` (1rem) for a professional architectural feel.
* **Don't** use standard tooltips. Use "Editorial Annotations"—small, non-modal text blocks in `label-sm` that appear in the margins.
