# Compound Income OS External LLM Review Packet - Current System Definition Handoff

Dies ist der Einstiegspunkt fuer die externe LLM-Review des aktuellen
`compound_income_os`-Handoffs nach dem Systemdefinition-Patch.

Dieses Paket repraesentiert den committed Repo-Stand:

- branch: `main`
- current_handoff_head: `e5b7afb855cbdece18d37183f288429a65b6d5af`
- current_handoff_short_head: `e5b7afb`
- canonical_system_definition:
  `docs/architecture/COMPOUND_INCOME_OS_SYSTEM_DEFINITION.md`

## Source-of-Truth / Precedence

Bei Konflikten gilt diese Reihenfolge:

1. `external_review_packet/00_READ_ME_FIRST.md`
   - Einstiegspunkt, Lesereihenfolge und externe Reviewer-Regeln.

2. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
   - autoritative Packet-Metadaten, Head, Scope, SHA-/ZIP-Fakten und
     aktuelle Handoff-Interpretation.

3. `external_review_packet/HANDOFF_LATEST.zip`
   - autoritatives Repo-Evidenz-Bundle fuer den in
     `HANDOFF_LATEST_CONTEXT.md` genannten Head.

4. `external_review_packet/HANDOFF_LATEST.sha256`
   - Checksumme zur Verifikation der ZIP-Bytes.

5. Historische Phase-Reports in `external_review_packet/`
   - nur historische Kontext-/Validierungsartefakte. Sie ueberschreiben weder
     `00_READ_ME_FIRST.md` noch `HANDOFF_LATEST_CONTEXT.md`.

## Canonical Review Inputs

Reviewer sollen in dieser Reihenfolge lesen:

1. `external_review_packet/00_READ_ME_FIRST.md`
2. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
3. ZIP-interne `HANDOFF_CONTEXT.md`
4. ZIP-interne `HANDOFF_VALIDATION.txt`
5. ZIP-interne Repo-Dateien, insbesondere:
   - `docs/architecture/COMPOUND_INCOME_OS_SYSTEM_DEFINITION.md`
   - `README.md`
   - `docs/CONTEXT_AND_ROADMAP.md`
   - `docs/architecture/01_TARGET_OS_KERNEL_V1.md`
   - `docs/architecture/05_ARCHITECTURE_BACKLOG.csv`
   - `docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md`
   - `docs/policies/LLM_CODEX_OPERATING_POLICY.md`
   - `src/`
   - `tests/`
   - `configs/`

## Conflict Rule

Wenn ZIP-internes `HANDOFF_CONTEXT.md` mit
`external_review_packet/HANDOFF_LATEST_CONTEXT.md` kollidiert, gewinnt
`external_review_packet/HANDOFF_LATEST_CONTEXT.md` fuer Packet-Metadaten,
Head/SHA/Scope, Precedence und Reviewer-Instruktionen.

ZIP-internes `HANDOFF_CONTEXT.md` ist generischer Exporter-Kontext. Es darf fuer
Exporter-Fakten genutzt werden, z. B. Profil, inkludierte/ausgelassene Gruppen
und Dirty-Worktree-Status zum Exportzeitpunkt. Es ueberschreibt nicht die
externen Packet-Metadaten.

## Historical Reports

Diese Dateien bleiben als historische Validierungs- und Kontextartefakte
erhalten:

- `external_review_packet/PATCH_02_FINAL_REPORT.md`
- `external_review_packet/PATCH_1_2_FINAL_REPORT.md`
- `external_review_packet/PATCH_1_3_FINAL_REPORT.md`

Sie koennen fruehere Patch-Kontexte erklaeren, repraesentieren aber nicht den
aktuellen Handoff-Head `e5b7afb855cbdece18d37183f288429a65b6d5af`. Alte
Phase-1.2-/Phase-1.3-Metadaten und fruehere `HANDOFF_LATEST`-Artefakte duerfen
nicht mit diesem aktuellen Packet vermischt werden.

## Reviewer Rules

- Vollstaendige relative Pfade verwenden.
- `docs/architecture/COMPOUND_INCOME_OS_SYSTEM_DEFINITION.md` als kanonischen
  Systemdefinitions-Einstiegspunkt behandeln.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Fundamentals, KPIs, Readiness-Ergebnisse oder Testergebnisse erfinden.
- Tests nur als bestanden bezeichnen, wenn die Evidenz im Repo, im Handoff, in
  `HANDOFF_LATEST_CONTEXT.md` oder in einem expliziten Operator-Log vorhanden
  ist.
