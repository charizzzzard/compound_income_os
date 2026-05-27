# Compound Income OS External LLM Review Packet - Runtime Gate Definition Template

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach dem Governance-/Contract-Patch:

- commit: `87c95febbd2d05a5bae7e80739e4f9f9719ee358`
- message: `docs: add runtime gate definition template`
- status: `RUNTIME_GATE_DEFINITION_TEMPLATE_ACCEPTED_WITH_FINDINGS`

Dieses Packet superseded aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck.

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- implementation_head: `87c95febbd2d05a5bae7e80739e4f9f9719ee358`
- implementation_short_head: `87c95fe`
- current_handoff_head: `87c95febbd2d05a5bae7e80739e4f9f9719ee358`
- current_handoff_short_head: `87c95fe`
- handoff_metadata_commit: `pending_until_metadata_commit`
- handoff_metadata_commit_note: `metadata commit is created after this file is written; use git HEAD after metadata commit or the operator final report for the exact metadata commit hash`
- bundle_purpose: `external_review_after_runtime_gate_definition_template`
- canonical_review_bundle: `external_review_packet/HANDOFF_LATEST.zip`
- canonical_checksum: `external_review_packet/HANDOFF_LATEST.sha256`
- canonical_context: `external_review_packet/HANDOFF_LATEST_CONTEXT.md`

## Source-of-Truth / Precedence

Bei Konflikten gilt diese Reihenfolge:

1. `external_review_packet/00_READ_ME_FIRST.md`
2. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
3. `external_review_packet/HANDOFF_LATEST.zip`
4. `external_review_packet/HANDOFF_LATEST.sha256`
5. historische Reports nur als Kontext

ZIP-internes `HANDOFF_CONTEXT.md` ist generischer Exporter-Kontext. Wenn es mit
`external_review_packet/HANDOFF_LATEST_CONTEXT.md` kollidiert, gewinnt die
externe Kontextdatei fuer Packet-Metadaten, Review-Scope, Precedence,
Dirty-State-Interpretation und Operator-/Reviewer-Instruktionen.

## Reviewer Instructions

- Verwende volle repo-relative Pfade in Findings.
- Inferiere keine ausgelassenen privaten, raw, Broker- oder Provider-Dateien.
- Behandle `docs/contracts/RUNTIME_GATE_DEFINITION_TEMPLATE.md` als
  Governance-/Contract-Template, nicht als Runtime-Enforcement-Engine.
- Behandle `docs/contracts/RUNTIME_GATE_BOUNDARY_CONTRACT.md` als
  Governance-/Design-Contract, nicht als Runtime-Enforcement-Engine.
- Behandle `src.runtime_enforcement_boundary_review` als read-only
  Governance-Review, nicht als Runtime-Enforcement-Engine, nicht als
  Release-Akzeptanz und nicht als Product-/Production-/Investment-Readiness.
- Das Ausfuellen des Runtime-Gate-Templates macht keinen Gate
  runtime-enforced.
- Unterscheide `documentation_only`, `review_evidence`,
  `runtime_relevant_candidate` und kuenftige `runtime_enforced` Semantik.
- Unterscheide `RECORDED` Handoff-Commands von tatsaechlich ausgefuehrten
  Pass/Fail-Ergebnissen.
- Unterscheide Tool-Verfuegbarkeit von Command-Erfolg.
- Inferiere keine Release-, Product-, Investment-, Broker-Import-, Replay-,
  Backtesting-, Dashboard- oder Outcome-Attribution-Readiness.
- Fehlende, stale oder unknown Daten muessen sichtbar bleiben.
- Keine stille Imputation, keine stille Ueberschreibung akzeptierter Fakten,
  keine Investment Advice und keine Order Execution.

## Review Scope

Reviewer sollen insbesondere pruefen:

- Runtime Gate Definition Template:
  - `docs/contracts/RUNTIME_GATE_DEFINITION_TEMPLATE.md`
  - `tests/test_runtime_gate_definition_template.py`
- Runtime Gate Boundary Contract:
  - `docs/contracts/RUNTIME_GATE_BOUNDARY_CONTRACT.md`
  - `tests/test_runtime_gate_boundary_contract.py`
- Runtime Enforcement Boundary Review:
  - `src/runtime_enforcement_boundary_review.py`
  - `tests/test_runtime_enforcement_boundary_review.py`
- External Review Gate Governance:
  - `docs/governance/EXTERNAL_REVIEW_COVERAGE_STANDARD.md`
  - `docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml`
  - `docs/governance/EXTERNAL_REVIEW_GATE_SEQUENCE.md`
- Status and cross-reference consistency:
  - `docs/architecture/CIOS_FEATURE_STATUS.yaml`
  - `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
  - `docs/MODULE_CONTRACTS.md`
  - `docs/CONTEXT_AND_ROADMAP.md`
  - `README.md`

## Explicit Non-Scope

Dieses Packet fuehrt nicht ein:

- Investmentlogik
- produktiver Portfolio Event Ledger
- Event-Ledger-Runtime
- Broker Import
- Broker Parser
- Provider Adapter
- API-Anbindung
- Scraping oder Web-Crawling
- automatische Transaktionsklassifikation
- Corporate Actions Engine
- FX Engine
- Replay, Backtesting oder Simulation
- Outcome Attribution
- Dashboard
- Valuation Automation
- Buy/Sell Recommendation Aenderungen
- Steuerberechnung
- Legal-/Commercial-Freigabe
- Order Execution
- Runtime-LLM-Agentenlogik
- Runtime-Enforcement-Engine
- automatische Release-Akzeptanz
- vollautomatische Release-Akzeptanz
- Product-/Production-Readiness
- Investment-Readiness

## Reviewer Notes

- Das neue Template standardisiert kuenftige Runtime-Gate-Vorschlaege.
- Aktuelle Governance-Producer bleiben `review_evidence` oder
  `documentation_only`.
- Kein aktueller Producer wird als runtime-enforced klassifiziert.
- Kein Gate darf automatische Release-Akzeptanz erhalten.
- Future runtime-sensitive areas bleiben Kandidaten mit separaten
  Contract-/Test-/Evidence-/Operator-Acceptance-Anforderungen.
- `python -m unittest tests.test_runtime_gate_definition_template -v` ergab
  `Ran 8 tests`, `OK`.
- `python -m unittest tests.test_runtime_gate_boundary_contract -v` ergab
  `Ran 7 tests`, `OK`.
- `python -m unittest discover -s tests -p "test_*.py" -v` wurde ausgefuehrt
  und ergab `Ran 824 tests`, `OK`.
- `pytest` und `ruff` waren im aktiven Python-Environment nicht installiert;
  daraus wurde kein Erfolg abgeleitet.
- Final Acceptance bleibt beim Human Operator.
