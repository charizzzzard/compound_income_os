# Compound Income OS External LLM Review Packet - Decision Quality Layer

Dies ist der Einstiegspunkt fuer die externe LLM-Review von `compound_income_os`
nach dem Patch `docs: add decision quality layer architecture`.

## Current Review Head

- project: `compound_income_os`
- branch: `main`
- current_handoff_head: `362cc6522626556d3f41e18c8d27148ce3b1110e`
- current_handoff_short_head: `362cc65`
- current_patch_context: `docs: add decision quality layer architecture`
- previous_local_start_head: `0da74ca0f8c3116524eb0d03b2e7f5dd32655b2e`
- previous_handoff_head: `8342bb34fd997165d1f0f96b757f8ad8bb699b4d`
- canonical_system_definition:
  `docs/architecture/COMPOUND_INCOME_OS_SYSTEM_DEFINITION.md`

Das vorherige externe Packet fuer `8342bb34fd997165d1f0f96b757f8ad8bb699b4d`
ist durch dieses Packet superseded.

## Source-of-Truth / Precedence

Bei Konflikten gilt diese Reihenfolge:

1. `external_review_packet/00_READ_ME_FIRST.md`
   - Einstiegspunkt, Lesereihenfolge und externe Reviewer-Regeln.

2. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
   - autoritative Packet-Metadaten, Head, Scope, SHA-/ZIP-Fakten und
     aktuelle Handoff-Interpretation.

3. `external_review_packet/HANDOFF_LATEST.zip`
   - autoritatives Repo-Evidenz-Bundle fuer den in
     `HANDOFF_LATEST_CONTEXT.md` genannten Handoff-Head.

4. `external_review_packet/HANDOFF_LATEST.sha256`
   - Checksumme zur Verifikation der ZIP-Bytes.

5. Historische Phase-Reports in `external_review_packet/`
   - nur historische Kontext-/Validierungsartefakte. Sie ueberschreiben weder
     `00_READ_ME_FIRST.md` noch `HANDOFF_LATEST_CONTEXT.md`.

## Canonical Review Inputs

Reviewer sollen in dieser Reihenfolge lesen:

1. `external_review_packet/00_READ_ME_FIRST.md`
2. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
3. `external_review_packet/HANDOFF_LATEST.sha256`
4. `external_review_packet/HANDOFF_LATEST.zip`
5. ZIP-intern:
   - `HANDOFF_CONTEXT.md`
   - `HANDOFF_VALIDATION.txt`
   - `HANDOFF_MANIFEST.csv`
   - `HANDOFF_ARTIFACT_INDEX.csv`
   - `docs/architecture/COMPOUND_INCOME_OS_SYSTEM_DEFINITION.md`
   - `docs/architecture/DECISION_QUALITY_LAYER.md`
   - `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`
   - `docs/governance/BASELINE_VS_CANDIDATE_VALIDATION.md`
   - `docs/research/SCIENTIFIC_ARCHITECTURE_REVIEW_CIOS.md`
   - `docs/research/UNCERTAINTY_DECISION_FRAMEWORK_CIOS.md`
   - `docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md`
   - `src/personal_input_closure.py`
   - `src/personal_decision_state_capture.py`
   - `README.md`
   - `docs/CONTEXT_AND_ROADMAP.md`
   - `docs/architecture/05_ARCHITECTURE_BACKLOG.csv`
   - `docs/architecture/06_ADOPTED_DECISIONS.yaml`

## Conflict Rule

Wenn ZIP-internes `HANDOFF_CONTEXT.md` mit
`external_review_packet/HANDOFF_LATEST_CONTEXT.md` kollidiert, gewinnt
`external_review_packet/HANDOFF_LATEST_CONTEXT.md` fuer Packet-Metadaten,
Head/SHA/Scope, Precedence und Reviewer-Instruktionen.

ZIP-internes `HANDOFF_CONTEXT.md` ist generischer Exporter-Kontext. Es darf fuer
Exporter-Fakten genutzt werden, z. B. Profil, inkludierte/ausgelassene Gruppen
und Dirty-Worktree-Status zum Exportzeitpunkt. Es ueberschreibt nicht die
externen Packet-Metadaten.

## Decision Quality Review Context

Dieses Packet enthaelt Patch 1.4:

- `docs/architecture/DECISION_QUALITY_LAYER.md`
- `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`
- `docs/governance/BASELINE_VS_CANDIDATE_VALIDATION.md`
- `docs/research/SCIENTIFIC_ARCHITECTURE_REVIEW_CIOS.md`
- `docs/research/UNCERTAINTY_DECISION_FRAMEWORK_CIOS.md`

Decision Quality ist ein Review-/Governance-Layer. `decision_confidence`
bedeutet Prozessvertrauen, nicht Erfolgswahrscheinlichkeit, Alpha-Prognose oder
Order-Freigabe. Quantitative und stochastische Methoden duerfen spaeter
Review-Artefakte erzeugen, aber keine selbst ausfuehrenden Empfehlungen.

Dieses Packet enthaelt keine Simulation, kein Monte Carlo, kein Backtesting,
keine Broker-/Order-/Auto-Trading-Logik und keine Runtime-LLM-Implementierung.

## Historical Reports

Diese Dateien bleiben als historische Validierungs- und Kontextartefakte
erhalten:

- `external_review_packet/PATCH_02_FINAL_REPORT.md`
- `external_review_packet/PATCH_1_2_FINAL_REPORT.md`
- `external_review_packet/PATCH_1_3_FINAL_REPORT.md`

Sie koennen fruehere Patch-Kontexte erklaeren, repraesentieren aber nicht den
aktuellen Handoff-Head `362cc6522626556d3f41e18c8d27148ce3b1110e`.
Sie ueberschreiben weder `00_READ_ME_FIRST.md` noch
`HANDOFF_LATEST_CONTEXT.md`.

## Reviewer Rules

- Vollstaendige relative Pfade verwenden.
- `docs/architecture/COMPOUND_INCOME_OS_SYSTEM_DEFINITION.md` als kanonischen
  Systemdefinitions-Einstiegspunkt behandeln.
- `docs/architecture/DECISION_QUALITY_LAYER.md` als kanonischen Einstieg fuer
  Patch 1.4 behandeln.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Fundamentals, KPIs, Readiness-Ergebnisse oder Testergebnisse erfinden.
- Tests nur als bestanden bezeichnen, wenn die Evidenz im Repo, im Handoff, in
  `HANDOFF_LATEST_CONTEXT.md` oder in einem expliziten Operator-Log vorhanden
  ist.
