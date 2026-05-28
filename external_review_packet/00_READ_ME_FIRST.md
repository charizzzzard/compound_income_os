# Compound Income OS External LLM Review Packet - ZIP-Safe Reproduction Hardening

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach dem Reproducibility-Hardening-Patch:

- commit: `31a9d20986ad6731fd18f9b371d2881292db20c6`
- message: `test: add zip-safe reproduction smoke`
- status: `ZIP_SAFE_REPRODUCTION_HARDENING_ACCEPTED_WITH_FINDINGS`

Dieses Packet superseded aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck.

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- implementation_head: `31a9d20986ad6731fd18f9b371d2881292db20c6`
- implementation_short_head: `31a9d20`
- current_handoff_head: `31a9d20986ad6731fd18f9b371d2881292db20c6`
- current_handoff_short_head: `31a9d20`
- handoff_metadata_commit: `pending_until_metadata_commit`
- handoff_metadata_commit_note: `metadata commit is created after this file is written; use git HEAD after metadata commit or the operator final report for the exact metadata commit hash`
- bundle_purpose: `external_review_after_zip_safe_reproduction_hardening`
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
- Starte ZIP-safe Reproduktion mit:
  - `python -m unittest tests.test_zip_safe_operator_journey -v`
  - `python -m unittest tests.test_reproduction_matrix -v`
- Verwende `configs/test_reproduction_matrix.json`, um ZIP-safe, local-repo,
  Git-context, private-input und optional-tooling Checks zu unterscheiden.
- Behandle lokale Full-Suite-Ergebnisse als `EXECUTED_IN_CURRENT_REPO`, nicht
  automatisch als `EXECUTED_IN_ZIP_CONTEXT`.
- Behandle `tests.test_handoff_bundle` und `tests.test_handoff_zip_export` als
  Git-/Local-Repo-Kontextchecks, nicht als ZIP-only Beweis.
- Behandle fehlendes `pytest` oder `ruff` als Environment-Realitaet, nicht als
  Erfolg und nicht automatisch als Repo-Logikfehler.
- Inferiere keine Release-, Product-, Investment-, Broker-Import-, Replay-,
  Backtesting-, Dashboard- oder Outcome-Attribution-Readiness.
- Fehlende, stale oder unknown Daten muessen sichtbar bleiben.
- Keine stille Imputation, keine stille Ueberschreibung akzeptierter Fakten,
  keine Investment Advice und keine Order Execution.

## Review Scope

Reviewer sollen insbesondere pruefen:

- `configs/test_reproduction_matrix.json`
- `tests/test_reproduction_matrix.py`
- `tests/test_zip_safe_operator_journey.py`
- `docs/governance/EXTERNAL_REPRODUCTION.md`
- `README.md`
- `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
- `src/data_freshness.py`
- `src/dashboard_operator_summary.py`
- `src/handoff_zip_export.py`
- `src/handoff_bundle.py`

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
- Product-/Production-Readiness
- Investment-Readiness
