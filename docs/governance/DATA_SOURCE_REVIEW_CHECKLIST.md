# Data Source Review Checklist

## Purpose

Kernel IDs: `KERNEL_DATA_SOURCE_STRATEGY`,
`KERNEL_DATA_LICENSE_BOUNDARY`, `KERNEL_RISK_CONTROL`.

Use this checklist before adding a new CIOS data source, adapter, handoff
allowance or commercial/product use case. It is not legal advice.

## Checklist

### Source Identity

- Source ID assigned.
- Source name and provider name recorded.
- Source type classified under
  `docs/contracts/DATA_SOURCE_LICENSE_BOUNDARY_CONTRACT.md`.
- Source owner identified.

### Provider Terms / License Evidence

- Provider URL or reference recorded.
- License or terms evidence file recorded.
- Unknown license defaults to review-required and no redistribution.

### Access Method

- Access method documented.
- Runtime adapter boundary identified where needed.
- No scraping or API access added without explicit review.

### Personal / Broker / Private Data Boundary

- Contains personal data: yes/no.
- Contains broker data: yes/no.
- Raw private data handoff allowed: normally no.
- Sanitization requirement documented.

### Paid Data Boundary

- Contains paid data: yes/no.
- Paid raw data is excluded from public handoffs unless explicitly reviewed.
- Commercial use is not approved by default.

### Redistribution Boundary

- Raw redistribution allowed: yes/no/evidence.
- Derived redistribution allowed: yes/no/evidence.
- Public availability is not treated as redistribution permission.

### Commercial-Use Boundary

- Commercial use allowed: yes/no/evidence.
- Legal/commercial review required where unclear.
- No product readiness inferred from this checklist.

### Attribution Requirements

- Attribution required: yes/no.
- Required attribution text/source reference recorded.

### Snapshot / As-Of Requirements

- `as_of_date` required: yes/no.
- Snapshot required: yes/no.
- Point-in-time replay implications documented.

### Freshness Policy Mapping

- Freshness policy ID assigned or deferred.
- Data Freshness status is not treated as license approval.

### Adapter Requirement

- Adapter required: yes/no.
- Provider-specific logic isolated from core scoring/ranking/reporting.

### Handoff / Export Boundary

- Raw data handoff allowed: yes/no.
- Derived data handoff allowed: yes/no.
- Handoff scan/allowlist implications documented.

### Operator Acceptance

- Human operator review required: yes/no.
- External review required: yes/no.
- ADR required: yes/no.

## Decision

Choose exactly one decision:

- `APPROVE_PRIVATE_LOCAL`
- `APPROVE_TEST_FIXTURE`
- `APPROVE_PUBLIC_METADATA_ONLY`
- `REQUIRE_LEGAL_REVIEW`
- `REQUIRE_COMMERCIAL_REVIEW`
- `REJECT_OR_PROHIBIT`

Document the evidence files and unresolved limitations before acceptance.
