# Compound Income OS External LLM Review Packet - Decision Quality Stage Integration

Dies ist der Einstiegspunkt fuer die externe LLM-Review von `compound_income_os`
nach `feat: integrate decision quality stage into personal run engine`.

## Current Review Head

- project: `compound_income_os`
- branch: `main`
- current_handoff_head: `05c6b01eb6ef21c9b4f4833327ab3bb39d00b56a`
- current_handoff_short_head: `05c6b01`
- current_patch_context: `feat: integrate decision quality stage into personal run engine`
- previous_repo_head: `1d141fb2cd6274957b9ba2aab8e559076bebc540`
- previous_handoff_head: `373db5da583fb3fdf558203d85d683750a8ed656`
- canonical_contract:
  `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`

Das vorherige externe Packet fuer `373db5da583fb3fdf558203d85d683750a8ed656`
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
   - `src/personal_run_engine.py`
   - `tests/test_personal_run_engine.py`
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
Implementierungscommit `05c6b01eb6ef21c9b4f4833327ab3bb39d00b56a`.

## Patch Scope

Dieses Packet enthaelt die read-only Integration des Decision-Quality-Producers
in `src.personal_run_engine`:

- `src/personal_decision_quality_state.py`
- `tests/test_personal_decision_quality_state.py`
- `src/personal_run_engine.py`
- `tests/test_personal_run_engine.py`
- minimale README-/Modulvertrag-/Roadmap-Referenzen

Der Producer ist als Stage `decision_quality` verfuegbar. Die Stage schreibt
`decision_quality_state.csv`, `decision_quality_state.json` und
`decision_quality_report.md` aus bestehenden processed/readiness/run/review-
Artefakten. Sie erzeugt keine neuen Fundamentals, keine Scores, keine
Portfolio-Regeln, keine Orders und keine Simulation/Backtesting/Outcome-
Attribution.

Dieser Patch haertet zusaetzlich host-unabhaengige Windows-/UNC-/Traversal-
Pfad-Redaction im Producer. Die Run Engine schreibt vor `decision_quality` eine
vorlaeufige aktuelle Manifest-/Used-Inputs-Lineage und finalisiert nach dem Run
Manifest und Artifact Index erneut.

## Reviewer Rules

- Vollstaendige relative Pfade verwenden.
- `src/personal_run_engine.py`, `src/personal_decision_quality_state.py`,
  `tests/test_personal_run_engine.py` und
  `tests/test_personal_decision_quality_state.py` als aktuelle Review-
  Einstiege behandeln.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Fundamentals, KPIs, Readiness-Ergebnisse oder Testergebnisse erfinden.
