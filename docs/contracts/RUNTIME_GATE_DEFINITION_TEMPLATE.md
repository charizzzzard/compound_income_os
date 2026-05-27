# Runtime Gate Definition Template

## Purpose

This template standardizes how future runtime-sensitive gates must be proposed
before any CIOS check can move from `documentation_only` or `review_evidence`
toward `runtime_relevant_candidate` or a future `runtime_enforced` state.

Filling out this template does not make a gate runtime_enforced. Runtime
enforced behavior requires a separate future implementation, tests, evidence
artifacts and explicit Human Operator acceptance.

This template rejects automatic release acceptance. It does not grant product
readiness, production readiness, investment readiness, investment advice,
broker import, order execution, dashboard expansion, replay, backtesting,
outcome attribution, valuation automation, API integration, scraping or runtime
LLM agent behavior.

## Required Fields

Every future runtime gate proposal must define the following fields:

| field | required meaning |
| --- | --- |
| `gate_id` | Stable uppercase identifier for the proposed gate. |
| `gate_name` | Human-readable gate name. |
| `gate_classification` | One of `documentation_only`, `review_evidence`, `runtime_relevant_candidate`, `future_runtime_enforced`. |
| `owner_surface` | Repo surface, module, contract or operator workflow responsible for the gate. |
| `trigger_condition` | Exact condition that causes the gate to be evaluated. |
| `runtime_surface_impacted` | Runtime, report, handoff, dashboard or operator surface affected; use `NOT_APPLICABLE` if none. |
| `input_artifacts` | Required inputs, with repo-relative paths where possible. |
| `output_artifacts` | Deterministic outputs, with repo-relative paths where possible. |
| `failure_modes` | What can fail, become stale, be missing, be unknown or be not applicable. |
| `severity_semantics` | Meaning of PASS, WARN, FAIL, NOT_AVAILABLE and any domain-specific states. |
| `blocking_behavior` | Whether the gate blocks review, runtime-sensitive work or only produces evidence. |
| `override_policy` | Whether a Human Operator override is allowed, how it is recorded and what it cannot override. |
| `rollback_or_correction_path` | How an accepted state can be reversed, corrected or superseded. |
| `evidence_required` | Evidence artifacts required before the gate result can be reviewed. |
| `tests_required` | Unit, integration, fixture, adversarial or reproduction tests required before promotion. |
| `operator_acceptance_required` | Explicit Human Operator decision required; default must be `yes` for runtime-sensitive gates. |
| `release_acceptance_semantics` | Must state that the gate cannot automatically accept a release. |
| `non_scope` | Explicit non-claims and forbidden inferences. |
| `promotion_prerequisites` | Requirements before changing classification to `runtime_relevant_candidate` or future `runtime_enforced`. |
| `demotion_or_retraction_conditions` | Conditions that return the gate to review-only or require correction. |

Allowed `gate_classification` values:

- `documentation_only`
- `review_evidence`
- `runtime_relevant_candidate`
- `future_runtime_enforced`

`future_runtime_enforced` is only a proposal classification. It is not runtime
enforcement until a later accepted implementation proves enforcement behavior.

## Template

```yaml
gate_id: ""
gate_name: ""
gate_classification: "documentation_only"
owner_surface: ""
trigger_condition: ""
runtime_surface_impacted: "NOT_APPLICABLE"
input_artifacts: []
output_artifacts: []
failure_modes:
  missing: ""
  stale: ""
  unknown: ""
  failed: ""
  not_applicable: ""
severity_semantics:
  PASS: ""
  WARN: ""
  FAIL: ""
  NOT_AVAILABLE: ""
blocking_behavior: ""
override_policy:
  allowed: false
  operator_record_required: true
  cannot_override:
    - automatic_release_acceptance
    - investment_advice_boundary
    - order_execution_boundary
rollback_or_correction_path: ""
evidence_required: []
tests_required: []
operator_acceptance_required: true
release_acceptance_semantics: "No automatic release acceptance. Human Operator remains final acceptance authority."
non_scope:
  - no runtime enforcement by template alone
  - no automatic release acceptance
  - no product readiness
  - no production readiness
  - no investment readiness
  - no investment advice
  - no buy/sell recommendation changes
  - no broker import
  - no order execution
  - no dashboard expansion
  - no replay, backtesting or outcome attribution
  - no valuation automation
promotion_prerequisites:
  - accepted canonical contract section
  - deterministic evidence artifact
  - tests covering positive, negative, missing, stale and unknown states
  - failure and severity semantics
  - override policy
  - rollback_or_correction path
  - privacy/evidence boundary when private, broker, provider or user data is affected
  - explicit Human Operator acceptance
demotion_or_retraction_conditions:
  - stale or missing evidence
  - failed reproduction
  - changed runtime surface without updated tests
  - unresolved privacy or provenance finding
  - operator rejection or superseding decision
```

## Hard Requirements

- Filling out this template does not make a gate runtime_enforced.
- Runtime enforced behavior requires a separate future implementation, tests,
  evidence artifacts and explicit Human Operator acceptance.
- No gate may automatically accept a release.
- Human Operator remains final acceptance authority.
- Missing, stale, unknown, failed and not-applicable data must remain visible.
- No silent imputation.
- No silent overwrite of accepted facts.
- Product readiness, production readiness and investment readiness must not be
  inferred from this template.
- The template must not introduce investment advice, buy/sell recommendation
  changes, broker import, order execution, dashboard expansion, replay,
  backtesting, outcome attribution, valuation automation, API integration,
  scraping or runtime LLM agent behavior.

## Review Use

Future proposals should copy the template block into a dedicated contract or
review artifact. Reviewers must classify the result as evidence until a later
accepted implementation changes the classification under
`docs/contracts/RUNTIME_GATE_BOUNDARY_CONTRACT.md`.
