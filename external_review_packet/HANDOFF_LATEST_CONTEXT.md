# HANDOFF LATEST CONTEXT - ZIP-Safe Reproduction Hardening

project_name: compound_income_os
canonical_name: Compound Income OS
short_name: CIOS
profile: full_review
bundle_name: HANDOFF_LATEST
bundle_purpose: external_review_after_zip_safe_reproduction_hardening
created_at_utc: see_zip_internal_handoff_context
branch: main
head_before_implementation: 99c42e6d925d7dab48ce93423a94f14e1d27c3ba
implementation_head: 31a9d20986ad6731fd18f9b371d2881292db20c6
implementation_short_head: 31a9d20
current_handoff_head: 31a9d20986ad6731fd18f9b371d2881292db20c6
current_handoff_short_head: 31a9d20
handoff_metadata_commit: pending_until_metadata_commit
handoff_metadata_commit_note: the metadata commit is created after this file is written; use git HEAD after the metadata commit or the operator final report for the exact metadata commit hash. This avoids a self-referential hash requirement.
implementation_commit_message: test: add zip-safe reproduction smoke
implementation_status: ZIP_SAFE_REPRODUCTION_HARDENING_ACCEPTED_WITH_FINDINGS
tracked_source_worktree_clean_before_handoff_generation: True
zip_internal_dirty_worktree_present: False
external_metadata_dirty_after_zip_generation_before_commit: True
dirty_state_explanation: external_review_packet/HANDOFF_LATEST.sha256 and external metadata are regenerated after the ZIP is written; this is handoff metadata dirtiness, not source-patch dirtiness.

canonical_review_bundle: external_review_packet/HANDOFF_LATEST.zip
canonical_checksum: external_review_packet/HANDOFF_LATEST.sha256
canonical_readme: external_review_packet/00_READ_ME_FIRST.md

zip_file_count: 498
zip_size_bytes: 13124717
zip_sha256: aabc16d9bf275d4b2957e90cd621af89ddad127a44a5a0e99e71e24aa95225ce
sha_match: True
zip_testzip: None
missing_required: []
nested_zip_count: 0
forbidden_match_count: 0
local_path_leak_count: 0
internal_head: 31a9d20986ad6731fd18f9b371d2881292db20c6
internal_dirty_worktree_present: False

## Source-of-Truth / Precedence

Bei Konflikten gilt diese Reihenfolge:

1. `external_review_packet/00_READ_ME_FIRST.md`
2. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
3. `external_review_packet/HANDOFF_LATEST.zip`
4. `external_review_packet/HANDOFF_LATEST.sha256`
5. historische Reports nur als Kontext

ZIP-internes `HANDOFF_CONTEXT.md` ist generischer Exporter-Kontext. Wenn es mit
dieser Datei kollidiert, gewinnt diese externe Datei fuer Packet-Metadaten,
Head/SHA/Scope, Precedence, Dirty-State-Interpretation und
Reviewer-Instruktionen.

## Current Packet Scope

Dieses Packet synchronisiert den externen Review-Kontext auf den committed
Repo-Stand `31a9d20986ad6731fd18f9b371d2881292db20c6` nach
`test: add zip-safe reproduction smoke`.

Review-Schwerpunkte:

- `configs/test_reproduction_matrix.json`
- `tests/test_reproduction_matrix.py`
- `tests/test_zip_safe_operator_journey.py`
- `docs/governance/EXTERNAL_REPRODUCTION.md`
- `README.md`
- `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
- `src/data_freshness.py`
- `src/dashboard_operator_summary.py`
- `src/handoff_zip_export.py`
- `src/handoff_bundle.py`

## ZIP-Safe Reproduction Hardening

`configs/test_reproduction_matrix.json` classifies validation commands as
`ZIP_SAFE`, `LOCAL_REPO_REQUIRED`, `PRIVATE_INPUT_REQUIRED`,
`GIT_CONTEXT_REQUIRED`, `TOOLING_OPTIONAL` or `UNKNOWN`.

It also defines validation-result labels:

- `EXECUTED_IN_CURRENT_REPO`
- `EXECUTED_IN_ZIP_CONTEXT`
- `RECORDED_FROM_PREVIOUS_RUN`
- `NOT_AVAILABLE`
- `SKIPPED_BY_DESIGN`
- `FAILED`

`tests/test_zip_safe_operator_journey.py` provides a minimal synthetic operator
journey smoke test. It uses only test-local synthetic fixtures and stdlib code,
generates Data Freshness JSON/Markdown plus Dashboard Operator Summary JSON in a
temporary test directory, and verifies that `MISSING`, `STALE` and `UNKNOWN`
states remain visible.

The smoke test is intentionally not a full personal-run replacement. It is a
ZIP-safe external-review smoke designed to avoid `.git`, private/raw inputs,
network access, broker writes, order execution and readiness claims.

## Explicit Non-Scope

- keine Investmentlogik
- kein produktiver Portfolio Event Ledger
- keine Event-Ledger-Runtime
- kein Broker Import
- kein Broker Parser
- kein Provider Adapter
- keine API-Anbindung
- kein Scraping oder Web-Crawling
- keine automatische Transaktionsklassifikation
- keine Corporate Actions Engine
- keine FX Engine
- kein Replay, Backtesting oder Simulation
- keine Outcome Attribution
- kein Dashboard
- keine Valuation Automation
- keine Buy/Sell Recommendation Aenderungen
- keine Steuerberechnung
- keine Legal-/Commercial-Freigabe
- keine Order Execution
- keine Runtime-LLM-Agentenlogik
- keine Runtime-Enforcement-Engine
- keine automatische Release-Akzeptanz
- keine Product-/Production-Readiness
- keine Investment-Readiness

## Validation Actually Performed

Preflight:

- `git branch --show-current`
  - result: `main`
- `git rev-parse HEAD`
  - result before implementation: `99c42e6d925d7dab48ce93423a94f14e1d27c3ba`
- `git status --short`
  - result before implementation: clean
- `python --version`
  - result: `Python 3.14.0`
- `python -m pytest --version`
  - result: failed because `pytest` is not installed in the active Python environment: `No module named pytest`
- `python -m ruff --version`
  - result: failed because `ruff` is not installed in the active Python environment: `No module named ruff`
- `git status --short --ignored external_review_packet`
  - result included ignored `external_review_packet/HANDOFF_LATEST.zip`

Targeted validation before handoff:

- `python -m unittest tests.test_zip_safe_operator_journey -v`
  - result: `Ran 1 test`, `OK`
- `python -m unittest tests.test_reproduction_matrix -v`
  - result: `Ran 3 tests`, `OK`
- `python -m unittest tests.test_readme_and_reports -v`
  - result: `Ran 14 tests`, `OK`
- `python -m unittest discover -s tests -p "test_*.py"`
  - result: `Ran 833 tests`, `OK`
- `git diff --check`
  - result: exit code `0`; no whitespace errors

Optional validation attempted:

- `python -m pytest -q`
  - result: failed because `pytest` is not installed in the active Python environment: `No module named pytest`
- `python -m ruff check .`
  - result: failed because `ruff` is not installed in the active Python environment: `No module named ruff`

No pytest success is claimed because `pytest` is not installed in the active
environment, and no ruff lint success is claimed. The full unittest discovery
suite was run locally and passed as listed above; this remains
`EXECUTED_IN_CURRENT_REPO`, not automatically `EXECUTED_IN_ZIP_CONTEXT`.

Handoff generation:

- `python -m src.handoff_zip_export --profile full_review --name HANDOFF_LATEST --output-path external_review_packet/HANDOFF_LATEST.zip --validation-command "python -m unittest tests.test_zip_safe_operator_journey -v" --validation-command "python -m unittest tests.test_reproduction_matrix -v" --validation-command "python -m unittest discover -s tests -p test_*.py" --validation-command "git diff --check" --validation-command "python -m pytest -q" --validation-command "python -m ruff check ."`
  - result: generated ZIP for head `31a9d20986ad6731fd18f9b371d2881292db20c6`
  - file_count: `498`
  - size_bytes: `13124717`
  - zip_sha256: `aabc16d9bf275d4b2957e90cd621af89ddad127a44a5a0e99e71e24aa95225ce`
  - forbidden_match_count: `0`
  - local_path_leak_count: `0`

ZIP-context smoke validation after handoff:

- Extracted a minimal subset from `external_review_packet/HANDOFF_LATEST.zip`
  into a temporary test directory without `.git`.
- `python -m unittest tests.test_zip_safe_operator_journey -v`
  - result: return code `0`; `Ran 1 test`, `OK`
- `python -m unittest tests.test_reproduction_matrix -v`
  - result: return code `0`; `Ran 3 tests`, `OK`
- This is `EXECUTED_IN_ZIP_CONTEXT` evidence for the ZIP-safe smoke and matrix
  only. It is not a claim that the full local unittest suite was executed from
  ZIP context.

## Remaining Findings

- `pytest` is not installed in the active Python environment.
- `ruff` is not installed in the active Python environment.
- Full local unittest success is evidence from the current checkout, not proof
  that every test is ZIP-only reproducible.
- Handoff exporter/bundle tests remain local-repo/Git-context validation, not
  ZIP-only smoke tests.
