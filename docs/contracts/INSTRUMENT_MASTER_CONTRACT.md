# Instrument Master Contract

## Contract Purpose

Kernel IDs: `KERNEL_INSTRUMENT_MASTER`,
`KERNEL_DATA_SOURCE_STRATEGY`, `KERNEL_PORTFOLIO_EVENT_LEDGER`,
`KERNEL_TIME_AWARE_REPLAY`, `KERNEL_RISK_CONTROL`.

Compound Income OS (CIOS) needs a canonical Instrument Master before production
broker import, Portfolio Event Ledger, corporate actions, FX/multi-currency,
performance attribution, replay or outcome work can safely merge data from
multiple sources.

This contract reduces identity risks from:

- ticker collisions,
- provider-ID mismatch,
- broker-symbol ambiguity,
- ISIN or share-class confusion,
- ETF-vs-stock confusion,
- currency or trading-venue context errors,
- historical symbol changes,
- corporate-action successor/predecessor drift,
- replay, attribution and outcome distortion.

It is a governance contract. It does not create a production database, runtime
matching engine or approved provider mapping.

## Scope

This contract defines:

- canonical instrument identity,
- accepted identifier classes,
- alias and symbol rules,
- identity confidence,
- review status,
- lifecycle status,
- provider/broker mapping boundary,
- provenance and evidence expectations,
- versioning and identity-change rules,
- sequencing rules for later implementation.

## Non-Scope

This contract does not implement:

- a production Instrument Master database,
- automatic online lookup,
- broker import,
- Portfolio Event Ledger,
- corporate-action processing,
- FX engine,
- pricing engine,
- valuation engine,
- recommendation engine,
- tax engine,
- legal or regulatory classification as fact.

## Definitions

- `instrument`: an economic asset or cash/currency object that may appear in a
  portfolio, watchlist, benchmark, transaction or report.
- `security`: a tradable financial instrument such as a stock, ETF, fund, bond
  or derivative.
- `issuer`: the legal entity or provider behind an instrument.
- `share_class`: a distinct class of an issuer or fund with separate economic,
  voting, currency, distribution or listing attributes.
- `listing`: an instrument's trading context on an exchange or venue.
- `exchange`: a regulated or recognized trading venue.
- `trading_venue`: exchange, broker venue or market context where a symbol is
  used.
- `ticker`: a market symbol within a listing or venue context.
- `broker_symbol`: symbol used by a broker; an alias, not a canonical ID.
- `provider_symbol`: symbol used by a data provider; an alias, not a canonical
  ID.
- `canonical_instrument_id`: stable CIOS-owned identifier for the economic
  instrument record.
- `instrument_identity_key`: the deterministic fields used to validate or
  derive a canonical identity candidate.
- `identifier`: ISIN, WKN, CUSIP, SEDOL, FIGI, LEI, MIC, exchange code,
  provider ID or broker ID when evidence exists.
- `alias`: historic or source-specific name, ticker or symbol mapped to an
  instrument or listing.
- `source_mapping`: mapping from a data source, broker or provider identifier
  to a canonical instrument candidate.
- `evidence_record`: file or review artifact supporting an identity claim.
- `identity_confidence`: confidence level for the current identity mapping.
- `lifecycle_status`: current state of the instrument identity.
- `corporate_action`: event such as split, merger, acquisition, liquidation,
  rename, share-class change or symbol change.
- `successor_instrument`: instrument that replaces or continues another
  instrument after a lifecycle event.
- `predecessor_instrument`: prior instrument linked to a successor.
- `active_instrument`: currently valid identity for new local references.
- `inactive_instrument`: identity retained for history but not used for new
  mapping without review.
- `tradable_listing`: venue-specific tradable symbol context.
- `economic_instrument`: economic exposure independent of one venue symbol.
- `portfolio_holding_reference`: future holding reference to a
  `canonical_instrument_id`.
- `event_ledger_reference`: future transaction/event reference to a
  `canonical_instrument_id` valid at event time.

## Canonical Identity Model

### 1. Economic Instrument

The Economic Instrument layer represents the economic exposure: stock, ETF,
fund, bond, cash/currency, crypto asset or other security. This layer owns the
`canonical_instrument_id`.

### 2. Listing / Trading Venue Context

Listings hold ticker, trading currency, MIC/exchange context and venue-specific
attributes. Multiple listings may point to one Economic Instrument, but the
listing context must remain visible.

### 3. Provider / Broker Mapping

Provider IDs, broker symbols and source aliases map source-specific records to
an Economic Instrument and, where needed, to a Listing. These mappings are not
canonical identity.

### 4. Portfolio Reference

Future holdings and transactions should reference `canonical_instrument_id`.
They may also store source alias and listing context for audit, but they must
not persist as ticker-only, name-only, broker-symbol-only or provider-ID-only
records.

Rules:

- Ticker alone is never canonical identity.
- ISIN alone can be useful but is not always sufficient for every instrument
  type or listing context.
- Broker symbols are aliases.
- Provider IDs are source mappings.
- Position records must not permanently rely only on name or ticker.

## Required Fields For Future Instrument Master Entries

Future registry entries must include:

- `canonical_instrument_id`
- `instrument_name`
- `instrument_type`
- `asset_class`
- `issuer_name`
- `primary_identifier_type`
- `primary_identifier_value`
- `identifiers`
- `listings`
- `broker_aliases`
- `provider_aliases`
- `currency`
- `domicile_or_country`
- `lifecycle_status`
- `identity_confidence`
- `review_status`
- `source_provenance`
- `evidence_files`
- `license_boundary_refs`
- `data_source_refs`
- `created_at`
- `updated_at`
- `effective_from`
- `effective_to`
- `predecessor_instrument_ids`
- `successor_instrument_ids`
- `known_limitations`
- `owner`
- `notes`

Optional fields may include:

- `isin`
- `wkn`
- `cusip`
- `sedol`
- `figi`
- `lei`
- `mic`
- `exchange_code`
- `trading_currency`
- `quote_currency`
- `base_currency`
- `fund_provider`
- `index_tracked`
- `distribution_policy`
- `share_class_currency`
- `accumulation_or_distribution`

## Allowed Values

`instrument_type`:

- `STOCK`
- `ETF`
- `FUND`
- `BOND`
- `CASH`
- `CURRENCY`
- `CRYPTO_ASSET`
- `DERIVATIVE`
- `OTHER_REVIEW_REQUIRED`
- `UNKNOWN_REVIEW_REQUIRED`

`asset_class`:

- `EQUITY`
- `FIXED_INCOME`
- `CASH_OR_CURRENCY`
- `CRYPTO`
- `MULTI_ASSET`
- `COMMODITY`
- `REAL_ESTATE`
- `DERIVATIVE`
- `OTHER_REVIEW_REQUIRED`
- `UNKNOWN_REVIEW_REQUIRED`

`lifecycle_status`:

- `ACTIVE`
- `INACTIVE`
- `DELISTED`
- `MERGED`
- `ACQUIRED`
- `LIQUIDATED`
- `RENAMED`
- `SYMBOL_CHANGED`
- `REVIEW_REQUIRED`
- `UNKNOWN`

`identity_confidence`:

- `HIGH`
- `MEDIUM`
- `LOW`
- `REVIEW_REQUIRED`
- `UNKNOWN`

`review_status`:

- `APPROVED_FOR_LOCAL_USE`
- `OPERATOR_REVIEW_REQUIRED`
- `EVIDENCE_REQUIRED`
- `CONFLICT_REVIEW_REQUIRED`
- `CORPORATE_ACTION_REVIEW_REQUIRED`
- `PROVIDER_MAPPING_REVIEW_REQUIRED`
- `BROKER_MAPPING_REVIEW_REQUIRED`
- `PROHIBITED`
- `UNKNOWN`

## Identity Rules

- `canonical_instrument_id` must be stable, deterministic and not
  provider-specific.
- Ticker-only identity is prohibited.
- Name-only identity is prohibited.
- Broker-symbol-only identity is prohibited.
- Provider-ID-only identity is prohibited.
- Conflicting primary identifiers require `REVIEW_REQUIRED`.
- Multiple listings may point to one Economic Instrument, but listing context
  must remain separate.
- Multiple share classes must not be silently merged.
- ETF/fund share classes must not be merged without evidence.
- Currency context must remain visible.
- Historic identifier or ticker changes must be versioned or retained as alias
  history, not overwritten.
- Corporate actions must not be silently folded into an existing identity.
- Manual merge or split decisions require evidence and operator review.

## Collision / Conflict Rules

| conflict | required status | rule |
| --- | --- | --- |
| same ticker, different exchanges | `CONFLICT_REVIEW_REQUIRED` | Do not merge without listing evidence. |
| same ticker, different countries | `CONFLICT_REVIEW_REQUIRED` | Country/venue context must be explicit. |
| same ISIN, different listings | `REVIEW_REQUIRED` | Economic identity may match, listing remains separate. |
| same name, different instruments | `CONFLICT_REVIEW_REQUIRED` | Name-only merge is prohibited. |
| same broker label, different ISIN | `BROKER_MAPPING_REVIEW_REQUIRED` | Broker alias must not decide identity. |
| providers disagree on identifiers | `PROVIDER_MAPPING_REVIEW_REQUIRED` | Source evidence required. |
| currency mismatch | `REVIEW_REQUIRED` | Trading/quote/base currency must be reviewed. |
| asset-class mismatch | `CONFLICT_REVIEW_REQUIRED` | No automatic correction. |
| instrument-type mismatch | `CONFLICT_REVIEW_REQUIRED` | No automatic correction. |
| ETF vs stock mismatch | `CONFLICT_REVIEW_REQUIRED` | Type conflict blocks merge. |
| active vs delisted mismatch | `CORPORATE_ACTION_REVIEW_REQUIRED` | Lifecycle review required. |

Every conflict requires evidence. Merge/split decisions require Human Operator
review and must remain traceable.

## Broker / Provider Mapping Boundary

Broker symbols and provider IDs are mappings, not canonical IDs.

Each future broker/provider mapping must include:

- `source_id`
- `provider_name`
- `provider_instrument_id` or `broker_symbol`
- `mapping_confidence`
- `mapping_review_status`
- `effective_from`
- `effective_to`
- `evidence_files`

Mapping conflicts must not be silently accepted. A production broker import
path remains blocked until both this Instrument Master contract and the
Portfolio Event Ledger contract exist.

## Relationship To Data Source Strategy / License Boundary

- Instrument identity needs provenance, but license boundary remains separate.
- Data Source Registry classifies sources; Instrument Master classifies
  instrument identity.
- Freshness evidence does not prove identity.
- License evidence does not prove identity.
- Provider mapping requires Source/License Boundary review.
- Public identifiers do not automatically become redistributable metadata.
- Paid/vendor raw data must not enter public handoffs without license review.

## Relationship To Data Freshness

Instrument Master entries may carry review/update timestamps. Freshness is
important for mapping confidence, but it is not identity evidence. Stale
instrument mappings must remain visible. Delistings, mergers and symbol changes
require review.

## Relationship To Corporate Actions

Corporate Actions are not implemented by this patch. The Instrument Master must
prepare for them through:

- predecessor/successor links,
- lifecycle status,
- `effective_from` and `effective_to`,
- review status.

No corporate-action processing is introduced here.

## Relationship To Portfolio Event Ledger

A future Event Ledger must not store only tickers. Transactions and holdings
should reference `canonical_instrument_id` and preserve source aliases for
audit. The ledger needs identity valid at the event timestamp. No Event Ledger
is implemented in this patch.

## Relationship To Replay / Outcome / Performance Attribution

Replay needs time-dependent instrument identity. Outcome attribution needs
stable instrument references. Backtesting and replay remain blocked until
Instrument Master, Event Ledger and snapshot/`as_of` rules exist. This patch
implements no replay, attribution, backtesting or performance-cause logic.

## Governance / Review Rules

Operator review is required when:

- identifiers conflict,
- ticker/name/broker/provider aliases are ambiguous,
- currency, venue or share-class context is missing,
- lifecycle status is unclear,
- corporate action links are needed,
- manual merge/split is proposed.

External review is required when source/provider identity data, license
boundary, public handoff or commercial use is unclear.

Merge or split is prohibited when evidence is missing, source terms are unknown
or the operator has not accepted the mapping. Such instruments must remain
`REVIEW_REQUIRED`, `EVIDENCE_REQUIRED` or `CONFLICT_REVIEW_REQUIRED`.

ADR required for:

- changing the `canonical_instrument_id` rule,
- introducing a production Instrument Master backend,
- adding automatic broker/provider mapping,
- adding production broker import,
- automating corporate actions,
- depending on provider-specific canonical IDs,
- commercially redistributing instrument data.

## Future Validation Expectations

Future validators should check:

- required fields,
- enum values,
- duplicate canonical IDs,
- ticker-only rejection,
- identifier conflicts,
- alias collisions,
- listing/currency mismatches,
- broker/provider mapping conflicts,
- lifecycle/effective-date consistency,
- evidence/provenance presence,
- handoff/private-data boundaries.

