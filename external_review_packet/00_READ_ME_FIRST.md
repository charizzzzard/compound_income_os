# Compound Income OS External LLM Review Packet - Minimal Dashboard Operator Summary Producer

Dies ist der Einstiegspunkt fuer die externe LLM-Review von
`compound_income_os` nach
`feat: add minimal dashboard operator summary producer`.

## Current Review Head

- project: `compound_income_os`
- branch: `main`
- current_handoff_head: `d827bfc070706edec34cd2f62fa48caacc3888c7`
- current_handoff_short_head: `d827bfc`
- current_patch_context: `feat: add minimal dashboard operator summary producer`
- previous_repo_head: `93edeb8d6c5d6ba077f871392e751677bd040ba5`
- previous_handoff_head: `0f267db5a43ac615131977ac2d227b14bc2d90fe`
- canonical_dashboard_operator_surface_contract:
  `docs/contracts/DASHBOARD_OPERATOR_SURFACE_CONTRACT.md`
- canonical_review_queue_summary_contract:
  `docs/contracts/REVIEW_QUEUE_SUMMARY_CONTRACT.md`
- canonical_external_reproduction_matrix:
  `docs/governance/EXTERNAL_REPRODUCTION.md`
- canonical_feature_status:
  `docs/architecture/CIOS_FEATURE_STATUS.yaml`
- canonical_known_gaps:
  `docs/architecture/CURRENT_KNOWN_GAPS.md`

Das vorherige externe Packet fuer `0f267db5a43ac615131977ac2d227b14bc2d90fe`
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
   - `src/dashboard_operator_summary.py`
   - `tests/test_dashboard_operator_summary.py`
   - `docs/contracts/DASHBOARD_OPERATOR_SURFACE_CONTRACT.md`
   - `docs/contracts/REVIEW_QUEUE_SUMMARY_CONTRACT.md`
   - `docs/governance/EXTERNAL_REPRODUCTION.md`
   - `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
   - `docs/architecture/CIOS_FEATURE_STATUS.yaml`
   - `docs/architecture/CURRENT_KNOWN_GAPS.md`
   - `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`
   - `docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md`

## Dirty-State Interpretation

ZIP-internes `HANDOFF_CONTEXT.md` kann `dirty_worktree_present: True` zeigen,
weil `external_review_packet/HANDOFF_LATEST.sha256` vor der ZIP-Erzeugung
entfernt und danach neu geschrieben wurde. Das ist eine Handoff-Artefakt-
Regeneration, kein Patch-Source-Dirty-State.

Der finale Repo-HEAD kann nach diesem Packet ein separater
Handoff-Metadatencommit sein. Der aktuelle Handoff-Head bleibt der
Implementierungscommit `d827bfc070706edec34cd2f62fa48caacc3888c7`.

## Patch Scope

Dieses Packet enthaelt:

- den Dashboard Operator Surface Contract fuer read-only Operator-/Dashboard-
  Status ohne visuelles Dashboard-Neudesign,
- den Minimal Dashboard Operator Summary Producer
  `src/dashboard_operator_summary.py`,
- die Run-Engine-Stage `dashboard_operator_summary` nach
  `decision_journal_validation`,
- das Output-Artefakt `data/processed/review_queue_summary.json`,
- Contract-Haertung fuer maschinennahe Surface-Felder, dominante
  Artifact-Availability und strukturierte `source_artifacts`,
- Feature-Status-/Known-Gaps-Update fuer den neuen read-only Summary Producer,
- die externe Reproduktionsmatrix inklusive minimalem ZIP-Smoke.

Der Patch erzeugt keine Decisions, keine Orders, keine Portfolio-Events und
keine Outcome Attribution.

## Reviewer Rules

- Vollstaendige relative Pfade verwenden.
- Den neuen Producer als read-only Operator-Summary-Aggregator behandeln, nicht
  als visuelles Dashboard und nicht als Investmentlogik.
- `PARTIAL`, `NOT_AVAILABLE`, `PASS` und `REVIEW` Semantik gegen die bestehenden
  Decision Quality / Decision Journal Validation Surfaces pruefen.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Simulation, kein Backtesting, keine Outcome Attribution und kein
  Portfolio Event Ledger inferieren.
- Keine Fundamentals, KPIs, Readiness-Ergebnisse oder Testergebnisse erfinden.
