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
- Data Freshness / Staleness Summary
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
If a readable Decision Quality State has `review_required=true`, the operator
surface must not return `PASS`; it must surface `REVIEW` and an operator
attention reason of `DECISION_QUALITY_REVIEW_REQUIRED`.

### `REVIEW`

Use `REVIEW` when at least one of these is true:

- validation findings exist,
- review queue items exist,
- `review_required=true` in Decision Quality,
- Data Freshness review is required,
- Data Freshness reports stale, missing or unknown relevant data,
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

For Data Freshness, `PARTIAL` applies when the `data_freshness` stage was
selected for the same run but `data_freshness_summary.json` is missing or
unreadable. Standalone legacy operator-summary calls may omit Data Freshness,
but a same-run selected Data Freshness stage must not be hidden as `PASS`.

## Required Surface Fields

Future dashboard/operator-summary artifacts must provide at least:

- `schema_version`
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
- `queue_medium_count`
- `stale_state_count`
- `data_freshness_status`
- `data_freshness_review_required`
- `data_freshness_fresh_count`
- `data_freshness_stale_count`
- `data_freshness_missing_count`
- `data_freshness_unknown_count`
- `data_freshness_review_required_count`
- `data_freshness_not_applicable_count`
- `data_freshness_blocking_dashboard_count`
- `data_freshness_top_reason_codes`
- `top_reason_codes`
- `operator_attention_required`
- `operator_attention_level`
- `operator_attention_reasons`
- `source_artifacts`
- `non_scope_confirmations`

### Machine Field Table

| field | type | required | nullable | allowed_values | default_when_missing | source |
| --- | --- | --- | --- | --- | --- | --- |
| `schema_version` | integer | yes | no | positive integer | none | Surface producer |
| `surface_generated_at` | string | yes | no | ISO-8601 UTC | current producer timestamp | Surface producer |
| `as_of_date` | string | yes | yes | `YYYY-MM-DD` | `null` only when no manifest/state date exists | Run manifest / Decision Quality |
| `source_commit_sha` | string | yes | yes | git SHA string | `null` | Run manifest / Decision Quality |
| `run_id` | string | yes | yes | stable run identifier | `null` | Run manifest / Decision Quality |
| `surface_status` | string | yes | no | `PASS`, `REVIEW`, `NOT_AVAILABLE`, `PARTIAL` | `NOT_AVAILABLE` | Surface producer |
| `artifact_status` | string | yes | no | `COMPLETE`, `PARTIAL`, `NOT_AVAILABLE`, `UNREADABLE`, `STALE`, `CONFLICTING` | `NOT_AVAILABLE` | Source artifact reader |
| `missing_artifacts` / `missing_required_artifacts` | array[string] | yes | no | artifact paths or redacted labels | `[]` | Source artifact reader |
| `partial_artifacts` | array[string] | yes | no | artifact paths or redacted labels | `[]` | Source artifact reader |
| `decision_quality_status` | string | yes | yes | `PASS`, `REVIEW`, `NOT_AVAILABLE`, `PARTIAL` or producer status | `NOT_AVAILABLE` | Decision Quality State |
| `decision_quality_review_required` | boolean | yes | yes | `true`, `false`, `null` | `null` | Decision Quality State |
| `process_confidence_level` | string | yes | yes | `HIGH`, `MEDIUM`, `LOW`, `REVIEW`, `null` | `null` | Decision Quality State |
| `decision_journal_validation_status` | string | yes | no | `PASS`, `REVIEW`, `NOT_AVAILABLE`, `PARTIAL` | `NOT_AVAILABLE` | Decision Journal Validation |
| `validation_findings_count` | integer | yes | no | `>=0` | `0` only for readable header-valid artifact | Decision Journal Validation |
| `validation_blocker_count` | integer | yes | no | `>=0` | `0` only for readable header-valid artifact | Decision Journal Validation |
| `validation_high_count` | integer | yes | no | `>=0` | `0` only for readable header-valid artifact | Decision Journal Validation |
| `queue_items` | integer | yes | no | `>=0` | `0` only for readable header-valid artifact | Review Queue |
| `queue_blocker_count` | integer | yes | no | `>=0` | `0` only for readable header-valid artifact | Review Queue |
| `queue_high_count` | integer | yes | no | `>=0` | `0` only for readable header-valid artifact | Review Queue |
| `queue_medium_count` | integer | yes | no | `>=0` | `0` only for readable header-valid artifact | Review Queue |
| `stale_state_count` | integer | yes | no | `>=0` | `0` only for readable header-valid artifact | Validation / Review Queue |
| `data_freshness_status` | string | yes | no | `FRESH`, `STALE`, `MISSING`, `UNKNOWN`, `REVIEW_REQUIRED`, `NOT_APPLICABLE`, `NOT_AVAILABLE`, `PARTIAL` | `NOT_AVAILABLE` | Data Freshness Summary |
| `data_freshness_review_required` | boolean | yes | no | `true`, `false` | `false` only for readable non-review-required summary | Data Freshness Summary |
| `data_freshness_fresh_count` | integer | yes | no | `>=0` | `0` | Data Freshness Summary |
| `data_freshness_stale_count` | integer | yes | no | `>=0` | `0` | Data Freshness Summary |
| `data_freshness_missing_count` | integer | yes | no | `>=0` | `0` | Data Freshness Summary |
| `data_freshness_unknown_count` | integer | yes | no | `>=0` | `0` | Data Freshness Summary |
| `data_freshness_review_required_count` | integer | yes | no | `>=0` | `0` | Data Freshness Summary |
| `data_freshness_not_applicable_count` | integer | yes | no | `>=0` | `0` | Data Freshness Summary |
| `data_freshness_blocking_dashboard_count` | integer | yes | no | `>=0` | `0` | Data Freshness Summary items |
| `data_freshness_top_reason_codes` | array[string] | yes | no | reason-code strings | `[]` | Data Freshness Summary |
| `top_reason_codes` | array[string] | yes | no | reason-code strings | `[]` | Validation / Review Queue |
| `operator_attention_required` | boolean | yes | no | `true`, `false` | `true` for missing/unreadable required artifacts | Surface producer |
| `operator_attention_level` | string | yes | no | `NONE`, `LOW`, `MEDIUM`, `HIGH`, `BLOCKER` | `BLOCKER` for missing/unreadable required artifacts | Surface producer |
| `operator_attention_reasons` | array[string] | yes | no | reason-code strings | required-artifact reason when unavailable | Surface producer |
| `source_artifacts` | array[object] | yes | no | see source artifact contract | `[]` | Source artifact reader |
| `non_scope_confirmations` | array[string] | yes | no | explicit non-scope statements | fixed contract list | Surface producer |

`process_confidence_level` remains process/review confidence, not Investment
Confidence. `operator_attention_required` is an operator follow-up flag, not an
order signal. `surface_status=PASS` is valid only when required artifacts are
present, readable, no findings or queue items exist, and readable Decision
Quality does not require review.

If Data Freshness is readable and `review_required=true`, or if it contains
`STALE`, `MISSING`, `UNKNOWN` or `REVIEW_REQUIRED` relevant items, the surface
must set operator attention and include `DATA_FRESHNESS_REVIEW_REQUIRED` in
`operator_attention_reasons`. This is a governance signal only.

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

Dominant aggregate artifact status is deterministic. When multiple source
artifact statuses are present, the aggregate `artifact_status` uses this
priority ladder:

```text
UNREADABLE > CONFLICTING > NOT_AVAILABLE > PARTIAL > STALE > COMPLETE
```

The aggregate field is intentionally lossy. Implementations must also preserve
`source_artifacts` or equivalent detail rows so that stale and conflicting
sub-states remain visible even when a higher-priority dominant status applies.

Decision Quality may be `NOT_AVAILABLE` without blocking Decision Journal
Validation. Stale state is a process freshness signal, not an investment risk.
Data Freshness may be `NOT_AVAILABLE` for standalone legacy calls; when the
same run selected `data_freshness`, missing or unreadable freshness output is
`PARTIAL` and must not be rendered as `PASS`.

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
- `review_required=true` in Decision Quality is an operator review signal and
  blocks `surface_status=PASS`.
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
