# External Review Packet - Stage 0 Validator And ZIP Reproduction Hardening

- patch_title: `STAGE_0_VALIDATOR_AND_ZIP_REPRO_HARDENING`
- bundle_purpose: `external_review_after_stage_0_validator_and_zip_repro_hardening`
- branch: `main`
- implementation_head: `46097b7f1040a9b3f022f3d9708217e6250b4c7f`
- base_head: `a12f2dba92d545c067e605bf5b34b4d0b12c670b`
- handoff_metadata_commit: assigned by Git after this handoff metadata commit
- current_origin_main_after_publish: verified through Git after push
- central_handoff_path: `external_review_packet/`
- handoff_zip: `external_review_packet/HANDOFF_LATEST.zip`
- handoff_sha256: `EB860E505DD1F1F523532CFB2B17250FA9288A8D3DC008695EE94AE7A7E96F9F`

## Review Scope

This packet packages the Stage-0 validator and ZIP reproducibility hardening
patch for external review. The patch closes carried-forward findings from
`OPERATIONAL_BACKBONE_STAGE_0_IDENTITY_AND_STAGING_PREFLIGHT` without expanding
scope into runtime broker import, Portfolio Event Ledger runtime, projections,
replay, outcome attribution, portfolio-state mutation or investment logic.

The patch hardens:

1. Instrument Master `asset_class` allowed-values and entry validation.
2. Broker Import Staging `PASS` / instrument-match invariants for synthetic
   instrument-bearing template rows.
3. Patch-profile ZIP dependency inclusion for validator modules that import
   `src.common`.
4. Reviewer wording that distinguishes `implementation_head`,
   `handoff_metadata_commit` / `publication_head`, and
   `current_origin_main_after_publish`.

## Primary Review Files

Inside the ZIP, start with:

1. `src/instrument_master_validation.py`
2. `tests/test_instrument_master_validation.py`
3. `docs/contracts/INSTRUMENT_MASTER_CONTRACT.md`
4. `docs/architecture/CIOS_INSTRUMENT_MASTER_TEMPLATE.yaml`
5. `src/broker_import_staging_validation.py`
6. `tests/test_broker_import_staging_validation.py`
7. `docs/contracts/BROKER_IMPORT_STAGING_CONTRACT.md`
8. `docs/architecture/CIOS_BROKER_IMPORT_STAGING_TEMPLATE.yaml`
9. `src/handoff_zip_export.py`
10. `tests/test_handoff_zip_export.py`
11. `tests/test_handoff_bundle.py`
12. `src/common.py`
13. `docs/governance/EXTERNAL_REPRODUCTION.md`
14. `HANDOFF_MANIFEST.csv`
15. `HANDOFF_ARTIFACT_INDEX.csv`
16. `HANDOFF_CHANGE_CLASSIFICATION.csv`
17. `HANDOFF_VALIDATION.txt`

## Validation Summary

Recorded local validation for this patch includes:

- `git diff --check`
- `python -m unittest tests.test_instrument_master_validation -v`
- `python -m unittest tests.test_broker_import_staging_validation -v`
- `python -m unittest tests.test_portfolio_event_ledger_validation -v`
- `python -m unittest tests.test_data_source_registry_validation -v`
- `python -m pytest tests/test_instrument_master_validation.py tests/test_broker_import_staging_validation.py -q`
- `python -m pytest tests/test_handoff_bundle.py tests/test_handoff_zip_export.py -q`
- `python -m ruff check src tests docs`
- `python -m pytest -q`

The full local pytest run reported `1048 passed, 443 subtests passed`.

## ZIP Policy

`HANDOFF_LATEST.zip` remains an ignored/untracked upload and transport artifact.
It is not force-added to Git. `HANDOFF_LATEST.sha256` is the committed integrity
pointer for the externally supplied ZIP.

For ZIP-safe Python validation, direct repo-local Python dependencies required
by included validator modules must also be present in the ZIP. This packet
includes `src/common.py` when Stage-0 validator modules are included.

## Boundary

This packet is pre-runtime validation and governance evidence only. It does not
implement portfolio logic, scoring formula changes, ranking formula changes,
valuation methodology changes, portfolio-rule changes, watchlist/fundamentals
logic changes, broker/provider/API integration, broker writes, order execution,
live trading, buy/sell automation, investment advice automation, backtesting,
replay, outcome attribution, production Event Ledger runtime, derived positions
runtime, private/raw portfolio publication, production readiness or investment
readiness.

Passing Instrument Master or Broker Import Staging validation does not approve
real instruments, broker import, event acceptance, portfolio-state mutation,
public redistribution, trading, replay or outcome attribution.

Human Operator remains final acceptance authority. External review must not
infer omitted private/raw/broker/provider/local/generated data.
