# Decision Falsification Trigger Contract v1

## Purpose

A falsification trigger is a locked, probabilistic, forward claim attached to
exactly one existing Decision Capture `decision_id`. It concerns the investment
thesis or company, not the holding period. Selling, watchlist removal, or a later
decision change does not delete or resolve it.

The workflow is proposal -> Human Review -> CLI Lock. Proposals are generated,
replaceable, and non-canonical. Only the human-operated lock appends to the
canonical ledger. Codex/LLMs may propose but must not lock.

## Canonical artifacts

- proposal: `data/processed/personal_decision_trigger_proposals.json`
- locked ledger: `data/processed/personal_decision_triggers.csv`

The proposal can be replaced. The locked ledger is append-only. An existing row
is never mutated. A necessary correction is a new record with
`supersedes_trigger_id`; the original history remains.

## Cardinality and decision link

- `decision_id` must already exist in the Decision Capture journal.
- a decision must have at least 2 and at most 5 active locked trigger records
  under this contract
- duplicate `trigger_id` values fail fast
- no synthetic benchmark Decision such as `BENCHMARK_000` is permitted

## Required locked fields

Every locked row contains:

- `trigger_id`
- `decision_id`
- `claim`
- `claim_type`
- `material`
- `decision_relevant`
- `future_facing`
- `falsifiable`
- `deterministically_resolvable`
- `tautological`
- `already_known`
- `purely_narrative_without_resolution_rule`
- `metric_name`
- `metric_definition_version`
- `source_document_type`
- `source_section`
- `line_item`
- `fallback_computation`
- `tolerance`
- `ambiguity_rule`
- `operator`
- `threshold`
- `unit`
- `probability_holds`
- `expected_resolution_date`
- `resolution_deadline`
- `policy_version`
- `created_at`
- `locked_at`
- `source_paths`
- `record_hash`
- `previous_record_hash`

`supersedes_trigger_id` is an optional correction link. A field that genuinely
does not apply stores `NOT_APPLICABLE`; no value may be invented.

## Deterministic resolvability

At lock time the trigger fixes the metric, definition version, resolving
document type, table/section, line item, unit, operator, decimal-string
threshold, decimal-string tolerance, definition-change behavior, and any
allowed fallback computation. A bare claim such as `Organic growth >= 5%` is
insufficient.

Example resolution definition:

```json
{
  "metric_name": "organic_revenue_growth_yoy",
  "metric_definition_version": "1",
  "source_document_type": "annual_report",
  "source_section": "Financial Review",
  "line_item": "Organic revenue growth (%)",
  "fallback_computation": "NOT_APPLICABLE",
  "operator": ">=",
  "threshold": "0.05",
  "unit": "ratio",
  "tolerance": "0.001",
  "ambiguity_rule": "UNRESOLVABLE_DEFINITION_IF_ISSUER_DEFINITION_CHANGES"
}
```

If the locked definition cannot later be resolved unambiguously, the result is
`UNRESOLVABLE_DEFINITION`; the resolver must not reinterpret the claim.

## Validation rules

- `probability_holds`, `threshold`, and `tolerance` are validated decimal
  strings; probability is in `[0,1]`, tolerance is non-negative
- operators are limited to `>=`, `>`, `<=`, `<`, `==`, and `!=`
- `expected_resolution_date` and `resolution_deadline` are ISO dates, with the
  deadline on or after the expected date and both after lock time
- source paths are repo-relative and cannot reference private raw/broker paths
- claims must be material, decision-relevant, future-facing, falsifiable, and
  deterministically resolvable
- tautological, already-known, unfalsifiable, or purely narrative claims fail
- no broker, order, transaction, or execution fields are part of the schema

## Canonical serialization and hash chain

Hashing excludes `record_hash` itself and includes an explicit
`HASH_SCHEMA_VERSION`. Native numeric floats are not accepted for persisted
probabilities, thresholds, or tolerance. Values are normalized before sorted,
compact, ASCII JSON serialization.

The chain stores `previous_record_hash`; the first row uses the contract-defined
genesis marker. The chain is tamper-evident, not tamper-proof. Changing
canonicalization rules requires a new hash schema version.

## Selection-bias diagnostics

The 2-5 rule does not impose a probability mix per decision. Dataset reports
monitor probability bins, share above 0.90, share between 0.35 and 0.75, and
claim-type distribution. `TRIGGER_DESIGN_REVIEW` requests human review; it never
creates artificial 50% counterclaims.

## Resolution and due-review contract

Confirmed resolutions are appended to
`data/processed/personal_trigger_resolutions.csv`. Every row contains
`trigger_id`, `resolution_status`, `resolved_value`, `resolution_date`,
`resolution_source`, `resolution_evidence_path`, `resolution_reason`,
`created_at`, `hash_schema_version`, `record_hash`, and
`previous_record_hash`.

Only `RESOLVED_TRUE`, `RESOLVED_FALSE`, `UNRESOLVABLE_DEFINITION`, and
`UNRESOLVABLE_CORPORATE` are final states. `OVERDUE` is never persisted as a
resolution. It is derived when the scan date is later than the locked deadline
and no final resolution exists. Binary resolutions require a repo-relative
evidence path; unresolvable states store `resolved_value=NOT_APPLICABLE`.

`python -m src.personal_trigger_resolution scan-due --as-of-date YYYY-MM-DD`
writes the replaceable `data/processed/personal_due_trigger_review.csv`. The
scan neither calls an LLM nor changes a trigger or resolution ledger. Its input
does not include holdings or watchlist state, so a sale, removal, or later
decision change cannot censor an open trigger. Only an explicit human-operated
`confirm` command appends a canonical resolution.
