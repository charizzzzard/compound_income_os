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

Historical commands must not be inferred after the fact.

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

## READY_FOR_REVIEW Semantics

`READY_FOR_REVIEW` or equivalent conservative states are operator review labels.
They must not be interpreted as fully reproduced operational readiness when
`provenance_status` is degraded or command evidence is incomplete.

## Human Authority

The Human Operator remains the final acceptance authority for audit evidence,
handoffs, release decisions and investment decisions.
