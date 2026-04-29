# LLM and Codex Operating Policy

## Core Rule

Deterministic Python remains the source of truth for Compound Income OS. LLMs and
Codex assist the repo; they do not decide.

## Allowed LLM Uses

LLMs may:

- review architecture or contracts
- summarize repo artifacts
- red-team assumptions
- draft documentation text
- propose review questions
- help shape scoped Codex tasks

LLMs must not:

- invent fundamentals
- create final investment decisions
- produce structured financial data without human approval
- silently fill missing data
- act as a runtime dependency in the core pipeline
- create broker/order instructions

## Codex Rules

Codex may implement only scoped, repo-first patches against stable contracts.

Codex must:

- inspect repo reality before editing
- preserve unrelated dirty files
- avoid private/raw/generated commits unless explicitly scoped
- keep validation commands and commit status visible
- keep patches minimal and evidence-based
- avoid runtime financial logic changes under documentation tasks

Codex must not:

- change scoring formulas unless explicitly requested
- change scoring weights unless explicitly requested
- touch unrelated dirty files
- implement broker write access
- implement live trading or order execution
- apply KPI values unless the task explicitly requests a reviewed apply step

## Cost-Aware Use

- prefer small scoped prompts
- avoid unnecessary full handoffs
- avoid mass LLM commentary by default
- materialize generated architecture/review outputs as repo artifacts only when
  they become canonical
- keep raw review transcripts and ZIP bundles as source material, not canonical
  docs
