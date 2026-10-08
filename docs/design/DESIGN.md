# Design System: ContractTracker

Tokens live in `docs/design/tokens.json` (v1); this guide explains them. The component contract is
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

- **Direction:** Ledger, because the owner reads dates and quotes, and ruled rows with right-aligned figures read fastest.
- **Decoration level:** minimal. No shadows on static blocks, 2px corners, hairline rules.
- **Signature:** the double rule under the masthead draws itself once (`--duration-deliberate`).
- **Weak for:** scanning many contracts at once (low density).

## Typography

- **Display:** Spectral (serif) for the brand, tab labels, row titles, figures and quotes.
- **Body and UI:** Work Sans. **Code:** system monospace (no file; still to do if a mono face is wanted).
- **Loading:** self-hosted through `@fontsource` packages, imported in `web/src/design/variants/1-ledger.css`.
- **Scale:** label 14, body 16, title 20, heading 28, display 40 (px). **Weights:** regular 400, strong 600.
- Current CSS also uses rem sizes off this scale (for example 1.0625rem for quotes); they are reported
  by `design-lint` as font-size debt and are not gated yet.

## Color

- **Approach:** restrained. One accent, ink green, used for the primary action, the current tab and focus.
- **Light:** bg `#f3f0e9`, surface `#f9f6f2`, text `#221811`, muted text `#544b41`, accent `#194e35`, field edge `#6f6151`.
- **Dark (designed, not inverted):** bg `#1e1a14`, surface `#27231e`, text `#ebe7e0`, accent `#83caa4`, field edge `#938b7f`.
- **Status:** success, warning, danger, info each have a solid text colour and a subtle fill, in both modes.
- **Contrast:** `contrast: 68 pairs checked (light 34, dark 34), 0 below minimum (must be 0), AAA body pairs: 8`.
- **Gamut:** the danger fill (light) and danger text (dark) were out of sRGB in the approved oklch values;
  their chroma was lowered (0.040 to 0.035, 0.080 to 0.060) so the hex fallback and oklch agree.

## Spacing, shape, motion

- **Space:** 4 and multiples of 8 (0, 4, 8, 16, 24, 32, 48, 64, 96). The CSS still holds rem values off
  this scale (spacing debt, not gated).
- **Radius:** control 2, container 2, overlay 4, full 9999 (the direction asks for sharp corners).
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
