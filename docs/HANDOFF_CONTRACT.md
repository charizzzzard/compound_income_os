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
- `outputs/handoffs/upload_ready/<upload_bundle_id>/<upload_bundle_id>.zip`
- `outputs/handoffs/upload_ready/<upload_bundle_id>/<upload_bundle_id>_CONTEXT.md`
- `outputs/handoffs/upload_ready/<upload_bundle_id>/<upload_bundle_id>.sha256`

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
- `HANDOFF_PATCH_IDENTITY.md`
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
hash match status, validation status, `manifest_sha256`, manifest row count and
the terminal metadata file-count delta. If no external commands are supplied, the
exporter records `self_validation_only` rather than a blank or misleading command
list.

Validation command records are provenance, not execution proof. Unless a
separate external context states `EXECUTED_IN_CURRENT_REPO` or
`EXECUTED_IN_ZIP_CONTEXT`, commands listed by the exporter are
`RECORDED_VALIDATION`.

`HANDOFF_PATCH_IDENTITY.md` separates snapshot evidence from patch-delta
evidence. It records patch title, bundle purpose, base HEAD, implementation
HEAD, current handoff HEAD, delta range, changed file count and delta evidence
status. `HANDOFF_CHANGE_CLASSIFICATION.csv` must be populated from
`git diff --name-status <base>..<head>` when Git context is available. If the
base cannot be resolved, the handoff must explicitly report unknown delta
evidence rather than silently presenting a full snapshot as complete patch
provenance.

`HANDOFF_CONTEXT.md` preserves `created_at_utc` as the canonical run timestamp.
Archive and upload-ready filenames use the same UTC timestamp normalized as
`YYYYMMDD-HHMMSS`; no local-time timestamp is used for default lifecycle output.
If `profile` and `bundle_name` are identical, filenames and upload bundle IDs use
one copy of the name segment, for example `HANDOFF_preview_<timestamp>...`
rather than `HANDOFF_preview_preview_<timestamp>...`. Distinct patch bundle
names still include both profile and bundle name.

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
- `outputs/handoffs/upload_ready/<upload_bundle_id>/` stores the uniquely named
  upload artifact trio for external LLM conversations.

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
- the manifest/file-count relationship is documented. `HANDOFF_MANIFEST.csv` is
  generated before terminal metadata files `HANDOFF_MANIFEST.csv` and
  `HANDOFF_VALIDATION.txt` are written, so ZIP `file_count` is expected to exceed
  manifest row count by exactly those terminal metadata files.

Validation must reject forbidden/private entries, nested ZIP files, raw private
data, identity maps, user-agent files, build outputs and cache/log files.

## Upload-Ready Artifacts

`latest` is for local automation. `archive` is the immutable historical record.
`upload_ready` is the recommended folder for external LLM uploads.

Do not upload generic `HANDOFF_LATEST.zip` when multiple handoffs exist. Upload
all three uniquely named files from the newest `upload_ready/<upload_bundle_id>/`
directory:

- `<upload_bundle_id>.zip`
- `<upload_bundle_id>_CONTEXT.md`
- `<upload_bundle_id>.sha256`

The `upload_bundle_id` includes project name, `HANDOFF`, profile, distinct bundle
name when applicable, normalized UTC run timestamp, short HEAD and the first
eight characters of the ZIP SHA256. The upload-ready ZIP must be byte-identical to
`outputs/handoffs/latest/HANDOFF_LATEST.zip`, the upload-ready context must match
the internal `HANDOFF_CONTEXT.md`, and the upload-ready SHA256 file must refer to
the unique ZIP filename rather than `HANDOFF_LATEST.zip`.
