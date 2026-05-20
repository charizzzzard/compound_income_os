# Dashboard Operator Surface Contract

contract_version: 1

## Purpose

The Dashboard Operator Surface is a read-only summary of process state. It is a
stable machine-readable and report-readable contract for future dashboard
surfaces.

It is not a trading dashboard, not a broker, not an order approval system, not a
performance or alpha forecast and not an Investment Confidence layer. It may
show process confidence, review blockers, stale state and operator attention
requirements, but it must not create, approve, prepare or execute investment
actions.

## Surface Scope

The surface covers:

- Decision Quality Summary
- Decision Journal Validation Summary
- Review Queue Summary
- Missing/Partial Artifact Status
- Stale State / Freshness Signals
- Non-Scope / Risk Notes

The surface reads already generated processed artifacts. It must not compute
scores, infer missing fundamentals, mutate journals, enrich private data or
write broker/order artifacts.

## Status Semantics

### `NOT_AVAILABLE`

Use `NOT_AVAILABLE` when:

- the stage did not run,
- the expected artifact is missing,
- the artifact is unreadable, or
- the state cannot be inspected safely.

`NOT_AVAILABLE` must never be interpreted as `PASS`.

### `PASS`

Use `PASS` when:

- the relevant stage ran,
- expected artifacts are present and readable,
- no findings exist,
- no queue items exist, and
- null or zero counts are explicitly visible.

Header-only, contract-valid Decision Journal Validation and Review Queue CSVs
are valid `PASS` inputs when both artifacts are present and readable.

### `REVIEW`

Use `REVIEW` when at least one of these is true:

- validation findings exist,
- review queue items exist,
- `review_required=true` in Decision Quality,
- duplicate decision IDs exist,
- due reviews exist,
- stale state exists,
- lineage mismatch exists, or
- other governance/review blockers are visible.

`REVIEW` is a process state, not a buy/sell/hold decision.

### `PARTIAL`

Use `PARTIAL` when:

- one expected artifact is present and readable,
- another expected artifact is missing or unreadable,
- enough information exists to show partial status, and
- a full `PASS` would be misleading.

For Decision Journal Validation, `PARTIAL` applies when the validation artifact
exists but the queue artifact does not, or the queue artifact exists but the
validation artifact does not. `PARTIAL` is also valid when Decision Quality is
missing but Decision Journal Validation can still be read.

## Required Surface Fields

Future dashboard/operator-summary artifacts must provide at least:

- `surface_generated_at`
- `as_of_date`
- `source_commit_sha`
- `run_id`
- `surface_status`
- `artifact_status`
- `missing_artifacts`
- `partial_artifacts`
- `decision_quality_status`
- `decision_quality_review_required`
- `process_confidence_level`
- `decision_journal_validation_status`
- `validation_findings_count`
- `validation_blocker_count`
- `validation_high_count`
- `queue_items`
- `queue_blocker_count`
- `queue_high_count`
- `stale_state_count`
- `top_reason_codes`
- `operator_attention_required`
- `operator_attention_reasons`
- `non_scope_confirmations`

## Artifact Availability Model

Allowed artifact availability values:

- `COMPLETE`
- `PARTIAL`
- `NOT_AVAILABLE`
- `UNREADABLE`
- `STALE`
- `CONFLICTING`

Rules:

- `COMPLETE` means all required artifacts for that surface segment are present,
  readable and contract-shaped.
- `PARTIAL` means some required artifacts are present and readable while others
  are missing or unreadable.
- `NOT_AVAILABLE` means no useful state can be read because the stage did not
  run or artifacts are absent.
- `UNREADABLE` means an artifact exists but cannot be parsed safely.
- `STALE` means the artifact is readable but older than the effective process
  context under the applicable freshness rule.
- `CONFLICTING` means two readable artifacts disagree on lineage, run ID,
  source commit, date or other contract identity fields.

Decision Quality may be `NOT_AVAILABLE` without blocking Decision Journal
Validation. Stale state is a process freshness signal, not an investment risk.

## Review Queue Summary Semantics

The dashboard surface must preserve these Review Queue Summary fields:

- `queue_items`
- `queue_blocker_count`
- `queue_high_count`
- `queue_medium_count`
- `queue_low_count`
- `queue_note_count`
- `top_reason_codes`
- `oldest_due_review_date`
- `max_days_overdue`
- `duplicate_decision_id_count`
- `stale_state_count`

Counts must remain numeric and explicit. Zero-count `PASS` states must be
visible.

## Semantic Protection Rules

- `process_confidence_level` is not Investment Confidence.
- `review_required` is not a buy/sell/hold decision.
- `operator_attention_required` is not an order signal.
- `stale_state` is process freshness, not a portfolio warning.
- `BLOCKER` and `HIGH` are governance/hygiene priorities, not investment risk
  labels.
- A dashboard implementation must not hide `PARTIAL`, `NOT_AVAILABLE` or
  `REVIEW` behind green UI states.

## Non-Scope Confirmations

The Dashboard Operator Surface must explicitly preserve these non-scope
confirmations:

- no broker/order/trading
- no score formula change
- no portfolio rule change
- no silent data enrichment
- no simulation/backtesting
- no outcome attribution
- no runtime LLM decisioning
- no tax quantification
- no portfolio event ledger
- no private raw data
