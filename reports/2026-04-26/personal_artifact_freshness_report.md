# Personal Artifact Freshness Report

Generated: 2026-04-26

## 1. Executive Summary

- Artifact drift active: `False`
- Unresolved current artifact drift total: `0`
- Reason codes: `MISSING_METADATA;STALE_DERIVED_ARTIFACT`

This report classifies artifact freshness and drift from existing processed artifacts only. It does not change scores, formulas, fundamentals values, watchlist values, or ranking outputs.

## 2. Input Artifacts

| Label | Path |
| --- | --- |
| evidence_delta_holdings | `data/processed/personal_evidence_applied_downstream_delta_holdings.csv` |
| evidence_delta_summary | `data/processed/personal_evidence_applied_downstream_delta_summary.csv` |
| kpi_tier | `data/processed/personal_kpi_tier_coverage.csv` |
| missing_kpi_summary | `data/processed/personal_missing_kpi_closure_summary.csv` |
| run_manifest | `data/processed/personal_run_manifest.json` |
| run_used_inputs | `data/processed/personal_run_used_inputs.csv` |
| scores | `data/processed/personal_company_scores.csv` |

## 3. Artifact Metadata Inventory

| Artifact | Exists | Rows | Metadata | Freshness | Reasons |
| --- | --- | ---: | --- | --- | --- |
| `evidence_delta_holdings` | `True` | 17 | `MISSING_METADATA` | `MISSING_METADATA` | `MISSING_METADATA` |
| `evidence_delta_summary` | `True` | 18 | `PARTIAL_METADATA` | `MISSING_METADATA` | `MISSING_METADATA` |
| `kpi_tier` | `True` | 17 | `MISSING_METADATA` | `MISSING_METADATA` | `MISSING_METADATA` |
| `missing_kpi_summary` | `True` | 23 | `PARTIAL_METADATA` | `MISSING_METADATA` | `MISSING_METADATA` |
| `run_used_inputs` | `True` | 25 | `PARTIAL_METADATA` | `MISSING_METADATA` | `MISSING_METADATA` |
| `scores` | `True` | 17 | `PARTIAL_METADATA` | `MISSING_METADATA` | `MISSING_METADATA` |

## 4. Status Counter Comparison

| Check | Drift Status | Freshness | Reasons | Observed |
| --- | --- | --- | --- | --- |
| `score_vs_evidence_delta_status_counters` | `REVIEW` | `MISSING_METADATA` | `MISSING_METADATA;STALE_DERIVED_ARTIFACT` | `scores={'OK': 0, 'REVIEW': 6, 'MISSING_DATA': 11, 'BLOCKED': 0}; delta={'OK': 0, 'REVIEW': 0, 'MISSING_DATA': 17, 'BLOCKED': 0}` |

## 5. Freshness Findings

| Metric | Value | Notes |
| --- | --- | --- |
| `artifact_drift_active` | `False` | True only for current unexplained drift. |
| `artifact_drift_explained_by_metadata` | `True` | Counter mismatch explained by missing/stale metadata. |
| `artifact_drift_status__REVIEW` | `7` | Artifact drift status count. |
| `artifact_freshness_status__MISSING_METADATA` | `7` | Artifact freshness status count. |
| `freshness_checks_total` | `7` | Rows in personal_artifact_freshness_checks.csv. |
| `freshness_reason_codes` | `MISSING_METADATA;STALE_DERIVED_ARTIFACT` | Union of freshness reason codes. |
| `unresolved_current_artifact_drift_total` | `0` | Current unexplained counter mismatches with comparable metadata. |
| `warnings_total` | `0` | Missing input warnings. |

## 6. Drift Findings

- Counter mismatches are treated as current `ARTIFACT_DRIFT` only when both artifacts have comparable metadata and the mismatch is not otherwise explained.
- In the current repository state, the score-vs-delta mismatch is classified through missing/stale metadata rather than accepted as current truth.

## 7. Resolved vs Unresolved Drift

- Current unexplained drift: `0`
- Drift explained by metadata/staleness: `True`

## 8. Reconciliation Impact

Reconciliation can consume `personal_artifact_freshness_summary.csv` to replace broad `ARTIFACT_DRIFT` with precise freshness blockers such as `MISSING_METADATA`, `STALE_ARTIFACT`, or `DERIVED_ARTIFACT_DEFERRED`.

## 9. Remaining Demo Readiness Blockers

- Watchlist sample input, valuation-required gaps, core-data review states, dividend/FCF gaps, and provenance gaps remain outside this patch.

## 10. Remaining Decision Readiness Blockers

- Decision readiness remains blocked until valuation, dividend/FCF, core data, provenance, and reviewed watchlist inputs are resolved.

## 11. Recommended Next Patch

`PATCH / VALUATION INPUT CONTRACT / REVIEWED MANUAL EVIDENCE / NO IMPUTATION`
