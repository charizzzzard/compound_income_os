# Data Visibility And Artifact Boundary

## Purpose

This document defines the CIOS data visibility and artifact boundary model for
Git tracking, generated outputs, handoff exports, reproduction, private inputs
and future operational portfolio-decision artifacts.

It complements `docs/governance/CIOS_PRACTICAL_OPERATING_STANDARD.md` and the
handoff rules in `docs/HANDOFF_CONTRACT.md`. It is governance documentation and
does not implement runtime enforcement.

## Why Data Visibility Is An Operational Portfolio-Decision Concern

Future operational portfolio-decision patches need auditable evidence without
publishing private portfolio data. If generated decision outputs are ignored and
not represented by manifests, hashes, status rows, schemas or sanitized
examples, a future operator decision can become difficult to review. If those
outputs are tracked too broadly, CIOS can expose private holdings, broker data,
provider material or sensitive strategy notes.

The boundary goal is therefore dual:

- preserve privacy and local-first operation;
- keep future decision evidence reviewable enough for the Human Operator and
  external reviewers.

## Current Boundary Layers

### Git / .gitignore

`.gitignore` keeps generated `data/processed/`, `reports/`, `outputs/`, private
raw inputs and strategy content local by default. It also blocks caches, virtual
environments, build outputs, local `.env` files and temporary test files.

Tracked templates and examples are allowed only through narrow allowlists or
explicit tracked files.

### Handoff Exporter

The canonical exporter is documented in `docs/HANDOFF_CONTRACT.md` and
implemented by `src/handoff_zip_export.py` and `src/handoff_bundle.py`.
Handoff profiles include committed source, docs, tests, configs and explicitly
allowlisted review artifacts. Handoff output is review evidence, not source
truth by itself.

### Handoff Forbidden Patterns

Forbidden handoff entries include `.git`, `.env`, private raw data, user-agent
files, private SEC identity files, `node_modules`, build outputs, caches, ZIPs,
logs and temporary test artifacts.

### Omitted Artifacts

Artifacts blocked from handoff must be represented through
`HANDOFF_OMITTED_ARTIFACTS.csv`, sanitized labels, manifests, hashes or explicit
context notes. Omission must not invite inference about private/raw/provider or
broker content.

### External Review Packet

`external_review_packet/` is the reviewer-facing central packet. The context,
checksum and ZIP are authoritative only for the scope they declare. Local
`outputs/` folders are evidence sources, not parallel handoffs.

### Reproduction Matrix

`configs/test_reproduction_matrix.json` classifies checks as ZIP-safe,
local-repo-required, private-input-required, Git-context-required or optional
tooling. Reviewers must not treat local-only or private-input-dependent tests as
ZIP-safe unless the matrix says so and reproduction proves it.

### Data-Source Registry

`configs/personal_run_data_sources.yaml` identifies configured local inputs and
whether they are required, optional or disabled. Registry visibility does not
publish file contents and does not turn private data into external review data.

### Path / Privacy Redaction

Reports and handoffs must avoid local absolute paths, credentials, private raw
paths and user-agent content. Path redaction protects the operator while still
allowing reviewers to understand which classes of artifacts are omitted.

## What Must Remain Private / Local-Only

The following must remain private or local-only by default:

- real personal portfolio inputs;
- broker exports;
- provider files;
- private raw files;
- generated personal decision reports;
- generated personal portfolio outputs;
- real tax/cost data;
- strategy files containing personal allocations, current holdings or sensitive
  investment theses;
- API keys, credentials and user-agent files;
- local absolute paths and local-only logs.

## What May Be Tracked As Templates

Templates may be tracked when they contain no real personal holdings, broker
records, provider data, private strategy or credentials. Examples include
header-only CSV templates, placeholder YAML/JSON schemas and documented
operator-input shapes.

## What May Be Tracked As Sanitized Examples

Sanitized examples may be tracked when they are synthetic or scrubbed enough to
avoid exposing personal holdings, current allocations, broker files, provider
files, tax/cost details or sensitive strategy. Sanitized examples should be
clearly labeled as examples and not accepted facts.

## What May Be Included In external_review_packet

The central handoff may include committed source, docs, tests, configs,
templates, sanitized examples, processed artifacts explicitly allowlisted by the
handoff profile and reports that are safe for external review.

Private raw data, real broker/provider files, local secrets, ZIP/log/cache/build
artifacts and local strategy material must remain omitted unless a later Human
Operator-approved boundary explicitly changes the treatment.

## What Should Be Manifest / Hash / Status Only

Generated operational artifacts that are relevant for review but unsafe or too
context-specific to track should be represented by:

- manifests;
- hashes;
- schema rows;
- status summaries;
- omitted-artifact records;
- sanitized examples;
- review queue rows;
- freshness / decision-quality status rows.

## Future Portfolio-Decision Outputs

Generated personal portfolio outputs should not be committed by default. If
they become relevant for review or long-term audit, prefer sanitized examples,
schema templates, hashes, manifests, or omitted-artifact records unless the
Human Operator explicitly accepts a tracked artifact boundary.

Future `MONTHLY_PORTFOLIO_DECISION_BRIEF_MVP` outputs should default to
generated local-only artifacts. Before any real decision brief is tracked or
included in handoff, the patch must decide whether it is represented as a
template, sanitized example, manifest/hash/status row or omitted artifact.

Future `RANKING_ROBUSTNESS_SENSITIVITY_PRODUCER_MVP` outputs may be
review-relevant, but they are not automatically safe to commit when they expose
real portfolio or ranking context.

## Operator Review Rule For Unignore / Allowlist Changes

Any unignore rule, handoff allowlist expansion or tracked generated artifact
boundary that touches portfolio-decision evidence, strategy, personal holdings,
broker/provider files, tax/cost data or generated personal reports requires
explicit Human Operator review.

Prefer report-only recommendations over broad `.gitignore` changes. Do not
broadly unignore `data/processed/`, `reports/`, `outputs/`,
`data/raw/private/**`, `data/raw/personal_*`, `reports/*/personal_*`,
`strategy/private/**` or real broker/provider/tax/raw data.

## Explicit Non-Claims

This boundary does not implement or approve:

- broker import staging;
- broker API;
- order execution;
- buy/sell automation;
- portfolio event ledger runtime;
- replay;
- backtesting;
- simulation;
- outcome attribution;
- valuation automation;
- scoring formula changes;
- ranking formula changes;
- portfolio-rule changes;
- production readiness;
- investment readiness;
- runtime enforcement engine;
- legal, tax or commercial approval.

The Human Operator remains final acceptance authority.
