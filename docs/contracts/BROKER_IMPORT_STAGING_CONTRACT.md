# Broker Import Staging Contract

## Purpose

Broker Import Staging is the pre-runtime boundary between raw broker or document
parsing and any future accepted Portfolio Event Ledger event.

It exists to keep source rows, parser uncertainty, instrument-match uncertainty
and operator-review state visible before any event is promoted. It does not
create an Event Ledger, a broker-import runtime, a parser integration or a
portfolio-state update.

## Source-Of-Truth Role

The staging layer is review evidence only. It may hold normalized candidates
derived from a broker export, broker document, manual operator row or sanitized
test fixture, but it is not the source of truth for portfolio state.

Future accepted portfolio events may only be created by a separately reviewed
promotion path into the Portfolio Event Ledger. That path does not exist in this
contract.

## Allowed Inputs

- sanitized synthetic fixtures;
- explicit operator-supplied local broker/document extracts for private local
  validation only;
- committed template metadata;
- source/license review evidence;
- Instrument Master candidate IDs as review candidates only.

## Forbidden Inputs

- inferred private broker files;
- broker/provider API calls;
- credentials, tokens, user-agent secrets or account identifiers;
- ignored raw/provider/private files in public handoff;
- paid/raw data without source-license review;
- staging rows treated as accepted ledger events.

Private broker files are not handoff-safe by default.

## Required Staging Fields

Every future staging row must preserve these fields:

- `staging_row_id`
- `source_id`
- `source_document_ref`
- `source_row_ref`
- `broker_account_ref`
- `raw_event_type`
- `raw_asset_name`
- `raw_ticker`
- `raw_isin`
- `raw_wkn`
- `raw_currency`
- `raw_quantity`
- `raw_gross_amount`
- `raw_fee_amount`
- `raw_tax_amount`
- `trade_date`
- `settlement_date`
- `effective_date`
- `proposed_canonical_instrument_id`
- `instrument_match_status`
- `parse_status`
- `validation_status`
- `review_status`
- `review_reason_codes`
- `source_provenance`
- `created_at`

## Validation Semantics

`src.broker_import_staging_validation` is the current read-only template
preflight. It validates the local
`docs/architecture/CIOS_BROKER_IMPORT_STAGING_TEMPLATE.yaml` structure only.

The preflight must check:

- `template_only: true`;
- `TEMPLATE_ONLY` or `PREFLIGHT_ONLY` maturity;
- required field definitions;
- allowed enum values;
- unique `staging_row_id` values;
- synthetic or redacted broker/source identifiers;
- no local absolute, UNC, drive-relative, traversal, raw, private or broker
  paths in template samples;
- ambiguous, unknown or no-match instrument states remain review-required;
- proposed Instrument Master IDs are not authoritative unless the match status
  is compatible.

Passing validation does not approve broker import, production readiness,
investment readiness, public redistribution or event-ledger readiness.

## Promotion Boundary

Staging rows are candidates, not ledger facts.

Before any future promotion can create Portfolio Event Ledger events, a separate
contract must define:

- accepted source classes;
- instrument-match evidence;
- event identity rules;
- duplicate/correction/reversal handling;
- operator acceptance workflow;
- private-data and handoff boundaries;
- tests proving that rejected or review-required rows cannot update accepted
  portfolio state.

## Review-Required Conditions

Rows must remain review-required when:

- instrument identity is missing, ambiguous or conflicting;
- only ticker/name/broker label evidence is present;
- raw event type is unknown;
- dates are missing or inconsistent;
- fees, taxes, net/gross amounts or currency are unclear;
- source provenance is incomplete;
- source-license status is unknown;
- broker account or document references are not redacted/synthetic;
- any field would imply an order, accepted event or portfolio-state mutation.

## Privacy / Handoff Boundary

Public review packets may include the contract, template, validator and tests.
They must not include raw private broker files, real account IDs, real broker
document IDs, credentials, user-agent values, transactions, orders or personal
portfolio rows unless a future explicit privacy/license review approves a
sanitized artifact.

## Source / License Boundary

Broker Import Staging does not override
`docs/contracts/DATA_SOURCE_LICENSE_BOUNDARY_CONTRACT.md`. Source-license,
freshness and provenance evidence are separate controls. Freshness evidence
does not prove event correctness, and license evidence does not prove
instrument identity.

## Non-Scope

This contract does not implement or authorize:

- broker/provider/API integration;
- broker writes;
- order execution;
- live trading;
- buy/sell automation;
- investment advice automation;
- production broker import;
- a production Portfolio Event Ledger;
- event-store database or SQLite layer;
- derived positions projection;
- reconciliation producer;
- replay;
- backtesting;
- outcome attribution;
- tax advice;
- scoring, ranking, valuation, watchlist or fundamentals logic changes.

Staging rows do not update portfolio state, do not feed scoring/ranking
directly, do not feed the Monthly Portfolio Decision Brief directly and are not
order instructions.
