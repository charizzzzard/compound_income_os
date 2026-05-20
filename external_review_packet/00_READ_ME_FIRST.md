# Compound Income OS External LLM Review Packet - Data Freshness Integration

Dies ist der Einstiegspunkt fuer die externe LLM-Review von
`compound_income_os` nach
`feat: integrate data freshness into personal run`.

## Current Review Head

- project: `compound_income_os`
- branch: `main`
- current_handoff_head: `17cff48e340a706551994aceda23143b268e8a9a`
- current_handoff_short_head: `17cff48`
- current_patch_context: `Data Freshness / Staleness Personal Run Integration`
- previous_repo_head: `3b7fe7d6fece46705a8ab617534def99a015406f`
- previous_handoff_head: `e17fc944cdc956bce1a41d2f7768af9af25c6a9f`
- canonical_data_freshness_contract:
  `docs/contracts/DATA_FRESHNESS_STALENESS_CONTRACT.md`
- canonical_data_freshness_config:
  `configs/data_freshness_thresholds.yaml`
- canonical_data_freshness_producer:
  `src/data_freshness.py`
- canonical_data_freshness_tests:
  `tests/test_data_freshness.py`
- canonical_personal_run_stage_dag:
  `docs/architecture/PERSONAL_RUN_STAGE_DAG.md`
- canonical_dashboard_operator_summary:
  `src/dashboard_operator_summary.py`
- canonical_dashboard_operator_tests:
  `tests/test_dashboard_operator_summary.py`
- canonical_system_map:
  `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
- canonical_feature_status:
  `docs/architecture/CIOS_FEATURE_STATUS.yaml`
- canonical_known_gaps:
  `docs/architecture/CURRENT_KNOWN_GAPS.md`
- canonical_external_reproduction_matrix:
  `docs/governance/EXTERNAL_REPRODUCTION.md`

Das vorherige externe Packet fuer `3b7fe7d6fece46705a8ab617534def99a015406f`
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
   - `docs/contracts/DATA_FRESHNESS_STALENESS_CONTRACT.md`
   - `configs/data_freshness_thresholds.yaml`
   - `src/data_freshness.py`
   - `tests/test_data_freshness.py`
   - `src/personal_run_engine.py`
   - `tests/test_personal_run_engine.py`
   - `src/dashboard_operator_summary.py`
   - `tests/test_dashboard_operator_summary.py`
   - `docs/architecture/PERSONAL_RUN_STAGE_DAG.md`
   - `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
   - `docs/architecture/CIOS_FEATURE_STATUS.yaml`
   - `docs/architecture/CURRENT_KNOWN_GAPS.md`
   - `docs/governance/EXTERNAL_REPRODUCTION.md`

## Dirty-State Interpretation

ZIP-internes `HANDOFF_CONTEXT.md` kann `dirty_worktree_present: True` zeigen,
weil `external_review_packet/HANDOFF_LATEST.sha256` und diese externen
Metadaten nach der ZIP-Erzeugung neu geschrieben wurden. Das ist eine
Handoff-Artefakt-Regeneration, kein Patch-Source-Dirty-State.

Der finale Repo-HEAD kann nach diesem Packet ein separater
Handoff-Metadatencommit sein. Der aktuelle Handoff-Head ist der letzte
Implementierungscommit `17cff48e340a706551994aceda23143b268e8a9a`.

## Patch Scope

Dieses Packet enthaelt:

- konservative Multi-Row-Freshness-Semantik in `src.data_freshness`,
- neue stabile Item-Felder fuer min/max/valid/invalid/missing/record counts,
- `data_freshness` als read-only Stage in `src.personal_run_engine`,
- `data/processed/data_freshness_summary.json` und
  `reports/<as_of_date>/data_freshness_summary.md` als Stage-Outputs,
- Data-Freshness-Felder in `src.dashboard_operator_summary`,
- Tests fuer Producer, Stage-Integration und Operator-Summary-Semantik,
- Cross-References in README, System Map, Feature Status, Known Gaps, Module
  Contracts, Stage-DAG, Roadmap und External Reproduction.

Der Patch erzeugt keine Decisions, keine Orders, keine Portfolio-Events, keine
Simulation, kein Replay und keine Outcome Attribution.

## Reviewer Rules

- Freshness darf nur aus expliziten Datumsfeldern oder dokumentierten
  Freshness-Signalen stammen.
- Bei Multi-Row-Artefakten steuert das aelteste valide Datum die
  Staleness-Bewertung.
- Zukunftsdatumswerte und invalide Datumswerte duerfen nicht als `FRESH`
  gerendert werden.
- `MISSING`, `UNKNOWN`, `STALE` und `REVIEW_REQUIRED` duerfen nicht als
  `FRESH` interpretiert werden.
- File-Existenz allein und Dateinamen sind keine Freshness-Belege.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Simulation, kein Backtesting, keine Outcome Attribution und kein
  Portfolio Event Ledger inferieren.
