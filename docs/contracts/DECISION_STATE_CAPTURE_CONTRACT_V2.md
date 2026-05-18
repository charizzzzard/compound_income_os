# Decision State Capture Contract v2

## Purpose

Decision State Capture v2 defines a minimal, friction-aware, append-only contract
for deliberate decisions and deliberate no-actions.

It is not:

- a full execution ledger
- outcome attribution
- benchmark return calculation
- policy feedback
- a thesis schema
- a tax lot tracker
- a broker/order execution process

Current expected outputs:

- `data/processed/personal_decision_state_capture.csv`
- `reports/<YYYY-MM-DD>/personal_decision_state_capture_report.md`

`src.personal_decision_state_capture` implements the current minimal standalone
producer for this contract. The tracked processed artifact may be header-only;
that means the producer exists, but real decision history has not necessarily
been captured yet.

## Manual Required Fields

The operator must provide these fields:

- `decision_scope`
- `proposed_action`
- `human_decision`
- `decision_status`
- `reasoning_3_sentences`
- `dominant_uncertainty`
- `benchmark_alternative`

`reasoning_3_sentences` should answer:

1. Why is this review relevant?
2. Why was this decision or no-action chosen?
3. What condition would change the decision?

## Conditional Required Fields

- `review_date` is required only for `HOLD_REVIEW`, `WAIT_*` proposed actions,
  `RESEARCH_MORE`, or `decision_status=REVIEW_SCHEDULED`.

It is not universally required.

## Auto-Filled Or System-Derived Fields

Future implementation should auto-fill mechanical fields through a small CLI or
local form. Direct Excel editing should be discouraged because it makes lineage,
defaults and validation harder to enforce.

Auto/system fields:

- `decision_id`
- `decision_date`
- `created_at`
- `run_id`
- `manifest_path`
- `primary_report_path`
- `source_snapshot_date`
- `accounting_basis`
- `asset_id`
- `ticker`
- `asset_name`
- `asset_type`
- `policy_ref`
- `benchmark_ref_or_label`

`benchmark_alternative` is the operator-selected v1 comparison category.
`benchmark_ref_or_label` is the replay-preserved concrete benchmark label or
reference. In v1, `benchmark_ref_or_label` may be derived from
`benchmark_alternative` if no benchmark registry exists.

No benchmark return calculation is performed in v1.

`accounting_basis` defaults to `SNAPSHOT_ONLY` unless a reviewed ledger basis
exists. Unresolved auto/system fields must be marked `UNKNOWN` or
`MISSING_REFERENCE` and surfaced in the report.

## Optional Fields

- `policy_version`
- `operator_state`
- `decision_pressure`
- `market_context_tag`
- `conviction`
- `cash_context`
- `source_paths`
- `notes`

`policy_version` is optional in v1. `operator_state` defaults to
`NOT_RECORDED`.

## Enums

### `decision_scope`

- `ASSET`
- `HOLDING_REVIEW`
- `PORTFOLIO`
- `CASH`
- `MONTHLY_REVIEW`
- `WATCHLIST`
- `UNKNOWN`

### `proposed_action`

- `ADD_REVIEW`
- `HOLD_REVIEW`
- `TRIM_REVIEW`
- `EXIT_REVIEW`
- `WAIT_FOR_EVIDENCE`
- `WAIT_FOR_PRICE`
- `WAIT_FOR_REVIEW`
- `RESEARCH_MORE`
- `REJECT_CANDIDATE`
- `NO_ACTION`
- `SKIP_MONTH`
- `CASH_DEPLOYMENT`
- `UNKNOWN`

These are review states, not execution instructions.

### `human_decision`

- `PENDING_REVIEW`
- `APPROVED_FOR_MANUAL_ACTION`
- `REJECTED`
- `DEFERRED`
- `NO_ACTION`
- `NOT_REVIEWED`

### `decision_status`

- `OPEN`
- `BLOCKED`
- `REVIEW_SCHEDULED`
- `CLOSED`
- `NOT_AVAILABLE`
- `INVALID`
- `INSUFFICIENT_EVIDENCE`
- `SUPERSEDED`

### `dominant_uncertainty`

- `MISSING_DATA`
- `VALUATION`
- `PORTFOLIO_FIT`
- `CASH_CONTEXT`
- `TAX_CONTEXT`
- `EVIDENCE_QUALITY`
- `BEHAVIOURAL_RISK`
- `UNKNOWN`

### `accounting_basis`

- `SNAPSHOT_ONLY`
- `PARTIAL_LEDGER`
- `RECONCILED_LEDGER`
- `UNKNOWN`

### `cash_context`

- `AVAILABLE_CASH`
- `RESERVED_CASH`
- `TAX_RESERVE`
- `NO_CASH`
- `UNKNOWN`

### `operator_state`

- `NORMAL`
- `MARKET_STRESS`
- `DRAWDOWN_STRESS`
- `EUPHORIA`
- `TIME_CONSTRAINED`
- `UNCERTAIN`
- `NOT_RECORDED`

Default: `NOT_RECORDED`.

### `decision_pressure`

- `NORMAL`
- `TIME_CONSTRAINED`
- `MARKET_STRESS`
- `UNKNOWN`

### `benchmark_alternative`

- `CASH`
- `CORE_ETF`
- `DIVIDEND_GROWTH_ETF`
- `QUALITY_ETF`
- `EXISTING_HOLDING`
- `WATCHLIST_CANDIDATE`
- `WATCHLIST_TOP_CANDIDATE`
- `NO_ACTION`
- `UNKNOWN`

## No-Action Capture Rule

No-action is required only if one of these applies:

- available cash above threshold is consciously not deployed
- a top candidate is consciously rejected or deferred
- decision readiness is blocked
- monthly review is explicitly skipped
- operator overrides the attention queue

Routine absence of activity does not require a journal entry unless it meets one
of those criteria.

## Replay Minimum Embedded In v1

Each entry must preserve enough context to reconstruct the review surface:

- `run_id`
- `manifest_path`
- `primary_report_path`
- `source_snapshot_date`
- `policy_ref`
- `benchmark_ref_or_label`
- `accounting_basis`

This is a minimal invariant, not a full time-aware replay engine.

## Explicitly Out Of Scope For v1

- `linked_transaction_id`
- manual execution tracking
- outcome attribution
- benchmark return calculation
- tax lot tracking
- FX attribution
- simulation
- backtesting
- policy feedback
- full Portfolio Event Ledger

## Examples

### `ADD_REVIEW`

Used when an asset is ready for human review as a potential manual action. It
does not instruct order execution.

### `WAIT_FOR_EVIDENCE`

Used when the review is blocked by missing or stale evidence.

### `NO_ACTION`

Used when the operator deliberately chooses no action under the no-action capture
rule.

### `SKIP_MONTH`

Used when the monthly review is explicitly skipped and should remain visible.

### `CASH_DEPLOYMENT`

Used when available cash is consciously reviewed for deployment or non-deployment.

## Acceptance Criteria For Future Implementation

- a real entry is possible in 5-7 minutes
- no field requires a full thesis
- no field requires tax calculation
- no field requires transaction reconciliation
- no field requires outcome assessment
- generated report shows open, blocked, wait/review, no-action and overdue
  review items
- producer writes processed/report artifacts only
- no broker/order execution logic is introduced
