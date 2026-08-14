# LLM and Codex Operating Policy

## Core Rule

Deterministic Python remains the source of truth for Compound Income OS. LLMs and
Codex assist the repo; they do not decide.

Historical LLM/Codex investment-skill evaluation must not be presented as
evidence of future LLM forecast ability because later events may already be
present in model parameters. Incremental LLM research value is measured
primarily forward-only against human-locked, contemporaneous claims. Historical
data may still support suitable deterministic quantitative research.

## Allowed LLM Uses

LLMs may:

- review architecture or contracts
- summarize repo artifacts
- red-team assumptions
- draft documentation text
- propose review questions
- help shape scoped Codex tasks
- compare handoff metadata against included repo evidence
- identify missing-data and provenance risks without filling the gaps
- propose falsifiable forward claims and resolution candidates for human review

LLMs must not:

- invent fundamentals
- create final investment decisions
- produce structured financial data without human approval
- silently fill missing data
- act as a runtime dependency in the core pipeline
- create broker/order instructions
- materialize KPI values without a reviewed apply path
- override deterministic Python artifacts, processed CSVs or validated reports

## Codex Rules

Codex may implement only scoped, repo-first patches against stable contracts.

Codex must:

- inspect repo reality before editing
- preserve unrelated dirty files
- avoid private/raw/generated commits unless explicitly scoped
- keep validation commands and commit status visible
- keep patches minimal and evidence-based
- avoid runtime financial logic changes under documentation tasks
- distinguish tracked HEAD reality, dirty/untracked worktree observations and
  roadmap statements
- run available cheap validation or clearly state what was not run

Codex must not:

- change scoring formulas unless explicitly requested
- change scoring weights unless explicitly requested
- touch unrelated dirty files
- implement broker write access
- implement live trading or order execution
- apply KPI values unless the task explicitly requests a reviewed apply step
- add runtime LLM dependencies to the deterministic core pipeline
- make or record final investment decisions on behalf of the operator
- lock falsification triggers, confirm trigger resolutions or promote policy on
  behalf of the operator

## Cost-Aware Use

- prefer small scoped prompts
- avoid unnecessary full handoffs
- avoid mass LLM commentary by default
- materialize generated architecture/review outputs as repo artifacts only when
  they become canonical
- keep raw review transcripts and ZIP bundles as source material, not canonical
  docs
- prefer repo-local deterministic checks before external LLM review
- use external LLMs for bounded review questions, not continuous runtime
  operation
