# Handoff Context

## Reviewer-Facing Metadata Layer

- patch_title: `MONTHLY_PORTFOLIO_DECISION_BRIEF_PERSONAL_RUN_INTEGRATION_IMPLEMENTATION`
- reviewer_facing_bundle_purpose: `external_review_after_monthly_portfolio_decision_brief_personal_run_integration_implementation`
- implementation_head: `9cb03c172c40307b576f165a51c6ae352db34e27`
- central_handoff_zip_head: `9cb03c172c40307b576f165a51c6ae352db34e27`
- current_handoff_head: `9cb03c172c40307b576f165a51c6ae352db34e27`
- current_repo_head_before_handoff_metadata_commit: `9cb03c172c40307b576f165a51c6ae352db34e27`
- remote_main_head_before_handoff_metadata_commit: `627b186022c7fd456a07378af8333a503b1d40e3`
- handoff_metadata_commit_head: `reported in the final operator report after commit creation`
- reviewer_facing_upload_folder: `external_review_packet`
- no_parallel_handoff_claimed: `True`

The ZIP represents the implementation snapshot at
`9cb03c172c40307b576f165a51c6ae352db34e27`. If this context file and checksum
are committed after ZIP export, the resulting repository HEAD is a metadata-only
publication offset and does not change source, tests, configs, runtime behavior
or the ZIP implementation snapshot.

The generated ZIP-internal context may use the generic exporter purpose
`external_llm_validation`; this reviewer-facing context records the specific
patch purpose for the central `external_review_packet/` upload folder.

## Source-of-Truth / Precedence

Bei Konflikten gilt diese Reihenfolge:

1. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
2. ZIP-internal `HANDOFF_CONTEXT.md`
3. ZIP-internal artifact indexes, omitted-artifact registers and patch identity
4. GitHub browser URL for committed repo inspection
5. Local-only/generated/ignored files only if explicitly included or summarized

`outputs/` may contain ignored local evidence, but it is not an authoritative
handoff and must not be treated as a parallel review packet.

- project_name: `compound_income_os`
- profile: `patch`
- bundle_name: `monthly_portfolio_decision_brief_personal_run_integration_implementation`
- bundle_purpose: `external_llm_validation`
- created_at_utc: `2026-05-31T16:01:18+00:00`
- branch: `main`
- head: `9cb03c172c40307b576f165a51c6ae352db34e27`
- base_head: `627b186022c7fd456a07378af8333a503b1d40e3`
- delta_range: `627b186022c7fd456a07378af8333a503b1d40e3..9cb03c172c40307b576f165a51c6ae352db34e27`
- delta_evidence_rows: `8`
- patch_identity_entry: `HANDOFF_PATCH_IDENTITY.md`
- dirty_worktree_present: `False`
- purpose: patch handoff for external LLM validation

## Included Artifact Groups
- `docs`
- `source`
- `tests`

## Omitted Artifact Groups
- `OMITTED_FORBIDDEN`
- `OMITTED_PRIVATE`

## Validation Summary
Executed in current repo after implementation: focused Personal Run tests, Monthly Brief tests, readme/report tests, full pytest, ruff and git diff check passed.

## External LLM Instructions
- Use only included artifacts and explicitly documented omissions.
- Do not infer private raw data, credentials, user-agent values, or omitted local files.
- Treat generated CSV and report artifacts as the review evidence surface.
- Check HANDOFF_CHANGE_CLASSIFICATION.csv before assuming dirty worktree state.
- Check HANDOFF_PATCH_IDENTITY.md before treating a snapshot as patch-delta evidence.
- HANDOFF_VALIDATION.txt records commands as RECORDED unless separate execution evidence says otherwise.
