# Personal Score Audit Provenance Report

Generated: 2026-04-26

## 1. Executive Summary

- Implementation path: `COMPANION_AUDIT`
- Provenance rows: `476`
- Trusted: `28`
- Partial: `0`
- Missing: `252`
- Ambiguous: `0`
- Not applicable: `196`
- Source metadata propagated rows: `28`

This companion audit propagates source metadata beside score-relevant KPI values without changing the existing score audit, scores, formulas, weights, or fundamentals values.

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

## 3. Chosen Implementation Path

Companion Audit. The existing `personal_score_audit.csv` remains unchanged to avoid breaking downstream consumers. `personal_score_audit_provenance.csv` carries one row per score-relevant KPI per holding with source metadata and provenance status.

## 4. Source Metadata Coverage

| Metric | Value | Notes |
| --- | --- | --- |
| `holdings_with_incomplete_provenance_total` | `10` | Distinct holdings with PARTIAL, MISSING, or AMBIGUOUS provenance. |
| `implementation_path` | `COMPANION_AUDIT` | Existing personal_score_audit.csv contract remains unchanged. |
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
| `provenance_rows_total` | `476` | Rows in personal_score_audit_provenance.csv. |
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
| `source_layer__NOT_APPLICABLE` | `196` | Source layer count. |
| `source_layer__NOT_FOUND` | `252` | Source layer count. |
| `source_metadata_propagated_total` | `28` | Rows carrying at least one source metadata field. |
| `warnings_total` | `0` | Missing input warnings. |

## 5. KPI Tier Coverage by Provenance Status

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

## 6. Holdings with Missing Provenance

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

## 7. Holdings with Trusted Provenance

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
| `US2546871060` | `US2546871060` | `revenue_cagr_5y` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |
| `US2546871060` | `US2546871060` | `share_count_cagr_5y` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |
| `US5949181045` | `US5949181045` | `eps_cagr_5y` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |
| `US5949181045` | `US5949181045` | `gross_margin` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |
| `US5949181045` | `US5949181045` | `operating_margin` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |
| `US5949181045` | `US5949181045` | `revenue_cagr_5y` | `EVIDENCE_REGISTRY` | `SOURCE_MATCHED` |

## 8. Ambiguous Cases

None.

## 9. Compatibility Notes

- Existing `personal_score_audit.csv` is not modified.
- Existing score formulas, weights, and KPI values are not modified.
- Downstream tools can join by `ticker`, `isin`, and `kpi_name` when they need source metadata.

## 10. Impact on Demo Readiness

`provenance_incomplete_flag` remains available for later reconciliation integration. Demo readiness remains REVIEW/BLOCKED while missing provenance remains visible.

## 11. Impact on Decision Readiness

Decision readiness remains blocked for score-relevant KPIs with MISSING, PARTIAL, or AMBIGUOUS provenance. This report does not change candidate status.

## 12. Recommended Next Patch

PATCH / MONTHLY SCHEMA STABILIZATION / TARGET_ACTION TO MONTHLY_ACTION COMPATIBILITY / NO ADVICE LANGUAGE
