# Handoff Context

- project_name: `compound_income_os`
- profile: `post_patch_2_external_review`
- bundle_name: `HANDOFF_LATEST`
- bundle_purpose: `external_llm_validation_after_patch_2`
- created_at_utc: `2026-05-13T07:04:51Z`
- branch: `main`
- head: `aeba5ae1d11bd7d269ea20570589fd2e49633b2a`
- short_head: `aeba5ae`
- dirty_worktree_present: `False` before handoff artifact generation
- patch_level: `Patch 2 finalized`
- canonical_vision: `COMPOUND_INCOME_OS_VISION_v1_2.md`
- personal_meta_operator_decision: `11 ambiguous candidates kept active for now`
- additional_personal_meta_archival: `none`
- purpose: final post-Patch-2 handoff for external LLM validation

## Included Artifact Groups
- configs
- docs
- processed_artifacts / `data/processed`
- reports
- repo_context
- source
- tests
- website_source
- archive_metadata / `_archive/sec`
- archive_metadata / `_archive/personal_meta`

## Omitted Artifact Groups
- OMITTED_FORBIDDEN
- OMITTED_PRIVATE
- raw private data
- generated caches

## External LLM Instructions
- Use `COMPOUND_INCOME_OS_VISION_v1_2.md` as the sole canonical vision document.
- Use `HANDOFF_LATEST.zip` as the sole canonical repo evidence bundle.
- Treat this ZIP as post-Patch-2 repo reality.
- Do not use older `COMPOUND_INCOME_OS_VISION_v1.md` or `COMPOUND_INCOME_OS_VISION_v1_1.md` documents if present elsewhere.
- Do not infer private raw data, credentials, user-agent values, or omitted local files.
- Reference files by full relative path, not basename.
- Check `HANDOFF_CHANGE_CLASSIFICATION.csv` before assuming dirty worktree state.
- Archived SEC modules are not active core pipeline modules.
- Website code is not part of the active core `src/` lifecycle.
- The archived personal-meta module is not active core pipeline code.
- If ZIP-internal `HANDOFF_CONTEXT.md` conflicts with this external context, this external `HANDOFF_LATEST_CONTEXT.md` wins for packet metadata.
- The 11 ambiguous Personal-Meta candidates from `docs/architecture/PATCH_02_PERSONAL_META_REMOVAL_SCOPE.md` are kept active for now.
