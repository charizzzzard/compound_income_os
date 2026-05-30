# External Review Packet Context

- project_name: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- patch_title: `MONTHLY_PORTFOLIO_DECISION_BRIEF_PATH_REDACTION_P0`
- bundle_purpose: `external_review_after_monthly_portfolio_decision_brief_path_redaction_p0`
- profile: `full_review`
- bundle_name: `HANDOFF_LATEST`
- base_head: `26dfcec438615cbc56d4e01979081a4e145c7402`
- implementation_head: `10fc5f7ace8708502ba68c5f1068bae76a0e67f7`
- preflight_head: `26dfcec438615cbc56d4e01979081a4e145c7402`
- central_handoff_zip_head: `10fc5f7ace8708502ba68c5f1068bae76a0e67f7`
- current_handoff_head: `10fc5f7ace8708502ba68c5f1068bae76a0e67f7`
- remote_main_head_at_export: `26dfcec438615cbc56d4e01979081a4e145c7402`
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

- patch_title: `MONTHLY_PORTFOLIO_DECISION_BRIEF_PATH_REDACTION_P0`
- bundle_purpose: `external_review_after_monthly_portfolio_decision_brief_path_redaction_p0`
- base_head: `26dfcec438615cbc56d4e01979081a4e145c7402`
- implementation_head: `10fc5f7ace8708502ba68c5f1068bae76a0e67f7`
- central_handoff_zip_head: `10fc5f7ace8708502ba68c5f1068bae76a0e67f7`
- delta_range: `26dfcec438615cbc56d4e01979081a4e145c7402..10fc5f7ace8708502ba68c5f1068bae76a0e67f7`
- changed_file_count: `2`

Changed files:

- `src/monthly_portfolio_decision_brief.py`
- `tests/test_monthly_portfolio_decision_brief.py`

## P0 Fix Purpose

This packet reviews the P0 path-redaction hardening for the Monthly Portfolio
Decision Brief MVP.

The fix ensures that foreign-platform absolute path syntax is redacted
deterministically before any read attempt:

- Windows-style absolute paths such as
  `C:\Users\Operator\private_decision_quality.json` are redacted in POSIX/ZIP
  review contexts.
- UNC-style paths such as `\\server\share\private.json` are redacted when they
  cannot be proven repo-internal on the current platform.
- Current-platform absolute paths inside the repository may still be rendered as
  repo-relative paths.
- Current-platform absolute paths outside the repository remain redacted.
- Private/raw/provider/broker/credential/user-agent tokens remain redacted
  before any read attempt.

No status semantics, scoring, ranking, valuation, portfolio rules, dashboard
semantics, Data Freshness producer semantics or Decision Quality semantics are
changed.

## Handoff Integrity Summary

- zip_path: `external_review_packet/HANDOFF_LATEST.zip`
- sha_path: `external_review_packet/HANDOFF_LATEST.sha256`
- zip_file_count: `529`
- zip_sha256: `e196164231c0f0b31304d9f4b8cfa44a4ccba35216b747963e5cefb9afa1d746`
- sha_match: `True`
- zip_testzip: `None`
- nested_zip_count: `0`
- forbidden_match_count: `0`
- local_path_leak_count: `0`
- no_parallel_handoff_claimed: `True`

## Validation Reality

Actually executed in the current local repo before handoff regeneration:

- `git status --short --branch`: PASS, expected tracked patch files only during implementation
- `git diff --check`: PASS, LF/CRLF warning only for changed files
- `python -m pytest tests/test_monthly_portfolio_decision_brief.py -q`: PASS, `12 passed in 1.76s`
- `python -m pytest tests/test_data_visibility_artifact_boundary_audit.py -q`: PASS, `13 passed in 4.78s`
- `python -m pytest tests/test_personal_run_engine.py -q`: PASS, `60 passed, 2 subtests passed in 14.88s`
- `python -m pytest tests/test_monthly_decision_report.py -q`: PASS, `19 passed in 1.33s`
- `python -m ruff check docs tests src`: PASS, `All checks passed!`
- `python -m pytest -q`: PASS, `989 passed, 410 subtests passed in 177.04s`

ZIP-internal `HANDOFF_VALIDATION.txt` records validation commands as
`RECORDED_VALIDATION`. It is command provenance, not proof of external execution
unless a separate reviewer/operator report says so.

## External LLM Review Instructions

- Review the redaction logic and regression tests only.
- Use repo-relative paths in findings.
- Do not infer omitted private/raw/provider/broker files.
- Do not treat ignored generated outputs as committed repo truth.
- Do not treat this P0 hardening as investment advice, order automation,
  valuation automation, broker/provider integration, runtime enforcement or
  product readiness.
- Distinguish evidence from inference and use canonical severities:
  `BLOCKER`, `MAJOR`, `MINOR`, `INFO`.

## Explicit Non-Scope

This packet does not claim or introduce:

- broker import
- broker/provider/API integration
- order execution
- buy/sell automation
- investment advice automation
- scoring formula changes
- ranking formula changes
- valuation methodology changes
- portfolio-rule changes
- personal_run_engine stage-order changes
- dashboard/data-freshness/decision-quality semantic changes
- replay/backtesting/simulation/outcome attribution
- tax/legal/commercial approval
- private/generated/raw publication
- runtime enforcement
- product, production or investment readiness

Human Operator remains final acceptance authority.
