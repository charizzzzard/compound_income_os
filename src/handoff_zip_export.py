from __future__ import annotations

import argparse
import hashlib
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from src.common import ROOT, resolve_repo_path

INCLUDED_DIRS = ("src", "tests", "docs", "configs", "scripts", "website")
INCLUDED_ROOT_FILES = ("README.md", "AGENTS.md", "pyproject.toml", "requirements.txt")
METADATA_FILES = ("ZIP_REPO_BRANCH.txt", "ZIP_REPO_HEAD.txt", "ZIP_REPO_STATUS.txt", "ZIP_REPO_EXPORT_NOTES.txt")
EXPECTED_REQUIRED_PATHS = ("src", "tests", "docs", "configs", "README.md")
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
)
LOCAL_ROOT_EXCLUDES = {"personal_sec_identity_map.csv", "personal_sec_scope_review_filled.csv", "lokales_Dashboard.txt"}
FORBIDDEN_PREFIXES = (
    ".git/",
    ".venv/",
    "venv/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "node_modules/",
    "website/compound-income-os-landing/node_modules/",
    "website/compound-income-os-landing/dist/",
    "reports/",
    "outputs/",
    "data/raw/private/",
)
FORBIDDEN_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules", "dist", "deploy_artifacts"}
FORBIDDEN_FILE_NAMES = {".env", ".env.local"}
FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


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


def run_git(args: list[str], repo_root: Path, *, allow_failure: bool = False) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0 and not allow_failure:
        raise RuntimeError(output or f"git {' '.join(args)} failed with exit code {result.returncode}")
    return output


def normalize_entry_name(path_value: str) -> str:
    return str(path_value).replace("\\", "/").lstrip("/")


def is_allowed_handoff_artifact(entry_name: str) -> bool:
    name = normalize_entry_name(entry_name)
    if name in HANDOFF_ARTIFACT_FILES:
        return True
    if name.startswith("reports/") and name.endswith("/personal_profile_review_unlock_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_missing_kpi_closure_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_evidence_applied_downstream_delta_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_kpi_tier_coverage_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/strategy_review_fundamentals_trust_scoring.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_artifact_reconciliation_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_kpi_provenance_audit_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_score_audit_provenance_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_monthly_action_schema_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_watchlist_input_gate_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_artifact_freshness_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_valuation_input_contract_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_core_kpi_closure_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_dividend_fcf_input_contract_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_readiness_status_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_private_input_review_report.md"):
        return len(name.split("/")) == 3
    if name.startswith("reports/") and name.endswith("/personal_private_input_apply_candidates_report.md"):
        return len(name.split("/")) == 3
    return False


def is_forbidden_entry(entry_name: str) -> bool:
    name = normalize_entry_name(entry_name)
    if not name:
        return False
    if is_allowed_handoff_artifact(name):
        return False
    first_part = name.split("/", 1)[0]
    parts = set(name.split("/"))
    if first_part in LOCAL_ROOT_EXCLUDES:
        return True
    if name.endswith(".zip"):
        return True
    if name.rsplit("/", 1)[-1] in FORBIDDEN_FILE_NAMES:
        return True
    if name.rsplit("/", 1)[-1].startswith(".env.") and name.endswith(".local"):
        return True
    if any(name.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        return True
    if "tests/_tmp" in name or name.startswith("tests/_tmp"):
        return True
    return bool(parts.intersection(FORBIDDEN_DIR_NAMES))


def missing_expected_paths(repo_root: Path) -> tuple[str, ...]:
    missing = []
    for rel_path in EXPECTED_REQUIRED_PATHS:
        if not (repo_root / rel_path).exists():
            missing.append(rel_path)
    return tuple(missing)


def iter_included_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for rel_dir in INCLUDED_DIRS:
        dir_path = repo_root / rel_dir
        if not dir_path.is_dir():
            continue
        for path in sorted(dir_path.rglob("*")):
            if not path.is_file():
                continue
            rel_name = normalize_entry_name(path.relative_to(repo_root).as_posix())
            if is_forbidden_entry(rel_name):
                continue
            files.append(path)
    for rel_file in (*INCLUDED_ROOT_FILES, *METADATA_FILES):
        path = repo_root / rel_file
        if path.is_file() and not is_forbidden_entry(rel_file):
            files.append(path)
    for rel_file in HANDOFF_ARTIFACT_FILES:
        path = repo_root / rel_file
        if path.is_file() and not is_forbidden_entry(rel_file):
            files.append(path)
    for rel_glob in HANDOFF_ARTIFACT_GLOBS:
        for path in sorted(repo_root.glob(rel_glob)):
            if path.is_file():
                rel_name = normalize_entry_name(path.relative_to(repo_root).as_posix())
                if not is_forbidden_entry(rel_name):
                    files.append(path)
    return sorted(set(files), key=lambda item: normalize_entry_name(item.relative_to(repo_root).as_posix()))


def write_metadata_files(repo_root: Path, *, branch: str, head: str, short_head: str, status_text: str, missing_expected: tuple[str, ...]) -> None:
    (repo_root / "ZIP_REPO_BRANCH.txt").write_text(f"{branch}\n", encoding="utf-8")
    (repo_root / "ZIP_REPO_HEAD.txt").write_text(f"full_head={head}\nshort_head={short_head}\n", encoding="utf-8")
    (repo_root / "ZIP_REPO_STATUS.txt").write_text(status_text.rstrip() + "\n", encoding="utf-8")
    notes = [
        "Compound Income OS handoff export",
        f"created_at_utc={datetime.now(UTC).isoformat(timespec='seconds')}",
        f"branch={branch}",
        f"head={head}",
        f"short_head={short_head}",
        "included_paths=src/, tests/, docs/, configs/, scripts/ if present, README.md, AGENTS.md if present, pyproject.toml if present, requirements.txt if present, ZIP_REPO_*.txt, explicit handoff artifacts",
        "handoff_artifacts=data/processed/personal_profile_review_unlock_summary.csv, data/processed/personal_profile_review_unlock_holdings.csv, data/processed/personal_missing_kpi_closure_summary.csv, data/processed/personal_missing_kpi_closure_holdings.csv, data/processed/personal_evidence_applied_downstream_delta_summary.csv, data/processed/personal_evidence_applied_downstream_delta_holdings.csv, data/processed/personal_kpi_tier_coverage.csv, data/processed/personal_artifact_reconciliation_summary.csv, data/processed/personal_artifact_reconciliation_checks.csv, data/processed/personal_kpi_provenance_audit.csv, data/processed/personal_kpi_provenance_summary.csv, data/processed/personal_score_audit_provenance.csv, data/processed/personal_score_audit_provenance_summary.csv, data/processed/personal_monthly_action_compatibility.csv, data/processed/personal_monthly_action_compatibility_summary.csv, data/processed/personal_watchlist_input_gate.csv, data/processed/personal_watchlist_input_gate_summary.csv, data/processed/personal_artifact_freshness_checks.csv, data/processed/personal_artifact_freshness_summary.csv, data/processed/personal_valuation_input_review_queue.csv, data/processed/personal_valuation_input_contract_summary.csv, data/processed/personal_core_kpi_closure_queue.csv, data/processed/personal_core_kpi_closure_summary.csv, data/processed/personal_dividend_fcf_input_review_queue.csv, data/processed/personal_dividend_fcf_input_contract_summary.csv, data/processed/personal_readiness_status_summary.csv, data/processed/personal_readiness_blockers.csv, data/processed/personal_readiness_next_actions.csv, data/processed/personal_private_input_review_validation.csv, data/processed/personal_private_input_review_summary.csv, data/processed/personal_private_input_apply_candidates_sanitized.csv, data/processed/personal_private_input_apply_candidates_summary.csv, reports/*/personal_profile_review_unlock_report.md, reports/*/personal_missing_kpi_closure_report.md, reports/*/personal_evidence_applied_downstream_delta_report.md, reports/*/personal_kpi_tier_coverage_report.md, reports/*/strategy_review_fundamentals_trust_scoring.md, reports/*/personal_artifact_reconciliation_report.md, reports/*/personal_kpi_provenance_audit_report.md, reports/*/personal_score_audit_provenance_report.md, reports/*/personal_monthly_action_schema_report.md, reports/*/personal_watchlist_input_gate_report.md, reports/*/personal_artifact_freshness_report.md, reports/*/personal_valuation_input_contract_report.md, reports/*/personal_core_kpi_closure_report.md, reports/*/personal_dividend_fcf_input_contract_report.md, reports/*/personal_readiness_status_report.md, reports/*/personal_private_input_review_report.md, reports/*/personal_private_input_apply_candidates_report.md",
        "excluded_paths=.git/, .venv/, venv/, __pycache__/, .pytest_cache/, .mypy_cache/, .ruff_cache/, deploy_artifacts/, reports/ except explicit handoff artifacts, outputs/, data/raw/private/, tests/_tmp*, *.zip, .env secrets, local root private files",
        f"MISSING_EXPECTED={', '.join(missing_expected) if missing_expected else 'none'}",
    ]
    (repo_root / "ZIP_REPO_EXPORT_NOTES.txt").write_text("\n".join(notes) + "\n", encoding="utf-8")


def remove_metadata_files(repo_root: Path) -> None:
    for rel_file in METADATA_FILES:
        path = repo_root / rel_file
        if path.exists():
            path.unlink()


def write_zip(zip_path: Path, repo_root: Path, files: Iterable[Path]) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            entry_name = normalize_entry_name(path.relative_to(repo_root).as_posix())
            info = zipfile.ZipInfo(entry_name, date_time=FIXED_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def scan_forbidden_entries(zip_path: Path) -> tuple[str, ...]:
    with zipfile.ZipFile(zip_path, "r") as archive:
        return tuple(sorted(name for name in archive.namelist() if is_forbidden_entry(name)))


def zip_top_level_contents(zip_path: Path) -> tuple[str, ...]:
    with zipfile.ZipFile(zip_path, "r") as archive:
        return tuple(sorted({name.split("/", 1)[0] for name in archive.namelist() if name}))


def validate_zip_required_entries(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = set(archive.namelist())
        for required_file in ("ZIP_REPO_HEAD.txt", "ZIP_REPO_STATUS.txt"):
            if required_file not in names:
                raise ValueError(f"handoff zip missing required metadata file: {required_file}")
        for required_dir in ("src/", "tests/"):
            if not any(name.startswith(required_dir) for name in names):
                raise ValueError(f"handoff zip missing required directory: {required_dir}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def export_handoff_zip(repo_root: str | Path = ROOT, output_dir: str | Path | None = None) -> HandoffExportResult:
    root = resolve_repo_path(repo_root).resolve()
    target_dir = resolve_repo_path(output_dir).resolve() if output_dir else root
    target_dir.mkdir(parents=True, exist_ok=True)

    branch = run_git(["branch", "--show-current"], root)
    head = run_git(["rev-parse", "HEAD"], root)
    short_head = run_git(["rev-parse", "--short", "HEAD"], root)
    status_text = run_git(["status", "--short"], root, allow_failure=True)
    missing_expected = missing_expected_paths(root)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_path = target_dir / f"compound_income_os_HANDOFF_{timestamp}_{short_head}.zip"

    write_metadata_files(root, branch=branch, head=head, short_head=short_head, status_text=status_text, missing_expected=missing_expected)
    try:
        files = iter_included_files(root)
        write_zip(zip_path, root, files)
    finally:
        remove_metadata_files(root)

    validate_zip_required_entries(zip_path)
    forbidden_matches = scan_forbidden_entries(zip_path)
    file_count = 0
    with zipfile.ZipFile(zip_path, "r") as archive:
        file_count = len(archive.namelist())
        archive.testzip()
    result = HandoffExportResult(
        zip_path=zip_path,
        branch=branch,
        head=head,
        short_head=short_head,
        file_count=file_count,
        size_bytes=zip_path.stat().st_size,
        sha256=sha256_file(zip_path),
        forbidden_matches=forbidden_matches,
        missing_expected=missing_expected,
        top_level_contents=zip_top_level_contents(zip_path),
    )
    if forbidden_matches:
        raise ValueError(f"handoff zip contains forbidden entries: {', '.join(forbidden_matches)}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a clean Compound Income OS handoff ZIP with forbidden-entry validation.")
    parser.add_argument("--repo-root", default=str(ROOT), help="Repository root to export.")
    parser.add_argument("--output-dir", default="", help="Directory for the handoff ZIP. Defaults to repo root.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = export_handoff_zip(args.repo_root, args.output_dir or None)
    print(f"ZIP path: {result.zip_path}")
    print(f"HEAD: {result.head}")
    print(f"branch: {result.branch}")
    print(f"file_count: {result.file_count}")
    print(f"size_bytes: {result.size_bytes}")
    print(f"sha256: {result.sha256}")
    print(f"forbidden_match_count: {len(result.forbidden_matches)}")
    print(f"missing_expected_files: {', '.join(result.missing_expected) if result.missing_expected else 'none'}")
    print(f"top_level_contents: {', '.join(result.top_level_contents)}")


if __name__ == "__main__":
    main()
