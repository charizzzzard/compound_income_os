# Compound Income OS External LLM Review Packet - Event Ledger Template Validation

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach dem Patch:

- commit: `6f7df408cba600b397eadb7218a1cfceed0108e3`
- message: `feat: add portfolio event ledger template validation`
- status: `EVENT_LEDGER_TEMPLATE_VALIDATION_ACCEPTED_WITH_FINDINGS`

Dieses Packet superseded aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck.

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- implementation_head: `6f7df408cba600b397eadb7218a1cfceed0108e3`
- implementation_short_head: `6f7df40`
- current_handoff_head: `6f7df408cba600b397eadb7218a1cfceed0108e3`
- current_handoff_short_head: `6f7df40`
- bundle_purpose: `external_review_after_portfolio_event_ledger_template_validation`
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
`external_review_packet/HANDOFF_LATEST_CONTEXT.md` kollidiert, gewinnt die
externe Kontextdatei fuer Packet-Metadaten, Review-Scope, Precedence,
Dirty-State-Interpretation und Operator-/Reviewer-Instruktionen.

## Reviewer Instructions

- Verwende volle repo-relative Pfade in Findings.
- Inferiere keine ausgelassenen privaten, raw, Broker- oder Provider-Dateien.
- Inferiere keine Production-Event-Ledger-Readiness.
- Inferiere keine Broker-Import-Readiness.
- Inferiere keine Replay-, Backtesting- oder Outcome-Attribution-Readiness.
- Behandle Template Validation nicht als echte Event-Acceptance.
- Unterscheide dokumentierte Maturity von Runtime Enforcement.
- Unterscheide tatsaechlich ausgefuehrte Tests von Full-Suite-Validation.
- Erhalte die Non-Scope-Grenzen.
- Fehlende, stale oder unknown Daten muessen sichtbar bleiben.
- Keine stille Imputation, keine Investment Advice und keine Order Execution.

## Review Scope

Reviewer sollen insbesondere pruefen:

- Portfolio Event Ledger Template Validation:
  - `src/portfolio_event_ledger_validation.py`
  - `tests/test_portfolio_event_ledger_validation.py`
  - `docs/architecture/CIOS_PORTFOLIO_EVENT_LEDGER_TEMPLATE.yaml`
- Portfolio Event Ledger Contract/Architecture:
  - `docs/contracts/PORTFOLIO_EVENT_LEDGER_CONTRACT.md`
  - `docs/architecture/CIOS_PORTFOLIO_EVENT_LEDGER.md`
- Governance/status consistency:
  - `docs/architecture/CIOS_FEATURE_STATUS.yaml`
  - `docs/architecture/CIOS_MATURITY_MODEL.yaml`
  - `docs/architecture/CURRENT_KNOWN_GAPS.md`
  - `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
  - `docs/governance/EXTERNAL_REPRODUCTION.md`
  - `docs/governance/CIOS_RISK_AND_CONTROL_FRAMEWORK.md`
  - `docs/MODULE_CONTRACTS.md`
  - `docs/CONTEXT_AND_ROADMAP.md`
  - `README.md`

## Explicit Non-Scope

Dieses Packet fuehrt nicht ein:

- produktive Event-Ledger-Datenbank
- Event-Ledger-Runtime
- Broker Import
- Broker Parser
- Provider Adapter
- API-Anbindung
- Scraping oder Web-Crawling
- automatische Transaktionsklassifikation
- Corporate Actions Engine
- FX Engine
- Replay, Backtesting oder Simulation
- Outcome Attribution
- Dashboard
- Investmentlogik
- Buy/Sell Recommendation Aenderungen
- Steuerberechnung
- Legal-/Commercial-Freigabe
- Scoring-/Ranking-Aenderung
- Portfolio-Regel-Aenderung
- Runtime-LLM-Agentenlogik

## Reviewer Notes

- Der Portfolio Event Ledger Template Validator ist read-only.
- Der Validator prueft Template-Struktur und Boundary-Regeln, nicht echte
  Broker- oder Portfolio-Events.
- Bestehende Broker-/Import-/Cost-/Tax-/History-Module sind keine kanonische
  Portfolio-Event-Ledger-Runtime.
- Template-Matrizen validieren Template-Beispiele, nicht produktive Events.
- Production broker import bleibt blockiert, bis Broker Import Staging
  Contract, Runtime-Validatoren, Review Workflow und Tests existieren.
