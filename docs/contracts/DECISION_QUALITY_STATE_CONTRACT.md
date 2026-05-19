# Decision Quality State Contract

contract_name: Decision Quality State Contract
contract_version: v1-design
status: design_only

## Purpose

The Decision Quality State Contract defines a future machine-readable state for
process quality, robustness and review readiness. It aggregates existing
processed artifacts. It does not create investment data, change scores, change
portfolio rules, execute orders or produce final investment decisions.

## Input Artifacts

Initial allowed input groups:

- `data/processed/personal_input_closure_report.csv`
- `data/processed/personal_decision_state_capture.csv`
- `data/processed/personal_kpi_provenance_summary.csv`
- `data/processed/personal_core_kpi_closure_summary.csv`
- `data/processed/personal_cash_refill_review.csv`
- `data/processed/personal_rebalance_review.csv`
- `data/processed/personal_monthly_buy_ranking.csv`
- `data/processed/personal_company_scores.csv`
- `data/processed/personal_score_audit.csv`
- `data/processed/personal_run_manifest.json`
- `data/processed/personal_run_used_inputs.csv`
- `reports/<YYYY-MM-DD>/personal_monthly_decision_report.md`
- `reports/<YYYY-MM-DD>/personal_decision_state_capture_report.md`

Missing optional inputs must be surfaced as `REVIEW`, `MISSING` or
`NOT_APPLICABLE`. Missing values must not be inferred.

## Output Artifacts

Future producers may write:

- `data/processed/decision_quality_state.csv`
- `data/processed/decision_quality_state.json`
- `reports/<YYYY-MM-DD>/decision_quality_report.md`

Patch 1.4 does not implement these outputs.

## Required State Fields

The future state must include at least:

- `run_id`
- `as_of_date`
- `generated_at`
- `source_commit_sha`
- `contract_version`
- `input_artifacts`
- `evidence_coverage_status`
- `evidence_coverage_pct`
- `data_quality_status`
- `missing_critical_fields`
- `stale_inputs`
- `conflicting_inputs`
- `decision_capture_status`
- `journal_quality_status`
- `portfolio_health_status`
- `cash_refill_status`
- `rebalance_status`
- `ranking_available`
- `ranking_stability_status`
- `sensitivity_status`
- `decision_confidence_level`
- `confidence_reason_codes`
- `review_required`
- `review_reason_codes`
- `non_scope_confirmations`

## Status Enums

Evidence and data coverage:

- `COVERED`
- `PARTIAL`
- `REVIEW`
- `MISSING`

Decision confidence level:

- `HIGH`
- `MEDIUM`
- `LOW`
- `REVIEW`

Ranking and sensitivity stability:

- `STABLE`
- `MODERATE`
- `UNSTABLE`
- `NOT_EVALUATED`

Validation status:

- `PASS`
- `WARN`
- `FAIL`
- `NOT_APPLICABLE`

## Reason-Code Taxonomy

Initial reason codes:

- `EVIDENCE_MISSING`
- `EVIDENCE_PARTIAL`
- `INPUT_CLOSURE_BLOCKED`
- `KPI_PROVENANCE_INCOMPLETE`
- `DECISION_JOURNAL_INCOMPLETE`
- `REVIEW_DATE_MISSING`
- `RANKING_UNSTABLE`
- `SENSITIVITY_NOT_EVALUATED`
- `SCENARIO_NOT_EVALUATED`
- `TAIL_RISK_NOT_EVALUATED`
- `BASELINE_NOT_DEFINED`
- `LINEAGE_INCOMPLETE`
- `CONTRACT_VERSION_MISMATCH`

Reason codes may be extended only by a contract update and tests.

## Lineage Fields

The state must preserve:

- source Git commit SHA
- contract version
- as-of date
- generation timestamp
- input artifact paths
- input artifact existence status
- run ID and manifest path when available
- primary report path when available
- source snapshot date when available

Absolute private local paths must not be stored. Private/raw paths must be
masked or rejected according to the relevant producer contract.

## Validation Rules

- All required fields must be present.
- Enum values must match this contract.
- `decision_confidence_level=HIGH` is invalid if critical inputs are `MISSING`
  or `INPUT_CLOSURE_BLOCKED`.
- `decision_confidence_level` must not be described as success probability.
- `evidence_coverage_pct` may be blank only when coverage is `MISSING` or
  `NOT_APPLICABLE`.
- `review_required=True` must include at least one `review_reason_codes` value.
- `source_commit_sha` must be present when Git metadata is available.
- `input_artifacts` must list full repo-relative paths.
- Scenario and Tail Risk may remain `NOT_EVALUATED` in v1.
- The state must not add broker, order, transaction, tax-lot or execution fields.

## Non-Scope

This contract does not define:

- broker writes
- order execution
- auto-trading
- new Decision Capture enums
- scoring formulas
- scoring weights
- portfolio rules
- simulation
- Monte Carlo
- backtesting
- outcome attribution
- runtime LLM dependencies

## Examples

### Blocked Personal Input State

```text
run_id=2026-05-18-monthly
as_of_date=2026-05-18
contract_version=v1-design
evidence_coverage_status=PARTIAL
data_quality_status=REVIEW
decision_capture_status=PASS
journal_quality_status=WARN
portfolio_health_status=WARN
ranking_available=True
ranking_stability_status=NOT_EVALUATED
sensitivity_status=NOT_EVALUATED
decision_confidence_level=REVIEW
confidence_reason_codes=INPUT_CLOSURE_BLOCKED;KPI_PROVENANCE_INCOMPLETE;SENSITIVITY_NOT_EVALUATED
review_required=True
review_reason_codes=INPUT_CLOSURE_BLOCKED;KPI_PROVENANCE_INCOMPLETE
```

### Ready-But-Not-Robustness-Evaluated State

```text
evidence_coverage_status=COVERED
data_quality_status=PASS
decision_capture_status=PASS
journal_quality_status=PASS
ranking_available=True
ranking_stability_status=NOT_EVALUATED
sensitivity_status=NOT_EVALUATED
decision_confidence_level=MEDIUM
confidence_reason_codes=SENSITIVITY_NOT_EVALUATED
review_required=True
review_reason_codes=SENSITIVITY_NOT_EVALUATED
```
