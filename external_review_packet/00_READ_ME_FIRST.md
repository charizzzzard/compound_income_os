# Compound Income OS External LLM Review Packet - Monthly Brief Schema Contract Hardening

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach der schema-level Reviewer-Surface-Haertung fuer den Monthly
Portfolio Decision Brief.

- patch_title: `MONTHLY_BRIEF_SCHEMA_CONTRACT_HARDENING`
- bundle_purpose: `external_review_after_monthly_brief_schema_contract_hardening`
- implementation_head: `a82b7d265912dd6147260cd6137d4e2609276355`
- central_handoff_zip_head: `a82b7d265912dd6147260cd6137d4e2609276355`
- current_handoff_head: `a82b7d265912dd6147260cd6137d4e2609276355`
- base_head: `23018bfb53877e3b35c166f2c9d8750c26c5787d`
- status: `MONTHLY_BRIEF_SCHEMA_CONTRACT_HARDENING_HANDOFF_READY`

Dieses Paket ersetzt aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck. Es ist der einzige authoritative externe Handoff fuer
diese Aufgabe; lokale Ordner unter `outputs/` sind nur Evidence-Quellen und kein
paralleler Review-Handoff.

## Metadata-Only Publication Offset

The ZIP represents the implementation snapshot at
`a82b7d265912dd6147260cd6137d4e2609276355`. If this README, the external
context file or checksum are committed after ZIP export, the resulting repo HEAD
is a metadata-only publication offset. That offset affects reviewer-facing
metadata only and does not change source, tests, examples, configs, runtime
behavior or the ZIP implementation snapshot. The exact metadata commit head is
reported in the final operator report after commit creation.

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- canonical_review_bundle: `external_review_packet/HANDOFF_LATEST.zip`
- canonical_checksum: `external_review_packet/HANDOFF_LATEST.sha256`
- canonical_context: `external_review_packet/HANDOFF_LATEST_CONTEXT.md`

## Source-of-Truth / Precedence

Bei Konflikten gilt diese Reihenfolge:

1. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
2. ZIP-internal `HANDOFF_CONTEXT.md`
3. ZIP-internal artifact indexes, omitted-artifact registers and patch identity
4. GitHub browser URL for committed repo inspection
5. Local-only/generated/ignored files only if explicitly included or summarized

## What Changed

The patch hardens the Monthly Portfolio Decision Brief reviewer surface by
adding:

- `docs/contracts/MONTHLY_PORTFOLIO_DECISION_BRIEF_SURFACE_SCHEMA.md`
- explicit `NOT_APPLICABLE` coverage in the REVIEW example tests
- README clarification that `synthetic_inputs/*` paths are illustrative
  reviewer-surface references, not included real fixtures
- contract wording that sanitized examples now exist, while additional examples
  such as `BLOCKED` may be future work

## Reviewer Instructions

- Review this as a contract/test/docs hardening patch, not as runtime feature
  expansion.
- Use repo-relative paths in findings.
- Check ZIP-internal:
  - `HANDOFF_CONTEXT.md`
  - `HANDOFF_PATCH_IDENTITY.md`
  - `HANDOFF_CHANGE_CLASSIFICATION.csv`
  - `HANDOFF_VALIDATION.txt`
  - `HANDOFF_MANIFEST.csv`
  - `HANDOFF_ARTIFACT_INDEX.csv`
  - `HANDOFF_OMITTED_ARTIFACTS.csv`
- `HANDOFF_VALIDATION.txt` contains `RECORDED_VALIDATION` entries. These are
  command provenance, not external execution proof unless a separate operator or
  reviewer report says so.
- Do not infer omitted private, raw, broker, provider, credential, user-agent or
  strategy files.
- Treat `outputs/` as local generated evidence only, not as a parallel handoff.

## Required Guardrails

Future Monthly Brief work must preserve:

- read-only behavior;
- default generated outputs as local/generated unless a separate tracked boundary
  is accepted;
- no real portfolio, broker, provider, raw, credential, account, transaction or
  private strategy data in tracked examples;
- no score/ranking/valuation/portfolio-rule/watchlist/fundamentals changes;
- no broker/provider/API/order/trade/live-trading behavior;
- Decision Quality as process quality only, never investment confidence;
- Human Operator as final acceptance authority.

## Handoff Integrity Summary

- zip_sha256: `0f2464d7f772bc28850cbcf2a94974fc8c24dfa5100e2356be1ef7c8f73145d6`
- sha_match: validated after packet synchronization
- zip_testzip: `None`
- nested_zip_count: `0`
- forbidden_match_count: `0`
- local_path_leak_count: `0`

## Explicit Non-Scope

This packet does not claim or introduce:

- broker import;
- broker/provider/API integration;
- order execution;
- live trading;
- buy/sell automation;
- investment advice automation;
- scoring formula changes;
- ranking formula changes;
- valuation methodology changes;
- portfolio-rule changes;
- watchlist logic changes;
- fundamentals logic changes;
- dashboard/data-freshness/decision-quality semantic changes;
- replay/backtesting/simulation/outcome attribution;
- tax/legal/commercial approval;
- private/generated/raw publication;
- runtime enforcement;
- product, production or investment readiness.

Human Operator remains final acceptance authority.
