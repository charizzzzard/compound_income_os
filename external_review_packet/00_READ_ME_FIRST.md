# Compound Income OS External LLM Review Packet

## Source of Truth / Precedence

Start with this file.

Use `HANDOFF_LATEST_CONTEXT.md` as authoritative packet metadata.
Use `HANDOFF_LATEST.zip` as authoritative repo evidence.
Use `COMPOUND_INCOME_OS_VISION_v1_2.md` as the sole canonical vision.
Use `PATCH_02_FINAL_REPORT.md` as the validation summary.

If any ZIP-internal `HANDOFF_CONTEXT.md` conflicts with external `HANDOFF_LATEST_CONTEXT.md`, the external `HANDOFF_LATEST_CONTEXT.md` wins.

The 11 Personal-Meta candidates resolved after handoff review are `keep_active_for_now`; no additional Personal-Meta archival or removal is part of this patch.

Canonical review inputs:

1. `COMPOUND_INCOME_OS_VISION_v1_2.md`
   - Canonical target vision for Patch 2 review.
   - Ignore older `COMPOUND_INCOME_OS_VISION_v1.md` or `COMPOUND_INCOME_OS_VISION_v1_1.md` if seen elsewhere.

2. `HANDOFF_LATEST.zip`
   - Canonical post-Patch-2 repo evidence bundle.

3. `HANDOFF_LATEST_CONTEXT.md`
   - Bundle metadata: branch, head, purpose, omissions, included artifact groups.

4. `HANDOFF_LATEST.sha256`
   - SHA256 checksum for the canonical ZIP.

5. `PATCH_02_FINAL_REPORT.md`
   - Validation and structural summary after Patch 2.

Rules for reviewers:
- Treat the ZIP as post-Patch-2 repo reality.
- Treat Vision v1.2 as canonical.
- Use full relative paths when referring to files.
- Do not infer omitted private/raw files.
- Do not treat archived SEC modules as active core pipeline.
- Do not treat website code as part of the core `src/` lifecycle.
- Do not treat the archived personal-meta module as active core pipeline.
