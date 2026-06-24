# UI Direction — v0.1 web app

Status: **chosen direction, locked** (resolves UI-DESIGN issue #61).
Audience: the implementer of #28 (analysis dashboard, report view, trace inspection).

This document is the visual contract for #28. It records the chosen direction, the
Nomic-derived tokens behind it, what the theme foundation already ships, and an
explicit list of what to build and what to avoid.

---

## 1. Decision summary

The v0.1 workbench adopts a **Nomic-Portal-matched** look:

> **Dark indigo-navy sidebar + light data canvas, with a scientific data palette
> (categorical for discrete conditions, viridis sequential for continuous scales).**

This was chosen by Mike after reviewing five rendered concepts (restrained-indigo,
data-palette, a blend, and dark variants). The winning concept ("Concept B,
Portal-matched") was validated against Nomic's **actual product UI**, not just the
marketing site — see §2.

The mockups that produced this decision live in `docs/assets/ui-concepts/`
(`concept-b-portal.html` is the locked one — open it in a browser to view); they are
reference artifacts, not shipping code. The raw extracted Nomic tokens are in
`docs/assets/nomic-extract/`.

---

## 2. Evidence base (how we grounded it)

Design tokens were extracted from Nomic's real surfaces with the `designlang` CLI
(`npx designlang https://www.nomic.bio/portal`). Key findings:

- **Brand primary:** indigo `#4a4ad8` (consistent across nomic.bio and the Portal).
- **Brand secondary:** mint-green `#4ad889`.
- **Extended accents in their system:** lavender `#7e66ed` / `#ece4ff`, deep navy
  `#15295a`, coral `#f96b6b` (errors), amber `#ffb700`.
- **Type:** Outfit (geometric variable sans), light display weights.
- **Material:** flat, soft shadows, occasional colored glows.

Critically, an embedded **product screenshot** on the `/portal` page shows the real
logged-in app: a **dark indigo-navy sidebar** (active item highlighted in brighter
indigo) beside a **light/white plotting canvas**. Its nav literally lists
`Scatterplot · Plate Heatmap · UMAP · Clustergram · Volcano · Response Curve ·
Heatmap Builder`, and its plots use **categorical** palettes for discrete conditions
plus a **viridis** colorbar for continuous expression. Our direction mirrors this.

> Note: the fully-dark marketing skin (`#090426` backgrounds) is Nomic's *marketing*
> surface, **not** the product. The product is light-canvas + dark-sidebar. We follow
> the product.

---

## 3. Tokens (locked)

Implemented in `apps/web/app/globals.css` as space-separated RGB CSS variables and
exposed through `apps/web/tailwind.config.ts`. Hex shown here for reference.

### Color

| Role | Token | Hex |
|---|---|---|
| Primary accent (indigo) | `accent` | `#4a4ad8` |
| Accent strong | `accent-strong` | `#3a3ab0` |
| Accent wash (selected rows / active bg) | `accent-wash` | `#ece4ff` |
| Secondary / positive (mint) | `secondary` | `#4ad889` |
| Secondary strong | `secondary-strong` | `#2fae6a` |
| Lavender | `lavender` | `#7e66ed` |
| Amber | `amber` | `#ffb700` |
| Coral / error / down-regulation | `coral` | `#f96b6b` |
| Status dot | `signal` | `#4ad889` |
| Ink (text) | `ink` | `#0e1116` |
| Muted text | `muted` | `#5b6772` |
| Faint text / axis labels | `faint` | `#8a95a0` |
| Surface (panels) | `surface` | `#ffffff` |
| Wash (page bg) | `wash` | `#f6f7f9` |
| Border | `border` | `#e4e5ee` |
| Border strong | `border-strong` | `#d3d6e2` |
| **Sidebar bg** | `nav` | `#0e0930` |
| Sidebar raised panel | `nav-2` | `#161046` |
| Sidebar border | `nav-border` | `#241d52` |
| Sidebar text | `nav-ink` | `#eef0ff` |
| Sidebar muted text | `nav-muted` | `#a7a4d8` |

### Data-viz palette (for #28 to apply in plots)

- **Categorical (conditions):** indigo `#4a4ad8` · mint `#4ad889` · amber `#ffb700`
  · lavender `#7e66ed` (extend with deep navy `#15295a` / coral `#f96b6b` if >4).
- **Sequential (continuous: expression, donor consistency, significance strength):**
  **viridis** ramp — `#440154 → #414487 → #2a788e → #22a884 → #7ad151 → #fde725`.
- **Non-significant / muted points:** `#c7ccd6`.

### Typography

- Family: **Outfit** (wired via `next/font/google` in `app/layout.tsx`, exposed as
  `--font-sans` / Tailwind `font-sans`). System-ui fallback.
- Numeric/tabular data uses `font-variant-numeric: tabular-nums` (set globally on
  `body`). Use a monospace face for dense value columns (log₂FC, q-value) if desired.
- Display weights stay light-to-semibold; avoid heavy/black weights.

### Shape, spacing, material

- **Radius:** small for controls/panels (≈6px panels, ≈10px cards). Avoid the large
  marketing radii (>20px) from the extraction — they suit a landing page, not a
  workbench.
- **Material:** flat. Hairline borders over heavy shadows. No glows in data areas.
- **Spacing:** dense but breathable; the extracted marketing spacing scale is too
  generous for tables — use tighter padding (≈8–12px cell padding).

---

## 4. Layout

- **Desktop:** fixed dark-navy left sidebar (~256px) + light content area. Sticky
  light top bar with breadcrumb, run/status pills, and primary actions.
- **First screen is the working surface** (project/analysis state) — no landing hero.
- **Active nav** item: indigo-tinted background + brighter text (matches Portal).
- The theme foundation (sidebar chrome, tokens, font) already ships — see §6.

### Screens for #28 to build

Project/workspace dashboard · analysis results dashboard (ranked proteins + plot) ·
evidence-backed report view · trace inspection · dataset/fixture selection &
validation state · eval display (if relevant). Web chat/tool handoff surface comes
from #27 and should adopt these same tokens.

### Representative composition (from the locked mockup)

Analysis-results screen: page header → 4 stat tiles → two-column (ranked-protein
**table** left, **volcano/plot** right) → provenance/trace strip. Conditions render as
colored chips; q-values as significance badges; the plot colors points by condition
(categorical) and can encode a continuous scale via viridis.

---

## 5. Responsive notes (observed in mockup review)

- Sidebar collapses below `lg`; provide the existing wrapped **mobile top-nav**.
- **Dense tables overflow on narrow screens** — make them horizontally scrollable
  (overflow container) or switch to a stacked/card layout under ~640px. Do not let
  columns clip silently.
- Stat tiles: 4-up desktop → 2-up mobile.
- Required before #28 merge: desktop **and** mobile screenshots, checked for text
  overlap and realistic artifact rendering (per #28 acceptance criteria).

---

## 6. What the theme foundation already ships (this issue)

Changed in `apps/web` so #28 starts from the right base, **not** a redesign:

- `app/globals.css` — full Nomic token set (replaces the old invented teal `#185c70`).
- `tailwind.config.ts` — all tokens exposed + `font-sans` mapped to Outfit.
- `app/layout.tsx` — Outfit font wired via `next/font/google`.
- `src/components/workspace-shell.tsx` — sidebar restyled to dark indigo-navy
  (indigo glyph, navy panels, muted-lavender nav text).

Not done here (belongs to #28): the dashboard/report/trace screens themselves, chart
components, active-route highlighting, and the responsive table treatment.

---

## 7. Do / Avoid

**Do**
- Keep the dark-navy sidebar + light data canvas.
- Use indigo as a flat, solid accent; mint for positive/success; coral for errors.
- Color plots with the categorical + viridis palettes above.
- Favor tables, plots, and dense project state; keep chrome quiet so data leads.
- Keep it flat with hairline borders.

**Avoid**
- ❌ A marketing landing-page hero or any "Start now" splash.
- ❌ Generic purple/blue **gradient** SaaS backgrounds (flat indigo is fine; gradients are not).
- ❌ Card-heavy dashboards where a table/plot is clearer.
- ❌ Large marketing radii, heavy shadows, or decorative glows in data areas.
- ❌ Inventing a new accent (e.g. the old teal) — stay on the Nomic palette.
- ❌ Auto-restyling away from this direction without review.
