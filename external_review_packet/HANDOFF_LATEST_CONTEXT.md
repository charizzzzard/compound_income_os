# HANDOFF LATEST CONTEXT - Cross-Patch Regression Governance Check

project_name: compound_income_os
canonical_name: Compound Income OS
short_name: CIOS
profile: full_review
bundle_name: HANDOFF_LATEST
bundle_purpose: external_review_after_cross_patch_regression_governance_check
created_at_utc: 2026-05-21T13:10:00Z
branch: main
implementation_head: e20113b374d78dea1bd575f65e587bb37b4f314e
implementation_short_head: e20113b
current_handoff_head: e20113b374d78dea1bd575f65e587bb37b4f314e
current_handoff_short_head: e20113b
implementation_commit_message: feat: add cross-patch regression governance check
implementation_status: CROSS_PATCH_REGRESSION_REVIEW_OPERATIONALIZED_ACCEPTED_WITH_FINDINGS
prior_external_review_coverage_governance_commit: 093b4bc57061dddd2a6384f50b72da0143f4043d
tracked_source_worktree_clean_before_handoff_generation: True
zip_internal_dirty_worktree_present: False
external_metadata_dirty_after_zip_generation_before_commit: True
dirty_state_explanation: external_review_packet/HANDOFF_LATEST.sha256 and external metadata are regenerated after the ZIP is written; this is handoff metadata dirtiness, not source-patch dirtiness.

canonical_review_bundle: external_review_packet/HANDOFF_LATEST.zip
canonical_checksum: external_review_packet/HANDOFF_LATEST.sha256
canonical_readme: external_review_packet/00_READ_ME_FIRST.md

zip_file_count: 484
zip_size_bytes: 13075040
zip_sha256: b2b0eecaa1e05fdb809020fdf5a4046b75be0986e813dbb51b5b035121da176f
sha_match: True
zip_testzip: None
missing_required: []
nested_zip_count: 0
forbidden_match_count: 0
local_path_leak_count: 0
internal_head: e20113b374d78dea1bd575f65e587bb37b4f314e
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
Repo-Stand `e20113b374d78dea1bd575f65e587bb37b4f314e` nach
`feat: add cross-patch regression governance check`.

Review-Schwerpunkte:

- `src/external_review_cross_patch_regression.py`
- `tests/test_external_review_cross_patch_regression.py`
- `docs/governance/EXTERNAL_REVIEW_COVERAGE_STANDARD.md`
- `docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml`
- `docs/governance/EXTERNAL_REVIEW_GATE_SEQUENCE.md`
- `docs/architecture/CIOS_FEATURE_STATUS.yaml`
- `docs/architecture/CURRENT_KNOWN_GAPS.md`
- `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
- `docs/MODULE_CONTRACTS.md`
- `docs/CONTEXT_AND_ROADMAP.md`
- `README.md`
- `tests/test_readme_and_reports.py`
- `tests/test_handoff_zip_export.py`
- `tests/test_handoff_bundle.py`

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
- keine Clean-Room-Automation
- keine vollautomatische Cross-Patch-Regression

## Cross-Patch Regression Boundary

`src.external_review_cross_patch_regression` operationalisiert
`CROSS_PATCH_REGRESSION_REVIEW` als read-only Governance-Regression-Check. Der
Producer liest repo-lokale Governance-, Architecture-, Status-, Known-Gaps- und
Handoff-Artefakte, schreibt eine CSV und einen Markdown-Report und macht Drift
sichtbar.

Der Producer implementiert keine Runtime-Enforcement-Engine, keine
Clean-Room-Automation, keine Release-Akzeptanz und keine Product-, Investment-
oder Production-Readiness.

## Validation Actually Performed

Preflight:

- `git branch --show-current`
  - result: `main`
- `git rev-parse HEAD`
  - result before implementation: `3cfd678479c1391dcea24ef006a9b944b7468fc9`
- `git rev-parse --short HEAD`
  - result before implementation: `3cfd678`
- `git status --short`
  - result before implementation: clean
- `git status --short --ignored external_review_packet`
  - result included ignored `external_review_packet/HANDOFF_LATEST.zip`

Targeted validation before handoff:

- `python -m unittest tests.test_external_review_cross_patch_regression -v`
  - result: `Ran 11 tests`, `OK`
- `python -m src.external_review_cross_patch_regression --as-of-date 2026-05-21`
  - result: `status: WARN`, `findings: 36`, `FAIL: 0`, `WARN: 14`, `PASS: 22`
- `python -m unittest tests.test_readme_and_reports -v`
  - result: `Ran 14 tests`, `OK`
- `python -m unittest tests.test_handoff_zip_export -v`
  - result: `Ran 9 tests`, `OK`
- `python -m unittest tests.test_handoff_bundle -v`
  - result: `Ran 17 tests`, `OK`
- `git diff --check`
  - result: exit code `0`; Git reported line-ending warnings for touched files but no whitespace errors

Optional validation attempted:

- `python -m pytest -q`
  - result: failed because `pytest` is not installed in the active Python environment: `No module named pytest`
- `python -m ruff check .`
  - result: failed because `ruff` is not installed in the active Python environment: `No module named ruff`

No full test suite is claimed by this context file.

Handoff generation:

- `python -m src.handoff_zip_export --profile full_review --name HANDOFF_LATEST --output-path external_review_packet/HANDOFF_LATEST.zip --validation-command "python -m unittest tests.test_external_review_cross_patch_regression -v" --validation-command "python -m unittest tests.test_readme_and_reports -v" --validation-command "python -m unittest tests.test_handoff_zip_export -v" --validation-command "python -m unittest tests.test_handoff_bundle -v" --validation-command "python -m pytest -q" --validation-command "python -m ruff check ." --validation-command "git diff --check"`
  - result: generated ZIP for head `e20113b374d78dea1bd575f65e587bb37b4f314e`
  - file_count: `484`
  - size_bytes: `13075040`
  - zip_sha256: `b2b0eecaa1e05fdb809020fdf5a4046b75be0986e813dbb51b5b035121da176f`
  - forbidden_match_count: `0`
  - local_path_leak_count: `0`

Post-generation ZIP validation:

- SHA match: `True`
- `zipfile.testzip()`: `None`
- `missing_required`: `[]`
- `nested_zip_count`: `0`
- `forbidden_match_count`: `0`
- `local_path_leak_count`: `0`
- internal `HANDOFF_CONTEXT.md` head:
  `e20113b374d78dea1bd575f65e587bb37b4f314e`
- Cross-Patch Regression producer in ZIP: `yes`
- Cross-Patch Regression tests in ZIP: `yes`
- Updated status/governance/cross-reference files in ZIP: `yes`
