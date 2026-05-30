# Compound Income OS External LLM Review Packet - Monthly Brief Path Redaction P0

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach dem P0-Hardening-Patch
`MONTHLY_PORTFOLIO_DECISION_BRIEF_PATH_REDACTION_P0`.

- local_handoff_head: `10fc5f7ace8708502ba68c5f1068bae76a0e67f7`
- remote_main_head_at_export: `26dfcec438615cbc56d4e01979081a4e145c7402`
- status: `P0_PATH_REDACTION_HANDOFF_READY`

Dieses Packet ersetzt aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck. Es ist der einzige authoritative externe Handoff fuer
diese Aufgabe; lokale Ordner unter `outputs/` sind nur Evidence-Quellen und kein
paralleler Review-Handoff.

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- base_head: `26dfcec438615cbc56d4e01979081a4e145c7402`
- implementation_head: `10fc5f7ace8708502ba68c5f1068bae76a0e67f7`
- central_handoff_zip_head: `10fc5f7ace8708502ba68c5f1068bae76a0e67f7`
- current_handoff_head: `10fc5f7ace8708502ba68c5f1068bae76a0e67f7`
- bundle_purpose: `external_review_after_monthly_portfolio_decision_brief_path_redaction_p0`
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
- Pruefe insbesondere, dass fremde Windows- und UNC-Pfade in ZIP-/POSIX-Kontext
  deterministisch redigiert werden.

## Handoff Integrity Summary

- zip_file_count: `529`
- zip_sha256: `e196164231c0f0b31304d9f4b8cfa44a4ccba35216b747963e5cefb9afa1d746`
- sha_match: `True`
- zip_testzip: `None`
- nested_zip_count: `0`
- forbidden_match_count: `0`
- local_path_leak_count: `0`

## Patch Delta

`HANDOFF_CHANGE_CLASSIFICATION.csv` lists exactly these patch-changed files:

- `src/monthly_portfolio_decision_brief.py`
- `tests/test_monthly_portfolio_decision_brief.py`

## Explicit Non-Scope

This packet does not claim or introduce:

- broker import
- broker/provider/API integration
- order execution
- buy/sell automation
- investment advice automation
- scoring formula changes
- ranking formula changes
- valuation methodology changes
- portfolio-rule changes
- personal_run_engine stage-order changes
- dashboard/data-freshness/decision-quality semantic changes
- replay/backtesting/simulation/outcome attribution
- tax/legal/commercial approval
- private/generated/raw publication
- runtime enforcement
- product, production or investment readiness

Human Operator remains final acceptance authority.
