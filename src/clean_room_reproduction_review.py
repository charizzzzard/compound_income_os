from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir
from src.external_review_cross_patch_regression import run_cross_patch_regression

DEFAULT_CSV_OUTPUT = "data/processed/clean_room_reproduction_review.csv"
DEFAULT_REPORT_OUTPUT_TEMPLATE = "reports/{as_of_date}/clean_room_reproduction_review_report.md"
DEFAULT_PACKET_ROOT = "external_review_packet"

EXTERNAL_README_NAME = "00_READ_ME_FIRST.md"
EXTERNAL_CONTEXT_NAME = "HANDOFF_LATEST_CONTEXT.md"
EXTERNAL_SHA_NAME = "HANDOFF_LATEST.sha256"
EXTERNAL_ZIP_NAME = "HANDOFF_LATEST.zip"

CSV_FIELDS = [
    "as_of_date",
    "check_id",
    "severity",
    "status",
    "file_path",
    "evidence",
    "finding",
    "recommended_action",
]

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "INFO": 3}
STATUS_ORDER = {"FAIL": 0, "WARN": 1, "MISSING": 2, "NOT_AVAILABLE": 3, "PASS": 4}

SOURCE_OF_TRUTH_ORDER = [
    "external_review_packet/00_READ_ME_FIRST.md",
    "external_review_packet/HANDOFF_LATEST_CONTEXT.md",
    "external_review_packet/HANDOFF_LATEST.zip",
    "external_review_packet/HANDOFF_LATEST.sha256",
    "historische Reports nur als Kontext",
]

REQUIRED_ZIP_FILES = [
    "src/clean_room_reproduction_review.py",
    "tests/test_clean_room_reproduction_review.py",
    "src/external_review_cross_patch_regression.py",
    "tests/test_external_review_cross_patch_regression.py",
    "docs/governance/EXTERNAL_REVIEW_COVERAGE_STANDARD.md",
    "docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml",
    "docs/governance/EXTERNAL_REVIEW_GATE_SEQUENCE.md",
    "docs/architecture/CIOS_FEATURE_STATUS.yaml",
    "docs/architecture/CURRENT_KNOWN_GAPS.md",
    "docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md",
    "docs/MODULE_CONTRACTS.md",
    "docs/CONTEXT_AND_ROADMAP.md",
    "README.md",
    "tests/test_readme_and_reports.py",
    "tests/test_handoff_zip_export.py",
    "tests/test_handoff_bundle.py",
]

OPTIONAL_REGENERATED_OUTPUTS = [
    "data/processed/external_review_cross_patch_regression.csv",
    "reports/2026-05-21/external_review_cross_patch_regression_report.md",
    "data/processed/clean_room_reproduction_review.csv",
    "reports/2026-05-21/clean_room_reproduction_review_report.md",
]

NON_SCOPE_PHRASES = {
    "Investmentlogik": ["keine Investmentlogik", "Investment logic"],
    "produktiver Portfolio Event Ledger": ["kein produktiver Portfolio Event Ledger", "no production event ledger"],
    "Event-Ledger-Runtime": ["keine Event-Ledger-Runtime", "Event-Ledger-Runtime"],
    "Broker Import": ["kein Broker Import", "Broker Import"],
    "Broker Parser": ["kein Broker Parser", "Broker Parser"],
    "Provider Adapter": ["kein Provider Adapter", "Provider Adapter"],
    "API/Scraping": ["keine API-Anbindung", "Scraping", "Web-Crawling"],
    "Corporate Actions Engine": ["Corporate Actions Engine"],
    "FX Engine": ["FX Engine"],
    "Replay/Backtesting/Simulation": ["Replay", "Backtesting", "Simulation"],
    "Outcome Attribution": ["Outcome Attribution"],
    "Dashboard": ["kein Dashboard", "Dashboard"],
    "Valuation Automation": ["Valuation Automation"],
    "Buy/Sell Recommendation": ["Buy/Sell Recommendation", "Buy/Sell"],
    "Steuerberechnung": ["Steuerberechnung", "tax"],
    "Legal/Commercial": ["Legal-/Commercial-Freigabe", "legal", "commercial"],
    "Order Execution": ["Order Execution", "order execution"],
    "Runtime LLM": ["Runtime-LLM-Agentenlogik", "runtime LLM"],
    "Runtime Enforcement": ["Runtime-Enforcement-Engine", "runtime enforcement"],
    "Full release acceptance": ["keine vollautomatische Release-Akzeptanz", "release acceptance"],
}


@dataclass(frozen=True)
class Finding:
    as_of_date: str
    check_id: str
    severity: str
    status: str
    file_path: str
    evidence: str
    finding: str
    recommended_action: str

    def row(self) -> dict[str, str]:
        return {
            "as_of_date": self.as_of_date,
            "check_id": self.check_id,
            "severity": self.severity,
            "status": self.status,
            "file_path": self.file_path,
            "evidence": self.evidence,
            "finding": self.finding,
            "recommended_action": self.recommended_action,
        }


def _finding(
    as_of_date: str,
    check_id: str,
    severity: str,
    status: str,
    file_path: str,
    evidence: str,
    finding: str,
    recommended_action: str,
) -> Finding:
    return Finding(
        as_of_date=as_of_date,
        check_id=check_id,
        severity=severity,
        status=status,
        file_path=file_path.replace("\\", "/"),
        evidence=evidence.replace("\n", " ")[:500],
        finding=finding,
        recommended_action=recommended_action,
    )


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda item: (
            SEVERITY_ORDER.get(item.severity, 99),
            item.check_id,
            item.file_path,
            STATUS_ORDER.get(item.status, 99),
            item.finding,
        ),
    )


def _repo_path(repo_root: Path, relative_path: str | Path) -> Path:
    path = Path(relative_path)
    return path if path.is_absolute() else repo_root / path


def _read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8-sig")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expected_sha(sha_text: str) -> str | None:
    match = re.search(r"\b([0-9a-fA-F]{64})\b", sha_text)
    return match.group(1).lower() if match else None


def _extract_key(text: str, key: str) -> str | None:
    pattern = re.compile(rf"^\s*-?\s*{re.escape(key)}:\s*`?([^`\n]+?)`?\s*$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _source_of_truth_consistent(text: str) -> bool:
    search_text = text
    marker = "Bei Konflikten gilt"
    if marker in text:
        search_text = text[text.find(marker) :]
    positions = [search_text.find(item) for item in SOURCE_OF_TRUTH_ORDER]
    return all(position >= 0 for position in positions) and positions == sorted(positions)


def _zip_names(zip_path: Path) -> tuple[str, ...]:
    with zipfile.ZipFile(zip_path) as archive:
        return tuple(sorted(archive.namelist()))


def _zip_member_text(zip_path: Path, name: str) -> str | None:
    with zipfile.ZipFile(zip_path) as archive:
        if name not in archive.namelist():
            return None
        return archive.read(name).decode("utf-8", errors="replace")


def _packet_path(packet_root: Path, name: str) -> Path:
    return packet_root / name


def _packet_display(packet_root: Path, name: str | None = None) -> str:
    root = packet_root.name if packet_root.is_absolute() else packet_root.as_posix()
    return f"{root}/{name}" if name else root


def check_packet_metadata_presence(as_of_date: str, packet_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for name in [EXTERNAL_README_NAME, EXTERNAL_CONTEXT_NAME, EXTERNAL_SHA_NAME, EXTERNAL_ZIP_NAME]:
        path = _packet_path(packet_root, name)
        file_path = _packet_display(packet_root, name)
        if path.exists():
            findings.append(_finding(as_of_date, "PACKET_METADATA_PRESENT", "INFO", "PASS", file_path, "exists", "Required packet metadata artifact is present.", "Keep packet files together for external review."))
        else:
            findings.append(_finding(as_of_date, "PACKET_METADATA_PRESENT", "P0", "MISSING", file_path, "missing", "Required packet metadata artifact is missing.", "Regenerate the external review packet."))
    return findings


def check_sha_zip_integrity(as_of_date: str, packet_root: Path) -> tuple[list[Finding], tuple[str, ...], str | None]:
    findings: list[Finding] = []
    zip_path = _packet_path(packet_root, EXTERNAL_ZIP_NAME)
    sha_path = _packet_path(packet_root, EXTERNAL_SHA_NAME)
    zip_file_path = _packet_display(packet_root, EXTERNAL_ZIP_NAME)
    names: tuple[str, ...] = ()
    actual_sha: str | None = None

    if not zip_path.exists():
        findings.append(_finding(as_of_date, "ZIP_INTEGRITY", "P0", "NOT_AVAILABLE", zip_file_path, "ZIP_NOT_AVAILABLE", "Handoff ZIP is not available for clean-room review.", "Regenerate HANDOFF_LATEST.zip."))
        return findings, names, actual_sha

    actual_sha = _sha256_file(zip_path)
    if not sha_path.exists():
        findings.append(_finding(as_of_date, "SHA256_MATCH", "P0", "MISSING", _packet_display(packet_root, EXTERNAL_SHA_NAME), "sha file missing", "Checksum file is missing.", "Regenerate HANDOFF_LATEST.sha256."))
    else:
        expected = _expected_sha(sha_path.read_text(encoding="utf-8-sig"))
        if expected == actual_sha:
            findings.append(_finding(as_of_date, "SHA256_MATCH", "INFO", "PASS", _packet_display(packet_root, EXTERNAL_SHA_NAME), actual_sha, "SHA256 file matches the ZIP.", "Keep checksum adjacent to the ZIP."))
        else:
            findings.append(_finding(as_of_date, "SHA256_MATCH", "P0", "FAIL", _packet_display(packet_root, EXTERNAL_SHA_NAME), f"expected={expected} actual={actual_sha}", "SHA256 file does not match the ZIP.", "Regenerate checksum after ZIP creation."))

    try:
        with zipfile.ZipFile(zip_path) as archive:
            bad_entry = archive.testzip()
            names = tuple(sorted(archive.namelist()))
        if bad_entry is None:
            findings.append(_finding(as_of_date, "ZIP_TESTZIP", "INFO", "PASS", zip_file_path, "zipfile.testzip=None", "ZIP integrity check passed.", "Keep zipfile.testzip in handoff QA."))
        else:
            findings.append(_finding(as_of_date, "ZIP_TESTZIP", "P0", "FAIL", zip_file_path, f"bad_entry={bad_entry}", "ZIP integrity check failed.", "Regenerate the handoff ZIP."))
    except zipfile.BadZipFile as exc:
        findings.append(_finding(as_of_date, "ZIP_TESTZIP", "P0", "FAIL", zip_file_path, str(exc), "ZIP is not readable.", "Regenerate the handoff ZIP."))
        return findings, names, actual_sha

    nested = tuple(name for name in names if name.endswith(".zip"))
    status = "PASS" if not nested else "FAIL"
    severity = "INFO" if not nested else "P0"
    findings.append(_finding(as_of_date, "ZIP_NESTED_COUNT", severity, status, zip_file_path, f"nested_zip_count={len(nested)}", "Nested ZIP count checked.", "Keep nested ZIP count at zero unless explicitly allowed."))
    findings.append(_finding(as_of_date, "ZIP_FILE_COUNT", "INFO", "PASS", zip_file_path, f"file_count={len(names)}", "ZIP file count captured for reproduction.", "Compare file count across packet refreshes."))

    try:
        from src.handoff_zip_export import scan_forbidden_entries, scan_local_path_leaks_in_zip

        forbidden = scan_forbidden_entries(zip_path)
        leaks = scan_local_path_leaks_in_zip(zip_path)
        findings.append(_finding(as_of_date, "ZIP_FORBIDDEN_MATCH_COUNT", "INFO" if not forbidden else "P0", "PASS" if not forbidden else "FAIL", zip_file_path, f"forbidden_match_count={len(forbidden)}", "Forbidden entry scan completed with existing handoff logic.", "Keep forbidden match count at zero."))
        findings.append(_finding(as_of_date, "ZIP_LOCAL_PATH_LEAK_COUNT", "INFO" if not leaks else "P0", "PASS" if not leaks else "FAIL", zip_file_path, f"local_path_leak_count={len(leaks)}", "Local path leak scan completed with existing handoff logic.", "Keep local path leak count at zero."))
    except Exception as exc:  # pragma: no cover - defensive boundary for optional scan logic
        findings.append(_finding(as_of_date, "ZIP_FORBIDDEN_MATCH_COUNT", "P2", "NOT_AVAILABLE", zip_file_path, type(exc).__name__, "Existing forbidden/local-path scan logic was not available.", "Report NOT_AVAILABLE instead of inventing scan results."))

    return findings, names, actual_sha


def check_internal_external_context(as_of_date: str, packet_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    zip_path = _packet_path(packet_root, EXTERNAL_ZIP_NAME)
    context_path = _packet_path(packet_root, EXTERNAL_CONTEXT_NAME)
    readme_path = _packet_path(packet_root, EXTERNAL_README_NAME)
    context_file = _packet_display(packet_root, EXTERNAL_CONTEXT_NAME)

    context = _read_text(context_path)
    readme = _read_text(readme_path)
    if context is None:
        findings.append(_finding(as_of_date, "EXTERNAL_CONTEXT_PRESENT", "P0", "MISSING", context_file, "missing", "External packet context is missing.", "Regenerate HANDOFF_LATEST_CONTEXT.md."))
        return findings

    if readme and _source_of_truth_consistent(readme) and _source_of_truth_consistent(context):
        findings.append(_finding(as_of_date, "SOURCE_OF_TRUTH_PRECEDENCE", "INFO", "PASS", "external_review_packet", "canonical order found", "Source-of-truth precedence is visible in external packet metadata.", "Keep external packet metadata authoritative over ZIP-internal context."))
    else:
        findings.append(_finding(as_of_date, "SOURCE_OF_TRUTH_PRECEDENCE", "P0", "FAIL", "external_review_packet", "precedence missing or inconsistent", "Source-of-truth precedence is not consistently documented.", "Restore canonical precedence in 00_READ_ME_FIRST.md and HANDOFF_LATEST_CONTEXT.md."))

    if not zip_path.exists():
        findings.append(_finding(as_of_date, "INTERNAL_EXTERNAL_CONTEXT", "P1", "NOT_AVAILABLE", _packet_display(packet_root, EXTERNAL_ZIP_NAME), "ZIP_NOT_AVAILABLE", "ZIP-internal context cannot be compared.", "Regenerate the handoff ZIP."))
        return findings

    internal = _zip_member_text(zip_path, "HANDOFF_CONTEXT.md")
    if internal is None:
        findings.append(_finding(as_of_date, "INTERNAL_EXTERNAL_CONTEXT", "P1", "MISSING", _packet_display(packet_root, EXTERNAL_ZIP_NAME), "HANDOFF_CONTEXT.md missing", "ZIP-internal context is missing.", "Regenerate the handoff ZIP."))
        return findings

    internal_head = _extract_key(internal, "head")
    external_head = _extract_key(context, "current_handoff_head") or _extract_key(context, "implementation_head")
    if internal_head and external_head and internal_head == external_head:
        findings.append(_finding(as_of_date, "INTERNAL_EXTERNAL_CONTEXT", "INFO", "PASS", context_file, f"head={external_head}", "ZIP-internal head matches external packet context.", "Keep head metadata synchronized."))
    elif internal_head and external_head:
        findings.append(_finding(as_of_date, "INTERNAL_EXTERNAL_CONTEXT", "P1", "WARN", context_file, f"internal={internal_head} external={external_head}", "ZIP-internal and external context heads differ; external packet context remains authoritative.", "Explain the conflict in external metadata or regenerate the packet."))
    else:
        findings.append(_finding(as_of_date, "INTERNAL_EXTERNAL_CONTEXT", "P1", "WARN", context_file, f"internal={internal_head} external={external_head}", "Could not extract comparable head metadata from both contexts.", "Keep `head` and `current_handoff_head` visible."))
    return findings


def check_required_zip_files(as_of_date: str, names: tuple[str, ...], packet_root: Path) -> list[Finding]:
    zip_file_path = _packet_display(packet_root, EXTERNAL_ZIP_NAME)
    if not names:
        return [_finding(as_of_date, "ZIP_REQUIRED_FILES", "P0", "NOT_AVAILABLE", zip_file_path, "ZIP_NOT_AVAILABLE", "Required file inclusion cannot be checked without ZIP entries.", "Regenerate HANDOFF_LATEST.zip.")]
    missing = [path for path in REQUIRED_ZIP_FILES if path not in names]
    if missing:
        return [_finding(as_of_date, "ZIP_REQUIRED_FILES", "P0", "FAIL", zip_file_path, "; ".join(missing), "Required review files are missing from the ZIP.", "Regenerate full_review handoff with required files included.")]
    return [_finding(as_of_date, "ZIP_REQUIRED_FILES", "INFO", "PASS", zip_file_path, f"required_files={len(REQUIRED_ZIP_FILES)}", "Required review files are present in the ZIP.", "Keep these files in future handoff profiles.")]


def check_validation_reality(as_of_date: str, packet_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    context_path = _packet_path(packet_root, EXTERNAL_CONTEXT_NAME)
    readme_path = _packet_path(packet_root, EXTERNAL_README_NAME)
    zip_path = _packet_path(packet_root, EXTERNAL_ZIP_NAME)
    context = _read_text(context_path) or ""
    readme = _read_text(readme_path) or ""
    combined = f"{context}\n{readme}"

    if "No full test suite is claimed" in combined:
        findings.append(_finding(as_of_date, "VALIDATION_NO_FULL_SUITE_CLAIM", "INFO", "PASS", _packet_display(packet_root, EXTERNAL_CONTEXT_NAME), "No full test suite is claimed", "Full-suite limitation is explicit.", "Keep this distinction when pytest/ruff are unavailable."))
    else:
        findings.append(_finding(as_of_date, "VALIDATION_NO_FULL_SUITE_CLAIM", "P1", "WARN", _packet_display(packet_root, EXTERNAL_CONTEXT_NAME), "missing phrase", "Full-suite limitation is not explicit in external packet metadata.", "State clearly whether full-suite validation was or was not run."))

    if "python -m pytest -q" in combined and "No module named pytest" in combined:
        findings.append(_finding(as_of_date, "VALIDATION_PYTEST_REALITY", "INFO", "PASS", _packet_display(packet_root, EXTERNAL_CONTEXT_NAME), "pytest not installed documented", "pytest unavailability is visible and not treated as success.", "Do not report pytest success unless it actually runs."))
    elif "python -m pytest -q" in combined:
        findings.append(_finding(as_of_date, "VALIDATION_PYTEST_REALITY", "P2", "WARN", _packet_display(packet_root, EXTERNAL_CONTEXT_NAME), "pytest command without missing/success detail", "pytest command is visible but its exact environment result is unclear.", "Document exact pytest result."))

    if "python -m ruff check ." in combined and "No module named ruff" in combined:
        findings.append(_finding(as_of_date, "VALIDATION_RUFF_REALITY", "INFO", "PASS", _packet_display(packet_root, EXTERNAL_CONTEXT_NAME), "ruff not installed documented", "ruff unavailability is visible and not treated as success.", "Do not report ruff success unless it actually runs."))
    elif "python -m ruff check ." in combined:
        findings.append(_finding(as_of_date, "VALIDATION_RUFF_REALITY", "P2", "WARN", _packet_display(packet_root, EXTERNAL_CONTEXT_NAME), "ruff command without missing/success detail", "ruff command is visible but its exact environment result is unclear.", "Document exact ruff result."))

    if not zip_path.exists():
        findings.append(_finding(as_of_date, "VALIDATION_RECORDED_COMMANDS", "P1", "NOT_AVAILABLE", _packet_display(packet_root, EXTERNAL_ZIP_NAME), "ZIP_NOT_AVAILABLE", "HANDOFF_VALIDATION.txt cannot be inspected.", "Regenerate handoff ZIP."))
        return findings
    validation = _zip_member_text(zip_path, "HANDOFF_VALIDATION.txt")
    if validation is None:
        findings.append(_finding(as_of_date, "VALIDATION_RECORDED_COMMANDS", "P1", "MISSING", _packet_display(packet_root, EXTERNAL_ZIP_NAME), "HANDOFF_VALIDATION.txt missing", "Handoff validation metadata is missing.", "Regenerate the handoff ZIP."))
    elif "status: RECORDED" in validation:
        findings.append(_finding(as_of_date, "VALIDATION_RECORDED_COMMANDS", "P2", "WARN", _packet_display(packet_root, EXTERNAL_ZIP_NAME), "status: RECORDED", "Handoff commands are recorded, not embedded pass/fail results.", "Use external context and actual local command output for pass/fail claims."))
    else:
        findings.append(_finding(as_of_date, "VALIDATION_RECORDED_COMMANDS", "INFO", "PASS", _packet_display(packet_root, EXTERNAL_ZIP_NAME), "no RECORDED markers", "Handoff validation status does not use RECORDED markers.", "Keep command-result semantics explicit."))
    return findings


def _cross_patch_counts(findings: list[Any]) -> dict[str, int]:
    counts = {status: 0 for status in ["PASS", "WARN", "FAIL", "MISSING", "NOT_AVAILABLE"]}
    for finding in findings:
        counts[finding.status] = counts.get(finding.status, 0) + 1
    return counts


def _expected_cross_patch_from_context(context: str) -> dict[str, int] | None:
    if "python -m src.external_review_cross_patch_regression --as-of-date" not in context:
        return None
    values: dict[str, int] = {}
    for key in ["findings", "FAIL", "WARN", "PASS"]:
        match = re.search(rf"{re.escape(key)}:\s*`?(\d+)`?", context)
        if match:
            values[key] = int(match.group(1))
    return values if values else None


def check_cross_patch_reproduction(as_of_date: str, repo_root: Path, packet_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    context = _read_text(_packet_path(packet_root, EXTERNAL_CONTEXT_NAME)) or ""
    try:
        cross_findings = run_cross_patch_regression(as_of_date=as_of_date, repo_root=repo_root)
    except Exception as exc:
        return [_finding(as_of_date, "CROSS_PATCH_REPRODUCTION", "P0", "FAIL", "src/external_review_cross_patch_regression.py", type(exc).__name__, "Cross-Patch Regression producer did not run in the local reproduction context.", "Fix producer/runtime errors before accepting clean-room reproducibility.")]

    counts = _cross_patch_counts(cross_findings)
    observed = {
        "findings": len(cross_findings),
        "FAIL": counts.get("FAIL", 0),
        "WARN": counts.get("WARN", 0),
        "PASS": counts.get("PASS", 0),
    }
    expected = _expected_cross_patch_from_context(context)
    if expected:
        comparable = {key: expected[key] for key in expected if key in observed}
        if all(observed[key] == value for key, value in comparable.items()):
            findings.append(_finding(as_of_date, "CROSS_PATCH_REPRODUCTION_BASELINE", "INFO", "PASS", "src/external_review_cross_patch_regression.py", json.dumps(observed, sort_keys=True), "Observed Cross-Patch Regression counts match the packet baseline.", "Keep count drift visible in future refreshes."))
        else:
            findings.append(_finding(as_of_date, "CROSS_PATCH_REPRODUCTION_BASELINE", "P2", "WARN", "src/external_review_cross_patch_regression.py", f"expected={json.dumps(expected, sort_keys=True)} observed={json.dumps(observed, sort_keys=True)}", "Observed Cross-Patch Regression counts differ from external packet baseline.", "Review whether the difference is expected after repo or packet changes."))
    else:
        findings.append(_finding(as_of_date, "CROSS_PATCH_REPRODUCTION_BASELINE", "INFO", "PASS", "src/external_review_cross_patch_regression.py", json.dumps(observed, sort_keys=True), "Observed Cross-Patch Regression counts captured without a fixed packet baseline.", "Use this row as reproduction evidence, not as universal expected values."))
    return findings


def check_zip_only_vs_full_packet(as_of_date: str, packet_root: Path, names: tuple[str, ...]) -> list[Finding]:
    findings: list[Finding] = []
    context_exists = _packet_path(packet_root, EXTERNAL_CONTEXT_NAME).exists()
    readme_exists = _packet_path(packet_root, EXTERNAL_README_NAME).exists()
    if context_exists and readme_exists:
        findings.append(_finding(as_of_date, "ZIP_ONLY_VS_FULL_PACKET", "INFO", "PASS", "external_review_packet", "external metadata present", "Full packet reproduction can use external metadata plus ZIP evidence.", "Keep external metadata and ZIP together for authoritative review."))
    else:
        findings.append(_finding(as_of_date, "ZIP_ONLY_VS_FULL_PACKET", "P1", "WARN", "external_review_packet", "external metadata incomplete", "ZIP-only reproduction cannot fully reconstruct packet metadata precedence.", "Provide 00_READ_ME_FIRST.md and HANDOFF_LATEST_CONTEXT.md with the ZIP."))

    if names:
        absent_outputs = [path for path in OPTIONAL_REGENERATED_OUTPUTS if path not in names]
        findings.append(_finding(as_of_date, "ZIP_OPTIONAL_OUTPUTS", "INFO", "PASS", _packet_display(packet_root, EXTERNAL_ZIP_NAME), f"outputs_not_in_zip={len(absent_outputs)}", "Generated processed/report outputs may be ignored and regenerated rather than bundled.", "Regenerate review outputs locally when they are not part of the handoff profile."))
    else:
        findings.append(_finding(as_of_date, "ZIP_OPTIONAL_OUTPUTS", "P2", "NOT_AVAILABLE", _packet_display(packet_root, EXTERNAL_ZIP_NAME), "ZIP_NOT_AVAILABLE", "Cannot inspect whether generated outputs are included.", "Regenerate the handoff ZIP."))
    return findings


def check_non_scope_preservation(as_of_date: str, packet_root: Path) -> list[Finding]:
    paths = [
        _packet_path(packet_root, EXTERNAL_README_NAME),
        _packet_path(packet_root, EXTERNAL_CONTEXT_NAME),
    ]
    combined = "\n".join(_read_text(path) or "" for path in paths).lower()
    missing = [label for label, variants in NON_SCOPE_PHRASES.items() if not any(variant.lower() in combined for variant in variants)]
    if missing:
        return [_finding(as_of_date, "NON_SCOPE_PRESERVATION", "P0", "WARN", "external_review_packet", "; ".join(missing), "One or more non-scope boundaries are not visible in packet metadata.", "Restore explicit non-scope boundaries in packet readme/context.")]
    return [_finding(as_of_date, "NON_SCOPE_PRESERVATION", "INFO", "PASS", "external_review_packet", f"checked={len(NON_SCOPE_PHRASES)}", "Required non-scope boundaries remain visible in packet metadata.", "Keep non-scope boundaries explicit.")]


def run_clean_room_reproduction_review(
    as_of_date: str,
    repo_root: str | Path = ".",
    packet_root: str | Path = DEFAULT_PACKET_ROOT,
    simulate_extracted_zip: str | Path | None = None,
) -> list[Finding]:
    root = Path(repo_root).resolve()
    packet = _repo_path(root, packet_root)
    packet_rel = Path(packet_root).as_posix()
    findings: list[Finding] = []
    findings.extend(check_packet_metadata_presence(as_of_date, packet))
    zip_findings, names, _actual_sha = check_sha_zip_integrity(as_of_date, packet)
    findings.extend(zip_findings)
    findings.extend(check_internal_external_context(as_of_date, packet))
    findings.extend(check_required_zip_files(as_of_date, names, packet))
    findings.extend(check_validation_reality(as_of_date, packet))
    findings.extend(check_cross_patch_reproduction(as_of_date, root, packet))
    findings.extend(check_zip_only_vs_full_packet(as_of_date, packet, names))
    findings.extend(check_non_scope_preservation(as_of_date, packet))
    if simulate_extracted_zip:
        simulated = _repo_path(root, simulate_extracted_zip)
        status = "PASS" if simulated.exists() else "NOT_AVAILABLE"
        severity = "INFO" if simulated.exists() else "P2"
        findings.append(_finding(as_of_date, "SIMULATED_EXTRACTED_ZIP", severity, status, Path(simulate_extracted_zip).as_posix(), "exists" if simulated.exists() else "missing", "Optional extracted-ZIP simulation path checked.", "Use this only as supplemental evidence; full packet metadata remains external."))
    else:
        findings.append(_finding(as_of_date, "SIMULATED_EXTRACTED_ZIP", "INFO", "NOT_AVAILABLE", packet_rel, "not requested", "No extracted-ZIP simulation path was requested.", "Use --simulate-extracted-zip for supplemental ZIP-only fixture checks."))
    return _sort_findings(findings)


def write_csv(findings: list[Finding], output_path: str | Path) -> Path:
    path = ensure_parent_dir(output_path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for finding in findings:
            writer.writerow(finding.row())
    return path


def _status_counts(findings: list[Finding]) -> dict[str, int]:
    counts = {status: 0 for status in ["PASS", "WARN", "FAIL", "MISSING", "NOT_AVAILABLE"]}
    for finding in findings:
        counts[finding.status] = counts.get(finding.status, 0) + 1
    return counts


def _section(findings: list[Finding], title: str, prefixes: tuple[str, ...]) -> list[str]:
    selected = [finding for finding in findings if finding.check_id.startswith(prefixes)]
    lines = [f"## {title}", ""]
    if not selected:
        lines.extend(["No findings for this section.", ""])
        return lines
    lines.extend(["| severity | status | check_id | file_path | finding | recommended_action |", "| --- | --- | --- | --- | --- | --- |"])
    for finding in selected:
        lines.append(f"| {finding.severity} | {finding.status} | `{finding.check_id}` | `{finding.file_path}` | {finding.finding} | {finding.recommended_action} |")
    lines.append("")
    return lines


def write_markdown_report(findings: list[Finding], as_of_date: str, output_path: str | Path) -> Path:
    path = ensure_parent_dir(output_path)
    counts = _status_counts(findings)
    lines = [
        "# Clean-Room Reproduction Review Report",
        "",
        "## Executive Summary",
        "",
        f"- as_of_date: `{as_of_date}`",
        f"- total_rows: `{len(findings)}`",
        f"- pass: `{counts.get('PASS', 0)}`",
        f"- warn: `{counts.get('WARN', 0)}`",
        f"- fail: `{counts.get('FAIL', 0)}`",
        f"- missing: `{counts.get('MISSING', 0)}`",
        f"- not_available: `{counts.get('NOT_AVAILABLE', 0)}`",
        "",
        "This is a read-only clean-room reproduction review. It does not implement release acceptance, runtime enforcement, investment logic, broker import, replay, backtesting, dashboard, valuation automation or order execution.",
        "",
        "## Repo/Run Context",
        "",
        "- repo_relative_inputs_only: `true`",
        "- no_network_access_required: `true`",
        "- no_private_raw_inputs_required: `true`",
        "- external_packet_metadata_required_for_authoritative_review: `true`",
        "",
        "## Checked Files",
        "",
    ]
    for file_path in sorted({finding.file_path for finding in findings}):
        lines.append(f"- `{file_path}`")
    lines.append("")
    lines.extend(_section(findings, "Packet Metadata Presence", ("PACKET_METADATA",)))
    lines.extend(_section(findings, "SHA / ZIP / Manifest / Context", ("SHA", "ZIP", "INTERNAL_EXTERNAL", "SOURCE_OF_TRUTH")))
    lines.extend(_section(findings, "Validation Reality", ("VALIDATION",)))
    lines.extend(_section(findings, "Cross-Patch Reproduction", ("CROSS_PATCH",)))
    lines.extend(_section(findings, "ZIP-only vs Full-Packet Distinction", ("ZIP_ONLY", "ZIP_OPTIONAL", "SIMULATED")))
    lines.extend(_section(findings, "Non-Scope Preservation", ("NON_SCOPE",)))
    lines.extend(
        [
            "## Recommended Next Actions",
            "",
            "1. Keep external packet metadata adjacent to the ZIP and checksum for authoritative review.",
            "2. Treat `RECORDED` handoff commands as command provenance, not pass/fail proof.",
            "3. Regenerate ignored CSV/Markdown review outputs locally when they are not part of the handoff ZIP.",
            "4. Do not infer release, product, investment or production readiness from this review artifact.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_and_write(
    as_of_date: str,
    repo_root: str | Path = ".",
    csv_output: str | Path = DEFAULT_CSV_OUTPUT,
    report_output: str | Path | None = None,
    packet_root: str | Path = DEFAULT_PACKET_ROOT,
    simulate_extracted_zip: str | Path | None = None,
) -> dict[str, Any]:
    findings = run_clean_room_reproduction_review(
        as_of_date=as_of_date,
        repo_root=repo_root,
        packet_root=packet_root,
        simulate_extracted_zip=simulate_extracted_zip,
    )
    report_path = report_output or DEFAULT_REPORT_OUTPUT_TEMPLATE.format(as_of_date=as_of_date)
    write_csv(findings, csv_output)
    write_markdown_report(findings, as_of_date, report_path)
    counts = _status_counts(findings)
    return {
        "status": "WARN" if counts.get("FAIL", 0) or counts.get("WARN", 0) or counts.get("MISSING", 0) or counts.get("NOT_AVAILABLE", 0) else "OK",
        "as_of_date": as_of_date,
        "findings": len(findings),
        "counts": counts,
        "csv_output": Path(csv_output).as_posix(),
        "report_output": Path(report_path).as_posix(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a read-only clean-room reproduction review for the current external packet.")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--csv-output", default=DEFAULT_CSV_OUTPUT)
    parser.add_argument("--report-output")
    parser.add_argument("--packet-root", default=DEFAULT_PACKET_ROOT)
    parser.add_argument("--simulate-extracted-zip")
    args = parser.parse_args()
    result = run_and_write(
        as_of_date=args.as_of_date,
        repo_root=args.repo_root,
        csv_output=args.csv_output,
        report_output=args.report_output,
        packet_root=args.packet_root,
        simulate_extracted_zip=args.simulate_extracted_zip,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
