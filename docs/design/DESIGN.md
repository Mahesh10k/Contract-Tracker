# Design System: ContractTracker

Tokens live in `docs/design/tokens.json` (v2); this guide explains them. The component contract is
`docs/design/components.md`, the every-state page is `docs/design/design-system.html`. `make design-lint`
keeps hardcoded colours out of `web/src`. When this guide and the tokens disagree, the tokens win.
The direction is the approved Ledger of `docs/design/variants/react-ui/README.md`; this file does not change it.

## Product Context

- **What this is:** a contract tracker that extracts five key terms from PDF contracts, computes the
  expiry and notice deadline in code, emails reminders and answers questions with cited clauses.
- **Who it's for:** a contract owner at a desk reading deadlines top to bottom, a few times a week.
- **Project type:** internal web app (React, Vite, Tailwind 4), one page with five tabs.
- **Memorable thing:** a ruled ledger: every figure sits beside the clause it came from.

## Aesthetic Direction

- **Direction:** Ledger, restyled on 2026-10-08 to the ContractTracker redesign mockup: warm paper, one ink-green accent, a section list on the left, rounded surfaces, pill badges, serif quotes in tinted blocks.
- **Decoration level:** minimal. No shadows on static blocks, hairline borders, 10/14/16 px corners.
- **Signature:** every figure sits beside the quoted clause it came from, in a tinted serif block.
- **Weak for:** scanning many contracts at once (low density).

## Typography

- **Display:** Spectral (serif) for the brand, panel titles, figures, answers and quotes.
- **Body and UI:** Work Sans. **Code:** system monospace (no file; still to do if a mono face is wanted).
- **Loading:** self-hosted through `@fontsource` packages, imported in `web/src/design/variants/1-ledger.css`.
- **Scale:** caption 13, body 15, lead 17, title 22, heading 26, display 40 (px). **Weights:** regular 400, strong 600.
- Current CSS also uses rem sizes off this scale (for example 1.0625rem for quotes); they are reported
  by `design-lint` as font-size debt and are not gated yet.

## Color

- **Approach:** restrained. One accent, ink green, used for the primary action, the current tab and focus.
- **Light:** bg `#f4f0e8`, surface `#fbf9f4`, quote block `#f1ece1`, text `#1a1714`, muted text `#5e574e`, accent `#1f4d3a`, rule `#e0d9cc`, field edge `#7f7564`.
- **Dark (designed, not inverted):** bg `#16140f`, surface `#1f1c16`, quote block `#26221b`, text `#f1ece2`, accent `#7fb89a`, rule `#353026`, field edge `#8c8272`.
- **Status:** success, warning, danger, info each have a solid text colour and a subtle fill, in both modes.
- **Contrast:** `contrast: 68 pairs checked (light 34, dark 34), 0 below minimum (must be 0), AAA body pairs: 8`.
- **Field edges:** the mockup draws inputs with its `line` colour (about 1.3:1 on the page). Fields use a darker edge (3:1) and cards and rules keep the mockup's `line`; this is a proposal for the mockup's owner.
- **Gamut (danger and info, unchanged from v1):** the danger fill (light) and danger text (dark) were out of sRGB in the approved oklch values;
  their chroma was lowered (0.040 to 0.035, 0.080 to 0.060) so the hex fallback and oklch agree.

## Spacing, shape, motion

- **Space:** 4 and multiples of 8 (0, 4, 8, 16, 24, 32, 48, 64, 96). The CSS still holds rem values off
  this scale (spacing debt, not gated).
- **Radius:** control 10, container 14, overlay 16, full 9999 (from the mockup).
- **Elevation:** 0 to 3; above 0 only for something pressable or an overlay. The Ledger uses 0 everywhere today.
- **Motion:** 80, 150, 240, 400, 700 ms; zero under reduced motion (the generated CSS and `index.css` both honour it).

## How the app uses the tokens

1. Edit `docs/design/tokens.json`, then run `make design-tokens`. It re-measures contrast, regenerates
   `web/src/styles/tokens.css` and `docs/design/tokens.css`, and rebuilds the design-system page.
2. `web/src/index.css` binds the role names the components read (`--background`, `--primary`, `--hairline`,
   `--ok-bg`) to the generated `--color-*` roles. It writes no colour.
3. The dark switch is `data-theme="dark"` on the root element. `web/index.html` sets it before the bundle
   paints (stored choice, else the system setting), and `useTheme` in `web/src/App.tsx` toggles it.

## Decisions log

- 2026-10-08: tokens derived from the approved Ledger values; v1. The dark switch moved from the `.dark`
  class to `data-theme` so the generated CSS, the page and the app share one selector.
- 2026-10-08: tokens v2 from the redesign mockup (palette, radius 10/14/16, type scale 13/15/17/22/26/40, section list layout). Logic, routes and tests unchanged.
