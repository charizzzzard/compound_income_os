# Baseline-vs-Candidate Validation

## Purpose

Baseline-vs-Candidate Validation is the governance rule for introducing new
analytical methods, robustness reports, sensitivity checks or decision-quality
producers. A candidate must improve the review process versus a defined
baseline. It must not win merely because it is more complex.

This is a review standard, not a performance-marketing standard and not a
production-release automation.

## When To Apply

Apply this governance when a patch:

- adds a new analytical output
- changes a decision-quality or robustness method
- introduces a candidate model or scoring-adjacent diagnostic
- changes assumptions used in ranking, sensitivity or scenario review
- adds a report that may influence human review priority
- claims better quality, stability, confidence or robustness

Do not use this process to bypass normal contract review, tests or human
approval.

## Champion / Challenger Logic

The baseline is the champion. It must be either:

- the current production behavior in the repo, or
- a simpler transparent rule when no production behavior exists.

The candidate is the challenger. It may be accepted only if it improves
contract integrity, data coverage, evidence quality, ranking stability,
sensitivity visibility, review precision or operator usability without creating
uncontrolled complexity.

Candidate complexity is not evidence of quality.

## Acceptance Status

Allowed validation outcomes:

- `ACCEPT`
- `REJECT`
- `ACCEPT_WITH_LIMITATIONS`
- `RESEARCH_ONLY`

`ACCEPT` means the candidate can become the new reviewed baseline through a
separate implementation patch.

`ACCEPT_WITH_LIMITATIONS` means the candidate may be used only under explicitly
documented conditions.

`RESEARCH_ONLY` means the candidate remains source material and must not affect
production outputs.

## Comparison Metrics

Use only metrics that can be computed from reviewed artifacts or manually
reviewed validation data:

- `contract_break_count`
- `data_coverage_delta`
- `evidence_quality_delta`
- `rank_stability_delta`
- `top_n_turnover`
- `sensitivity_score_delta`
- `false_precision_reduction`
- `review_flag_precision`
- `scenario_robustness_score`
- `decision_journal_completeness`

Metrics must be accompanied by input artifact paths, as-of dates and contract
versions. Metrics must not be presented as investment performance claims unless
an accepted outcome contract exists.

For Phase 1.5, `scenario_robustness_score` is a reserved later governance
field. It must be reported as `NOT_EVALUATED` until Scenario/Tail-Risk contracts
and producers exist, and it must not be used as an acceptance criterion for the
minimal Decision Quality producer.

## Bias And Failure-Mode Checks

Every candidate review must explicitly consider:

- look-ahead bias
- survivorship bias
- data snooping
- overfitting
- backtest overfitting
- hidden imputation
- unstable rankings
- missing lineage
- sample-only data treated as real data
- complexity without operator value

If a candidate uses historical data, the review must state whether the data are
point-in-time. If not, the candidate cannot support production performance or
alpha claims.

## Required Review Questions

1. What is the baseline?
2. What exactly changed in the candidate?
3. Which input artifacts and dates were used?
4. Did the candidate reduce missing data or only hide it?
5. Did the candidate improve evidence quality or only produce a cleaner report?
6. Did the candidate improve ranking stability?
7. Did the candidate increase false precision?
8. Did the candidate add maintenance burden or review fatigue?
9. Which failure modes remain?
10. What acceptance status is justified?

## Non-Scope

This governance document does not authorize:

- performance marketing
- live-trading proof
- alpha claims
- automatic production approval
- broker action
- order execution
- score-weight optimization
- portfolio-rule mutation
- hidden data enrichment
- simulation or backtesting as production evidence before accepted replay,
  outcome and accounting foundations exist

## Minimal Review Record

```text
validation_id:
validation_date:
baseline_name:
candidate_name:
source_commit_sha:
as_of_date:
input_artifacts:
contract_versions:
metrics:
failure_mode_review:
acceptance_status:
limitations:
reviewer:
```
