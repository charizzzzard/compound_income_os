# Compound Income OS External LLM Review Packet - Review Queue Semantics + Surface Hardening

Dies ist der Einstiegspunkt fuer die externe LLM-Review von `compound_income_os`
nach `fix: harden decision review queue semantics`.

## Current Review Head

- project: `compound_income_os`
- branch: `main`
- current_handoff_head: `95713e85f85f756f3bb3b9bdd6beec992416a56f`
- current_handoff_short_head: `95713e8`
- current_patch_context: `fix: harden decision review queue semantics`
- previous_repo_head: `1f55b0a281ebeb1769e0ebf39d1feb176b29b8bd`
- previous_handoff_head: `8ea648d75260cd062de385c6b1fe59f101b225ac`
- canonical_decision_state_contract:
  `docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md`
- canonical_decision_quality_contract:
  `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`

Das vorherige externe Packet fuer `8ea648d75260cd062de385c6b1fe59f101b225ac`
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
Implementierungscommit `95713e85f85f756f3bb3b9bdd6beec992416a56f`.

## Patch Scope

Dieses Packet enthaelt Phase 1.6B Review Queue Semantics + Surface Hardening:

- Duplicate `decision_id` wird als `DECISION_ID_DUPLICATE` mit Priority
  `BLOCKER` sichtbar.
- Validation-Finding-Counts und Queue-Counts werden getrennt in Report-Surfaces
  gerendert.
- Die MVP-Prioritaetentaxonomie ist stabil dokumentiert.
- Stale-State-Semantik bleibt konservativ: jedes aeltere Decision-Quality-
  `as_of_date` ist stale.

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
- `src/personal_decision_journal_validation.py`, `src/personal_run_engine.py`,
  `src/build_monthly_decision_report.py` und die zugehoerigen Tests als
  aktuelle Review-Einstiege behandeln.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Simulation, kein Backtesting, keine Outcome Attribution und kein
  Portfolio Event Ledger inferieren.
- Keine Fundamentals, KPIs, Readiness-Ergebnisse oder Testergebnisse erfinden.
