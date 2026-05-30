# Compound Income OS External LLM Review Packet - Data Visibility Artifact Boundary Audit

Dies ist der Einstiegspunkt fuer die externe Review von Compound Income OS
(CIOS) nach dem Engineering-Audit-Patch
`DATA_VISIBILITY_AND_ARTIFACT_BOUNDARY_AUDIT`.

- local_handoff_head: `31a30228645e9a908b12db5d95a3a02b44045ea2`
- remote_main_head_at_export: `5c9b87f5bcdbe2ac32ba2388f62258809ac10701`
- status: `AUDIT_PATCH_HANDOFF_READY`

Dieses Packet ersetzt aeltere Dateien in `external_review_packet/` fuer den
aktuellen Review-Zweck. Es ist der einzige authoritative externe Handoff fuer
diese Aufgabe; lokale Ordner unter `outputs/` sind nur Evidence-Quellen und kein
paralleler Review-Handoff.

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- base_head: `5c9b87f5bcdbe2ac32ba2388f62258809ac10701`
- implementation_head: `31a30228645e9a908b12db5d95a3a02b44045ea2`
- central_handoff_zip_head: `31a30228645e9a908b12db5d95a3a02b44045ea2`
- current_handoff_head: `31a30228645e9a908b12db5d95a3a02b44045ea2`
- bundle_purpose: `external_review_after_data_visibility_and_artifact_boundary_audit`
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
- Behandle diesen Audit nicht als `.gitignore`-Cleanup oder Runtime
  Enforcement.

## Handoff Integrity Summary

- zip_file_count: `526`
- zip_sha256: `c30f83c128233730ea7248b09a28e5168b0a6689963625c17dd34ea92751cce9`
- sha_match: `True`
- zip_testzip: `None`
- nested_zip_count: `0`
- forbidden_match_count: `0`
- local_path_leak_count: `0`

## Patch Delta

`HANDOFF_CHANGE_CLASSIFICATION.csv` lists exactly these patch-changed files:

- `docs/governance/DATA_VISIBILITY_AND_ARTIFACT_BOUNDARY.md`
- `src/data_visibility_artifact_boundary_audit.py`
- `tests/test_data_visibility_artifact_boundary_audit.py`

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
