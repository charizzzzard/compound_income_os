# External Review Packet - Audit Command Provenance Hardening

- patch_title: `AUDIT_COMMAND_PROVENANCE_HARDENING`
- bundle_purpose: `external_review_after_audit_command_provenance_hardening`
- branch: `main`
- implementation_head: `163585ed9c5b53a5520babbc8de738e75c89091b`
- central_handoff_path: `external_review_packet/`
- handoff_zip: `external_review_packet/HANDOFF_LATEST.zip`
- handoff_sha256: `7FB20A829210D74BA549F56BC2589C152554CAB9DDF2C82A228DCD72B40C60D6`

## Review Scope

This packet packages the `AUDIT_COMMAND_PROVENANCE_HARDENING` patch for external
review. The patch creates a forward-looking command provenance standard for
future Full Portfolio Capability Execution Audits.

The patch does not reconstruct previous audit commands and does not claim that
old audit artifacts are now fully reproduced. It defines how future audits must
record command provenance deterministically at execution or inspection time.

## Primary Review Files

Inside the ZIP, start with:

1. `docs/contracts/AUDIT_COMMAND_PROVENANCE_CONTRACT.md`
2. `examples/audit_command_provenance/audit_run_manifest.example.json`
3. `src/audit_command_provenance.py`
4. `tests/test_audit_command_provenance.py`
5. `docs/governance/FULL_PORTFOLIO_CAPABILITY_EXECUTION_AUDIT_ACCEPTANCE.md`
6. `external_review_packet/FULL_PORTFOLIO_CAPABILITY_EXECUTION_AUDIT_REPORT.md`
7. `external_review_packet/AUDIT_CAPABILITY_EXECUTION_MATRIX.csv`
8. `external_review_packet/AUDIT_VALIDATION_EVIDENCE.md`
9. `HANDOFF_MANIFEST.csv`
10. `HANDOFF_ARTIFACT_INDEX.csv`
11. `HANDOFF_CHANGE_CLASSIFICATION.csv`
12. `HANDOFF_VALIDATION.txt`

## ZIP Policy

`HANDOFF_LATEST.zip` remains an ignored/untracked upload and transport artifact.
It is not force-added to Git. `HANDOFF_LATEST.sha256` is the committed integrity
pointer for the externally supplied ZIP.

## Boundary

This packet is governance and audit provenance evidence only. It does not
implement feature logic, change scoring/ranking/valuation/portfolio rules,
publish private/raw/generated personal portfolio data, execute orders, create
broker writes, enable auto-trading, or claim production/investment readiness.

Human Operator remains final acceptance authority. External review must not
infer omitted private/raw/broker/provider/local/generated data.
