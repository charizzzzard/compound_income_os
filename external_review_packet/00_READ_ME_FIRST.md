# Compound Income OS External LLM Review Packet - Handoff Delta Evidence Hardening

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach dem Handoff-Delta-Evidence-Hardening-Patch:

- commit: `40f43ae9662e72cb530ca8e407f657dda4a6a289`
- message: `chore: add handoff delta evidence`
- status: `HANDOFF_DELTA_EVIDENCE_HARDENING_ACCEPTED_WITH_FINDINGS`

Dieses Packet superseded aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck.

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- base_head: `f4fa942b3f4d82f7ac1320dd5805d3319e9b6127`
- implementation_head: `40f43ae9662e72cb530ca8e407f657dda4a6a289`
- implementation_short_head: `40f43ae`
- current_handoff_head: `40f43ae9662e72cb530ca8e407f657dda4a6a289`
- current_handoff_short_head: `40f43ae`
- delta_range: `f4fa942b3f4d82f7ac1320dd5805d3319e9b6127..40f43ae9662e72cb530ca8e407f657dda4a6a289`
- handoff_metadata_commit: `pending_until_metadata_commit`
- handoff_metadata_commit_note: `metadata commit is created after this file is written; use git HEAD after metadata commit or the operator final report for the exact metadata commit hash`
- bundle_purpose: `external_review_after_handoff_delta_evidence_hardening`
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
- Pruefe `HANDOFF_PATCH_IDENTITY.md`, bevor ein Snapshot als Patch-Delta-Beweis
  behandelt wird.
- Pruefe `HANDOFF_CHANGE_CLASSIFICATION.csv`; sie muss fuer diesen Patch
  Git-Delta-Zeilen enthalten und darf nicht nur aus einem Header bestehen.
- Behandle `HANDOFF_VALIDATION.txt` als `RECORDED_VALIDATION`, sofern keine
  externe Kontextdatei oder ein Operatorbericht eine tatsaechliche Ausfuehrung
  als `EXECUTED_IN_CURRENT_REPO` oder `EXECUTED_IN_ZIP_CONTEXT` belegt.
- Verwende `configs/test_reproduction_matrix.json`, um ZIP-safe, local-repo,
  Git-context, private-input und optional-tooling Checks zu unterscheiden.
- Behandle fehlendes `pytest` oder `ruff` als Environment-Realitaet, nicht als
  Erfolg und nicht automatisch als Repo-Logikfehler.
- Inferiere keine Release-, Product-, Investment-, Broker-Import-, Replay-,
  Backtesting-, Dashboard- oder Outcome-Attribution-Readiness.
- Fehlende, stale oder unknown Daten muessen sichtbar bleiben.
- Keine stille Imputation, keine stille Ueberschreibung akzeptierter Fakten,
  keine Investment Advice und keine Order Execution.

## Review Scope

Reviewer sollen insbesondere pruefen:

- `HANDOFF_PATCH_IDENTITY.md`
- `HANDOFF_CHANGE_CLASSIFICATION.csv`
- `HANDOFF_VALIDATION.txt`
- `src/handoff_bundle.py`
- `tests/test_handoff_bundle.py`
- `tests/test_handoff_zip_export.py`
- `tests/test_runtime_gate_definition_template.py`
- `docs/HANDOFF_CONTRACT.md`
- `docs/governance/EXTERNAL_REPRODUCTION.md`
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
- Product-/Production-Readiness
- Investment-Readiness
