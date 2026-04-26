# Personal Valuation Input Contract Report

## Executive Summary
- Affected STANDARD rows: 10
- Queue rows: 10
- Approved rows: 0
- Missing rows: 10
- Invalid rows: 0
- No imputation confirmed: True

## Input Artifacts
- `evidence_applied_master`: `data/processed/personal_fundamentals_master_evidence_applied.csv`
- `kpi_tier`: `data/processed/personal_kpi_tier_coverage.csv`
- `queue_output`: `data/processed/personal_valuation_input_review_queue.csv`
- `scores`: `data/processed/personal_company_scores.csv`
- `summary_output`: `data/processed/personal_valuation_input_contract_summary.csv`
- `valuation_review_input`: `<private_path>`

## Valuation Required KPI Contract
- Required fields: `normalized_fcf_yield_pct`, `target_fcf_yield_pct`.
- Values are only valid when numeric, reviewed as `APPROVED`, and backed by source reference and source date.
- Plausibility guardrail is technical only: numeric values must be between -100 and 100.
- Missing values are not calculated, inferred, or written into master/score artifacts by this module.

## Affected STANDARD Rows
| ticker | isin | company_name | missing_valuation_kpis | valuation_input_status | reason_code |
| --- | --- | --- | --- | --- | --- |
| US02079K3059 | US02079K3059 | Alphabet Inc. Reg. Shs Cap.Stk Cl. A DL-,001 | normalized_fcf_yield_pct; target_fcf_yield_pct | MISSING | INPUT_FILE_MISSING;NO_IMPUTATION;VALUATION_REQUIRED_MISSING |
| US0378331005 | US0378331005 | Apple Inc. Registered Shares o.N. | normalized_fcf_yield_pct; target_fcf_yield_pct | MISSING | INPUT_FILE_MISSING;NO_IMPUTATION;VALUATION_REQUIRED_MISSING |
| US0394831020 | US0394831020 | Archer Daniels Midland Co. Registered Shares o.N. | normalized_fcf_yield_pct; target_fcf_yield_pct | MISSING | INPUT_FILE_MISSING;NO_IMPUTATION;VALUATION_REQUIRED_MISSING |
| US22788C1053 | US22788C1053 | Crowdstrike Holdings Inc Registered Shs Cl.A DL-,0005 | normalized_fcf_yield_pct; target_fcf_yield_pct | MISSING | INPUT_FILE_MISSING;NO_IMPUTATION;VALUATION_REQUIRED_MISSING |
| US2546871060 | US2546871060 | Walt Disney Co., The Registered Shares DL -,01 | normalized_fcf_yield_pct; target_fcf_yield_pct | MISSING | INPUT_FILE_MISSING;NO_IMPUTATION;VALUATION_REQUIRED_MISSING |
| US5949181045 | US5949181045 | Microsoft Corp. Registered Shares DL-,00000625 | normalized_fcf_yield_pct; target_fcf_yield_pct | MISSING | INPUT_FILE_MISSING;NO_IMPUTATION;VALUATION_REQUIRED_MISSING |
| US69608A1088 | US69608A1088 | Palantir Technologies Inc. Registered Shares o.N. | normalized_fcf_yield_pct; target_fcf_yield_pct | MISSING | INPUT_FILE_MISSING;NO_IMPUTATION;VALUATION_REQUIRED_MISSING |
| US8522341036 | US8522341036 | Block Inc. Registered Shs Class A | normalized_fcf_yield_pct; target_fcf_yield_pct | MISSING | INPUT_FILE_MISSING;NO_IMPUTATION;VALUATION_REQUIRED_MISSING |
| US92826C8394 | US92826C8394 | VISA Inc. Reg. Shares Class A DL -,0001 | normalized_fcf_yield_pct; target_fcf_yield_pct | MISSING | INPUT_FILE_MISSING;NO_IMPUTATION;VALUATION_REQUIRED_MISSING |
| US98138J5039 | US98138J5039 | Workhorse Group Inc. Registered Shares New DL-,001 | normalized_fcf_yield_pct; target_fcf_yield_pct | MISSING | INPUT_FILE_MISSING;NO_IMPUTATION;VALUATION_REQUIRED_MISSING |

## Review Queue Summary
- `MISSING`: 10

## Optional Review Input Validation
- Input status: `MISSING`
- Review input path: `<private_path>`
- Private reviewed valuation values are not printed in this report.

## No-Imputation Guardrail
- This module does not calculate valuation values from price, FCF, or any other field.
- This module does not update the fundamentals master, score audit, company scores, monthly ranking, or watchlist.

## Reconciliation Impact
- `MISSING_VALUATION_REQUIRED` remains active until approved valuation inputs exist and are applied through a separate reviewed workflow.
- This patch only makes the missing valuation contract and review queue explicit.

## Remaining Demo Readiness Blockers
- Watchlist sample/review state, provenance gaps, core-data review states, and stale metadata remain outside this patch.

## Remaining Decision Readiness Blockers
- Valuation-required gaps remain blocked while reviewed inputs are missing or unapplied.
- Dividend/FCF gaps and provenance gaps remain separate blockers.

## Reason Code Counts
- `INPUT_FILE_MISSING`: 10
- `NO_IMPUTATION`: 10
- `VALUATION_REQUIRED_MISSING`: 10

## Recommended Next Patch
`PATCH / CORE KPI CLOSURE REPORT / REVIEW_CORE_DATA / SEC + MANUAL REVIEW / NO VALUE CHANGES`
