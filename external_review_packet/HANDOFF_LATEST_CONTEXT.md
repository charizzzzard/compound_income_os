# Handoff Context

## Reviewer-Facing Metadata Layer

- patch_title: `SANITIZED_MONTHLY_BRIEF_EXAMPLE_OUTPUT`
- reviewer_facing_bundle_purpose: `external_review_after_sanitized_monthly_brief_example_output`
- implementation_head: `88d931233964824abe0400a1cfc87884199f4b64`
- central_handoff_zip_head: `88d931233964824abe0400a1cfc87884199f4b64`
- current_handoff_head: `88d931233964824abe0400a1cfc87884199f4b64`
- current_repo_head_before_handoff_metadata_commit: `88d931233964824abe0400a1cfc87884199f4b64`
- remote_main_head_before_handoff_metadata_commit: `9aceb38e12a8500237efc9ddd090919b8f8adddc`
- handoff_metadata_commit_head: `reported in the final operator report after commit creation`
- reviewer_facing_upload_folder: `external_review_packet`
- no_parallel_handoff_claimed: `True`

The ZIP represents the implementation snapshot at
`88d931233964824abe0400a1cfc87884199f4b64`. If this context file and checksum
are committed after ZIP export, the resulting repository HEAD is a metadata-only
publication offset and does not change source, tests, examples, configs, runtime
behavior or the ZIP implementation snapshot.

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
- bundle_name: `sanitized_monthly_brief_example_output`
- bundle_purpose: `external_llm_validation`
- created_at_utc: `2026-05-31T16:31:35+00:00`
- branch: `main`
- head: `88d931233964824abe0400a1cfc87884199f4b64`
- base_head: `9aceb38e12a8500237efc9ddd090919b8f8adddc`
- delta_range: `9aceb38e12a8500237efc9ddd090919b8f8adddc..88d931233964824abe0400a1cfc87884199f4b64`
- delta_evidence_rows: `9`
- patch_identity_entry: `HANDOFF_PATCH_IDENTITY.md`
- dirty_worktree_present: `False`
- purpose: patch handoff for external LLM validation

## Included Artifact Groups
- `docs`
- `repo_context`
- `tests`

## Omitted Artifact Groups
- `OMITTED_FORBIDDEN`
- `OMITTED_PRIVATE`

## Validation Summary
Executed in current repo after implementation: example tests, Monthly Brief tests, Personal Run tests, ruff, git diff check and reviewer-surface rg checks passed. Full pytest skipped because this patch only adds static examples, contract pointer and focused tests.

## External LLM Instructions
- Use only included artifacts and explicitly documented omissions.
- Do not infer private raw data, credentials, user-agent values, or omitted local files.
- Treat generated CSV and report artifacts as the review evidence surface.
- Check HANDOFF_CHANGE_CLASSIFICATION.csv before assuming dirty worktree state.
- Check HANDOFF_PATCH_IDENTITY.md before treating a snapshot as patch-delta evidence.
- HANDOFF_VALIDATION.txt records commands as RECORDED unless separate execution evidence says otherwise.
