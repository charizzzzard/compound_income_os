# Handoff Context

- project_name: `compound_income_os`
- profile: `patch`
- bundle_name: `final_audit_governance_carried_forward_closure`
- bundle_purpose: `external_llm_validation`
- created_at_utc: `2026-05-31T23:43:03+00:00`
- branch: `main`
- head: `4afad452327e35d4146d108e819fdfd7393a697d`
- base_head: `8aa2a65595e95aa3fdfa68a3315379b6128e8fde`
- delta_range: `8aa2a65595e95aa3fdfa68a3315379b6128e8fde..4afad452327e35d4146d108e819fdfd7393a697d`
- delta_evidence_rows: `7`
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
Final audit governance carried-forward closure: command provenance semantic validation, JSON schema, documented status taxonomy, validation provenance language and ZIP transport policy hardened. No portfolio, scoring, ranking, valuation, broker/provider/API, order or trading logic changed.

## External LLM Instructions
- Use only included artifacts and explicitly documented omissions.
- Do not infer private raw data, credentials, user-agent values, or omitted local files.
- Treat generated CSV and report artifacts as the review evidence surface.
- Check HANDOFF_CHANGE_CLASSIFICATION.csv before assuming dirty worktree state.
- Check HANDOFF_PATCH_IDENTITY.md before treating a snapshot as patch-delta evidence.
- HANDOFF_VALIDATION.txt records commands as RECORDED unless separate execution evidence says otherwise.
