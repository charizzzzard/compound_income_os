# Monthly Portfolio Decision Brief - REVIEW Synthetic Example

This is a synthetic and sanitized reviewer-facing example. It is not a generated
real portfolio output and does not represent private holdings, account values,
operator decisions, broker exports, provider files, raw data, credentials or
local paths.

- as_of_date: `2026-05-30`
- generated_at_utc: `2026-05-30T00:00:00Z`
- decision_brief_status: `REVIEW`
- source_module: `src.monthly_portfolio_decision_brief`

## Input Artifact Status

| Artifact | Status | Exists | Source stage | Path | Reason |
| --- | --- | --- | --- | --- | --- |
| `monthly_ranking` | `AVAILABLE` | `true` | `monthly` | `examples/monthly_portfolio_decision_brief/synthetic_inputs/monthly_ranking_REVIEW.csv` | `SYNTHETIC_EXAMPLE_AVAILABLE` |
| `decision_quality_state` | `MISSING` | `false` | `decision_quality` | `examples/monthly_portfolio_decision_brief/synthetic_inputs/decision_quality_REVIEW.json` | `SYNTHETIC_EXAMPLE_MISSING` |
| `decision_review_queue` | `NOT_AVAILABLE` | `false` | `decision_journal_validation` | `examples/monthly_portfolio_decision_brief/synthetic_inputs/review_queue_REVIEW.csv` | `SYNTHETIC_EXAMPLE_NOT_AVAILABLE` |

## Portfolio Decision Readiness

- decision_brief_status: `REVIEW`
- conservative_rule: `Missing mandatory inputs result in BLOCKED; degraded or missing review evidence results in REVIEW.`

## Ranking Summary

| Rank | Ticker | Target action | Allocation status | Amount EUR | Rationale |
| --- | --- | --- | --- | ---: | --- |
| 1 | `SYNTH_REVIEW_C` | `REVIEW_ONLY` | `REVIEW_REQUIRED` | 0 | Synthetic upstream ranking evidence preserved while optional evidence is degraded. |

## Data Freshness Summary

- artifact_status: `AVAILABLE`
- overall_status: `REVIEW_REQUIRED`
- review_required: `true`
- degraded_state_indicators: `STALE ;MISSING ;UNKNOWN ;REVIEW_REQUIRED`
- visible_optional_states: `MISSING ;STALE ;UNKNOWN ;REVIEW_REQUIRED ;NOT_AVAILABLE ;NOT_APPLICABLE`

## Decision Quality Summary

- artifact_status: `MISSING`
- decision_confidence_level: `NOT_AVAILABLE`
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
