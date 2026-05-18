# Compound Income OS System Definition

## One-Sentence Definition

Compound Income OS is a local, deterministic investment decision-support
operating system that turns reviewed local evidence into auditable Python
artifacts and reports for a human final decision, without broker write access,
auto-trading, investment advice, runtime LLM dependency or invented data.

## What The System Is

Compound Income OS is:

- a local-first portfolio research and review system
- a deterministic Python artifact pipeline
- a decision-support OS for a long-horizon Dividend Growth, Quality Compounder
  and Value Discipline mandate
- a conservative missing-data surface that marks `REVIEW`, `MISSING_DATA`,
  `NOT_AVAILABLE` or `INSUFFICIENT_HISTORY` instead of filling gaps silently
- a set of CSV and Markdown contracts for positions, fundamentals, scores,
  watchlist, monthly ranking, readiness, dashboard, handoff and decision capture
- a governance system that separates current tracked repo reality, dirty local
  observations and roadmap intent

The current source of truth is the deterministic Python core plus its processed
artifacts, reports, tests and canonical documentation. External review bundles
are evidence packages, not a replacement for the tracked repo.

## What The System Is Not

Compound Income OS is not:

- a trading bot
- a broker/order execution system
- an autonomous portfolio manager
- an investment adviser
- a runtime financial-advice LLM agent
- a live-data or API-dependent core pipeline
- a system that imputes fundamentals, prices, cashflows, tax values or
  benchmarks
- a dashboard that creates new financial logic
- a backtesting, simulation or optimizer layer before Decision Capture and
  accounting/replay foundations exist

## Investment Philosophy

The investment philosophy is defined by three pillars:

- Dividend Growth: sustainable and growing shareholder cash returns matter.
- Quality Compounders: durable businesses, capital allocation and long holding
  periods matter.
- Value Discipline: valuation is a guardrail and timing discipline, not a claim
  of precise fair value.

Scores create diagnostic attention. They do not create final decisions.
No-action is a valid decision when evidence, valuation, portfolio fit, cash
context, opportunity cost or operator state argue against action.

## Six Kernels

### 1. Identity & Evidence

Purpose: every statement about an asset must trace to identifiable, reviewed and
versioned evidence.

Current capabilities include broker/document normalization, personal
fundamentals master and coverage, evidence registry and proposed updates,
processed SEC-derived evidence artifacts, and private-data omission rules for
handoffs.

Missing capabilities include a complete security master, universal evidence
aging and full point-in-time evidence replay.

### 2. Portfolio Accounting & State

Purpose: portfolio state must be explainable from reviewed snapshots today and
from a future event ledger later.

Current capabilities include positions snapshots, configured monthly cash
contribution, portfolio review/action tables, cash-refill review, rebalance
review, partial history, performance and cost/tax artifacts.

Missing capabilities include a full Portfolio Event Ledger, reconciled
transaction history, tax lots and FX attribution. Snapshots must not be described
as a full ledger.

### 3. Research & Valuation

Purpose: assets are reviewed as investment cases, not merely sorted by scores.

Current capabilities include deterministic scoring, score audit, KPI tier
guardrails, valuation input contract artifacts, dividend/FCF input contract
artifacts and readiness queues.

Missing capabilities include a minimum viable research note producer, a research
case workbench and a full thesis schema.

### 4. Decision Packet & Journal

Purpose: deliberate decisions and deliberate no-actions should be append-only,
reviewable and later replayable.

Current capabilities include monthly reports, readiness/gap artifacts and
`src.personal_decision_state_capture`. The producer can validate the current
decision-state CSV, append one human-operated decision/no-action row through the
contract-v2 CLI, reject duplicate decision IDs, refresh the report and keep
broker/private local paths out of stored path fields. The current tracked
processed decision-state artifact may still be header-only, so real decision
history is not guaranteed to be present.

Missing capabilities include monthly prefill from reports, routine human usage,
a review-date queue and downstream outcome links.

### 5. Benchmark & Outcome

Purpose: decisions should later be compared with a relevant alternative.

Current capabilities include benchmark history, multi-benchmark performance and
portfolio history snapshots.

Missing capabilities include decision-level benchmark contracts, outcome
attribution and opportunity-cost review. Return calculation remains deferred for
Decision Capture v1.

### 6. Policy & Feedback

Purpose: improve the OS through explicit policy changes, not black-box optimizer
behavior.

Current capabilities include the project charter, module contracts, post-
iteration QA, documentation drift process, handoff contract, architecture
backlog and LLM/Codex operating policy.

Missing capabilities include strategy feedback reports and a policy-change
proposal loop based on real captured decisions.

## Roles

### Human Operator

The human operator is the strategy owner and final decision maker. The operator
reviews evidence, resolves private inputs, approves or rejects manual data apply
paths, chooses no-action when appropriate and performs any external broker action
manually outside the system.

### Deterministic Python Core

The Python core is the source of truth for normalized inputs, processed
artifacts, reports, readiness checks and decision-capture validation. It must
remain local-first, deterministic and inspectable. It may emit review
recommendations and diagnostics, but it must not execute orders or invent data.

### Codex

Codex may inspect repo reality, implement scoped patches, update contracts and
tests, and run validation commands. Codex must keep patches minimal, preserve
unrelated dirty files, avoid private/raw/generated commits unless explicitly
scoped and must not hide product logic inside documentation or governance work.

### External LLMs

External LLMs may review architecture, red-team assumptions, summarize included
artifacts, propose questions and draft non-authoritative text. They must not
make final investment decisions, invent fundamentals, create structured
financial data without reviewed human approval, act as runtime dependencies or
override deterministic Python artifacts.

For external review packets, `external_review_packet/00_READ_ME_FIRST.md` and
`external_review_packet/HANDOFF_LATEST_CONTEXT.md` define Phase-specific
metadata precedence. ZIP-internal `HANDOFF_CONTEXT.md` is exporter context and
does not override external Phase-specific metadata.

## Monthly Operating Loop

1. Import reviewed local broker/document or CSV inputs.
2. Refresh or validate fundamentals, evidence, overlays and readiness artifacts.
3. Run deterministic scoring, coverage, watchlist, monthly ranking and portfolio
   health surfaces.
4. Build reports from processed artifacts only.
5. Review blockers, no-action candidates, cash context and opportunity cost.
6. Capture deliberate decisions or deliberate no-actions through Decision
   Capture when the capture rule applies.
7. Execute any broker action manually outside the system, if the human operator
   independently decides to do so.
8. Preserve run, report, manifest, policy and benchmark references for later
   replay and feedback.

## Current Capabilities

- read-only import and normalization of local portfolio inputs
- personal fundamentals master, coverage, evidence, overlay and reviewed apply
  projections
- deterministic scoring, score audit and KPI provenance surfaces
- watchlist, monthly ranking, savings-plan registry/routing, cash-refill review
  and rebalance review surfaces
- Markdown reports built from processed artifacts
- dashboard consolidation from processed artifacts without new financial logic
- human-operated append-only Decision Capture producer with processed/report
  outputs
- handoff ZIP exporter with private/raw omission rules and validation metadata
- documentation, architecture and LLM/Codex governance baseline

## Known Missing Capabilities

- real populated Decision Capture history
- Decision Capture prefill and review-date queue
- personal watchlist replacement for current sample/demo watchlist input
- reviewed valuation inputs for required valuation KPIs
- reviewed dividend/FCF inputs or reviewed SEC evidence apply path
- complete KPI provenance closure
- full Portfolio Event Ledger and tax-lot accounting
- decision-level benchmark and outcome attribution
- policy feedback based on captured decisions

## Explicit Deferred Work

- broker write access, order routing and auto-trading
- investment-advice automation
- runtime LLM commentary in the core pipeline
- KPI materialization without a reviewed apply path
- simulation, Monte Carlo, backtesting and optimization before Decision Capture,
  event/accounting and replay foundations exist
- tax-quantified profit-taking or loss-realization before reconciled ledger
  evidence exists
- heavy thesis/research workbench before a smaller research note proves useful
- public/SaaS productization before local OS contracts stabilize

## Non-Negotiable Invariants

- No broker writes.
- No order execution.
- No auto-trading.
- No final investment decision by Python, Codex or external LLMs.
- No invented fundamentals, prices, cashflows, tax values or benchmarks.
- No silent fallback from personal holdings to sample fundamentals.
- No KPI materialization without reviewed source evidence and an explicit apply
  path.
- Scores are clamped to `0..100` and remain diagnostic, not final decisions.
- Monthly cash contribution is read from configuration.
- Reports are built only from processed artifacts.
- Dashboard consolidates processed artifacts and does not add financial logic.
- CSV and Markdown artifacts remain deterministic.
- Private raw data and generated processed/report artifacts are not part of
  governance commits unless explicitly scoped.
- Handoff ZIPs are review evidence packages and must not include private raw
  data, credentials, caches, old ZIPs or forbidden artifacts.
