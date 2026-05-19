# Compound Income OS External LLM Review Packet - Decision Quality Producer Integration-Readiness Fix

Dies ist der Einstiegspunkt fuer die externe LLM-Review von `compound_income_os`
nach dem Phase-1.5B-Fix `fix: harden decision quality producer integration readiness`.

## Current Review Head

- project: `compound_income_os`
- branch: `main`
- current_handoff_head: `373db5da583fb3fdf558203d85d683750a8ed656`
- current_handoff_short_head: `373db5d`
- current_patch_context: `fix: harden decision quality producer integration readiness`
- previous_repo_head: `9bf67f18fb4d8249d0d84c24656dcf5020c2a734`
- previous_handoff_head: `dcc85269c911ffdde22ddcf8fced3d9b41ca2528`
- canonical_contract:
  `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`

Das vorherige externe Packet fuer `dcc85269c911ffdde22ddcf8fced3d9b41ca2528`
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
Implementierungscommit `373db5da583fb3fdf558203d85d683750a8ed656`.

## Patch Scope

Dieses Packet enthaelt den Integration-Readiness-Fix nach Phase 1.5B:

- `src/personal_decision_quality_state.py`
- `tests/test_personal_decision_quality_state.py`
- minimale README-Referenz zum Default-Report-Pfad

Der Producer aggregiert bestehende processed/readiness/run/review-Artefakte zu
`decision_quality_state.csv`, `decision_quality_state.json` und einem Markdown-
Report. Er erzeugt keine neuen Fundamentals, keine Scores, keine Portfolio-
Regeln, keine Orders und keine Simulation/Backtesting/Outcome-Attribution.

Der Fix haertet reale `personal_run_engine`-Stage-Erkennung (`monthly`,
`scoring`), Pflichtartefakt-Erkennung, Pfad-Redaktion, minimale
`run_used_inputs`-Lineage-Pruefung, Report-Non-Scope und den aus `as_of_date`
abgeleiteten Default-Report-Pfad. Er integriert den Producer noch nicht in
`personal_run_engine`.

## Reviewer Rules

- Vollstaendige relative Pfade verwenden.
- `src/personal_decision_quality_state.py` und
  `tests/test_personal_decision_quality_state.py` als aktuelle Producer-
  Review-Einstiege behandeln.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Fundamentals, KPIs, Readiness-Ergebnisse oder Testergebnisse erfinden.
