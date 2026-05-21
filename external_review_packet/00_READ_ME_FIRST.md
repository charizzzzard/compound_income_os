# Compound Income OS External LLM Review Packet - Portfolio Event Ledger Contract

Dies ist der Einstiegspunkt fuer die externe Delta-Review von Compound Income
OS (CIOS) nach dem Patch:

- commit: `9f4a666490af97bcd85fceb6a6a62327ffc2b73f`
- message: `docs: define portfolio event ledger contract`
- status: `PORTFOLIO_EVENT_LEDGER_CONTRACT_ACCEPTED_WITH_FINDINGS`

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- current_handoff_head: `9f4a666490af97bcd85fceb6a6a62327ffc2b73f`
- current_handoff_short_head: `9f4a666`
- bundle_purpose: `external_llm_review_after_portfolio_event_ledger_contract`
- canonical_review_bundle: `external_review_packet/HANDOFF_LATEST.zip`
- canonical_checksum: `external_review_packet/HANDOFF_LATEST.sha256`
- canonical_context: `external_review_packet/HANDOFF_LATEST_CONTEXT.md`

## Source-of-Truth / Precedence

Bei Konflikten gilt diese Reihenfolge:

1. `external_review_packet/00_READ_ME_FIRST.md`
2. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
3. `external_review_packet/HANDOFF_LATEST.zip`
4. `external_review_packet/HANDOFF_LATEST.sha256`
5. historische Reports nur als Kontext

ZIP-internes `HANDOFF_CONTEXT.md` ist generischer Exporter-Kontext. Wenn es mit
dieser externen Kontextdatei kollidiert, gewinnen die externen Dateien fuer
Head, Scope, SHA, Precedence und Dirty-State-Interpretation.

## Review Scope

Reviewer sollen insbesondere pruefen:

- Portfolio Event Ledger:
  - `docs/contracts/PORTFOLIO_EVENT_LEDGER_CONTRACT.md`
  - `docs/architecture/CIOS_PORTFOLIO_EVENT_LEDGER.md`
  - `docs/architecture/CIOS_PORTFOLIO_EVENT_LEDGER_TEMPLATE.yaml`
- Instrument Master:
  - `docs/contracts/INSTRUMENT_MASTER_CONTRACT.md`
  - `docs/architecture/CIOS_INSTRUMENT_MASTER.md`
  - `docs/architecture/CIOS_INSTRUMENT_MASTER_TEMPLATE.yaml`
- Data Source / License Boundary:
  - `docs/architecture/CIOS_DATA_SOURCE_STRATEGY.md`
  - `docs/contracts/DATA_SOURCE_LICENSE_BOUNDARY_CONTRACT.md`
  - `docs/architecture/CIOS_DATA_SOURCE_REGISTRY_TEMPLATE.yaml`
  - `src/data_source_registry_validation.py`
  - `tests/test_data_source_registry_validation.py`
- Governance/status consistency:
  - `docs/architecture/CIOS_FEATURE_STATUS.yaml`
  - `docs/architecture/CIOS_MATURITY_MODEL.yaml`
  - `docs/architecture/CURRENT_KNOWN_GAPS.md`
  - `docs/governance/CIOS_RISK_AND_CONTROL_FRAMEWORK.md`
  - `docs/governance/EXTERNAL_REPRODUCTION.md`
  - `README.md`
  - `docs/CONTEXT_AND_ROADMAP.md`
  - `docs/MODULE_CONTRACTS.md`

## Dirty-State Interpretation

ZIP-internes `HANDOFF_CONTEXT.md` kann `dirty_worktree_present: True` zeigen,
weil `external_review_packet/HANDOFF_LATEST.sha256` und diese externen
Metadaten nach der ZIP-Erzeugung neu geschrieben wurden. Entscheidend ist der
tracked Source State vor Handoff-Erzeugung und der finale Status nach dem
Handoff-Metadatencommit.

## Explicit Non-Scope

Dieses Packet fuehrt nicht ein:

- produktive Event-Ledger-Datenbank
- Event-Ledger-Runtime
- Broker Parser
- Broker Import Pipeline
- API-Anbindung
- Scraping oder Web-Crawling
- Provider-Adapter
- automatische Transaktionsklassifikation
- Corporate Actions Processing
- FX Engine
- Replay, Backtesting oder Simulation
- Outcome oder Performance Attribution
- Dashboard
- Investmentlogik
- Buy/Sell Recommendations
- Steuerberechnung
- Legal-/Commercial-Freigabe
- Scoring-/Ranking-Aenderung
- Portfolio-Regel-Aenderung
- Runtime-LLM-Agentenlogik

## Reviewer Notes

- Der Portfolio Event Ledger ist Contract und Template only.
- Er akzeptiert keine echten Broker-, Portfolio-, Steuer-, Dividenden- oder
  FX-Events.
- Bestehende Cost-/Tax- und Broker-Dokumentmodule bleiben operative
  Spezialmodule, kein kanonischer Event Ledger.
- Production broker import bleibt blockiert, bis Staging Contract, Validatoren,
  Review Workflow und Tests existieren.
- Replay, Performance Attribution und Outcome Attribution bleiben blockiert, bis
  ein produktiver Event Ledger plus Time-Aware Replay existiert.
