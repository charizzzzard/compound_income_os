# External Review Packet Context

- project_name: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- patch_title: `CIOS_PRACTICAL_OPERATING_STANDARD`
- bundle_purpose: `external_review_after_cios_practical_operating_standard`
- profile: `full_review`
- bundle_name: `HANDOFF_LATEST`
- base_head: `e8ac5583502ad90a9240b857469debb87eacc6b2`
- implementation_head: `af1622a8e1fa3ac89b53a23cda05d50ebb334323`
- preflight_head: `e8ac5583502ad90a9240b857469debb87eacc6b2`
- central_handoff_zip_head: `af1622a8e1fa3ac89b53a23cda05d50ebb334323`
- current_handoff_head: `af1622a8e1fa3ac89b53a23cda05d50ebb334323`
- remote_main_head_at_export: `e8ac5583502ad90a9240b857469debb87eacc6b2`
- dirty_worktree_present_at_export: `False`
- reviewer_facing_upload_folder: `external_review_packet`

If this context file and checksum are committed after ZIP export, the repo HEAD
may become a metadata-only head newer than `central_handoff_zip_head`. That is an
allowed head-offset case only when explicitly reported by the operator report.

## Source-of-Truth / Precedence

Bei Konflikten gilt diese Reihenfolge:

1. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
2. ZIP-internal `HANDOFF_CONTEXT.md`
3. ZIP-internal artifact indexes, omitted-artifact registers and patch identity
4. GitHub browser URL for committed repo inspection
5. Local-only/generated/ignored files only if explicitly included or summarized

## Patch Identity

- patch_title: `CIOS_PRACTICAL_OPERATING_STANDARD`
- bundle_purpose: `external_review_after_cios_practical_operating_standard`
- base_head: `e8ac5583502ad90a9240b857469debb87eacc6b2`
- implementation_head: `af1622a8e1fa3ac89b53a23cda05d50ebb334323`
- central_handoff_zip_head: `af1622a8e1fa3ac89b53a23cda05d50ebb334323`
- delta_range: `e8ac5583502ad90a9240b857469debb87eacc6b2..af1622a8e1fa3ac89b53a23cda05d50ebb334323`
- changed_file_count: `2`

Changed files:

- `docs/governance/CIOS_PRACTICAL_OPERATING_STANDARD.md`
- `tests/test_practical_operating_standard.py`

## Review Findings Ingested

The externally reviewed draft was accepted with findings and no blocker or
major finding. This materialized standard incorporates the accepted minor
hardenings:

- `MINOR-001`: explicit `push_status` and `remote_main_contains_head` fields.
- `MINOR-002`: canonical external review severities `BLOCKER`, `MAJOR`,
  `MINOR`, `INFO`.
- `MINOR-003`: missing, stale or unknown data must remain visible and must not
  be silently imputed, overwritten, suppressed or converted into accepted facts.

## Handoff Integrity Summary

- zip_path: `external_review_packet/HANDOFF_LATEST.zip`
- sha_path: `external_review_packet/HANDOFF_LATEST.sha256`
- zip_file_count: `522`
- zip_sha256: `cb878971be66cc008c9a793bc54b26ca82dd6ba6d76532836a4bf89878a85c0f`
- sha_match: `True`
- zip_testzip: `None`
- nested_zip_count: `0`
- forbidden_match_count: `0`
- local_path_leak_count: `0`
- no_parallel_handoff_claimed: `True`

## Validation Reality

Actually executed in the current local repo before handoff regeneration:

- `git diff --check`: PASS
- `python -m ruff check docs tests src`: PASS, `All checks passed!`
- `python -m pytest tests/test_practical_operating_standard.py -q`: PASS,
  `6 passed, 57 subtests passed`
- `python -m pytest tests/test_readme_and_reports.py -q`: PASS,
  `14 passed, 130 subtests passed`

ZIP-internal `HANDOFF_VALIDATION.txt` records validation commands as
`RECORDED_VALIDATION`. It is command provenance, not proof of external execution
unless a separate reviewer/operator report says so.

## External LLM Review Instructions

- Review the new practical operating standard and its tests only for this patch
  delta.
- Do not infer omitted private/raw/provider/broker files.
- Do not treat documentation-only standards as runtime enforcement.
- Do not treat external LLM review as final acceptance.
- Map all findings to `BLOCKER`, `MAJOR`, `MINOR` or `INFO`.
- Distinguish documented, tested, enforced, operationally_ready and
  production_ready.
- Cite repo-relative paths in findings.

## Explicit Non-Scope

This packet does not claim or introduce:

- CIOS feature logic
- investment logic changes
- scoring changes
- ranking changes
- valuation changes
- portfolio-rule changes
- dashboard/data-freshness/report semantic changes
- broker import changes
- provider/API integration
- order execution
- buy/sell automation
- private/generated/raw publication
- runtime enforcement
- product, production or investment readiness

Human Operator remains final acceptance authority.
