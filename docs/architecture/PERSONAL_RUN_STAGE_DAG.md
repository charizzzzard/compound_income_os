# Personal Run Stage DAG

## Purpose

This document is the canonical governance and external-review map for the
current Personal Run stage graph.

It documents the observed orchestration contract in `src/personal_run_engine.py`.
It does not change execution behavior, add financial logic, authorize orders,
create a replay engine or implement a visual dashboard.

The source of truth for actual execution remains `src/personal_run_engine.py`.
If this document and code disagree, code wins until this document is updated.

## Source Of Truth

Authoritative runtime objects and outputs:

- `STAGE_ORDER` in `src/personal_run_engine.py`
- `STAGE_RUNNERS` in `src/personal_run_engine.py`
- `StageResult`
- `data/processed/personal_run_manifest.json`
- `data/processed/personal_run_artifacts.csv`
- `data/processed/personal_run_used_inputs.csv`
- `reports/<as_of_date>/personal_run_report.md`

`StageResult` records `stage_name`, `status`, `required_inputs`,
`used_inputs`, `produced_outputs`, `warnings` and `notes`.

`personal_run_manifest.json` records selected stages, executed stage order,
inputs, outputs, stage results, run status and source metadata.

`personal_run_artifacts.csv` records produced outputs from
`StageResult.produced_outputs`.

`personal_run_used_inputs.csv` records consumed inputs from
`StageResult.used_inputs`.

`personal_run_report.md` is the operator-readable run surface built from the
same stage result and artifact rows.

## Current Linear Stage Order

The current canonical stage order is:

1. `data_sources_validate`
2. `import`
3. `savings_plan`
4. `fundamentals_seed`
5. `fundamentals_profile`
6. `fundamentals_snapshot_ingest`
7. `fundamentals_snapshot_review`
8. `fundamentals_evidence_compose`
9. `fundamentals_evidence`
10. `fundamentals_evidence_apply`
11. `fundamentals_overlay`
12. `scoring`
13. `coverage`
14. `watchlist`
15. `portfolio_review`
16. `cash_refill_review`
17. `rebalance_review`
18. `monthly`
19. `decision_quality`
20. `decision_journal_validation`
21. `data_freshness`
22. `dashboard_operator_summary`
23. `monthly_portfolio_decision_brief`
24. `history`
25. `benchmark_archive`
26. `performance`
27. `multi_benchmark`
28. `cost_tax`
29. `dashboard`

The list is a linear execution order. The dependency table below makes the
review-time data dependencies explicit without changing how the engine runs.

## Dependency DAG Table

| stage_name | purpose | canonical_runner | required_upstream_stages | primary_inputs | primary_outputs | downstream_consumers | failure_behavior | review_surface | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `data_sources_validate` | Validate local personal data source registry and resolved source status. | `run_data_sources_validate_stage` | none | `configs/personal_run_data_sources.yaml` | `personal_data_source_status.csv`; `personal_data_source_registry_resolved.csv` | stages using registry-resolved defaults | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report; manifest; used-inputs index | Read-only registry validation; no secrets or API writes. |
| `import` | Normalize personal positions into processed portfolio snapshot. | `run_import_stage` | optionally `data_sources_validate` | raw or registry-resolved positions input | `personal_positions_snapshot.csv` | `scoring`; `portfolio_review`; `monthly`; reports | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report; artifact index | No broker writes; local input only. |
| `savings_plan` | Validate and route savings-plan registry context. | `run_savings_plan_stage` | optionally `data_sources_validate` | savings-plan registry config and processed context | savings-plan registry/routing artifacts | `monthly` | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report | Read-only routing support; no execution. |
| `fundamentals_seed` | Create or refresh manual fundamentals seed/template context. | `run_fundamentals_seed_stage` | optionally `data_sources_validate` | personal master or seed inputs | fundamentals seed/template artifacts | fundamentals profile and evidence stages | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report | Does not infer missing fundamentals. |
| `fundamentals_profile` | Profile personal fundamentals master for applicability and coverage. | `run_fundamentals_profile_stage` | optionally `fundamentals_seed` | personal fundamentals master; schema/profile config | profiled personal master and profile summaries | evidence, scoring and coverage stages when explicitly selected | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report | Profiled master is only used via explicit option. |
| `fundamentals_snapshot_ingest` | Ingest local external fundamentals snapshot into staging artifacts. | `run_fundamentals_snapshot_ingest_stage` | optionally `fundamentals_profile` | local snapshot CSV; personal master | normalized snapshot; unmatched rows; evidence staging | `fundamentals_snapshot_review` | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report | Exact identity matching; no web/API path. |
| `fundamentals_snapshot_review` | Validate manual review of snapshot evidence staging. | `run_fundamentals_snapshot_review_stage` | `fundamentals_snapshot_ingest` when same run uses snapshot review | snapshot staging; manual review CSV | review registry; promoted snapshot evidence; backlog; summary | `fundamentals_evidence_compose` | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report | Review only; no master writeback. |
| `fundamentals_evidence_compose` | Compose manual raw evidence and promoted snapshot evidence. | `run_fundamentals_evidence_compose_stage` | optionally `fundamentals_snapshot_review` | raw evidence CSV; promoted snapshot evidence | composed evidence; conflicts; summary | `fundamentals_evidence` when explicitly selected | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report | Conflict visibility; no raw evidence overwrite. |
| `fundamentals_evidence` | Evaluate fundamentals evidence and proposed updates. | `run_fundamentals_evidence_stage` | optionally `fundamentals_evidence_compose` | raw or composed evidence; personal master | proposed updates; evidence audit/summaries | `fundamentals_evidence_apply`; `scoring`; `coverage` | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report | Missing data remains visible; no hidden imputation. |
| `fundamentals_evidence_apply` | Project validated proposed updates into a separate applied master. | `run_fundamentals_evidence_apply_stage` | `fundamentals_evidence` when applying same-run evidence | proposed updates; base personal master | evidence-applied master; apply registry; summary | `scoring`; `coverage` when explicitly selected | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report | Separate applied master only; no raw master overwrite. |
| `fundamentals_overlay` | Validate analyst overlays and project separate applied overlay master. | `run_fundamentals_overlay_stage` | optionally fundamentals profile/evidence stages | overlay CSV; personal master; schema | overlay registry; overlay-applied master; backlog; report | `scoring`; `coverage` when explicitly selected | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report | No score formula or core KPI change. |
| `scoring` | Build company scores from positions/fundamentals/scoring configs. | `run_scoring_stage` | `import` and chosen fundamentals source when same run requires them | positions; fundamentals master mode; scoring weights | company scores; score audit | `coverage`; `watchlist`; `portfolio_review`; `monthly`; `decision_quality` | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report; score audit | No weight/formula changes by orchestration. |
| `coverage` | Build coverage and missing-data review artifacts. | `run_coverage_stage` | `scoring` or chosen fundamentals source when same run requires it | positions; scores; fundamentals coverage inputs | coverage CSV/report artifacts | reports; input closure; operator review | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report; monthly/snapshot reports | Coverage is review support, not data filling. |
| `watchlist` | Rank watchlist candidates from processed scores and rules. | `run_watchlist_stage` | `scoring` when same run builds scores | watchlist CSV; scores; rules | ranked watchlist; optional report | `monthly` | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report | Ranking support only; no order instruction. |
| `portfolio_review` | Evaluate holdings against scores and portfolio rules. | `run_portfolio_review_stage` | `import`; `scoring` when same run builds scores | positions; scores; portfolio rules | portfolio review artifacts | `monthly`; `decision_quality`; reports | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report; monthly report | Conservative review actions only. |
| `cash_refill_review` | Review cash-refill readiness from processed cash/portfolio context. | `run_cash_refill_review_stage` | optionally `import` and portfolio context stages | processed cash/portfolio inputs; thresholds | `personal_cash_refill_review.csv`; report | `decision_quality`; monthly report | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report; Decision Quality | No cash deployment instruction. |
| `rebalance_review` | Review rebalancing readiness from processed portfolio context. | `run_rebalance_review_stage` | optionally `portfolio_review` | positions; scores; portfolio rules/thresholds | `personal_rebalance_review.csv`; report | `decision_quality`; monthly report | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report; Decision Quality | No sell/order execution. |
| `monthly` | Build monthly ranking and decision-support artifacts. | `run_monthly_stage` | `import`; `scoring`; `watchlist`; `portfolio_review`; `cash_refill_review`; `rebalance_review` when selected together | positions; scores; watchlist; rules; savings-plan/routing context | monthly buy ranking; rebalance proposals; monthly report | `decision_quality`; operator reports | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Monthly Decision Report; Personal Run Report | Monthly ranking remains decision support. |
| `decision_quality` | Aggregate existing readiness/evidence/run/review artifacts into Decision Quality State. | `run_decision_quality_stage` | `monthly`; `scoring`; `cash_refill_review`; `rebalance_review`; input closure and decision capture artifacts as available | input closure; decision capture; cash/refill; rebalance; manifest; used inputs; ranking; score audit | `decision_quality_state.csv`; `decision_quality_state.json`; `decision_quality_report.md` | `decision_journal_validation`; `dashboard_operator_summary`; reports | Failure marks run `FAILED`; later requested stages are `SKIPPED`; preflight lineage is written before running. | Decision Quality Surface; Personal Run Report | Read-only process confidence; no investment confidence. |
| `decision_journal_validation` | Validate append-only decision journal and produce review queue. | `run_decision_journal_validation_stage` | `decision_quality` when selected together | decision capture journal; Decision Quality State; manifest; used inputs | `decision_journal_validation.csv`; `decision_review_queue.csv`; `decision_journal_validation_report.md` | `data_freshness`; `dashboard_operator_summary`; reports | Failure marks run `FAILED`; later requested stages are `SKIPPED`; preflight lineage is written before running. | Decision Journal Validation Surface; Review Queue | No decision creation or mutation. |
| `data_freshness` | Evaluate configured artifacts against explicit freshness/staleness thresholds. | `run_data_freshness_stage` | `decision_journal_validation` when selected together | `configs/data_freshness_thresholds.yaml`; configured repo-local artifacts; current manifest as available | `data_freshness_summary.json`; `data_freshness_summary.md` | `dashboard_operator_summary`; future dashboard surface | Failure marks run `FAILED`; later requested stages are `SKIPPED`; preflight lineage is written before running. | Data Freshness Summary; Personal Run Report via Dashboard Operator Summary | Read-only; no mtime, filename or file-existence freshness; no data enrichment. |
| `dashboard_operator_summary` | Aggregate Decision Quality, journal validation, review queue and Data Freshness into machine-readable operator summary. | `run_dashboard_operator_summary_stage` | `decision_journal_validation`; `data_freshness`; `decision_quality` when selected together | decision quality JSON; validation CSV; review queue CSV; data freshness summary; manifest; artifact index; used inputs | `review_queue_summary.json` | Personal Run Report; Monthly Portfolio Decision Brief; future dashboard surface | Failure marks run `FAILED`; later requested stages are `SKIPPED`; preflight lineage is written before running. | Dashboard Operator Summary section | Machine summary only; no visual dashboard/server. |
| `monthly_portfolio_decision_brief` | Consolidate already-generated monthly ranking, portfolio health, Data Freshness, Decision Quality and review-queue evidence into a compact operator review brief. | `run_monthly_portfolio_decision_brief_stage` | `monthly`; `cash_refill_review`; `rebalance_review`; `decision_quality`; `decision_journal_validation`; `data_freshness`; `dashboard_operator_summary` when selected together | monthly ranking; cash refill review; rebalance review; Data Freshness summary; Decision Quality state; Decision Review Queue | `monthly_portfolio_decision_brief.json`; `monthly_portfolio_decision_brief.csv`; `monthly_portfolio_decision_brief.md` | Human Operator monthly review; external review metadata when included via central handoff | Expected evidence gaps are surfaced as `BLOCKED` or `REVIEW` in the generated brief; runtime/write failures mark the stage `FAILED` and later requested stages are `SKIPPED`. | Monthly Portfolio Decision Brief; Personal Run Report section; manifest; artifact index; used-inputs index | Optional read-only stage; reuses the existing Monthly Brief producer; no score, ranking, valuation, portfolio-rule, broker/API, order or buy/sell automation changes. |
| `history` | Archive portfolio snapshots and build portfolio timeseries artifacts. | `run_history_stage` | `import` when same run builds positions | positions snapshot; existing archive | portfolio snapshot archive; portfolio timeseries; summary/report | `performance`; reports | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report | Not a full event ledger. |
| `benchmark_archive` | Archive selected benchmark timeseries and registry context. | `run_benchmark_archive_stage` | none | benchmark CSV/config | benchmark archive; registry; normalized benchmark series | `performance`; `multi_benchmark` | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report | No API/FX/interpolation layer. |
| `performance` | Compare portfolio timeseries and benchmark under explicit snapshot/history mode. | `run_performance_stage` | `history`; `benchmark_archive` when selected together | positions/portfolio timeseries; benchmark series; config | performance comparison; KPIs; report | dashboard/report surfaces | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report; performance report | Not outcome attribution. |
| `multi_benchmark` | Compare portfolio timeseries against multiple explicit benchmarks. | `run_multi_benchmark_stage` | `history`; `benchmark_archive`; `performance` context when relevant | benchmark archive/registry; portfolio timeseries; selected symbols | multi-benchmark comparison; summary; KPIs; report | dashboard/report surfaces | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report | No automatic benchmark selection. |
| `cost_tax` | Normalize and report cost/tax review data from manual/local evidence. | `run_cost_tax_stage` | none | manual ledger; optional local documents; config | normalized ledger; summary; KPIs; report/archive | dashboard/report surfaces | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Personal Run Report | No tax quantification or lot reconstruction. |
| `dashboard` | Consolidate already processed artifacts into dashboard CSVs and markdown report. | `run_dashboard_stage` | relevant processed artifacts from earlier stages when selected together | processed positions/scores/watchlist/review/performance/cost-tax artifacts | dashboard KPIs; sections; summary; universe section; report | local dashboard server/read-only UI | Failure marks run `FAILED`; later requested stages are `SKIPPED`. | Dashboard report | Consolidation only; no new financial logic. |

## Dependency Groups

### Input/Data Source Layer

- `data_sources_validate`

This layer validates local source availability and resolved defaults. It does
not fetch external data, store secrets or create personal input data.

### Import/Portfolio Base Layer

- `import`
- `savings_plan`

This layer prepares processed portfolio and savings-plan context used by later
portfolio, ranking and report stages.

### Fundamentals Evidence Layer

- `fundamentals_seed`
- `fundamentals_profile`
- `fundamentals_snapshot_ingest`
- `fundamentals_snapshot_review`
- `fundamentals_evidence_compose`
- `fundamentals_evidence`
- `fundamentals_evidence_apply`
- `fundamentals_overlay`

This layer keeps raw evidence, staging, review, apply and overlay concerns
separate. It must not silently enrich fundamentals or overwrite raw personal
masters.

### Scoring/Coverage/Watchlist Layer

- `scoring`
- `coverage`
- `watchlist`

This layer derives scores, coverage signals and watchlist ranking from existing
inputs and configs. The orchestrator does not change scoring weights or
formulas.

### Portfolio Health Layer

- `portfolio_review`
- `cash_refill_review`
- `rebalance_review`

This layer surfaces portfolio-health, cash-refill and rebalance review state. It
does not create orders or broker actions.

### Monthly Decision Support Layer

- `monthly`

This layer builds monthly decision-support artifacts and reports from processed
inputs.

### Decision Quality / Journal Governance Layer

- `decision_quality`
- `decision_journal_validation`
- `data_freshness`

This layer turns existing artifacts into process-confidence, validation and
review-queue and freshness state. It does not create new decisions, mutate the
journal, infer freshness from file existence or attribute outcomes.

### Operator Summary Layer

- `dashboard_operator_summary`

This layer produces `review_queue_summary.json` for future dashboard/operator
surfaces from Decision Quality, journal validation, review queue and Data
Freshness state. It is machine-readable governance state, not a visual
dashboard.

### History/Performance/Benchmark Layer

- `history`
- `benchmark_archive`
- `performance`
- `multi_benchmark`

This layer archives snapshots and compares explicit timeseries/benchmark inputs.
It is not time-aware replay and not outcome attribution.

### Cost/Tax Review Data Layer

- `cost_tax`

This layer normalizes cost/tax review data where explicitly provided. It does
not quantify tax consequences or reconstruct lots.

### Dashboard Surface Layer

- `dashboard`

This layer consolidates already processed artifacts into dashboard outputs. It
does not compute new investment decisions.

## Failure And Skip Semantics

Current orchestrator semantics:

- Stages not selected by `--stage` are recorded as `NOT_REQUESTED`.
- If an executed stage raises an exception, that stage is recorded as `FAILED`.
- After a failed requested stage, later requested stages are recorded as
  `SKIPPED`.
- `run_status=FAILED` when any requested stage fails.
- `RuntimeError` is raised again after final run outputs are finalized.
- Manifest, artifact index, used-inputs index and run report are written as far
  as possible in failure cases.
- `decision_quality`, `decision_journal_validation`, `data_freshness` and
  `dashboard_operator_summary` write provisional lineage before execution so
  the producers can inspect a current manifest/used-input context.

These semantics are governance-critical because failed and skipped stages must
remain visible to external review and future dashboard surfaces.

## Artifact Lineage

`StageResult.produced_outputs` is converted into `personal_run_artifacts.csv`
rows with:

- `artifact_role`
- `artifact_path`
- `stage_name`
- `produced`
- `notes`

`StageResult.used_inputs` is converted into `personal_run_used_inputs.csv` rows
with:

- `stage_name`
- `stage_status`
- `input_role`
- `input_path`
- `input_exists`
- `notes`

`personal_run_manifest.json` preserves selected stages, executed stage order,
input snapshot, output paths, stage results, warnings, source metadata and run
status.

Paths in manifest, artifact index, used-inputs index and report surfaces should
remain repo-relative and reviewable. Private/raw local paths must not be exposed
in external handoffs.

## Dashboard And Operator Blockers

This Stage-DAG reduces dashboard readiness risk by making the orchestration
order, producer placement and review surfaces explicit.

It does not make the project ready for a full visual dashboard, replay, outcome
attribution, backtesting, Monte Carlo, a Portfolio Event Ledger or broker/order
execution.

The DAG prepares these areas by documenting stage boundaries and lineage
surfaces. The Data Freshness/Staleness Contract and `data_freshness` stage now
make stale, missing and unknown data states visible to the operator summary, but
they do not replace the Dashboard Operator Surface Contract, Review Queue
Summary Contract, Replay Contract or Event Ledger design.

## Invariants And Non-Scope

The Personal Run Orchestrator remains read-only decision support, deterministic
local execution, explicit stage execution only, human-final-decision and local
artifact based.

It must not introduce broker writes, order execution, auto-trading, runtime LLM
decisions, hidden data imputation, score formula changes, portfolio rule
changes, simulation, backtesting, Monte Carlo, outcome attribution, Portfolio
Event Ledger behavior, tax quantification or private/raw data in external
handoffs.

## Maintenance Rules

Update this document whenever any of these change:

- `STAGE_ORDER`
- `STAGE_RUNNERS`
- a new stage is added
- a stage is removed
- stage inputs or outputs change
- failure/skip/finalization semantics change
- `StageResult` lineage semantics change
- `personal_run_manifest.json` schema changes
- `personal_run_artifacts.csv` schema changes
- `personal_run_used_inputs.csv` schema changes
- Operator Summary or Dashboard Surface inputs change
- Decision Quality integration changes
- Decision Journal Validation integration changes
- Data Freshness integration changes

If a future patch introduces a true data-dependency executor rather than the
current linear order, that patch must update this document and the related
tests in the same commit.
