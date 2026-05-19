# Compound Income OS External LLM Review Packet - Decision Quality Path Redaction and Report Surface

Dies ist der Einstiegspunkt fuer die externe LLM-Review von `compound_income_os`
nach `feat: surface decision quality in reports`.

## Current Review Head

- project: `compound_income_os`
- branch: `main`
- current_handoff_head: `785196fde4268eae4199bd0c6351419b8e3b18bf`
- current_handoff_short_head: `785196f`
- current_patch_context: `feat: surface decision quality in reports`
- previous_repo_head: `e8741657a56e9e31f6ea4757c59d7d518a27fce6`
- previous_handoff_head: `05c6b01eb6ef21c9b4f4833327ab3bb39d00b56a`
- canonical_contract:
  `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`

Das vorherige externe Packet fuer `05c6b01eb6ef21c9b4f4833327ab3bb39d00b56a`
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
   - `src/personal_run_engine.py`
   - `tests/test_personal_run_engine.py`
   - `src/build_monthly_decision_report.py`
   - `tests/test_monthly_decision_report.py`
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
Implementierungscommit `785196fde4268eae4199bd0c6351419b8e3b18bf`.

## Patch Scope

Dieses Packet enthaelt den Bugfix fuer host-unabhaengige Windows-/UNC-/
Traversal-Pfad-Redaction und eine minimale Decision-Quality-Surface in
bestehenden Reportflaechen:

- `src/personal_decision_quality_state.py`
- `tests/test_personal_decision_quality_state.py`
- `src/personal_run_engine.py`
- `tests/test_personal_run_engine.py`
- `src/build_monthly_decision_report.py`
- `tests/test_monthly_decision_report.py`
- minimale README-/Modulvertrag-/Roadmap-Referenzen

Der Producer erkennt Windows-Absolute-, UNC- und Traversal-Pfade vor Host-Path-
Resolution und schreibt keine lokalen Laufwerke, Usernamen, UNC-Servernamen
oder externe absolute Pfade in CSV/JSON/Markdown. Der Personal Run Report
rendert eine Decision-Quality-Sektion aus dem erzeugten State oder
`NOT_AVAILABLE`, wenn die Stage nicht gelaufen ist. Der Monthly Decision Report
Builder kann dieselbe Surface aus einem explizit uebergebenen State rendern.

Die Surface zeigt `decision_confidence_level` als Prozess-/Review-Confidence,
nicht als Investment-Confidence, Erfolgswahrscheinlichkeit, Alpha-Prognose oder
Order-Freigabe. `NOT_EVALUATED` fuer Ranking Robustness, Sensitivity, Scenario
und Tail Risk bleibt sichtbar.

## Reviewer Rules

- Vollstaendige relative Pfade verwenden.
- `src/personal_decision_quality_state.py`, `src/personal_run_engine.py`,
  `src/build_monthly_decision_report.py` und die zugehoerigen Tests als
  aktuelle Review-Einstiege behandeln.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Fundamentals, KPIs, Readiness-Ergebnisse oder Testergebnisse erfinden.
