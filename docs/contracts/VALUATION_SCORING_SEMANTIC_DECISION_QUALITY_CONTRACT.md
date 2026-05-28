# Valuation / Scoring Semantic Decision Quality Contract

## Purpose

This contract defines a deterministic, read-only semantic review layer for
valuation and scoring outputs before any future valuation automation, scoring
formula change, DCF methodology, provider ingestion, simulation, backtesting or
buy/sell automation.

The review checks wording, labels, comments, operator-facing fields and
failure-mode semantics. It emits evidence and review findings only.

## Scope

The review may inspect committed source, documentation and configuration
artifacts that expose valuation, scoring, monthly ranking or decision-quality
wording. Current primary surfaces include:

- `docs/contracts/VALUATION_ENGINE_BOUNDARY_CONTRACT.md`
- `src/valuation_engine.py`
- `src/scoring_engine.py`
- `src/monthly_ranking_engine.py`
- `src/build_monthly_decision_report.py`
- `src/personal_decision_quality_state.py`

## Non-Scope

This contract and its producer do not implement:

- valuation automation;
- new valuation methodology;
- DCF engine;
- analyst target price ingestion;
- provider/API integration;
- scraping or crawling;
- broker import;
- order execution;
- Buy/Sell recommendation changes;
- scoring formula changes;
- ranking changes;
- portfolio event ledger runtime;
- replay, backtesting or simulation;
- outcome attribution;
- dashboard expansion;
- tax, legal or commercial approval;
- runtime enforcement;
- runtime LLM decisioning;
- product, production or investment readiness.

## Input Boundary

Inputs are committed local files only. The review must not require private raw
files, broker/provider files, network access or `.git` context.

Missing input artifacts must be surfaced as visible review findings. They must
not be silently ignored.

## Output Boundary

The producer writes deterministic evidence artifacts only:

- `data/processed/valuation_scoring_semantic_decision_quality_review.csv`
- `data/processed/valuation_scoring_semantic_decision_quality_review.json`
- `reports/<as_of_date>/valuation_scoring_semantic_decision_quality_review.md`

The review does not alter valuation/scoring outputs. It does not feed any
values into `src/valuation_engine.py`. It does not alter
`src/scoring_engine.py` formulas. It does not decide whether to buy, sell,
hold, trim or rebalance.

## Required Checked Terms

The review must check current valuation/scoring terminology and operator
surfaces, including where present:

- `BUYABLE`
- `TOO_EXPENSIVE`
- `REVIEW`
- `BLOCKED`
- `eligible_for_purchase`
- `fair_value_estimate`
- `margin_of_safety_pct`
- `fair_value_score`
- `valuation_score`
- `valuation_comment`
- hybrid Fair Value / hybride Fair-Value-Sicht
- Unterbewertung
- estimated fair value / geschaetzter Fair Value
- `decision_confidence_level`
- `review_required`

## Semantic Risk Categories

Allowed semantic categories are:

- `ADVICE_RISK`
- `AUTOMATION_RISK`
- `CERTAINTY_RISK`
- `LABEL_AMBIGUITY`
- `FAILURE_MODE_VISIBILITY`
- `DATA_QUALITY_MASKING`
- `OPERATOR_BOUNDARY`
- `NON_SCOPE_ALIGNMENT`

## Severity Levels

Allowed severity values are:

- `P0`: must fix before acceptance of the semantic review surface
- `P1`: must fix before valuation automation, formula changes or runtime-sensitive work
- `P2`: should fix before broader operator-surface expansion
- `INFO`: non-blocking evidence

Allowed status values are:

- `OK`
- `REVIEW`
- `WARNING`
- `FAIL`
- `NOT_APPLICABLE`

## Deterministic Rule Semantics

Rules are static and deterministic. No wall-clock time, network call, LLM call
or private input may affect a finding.

- Terms implying order readiness or automatic action are `FAIL`.
- Risky operator-facing labels are at least `REVIEW` unless bounded by clear
  wording.
- Technical fields that can imply certainty, such as `fair_value_estimate` or
  `margin_of_safety_pct`, are review surfaces even when current behavior is
  deterministic.
- Missing, stale, conflict, unknown and review states must remain visible.
- Positive valuation or scoring wording must not mask degraded data quality.

## Operator Interpretation Boundary

Operator-facing wording must not imply advice, certainty, automation,
guarantee, order readiness or investment readiness.

The Human Operator remains final acceptance authority. PASS/OK evidence from
this review is not release acceptance, not investment advice and not product or
production readiness.

## No-Investment-Advice Boundary

The review may flag terms such as `BUYABLE`, `BUY_CANDIDATE`, `TOP_UP`,
`TOO_EXPENSIVE`, `Unterbewertung`, `fair_value_estimate` or
`margin_of_safety_pct` as semantic review surfaces. It must not reinterpret
them as investment advice and must not change the underlying behavior.

## No-Automation Boundary

The review does not automate decisions and does not enable orders. Any future
automation would require separate accepted contracts, tests, evidence artifacts,
operator wording boundaries, runtime semantics and explicit Human Operator
acceptance.

## Missing / Stale / Conflict Visibility Requirements

Missing, stale, unknown, conflict, invalid, blocked and review states must
remain visible. They must not be hidden by positive scoring labels, valuation
comments, ranking fields or report summaries.

## Related Contracts and Modules

- `docs/contracts/VALUATION_ENGINE_BOUNDARY_CONTRACT.md`
- `docs/contracts/VALUATION_INPUT_PROVENANCE_AND_CONFLICT_CONTRACT.md`
- `docs/contracts/VALUATION_INPUT_AS_OF_TEMPORAL_INTEGRITY_CONTRACT.md`
- `src/personal_decision_quality_state.py`

These surfaces remain evidence and review mechanisms. They are not runtime
enforcement and not automatic release acceptance.
