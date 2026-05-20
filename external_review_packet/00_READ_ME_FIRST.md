# Compound Income OS External LLM Review Packet - System Map + Feature Status + Surface PASS Fix

Dies ist der Einstiegspunkt fuer die externe LLM-Review von
`compound_income_os` nach
`docs: add system map and harden decision journal surface`.

## Current Review Head

- project: `compound_income_os`
- branch: `main`
- current_handoff_head: `e1ec6682942139ad14a7ffc7f59ef88bd6bc4c4e`
- current_handoff_short_head: `e1ec668`
- current_patch_context: `docs: add system map and harden decision journal surface`
- previous_repo_head: `05d1426a3a5ebbb3a93c4541da1e767a1d7b16c4`
- previous_handoff_head: `95713e85f85f756f3bb3b9bdd6beec992416a56f`
- canonical_system_map:
  `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
- canonical_feature_status:
  `docs/architecture/CIOS_FEATURE_STATUS.yaml`
- canonical_known_gaps:
  `docs/architecture/CURRENT_KNOWN_GAPS.md`
- canonical_decision_state_contract:
  `docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md`
- canonical_decision_quality_contract:
  `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`

Das vorherige externe Packet fuer `95713e85f85f756f3bb3b9bdd6beec992416a56f`
ist durch dieses Packet superseded.

## Source-of-Truth / Precedence

Bei Konflikten gilt diese Reihenfolge:

1. `external_review_packet/00_READ_ME_FIRST.md`
2. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
3. `external_review_packet/HANDOFF_LATEST.zip`
4. `external_review_packet/HANDOFF_LATEST.sha256`
5. historische Phase-Reports nur als historische Kontext-/Validierungsartefakte

ZIP-internes `HANDOFF_CONTEXT.md` ist generischer Exporter-Kontext. Wenn es mit
`external_review_packet/HANDOFF_LATEST_CONTEXT.md` kollidiert, gewinnt die
externe Kontextdatei fuer Head, Scope, SHA und Dirty-State-Interpretation.

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
   - `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
   - `docs/architecture/CIOS_FEATURE_STATUS.yaml`
   - `docs/architecture/CURRENT_KNOWN_GAPS.md`
   - `src/personal_decision_journal_validation.py`
   - `tests/test_personal_decision_journal_validation.py`
   - `src/personal_run_engine.py`
   - `tests/test_personal_run_engine.py`
   - `src/build_monthly_decision_report.py`
   - `tests/test_monthly_decision_report.py`
   - `docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md`
   - `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`
   - `docs/architecture/DECISION_QUALITY_LAYER.md`

## Dirty-State Interpretation

ZIP-internes `HANDOFF_CONTEXT.md` kann `dirty_worktree_present: True` zeigen,
weil `external_review_packet/HANDOFF_LATEST.sha256` vor der ZIP-Erzeugung
entfernt und danach neu geschrieben wurde. Das ist eine Handoff-Artefakt-
Regeneration, kein Patch-Source-Dirty-State.

Der finale Repo-HEAD kann nach diesem Packet ein separater
Handoff-Metadatencommit sein. Der aktuelle Handoff-Head bleibt der
Implementierungscommit `e1ec6682942139ad14a7ffc7f59ef88bd6bc4c4e`.

## Patch Scope

Dieses Packet enthaelt:

- eine aktuelle externe-Review-taugliche System Map,
- einen maschinenlesbaren Feature-Status mit 36 Capabilities,
- eine Known-Gaps-Liste fuer Dashboard-, Replay-, Outcome- und Deferred-Themen,
- den Surface-Fix fuer Decision Journal Validation:
  - fehlende/nicht lesbare Artefakte bleiben `NOT_AVAILABLE`,
  - vorhandene Header-only Validation-/Queue-Artefakte rendern `PASS` mit
    Null-Counts,
  - Findings und Queue Items bleiben als `REVIEW` sichtbar.

Der Patch erzeugt keine Decisions, keine Orders, keine Portfolio-Events und
keine Outcome Attribution.

## Handoff Reproducibility Note

Dieses Handoff ist ein Review-Bundle ohne private/raw Artefakte. Die unten
dokumentierten Tests wurden lokal im Repo ausgefuehrt. Externe Reviewer sollen
keine ausgelassenen privaten Fixtures, raw Daten oder lokalen Broker-Dokumente
inferieren; nicht jeder lokale Test muss aus dem ZIP allein reproduzierbar sein,
wenn private/raw Inputs bewusst ausgeschlossen sind.

## Reviewer Rules

- Vollstaendige relative Pfade verwenden.
- System Map, Feature Status und Known Gaps als aktuelle Review-Einstiege
  behandeln.
- Den Decision-Journal-Surface-Fix explizit gegen `PASS` vs `NOT_AVAILABLE`
  pruefen.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Simulation, kein Backtesting, keine Outcome Attribution und kein
  Portfolio Event Ledger inferieren.
- Keine Fundamentals, KPIs, Readiness-Ergebnisse oder Testergebnisse erfinden.
