# CIOS Risk And Control Framework

## Purpose

This framework defines current CIOS risk categories and required controls. Risks
are not considered solved unless there is an artifact, control, validation gate
or accepted non-scope statement.

Allowed current status values:

- `OPERABLE`
- `PARTIAL`
- `CONTRACT_ONLY`
- `KNOWN_GAP`
- `NOT_STARTED`
- `REVIEW_REQUIRED`

## Risk Taxonomy

| risk | description | likely failure mode | required control | evidence artefact | gate/check | owner | current status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| data risk | Inputs may be incomplete, malformed or unreviewed. | Reports look complete while source data is weak. | Schema checks, missing-data flags, input closure. | `docs/MODULE_CONTRACTS.md`; tests under `tests/`. | Targeted unit tests and report checks. | Human Operator / Codex | PARTIAL |
| stale/missing data risk | Existing files may be stale, missing or unknown. | Stale data is treated as current. | Data Freshness contract, thresholds and stage. | `docs/contracts/DATA_FRESHNESS_STALENESS_CONTRACT.md`; `src/data_freshness.py`. | `tests/test_data_freshness.py`. | Codex / Human Operator | PARTIAL |
| instrument identity risk | Tickers, ISINs or names can mismatch. | Evidence attaches to the wrong instrument. | Future Instrument Master contract before production broker path. | Current identity docs and tests are partial. | Identity tests where implemented. | Human Operator | KNOWN_GAP |
| broker import risk | Local broker exports or documents may parse incorrectly. | Holdings or cash state is wrong. | Read-only import, schema checks, no broker writes. | `src/import_broker.py`; `src/traderepublic_documents.py`. | Import/parser tests. | Codex / Human Operator | PARTIAL |
| corporate actions risk | Splits, mergers or symbol changes may be missing. | Historical state and identity drift. | Corporate Actions input contract before replay/outcome. | No canonical contract yet. | None beyond known-gap tracking. | Human Operator | KNOWN_GAP |
| FX/multi-currency risk | Currency exposure may be incomplete. | Portfolio state or performance is misleading. | FX contract before multi-currency decisions. | Limited current evidence. | Future FX tests. | Human Operator | KNOWN_GAP |
| model/ranking risk | Scores/rankings can overstate precision. | Ranking output is treated as an order signal. | Score audit, no formula changes without review, robustness later. | `src/scoring_engine.py`; `docs/architecture/DECISION_QUALITY_LAYER.md`. | Scoring and Decision Quality tests. | Codex / Human Operator | PARTIAL |
| valuation risk | Valuation inputs may be missing or unreviewed. | False confidence in entry timing. | Valuation methodology contract before automation. | `src/personal_valuation_input_contract.py`. | Valuation input tests. | Human Operator | PARTIAL |
| investment decision risk | Process output can be mistaken for final advice. | Human bypasses review discipline. | Constitution, operating model, decision journal. | `docs/governance/CIOS_SYSTEM_CONSTITUTION.md`; `docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md`. | Review queue and report tests. | Human Operator | PARTIAL |
| LLM/agent risk | LLM output may hallucinate or over-authorize. | Codex/external LLM treated as final authority. | Operating model and LLM policy. | `docs/policies/LLM_CODEX_OPERATING_POLICY.md`; this framework. | Docs tests and human review. | Human Operator | PARTIAL |
| release/handoff risk | Handoff metadata can drift from repo state. | External review validates stale package. | Handoff contract, checksum, forbidden scans. | `docs/HANDOFF_CONTRACT.md`; `src/handoff_bundle.py`. | Handoff tests. | Codex / Human Operator | OPERABLE |
| privacy/security risk | Private raw data, paths or secrets leak. | Handoff or commit exposes local data. | Handoff allowlist and content scanner. | `src/handoff_bundle.py`; `docs/governance/EXTERNAL_REPRODUCTION.md`. | Handoff bundle tests. | Codex / Human Operator | PARTIAL |
| data license/commercial risk | Data source terms may not allow product use. | Commercial packaging violates license constraints or public handoff over-shares restricted data. | Data Source Strategy, License Boundary Contract, template validation preflight, later legal/commercial review and runtime enforcement. | `docs/architecture/CIOS_DATA_SOURCE_STRATEGY.md`; `docs/contracts/DATA_SOURCE_LICENSE_BOUNDARY_CONTRACT.md`; `src/data_source_registry_validation.py`; `tests/test_data_source_registry_validation.py`. | Registry-template validation now exists; provider approval, runtime enforcement and legal/commercial review remain open. | Human Operator | PARTIAL |
| compliance/regulatory risk | Advice or automation may trigger obligations. | System becomes automated advice without review. | No automated advice; regulatory review before autonomy. | Constitution; project charter. | Human acceptance gate. | Human Operator | CONTRACT_ONLY |
| operations/recovery risk | Local data or release artifacts can be lost or inconsistent. | Cannot reproduce or roll back. | Git discipline, manifests, future backup/recovery standard. | `docs/CODEX_TASKS/POST_ITERATION_QA.md`; manifests. | Git status and validation logs. | Human Operator | PARTIAL |
| path-dependency / lock-in risk | Early provider/schema choices constrain future design. | Hard-to-reverse adapters or data models. | Evolution guardrails and ADR requirement. | `docs/governance/CIOS_EVOLUTION_GUARDRAILS.md`. | ADR/risk review for irreversible changes. | Human Operator | CONTRACT_ONLY |

## Control Rule

A risk status may move toward `OPERABLE` only when the repo contains at least
one of:

- an accepted contract,
- deterministic code,
- tests or validation gates,
- release/handoff evidence,
- accepted non-scope documentation,
- a human operator acceptance record.

Optimistic architecture text alone is not sufficient.
