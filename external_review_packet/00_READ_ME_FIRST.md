# Compound Income OS External LLM Review Packet  Phase 1.3

Dies ist der Einstiegspunkt fuer die externe LLM-Review des Phase-1.3-Handoffs von `compound_income_os`.

## Source-of-truth / Precedence

Bei Konflikten gilt diese Reihenfolge:

1. `external_review_packet/00_READ_ME_FIRST.md`
   - Einstiegspunkt und Reviewer-Instruktionen

2. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
   - autoritative Phase-1.3-Packet-Metadaten und Lineage

3. `external_review_packet/PATCH_1_3_FINAL_REPORT.md`
   - Implementierungszusammenfassung, Validierungsevidenz, Guardrails, bekannte Findings

4. `external_review_packet/HANDOFF_LATEST.sha256`
   - Checksumme fuer das ZIP

5. `external_review_packet/HANDOFF_LATEST.zip`
   - kanonisches Repo-Evidenz-Bundle

6. ZIP-interne Repo-Dateien, insbesondere:
   - `docs/COMPOUND_INCOME_OS_VISION_v1_2.md`
   - `docs/CONTEXT_AND_ROADMAP.md`
   - `docs/MODULE_CONTRACTS.md`
   - `README.md`
   - `src/`
   - `tests/`
   - `configs/`

## Conflict Rule

Wenn ZIP-internes `HANDOFF_CONTEXT.md` mit externem `HANDOFF_LATEST_CONTEXT.md` kollidiert, gewinnt `external_review_packet/HANDOFF_LATEST_CONTEXT.md` fuer Phase-1.3-Metadaten, Lineage, Scope und Reviewer-Instruktionen.

ZIP-internes `HANDOFF_CONTEXT.md` ist generische Exporter-Metadokumentation. Es darf fuer ZIP-Source-Fakten genutzt werden, zum Beispiel Source Head, Dirty-Worktree-Status zum Exportzeitpunkt, Exporter-Profil und inkludierte/ausgelassene Gruppen. Es ueberschreibt nicht die Phase-1.3-spezifischen externen Metadaten.

## Artifact-Lineage Warning

Nicht verwechseln:

- `phase_1_3_final_head`: `feff13240a89b1e306226f43032abb68c35c3d1c`
- `handoff_zip_source_head`: `a36c3fc403138454d2581f276d7a5d849b940bfe`
- `artifact_checksum_commit`: `a551ad9746126d1ec60ed8488a18aa8fa22335a2`

`a36c3fc...` ist der ZIP-Source-Head. `a551ad9...` ist laut Git-Evidenz ein Artifact-/Checksum-Commit mit Aenderung nur an `external_review_packet/HANDOFF_LATEST.sha256`. Keiner dieser beiden Heads ist ein neuer funktionaler Phase-1.3-Implementierungsstand.

## Canonical Review Inputs

Reviewer sollen diese Inputs verwenden:

- `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
- `external_review_packet/PATCH_1_3_FINAL_REPORT.md`
- `external_review_packet/HANDOFF_LATEST.sha256`
- `external_review_packet/HANDOFF_LATEST.zip`
- ZIP-interne Repo-Dateien:
  - `docs/COMPOUND_INCOME_OS_VISION_v1_2.md`
  - `docs/CONTEXT_AND_ROADMAP.md`
  - `docs/MODULE_CONTRACTS.md`
  - `README.md`
  - `src/`
  - `tests/`
  - `configs/`

## Reviewer Rules

- Vollstaendige relative Pfade verwenden.
- Keine privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading, Steuerquantifizierung, Sell-Logik oder Phase-1.4-Implementierung inferieren.
- Fehlende private Inputs nicht als imputierte Werte behandeln.
- Tests nur als bestanden bezeichnen, wenn die Evidenz im Report, im Repo oder im Operator-Log explizit vorhanden ist.
- Alte Phase-1.2-Texte aus stale externem Kontext nicht verwenden, wenn sie durch dieses Phase-1.3-Packet ersetzt wurden.
- ZIP-internes `HANDOFF_CONTEXT.md` nur als generische Exporter-Metadaten behandeln.
