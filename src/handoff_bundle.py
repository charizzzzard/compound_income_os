from __future__ import annotations

import csv
import hashlib
import io
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from src.common import ROOT, resolve_repo_path

FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
STANDARD_HANDOFF_ENTRIES = (
    "HANDOFF_CONTEXT.md",
    "HANDOFF_REPORT.md",
    "HANDOFF_MANIFEST.csv",
    "HANDOFF_ARTIFACT_INDEX.csv",
    "HANDOFF_GUARDRAILS.md",
    "HANDOFF_OMITTED_ARTIFACTS.csv",
    "HANDOFF_CHANGE_CLASSIFICATION.csv",
    "HANDOFF_PATCH_IDENTITY.md",
    "HANDOFF_VALIDATION.txt",
    "HANDOFF_GIT_STATUS_SANITIZED.txt",
    "HANDOFF_EXTERNAL_REVIEW_CHECKLIST.md",
)
FORBIDDEN_PATTERNS = (
    ".git/**",
    ".env",
    ".env.*",
    "**/.env",
    "**/.env.*",
    "data/raw/private/**",
    "**/sec_user_agent.local.txt",
    "**/*user_agent*",
    "**/personal_sec_identity_map.csv",
    "**/personal_sec_scope_review_filled.csv",
    "node_modules/**",
    "dist/**",
    "deploy_artifacts/**",
    "__pycache__/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    ".cache/**",
    "*.pyc",
    "*.zip",
    "*.log",
    ".DS_Store",
    "Thumbs.db",
    "tests/_tmp_*",
)
FORBIDDEN_PREFIXES = (
    ".git/",
    ".venv/",
    "venv/",
    "data/raw/private/",
    "node_modules/",
    "website/compound-income-os-landing/node_modules/",
    "website/compound-income-os-landing/dist/",
    "website/compound-income-os-landing/deploy_artifacts/",
    "outputs/",
)
FORBIDDEN_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache", "node_modules", "dist", "deploy_artifacts"}
FORBIDDEN_FILE_NAMES = {
    ".ds_store",
    ".env",
    ".env.local",
    "sec_user_agent.local.txt",
    "personal_sec_identity_map.csv",
    "personal_sec_scope_review_filled.csv",
    "thumbs.db",
}
TEXT_SCAN_SUFFIXES = {
    ".csv",
    ".css",
    ".html",
    ".json",
    ".md",
    ".py",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
}
PRODUCTIVE_LOCAL_PATH_PREFIXES = ("data/processed/", "reports/", "docs/", "README.md", "HANDOFF_")
PRODUCTIVE_WINDOWS_USER_RE = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/:\s\"'`<>|]+", re.IGNORECASE)
PRODUCTIVE_POSIX_USER_RE = re.compile(r"/(?:Users|home)/[^/\s\"'`<>|]+")
PRODUCTIVE_UNC_RE = re.compile(r"(?:\\\\|//)[^\\/\s\"'`<>|]+[\\/][^\\/\s\"'`<>|]+[\\/]")


def _current_operator_path_re() -> re.Pattern[str] | None:
    user_name = Path.home().name
    if not user_name:
        return None
    escaped = re.escape(user_name)
    return re.compile(
        rf"(?:[A-Za-z]:[\\/]+Users[\\/]+{escaped}[\\/]+|/(?:Users|home)/{escaped}/)",
        re.IGNORECASE,
    )


REAL_OPERATOR_PATH_RE = _current_operator_path_re()


@dataclass(frozen=True)
class HandoffBundleResult:
    zip_path: Path
    profile: str
    bundle_name: str
    branch: str
    head: str
    short_head: str
    file_count: int
    size_bytes: int
    sha256: str
    forbidden_matches: tuple[str, ...]
    included_entries: tuple[str, ...]
    omitted_rows: tuple[dict[str, str], ...]
    upload_ready_dir: Path | None = None


def normalize_entry_name(path_value: str | Path) -> str:
    return str(path_value).replace("\\", "/").lstrip("/")


def run_git(args: list[str], repo_root: Path, *, allow_failure: bool = False) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0 and not allow_failure:
        raise RuntimeError(output or f"git {' '.join(args)} failed with exit code {result.returncode}")
    return output


def parse_git_status_short_line(line: str) -> tuple[str, str]:
    if not line.strip():
        return "", ""
    if len(line) >= 3 and line[2] == " ":
        return line[:2].strip(), line[3:].strip()
    parts = line.strip().split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def is_forbidden_entry(entry_name: str) -> bool:
    name = normalize_entry_name(entry_name)
    if not name:
        return True
    basename = name.rsplit("/", 1)[-1]
    lowered = basename.lower()
    parts = set(name.split("/"))
    if name.endswith(".zip") or name.endswith(".log") or name.endswith(".pyc"):
        return True
    if lowered in FORBIDDEN_FILE_NAMES:
        return True
    if lowered.startswith(".env") or "user_agent" in lowered:
        return True
    if any(name.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        return True
    if name.startswith("tests/_tmp") or "/tests/_tmp" in name:
        return True
    return bool(parts.intersection(FORBIDDEN_DIR_NAMES))


def _is_text_scannable(entry_name: str) -> bool:
    suffix = Path(entry_name).suffix.lower()
    return suffix in TEXT_SCAN_SUFFIXES or entry_name.startswith("HANDOFF_") or entry_name == "README.md"


def _content_local_path_leak_reasons(entry_name: str, text: str) -> tuple[str, ...]:
    name = normalize_entry_name(entry_name)
    productive = name.startswith(PRODUCTIVE_LOCAL_PATH_PREFIXES) or name == "README.md"
    reasons: list[str] = []
    if productive:
        if PRODUCTIVE_WINDOWS_USER_RE.search(text):
            reasons.append("LOCAL_WINDOWS_USER_PATH")
        if PRODUCTIVE_POSIX_USER_RE.search(text):
            reasons.append("LOCAL_POSIX_USER_PATH")
        if PRODUCTIVE_UNC_RE.search(text):
            reasons.append("LOCAL_UNC_PATH")
    elif name.startswith(("src/", "tests/")):
        if REAL_OPERATOR_PATH_RE is not None and REAL_OPERATOR_PATH_RE.search(text):
            reasons.append("REAL_OPERATOR_LOCAL_PATH")
    return tuple(dict.fromkeys(reasons))


def sanitize_path_for_external(path_value: str) -> str:
    name = normalize_entry_name(path_value)
    basename = name.rsplit("/", 1)[-1].lower()
    if "user_agent" in basename or basename == "sec_user_agent.local.txt":
        return "<user_agent_file>"
    if "data/raw/private" in name:
        return "<private_raw_file>"
    if basename in {"personal_sec_identity_map.csv", "personal_sec_scope_review_filled.csv"}:
        return "<private_sec_review_file>"
    if name.endswith(".zip"):
        return "<local_zip>"
    if name.endswith(".log"):
        return "<local_log>"
    if basename.startswith(".env"):
        return "<env_file>"
    return name


def classify_change_path(path_value: str, included_entries: set[str]) -> dict[str, str]:
    raw_path = normalize_entry_name(path_value)
    display_path = sanitize_path_for_external(raw_path)
    if raw_path in included_entries:
        classification = "INCLUDED_IN_BUNDLE"
        included = "True"
        omitted_reason = ""
        safe = "True"
    elif is_forbidden_entry(raw_path):
        if display_path.startswith("<private"):
            classification = "OMITTED_PRIVATE"
        else:
            classification = "OMITTED_FORBIDDEN"
        included = "False"
        omitted_reason = "FORBIDDEN_PATH"
        safe = "False"
    elif raw_path.startswith("data/processed/") or raw_path.startswith("reports/"):
        classification = "SAFE_BUT_NOT_RELEVANT"
        included = "False"
        omitted_reason = "NOT_SELECTED_FOR_PROFILE"
        safe = "True"
    else:
        classification = "OMITTED_UNRELATED_DIRTY"
        included = "False"
        omitted_reason = "NOT_SELECTED_FOR_PROFILE"
        safe = "True"
    return {
        "path": display_path,
        "status": "",
        "change_type": "",
        "evidence_source": "git status --short",
        "delta_range": "",
        "included_in_zip": included,
        "classification": classification,
        "included": included,
        "omitted_reason": omitted_reason,
        "safe_for_external_review": safe,
        "notes": "",
    }


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def csv_bytes(fieldnames: list[str], rows: Iterable[dict[str, str]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fieldnames})
    return buffer.getvalue().encode("utf-8")


def resolve_include_paths(repo_root: Path, include_paths: Iterable[str | Path]) -> tuple[list[Path], list[dict[str, str]]]:
    files: list[Path] = []
    omitted: list[dict[str, str]] = []
    for item in include_paths:
        path = resolve_repo_path(item).resolve()
        try:
            rel_name = normalize_entry_name(path.relative_to(repo_root).as_posix())
        except ValueError:
            omitted.append(omitted_row(str(item), "OUTSIDE_REPO", "False", "True", "False", "Include path is outside repository."))
            continue
        if is_forbidden_entry(rel_name):
            omitted.append(omitted_row(rel_name, "FORBIDDEN_PATH", "False", "True", "False", "Central guardrail blocked this path."))
            continue
        if not path.is_file():
            omitted.append(omitted_row(rel_name, "MISSING_PATH", "False", "True", "False", "Requested include path does not exist."))
            continue
        files.append(path)
    return sorted(set(files), key=lambda path: normalize_entry_name(path.relative_to(repo_root).as_posix())), omitted


def omitted_row(
    artifact_path_or_category: str,
    omission_reason: str,
    safe_to_include: str,
    required_for_external_review: str,
    replacement_context_provided: str,
    notes: str,
) -> dict[str, str]:
    return {
        "artifact_path_or_category": sanitize_path_for_external(artifact_path_or_category),
        "omission_reason": omission_reason,
        "safe_to_include": safe_to_include,
        "required_for_external_review": required_for_external_review,
        "replacement_context_provided": replacement_context_provided,
        "notes": notes,
    }


def manifest_rows(repo_root: Path, files: list[Path], metadata_entries: dict[str, bytes], profile: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in files:
        rel_name = normalize_entry_name(path.relative_to(repo_root).as_posix())
        rows.append(
            {
                "entry_name": rel_name,
                "size_bytes": str(path.stat().st_size),
                "sha256": sha256_file(path),
                "entry_type": "file",
                "source_group": source_group(rel_name),
                "profile": profile,
                "required_for_review": "True",
            }
        )
    for entry_name, content in sorted(metadata_entries.items()):
        rows.append(
            {
                "entry_name": entry_name,
                "size_bytes": str(len(content)),
                "sha256": sha256_bytes(content),
                "entry_type": "metadata",
                "source_group": "handoff_metadata",
                "profile": profile,
                "required_for_review": "True",
            }
        )
    return sorted(rows, key=lambda row: row["entry_name"])


def artifact_index_rows(files: list[Path], repo_root: Path, included_entries: set[str]) -> list[dict[str, str]]:
    rows = []
    for path in files:
        rel_name = normalize_entry_name(path.relative_to(repo_root).as_posix())
        rows.append(
            {
                "artifact_path": rel_name,
                "artifact_kind": artifact_kind(rel_name),
                "semantic_role": semantic_role(rel_name),
                "produced_by": "",
                "consumed_by": "external_llm_validation",
                "included": str(rel_name in included_entries),
                "omission_reason": "",
                "notes": "",
            }
        )
    return sorted(rows, key=lambda row: row["artifact_path"])


def source_group(entry_name: str) -> str:
    if entry_name.startswith("src/"):
        return "source"
    if entry_name.startswith("tests/"):
        return "tests"
    if entry_name.startswith("data/processed/"):
        return "processed_artifacts"
    if entry_name.startswith("reports/"):
        return "reports"
    if entry_name.startswith("docs/"):
        return "docs"
    if entry_name.startswith("configs/"):
        return "configs"
    if entry_name.startswith("website/"):
        return "website_source"
    return "repo_context"


def artifact_kind(entry_name: str) -> str:
    if entry_name.endswith(".py"):
        return "python"
    if entry_name.endswith(".csv"):
        return "csv"
    if entry_name.endswith(".md"):
        return "markdown"
    if entry_name.endswith(".json"):
        return "json"
    return "file"


def semantic_role(entry_name: str) -> str:
    if entry_name.startswith("tests/"):
        return "validation_test"
    if entry_name.startswith("src/"):
        return "implementation"
    if entry_name.startswith("data/processed/"):
        return "generated_data_artifact"
    if entry_name.startswith("reports/"):
        return "generated_report"
    return "context"


def context_markdown(
    *,
    project_name: str,
    profile: str,
    bundle_name: str,
    branch: str,
    head: str,
    dirty_worktree_present: bool,
    purpose: str,
    base_head: str,
    delta_range: str,
    delta_row_count: int,
    patch_identity_entry: str,
    included_groups: list[str],
    omitted_groups: list[str],
    validation_summary: str,
) -> bytes:
    lines = [
        "# Handoff Context",
        "",
        f"- project_name: `{project_name}`",
        f"- profile: `{profile}`",
        f"- bundle_name: `{bundle_name}`",
        "- bundle_purpose: `external_llm_validation`",
        f"- created_at_utc: `{datetime.now(UTC).isoformat(timespec='seconds')}`",
        f"- branch: `{branch}`",
        f"- head: `{head}`",
        f"- base_head: `{base_head or 'UNKNOWN_DELTA_BASE'}`",
        f"- delta_range: `{delta_range or 'UNKNOWN_DELTA_RANGE'}`",
        f"- delta_evidence_rows: `{delta_row_count}`",
        f"- patch_identity_entry: `{patch_identity_entry}`",
        f"- dirty_worktree_present: `{dirty_worktree_present}`",
        f"- purpose: {purpose}",
        "",
        "## Included Artifact Groups",
    ]
    lines.extend(f"- `{group}`" for group in sorted(set(included_groups)))
    lines.extend(["", "## Omitted Artifact Groups"])
    lines.extend(f"- `{group}`" for group in (sorted(set(omitted_groups)) or ["none"]))
    lines.extend(
        [
            "",
            "## Validation Summary",
            validation_summary or "See HANDOFF_VALIDATION.txt.",
            "",
            "## External LLM Instructions",
            "- Use only included artifacts and explicitly documented omissions.",
            "- Do not infer private raw data, credentials, user-agent values, or omitted local files.",
            "- Treat generated CSV and report artifacts as the review evidence surface.",
            "- Check HANDOFF_CHANGE_CLASSIFICATION.csv before assuming dirty worktree state.",
            "- Check HANDOFF_PATCH_IDENTITY.md before treating a snapshot as patch-delta evidence.",
            "- HANDOFF_VALIDATION.txt records commands as RECORDED unless separate execution evidence says otherwise.",
        ]
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def patch_identity_markdown(
    *,
    patch_title: str,
    bundle_purpose: str,
    base_head: str,
    implementation_head: str,
    current_handoff_head: str,
    delta_range: str,
    changed_file_count: int,
    delta_evidence_status: str,
    change_classification_entry: str,
) -> bytes:
    lines = [
        "# Handoff Patch Identity",
        "",
        f"- patch_title: `{patch_title}`",
        f"- bundle_purpose: `{bundle_purpose}`",
        f"- base_head: `{base_head or 'UNKNOWN_DELTA_BASE'}`",
        f"- implementation_head: `{implementation_head}`",
        f"- current_handoff_head: `{current_handoff_head}`",
        f"- delta_range: `{delta_range or 'UNKNOWN_DELTA_RANGE'}`",
        f"- changed_file_count: `{changed_file_count}`",
        f"- delta_evidence_status: `{delta_evidence_status}`",
        f"- change_classification_entry: `{change_classification_entry}`",
        "",
        "## Evidence Classes",
        "",
        "- `SNAPSHOT_STATE`: file is present in the exported bundle at the handoff head.",
        "- `PATCH_DELTA`: file is part of the Git diff between base and implementation head.",
        "- `RECORDED_VALIDATION`: command is recorded in the handoff metadata but was not executed by the exporter.",
        "- `EXECUTED_IN_CURRENT_REPO`: command was actually run in the local checkout and reported by the operator/context.",
        "- `EXECUTED_IN_ZIP_CONTEXT`: command was actually run from extracted ZIP content.",
        "- `GIT_CONTEXT_REQUIRED`: evidence requires `.git` metadata.",
        "- `PRIVATE_INPUT_REQUIRED`: evidence requires private/raw inputs omitted from public handoff.",
        "- `TOOLING_OPTIONAL`: evidence depends on optional tools such as pytest or ruff.",
        "",
        "## Validation Result Semantics",
        "",
        "`HANDOFF_VALIDATION.txt` is generated by the exporter and lists commands as `RECORDED`.",
        "Those records are command provenance only. They are not pass/fail execution results unless an external context explicitly reports actual execution.",
        "",
        "## Boundary",
        "",
        "This artifact identifies patch evidence. It does not implement runtime enforcement, release acceptance, broker import, order execution, investment logic, valuation automation, dashboard expansion, replay, backtesting or outcome attribution.",
    ]
    if delta_evidence_status != "COMPLETE":
        lines.extend(
            [
                "",
                "## Delta Evidence Warning",
                "",
                f"Delta evidence status is `{delta_evidence_status}`. Treat this handoff as snapshot evidence plus partial/unknown delta evidence until Git context is available.",
            ]
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def report_markdown(
    *,
    profile: str,
    bundle_name: str,
    included_entries: list[str],
    omitted_rows: list[dict[str, str]],
    validation_summary: str,
    recommended_next_step: str,
) -> bytes:
    source_files = [entry for entry in included_entries if entry.startswith(("src/", "tests/"))]
    artifacts = [entry for entry in included_entries if entry.startswith(("data/processed/", "reports/"))]
    lines = [
        "# Handoff Report",
        "",
        "## Executive Summary",
        f"- profile: `{profile}`",
        f"- bundle_name: `{bundle_name}`",
        "- purpose: external LLM validation with unified context and guardrails.",
        "",
        "## Scope",
        "This ZIP contains only selected review-safe files plus standardized HANDOFF_* metadata.",
        "",
        "## Included Source/Test Files",
    ]
    lines.extend(f"- `{entry}`" for entry in source_files or ["none"])
    lines.extend(["", "## Included Data/Report Artifacts"])
    lines.extend(f"- `{entry}`" for entry in artifacts or ["none"])
    lines.extend(["", "## Known Omissions"])
    lines.extend(f"- `{row['artifact_path_or_category']}`: `{row['omission_reason']}`" for row in omitted_rows or [])
    if not omitted_rows:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Guardrail Confirmation",
            "- Private raw files are omitted.",
            "- User-agent and env files are omitted.",
            "- Nested ZIPs, logs, node_modules, dist and deploy artifacts are omitted.",
            "",
            "## Validation Commands",
            validation_summary or "See HANDOFF_VALIDATION.txt.",
            "",
            "## External Review Checklist",
            "- Confirm HANDOFF_MANIFEST.csv hashes match included files.",
            "- Confirm HANDOFF_OMITTED_ARTIFACTS.csv contains expected private omissions.",
            "- Confirm no forbidden entry appears in the archive.",
            "- Confirm profile-specific artifacts are sufficient for review.",
            "",
            "## Recommended Next Step",
            recommended_next_step or "Review included artifacts.",
        ]
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def guardrails_markdown(profile: str) -> bytes:
    lines = [
        "# Handoff Guardrails",
        "",
        f"- profile: `{profile}`",
        "",
        "## Forbidden Patterns",
    ]
    lines.extend(f"- `{pattern}`" for pattern in FORBIDDEN_PATTERNS)
    lines.extend(
        [
            "",
            "## Privacy Rules",
            "- Do not include private raw files.",
            "- Do not include user-agent files or environment files.",
            "- Do not include local ZIPs or logs.",
            "",
            "## Execution Confirmations",
            "- no_network_confirmation: profile dependent; this exporter performs no network fetch.",
            "- no_score_change_confirmation: exporter does not modify scoring logic.",
            "- no_value_apply_confirmation: exporter does not apply evidence or mutate data values.",
        ]
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def validation_text(
    *,
    validation_summary: str,
    validation_commands: Iterable[str],
    validation_log: str,
    forbidden_count: int,
    file_count: int,
    nested_zip_count: int,
    local_path_leak_count: int,
    manifest_sha256: str,
    manifest_row_count: int,
    terminal_metadata_count: int,
    sha256_verified: str = "ARCHIVE_SHA256_CALCULATED_AFTER_WRITE",
    context_match: str = "INTERNAL_EXTERNAL_MATCH_VALIDATED_ON_LATEST_PUBLISH",
    latest_archive_hash_match: str = "VALIDATED_DURING_LATEST_PUBLISH",
    validation_status: str = "SELF_VALIDATION_RECORDED",
) -> bytes:
    commands = [str(command).strip() for command in validation_commands if str(command).strip()]
    lines = [
        "HANDOFF VALIDATION",
        "commands_run:",
    ]
    if commands:
        for command in commands:
            lines.extend([f"- command: {command}", "  status: RECORDED", "  execution_status: RECORDED_VALIDATION"])
    else:
        lines.extend(["- command: self_validation_only", "  status: RECORDED", "  execution_status: RECORDED_VALIDATION"])
    summary_text = validation_summary or (
        "Validation commands recorded below." if commands else "Self-validation recorded by handoff exporter."
    )
    lines.extend(["", "validation_summary:", summary_text])
    if validation_log.strip():
        lines.extend(["", "validation_log:", validation_log.strip()])
    lines.extend(["", "validation_results:"])
    lines.extend(
        [
            "zip_integrity=OK",
            f"sha256_verified={sha256_verified}",
            f"file_count={file_count}",
            f"forbidden_count={forbidden_count}",
            f"nested_zip_count={nested_zip_count}",
            f"local_path_leak_count={local_path_leak_count}",
            f"context_match={context_match}",
            f"latest_archive_hash_match={latest_archive_hash_match}",
            f"validation_status={validation_status}",
            f"manifest_sha256={manifest_sha256}",
            f"manifest_row_count={manifest_row_count}",
            f"terminal_metadata_count={terminal_metadata_count}",
            f"manifest_file_count_delta={file_count - manifest_row_count}",
            "manifest_file_count_note=HANDOFF_MANIFEST.csv is generated before terminal metadata entries HANDOFF_MANIFEST.csv and HANDOFF_VALIDATION.txt are written; ZIP file_count includes those terminal metadata files.",
        ]
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def parse_context_metadata(context_text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in context_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        metadata[key.strip()] = value.strip().strip("`").strip()
    return metadata


def parse_validation_metadata(validation_text_value: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in validation_text_value.splitlines():
        stripped = line.strip()
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def scan_local_path_leaks_in_zip(zip_path: str | Path) -> tuple[str, ...]:
    findings: list[str] = []
    with zipfile.ZipFile(zip_path, "r") as archive:
        for name in archive.namelist():
            entry_name = normalize_entry_name(name)
            if not entry_name or entry_name.endswith("/") or not _is_text_scannable(entry_name):
                continue
            try:
                text = archive.read(name).decode("utf-8")
            except UnicodeDecodeError:
                continue
            for reason in _content_local_path_leak_reasons(entry_name, text):
                findings.append(f"{entry_name}:{reason}")
    return tuple(sorted(findings))


def safe_handoff_component(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value).strip("_")
    return safe or "handoff"


def normalized_context_timestamp(created_at_utc: str) -> str:
    try:
        parsed = datetime.fromisoformat(created_at_utc.replace("Z", "+00:00"))
        return parsed.strftime("%Y%m%d-%H%M%S")
    except ValueError:
        digits = "".join(char for char in created_at_utc if char.isdigit())
        if len(digits) >= 14:
            return f"{digits[:8]}-{digits[8:14]}"
    return "unknown-time"


def upload_bundle_id_from_context(context_bytes: bytes, zip_sha256: str) -> str:
    context = parse_context_metadata(context_bytes.decode("utf-8"))
    project_name = safe_handoff_component(context.get("project_name", "compound_income_os"))
    profile = safe_handoff_component(context.get("profile", "profile"))
    bundle_name = safe_handoff_component(context.get("bundle_name", "bundle"))
    created_at = normalized_context_timestamp(context.get("created_at_utc", ""))
    short_head = safe_handoff_component(context.get("head", "unknown")[:7])
    short_sha = zip_sha256[:8].upper()
    name_segment = handoff_name_segment(profile, bundle_name)
    return f"{project_name}_HANDOFF_{name_segment}_{created_at}_{short_head}_{short_sha}"


def handoff_name_segment(profile: str, bundle_name: str) -> str:
    safe_profile = safe_handoff_component(profile)
    safe_bundle = safe_handoff_component(bundle_name)
    if not safe_bundle or safe_bundle == safe_profile:
        return safe_profile
    return f"{safe_profile}_{safe_bundle}"


def _zip_validation_details(zip_path: Path, *, expected_context_bytes: bytes | None = None) -> dict[str, str]:
    with zipfile.ZipFile(zip_path, "r") as archive:
        bad_entry = archive.testzip()
        if bad_entry:
            raise ValueError(f"handoff ZIP failed integrity check at {bad_entry}")
        names = archive.namelist()
        missing = [entry for entry in STANDARD_HANDOFF_ENTRIES if entry not in names]
        if missing:
            raise ValueError(f"handoff ZIP missing standard entries: {', '.join(missing)}")
        internal_context = archive.read("HANDOFF_CONTEXT.md")
        validation_text_bytes = archive.read("HANDOFF_VALIDATION.txt")

    if expected_context_bytes is not None and internal_context != expected_context_bytes:
        raise ValueError("handoff latest context does not match internal HANDOFF_CONTEXT.md")

    forbidden = tuple(sorted(name for name in names if is_forbidden_entry(name)))
    nested_zip = tuple(sorted(name for name in names if name.endswith(".zip")))
    local_path_leaks = scan_local_path_leaks_in_zip(zip_path)
    validation = parse_validation_metadata(validation_text_bytes.decode("utf-8"))
    reported_file_count = int(validation.get("file_count", "-1"))
    reported_forbidden_count = int(validation.get("forbidden_count", "-1"))
    reported_nested_zip_count = int(validation.get("nested_zip_count", "-1"))
    reported_local_path_leak_count = int(validation.get("local_path_leak_count", "-1"))
    if reported_file_count != len(names):
        raise ValueError(
            f"handoff validation file_count mismatch: reported {reported_file_count}, actual {len(names)}"
        )
    if reported_forbidden_count != len(forbidden):
        raise ValueError(
            f"handoff validation forbidden_count mismatch: reported {reported_forbidden_count}, actual {len(forbidden)}"
        )
    if reported_nested_zip_count != len(nested_zip):
        raise ValueError(
            f"handoff validation nested_zip_count mismatch: reported {reported_nested_zip_count}, actual {len(nested_zip)}"
        )
    if reported_local_path_leak_count != len(local_path_leaks):
        raise ValueError(
            f"handoff validation local_path_leak_count mismatch: reported {reported_local_path_leak_count}, actual {len(local_path_leaks)}"
        )
    if forbidden:
        raise ValueError(f"handoff ZIP contains forbidden entries: {', '.join(forbidden)}")
    if nested_zip:
        raise ValueError(f"handoff ZIP contains nested ZIP entries: {', '.join(nested_zip)}")
    if local_path_leaks:
        raise ValueError(f"handoff ZIP contains local path leaks: {', '.join(local_path_leaks)}")

    context = parse_context_metadata(internal_context.decode("utf-8"))
    return {
        "file_count": str(len(names)),
        "forbidden_count": str(len(forbidden)),
        "nested_zip_count": str(len(nested_zip)),
        "local_path_leak_count": str(len(local_path_leaks)),
        "profile": context.get("profile", ""),
        "bundle_name": context.get("bundle_name", ""),
        "created_at_utc": context.get("created_at_utc", ""),
        "branch": context.get("branch", ""),
        "head": context.get("head", ""),
    }


def validate_handoff_archive(zip_path: str | Path, *, expected_context_bytes: bytes | None = None) -> dict[str, str]:
    return _zip_validation_details(Path(zip_path), expected_context_bytes=expected_context_bytes)


def validate_latest_handoff(latest_dir: str | Path, *, archive_zip_path: str | Path | None = None) -> dict[str, str]:
    latest = Path(latest_dir)
    zip_path = latest / "HANDOFF_LATEST.zip"
    context_path = latest / "HANDOFF_LATEST_CONTEXT.md"
    sha_path = latest / "HANDOFF_LATEST.sha256"
    missing = [path.name for path in (zip_path, context_path, sha_path) if not path.exists()]
    if missing:
        raise ValueError(f"handoff latest missing required files: {', '.join(missing)}")

    actual_sha = sha256_file(zip_path)
    sha_text = sha_path.read_text(encoding="utf-8").strip()
    reported_sha = sha_text.split()[0] if sha_text else ""
    if reported_sha.upper() != actual_sha.upper():
        raise ValueError("handoff latest SHA256 file does not match HANDOFF_LATEST.zip")

    context_bytes = context_path.read_bytes()
    details = validate_handoff_archive(zip_path, expected_context_bytes=context_bytes)
    external_context = parse_context_metadata(context_bytes.decode("utf-8"))
    for key in ("profile", "bundle_name", "created_at_utc", "branch", "head"):
        if details.get(key, "") != external_context.get(key, ""):
            raise ValueError(f"handoff latest context metadata mismatch for {key}")

    if archive_zip_path is not None:
        archive_sha = sha256_file(Path(archive_zip_path))
        if archive_sha.upper() != actual_sha.upper():
            raise ValueError("handoff archive copy hash does not match latest ZIP hash")
    details["sha256"] = actual_sha
    return details


def validate_upload_ready_handoff(upload_dir: str | Path, *, archive_zip_path: str | Path | None = None) -> dict[str, str]:
    upload = Path(upload_dir)
    bundle_id = upload.name
    zip_path = upload / f"{bundle_id}.zip"
    if not zip_path.exists():
        zip_candidates = sorted(upload.glob("*.zip"))
        if len(zip_candidates) == 1:
            zip_path = zip_candidates[0]
            bundle_id = zip_path.stem
    context_path = upload / f"{bundle_id}_CONTEXT.md"
    sha_path = upload / f"{bundle_id}.sha256"
    missing = [path.name for path in (zip_path, context_path, sha_path) if not path.exists()]
    if missing:
        raise ValueError(f"handoff upload-ready missing required files: {', '.join(missing)}")

    actual_sha = sha256_file(zip_path)
    sha_text = sha_path.read_text(encoding="utf-8").strip()
    parts = sha_text.split()
    reported_sha = parts[0] if parts else ""
    reported_name = parts[1] if len(parts) > 1 else ""
    if reported_sha.upper() != actual_sha.upper():
        raise ValueError("handoff upload-ready SHA256 file does not match upload ZIP")
    if reported_name != zip_path.name:
        raise ValueError("handoff upload-ready SHA256 file does not reference the unique ZIP filename")

    details = validate_handoff_archive(zip_path, expected_context_bytes=context_path.read_bytes())
    if archive_zip_path is not None:
        archive_sha = sha256_file(Path(archive_zip_path))
        if archive_sha.upper() != actual_sha.upper():
            raise ValueError("handoff archive copy hash does not match upload-ready ZIP hash")
    details["sha256"] = actual_sha
    return details


def write_latest_handoff_files(zip_path: Path, repo_root: Path, context_bytes: bytes, zip_sha256: str) -> None:
    latest_dir = repo_root / "outputs" / "handoffs" / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    actual_archive_sha = sha256_file(zip_path)
    if actual_archive_sha.upper() != zip_sha256.upper():
        raise ValueError("handoff archive SHA256 changed before latest update")
    validate_handoff_archive(zip_path, expected_context_bytes=context_bytes)

    staging_dir = latest_dir / f".staging_{zip_sha256[:12]}"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    try:
        staged_zip = staging_dir / "HANDOFF_LATEST.zip"
        staged_context = staging_dir / "HANDOFF_LATEST_CONTEXT.md"
        staged_sha = staging_dir / "HANDOFF_LATEST.sha256"
        shutil.copyfile(zip_path, staged_zip)
        staged_context.write_bytes(context_bytes)
        staged_sha.write_text(f"{sha256_file(staged_zip)}  HANDOFF_LATEST.zip\n", encoding="utf-8")
        validate_latest_handoff(staging_dir, archive_zip_path=zip_path)

        final_zip = latest_dir / "HANDOFF_LATEST.zip"
        final_context = latest_dir / "HANDOFF_LATEST_CONTEXT.md"
        final_sha = latest_dir / "HANDOFF_LATEST.sha256"
        staged_zip.replace(final_zip)
        staged_context.replace(final_context)
        final_sha.write_text(f"{sha256_file(final_zip)}  HANDOFF_LATEST.zip\n", encoding="utf-8")
        validate_latest_handoff(latest_dir, archive_zip_path=zip_path)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)


def write_upload_ready_handoff_files(zip_path: Path, repo_root: Path, context_bytes: bytes, zip_sha256: str) -> Path:
    latest_dir = repo_root / "outputs" / "handoffs" / "latest"
    validate_latest_handoff(latest_dir, archive_zip_path=zip_path)
    validate_handoff_archive(zip_path, expected_context_bytes=context_bytes)
    bundle_id = upload_bundle_id_from_context(context_bytes, zip_sha256)
    upload_root = repo_root / "outputs" / "handoffs" / "upload_ready"
    upload_root.mkdir(parents=True, exist_ok=True)
    staging_dir = upload_root / f".staging_{bundle_id}"
    final_dir = upload_root / bundle_id
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    try:
        zip_name = f"{bundle_id}.zip"
        context_name = f"{bundle_id}_CONTEXT.md"
        sha_name = f"{bundle_id}.sha256"
        staged_zip = staging_dir / zip_name
        staged_context = staging_dir / context_name
        staged_sha = staging_dir / sha_name
        shutil.copyfile(zip_path, staged_zip)
        staged_context.write_bytes(context_bytes)
        staged_sha.write_text(f"{sha256_file(staged_zip)}  {zip_name}\n", encoding="utf-8")
        validate_upload_ready_handoff(staging_dir, archive_zip_path=zip_path)

        final_dir.mkdir(parents=True, exist_ok=True)
        staged_zip.replace(final_dir / zip_name)
        staged_context.replace(final_dir / context_name)
        staged_sha.replace(final_dir / sha_name)
        validate_upload_ready_handoff(final_dir, archive_zip_path=zip_path)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
    return final_dir


def external_review_checklist() -> bytes:
    return (
        "# External Review Checklist\n\n"
        "- Verify the bundle profile and purpose.\n"
        "- Inspect HANDOFF_MANIFEST.csv before reviewing content.\n"
        "- Inspect HANDOFF_OMITTED_ARTIFACTS.csv for private or forbidden omissions.\n"
        "- Validate generated artifacts against source and tests.\n"
        "- Do not assume omitted private raw data.\n"
    ).encode("utf-8")


def change_classification_rows(status_text: str, included_entries: set[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in status_text.splitlines():
        status, path_text = parse_git_status_short_line(line)
        if not path_text:
            continue
        row = classify_change_path(path_text, included_entries)
        row["status"] = status
        rows.append(row)
    return rows


def parse_git_name_status_line(line: str) -> tuple[str, str, str]:
    parts = [part for part in line.strip().split("\t") if part]
    if len(parts) < 2:
        return "", "", ""
    status = parts[0]
    if status.startswith("R") or status.startswith("C"):
        old_path = parts[1] if len(parts) > 1 else ""
        new_path = parts[2] if len(parts) > 2 else old_path
        return status, new_path, old_path
    return status, parts[1], ""


def classify_delta_path(
    *,
    path_value: str,
    change_type: str,
    included_entries: set[str],
    delta_range: str,
    evidence_source: str,
    notes: str = "",
) -> dict[str, str]:
    raw_path = normalize_entry_name(path_value)
    display_path = sanitize_path_for_external(raw_path)
    included = raw_path in included_entries
    if raw_path.startswith("external_review_packet/") or raw_path.startswith("outputs/handoffs/"):
        classification = "HANDOFF_METADATA"
        safe = "True"
        omitted_reason = "NOT_SELECTED_FOR_PROFILE" if not included else ""
    elif included:
        classification = "PATCH_CHANGED"
        safe = "True"
        omitted_reason = ""
    elif is_forbidden_entry(raw_path):
        classification = "OMITTED_PRIVATE" if display_path.startswith("<private") else "OMITTED_FORBIDDEN"
        safe = "False"
        omitted_reason = "FORBIDDEN_PATH"
    elif raw_path.startswith("data/processed/") or raw_path.startswith("reports/"):
        classification = "GENERATED_ARTIFACT"
        safe = "True"
        omitted_reason = "NOT_SELECTED_FOR_PROFILE"
    else:
        classification = "UNKNOWN"
        safe = "True"
        omitted_reason = "NOT_SELECTED_FOR_PROFILE"
    return {
        "path": display_path,
        "status": change_type,
        "change_type": change_type,
        "evidence_source": evidence_source,
        "delta_range": delta_range,
        "included_in_zip": str(included),
        "classification": classification,
        "included": str(included),
        "omitted_reason": omitted_reason,
        "safe_for_external_review": safe,
        "notes": notes,
    }


def delta_change_classification_rows(
    *,
    diff_text: str,
    included_entries: set[str],
    base_head: str,
    head: str,
) -> list[dict[str, str]]:
    delta_range = f"{base_head}..{head}" if base_head and head else ""
    if not diff_text.strip():
        return [
            {
                "path": "<no_patch_delta_rows>",
                "status": "NO_CHANGES",
                "change_type": "NO_CHANGES",
                "evidence_source": "git diff --name-status",
                "delta_range": delta_range,
                "included_in_zip": "False",
                "classification": "UNKNOWN",
                "included": "False",
                "omitted_reason": "",
                "safe_for_external_review": "True",
                "notes": "Git diff returned no changed paths for this range.",
            }
        ]
    rows: list[dict[str, str]] = []
    for line in diff_text.splitlines():
        change_type, path_text, old_path = parse_git_name_status_line(line)
        if not path_text:
            continue
        notes = f"renamed_from={sanitize_path_for_external(old_path)}" if old_path else ""
        rows.append(
            classify_delta_path(
                path_value=path_text,
                change_type=change_type,
                included_entries=included_entries,
                delta_range=delta_range,
                evidence_source="git diff --name-status",
                notes=notes,
            )
        )
    return rows


def unavailable_delta_row(reason: str, head: str) -> dict[str, str]:
    return {
        "path": "<delta_unavailable>",
        "status": "UNKNOWN_DELTA_BASE",
        "change_type": "UNKNOWN_DELTA_BASE",
        "evidence_source": "GIT_CONTEXT_UNAVAILABLE",
        "delta_range": f"UNKNOWN_DELTA_BASE..{head}" if head else "UNKNOWN_DELTA_RANGE",
        "included_in_zip": "False",
        "classification": "UNKNOWN",
        "included": "False",
        "omitted_reason": "",
        "safe_for_external_review": "True",
        "notes": reason,
    }


def write_zip(zip_path: Path, files: list[Path], repo_root: Path, metadata_entries: dict[str, bytes]) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            entry_name = normalize_entry_name(path.relative_to(repo_root).as_posix())
            info = zipfile.ZipInfo(entry_name, date_time=FIXED_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
        for entry_name, content in sorted(metadata_entries.items()):
            info = zipfile.ZipInfo(entry_name, date_time=FIXED_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)


def validate_zip(zip_path: Path) -> tuple[tuple[str, ...], int]:
    details = validate_handoff_archive(zip_path)
    return (), int(details["file_count"])


def export_handoff_bundle(
    *,
    profile: str,
    bundle_name: str,
    include_paths: Iterable[str | Path],
    repo_root: str | Path = ROOT,
    output_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    purpose: str = "external LLM validation",
    validation_summary: str = "",
    validation_commands: Iterable[str] = (),
    validation_log: str = "",
    recommended_next_step: str = "",
    omitted_artifacts: Iterable[dict[str, str]] = (),
    patch_title: str | None = None,
    patch_bundle_purpose: str | None = None,
) -> HandoffBundleResult:
    root = resolve_repo_path(repo_root).resolve()
    lifecycle_enabled = output_dir is None and output_path is None
    if output_path:
        zip_path = resolve_repo_path(output_path).resolve()
        target_dir = zip_path.parent
    else:
        target_dir = resolve_repo_path(output_dir).resolve() if output_dir else root / "outputs" / "handoffs" / "archive"
        zip_path = Path()
    target_dir.mkdir(parents=True, exist_ok=True)
    files, include_omissions = resolve_include_paths(root, include_paths)
    included_entries = [normalize_entry_name(path.relative_to(root).as_posix()) for path in files]
    included_set = set(included_entries)
    branch = run_git(["branch", "--show-current"], root, allow_failure=True)
    head = run_git(["rev-parse", "HEAD"], root)
    short_head = run_git(["rev-parse", "--short", "HEAD"], root)
    base_head = run_git(["rev-parse", "HEAD^"], root, allow_failure=True)
    if "fatal:" in base_head.lower():
        base_head = ""
    delta_range = f"{base_head}..{head}" if base_head else ""
    diff_text = run_git(["diff", "--name-status", delta_range], root, allow_failure=True) if delta_range else ""
    status_text = run_git(["status", "--short"], root, allow_failure=True)
    omitted_rows = list(omitted_artifacts) + include_omissions
    included_groups = [source_group(entry) for entry in included_entries]
    omitted_groups = [row.get("omission_reason", "") for row in omitted_rows if row.get("omission_reason", "")]
    delta_rows = (
        delta_change_classification_rows(
            diff_text=diff_text,
            included_entries=included_set,
            base_head=base_head,
            head=head,
        )
        if delta_range
        else [unavailable_delta_row("Git base head is unavailable; cannot prove patch delta completeness.", head)]
    )
    dirty_rows = change_classification_rows(status_text, included_set)
    if dirty_rows:
        delta_rows.extend(dirty_rows)
    delta_evidence_status = "COMPLETE" if delta_range and delta_rows and delta_rows[0]["path"] != "<no_patch_delta_rows>" else "UNAVAILABLE_OR_EMPTY"
    metadata_entries: dict[str, bytes] = {
        "HANDOFF_CONTEXT.md": context_markdown(
            project_name="compound_income_os",
            profile=profile,
            bundle_name=bundle_name,
            branch=branch,
            head=head,
            dirty_worktree_present=bool(status_text.strip()),
            purpose=purpose,
            base_head=base_head,
            delta_range=delta_range,
            delta_row_count=len(delta_rows),
            patch_identity_entry="HANDOFF_PATCH_IDENTITY.md",
            included_groups=included_groups,
            omitted_groups=omitted_groups,
            validation_summary=validation_summary,
        ),
        "HANDOFF_PATCH_IDENTITY.md": patch_identity_markdown(
            patch_title=patch_title or bundle_name,
            bundle_purpose=patch_bundle_purpose or purpose,
            base_head=base_head,
            implementation_head=head,
            current_handoff_head=head,
            delta_range=delta_range,
            changed_file_count=sum(1 for row in delta_rows if row["classification"] in {"PATCH_CHANGED", "HANDOFF_METADATA", "GENERATED_ARTIFACT", "UNKNOWN"}),
            delta_evidence_status=delta_evidence_status,
            change_classification_entry="HANDOFF_CHANGE_CLASSIFICATION.csv",
        ),
        "HANDOFF_REPORT.md": report_markdown(
            profile=profile,
            bundle_name=bundle_name,
            included_entries=included_entries,
            omitted_rows=omitted_rows,
            validation_summary=validation_summary,
            recommended_next_step=recommended_next_step,
        ),
        "HANDOFF_ARTIFACT_INDEX.csv": csv_bytes(
            ["artifact_path", "artifact_kind", "semantic_role", "produced_by", "consumed_by", "included", "omission_reason", "notes"],
            artifact_index_rows(files, root, included_set),
        ),
        "HANDOFF_GUARDRAILS.md": guardrails_markdown(profile),
        "HANDOFF_OMITTED_ARTIFACTS.csv": csv_bytes(
            [
                "artifact_path_or_category",
                "omission_reason",
                "safe_to_include",
                "required_for_external_review",
                "replacement_context_provided",
                "notes",
            ],
            omitted_rows,
        ),
        "HANDOFF_CHANGE_CLASSIFICATION.csv": csv_bytes(
            [
                "path",
                "status",
                "change_type",
                "evidence_source",
                "delta_range",
                "included_in_zip",
                "classification",
                "included",
                "omitted_reason",
                "safe_for_external_review",
                "notes",
            ],
            delta_rows,
        ),
        "HANDOFF_GIT_STATUS_SANITIZED.txt": (
            "\n".join(f"{row['change_type']} {row['path']} {row['classification']} {row['delta_range']}" for row in delta_rows) + "\n"
        ).encode("utf-8"),
        "HANDOFF_EXTERNAL_REVIEW_CHECKLIST.md": external_review_checklist(),
    }
    manifest_row_values = manifest_rows(root, files, metadata_entries, profile)
    metadata_entries["HANDOFF_MANIFEST.csv"] = csv_bytes(
        ["entry_name", "size_bytes", "sha256", "entry_type", "source_group", "profile", "required_for_review"],
        manifest_row_values,
    )
    safe_name = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in bundle_name).strip("_")
    context_created_at = parse_context_metadata(metadata_entries["HANDOFF_CONTEXT.md"].decode("utf-8")).get("created_at_utc", "")
    timestamp = normalized_context_timestamp(context_created_at)
    if not output_path:
        zip_path = target_dir / f"compound_income_os_HANDOFF_{handoff_name_segment(profile, safe_name)}_{timestamp}_{short_head}.zip"
    pending_entries = included_entries + list(metadata_entries) + ["HANDOFF_VALIDATION.txt"]
    pending_forbidden = tuple(sorted(entry for entry in pending_entries if is_forbidden_entry(entry)))
    pending_nested_zip = tuple(sorted(entry for entry in pending_entries if entry.endswith(".zip")))
    pending_file_count = len(pending_entries)
    manifest_sha256 = sha256_bytes(metadata_entries["HANDOFF_MANIFEST.csv"])
    metadata_entries["HANDOFF_VALIDATION.txt"] = validation_text(
        validation_summary=validation_summary,
        validation_commands=validation_commands,
        validation_log=validation_log,
        forbidden_count=len(pending_forbidden),
        file_count=pending_file_count,
        nested_zip_count=len(pending_nested_zip),
        local_path_leak_count=0,
        manifest_sha256=manifest_sha256,
        manifest_row_count=len(manifest_row_values),
        terminal_metadata_count=2,
    )
    write_zip(zip_path, files, root, metadata_entries)
    forbidden, file_count = validate_zip(zip_path)
    sha256 = sha256_file(zip_path)
    if forbidden:
        raise ValueError(f"handoff ZIP contains forbidden entries: {', '.join(forbidden)}")
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = tuple(sorted(archive.namelist()))
    upload_ready_dir: Path | None = None
    if lifecycle_enabled:
        write_latest_handoff_files(zip_path, root, metadata_entries["HANDOFF_CONTEXT.md"], sha256)
        upload_ready_dir = write_upload_ready_handoff_files(zip_path, root, metadata_entries["HANDOFF_CONTEXT.md"], sha256)
    return HandoffBundleResult(
        zip_path=zip_path,
        profile=profile,
        bundle_name=bundle_name,
        branch=branch,
        head=head,
        short_head=short_head,
        file_count=file_count,
        size_bytes=zip_path.stat().st_size,
        sha256=sha256,
        forbidden_matches=forbidden,
        included_entries=names,
        omitted_rows=tuple(omitted_rows),
        upload_ready_dir=upload_ready_dir,
    )


def scan_forbidden_entries(zip_path: str | Path) -> tuple[str, ...]:
    with zipfile.ZipFile(zip_path, "r") as archive:
        return tuple(sorted(name for name in archive.namelist() if is_forbidden_entry(name)))


def zip_top_level_contents(zip_path: str | Path) -> tuple[str, ...]:
    with zipfile.ZipFile(zip_path, "r") as archive:
        return tuple(sorted({name.split("/", 1)[0] for name in archive.namelist() if name}))
