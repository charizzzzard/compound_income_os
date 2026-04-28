from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from src.common import ensure_parent_dir, resolve_repo_path, write_csv_rows

DEFAULT_OUTPUT = "data/processed/repo_docs_drift_check.csv"
DEFAULT_REPORT_OUTPUT = "reports/2026-04-28/repo_docs_drift_check_report.md"

FIELDS = ["finding_id", "finding_type", "path", "docs_target", "severity", "status", "notes"]


@dataclass(frozen=True)
class DocsDriftCheckResult:
    output_path: Path
    report_path: Path
    findings: list[dict[str, str]]


def _read_text(path_value: str | Path) -> str:
    path = resolve_repo_path(path_value)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _module_name(path: Path) -> str:
    return f"src.{path.stem}"


def build_findings() -> list[dict[str, str]]:
    root = resolve_repo_path(".")
    module_contracts = _read_text("docs/MODULE_CONTRACTS.md")
    handoff_contract = _read_text("docs/HANDOFF_CONTRACT.md")
    website_readme = _read_text("website/compound-income-os-landing/README.md")
    findings: list[dict[str, str]] = []

    for path in sorted((root / "src").glob("*.py")):
        if path.name == "__init__.py":
            continue
        rel = path.relative_to(root).as_posix()
        if _module_name(path) not in module_contracts and path.stem not in module_contracts:
            findings.append(
                {
                    "finding_id": "",
                    "finding_type": "MODULE_NOT_MENTIONED",
                    "path": rel,
                    "docs_target": "docs/MODULE_CONTRACTS.md",
                    "severity": "REVIEW",
                    "status": "OPEN",
                    "notes": "Source module is not mentioned in module contracts.",
                }
            )

    for path in sorted((root / "src").glob("*handoff*.py")):
        rel = path.relative_to(root).as_posix()
        if path.stem not in handoff_contract:
            findings.append(
                {
                    "finding_id": "",
                    "finding_type": "HANDOFF_MODULE_NOT_MENTIONED",
                    "path": rel,
                    "docs_target": "docs/HANDOFF_CONTRACT.md",
                    "severity": "REVIEW",
                    "status": "OPEN",
                    "notes": "Handoff-related module should be covered by the handoff contract.",
                }
            )

    mockup = "website/compound-income-os-landing/mockup"
    claude = "website/compound-income-os-landing/mockup/source_materials/claude_design_compound_income_os"
    if mockup not in website_readme:
        findings.append(
            {
                "finding_id": "",
                "finding_type": "WEBSITE_MOCKUP_FOLDER_NOT_MENTIONED",
                "path": mockup,
                "docs_target": "website/compound-income-os-landing/README.md",
                "severity": "REVIEW",
                "status": "OPEN",
                "notes": "Website mockup source folder is not documented.",
            }
        )
    if claude not in website_readme:
        findings.append(
            {
                "finding_id": "",
                "finding_type": "CLAUDE_REFERENCE_FOLDER_NOT_MENTIONED",
                "path": claude,
                "docs_target": "website/compound-income-os-landing/README.md",
                "severity": "REVIEW",
                "status": "OPEN",
                "notes": "Claude design reference folder is not documented.",
            }
        )

    for index, row in enumerate(findings, start=1):
        row["finding_id"] = f"DOCS_DRIFT_{index:04d}"
    return findings


def render_report(findings: list[dict[str, str]]) -> str:
    lines = [
        "# Repo Docs Drift Check",
        "",
        "## Summary",
        "",
        f"- findings_count: {len(findings)}",
        "- mode: review-only",
        "",
        "## Findings",
        "",
    ]
    if findings:
        for row in findings:
            lines.append(f"- `{row['finding_id']}` {row['finding_type']} `{row['path']}` -> `{row['docs_target']}`")
    else:
        lines.append("- None.")
    lines.extend(["", "## Guardrails", "", "- This check reports documentation drift only.", "- It does not mutate source data, scores, or website build artifacts."])
    return "\n".join(lines) + "\n"


def run_repo_docs_drift_check(*, output: str | Path = DEFAULT_OUTPUT, report_output: str | Path = DEFAULT_REPORT_OUTPUT) -> DocsDriftCheckResult:
    findings = build_findings()
    output_path = write_csv_rows(output, FIELDS, findings)
    report_path = ensure_parent_dir(report_output)
    report_path.write_text(render_report(findings), encoding="utf-8")
    return DocsDriftCheckResult(resolve_repo_path(output_path), resolve_repo_path(report_path), findings)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report lightweight documentation drift findings.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_repo_docs_drift_check(output=args.output, report_output=args.report_output)
    print(f"docs_drift_output={result.output_path}")
    print(f"docs_drift_report={result.report_path}")
    print(f"docs_drift_findings={len(result.findings)}")


if __name__ == "__main__":
    main()
