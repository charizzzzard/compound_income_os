# CIOS Practical Operating Standard

## Purpose

This standard defines the practical day-to-day operating rules for Codex,
external LLM reviewers and the Human Operator when changing Compound Income OS
(CIOS). It materializes the accepted working baseline from
`docs/governance/CIOS_CODEX_OPERATIONALIZATION_STANDARD.md` into an actionable
patch lifecycle standard.

This is a governance document. It does not implement runtime enforcement,
investment logic, scoring changes, ranking changes, valuation changes,
portfolio-rule changes, dashboard semantics, data-freshness semantics, broker
integration, provider/API integration, order execution, buy/sell automation,
production readiness, product readiness or investment readiness.

## Core Rule

CIOS is a deterministic, local-first investment decision support system. The
committed repository, deterministic artifacts and central handoff packet are
evidence surfaces. They do not execute orders and they do not replace the Human
Operator.

The Human Operator remains final acceptance authority for patches, handoffs,
external review ingestion, release-scope acceptance and investment decisions.

## Source-Of-Truth Precedence

For current patch and external review work, use this precedence:

1. Committed Git repository state for source, docs, tests and configs.
2. `external_review_packet/HANDOFF_LATEST_CONTEXT.md` for central external
   review packet metadata, scope, head semantics and precedence.
3. `external_review_packet/HANDOFF_LATEST.zip` for the included review evidence
   snapshot.
4. `external_review_packet/HANDOFF_LATEST.sha256` for checksum binding.
5. ZIP-internal `HANDOFF_CONTEXT.md`, `HANDOFF_PATCH_IDENTITY.md`,
   `HANDOFF_CHANGE_CLASSIFICATION.csv`, `HANDOFF_VALIDATION.txt`,
   artifact indexes and omitted-artifact registers as secondary context.
6. `outputs/` only as local generated evidence unless explicitly accepted,
   committed, summarized by the central context or included in the central
   packet.

Do not infer ignored, generated, local-only, private, raw, broker or provider
files from GitHub.

## GitHub And Central Handoff Packet Usage

GitHub is the browser-visible committed source inspection surface. The central
handoff packet is the reviewer-facing evidence snapshot. They are complementary
and must not be silently treated as identical.

Reports must explicitly state:

- `repo_current_head`
- `implementation_head`
- `central_handoff_zip_head`
- `current_handoff_head`
- `remote_main_head`
- `push_status`
- `remote_main_contains_head`

Allowed `push_status` values are:

- `PUSHED`
- `NOT_PUSHED`
- `NOT_CHECKED`
- `NOT_APPLICABLE`

Allowed `remote_main_contains_head` values are:

- `YES`
- `NO`
- `NOT_CHECKED`
- `NOT_APPLICABLE`

Remote publication status must not be inferred from local commit state alone.
It must be checked with Git remote evidence or reported as `NOT_CHECKED` or
`NOT_APPLICABLE`.

## Normal Patch Lifecycle

Every normal CIOS patch should follow this order:

1. Repo-reality preflight.
2. Scope and non-scope confirmation.
3. Relevant file inspection.
4. Minimal implementation.
5. Targeted validation.
6. Optional broader validation when appropriate.
7. Diff review.
8. Commit isolated patch files.
9. Handoff regeneration or explicit no-handoff justification.
10. Optional metadata-only handoff commit.
11. Optional normal push to `origin/main`.
12. External review when required.
13. Human Operator acceptance or rework decision.

Do not combine unrelated feature, cleanup, handoff and acceptance work unless
the task explicitly scopes that combination.

## Preflight Requirements

Before editing, Codex must inspect and report:

- current branch;
- `git rev-parse HEAD`;
- short HEAD;
- `git status --short --branch`;
- `git diff --name-status`;
- `git diff --check`;
- configured remotes;
- remote main HEAD when network and credentials allow;
- relevant authoritative files;
- whether ignored/generated/private-risk paths are relevant to the task.

If the worktree is dirty, Codex must classify dirty files and preserve unrelated
changes.

## Targeted Validation

Each patch must define targeted validation commands before or during
implementation. Commands must be reported with:

- command text;
- execution context;
- result;
- evidence class: `EXECUTED`, `RECORDED_ONLY` or `SKIPPED`;
- scope relation: `IN_SCOPE`, `OUT_OF_SCOPE` or `GLOBAL_BASELINE`.

Recorded validation is not execution proof. `HANDOFF_VALIDATION.txt` entries
remain `RECORDED_VALIDATION` unless independently executed and reported.

## Minimum Validation Commands

For governance-only patches, the minimum expected commands are:

- `git diff --check`
- `python -m ruff check docs tests src`
- the targeted pytest or unittest file when a test is added or changed

For runtime patches, the task must add targeted runtime tests and run any
directly related existing tests. Full-suite validation should be run when the
blast radius justifies it or when the task explicitly requires it.

## Handoff Regeneration Rules

Regenerate or reconcile the central handoff under `external_review_packet/` when
a patch changes reviewer-facing governance, external review state, source of
truth, release evidence, handoff behavior or material operator context.

If the ZIP is regenerated, validate and report:

- SHA256 file matches ZIP;
- `zipfile.testzip()` returns `None`;
- ZIP file count;
- nested ZIP count;
- forbidden/private/raw/provider/broker/local-path leak counts where tooling
  exists;
- `HANDOFF_PATCH_IDENTITY.md` patch title and head fields;
- `HANDOFF_CHANGE_CLASSIFICATION.csv` changed files;
- whether the ZIP head differs from repo or remote head.

If the ZIP is not regenerated, explain why and report the residual risk. Do not
silently leave a stale handoff.

## External LLM Review Protocol

External reviews are advisory. External reviewers must use the source-of-truth
precedence in this standard and cite repo-relative paths.

Findings must use exactly these severities:

- `BLOCKER`
- `MAJOR`
- `MINOR`
- `INFO`

Alternative labels such as critical, medium, advisory or observation must be
mapped explicitly to these canonical severities before operator acceptance.

External reviewers must distinguish:

- documented;
- tested;
- enforced;
- operationally_ready;
- production_ready.

External reviewers must not infer omitted private/raw/provider/broker files and
must not treat external review as final acceptance.

## Operator Acceptance Protocol

Operator decisions should use one of these durable states:

- `ACCEPT_BASELINE_AS_WORKING_INPUT`
- `ACCEPT_WITH_FINDINGS`
- `RUN_NEXT_PATCH`
- `PAUSE_FOR_MANUAL_REVIEW`
- `REJECT_OR_REWORK`
- `ACCEPT_RELEASE_SCOPE_ONLY`

Chat-only decisions are not durable repo truth unless materialized in a tracked
accepted document or central handoff context. The Human Operator remains final
acceptance authority.

## Allowed Metadata-Only Head Offsets

The following head offsets are allowed only when explicitly reported:

- metadata-only commits after implementation;
- handoff metadata sync commits;
- central packet publication commits;
- report-only ignored outputs;
- remote verification evidence captured after implementation.

When an offset exists, the final report and central context must separate:

- implementation head;
- central handoff ZIP head;
- metadata-only head;
- remote main head;
- current repo head.

## Forbidden Parallel Handoffs

`external_review_packet/` is the reviewer-facing central handoff unless a later
accepted standard explicitly changes that rule. `outputs/handoffs/latest/`,
`outputs/handoffs/archive/`, `outputs/handoffs/upload_ready/` and other
`outputs/` folders may be generated evidence sources, but they must not be
presented as a second authoritative external review packet.

## Required Final Report Structure

Final patch reports should include:

- executive verdict;
- repo reality;
- task scope reality;
- implemented changes;
- validation reality;
- source-of-truth and handoff reality;
- residual risks;
- operator decision recommendation;
- final non-claims.

Under repo reality, reports must include:

- branch;
- HEAD before;
- HEAD after implementation;
- HEAD after metadata or handoff sync, if applicable;
- remote main before and after when checked;
- `push_status`;
- `remote_main_contains_head`;
- dirty state before and after;
- files changed;
- commit SHA;
- push method when pushed.

## Residual Risk Handling

Residual risks must be classified as:

- `BLOCKER`
- `MAJOR`
- `MINOR`
- `INFO`

Each residual risk must state scope relation, evidence and required follow-up or
acceptance rationale.

## Missing Stale Unknown Data Visibility Invariant

Missing, stale or unknown data must remain visible and must not be silently
imputed, overwritten, suppressed or converted into accepted facts.

This invariant applies especially to:

- data-contract work;
- dashboard work;
- report work;
- evidence work;
- valuation work;
- portfolio work;
- watchlist work;
- ranking work;
- decision-journal work.

## Acceptance Threshold

A patch may be recommended for operator acceptance only when:

- scope is preserved;
- required validation is executed or honestly classified as skipped;
- handoff state is current or stale risk is explicit;
- no private/raw/provider/broker files are introduced;
- no unrelated dirty files are staged;
- external review findings, if any, are ingested with canonical severities;
- the Human Operator remains final acceptance authority.

## Practical Default For Future CIOS Work

Default to the smallest safe patch that hardens existing behavior, evidence or
governance. Prefer deterministic local tests over broad claims. Prefer
contract-first work before runtime-sensitive features. Do not proceed to broker,
order, valuation automation, replay, backtesting, outcome attribution or
production-readiness work without the required accepted gates.

## Final Non-Claims

This standard does not claim:

- production readiness;
- product readiness;
- investment readiness;
- broker readiness;
- provider/API readiness;
- order execution capability;
- buy/sell automation;
- runtime enforcement;
- legal, tax or commercial approval.

It governs practical repo operation, review and handoff discipline only.
