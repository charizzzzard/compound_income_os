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
- `scenario_status`
- `tail_risk_status`
- `scenario_robustness_score`
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

Producer artifact and review status fields may additionally use:

- `REVIEW`
- `MISSING`
- `NOT_EVALUATED`

These values must not be treated as successful readiness. They exist to keep
missing, blocked or intentionally deferred producer areas visible.

## Reason-Code Taxonomy

Initial reason codes:

- `EVIDENCE_MISSING`
- `EVIDENCE_PARTIAL`
- `INPUT_CLOSURE_BLOCKED`
- `KPI_PROVENANCE_INCOMPLETE`
- `DECISION_JOURNAL_INCOMPLETE`
- `REVIEW_DATE_MISSING`
- `RANKING_UNSTABLE`
- `RANKING_STABILITY_NOT_EVALUATED`
- `SENSITIVITY_NOT_EVALUATED`
- `SCENARIO_NOT_EVALUATED`
- `TAIL_RISK_NOT_EVALUATED`
- `BASELINE_NOT_DEFINED`
- `LINEAGE_INCOMPLETE`
- `CONTRACT_VERSION_MISMATCH`

Reason codes may be extended only by a contract update and tests.

## Producer Serialization Rules

Future producers must use deterministic serialization.

CSV output:

- UTF-8
- LF newlines
- comma-separated
- header required
- booleans serialized as `true` or `false`
- missing scalar values serialized as an empty string
- missing list values serialized as an empty string
- list delimiter: semicolon `;`
- percent values serialized as decimal ratios between `0.0` and `1.0`, not
  `0-100`
- timestamps serialized as ISO-8601 UTC when generated
- as-of dates serialized as `YYYY-MM-DD`
- enum values serialized as uppercase snake case

JSON output:

- UTF-8
- LF newlines
- `sort_keys=True`
- `indent=2`
- booleans serialized as native JSON booleans
- lists serialized as native arrays
- missing optional scalar values serialized as `null`
- percent values serialized as numeric decimal ratios between `0.0` and `1.0`
- timestamps serialized as ISO-8601 UTC
- enum values serialized as uppercase snake case

## Producer Field Schema

This table is producer-ready for a minimal Phase 1.5 producer. It defines field
shape only; it does not implement a producer.

| field_name | type | required | allowed_empty | csv_serialization | json_serialization | allowed_values / enum | default_when_missing | validation_rule | phase_1_5_behavior |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `run_id` | string | yes | no | scalar | string | repo run ID | empty invalid | must identify the monthly or operator run | mandatory |
| `as_of_date` | date | yes | no | `YYYY-MM-DD` | string | date | empty invalid | must parse as date | mandatory |
| `generated_at` | timestamp | yes | no | ISO-8601 UTC | string | UTC timestamp | empty invalid | must include timezone or `Z` | generated by producer |
| `source_commit_sha` | string | yes when Git metadata available | no when available | scalar | string | 40-char SHA or explicit unavailable marker | empty only if Git unavailable | full SHA preferred | mandatory when Git is available |
| `contract_version` | string | yes | no | scalar | string | `v1-design` until promoted | empty invalid | must equal this contract version | mandatory |
| `input_artifacts` | list[string] | yes | no | semicolon list | array | repo-relative paths | empty invalid | no absolute private paths | mandatory |
| `evidence_coverage_status` | enum | yes | no | enum | string | `COVERED`;`PARTIAL`;`REVIEW`;`MISSING` | `MISSING` | must reflect evidence/provenance inputs | mandatory |
| `evidence_coverage_pct` | decimal ratio | yes | yes when not measurable | decimal string | number or null | `0.0..1.0` | empty/null | blank only when coverage is `MISSING` or not measurable | mandatory if computable |
| `data_quality_status` | enum | yes | no | enum | string | `COVERED`;`PARTIAL`;`REVIEW`;`MISSING` | `MISSING` | must not hide missing/sample-only inputs | mandatory |
| `missing_critical_fields` | list[string] | yes | yes | semicolon list or empty | array | contract field names or input names | empty list | non-empty caps confidence | mandatory |
| `stale_inputs` | list[string] | yes | yes | semicolon list or empty | array | repo-relative paths or input labels | empty list | stale basis must be visible | mandatory |
| `conflicting_inputs` | list[string] | yes | yes | semicolon list or empty | array | repo-relative paths or input labels | empty list | non-empty blocks `HIGH` | mandatory |
| `decision_capture_status` | enum | yes | no | enum | string | `PASS`;`WARN`;`FAIL`;`NOT_APPLICABLE`;`MISSING` | `MISSING` | empty journal may be `MISSING` or `NOT_APPLICABLE` only when explicitly justified | mandatory if artifact expected |
| `journal_quality_status` | enum | yes | no | enum | string | `PASS`;`WARN`;`FAIL`;`NOT_APPLICABLE`;`MISSING` | `MISSING` | must reflect append-only capture completeness only | mandatory |
| `portfolio_health_status` | enum | yes | no | enum | string | `PASS`;`WARN`;`FAIL`;`REVIEW`;`NOT_APPLICABLE`;`MISSING` | `MISSING` | must not change portfolio rules | mandatory |
| `cash_refill_status` | enum | yes | no | enum | string | `PASS`;`WARN`;`FAIL`;`REVIEW`;`NOT_APPLICABLE`;`MISSING` | `MISSING` | read from cash-refill review artifact | mandatory |
| `rebalance_status` | enum | yes | no | enum | string | `PASS`;`WARN`;`FAIL`;`REVIEW`;`NOT_APPLICABLE`;`MISSING` | `MISSING` | read from rebalance review artifact | mandatory |
| `ranking_available` | boolean | yes | no | `true`/`false` | boolean | `true`;`false` | `false` | true only when ranking artifact exists and is readable | mandatory |
| `ranking_stability_status` | enum | yes | no | enum | string | `STABLE`;`MODERATE`;`UNSTABLE`;`NOT_EVALUATED` | `NOT_EVALUATED` | not inferred before robustness producer exists | Phase 1.5 default `NOT_EVALUATED` |
| `sensitivity_status` | enum | yes | no | enum | string | `STABLE`;`MODERATE`;`UNSTABLE`;`NOT_EVALUATED` | `NOT_EVALUATED` | not inferred before sensitivity producer exists | Phase 1.5 default `NOT_EVALUATED` |
| `scenario_status` | enum | yes | no | enum | string | `PASS`;`WARN`;`FAIL`;`NOT_APPLICABLE`;`NOT_EVALUATED` | `NOT_EVALUATED` | no scenario computation in Phase 1.5 | Phase 1.5 default `NOT_EVALUATED` |
| `tail_risk_status` | enum | yes | no | enum | string | `PASS`;`WARN`;`FAIL`;`NOT_APPLICABLE`;`NOT_EVALUATED` | `NOT_EVALUATED` | no tail-risk computation in Phase 1.5 | Phase 1.5 default `NOT_EVALUATED` |
| `scenario_robustness_score` | enum or empty | yes | yes | `NOT_EVALUATED` or empty | string or null | `NOT_EVALUATED` in Phase 1.5 | `NOT_EVALUATED` | must not be numeric until scenario contract exists | reserved only |
| `decision_confidence_level` | enum | yes | no | enum | string | `HIGH`;`MEDIUM`;`LOW`;`REVIEW` | `REVIEW` | must be rule-derived by this contract | mandatory |
| `confidence_reason_codes` | list[string] | yes | yes | semicolon list or empty | array | reason-code taxonomy | empty list | required when confidence below `HIGH` | mandatory |
| `review_required` | boolean | yes | no | `true`/`false` | boolean | `true`;`false` | `true` | false only with no hard blockers and valid mandatory inputs | mandatory |
| `review_reason_codes` | list[string] | yes | yes only when `review_required=false` | semicolon list or empty | array | reason-code taxonomy | empty list | non-empty required when `review_required=true` | mandatory |
| `non_scope_confirmations` | list[string] | yes | no | semicolon list | array | explicit non-scope labels | empty invalid | must confirm no broker/order/trading/scoring mutation | mandatory |

## Deterministic Decision Confidence Rule Matrix

`decision_confidence_level` is rule-derived process confidence. It is not a
manual opinion and not a probability score. Producers must apply the most
restrictive applicable rule.

| condition | required result | required reason code |
| --- | --- | --- |
| Input Closure or equivalent input blocker is `BLOCKED`, `FAIL` or `REVIEW_REQUIRED` | `decision_confidence_level=REVIEW` | `INPUT_CLOSURE_BLOCKED` |
| `missing_critical_fields` is not empty | maximum `LOW` | `EVIDENCE_MISSING` |
| `data_quality_status=MISSING` | `decision_confidence_level=REVIEW` | `EVIDENCE_MISSING` |
| `data_quality_status=REVIEW` | maximum `LOW` | `EVIDENCE_PARTIAL` or specific blocker code |
| `evidence_coverage_status=PARTIAL` | maximum `MEDIUM` | `EVIDENCE_PARTIAL` |
| `ranking_stability_status=NOT_EVALUATED` in Phase 1.5 | maximum `MEDIUM` | `RANKING_STABILITY_NOT_EVALUATED` |
| `sensitivity_status=NOT_EVALUATED` in Phase 1.5 | maximum `MEDIUM` | `SENSITIVITY_NOT_EVALUATED` |
| `scenario_status=NOT_EVALUATED` in Phase 1.5 | no hard blocker | optional `SCENARIO_NOT_EVALUATED` |
| `tail_risk_status=NOT_EVALUATED` in Phase 1.5 | no hard blocker | optional `TAIL_RISK_NOT_EVALUATED` |
| contract version mismatch | `decision_confidence_level=REVIEW` | `CONTRACT_VERSION_MISMATCH` |
| lineage incomplete for mandatory inputs | `decision_confidence_level=REVIEW` | `LINEAGE_INCOMPLETE` |

`HIGH` is allowed only when all of the following are true:

- `data_quality_status=COVERED`
- `evidence_coverage_status=COVERED`
- `missing_critical_fields` is empty
- `conflicting_inputs` is empty
- `decision_capture_status` is not `MISSING`
- `portfolio_health_status` is not `REVIEW`
- all Phase 1.5 mandatory inputs are present and valid
- no hard blocker reason codes are present

`MEDIUM` is allowed when no hard blockers are present, at least one optional or
not-yet-evaluated Phase 1.5 area exists, and the data state is neither
`MISSING` nor hard `REVIEW`.

`LOW` is required when relevant data are partially missing and the review is not
hard-blocked, but process confidence remains low.

`REVIEW` is required when hard blockers exist, contract version does not match,
lineage is incomplete, a critical input is missing, or Input Closure is blocked.

## Minimal Producer Input Matrix For Phase 1.5

| input_artifact | expected_path | producer_module | phase_1_5_required | missing_behavior | contribution_to_confidence | expected_status_if_not_available | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| personal_input_closure_report | `data/processed/personal_input_closure_report.csv` | `src.personal_input_closure` | yes | hard review blocker | drives data-quality and input-closure reason codes | `MISSING` / `REVIEW` | mandatory readiness surface |
| personal_decision_state_capture | `data/processed/personal_decision_state_capture.csv` | `src.personal_decision_state_capture` | yes if Decision Capture is expected for the run | visible journal gap | drives `decision_capture_status` and `journal_quality_status` | `MISSING` or `NOT_APPLICABLE` with reason | empty journal must not be treated as complete |
| personal_kpi_provenance_summary / audit | `data/processed/personal_kpi_provenance_summary.csv`; `data/processed/personal_kpi_provenance_audit.csv` | `src.personal_kpi_provenance_audit` | yes when score interpretation depends on KPI provenance | review blocker or coverage cap | drives evidence coverage and KPI reason codes | `MISSING` / `REVIEW` | no KPI values inferred |
| personal_core_kpi_closure | `data/processed/personal_core_kpi_closure_summary.csv` | `src.personal_core_kpi_closure` | yes when available in repo profile | review blocker or coverage cap | contributes missing critical fields | `MISSING` / `REVIEW` | does not replace provenance audit |
| cash_refill_review | `data/processed/personal_cash_refill_review.csv` | `src.cash_refill_review` | yes | review blocker when missing | drives `cash_refill_status` | `MISSING` / `REVIEW` | no cash deployment decision |
| rebalance_review | `data/processed/personal_rebalance_review.csv` | `src.rebalance_review` | yes | review blocker when missing | drives `rebalance_status` and portfolio health | `MISSING` / `REVIEW` | no sell/order execution |
| personal_run_manifest | `data/processed/personal_run_manifest.json` | `src.personal_run_engine` | yes | lineage blocker | drives lineage and replay confidence | `MISSING` / `REVIEW` | repo-relative refs only |
| personal_run_used_inputs | `data/processed/personal_run_used_inputs.csv` | `src.personal_run_engine` | yes | lineage blocker | drives input artifact traceability | `MISSING` / `REVIEW` | no raw/private expansion |
| monthly_ranking output | `data/processed/personal_monthly_buy_ranking.csv` | `src.monthly_ranking_engine` | yes when ranking is part of monthly run | ranking unavailable | drives `ranking_available`; robustness remains separate | `MISSING` / `REVIEW` | no score formula change |
| scoring output | `data/processed/personal_company_scores.csv`; `data/processed/personal_score_audit.csv` | `src.scoring_engine` | yes when ranking/score interpretation is reviewed | evidence/data-quality cap | supports evidence and score-audit context | `MISSING` / `REVIEW` | no score recomputation by DQ producer |
| report refs / artifact index | run manifest and report paths | `src.personal_run_engine` / report builders | yes | lineage blocker | supports replay/review references | `MISSING` / `REVIEW` | full relative paths only |
| ranking robustness | future robustness artifact | future producer | no | surface as not evaluated | caps confidence at `MEDIUM` | `NOT_EVALUATED` | optional in Phase 1.5 |
| sensitivity | future sensitivity artifact | future producer | no | surface as not evaluated | caps confidence at `MEDIUM` | `NOT_EVALUATED` | optional in Phase 1.5 |
| scenario | future scenario artifact | future contract/producer | no | surface as not evaluated | no hard blocker in Phase 1.5 | `NOT_EVALUATED` | design-only |
| tail risk | future tail-risk artifact | future contract/producer | no | surface as not evaluated | no hard blocker in Phase 1.5 | `NOT_EVALUATED` | design-only |
| outcome scoreboard | future outcome artifact | deferred | no | surface as not evaluated or not applicable | no Phase 1.5 confidence input | `NOT_EVALUATED` / `NOT_APPLICABLE` | deferred |
| calibration | future calibration artifact | deferred | no | surface as not evaluated | no Phase 1.5 confidence input | `NOT_EVALUATED` | deferred |
| regret | future regret artifact | deferred | no | surface as not evaluated | no Phase 1.5 confidence input | `NOT_EVALUATED` | deferred |

## Phase 1.5 Default Rules

- `ranking_stability_status=NOT_EVALUATED` until a Ranking Robustness producer
  exists.
- `sensitivity_status=NOT_EVALUATED` until a Sensitivity producer exists.
- `scenario_status=NOT_EVALUATED`.
- `tail_risk_status=NOT_EVALUATED`.
- `scenario_robustness_score=NOT_EVALUATED` in CSV and JSON for Phase 1.5,
  unless a future Scenario/Tail-Risk contract changes this explicitly.
- `review_required=true` when any hard blocker exists.
- `review_required=false` only when no hard blockers exist and all Phase 1.5
  mandatory inputs are present, readable and contract-valid.
- `REVIEW`, `MISSING` and `NOT_EVALUATED` must be visible values, not silently
  converted into ready states.

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
scenario_status=NOT_EVALUATED
tail_risk_status=NOT_EVALUATED
scenario_robustness_score=NOT_EVALUATED
decision_confidence_level=REVIEW
confidence_reason_codes=INPUT_CLOSURE_BLOCKED;KPI_PROVENANCE_INCOMPLETE;SENSITIVITY_NOT_EVALUATED;RANKING_STABILITY_NOT_EVALUATED
review_required=True
review_reason_codes=INPUT_CLOSURE_BLOCKED;KPI_PROVENANCE_INCOMPLETE
```

### Ready-But-Not-Robustness-Evaluated State

```text
evidence_coverage_status=COVERED
data_quality_status=COVERED
decision_capture_status=PASS
journal_quality_status=PASS
ranking_available=True
ranking_stability_status=NOT_EVALUATED
sensitivity_status=NOT_EVALUATED
scenario_status=NOT_EVALUATED
tail_risk_status=NOT_EVALUATED
scenario_robustness_score=NOT_EVALUATED
decision_confidence_level=MEDIUM
confidence_reason_codes=RANKING_STABILITY_NOT_EVALUATED;SENSITIVITY_NOT_EVALUATED
review_required=True
review_reason_codes=RANKING_STABILITY_NOT_EVALUATED;SENSITIVITY_NOT_EVALUATED
```
