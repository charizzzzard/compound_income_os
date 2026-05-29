# Compound Income OS External LLM Review Packet - Dashboard Freshness Surface Contract

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach dem contract-/test-only Governance-Patch
`DASHBOARD_FRESHNESS_SURFACE_CONTRACT`.

- commit: `37c760114a400bbd702b185c90816015eb916369`
- message: `Add dashboard freshness surface contract`
- status: `DASHBOARD_FRESHNESS_SURFACE_CONTRACT_READY_FOR_EXTERNAL_REVIEW`

Dieses Packet ersetzt aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck.

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- base_head: `656e1a475c541ebd7b7e41eb16ba682f289a95a4`
- implementation_head: `37c760114a400bbd702b185c90816015eb916369`
- implementation_short_head: `37c7601`
- current_handoff_head: `37c760114a400bbd702b185c90816015eb916369`
- current_handoff_short_head: `37c7601`
- delta_range: `656e1a475c541ebd7b7e41eb16ba682f289a95a4..37c760114a400bbd702b185c90816015eb916369`
- handoff_metadata_commit: `pending_metadata_commit_after_packet_synchronization`
- handoff_metadata_commit_note: `external_review_packet tracked metadata is synchronized after the implementation commit; the ZIP content itself is exported from implementation_head.`
- bundle_purpose: `external_review_after_dashboard_freshness_surface_contract`
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
- Pruefe, dass `HANDOFF_PATCH_IDENTITY.md` im ZIP die patch-spezifischen Werte
  enthaelt:
  - `patch_title: DASHBOARD_FRESHNESS_SURFACE_CONTRACT`
  - `bundle_purpose: external_review_after_dashboard_freshness_surface_contract`
  - `implementation_head: 37c760114a400bbd702b185c90816015eb916369`
- Pruefe, dass `HANDOFF_CHANGE_CLASSIFICATION.csv` genau diese sieben
  patch-geaenderten Dateien ausweist:
  - `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
  - `docs/architecture/CIOS_FEATURE_STATUS.yaml`
  - `docs/architecture/CURRENT_KNOWN_GAPS.md`
  - `docs/contracts/DASHBOARD_FRESHNESS_SURFACE_CONTRACT.md`
  - `docs/contracts/DASHBOARD_OPERATOR_SURFACE_CONTRACT.md`
  - `docs/contracts/DATA_FRESHNESS_STALENESS_CONTRACT.md`
  - `tests/test_dashboard_freshness_surface_contract.py`
- Pruefe, dass `HANDOFF_VALIDATION.txt` weiterhin `RECORDED_VALIDATION` als
  Provenienz verwendet.
- Inferiere keine ausgelassenen privaten, raw, Broker- oder Provider-Dateien.
- Inferiere keine Valuation Automation, DCF, Investment Advice, Investment
  Readiness, Buy/Sell-Automation, Order Execution oder Product-/Production-
  Readiness.

## Review Scope

Reviewer sollen insbesondere pruefen:

- `docs/contracts/DASHBOARD_FRESHNESS_SURFACE_CONTRACT.md`
- `tests/test_dashboard_freshness_surface_contract.py`
- `docs/contracts/DATA_FRESHNESS_STALENESS_CONTRACT.md`
- `docs/contracts/DASHBOARD_OPERATOR_SURFACE_CONTRACT.md`
- `docs/architecture/CIOS_FEATURE_STATUS.yaml`
- `docs/architecture/CURRENT_KNOWN_GAPS.md`
- `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
- ZIP-internal:
  - `HANDOFF_CONTEXT.md`
  - `HANDOFF_PATCH_IDENTITY.md`
  - `HANDOFF_CHANGE_CLASSIFICATION.csv`
  - `HANDOFF_VALIDATION.txt`

## Handoff Integrity Summary

- zip_file_count: `518`
- zip_size_bytes: `13190399`
- zip_sha256: `19c75b6989806cb1e345bcaebac2be9a6d31ffa988370fe26d1f7722ad4c6d29`
- sha_match: `True`
- zip_testzip: `None`
- missing_required: `[]`
- nested_zip_count: `0`
- forbidden_match_count: `0`
- local_path_leak_count: `0`
- delta_evidence_artifact: `HANDOFF_PATCH_IDENTITY.md`
- change_classification_artifact: `HANDOFF_CHANGE_CLASSIFICATION.csv`
- change_classification_rows: `7`

## Validation Reality

Executed in current local repo before handoff synchronization:

- `python -m pytest tests/test_dashboard_freshness_surface_contract.py -q`: PASS, 10 tests, 59 subtests
- `python -m pytest tests/test_dashboard_operator_summary.py -q`: PASS, 16 tests
- `python -m pytest tests/test_personal_run_engine.py -q`: PASS, 60 tests, 2 subtests
- `python -m pytest -q`: PASS, 939 tests, 278 subtests
- `python -m ruff check .`: PASS
- `python -m unittest discover -s tests -p "test_*.py" -v`: PASS, 939 tests
- `git diff --check`: PASS, LF/CRLF working-copy warning only

ZIP-internes `HANDOFF_VALIDATION.txt` records requested validation commands as
`RECORDED_VALIDATION`; those lines are not automatic proof that an external
reviewer executed them from the ZIP.

## Explicit Non-Scope

This packet does not claim or introduce:

- runtime behavior changes
- scoring changes
- ranking changes
- valuation changes
- dashboard semantics changes
- monthly report semantics changes
- DCF engine
- valuation automation
- provider/API integration
- scraping or crawling
- broker import
- order execution
- buy/sell automation
- investment advice
- replay, backtesting or simulation
- outcome attribution
- dashboard UI/server
- runtime enforcement
- product, production or investment readiness

Human Operator remains final acceptance authority.
