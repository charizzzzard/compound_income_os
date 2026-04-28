# App UI kit — Compound Income OS

The local OS surface. Open `index.html`. The sidebar is wired — clicking switches views.

## Views shipped

- **Dashboard** — KPI grid, holdings table (with a click-through Holding Inspector drawer), dividend-snowball sparkline, data-quality coverage bar, latest journal entry.
- **Monthly Run** — review banner, segmented filter, decision queue (ELIGIBLE / DEFERRED / BLOCKED), run manifest, rule trace.
- **Decision Journal** — cycle history, latest entry rendered as Markdown.
- **SEC Evidence** — proposed/applied/skipped tabs, proposal table with **Review update / Skip** actions and an **Apply to evidence-applied master** step.
- **Dividend Snowball Analysis** — illustrative income path (reinvest vs manual scenarios), assumptions, rule-based concentration caps, candidate contribution table, data-quality status, provenance strip, explicit *Illustrative calculation. Not a forecast.* framing.

Other sidebar entries (Watchlist, Ranking, Snowball, Data Quality, Fundamentals, Reports, Settings) render a placeholder card per the brief — the four hi-fi views above carry the visual + interaction surface.

## Components

- `AppShell.jsx` — `Sidebar` (nav + groups + "Local data" footer), `Topbar` (crumbs, status chip, run id), `AppShell` wrapper. Inline glyph set (`Glyph.*`) follows the ICONOGRAPHY rule: 16×16, 1.4 stroke, currentColor.
- `DashboardView.jsx` — `DashboardView`, `HoldingDrawer`.
- `Views.jsx` — `MonthlyRunView`, `JournalView`, `EvidenceView`, `PlaceholderView`.

## Conventions

- KPI numbers always JetBrains Mono with tabular numerals.
- Status pills use the semantic palette only: COVERED · PARTIAL · REVIEW · NO_MATCH · MISSING_DATA · INSUFFICIENT_INPUTS · INSUFFICIENT_HISTORY. Trading red/green is not used.
- Every panel cites the artifact that produced it (`positions_snapshot.csv`, `company_scores.csv`, …) — provenance is a first-class affordance, not metadata.
- Drawer instead of modal for the Holding Inspector — keeps the dashboard context visible.
