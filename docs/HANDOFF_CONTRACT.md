# Unified Handoff Contract

The canonical external-review export entry point is:

```text
python -m src.handoff_zip_export --profile <profile> --name <bundle_name>
```

By default, ZIPs are written to `outputs/handoffs/archive/`. The exporter also
updates:

- `outputs/handoffs/latest/HANDOFF_LATEST.zip`
- `outputs/handoffs/latest/HANDOFF_LATEST.sha256`
- `outputs/handoffs/latest/HANDOFF_LATEST_CONTEXT.md`

Root-level ZIP output is only allowed through an explicit `--output-path`.

Supported profiles:

- `patch`: patch-specific external LLM validation context.
- `preview`: website/private preview handoff with legacy preview artifact coverage.
- `data_closure`: processed fundamentals, SEC, evidence and readiness review context.
- `full_review`: broad repo context without private raw data or generated build outputs.
- `manifest_only`: metadata, hashes, omitted artifacts and change classification only.

Every profile writes the same standard metadata files:

- `HANDOFF_CONTEXT.md`
- `HANDOFF_REPORT.md`
- `HANDOFF_MANIFEST.csv`
- `HANDOFF_ARTIFACT_INDEX.csv`
- `HANDOFF_GUARDRAILS.md`
- `HANDOFF_OMITTED_ARTIFACTS.csv`
- `HANDOFF_CHANGE_CLASSIFICATION.csv`
- `HANDOFF_VALIDATION.txt`
- `HANDOFF_GIT_STATUS_SANITIZED.txt`
- `HANDOFF_EXTERNAL_REVIEW_CHECKLIST.md`

Forbidden entries are centrally enforced before profile allowlists:

- `.git/**`
- `.env` and `.env.*`
- `data/raw/private/**`
- user-agent files
- SEC identity/review private files
- `node_modules/**`, `dist/**`, `deploy_artifacts/**`
- caches, `*.pyc`, `*.zip`, `*.log`, `tests/_tmp_*`

Patch handoffs must include source, tests, processed artifacts and reports required
for external validation, while private approval templates and private raw inputs
remain omitted and documented in `HANDOFF_OMITTED_ARTIFACTS.csv`.

Validation commands can be recorded with repeatable `--validation-command`
arguments. `HANDOFF_VALIDATION.txt` records validation provenance: command text,
command status, ZIP integrity, SHA256 verification, file count, forbidden/private
count, nested ZIP count, internal/external context match status, archive/latest
hash match status, validation status and `manifest_sha256`. If no external
commands are supplied, the exporter records `self_validation_only` rather than a
blank or misleading command list.

## External LLM Context Requirements

Every external-review handoff must be self-contained enough for an external LLM
to review without private files, credentials, hidden local state, or prior chat
context. The bundle context must include project name, profile, bundle name,
branch, HEAD, dirty worktree presence, included artifact groups, omitted artifact
groups, validation summary location, and instructions not to infer omitted
private data.

The latest lifecycle is part of the contract:

- `outputs/handoffs/archive/<bundle>.zip` stores the immutable archive copy.
- `outputs/handoffs/latest/HANDOFF_LATEST.zip` points to the newest handoff.
- `outputs/handoffs/latest/HANDOFF_LATEST.sha256` must match the latest ZIP.
- `outputs/handoffs/latest/HANDOFF_LATEST_CONTEXT.md` must match the newest
  bundle context.

Latest publishing is atomic at the contract level. The exporter must build the
archive ZIP first, validate it, stage the latest ZIP/context/SHA files, validate
the staged latest set, and only then replace `outputs/handoffs/latest/`. The
previous latest set must remain untouched if validation fails.

Latest validation must confirm:

- the latest ZIP opens successfully
- the external `HANDOFF_LATEST_CONTEXT.md` matches the internal
  `HANDOFF_CONTEXT.md`
- the latest SHA256 file matches the actual latest ZIP
- the archive ZIP hash equals the latest ZIP hash
- `HANDOFF_VALIDATION.txt` `file_count` equals the actual ZIP entry count
- `forbidden_count` is `0`
- `nested_zip_count` is `0`

Validation must reject forbidden/private entries, nested ZIP files, raw private
data, identity maps, user-agent files, build outputs and cache/log files.
