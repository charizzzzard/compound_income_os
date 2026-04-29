# Meta Review Loop Protocol

This protocol defines how future Compound Income OS architecture reviews are run
without uncontrolled expansion.

## Review Purpose

Architecture review is appropriate when a change affects system boundaries,
producer sequence, data contracts, policy, replay, handoff, or human decision
authority.

It is not required for small bug fixes within an already stable contract.

## Roles

GPT/Claude reviews may be used to red-team architecture, find blind spots,
compare alternatives and draft improved contracts.

Codex may execute only after the contract is stable enough to define:

- scope
- inputs
- outputs
- non-goals
- guardrails
- validation commands
- commit boundaries

The operator remains strategy owner and final decision maker.

## Required Outputs

Every review loop must produce at least one material artifact:

- architecture decision
- contract
- policy
- backlog item
- explicit deferral
- validation criterion

Review outputs that do not become artifacts, backlog items or explicit deferrals
are not considered adopted.

## Execution Gate

Codex execution is allowed only when:

- the repo reality is inspected first
- the contract is stable
- the patch is minimal and repo-first
- source/test/docs boundaries are clear
- private/raw/generated commit exclusions are explicit
- validation commands are known

Codex must not turn a review prompt into runtime logic unless the task explicitly
requests implementation.

## Anti-Expansion Rules

- Do not add simulation before Decision Capture and replay/accounting foundations
  exist.
- Do not add outcome attribution before decisions are captured.
- Do not add runtime LLM commentary to the core pipeline.
- Do not expand thesis schemas before a minimum viable research note is proven
  useful.
- Do not treat a backlog item as current behavior.

## Review Cycle

1. Gather repo reality and source artifacts.
2. Ask for independent critique only when architecture risk is material.
3. Synthesize conflicts and accepted decisions.
4. Convert decisions into canonical docs/contracts/backlog.
5. Defer non-essential work explicitly.
6. Execute with Codex only after the contract is stable.
7. Validate and commit the canonical artifact, not raw transcripts.
