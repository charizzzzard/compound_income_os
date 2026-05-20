# Review Queue Summary Contract

contract_version: 1

## Purpose

The Review Queue Summary is a future machine-readable summary for the Dashboard
Operator Surface. It is derived from Decision Journal Validation and Review
Queue artifacts. It is read-only and does not create decisions, update the
journal, execute orders or infer investment actions.

This contract defines the target artifact and the minimal producer surface. The
current producer is `src/dashboard_operator_summary.py`; it remains read-only
and aggregates existing governance artifacts only.

## Inputs

Primary inputs:

- `data/processed/decision_journal_validation.csv`
- `data/processed/decision_review_queue.csv`

Optional context:

- `data/processed/decision_quality_state.csv`
- `data/processed/decision_quality_state.json`
- `data/processed/personal_run_manifest.json`
- `data/processed/personal_run_artifacts.csv`

## Output Target

Target JSON artifact:

- `data/processed/review_queue_summary.json`

Optional later CSV artifact:

- `data/processed/review_queue_summary.csv`

No CSV output is required for the minimal producer.

## Required Fields

The future JSON summary must include at least:

- `schema_version`
- `as_of_date`
- `run_id`
- `source_commit_sha`
- `artifact_status`
- `validation_status`
- `validation_findings_count`
- `validation_blocker_count`
- `validation_high_count`
- `queue_items`
- `queue_blocker_count`
- `queue_high_count`
- `queue_medium_count`
- `stale_state_count`
- `duplicate_decision_id_count`
- `missing_review_date_count`
- `due_review_count`
- `decision_quality_review_required_count`
- `lineage_mismatch_count`
- `top_reason_codes`
- `operator_attention_required`
- `operator_attention_level`
- `operator_attention_reasons`
- `missing_artifacts`
- `missing_required_artifacts`
- `partial_artifacts`
- `source_artifacts`
- `non_scope_confirmations`

## Source Artifacts

`source_artifacts` is a structured list. Each entry must use this shape:

```json
{
  "path": "data/processed/decision_review_queue.csv",
  "required": true,
  "status": "COMPLETE",
  "row_count": 0,
  "sha256": null,
  "reason": null
}
```

Required fields per source artifact:

- `path`: repo-relative path or stable redacted label.
- `required`: native JSON boolean.
- `status`: one of the artifact availability values below.
- `row_count`: integer count for readable tabular artifacts; `null` when not
  measurable.
- `sha256`: optional artifact hash; `null` when unavailable or intentionally
  not emitted.
- `reason`: optional machine-readable reason for missing, unreadable, stale or
  conflicting state.

Raw local absolute paths, Windows drive paths, UNC paths and path traversal
strings must not be emitted.

## Status And Enum Values

Summary status values:

- `PASS`
- `REVIEW`
- `NOT_AVAILABLE`
- `PARTIAL`

Artifact availability values:

- `COMPLETE`
- `PARTIAL`
- `NOT_AVAILABLE`
- `UNREADABLE`
- `STALE`
- `CONFLICTING`

Operator attention levels:

- `NONE`
- `LOW`
- `MEDIUM`
- `HIGH`
- `BLOCKER`

## Rules

- Missing required artifacts produce `NOT_AVAILABLE` or `PARTIAL`, never
  `PASS`.
- Header-only, contract-valid validation and queue artifacts produce `PASS`
  with zero counts.
- Any `BLOCKER` queue item sets `operator_attention_level=BLOCKER`.
- Any `HIGH` queue item sets at least `operator_attention_level=HIGH`.
- Stale-only findings set `operator_attention_level=MEDIUM` unless another
  blocker/high rule applies.
- Duplicate decision ID findings set `operator_attention_level=BLOCKER`.
- Validation findings without queue items must remain visible.
- Queue items without validation findings must remain visible.
- `operator_attention_required=true` is a process-follow-up signal, not an
  investment action or order signal.

## Serialization

JSON serialization requirements:

- UTF-8
- LF newlines
- `sort_keys=True`
- `indent=2`
- native JSON booleans
- native JSON arrays
- missing optional scalar values: `null`

CSV serialization, if later added, must follow existing project conventions:
UTF-8, LF, deterministic header order, comma-separated fields and semicolon
delimiters for list-like fields.

## Non-Scope Confirmations

The summary must not introduce:

- broker/order/trading logic
- score formula changes
- portfolio rule changes
- silent data enrichment
- simulation/backtesting
- outcome attribution
- runtime LLM decisioning
- tax quantification
- portfolio event ledger behavior
- private raw data exposure
