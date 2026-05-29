# Valuation Methodology Proposal Template

## Purpose

This template defines how a future valuation methodology may be proposed for
CIOS before any DCF work, valuation automation, scoring integration, ranking
integration, provider/API integration or investment recommendation logic is
implemented.

The template is proposal-only governance evidence. It supports deterministic,
local-first, reviewable methodology design. It is not a runtime engine, not a
formula implementation, not release acceptance and not investment advice.

The Human Operator remains final authority for any later acceptance decision.

## Methodology Identity

Every future proposal must identify itself without using personal names as
canonical ownership fields:

```yaml
methodology_id: ""
methodology_name: ""
methodology_family: ""
proposal_status: "PROPOSED_ONLY"
owner_role: ""
reviewer_role: ""
contract_reference: "docs/contracts/VALUATION_METHODOLOGY_PROPOSAL_TEMPLATE.md"
related_boundary_contract: "docs/contracts/VALUATION_METHODOLOGY_BOUNDARY_CONTRACT.md"
version: ""
decision_record_reference: ""
```

Allowed `proposal_status` values are:

- `PROPOSED_ONLY`
- `REVIEW_REQUIRED`
- `REJECTED`
- `SUPERSEDED`
- `ACCEPTED_FOR_DESIGN_ONLY`

`ACCEPTED_FOR_DESIGN_ONLY` does not mean runtime use. Proposal acceptance does
not imply runtime enforcement.

## Scope Boundary

A proposal may define what a methodology intends to evaluate, such as a future
historical multiple comparison, normalized owner earnings / FCF yield view,
dividend support view, DCF candidate, scenario view or sensitivity view.

A proposal must also define what it must not evaluate. At minimum it must not
evaluate order execution, broker actions, tax advice, legal approval,
commercial approval, product readiness, production readiness or investment
readiness.

The proposal must explicitly state:

- it is not investment advice;
- it is not a direct buy/sell recommendation;
- it is not an order instruction;
- proposal acceptance does not imply runtime enforcement;
- proposal acceptance does not authorize scoring integration, ranking
  integration, provider/API integration or valuation automation.

## Required Input Data

Every proposal must list:

- required data fields;
- optional data fields;
- source data evidence;
- data provenance requirements;
- freshness/staleness requirements;
- `as_of_date` or snapshot requirements;
- source license or usage boundary assumptions;
- handling for missing, stale, unknown, conflicting or blocked data.

Missing, stale, unknown, conflicting or blocked data must remain visible in any
future review artifact. The proposal must not silently impute missing values,
must not silently overwrite accepted facts and must not upgrade degraded
evidence to `OK` without explicit evidence and Human Operator acceptance.

## Calculation Semantics

Calculation sections are placeholders only. They may describe proposed
semantics, assumptions, inputs and expected outputs, but they must not contain a
runtime valuation formula.

Each calculation placeholder must be marked:

```yaml
calculation_status: "PROPOSED_ONLY"
runtime_status: "NOT_RUNTIME_ENFORCED"
formula_implementation_status: "NOT_IMPLEMENTED"
```

No real DCF formula, valuation formula, scoring formula change or ranking
formula change is implemented by this template.

Any later methodology implementation must define:

- accepted formula semantics;
- accepted input domains and invalid-value handling;
- uncertainty and sensitivity semantics;
- no silent imputation rules;
- no silent overwrite rules;
- deterministic reproduction path;
- tests required before runtime use.

## Review Gates

Before any future runtime use, a methodology proposal requires:

- methodology review required;
- data provenance review required;
- temporal integrity review required;
- semantic decision-quality review required;
- adversarial input / failure-mode review required;
- operator wording review required;
- test coverage required before runtime use;
- Human Operator acceptance required.

These gates are evidence and review prerequisites. They are not automatic
release acceptance and they do not create runtime enforcement.

## Output Semantics

Allowed proposal output states are:

- `PROPOSED_ONLY`
- `REVIEW_REQUIRED`
- `NOT_EVALUATED`
- `INSUFFICIENT_DATA`
- `BLOCKED`
- `REJECTED`

Output states must not include direct buy/sell recommendations. They must not
claim product readiness, production readiness or investment readiness.

Any future operator-facing output must preserve uncertainty, data-quality
limits and the Human Operator decision boundary.

## Traceability

Every proposal must link to:

- source data evidence;
- data provenance evidence;
- temporal integrity evidence;
- methodology contract/version;
- tests required before runtime use;
- review findings;
- later Human Operator acceptance decision, if any.

Traceability links are evidence pointers only. They do not implement a
methodology and do not authorize runtime use.

## Explicit Non-Scope

This template does not implement:

- DCF engine;
- valuation automation;
- scoring integration;
- ranking integration;
- provider/API integration;
- scraping or crawling;
- broker import;
- order execution;
- buy/sell automation;
- investment advice;
- replay/backtesting/simulation;
- outcome attribution;
- product readiness;
- production readiness;
- investment readiness.

It also does not change existing valuation formulas, scoring formulas, ranking
logic, portfolio rules, report outputs or buy/sell semantics.

## Proposal Acceptance Boundary

Completing this template can only create review evidence. It cannot promote a
methodology to runtime use.

Runtime use would require a separate accepted methodology contract,
implementation patch, tests, evidence artifacts, rollback/correction path,
operator-facing wording boundary and explicit Human Operator acceptance.
