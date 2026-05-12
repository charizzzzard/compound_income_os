# Patch 2.2a  Personal-Meta Removal Scope

## Repo Reality

- branch: `main`
- head: `d2f5958`
- tests: `python -m unittest discover -s tests -p "test_*.py" -v` -> `Ran 529 tests in 96.816s`, `OK`

## Why This Discovery Exists

Patch 2.2 was stopped because the repo did not contain an explicit documented list of the 13 Personal-Meta modules.

This discovery does not remove, archive, or edit imports. It records the current evidence and separates high-confidence removal/archive candidates from modules that need an operator decision.

Important result: the intended list of 13 modules cannot be reconstructed with high confidence from current repo documentation. The only high-confidence archive candidate is `src/personal_profile_review_materialize.py`. Several other modules look like review/reporting helpers or `LOCAL_PATCH` artifacts, but current docs also connect some of them to handoff, dashboard-readiness, reconciliation, or the v1.2 target architecture.

Patch 2.2b status: `personal_profile_review_materialize.py` archived to `_archive/personal_meta/`.

## Candidate Inventory

| Module | Tests | Imports In | Outputs / Artifacts | Docs / Contract Evidence | Classification | Proposed Treatment | Confidence |
|---|---|---|---|---|---|---|---|
| `src/personal_artifact_freshness.py` | `tests/test_personal_artifact_freshness.py` | tests only | `data/processed/personal_artifact_freshness_checks.csv`, `data/processed/personal_artifact_freshness_summary.csv`, report | Handoff allowlist includes outputs; reconciliation can consume freshness summary; no explicit removal note | `UNCLEAR_NEEDS_OPERATOR_DECISION` | `operator_decision_required` | medium |
| `src/personal_artifact_reconciliation.py` | `tests/test_personal_artifact_reconciliation.py` | tests only | `data/processed/personal_artifact_reconciliation_summary.csv`, `data/processed/personal_artifact_reconciliation_checks.csv`, report | Handoff allowlist includes outputs; readiness status consumes reconciliation artifacts; no explicit removal note | `UNCLEAR_NEEDS_OPERATOR_DECISION` | `operator_decision_required` | medium |
| `src/personal_core_kpi_closure.py` | `tests/test_personal_core_kpi_closure.py` | tests only | `data/processed/personal_core_kpi_closure_queue.csv`, `data/processed/personal_core_kpi_closure_summary.csv`, report | Dashboard readiness tests reference core KPI closure summary; handoff allowlist includes outputs; no explicit removal note | `UNCLEAR_NEEDS_OPERATOR_DECISION` | `operator_decision_required` | medium |
| `src/personal_decision_state_capture.py` | `tests/test_personal_decision_state_capture.py` | tests only | `data/processed/personal_decision_state_capture.csv`, report | `docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md`, `docs/CONTEXT_AND_ROADMAP.md`, README and Vision v1.2 identify it as the first minimal producer | `KEEP_DECISION_CAPTURE` | `keep` | high |
| `src/personal_dividend_fcf_input_contract.py` | `tests/test_personal_dividend_fcf_input_contract.py` | tests only | `data/processed/personal_dividend_fcf_input_contract_summary.csv`, report | Handoff allowlist includes outputs; artifact reconciliation/readiness consume summary; no explicit removal note | `UNCLEAR_NEEDS_OPERATOR_DECISION` | `operator_decision_required` | medium |
| `src/personal_evidence_applied_downstream_delta.py` | `tests/test_personal_evidence_applied_downstream_delta.py` | tests only | `data/processed/personal_evidence_applied_downstream_delta_summary.csv`, `data/processed/personal_evidence_applied_downstream_delta_holdings.csv`, report | `docs/MODULE_CONTRACTS.md` marks it `LOCAL_PATCH`; README frames it as external review/LLM handoff evidence; artifact freshness/reconciliation consume its outputs | `UNCLEAR_NEEDS_OPERATOR_DECISION` | `operator_decision_required` | medium |
| `src/personal_kpi_provenance_audit.py` | `tests/test_personal_kpi_provenance_audit.py` | `src/personal_score_audit_provenance.py`, tests | `data/processed/personal_kpi_provenance_audit.csv`, report | Handoff allowlist includes outputs; production import from score-audit provenance module means removal is not isolated | `KEEP_ACTIVE_OBSERVE_REPORTING` | `keep` | high |
| `src/personal_kpi_tier_coverage.py` | `tests/test_personal_kpi_tier_coverage.py` | tests only | `data/processed/personal_kpi_tier_coverage.csv`, report | Vision v1.2 lists it under observe; `docs/MODULE_CONTRACTS.md` marks it `LOCAL_PATCH` but describes read-only operational review | `KEEP_ACTIVE_OBSERVE_REPORTING` | `keep` | high |
| `src/personal_missing_kpi_closure_report.py` | `tests/test_personal_missing_kpi_closure_report.py` | tests only | `data/processed/personal_missing_kpi_closure_summary.csv`, `data/processed/personal_missing_kpi_closure_holdings.csv`, report | Vision v1.2 lists it under observe; `docs/MODULE_CONTRACTS.md` marks it `LOCAL_PATCH`; README frames report for external review handoffs | `KEEP_ACTIVE_OBSERVE_REPORTING` | `keep` | medium |
| `src/personal_monthly_action_schema.py` | `tests/test_personal_monthly_action_schema.py` | tests only | monthly-action schema report | Handoff allowlist includes report; no pipeline stage and no explicit target-architecture placement found | `UNCLEAR_NEEDS_OPERATOR_DECISION` | `operator_decision_required` | medium |
| `src/personal_private_input_apply_candidates.py` | `tests/test_personal_private_input_apply_candidates.py` | tests only | private candidate CSV, sanitized processed CSV, summary, report | Handoff allowlist includes sanitized/summary outputs; dashboard readiness references private apply candidate summary; no explicit removal note | `UNCLEAR_NEEDS_OPERATOR_DECISION` | `operator_decision_required` | medium |
| `src/personal_private_input_review.py` | `tests/test_personal_private_input_review.py` | tests only | validation CSV, summary, report | Handoff allowlist includes outputs; dashboard readiness references private input review summary; no explicit removal note | `UNCLEAR_NEEDS_OPERATOR_DECISION` | `operator_decision_required` | medium |
| `src/personal_profile_review_materialize.py` | `tests/test_personal_profile_review_materialize.py` | tests only | `data/raw/personal_fundamentals_profile_review.csv`, materialization report | `docs/MODULE_CONTRACTS.md` says it materializes archived SEC identity seed; Patch 1 kept it alive via inline-copied SEC constant; no active `src` imports or pipeline stage; test is specific to temporary materialization | `ARCHIVE_PERSONAL_META` | `archive_to__archive/personal_meta/` | high |
| `src/personal_profile_review_unlock_report.py` | `tests/test_personal_profile_review_unlock_report.py` | tests only | `data/processed/personal_profile_review_unlock_summary.csv`, `data/processed/personal_profile_review_unlock_holdings.csv`, report | `docs/MODULE_CONTRACTS.md` marks it `LOCAL_PATCH`; README frames it as external review/LLM handoff report; `personal_missing_kpi_closure_report` consumes unlock holdings by default | `UNCLEAR_NEEDS_OPERATOR_DECISION` | `operator_decision_required` | medium |
| `src/personal_readiness_status.py` | `tests/test_personal_readiness_status.py` | tests only | `data/processed/personal_readiness_status_summary.csv`, blockers, next actions, report | Vision v1.2 lists it under observe; dashboard readiness consumes readiness summary; `docs/CONTEXT_AND_ROADMAP.md` keeps dashboard/readiness as repo reality | `KEEP_ACTIVE_OBSERVE_REPORTING` | `keep` | high |
| `src/personal_run_engine.py` | `tests/test_personal_run_engine.py` | tests only | personal run manifest, artifacts, used-inputs, report | `docs/CONTEXT_AND_ROADMAP.md`, `docs/MODULE_CONTRACTS.md`, README and Vision v1.2 identify it as the personal orchestrator | `KEEP_ORCHESTRATOR` | `keep` | high |
| `src/personal_score_audit_provenance.py` | `tests/test_personal_score_audit_provenance.py` | tests only | `data/processed/personal_score_audit_provenance.csv`, summary, report | Vision v1.2 lists it under score; it imports `src.personal_kpi_provenance_audit`; handoff allowlist includes outputs | `KEEP_ACTIVE_OBSERVE_REPORTING` | `keep` | high |
| `src/personal_valuation_input_contract.py` | `tests/test_personal_valuation_input_contract.py` | tests only | `data/processed/personal_valuation_input_contract_summary.csv`, report | Dashboard readiness references valuation contract summary; handoff allowlist includes outputs; no explicit removal note | `UNCLEAR_NEEDS_OPERATOR_DECISION` | `operator_decision_required` | medium |
| `src/personal_watchlist_input_gate.py` | `tests/test_personal_watchlist_input_gate.py` | tests only | `data/processed/personal_watchlist_input_gate.csv`, summary, report | Dashboard readiness and artifact reconciliation consume watchlist gate summary; handoff allowlist includes outputs; no explicit removal note | `UNCLEAR_NEEDS_OPERATOR_DECISION` | `operator_decision_required` | medium |

## Proposed Removal / Archive List

### High Confidence

| Module | Proposed Treatment | Evidence |
|---|---|---|
| `src/personal_profile_review_materialize.py` | `archive_to__archive/personal_meta/` | Contract says archived SEC-Identity-Seed materializer; Patch 1 kept it alive only by inline-copying an SEC constant; no active `src` imports or personal-run stage; paired test only covers this temporary materialization path |

### Needs Operator Decision

| Module | Reason Ambiguous | Options |
|---|---|---|
| `src/personal_artifact_freshness.py` | Looks like handoff/observe hygiene, but its summary is consumed by reconciliation and handoff allowlists. No removal note. | `keep` or `archive_to__archive/personal_meta/` |
| `src/personal_artifact_reconciliation.py` | Readiness consumes reconciliation artifacts; no explicit target-architecture placement or removal note. | `keep` or `archive_to__archive/personal_meta/` |
| `src/personal_core_kpi_closure.py` | Produces review queues and readiness blockers; no active stage, but dashboard readiness references its summary. | `keep` or `archive_to__archive/personal_meta/` |
| `src/personal_dividend_fcf_input_contract.py` | Produces review summary used by readiness/reconciliation; no explicit removal note. | `keep` or `archive_to__archive/personal_meta/` |
| `src/personal_evidence_applied_downstream_delta.py` | Marked `LOCAL_PATCH` and handoff-oriented, but consumed by artifact freshness/reconciliation. | `keep` or `archive_to__archive/personal_meta/` |
| `src/personal_monthly_action_schema.py` | Handoff report exists, but no active stage or clear target-architecture placement found. | `keep` or `archive_to__archive/personal_meta/` |
| `src/personal_private_input_apply_candidates.py` | Produces private/sanitized candidate workflow and dashboard summary; no explicit removal note. | `keep` or `archive_to__archive/personal_meta/` |
| `src/personal_private_input_review.py` | Produces private input validation/summary used by dashboard readiness; no explicit removal note. | `keep` or `archive_to__archive/personal_meta/` |
| `src/personal_profile_review_unlock_report.py` | Marked `LOCAL_PATCH` and handoff-oriented, but consumed by missing-KPI closure defaults. | `keep` or `archive_to__archive/personal_meta/` |
| `src/personal_valuation_input_contract.py` | Produces readiness blocker summary; no explicit removal note. | `keep` or `archive_to__archive/personal_meta/` |
| `src/personal_watchlist_input_gate.py` | Produces watchlist gate summary consumed by readiness/reconciliation; no explicit removal note. | `keep` or `archive_to__archive/personal_meta/` |

Potential 13-module operator-review set: the 11 ambiguous modules above plus `src/personal_profile_review_materialize.py` and, if the operator decides the score provenance companion is temporary despite Vision v1.2 listing it under score, `src/personal_score_audit_provenance.py`. This is not high-confidence enough to execute.

## Modules Explicitly Not To Remove

| Module | Reason |
|---|---|
| `src/personal_decision_state_capture.py` | Decision Capture is the accepted P0 producer and is documented in the contract, README, roadmap, and Vision v1.2. |
| `src/personal_kpi_provenance_audit.py` | Imported by `src.personal_score_audit_provenance`; removal would not be isolated. |
| `src/personal_kpi_tier_coverage.py` | Vision v1.2 places it in observe; downstream closure/readiness artifacts use it. |
| `src/personal_missing_kpi_closure_report.py` | Vision v1.2 places it in observe; contracts and README describe it as read-only closure visibility. |
| `src/personal_readiness_status.py` | Vision v1.2 places it in observe; dashboard readiness depends on readiness status outputs. |
| `src/personal_run_engine.py` | Personal orchestrator; explicitly documented in roadmap, contracts, README, and Vision v1.2. |
| `src/personal_score_audit_provenance.py` | Vision v1.2 places it in score; it has companion import dependency on `personal_kpi_provenance_audit`. Treat as keep unless operator explicitly overrides. |

## Recommended Patch 2.2 Execution Plan

- Commit sequence:
  - Commit 2.2.1: archive `src/personal_profile_review_materialize.py` and `tests/test_personal_profile_review_materialize.py` to `_archive/personal_meta/` if operator approves archival convention.
  - Commit 2.2.2: apply only operator-approved decisions for the ambiguous modules, one coherent group at a time.
  - Commit 2.2.3: update README, `docs/MODULE_CONTRACTS.md`, `docs/CONTEXT_AND_ROADMAP.md`, and handoff allowlists only for modules actually archived/removed.
- Tests to run:
  - `python -m unittest discover -s tests -p "test_*.py" -v`
  - targeted tests for any modules that remain but lose optional input defaults.
  - `python -m src.personal_run_engine --help`
  - `python -m src.dashboard_engine --help`
- Docs to update:
  - `docs/MODULE_CONTRACTS.md`: remove or mark archived rows for approved modules only.
  - `docs/CONTEXT_AND_ROADMAP.md`: update active module count and Personal-Meta status.
  - `README.md`: remove CLI/artifact references only when the underlying module is actually archived or removed.
  - `src/handoff_zip_export.py`: remove allowlisted processed/report artifacts only for archived/removed modules.
- Acceptance criteria:
  - No active `src` import references an archived/removed module.
  - No active `tests/test_*.py` imports an archived/removed module.
  - Normal unittest discovery remains green.
  - Archived tests do not run under `python -m unittest discover -s tests -p "test_*.py"`.
  - No Phase-1 product logic, scoring changes, portfolio rule changes, or dashboard behavior changes are introduced.
