# CIOS Traceability Standard

## Purpose

This standard defines the minimum traceability expected for CIOS patches,
contracts, outputs and releases. It is designed to keep future growth linked to
explicit kernels, requirements, gaps and controls.

## Traceability Chain

The target chain is:

`Requirement -> Contract -> Config -> Code -> Test -> Output -> Release -> Decision -> Outcome`

CIOS does not yet implement the complete chain for every domain. Where later
links do not exist, the gap must remain visible.

## Patch Mapping Rule

Every non-trivial patch must map to at least one of:

- kernel
- requirement
- known gap
- risk control
- release gate
- data boundary
- product boundary

No major feature may be added without traceability to a kernel or accepted
requirement.

## Minimum Future Traceability Fields

Future traceability registries or manifests should use these fields:

| field | purpose |
| --- | --- |
| `artifact_id` | stable artifact identifier |
| `kernel_id` | one or more CIOS kernel IDs |
| `requirement_id` | accepted requirement or gap ID |
| `related_contracts` | contract documents |
| `related_configs` | config files |
| `related_code` | source modules |
| `related_tests` | tests or validation commands |
| `related_outputs` | produced artifacts or reports |
| `related_release` | release/handoff identifier |
| `known_gaps` | unresolved known gaps |
| `owner` | human or process owner |
| `review_status` | proposed, reviewed, accepted, rejected or deferred |

## Kernel IDs

Stable kernel IDs for governance mapping include:

- `KERNEL_META_GOVERNANCE`
- `KERNEL_SYSTEM_CONSTITUTION`
- `KERNEL_OPERATING_MODEL`
- `KERNEL_RISK_CONTROL`
- `KERNEL_TRACEABILITY`
- `KERNEL_RELEASE_ENGINEERING`
- `KERNEL_HANDOFF_GOVERNANCE`
- `KERNEL_DATA_SOURCE_STRATEGY`
- `KERNEL_DATA_FRESHNESS`
- `KERNEL_INSTRUMENT_MASTER`
- `KERNEL_PORTFOLIO_EVENT_LEDGER`
- `KERNEL_TIME_AWARE_REPLAY`
- `KERNEL_DASHBOARD_OPERATOR_SURFACE`
- `KERNEL_PRODUCT_COMMERCIAL_BOUNDARY`

## Evidence Rules

- Evidence files must exist before they are cited as implemented evidence.
- Missing evidence should be represented as `KNOWN_GAP`, `NOT_STARTED` or
  `REVIEW_REQUIRED`, not inferred.
- Tests are evidence of behavior, not proof of investment correctness.
- Handoff packages are review evidence, not final authority without human
  acceptance.
- Generated outputs should not be committed unless explicitly scoped.
