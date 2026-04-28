# Documentation Maintenance

This repo treats documentation as part of the patch contract. Every patch that
adds or changes a workflow must either update the relevant docs or state
`DOCS_NOT_REQUIRED` with a short rationale in the patch report.

## Required Checks

- New source module: add or update `docs/MODULE_CONTRACTS.md`, or document why the module is temporary/local-only.
- New user-facing workflow stage: mention it in `README.md` if operators are expected to run it.
- New strategic workflow or roadmap change: update `docs/CONTEXT_AND_ROADMAP.md`.
- New generated artifact: document the output contract or classify it as temporary/regeneratable in the patch report.
- New handoff/export behavior: update `docs/HANDOFF_CONTRACT.md`.
- New website/mockup/reference material: update the website README and keep source/reference material separate from production source.
- New private/raw/local-only artifact visible in `git status`: document that it is not for commit.

## SEC Workflow Guardrails

The SEC-derived KPI workflow is review-gated. CompanyFacts snapshots, approved
facts, derived KPI proposals, evidence proposals, reviewed evidence apply,
closure impact, period-selection review, concept diagnostics, alias review,
human alias approval input, and approved alias map generation must not mutate raw
masters or scores. The approved alias map remains inactive for period selection
until a later explicit patch.

## Consolidation Rule

Before consolidation commits, run the docs drift checklist in
`docs/CODEX_TASKS/DOCS_DRIFT_CHECKLIST.md` and generate the docs drift report.
Warnings may be accepted for later review, but they must be visible.
