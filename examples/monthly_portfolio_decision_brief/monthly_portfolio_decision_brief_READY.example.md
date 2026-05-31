# Monthly Portfolio Decision Brief - READY Synthetic Example

This is a synthetic and sanitized reviewer-facing example. It is not a generated
real portfolio output and does not represent private holdings, account values,
operator decisions, broker exports, provider files, raw data, credentials or
local paths.

- as_of_date: `2026-05-30`
- generated_at_utc: `2026-05-30T00:00:00Z`
- decision_brief_status: `READY`
- source_module: `src.monthly_portfolio_decision_brief`

## Input Artifact Status

| Artifact | Status | Exists | Source stage | Path | Reason |
| --- | --- | --- | --- | --- | --- |
| `monthly_ranking` | `AVAILABLE` | `true` | `monthly` | `examples/monthly_portfolio_decision_brief/synthetic_inputs/monthly_ranking_READY.csv` | `SYNTHETIC_EXAMPLE_AVAILABLE` |
| `data_freshness_summary` | `AVAILABLE` | `true` | `data_freshness` | `examples/monthly_portfolio_decision_brief/synthetic_inputs/data_freshness_READY.json` | `SYNTHETIC_EXAMPLE_AVAILABLE` |

## Portfolio Decision Readiness

- decision_brief_status: `READY`
- conservative_rule: `Missing mandatory inputs result in BLOCKED; degraded or missing review evidence results in REVIEW.`

## Ranking Summary

| Rank | Ticker | Target action | Allocation status | Amount EUR | Execution mode | Execution reason | Rationale |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| 1 | `SYNTH_QUALITY_A` | `REVIEW_ONLY` | `SELECTED_FOR_REVIEW` | 0 | `SAVINGS_PLAN_EXISTING` | `synthetic_existing_plan_review_only` | Synthetic upstream ranking evidence preserved for review. |
| 2 | `SYNTH_DIVIDEND_B` | `REVIEW_ONLY` | `WATCHLIST_REVIEW` | 0 | `NOT_APPLICABLE` | `synthetic_non_actionable_watchlist_row` | Synthetic secondary candidate for surface inspection. |

## Data Freshness Summary

- artifact_status: `AVAILABLE`
- overall_status: `FRESH`
- review_required: `false`
- degraded_state_indicators: `None`

| Freshness status | Count |
| --- | ---: |
| `FRESH` | 3 |
| `STALE` | 0 |
| `MISSING` | 0 |
| `UNKNOWN` | 0 |
| `REVIEW_REQUIRED` | 0 |
| `NOT_APPLICABLE` | 0 |

## Decision Quality Summary

- artifact_status: `AVAILABLE`
- decision_confidence_level: `MEDIUM`
- process_confidence_not_investment_confidence: `true`
- review_required: `false`

## Explicit Non-Claims

- no order execution
- no buy/sell automation
- no investment advice
- no valuation automation
- no scoring formula change
- no ranking formula change
- no portfolio rule change
- no broker/provider/API integration
- no replay/backtesting/outcome attribution

Operator acceptance boundary: Human Operator remains final acceptance authority.
