# Personal Monthly Action Schema Report

Generated: 2026-04-26

## 1. Executive Summary

- Implementation path: `COMPANION_ADAPTER`
- Monthly rows: `18`
- Compatibility rows: `18`
- Monthly schema drift resolved: `True`
- Forbidden monthly_action values: `0`

This report creates a neutral `monthly_action` compatibility layer from existing monthly artifacts only. It does not change scores, formulas, fundamentals values, allocations, or ranking order.

## 2. Input Artifacts

- Monthly input: `data/processed/personal_monthly_buy_ranking.csv`
- Compatibility output: `data/processed/personal_monthly_action_compatibility.csv`
- Summary output: `data/processed/personal_monthly_action_compatibility_summary.csv`

## 3. Existing Monthly Schema

- Has `target_action`: `True`
- Has `allocation_status`: `True`
- Has `monthly_action`: `False`

`target_action` and `allocation_status` remain legacy/internal compatibility fields. The new product-facing action language is the neutral `monthly_action` field in the companion artifact.

## 4. Chosen Implementation Path

Option B: companion/adapter artifact. This avoids changing the dirty pre-existing monthly ranking engine or the legacy monthly CSV contract in this patch.

## 5. Mapping Rules

| Legacy condition | Neutral monthly_action |
| --- | --- |
| valuation review/missing in action, allocation, or constraints | `WAIT_FOR_VALUATION` |
| coverage review/missing in action, allocation, or constraints | `WAIT_FOR_COVERAGE` |
| `REVIEW_CORE_DATA` or `REVIEW_FCF_DATA` | `REVIEW_DATA` |
| blocked/not eligible allocation | `NOT_READY` |
| legacy do-not-enter-candidate action | `NOT_READY` |
| cash/hold state | `NO_ACTION` |
| legacy add/top-up candidate | `ADD_CANDIDATE_REVIEW` |
| missing inputs | `NOT_AVAILABLE` |

## 6. Generated Monthly Action Values

| monthly_action | Count |
| --- | ---: |
| `NO_ACTION` | 1 |
| `WAIT_FOR_VALUATION` | 17 |

## 7. Advice-Language Guardrail

The new `monthly_action` field permits only neutral review/wait/block/no-action states. Legacy/internal filenames and columns may still contain historical wording, but no new product-facing action value uses order, execution, trade, or direct advice language.

## 8. Reconciliation Impact

Reconciliation can treat `MONTHLY_SCHEMA_DRIFT` as resolved when `monthly_action_compatibility_available=True`, `monthly_schema_drift_resolved=True`, and forbidden monthly action count is zero.

## 9. Remaining Demo Readiness Blockers

- Artifact drift, sample watchlist input, valuation gaps, core-data review states, and provenance gaps remain outside this schema patch.

## 10. Remaining Decision Readiness Blockers

- This patch does not make any holding decision-ready. It only stabilizes neutral action terminology for downstream consumers.

## 11. Recommended Next Patch

`PATCH / WATCHLIST SAMPLE INPUT GATE / DEMO_ONLY LABELING / NO VALUE CHANGES`

## Compatibility Sample

| rank | ticker | monthly_action | reason |
| --- | --- | --- | --- |
| `1` | `HOLD_CASH` | `NO_ACTION` | `LEGACY_TARGET_ACTION_HOLD_CASH` |
| `2` | `IE00BP3QZ825` | `WAIT_FOR_VALUATION` | `VALUATION_REVIEW_OR_MISSING` |
| `3` | `US5949181045` | `WAIT_FOR_VALUATION` | `VALUATION_REVIEW_OR_MISSING` |
| `4` | `US0378331005` | `WAIT_FOR_VALUATION` | `VALUATION_REVIEW_OR_MISSING` |
| `5` | `US0394831020` | `WAIT_FOR_VALUATION` | `VALUATION_REVIEW_OR_MISSING` |
