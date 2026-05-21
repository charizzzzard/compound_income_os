# Data Source License Boundary Contract

## Contract Purpose

Kernel IDs: `KERNEL_DATA_LICENSE_BOUNDARY`,
`KERNEL_DATA_SOURCE_STRATEGY`, `KERNEL_TRACEABILITY`,
`KERNEL_HANDOFF_GOVERNANCE`, `KERNEL_PRODUCT_COMMERCIAL_BOUNDARY`.

This contract defines minimum metadata, classifications, review statuses and
hard rules for future CIOS data sources. It is a governance contract only. It
does not approve any real provider, grant legal rights or implement runtime
enforcement.

## Definitions

- `source`: a specific origin of data used by CIOS.
- `provider`: the person, organization or system that makes a source available.
- `adapter`: code or process that reads a source into CIOS boundaries.
- `raw_data`: data as received before CIOS normalization.
- `normalized_data`: data transformed into a CIOS contract shape.
- `derived_data`: CIOS output computed from one or more sources.
- `evidence_record`: a traceable record supporting a fact or data point.
- `snapshot`: a time-bound source capture with explicit date metadata.
- `provenance`: metadata that records origin, lineage and review state.
- `license_boundary`: documented limits on use, display, export and
  redistribution.
- `redistribution`: sharing raw or derived data outside the local operator
  context.
- `commercial_use`: use in a product, service, sale, subscription, public
  package or commercial workflow.
- `public_handoff`: an external review bundle or public package.
- `private_local_use`: local use by the human operator on private files.

## Required Source Metadata Fields

Future registries must include these fields:

- `source_id`
- `source_name`
- `source_type`
- `provider_name`
- `provider_url_or_reference`
- `access_method`
- `license_classification`
- `usage_scope`
- `redistribution_allowed`
- `commercial_use_allowed`
- `attribution_required`
- `raw_data_handoff_allowed`
- `derived_data_handoff_allowed`
- `contains_personal_data`
- `contains_broker_data`
- `contains_paid_data`
- `requires_operator_review`
- `requires_external_review`
- `as_of_date_required`
- `snapshot_required`
- `freshness_policy_id`
- `provenance_required`
- `adapter_required`
- `current_status`
- `evidence_files`
- `license_evidence_files`
- `provenance_evidence_files`
- `freshness_evidence_files`
- `review_evidence_files`
- `known_limitations`
- `owner`
- `review_status`

`evidence_files` remains as a backward-compatible aggregate field. New
templates and future registries should also split evidence by purpose:

- `license_evidence_files`: source terms, license text, operator/legal review
  notes or explicit fixture classification evidence.
- `provenance_evidence_files`: files that show where the data came from or how
  it was derived.
- `freshness_evidence_files`: files that support currentness/staleness only.
  Freshness evidence is not license evidence.
- `review_evidence_files`: operator, external, legal or commercial review notes
  that justify the current review status.

## Allowed Classification Values

- `OFFICIAL_PUBLIC`
- `PUBLIC_COMPANY_FILINGS`
- `USER_PRIVATE_EXPORT`
- `MANUAL_OPERATOR_INPUT`
- `PAID_VENDOR`
- `WEB_SOURCE_REVIEW_REQUIRED`
- `COMMUNITY_DATASET_REVIEW_REQUIRED`
- `INTERNAL_DERIVED`
- `TEST_FIXTURE`
- `UNKNOWN_REVIEW_REQUIRED`

## Allowed Usage Scopes

- `PRIVATE_LOCAL_ONLY`
- `INTERNAL_REVIEW`
- `TEST_ONLY`
- `PUBLIC_DOC_REFERENCE`
- `PUBLIC_HANDOFF_METADATA_ONLY`
- `PUBLIC_HANDOFF_DERIVED_ALLOWED`
- `DASHBOARD_LOCAL_ALLOWED`
- `COMMERCIAL_REVIEW_REQUIRED`
- `PROHIBITED`

## Required Review Statuses

- `APPROVED_FOR_PRIVATE_LOCAL_USE`
- `APPROVED_FOR_TEST_FIXTURES`
- `APPROVED_FOR_PUBLIC_METADATA_ONLY`
- `APPROVED_FOR_DERIVED_HANDOFF`
- `COMMERCIAL_REVIEW_REQUIRED`
- `LEGAL_REVIEW_REQUIRED`
- `OPERATOR_REVIEW_REQUIRED`
- `PROHIBITED`
- `UNKNOWN`

## Hard Rules

- Unknown license means not approved for commercial use or public
  redistribution.
- File existence is not license evidence.
- Freshness evidence is not license evidence.
- Public availability is not redistribution permission.
- Paid data must never be bundled into public handoffs unless explicitly
  reviewed and allowed.
- Broker/user-private exports must remain private unless explicitly sanitized
  and allowed.
- Derived outputs must carry provenance and license boundary metadata.
- No silent source substitution.
- No silent overwrite of accepted facts.
- Public handoffs must not bundle private broker exports, paid raw vendor data,
  credentials, secrets or restricted raw datasets.

## Registry Validation Preflight

`src.data_source_registry_validation` is the minimal read-only preflight for
`docs/architecture/CIOS_DATA_SOURCE_REGISTRY_TEMPLATE.yaml`.

The preflight:

- validates that the registry remains `template_only: true`,
- checks required fields from this contract,
- checks allowed `license_classification`, `usage_scope` and `review_status`
  values,
- keeps license, provenance, freshness and review evidence semantically
  separate,
- rejects risky public, commercial, paid, broker, personal-data and
  redistribution combinations.

It does not approve providers, implement runtime enforcement, contact external
services, provide legal advice or make CIOS commercial-ready.

Conservative validation rules include:

- unknown license cannot claim public handoff, dashboard, commercial or
  redistribution use,
- paid, broker or personal raw data cannot be allowed in public handoff,
- commercial use requires legal/commercial review status and explicit license
  evidence,
- redistribution requires explicit license evidence,
- freshness evidence cannot satisfy license evidence,
- provider-specific source classes require an adapter boundary,
- non-test sources require provenance,
- time-sensitive sources require `as_of_date` and snapshot semantics.

## Future Output Expectations

Future implementations should produce or maintain:

- machine-readable source registry,
- source-level evidence,
- source-level review status,
- linkage to freshness policy,
- linkage to adapter boundary,
- linkage to handoff boundary,
- source-level provenance and known limitations.

## Review Requirements

ADR required for:

- selecting a paid vendor as canonical source,
- adding provider-specific runtime adapter,
- changing public/private handoff boundary,
- allowing commercial use of source-derived outputs,
- allowing redistribution of derived data,
- adopting broker import as production path,
- changing source precedence rules,
- changing accepted source/license classification values.

External legal/commercial review required for commercial use, redistribution,
paid-vendor bundling, public product packaging or any unclear source terms.

## Non-Scope

This contract does not provide:

- legal advice,
- provider-specific legal conclusion,
- runtime enforcement implementation,
- actual source approval except synthetic test-fixture patterns and already
  documented repo-internal metadata references.
