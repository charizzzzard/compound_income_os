# Decision Quality Layer

## Purpose

The Decision Quality & Robustness Layer turns existing processed readiness,
evidence, journal and portfolio-health artifacts into a reviewable process
quality surface. It is a governance and review layer, not a trading layer, not a
forecasting layer and not a simulation layer.

The layer answers process questions:

- Is the evidence base complete enough to support a human review?
- Are important data gaps, sample-only inputs and stale inputs visible?
- Was the human decision or no-action captured with replay references?
- Is the ranking stable enough to rely on as an attention queue?
- Which assumptions, scenarios or tail-risk lenses still need review?
- Did a candidate feature improve process quality versus the baseline?

It does not answer "what will the market do?" and it does not convert a score
or confidence level into an investment decision.

## Definition

`decision_confidence` means process confidence. It is not a probability of
investment success, expected return, alpha, outperformance or execution quality.

Process confidence may be high only when data quality, evidence coverage,
lineage, journal completeness and applicable robustness checks are sufficient
for human review. A high confidence value never authorizes broker action, order
execution, auto-trading or automatic policy change.

## Research Inputs

This design is based on the current canonical architecture and these research
inputs:

- `docs/research/SCIENTIFIC_ARCHITECTURE_REVIEW_CIOS.md`
- `docs/research/UNCERTAINTY_DECISION_FRAMEWORK_CIOS.md`

The imported research files are source material. They may contain visible
encoding artifacts from their original export. This patch does not rewrite their
content.

## Existing Inputs

The first Decision Quality layer must read existing deterministic artifacts
before adding new producers:

- `src.personal_input_closure`
- `src.personal_decision_state_capture`
- `src.personal_kpi_provenance_audit`
- `src.personal_core_kpi_closure`
- `src.cash_refill_review`
- `src.rebalance_review`
- `src.monthly_ranking_engine`
- `src.scoring_engine`
- personal run manifest, report references and used-inputs artifacts

Relevant current input artifact groups include:

- personal input closure CSV and report
- decision-state capture CSV and report
- KPI provenance audit and summary
- core KPI closure queue and summary
- cash-refill review
- rebalance review
- monthly ranking and monthly decision report
- score audit and company scores
- run manifest, artifact index and used-inputs index

## Target Outputs

The target output family is intentionally small and reviewable:

- `decision_quality_state`
- `decision_quality_report`
- `rank_robustness_report`
- `sensitivity_report`
- `journal_validation_report`
- `baseline_candidate_validation_report`

Patch 1.4 defines the architecture only. It does not implement these producers.

## Module Boundaries

### Data Quality

Data Quality reports whether required input groups are present, reviewed,
sample-only, stale, conflicting or blocked. It must preserve missing data and
must never fill missing fundamentals, valuations, dividend/FCF metrics or
private inputs.

### Evidence Coverage

Evidence Coverage reports whether decision-relevant facts have source metadata,
review status, as-of date and lineage. It must distinguish `COVERED`,
`PARTIAL`, `REVIEW` and `MISSING`.

### Decision Confidence

Decision Confidence composes process-quality signals only. It may use evidence
coverage, data quality, journal quality, lineage completeness, robustness
availability and portfolio-health review status. It must not be displayed or
stored as a success probability.

### Decision Journal Validation

Decision Journal Validation reviews append-only Decision Capture rows for
contract completeness, duplicate IDs, missing replay references, missing review
dates and hollow or incomplete manual rationale. It must not mutate the journal
or change decision status automatically.

### Ranking Robustness

Ranking Robustness checks whether attention queues are stable enough to use for
review prioritization. Early versions should use deterministic perturbation and
threshold-crossing diagnostics. They must not change score formulas, score
weights, rankings or portfolio rules.

### Sensitivity

Sensitivity exposes which assumptions, thresholds or inputs materially change
the review surface. It is an explanation layer and a review queue input, not an
optimizer.

### Scenario And Tail Risk

Scenario and Tail Risk remain design-only in this phase. Future artifacts may
describe deterministic scenario assumptions, drawdown visibility or tail-risk
eligibility. They must not become Monte Carlo, backtesting or crash-prediction
engines before the decision journal, replay, outcome and accounting foundations
are ready.

### Baseline-vs-Candidate Governance

Baseline-vs-Candidate Governance requires any new analytical module or more
complex method to be compared against the current production baseline or a
simpler rule. A candidate is acceptable only if it improves reviewability,
contract integrity, evidence quality or robustness without creating false
precision or scope drift.

## Non-Scope

This layer is not:

- a market prediction machine
- an autonomous decision engine
- a broker/order engine
- an auto-trading layer
- a source of new `proposed_action` enums
- a simulation engine
- a Monte Carlo engine
- a backtesting engine
- a runtime LLM module
- a confidence-as-success-probability system
- a score-weight or portfolio-rule optimizer

## Failure Modes

The layer exists partly to prevent these failures:

- false precision from process scores
- overfitting and data snooping
- backtest illusion
- hidden imputation
- review fatigue from too many flags
- confidence misuse as an investment probability
- scope creep toward trading, forecasting or optimization
- candidate complexity that does not improve process quality
- missing lineage hidden behind polished reports
- scenario or tail-risk language used as prediction

## Roadmap Placement

Patch 1.4 creates the design and contract basis. A later minimal producer may
materialize a `decision_quality_state` only after this design is reviewed and
accepted. Ranking Robustness, Sensitivity, Scenario, Tail Risk and Outcome
Scoreboards remain separate later steps.
