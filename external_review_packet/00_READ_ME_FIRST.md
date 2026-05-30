# Compound Income OS External LLM Review Packet - Monthly Portfolio Decision Brief MVP

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach dem Implementierungs-Patch
`MONTHLY_PORTFOLIO_DECISION_BRIEF_MVP`.

- local_handoff_head: `9d669c285bcebee496cc48385f689463ce29a7c1`
- remote_main_head_at_export: `c730cc975c3974245f191cebd0699ad863cf7fe8`
- status: `MVP_PATCH_HANDOFF_READY`

Dieses Packet ersetzt aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck. Es ist der einzige authoritative externe Handoff fuer
diese Aufgabe; lokale Ordner unter `outputs/` sind nur Evidence-Quellen und kein
paralleler Review-Handoff.

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- base_head: `c730cc975c3974245f191cebd0699ad863cf7fe8`
- implementation_head: `9d669c285bcebee496cc48385f689463ce29a7c1`
- central_handoff_zip_head: `9d669c285bcebee496cc48385f689463ce29a7c1`
- current_handoff_head: `9d669c285bcebee496cc48385f689463ce29a7c1`
- bundle_purpose: `external_review_after_monthly_portfolio_decision_brief_mvp`
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
- Behandle diesen MVP als deterministische Evidence-Konsolidierung, nicht als
  Entscheidungsautomatisierung.

## Handoff Integrity Summary

- zip_file_count: `529`
- zip_sha256: `4a4965cab060800ffb7ef94d1555dc3d2502f26d87fc163d029a4ac8c1dbbb0a`
- sha_match: `True`
- zip_testzip: `None`
- nested_zip_count: `0`
- forbidden_match_count: `0`
- local_path_leak_count: `0`

## Patch Delta

`HANDOFF_CHANGE_CLASSIFICATION.csv` lists exactly these patch-changed files:

- `docs/architecture/CIOS_FEATURE_STATUS.yaml`
- `docs/contracts/MONTHLY_PORTFOLIO_DECISION_BRIEF_CONTRACT.md`
- `src/monthly_portfolio_decision_brief.py`
- `tests/test_monthly_portfolio_decision_brief.py`

## Generated Output Boundary

The producer default outputs are generated/local-only by default:

- `data/processed/monthly_portfolio_decision_brief.json`
- `data/processed/monthly_portfolio_decision_brief.csv`
- `reports/<as_of_date>/monthly_portfolio_decision_brief.md`

Real generated monthly decision brief outputs are not committed by this patch
and must not be inferred from the handoff packet.

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
- dashboard/report semantic changes outside the new standalone brief producer
- replay/backtesting/simulation/outcome attribution
- tax/legal/commercial approval
- private/generated/raw publication
- runtime enforcement
- product, production or investment readiness

Human Operator remains final acceptance authority.
