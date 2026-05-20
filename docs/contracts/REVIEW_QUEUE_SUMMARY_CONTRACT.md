# Review Queue Summary Contract

contract_version: 1

## Purpose

The Review Queue Summary is a future machine-readable summary for the Dashboard
Operator Surface. It is derived from Decision Journal Validation and Review
Queue artifacts. It is read-only and does not create decisions, update the
journal, execute orders or infer investment actions.

This patch defines the target contract only. A producer may be added later.

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

No output is implemented by this contract patch.

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
- `partial_artifacts`
- `non_scope_confirmations`

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
