# CIOS Operating Model

## Purpose

This operating model defines who or what can propose, validate, accept and
reject changes in Compound Income OS (CIOS). It is a governance document, not a
runtime module.

## Roles

### Human Operator

The human operator owns strategy, private inputs, final acceptance, final
investment decisions and release acceptance. The human operator can accept,
reject, pause or revert a patch after reviewing evidence.

### Codex / Local Coding Agent

Codex can inspect repo reality, implement scoped patches, update docs/tests,
run validation and prepare commits. Codex cannot self-certify final acceptance,
cannot make investment decisions and cannot override the human operator.

### External LLM Reviewer

External LLM reviewers can critique architecture, find gaps, check handoff
bundles and recommend follow-up patches. Their output is advisory unless the
human operator accepts it into the repo.

### Test / Validation Runner

Tests and validation commands verify behavior, structure, serialization,
contracts and reproducibility. They do not decide investment actions and do not
make a release accepted by themselves.

### Repo

The committed Git repo is the primary durable source of truth for code, docs,
contracts, configs and tests.

### Manifest / Release Artifacts

Run manifests, artifact indexes, used-input indexes, validation outputs,
handoff contexts and checksum files are evidence artifacts. They support review
but do not supersede the committed repo unless the release process explicitly
defines their precedence.

## Authority Model

| Actor | Can propose | Can implement | Can validate | Can accept | Can reject | Authority class |
| --- | --- | --- | --- | --- | --- | --- |
| Human Operator | yes | manually | yes | yes | yes | final |
| Codex | yes | yes | yes | no | no | implementation assistant |
| External LLM Reviewer | yes | no | advisory review | no | advisory only | advisory |
| Tests / Validation | no | no | yes | no | no | evidence |
| Git Repo | no | no | stores evidence | no | no | source of truth |
| Release / Handoff Artifacts | no | no | support review | no | no | release evidence |

Final acceptance always requires the human operator. A green test suite without
human acceptance is not final acceptance.

## Standard Loops

### Patch Loop

1. Inspect branch, HEAD and worktree.
2. Inspect authoritative files.
3. Make scoped changes.
4. Run targeted validation.
5. Commit only isolated, reviewed changes.
6. Report exact results and residual risks.

### External Review Loop

1. Create or update a handoff only when the patch requires it.
2. Include source, docs, tests, configs and metadata needed for review.
3. Exclude private/raw/secret data.
4. Treat external findings as advisory until accepted by the human operator.
5. Convert accepted findings into scoped follow-up patches.

### Release Loop

1. Freeze the implementation commit.
2. Run release validation.
3. Generate release/handoff metadata when required.
4. Verify checksums, required files and forbidden-content scans.
5. Commit metadata separately when needed.
6. Human operator accepts or rejects the release.

### Monthly Operator Run Loop

1. Prepare explicit local inputs.
2. Run selected deterministic stages.
3. Inspect manifests, data freshness, decision quality and review queue.
4. Build reports from processed artifacts.
5. Capture human decision/no-action where applicable.
6. Execute any broker action manually outside CIOS, if the operator decides so.

### Data Import / Review Loop

1. Import local inputs read-only.
2. Validate identity, schema, freshness and missing data.
3. Surface review-required states.
4. Apply only explicit reviewed transformations.
5. Preserve lineage and output contracts.

### Recovery / Rollback Loop

1. Prefer Git revert or forward fixes over destructive local resets.
2. Keep unrelated dirty files isolated.
3. Recover from committed state and validation evidence.
4. Document any manual repair in a follow-up patch or release note.

## Explicit Rules

- The human operator is the final acceptance authority.
- Tests validate behavior but do not decide investment actions.
- External LLMs can critique but not accept releases.
- Codex can patch but not self-certify final acceptance.
- Repo, manifests, validation outputs and release artifacts are authoritative
  evidence only when committed or explicitly accepted.
- Chat history and uncommitted generated text are not authoritative.
