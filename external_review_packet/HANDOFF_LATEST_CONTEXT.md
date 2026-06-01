# Handoff Context

- project_name: `compound_income_os`
- profile: `patch`
- bundle_name: `stage_0_validator_and_zip_repro_hardening`
- bundle_purpose: `external_llm_validation`
- created_at_utc: `2026-06-01T09:05:06+00:00`
- branch: `main`
- head: `46097b7f1040a9b3f022f3d9708217e6250b4c7f`
- base_head: `a12f2dba92d545c067e605bf5b34b4d0b12c670b`
- delta_range: `a12f2dba92d545c067e605bf5b34b4d0b12c670b..46097b7f1040a9b3f022f3d9708217e6250b4c7f`
- delta_evidence_rows: `7`
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
Stage-0 validator and ZIP reproducibility hardening validation recorded by Codex; full pytest passed locally.

## External LLM Instructions
- Use only included artifacts and explicitly documented omissions.
- Do not infer private raw data, credentials, user-agent values, or omitted local files.
- Treat generated CSV and report artifacts as the review evidence surface.
- Check HANDOFF_CHANGE_CLASSIFICATION.csv before assuming dirty worktree state.
- Check HANDOFF_PATCH_IDENTITY.md before treating a snapshot as patch-delta evidence.
- HANDOFF_VALIDATION.txt records commands as RECORDED unless separate execution evidence says otherwise.
