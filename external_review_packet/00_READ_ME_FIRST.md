# Compound Income OS External LLM Review Packet - Personal Run Stage DAG

Dies ist der Einstiegspunkt fuer die externe LLM-Review von
`compound_income_os` nach
`docs: add personal run stage dag`.

## Current Review Head

- project: `compound_income_os`
- branch: `main`
- current_handoff_head: `1fe3b85d20afa1a91d65137ccfb98c337ee017db`
- current_handoff_short_head: `1fe3b85`
- current_patch_context: `docs: add personal run stage dag`
- previous_repo_head: `15b1d73f170d0eaf927d3b9802f09569e79b349b`
- previous_handoff_head: `251635b509c24328c57edc4947becd93fb31d886`
- canonical_personal_run_stage_dag:
  `docs/architecture/PERSONAL_RUN_STAGE_DAG.md`
- canonical_personal_run_engine:
  `src/personal_run_engine.py`
- canonical_system_map:
  `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
- canonical_feature_status:
  `docs/architecture/CIOS_FEATURE_STATUS.yaml`
- canonical_known_gaps:
  `docs/architecture/CURRENT_KNOWN_GAPS.md`
- canonical_external_reproduction_matrix:
  `docs/governance/EXTERNAL_REPRODUCTION.md`

Das vorherige externe Packet fuer `251635b509c24328c57edc4947becd93fb31d886`
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
   - `.gitattributes`
   - `docs/architecture/PERSONAL_RUN_STAGE_DAG.md`
   - `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
   - `docs/architecture/CIOS_FEATURE_STATUS.yaml`
   - `docs/architecture/CURRENT_KNOWN_GAPS.md`
   - `docs/governance/EXTERNAL_REPRODUCTION.md`
   - `src/personal_run_engine.py`
   - `tests/test_personal_run_engine.py`
   - `tests/test_readme_and_reports.py`

## Dirty-State Interpretation

ZIP-internes `HANDOFF_CONTEXT.md` kann `dirty_worktree_present: True` zeigen,
weil `external_review_packet/HANDOFF_LATEST.sha256` nach der ZIP-Erzeugung
neu geschrieben wurde. Das ist eine Handoff-Artefakt-Regeneration, kein
Patch-Source-Dirty-State.

Der finale Repo-HEAD kann nach diesem Packet ein separater
Handoff-Metadatencommit sein. Der aktuelle Handoff-Head ist der letzte
Implementierungscommit `1fe3b85d20afa1a91d65137ccfb98c337ee017db`.

## Patch Scope

Dieses Packet enthaelt:

- `docs/architecture/PERSONAL_RUN_STAGE_DAG.md` als kanonische
  Stage-DAG-/Orchestrator-Review-Dokumentation,
- Cross-References in README, System Map, Feature Status, Known Gaps, Module
  Contracts, Roadmap und External Reproduction,
- einen Docs-Test, der die neue Datei gegen die echte `STAGE_ORDER` aus
  `src.personal_run_engine` absichert,
- ein aktualisiertes Handoff-ZIP mit `PERSONAL_RUN_STAGE_DAG.md`.

Der Patch dokumentiert Orchestrierung, Failure-/Skip-Semantik und Lineage. Er
erzeugt keine Decisions, keine Orders, keine Portfolio-Events, keine Simulation,
kein Replay und keine Outcome Attribution.

## Reviewer Rules

- `src/personal_run_engine.py` bleibt Source of Truth fuer die tatsaechliche
  Ausfuehrung.
- `docs/architecture/PERSONAL_RUN_STAGE_DAG.md` ist Review-/Governance-Doku,
  keine neue Runtime-Logik.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Simulation, kein Backtesting, keine Outcome Attribution und kein
  Portfolio Event Ledger inferieren.
- Keine Fundamentals, KPIs, Readiness-Ergebnisse oder Testergebnisse erfinden.
