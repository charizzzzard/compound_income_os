# Compound Income OS External LLM Review Packet - ZIP-Safe Watchlist Test Reproduction Fix

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach dem ZIP-safe Watchlist-/Monthly-Ranking-Testreproduktionsfix:

- commit: `1f04816860bbec2970603d68bbdfe7fe36d286fc`
- message: `test: make watchlist ranking fixture zip safe`
- status: `WATCHLIST_ZIP_SAFE_REPRODUCTION_FIX_ACCEPTED_WITH_FINDINGS`

Dieses Packet superseded aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck.

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- base_head: `6561ed78ec4204885afb62423d346215c0fc1706`
- implementation_head: `1f04816860bbec2970603d68bbdfe7fe36d286fc`
- implementation_short_head: `1f04816`
- current_handoff_head: `1f04816860bbec2970603d68bbdfe7fe36d286fc`
- current_handoff_short_head: `1f04816`
- delta_range: `6561ed78ec4204885afb62423d346215c0fc1706..1f04816860bbec2970603d68bbdfe7fe36d286fc`
- handoff_metadata_commit: `pending_until_metadata_commit`
- handoff_metadata_commit_note: `metadata commit is created after this file is written; use git HEAD after metadata commit or the operator final report for the exact metadata commit hash`
- bundle_purpose: `external_review_after_watchlist_zip_safe_fixture_fix`
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
- Pruefe `tests/test_watchlist_engine.py` darauf, dass
  `test_watchlist_and_monthly_ranking_block_missing_data_consistently` keine
  implizite Abhaengigkeit auf `data/raw/savings_plan_registry.csv` mehr hat.
- Pruefe, dass die Test-Fixture header-only, synthetisch und unter `tests/`
  temporaer erzeugt wird.
- Pruefe, dass `build_monthly_ranking(...)` im betroffenen Test einen
  expliziten `savings_plan_registry_path` erhaelt.
- Behandle `HANDOFF_VALIDATION.txt` als `RECORDED_VALIDATION`, sofern keine
  externe Kontextdatei oder ein Operatorbericht eine tatsaechliche Ausfuehrung
  als `EXECUTED_IN_CURRENT_REPO` oder `EXECUTED_IN_ZIP_CONTEXT` belegt.
- Behandle fehlendes `pytest` oder `ruff` als Environment-Realitaet, nicht als
  Erfolg und nicht automatisch als Repo-Logikfehler.
- Inferiere keine Valuation Automation, Investment Advice, Investment
  Readiness, Buy/Sell-Automation, Order Execution oder Product-/Production-
  Readiness.
- Fehlende, stale, unknown, invalid, inconsistent, conflict oder review states
  muessen sichtbar bleiben.
- Keine stille Imputation, keine stille Ueberschreibung akzeptierter Fakten.

## Review Scope

Reviewer sollen insbesondere pruefen:

- `tests/test_watchlist_engine.py`
- `src/savings_plan_registry.py`
- `src/monthly_ranking_engine.py`
- `src/watchlist_engine.py`
- `tests/test_savings_plan_registry.py`
- `tests/test_savings_plan_routing.py`
- extracted ZIP context execution for:
  - `python -m unittest tests.test_watchlist_engine -v`
  - `python -m unittest tests.test_operator_surface_wording -v`
  - `python -m unittest tests.test_valuation_scoring_semantic_decision_quality_review -v`

## Handoff Integrity Summary

- zip_file_count: `512`
- zip_size_bytes: `13169694`
- zip_sha256: `7de713aa27b0692226999ffeec79d34d2a616a30952d612ef7937cfe5c0ca1a1`
- sha_match: `True`
- zip_testzip: `None`
- missing_required: `[]`
- nested_zip_count: `0`
- forbidden_match_count: `0`
- local_path_leak_count: `0`
- delta_evidence_artifact: `HANDOFF_PATCH_IDENTITY.md`
- change_classification_artifact: `HANDOFF_CHANGE_CLASSIFICATION.csv`
- change_classification_rows: `1`

## Validation Reality

Executed in current local repo before implementation commit:

- `python -m unittest tests.test_operator_surface_wording -v`: PASS, 4 tests
- `python -m unittest tests.test_monthly_decision_report -v`: PASS, 13 tests
- `python -m unittest tests.test_watchlist_engine -v`: PASS, 9 tests
- `python -m unittest tests.test_valuation_scoring_semantic_decision_quality_review -v`: PASS, 12 tests
- `python -m unittest tests.test_savings_plan_registry -v`: PASS, 11 tests
- `python -m unittest tests.test_savings_plan_routing -v`: PASS, 21 tests
- `python -m unittest tests.test_reproduction_matrix -v`: PASS, 3 tests
- `python -m unittest discover -s tests -p "test_*.py"`: PASS, 894 tests
- `git diff --check`: PASS with LF-to-CRLF working-copy warnings only

Executed from extracted ZIP context without `.git`:

- `python -m unittest tests.test_watchlist_engine -v`: PASS, 9 tests
- `python -m unittest tests.test_operator_surface_wording -v`: PASS, 4 tests
- `python -m unittest tests.test_valuation_scoring_semantic_decision_quality_review -v`: PASS, 12 tests

Optional tools:

- `python -m pytest -q`: NOT_AVAILABLE, `No module named pytest`
- `python -m ruff check .`: NOT_AVAILABLE, `No module named ruff`

## Explicit Non-Scope

This packet does not claim or introduce:

- valuation automation
- new valuation methodology
- DCF engine
- analyst target price ingestion
- provider/API adapter, scraping or crawling
- broker import
- order execution
- Buy/Sell recommendation changes
- scoring formula changes
- ranking changes
- portfolio event ledger runtime
- replay, backtesting or simulation
- outcome attribution
- dashboard expansion
- tax calculation
- legal or commercial approval
- runtime enforcement engine
- runtime LLM decisioning
- product, production or investment readiness

Human Operator remains final acceptance authority.
