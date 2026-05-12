from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from src.common import ROOT, resolve_repo_path
from src.handoff_bundle import (
    HandoffBundleResult,
    export_handoff_bundle,
    is_forbidden_entry as bundle_forbidden_entry,
    normalize_entry_name,
    omitted_row,
    scan_forbidden_entries as bundle_scan_forbidden_entries,
    zip_top_level_contents,
)

INCLUDED_DIRS = ("src", "tests", "docs", "configs", "scripts", "website", "_archive")
INCLUDED_ROOT_FILES = ("README.md", "AGENTS.md", "pyproject.toml", "requirements.txt")
HANDOFF_ARTIFACT_FILES = (
    "data/processed/personal_profile_review_unlock_summary.csv",
    "data/processed/personal_profile_review_unlock_holdings.csv",
    "data/processed/personal_missing_kpi_closure_summary.csv",
    "data/processed/personal_missing_kpi_closure_holdings.csv",
    "data/processed/personal_evidence_applied_downstream_delta_summary.csv",
    "data/processed/personal_evidence_applied_downstream_delta_holdings.csv",
    "data/processed/personal_kpi_tier_coverage.csv",
    "data/processed/personal_artifact_reconciliation_summary.csv",
    "data/processed/personal_artifact_reconciliation_checks.csv",
    "data/processed/personal_kpi_provenance_audit.csv",
    "data/processed/personal_kpi_provenance_summary.csv",
    "data/processed/personal_score_audit_provenance.csv",
    "data/processed/personal_score_audit_provenance_summary.csv",
    "data/processed/personal_monthly_action_compatibility.csv",
    "data/processed/personal_monthly_action_compatibility_summary.csv",
    "data/processed/personal_watchlist_input_gate.csv",
    "data/processed/personal_watchlist_input_gate_summary.csv",
    "data/processed/personal_artifact_freshness_checks.csv",
    "data/processed/personal_artifact_freshness_summary.csv",
    "data/processed/personal_valuation_input_review_queue.csv",
    "data/processed/personal_valuation_input_contract_summary.csv",
    "data/processed/personal_core_kpi_closure_queue.csv",
    "data/processed/personal_core_kpi_closure_summary.csv",
    "data/processed/personal_dividend_fcf_input_review_queue.csv",
    "data/processed/personal_dividend_fcf_input_contract_summary.csv",
    "data/processed/personal_readiness_status_summary.csv",
    "data/processed/personal_readiness_blockers.csv",
    "data/processed/personal_readiness_next_actions.csv",
    "data/processed/personal_private_input_review_validation.csv",
    "data/processed/personal_private_input_review_summary.csv",
    "data/processed/personal_private_input_apply_candidates_sanitized.csv",
    "data/processed/personal_private_input_apply_candidates_summary.csv",
    "data/processed/personal_sec_core_kpi_refresh_plan.csv",
    "data/processed/personal_sec_core_kpi_refresh_plan_summary.csv",
    "data/processed/personal_sec_refresh_preflight.csv",
    "data/processed/personal_sec_refresh_preflight_summary.csv",
    "data/processed/personal_sec_core_refresh_execution_readiness.csv",
    "data/processed/personal_sec_core_refresh_execution_readiness_summary.csv",
    "data/processed/personal_sec_core_refresh_impact_summary.csv",
    "data/processed/personal_sec_core_refresh_impact_holdings.csv",
    "data/processed/personal_sec_kpi_extraction_gap_matrix.csv",
    "data/processed/personal_sec_kpi_extraction_concept_candidates.csv",
    "data/processed/personal_sec_kpi_extraction_gap_summary.csv",
    "data/processed/personal_sec_companyfacts_concept_review_table.csv",
    "data/processed/personal_sec_companyfacts_concept_review_summary.csv",
    "data/processed/dashboard_readiness_panel.csv",
    "data/processed/dashboard_readiness_blockers.csv",
    "data/processed/dashboard_readiness_next_actions.csv",
    "data/processed/dashboard_readiness_payload.json",
    "data/processed/website_private_preview_route_matrix.csv",
    "data/processed/website_private_preview_cta_matrix.csv",
    "data/processed/website_private_preview_copy_guardrails.csv",
    "data/processed/website_private_preview_qa_summary.csv",
    "data/processed/website_static_build_package_qa.csv",
    "data/processed/website_static_build_package_summary.csv",
    "data/processed/website_private_preview_copy_freeze_matrix.csv",
    "data/processed/website_private_preview_copy_freeze_summary.csv",
    "data/processed/website_private_preview_handoff_index.csv",
    "data/processed/website_private_preview_release_summary.csv",
    "data/processed/website_private_preview_handoff_zip_content_index.csv",
    "data/processed/website_private_preview_handoff_qa_summary.csv",
)
HANDOFF_ARTIFACT_GLOBS = (
    "reports/*/personal_profile_review_unlock_report.md",
    "reports/*/personal_missing_kpi_closure_report.md",
    "reports/*/personal_evidence_applied_downstream_delta_report.md",
    "reports/*/personal_kpi_tier_coverage_report.md",
    "reports/*/strategy_review_fundamentals_trust_scoring.md",
    "reports/*/personal_artifact_reconciliation_report.md",
    "reports/*/personal_kpi_provenance_audit_report.md",
    "reports/*/personal_score_audit_provenance_report.md",
    "reports/*/personal_monthly_action_schema_report.md",
    "reports/*/personal_watchlist_input_gate_report.md",
    "reports/*/personal_artifact_freshness_report.md",
    "reports/*/personal_valuation_input_contract_report.md",
    "reports/*/personal_core_kpi_closure_report.md",
    "reports/*/personal_dividend_fcf_input_contract_report.md",
    "reports/*/personal_readiness_status_report.md",
    "reports/*/personal_private_input_review_report.md",
    "reports/*/personal_private_input_apply_candidates_report.md",
    "reports/*/personal_sec_core_kpi_refresh_plan_report.md",
    "reports/*/personal_sec_refresh_preflight_report.md",
    "reports/*/personal_sec_core_refresh_execution_readiness_report.md",
    "reports/*/personal_sec_core_refresh_impact_report.md",
    "reports/*/personal_sec_kpi_extraction_gap_review_report.md",
    "reports/*/personal_sec_companyfacts_concept_review_table_report.md",
    "reports/*/dashboard_readiness_panel_report.md",
    "reports/*/dashboard_readiness_payload_report.md",
    "reports/*/website_private_preview_route_matrix_report.md",
    "reports/*/website_static_build_package_report.md",
    "reports/*/website_private_preview_copy_freeze_report.md",
    "reports/*/website_private_preview_release_notes.md",
    "reports/*/website_private_preview_handoff_qa_report.md",
)
PATCH_FILE_LISTS = {
    "sec_companyfacts_concept_review": (
        "_archive/sec/src/personal_sec_kpi_extraction_gap_review.py",
        "_archive/sec/tests/test_personal_sec_kpi_extraction_gap_review.py",
        "data/processed/personal_sec_kpi_extraction_gap_matrix.csv",
        "data/processed/personal_sec_kpi_extraction_concept_candidates.csv",
        "data/processed/personal_sec_kpi_extraction_gap_summary.csv",
        "reports/2026-04-27/personal_sec_kpi_extraction_gap_review_report.md",
        "_archive/sec/src/personal_sec_companyfacts_concept_review_table.py",
        "_archive/sec/tests/test_personal_sec_companyfacts_concept_review_table.py",
        "data/processed/personal_sec_companyfacts_concept_review_table.csv",
        "data/processed/personal_sec_companyfacts_concept_review_summary.csv",
        "reports/2026-04-27/personal_sec_companyfacts_concept_review_table_report.md",
    ),
    "unified_handoff_export_system": (
        "src/handoff_bundle.py",
        "src/handoff_zip_export.py",
        "src/patch_handoff_export.py",
        "tests/test_handoff_bundle.py",
        "tests/test_handoff_zip_export.py",
        "tests/test_patch_handoff_export.py",
        "docs/HANDOFF_CONTRACT.md",
        "docs/CODEX_TASKS/POST_ITERATION_QA.md",
    ),
}


@dataclass(frozen=True)
class HandoffExportResult:
    zip_path: Path
    branch: str
    head: str
    short_head: str
    file_count: int
    size_bytes: int
    sha256: str
    forbidden_matches: tuple[str, ...]
    missing_expected: tuple[str, ...]
    top_level_contents: tuple[str, ...]


def is_allowed_handoff_artifact(entry_name: str) -> bool:
    name = normalize_entry_name(entry_name)
    if name in HANDOFF_ARTIFACT_FILES:
        return True
    for glob_value in HANDOFF_ARTIFACT_GLOBS:
        if not glob_value.startswith("reports/*/"):
            continue
        suffix = glob_value.removeprefix("reports/*/")
        if name.startswith("reports/") and name.endswith(f"/{suffix}") and len(name.split("/")) == 3:
            return True
    return False


def is_forbidden_entry(entry_name: str) -> bool:
    name = normalize_entry_name(entry_name)
    if is_allowed_handoff_artifact(name):
        return False
    if name.startswith("reports/"):
        return True
    if name.startswith("data/processed/") and name not in HANDOFF_ARTIFACT_FILES:
        return True
    return bundle_forbidden_entry(name)


def scan_forbidden_entries(zip_path: str | Path) -> tuple[str, ...]:
    # Legacy public API keeps allowlisted report exceptions while using the
    # centralized forbidden rules for private/env/build artifacts.
    import zipfile

    with zipfile.ZipFile(zip_path, "r") as archive:
        return tuple(sorted(name for name in archive.namelist() if is_forbidden_entry(name)))


def existing_paths(repo_root: Path, rel_paths: list[str] | tuple[str, ...]) -> list[str]:
    return [path for path in rel_paths if (repo_root / path).is_file()]


def paths_from_globs(repo_root: Path, globs: list[str] | tuple[str, ...]) -> list[str]:
    paths: list[str] = []
    for glob_value in globs:
        paths.extend(normalize_entry_name(path.relative_to(repo_root).as_posix()) for path in sorted(repo_root.glob(glob_value)) if path.is_file())
    return paths


def recursive_profile_paths(repo_root: Path, dirs: tuple[str, ...]) -> list[str]:
    paths: list[str] = []
    for rel_dir in dirs:
        base = repo_root / rel_dir
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            rel_name = normalize_entry_name(path.relative_to(repo_root).as_posix())
            if not bundle_forbidden_entry(rel_name):
                paths.append(rel_name)
    return paths


def profile_include_paths(profile: str, name: str, repo_root: Path, explicit_includes: list[str] | None = None) -> list[str]:
    explicit = list(explicit_includes or [])
    if profile == "patch":
        return sorted(set(explicit or PATCH_FILE_LISTS.get(name, ())))
    if profile == "manifest_only":
        return []
    if profile == "data_closure":
        module_paths = recursive_profile_paths(repo_root, ("src", "tests", "docs", "configs"))
        personal_artifacts = [path for path in HANDOFF_ARTIFACT_FILES if path.startswith("data/processed/personal_")]
        personal_reports = [path for path in paths_from_globs(repo_root, HANDOFF_ARTIFACT_GLOBS) if path.startswith("reports/") and "/personal_" in path]
        return sorted(set(module_paths + existing_paths(repo_root, personal_artifacts) + personal_reports))
    if profile == "full_review":
        return sorted(set(recursive_profile_paths(repo_root, INCLUDED_DIRS) + existing_paths(repo_root, INCLUDED_ROOT_FILES) + existing_paths(repo_root, list(HANDOFF_ARTIFACT_FILES)) + paths_from_globs(repo_root, HANDOFF_ARTIFACT_GLOBS)))
    # preview preserves the previous broad source/context export with explicit allowlisted artifacts.
    return sorted(set(recursive_profile_paths(repo_root, INCLUDED_DIRS) + existing_paths(repo_root, INCLUDED_ROOT_FILES) + existing_paths(repo_root, list(HANDOFF_ARTIFACT_FILES)) + paths_from_globs(repo_root, HANDOFF_ARTIFACT_GLOBS)))


def default_omitted_artifacts(profile: str) -> list[dict[str, str]]:
    rows = [
        omitted_row("data/raw/private/**", "OMITTED_PRIVATE", "False", "False", "True", "Private raw inputs are never exported."),
        omitted_row("**/sec_user_agent.local.txt", "OMITTED_FORBIDDEN", "False", "False", "True", "User-agent files are never exported."),
        omitted_row("*.zip", "OMITTED_FORBIDDEN", "False", "False", "True", "Nested ZIPs are never exported."),
        omitted_row("**/__pycache__/**", "OMITTED_FORBIDDEN", "False", "False", "True", "Python cache directories are never exported."),
        omitted_row("**/*.pyc", "OMITTED_FORBIDDEN", "False", "False", "True", "Python bytecode files are never exported."),
        omitted_row("**/.pytest_cache/**", "OMITTED_FORBIDDEN", "False", "False", "True", "Test runner cache directories are never exported."),
        omitted_row("**/.mypy_cache/**", "OMITTED_FORBIDDEN", "False", "False", "True", "Type-checker cache directories are never exported."),
        omitted_row("**/.ruff_cache/**", "OMITTED_FORBIDDEN", "False", "False", "True", "Linter cache directories are never exported."),
        omitted_row("**/.cache/**", "OMITTED_FORBIDDEN", "False", "False", "True", "Generic local cache directories are never exported."),
        omitted_row("**/.DS_Store", "OMITTED_FORBIDDEN", "False", "False", "True", "OS metadata files are never exported."),
        omitted_row("**/Thumbs.db", "OMITTED_FORBIDDEN", "False", "False", "True", "OS metadata files are never exported."),
    ]
    if profile == "patch":
        rows.append(
            omitted_row(
                "data/raw/private/fundamentals/personal_sec_companyfacts_concept_approval_template.csv",
                "OMITTED_PRIVATE",
                "False",
                "False",
                "True",
                "Private manual approval input is referenced but not included.",
            )
        )
    return rows


def export_profile_handoff_zip(
    *,
    profile: str,
    name: str,
    repo_root: str | Path = ROOT,
    output_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    include_paths: list[str] | None = None,
    validation_summary: str = "",
    validation_commands: list[str] | None = None,
    validation_log: str = "",
) -> HandoffBundleResult:
    root = resolve_repo_path(repo_root).resolve()
    selected = profile_include_paths(profile, name, root, include_paths)
    return export_handoff_bundle(
        profile=profile,
        bundle_name=name or profile,
        include_paths=selected,
        repo_root=root,
        output_dir=output_dir,
        output_path=output_path,
        purpose=f"{profile} handoff for external LLM validation",
        validation_summary=validation_summary,
        validation_commands=validation_commands or (),
        validation_log=validation_log,
        recommended_next_step="MANUAL SEC CONCEPT APPROVAL FILL / PRIVATE INPUT ONLY" if profile == "patch" else "Review handoff package.",
        omitted_artifacts=default_omitted_artifacts(profile),
    )


def export_handoff_zip(repo_root: str | Path = ROOT, output_dir: str | Path | None = None) -> HandoffExportResult:
    result = export_profile_handoff_zip(profile="preview", name="preview", repo_root=repo_root, output_dir=output_dir)
    return HandoffExportResult(
        zip_path=result.zip_path,
        branch=result.branch,
        head=result.head,
        short_head=result.short_head,
        file_count=result.file_count,
        size_bytes=result.size_bytes,
        sha256=result.sha256,
        forbidden_matches=scan_forbidden_entries(result.zip_path),
        missing_expected=tuple(path for path in ("src", "tests", "docs", "configs", "README.md") if not (resolve_repo_path(repo_root) / path).exists()),
        top_level_contents=zip_top_level_contents(result.zip_path),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a unified Compound Income OS handoff ZIP.")
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--output-path", default="", help="Explicit ZIP path. Root-level ZIPs require this option.")
    parser.add_argument("--profile", default="preview", choices=["patch", "preview", "data_closure", "full_review", "manifest_only"])
    parser.add_argument("--name", default="")
    parser.add_argument("--include", action="append", default=[], help="Explicit file include for profile=patch; repeatable.")
    parser.add_argument("--patch-file-list", help="Known patch file-list name; defaults to --name.")
    parser.add_argument("--validation-summary", default="")
    parser.add_argument("--validation-command", action="append", default=[], help="Validation command already run for this bundle; repeatable.")
    parser.add_argument("--validation-log", default="", help="Optional path to a validation log to embed as text.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    name = args.name or args.patch_file_list or args.profile
    includes = args.include or list(PATCH_FILE_LISTS.get(args.patch_file_list or "", ()))
    validation_log = ""
    if args.validation_log:
        validation_log = resolve_repo_path(args.validation_log).read_text(encoding="utf-8")
    result = export_profile_handoff_zip(
        profile=args.profile,
        name=name,
        repo_root=args.repo_root,
        output_dir=args.output_dir or None,
        output_path=args.output_path or None,
        include_paths=includes or None,
        validation_summary=args.validation_summary,
        validation_commands=args.validation_command,
        validation_log=validation_log,
    )
    print(f"ZIP path: {result.zip_path}")
    print(f"HEAD: {result.head}")
    print(f"branch: {result.branch}")
    print(f"profile: {result.profile}")
    print(f"bundle_name: {result.bundle_name}")
    print(f"file_count: {result.file_count}")
    print(f"size_bytes: {result.size_bytes}")
    print(f"zip_sha256: {result.sha256}")
    print(f"forbidden_match_count: {len(bundle_scan_forbidden_entries(result.zip_path))}")


if __name__ == "__main__":
    main()
