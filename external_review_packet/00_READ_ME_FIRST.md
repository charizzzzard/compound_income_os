# Compound Income OS External LLM Review Packet - Monthly Brief Personal Run Integration

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach der optionalen Integration des bestehenden Monthly Portfolio
Decision Brief in den Personal Run.

- patch_title: `MONTHLY_PORTFOLIO_DECISION_BRIEF_PERSONAL_RUN_INTEGRATION_IMPLEMENTATION`
- bundle_purpose: `external_review_after_monthly_portfolio_decision_brief_personal_run_integration_implementation`
- implementation_head: `9cb03c172c40307b576f165a51c6ae352db34e27`
- central_handoff_zip_head: `9cb03c172c40307b576f165a51c6ae352db34e27`
- current_handoff_head: `9cb03c172c40307b576f165a51c6ae352db34e27`
- base_head: `627b186022c7fd456a07378af8333a503b1d40e3`
- status: `PERSONAL_RUN_INTEGRATION_HANDOFF_READY`

Dieses Paket ersetzt aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck. Es ist der einzige authoritative externe Handoff fuer
diese Aufgabe; lokale Ordner unter `outputs/` sind nur Evidence-Quellen und kein
paralleler Review-Handoff.

## Metadata-Only Publication Offset

The ZIP represents the implementation snapshot at
`9cb03c172c40307b576f165a51c6ae352db34e27`. If this README, the external
context file or checksum are committed after ZIP export, the resulting repo HEAD
is a metadata-only publication offset. That offset affects reviewer-facing
metadata only and does not change source, tests, configs, runtime behavior or
the ZIP implementation snapshot. The exact metadata commit head is reported in
the final operator report after commit creation.

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

The existing deterministic Monthly Portfolio Decision Brief producer is now
available as an optional Personal Run stage named
`monthly_portfolio_decision_brief`.

The stage is placed after `dashboard_operator_summary` and before `history`. It
reuses the existing producer and records generated JSON, CSV and Markdown
artifacts through the Personal Run manifest, artifact index and used-inputs
surfaces.

The integration is read-only. It does not recalculate scores, ranking,
valuation, portfolio rules, watchlist logic or fundamentals, and it does not add
broker/provider/API/order/trade/live-trading behavior.

## Reviewer Instructions

- Review this as a Personal Run integration patch, not as a greenfield Monthly
  Brief MVP implementation.
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
- optional Personal Run stage semantics unless a separate accepted patch changes
  the contract;
- hard mandatory ranking input behavior: missing, unreadable or schema-invalid
  `personal_monthly_buy_ranking.csv` must stay `BLOCKED` or equivalent;
- visible optional evidence gaps for cash refill, rebalance, Data Freshness,
  Decision Quality and review queue;
- no normalization of `STALE`, `MISSING`, `UNKNOWN`, `REVIEW_REQUIRED`,
  `NOT_AVAILABLE` or `NOT_APPLICABLE` into clean `OK` or `READY`;
- Decision Quality as process quality only, never investment confidence;
- no direct reads from private/raw/broker/provider/credential/.env/user-agent or
  private strategy files;
- generated real outputs local/ignored unless a separate tracked-artifact
  boundary is accepted;
- `external_review_packet/` as the only central handoff;
- Human Operator as final acceptance authority.

## Handoff Integrity Summary

- zip_sha256: `468f2e3acac8007ba258a8eba46a2478ee7525084ee454498b77faced3d26d24`
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
