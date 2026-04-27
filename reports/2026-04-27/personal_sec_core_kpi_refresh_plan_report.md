# Personal SEC Core KPI Refresh Plan Report

## 1. Executive Summary
- Affected rows: `4`
- Ready for explicit SEC refresh: `4`
- Mapping review required: `0`
- Network performed: `False`
- Value fetch performed: `False`

## 2. Input Artifacts
- `core_closure_queue`: `data/processed/personal_core_kpi_closure_queue.csv`
- `plan_output`: `data/processed/personal_sec_core_kpi_refresh_plan.csv`
- `sec_identity_apply`: `data/processed/personal_sec_identity_apply_changes.csv`
- `sec_identity_map`: `<private_path>`
- `sec_scope_review`: `data/processed/personal_sec_scope_review.csv`
- `summary_output`: `data/processed/personal_sec_core_kpi_refresh_plan_summary.csv`

## 3. Core KPI Gaps in Scope
| ticker | isin | company_name | missing_core_kpis |
| --- | --- | --- | --- |
| US02079K3059 | US02079K3059 | Alphabet Inc. Reg. Shs Cap.Stk Cl. A DL-,001 | gross_margin; operating_margin; revenue_cagr_5y; share_count_cagr_5y |
| US22788C1053 | US22788C1053 | Crowdstrike Holdings Inc Registered Shs Cl.A DL-,0005 | eps_cagr_5y; gross_margin; operating_margin; revenue_cagr_5y; share_count_cagr_5y |
| US8522341036 | US8522341036 | Block Inc. Registered Shs Class A | gross_margin; operating_margin; revenue_cagr_5y |
| US92826C8394 | US92826C8394 | VISA Inc. Reg. Shares Class A DL -,0001 | eps_cagr_5y; gross_margin; revenue_cagr_5y; share_count_cagr_5y |

## 4. SEC Identity Readiness
| ticker | sec_identity_status | sec_refresh_plan_status |
| --- | --- | --- |
| US02079K3059 | `APPROVED_IDENTITY` | `READY_FOR_EXPLICIT_SEC_REFRESH` |
| US22788C1053 | `APPROVED_IDENTITY` | `READY_FOR_EXPLICIT_SEC_REFRESH` |
| US8522341036 | `APPROVED_IDENTITY` | `READY_FOR_EXPLICIT_SEC_REFRESH` |
| US92826C8394 | `APPROVED_IDENTITY` | `READY_FOR_EXPLICIT_SEC_REFRESH` |

## 5. KPI-to-SEC Mapping Readiness
| ticker | mapping_status | mapping_review_required | candidate_fact_tags |
| --- | --- | --- | --- |
| US02079K3059 | `MAPPED` | `no` | `GrossProfit; OperatingIncomeLoss; RevenueFromContractWithCustomerExcludingAssessedTax; Revenues; SalesRevenueNet; WeightedAverageNumberOfDilutedSharesOutstanding` |
| US22788C1053 | `MAPPED` | `no` | `EarningsPerShareDiluted; GrossProfit; OperatingIncomeLoss; RevenueFromContractWithCustomerExcludingAssessedTax; Revenues; SalesRevenueNet; WeightedAverageNumberOfDilutedSharesOutstanding` |
| US8522341036 | `MAPPED` | `no` | `GrossProfit; OperatingIncomeLoss; RevenueFromContractWithCustomerExcludingAssessedTax; Revenues; SalesRevenueNet` |
| US92826C8394 | `MAPPED` | `no` | `EarningsPerShareDiluted; GrossProfit; RevenueFromContractWithCustomerExcludingAssessedTax; Revenues; SalesRevenueNet; WeightedAverageNumberOfDilutedSharesOutstanding` |

## 6. Refresh Plan
- Rows marked `READY_FOR_EXPLICIT_SEC_REFRESH` have approved identities and mapped KPI fact candidates.
- Rows marked `MAPPING_REVIEW_REQUIRED` need mapping review before any explicit SEC refresh.
- This report is a plan only and does not fetch or apply values.

## 7. Network Guardrail
- `network_performed=False`.
- No `--allow-network` path was executed.
- No SEC CompanyFacts HTTP request was made.

## 8. No-Value-Change Guardrail
- `value_fetch_performed=False`.
- `evidence_apply_performed=False`.
- `master_mutation_performed=False`.
- `score_mutation_performed=False`.

## 9. Future Explicit Refresh Requirements
- Approved SEC identities must be present.
- A SEC user agent is required.
- A future refresh must use an explicit network gate.
- Evidence review/apply must remain a separate step.

## 10. Readiness Impact
- `REVIEW_CORE_DATA` is not resolved by this plan.
- Plan-ready status is visible in `personal_sec_core_kpi_refresh_plan_summary.csv`.

## 11. Remaining Blockers
- `MISSING_VALUATION_REQUIRED`
- `MISSING_DIVIDEND_FCF_REQUIRED`
- `PROVENANCE_INCOMPLETE`
- `REVIEW_CORE_DATA`
- `WATCHLIST_SAMPLE_INPUT`
- `WATCHLIST_REVIEW_OR_MISSING_DATA`

## 12. Recommended Next Patch
`PATCH / SEC REFRESH COMMAND PREFLIGHT / EXPLICIT NETWORK GATES / NO FETCH BY DEFAULT`

## Reason Code Counts
- `ALLOW_NETWORK_REQUIRED_FOR_FUTURE_REFRESH`: 4
- `CORE_KPI_MISSING`: 4
- `NO_EVIDENCE_APPLY`: 4
- `NO_MASTER_MUTATION`: 4
- `NO_NETWORK_BY_DEFAULT`: 4
- `NO_SCORE_MUTATION`: 4
- `NO_VALUE_FETCH`: 4
- `READY_FOR_EXPLICIT_SEC_REFRESH`: 4
- `SEC_IDENTITY_AVAILABLE`: 4
- `SEC_USER_AGENT_REQUIRED_FOR_FUTURE_REFRESH`: 4
