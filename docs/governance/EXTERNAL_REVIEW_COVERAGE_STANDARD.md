# External Review Coverage Standard

## Purpose

This standard defines how Compound Income OS (CIOS) external reviews must
describe coverage, evidence, gaps and gate recommendations. It converts
external review findings into a repeatable governance language without granting
release acceptance or product readiness.

The standard exists because external reviews had strong coverage for handoff
integrity, source-of-truth precedence and non-scope boundaries, but only partial
coverage for clean-room reproduction, cross-patch regression, runtime
enforcement, semantic investment logic, adversarial inputs, temporal integrity,
broker import readiness, dashboard interpretation and release environment
parity.

## Scope

External review coverage applies to:

- Handoff packets, SHA files, manifests and source-of-truth documents.
- Architecture, contracts, feature status, maturity and known-gaps documents.
- Tests and validation outputs explicitly included in the handoff.
- Review gates that block future feature classes until evidence exists.
- Advisory findings from external LLM reviews, coding agents and human
  reviewers.

## Non-Scope

This standard does not implement:

- Investment logic, scoring formulas, portfolio rules or recommendations.
- Runtime Event Ledger, Broker Import, Replay, Backtesting, Dashboard,
  Valuation Automation or Outcome Attribution.
- Legal, tax, commercial or investment approval.
- Order execution, broker writes, API integration, scraping or provider
  adapters.
- Runtime enforcement of the gates defined here.

## Source Of Truth For External Reviews

For an external review packet, reviewers must use the packet's explicit
precedence order. If a packet does not provide a stricter order, use:

1. `external_review_packet/00_READ_ME_FIRST.md`
2. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
3. `external_review_packet/HANDOFF_LATEST.zip`
4. `external_review_packet/HANDOFF_LATEST.sha256`
5. Historical reports only as context

If ZIP-internal metadata conflicts with the external packet context, the
external packet context wins for packet metadata, review scope, dirty-state
interpretation and reviewer instructions.

External reviews must distinguish:

- Tracked source state from handoff metadata dirtiness.
- Local validation from clean-room reproduction.
- Test presence from sufficient regression coverage.
- Generated artifacts from semantically correct artifacts.
- Maturity documentation from operational readiness.

## Coverage State Semantics

Reviewers must not collapse the following states:

- `documented`: A rule, contract or boundary is written down.
- `tested`: A test or validation command checks a specific behavior.
- `enforced`: Runtime or release tooling blocks invalid states.
- `operationally_ready`: The workflow has the required contracts, runtime,
  validation, review flow and tests for local use.
- `production_ready`: The workflow has release-grade validation, clean-room
  reproduction, operator acceptance and no unresolved blocking gaps.

Documentation alone is not enforcement. A template validator is not a runtime
workflow. A passing local test is not clean-room release evidence.

## Validation And Acceptance Distinctions

Reviewers must keep these concepts separate:

- `Template Validation`: read-only checks over template structure, placeholder
  values, required fields and conservative boundary rules.
- `Runtime Validation`: checks over actual runtime inputs, outputs, state
  transitions and failure modes.
- `Event Acceptance`: explicit acceptance of a concrete event or fact into an
  auditable workflow.
- `Operator Acceptance`: final human acceptance of a patch, release, handoff or
  review outcome.

Template validation must never be described as real event acceptance, broker
import readiness, replay readiness, dashboard readiness or investment
readiness.

## Coverage Ratings

- `STRONG`: Evidence exists, is current, is included in the review packet and is
  backed by focused validation or clear source-of-truth metadata.
- `PARTIAL`: Evidence exists but is limited to docs, templates, local tests or a
  narrow path.
- `WEAK`: Evidence is indirect, stale, incomplete, not tested or easily
  misinterpreted.
- `NOT_COVERED`: No systematic review evidence exists for the dimension.
- `UNKNOWN`: The reviewer cannot determine coverage from the available packet.

## Priority Levels

- `P0`: Blocks feature classes that could create misleading decisions,
  private-data leakage, runtime overclaims, broker/import risk or false
  readiness.
- `P1`: Blocks major release confidence, clean reproduction, cross-kernel
  consistency or operator clarity.
- `P2`: Improves maintainability, reviewer ergonomics or future governance but
  does not block near-term contract-only work.

## Mandatory Review Coverage Matrix

Every coverage audit must include a matrix with these columns:

| Review Dimension | Current Coverage | Evidence | What is still not checked | Risk if unchecked | Recommended Review Gate | Priority |
| --- | --- | --- | --- | --- | --- | --- |

Rows must explicitly distinguish documented, tested, enforced,
operationally-ready and production-ready states.

## Authority And Acceptance Rules

- External reviews may recommend, warn, block or request follow-up, but they may
  not grant final release acceptance.
- Final acceptance remains with the Human Operator.
- External LLMs and coding agents are advisory or executive aids, not acceptance
  authorities.
- Coding agents must not self-accept their own work as final release approval.
- Review recommendations must preserve non-scope boundaries.

## Hard Review Invariants

- Missing, stale and unknown data must remain visible.
- No silent imputation.
- No silent overwrite of accepted facts.
- No investment advice.
- No order execution.
- No legal, tax, commercial or provider approval unless an explicit accepted
  review artifact exists.
- No production-readiness claim may be inferred from documentation, templates or
  local-only validation.

## Gate Registry

The canonical machine-readable review gate list is
`docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml`.

The feature-class sequencing rules are documented in
`docs/governance/EXTERNAL_REVIEW_GATE_SEQUENCE.md`.
