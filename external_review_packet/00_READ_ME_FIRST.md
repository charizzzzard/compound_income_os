# Compound Income OS External LLM Review Packet - Practical Operating Standard

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach dem Governance-Patch `CIOS_PRACTICAL_OPERATING_STANDARD`.

- local_handoff_head: `af1622a8e1fa3ac89b53a23cda05d50ebb334323`
- remote_main_head_at_export: `e8ac5583502ad90a9240b857469debb87eacc6b2`
- status: `GOVERNANCE_PATCH_HANDOFF_READY`

Dieses Packet ersetzt aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck. Es ist der einzige authoritative externe Handoff fuer
diese Aufgabe; lokale Ordner unter `outputs/` sind nur Evidence-Quellen und kein
paralleler Review-Handoff.

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- base_head: `e8ac5583502ad90a9240b857469debb87eacc6b2`
- implementation_head: `af1622a8e1fa3ac89b53a23cda05d50ebb334323`
- preflight_head: `e8ac5583502ad90a9240b857469debb87eacc6b2`
- central_handoff_zip_head: `af1622a8e1fa3ac89b53a23cda05d50ebb334323`
- current_handoff_head: `af1622a8e1fa3ac89b53a23cda05d50ebb334323`
- bundle_purpose: `external_review_after_cios_practical_operating_standard`
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
- Findings muessen die kanonischen Severities `BLOCKER`, `MAJOR`, `MINOR` oder
  `INFO` verwenden.
- Inferiere keine ausgelassenen privaten, raw, Broker- oder Provider-Dateien.
- Inferiere nicht, dass GitHub lokale uncommitted, ignored oder generated files
  enthaelt.
- Behandle Dokumentations- und Governance-Standards nicht als Runtime
  Enforcement.

## Handoff Integrity Summary

- zip_file_count: `522`
- zip_sha256: `cb878971be66cc008c9a793bc54b26ca82dd6ba6d76532836a4bf89878a85c0f`
- sha_match: `True`
- zip_testzip: `None`
- nested_zip_count: `0`
- forbidden_match_count: `0`
- local_path_leak_count: `0`

## Patch Delta

`HANDOFF_CHANGE_CLASSIFICATION.csv` lists exactly these patch-changed files:

- `docs/governance/CIOS_PRACTICAL_OPERATING_STANDARD.md`
- `tests/test_practical_operating_standard.py`

## Explicit Non-Scope

This packet does not claim or introduce:

- CIOS feature logic
- investment logic changes
- scoring changes
- ranking changes
- valuation changes
- portfolio-rule changes
- dashboard/data-freshness/report semantic changes
- broker import changes
- provider/API integration
- order execution
- buy/sell automation
- private/generated/raw publication
- runtime enforcement
- public GitHub repository visibility
- product, production or investment readiness

Human Operator remains final acceptance authority.
