# CIOS Codex Operationalization Standard

## Purpose

This standard defines how Codex, GitHub repository inspection, central handoff
packets, external LLM reviews, head-offset handling and failure-mode reporting
must work for Compound Income OS (CIOS).

It is a governance standard. It does not implement runtime enforcement,
investment logic, scoring changes, ranking changes, valuation changes,
portfolio-rule changes, dashboard semantics, data-freshness semantics, broker
integration, provider/API integration, order execution, buy/sell automation,
production readiness, product readiness or investment readiness.

## Source Of Truth Hierarchy

For CIOS patch work and external review, the source-of-truth hierarchy is:

1. The committed GitHub repository for source, docs, tests and configs.
2. `external_review_packet/HANDOFF_LATEST_CONTEXT.md` for current external
   review packet metadata, scope, head semantics and precedence.
3. `external_review_packet/HANDOFF_LATEST.zip` for the included review evidence
   snapshot.
4. `external_review_packet/HANDOFF_LATEST.sha256` for checksum binding of the
   current reviewer-facing ZIP.
5. ZIP-internal `HANDOFF_CONTEXT.md`, `HANDOFF_PATCH_IDENTITY.md`,
   `HANDOFF_CHANGE_CLASSIFICATION.csv`, `HANDOFF_VALIDATION.txt`,
   artifact indexes and omitted-artifact registers as secondary packet context.
6. `outputs/` only as local generated evidence unless explicitly accepted,
   committed, summarized by the central packet context or included in the
   central packet.

Ignored outputs are not authoritative repo truth by themselves. GitHub committed
state must not be treated as containing ignored ZIPs, local generated reports,
private/raw inputs, provider artifacts or broker artifacts unless they are
explicitly committed or included in the central handoff.

## Required Head Taxonomy

Every material Codex patch, handoff sync, external review ingestion or operator
closure must report the relevant heads separately:

- `repo_current_head`: current local Git HEAD at the time of inspection.
- `implementation_head`: commit containing the patch implementation.
- `preflight_head`: HEAD observed before a preflight or evidence capture step.
- `handoff_export_head`: HEAD used by the handoff exporter to build the ZIP.
- `handoff_metadata_commit_head`: metadata-only commit that updates handoff
  context, checksum or publication files after implementation.
- `central_handoff_zip_head`: HEAD represented by the current central ZIP.
- `current_handoff_head`: HEAD declared by the central handoff context as the
  current reviewer-facing handoff state.
- `remote_main_head`: HEAD of `origin/main` or the configured remote main
  branch at the time of verification.
- `accepted_review_head`: HEAD accepted by the Human Operator for a specific
  review or closure.

If any of these differ, the report must say why. A report must not silently
collapse implementation, metadata, handoff and remote heads into one value.

## Allowed Head Offset Cases

The following head offsets are allowed only when explicitly reported:

- Metadata-only commits after implementation.
- Handoff metadata sync commits after a ZIP was exported.
- Central packet publication commits that update reviewer-facing context or
  checksum files.
- Report-only ignored outputs under `outputs/`.
- Remote verification evidence captured after the implementation commit.

Allowed offset does not mean ambiguity is acceptable. The central context must
state which head the ZIP represents and which head the repository currently
exposes.

## Disallowed Ambiguity

CIOS reports, handoffs and reviews must not:

- claim GitHub HEAD equals handoff HEAD without checking both;
- treat ignored outputs as committed repo truth;
- treat `HANDOFF_VALIDATION.txt` recorded validation as executed validation;
- treat external LLM review as final acceptance;
- treat documentation-only standards as runtime enforcement;
- infer private/raw/provider/broker files from omitted files;
- infer production readiness, product readiness or investment readiness from
  tests, documentation or handoff generation;
- imply broker writes, order execution, buy/sell automation or investment
  advice from operator-facing evidence surfaces.

## Handoff Reconciliation Gates

Before a central external handoff is presented as reviewer-facing, reconciliation
must verify and report:

- `external_review_packet/HANDOFF_LATEST.sha256` matches the actual
  `external_review_packet/HANDOFF_LATEST.zip`.
- The ZIP opens and `zipfile.testzip()` is `None`.
- `nested_zip_count` is `0`.
- `forbidden_count` is `0`.
- No private, raw, secret, provider, broker, cache or local path leak entries
  are present.
- External context head fields are internally consistent or differences are
  explicitly explained.
- External packet context precedence is explicit.
- ZIP-internal `HANDOFF_VALIDATION.txt` validation entries are classified as
  `RECORDED_VALIDATION` unless independently executed in the current repo or
  extracted ZIP context.
- Actual ZIP file count and ZIP-internal `HANDOFF_VALIDATION.txt` `file_count`
  match, or the expected post-assembly delta is explicitly documented.
- Any files included after manifest or index generation are represented as
  `POST_MANIFEST_INCLUDED_EVIDENCE` or the packet fails reconciliation.
- `PRE_FLIGHT_REPO_REMOTE/*` evidence is represented in a deterministic index or
  explicitly listed as post-manifest evidence.

`outputs/handoffs/latest/` may be a generated source folder. The reviewer-facing
central packet remains `external_review_packet/` unless a later accepted
standard explicitly changes that rule.

## Codex Operating Requirements

Codex must:

- inspect repo reality before editing: branch, HEAD, short HEAD, dirty state,
  remote state and relevant files;
- preserve unrelated dirty files;
- keep patches scoped and minimal;
- avoid changing runtime financial logic under governance tasks;
- avoid changing scoring, ranking, valuation, portfolio-rule, dashboard,
  data-freshness, broker, provider, API or order-execution behavior unless that
  behavior is explicitly in scope;
- report skipped validation instead of implying success;
- run cheap targeted validation when available;
- keep handoff updates centralized under `external_review_packet/` when a
  handoff is required;
- distinguish tracked repo state from local generated state;
- distinguish recorded validation from actually executed validation.

Codex must not self-certify final acceptance. Codex can report that a patch is
implemented or validated within scope; final acceptance remains with the Human
Operator.

## External LLM Review Requirements

External LLM reviews are advisory. Reviewer prompts must include:

- source-of-truth precedence;
- head taxonomy and expected head relationships;
- changed files and patch identity;
- strict non-scope boundaries;
- validation reality, including the distinction between recorded validation and
  executed validation;
- known open gaps and known intentionally omitted artifacts.

External reviewers must cite repo-relative paths, separate evidence from
inference and distinguish:

- documented;
- tested;
- enforced;
- operationally_ready;
- production_ready.

External reviewers must not infer omitted local/private/raw/provider/broker
files. External reviewers cannot accept releases and cannot override the Human
Operator.

## Operator Decision Capture

Accepted operator decision states are:

- `ACCEPT_BASELINE_AS_WORKING_INPUT`
- `ACCEPT_WITH_FINDINGS`
- `RUN_NEXT_PATCH`
- `PAUSE_FOR_MANUAL_REVIEW`
- `REJECT_OR_REWORK`
- `ACCEPT_RELEASE_SCOPE_ONLY`

Chat-only decisions are not durable repo truth unless they are materialized in a
tracked accepted document or a central handoff context. The Human Operator
remains final acceptance authority for patches, releases, handoffs, external
review ingestion and investment decisions.

## Failure Mode Reporting

Codex and external review reports must classify failures as one of:

- `PATCH_INDUCED`
- `PRE_EXISTING`
- `TOOLING_NOT_AVAILABLE`
- `ENVIRONMENT_REQUIRED`
- `LOCAL_FIXTURE_REQUIRED`
- `RECORDED_ONLY`
- `BLOCKED_OPERATOR_ACTION_REQUIRED`
- `UNKNOWN_REVIEW_REQUIRED`

Reports must include command text, execution context, result, evidence class and
whether the failure is inside or outside patch scope. A failed optional tool may
be a finding, but it must not be silently converted into a pass.

## Explicit Non-Scope

This standard does not implement or approve:

- CIOS feature logic;
- investment logic changes;
- scoring changes;
- ranking changes;
- valuation changes;
- portfolio-rule changes;
- dashboard/data-freshness/report semantic changes;
- broker import changes;
- provider/API integration;
- scraping or crawling;
- order execution;
- buy/sell automation;
- runtime LLM dependency;
- runtime enforcement;
- replay, backtesting, simulation or outcome attribution;
- public/commercial packaging approval;
- production readiness;
- product readiness;
- investment readiness.

The standard governs evidence, handoff reconciliation and review workflow only.
