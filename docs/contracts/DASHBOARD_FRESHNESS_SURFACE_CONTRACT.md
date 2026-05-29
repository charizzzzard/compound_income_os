# Dashboard Freshness Surface Contract

## Purpose

This contract defines how Data Freshness status must be exposed on
operator-facing dashboard and report surfaces.

It is a visibility and reviewability contract. It does not implement a dashboard
UI, a web server, runtime enforcement, investment logic, order execution, replay
or outcome attribution.

## Contract Position

This contract bridges:

- `docs/contracts/DATA_FRESHNESS_STALENESS_CONTRACT.md`
- `docs/contracts/DASHBOARD_OPERATOR_SURFACE_CONTRACT.md`

It does not replace either parent contract. The Data Freshness / Staleness
Contract remains authoritative for freshness producer semantics. The Dashboard
Operator Surface Contract remains authoritative for the general operator-summary
surface. This contract defines only the Freshness-specific operator-surface
obligations between them.

## Operator Surface Scope

Affected operator-facing surfaces:

- dashboard operator summary
- personal run report / operator summary when it renders dashboard operator
  summary evidence
- monthly decision report only when a Data Freshness summary is explicitly
  supplied to that report builder or CLI

This is not a UI/server implementation contract. It does not require a visual
dashboard, browser UI, server route, live panel or runtime gate.

## Required Freshness Surface Fields

Where the Data Freshness surface is present, these field families must remain
visible or be documented with stable aliases:

- `data_freshness_status`
- `data_freshness_review_required`
- `data_freshness_artifact_status` or equivalent artifact visibility field,
  such as the aggregate `artifact_status` plus `source_artifacts`
- `data_freshness_fresh_count`
- `data_freshness_stale_count`
- `data_freshness_missing_count`
- `data_freshness_unknown_count`
- `data_freshness_review_required_count`
- `data_freshness_not_applicable_count` where applicable
- `data_freshness_source_artifact` or equivalent source artifact reference,
  such as `source_artifacts`
- `data_freshness_top_reason_codes` or equivalent reason-code list
- `operator_attention_required`
- `operator_attention_reasons`

If an implementation uses aliases, the alias must preserve the same review
meaning and must not hide degraded Freshness states.

## Allowed Freshness States

Allowed or referenced Freshness states and operator-surface obligations:

| state | operator-surface obligation |
| --- | --- |
| `FRESH` | May remain non-review if no other review condition applies. |
| `STALE` | Must remain visible and must not be normalized to `PASS` or `OK`. |
| `MISSING` | Must remain visible and must not be normalized to `PASS` or `OK`. |
| `UNKNOWN` | Must remain visible and must not be normalized to `PASS` or `OK`. |
| `REVIEW_REQUIRED` | Must force operator attention or equivalent review visibility. |
| `NOT_APPLICABLE` | Must remain visible and must not be silently dropped. |
| `NOT_AVAILABLE` | Must remain visible and must not be presented as `FRESH`. |
| `PARTIAL` | Must remain visible when selected or expected Freshness artifacts are missing or unreadable. |

## Surface Status Mapping

Freshness contributes to operator-facing `surface_status` under these rules:

- Freshness problems must never be silently normalized to `PASS`.
- `STALE`, `MISSING`, `UNKNOWN`, `REVIEW_REQUIRED`, and `PARTIAL` must result
  in `REVIEW`, `PARTIAL`, or an equivalent non-`PASS` status according to the
  Dashboard Operator Surface Contract.
- `FRESH` alone must not force `REVIEW`.
- `NOT_AVAILABLE` must be explicitly visible; whether it forces `REVIEW`
  depends on whether Freshness was expected for the run.
- Missing same-run `data_freshness_summary.json` when the `data_freshness`
  stage was selected must not result in `PASS`.

## Artifact Visibility

Freshness artifacts must be distinguishable at the operator surface:

- readable Freshness summary
- expected but missing Freshness summary
- unreadable Freshness summary
- Freshness stage not selected / legacy standalone call

The surface must not infer Freshness from the existence or success of unrelated
stages.

## No Silent Normalization

- Do not convert `STALE`/`MISSING`/`UNKNOWN`/`REVIEW_REQUIRED`/`PARTIAL`/`NOT_AVAILABLE` to `PASS`.
- Do not convert `STALE`/`MISSING`/`UNKNOWN`/`REVIEW_REQUIRED`/`PARTIAL`/`NOT_AVAILABLE` to `OK`.
- Do not hide missing Freshness artifacts.
- Do not infer Freshness from unrelated successful stages.
- Do not impute Freshness counts.
- Do not overwrite accepted facts silently.

## Acceptance Criteria For Future Operator Surface Hardening

A future `DASHBOARD_FRESHNESS_OPERATOR_SURFACE_HARDENING` patch must include:

- tests for `FRESH`
- tests for `STALE`
- tests for `MISSING`
- tests for `UNKNOWN`
- tests for `REVIEW_REQUIRED`
- tests for `NOT_APPLICABLE`
- tests for `NOT_AVAILABLE`
- tests for `PARTIAL` / missing expected artifact
- tests proving no silent `PASS` normalization
- tests proving `operator_attention_reasons` remain stable
- tests proving missing, unreadable and not-selected Freshness artifacts remain
  distinguishable

## Explicit Non-Scope

This contract does not implement or approve:

- dashboard UI server
- web app implementation
- broker integration
- order execution
- buy/sell automation
- investment advice
- valuation automation
- DCF engine
- provider/API integration
- scraping/crawling
- replay/backtesting/simulation
- outcome attribution
- score/ranking/portfolio-rule changes
- runtime enforcement
- production/product/investment readiness claims

## Human Operator Authority

The Human Operator remains final acceptance authority.

This contract governs visibility and reviewability only. It does not authorize
investment action, trading action, order preparation, order execution,
automation, production release or investment readiness.
