# Personal Artifact Reconciliation Report

Generated: 2026-04-26

## 1. Executive Summary

- Demo readiness: `BLOCKED`
- Decision readiness: `BLOCKED`
- Reason codes: `CORE_KPI_MISSING;DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;MISSING_DIVIDEND_FCF_REQUIRED;MISSING_METADATA;MISSING_VALUATION_REQUIRED;NO_IMPUTATION;NO_VALUE_CHANGES;PROVENANCE_INCOMPLETE;REVIEW_CORE_DATA;SEC_IDENTITY_AVAILABLE;STALE_ARTIFACT;VALUATION_REQUIRED_MISSING;WATCHLIST_REVIEW_OR_MISSING_DATA;WATCHLIST_SAMPLE_INPUT`
- Scoring fundamentals source mode: `EVIDENCE_APPLIED`

This report reconciles existing processed artifacts only. It does not change scores, formulas, fundamentals values, watchlist values, or monthly ranking outputs.

## 2. Input Artifacts

| Label | Path |
| --- | --- |
| artifact_freshness_summary | `data/processed/personal_artifact_freshness_summary.csv` |
| core_kpi_closure_summary | `data/processed/personal_core_kpi_closure_summary.csv` |
| dividend_fcf_contract_summary | `data/processed/personal_dividend_fcf_input_contract_summary.csv` |
| evidence_delta_holdings | `data/processed/personal_evidence_applied_downstream_delta_holdings.csv` |
| evidence_delta_summary | `data/processed/personal_evidence_applied_downstream_delta_summary.csv` |
| kpi_tier | `data/processed/personal_kpi_tier_coverage.csv` |
| manifest | `data/processed/personal_run_manifest.json` |
| missing_kpi_holdings | `data/processed/personal_missing_kpi_closure_holdings.csv` |
| missing_kpi_summary | `data/processed/personal_missing_kpi_closure_summary.csv` |
| monthly | `data/processed/personal_monthly_buy_ranking.csv` |
| monthly_action_summary | `data/processed/personal_monthly_action_compatibility_summary.csv` |
| score_audit | `data/processed/personal_score_audit.csv` |
| scores | `data/processed/personal_company_scores.csv` |
| used_inputs | `data/processed/personal_run_used_inputs.csv` |
| valuation_contract_summary | `data/processed/personal_valuation_input_contract_summary.csv` |
| watchlist | `data/processed/personal_watchlist_ranked.csv` |
| watchlist_gate_summary | `data/processed/personal_watchlist_input_gate_summary.csv` |

## 3. Counter Reconciliation

| Metric | Value | Notes |
| --- | --- | --- |
| `artifact_drift_active` | `False` | Observed from artifact freshness summary when present. |
| `artifact_freshness_reason_codes` | `MISSING_METADATA;STALE_DERIVED_ARTIFACT` | Freshness reason codes from artifact freshness summary. |
| `artifact_freshness_summary_available` | `True` | Artifact freshness summary was loaded. |
| `blocked_checks_total` | `3` | Checks with BLOCKED status. |
| `checks_total` | `8` | Number of reconciliation checks. |
| `core_kpi_closure_affected_standard_rows_count` | `4` | Core KPI closure summary metric. |
| `core_kpi_closure_manual_evidence_required_count` | `0` | Core KPI closure summary metric. |
| `core_kpi_closure_no_value_changes_confirmed` | `True` | Core KPI closure summary metric. |
| `core_kpi_closure_queue_rows_count` | `4` | Core KPI closure summary metric. |
| `core_kpi_closure_reason_codes` | `CORE_KPI_MISSING;NO_VALUE_CHANGES;PROFILE_NOT_STANDARD;REVIEW_CORE_DATA;SEC_IDENTITY_AVAILABLE` | Core KPI closure summary metric. |
| `core_kpi_closure_required_core_kpis` | `eps_cagr_5y; gross_margin; operating_margin; revenue_cagr_5y; share_count_cagr_5y` | Core KPI closure summary metric. |
| `core_kpi_closure_review_existing_evidence_count` | `0` | Core KPI closure summary metric. |
| `core_kpi_closure_sec_evidence_possible_count` | `4` | Core KPI closure summary metric. |
| `core_kpi_closure_source_unknown_count` | `0` | Core KPI closure summary metric. |
| `core_kpi_closure_summary_available` | `True` | Core KPI closure summary was loaded. |
| `decision_readiness_status` | `BLOCKED` | Conservative status from reconciliation checks. |
| `delta_score_data_quality__BLOCKED` | `0` | Evidence-applied delta summary data-quality count. |
| `delta_score_data_quality__MISSING_DATA` | `17` | Evidence-applied delta summary data-quality count. |
| `delta_score_data_quality__OK` | `0` | Evidence-applied delta summary data-quality count. |
| `delta_score_data_quality__REVIEW` | `0` | Evidence-applied delta summary data-quality count. |
| `demo_readiness_status` | `BLOCKED` | Conservative status from reconciliation checks. |
| `dividend_fcf_contract_affected_standard_rows_count` | `10` | Dividend/FCF input contract summary metric. |
| `dividend_fcf_contract_approved_rows_count` | `0` | Dividend/FCF input contract summary metric. |
| `dividend_fcf_contract_input_file_status` | `MISSING` | Dividend/FCF input contract summary metric. |
| `dividend_fcf_contract_invalid_rows_count` | `0` | Dividend/FCF input contract summary metric. |
| `dividend_fcf_contract_manual_evidence_required_count` | `0` | Dividend/FCF input contract summary metric. |
| `dividend_fcf_contract_missing_rows_count` | `10` | Dividend/FCF input contract summary metric. |
| `dividend_fcf_contract_no_imputation_confirmed` | `True` | Dividend/FCF input contract summary metric. |
| `dividend_fcf_contract_queue_rows_count` | `10` | Dividend/FCF input contract summary metric. |
| `dividend_fcf_contract_reason_codes` | `DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;NO_IMPUTATION;PROFILE_NOT_STANDARD;SEC_IDENTITY_AVAILABLE` | Dividend/FCF input contract summary metric. |
| `dividend_fcf_contract_review_existing_evidence_count` | `0` | Dividend/FCF input contract summary metric. |
| `dividend_fcf_contract_review_rows_count` | `0` | Dividend/FCF input contract summary metric. |
| `dividend_fcf_contract_sec_evidence_possible_count` | `10` | Dividend/FCF input contract summary metric. |
| `dividend_fcf_contract_source_unknown_count` | `0` | Dividend/FCF input contract summary metric. |
| `dividend_fcf_contract_summary_available` | `True` | Dividend/FCF input contract summary was loaded. |
| `evidence_delta_current_missing_required_kpi_total` | `10` | Current missing required KPI count from evidence-applied delta summary. |
| `kpi_tier_resulting_monthly_action__DO_NOT_BUY` | `7` | KPI tier resulting monthly action count. |
| `kpi_tier_resulting_monthly_action__REVIEW_CORE_DATA` | `4` | KPI tier resulting monthly action count. |
| `kpi_tier_resulting_monthly_action__WAIT_VALUATION` | `6` | KPI tier resulting monthly action count. |
| `missing_kpi_closure_missing_required_kpi_total` | `10` | Baseline from missing-KPI closure summary. |
| `monthly_action__NO_ACTION` | `1` | Neutral monthly_action count from compatibility summary. |
| `monthly_action__WAIT_FOR_VALUATION` | `17` | Neutral monthly_action count from compatibility summary. |
| `monthly_action_compatibility_available` | `True` | Neutral monthly_action compatibility artifact available. |
| `monthly_action_forbidden_values_total` | `0` | Forbidden monthly_action values in compatibility summary. |
| `monthly_has_allocation_status` | `True` | Schema check. |
| `monthly_has_monthly_action` | `False` | Schema check. |
| `monthly_has_target_action` | `True` | Schema check. |
| `monthly_rows_total` | `18` | Rows in personal_monthly_buy_ranking.csv. |
| `monthly_schema_drift_resolved` | `True` | Monthly schema drift check resolved by direct field or companion compatibility artifact. |
| `monthly_target_action__DO_NOT_BUY` | `7` | Monthly target_action count. |
| `monthly_target_action__HOLD_CASH` | `1` | Monthly target_action count. |
| `monthly_target_action__REVIEW_CORE_DATA` | `4` | Monthly target_action count. |
| `monthly_target_action__WAIT_VALUATION` | `6` | Monthly target_action count. |
| `not_available_checks_total` | `0` | Checks with NOT_AVAILABLE status. |
| `readiness_reason_codes` | `CORE_KPI_MISSING;DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;MISSING_DIVIDEND_FCF_REQUIRED;MISSING_METADATA;MISSING_VALUATION_REQUIRED;NO_IMPUTATION;NO_VALUE_CHANGES;PROVENANCE_INCOMPLETE;REVIEW_CORE_DATA;SEC_IDENTITY_AVAILABLE;STALE_ARTIFACT;VALUATION_REQUIRED_MISSING;WATCHLIST_REVIEW_OR_MISSING_DATA;WATCHLIST_SAMPLE_INPUT` | Union of BLOCKED/REVIEW/NOT_AVAILABLE reason codes. |
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
| `unresolved_current_artifact_drift_total` | `0` | Current unexplained drift count from freshness summary. |
| `valuation_contract_affected_standard_rows_count` | `10` | Valuation input contract summary metric. |
| `valuation_contract_approved_rows_count` | `0` | Valuation input contract summary metric. |
| `valuation_contract_input_file_status` | `MISSING` | Valuation input contract summary metric. |
| `valuation_contract_invalid_rows_count` | `0` | Valuation input contract summary metric. |
| `valuation_contract_missing_rows_count` | `10` | Valuation input contract summary metric. |
| `valuation_contract_no_imputation_confirmed` | `True` | Valuation input contract summary metric. |
| `valuation_contract_queue_rows_count` | `10` | Valuation input contract summary metric. |
| `valuation_contract_reason_codes` | `INPUT_FILE_MISSING;NO_IMPUTATION;PROFILE_NOT_STANDARD;VALUATION_REQUIRED_MISSING` | Valuation input contract summary metric. |
| `valuation_contract_review_rows_count` | `0` | Valuation input contract summary metric. |
| `valuation_contract_summary_available` | `True` | Valuation input contract summary was loaded. |
| `warnings_total` | `0` | Missing input warnings. |
| `watchlist_data_quality__MISSING_DATA` | `8` | Watchlist data-quality count. |
| `watchlist_data_status` | `MISSING_DATA` | Watchlist input gate summary metric. |
| `watchlist_input_path` | `data/raw/sample_watchlist.csv` | Observed watchlist input path from used inputs. |
| `watchlist_input_status` | `SAMPLE_DEMO_ONLY` | Watchlist input gate summary metric. |
| `watchlist_readiness_status` | `BLOCKED` | Watchlist input gate summary metric. |
| `watchlist_review_or_missing_data_active` | `True` | Watchlist input gate summary metric. |
| `watchlist_rows_total` | `8` | Rows in personal_watchlist_ranked.csv. |
| `watchlist_sample_input_active` | `True` | Watchlist input gate summary metric. |
| `watchlist_status__REVIEW` | `8` | Watchlist status count. |

## 4. Drift Findings

| Check | Status | Reasons | Evidence |
| --- | --- | --- | --- |
| `per_kpi_provenance` | `REVIEW` | `PROVENANCE_INCOMPLETE` | personal_score_audit.csv exists, but per-KPI source-reference join is not fully materialized |
| `score_vs_delta_data_quality` | `REVIEW` | `MISSING_METADATA;STALE_ARTIFACT` | personal_company_scores.csv; personal_evidence_applied_downstream_delta_summary.csv; personal_artifact_freshness_summary.csv |
| `standard_core_review` | `BLOCKED` | `CORE_KPI_MISSING;NO_VALUE_CHANGES;REVIEW_CORE_DATA;SEC_IDENTITY_AVAILABLE` | personal_kpi_tier_coverage.csv; personal_core_kpi_closure_summary.csv |
| `standard_dividend_fcf_required` | `REVIEW` | `DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;MISSING_DIVIDEND_FCF_REQUIRED;NO_IMPUTATION;SEC_IDENTITY_AVAILABLE` | personal_kpi_tier_coverage.csv; personal_dividend_fcf_input_contract_summary.csv |
| `standard_valuation_required` | `BLOCKED` | `INPUT_FILE_MISSING;MISSING_VALUATION_REQUIRED;NO_IMPUTATION;VALUATION_REQUIRED_MISSING` | personal_kpi_tier_coverage.csv; personal_valuation_input_contract_summary.csv |
| `watchlist_demo_decision_readiness` | `BLOCKED` | `WATCHLIST_REVIEW_OR_MISSING_DATA;WATCHLIST_SAMPLE_INPUT` | personal_run_used_inputs.csv; personal_watchlist_ranked.csv; personal_watchlist_input_gate_summary.csv |

## 5. Demo Readiness

Status: `BLOCKED`

Demo readiness is blocked when processed artifacts disagree, schema drift can hide action states, or sample inputs are used without explicit labeling.

## 6. Decision Readiness

Status: `BLOCKED`

Decision readiness remains blocked while valuation-required data, core review data, sample watchlist inputs, schema drift, or incomplete KPI provenance remain unresolved.

## 7. Blockers

- `standard_core_review`: `CORE_KPI_MISSING;NO_VALUE_CHANGES;REVIEW_CORE_DATA;SEC_IDENTITY_AVAILABLE`. Review SEC/manual core KPI closure queue; do not impute values.
- `standard_valuation_required`: `INPUT_FILE_MISSING;MISSING_VALUATION_REQUIRED;NO_IMPUTATION;VALUATION_REQUIRED_MISSING`. Populate reviewed valuation input with approved values and source metadata; do not impute values.
- `watchlist_demo_decision_readiness`: `WATCHLIST_REVIEW_OR_MISSING_DATA;WATCHLIST_SAMPLE_INPUT`. Use a reviewed watchlist input or label current output as sample/demo-only.

## 8. Review Items

- `per_kpi_provenance`: `PROVENANCE_INCOMPLETE`. Add a dedicated KPI provenance audit artifact.
- `score_vs_delta_data_quality`: `MISSING_METADATA;STALE_ARTIFACT`. Add comparable metadata or regenerate stale derived delta; do not treat stale counters as current truth.
- `standard_dividend_fcf_required`: `DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;MISSING_DIVIDEND_FCF_REQUIRED;NO_IMPUTATION;SEC_IDENTITY_AVAILABLE`. Populate reviewed dividend/FCF input with approved values and source metadata; do not impute values.

## 9. Can Remain Review

- Advanced optional KPI gaps can remain visible if they do not drive candidate status.
- FINANCIAL, OTHER, ETF, ADR, and non-US rows can remain separate from STANDARD scoring until explicit profile models exist.
- Dividend/FCF gaps can remain REVIEW for a data-quality demo, but not for a decision-quality demo.

## 10. Recommended Next Patch

Implement a KPI provenance audit that maps score-relevant KPI values to raw/profiled/evidence/overlay source metadata, then address valuation-required input contracts without imputation.
