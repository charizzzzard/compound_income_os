# Monthly Portfolio Decision Brief - BLOCKED Synthetic Example

This is a synthetic and sanitized reviewer-facing example. It is not a generated
real portfolio output and does not represent private holdings, account values,
operator decisions, broker exports, provider files, raw data, credentials or
local paths.

- as_of_date: `2026-05-30`
- generated_at_utc: `2026-05-30T00:00:00Z`
- decision_brief_status: `BLOCKED`
- source_module: `src.monthly_portfolio_decision_brief`

## Input Artifact Status

| Artifact | Status | Exists | Source stage | Path | Reason |
| --- | --- | --- | --- | --- | --- |
| `monthly_ranking` | `MISSING` | `false` | `monthly` | `examples/monthly_portfolio_decision_brief/synthetic_inputs/monthly_ranking_BLOCKED.csv` | `SYNTHETIC_EXAMPLE_MANDATORY_INPUT_MISSING` |

## Portfolio Decision Readiness

- decision_brief_status: `BLOCKED`
- reason: `Mandatory monthly ranking evidence is missing.`
- conservative_rule: `Missing mandatory inputs result in BLOCKED; degraded or missing review evidence results in REVIEW.`

## Ranking Summary

| Rank | Ticker | Target action | Allocation status | Amount EUR | Rationale |
| --- | --- | --- | --- | ---: | --- |
|  | `NOT_AVAILABLE` | `MISSING` | `MISSING` |  | Mandatory monthly ranking evidence is missing; no candidate rows are inferred. |

## Data Freshness Summary

- artifact_status: `NOT_AVAILABLE`
- overall_status: `NOT_AVAILABLE`
- review_required: `false`
- degraded_state_indicators: `None`

## Decision Quality Summary

- artifact_status: `NOT_AVAILABLE`
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
