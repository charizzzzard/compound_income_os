# Valuation Input Provenance And Conflict Contract

## Purpose

This contract defines a read-only review layer for valuation input provenance,
source metadata, conflicts, freshness/as-of gaps and review status before any
future valuation automation.

It complements `docs/contracts/VALUATION_ENGINE_BOUNDARY_CONTRACT.md`. It does
not change valuation formulas and does not feed reviewed values into
`src.valuation_engine`.

## Scope

The provenance review may read:

- `data/processed/personal_valuation_input_review_queue.csv`;
- optional private reviewed valuation input at
  `data/raw/private/fundamentals/personal_valuation_review_input.csv`;
- optional evidence-applied master metadata when present.

The review writes deterministic CSV and Markdown evidence artifacts that make
`OK`, `REVIEW`, `MISSING`, `INVALID`, `CONFLICT`, `STALE` and
`NOT_APPLICABLE` states visible.

## Non-Scope

This contract does not implement:

- valuation automation;
- new valuation methodology;
- DCF engine;
- analyst target price ingestion;
- automatic fair-value ingestion;
- provider, API, scraping or crawling integration;
- broker import;
- order execution;
- buy/sell recommendation changes;
- portfolio event ledger runtime;
- replay, backtesting or simulation;
- outcome attribution;
- dashboard expansion;
- tax, legal or commercial approval;
- runtime enforcement;
- product, production or investment readiness.

## Input Boundary

Inputs are existing local CSV artifacts. Missing optional inputs must not crash
the producer. Missing private review input and missing optional evidence input
must be reported explicitly.

The private review input schema follows the current valuation input contract
fields:

- `ticker`
- `isin`
- `normalized_fcf_yield_pct`
- `target_fcf_yield_pct`
- `valuation_review_status`
- `valuation_source_type`
- `valuation_source_name`
- `valuation_source_reference`
- `valuation_source_as_of_date`
- `valuation_reviewed_by`
- `valuation_reviewed_at`
- `valuation_notes`

## Output Boundary

Outputs are review evidence only:

- `personal_valuation_input_provenance_review.csv`
- `personal_valuation_input_provenance_summary.csv`
- `personal_valuation_input_provenance_review.md`

They are not Human Operator acceptance, not valuation automation, not investment
advice and not investment readiness.

## Identity Matching Rules

ISIN is the preferred valuation input identity. Ticker is used only as fallback
when ISIN is blank. Blank ISIN and blank ticker cannot establish a reliable
identity and must not be silently accepted as `OK`.

Duplicate identities in the reviewed valuation input are conflicts. Conflicts
must remain visible even when one duplicate row appears otherwise valid.

## Provenance Rules

Approved valuation inputs require:

- numeric required values;
- approved review status;
- known source type;
- non-blank source reference;
- valid source as-of date;
- source freshness inside the configured max age.

Unknown source type, missing source reference, missing source date and invalid
source date cannot be silently upgraded to `OK`.

## Conflict Rules

The review must flag:

- duplicate valuation identity;
- conflicting `normalized_fcf_yield_pct`;
- conflicting `target_fcf_yield_pct`;
- conflicting source reference;
- conflicting source as-of date;
- conflicting source type.

The producer does not resolve conflicts and does not overwrite accepted facts.

## Freshness / As-Of Rules

The review uses an explicit injected `as_of_date`; tests must not depend on the
wall-clock date. A reviewed valuation source older than `max_source_age_days`
must become `STALE` or otherwise require review. Source dates after the
effective as-of date are invalid review evidence.

Detailed ordering between run `as_of_date`, `valuation_source_as_of_date` and
`valuation_reviewed_at` is governed by
`docs/contracts/VALUATION_INPUT_AS_OF_TEMPORAL_INTEGRITY_CONTRACT.md`.

## Missing / Invalid Semantics

Missing valuation values remain `MISSING` and include `NO_IMPUTATION`. This is
an explicit no imputation guarantee.
Non-numeric values are `INVALID`. Values outside the accepted technical range
are `INVALID`. Non-STANDARD rows remain `NOT_APPLICABLE`.

No missing, stale, unknown, invalid or conflict state may be silently converted
to `OK`.

## Explicit Non-Claims

This contract and its producer do not provide investment advice, order
execution, valuation automation, investment readiness, production readiness or
product readiness.

## Promotion Requirements Before Future Valuation Automation

Before any future valuation automation, CIOS requires separate accepted reviews
for semantic decision quality, adversarial input/failure modes, data conflict
and provenance, as-of temporal integrity, operator wording boundaries and Human
Operator acceptance.
