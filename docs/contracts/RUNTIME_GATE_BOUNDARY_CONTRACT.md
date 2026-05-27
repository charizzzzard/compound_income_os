# Runtime Gate Boundary Contract

## Purpose

This contract defines the canonical runtime gate boundary semantics for
Compound Income OS (CIOS). It classifies governance checks, review evidence and
future runtime-sensitive gates so that documentation, tests, reports and
runtime enforcement cannot be confused.

This contract is a classification and design boundary. It does not implement a
Runtime Enforcement Engine. It does not grant release acceptance, product
readiness, production readiness or investment readiness. Findings from review
producers are evidence for the Human Operator; they are not automatic
acceptance.

## Scope

This contract defines:

- gate classification terms;
- the current classification of governance checks and future candidate gates;
- hard invariants for release and runtime claims;
- the promotion path from review evidence to runtime-relevant candidate and
  eventually runtime-enforced status;
- cases that must not be promoted automatically;
- prerequisites for future runtime-sensitive work.

Future runtime gate proposals must use
`docs/contracts/RUNTIME_GATE_DEFINITION_TEMPLATE.md` before any promotion from
`documentation_only` or `review_evidence` toward `runtime_relevant_candidate` or
future `runtime_enforced` status.

## Non-Scope

This contract does not implement:

- runtime enforcement;
- automatic release acceptance;
- product readiness, production readiness or investment readiness;
- investment logic or buy/sell recommendation changes;
- productive Portfolio Event Ledger or Event Ledger Runtime;
- broker import, broker parser, provider adapter, API integration or scraping;
- automatic transaction classification;
- Corporate Actions Engine, FX Engine or tax calculation;
- order execution;
- dashboard expansion;
- replay, backtesting, simulation or outcome attribution;
- valuation automation;
- legal or commercial approval;
- runtime LLM agent logic.

## Definitions

- `documentation_only`: A rule, boundary or design statement exists only in
  documentation. It is not tested, not operationally enforced and not evidence
  of readiness by itself.
- `review_evidence`: A deterministic artifact, report, validation result or
  review finding that can inform Human Operator acceptance. It does not accept
  releases or enforce runtime state by itself.
- `runtime_relevant_candidate`: A gate or check that may later affect runtime
  workflow admission, but only after an accepted contract, tests, failure
  semantics, operator override semantics, evidence artifacts and explicit Human
  Operator acceptance exist.
- `runtime_enforced`: A future state in which accepted runtime or release
  tooling blocks invalid runtime state according to an explicit accepted
  contract. No current CIOS governance producer has this classification.
- `operator_acceptance_required`: The Human Operator must explicitly accept a
  patch, gate result, override or release decision. Review evidence alone is
  insufficient.
- `non_runtime_governance_check`: A check that reads local repo or packet
  artifacts and produces review evidence without changing runtime behavior.
- `hard_non_scope`: A boundary that must not be inferred as implemented,
  accepted or ready unless a later explicit scope, contract, tests and Human
  Operator acceptance say so.
- `production_ready`: A future release claim requiring release-grade
  validation, clean-room reproduction, accepted runtime contracts, accepted
  operator workflow and no unresolved blocking gaps. This contract does not
  grant it.
- `investment_ready`: A prohibited inference that CIOS is ready to provide
  investment advice or automated investment decisions. This contract does not
  grant it.
- `release_acceptance`: A Human Operator decision that a release or handoff is
  accepted for its stated scope. External reviews and governance producers
  cannot grant this automatically.
- `automatic_release_acceptance`: A prohibited workflow in which a check,
  model, script, CI job or report accepts a release without Human Operator
  decision.
- `human_operator_final_acceptance`: The final authority for accepting patches,
  releases, handoffs, overrides and readiness claims.
- `evidence_artifact`: A deterministic, repo-relative artifact that records
  inputs, checks, status and limitations for review.
- `override`: A documented Human Operator action that allows a workflow to
  continue despite a warning or failure, subject to explicit scope and evidence.
- `rollback_or_correction`: A documented path to reverse, supersede or correct
  an accepted state if a gate, fact or workflow state is later found wrong.

## Gate Classification Model

| gate_or_check | current_classification | may_become_runtime_relevant | may_block_runtime_sensitive_work | may_auto_accept_release | required_before_runtime_use | notes |
| --- | --- | --- | --- | --- | --- | --- |
| RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW | review_evidence | yes | yes | no | Runtime Gate Boundary Contract, tests, explicit Human Operator acceptance | Current producer is read-only governance evidence, not runtime_enforced. |
| clean_room_reproduction_review | review_evidence | no | yes | no | Not applicable for runtime use | Packet reproduction evidence must not become runtime enforcement automatically. |
| release_ci_environment_parity_review | review_evidence | no | yes | no | Not applicable for runtime use | Environment observations are not CI green and not release acceptance. |
| external_review_cross_patch_regression | review_evidence | no | yes | no | Not applicable for runtime use | Drift findings can block review, but they do not enforce runtime state. |
| handoff_bundle verification | review_evidence | no | yes | no | Not applicable for runtime use | Handoff integrity evidence is not product or production readiness. |
| future Broker Import Staging Contract | runtime_relevant_candidate | yes | yes | no | Accepted staging contract, identity/event mapping tests, privacy boundary, rollback/correction path | No broker import exists from this contract. |
| future Portfolio Event Ledger Runtime Contract | runtime_relevant_candidate | yes | yes | no | Accepted runtime contract, append-only tests, correction/reversal tests, event acceptance workflow | No productive Event Ledger exists from this contract. |
| future Dashboard Misinterpretation Review | review_evidence | yes | yes | no | Operator comprehension evidence, wording boundaries, dashboard contract | No dashboard expansion exists from this contract. |
| future As-of / Temporal Integrity Review | review_evidence | yes | yes | no | As-of contract, temporal tests, stale/unknown evidence artifacts | Required before replay, backtesting and outcome attribution. |
| future Snapshot / Replay Contract | runtime_relevant_candidate | yes | yes | no | Accepted snapshot/as_of contract, deterministic replay tests, correction path | No replay or backtesting exists from this contract. |
| future Attribution Contract | runtime_relevant_candidate | yes | yes | no | Accepted attribution contract, event/decision linkage, temporal evidence | No outcome attribution exists from this contract. |
| future Semantic Decision Quality Review | review_evidence | yes | yes | no | Semantic review evidence, adversarial examples, operator wording boundary | No investment advice or valuation automation exists from this contract. |
| future Adversarial Input Review | review_evidence | yes | yes | no | Negative fixtures, failure semantics, missing/stale/unknown handling tests | Review evidence only until explicitly scoped as runtime. |
| future Valuation Methodology Contract | runtime_relevant_candidate | yes | yes | no | Accepted methodology, source/provenance evidence, semantic tests, operator acceptance | No valuation automation exists from this contract. |

Classification rules:

- Current governance producers remain `review_evidence` or
  `documentation_only`.
- No current CIOS producer is classified as `runtime_enforced`.
- No gate may have `may_auto_accept_release = yes`.
- Runtime-sensitive future areas may only be described as candidates until a
  later accepted runtime contract exists.

## Hard Invariants

- No gate may auto-accept a release.
- Human Operator remains final acceptance authority.
- PASS, WARN and FAIL results from governance producers are evidence, not
  release approval.
- Missing, stale and unknown data must remain visible.
- No silent imputation.
- No silent overwrite of accepted facts.
- Runtime-relevant status requires an explicit contract, tests, failure
  semantics, operator override semantics, evidence artifact,
  rollback_or_correction path and explicit Human Operator acceptance.
- Product readiness, production readiness and investment readiness must not be
  inferred from governance evidence.
- Investment, broker, order, dashboard, replay, backtesting,
  outcome-attribution and valuation-automation claims remain prohibited unless
  they are explicitly scoped, tested and accepted in a later patch.
- External LLM reviews are advisory evidence only and cannot accept releases.

## Promotion Path

A check may move from `review_evidence` to `runtime_relevant_candidate` only
when all of the following exist:

- completed Runtime Gate Definition Template;
- canonical contract section;
- owner surface;
- trigger condition;
- failure semantics;
- severity semantics;
- generated evidence artifact;
- tests;
- operator override semantics;
- rollback_or_correction path;
- dashboard/report wording boundary, if visible to an operator;
- privacy/evidence boundary, if user, broker, provider or private data is
  affected;
- deterministic reproduction path;
- explicit Human Operator acceptance;
- documented non-claims.

A `runtime_relevant_candidate` may move to `runtime_enforced` only in a later
explicitly scoped patch that implements runtime or release tooling and is
accepted by the Human Operator. That later patch must prove the enforcement
behavior with tests and must preserve all non-scope boundaries not explicitly
changed.

## Non-Promotion Cases

The following must not be promoted automatically:

- external LLM review results;
- handoff metadata generation;
- environment parity observations;
- clean-room reproduction evidence;
- regex- or pattern-based overclaim detection;
- local path leak scans;
- pytest or ruff availability checks;
- generated reports without Human Operator acceptance.

## Runtime-Sensitive Prerequisites

| future_area | required_contracts | required_tests | required_evidence_artifacts | required_operator_decisions | explicit_non_claims_until_accepted | rollback_or_correction_requirement |
| --- | --- | --- | --- | --- | --- | --- |
| Broker Import Staging | Broker Import Staging Contract, Instrument Master Contract, Portfolio Event Ledger Contract, Runtime Gate Boundary Contract | identity mapping, event mapping, privacy boundary, malformed input tests | staging readiness report, mapping matrix, omitted/private data evidence | accept staging scope and residual findings | no broker parser, no broker API, no production import, no order execution | documented rejection/correction path for staged rows |
| Portfolio Event Ledger Runtime | Portfolio Event Ledger Runtime Contract, Runtime Gate Boundary Contract | append-only behavior, correction/reversal/supersession, event acceptance workflow, private event exclusion | runtime readiness report, event acceptance evidence, correction chain evidence | accept runtime design and operator event acceptance workflow | no productive ledger, no broker import production, no replay | append-only correction/reversal path |
| Dashboard Expansion | Dashboard Operator Surface Contract, Dashboard Misinterpretation Review, Runtime Gate Boundary Contract | operator comprehension, misleading wording, stale/unknown display, action-like UI guardrails | dashboard surface review, wording findings, stale/unknown visibility report | accept dashboard surface scope | no dashboard readiness, no advice, no order instruction | report/dashboard correction path |
| Replay / Backtesting | Snapshot / Replay Contract, As-of / Temporal Integrity Review, Event Ledger Runtime Contract | point-in-time data, snapshot/as_of behavior, stale/unknown temporal handling | replay readiness report, snapshot evidence, temporal matrix | accept replay/backtesting scope and limitations | no replay, no backtesting, no performance promise | replay invalidation/correction path |
| Outcome Attribution | Attribution Contract, Event Ledger Runtime Contract, As-of / Temporal Integrity Review | decision-event linkage, temporal attribution, missing/conflicting data | attribution readiness report, linkage evidence, unresolved gaps | accept attribution scope and residual uncertainty | no outcome attribution, no performance attribution | attribution correction/supersession path |
| Valuation Automation | Valuation Methodology Contract, Semantic Decision Quality Review, Data Conflict and Provenance Review | methodology tests, source/provenance conflicts, adversarial semantic cases | valuation methodology evidence, source conflict matrix, uncertainty report | accept methodology and wording boundaries | no valuation automation, no investment readiness, no advice | valuation rollback/correction path |
| Provider Adapter / API Integration | Data Source License Boundary Contract, Provider Adapter Contract, Local Security and Secret Hygiene Review | license boundary, provenance, network failure, credential handling | provider readiness report, license evidence, secret hygiene scan | accept provider scope and legal/commercial limitations | no provider approval, no commercial approval, no scraping unless scoped | provider data quarantine/correction path |
| Order Execution | Order Execution Contract, Decision Support Compliance Review, Runtime Gate Boundary Contract | explicit operator authorization, broker write prevention, failure/rollback behavior | order-readiness evidence, compliance boundary report, operator authorization record | explicit Human Operator decision for any order-capable scope | no order execution, no broker write capability, no investment advice | order cancel/reversal/correction path |

## Explicit Non-Claims

This contract does not claim:

- runtime enforcement;
- automatic release acceptance;
- production readiness;
- investment readiness;
- order execution;
- broker import;
- dashboard expansion;
- replay or backtesting;
- outcome attribution;
- valuation automation;
- broker, provider or API integration;
- Event Ledger Runtime.

Any future claim in these areas requires a later explicit scope, accepted
contract, tests, evidence artifacts and Human Operator acceptance.
