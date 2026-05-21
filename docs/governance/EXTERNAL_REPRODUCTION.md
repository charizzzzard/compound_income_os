# External Reproduction Matrix

## Purpose

The external handoff is a review bundle without private/raw artifacts. It is
designed for LLM/code review of committed source, tests, docs, configs and
selected non-private review context.

Not every locally executed test must be reproducible from the ZIP alone. Private
broker documents, raw personal inputs, ignored processed artifacts and local
operator files are intentionally excluded.

## Test Categories

Use these labels when reporting validation:

| label | meaning | ZIP-only expectation |
| --- | --- | --- |
| `ZIP_SAFE` | Can be inspected from extracted ZIP content without running code. | Yes. |
| `ZIP_SAFE_WITH_PYTHON` | Can run from an extracted ZIP with repo files, Python and included synthetic fixtures. | Yes, if the Python version and stdlib assumptions match. |
| `LOCAL_REPO_REQUIRED` | Requires a real local checkout shape or generated local artifacts outside the review ZIP. | No. |
| `GIT_CONTEXT_REQUIRED` | May call Git or rely on committed/ignored status, branch, HEAD or local repo metadata. | No, unless the ZIP is unpacked inside a Git checkout with matching history. |
| `PRIVATE_INPUT_REQUIRED` | Requires private/raw/broker/operator-owned inputs. | No. |
| `RUNTIME_DATA_REQUIRED` | Requires generated processed/runtime data not included in the handoff. | No. |

### `ZIP_SAFE_TESTS`

Tests in this category are expected to run from repository source and synthetic
fixtures included in the handoff, subject to the Python environment matching the
project's standard-library-first assumptions.

Recommended examples:

- `python -m unittest tests.test_data_source_registry_validation -v`
- `python -m src.data_source_registry_validation docs/architecture/CIOS_DATA_SOURCE_REGISTRY_TEMPLATE.yaml`
- `python -m unittest tests.test_personal_decision_journal_validation -v`
- `python -m unittest tests.test_monthly_decision_report -v`
- `python -m unittest tests.test_personal_decision_quality_state -v`
- `python -m unittest tests.test_data_freshness -v`
- `python -m unittest tests.test_readme_and_reports -v`

The registry-template validator is `ZIP_SAFE_WITH_PYTHON`: it reads only the
template and contract-shaped local YAML data and must not contact providers,
networks or private inputs.

`tests.test_readme_and_reports` is ZIP-safe only when the bundle includes
root-level LF governance files such as `.gitattributes`.

Handoff exporter and bundle tests such as
`python -m unittest tests.test_handoff_zip_export -v` and
`python -m unittest tests.test_handoff_bundle -v` are local-repo validation
tests. They may inspect Git state, ignored-path policy, exporter context or
local handoff behavior and should be reported as `LOCAL_REPO_REQUIRED` or
`GIT_CONTEXT_REQUIRED`, not as ZIP-only smoke tests.

### `REQUIRES_PRIVATE_FIXTURES`

Tests or workflows in this category require private/raw broker, portfolio,
fundamentals or local document inputs. Those inputs must not be inferred from
the ZIP and must not be added to review bundles.

Examples:

- workflows that parse real local broker documents,
- workflows that require private `data/raw/private/` content,
- workflows that depend on the operator's real personal master or watchlist.

### `RUNTIME_OR_DATA_DEPENDENT_TESTS`

Tests in this category may be deterministic in the local repo but can depend on
generated processed outputs, private configured paths or larger orchestration
context. They are useful for local validation, but external reviewers should not
infer missing private/provider inputs from a ZIP-only failure.

Examples:

- full `personal_run_engine` end-to-end paths that expect local source configs,
- dashboard/server checks that read ignored processed artifacts,
- any test requiring real broker, provider, paid-vendor or operator-owned raw
  input files.

### `LOCAL_ONLY_VALIDATION`

Tests or validation steps in this category may rely on ignored local artifacts,
current local reports, local handoff archives or generated processed outputs
that are deliberately not committed.

Examples:

- validation of a local `external_review_packet/HANDOFF_LATEST.zip`,
- checks against ignored `data/processed/` artifacts,
- checks against local dated reports under `reports/`.

### `OPTIONAL_ENVIRONMENTAL`

Optional environment-dependent checks may vary by machine. They are useful but
must not be reported as passed unless actually executed.

Examples:

- `pytest` availability,
- line-ending behavior,
- local shell support for heredoc syntax,
- external ZIP extraction policy.

## Current Recommended External Test Strategy

For a review focused on Decision Quality, Decision Journal Validation and
operator surfaces, start with:

```powershell
python -m unittest tests.test_personal_decision_journal_validation -v
python -m unittest tests.test_monthly_decision_report -v
python -m unittest tests.test_personal_decision_quality_state -v
python -m unittest tests.test_data_source_registry_validation -v
python -m unittest tests.test_data_freshness -v
python -m unittest tests.test_personal_run_engine -v
python -m unittest tests.test_readme_and_reports -v
```

Then run any additional targeted tests named in
`external_review_packet/HANDOFF_LATEST_CONTEXT.md`.

Architecture review artifacts that are ZIP-review relevant include:

- `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
- `docs/architecture/CIOS_META_ARCHITECTURE.md`
- `docs/architecture/CIOS_MATURITY_MODEL.yaml`
- `docs/architecture/CIOS_DATA_SOURCE_STRATEGY.md`
- `docs/architecture/CIOS_DATA_SOURCE_REGISTRY_TEMPLATE.yaml`
- `src/data_source_registry_validation.py`
- `tests/test_data_source_registry_validation.py`
- `docs/architecture/PERSONAL_RUN_STAGE_DAG.md`
- `docs/governance/CIOS_SYSTEM_CONSTITUTION.md`
- `docs/governance/CIOS_OPERATING_MODEL.md`
- `docs/governance/CIOS_RISK_AND_CONTROL_FRAMEWORK.md`
- `docs/governance/CIOS_TRACEABILITY_STANDARD.md`
- `docs/governance/CIOS_EVOLUTION_GUARDRAILS.md`
- `docs/governance/CIOS_FINAL_META_BASELINE_ACCEPTANCE.md`
- `docs/contracts/DATA_FRESHNESS_STALENESS_CONTRACT.md`
- `docs/contracts/DATA_SOURCE_LICENSE_BOUNDARY_CONTRACT.md`
- `docs/governance/DATA_SOURCE_REVIEW_CHECKLIST.md`
- `docs/architecture/CIOS_FEATURE_STATUS.yaml`
- `docs/architecture/CURRENT_KNOWN_GAPS.md`

Do not claim a full test suite unless `python -m unittest discover -s tests -p
"test_*.py"` or an equivalent full-suite command was actually executed.

## Minimal External Smoke From Extracted ZIP

Assumption: Python 3.11+ or the repo-compatible local Python version is
available, and the working directory is the extracted handoff root.

Example smoke sequence:

```powershell
Expand-Archive .\HANDOFF_LATEST.zip -DestinationPath .\review
Set-Location .\review
python -m unittest tests.test_dashboard_operator_summary -v
python -m unittest tests.test_data_freshness -v
python -m unittest tests.test_personal_run_engine -v
python -m unittest tests.test_personal_decision_journal_validation -v
python -m unittest tests.test_personal_decision_quality_state -v
python -m unittest tests.test_readme_and_reports -v
```

The full-review handoff must include `.gitattributes` when this smoke sequence
is recommended, because the README/report tests validate LF-normalization
governance from that file.

These smoke tests do not replace local full validation. Private/raw fixtures are
intentionally absent from review bundles, and tests that require such fixtures
are not automatic patch failures when run from the ZIP alone.

## Handoff Interpretation

External reviewers should:

1. Verify `external_review_packet/HANDOFF_LATEST.sha256` against
   `external_review_packet/HANDOFF_LATEST.zip`.
2. Check ZIP integrity with `zipfile.testzip()`.
3. Read `external_review_packet/00_READ_ME_FIRST.md`.
4. Read `external_review_packet/HANDOFF_LATEST_CONTEXT.md`.
5. Treat the external context file as authoritative for current handoff head,
   scope, SHA and dirty-state interpretation.

ZIP-internal `HANDOFF_CONTEXT.md` is exporter context. If it reports
`dirty_worktree_present=True`, this can be caused by handoff SHA regeneration
and does not by itself prove uncommitted patch-source dirtiness.

Private/raw artifacts, credentials, local user-agent files, ignored personal
outputs and broker documents must not be inferred when absent from the bundle.
External reviewers must also not infer source-license approval from missing
raw/provider data. Public handoffs may include code, docs, configs, tests and
sanitized derived metadata; they must not bundle private broker exports, paid
raw vendor data, credentials, secrets or restricted raw datasets. Where
source/license metadata is present, review it against
`docs/contracts/DATA_SOURCE_LICENSE_BOUNDARY_CONTRACT.md`; absence of an active
source registry does not imply approval for redistribution or commercial use.
