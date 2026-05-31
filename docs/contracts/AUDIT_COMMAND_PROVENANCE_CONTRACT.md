# Audit Command Provenance Contract

## Purpose

This contract defines the forward-looking command provenance manifest for future
Full Portfolio Capability Execution Audits. It closes the audit finding that
generated artifacts were not always reconstructible from recorded commands.

The contract does not reconstruct prior audit commands. It defines how future
audits must record command evidence at the time of execution or inspection.

## Scope

The command provenance manifest is operational audit evidence only. It is not:

- production readiness
- investment readiness
- investment advice automation
- broker, provider or API integration
- order execution
- buy/sell automation
- proof that historical artifacts have been reproduced after the fact

## Manifest Format

The canonical machine-readable format is JSON.

The structural schema is:

- `docs/schemas/audit_run_manifest.schema.json`

Required top-level fields:

- `schema_version`
- `run_id`
- `repo_head`
- `created_at_utc`
- `entries`

`entries` must be a non-empty list of command provenance entries.

## Required Entry Fields

Each entry must contain:

- `run_id`
- `repo_head`
- `capability_id`
- `capability_status_from_feature_registry`
- `execution_classification`
- `command`
- `command_kind`
- `working_directory`
- `input_paths`
- `output_paths`
- `exit_code`
- `recorded_at_utc`
- `result_status`
- `conservative_state`
- `provenance_status`
- `notes`

`working_directory`, `input_paths` and `output_paths` must be repo-relative
paths or `"."`.

All `entry.run_id` values must match the top-level `run_id`. All
`entry.repo_head` values must match the top-level `repo_head`.

`repo_head` must be a 40-character hexadecimal Git SHA. Synthetic examples may
use the explicit 40-zero placeholder:
`0000000000000000000000000000000000000000`.

`created_at_utc` and `recorded_at_utc` must be RFC3339 UTC-like strings ending
in `Z` or `+00:00`.

## Command Kinds

Allowed `command_kind` values:

- `python_module`
- `pytest`
- `ruff`
- `inspection_only`
- `skipped`
- `not_executable`

## Result Status Values

Allowed `result_status` values:

- `PASS`
- `FAIL`
- `SKIPPED`
- `REVIEW`
- `NOT_EXECUTABLE_FROM_REPO_STATE`

## Provenance Status Values

Allowed `provenance_status` values:

- `COMMAND_RECORDED`
- `COMMAND_REPRODUCED`
- `OUTPUT_OBSERVED_COMMAND_NOT_RECORDED`
- `SKIPPED_NO_ENTRYPOINT`
- `SKIPPED_PRIVATE_INPUT_REQUIRED`
- `SKIPPED_DEFERRED`

Degraded provenance values:

- `OUTPUT_OBSERVED_COMMAND_NOT_RECORDED`
- `SKIPPED_NO_ENTRYPOINT`
- `SKIPPED_PRIVATE_INPUT_REQUIRED`
- `SKIPPED_DEFERRED`

Degraded provenance is allowed, but it must remain visible in review evidence.
It must not be relabeled as reproduced execution.

## COMMAND_REPRODUCED Rule

`COMMAND_REPRODUCED` may only be used when the command was actually executed in
the current audit run and the entry records at least:

- non-empty `command`
- integer `exit_code`
- non-empty `recorded_at_utc`
- non-skipped `result_status`
- `command_kind` other than `skipped` or `not_executable`

Historical commands must not be inferred after the fact.

## Degraded Provenance Rules

`OUTPUT_OBSERVED_COMMAND_NOT_RECORDED` must record:

- `command`: `""`
- `exit_code`: `null`
- a non-`PASS` `result_status`

It remains degraded evidence and must not be counted as reproduced execution.

`SKIPPED_NO_ENTRYPOINT`, `SKIPPED_PRIVATE_INPUT_REQUIRED` and
`SKIPPED_DEFERRED` must record:

- `command`: `""`
- `exit_code`: `null`
- `result_status`: `SKIPPED` or `NOT_EXECUTABLE_FROM_REPO_STATE`
- `command_kind`: `skipped` or `not_executable`

`COMMAND_RECORDED` records command provenance text, but it is not independent
execution proof unless a separate validation source says so.

## Path And Secret Policy

Reviewer-facing provenance must not contain:

- absolute local paths
- UNC paths
- home-directory paths
- secrets
- credentials
- API keys
- broker account identifiers
- private/raw/generated portfolio data values

The manifest may reference generated artifact paths only as repo-relative paths.
It must not publish private data values from those artifacts.

Windows drive-relative paths such as `C:foo`, `C:Users/operator/file.csv` and
`D:folder/file` are invalid because they are local-environment dependent even
though they are not absolute paths.

## READY_FOR_REVIEW Semantics

`READY_FOR_REVIEW` or equivalent conservative states are operator review labels.
They must not be interpreted as fully reproduced operational readiness when
`provenance_status` is degraded or command evidence is incomplete.

Future audits must distinguish:

- `COMMAND_REPRODUCED_READY_FOR_REVIEW`: a command was executed in the current
  run and the output is operator-reviewable.
- `OUTPUT_OBSERVED_READY_FOR_REVIEW`: an output was observed and is
  operator-reviewable, but exact command provenance is degraded.

The manifest may encode this distinction through `provenance_status` and
`conservative_state`; review summaries must not collapse both labels into
operational readiness.

## Validation Provenance Labels

Future handoff and audit validation evidence must distinguish:

- `RECORDED_BY_CODEX`: command text or validation result was recorded by Codex
  as provenance but not independently rerun in the current reviewing context.
- `EXECUTED_IN_CURRENT_RUN`: command was executed in the current local run.
- `INDEPENDENTLY_REVIEWED`: an external reviewer or operator independently
  checked the evidence and recorded that review.
- `NOT_AVAILABLE`: command, dependency, artifact or execution evidence was not
  available.

Do not claim independent execution unless it actually occurred and is recorded.

## Dedicated Validation Command

The recurring audit provenance validation command is:

```text
python -m src.audit_command_provenance --manifest examples/audit_command_provenance/audit_run_manifest.example.json
```

Future audit manifests should replace the example path with the run-specific
manifest path. This command validates provenance structure and semantics only;
it does not execute portfolio logic, broker/provider logic or private inputs.

## Handoff ZIP Policy

`external_review_packet/HANDOFF_LATEST.sha256` is the committed integrity
pointer for `external_review_packet/HANDOFF_LATEST.zip`.

`HANDOFF_LATEST.zip` may remain an ignored/untracked external upload and
transport artifact unless a future policy change explicitly makes ZIP tracking
mandatory. Reviewers need the supplied ZIP file to independently verify bundled
content. Top-level reviewer-facing evidence may be committed when intentionally
extracted.

## Human Authority

The Human Operator remains the final acceptance authority for audit evidence,
handoffs, release decisions and investment decisions.
