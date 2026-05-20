# Compound Income OS External LLM Review Packet - Dashboard Operator Surface Contracts

Dies ist der Einstiegspunkt fuer die externe LLM-Review von
`compound_income_os` nach
`docs: add dashboard operator surface contracts`.

## Current Review Head

- project: `compound_income_os`
- branch: `main`
- current_handoff_head: `0f267db5a43ac615131977ac2d227b14bc2d90fe`
- current_handoff_short_head: `0f267db`
- current_patch_context: `docs: add dashboard operator surface contracts`
- previous_repo_head: `7fd952731bc584df7f05492dacb02a78472b339a`
- previous_handoff_head: `e1ec6682942139ad14a7ffc7f59ef88bd6bc4c4e`
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

Das vorherige externe Packet fuer `e1ec6682942139ad14a7ffc7f59ef88bd6bc4c4e`
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
Implementierungscommit `0f267db5a43ac615131977ac2d227b14bc2d90fe`.

## Patch Scope

Dieses Packet enthaelt:

- den Dashboard Operator Surface Contract fuer read-only Operator-/Dashboard-
  Status ohne visuelles Dashboard-Neudesign,
- den Review Queue Summary Contract als Zielvertrag fuer
  `review_queue_summary.json`,
- die externe Reproduktionsmatrix fuer ZIP-safe, private-fixture und local-only
  Tests,
- Feature-Status-Haertung mit getrennten Repo-/Packet-/Generated-Handoff-
  Evidence-Feldern,
- Known-Gaps-Update fuer Dashboard Surface Contract, Review Queue Summary
  Contract, External Reproduction Matrix und Partial Artifact Availability.

Der Patch erzeugt keine Decisions, keine Orders, keine Portfolio-Events und
keine Outcome Attribution.

## Reviewer Rules

- Vollstaendige relative Pfade verwenden.
- Die neuen Contract-Dateien als Design-/Governance-Contract behandeln, nicht
  als bereits implementierten Dashboard Producer.
- `PARTIAL`, `NOT_AVAILABLE`, `PASS` und `REVIEW` Semantik gegen die bestehenden
  Decision Quality / Decision Journal Validation Surfaces pruefen.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Simulation, kein Backtesting, keine Outcome Attribution und kein
  Portfolio Event Ledger inferieren.
- Keine Fundamentals, KPIs, Readiness-Ergebnisse oder Testergebnisse erfinden.
