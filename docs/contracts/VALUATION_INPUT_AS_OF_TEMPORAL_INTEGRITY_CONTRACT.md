# Valuation Input As-Of Temporal Integrity Contract

## Purpose

This contract defines a read-only temporal integrity review for valuation inputs
before any future valuation automation. It checks whether valuation source dates
and review dates are parseable, ordered and compatible with an explicit run
`as_of_date`.

This contract complements
`docs/contracts/VALUATION_INPUT_PROVENANCE_AND_CONFLICT_CONTRACT.md` and
`docs/contracts/VALUATION_ENGINE_BOUNDARY_CONTRACT.md`. It does not change
valuation formulas and does not feed reviewed values into `src.valuation_engine`.

## Non-Scope

This contract and its producer do not implement:

- valuation automation;
- new valuation methodology;
- DCF engine;
- analyst target price ingestion;
- provider/API integration;
- scraping or web crawling;
- broker import;
- order execution;
- Buy/Sell recommendation changes;
- scoring or ranking changes;
- replay, backtesting or outcome attribution;
- dashboard expansion;
- tax calculation;
- legal or commercial approval;
- runtime enforcement;
- product, production or investment readiness.

## Input Boundary

The temporal review may read:

- `data/processed/personal_valuation_input_review_queue.csv`;
- optional `data/raw/private/fundamentals/personal_valuation_review_input.csv`;
- optional `data/processed/personal_valuation_input_provenance_review.csv`;
- optional `data/processed/personal_fundamentals_master_evidence_applied.csv`.

Missing optional inputs must not crash the producer. Missing temporal evidence
must remain visible and must not be imputed.

## Temporal Rules

- All checks use an explicit injected run `as_of_date`.
- Tests must not depend on the wall-clock date.
- `valuation_source_as_of_date` must be parseable when present.
- `valuation_source_as_of_date` must not be after the run `as_of_date`.
- `valuation_reviewed_at` must be parseable when present.
- `valuation_reviewed_at` must not be after the run `as_of_date`.
- `valuation_reviewed_at` must not be before `valuation_source_as_of_date`
  when both are present.
- Missing temporal evidence remains visible.
- Invalid temporal evidence remains visible.
- Non-STANDARD rows remain `NOT_APPLICABLE`.
- Existing `MISSING`, `INVALID`, `REVIEW`, `CONFLICT` or `STALE` upstream
  provenance states must not be silently upgraded to `OK`.

## Output Boundary

The producer writes deterministic evidence artifacts only:

- `data/processed/personal_valuation_input_temporal_integrity_review.csv`;
- `data/processed/personal_valuation_input_temporal_integrity_summary.csv`;
- `reports/<as_of_date>/personal_valuation_input_temporal_integrity_review.md`.

It does not mutate valuation inputs and does not feed values into
`src.valuation_engine`.

## Missing / Invalid Semantics

Missing source dates, missing review dates, invalid date strings, future dates
and inconsistent date ordering must remain visible. The producer emits explicit
reason codes and confirms no imputation. It must never infer temporal validity
from file presence alone.

## Promotion Requirement

Before any future valuation automation, CIOS requires accepted temporal
integrity review, provenance/conflict review, semantic decision quality review,
adversarial input review, operator wording boundaries and Human Operator
acceptance.

## Explicit Non-Claims

This contract does not provide investment advice, valuation automation, order
execution, production readiness, product readiness or investment readiness.
