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

## Operator-Surface Wording Hardening

Operator-facing reports may preserve internal machine fields in CSV artifacts,
but Markdown and human-readable summary surfaces must render bounded display
wording for risky internal terms:

- `BUYABLE` should display as reviewable evidence with explicit operator review,
  not as an order instruction.
- `eligible_for_purchase` should display as local screening evidence with
  operator review required.
- `valuation_comment` should display as a valuation evidence note.
- `fair_value_estimate` should display as a heuristic fair-value estimate based
  on available inputs.
- `margin_of_safety_pct` should display as an indicative field, not certainty.
- `Unterbewertung` or equivalent discount wording should display as possible
  valuation discount based on current inputs.

This hardening does not alter formulas, rankings, target actions, portfolio
rules or buy/sell logic. Degraded states such as `MISSING`, `MISSING_DATA`,
`REVIEW`, `STALE`, `CONFLICT`, `UNKNOWN` and `BLOCKED` must remain visible.

## Adversarial Input / Failure Mode Semantics

The review layer must treat malformed, conflicting, stale, unknown, invalid and
missing valuation/scoring states as review evidence. Examples include empty
numeric fields, placeholders such as `N/A` or `--`, non-numeric text,
percentage-formatted strings in unexpected surfaces, conflicting data-quality
flags and precise-looking valuation fields produced from degraded inputs.

Malformed or conflicting inputs must not be silently imputed and must not be
silently upgraded to `OK`. They should surface as `REVIEW`, `WARNING` or
`FAIL` evidence depending on whether the wording can imply advice, certainty,
automation or order readiness.

This adversarial/failure-mode review does not change valuation formulas,
scoring formulas, ranking logic, target actions or portfolio behavior. It only
emits deterministic evidence for the Human Operator and later hardening work.

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
- `docs/contracts/VALUATION_METHODOLOGY_BOUNDARY_CONTRACT.md`
- `docs/contracts/VALUATION_INPUT_PROVENANCE_AND_CONFLICT_CONTRACT.md`
- `docs/contracts/VALUATION_INPUT_AS_OF_TEMPORAL_INTEGRITY_CONTRACT.md`
- `src/personal_decision_quality_state.py`

These surfaces remain evidence and review mechanisms. They are not runtime
enforcement and not automatic release acceptance.
