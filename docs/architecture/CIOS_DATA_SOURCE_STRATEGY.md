# CIOS Data Source Strategy

## Purpose

Kernel IDs: `KERNEL_DATA_SOURCE_STRATEGY`, `KERNEL_DATA_LICENSE_BOUNDARY`,
`KERNEL_DATA_FRESHNESS`, `KERNEL_HANDOFF_GOVERNANCE`,
`KERNEL_PRODUCT_COMMERCIAL_BOUNDARY`.

This strategy defines how Compound Income OS (CIOS) may classify, review and
later integrate data sources without creating provider lock-in, license drift,
privacy leakage or false commercial readiness.

It is a governance and architecture strategy. It does not approve a provider,
implement an API, scrape a website, buy data or make a legal conclusion.

## Scope

In scope:

- source classes and default usage posture
- provider-agnostic integration boundaries
- license and usage review gates
- relationship to provenance, evidence, freshness, handoff and commercial
  boundaries
- sequencing rules for future source integrations

Out of scope:

- actual provider selection
- API implementation
- scraping implementation
- broker parser production hardening
- legal advice
- commercial readiness claim
- pricing, trading, backtesting, replay or outcome attribution

## Principles

- Local-first data use: private local inputs remain local unless explicitly
  reviewed for export.
- Evidence-first data handling: facts need source artifacts and provenance.
- Provider-agnostic architecture: provider-specific assumptions stay behind
  adapters.
- Adapter boundary rule: runtime integrations need explicit source adapters.
- No silent source substitution: sample, stale or alternate source data must
  not replace expected data silently.
- No silent overwrite of accepted facts: reviewed source facts need explicit
  supersession or append-only treatment.
- No hidden stale/missing/unknown data: freshness state must remain visible.
- Explicit provenance required: derived data must point back to source class and
  evidence.
- Explicit `as_of_date` / snapshot handling for time-sensitive data.
- License classification before commercial or product use.
- Private/raw data must not leak into public handoffs.

## Data Source Typology

| source_type | examples | default posture |
| --- | --- | --- |
| public/open official data | official statistical or regulator datasets | review terms before redistribution |
| public company filings | issuer or regulator filings | metadata/reference may be public; raw redistribution needs review |
| broker/exported user data | user account exports, broker PDFs | private local only |
| manually curated operator data | personal master, watchlist, reviews | private local or sanitized derived use |
| paid/licensed vendor data | commercial financial data | prohibited for handoff/redistribution until reviewed |
| web pages / scraped-like sources | HTML pages, unofficial endpoints | prohibited until review |
| community/third-party datasets | GitHub/Kaggle/community files | review-required |
| synthetic/test fixtures | invented test rows | test only, handoff allowed if clearly synthetic |
| derived/processed internal outputs | CIOS-generated summaries | allowed only within source/license boundary metadata |

## Approved Conceptual Use Classes

- `LOCAL_PRIVATE_USE`
- `LOCAL_REVIEW_ONLY`
- `TEST_FIXTURE_ONLY`
- `PUBLIC_HANDOFF_ALLOWED`
- `PUBLIC_DOC_REFERENCE_ALLOWED`
- `DASHBOARD_ALLOWED`
- `COMMERCIAL_REVIEW_REQUIRED`
- `REDISTRIBUTION_PROHIBITED`
- `PROHIBITED_UNTIL_REVIEW`

## Data Source Decision Matrix

| source_type | private_local_use | public_handoff | dashboard_use | commercial_use | redistribution | required_controls | default_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| official public data | allowed after source review | metadata or derived only after review | local allowed with provenance/freshness | review required | prohibited unless license allows | license evidence, attribution, snapshot | `COMMERCIAL_REVIEW_REQUIRED` |
| public company filings | allowed after source review | metadata/reference or derived only after review | local allowed with provenance/freshness | review required | prohibited unless license allows | filing reference, as_of date, source URL/reference | `COMMERCIAL_REVIEW_REQUIRED` |
| user private broker export | allowed locally | prohibited except sanitized metadata | local allowed only | prohibited until review | prohibited | privacy boundary, no raw handoff, operator ownership | `PRIVATE_LOCAL_ONLY` |
| manual operator input | allowed locally | sanitized derived only | local allowed | review required | prohibited unless explicitly allowed | provenance, owner, review status | `INTERNAL_REVIEW` |
| paid vendor data | allowed only under contract terms | prohibited unless explicitly licensed | local only if terms allow | legal/commercial review required | prohibited by default | vendor terms, proof of rights, no raw handoff | `LEGAL_REVIEW_REQUIRED` |
| web source / scraped-like data | review required | prohibited | prohibited until review | prohibited until review | prohibited | access method review, terms review, adapter boundary | `PROHIBITED_UNTIL_REVIEW` |
| community dataset | review required | metadata only after review | review required | legal/commercial review required | prohibited unless license allows | license file, attribution, provenance | `COMMERCIAL_REVIEW_REQUIRED` |
| internal derived output | allowed | allowed only when source boundary permits | local allowed | review required | depends on source boundary | source lineage, license inheritance, handoff scan | `PUBLIC_HANDOFF_METADATA_ONLY` |
| test fixture | allowed for tests | allowed if synthetic and non-private | allowed in demos/tests | not production data | allowed only as synthetic fixture | label as synthetic, no real personal data | `TEST_FIXTURE_ONLY` |

## Provider-Agnostic Integration Model

Future source integration should pass through these boundaries:

1. Source Registry
2. Source Adapter
3. Raw Snapshot
4. Normalized Dataset
5. Evidence Record
6. Freshness Signal
7. Provenance Metadata
8. License Classification
9. Review Status

Provider-specific code belongs in adapters. Core scoring, ranking, decision
quality, freshness and dashboard surfaces should read normalized artifacts and
metadata, not provider-specific runtime APIs.

## Relationship To Other Kernels

- Data Freshness answers: is the data current enough for intended use?
- License Boundary answers: is the data allowed to be used, transformed,
  displayed, exported or redistributed?
- Provenance answers: where did the data come from?
- Evidence answers: what artifact supports the fact?

These are related but not interchangeable:

- Fresh data can still be license-prohibited.
- Licensed data can still be stale.
- Public data can still be unsuitable for redistribution.
- Derived data still needs provenance.

Relationships:

- Data Freshness: source metadata should map to a freshness policy.
- Instrument Master: stable identifiers are required before merging
  broker/provider data.
- Portfolio Event Ledger: required before production broker import or
  attribution.
- Broker Import Staging: remains read-only and local until identity/event
  contracts exist.
- Time-Aware Replay: requires source snapshots and `as_of` semantics.
- Dashboard Operator Surface: may display source status but must not hide
  private/license constraints.
- Handoff Governance: public handoffs may include code, docs, configs, tests and
  sanitized derived metadata, not restricted raw data.
- Commercial/Product Boundary: source-license review is prerequisite but not
  sufficient for commercial readiness.

## Sequencing Rules

- No provider-specific dependency without adapter boundary.
- No commercial use before license boundary review.
- No dashboard use before provenance and freshness semantics.
- No replay/backtesting use before snapshot and `as_of` semantics.
- No broker-derived production path before Instrument Master and Event Ledger
  contracts.
- No redistribution of raw/provider data without explicit license review.
- No provider-specific source precedence hardcoded in core logic.
- No public handoff of raw private, broker, paid vendor or restricted source
  data without explicit review.

## Decision Rules

A new source requires an ADR when it:

- selects a paid vendor as canonical source,
- adds a provider-specific runtime adapter,
- changes public/private handoff boundary,
- allows commercial use of source-derived outputs,
- allows redistribution of derived data,
- adopts broker import as production path,
- changes source precedence rules,
- changes accepted source/license classification values.

Human Operator acceptance is required for any source used with private data,
broker exports, manual operator inputs or commercial implications.

External legal/commercial review is required before commercial use,
redistribution, paid-vendor bundling or public product packaging. This strategy
does not provide legal advice or a legal conclusion.

Sources must remain private-only when they contain user broker exports, personal
holdings, private raw files, credentials, paid vendor raw data or unknown
license terms.

## Path-Dependency Review

Data-source choices that can create lock-in:

- canonical provider selection,
- provider-specific identifiers in normalized data,
- implicit source precedence,
- dashboard fields tied to provider-specific payloads,
- source-derived outputs without license inheritance metadata,
- replay snapshots that omit provider/source version.

Reversible design requires adapters, normalized contracts, source IDs, snapshot
metadata, license classifications and migration notes.

## Non-Scope

This strategy does not:

- approve a provider,
- implement API access,
- implement scraping,
- approve paid data,
- approve commercial use,
- approve redistribution,
- provide legal advice,
- make CIOS commercial-ready.
