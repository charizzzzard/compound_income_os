# Compound Income OS External LLM Review Packet - Monthly Brief Baseline Reconciliation

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach der Baseline-Reconciliation fuer den Monthly Portfolio Decision
Brief.

- patch_title: `MONTHLY_PORTFOLIO_DECISION_BRIEF_BASELINE_RECONCILIATION_AND_HANDOFF_UPDATE`
- bundle_purpose: `external_review_after_monthly_portfolio_decision_brief_baseline_reconciliation`
- local_handoff_head: `d94cd922f5a36eddfcf509763d6e827ec53e94e5`
- remote_main_head_at_export: `d94cd922f5a36eddfcf509763d6e827ec53e94e5`
- status: `BASELINE_RECONCILIATION_HANDOFF_READY`

Dieses Packet ersetzt aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck. Es ist der einzige authoritative externe Handoff fuer
diese Aufgabe; lokale Ordner unter `outputs/` sind nur Evidence-Quellen und kein
paralleler Review-Handoff.

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- base_head: `10fc5f7ace8708502ba68c5f1068bae76a0e67f7`
- implementation_head: `d94cd922f5a36eddfcf509763d6e827ec53e94e5`
- central_handoff_zip_head: `d94cd922f5a36eddfcf509763d6e827ec53e94e5`
- current_handoff_head: `d94cd922f5a36eddfcf509763d6e827ec53e94e5`
- bundle_purpose: `external_review_after_monthly_portfolio_decision_brief_baseline_reconciliation`
- canonical_review_bundle: `external_review_packet/HANDOFF_LATEST.zip`
- canonical_checksum: `external_review_packet/HANDOFF_LATEST.sha256`
- canonical_context: `external_review_packet/HANDOFF_LATEST_CONTEXT.md`

If this metadata file is committed after ZIP export, the repo HEAD may become a
metadata-only head that is newer than `central_handoff_zip_head`. That offset is
expected only when reported explicitly in the operator report.

## Source-of-Truth / Precedence

Bei Konflikten gilt diese Reihenfolge:

1. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
2. ZIP-internal `HANDOFF_CONTEXT.md`
3. ZIP-internal artifact indexes, omitted-artifact registers and patch identity
4. GitHub browser URL for committed repo inspection
5. Local-only/generated/ignored files only if explicitly included or summarized

## What Changed In Review Framing

The Monthly Portfolio Decision Brief is not a historical greenfield MVP area
anymore. The current committed repository already contains:

- `src/monthly_portfolio_decision_brief.py`
- `tests/test_monthly_portfolio_decision_brief.py`
- `docs/contracts/MONTHLY_PORTFOLIO_DECISION_BRIEF_CONTRACT.md`

The component checkpoint is accepted with findings as a current baseline. It is
not historical pre-MVP evidence. Future work must be framed as follow-up,
hardening, Personal Run integration, synthetic/sanitized example output or
operator-surface extension.

## Ingested Findings

- MAJOR: Timing mismatch; the repo already contains Monthly Brief implementation
  artifacts.
- MAJOR: The report-only checkpoint under `outputs/` is local/ignored evidence,
  not authoritative handoff by itself.
- MINOR: Personal-Run integration remains open and must be a separate
  deterministic patch.
- MINOR: No committed sanitized example brief output exists; a future patch may
  add one without committing real portfolio, broker, provider, private, raw or
  strategy data.
- INFO: Existing read-only, deterministic and non-claims guardrails must remain
  regression-protected.

## Reviewer Instructions

- Verwende volle repo-relative Pfade in Findings.
- Pruefe ZIP-intern:
  - `HANDOFF_CONTEXT.md`
  - `HANDOFF_PATCH_IDENTITY.md`
  - `HANDOFF_CHANGE_CLASSIFICATION.csv`
  - `HANDOFF_VALIDATION.txt`
  - `HANDOFF_MANIFEST.csv`
  - `HANDOFF_ARTIFACT_INDEX.csv`
  - `HANDOFF_OMITTED_ARTIFACTS.csv`
- `HANDOFF_VALIDATION.txt` enthaelt `RECORDED_VALIDATION`-Eintraege. Diese
  sind Befehlsprovenienz, nicht Ausfuehrungsbeweise, sofern kein separater
  Operator- oder Reviewer-Bericht die Ausfuehrung belegt.
- Inferiere keine ausgelassenen privaten, raw, Broker- oder Provider-Dateien.
- Behandle `outputs/` nicht als parallelen Handoff.
- Pruefe zukuenftige Monthly-Brief-Arbeit nur als Follow-up/Hardening/Integration,
  nicht als Greenfield-MVP.

## Required Future Guardrails

Future Monthly Brief work must preserve:

- read-only behavior;
- consumption of existing processed/generated artifacts only;
- no broker/provider/API/HTTP/order/trade/execution integration;
- no score/ranking/valuation/portfolio-rule/watchlist/fundamentals recalculation;
- hard mandatory ranking input behavior: missing/unreadable/schema-invalid
  `personal_monthly_buy_ranking.csv` must be `BLOCKED` or equivalent;
- visible optional evidence gaps for cash refill, rebalance, Data Freshness,
  Decision Quality and review queue;
- no normalization of `STALE`, `MISSING`, `UNKNOWN`, `REVIEW_REQUIRED`,
  `NOT_AVAILABLE` or `NOT_APPLICABLE` into `OK` or `READY`;
- Decision Quality as process quality only, never investment confidence;
- no direct reads from private/raw/broker/provider/credential/.env/user-agent or
  private strategy files;
- path redaction before read attempts where relevant;
- generated real outputs local/ignored unless a separate tracked-artifact
  boundary is accepted;
- `external_review_packet/` as the only central handoff;
- Human Operator as final acceptance authority.

## Handoff Integrity Summary

- zip_file_count: `529`
- zip_sha256: `01d1a148bcc6e4d52319a41407de400a4ae344243d26e9a4e0d7c4ee4e5f6d15`
- sha_match: `True`
- zip_testzip: `None`
- nested_zip_count: `0`
- forbidden_match_count: `0`
- local_path_leak_count: `0`

## Explicit Non-Scope

This packet does not claim or introduce:

- source implementation changes;
- test implementation changes;
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
- personal_run_engine stage-order changes;
- dashboard/data-freshness/decision-quality semantic changes;
- replay/backtesting/simulation/outcome attribution;
- tax/legal/commercial approval;
- private/generated/raw publication;
- runtime enforcement;
- product, production or investment readiness.

Human Operator remains final acceptance authority.
