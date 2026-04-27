# Personal SEC Refresh Preflight Report

## 1. Executive Summary
- Plan rows: `4`
- Ready for explicit network run: `0`
- Review required: `4`
- Blocked: `0`
- Future refresh command status: `AVAILABLE`
- Network performed: `False`

## 2. Input SEC Plan
- `fetch_module`: `src/external_sec_companyfacts_fetch.py`
- `preflight_output`: `data/processed/personal_sec_refresh_preflight.csv`
- `refresh_cli_module`: `src/personal_sec_refresh_pipeline.py`
- `sec_identity_map`: `<private_path>`
- `sec_plan`: `data/processed/personal_sec_core_kpi_refresh_plan.csv`
- `sec_plan_summary`: `data/processed/personal_sec_core_kpi_refresh_plan_summary.csv`
- `summary_output`: `data/processed/personal_sec_refresh_preflight_summary.csv`

## 3. Identity Map Preflight
- Identity map present: `True`
- Identity schema valid: `True`
- Private identity-map rows, CIKs, entity names, and notes are not rendered.

## 4. SEC User-Agent / Network Gate
- SEC user-agent present: `False`
- Network gate required for future refresh: `True`
- No network gate is enabled or used by this preflight.

## 5. Fetch Module / CLI Availability
| ticker | preflight_status | fetch_module_status | refresh_cli_status | reason_codes |
| --- | --- | --- | --- | --- |
| US02079K3059 | `REVIEW_REQUIRED` | `AVAILABLE` | `AVAILABLE` | `ALLOW_NETWORK_REQUIRED_FOR_FUTURE_REFRESH;FETCH_MODULE_AVAILABLE;NO_EVIDENCE_APPLY;NO_FETCH_PERFORMED;NO_MASTER_MUTATION;NO_NETWORK_BY_DEFAULT;NO_NETWORK_PERFORMED;NO_RAW_SEC_SNAPSHOT_WRITTEN;NO_SCORE_MUTATION;REFRESH_CLI_AVAILABLE;REVIEW_REQUIRED;SEC_IDENTITY_MAP_PRESENT;SEC_REFRESH_PLAN_READY;SEC_USER_AGENT_MISSING` |
| US22788C1053 | `REVIEW_REQUIRED` | `AVAILABLE` | `AVAILABLE` | `ALLOW_NETWORK_REQUIRED_FOR_FUTURE_REFRESH;FETCH_MODULE_AVAILABLE;NO_EVIDENCE_APPLY;NO_FETCH_PERFORMED;NO_MASTER_MUTATION;NO_NETWORK_BY_DEFAULT;NO_NETWORK_PERFORMED;NO_RAW_SEC_SNAPSHOT_WRITTEN;NO_SCORE_MUTATION;REFRESH_CLI_AVAILABLE;REVIEW_REQUIRED;SEC_IDENTITY_MAP_PRESENT;SEC_REFRESH_PLAN_READY;SEC_USER_AGENT_MISSING` |
| US8522341036 | `REVIEW_REQUIRED` | `AVAILABLE` | `AVAILABLE` | `ALLOW_NETWORK_REQUIRED_FOR_FUTURE_REFRESH;FETCH_MODULE_AVAILABLE;NO_EVIDENCE_APPLY;NO_FETCH_PERFORMED;NO_MASTER_MUTATION;NO_NETWORK_BY_DEFAULT;NO_NETWORK_PERFORMED;NO_RAW_SEC_SNAPSHOT_WRITTEN;NO_SCORE_MUTATION;REFRESH_CLI_AVAILABLE;REVIEW_REQUIRED;SEC_IDENTITY_MAP_PRESENT;SEC_REFRESH_PLAN_READY;SEC_USER_AGENT_MISSING` |
| US92826C8394 | `REVIEW_REQUIRED` | `AVAILABLE` | `AVAILABLE` | `ALLOW_NETWORK_REQUIRED_FOR_FUTURE_REFRESH;FETCH_MODULE_AVAILABLE;NO_EVIDENCE_APPLY;NO_FETCH_PERFORMED;NO_MASTER_MUTATION;NO_NETWORK_BY_DEFAULT;NO_NETWORK_PERFORMED;NO_RAW_SEC_SNAPSHOT_WRITTEN;NO_SCORE_MUTATION;REFRESH_CLI_AVAILABLE;REVIEW_REQUIRED;SEC_IDENTITY_MAP_PRESENT;SEC_REFRESH_PLAN_READY;SEC_USER_AGENT_MISSING` |

## 6. Future Explicit Refresh Command Plan
- Stable module path detected only when the committed module file exposes explicit `--allow-network` and `--sec-user-agent` gates.
- Future refresh must provide approved identity map path, SEC user-agent, and explicit allow-network flag.
- Expected follow-up remains separate: SEC snapshot, evidence review, evidence compose/apply, downstream run.

## 7. Network Guardrail
- `network_performed=False`.
- `fetch_performed=False`.
- No HTTP request, CompanyFacts download, or raw SEC snapshot write was performed.

## 8. No-Value-Change Guardrail
- `raw_sec_snapshot_written=False`.
- `evidence_apply_performed=False`.
- `master_mutation_performed=False`.
- `score_mutation_performed=False`.

## 9. Readiness Impact
- `REVIEW_CORE_DATA` is not resolved by preflight.
- Preflight only confirms whether a later explicit network run would be gate-ready.

## 10. Remaining Blockers
- `MISSING_VALUATION_REQUIRED`
- `MISSING_DIVIDEND_FCF_REQUIRED`
- `PROVENANCE_INCOMPLETE`
- `REVIEW_CORE_DATA`
- `WATCHLIST_SAMPLE_INPUT`
- `WATCHLIST_REVIEW_OR_MISSING_DATA`

## 11. Recommended Next Patch
`PATCH / DASHBOARD READINESS PANEL / REAL BLOCKER DATA / NO DUMMY CLAIMS`
