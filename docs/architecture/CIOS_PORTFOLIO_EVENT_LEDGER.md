# CIOS Portfolio Event Ledger

## Architecture Role

Kernel IDs: `KERNEL_PORTFOLIO_EVENT_LEDGER`,
`KERNEL_INSTRUMENT_MASTER`, `KERNEL_TIME_AWARE_REPLAY`,
`KERNEL_DATA_SOURCE_STRATEGY`, `KERNEL_RISK_CONTROL`.

The Portfolio Event Ledger is the future audit spine for portfolio history in
Compound Income OS. It is not implemented as a runtime database in this patch.
This document explains where the ledger belongs and why it must exist before
broker-import hardening, replay, performance attribution, outcome attribution
or corporate-action automation.

## Layer Model

1. Event Ledger Contract:
   `docs/contracts/PORTFOLIO_EVENT_LEDGER_CONTRACT.md` defines event identity,
   required fields, allowed values, append-only rules and review boundaries.
2. Event Ledger Template Validation Preflight:
   `src.portfolio_event_ledger_validation` validates the template-only YAML,
   enum sets, required fields, event-type matrix and neutral placeholder
   boundaries. It is manual/read-only and does not accept events.
3. Future Event Ledger Registry / Store:
   not implemented; will require validators, persistence rules and release
   gates.
4. Future Broker Import Staging:
   will normalize broker rows into reviewable event candidates, not directly
   accepted ledger facts.
5. Future Corporate Actions:
   will connect instrument lifecycle changes to ledger events after a separate
   Corporate Actions Contract.
6. Future Time-Aware Replay:
   will reconstruct state from accepted events, snapshots and `as_of` rules.
7. Future Outcome Attribution:
   will link accepted decisions to later accepted events and replayable state.

## Intended Data Flow

```text
Broker/Manual Source
  -> Source Registry / License Boundary
  -> Instrument Master
  -> Portfolio Event Ledger
  -> Replay / Performance / Outcome Review
```

The source layer answers where the data came from and whether it can be used.
The Instrument Master answers what instrument an event references. The Event
Ledger answers what happened, when, in which account, in which currency and
with which evidence.

The current validation preflight sits before any future event-store runtime. It
checks the template shape and conservative boundaries only: no real broker
events, no private portfolio history, no event acceptance, no tax approval, no
FX conversion and no replay readiness can be inferred from a passing template.

## Why Before Broker Import, Replay And Attribution

Production broker import without a ledger contract would risk accepting broker
rows as canonical facts before identity, correction, reversal, currency and
evidence rules are fixed. Replay without accepted events would reconstruct
history from incomplete snapshots. Outcome attribution without an event ledger
would link decisions to outcomes without auditable portfolio state.

## Append-Only / Correction / Reversal

Accepted event facts should not be silently edited. A future ledger should
represent corrections, reversals and supersessions as explicit events or linked
records with evidence and operator review. This preserves auditability and
keeps historical replay possible.

## Open Decisions

The following remain intentionally open:

- production event-store backend,
- event ID generation algorithm,
- event duplicate detection,
- broker import staging schema,
- runtime correction/reversal validator,
- FX-rate source policy,
- Corporate Actions Contract,
- Time-Aware Replay Contract,
- public/commercial handling of derived event summaries.

Each hard-to-reverse choice requires ADR plus risk review.

## Sequencing

- No production broker import before Instrument Master Contract, Portfolio
  Event Ledger Contract, broker-import staging contract, validators, review
  workflow and tests.
- No replay before Event Ledger plus snapshot/`as_of` rules.
- No performance attribution before Event Ledger plus Time-Aware Replay.
- No outcome attribution before decision journal, Event Ledger and Time-Aware
  Replay are linked.
- No corporate-action automation before Corporate Actions Contract.
- No implicit FX conversion before FX/Multi-Currency Contract.

## Next Patches

The current implementation-oriented follow-up is the read-only Event Ledger
Template Validation Preflight. Later follow-ups should remain contract-first:

- Broker Import Staging Contract,
- Time-Aware Replay Contract,
- Corporate Actions Contract.
