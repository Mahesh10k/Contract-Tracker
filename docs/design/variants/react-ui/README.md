# Design directions: React UI (round 1)

Screens rendered: the five tabs (Upload, Contracts, Deadlines, Ask, Needs review) with the
real golden-contract wording. Screenshots: not taken (the browser launch was declined, so
nothing here describes how a direction looks on screen).

## How to view each one

```bash
cd web && npm install && npm run dev
```

Then open (the mock flag uses sample data, no server needed):

- http://localhost:5173/?variant=1-ledger&mock=1
- http://localhost:5173/?variant=2-panel&mock=1
- http://localhost:5173/?variant=3-grid&mock=1
- http://localhost:5173/?mock=1 is the neutral baseline.

The theme button in the header switches light and dark. The switch exists only in
development builds; production ships the one direction you choose.

## The three directions

| | 1-ledger | 2-panel | 3-grid |
| --- | --- | --- | --- |
| Serves first | owner at a desk reading deadlines top to bottom | owner triaging many contracts on a monitor | owner checking what is due a few times a week on a laptop |
| Display / body | Spectral (serif) / Work Sans | IBM Plex Sans Condensed / IBM Plex Sans | Schibsted Grotesk, one family |
| Temperature | warm grey-bone paper, ink-green accent | cool graphite, teal accent | neutral white, cobalt accent |
| Layout rhythm | one wide left-aligned column, ruled rows, right-aligned figures | left status rail, dense rows | 12-column grid, headings in the margin, hairlines |
| Motion moment | the double rule under the masthead draws itself | table rows settle in one by one | the index rules draw in from the left |
| Weak for | scanning many contracts (low density) | reading long quotes | very narrow screens |

## Checks

- Contrast: 120 pairs checked across both themes (text, secondary text, labels, status badges,
  field edges 3:1, focus ring 3:1), 0 below the ratio. Reproduce: `python3 .scratch/contrast.py`.
- Distinctness: 3 of 3 pairs judged distinct on display family, temperature and layout rhythm.
  This is a judgement, not a measurement.
- Hard rules: no purple or indigo gradients, no emoji, no Inter or Space Grotesk, radius and
  shadow follow a hierarchy, focus ring on every control, reduced-motion guard on every
  animation, body text 16px.
- Not checked: how any direction looks on screen, touch targets on a phone (buttons are 44px
  tall by their CSS), and the 375px layouts.

## Recommended

1-ledger. The product's job is to show a deadline next to the sentence that sets it, and the
Ledger rows with italic quotes and right-aligned figures do that most plainly. Pick another
if triage speed matters more to you than reading.

Chosen: 1-ledger (by the developer, 2026-10-06). It is now the default look; the other two stay as dev-only alternatives (?variant=2-panel, ?variant=3-grid).
