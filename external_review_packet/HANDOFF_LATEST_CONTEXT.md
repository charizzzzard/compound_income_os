# Handoff Context

- project_name: `compound_income_os`
- profile: `patch`
- bundle_name: `operational_backbone_stage_0_identity_and_staging_preflight`
- bundle_purpose: `external_llm_validation`
- created_at_utc: `2026-06-01T07:41:21+00:00`
- branch: `main`
- head: `926dbc75337030602629d4e369855e2fe72ebd54`
- base_head: `a7683b4c36bc3973d9019420d0e47a280abccec5`
- delta_range: `a7683b4c36bc3973d9019420d0e47a280abccec5..926dbc75337030602629d4e369855e2fe72ebd54`
- delta_evidence_rows: `18`
- patch_identity_entry: `HANDOFF_PATCH_IDENTITY.md`
- dirty_worktree_present: `False`
- purpose: patch handoff for external LLM validation

## Included Artifact Groups
- `docs`
- `repo_context`
- `source`
- `tests`

## Omitted Artifact Groups
- `OMITTED_FORBIDDEN`
- `OMITTED_PRIVATE`

## Validation Summary
See HANDOFF_VALIDATION.txt.

## External LLM Instructions
- Use only included artifacts and explicitly documented omissions.
- Do not infer private raw data, credentials, user-agent values, or omitted local files.
- Treat generated CSV and report artifacts as the review evidence surface.
- Check HANDOFF_CHANGE_CLASSIFICATION.csv before assuming dirty worktree state.
- Check HANDOFF_PATCH_IDENTITY.md before treating a snapshot as patch-delta evidence.
- HANDOFF_VALIDATION.txt records commands as RECORDED unless separate execution evidence says otherwise.
