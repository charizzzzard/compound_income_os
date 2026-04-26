# Personal Core KPI Closure Report

## Executive Summary
- Affected STANDARD rows: 4
- Queue rows: 4
- SEC evidence possible: 4
- Manual evidence required: 0
- Review existing evidence: 0
- No value changes confirmed: True

## Input Artifacts
- `evidence_applied_master`: `data/processed/personal_fundamentals_master_evidence_applied.csv`
- `evidence_registry`: `data/processed/personal_fundamentals_evidence_registry.csv`
- `kpi_tier`: `data/processed/personal_kpi_tier_coverage.csv`
- `metric_definitions`: `configs/fundamentals_metric_definitions.yaml`
- `queue_output`: `data/processed/personal_core_kpi_closure_queue.csv`
- `scores`: `data/processed/personal_company_scores.csv`
- `sec_identity_apply`: `data/processed/personal_sec_identity_apply_changes.csv`
- `sec_scope_review`: `data/processed/personal_sec_scope_review.csv`
- `summary_output`: `data/processed/personal_core_kpi_closure_summary.csv`

## Core KPI Contract
- Contract status: `OK`
- Required core KPIs: `eps_cagr_5y; gross_margin; operating_margin; revenue_cagr_5y; share_count_cagr_5y`
- Non-STANDARD profiles are not evaluated against the STANDARD core KPI contract.

## Affected STANDARD Rows
| ticker | isin | company_name | missing_core_kpis | sec_scope_status | evidence_registry_status | evidence_applied_status | recommended_closure_path | reason_code |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| US02079K3059 | US02079K3059 | Alphabet Inc. Reg. Shs Cap.Stk Cl. A DL-,001 | gross_margin; operating_margin; revenue_cagr_5y; share_count_cagr_5y | SEC_ELIGIBLE | NO_EVIDENCE | NO_APPLIED_VALUE | SEC_EVIDENCE_POSSIBLE | CORE_KPI_MISSING;NO_VALUE_CHANGES;REVIEW_CORE_DATA;SEC_IDENTITY_AVAILABLE |
| US22788C1053 | US22788C1053 | Crowdstrike Holdings Inc Registered Shs Cl.A DL-,0005 | eps_cagr_5y; gross_margin; operating_margin; revenue_cagr_5y; share_count_cagr_5y | SEC_ELIGIBLE | NO_EVIDENCE | NO_APPLIED_VALUE | SEC_EVIDENCE_POSSIBLE | CORE_KPI_MISSING;NO_VALUE_CHANGES;REVIEW_CORE_DATA;SEC_IDENTITY_AVAILABLE |
| US8522341036 | US8522341036 | Block Inc. Registered Shs Class A | gross_margin; operating_margin; revenue_cagr_5y | SEC_ELIGIBLE | NO_EVIDENCE | NO_APPLIED_VALUE | SEC_EVIDENCE_POSSIBLE | CORE_KPI_MISSING;NO_VALUE_CHANGES;REVIEW_CORE_DATA;SEC_IDENTITY_AVAILABLE |
| US92826C8394 | US92826C8394 | VISA Inc. Reg. Shares Class A DL -,0001 | eps_cagr_5y; gross_margin; revenue_cagr_5y; share_count_cagr_5y | SEC_ELIGIBLE | NO_EVIDENCE | NO_APPLIED_VALUE | SEC_EVIDENCE_POSSIBLE | CORE_KPI_MISSING;NO_VALUE_CHANGES;REVIEW_CORE_DATA;SEC_IDENTITY_AVAILABLE |

## Missing Core KPI Matrix
- `US02079K3059`: missing `gross_margin; operating_margin; revenue_cagr_5y; share_count_cagr_5y`; covered `eps_cagr_5y`
- `US22788C1053`: missing `eps_cagr_5y; gross_margin; operating_margin; revenue_cagr_5y; share_count_cagr_5y`; covered ``
- `US8522341036`: missing `gross_margin; operating_margin; revenue_cagr_5y`; covered `eps_cagr_5y; share_count_cagr_5y`
- `US92826C8394`: missing `eps_cagr_5y; gross_margin; revenue_cagr_5y; share_count_cagr_5y`; covered `operating_margin`

## Evidence / SEC / Manual Closure Diagnostics
- `SEC_EVIDENCE_POSSIBLE` means a reviewed SEC identity exists structurally; no SEC network call was made.
- `REVIEW_EXISTING_EVIDENCE` means exact existing registry/applied signals should be reviewed before any apply step.
- `MANUAL_EVIDENCE_REQUIRED` means no sufficient structural evidence path was found.

## Recommended Review Actions
- `US02079K3059`: Run reviewed SEC evidence workflow for missing core KPIs.
- `US22788C1053`: Run reviewed SEC evidence workflow for missing core KPIs.
- `US8522341036`: Run reviewed SEC evidence workflow for missing core KPIs.
- `US92826C8394`: Run reviewed SEC evidence workflow for missing core KPIs.

## No-Value-Change Guardrail
- This module does not fetch SEC data, calculate missing KPIs, impute values, or write to master/score/evidence-apply artifacts.

## Reconciliation Impact
- `REVIEW_CORE_DATA` remains active until missing core KPI values are reviewed and applied through a separate workflow.
- This patch only makes the core closure path explicit.

## Remaining Demo Readiness Blockers
- Watchlist sample/review state, valuation gaps, dividend/FCF gaps, provenance gaps, and freshness metadata review remain outside this patch.

## Remaining Decision Readiness Blockers
- Core KPI gaps remain REVIEW while values are missing or only structurally indicated.

## Reason Code Counts
- `CORE_KPI_MISSING`: 4
- `NO_VALUE_CHANGES`: 4
- `REVIEW_CORE_DATA`: 4
- `SEC_IDENTITY_AVAILABLE`: 4

## Recommended Next Patch
`PATCH / DIVIDEND FCF INPUT CONTRACT / REVIEWED EVIDENCE QUEUE / NO IMPUTATION`
