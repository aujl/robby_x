# CamJam UI Styling Guide

The control console uses Tailwind CSS with a brand palette tuned for readability in both light and dark themes.

## Design Tokens
- **Brand Primary (`brand-500`)** `#289dff` – buttons, active outlines, and telemetry highlights.
- **Surface Dark** `#0f172a` – backgrounds for cards in dark theme.
- **Surface Light** `#f8fafc` – card text contrast in light theme.
- **Alert Colors**
  - Danger: `#f87171`
  - Caution: `#facc15`
  - Safe: `#34d399`

Tokens are defined in `frontend/tailwind.config.cjs` and consumed via utilities in `frontend/src/theme/tailwind.css`.

## Component Patterns
- `.card` – shared container with glassmorphism backdrop for controls and telemetry.
- `.btn` – rounded actionable controls with focus outlines and transition states.
- `grid-layout` – responsive CSS grid that adapts via `data-layout` attributes for desktop, tablet, and phone breakpoints.

## Typography & Iconography
- Font family: Inter (system fallbacks).
- Numeric data uses `font-mono` for telemetry readability.
- Icons can be supplied via SVG sprites (not bundled yet). Reserve 20px squares for placement.

## Accessibility Considerations
- Minimum contrast ratio 4.5:1 across states.
- Focus outlines use `focus-visible` utilities with brand glows.
- Touch targets enforced at 44px minimum via Tailwind padding utilities.

## Extensibility
- Add new widgets by composing `.card` containers and hooking into the ControlContext.
- Extend the palette under `theme.extend.colors` in the Tailwind config.
- Theme toggling is controlled via the `dark` class on `<html>`; additional themes can attach to the same mechanism.
