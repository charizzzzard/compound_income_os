# Compound Income OS External LLM Review Packet

## Source of Truth / Precedence

Start with this file.

Use `HANDOFF_LATEST_CONTEXT.md` as authoritative packet metadata.
Use `HANDOFF_LATEST.zip` as authoritative repo evidence.
Use `COMPOUND_INCOME_OS_VISION_v1_2.md` as the sole canonical vision.
Use `PATCH_1_2_FINAL_REPORT.md` as the validation summary.

If any ZIP-internal `HANDOFF_CONTEXT.md` conflicts with external `HANDOFF_LATEST_CONTEXT.md`, the external `HANDOFF_LATEST_CONTEXT.md` wins.

Patch 1.2 is functionally complete at implementation head `a09d5b3`.
This handoff is an artifact-only backfill because the original Phase 1.2 implementation prompt did not require a fresh external review packet.

Canonical review inputs:

1. `COMPOUND_INCOME_OS_VISION_v1_2.md`
   - Canonical target vision for Patch 1.2 review.
   - Ignore older `COMPOUND_INCOME_OS_VISION_v1.md` or `COMPOUND_INCOME_OS_VISION_v1_1.md` if seen elsewhere.

2. `HANDOFF_LATEST.zip`
   - Canonical post-Patch-1.2 repo evidence bundle.

3. `HANDOFF_LATEST_CONTEXT.md`
   - Bundle metadata: branch, implementation head, current handoff head, purpose, omissions, included artifact groups.

4. `HANDOFF_LATEST.sha256`
   - SHA256 checksum for the canonical ZIP.

5. `PATCH_1_2_FINAL_REPORT.md`
   - Validation, guardrail and output-contract summary for Patch 1.2.

Rules for reviewers:
- Treat the ZIP as post-Patch-1.2 repo reality.
- Treat Vision v1.2 as canonical.
- Use full relative paths when referring to files.
- Do not infer omitted private/raw files.
- Do not treat `execution_mode` as a Decision Capture schema field.
- Do not infer broker writes, HTTP calls, order execution, auto-trading, or Phase-1.3+ logic.
- Missing routing inputs remain deliberately visible as `NO_RECOMMENDATION` or failed gates; do not treat them as imputed defaults.
- If ZIP-internal generic exporter metadata conflicts with this external context, this external `HANDOFF_LATEST_CONTEXT.md` wins for packet metadata.
