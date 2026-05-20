# CIOS Current System Map

## Definition

Compound Income OS (CIOS) is a local-first, deterministic Investment Decision
Support System for a long-term equity portfolio. It supports human review,
evidence tracking, ranking, reporting and governance.

CIOS is not a trading bot, not a broker, not an order execution system and not
a market prediction machine. The system may surface evidence, gaps, review
states and operator actions, but the human operator remains the final decision
maker.

## Current System Capabilities

- Portfolio Inputs: read-only import and normalization of local CSV and local
  text-based broker document inputs into processed portfolio artifacts.
- Portfolio Rules: deterministic portfolio sleeve, allocation and rule-review
  helpers from configuration.
- Savings Plan Registry / Routing: manual registry validation and read-only
  routing markers for monthly candidates.
- Fundamentals / Evidence / KPI Coverage: local fundamentals master, evidence
  registry, snapshot review, evidence apply, overlay, KPI coverage and gap
  diagnostics.
- Watchlist / Scoring / Monthly Ranking: watchlist ranking, company scores,
  score audit and monthly buy ranking from existing processed inputs.
- Portfolio Health: cash refill and rebalance review artifacts without sell,
  tax or order execution.
- Decision Capture: append-only human decision or explicit no-action capture
  according to `DECISION_STATE_CAPTURE_CONTRACT_V2`.
- Decision Quality State: review/governance state from existing readiness,
  run, journal, cash/rebalance, ranking and score-audit artifacts.
- Decision Journal Validation / Review Queue: read-only validation of the
  append-only journal and deterministic operator review queue.
- Monthly Decision Report: report surface for portfolio health, decision
  quality and decision journal validation when explicit artifacts are present.
- Personal Run Engine: explicit stage orchestration with manifest, used-inputs,
  artifact index and run report.
- Handoff Governance: external review bundles with private/raw data excluded.

## Current Governance Flow

1. Raw or manually supplied input artifacts remain local and explicit.
2. Processed artifacts are generated deterministically under `data/processed/`.
3. Scoring, ranking and portfolio-health modules create decision-support
   artifacts, not decisions.
4. `decision_quality` evaluates process/readiness state from existing outputs.
5. `decision_journal_validation` evaluates the append-only journal and produces
   review queue artifacts.
6. Report surfaces render available states and show `NOT_AVAILABLE` only when
   an artifact is missing, unreadable or the stage did not run.
7. Handoff export packages code, docs, tests, configs and selected review
   context for external validation.

## Current `personal_run_engine` Stage Overview

The current engine uses a linear canonical stage order. This is an execution
order, not yet a full formal data-dependency DAG.

Observed stage order:

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
21. `history`
22. `benchmark_archive`
23. `performance`
24. `multi_benchmark`
25. `cost_tax`
26. `dashboard`

`decision_quality` runs after the monthly and portfolio-health review stages.
It writes:

- `data/processed/decision_quality_state.csv`
- `data/processed/decision_quality_state.json`
- `reports/<as_of_date>/decision_quality_report.md`

`decision_journal_validation` runs after `decision_quality`. It writes:

- `data/processed/decision_journal_validation.csv`
- `data/processed/decision_review_queue.csv`
- `reports/<as_of_date>/decision_journal_validation_report.md`

The complete Stage-DAG, including required/optional input edges and
dashboard-facing operator summary contract, remains a known gap.

## Authoritative Artifacts

- Contracts:
  - `docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md`
  - `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`
- Architecture docs:
  - `docs/architecture/COMPOUND_INCOME_OS_SYSTEM_DEFINITION.md`
  - `docs/architecture/DECISION_QUALITY_LAYER.md`
  - `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
  - `docs/architecture/CIOS_FEATURE_STATUS.yaml`
  - `docs/architecture/CURRENT_KNOWN_GAPS.md`
- Governance docs:
  - `docs/MODULE_CONTRACTS.md`
  - `docs/CONTEXT_AND_ROADMAP.md`
  - `docs/governance/BASELINE_VS_CANDIDATE_VALIDATION.md`
- Configs:
  - `configs/portfolio_rules.yaml`
  - `configs/scoring_weights.yaml`
  - `configs/fundamentals_schema.yaml`
  - `configs/fundamentals_score_rules.yaml`
  - `configs/fundamentals_metric_definitions.yaml`
  - `configs/personal_run_data_sources.yaml`
- Source modules:
  - `src/personal_run_engine.py`
  - `src/personal_decision_quality_state.py`
  - `src/personal_decision_journal_validation.py`
  - `src/personal_decision_state_capture.py`
  - `src/build_monthly_decision_report.py`
- Tests:
  - `tests/test_personal_run_engine.py`
  - `tests/test_personal_decision_quality_state.py`
  - `tests/test_personal_decision_journal_validation.py`
  - `tests/test_monthly_decision_report.py`
- Generated outputs:
  - processed CSV/JSON artifacts under `data/processed/`
  - Markdown reports under `reports/<date>/`
- Handoff files:
  - `external_review_packet/00_READ_ME_FIRST.md`
  - `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
  - `external_review_packet/HANDOFF_LATEST.sha256`
  - `external_review_packet/HANDOFF_LATEST.zip`

## Report Surfaces

- Personal Run Report: summarizes selected stages, produced artifacts, Decision
  Quality and Decision Journal Validation when produced by the run.
- Monthly Decision Report: renders portfolio health, Decision Quality and
  Decision Journal Validation only when explicit state artifacts are supplied.
- Decision Quality Surface: shows process/review confidence, hard blockers,
  reason codes and `NOT_EVALUATED` robustness fields.
- Decision Journal Validation Surface: shows validation status, validation
  finding counts, queue counts and stale-state counts.
- Review Queue Surface: lists due or blocked operator follow-ups.

Missing, unreadable or not-run artifacts render as `NOT_AVAILABLE`. Existing
header-only Decision Journal Validation and Review Queue CSVs render as `PASS`
with zero counts.

## Known Limitations

- External ZIP reproducibility is intentionally limited when private/raw inputs
  are excluded from the handoff bundle.
- There is no full replay engine yet.
- There is no outcome attribution.
- There is no Portfolio Event Ledger.
- There is no Ranking Robustness or Sensitivity producer yet.
- There is no full dashboard operator surface contract yet.
- Decision Quality stale-state handling is conservative: any older
  `as_of_date` is stale in the current MVP.
- Scenario, Tail Risk, Calibration and Regret remain non-implemented or
  `NOT_EVALUATED` design areas.

## Dashboard Readiness Verdict

- `NOT_READY_FOR_FULL_DASHBOARD`: full dashboard needs a surface contract,
  Stage-DAG, final operator summary and freshness/staleness contract.
- `READY_FOR_OPERATOR_SURFACE_CONTRACT`: Decision Quality and Review Queue
  fields are now stable enough to define a dashboard-facing contract.
- `READY_FOR_DASHBOARD_SUMMARY_DESIGN`: summary cards can be designed from
  existing fields without adding financial logic.
- `NOT_READY_FOR_OUTCOME_ATTRIBUTION`: no Portfolio Event Ledger, replay or
  outcome ledger exists yet.
- `NOT_READY_FOR_BACKTESTING`: no replay, event ledger, decision journal
  validation history or bias controls are complete enough for backtesting.

## Next Recommended Hardening Patches

1. Dashboard Operator Surface Contract.
2. Stage-DAG / Operator Summary.
3. Data Freshness / Staleness Contract.
4. Dashboard Surface for Decision Quality and Review Queue Summary.
5. Ranking Robustness / Sensitivity producer later.
6. Portfolio Event Ledger later.
7. Replay / Outcome later.
