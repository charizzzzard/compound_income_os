# Data Freshness / Staleness Contract

## Purpose

This contract defines how Compound Income OS records and reviews data freshness,
staleness, missing freshness signals, and review-required freshness states.

The contract is a governance and operator-readiness contract. It does not claim
that current local data is fresh unless a runtime producer can prove it from
explicit evidence. Runtime source of truth is the implementing producer and its
generated artifacts; this document defines the expected semantics.

This contract prepares later dashboard, replay, and outcome-attribution work. It
does not implement replay, historical point-in-time reconstruction, portfolio
event ledger logic, performance-cause attribution, tax quantification, broker
writes, or investment decisions.

## Status Vocabulary

Only these freshness status values are allowed:

| status | meaning |
|---|---|
| `FRESH` | Freshness is supported by a reliable explicit signal and is inside the configured fresh window. |
| `STALE` | Data exists and has a reliable explicit signal, but exceeds the configured threshold. |
| `MISSING` | An expected artifact or input is absent. |
| `UNKNOWN` | The artifact exists, but no reliable freshness signal is available. |
| `REVIEW_REQUIRED` | The state requires human review and must not be interpreted as an investment action. |
| `NOT_APPLICABLE` | The data class is outside the current run or scope. |

`UNKNOWN`, `MISSING`, `STALE`, and `REVIEW_REQUIRED` must never be rendered as
`FRESH` or dashboard pass states.

## Data Classes

The initial data classes are limited to repo-evidenced artifacts, modules, and
contracts:

| data_class | typical source_path | purpose |
|---|---|---|
| `portfolio_snapshot` | `data/processed/personal_positions_snapshot.csv` | Holdings / portfolio base state. |
| `cash_savings_plan_inputs` | `data/raw/savings_plan_registry.csv` | Cash and savings-plan routing inputs. |
| `fundamentals_master` | `data/raw/personal_fundamentals_master.csv` | Manual or imported fundamentals master data. |
| `fundamentals_evidence_registry` | `data/processed/personal_fundamentals_evidence_registry.csv` | SEC/evidence registry state. |
| `evidence_applied_fundamentals` | `data/processed/personal_fundamentals_master_evidence_applied.csv` | Fundamentals after evidence application. |
| `watchlist_ranking_inputs` | `data/processed/personal_watchlist_ranked.csv` | Watchlist / ranking input surface. |
| `coverage_outputs` | `data/processed/personal_fundamentals_coverage.csv` | KPI / evidence coverage output. |
| `monthly_decision_report_inputs` | `data/processed/personal_monthly_buy_ranking.csv` | Monthly decision-support ranking inputs. |
| `decision_journal` | `data/processed/personal_decision_state_capture.csv` | Decision journal input for validation. |
| `review_queue` | `data/processed/decision_review_queue.csv` | Review queue output. |
| `decision_quality_state` | `data/processed/decision_quality_state.json` | Decision Quality State output. |
| `dashboard_operator_summary_inputs` | `data/processed/review_queue_summary.json` | Dashboard operator summary input. |
| `benchmark_performance_artifacts` | `data/processed/performance_summary.csv` | Benchmark / performance artifacts, where present. |
| `cost_tax_artifacts` | `data/processed/cost_tax_summary.csv` | Cost/tax review-data artifacts, where present. |

New data classes require a contract update and tests. A missing external/private
handoff artifact must not be used to infer freshness.

## Freshness Signals

Allowed freshness signals are:

- explicit `as_of_date`
- explicit `data_date`
- explicit class-specific fields such as `source_as_of_date`, `portfolio_date`,
  `ranking_date`, `period_end`, or `benchmark_reference_end_date`
- manifest or run timestamp fields when the artifact contract documents them
- report timestamp fields when the report contract documents them
- artifact lineage metadata from `personal_run_manifest.json`,
  `personal_run_artifacts.csv`, or `personal_run_used_inputs.csv`
- file modified time only when explicitly documented as a weaker signal

The current MVP producer does not treat file modified time as sufficient evidence
for `FRESH`. If no reliable explicit signal exists, the status is `UNKNOWN`.

The contract forbids these shortcuts:

- no implicit trust in filenames
- no implicit trust in file existence alone
- no silent conversion from `UNKNOWN` to `FRESH`
- no freshness inference from excluded private/raw handoff artifacts
- no hidden data enrichment

## Threshold Semantics

Thresholds are explicit, deterministic, and reviewable. The default threshold
configuration is `configs/data_freshness_thresholds.yaml`.

For each data class the threshold configuration must define:

- source path
- accepted freshness date fields
- threshold days
- missing behavior
- unknown behavior
- review escalation flags
- dashboard blocking behavior
- replay blocking behavior
- outcome-attribution blocking behavior

Malformed threshold configuration must fail fast or become review-required. It
must never silently produce `FRESH`.

The initial thresholds are governance defaults, not investment risk rules. They
may be tightened by later review, but stale state is always a process freshness
signal and not an automatic buy/sell/order signal.

## Output Contract

When a summary is generated, the JSON output must contain stable fields:

Top-level fields:

- `generated_at_utc`
- `contract_version`
- `overall_status`
- `review_required`
- `summary_counts`
- `items`

Per item:

- `data_class`
- `source_path`
- `freshness_status`
- `age_days`
- `as_of_date`
- `threshold_days`
- `evidence_source`
- `reason`
- `blocks_dashboard`
- `blocks_replay`
- `blocks_outcome_attribution`
- `review_required`

Rules:

- All fields must be deterministic and testable.
- Unknown data must be `UNKNOWN` or `MISSING`, not `FRESH`.
- `overall_status` may be `FRESH` only when every relevant item is `FRESH` or
  `NOT_APPLICABLE`.
- `REVIEW_REQUIRED`, `STALE`, `UNKNOWN`, and `MISSING` must stay visible in
  dashboard/operator surfaces.

## Markdown Summary

If generated, the Markdown summary must include:

- short overall status
- table per data class
- review-required notes
- dashboard / replay / outcome-attribution blockers
- explicit non-scope note

It must not include investment recommendations or inferred data quality claims.

## Dashboard / Operator Semantics

Freshness is a governance and operator-attention signal:

- `FRESH` may be displayed only when proven.
- `STALE`, `UNKNOWN`, and `MISSING` must not increase decision confidence.
- Operator Summary may include freshness as process state, not as investment
  instruction.
- Review Queue may use stale inputs as a review reason, but must not force a
  buy/sell decision.
- Dashboard surfaces must not render missing freshness as `PASS`.

## Replay / Outcome Boundary

This contract is a prerequisite for replay and outcome attribution. It does not:

- implement replay
- reconstruct historical point-in-time state
- create a portfolio event ledger
- calculate outcome attribution
- calculate tax effects
- run simulation, backtesting, or Monte Carlo

## Non-Scope

- no broker/order/trading
- no score formula change
- no portfolio rule change
- no silent data enrichment
- no simulation/backtesting
- no outcome attribution
- no runtime LLM decisioning
- no tax quantification
- no portfolio event ledger
- no private raw data

