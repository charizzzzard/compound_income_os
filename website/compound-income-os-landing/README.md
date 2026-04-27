# Compound Income OS Landing Page

This is an isolated React/Vite prototype for the Compound Income OS landing page. It presents the local-first portfolio research workflow, synthetic dashboard mockups, and review screenshot artifacts for external visual QA.

The page is a marketing prototype only. It is not investment advice, does not execute orders, and does not connect to brokerages. All dashboard values shown in the page and screenshots are synthetic demo values.

## Mockup Master Plan v4 - Wave 1

This private-preview build implements the first website mockup wave:

- M1 Home as a shorter wayfinder page.
- M2 Workflow as a dedicated monthly-cadence page.
- P2 Monthly Decision Report Render as a static product-UI mockup.
- P5 Local Dashboard Viewer as a static product-UI mockup.

The remaining planned pages are intentionally not fully implemented in this wave:

- Evidence & Data Quality
- Portfolio Model
- Local Dashboard
- Manifesto & Access

All product UI values are synthetic, sanitized, or aggregated. The build does not imply decision readiness and does not provide investment advice.

## Private Preview Readiness Payload

This landing page can include a static, sanitized readiness sample payload for private demos:

- `public/demo/readiness_payload.sample.json`

The file is derived from local processed readiness artifacts and is intended for private preview/handoff review only.

It must not contain private raw files, broker exports, private SEC identity maps, private input values, investment advice, or order/execution signals.

## Website Mockup Wave Two

Wave Two adds the `/evidence` private-preview page and the P3 Evidence Workspace mockup.

Implemented:

- M3 Evidence & Data Quality page.
- P3 Evidence Workspace static product-UI mockup.
- Coverage tier demo table with synthetic holdings.
- 7-stage SEC pipeline visual.
- 9 status labels with plain-English explanations.
- Three-layer fundamentals master visual.

Not implemented in this wave:

- M4 Portfolio page.
- M5 Dashboard page.
- M6 Manifesto page.
- Live SEC fetches.
- Real portfolio values.
- Public deployment.

## Mockup Master Plan v4 - Wave Two-B

This private-preview build adds the M5 Local Dashboard page:

- `/dashboard`
- Five KPI groups
- static Local Dashboard Viewer mockup
- readiness strip from sanitized local artifacts
- Dividend Snowball, Reinvest Comparison, Cashflow Calendar, Benchmark, and Cost/Tax sections

The page is a private preview mockup. It does not imply decision readiness and does not provide investment, tax, or legal advice.

## Mockup Master Plan v4 - Wave Three

This private-preview build adds the M4 Portfolio Model page:

- `/portfolio`
- Four portfolio sleeves
- rule-band mockups
- holdings and sleeves workspace
- concentration and cash-rule visualizations
- review-state model

The page is a private-preview mockup. It does not imply decision readiness and does not provide investment, tax, or legal advice.

## Mockup Master Plan v4 - Wave Four

This private-preview build adds the M6 Manifesto / Access page:

- `/manifesto`
- manifesto principles
- built-for / not-built-for positioning
- private-preview access cards
- public-launch blockers

The page is a private-preview mockup. It does not imply public launch readiness, decision readiness, or investment advice.

## Private Preview Route Matrix QA

The private-preview website is checked through a route and CTA matrix covering:

- Home
- Workflow
- Evidence
- Portfolio
- Dashboard
- Manifesto / About

The QA artifacts are generated under `data/processed/` and `reports/` and validate internal route coverage, pending CTA behavior, public-launch blockers, no-advice copy, and private-data guardrails.

## Static Build Package QA

The private-preview website can be built as a static package for local review.

The QA checks verify:

- `dist/` is generated successfully
- static assets are referenced safely
- private files and environment files are excluded
- public launch blockers remain documented
- no public deploy has been performed
- the build remains private-preview only

## Private Preview Copy Freeze

The private-preview website copy is checked through a final copy-freeze review covering:

- brand consistency
- route and screenshot coverage
- CTA safety
- no-advice language
- no private-data leakage
- public-launch blocker visibility
- static build QA linkage

The generated freeze artifacts live under `data/processed/` and `reports/`.

## Private Preview Release Notes

The current private-preview website handoff is indexed through generated release notes and a handoff index.

Generated artifacts:

- `data/processed/website_private_preview_handoff_index.csv`
- `data/processed/website_private_preview_release_summary.csv`
- `reports/2026-04-27/website_private_preview_release_notes.md`

These artifacts summarize the included pages, screenshots, QA evidence, static build checks, copy-freeze status, and remaining public-launch blockers.

## Commands

Install dependencies:

```bash
npm install
```

Run a local development preview:

```bash
npm run dev -- --host 127.0.0.1 --port 5173
```

Build the production bundle:

```bash
npm run build
```

Run a local production preview after building:

```bash
npm run preview -- --host 127.0.0.1 --port 4173
```

Generate deterministic review screenshots:

```bash
npm run screenshots
```

Do not open `index.html` directly via `file://`. Use the Vite dev server or a built preview so module imports, assets, and styles resolve correctly.

## Deployment

The production build writes static files to:

```text
dist/
```

Important:

- Do not commit `dist/`.
- Do not commit `node_modules/`.
- Do not open source `index.html` directly via `file://`.
- If reviewing from a Handoff ZIP, extract the ZIP first and run the npm commands from this folder.

Deployment options:

- Vercel: import `website/compound-income-os-landing` as the project folder, or configure it as the root directory.
- Netlify: use build command `npm run build` and publish directory `dist`.
- GitHub Pages: possible, but requires a repository/public workflow decision.
- Own server: upload `dist/` after `npm run build`.

## CTA Configuration

CTA URLs and shared site metadata live in:

```text
src/siteConfig.js
```

Optional deployment overrides can be provided with `VITE_*` environment variables. Copy `.env.example` to a local `.env` file if needed. The app builds without these variables and renders honest pending states instead of placeholder email addresses or fake public links.

## Public Launch Blockers

This build is a private preview. The following items must be real and verified before any public deploy:

- Imprint page (legal requirement in DE/EU); `VITE_IMPRINT_URL` must be set.
- Privacy policy page; `VITE_PRIVACY_URL` must be set.
- Real CTA targets: `VITE_SAMPLE_REPORT_URL`, `VITE_EARLY_ACCESS_URL`, `VITE_SETUP_SERVICE_URL`, `VITE_GITHUB_URL`.
- Real pricing or scope for Pro Modules and Setup Service.
- No public deploy has been performed.
- All KPI and chart values shown are synthetic demo values.
- The product is not investment, tax, or legal advice.
