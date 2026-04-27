# Website Private Preview Route Matrix QA

## Executive Summary

- Private preview QA status: `PASS`
- Routes total: `7`
- Routes pass/review/blocked: `7` / `0` / `0`
- CTAs invalid: `0`
- Main routes screenshot covered: `True`

## Route Matrix

| Route | Status | Reason codes |
|---|---:|---|
| `/` | `PASS` | `ROUTE_OK` |
| `/workflow` | `PASS` | `ROUTE_OK` |
| `/evidence` | `PASS` | `ROUTE_OK` |
| `/portfolio` | `PASS` | `ROUTE_OK` |
| `/dashboard` | `PASS` | `ROUTE_OK` |
| `/manifesto` | `PASS` | `ROUTE_OK` |
| `/about` | `PASS` | `ABOUT_ALIAS_TO_MANIFESTO` |

## CTA Matrix

| Source | CTA | Target type | Status |
|---|---|---:|---:|
| `/` | Read a sample monthly report | `ANCHOR` | `PASS` |
| `/` | See the workflow | `INTERNAL_ROUTE` | `PASS` |
| `/` | Read the manifesto | `INTERNAL_ROUTE` | `PASS` |
| `/workflow` | See the evidence layer | `INTERNAL_ROUTE` | `PASS` |
| `/workflow` | Read a sample monthly report | `ANCHOR` | `PASS` |
| `/evidence` | Read a sample monthly report | `ANCHOR` | `PASS` |
| `/evidence` | See the portfolio model | `INTERNAL_ROUTE` | `PASS` |
| `/portfolio` | Open local dashboard | `INTERNAL_ROUTE` | `PASS` |
| `/dashboard` | Private preview status | `INTERNAL_ROUTE` | `PASS` |
| `/manifesto` | View the workflow | `INTERNAL_ROUTE` | `PASS` |
| `/manifesto` | Request private preview | `PENDING_DISABLED` | `PASS` |
| `/manifesto` | Request setup | `PENDING_DISABLED` | `PASS` |
| `/manifesto` | See the workflow | `INTERNAL_ROUTE` | `PASS` |
| `/manifesto` | Open local dashboard | `INTERNAL_ROUTE` | `PASS` |
| `footer` | Imprint pending | `PENDING_DISABLED` | `PASS` |
| `footer` | Privacy pending | `PENDING_DISABLED` | `PASS` |

## Copy Guardrails

| Check | Status | Violations |
|---|---:|---:|
| `forbidden_action_terms` | `PASS` | `0` |
| `private_path_or_identity_markers` | `PASS` | `0` |
| `decision_ready_dummy_claims` | `PASS` | `0` |
| `public_launch_dummy_claims` | `PASS` | `0` |
| `brand_pivot_claims` | `PASS` | `0` |

## Screenshot Coverage

- Screenshot count: `6`
- Covered routes: `/`, `/workflow`, `/evidence`, `/portfolio`, `/dashboard`, `/manifesto`

## Private Preview / Public Launch Guardrails

- Public launch remains blocked.
- Imprint and privacy stay pending unless configured through real environment URLs.
- No fake checkout, waitlist, or placeholder public CTA targets are allowed.

## Advice / Privacy Guardrails

- No private raw paths are allowed in website source or public demo payloads.
- Market-action terms are blocked in new CTA/display fields, with legacy/internal filename exceptions only.

## Fixed Issues

- Screenshot script now covers all six main private-preview routes.
- Route/CTA/copy matrices are generated as deterministic QA artifacts.

## Remaining Review Items

- Public launch blockers remain intentionally active.
- External CTA targets remain pending until real environment URLs are configured.

## Handoff Impact

- QA CSVs and this report are allowlisted for handoff export.

## Recommended Next Patch

`PATCH / WEBSITE PRIVATE PREVIEW Handoff Review / STATIC BUILD PACKAGE QA / NO PUBLIC DEPLOY`
