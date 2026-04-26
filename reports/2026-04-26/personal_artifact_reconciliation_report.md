# Personal Artifact Reconciliation Report

Generated: 2026-04-26

## 1. Executive Summary

- Demo readiness: `BLOCKED`
- Decision readiness: `BLOCKED`
- Reason codes: `ARTIFACT_DRIFT;MISSING_DIVIDEND_FCF_REQUIRED;MISSING_VALUATION_REQUIRED;MONTHLY_SCHEMA_DRIFT;PROVENANCE_INCOMPLETE;REVIEW_CORE_DATA;WATCHLIST_REVIEW_OR_MISSING_DATA;WATCHLIST_SAMPLE_INPUT`
- Scoring fundamentals source mode: `EVIDENCE_APPLIED`

This report reconciles existing processed artifacts only. It does not change scores, formulas, fundamentals values, watchlist values, or monthly ranking outputs.

## 2. Input Artifacts

| Label | Path |
| --- | --- |
| evidence_delta_holdings | `data/processed/personal_evidence_applied_downstream_delta_holdings.csv` |
| evidence_delta_summary | `data/processed/personal_evidence_applied_downstream_delta_summary.csv` |
| kpi_tier | `data/processed/personal_kpi_tier_coverage.csv` |
| manifest | `data/processed/personal_run_manifest.json` |
| missing_kpi_holdings | `data/processed/personal_missing_kpi_closure_holdings.csv` |
| missing_kpi_summary | `data/processed/personal_missing_kpi_closure_summary.csv` |
| monthly | `data/processed/personal_monthly_buy_ranking.csv` |
| score_audit | `data/processed/personal_score_audit.csv` |
| scores | `data/processed/personal_company_scores.csv` |
| used_inputs | `data/processed/personal_run_used_inputs.csv` |
| watchlist | `data/processed/personal_watchlist_ranked.csv` |

## 3. Counter Reconciliation

| Metric | Value | Notes |
| --- | --- | --- |
| `blocked_checks_total` | `4` | Checks with BLOCKED status. |
| `checks_total` | `8` | Number of reconciliation checks. |
| `decision_readiness_status` | `BLOCKED` | Conservative status from reconciliation checks. |
| `delta_score_data_quality__BLOCKED` | `0` | Evidence-applied delta summary data-quality count. |
| `delta_score_data_quality__MISSING_DATA` | `17` | Evidence-applied delta summary data-quality count. |
| `delta_score_data_quality__OK` | `0` | Evidence-applied delta summary data-quality count. |
| `delta_score_data_quality__REVIEW` | `0` | Evidence-applied delta summary data-quality count. |
| `demo_readiness_status` | `BLOCKED` | Conservative status from reconciliation checks. |
| `evidence_delta_current_missing_required_kpi_total` | `10` | Current missing required KPI count from evidence-applied delta summary. |
| `kpi_tier_resulting_monthly_action__DO_NOT_BUY` | `7` | KPI tier resulting monthly action count. |
| `kpi_tier_resulting_monthly_action__REVIEW_CORE_DATA` | `4` | KPI tier resulting monthly action count. |
| `kpi_tier_resulting_monthly_action__WAIT_VALUATION` | `6` | KPI tier resulting monthly action count. |
| `missing_kpi_closure_missing_required_kpi_total` | `10` | Baseline from missing-KPI closure summary. |
| `monthly_has_allocation_status` | `True` | Schema check. |
| `monthly_has_monthly_action` | `False` | Schema check. |
| `monthly_has_target_action` | `True` | Schema check. |
| `monthly_rows_total` | `18` | Rows in personal_monthly_buy_ranking.csv. |
| `monthly_target_action__DO_NOT_BUY` | `7` | Monthly target_action count. |
| `monthly_target_action__HOLD_CASH` | `1` | Monthly target_action count. |
| `monthly_target_action__REVIEW_CORE_DATA` | `4` | Monthly target_action count. |
| `monthly_target_action__WAIT_VALUATION` | `6` | Monthly target_action count. |
| `not_available_checks_total` | `0` | Checks with NOT_AVAILABLE status. |
| `readiness_reason_codes` | `ARTIFACT_DRIFT;MISSING_DIVIDEND_FCF_REQUIRED;MISSING_VALUATION_REQUIRED;MONTHLY_SCHEMA_DRIFT;PROVENANCE_INCOMPLETE;REVIEW_CORE_DATA;WATCHLIST_REVIEW_OR_MISSING_DATA;WATCHLIST_SAMPLE_INPUT` | Union of BLOCKED/REVIEW/NOT_AVAILABLE reason codes. |
| `review_checks_total` | `3` | Checks with REVIEW status. |
| `score_data_quality__BLOCKED` | `0` | Current score CSV data-quality count. |
| `score_data_quality__MISSING_DATA` | `11` | Current score CSV data-quality count. |
| `score_data_quality__OK` | `0` | Current score CSV data-quality count. |
| `score_data_quality__REVIEW` | `6` | Current score CSV data-quality count. |
| `score_delta_mismatch_statuses` | `MISSING_DATA;REVIEW` | Statuses whose score CSV and delta summary counts differ. |
| `score_rows_total` | `17` | Rows in personal_company_scores.csv. |
| `scoring_fundamentals_master_path` | `data/processed/personal_fundamentals_master_evidence_applied.csv` | Observed scoring fundamentals master path. |
| `scoring_fundamentals_source_mode` | `EVIDENCE_APPLIED` | Observed from used-inputs/manifest. |
| `standard_missing_dividend_fcf_required_rows_total` | `10` | STANDARD rows missing dividend/FCF-required data. |
| `standard_missing_valuation_required_rows_total` | `10` | STANDARD rows missing valuation-required data. |
| `standard_review_core_data_rows_total` | `4` | STANDARD rows with resulting_monthly_action=REVIEW_CORE_DATA. |
| `standard_rows_total` | `10` | Rows in KPI tier coverage with company_type_profile=STANDARD. |
| `warnings_total` | `0` | Missing input warnings. |
| `watchlist_data_quality__MISSING_DATA` | `8` | Watchlist data-quality count. |
| `watchlist_input_path` | `data/raw/sample_watchlist.csv` | Observed watchlist input path from used inputs. |
| `watchlist_rows_total` | `8` | Rows in personal_watchlist_ranked.csv. |
| `watchlist_status__REVIEW` | `8` | Watchlist status count. |

## 4. Drift Findings

| Check | Status | Reasons | Evidence |
| --- | --- | --- | --- |
| `monthly_schema_contract` | `REVIEW` | `MONTHLY_SCHEMA_DRIFT` | personal_monthly_buy_ranking.csv; current delta-style review artifacts expose monthly_action as derived output |
| `per_kpi_provenance` | `REVIEW` | `PROVENANCE_INCOMPLETE` | personal_score_audit.csv exists, but per-KPI source-reference join is not fully materialized |
| `score_vs_delta_data_quality` | `BLOCKED` | `ARTIFACT_DRIFT` | personal_company_scores.csv vs personal_evidence_applied_downstream_delta_summary.csv |
| `standard_core_review` | `BLOCKED` | `REVIEW_CORE_DATA` | personal_kpi_tier_coverage.csv |
| `standard_dividend_fcf_required` | `REVIEW` | `MISSING_DIVIDEND_FCF_REQUIRED` | personal_kpi_tier_coverage.csv |
| `standard_valuation_required` | `BLOCKED` | `MISSING_VALUATION_REQUIRED` | personal_kpi_tier_coverage.csv |
| `watchlist_demo_decision_readiness` | `BLOCKED` | `WATCHLIST_REVIEW_OR_MISSING_DATA;WATCHLIST_SAMPLE_INPUT` | personal_run_used_inputs.csv; personal_watchlist_ranked.csv |

## 5. Demo Readiness

Status: `BLOCKED`

Demo readiness is blocked when processed artifacts disagree, schema drift can hide action states, or sample inputs are used without explicit labeling.

## 6. Decision Readiness

Status: `BLOCKED`

Decision readiness remains blocked while valuation-required data, core review data, sample watchlist inputs, schema drift, or incomplete KPI provenance remain unresolved.

## 7. Blockers

- `score_vs_delta_data_quality`: `ARTIFACT_DRIFT`. Regenerate evidence-applied delta after the current scoring/tiering run.
- `standard_core_review`: `REVIEW_CORE_DATA`. Close core-quality KPI evidence or keep blocked.
- `standard_valuation_required`: `MISSING_VALUATION_REQUIRED`. Add reviewed valuation input contract or manual overlay; do not impute values.
- `watchlist_demo_decision_readiness`: `WATCHLIST_REVIEW_OR_MISSING_DATA;WATCHLIST_SAMPLE_INPUT`. Use a reviewed watchlist input or label current output as sample/demo-only.

## 8. Review Items

- `monthly_schema_contract`: `MONTHLY_SCHEMA_DRIFT`. Add a compatibility alias or update report readers in a dedicated schema patch.
- `per_kpi_provenance`: `PROVENANCE_INCOMPLETE`. Add a dedicated KPI provenance audit artifact.
- `standard_dividend_fcf_required`: `MISSING_DIVIDEND_FCF_REQUIRED`. Add reviewed FCF/dividend evidence or keep rows in REVIEW.

## 9. Can Remain Review

- Advanced optional KPI gaps can remain visible if they do not drive candidate status.
- FINANCIAL, OTHER, ETF, ADR, and non-US rows can remain separate from STANDARD scoring until explicit profile models exist.
- Dividend/FCF gaps can remain REVIEW for a data-quality demo, but not for a decision-quality demo.

## 10. Recommended Next Patch

Implement a KPI provenance audit that maps score-relevant KPI values to raw/profiled/evidence/overlay source metadata, then address valuation-required input contracts without imputation.
