# Portfolio Event Ledger Contract

## Contract Purpose

Kernel IDs: `KERNEL_PORTFOLIO_EVENT_LEDGER`,
`KERNEL_INSTRUMENT_MASTER`, `KERNEL_DATA_SOURCE_STRATEGY`,
`KERNEL_DATA_FRESHNESS`, `KERNEL_TIME_AWARE_REPLAY`,
`KERNEL_RISK_CONTROL`.

Compound Income OS (CIOS) needs a Portfolio Event Ledger before production
broker import, performance attribution, outcome attribution, time-aware replay,
corporate actions, FX/multi-currency processing or dashboard expansion can
rely on portfolio history.

This contract reduces risks from:

- non-auditable portfolio history,
- silent overwrite of transactions,
- broker-import ambiguity,
- ticker-only event references,
- cashflow, dividend, fee and tax confusion,
- FX and multi-currency errors,
- corporate-action distortion,
- performance or outcome attribution without a time base,
- replay without snapshot and event evidence.

It is a governance contract. It does not create a production event store,
runtime ledger engine, broker parser or performance/outcome calculation.

## Scope

This contract defines:

- event types,
- required fields,
- event identity,
- instrument references,
- portfolio and account context,
- event time semantics,
- `as_of_date`, `recorded_at` and `effective_date` rules,
- amount, quantity and currency rules,
- provenance and evidence requirements,
- append-only, correction, reversal and supersession rules,
- broker/provider boundary,
- relationship to Instrument Master, Data Source Strategy, License Boundary,
  Data Freshness, Corporate Actions, FX, Replay and Outcome Attribution.

## Non-Scope

This contract does not implement:

- a production Event Ledger database,
- broker parser,
- API integration,
- automatic transaction classification,
- corporate-actions processing,
- FX engine,
- tax engine,
- performance engine,
- replay engine,
- outcome attribution,
- dashboard,
- trading or order execution,
- investment advice.

## Definitions

- `portfolio_event`: a dated portfolio, cash, instrument, broker, fee, tax,
  transfer, FX or corporate-action record that may affect portfolio state or
  audit history.
- `ledger_event`: normalized event record intended for a future append-only
  ledger.
- `event_id`: CIOS-owned stable event identifier.
- `event_type`: normalized type such as `BUY`, `SELL`, `DIVIDEND` or
  `FX_CONVERSION`.
- `event_time`: timestamp or date representing when the event is considered to
  occur for ledger ordering.
- `trade_date`: date a trade was executed, if applicable and evidenced.
- `settlement_date`: date cash/instrument settlement occurs, if applicable and
  evidenced.
- `effective_date`: date the event takes economic effect.
- `recorded_at`: date/time CIOS or the operator recorded the event.
- `as_of_date`: date through which the event source claims to be current.
- `account`: local account or broker account context.
- `portfolio`: local portfolio scope that owns the event.
- `broker/source account`: source-specific account identifier or alias.
- `canonical_instrument_id`: Instrument Master identifier for instrument
  events.
- `quantity`: event quantity.
- `gross_amount`: amount before fees, taxes or withholding where available.
- `net_amount`: cash amount after visible fees/taxes where available.
- `fee`: explicit fee amount, not silently hidden in net value if separable.
- `tax`: explicit tax or withholding amount, not silently hidden if separable.
- `cashflow`: cash movement distinct from a trade.
- `dividend`: distribution from an instrument.
- `interest`: cash or instrument income that is not a dividend.
- `deposit`: cash inflow.
- `withdrawal`: cash outflow.
- `buy`: acquisition event.
- `sell`: disposal event.
- `transfer`: movement between accounts without automatic gain/loss
  interpretation.
- `corporate_action`: split, merger, spinoff, return of capital or similar
  instrument lifecycle event.
- `FX rate`: exchange rate used for a currency conversion or base-currency
  representation.
- `base currency`: portfolio reporting currency.
- `transaction currency`: currency of the event transaction.
- `quote currency`: currency used by a quote or FX rate.
- `source document`: broker export, statement, manual operator file or other
  source artifact.
- `evidence record`: file or review artifact supporting an event claim.
- `provenance`: source chain that explains where the event came from.
- `correction event`: event that corrects a prior event without overwriting it.
- `reversal event`: event that reverses a prior event.
- `superseded event`: prior event replaced by a later superseding event.
- `append-only ledger`: ledger discipline where accepted facts are not silently
  mutated in place.

## Event Identity Model

`event_id` must be stable, deterministic or uniquely generated and must not be
broker-only. `broker_transaction_id` or `source_event_id` is a source mapping,
not sufficient canonical event identity.

Event identity must consider source, account, event type, event date and
evidence. It must not be derived only from mutable fields such as amount, note,
display name or current ticker. Duplicate detection needs later dedicated
rules.

Ledger entries must not reference instruments only by ticker, name, broker
symbol or provider ID. Instrument events should reference
`canonical_instrument_id` once the Instrument Master is operable. Until then,
events with unresolved identity must remain review-required and must not be
treated as accepted canonical history.

## Required Fields For Future Ledger Events

Future ledger events must include:

- `event_id`
- `event_type`
- `event_status`
- `portfolio_id`
- `account_id`
- `broker_or_source_account_id`
- `canonical_instrument_id`
- `instrument_identity_status`
- `event_time`
- `trade_date`
- `settlement_date`
- `effective_date`
- `recorded_at`
- `as_of_date`
- `quantity`
- `quantity_unit`
- `gross_amount`
- `net_amount`
- `fee_amount`
- `tax_amount`
- `transaction_currency`
- `cash_currency`
- `base_currency`
- `fx_rate`
- `fx_rate_source`
- `fx_rate_as_of_date`
- `source_id`
- `source_event_id`
- `source_document_ref`
- `source_row_ref`
- `source_provenance`
- `evidence_files`
- `license_boundary_refs`
- `data_freshness_refs`
- `correction_of_event_id`
- `reversal_of_event_id`
- `supersedes_event_id`
- `correction_reason`
- `reversal_reason`
- `supersession_reason`
- `correction_review_status`
- `reversal_review_status`
- `supersession_review_status`
- `correction_evidence_files`
- `reversal_evidence_files`
- `supersession_evidence_files`
- `predecessor_event_ids`
- `successor_event_ids`
- `validation_status`
- `review_status`
- `created_at`
- `updated_at`
- `owner`
- `known_limitations`
- `notes`
- `fx_from_currency`
- `fx_to_currency`
- `fx_rate_convention`
- `fx_rate_direction`
- `fx_rate_includes_spread`
- `fx_rate_review_status`
- `source_account_id`
- `target_account_id`
- `transfer_direction`
- `transfer_pair_id`
- `transfer_review_status`

Nullable and `NOT_APPLICABLE` rules:

- `canonical_instrument_id` can be `NOT_APPLICABLE` only for cash-only events.
- `fee_amount` and `tax_amount` can be `0` when the source supports that value
  or `UNKNOWN`/review-required when not evidenced.
- `settlement_date` can be `UNKNOWN` or review-required, but must not be
  invented.
- `fx_rate` can be `NOT_APPLICABLE` only when `transaction_currency` equals
  `base_currency` and no conversion is represented.
- `source_event_id` can be `UNKNOWN` for manual operator input, but the event
  must then carry a review-required status.
- The template must publish machine-readable `required_by_event_type`,
  `nullable_by_event_type`, `not_applicable_by_event_type` and
  `review_required_by_event_type` matrices before any future event-store
  implementation uses it.
- `ACCEPTED_FOR_LOCAL_USE` is only a future local review status. It is not a
  legal approval, tax approval, commercial approval, investment approval or
  public-handoff approval for private broker or portfolio events.

## Allowed Values

`event_type`:

- `BUY`
- `SELL`
- `DIVIDEND`
- `INTEREST`
- `DEPOSIT`
- `WITHDRAWAL`
- `FEE`
- `TAX`
- `TRANSFER_IN`
- `TRANSFER_OUT`
- `CASH_ADJUSTMENT`
- `FX_CONVERSION`
- `SPLIT`
- `MERGER`
- `SPINOFF`
- `RETURN_OF_CAPITAL`
- `DISTRIBUTION`
- `CORPORATE_ACTION_REVIEW_REQUIRED`
- `MANUAL_ADJUSTMENT_REVIEW_REQUIRED`
- `UNKNOWN_REVIEW_REQUIRED`

`event_status`:

- `DRAFT`
- `IMPORTED_UNREVIEWED`
- `OPERATOR_REVIEW_REQUIRED`
- `VALIDATED`
- `ACCEPTED`
- `SUPERSEDED`
- `CORRECTED`
- `REVERSED`
- `REJECTED`
- `UNKNOWN`

`validation_status`:

- `VALID`
- `WARNING`
- `REVIEW_REQUIRED`
- `ERROR`
- `NOT_EVALUATED`

`review_status`:

- `OPERATOR_REVIEW_REQUIRED`
- `EVIDENCE_REQUIRED`
- `INSTRUMENT_REVIEW_REQUIRED`
- `CASH_REVIEW_REQUIRED`
- `FX_REVIEW_REQUIRED`
- `CORPORATE_ACTION_REVIEW_REQUIRED`
- `TAX_REVIEW_REQUIRED`
- `BROKER_MAPPING_REVIEW_REQUIRED`
- `ACCEPTED_FOR_LOCAL_USE`
- `REJECTED`
- `UNKNOWN`

`quantity_unit`:

- `SHARES`
- `UNITS`
- `CURRENCY`
- `CONTRACTS`
- `NOT_APPLICABLE`
- `UNKNOWN_REVIEW_REQUIRED`

## Hard Ledger Rules

- Append-only preference: accepted events are not silently overwritten.
- Corrections must be modeled as correction, reversal or superseding events.
- No event may reference an instrument only through ticker, name,
  broker-symbol or provider ID.
- Broker transaction IDs are source mappings, not canonical event identity.
- Events without sufficient instrument identity must remain `REVIEW_REQUIRED`.
- Events with unknown currency must not be `VALID`.
- FX conversions need visible rate, source and `as_of_date`, or
  `FX_REVIEW_REQUIRED`.
- Fees and taxes must not be hidden in `net_amount` when separately available.
- Cashflows must remain distinguishable from trades.
- Dividends, taxes, fees and corporate actions must not be silently merged.
- Corporate actions must not be automatically processed by this contract.
- Production broker import must not start before Instrument Master and Event
  Ledger contracts exist.
- Even with those contracts and the current Broker Import Staging preflight,
  production broker import remains blocked until a staging-to-ledger promotion
  contract, review workflow, accepted fixtures and runtime tests exist.
- Performance attribution must not occur before Event Ledger and Time-Aware
  Replay.
- Replay must not occur before Event Ledger and snapshot/`as_of` rules.

## Event-Type Specific Rules

### BUY / SELL

- `canonical_instrument_id` is required.
- `quantity` is required.
- `trade_date` is required or `REVIEW_REQUIRED`.
- `transaction_currency` is required.
- gross, net, fee and tax semantics must remain visible.
- broker/source provenance is required.

### DIVIDEND / INTEREST / DISTRIBUTION

- Income event types must remain separate.
- Instrument reference is required except for cash interest.
- withholding tax or `tax_amount` must be visible when present.
- `cash_currency` is required.
- ex-date or pay-date fields may be used only when supported by evidence.

### DEPOSIT / WITHDRAWAL

- These are cash-only events.
- `canonical_instrument_id` can be `NOT_APPLICABLE`.
- `account_id` and `cash_currency` are required.
- source and evidence are required.

### FEE / TAX

- Fee and tax events must not be netting-only when separate evidence exists.
- Linkage to a related event is optional, but if known it should use
  predecessor/reference fields.
- Tax events with unknown tax type require review.

### TRANSFER_IN / TRANSFER_OUT

- Instrument and cash transfers must be distinguishable.
- No automatic gain/loss interpretation is allowed.
- source and target account boundaries must remain visible through
  `source_account_id`, `target_account_id`, `transfer_direction`,
  `transfer_pair_id` and `transfer_review_status` where applicable.

### FX_CONVERSION

- From/to currency, amount, rate, source and `as_of_date` must be visible.
- `fx_from_currency`, `fx_to_currency`, `fx_rate_convention`,
  `fx_rate_direction`, `fx_rate_includes_spread` and
  `fx_rate_review_status` must keep rate direction and review state explicit.
- No implicit FX rate may be invented.

### Corporate Action Types

`SPLIT`, `MERGER`, `SPINOFF` and `RETURN_OF_CAPITAL` remain review-required
until a Corporate Actions Contract exists. This contract defines event shape
only and does not process corporate actions.

## Correction / Reversal / Supersession Semantics

An accepted event must not be deleted or overwritten silently. Corrections,
reversals and supersessions require:

- `correction_of_event_id`, `reversal_of_event_id` or `supersedes_event_id`,
- predecessor/successor chain where relevant,
- structured reason in `correction_reason`, `reversal_reason` or
  `supersession_reason`,
- structured review status in `correction_review_status`,
  `reversal_review_status` or `supersession_review_status`,
- evidence in `correction_evidence_files`, `reversal_evidence_files` or
  `supersession_evidence_files`,
- operator review,
- audit trail.

Accepted facts cannot be silently overwritten.

## Template Validation Preflight

`src.portfolio_event_ledger_validation` is the current read-only template
preflight. It validates only the local
`docs/architecture/CIOS_PORTFOLIO_EVENT_LEDGER_TEMPLATE.yaml` structure and
does not create or approve ledger events.

The preflight must enforce:

- `template_only: true`,
- required contract fields in the template and every template entry,
- allowed enum values,
- event-type required/nullable/not-applicable/review-required matrices,
- neutral placeholders only; no real broker, portfolio, tax, dividend or FX
  data,
- no `ACCEPTED`, `VALIDATED`, `VALID` or `ACCEPTED_FOR_LOCAL_USE` template
  entries,
- structured correction/reversal/supersession rules,
- explicit FX direction/convention or `FX_REVIEW_REQUIRED`,
- explicit transfer account boundary or transfer review requirement.

This preflight is not a production Event Ledger, broker import staging layer,
runtime enforcement, tax calculation, legal/commercial approval, performance
engine, replay engine or outcome-attribution module.

## Broker / Source Mapping Boundary

Broker exports, broker statements, manual operator rows and future provider
records are sources. They can provide `source_event_id`, `source_document_ref`,
`source_row_ref` and provenance, but they do not by themselves approve event
identity, instrument identity, legal use, public handoff or commercial use.

Broker import remains read-only and non-production until staging, validation,
review workflow and test contracts exist. No broker write path or order
execution is authorized by this contract.

## Relationship To Instrument Master

The Event Ledger references `canonical_instrument_id`; the Instrument Master
solves identity, while the Event Ledger solves time-ordered event history.
Instrument mapping review must be possible before event acceptance.
Ticker-only ledgers are prohibited. Corporate actions require linkage between
Instrument Master lifecycle state and ledger events.

## Relationship To Data Source Strategy / License Boundary

- Broker/raw data remains private unless explicitly reviewed and allowed.
- Source Registry and License Boundary classify sources and usage boundaries.
- Event Ledger must not infer license approval.
- Public handoff must not include private broker events.
- Derived or sanitized summaries need provenance and handoff-boundary review.
- License evidence is not event evidence, and event evidence is not license
  approval.

## Relationship To Data Freshness

Event data can carry `as_of_date`, `recorded_at` and source freshness signals.
Freshness is not event correctness. Stale source data must not be silently
accepted. Missing event dates remain review-required or unknown; they must not
be filled silently.

## Relationship To FX / Multi-Currency

`transaction_currency`, `cash_currency` and `base_currency` must stay separate.
`fx_rate`, `fx_rate_source` and `fx_rate_as_of_date` must be visible when a
conversion is represented. No implicit FX conversion is allowed. Multi-currency
performance remains future work.

## Relationship To Corporate Actions

A Corporate Actions Contract is still missing. The ledger must be able to
represent corporate-action event candidates, but processing is blocked until a
future contract and validators exist. Instrument predecessor/successor links
prepare later review, not automatic processing.

## Relationship To Replay / Outcome / Performance Attribution

The Event Ledger is a prerequisite, not an implementation. Replay requires an
event ledger, snapshots and `as_of` semantics. Outcome Attribution requires
accepted decisions, accepted events, market data and replay. This patch
implements no performance calculation, outcome attribution, replay, simulation
or backtesting.

## Governance / Review Rules

Operator review is required when:

- source provenance is incomplete,
- instrument identity is missing or unresolved,
- currency or FX data is missing,
- fee/tax separation is unclear,
- event type is ambiguous,
- broker/source mapping conflicts,
- a correction, reversal or supersession is proposed,
- corporate action handling is needed.

External review is required when data source/license boundaries, public
handoff, commercial use, broker-import staging or event identity rules change.

An event must not be accepted when required identity, currency, time or evidence
fields are missing and no explicit review disposition exists. An event may be
rejected when evidence contradicts it, source terms prohibit use, or operator
review does not accept the mapping.

ADR required for:

- production Event Ledger backend,
- production broker-import path,
- automatic transaction classification,
- event-ID generation rule,
- correction/reversal semantic changes,
- corporate-actions automation,
- canonical FX-rate source,
- performance or outcome attribution,
- public or commercial redistribution of event data.

## Future Validation Expectations

Future validators should check:

- template-only invariant,
- required fields,
- enum values,
- required/nullable/not-applicable matrix consistency,
- event_id uniqueness,
- duplicate transaction detection,
- ticker-only rejection,
- missing `canonical_instrument_id`,
- FX direction/convention consistency,
- transfer source/target account boundaries,
- fee/tax/net-amount consistency,
- structured correction/reversal/supersession chains,
- source provenance,
- broker/source mapping,
- no private/raw broker events in public handoffs,
- handoff/private-data boundary.
