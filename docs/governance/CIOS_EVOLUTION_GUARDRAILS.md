# CIOS Evolution Guardrails

## Purpose

These guardrails protect future optionality. They define how CIOS may grow
without locking the system into premature providers, data models, dashboards,
commercial claims or automated decisions.

## Path-Dependency Controls

- Prefer contracts before runtime for P0 kernels.
- Prefer adapter boundaries before provider-specific code.
- Prefer append-only records for ledger-like facts.
- Prefer explicit `as_of_date` and snapshot semantics for time-sensitive data.
- Prefer schema versions before migrations become necessary.
- Prefer reversible patches over hard-to-reverse platform commitments.

## Strategic Optionality Principles

- Keep data sources provider-agnostic until a license and adapter review exists.
- Keep investment policy separate from scoring implementation.
- Keep dashboard surfaces read-only until core data contracts are stable.
- Keep replay and outcome attribution separate from performance reporting.
- Keep commercial packaging separate from local private operator workflows.

## Anti-Lock-In Rules

- No provider-specific data dependency without adapter boundary and license
  classification.
- No broker import production path before Instrument Master and Portfolio Event
  Ledger contracts exist.
- No valuation automation before methodology contract and evidence requirements
  exist.
- No runtime LLM behavior before authority, audit, reproducibility and
  failure-mode controls exist.
- No commercial use before license-boundary and product-boundary review.

## Sequencing Rules

- No broker import production path before Instrument Master + Event Ledger
  Contract.
- No performance attribution before Event Ledger + Time-Aware Replay.
- No backtesting before `as_of` / snapshot / replay semantics.
- No dashboard expansion before core data quality and operator-surface
  contracts.
- No commercial packaging before data license and product boundary review.
- No automated decision/autonomy before authority and regulatory review.
- No provider-specific data dependency without adapter boundary and license
  classification.
- No valuation automation before methodology contract and evidence
  requirements.
- No outcome attribution before decision journal, event ledger and time-aware
  replay are linked.
- No runtime LLM behavior before authority, audit, reproducibility and
  failure-mode controls exist.

## Architecture Rules

- P0 kernel runtime changes require a contract first.
- Ledger-like facts should be append-only or explicitly superseded.
- Time-sensitive data needs explicit `as_of_date`, `data_date` or documented
  freshness evidence.
- New schemas should include a schema or contract version where practical.
- Migration and recovery paths must be documented for irreversible changes.
- Dashboard work must not introduce new financial logic.
- Backtesting, simulation and Monte Carlo remain deferred until replay and
  outcome foundations exist.

## ADR Requirement

An ADR is required for irreversible or hard-to-reverse decisions, including:

- provider lock-in,
- database/platform lock-in,
- broker/API write paths,
- data license assumptions,
- runtime LLM authority,
- schema migrations that break existing artifacts,
- commercial packaging boundaries,
- automated decision behavior.

## Escape Hatch

Any future architectural constraint may be revised only through documented ADR,
risk review and migration plan. A convenience patch is not enough to overturn
this baseline.
