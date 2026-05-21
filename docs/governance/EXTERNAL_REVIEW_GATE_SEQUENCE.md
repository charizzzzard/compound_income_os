# External Review Gate Sequence

This document defines conservative sequencing for future CIOS feature classes.
It is a governance standard, not feature readiness and not runtime enforcement.

The gate definitions are machine-readable in
`docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml`. The coverage vocabulary is
defined in `docs/governance/EXTERNAL_REVIEW_COVERAGE_STANDARD.md`.

## Before Instrument Master Expansion

Required gates:

- `INSTRUMENT_IDENTITY_AND_MAPPING_REVIEW`
- `DATA_CONFLICT_AND_PROVENANCE_REVIEW`
- `CROSS_PATCH_REGRESSION_REVIEW`

Rationale: Instrument expansion must not rely on ticker-only, broker-symbol-only
or provider-ID-only identity, and it must not reinterpret existing configs as a
canonical Instrument Master.

## Before Portfolio Event Ledger Runtime

Required gates:

- `PORTFOLIO_EVENT_LEDGER_RUNTIME_READINESS_REVIEW`
- `AS_OF_TEMPORAL_INTEGRITY_REVIEW`
- `RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW`
- `ADVERSARIAL_INPUT_AND_FAILURE_MODE_REVIEW`
- `CROSS_PATCH_REGRESSION_REVIEW`

Rationale: Template validation is not runtime event validation. Runtime ledger
work needs append-only semantics, correction/reversal handling, temporal
integrity, adversarial input coverage and explicit enforcement boundaries.

## Before Broker Import Staging

Required gates:

- `BROKER_IMPORT_STAGING_READINESS_REVIEW`
- `INSTRUMENT_IDENTITY_AND_MAPPING_REVIEW`
- `DATA_CONFLICT_AND_PROVENANCE_REVIEW`
- `LOCAL_SECURITY_AND_SECRET_HYGIENE_REVIEW`
- `CROSS_PATCH_REGRESSION_REVIEW`

Rationale: Existing read-only import, cost, tax and history modules are not a
Broker Import Staging Contract and must not be treated as production staging.

## Before Broker Import Production

Required gates:

- `BROKER_IMPORT_STAGING_READINESS_REVIEW`
- `PORTFOLIO_EVENT_LEDGER_RUNTIME_READINESS_REVIEW`
- `INSTRUMENT_IDENTITY_AND_MAPPING_REVIEW`
- `LOCAL_SECURITY_AND_SECRET_HYGIENE_REVIEW`
- `DECISION_SUPPORT_COMPLIANCE_REVIEW`
- `CLEAN_ROOM_REPRODUCTION_REVIEW`

Rationale: Production broker import is blocked until staging, identity, event,
privacy, compliance and reproduction evidence exist.

## Before Replay

Required gates:

- `AS_OF_TEMPORAL_INTEGRITY_REVIEW`
- `PORTFOLIO_EVENT_LEDGER_RUNTIME_READINESS_REVIEW`
- `CROSS_PATCH_REGRESSION_REVIEW`

Rationale: Replay requires accepted event history, snapshot/as_of semantics and
no hidden temporal imputation.

## Before Backtesting

Required gates:

- `AS_OF_TEMPORAL_INTEGRITY_REVIEW`
- `PORTFOLIO_EVENT_LEDGER_RUNTIME_READINESS_REVIEW`
- `SEMANTIC_DECISION_QUALITY_REVIEW`
- `CLEAN_ROOM_REPRODUCTION_REVIEW`

Rationale: Backtesting without point-in-time data, decision-state evidence and
replay foundations can create false precision.

## Before Outcome Attribution

Required gates:

- `PORTFOLIO_EVENT_LEDGER_RUNTIME_READINESS_REVIEW`
- `AS_OF_TEMPORAL_INTEGRITY_REVIEW`
- `SEMANTIC_DECISION_QUALITY_REVIEW`
- `DATA_CONFLICT_AND_PROVENANCE_REVIEW`

Rationale: Outcome attribution requires accepted decisions, accepted events,
source evidence, temporal integrity and reviewed semantics.

## Before Dashboard Expansion

Required gates:

- `OPERATOR_COMPREHENSION_REVIEW`
- `DASHBOARD_MISINTERPRETATION_REVIEW`
- `DECISION_SUPPORT_COMPLIANCE_REVIEW`
- `RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW`

Rationale: Dashboard surfaces must not make process state look like investment
advice, event acceptance, broker readiness or order instruction.

## Before Valuation Automation

Required gates:

- `SEMANTIC_DECISION_QUALITY_REVIEW`
- `AS_OF_TEMPORAL_INTEGRITY_REVIEW`
- `DATA_CONFLICT_AND_PROVENANCE_REVIEW`

Rationale: Valuation automation needs reviewed methodology, source provenance,
temporal consistency and clear uncertainty handling.

## Before Public Or Commercial Packaging

Required gates:

- `CLEAN_ROOM_REPRODUCTION_REVIEW`
- `LOCAL_SECURITY_AND_SECRET_HYGIENE_REVIEW`
- `DECISION_SUPPORT_COMPLIANCE_REVIEW`
- `OPERATOR_COMPREHENSION_REVIEW`
- `RELEASE_CI_ENVIRONMENT_PARITY_REVIEW`

Rationale: Public or commercial packaging must not include private/raw data,
must be reproducible from the packet, must keep local/CI validation semantics
visible, and must not imply legal, tax, commercial or investment approval.

## Before Major External Review Or Release Gate Claims

Required gates:

- `CLEAN_ROOM_REPRODUCTION_REVIEW`
- `CROSS_PATCH_REGRESSION_REVIEW`
- `RELEASE_CI_ENVIRONMENT_PARITY_REVIEW`
- `LOCAL_SECURITY_AND_SECRET_HYGIENE_REVIEW`

Rationale: Major external review and release-gate claims need reproducible
handoff evidence, cross-kernel regression visibility, environment parity and
secret-hygiene evidence. Recorded validation commands alone are not pass/fail
evidence.

## Non-Scope

This sequence does not implement any gate as runtime enforcement. It does not
authorize Broker Import, Event Ledger Runtime, Replay, Backtesting, Dashboard
Expansion, Valuation Automation, Outcome Attribution or public/commercial
packaging.
