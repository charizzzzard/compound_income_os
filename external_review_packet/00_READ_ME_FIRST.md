# Compound Income OS External LLM Review Packet - Cross-Patch Regression Governance

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach dem Governance-Automation-Patch:

- commit: `e20113b374d78dea1bd575f65e587bb37b4f314e`
- message: `feat: add cross-patch regression governance check`
- status: `CROSS_PATCH_REGRESSION_REVIEW_OPERATIONALIZED_ACCEPTED_WITH_FINDINGS`

Dieses Packet superseded aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck.

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- implementation_head: `e20113b374d78dea1bd575f65e587bb37b4f314e`
- implementation_short_head: `e20113b`
- current_handoff_head: `e20113b374d78dea1bd575f65e587bb37b4f314e`
- current_handoff_short_head: `e20113b`
- bundle_purpose: `external_review_after_cross_patch_regression_governance_check`
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
- Behandle `src.external_review_cross_patch_regression` als read-only
  Governance-Check, nicht als Release-Akzeptanz und nicht als Runtime
  Enforcement.
- Unterscheide `RECORDED` Handoff-Commands von tatsaechlich ausgefuehrten
  Pass/Fail-Ergebnissen.
- Inferiere keine Release-, Product-, Investment-, Broker-Import-, Replay-,
  Backtesting-, Dashboard- oder Outcome-Attribution-Readiness.
- Unterscheide tatsaechlich ausgefuehrte Tests von Full-Suite-Validation.
- Fehlende, stale oder unknown Daten muessen sichtbar bleiben.
- Keine stille Imputation, keine stille Ueberschreibung akzeptierter Fakten,
  keine Investment Advice und keine Order Execution.

## Review Scope

Reviewer sollen insbesondere pruefen:

- Cross-Patch Regression Governance Check:
  - `src/external_review_cross_patch_regression.py`
  - `tests/test_external_review_cross_patch_regression.py`
  - `data/processed/external_review_cross_patch_regression.csv`, falls im ZIP-Profil enthalten
  - `reports/2026-05-21/external_review_cross_patch_regression_report.md`, falls im ZIP-Profil enthalten
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
- Regression surfaces:
  - `tests/test_readme_and_reports.py`
  - `tests/test_handoff_zip_export.py`
  - `tests/test_handoff_bundle.py`

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
- Clean-Room-Automation
- vollautomatische Cross-Patch-Regression

## Reviewer Notes

- Der neue Producer operationalisiert `CROSS_PATCH_REGRESSION_REVIEW` als
  lokalen read-only Check mit CSV- und Markdown-Output.
- Der Producer meldet Drift sichtbar, akzeptiert aber keinen Release.
- Der aktuelle Lauf meldete keine `FAIL`, aber `WARN`-Rows fuer historische
  patch-relative Known-Gaps-Formulierungen und fuer `RECORDED`-Handoff-Command
  Semantik.
- Final Acceptance bleibt beim Human Operator.
