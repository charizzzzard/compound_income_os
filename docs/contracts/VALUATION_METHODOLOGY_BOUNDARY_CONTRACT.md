# Valuation Methodology Boundary Contract

## Purpose

This contract defines methodology boundaries before any future valuation
automation, DCF work, provider integration or valuation formula change in CIOS.
It is evidence-first, deterministic, local-first and reviewable.

The Human Operator remains final authority. This contract is governance
evidence only; it is not a runtime gate, not release acceptance and not an
investment decision.

## Current State

Current valuation outputs are heuristic supporting evidence only. Existing
surfaces such as `fair_value_estimate`, `margin_of_safety_pct`,
`fair_value_score` and `valuation_comment` are not a complete valuation
methodology and must not be interpreted as intrinsic value certainty.

Existing scoring and ranking outputs are decision-support evidence, not
investment advice, not order instructions and not automatic buy/sell decisions.
The current system can prioritize review candidates, but the Human Operator
decides whether any later action is acceptable.

## Explicit Non-Scope

This contract implements:

- no DCF engine;
- no valuation automation;
- no new valuation formula;
- no scoring formula change;
- no ranking change;
- no analyst target price ingestion;
- no provider/API integration;
- no scraping or crawling;
- no broker import;
- no order execution;
- no buy/sell automation;
- no investment advice;
- no replay/backtesting/simulation;
- no outcome attribution;
- no product readiness;
- no production readiness;
- no investment readiness.

It also does not change `src.valuation_engine`, `src.scoring_engine`,
`src.monthly_ranking_engine`, portfolio rules, operator decisions or generated
actions.

## Future Methodology Preconditions

Before any future DCF, provider, formula or automated fair-value work, CIOS
requires later explicit contracts, tests and Human Operator acceptance for:

- valuation input provenance;
- `as_of_date` / snapshot semantics;
- stale, missing, conflict, unknown and invalid data handling;
- accepted valuation methods and formulas;
- sensitivity and scenario semantics;
- confidence and uncertainty language;
- manual operator acceptance boundaries;
- report wording boundaries;
- no silent imputation;
- no silent overwrite of accepted facts;
- rollback or correction handling if a methodology is later retracted.

Missing/stale/conflicting/unknown/invalid data remains visible at every review
surface. No future methodology may silently upgrade degraded evidence to `OK`.

## Allowed Future Method Families

These families may be proposed later as future candidates only. They are not
implemented by this contract:

- historical multiple comparison;
- normalized owner earnings / FCF yield view;
- dividend yield / dividend growth support view;
- DCF as future methodology only after contract, tests, evidence and explicit
  Human Operator acceptance;
- scenario/sensitivity view as future evidence only.

Any future method family must define inputs, formulas, stale-data behavior,
uncertainty wording, report interpretation and rollback/correction semantics
before it can be used as more than review evidence.

## Prohibited Claims

Current and future valuation documents, reports and operator surfaces must not
claim or imply:

- guaranteed undervaluation;
- risk-free return;
- automatic buy/sell;
- order execution;
- investment advice;
- complete intrinsic value certainty;
- production readiness;
- investment readiness.

Terms such as fair value, margin of safety, discount, cheap, expensive or
candidate must remain bounded by evidence, uncertainty, data-quality and Human
Operator interpretation language.

## Required Operator Interpretation

Valuation and scoring outputs may support review and prioritization. Outputs
are evidence, not instructions.

The Human Operator remains final authority. The operator must be able to see
missing, stale, conflicting, unknown and invalid states before relying on a
valuation or score surface.

No silent imputation and no silent overwrite of accepted facts are allowed.
Fallback values are explicit conservative evidence, not truth and not
acceptance.
