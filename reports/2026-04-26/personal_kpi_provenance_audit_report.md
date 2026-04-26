# Personal KPI Provenance Audit Report

Generated: 2026-04-26

## 1. Executive Summary

- Audit rows: `476`
- Trusted: `28`
- Partial: `0`
- Missing: `252`
- Ambiguous: `0`
- Not applicable: `196`
- Provenance incomplete flag: `True`

This audit materializes score-relevant KPI provenance only. It does not add values, impute missing KPIs, change score formulas, or call external APIs.

## 2. Input Artifacts

| Label | Path |
| --- | --- |
| evidence_applied_master | `data/processed/personal_fundamentals_master_evidence_applied.csv` |
| evidence_registry | `data/processed/personal_fundamentals_evidence_registry.csv` |
| metric_definitions | `configs/fundamentals_metric_definitions.yaml` |
| overlay | `data/raw/personal_fundamentals_overlay.csv` |
| profiled_master | `data/processed/personal_fundamentals_master_profiled.csv` |
| raw_master | `data/raw/personal_fundamentals_master.csv` |
| run_manifest | `data/processed/personal_run_manifest.json` |
| run_used_inputs | `data/processed/personal_run_used_inputs.csv` |
| score_audit | `data/processed/personal_score_audit.csv` |

## 3. Provenance Coverage Summary

| Metric | Value | Notes |
| --- | --- | --- |
| `audit_rows_total` | `476` | Rows in personal_kpi_provenance_audit.csv. |
| `holdings_with_incomplete_provenance_total` | `10` | Distinct holdings with PARTIAL, MISSING, or AMBIGUOUS provenance. |
| `kpi_required_status__ADVANCED_OPTIONAL__MISSING` | `50` | KPI tier by provenance status count. |
| `kpi_required_status__ADVANCED_OPTIONAL__NOT_APPLICABLE` | `35` | KPI tier by provenance status count. |
| `kpi_required_status__CORE_QUALITY_REQUIRED__MISSING` | `22` | KPI tier by provenance status count. |
| `kpi_required_status__CORE_QUALITY_REQUIRED__NOT_APPLICABLE` | `35` | KPI tier by provenance status count. |
| `kpi_required_status__CORE_QUALITY_REQUIRED__TRUSTED` | `28` | KPI tier by provenance status count. |
| `kpi_required_status__DIVIDEND_FCF_REQUIRED__MISSING` | `30` | KPI tier by provenance status count. |
| `kpi_required_status__DIVIDEND_FCF_REQUIRED__NOT_APPLICABLE` | `21` | KPI tier by provenance status count. |
| `kpi_required_status__UNKNOWN__MISSING` | `130` | KPI tier by provenance status count. |
| `kpi_required_status__UNKNOWN__NOT_APPLICABLE` | `91` | KPI tier by provenance status count. |
| `kpi_required_status__VALUATION_REQUIRED__MISSING` | `20` | KPI tier by provenance status count. |
| `kpi_required_status__VALUATION_REQUIRED__NOT_APPLICABLE` | `14` | KPI tier by provenance status count. |
| `provenance_incomplete_flag` | `True` | Can feed future reconciliation PROVENANCE_INCOMPLETE. |
| `provenance_status__AMBIGUOUS` | `0` | Provenance status count. |
| `provenance_status__MISSING` | `252` | Provenance status count. |
| `provenance_status__NOT_APPLICABLE` | `196` | Provenance status count. |
| `provenance_status__PARTIAL` | `0` | Provenance status count. |
| `provenance_status__TRUSTED` | `28` | Provenance status count. |
| `reason_code__EVIDENCE_APPLIED_VALUE_MISSING` | `252` | Reason code count. |
| `reason_code__EVIDENCE_REGISTRY_MISSING` | `252` | Reason code count. |
| `reason_code__PROFILE_NOT_STANDARD` | `196` | Reason code count. |
| `reason_code__SOURCE_MATCHED` | `28` | Reason code count. |
| `source_layer__EVIDENCE_REGISTRY` | `28` | Source layer count. |
| `source_layer__NOT_FOUND` | `448` | Source layer count. |
| `warnings_total` | `0` | Missing input warnings. |

## 4. KPI Tier Coverage by Provenance Status

| Metric | Value |
| --- | --- |
| `kpi_required_status__ADVANCED_OPTIONAL__MISSING` | `50` |
| `kpi_required_status__ADVANCED_OPTIONAL__NOT_APPLICABLE` | `35` |
| `kpi_required_status__CORE_QUALITY_REQUIRED__MISSING` | `22` |
| `kpi_required_status__CORE_QUALITY_REQUIRED__NOT_APPLICABLE` | `35` |
| `kpi_required_status__CORE_QUALITY_REQUIRED__TRUSTED` | `28` |
| `kpi_required_status__DIVIDEND_FCF_REQUIRED__MISSING` | `30` |
| `kpi_required_status__DIVIDEND_FCF_REQUIRED__NOT_APPLICABLE` | `21` |
| `kpi_required_status__UNKNOWN__MISSING` | `130` |
| `kpi_required_status__UNKNOWN__NOT_APPLICABLE` | `91` |
| `kpi_required_status__VALUATION_REQUIRED__MISSING` | `20` |
| `kpi_required_status__VALUATION_REQUIRED__NOT_APPLICABLE` | `14` |

## 5. Holdings with Missing Provenance

| Ticker | ISIN | KPI | Layer | Reason |
| --- | --- | --- | --- | --- |
| `US02079K3059` | `US02079K3059` | `buyback_yield` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `dividend_cagr_5y` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `dividend_streak_years` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `dividend_yield_current_pct` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `dividend_yield_hist_pct` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `drawdown_from_high_pct` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `ev_ebit_current` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `ev_ebit_hist` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `expected_return_pct` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `fcf_margin` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `fcf_per_share_cagr_5y` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `fcf_yield_current_pct` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `fcf_yield_hist_pct` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `gross_margin` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `interest_coverage` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `net_debt_to_ebitda` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `normalized_fcf_yield_pct` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `operating_margin` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `payout_ratio_eps` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |
| `US02079K3059` | `US02079K3059` | `payout_ratio_fcf` | `NOT_FOUND` | `EVIDENCE_REGISTRY_MISSING;EVIDENCE_APPLIED_VALUE_MISSING` |

## 6. Holdings with Partial Provenance

None.

## 7. Ambiguous Source Cases

None.

## 8. Trusted KPI Examples

| Ticker | ISIN | KPI | Layer | Reason |
| --- | --- | --- | --- | --- |
| `US02079K3059` | `US02079K3059` | `eps_cagr_5y` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |
| `US0378331005` | `US0378331005` | `eps_cagr_5y` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |
| `US0378331005` | `US0378331005` | `gross_margin` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |
| `US0378331005` | `US0378331005` | `operating_margin` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |
| `US0378331005` | `US0378331005` | `revenue_cagr_5y` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |
| `US0378331005` | `US0378331005` | `share_count_cagr_5y` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |
| `US0394831020` | `US0394831020` | `eps_cagr_5y` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |
| `US0394831020` | `US0394831020` | `gross_margin` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |
| `US0394831020` | `US0394831020` | `share_count_cagr_5y` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |
| `US2546871060` | `US2546871060` | `operating_margin` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |

## 9. Impact on Demo Readiness

Demo readiness remains REVIEW/BLOCKED while KPI values cannot be traced to source references for all decision-relevant rows. The summary metric `provenance_incomplete_flag` is intended for later reconciliation integration.

## 10. Impact on Decision Readiness

Decision readiness remains BLOCKED for KPIs with `MISSING`, `PARTIAL`, or `AMBIGUOUS` provenance. This is separate from KPI value availability and does not change scoring output.

## 11. Recommended Next Patch

Extend evidence/apply artifacts so score audit rows can carry per-KPI `source_reference`, `source_type`, and `source_as_of_date` without changing KPI values.
