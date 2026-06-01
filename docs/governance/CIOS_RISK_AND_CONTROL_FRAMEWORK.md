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
| instrument identity risk | Tickers, ISINs, broker symbols, provider IDs or names can mismatch across venues, currencies, share classes and lifecycle states. | Evidence, holdings or future events attach to the wrong instrument. | Instrument Master Contract and read-only template validation now define canonical identity, conflict rules and mapping boundaries; future production registry and broker/provider mapping review are still required. | `docs/contracts/INSTRUMENT_MASTER_CONTRACT.md`; `docs/architecture/CIOS_INSTRUMENT_MASTER.md`; `docs/architecture/CIOS_INSTRUMENT_MASTER_TEMPLATE.yaml`; `src/instrument_master_validation.py`; `tests/test_instrument_master_validation.py`. | No production broker import before Instrument Master production registry acceptance plus Portfolio Event Ledger and staging-promotion controls; no performance attribution before Event Ledger and Time-Aware Replay. | Human Operator | PARTIAL |
| portfolio event ledger risk | Future transactions, cashflows, fees, taxes, transfers or corporate-action candidates may be non-auditable or overwritten. | Replay, performance or outcome review uses incomplete or mutable event history. | Portfolio Event Ledger Contract, Instrument Master Contract, Broker Import Staging Contract and read-only template validation preflights; runtime ledger validation, correction/reversal engine and staging-to-ledger promotion remain future controls. | `docs/contracts/PORTFOLIO_EVENT_LEDGER_CONTRACT.md`; `docs/architecture/CIOS_PORTFOLIO_EVENT_LEDGER.md`; `docs/architecture/CIOS_PORTFOLIO_EVENT_LEDGER_TEMPLATE.yaml`; `src/portfolio_event_ledger_validation.py`; `tests/test_portfolio_event_ledger_validation.py`; `docs/contracts/BROKER_IMPORT_STAGING_CONTRACT.md`; `src/broker_import_staging_validation.py`. | No production broker import before staging-to-ledger promotion contract, review workflow, accepted fixtures and runtime tests; no replay before event ledger plus snapshot/as_of semantics. | Human Operator | PARTIAL |
| broker import risk | Local broker exports or documents may parse incorrectly. | Holdings, cash state or future event candidates are wrong. | Read-only import, schema checks, no broker writes, Instrument Master validation preflight, Broker Import Staging Contract/template validation and Portfolio Event Ledger Contract/template validation. | `src/import_broker.py`; `src/traderepublic_documents.py`; `docs/contracts/INSTRUMENT_MASTER_CONTRACT.md`; `docs/contracts/BROKER_IMPORT_STAGING_CONTRACT.md`; `docs/contracts/PORTFOLIO_EVENT_LEDGER_CONTRACT.md`; `src/broker_import_staging_validation.py`. | Existing read-only import/cost/tax modules are not production Broker Import Staging; production broker import path is blocked until staging-to-ledger promotion, review workflow, accepted fixtures and runtime tests exist. | Codex / Human Operator | PARTIAL |
| corporate actions risk | Splits, mergers or symbol changes may be missing. | Historical state and identity drift. | Corporate Actions input contract before replay/outcome. | No canonical contract yet. | None beyond known-gap tracking. | Human Operator | KNOWN_GAP |
| FX/multi-currency risk | Currency exposure may be incomplete. | Portfolio state or performance is misleading. | FX contract before multi-currency decisions. | Limited current evidence. | Future FX tests. | Human Operator | KNOWN_GAP |
| model/ranking risk | Scores/rankings can overstate precision. | Ranking output is treated as an order signal. | Score audit, no formula changes without review, robustness later. | `src/scoring_engine.py`; `docs/architecture/DECISION_QUALITY_LAYER.md`. | Scoring and Decision Quality tests. | Codex / Human Operator | PARTIAL |
| valuation risk | Valuation inputs may be missing or unreviewed. | False confidence in entry timing. | Valuation methodology contract before automation. | `src/personal_valuation_input_contract.py`. | Valuation input tests. | Human Operator | PARTIAL |
| performance/outcome attribution risk | Performance or outcome claims may be computed without accepted events, time-aware replay or decision linkage. | Attribution explains results from incomplete snapshots or non-auditable history. | Portfolio Event Ledger Contract, future Time-Aware Replay Contract and future outcome attribution contract. | `docs/contracts/PORTFOLIO_EVENT_LEDGER_CONTRACT.md`; `docs/architecture/CIOS_PORTFOLIO_EVENT_LEDGER.md`. | No performance/outcome attribution before Event Ledger, snapshots/as_of rules and Time-Aware Replay exist. | Human Operator | CONTRACT_ONLY |
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
