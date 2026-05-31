# Audit Command Provenance Hardening Acceptance

## Purpose

This document records the external review outcome and Human Operator acceptance
for `AUDIT_COMMAND_PROVENANCE_HARDENING`.

This is an operator acceptance record for governance / audit-provenance
hardening for future audit runs. It is not Production Readiness, not Investment
Readiness, not full historical audit reconstruction, and not full deterministic
reproduction of old audit artifacts.

## Acceptance Status

- acceptance_status: `ACCEPTED_WITH_FINDINGS_BY_HUMAN_OPERATOR`
- accepted_by: `Human Operator`
- accepted_artifact_type: `governance / audit-provenance hardening for future audit runs`
- external_review_verdict: `ACCEPTED_WITH_FINDINGS`
- external_review_next_step:
  `OPERATOR_ACCEPTANCE_RECORD_FOR_AUDIT_COMMAND_PROVENANCE_HARDENING`

External LLM reviews are advisory and do not replace Human Operator acceptance
authority.

## Patch Identity

- patch_title: `AUDIT_COMMAND_PROVENANCE_HARDENING`
- repository: `charizzzzard/compound_income_os`
- branch: `main`
- base_head: `560e9c1166f7c5319b2c5dcb8055fe1dfd99fe57`
- implementation_head: `163585ed9c5b53a5520babbc8de738e75c89091b`
- publication_head_before_acceptance_record:
  `73ff28a99bacfe5cf796d5e4084b63a592fa2ea6`
- handoff_sha256:
  `7FB20A829210D74BA549F56BC2589C152554CAB9DDF2C82A228DCD72B40C60D6`
- authoritative_handoff_path: `external_review_packet/`
- handoff_zip_policy:
  `HANDOFF_LATEST.zip remains ignored/untracked upload and transport artifact; HANDOFF_LATEST.sha256 is the committed integrity pointer.`

## Scope Summary

The accepted patch adds a forward-looking audit command provenance standard for
future Full Portfolio Capability Execution Audits.

Accepted scope:

- machine-readable audit run manifest format;
- explicit `provenance_status` values;
- degraded provenance semantics;
- repo-relative path policy;
- validator/helper;
- synthetic example manifest;
- targeted tests;
- updated central external review handoff metadata.

The patch does not reconstruct historical audit commands. Old audit artifacts
remain not fully command-reproduced. Future Full Portfolio Capability Execution
Audits must record command provenance deterministically at execution or
inspection time.

P1 closure status: `P1_CLOSED_FOR_FUTURE_RUNS`.

This does not retroactively close historical audit command reconstruction. Prior
audit artifacts remain not fully command-reproduced unless future evidence
proves otherwise.

## Evidence Summary

Patch evidence:

- command provenance contract added:
  `docs/contracts/AUDIT_COMMAND_PROVENANCE_CONTRACT.md`
- synthetic manifest added:
  `examples/audit_command_provenance/audit_run_manifest.example.json`
- validator/helper added:
  `src/audit_command_provenance.py`
- targeted tests added:
  `tests/test_audit_command_provenance.py`
- handoff packet metadata updated under `external_review_packet/`
- publication metadata synchronized on `origin/main`

Codex-reported validation:

- `python -m ruff check .`: `PASS`
- `python -m pytest tests/test_audit_command_provenance.py -q`: `PASS`
- `python -m pytest tests/test_handoff_bundle.py tests/test_handoff_zip_export.py -q`: `PASS`
- `python -m pytest -q`: `PASS`, `1012 passed, 411 subtests passed`
- handoff scanner: `forbidden_count=0`
- handoff scanner: `local_path_leak_count=0`

External review basis:

- external review outcome: `ACCEPTED_WITH_FINDINGS`
- no P0 blockers
- no P1 high findings
- P1 command-provenance finding assessed as
  `P1_CLOSED_FOR_FUTURE_RUNS`
- handoff integrity accepted
- scope boundaries respected
- external review independently verified ZIP/SHA and targeted provenance tests
  where reported by reviewer

## Handoff Status

- handoff_path: `external_review_packet/`
- handoff_zip: `external_review_packet/HANDOFF_LATEST.zip`
- handoff_sha: `external_review_packet/HANDOFF_LATEST.sha256`
- handoff_sha256:
  `7FB20A829210D74BA549F56BC2589C152554CAB9DDF2C82A228DCD72B40C60D6`
- zip_file_count: `19`
- nested_zip_count: `0`
- handoff_manifest_present: `true`
- handoff_change_classification_present: `true`
- handoff_omitted_artifacts_present: `true`
- zip_policy: `ignored/untracked upload and transport artifact`

Independent ZIP content verification requires access to the supplied external
ZIP artifact.

## Findings Carried Forward

### P2: Windows Drive-Relative Paths Should Be Rejected

- severity: `P2_MEDIUM`
- finding: Path validator should reject Windows drive-relative paths such as
  `C:foo`, `C:Users/operator/file.csv` and `D:folder/file`.
- current_reality: The validator rejects absolute Windows/POSIX paths,
  UNC-like starts, home paths and parent traversal.
- required_follow_up: Explicitly reject drive-relative Windows strings before
  the next real audit run.

### P2: Semantic Cross-Field Consistency Checks Should Be Added

- severity: `P2_MEDIUM`
- finding: Validator should add semantic cross-field consistency checks before
  the next real audit run.
- required_follow_up:
  - `entry.run_id` must match top-level `run_id`;
  - `entry.repo_head` must match top-level `repo_head`;
  - `repo_head` should be 40-hex or an explicitly documented synthetic
    placeholder;
  - `created_at_utc` and `recorded_at_utc` should be RFC3339/UTC;
  - `SKIPPED_*` provenance should require `command=""`, `exit_code=null` and
    `result_status` `SKIPPED` or `NOT_EXECUTABLE_FROM_REPO_STATE`;
  - `OUTPUT_OBSERVED_COMMAND_NOT_RECORDED` should require `command=""` and
    remain degraded, not reproduced;
  - `provenance_status`, `command_kind`, `result_status`, `exit_code` and
    `command` should be mutually consistent.

### P3: Optional JSON Schema

- severity: `P3_LOW_INFO`
- finding: Optional JSON Schema could be added for the audit command provenance
  manifest.

### P3: Recorded Versus Executed Validation Wording

- severity: `P3_LOW_INFO`
- finding: Continue distinguishing `RECORDED` validation from independently
  executed validation in external handoffs.

### P3: ZIP Transport Artifact Policy

- severity: `P3_LOW_INFO`
- finding: `HANDOFF_LATEST.zip` remains an external/upload transport artifact;
  independent ZIP verification requires access to the supplied ZIP.

## Boundary Confirmation

This acceptance does not introduce or claim:

- production readiness;
- investment readiness;
- broker integration;
- provider/API integration;
- order execution;
- live trading;
- buy/sell automation;
- investment advice automation;
- performance claims;
- private data publication;
- scoring formula changes;
- ranking formula changes;
- valuation methodology changes;
- portfolio-rule changes;
- watchlist/fundamentals logic changes;
- backtesting;
- historical audit reconstruction;
- full deterministic reproduction of old audit artifacts.

## Human Authority

The Human Operator remains final acceptance authority for patches, audit
evidence, handoffs, external review ingestion, release decisions and investment
decisions.
