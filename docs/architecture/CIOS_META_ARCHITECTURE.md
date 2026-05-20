# CIOS Meta Architecture

## Purpose

This document defines the meta-governance layers above CIOS implementation
work. It does not prescribe every future feature. It defines the control system
that lets future features evolve safely.

## Meta Layers

| layer | name | purpose | primary evidence |
| --- | --- | --- | --- |
| L0 | System Purpose / Constitution | Define what CIOS is and is not. | `docs/governance/CIOS_SYSTEM_CONSTITUTION.md` |
| L1 | Operating Model / Authority Model | Define roles, authority and acceptance. | `docs/governance/CIOS_OPERATING_MODEL.md` |
| L2 | Management System | Define patch, review, release and monthly loops. | Operating model, `docs/CODEX_TASKS/POST_ITERATION_QA.md` |
| L3 | Lifecycle Model | Define how kernels move from gap to operable. | `docs/architecture/CIOS_MATURITY_MODEL.yaml` |
| L4 | Risk & Control Framework | Define risk categories, controls and gates. | `docs/governance/CIOS_RISK_AND_CONTROL_FRAMEWORK.md` |
| L5 | Architecture Governance | Define kernels, contracts, Stage-DAG and known gaps. | architecture docs and contracts |
| L6 | Engineering Disciplines | Define deterministic code, tests, configs and handoffs. | `src/`, `tests/`, configs and handoff docs |
| L7 | Implementation | Implement local read-only producers and reports. | committed source modules |
| L8 | Operation & Outcome | Run local workflows, capture decisions and later outcomes. | manifests, reports, decision journal, future outcome evidence |

## Engineering Disciplines Under Meta Governance

Engineering disciplines such as deterministic Python, stdlib-first modules,
CSV/JSON/Markdown contracts, unit tests, manifests, artifact indexes and
handoff validation sit below the constitution and operating model. They are
implementation disciplines, not authority sources by themselves.

## Domain Kernels Under Architecture Governance

Domain kernels such as Data Freshness, Decision Quality, Instrument Master,
Portfolio Event Ledger, Time-Aware Replay and Dashboard Operator Surface must
map to contracts, tests and known gaps. Kernel implementation may be phased, but
status must remain conservative.

## Releases And Handoffs As Evidence

Releases and handoffs are evidence artifacts. They package the current repo
state, validation outputs, metadata and checksums for review. They do not
override committed source files or human acceptance.

## Why This Meta Layer Exists

The meta layer prevents premature lock-in. It fixes identity, authority,
traceability, risk controls and sequencing rules while keeping future providers,
dashboards, ledgers, replay systems and product boundaries open.

This meta architecture enables safe evolution; it is not a feature-complete
architecture and not a product plan.
