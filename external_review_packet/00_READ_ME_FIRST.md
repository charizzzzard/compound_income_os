# Compound Income OS External LLM Review Packet - Decision Quality Contract Hardening

Dies ist der Einstiegspunkt fuer die externe LLM-Review von `compound_income_os`
nach Patch 1.5A `docs: harden decision quality state contract`.

## Current Review Head

- project: `compound_income_os`
- branch: `main`
- current_handoff_head: `54156127153f45614d165414e4a97a9be2aba1ed`
- current_handoff_short_head: `5415612`
- current_patch_context: `docs: harden decision quality state contract`
- previous_repo_head: `45c0afb8cf992c460e67fa6e4f566d1d150158d9`
- previous_handoff_head: `362cc6522626556d3f41e18c8d27148ce3b1110e`
- canonical_system_definition:
  `docs/architecture/COMPOUND_INCOME_OS_SYSTEM_DEFINITION.md`

Das vorherige externe Packet fuer `362cc6522626556d3f41e18c8d27148ce3b1110e`
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
   - `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`
   - `docs/architecture/DECISION_QUALITY_LAYER.md`
   - `docs/governance/BASELINE_VS_CANDIDATE_VALIDATION.md`
   - `docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md`
   - `src/personal_input_closure.py`
   - `src/personal_decision_state_capture.py`
   - `docs/architecture/05_ARCHITECTURE_BACKLOG.csv`
   - `docs/architecture/06_ADOPTED_DECISIONS.yaml`

## Dirty-State Interpretation

ZIP-internes `HANDOFF_CONTEXT.md` kann `dirty_worktree_present: True` zeigen,
weil `external_review_packet/HANDOFF_LATEST.sha256` vor der ZIP-Erzeugung
entfernt und danach neu geschrieben wurde. Das ist eine Handoff-Artefakt-
Regeneration, kein Patch-Source-Dirty-State.

Autoritativ fuer die Interpretation ist diese externe Metadatenkette:

- Der tracked Worktree war nach dem Implementierungscommit vor der
  Handoff-Cleanup-Sequenz sauber.
- Das ZIP wurde fuer `54156127153f45614d165414e4a97a9be2aba1ed` erzeugt.
- Die externe `HANDOFF_LATEST_CONTEXT.md` gewinnt gegen ZIP-internes
  `HANDOFF_CONTEXT.md`, wenn Dirty-State-Labels unterschiedlich wirken.

## Decision Quality Contract Hardening Context

Dieses Packet enthaelt Patch 1.5A:

- `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`
- `docs/architecture/DECISION_QUALITY_LAYER.md`
- `docs/governance/BASELINE_VS_CANDIDATE_VALIDATION.md`
- `docs/architecture/05_ARCHITECTURE_BACKLOG.csv`
- `docs/architecture/06_ADOPTED_DECISIONS.yaml`

Der Patch macht den Decision-Quality-State-Contract producer-ready durch:

- Feldtypen und CSV-/JSON-Serialisierung
- deterministische `decision_confidence_level`-Ableitung
- Minimal Producer Input Matrix fuer Phase 1.5
- Default-Regeln fuer `NOT_EVALUATED`, `REVIEW` und `MISSING`
- explizite Phase-1.5-Grenzen fuer Scenario, Tail Risk, Outcome, Calibration
  und Regret

Es wurde kein Python-Producer implementiert.

## Historical Reports

Historische Reports bleiben nur historische Validierungs- und
Kontextartefakte. Sie repraesentieren nicht den aktuellen Handoff-Head und
ueberschreiben weder `00_READ_ME_FIRST.md` noch `HANDOFF_LATEST_CONTEXT.md`.

## Reviewer Rules

- Vollstaendige relative Pfade verwenden.
- `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md` als kanonischen Einstieg
  fuer Patch 1.5A behandeln.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Fundamentals, KPIs, Readiness-Ergebnisse oder Testergebnisse erfinden.
- Tests nur als bestanden bezeichnen, wenn die Evidenz im Repo, im Handoff, in
  `HANDOFF_LATEST_CONTEXT.md` oder in einem expliziten Operator-Log vorhanden
  ist.
