# External Review Packet Context

- project_name: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- patch_title: `MONTHLY_PORTFOLIO_DECISION_BRIEF_BASELINE_RECONCILIATION_AND_HANDOFF_UPDATE`
- bundle_purpose: `external_review_after_monthly_portfolio_decision_brief_baseline_reconciliation`
- profile: `full_review`
- bundle_name: `monthly_portfolio_decision_brief_baseline_reconciliation`
- bundle_name_in_upload_folder: `HANDOFF_LATEST`
- base_head: `10fc5f7ace8708502ba68c5f1068bae76a0e67f7`
- implementation_head: `d94cd922f5a36eddfcf509763d6e827ec53e94e5`
- preflight_head: `d94cd922f5a36eddfcf509763d6e827ec53e94e5`
- central_handoff_zip_head: `d94cd922f5a36eddfcf509763d6e827ec53e94e5`
- current_handoff_head: `d94cd922f5a36eddfcf509763d6e827ec53e94e5`
- remote_main_head_at_export: `d94cd922f5a36eddfcf509763d6e827ec53e94e5`
- dirty_worktree_present_at_export: `False`
- reviewer_facing_upload_folder: `external_review_packet`

If this context file and checksum are committed after ZIP export, the repo HEAD
may become a metadata-only head newer than `central_handoff_zip_head`. That is an
allowed head-offset case only when explicitly reported by the operator report.

## Source-of-Truth / Precedence

Bei Konflikten gilt diese Reihenfolge:

1. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
2. ZIP-internal `HANDOFF_CONTEXT.md`
3. ZIP-internal artifact indexes, omitted-artifact registers and patch identity
4. GitHub browser URL for committed repo inspection
5. Local-only/generated/ignored files only if explicitly included or summarized

`outputs/` may contain ignored local evidence, including checkpoint reports, but
it is not an authoritative handoff and must not be treated as a parallel review
packet.

## Reconciliation Purpose

This packet reconciles the Monthly Portfolio Decision Brief component checkpoint
and external checkpoint review into the central project handoff state.

The Monthly Portfolio Decision Brief is no longer a historical greenfield
pre-MVP area. The current committed repository already contains these baseline
implementation artifacts:

- `src/monthly_portfolio_decision_brief.py`
- `tests/test_monthly_portfolio_decision_brief.py`
- `docs/contracts/MONTHLY_PORTFOLIO_DECISION_BRIEF_CONTRACT.md`

The checkpoint is accepted with findings as a current baseline. It is not
historical pre-MVP evidence. Future work must be framed as baseline follow-up,
hardening, Personal Run integration, synthetic/sanitized example output or
operator-surface extension.

Future work must not be framed as:

- greenfield MVP implementation;
- full rewrite;
- new investment methodology;
- broker execution;
- live trading;
- automated buy/sell decision system.

## Ingested External Checkpoint Review

- checkpoint_review_status: `CHECKPOINT_ACCEPTED_WITH_FINDINGS`
- reviewed_checkpoint_name: `MONTHLY_PORTFOLIO_DECISION_BRIEF_COMPONENT_CHECKPOINT`
- checkpoint_report_source: `outputs/monthly_portfolio_decision_brief_component_checkpoint/MONTHLY_PORTFOLIO_DECISION_BRIEF_COMPONENT_CHECKPOINT.md`
- checkpoint_report_authority: `LOCAL_IGNORED_EVIDENCE_NOT_AUTHORITATIVE_HANDOFF`
- human_operator_final_acceptance_required: `True`

### MAJOR Findings

1. Timing mismatch:
   The repo baseline already contains Monthly Portfolio Decision Brief
   implementation artifacts, so the checkpoint is not a historical pre-MVP
   snapshot.

2. Report-only checkpoint:
   The checkpoint was generated under `outputs/` and is local/ignored evidence,
   not an authoritative central handoff by itself.

### MINOR Findings

3. Personal-Run integration remains open:
   It should be handled as a separate patch only if stage order, manifest,
   artifact index and used inputs can be extended deterministically.

4. No committed sanitized example brief output:
   A future separate patch may add synthetic/sanitized fixture output, but no
   real portfolio, broker, provider, private, raw or strategy data may be
   committed.

### INFO Findings

5. Existing read-only, deterministic and non-claims guardrails appear well
   covered and must remain regression-protected.

## Required Guardrails For Future Monthly Brief Work

Future Monthly Brief follow-up prompts must preserve these rules:

1. Existing files must be inspected first; no greenfield rewrite.
2. The brief remains read-only.
3. Only existing processed/generated artifacts may be consumed.
4. No broker/provider/API/HTTP/order/trade/execution integration.
5. No recalculation of score, ranking, valuation, portfolio rules, watchlist
   logic or fundamentals.
6. Mandatory ranking input remains hard: missing, unreadable or schema-invalid
   `personal_monthly_buy_ranking.csv` must produce `BLOCKED` or equivalent.
7. Optional evidence remains visible: cash refill, rebalance, Data Freshness,
   Decision Quality and review queue must not be silently imputed.
8. `STALE`, `MISSING`, `UNKNOWN`, `REVIEW_REQUIRED`, `NOT_AVAILABLE` and
   `NOT_APPLICABLE` must not be normalized into `OK` or `READY`.
9. Decision Quality remains process quality, never investment confidence.
10. No direct reads from private/raw/broker/provider/credential/.env/user-agent
    or private strategy files.
11. Path redaction must happen before read attempts where relevant.
12. Generated real outputs remain local/ignored unless a separate
    tracked-artifact boundary is explicitly accepted.
13. `external_review_packet/` remains the only central handoff.
14. Human Operator remains final acceptance authority.

## Handoff Integrity Summary

- zip_path: `external_review_packet/HANDOFF_LATEST.zip`
- sha_path: `external_review_packet/HANDOFF_LATEST.sha256`
- zip_file_count: `529`
- zip_sha256: `01d1a148bcc6e4d52319a41407de400a4ae344243d26e9a4e0d7c4ee4e5f6d15`
- sha_match: `True`
- zip_testzip: `None`
- nested_zip_count: `0`
- forbidden_match_count: `0`
- local_path_leak_count: `0`
- no_parallel_handoff_claimed: `True`

## Validation Reality

Actually executed in the current local repo for the checkpoint baseline before
handoff regeneration:

- `git status --short --branch`: PASS, clean tracked state before checkpoint report generation
- `git rev-parse HEAD`: PASS, `d94cd922f5a36eddfcf509763d6e827ec53e94e5`
- `git remote -v`: PASS, GitHub origin configured
- `git ls-remote --heads origin main`: PASS, remote main equals local HEAD
- `git diff --check`: PASS
- `python -m pytest -q`: PASS, `989 passed, 410 subtests passed in 170.63s`
- `python -m ruff check .`: PASS, `All checks passed!`

ZIP-internal `HANDOFF_VALIDATION.txt` records validation commands as
`RECORDED_VALIDATION`. It is command provenance, not proof of external execution
unless a separate reviewer/operator report says so.

## External LLM Review Instructions

- Review this as a baseline reconciliation packet, not as greenfield MVP work.
- Use repo-relative paths in findings.
- Do not infer omitted private/raw/provider/broker files.
- Do not treat ignored generated outputs as committed repo truth.
- Do not treat the local checkpoint report under `outputs/` as an authoritative
  handoff by itself.
- Distinguish implemented behavior, documentation, generated artifacts,
  ignored/local evidence, tests and future intent.
- Use canonical severities: `BLOCKER`, `MAJOR`, `MINOR`, `INFO`.

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
