# CIOS Instrument Master Architecture

## Purpose

Kernel ID: `KERNEL_INSTRUMENT_MASTER`.

The Instrument Master is the identity layer that must sit between source data
and ledger/replay/attribution systems. It defines how CIOS will later identify
financial instruments without relying on tickers, broker labels or provider IDs
as canonical truth.

The source of truth for the contract is
`docs/contracts/INSTRUMENT_MASTER_CONTRACT.md`.

## Architecture Role

The Instrument Master prepares CIOS for:

- controlled broker/provider mapping,
- future Portfolio Event Ledger references,
- corporate-action lineage,
- FX/multi-currency context,
- performance attribution,
- replay and outcome analysis.

It does not implement any of those runtime systems in this patch.

## Layer Model

1. Instrument Identity Contract: required fields, allowed values, evidence and
   conflict rules.
2. Instrument Master Registry: future machine-readable registry, currently only
   a template placeholder.
3. Broker / Provider Mapping: future source-specific alias layer.
4. Corporate Actions: future lifecycle and predecessor/successor handling.
5. Event Ledger Linkage: future transaction/holding reference to
   `canonical_instrument_id`.

## Data Flow

Target future flow:

`Source Registry -> Instrument Evidence -> Instrument Master -> Event Ledger -> Replay/Outcome`

Current patch state:

- Data Source Strategy and License Boundary exist.
- Instrument Master Contract exists.
- Instrument Master Template exists as template-only.
- No production registry, validator, broker mapping, event ledger, replay or
  outcome pipeline exists.

## Why This Precedes Broker Import And Event Ledger

Broker exports and provider feeds often use local symbols, venue-specific
labels or provider IDs. If those values become canonical too early, later
transactions, corporate actions and replay can attach to the wrong instrument.

The Event Ledger must eventually store event-time references to
`canonical_instrument_id`, not only a ticker or broker symbol. That requires
the identity model before ledger implementation.

## Prohibited Identity Shortcuts

- Ticker-only identity is prohibited.
- Name-only identity is prohibited.
- Broker-symbol-only identity is prohibited.
- Provider-ID-only identity is prohibited.
- ISIN-only identity is not universally sufficient because listings,
  share-class context and instrument type still matter.

## Relationship To Adjacent Kernels

- Data Source Strategy: governs source/provider boundaries and adapter rules.
- License Boundary: governs use/export rights, not identity truth.
- Data Freshness: shows whether source identity evidence is current; it does
  not prove identity.
- Broker Import: remains read-only and non-production until Instrument Master
  and Event Ledger contracts exist.
- Corporate Actions: future module will update lifecycle and predecessor /
  successor links.
- Portfolio Event Ledger: must reference canonical identity at event time.
- Replay / Outcome / Attribution: remain blocked until identity, ledger and
  time-aware snapshots are linked.

## Template Boundary

`docs/architecture/CIOS_INSTRUMENT_MASTER_TEMPLATE.yaml` is a template-only
artifact. It contains generic non-real entries and does not approve any real
instrument, broker mapping, provider mapping, data source or legal/commercial
use.

Existing portfolio, watchlist, scoring and benchmark configs remain operational
local inputs. They are not reinterpreted as a canonical Instrument Master by
this patch.

## Open Decisions

- final `canonical_instrument_id` generation policy,
- production registry storage format,
- instrument-registry validator implementation,
- broker/provider mapping record format,
- corporate-action event model,
- FX/multi-currency identity treatment,
- Event Ledger linkage contract.

Each hard-to-reverse decision needs ADR plus risk review.

## Next Patch Options

- Instrument Master Registry Template / Validation,
- Portfolio Event Ledger Contract,
- Broker Import Staging Contract,
- Corporate Actions Contract.

