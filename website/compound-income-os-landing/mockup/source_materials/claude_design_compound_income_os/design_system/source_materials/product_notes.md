# Compound Income OS — Product Notes for Design Prototype

## Purpose

These notes describe the product, language, UI model, and safe dashboard behavior for a first high-quality design prototype of **Compound Income OS**.

The prototype should communicate a calm, rigorous, local-first portfolio research system. It should not look like a trading app, brokerage app, robo-advisor, or high-frequency signal dashboard.

## Product Positioning

**One-liner:** A local operating system for long-term investing.

**Category:** Local-first portfolio research and decision-support operating system.

**Audience:** technically sophisticated long-term investors, especially dividend-growth and quality-compounder investors, who already maintain broker exports, fundamentals files, watchlists, evidence notes, and periodic review routines.

**Core promise:** Make the monthly portfolio decision process reproducible, auditable, and visible.

**What the system does:**

- Imports local broker exports and normalizes positions.
- Reads a local fundamentals master and local evidence files.
- Produces deterministic CSV and Markdown artifacts.
- Builds portfolio snapshots, scores, rankings, dashboards, monthly decision reports, dividend analysis, evidence reports, and review backlogs.
- Makes missing data visible instead of filling it silently.
- Keeps raw, processed, and report artifacts separate.
- Runs locally and does not require broker connections.

**What the system does not do:**

- No broker execution.
- No orders.
- No investment, tax, or legal advice.
- No return promises.
- No automatic recommendation language.
- No hidden data filling.
- No opaque cloud account requirement for the core workflow.

## Brand Essence

**The discipline of compounding, made auditable.**

The product should feel like a quiet instrument for serious private investors. It is closer to an engineering dashboard, a research workbench, and a decision journal than to a consumer fintech app.

## Tone of Voice

Use short, declarative, concrete language.

Prefer:

- local
- reproducible
- deterministic
- evidence
- manifest
- coverage
- review
- missing data
- decision journal
- monthly run
- artifacts
- audit trail

Avoid:

- supercharge
- unlock
- effortless
- AI tells you what to buy
- buy signals
- alpha
- guaranteed returns
- beat the market
- wealth-building platform
- automated advisor
- real-time optimization

## Primary Narrative

1. Long-term portfolios fail by drift, not drama.
2. The user needs a monthly workflow, not another disconnected dashboard.
3. Compound Income OS turns local files into reproducible research artifacts.
4. Coverage gaps and review cases are visible by default.
5. Each monthly cycle ends in a dashboard, a decision report, and a journal entry.

## Homepage / Hero Copy

### Recommended Hero

**Headline:** A local operating system for long-term investing.

**Subheadline:** Compound Income OS turns your broker exports, fundamentals, and evidence files into reproducible rankings, dashboards, and monthly decision reports. Local-first. No broker execution. No advice.

**Primary CTA:** Join Early Access

**Secondary CTA:** Request GitHub Access

**Microcopy:** Open-source core. No cloud account required. Not investment advice.

## Product Pillars

| Pillar | UI Meaning |
|---|---|
| Local-first | Emphasize local files, no cloud account, no upload requirement. |
| Evidence-only | Show missing, partial, review, and blocked states clearly. |
| Reproducible | Show run IDs, source artifacts, manifests, and deterministic outputs. |
| Monthly discipline | Design around monthly review cycles, not daily trading. |
| Transparent scoring | Business, valuation, dividend, and buy scores should show their components. |
| No execution | Buttons should say review, document, export, inspect — not buy, sell, execute. |

## Core Workflow

Use this as the main product flow in the prototype:

1. **Broker export in**
   Local CSV or broker document is normalized into positions.

2. **Data quality check**
   Coverage is computed against the fundamentals master. Gaps become visible before scoring.

3. **Scoring and ranking**
   Holdings and watchlist candidates are scored with transparent business, valuation, dividend, and buy-score components.

4. **Dividend impact**
   The dividend snowball view calculates income impact from declared rates, current weights, candidate allocations, and rules.

5. **Monthly decision report**
   The system produces a Markdown report with candidate status, constraints, blockers, and rationale.

6. **Decision journal**
   The user records final reasoning as an artifact that can be re-read later.

## Suggested App Information Architecture

### 1. Portfolio & Structure

Purpose: Show what the user actually owns.

Core elements:

- Total assets
- Invested assets
- Cash
- Cash weight
- Number of holdings
- Sleeve allocation
- Top-10 concentration
- Asset-type split
- Non-core exposure
- Review flags

Recommended visual components:

- Large KPI cards
- Sleeve allocation bars or donut
- Concentration bar list
- Holdings table with status badges

### 2. Score & Fundamentals

Purpose: Show portfolio quality, valuation discipline, and missing inputs.

Core elements:

- Weighted business score
- Weighted valuation score
- Weighted dividend score
- Weighted buy score
- Score distribution
- Purchase readiness
- Watchlist ranking
- Data-quality flag per holding

Recommended visual components:

- Score cards with trend deltas
- Quadrant: Business Quality vs Valuation
- Candidate list with constraints
- Coverage and score audit side panel

### 3. Dividend Snowball

Purpose: Make income compounding visible without pretending to forecast returns.

Core elements:

- Current annual dividend income
- Current monthly dividend income
- Forward portfolio yield
- Dividend growth assumptions
- Monthly contribution assumption
- Reinvestment assumption
- Income by holding / sleeve
- 5-year illustrative income path
- Candidate income impact

Recommended visual components:

- Annual income line chart
- Monthly dividend calendar
- Income-by-sleeve bars
- Candidate impact cards

Important wording: call this an **illustrative calculation**, not a forecast.

### 4. Monthly Decision

Purpose: Turn analysis into a documented review queue.

Core elements:

- Monthly new cash
- Eligible candidates
- Deferred candidates
- Blocked cases
- Constraint checks
- Candidate rationale
- Journal entry status

Recommended visual components:

- Ranked decision queue
- Rule/checklist badges
- Candidate detail drawer
- Markdown report preview

Safe button language:

- Review Candidate
- Open Evidence
- Export Report
- Add Journal Note
- Mark Reviewed

Avoid button language:

- Buy Now
- Sell Now
- Execute
- Auto-Rebalance

### 5. Evidence & Data Quality

Purpose: Make trust visible.

Core elements:

- Coverage status
- Missing required KPIs
- Optional missing KPIs
- Evidence hits
- Proposed updates
- Research backlog
- SEC identity status
- Manual overlay required

Recommended visual components:

- Coverage status tiles
- Blocker count bars
- Research-priority table
- Evidence pipeline stepper
- Artifact lineage panel

Status vocabulary:

- OK
- COVERED
- PARTIAL
- REVIEW
- MISSING_DATA
- NO_MATCH
- INSUFFICIENT_INPUTS
- INSUFFICIENT_HISTORY
- BLOCKED
- NOT_AVAILABLE

### 6. Benchmark & Performance

Purpose: Compare configured portfolio history against configured benchmarks where enough history exists.

Core elements:

- Portfolio NAV
- Benchmark reference
- Active return
- Volatility
- Drawdown
- History sufficiency status

Important behavior:

- If history is insufficient, the UI must show `INSUFFICIENT_HISTORY`, not fake a chart.
- Never imply future performance.

### 7. Costs & Taxes

Purpose: Surface costs, taxes, and ledger quality where user-provided data exists.

Core elements:

- Total fees
- Total taxes
- Withholding tax
- Ledger coverage
- Verification status
- Cost/tax events

Important wording:

- Say "cost and tax artifacts".
- Do not say "tax optimization".
- Do not imply tax advice.

### 8. Methodology & Run Manifest

Purpose: Make the pipeline auditable.

Core elements:

- Run ID
- Snapshot date
- Source artifact paths
- Generated artifacts
- Stage statuses
- Input freshness
- Data-quality flags

Recommended visual components:

- Run manifest summary
- Source-to-output lineage graph
- Artifact table
- Validation checklist

## Dashboard Visual Direction

Design target: Apple-like clarity, but with financial research credibility.

### Layout

- Use generous whitespace.
- Use a dark, high-contrast app surface for the dashboard preview.
- Use neutral cards, subtle borders, and soft shadows.
- Keep charts calm and readable.
- Use monospace numerics for values, percentages, run IDs, and artifact paths.
- Prefer visible status badges over decorative icons.

### Color Semantics

Use restrained semantic colors only:

- OK / covered: calm green
- Review / partial: amber
- Missing / blocked: red or muted rose
- Not available / insufficient: neutral gray
- Primary accent: deep blue or graphite-blue

### Typography

- Wordmark: `Compound Income OS`
- Primary UI font: modern sans-serif
- Numeric / artifact font: monospace
- Avoid crypto/neon aesthetics.

## Data Contract for `dummy_dashboard_data.json`

The dummy JSON is intentionally structured for frontend use and includes both high-level sections and repo-aligned table shapes.

Top-level keys:

- `metadata`
- `app_copy`
- `run_context`
- `portfolio_summary`
- `kpi_cards`
- `sections`
- `charts`
- `tables`
- `methodology`
- `disclaimer`

Important: The data is dummy and sanitized. It should be used for layout, charts, and component behavior only.

## Must-Show UI States

The prototype should visibly include:

- At least one `OK` state.
- At least one `PARTIAL` state.
- At least one `REVIEW` state.
- At least one `MISSING_DATA` state.
- At least one `INSUFFICIENT_HISTORY` or `NOT_AVAILABLE` state.
- A run manifest / source artifact reference.
- A "Not investment advice" disclaimer.

## Suggested Dashboard CTA / Action Labels

Use:

- Run Monthly Review
- Inspect Coverage
- Open Decision Report
- Export Artifacts
- Review Evidence
- Add Journal Entry
- Request GitHub Access
- Join Early Access

Avoid:

- Trade
- Execute
- Auto-Buy
- Sell Signal
- Alpha Engine
- Guaranteed Income
- Optimized for Returns

## Safe Footer Disclaimer

Compound Income OS is a research and decision-support tool. It does not provide investment, tax, or legal advice, does not guarantee any return, and does not execute orders or connect to brokerages. All decisions, risks, and outcomes remain solely with the user. Past data does not predict future results.

## Notes for Claude Design

Build a product-first prototype, not a marketing-only landing page.

The ideal first screen should show:

1. Wordmark and concise hero.
2. A polished dashboard mockup with real-looking dummy KPIs.
3. Clear evidence/data-quality states.
4. Dividend snowball section.
5. Monthly decision workflow.
6. Compliance-safe disclaimer.

Use `dummy_dashboard_data.json` as the single dummy data source. Do not invent additional holdings unless needed for layout testing. If additional examples are needed, keep them clearly dummy and do not use identifiable real portfolio data.
