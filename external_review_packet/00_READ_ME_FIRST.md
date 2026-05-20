# Compound Income OS External LLM Review Packet - Operator Summary Semantics + Handoff Hygiene

Dies ist der Einstiegspunkt fuer die externe LLM-Review von
`compound_income_os` nach
`fix: harden operator summary and handoff hygiene`.

## Current Review Head

- project: `compound_income_os`
- branch: `main`
- current_handoff_head: `12f2099e5cfe53c2d0192ee236c584fc3ade5144`
- current_handoff_short_head: `12f2099`
- current_patch_context: `fix: harden operator summary and handoff hygiene`
- previous_repo_head: `1caa36994fc273aa0b3073a5feb5bf883ad3659b`
- previous_handoff_head: `d827bfc070706edec34cd2f62fa48caacc3888c7`
- canonical_dashboard_operator_summary_producer:
  `src/dashboard_operator_summary.py`
- canonical_handoff_exporter:
  `src/handoff_zip_export.py`
- canonical_handoff_bundle:
  `src/handoff_bundle.py`
- canonical_external_reproduction_matrix:
  `docs/governance/EXTERNAL_REPRODUCTION.md`
- canonical_dashboard_operator_surface_contract:
  `docs/contracts/DASHBOARD_OPERATOR_SURFACE_CONTRACT.md`
- canonical_review_queue_summary_contract:
  `docs/contracts/REVIEW_QUEUE_SUMMARY_CONTRACT.md`

Das vorherige externe Packet fuer `d827bfc070706edec34cd2f62fa48caacc3888c7`
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
   - `src/dashboard_operator_summary.py`
   - `tests/test_dashboard_operator_summary.py`
   - `src/handoff_bundle.py`
   - `src/handoff_zip_export.py`
   - `tests/test_handoff_bundle.py`
   - `tests/test_handoff_zip_export.py`
   - `docs/contracts/DASHBOARD_OPERATOR_SURFACE_CONTRACT.md`
   - `docs/contracts/REVIEW_QUEUE_SUMMARY_CONTRACT.md`
   - `docs/governance/EXTERNAL_REPRODUCTION.md`

## Dirty-State Interpretation

ZIP-internes `HANDOFF_CONTEXT.md` kann `dirty_worktree_present: True` zeigen,
weil `external_review_packet/HANDOFF_LATEST.sha256` nach der ZIP-Erzeugung
neu geschrieben wurde. Das ist eine Handoff-Artefakt-Regeneration, kein
Patch-Source-Dirty-State.

Der finale Repo-HEAD kann nach diesem Packet ein separater
Handoff-Metadatencommit sein. Der aktuelle Handoff-Head bleibt der
Implementierungscommit `12f2099e5cfe53c2d0192ee236c584fc3ade5144`.

## Patch Scope

Dieses Packet enthaelt:

- den Semantik-Fix: lesbares Decision Quality `review_required=true` verhindert
  `surface_status=PASS` und setzt `DECISION_QUALITY_REVIEW_REQUIRED`,
- Regression-Tests fuer Decision-Quality-Review-Semantik in der Operator
  Summary,
- `.gitattributes` im Full-Review-Handoff fuer ZIP-safe
  `tests.test_readme_and_reports`,
- Ausschluss alter `website_static_build_package_*` Artefakte aus dem
  Full-Review-Handoff,
- einen ZIP-Content-Scanner gegen lokale absolute User-Pfade in produktiven
  Handoff-Artefakten,
- minimale Contract-/Reproduction-Doku zur neuen Semantik und ZIP-Repro.

Der Patch erzeugt keine Decisions, keine Orders, keine Portfolio-Events und
keine Outcome Attribution.

## Reviewer Rules

- Vollstaendige relative Pfade verwenden.
- Den Operator Summary Producer als read-only Governance-Surface behandeln,
  nicht als visuelles Dashboard und nicht als Investmentlogik.
- `review_required=true` in Decision Quality als Operator-Review-Signal
  pruefen; es darf nicht zu `PASS` werden.
- `.gitattributes` muss im ZIP vorhanden sein, wenn
  `tests.test_readme_and_reports` als ZIP-safe Smoke-Test empfohlen wird.
- Keine ausgelassenen privaten oder rohen Dateien inferieren.
- Keine Broker-Writes, HTTP-Calls, Order-Ausfuehrung, Auto-Trading,
  Steuerquantifizierung oder Runtime-LLM-Entscheidungen inferieren.
- Keine Simulation, kein Backtesting, keine Outcome Attribution und kein
  Portfolio Event Ledger inferieren.
- Keine Fundamentals, KPIs, Readiness-Ergebnisse oder Testergebnisse erfinden.
