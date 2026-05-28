# Valuation Engine Boundary Contract

## Purpose

This contract defines the current boundary of `src.valuation_engine`.
The valuation engine is deterministic decision-support logic. It computes
bounded valuation component scores and a heuristic `fair_value_estimate` from
provided inputs.

The engine is not a valuation automation system. Its outputs are evidence for
the Human Operator and downstream deterministic scoring surfaces, not
investment advice and not automatic acceptance of any decision.

## Scope

The current engine:

- reads already-provided valuation inputs from row dictionaries;
- reads committed scoring weights from `configs/scoring_weights.yaml`;
- computes relative score components for historical multiples, normalized FCF
  yield and dividend yield;
- computes a bounded `fair_value_score`;
- computes a heuristic `fair_value_estimate`;
- computes `margin_of_safety_pct`;
- returns data-quality and comment fields that keep missing or degraded inputs
  visible.

## Non-Scope

The valuation engine does not:

- fetch data;
- scrape, crawl or call APIs;
- ingest analyst target prices;
- implement a DCF engine;
- validate legal or commercial data licensing;
- decide whether to buy, sell, hold, trim or rebalance;
- provide buy/sell recommendation changes;
- provide no investment advice;
- provide no order execution;
- claim no valuation automation;
- claim no product, production or investment readiness.

## Input Boundary

Inputs are caller-provided row values and a local scoring-weight config.
The engine treats absent, blank, zero or non-numeric valuation inputs as invalid
for the relevant component. It does not infer missing valuation values from
other data and does not repair source rows.

`current_price_eur <= 0` or invalid valuation inputs must not crash the system.
The output must still contain the expected valuation keys and conservative
fallback evidence.

## Output Boundary

Outputs are deterministic metrics only:

- component scores;
- `fair_value_score`;
- `fair_value_estimate`;
- `margin_of_safety_pct`;
- relative ratio diagnostics;
- `data_quality_flag`;
- `valuation_comment`.

These outputs are not Human Operator acceptance, not release acceptance and not
investment readiness.

## Missing/Invalid Data Semantics

Missing, stale and unknown inputs must remain visible to reviewers and the
Human Operator. Fallback scores are conservative explicit fallbacks, not silent
truth and not silent imputation.

Data quality flags must remain visible and must not be silently upgraded:

- materially missing valuation inputs must become or remain `MISSING_DATA`;
- partially missing valuation inputs must become or remain `REVIEW`;
- an incoming `REVIEW` or `MISSING_DATA` flag must not be silently upgraded to
  `OK` by the valuation engine.

## Behavioral Invariants

- Scores are clamped to the configured `0..100` score range.
- Invalid relative-score inputs return the explicit fallback-like score `35.0`
  and `ok == False`.
- Invalid fair-value-ratio inputs return `None` and `ok == False`.
- Invalid diagnostic ratios return `0.0`.
- Missing component inputs use explicit fallback scores.
- Current price values that are zero, negative or invalid do not raise
  exceptions.
- The engine does not write files and does not mutate source inputs.
- Missing, stale, unknown, failed or not-applicable states must not be hidden by
  generated comments or downstream wording.

## Review/Promotion Requirements

Any future methodology change requires
`docs/contracts/VALUATION_METHODOLOGY_BOUNDARY_CONTRACT.md` plus a later
explicit methodology implementation contract and review. Before any valuation
automation, the project must complete the relevant review gates for semantic
decision quality, as-of temporal integrity, data conflict and provenance,
operator wording and Human Operator acceptance.

Valuation input temporal integrity review remains outside `src.valuation_engine`
and must not feed reviewed values into the engine.

Any future runtime-relevant valuation gate would require its own contract,
tests, evidence artifacts, failure semantics, operator override semantics and
rollback or correction path under
`docs/contracts/RUNTIME_GATE_BOUNDARY_CONTRACT.md`.

## Explicit Non-Claims

This contract does not implement:

- valuation automation;
- investment readiness;
- production readiness;
- product readiness;
- investment advice;
- order execution;
- broker import;
- provider or API integration;
- scraping or crawling;
- replay, backtesting or outcome attribution;
- dashboard expansion;
- tax, legal or commercial approval;
- runtime enforcement.
