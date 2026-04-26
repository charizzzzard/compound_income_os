# Personal Dividend / FCF Input Contract Report

## Executive Summary
- Affected STANDARD rows: 10
- Queue rows: 10
- Approved rows: 0
- Missing rows: 10
- SEC evidence possible: 10
- No imputation confirmed: True

## Input Artifacts
- `dividend_fcf_review_input`: `<private_path>`
- `evidence_applied_master`: `data/processed/personal_fundamentals_master_evidence_applied.csv`
- `evidence_registry`: `data/processed/personal_fundamentals_evidence_registry.csv`
- `kpi_tier`: `data/processed/personal_kpi_tier_coverage.csv`
- `metric_definitions`: `configs/fundamentals_metric_definitions.yaml`
- `queue_output`: `data/processed/personal_dividend_fcf_input_review_queue.csv`
- `scores`: `data/processed/personal_company_scores.csv`
- `sec_identity_apply`: `data/processed/personal_sec_identity_apply_changes.csv`
- `sec_scope_review`: `data/processed/personal_sec_scope_review.csv`
- `summary_output`: `data/processed/personal_dividend_fcf_input_contract_summary.csv`

## Dividend / FCF Required KPI Contract
- Contract status: `OK`
- Required KPIs: `fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf`
- Values are only valid when numeric, reviewed as `APPROVED`, and backed by source reference and source date.
- Plausibility guardrail is technical only: numeric values must be between -100 and 300.

## Affected STANDARD Rows
| ticker | isin | company_name | missing_dividend_fcf_kpis | input_status | sec_scope_status | evidence_registry_status | evidence_applied_status | recommended_closure_path | reason_code |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| US02079K3059 | US02079K3059 | Alphabet Inc. Reg. Shs Cap.Stk Cl. A DL-,001 | fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf | MISSING | SEC_ELIGIBLE | NO_EVIDENCE | NO_APPLIED_VALUE | SEC_EVIDENCE_POSSIBLE | DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;NO_IMPUTATION;SEC_IDENTITY_AVAILABLE |
| US0378331005 | US0378331005 | Apple Inc. Registered Shares o.N. | fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf | MISSING | SEC_ELIGIBLE | NO_EVIDENCE | NO_APPLIED_VALUE | SEC_EVIDENCE_POSSIBLE | DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;NO_IMPUTATION;SEC_IDENTITY_AVAILABLE |
| US0394831020 | US0394831020 | Archer Daniels Midland Co. Registered Shares o.N. | fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf | MISSING | SEC_ELIGIBLE | NO_EVIDENCE | NO_APPLIED_VALUE | SEC_EVIDENCE_POSSIBLE | DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;NO_IMPUTATION;SEC_IDENTITY_AVAILABLE |
| US22788C1053 | US22788C1053 | Crowdstrike Holdings Inc Registered Shs Cl.A DL-,0005 | fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf | MISSING | SEC_ELIGIBLE | NO_EVIDENCE | NO_APPLIED_VALUE | SEC_EVIDENCE_POSSIBLE | DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;NO_IMPUTATION;SEC_IDENTITY_AVAILABLE |
| US2546871060 | US2546871060 | Walt Disney Co., The Registered Shares DL -,01 | fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf | MISSING | SEC_ELIGIBLE | NO_EVIDENCE | NO_APPLIED_VALUE | SEC_EVIDENCE_POSSIBLE | DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;NO_IMPUTATION;SEC_IDENTITY_AVAILABLE |
| US5949181045 | US5949181045 | Microsoft Corp. Registered Shares DL-,00000625 | fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf | MISSING | SEC_ELIGIBLE | NO_EVIDENCE | NO_APPLIED_VALUE | SEC_EVIDENCE_POSSIBLE | DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;NO_IMPUTATION;SEC_IDENTITY_AVAILABLE |
| US69608A1088 | US69608A1088 | Palantir Technologies Inc. Registered Shares o.N. | fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf | MISSING | SEC_ELIGIBLE | NO_EVIDENCE | NO_APPLIED_VALUE | SEC_EVIDENCE_POSSIBLE | DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;NO_IMPUTATION;SEC_IDENTITY_AVAILABLE |
| US8522341036 | US8522341036 | Block Inc. Registered Shs Class A | fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf | MISSING | SEC_ELIGIBLE | NO_EVIDENCE | NO_APPLIED_VALUE | SEC_EVIDENCE_POSSIBLE | DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;NO_IMPUTATION;SEC_IDENTITY_AVAILABLE |
| US92826C8394 | US92826C8394 | VISA Inc. Reg. Shares Class A DL -,0001 | fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf | MISSING | SEC_ELIGIBLE | NO_EVIDENCE | NO_APPLIED_VALUE | SEC_EVIDENCE_POSSIBLE | DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;NO_IMPUTATION;SEC_IDENTITY_AVAILABLE |
| US98138J5039 | US98138J5039 | Workhorse Group Inc. Registered Shares New DL-,001 | fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf | MISSING | SEC_ELIGIBLE | NO_EVIDENCE | NO_APPLIED_VALUE | SEC_EVIDENCE_POSSIBLE | DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;NO_IMPUTATION;SEC_IDENTITY_AVAILABLE |

## Missing Dividend / FCF KPI Matrix
- `US02079K3059`: missing `fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf`; covered ``
- `US0378331005`: missing `fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf`; covered ``
- `US0394831020`: missing `fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf`; covered ``
- `US22788C1053`: missing `fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf`; covered ``
- `US2546871060`: missing `fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf`; covered ``
- `US5949181045`: missing `fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf`; covered ``
- `US69608A1088`: missing `fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf`; covered ``
- `US8522341036`: missing `fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf`; covered ``
- `US92826C8394`: missing `fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf`; covered ``
- `US98138J5039`: missing `fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf`; covered ``

## Optional Review Input Validation
- Input status: `MISSING`
- Review input path: `<private_path>`
- Private reviewed dividend/FCF values are not printed in this report.

## Evidence / SEC / Manual Closure Diagnostics
- `SEC_EVIDENCE_POSSIBLE` means a reviewed SEC identity exists structurally; no SEC network call was made.
- `REVIEW_EXISTING_EVIDENCE` means exact existing registry/applied signals should be reviewed before any apply step.
- `MANUAL_EVIDENCE_REQUIRED` means no sufficient structural evidence path was found.

## No-Imputation Guardrail
- This module does not fetch SEC data, calculate dividend/FCF KPIs, impute values, or write to master/score/evidence-apply artifacts.

## Reconciliation Impact
- `MISSING_DIVIDEND_FCF_REQUIRED` remains active until approved dividend/FCF inputs exist and are applied through a separate reviewed workflow.
- This patch only makes the dividend/FCF input contract and review queue explicit.

## Remaining Demo Readiness Blockers
- Watchlist sample/review state, valuation gaps, core-data review states, provenance gaps, and freshness metadata review remain outside this patch.

## Remaining Decision Readiness Blockers
- Dividend/FCF gaps remain blocked while reviewed inputs are missing or unapplied.

## Reason Code Counts
- `DIVIDEND_FCF_REQUIRED_MISSING`: 10
- `INPUT_FILE_MISSING`: 10
- `NO_IMPUTATION`: 10
- `SEC_IDENTITY_AVAILABLE`: 10

## Recommended Next Patch
`PATCH / READINESS STATUS CONSOLIDATION / BLOCKER SUMMARY / NO VALUE CHANGES`
