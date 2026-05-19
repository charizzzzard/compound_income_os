# Compound Income OS External LLM Review Packet - Decision Quality Contract Consistency Fix

Dies ist der Einstiegspunkt fuer die externe LLM-Review von `compound_income_os`
nach dem Docs-only Fix `docs: fix decision quality contract consistency`.

## Current Review Head

- project: `compound_income_os`
- branch: `main`
- current_handoff_head: `d913567c3f5d9b80f910ee68db1fc82b1dfc20c7`
- current_handoff_short_head: `d913567`
- current_patch_context: `docs: fix decision quality contract consistency`
- previous_repo_head: `fc0d879d3c5618621eaff93ce6eb41882082632e`
- previous_handoff_head: `54156127153f45614d165414e4a97a9be2aba1ed`
- canonical_contract:
  `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`

Das vorherige externe Packet fuer `54156127153f45614d165414e4a97a9be2aba1ed`
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
   - `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md`
   - `docs/architecture/DECISION_QUALITY_LAYER.md`
   - `docs/governance/BASELINE_VS_CANDIDATE_VALIDATION.md`
   - `docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md`
   - `src/personal_input_closure.py`
   - `src/personal_decision_state_capture.py`
   - `docs/architecture/05_ARCHITECTURE_BACKLOG.csv`
   - `docs/architecture/06_ADOPTED_DECISIONS.yaml`

## Dirty-State Interpretation

ZIP-internes `HANDOFF_CONTEXT.md` kann `dirty_worktree_present: True` zeigen,
weil `external_review_packet/HANDOFF_LATEST.sha256` vor der ZIP-Erzeugung
entfernt und danach neu geschrieben wurde. Das ist eine Handoff-Artefakt-
Regeneration, kein Patch-Source-Dirty-State.

Der finale Repo-HEAD kann nach diesem Packet ein separater
Handoff-Metadatencommit sein. Der aktuelle Handoff-Head bleibt der
Implementierungscommit `d913567c3f5d9b80f910ee68db1fc82b1dfc20c7`.

## Patch Scope

Dieses Packet enthaelt einen minimalen Docs-only Contract-Fix:

- kritische `missing_critical_fields` sind jetzt eindeutige `REVIEW` Hard
  Blocker
- `review_required=true` ist auf Hard Blocker begrenzt
- Ranking/Sensitivity `NOT_EVALUATED` cappt in Phase 1.5 nur Confidence auf
  maximal `MEDIUM`
- `evidence_coverage_pct`/nicht messbare Coverage ist ohne Evidence-Enum-
  Erweiterung geklaert
- Beispiele verwenden contract-konforme lowercase Booleans
- Patch 1.5A bleibt ohne Producer; Phase 1.5B ist die erste moegliche
  Implementierung

## Reviewer Rules

- Vollstaendige relative Pfade verwenden.
- `docs/contracts/DECISION_QUALITY_STATE_CONTRACT.md` als kanonischen Einstieg
  fuer diesen Fix behandeln.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Fundamentals, KPIs, Readiness-Ergebnisse oder Testergebnisse erfinden.
