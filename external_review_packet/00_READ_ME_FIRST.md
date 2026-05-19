# Compound Income OS External LLM Review Packet - Minimal Decision Quality Producer

Dies ist der Einstiegspunkt fuer die externe LLM-Review von `compound_income_os`
nach Phase 1.5B `feat: add minimal decision quality state producer`.

## Current Review Head

- project: `compound_income_os`
- branch: `main`
- current_handoff_head: `dcc85269c911ffdde22ddcf8fced3d9b41ca2528`
- current_handoff_short_head: `dcc8526`
- current_patch_context: `feat: add minimal decision quality state producer`
- previous_repo_head: `6bef7e2f1ec6c949d4906bff1eabcdf97b720603`
- previous_handoff_head: `d913567c3f5d9b80f910ee68db1fc82b1dfc20c7`
- canonical_contract:
  `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`

Das vorherige externe Packet fuer `d913567c3f5d9b80f910ee68db1fc82b1dfc20c7`
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
   - `src/personal_decision_quality_state.py`
   - `tests/test_personal_decision_quality_state.py`
   - `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`
   - `docs/architecture/DECISION_QUALITY_LAYER.md`
   - `docs/governance/BASELINE_VS_CANDIDATE_VALIDATION.md`
   - `docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md`
   - `src/personal_input_closure.py`
   - `src/personal_decision_state_capture.py`

## Dirty-State Interpretation

ZIP-internes `HANDOFF_CONTEXT.md` kann `dirty_worktree_present: True` zeigen,
weil `external_review_packet/HANDOFF_LATEST.sha256` vor der ZIP-Erzeugung
entfernt und danach neu geschrieben wurde. Das ist eine Handoff-Artefakt-
Regeneration, kein Patch-Source-Dirty-State.

Der finale Repo-HEAD kann nach diesem Packet ein separater
Handoff-Metadatencommit sein. Der aktuelle Handoff-Head bleibt der
Implementierungscommit `dcc85269c911ffdde22ddcf8fced3d9b41ca2528`.

## Patch Scope

Dieses Packet enthaelt Phase 1.5B:

- `src/personal_decision_quality_state.py`
- `tests/test_personal_decision_quality_state.py`
- Contract-Beispiel-Fix in
  `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`
- minimale README-/Module-/Roadmap-Referenzen

Der Producer aggregiert bestehende processed/readiness/run/review-Artefakte zu
`decision_quality_state.csv`, `decision_quality_state.json` und einem Markdown-
Report. Er erzeugt keine neuen Fundamentals, keine Scores, keine Portfolio-
Regeln, keine Orders und keine Simulation/Backtesting/Outcome-Attribution.

## Reviewer Rules

- Vollstaendige relative Pfade verwenden.
- `src/personal_decision_quality_state.py` und
  `tests/test_personal_decision_quality_state.py` als aktuelle Producer-
  Review-Einstiege behandeln.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Fundamentals, KPIs, Readiness-Ergebnisse oder Testergebnisse erfinden.
