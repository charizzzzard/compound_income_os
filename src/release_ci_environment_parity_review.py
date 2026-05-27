from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import platform
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir

DEFAULT_CSV_OUTPUT = "data/processed/release_ci_environment_parity_review.csv"
DEFAULT_REPORT_OUTPUT_TEMPLATE = "reports/{as_of_date}/release_ci_environment_parity_review_report.md"
DEFAULT_PACKET_ROOT = "external_review_packet"

CSV_FIELDS = [
    "as_of_date",
    "check_id",
    "severity",
    "status",
    "scope",
    "command",
    "evidence",
    "finding",
    "recommended_action",
]

SEVERITY_ORDER = {"FAIL": 0, "WARN": 1, "NOT_AVAILABLE": 2, "INFO": 3, "PASS": 4}
STATUS_ORDER = {
    "RAN_FAILED": 0,
    "NOT_INSTALLED": 1,
    "SKIPPED_NOT_AVAILABLE": 2,
    "NOT_RUN": 3,
    "NOT_APPLICABLE": 4,
    "AVAILABLE": 5,
    "RAN_OK": 6,
}

EXPECTED_COMMANDS = [
    ("EXPECTED_UNITTEST_PARITY_REVIEW", "python -m unittest tests.test_release_ci_environment_parity_review -v", ("python_module", "unittest")),
    ("EXPECTED_PARITY_CLI", "python -m src.release_ci_environment_parity_review --as-of-date {as_of_date}", ("python_module", "src.release_ci_environment_parity_review")),
    ("EXPECTED_CLEAN_ROOM_TESTS", "python -m unittest tests.test_clean_room_reproduction_review -v", ("python_module", "unittest")),
    ("EXPECTED_CROSS_PATCH_TESTS", "python -m unittest tests.test_external_review_cross_patch_regression -v", ("python_module", "unittest")),
    ("EXPECTED_GIT_DIFF_CHECK", "git diff --check", ("binary", "git")),
    ("EXPECTED_PYTEST", "python -m pytest -q", ("python_module", "pytest")),
    ("EXPECTED_RUFF", "python -m ruff check .", ("python_module", "ruff")),
]

NON_SCOPE_STATEMENT = (
    "This read-only environment parity review does not implement release acceptance, "
    "runtime enforcement, investment logic, broker import, replay, backtesting, "
    "dashboard, outcome attribution, valuation automation or product/production readiness."
)


@dataclass(frozen=True)
class Finding:
    as_of_date: str
    check_id: str
    severity: str
    status: str
    scope: str
    command: str
    evidence: str
    finding: str
    recommended_action: str

    def row(self) -> dict[str, str]:
        return {
            "as_of_date": self.as_of_date,
            "check_id": self.check_id,
            "severity": self.severity,
            "status": self.status,
            "scope": self.scope,
            "command": self.command,
            "evidence": self.evidence,
            "finding": self.finding,
            "recommended_action": self.recommended_action,
        }


def _finding(
    as_of_date: str,
    check_id: str,
    severity: str,
    status: str,
    scope: str,
    command: str,
    evidence: str,
    finding: str,
    recommended_action: str,
) -> Finding:
    return Finding(
        as_of_date=as_of_date,
        check_id=check_id,
        severity=severity,
        status=status,
        scope=scope,
        command=command,
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
            item.scope,
            item.command,
            STATUS_ORDER.get(item.status, 99),
            item.finding,
        ),
    )


def _repo_context(repo_root: Path) -> str:
    cwd = Path.cwd().resolve()
    try:
        relative = cwd.relative_to(repo_root.resolve())
    except ValueError:
        return "OUTSIDE_REPO"
    return "." if str(relative) == "." else relative.as_posix()


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _binary_available(binary_name: str) -> bool:
    return shutil.which(binary_name) is not None


def _dependency_available(kind: str, name: str) -> bool:
    if kind == "python_module":
        return _module_available(name)
    if kind == "binary":
        return _binary_available(name)
    return False


def check_python_environment(as_of_date: str, repo_root: Path) -> list[Finding]:
    findings = [
        _finding(as_of_date, "PYTHON_EXECUTABLE", "INFO", "AVAILABLE", "python_environment", "python", Path(sys.executable).name, "Python executable name captured without local absolute path.", "Keep absolute local paths out of reports."),
        _finding(as_of_date, "PYTHON_VERSION", "INFO", "AVAILABLE", "python_environment", "python --version", platform.python_version(), "Python version captured for environment parity.", "Compare against future CI/Clean-Room baseline."),
        _finding(as_of_date, "PYTHON_IMPLEMENTATION", "INFO", "AVAILABLE", "python_environment", "platform.python_implementation", platform.python_implementation(), "Python implementation captured.", "Keep implementation visible for parity reviews."),
        _finding(as_of_date, "PLATFORM", "INFO", "AVAILABLE", "python_environment", "platform.system", f"{platform.system()} {platform.release()} {platform.machine()}".strip(), "Platform captured without local path details.", "Compare against future CI/Clean-Room baseline."),
        _finding(as_of_date, "WORKING_DIRECTORY_CONTEXT", "INFO", "AVAILABLE", "repo_context", "Path.cwd", _repo_context(repo_root), "Working directory captured as repo-relative context.", "Avoid absolute local path leakage."),
    ]
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    findings.append(_finding(as_of_date, "VIRTUAL_ENVIRONMENT", "INFO", "AVAILABLE" if in_venv else "NOT_APPLICABLE", "python_environment", "sys.prefix", f"in_virtualenv={in_venv}", "Virtual environment state captured without path value.", "Keep environment state visible without leaking local paths."))
    return findings


def check_tool_availability(as_of_date: str) -> list[Finding]:
    checks = [
        ("TOOL_UNITTEST", "unittest", "python_module", "python -m unittest"),
        ("TOOL_PYTEST", "pytest", "python_module", "python -m pytest"),
        ("TOOL_RUFF", "ruff", "python_module", "python -m ruff"),
        ("TOOL_GIT", "git", "binary", "git"),
        ("TOOL_PYTHON_M_EXECUTION", "runpy", "python_module", "python -m"),
    ]
    findings: list[Finding] = []
    for check_id, name, kind, command in checks:
        available = _dependency_available(kind, name)
        if available:
            findings.append(_finding(as_of_date, check_id, "PASS", "AVAILABLE", "tool_availability", command, f"{kind}:{name}", "Tool/module required for the command class is available.", "Command may be run by validation, but availability alone is not command success."))
        else:
            severity = "WARN" if name in {"pytest", "ruff"} else "FAIL"
            findings.append(_finding(as_of_date, check_id, severity, "NOT_INSTALLED", "tool_availability", command, f"{kind}:{name}", "Tool/module required for the command class is not installed or not discoverable.", "Install only if this tool is accepted as required for the environment baseline."))
    return findings


def check_expected_commands(as_of_date: str) -> list[Finding]:
    findings: list[Finding] = []
    for check_id, command_template, dependency in EXPECTED_COMMANDS:
        command = command_template.format(as_of_date=as_of_date)
        kind, name = dependency
        available = _dependency_available(kind, name)
        if available:
            findings.append(_finding(as_of_date, check_id, "INFO", "NOT_RUN", "expected_validation_command", command, f"dependency={kind}:{name} available", "Expected command dependency is available; command execution is handled by explicit validation, not by this producer.", "Record actual command result separately as RAN_OK or RAN_FAILED in the patch report."))
        else:
            findings.append(_finding(as_of_date, check_id, "WARN", "SKIPPED_NOT_AVAILABLE", "expected_validation_command", command, f"dependency={kind}:{name} not available", "Expected command cannot run in this environment because its dependency is unavailable.", "Do not report this command as successful; install dependency only if required by governance baseline."))
    return findings


def check_handoff_validation_recording(as_of_date: str, repo_root: Path, packet_root: str | Path) -> list[Finding]:
    packet = Path(packet_root)
    if not packet.is_absolute():
        packet = repo_root / packet
    zip_path = packet / "HANDOFF_LATEST.zip"
    if not zip_path.exists():
        return [_finding(as_of_date, "HANDOFF_VALIDATION_RECORDED", "WARN", "NOT_APPLICABLE", "handoff_packet", "HANDOFF_VALIDATION.txt", "ZIP_NOT_AVAILABLE", "Handoff validation metadata cannot be inspected without ZIP.", "Regenerate handoff before treating recorded commands as packet evidence.")]
    try:
        import zipfile

        with zipfile.ZipFile(zip_path) as archive:
            if "HANDOFF_VALIDATION.txt" not in archive.namelist():
                return [_finding(as_of_date, "HANDOFF_VALIDATION_RECORDED", "WARN", "NOT_APPLICABLE", "handoff_packet", "HANDOFF_VALIDATION.txt", "missing", "Handoff validation metadata is not present.", "Regenerate handoff with validation metadata.")]
            text = archive.read("HANDOFF_VALIDATION.txt").decode("utf-8", errors="replace")
    except zipfile.BadZipFile as exc:
        return [_finding(as_of_date, "HANDOFF_VALIDATION_RECORDED", "FAIL", "RAN_FAILED", "handoff_packet", "HANDOFF_VALIDATION.txt", type(exc).__name__, "Handoff ZIP is unreadable.", "Regenerate handoff ZIP.")]
    if "status: RECORDED" in text:
        return [_finding(as_of_date, "HANDOFF_VALIDATION_RECORDED", "WARN", "NOT_RUN", "handoff_packet", "HANDOFF_VALIDATION.txt", "status: RECORDED", "Handoff embeds command provenance, not true command exit-code results.", "Keep actual validation command results in external context and patch report.")]
    return [_finding(as_of_date, "HANDOFF_VALIDATION_RECORDED", "PASS", "AVAILABLE", "handoff_packet", "HANDOFF_VALIDATION.txt", "no RECORDED markers", "Handoff validation does not use RECORDED markers.", "Keep command-result semantics explicit.")]


def run_environment_parity_review(
    as_of_date: str,
    repo_root: str | Path = ".",
    packet_root: str | Path = DEFAULT_PACKET_ROOT,
) -> list[Finding]:
    root = Path(repo_root).resolve()
    findings: list[Finding] = []
    findings.extend(check_python_environment(as_of_date, root))
    findings.extend(check_tool_availability(as_of_date))
    findings.extend(check_expected_commands(as_of_date))
    findings.extend(check_handoff_validation_recording(as_of_date, root, packet_root))
    findings.append(_finding(as_of_date, "NON_SCOPE_BOUNDARY", "PASS", "NOT_APPLICABLE", "governance_boundary", "n/a", NON_SCOPE_STATEMENT, "Environment parity review remains governance evidence only.", "Do not infer release, product, production or investment readiness."))
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
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.status] = counts.get(finding.status, 0) + 1
    return dict(sorted(counts.items()))


def _severity_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: SEVERITY_ORDER.get(item[0], 99)))


def _section(findings: list[Finding], title: str, scopes: tuple[str, ...]) -> list[str]:
    selected = [finding for finding in findings if finding.scope in scopes]
    lines = [f"## {title}", ""]
    if not selected:
        lines.extend(["No rows for this section.", ""])
        return lines
    lines.extend(["| severity | status | check_id | command | evidence | finding |", "| --- | --- | --- | --- | --- | --- |"])
    for finding in selected:
        lines.append(f"| {finding.severity} | {finding.status} | `{finding.check_id}` | `{finding.command}` | {finding.evidence} | {finding.finding} |")
    lines.append("")
    return lines


def write_markdown_report(findings: list[Finding], as_of_date: str, output_path: str | Path) -> Path:
    path = ensure_parent_dir(output_path)
    lines = [
        "# Release CI Environment Parity Review Report",
        "",
        "## Executive Summary",
        "",
        f"- as_of_date: `{as_of_date}`",
        f"- total_rows: `{len(findings)}`",
        f"- severity_counts: `{json.dumps(_severity_counts(findings), sort_keys=True)}`",
        f"- status_counts: `{json.dumps(_status_counts(findings), sort_keys=True)}`",
        "",
        NON_SCOPE_STATEMENT,
        "",
        "This producer records environment parity evidence. It does not execute expensive validation commands by default and does not convert tool availability into command success.",
        "",
    ]
    lines.extend(_section(findings, "Python Environment", ("python_environment", "repo_context")))
    lines.extend(_section(findings, "Tool Availability", ("tool_availability",)))
    lines.extend(_section(findings, "Expected Validation Commands", ("expected_validation_command",)))
    lines.extend(_section(findings, "Handoff Validation Reality", ("handoff_packet",)))
    lines.extend(_section(findings, "Non-Scope Boundary", ("governance_boundary",)))
    lines.extend(
        [
            "## Recommended Next Actions",
            "",
            "1. Treat `NOT_INSTALLED` pytest/ruff rows as environment limitations, not green results.",
            "2. Record actual command execution separately when commands are run by the operator or CI.",
            "3. Do not claim CI-green, release acceptance or production readiness from this local parity report.",
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
) -> dict[str, Any]:
    findings = run_environment_parity_review(as_of_date=as_of_date, repo_root=repo_root, packet_root=packet_root)
    report_path = report_output or DEFAULT_REPORT_OUTPUT_TEMPLATE.format(as_of_date=as_of_date)
    write_csv(findings, csv_output)
    write_markdown_report(findings, as_of_date, report_path)
    return {
        "status": "WARN" if any(finding.severity in {"WARN", "FAIL"} for finding in findings) else "OK",
        "as_of_date": as_of_date,
        "findings": len(findings),
        "severity_counts": _severity_counts(findings),
        "status_counts": _status_counts(findings),
        "csv_output": Path(csv_output).as_posix(),
        "report_output": Path(report_path).as_posix(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run read-only release CI environment parity review.")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--csv-output", default=DEFAULT_CSV_OUTPUT)
    parser.add_argument("--report-output")
    parser.add_argument("--packet-root", default=DEFAULT_PACKET_ROOT)
    args = parser.parse_args()
    result = run_and_write(
        as_of_date=args.as_of_date,
        repo_root=args.repo_root,
        csv_output=args.csv_output,
        report_output=args.report_output,
        packet_root=args.packet_root,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
