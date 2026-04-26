# Strategy Review: Fundamentals Coverage, Trust Chain, Scoring Sanity

Date: 2026-04-26
Mode: read-only strategy review
Repository branch: main
Observed HEAD: ce801aa

## 1. Executive Summary

Profile review is no longer the primary blocker in the observed local artifact set. The current gap summary shows a populated profile review input, 12 approved profile rows, and 5 not-reviewed rows. The current evidence apply path also appears operational: the evidence apply summary reports 30 proposed updates, 30 applied rows, 30 applied fields, and no skipped fields.

The current blocker is downstream decision data quality. In the latest processed artifacts, all 17 personal score rows remain non-OK: `personal_company_scores.csv` shows 6 `REVIEW` rows and 11 `MISSING_DATA` rows, while `personal_evidence_applied_downstream_delta_summary.csv` still reports 17 `MISSING_DATA` rows. This mismatch is an artifact-drift finding and should be reconciled before using the reports as a demo source of truth.

For STANDARD-profile holdings, valuation and dividend/FCF data are the broadest blockers. All 10 STANDARD rows in `personal_kpi_tier_coverage.csv` miss valuation-required KPIs (`normalized_fcf_yield_pct`, `target_fcf_yield_pct`) and dividend/FCF-required KPIs. Four STANDARD rows still lack enough core-quality data and remain `REVIEW_CORE_DATA`. Six STANDARD rows have at least partial/OK core-quality data but remain `WAIT_VALUATION`.

The trust chain is mostly traceable at the run-input level. `personal_run_used_inputs.csv` records that the scoring and downstream stages used `data/processed/personal_fundamentals_master_evidence_applied.csv` with `fundamentals_source_mode=EVIDENCE_APPLIED`. However, per-KPI score audit rows are not fully traceable back to evidence registry source references for every number. That is the main evidence trust-chain gap before product-like demo use.

## 2. Repo Reality

### Committed HEAD Reality

- Branch: `main`
- HEAD short: `ce801aa`
- HEAD full observed earlier in session: `ce801aa8f74d195b28caacd31fbaaac0accf31b4`
- Canonical docs available: `README.md`, `docs/PROJECT_CHARTER.md`, `docs/CONTEXT_AND_ROADMAP.md`, `docs/MODULE_CONTRACTS.md`
- Handoff exporter available: `src/handoff_zip_export.py`
- Website deployment dry-run state exists in HEAD, but website work is outside this review scope.

### Dirty Working Tree Reality

The worktree contains existing uncommitted backend/report changes. They were not modified by this review.

Modified tracked files observed:

- `README.md`
- `configs/fundamentals_metric_definitions.yaml`
- `data/raw/personal_fundamentals_profile_review.csv`
- `data/raw/personal_fundamentals_profile_review_template.csv`
- `docs/MODULE_CONTRACTS.md`
- `src/fundamentals_engine.py`
- `src/fundamentals_master.py`
- `src/monthly_ranking_engine.py`
- `src/scoring_engine.py`
- `tests/test_fundamentals_evidence_engine.py`
- `tests/test_fundamentals_master.py`
- `tests/test_monthly_ranking_engine.py`
- `tests/test_scoring_engine.py`

Untracked review-relevant files observed:

- `src/personal_evidence_applied_downstream_delta.py`
- `src/personal_kpi_tier_coverage.py`
- `src/personal_missing_kpi_closure_report.py`
- `tests/test_personal_evidence_applied_downstream_delta.py`
- `tests/test_personal_missing_kpi_closure_report.py`
- `compound_income_os_HANDOFF_20260426-204236_ce801aa.zip`

Private raw inputs were inspected only structurally. No private raw content was copied into this report.

### Reliable Review Inputs Present

- `data/processed/personal_company_scores.csv`
- `data/processed/personal_score_audit.csv`
- `data/processed/personal_fundamentals_coverage.csv`
- `data/processed/personal_fundamentals_gap_diagnostics.csv`
- `data/processed/personal_fundamentals_gap_summary.csv`
- `data/processed/personal_kpi_tier_coverage.csv`
- `data/processed/personal_missing_kpi_closure_holdings.csv`
- `data/processed/personal_missing_kpi_closure_summary.csv`
- `data/processed/personal_evidence_applied_downstream_delta_holdings.csv`
- `data/processed/personal_evidence_applied_downstream_delta_summary.csv`
- `data/processed/personal_fundamentals_evidence_registry.csv`
- `data/processed/personal_fundamentals_evidence_apply_summary.csv`
- `data/processed/personal_fundamentals_master_profiled.csv`
- `data/processed/personal_fundamentals_master_evidence_applied.csv`
- `data/processed/personal_monthly_buy_ranking.csv`
- `data/processed/personal_watchlist_ranked.csv`
- `data/processed/personal_run_used_inputs.csv`
- `data/processed/personal_run_manifest.json`

## 3. Fundamentals Coverage Findings

The current metric contract separates STANDARD required KPIs into tiers:

| Tier | KPIs | Current observed impact |
| --- | --- | --- |
| `CORE_QUALITY_REQUIRED` | `revenue_cagr_5y`, `eps_cagr_5y`, `gross_margin`, `operating_margin`, `share_count_cagr_5y` | 2 STANDARD rows OK, 4 PARTIAL, 4 MISSING |
| `VALUATION_REQUIRED` | `normalized_fcf_yield_pct`, `target_fcf_yield_pct` | Missing for all 10 STANDARD rows |
| `DIVIDEND_FCF_REQUIRED` | `fcf_margin`, `payout_ratio_fcf`, `fcf_per_share_cagr_5y` | Missing for all 10 STANDARD rows |
| `ADVANCED_OPTIONAL` | `buyback_yield`, `interest_coverage`, `net_debt_to_ebitda`, `roce`, `roic` | Missing for all 10 STANDARD rows, but should not block core scoring alone |

Current processed counters:

| Artifact | Finding |
| --- | --- |
| `personal_company_scores.csv` | 17 rows: 6 `REVIEW`, 11 `MISSING_DATA` |
| `personal_kpi_tier_coverage.csv` | 10 STANDARD rows, 1 FINANCIAL row, 6 OTHER rows |
| `personal_kpi_tier_coverage.csv` | 4 `REVIEW_CORE_DATA`, 6 `WAIT_VALUATION`, 7 `DO_NOT_BUY` |
| `personal_watchlist_ranked.csv` | 8 rows, all `REVIEW`, all `MISSING_DATA` |
| `personal_fundamentals_gap_diagnostics.csv` | 9 `SEC_KPI_PARTIAL`, 1 `SEC_KPI_MISSING`, 3 non-US/current SEC-scope gaps, 2 ETF/non-company gaps, 2 market-data-required gaps |

## 4. Coverage Gap Matrix

| Priority | Gap | Evidence | Required next action |
| --- | --- | --- | --- |
| `MUST_FIX_BEFORE_DEMO` | Artifact drift between score CSV and delta summary | Score CSV shows 6 `REVIEW` + 11 `MISSING_DATA`; delta summary still shows 17 `MISSING_DATA` | Re-run or reconcile downstream delta/report artifacts after tiering and evidence-applied scoring |
| `MUST_FIX_BEFORE_DEMO` | Valuation-required KPIs missing for all STANDARD rows | `personal_kpi_tier_coverage.csv` | Add explicit valuation input contract or manual overlay workflow for `normalized_fcf_yield_pct` and `target_fcf_yield_pct` |
| `MUST_FIX_BEFORE_DEMO` | Four STANDARD rows lack enough core-quality data | `personal_kpi_tier_coverage.csv` rows with `REVIEW_CORE_DATA` | Close SEC evidence mapping or manual evidence for missing core KPIs |
| `MUST_FIX_BEFORE_DEMO` | Monthly action schema drift | Monthly output uses `target_action`/`allocation_status`; newer delta-style reports expect `monthly_action` | Align report readers with existing monthly schema or add a stable alias artifact |
| `MUST_FIX_BEFORE_DEMO` | Watchlist input is sample-based in current run | `personal_run_used_inputs.csv` shows `watchlist_input=data/raw/sample_watchlist.csv` | Replace with reviewed personal watchlist input or label as sample/demo-only |
| `SHOULD_FIX_FOR_DECISION_QUALITY` | Dividend/FCF KPIs missing for all STANDARD rows | `personal_kpi_tier_coverage.csv` | Add reviewed FCF/dividend data source or manual overlay |
| `SHOULD_FIX_FOR_DECISION_QUALITY` | Debt/advanced KPIs missing for STANDARD rows | `personal_kpi_tier_coverage.csv` | Keep optional for core score, but expose as risk/review flags |
| `SHOULD_FIX_FOR_DECISION_QUALITY` | FINANCIAL profile lacks separate scoring path | One FINANCIAL row is `NOT_APPLICABLE` for STANDARD tiers | Add financial-company KPI profile or keep excluded |
| `SHOULD_FIX_FOR_DECISION_QUALITY` | Non-US, ETF, ADR, OTHER cases are structurally blocked | Gap diagnostics and profile coverage | Add non-US/manual fundamentals, ETF/fund facts, ADR policy, and OTHER profile workflow |
| `CAN_REMAIN_REVIEW` | Advanced optional KPIs missing | Tier contract marks as advanced optional | Keep visible, do not block core quality |
| `CAN_REMAIN_REVIEW` | OTHER profile rows excluded from STANDARD scoring | `company_type_profile=OTHER` rows | Keep excluded unless explicit model exists |
| `UNKNOWN_NEEDS_SOURCE` | Per-KPI source trace into score audit | Evidence registry has sources, score audit has values, but not full source-reference join per KPI | Extend score audit provenance before public/product-like demo |

## 5. Holdings / Watchlist Data Risk Priorities

High-priority data-risk groups from processed artifacts:

| Group | Current risk | Why it matters |
| --- | --- | --- |
| STANDARD rows with `REVIEW_CORE_DATA` | Core quality insufficient | Core quality score cannot be trusted enough for decision support |
| STANDARD rows with `WAIT_VALUATION` | Core may be usable, but valuation missing | Monthly candidate gating should remain blocked |
| All STANDARD dividend/FCF rows | Dividend/FCF tier missing | Dividend-growth workflow remains incomplete |
| Watchlist rows | All watchlist rows are `REVIEW`/`MISSING_DATA` | Watchlist ranking is not decision-ready |
| FINANCIAL/OTHER/non-US/ETF/ADR rows | Not covered by STANDARD KPI model | Must remain separate or explicitly modeled |

## 6. Evidence & Trust Chain Findings

| Chain element | Status | Finding |
| --- | --- | --- |
| Raw Fundamentals Master | `MOSTLY_TRUSTED` | Raw master exists and was not mutated by this review. Private/raw contents were not printed. |
| Profiled Master | `MOSTLY_TRUSTED` | Profile registry and profiled master exist; profile review blocker appears resolved for 12 rows. |
| Evidence Snapshot Ingestion | `MOSTLY_TRUSTED` | Snapshot/evidence artifacts exist. Trust depends on reviewed identity and source metadata quality. |
| Evidence Registry | `MOSTLY_TRUSTED` | Evidence rows include source metadata and verification fields. |
| Evidence Apply | `TRUSTED` | Apply summary reports 30 applied rows/fields and no skips in current processed artifact. |
| Evidence-Applied Master | `MOSTLY_TRUSTED` | Used by latest personal run according to used-inputs. |
| Personal Run Used Inputs | `TRUSTED` | `fundamentals_source_mode=EVIDENCE_APPLIED` is visible for scoring/downstream stages. |
| Score Audit | `REVIEW_NEEDED` | Component values are visible, but per-KPI source references are not fully joined back to evidence rows. |
| Downstream Reports | `REVIEW_NEEDED` | Some processed summaries disagree with current score CSV counters. |
| Dashboard Inputs | `REVIEW_NEEDED` | Dashboard can display processed artifacts, but stale or schema-drifted artifacts can mislead. |
| Handoff Export | `MOSTLY_TRUSTED` | Export module exists and has forbidden-entry rules; current strategy report was not in the prior ZIP. |
| READ_FIRST entry | `REVIEW_NEEDED` | README and docs exist, but no single `READ_FIRST.md` entry point was verified. |

## 7. Scoring / Ranking Methodology Findings

Score components are transparent in config and artifacts. Business score, quality, dividend, balance sheet, growth quality, capital allocation, valuation, expected return, drawdown, and portfolio fit are separated.

Current conservative gates appear effective: no processed row is currently decision-ready, watchlist rows remain `REVIEW`, and monthly ranking does not produce a clean candidate state from incomplete data.

Main methodology risks:

| Risk | Status | Impact |
| --- | --- | --- |
| Data-coverage bias | `REVIEW_NEEDED` | Rows with more available KPIs can receive numeric scores even if still not decision-ready; views must sort/filter by quality flags first. |
| Fallback score interpretation | `REVIEW_NEEDED` | Missing component fallback scores can look precise unless audit flags are prominent. |
| Buy-score terminology | `REVIEW_NEEDED` | Internal `buy_score` naming is legacy-compatible but can be unsafe in public/product-facing surfaces. |
| Monthly schema mismatch | `GAP` | `target_action`/`allocation_status` vs `monthly_action` expectations can break reports or undercount actions. |
| Profile-specific scoring | `GAP` | FINANCIAL, OTHER, ETF, ADR, and non-US holdings are not methodologically comparable to STANDARD rows. |

## 8. Must Fix Before Demo

If the demo goal is data-quality workflow demonstration, some gaps can remain visible. If the demo goal is product-like decision quality, these are must-fix:

1. Reconcile current processed artifacts so score CSV, tier coverage, missing-KPI closure, evidence-applied delta, monthly ranking, and dashboard inputs agree.
2. Add or finalize valuation data contract for STANDARD rows.
3. Close core-quality gaps for STANDARD rows that still show `REVIEW_CORE_DATA`.
4. Align monthly output schema with downstream report expectations.
5. Replace or explicitly label sample watchlist input in personal-run demo.
6. Add per-KPI provenance from score/audit values to evidence registry or overlay source metadata.
7. Keep FINANCIAL, OTHER, ETF, ADR, and non-US holdings visibly outside STANDARD scoring unless explicit profile models exist.

## 9. Can Remain REVIEW

- Advanced optional KPIs may remain missing if the UI and reports clearly show they are non-blocking.
- OTHER-profile holdings can remain excluded from STANDARD scoring.
- FINANCIAL profile can remain separate if not presented as comparable to STANDARD industrial/technology holdings.
- Non-US, ETF, and ADR cases can remain as workflow backlog if labeled clearly.
- Private demo can tolerate missing dividend/FCF data only if monthly candidate generation remains blocked and reports show why.

## 10. Recommended Patch Sequence

1. Artifact reconciliation patch: regenerate/read current processed artifacts into one consistent evidence-applied, tier-aware status report.
2. Provenance patch: extend score audit or a companion audit artifact with per-KPI `source_name`, `source_reference`, `source_type`, `source_as_of_date`, and applied/raw/reviewed status.
3. Valuation input contract patch: define manual/evidence valuation fields for `normalized_fcf_yield_pct` and `target_fcf_yield_pct`, without auto-imputation.
4. Core KPI closure patch: target the four STANDARD rows with insufficient core-quality coverage.
5. Dividend/FCF patch: add reviewed FCF/dividend evidence or overlay workflow for dividend-growth analysis.
6. Monthly/report schema patch: stabilize `monthly_action` vs `target_action` terminology and downstream readers.
7. Non-standard profile patch: keep FINANCIAL/OTHER/ETF/non-US/ADR workflows explicit and separate.
8. Demo readiness patch: create a deterministic demo-readiness report with PASS/REVIEW/BLOCKED gates.

## 11. Concrete Next Codex Prompts

### Prompt 1: Artifact Reconciliation

Task type: PATCH / ARTIFACT RECONCILIATION / EVIDENCE-APPLIED STATUS / READONLY-FIRST. Compare `personal_company_scores.csv`, `personal_kpi_tier_coverage.csv`, `personal_missing_kpi_closure_*`, `personal_evidence_applied_downstream_delta_*`, `personal_monthly_buy_ranking.csv`, and `personal_run_used_inputs.csv`. Produce a deterministic reconciliation report showing stale or contradictory counters. Do not change scoring formulas.

### Prompt 2: Score Audit Provenance

Task type: PATCH / KPI PROVENANCE AUDIT / EVIDENCE TRUST CHAIN. Extend or add an audit artifact that maps each score-relevant KPI per holding to raw master, profiled master, evidence registry, evidence-applied master, or manual overlay. Include source references where available. Do not invent missing values.

### Prompt 3: Valuation Required Inputs

Task type: PATCH / VALUATION INPUT CONTRACT / NO IMPUTATION. Define a reviewed manual/evidence input workflow for `normalized_fcf_yield_pct` and `target_fcf_yield_pct`, with validation and explicit REVIEW status. Keep BUY_CANDIDATE blocked until valuation status is OK.

### Prompt 4: Core KPI Closure

Task type: PATCH / CORE KPI CLOSURE REPORT / SEC + MANUAL REVIEW. Build a targeted closure report for STANDARD rows with `REVIEW_CORE_DATA`, listing missing core KPIs, available evidence, proposed source path, and next manual review action.

### Prompt 5: Monthly Schema Stabilization

Task type: PATCH / MONTHLY ACTION SCHEMA / REPORT COMPATIBILITY. Align downstream reports that expect `monthly_action` with the existing monthly ranking artifact fields `target_action` and `allocation_status`, preserving backward compatibility and avoiding investment advice language.

## 12. Validation Notes

`git diff --check` passed with line-ending warnings for pre-existing dirty files. Full `compileall` and full test discovery were not run in this read-only review because they can create bytecode/cache or test temp artifacts in the working tree.
