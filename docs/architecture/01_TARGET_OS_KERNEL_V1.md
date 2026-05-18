# Target OS Kernel v1

Compound Income OS is a local-first deterministic investment-review operating
system. The OS kernel defines six domains that keep the system coherent as it
evolves.

## Kernel 1: Identity & Evidence

Purpose: every statement about an asset must trace to identifiable, reviewed and
versioned evidence.

Exists today:

- broker/document import normalization
- personal fundamentals master and coverage
- fundamentals evidence registry and proposed updates
- SEC identity, CompanyFacts and derived KPI governance
- handoff omission rules for private evidence

Not built yet:

- a complete security master
- universal evidence aging policy
- full point-in-time evidence replay

Invariant: missing data remains visible and is never silently filled.

## Kernel 2: Portfolio Accounting & State

Purpose: the portfolio state must be explainable from reviewed snapshots today
and, later, from a lightweight event ledger.

Exists today:

- positions snapshots
- configured cash contribution
- portfolio review/action tables
- partial history, performance and cost/tax artifacts

Not built yet:

- full Portfolio Event Ledger
- reconciled transaction history
- tax lot accounting
- FX attribution

V1 stance: keep this lightweight until Decision Capture has real usage. Snapshots
must not be described as a full ledger.

## Kernel 3: Research & Valuation

Purpose: assets are reviewed as investment cases, not just ranked by scores.

Exists today:

- deterministic scoring and score audit
- KPI tier guardrails
- valuation input contracts
- SEC-derived KPI evidence proposals and reviewed apply projections

Not built yet:

- minimum viable research note producer
- research case workbench
- full thesis schema

Invariant: score is diagnostic, not a decision.

## Kernel 4: Decision Packet & Journal

Purpose: every deliberate decision or deliberate no-action should be append-only,
reviewable and replayable.

Exists today:

- monthly reports and readiness/gap artifacts that can feed a decision packet
- minimal standalone `src.personal_decision_state_capture` producer for
  append-only decision/no-action capture artifacts

Not built yet:

- operationalized monthly Decision Capture workflow with real populated history
- append-only decision journal beyond the current processed/report artifact
- review-date queue

This is the first producer sequence after the architecture baseline.

## Kernel 5: Benchmark & Outcome

Purpose: decisions should later be compared against a relevant alternative.

Exists today:

- benchmark history and multi-benchmark performance modules
- portfolio history snapshots

Not built yet:

- decision-level benchmark contract
- outcome attribution
- opportunity-cost review

V1 stance: preserve benchmark references in Decision Capture, but defer return
calculation and attribution.

## Kernel 6: Policy & Feedback

Purpose: improve the OS through explicit policy changes, not blackbox optimizer
behavior.

Exists today:

- project charter
- module contracts
- post-iteration QA
- documentation drift process
- handoff contract

Not built yet:

- policy change proposal template
- strategy feedback report
- rule-change review loop based on real captured decisions

Invariant: feedback proposes changes; it does not apply them automatically.

## Cross-Cutting Invariants

- missing data remains visible
- no silent imputation
- score is diagnostic, not a decision
- no-action is a valid decision
- every decision should be replayable from run, report and manifest context
- operator time budget is a hard constraint
- LLMs and Codex assist but do not decide
- no live trading or order execution
- no simulation/backtesting before Decision Capture and accounting/replay
  foundations exist

## Operating Loop v1

```text
Evidence/Readiness
  -> Research/Attention
  -> Decision Capture
  -> Replay Context
  -> Future Outcome
  -> Future Feedback
```

The replay minimum is embedded in Decision Capture v1 through `run_id`,
`manifest_path`, `primary_report_path`, `source_snapshot_date`, `policy_ref`,
`benchmark_ref_or_label` and `accounting_basis`. It is not a separate full replay
system yet.
