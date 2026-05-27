# Compound Income OS External LLM Review Packet - Governance Handoff Hygiene Cleanup

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach dem Governance-Automation-Patch:

- commit: `8505a59036e4bc86f37b9ae18e512e0d314edb6d`
- message: `chore: harden governance handoff hygiene`
- status: `GOVERNANCE_HANDOFF_HYGIENE_ACCEPTED_WITH_FINDINGS`

Dieses Packet superseded aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck.

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- implementation_head: `8505a59036e4bc86f37b9ae18e512e0d314edb6d`
- implementation_short_head: `8505a59`
- current_handoff_head: `8505a59036e4bc86f37b9ae18e512e0d314edb6d`
- current_handoff_short_head: `8505a59`
- handoff_metadata_commit: `pending_until_metadata_commit`
- handoff_metadata_commit_note: `metadata commit is created after this file is written; use git HEAD after metadata commit or the operator final report for the exact metadata commit hash`
- bundle_purpose: `external_review_after_governance_handoff_hygiene_cleanup`
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
- Behandle `src.release_ci_environment_parity_review` als read-only
  Environment-Parity-Check, nicht als CI-Green, nicht als Release-Akzeptanz
  und nicht als Product-/Production-Readiness.
- Behandle `src.clean_room_reproduction_review` als read-only
  Packet-Reproduction-Check, nicht als Release-Akzeptanz, nicht als
  CI-Clean-Room-Automation und nicht als Runtime Enforcement.
- Behandle die Handoff-Hygiene-Aenderung als Scanner-/Metadaten-Haertung,
  nicht als neues Release-Gate und nicht als Runtime Enforcement.
- Behandle `src.external_review_cross_patch_regression` als read-only
  Governance-Regression-Check.
- Unterscheide `RECORDED` Handoff-Commands von tatsaechlich ausgefuehrten
  Pass/Fail-Ergebnissen.
- Unterscheide Tool-Verfuegbarkeit von Command-Erfolg.
- Inferiere keine Release-, Product-, Investment-, Broker-Import-, Replay-,
  Backtesting-, Dashboard- oder Outcome-Attribution-Readiness.
- Fehlende, stale oder unknown Daten muessen sichtbar bleiben.
- Keine stille Imputation, keine stille Ueberschreibung akzeptierter Fakten,
  keine Investment Advice und keine Order Execution.

## Review Scope

Reviewer sollen insbesondere pruefen:

- Release CI Environment Parity Review:
  - `src/release_ci_environment_parity_review.py`
  - `tests/test_release_ci_environment_parity_review.py`
  - `data/processed/release_ci_environment_parity_review.csv`, falls im ZIP-Profil enthalten
  - `reports/2026-05-21/release_ci_environment_parity_review_report.md`, falls im ZIP-Profil enthalten
- Clean-Room Reproduction Review:
  - `src/clean_room_reproduction_review.py`
  - `tests/test_clean_room_reproduction_review.py`
  - `src/handoff_bundle.py`
  - `tests/test_handoff_bundle.py`
- Cross-Patch Regression Governance Check:
  - `src/external_review_cross_patch_regression.py`
  - `tests/test_external_review_cross_patch_regression.py`
- External Review Coverage Governance:
  - `docs/governance/EXTERNAL_REVIEW_COVERAGE_STANDARD.md`
  - `docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml`
  - `docs/governance/EXTERNAL_REVIEW_GATE_SEQUENCE.md`
- Status and cross-reference consistency:
  - `docs/architecture/CIOS_FEATURE_STATUS.yaml`
  - `docs/architecture/CURRENT_KNOWN_GAPS.md`
  - `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
  - `docs/MODULE_CONTRACTS.md`
  - `docs/CONTEXT_AND_ROADMAP.md`
  - `README.md`

## Explicit Non-Scope

Dieses Packet fuehrt nicht ein:

- Investmentlogik
- produktiver Portfolio Event Ledger
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
- Valuation Automation
- Buy/Sell Recommendation Aenderungen
- Steuerberechnung
- Legal-/Commercial-Freigabe
- Order Execution
- Runtime-LLM-Agentenlogik
- Runtime-Enforcement-Engine
- automatische Release-Akzeptanz
- vollautomatische Release-Akzeptanz
- Product-/Production-Readiness
- Investment-Readiness

## Reviewer Notes

- Der neue Producer operationalisiert `RELEASE_CI_ENVIRONMENT_PARITY_REVIEW`
  als lokalen read-only Environment-Parity-Check mit CSV- und Markdown-Output.
- Der Producer prueft lokale Python-/Tool-Verfuegbarkeit, erwartete
  Validierungsbefehle und Handoff-RECORDED-Semantik. Er behauptet keinen
  CI-Green.
- `pytest` und `ruff` waren im aktiven Python-Environment nicht installiert;
  daraus wurde kein Erfolg abgeleitet.
- `src.clean_room_reproduction_review.REQUIRED_ZIP_FILES` schuetzt nun auch
  `src/clean_room_reproduction_review.py` und
  `tests/test_clean_room_reproduction_review.py`.
- `src.handoff_bundle` enthaelt keinen hartcodierten lokalen Operatornamen
  mehr; echte aktuelle Operatorpfade werden zur Laufzeit erkannt, waehrend
  synthetische Test-Fixture-Pfade wie `C:\Users\Max\private.csv` weiterhin als
  Tests abgegrenzt bleiben.
- `NON_SCOPE_PRESERVATION` akzeptiert konservative Negativvarianten wie
  `keine automatische Release-Akzeptanz`,
  `keine vollautomatische Release-Akzeptanz`, `no release acceptance`,
  `no full release acceptance` und `no automated release acceptance`.
- Final Acceptance bleibt beim Human Operator.
