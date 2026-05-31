# Handoff Context

- project_name: `compound_income_os`
- profile: `patch`
- bundle_name: `audit_command_provenance_hardening`
- bundle_purpose: `external_llm_validation`
- created_at_utc: `2026-05-31T22:56:26+00:00`
- branch: `main`
- head: `163585ed9c5b53a5520babbc8de738e75c89091b`
- base_head: `560e9c1166f7c5319b2c5dcb8055fe1dfd99fe57`
- delta_range: `560e9c1166f7c5319b2c5dcb8055fe1dfd99fe57..163585ed9c5b53a5520babbc8de738e75c89091b`
- delta_evidence_rows: `4`
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
Audit command provenance contract, synthetic manifest, validator and tests added for future full portfolio capability audits. Historical audit commands were not reconstructed.

## External LLM Instructions
- Use only included artifacts and explicitly documented omissions.
- Do not infer private raw data, credentials, user-agent values, or omitted local files.
- Treat generated CSV and report artifacts as the review evidence surface.
- Check HANDOFF_CHANGE_CLASSIFICATION.csv before assuming dirty worktree state.
- Check HANDOFF_PATCH_IDENTITY.md before treating a snapshot as patch-delta evidence.
- HANDOFF_VALIDATION.txt records commands as RECORDED unless separate execution evidence says otherwise.
