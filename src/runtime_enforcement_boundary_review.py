from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir

DEFAULT_CSV_OUTPUT = "data/processed/runtime_enforcement_boundary_review.csv"
DEFAULT_REPORT_OUTPUT_TEMPLATE = "reports/{as_of_date}/runtime_enforcement_boundary_review_report.md"

REGISTRY_PATH = "docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml"
SEQUENCE_PATH = "docs/governance/EXTERNAL_REVIEW_GATE_SEQUENCE.md"
COVERAGE_STANDARD_PATH = "docs/governance/EXTERNAL_REVIEW_COVERAGE_STANDARD.md"
FEATURE_STATUS_PATH = "docs/architecture/CIOS_FEATURE_STATUS.yaml"
KNOWN_GAPS_PATH = "docs/architecture/CURRENT_KNOWN_GAPS.md"
SYSTEM_MAP_PATH = "docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md"
MODULE_CONTRACTS_PATH = "docs/MODULE_CONTRACTS.md"
CONTEXT_ROADMAP_PATH = "docs/CONTEXT_AND_ROADMAP.md"
README_PATH = "README.md"

RELEVANT_TEXT_FILES = [
    REGISTRY_PATH,
    SEQUENCE_PATH,
    COVERAGE_STANDARD_PATH,
    FEATURE_STATUS_PATH,
    KNOWN_GAPS_PATH,
    SYSTEM_MAP_PATH,
    MODULE_CONTRACTS_PATH,
    CONTEXT_ROADMAP_PATH,
    README_PATH,
]

BOUNDARY_MODULES = {
    "src.release_ci_environment_parity_review": "release_ci_environment_parity_review",
    "src.clean_room_reproduction_review": "clean_room_reproduction_review",
    "src.external_review_cross_patch_regression": "external_review_cross_patch_regression",
    "src.handoff_bundle": "handoff_bundle",
    "src.portfolio_event_ledger_validation": "portfolio_event_ledger_validation",
    "src.data_source_registry_validation": "data_source_registry_validation",
}

NON_SCOPE_REQUIREMENTS = {
    "runtime_enforcement_engine": [
        "does not implement runtime enforcement",
        "does not implement any gate as runtime enforcement",
        "keine Runtime-Enforcement-Engine",
        "not runtime enforcement",
    ],
    "automatic_release_acceptance": [
        "keine automatische Release-Akzeptanz",
        "keine vollautomatische Release-Akzeptanz",
        "no release acceptance",
        "no automated release acceptance",
        "not release acceptance",
    ],
    "runtime_llm_agent_logic": [
        "keine Runtime-LLM-Agentenlogik",
        "Runtime-LLM-Agentenlogik",
        "runtime LLM",
    ],
    "broker_order_execution": [
        "kein Broker Import",
        "keine Order Execution",
        "no broker import",
        "order execution",
    ],
    "product_investment_readiness": [
        "Product-/Production-Readiness",
        "Investment-Readiness",
        "product readiness",
        "investment readiness",
        "Production-Readiness",
    ],
}

RISKY_PATTERNS = {
    "runtime_enforced": re.compile(r"\bruntime[_ -]?enforced\b|\bruntime enforcement engine\b", re.IGNORECASE),
    "release_acceptance": re.compile(r"\brelease acceptance\b|Release-Akzeptanz", re.IGNORECASE),
    "production_ready": re.compile(r"\bproduction[_ -]?ready\b|Production-Readiness|product readiness", re.IGNORECASE),
    "investment_ready": re.compile(r"\binvestment readiness\b|Investment-Readiness", re.IGNORECASE),
    "broker_order_execution": re.compile(r"\border execution\b|Order Execution|broker import production", re.IGNORECASE),
    "runtime_llm": re.compile(r"\bruntime LLM\b|Runtime-LLM-Agentenlogik", re.IGNORECASE),
    "dashboard_readiness": re.compile(r"\bdashboard readiness\b", re.IGNORECASE),
    "replay_backtesting_outcome": re.compile(r"\breplay readiness\b|\bbacktesting readiness\b|\boutcome-attribution readiness\b", re.IGNORECASE),
}

NEGATION_MARKERS = (
    "no ",
    "not ",
    "does not",
    "do not",
    "without",
    "must never",
    "non-scope",
    "keine",
    "kein",
    "nicht",
    "blocked",
    "remain open",
    "not imply",
    "not implement",
    "not feature readiness",
    "not runtime enforcement",
    "not release acceptance",
)

SAFE_REVIEW_CONTEXT_MARKERS = (
    "review whether",
    "review readiness",
    "before ",
    "blocks_features",
    "trigger_condition",
    "gate_id",
    "gate_name",
    "non_scope",
    "required_inputs",
    "required_outputs",
    "acceptance_criteria",
    "evidence_required",
    "operator_acceptance_required",
    "blocked until",
    "blocks ",
    "boundary",
    "boundaries",
    "coverage for",
    "distinguish",
    "separate",
    "trennt",
    "`production_ready`",
    "`operationally_ready`",
    "`enforced`",
    "readiness review",
    "source-of-truth",
)

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

SEVERITY_ORDER = {"FAIL": 0, "WARN": 1, "NOT_AVAILABLE": 2, "INFO": 3, "PASS": 4}
STATUS_ORDER = {"FAIL": 0, "WARN": 1, "NOT_AVAILABLE": 2, "PASS": 3}


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


def _repo_path(repo_root: Path, relative_path: str) -> Path:
    return repo_root / relative_path


def _read_text(repo_root: Path, relative_path: str) -> str | None:
    path = _repo_path(repo_root, relative_path)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _load_json_file(repo_root: Path, relative_path: str) -> tuple[dict[str, Any] | None, str | None]:
    text = _read_text(repo_root, relative_path)
    if text is None:
        return None, "file missing"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"json parse error: {exc}"
    if not isinstance(data, dict):
        return None, "root is not a mapping"
    return data, None


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
        file_path=file_path,
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


def _combined_text(repo_root: Path, paths: list[str]) -> tuple[str, list[str]]:
    texts: list[str] = []
    missing: list[str] = []
    for relative_path in paths:
        text = _read_text(repo_root, relative_path)
        if text is None:
            missing.append(relative_path)
        else:
            texts.append(text)
    return "\n".join(texts), missing


def check_non_scope_present(as_of_date: str, repo_root: Path) -> list[Finding]:
    combined, missing = _combined_text(repo_root, RELEVANT_TEXT_FILES)
    findings: list[Finding] = []
    if missing:
        findings.append(_finding(as_of_date, "RUNTIME_ENFORCEMENT_NON_SCOPE_PRESENT", "NOT_AVAILABLE", "NOT_AVAILABLE", "multiple", "; ".join(missing), "One or more boundary source files are missing.", "Restore the missing governance/status files."))

    lower = combined.lower()
    missing_labels = [
        label
        for label, variants in NON_SCOPE_REQUIREMENTS.items()
        if not any(variant.lower() in lower for variant in variants)
    ]
    if missing_labels:
        findings.append(_finding(as_of_date, "RUNTIME_ENFORCEMENT_NON_SCOPE_PRESENT", "FAIL", "FAIL", "multiple", "; ".join(missing_labels), "Required runtime-enforcement non-scope boundaries are not all visible.", "Restore explicit non-scope language before runtime-sensitive work."))
    else:
        findings.append(_finding(as_of_date, "RUNTIME_ENFORCEMENT_NON_SCOPE_PRESENT", "PASS", "PASS", "multiple", f"checked={len(NON_SCOPE_REQUIREMENTS)}", "Required runtime-enforcement non-scope boundaries remain visible.", "Keep these boundaries explicit in future handoffs."))
    return findings


def _line_is_negated(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in NEGATION_MARKERS)


def _line_is_review_context(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in SAFE_REVIEW_CONTEXT_MARKERS)


def check_runtime_language_overclaim(as_of_date: str, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    risky_hits: list[str] = []
    missing: list[str] = []
    for relative_path in RELEVANT_TEXT_FILES:
        text = _read_text(repo_root, relative_path)
        if text is None:
            missing.append(relative_path)
            continue
        previous_lines: list[str] = []
        in_non_scope_section = False
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.lower() == "## non-scope":
                in_non_scope_section = True
            elif stripped.startswith("## ") and stripped.lower() != "## non-scope":
                in_non_scope_section = False

            context_line = " ".join([*previous_lines[-3:], line])
            previous_lines.append(line)
            if stripped.startswith("## ") or in_non_scope_section or _line_is_negated(context_line) or _line_is_review_context(context_line):
                continue
            for label, pattern in RISKY_PATTERNS.items():
                if pattern.search(line):
                    risky_hits.append(f"{relative_path}:{line_no}:{label}:{line.strip()[:180]}")

    if missing:
        findings.append(_finding(as_of_date, "RUNTIME_LANGUAGE_OVERCLAIM_SCAN", "NOT_AVAILABLE", "NOT_AVAILABLE", "multiple", "; ".join(missing), "One or more files could not be scanned for overclaim language.", "Restore missing files or narrow the scan list."))
    if risky_hits:
        findings.append(_finding(as_of_date, "RUNTIME_LANGUAGE_OVERCLAIM_SCAN", "WARN", "WARN", "multiple", " | ".join(risky_hits[:8]), "Potential runtime/release/product overclaim language appears without an obvious negation marker.", "Review each line and either add explicit non-scope wording or provide implementation evidence."))
    else:
        findings.append(_finding(as_of_date, "RUNTIME_LANGUAGE_OVERCLAIM_SCAN", "PASS", "PASS", "multiple", f"scanned_files={len(RELEVANT_TEXT_FILES) - len(missing)}", "No unnegated runtime/release/product readiness overclaim language was found in the reviewed surface.", "Keep risky readiness language paired with explicit boundaries."))
    return findings


def check_registry_alignment(as_of_date: str, repo_root: Path) -> list[Finding]:
    data, error = _load_json_file(repo_root, REGISTRY_PATH)
    if error:
        return [_finding(as_of_date, "REVIEW_GATE_REGISTRY_ALIGNMENT", "FAIL", "FAIL", REGISTRY_PATH, error, "Gate registry cannot be loaded.", "Restore valid gate registry JSON/YAML.")]

    gates = data.get("gates", [])
    if not isinstance(gates, list):
        return [_finding(as_of_date, "REVIEW_GATE_REGISTRY_ALIGNMENT", "FAIL", "FAIL", REGISTRY_PATH, "gates is not a list", "Gate registry has no gates list.", "Represent gates as a list.")]

    gate = next((item for item in gates if isinstance(item, dict) and item.get("gate_id") == "RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW"), None)
    if gate is None:
        return [_finding(as_of_date, "REVIEW_GATE_REGISTRY_ALIGNMENT", "FAIL", "FAIL", REGISTRY_PATH, "missing gate", "RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW is not registered.", "Add the gate before runtime-sensitive work.")]

    text = json.dumps(gate, sort_keys=True).lower()
    required_fragments = ["runtime implementation", "feature readiness approval", "runtime_stage_integration", "production_workflow_claims", "dashboard_readiness_claims"]
    missing_fragments = [fragment for fragment in required_fragments if fragment not in text]
    if missing_fragments:
        return [_finding(as_of_date, "REVIEW_GATE_REGISTRY_ALIGNMENT", "WARN", "WARN", REGISTRY_PATH, "; ".join(missing_fragments), "Runtime enforcement gate exists but misses one or more governance-only/blocking semantics.", "Keep the registry gate explicitly governance-only and blocking runtime/readiness claims.")]
    return [_finding(as_of_date, "REVIEW_GATE_REGISTRY_ALIGNMENT", "PASS", "PASS", REGISTRY_PATH, "RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW", "Runtime enforcement boundary gate is registered with governance-only semantics.", "Keep registry and sequence aligned.")]


def check_sequence_alignment(as_of_date: str, repo_root: Path) -> list[Finding]:
    text = _read_text(repo_root, SEQUENCE_PATH)
    if text is None:
        return [_finding(as_of_date, "REVIEW_GATE_SEQUENCE_ALIGNMENT", "FAIL", "FAIL", SEQUENCE_PATH, "file missing", "Gate sequence cannot be reviewed.", "Restore gate sequence document.")]

    required_sections = [
        "Before Portfolio Event Ledger Runtime",
        "Before Broker Import Staging",
        "Before Dashboard Expansion",
    ]
    missing_sections = [section for section in required_sections if section not in text]
    if missing_sections:
        return [_finding(as_of_date, "REVIEW_GATE_SEQUENCE_ALIGNMENT", "FAIL", "FAIL", SEQUENCE_PATH, "; ".join(missing_sections), "Runtime-sensitive sequence sections are missing.", "Restore runtime-sensitive sequence sections.")]

    missing_gate_sections: list[str] = []
    for section in required_sections:
        marker = f"## {section}"
        start = text.find(marker)
        end = text.find("\n## ", start + len(marker))
        section_text = text[start:] if end == -1 else text[start:end]
        if "RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW" not in section_text:
            missing_gate_sections.append(section)
    if missing_gate_sections:
        return [_finding(as_of_date, "REVIEW_GATE_SEQUENCE_ALIGNMENT", "WARN", "WARN", SEQUENCE_PATH, "; ".join(missing_gate_sections), "Runtime enforcement boundary gate is not sequenced before all expected runtime-sensitive work.", "Add the gate to the listed sections or document why it is not sequenced.")]
    return [_finding(as_of_date, "REVIEW_GATE_SEQUENCE_ALIGNMENT", "PASS", "PASS", SEQUENCE_PATH, "Portfolio Event Ledger Runtime; Broker Import Staging; Dashboard Expansion", "Runtime enforcement boundary gate is sequenced before reviewed runtime-sensitive work.", "Keep sequence conservative.")]


def check_module_boundary_clarity(as_of_date: str, repo_root: Path) -> list[Finding]:
    module_contracts = _read_text(repo_root, MODULE_CONTRACTS_PATH)
    if module_contracts is None:
        return [_finding(as_of_date, "MODULE_BOUNDARY_CLARITY", "FAIL", "FAIL", MODULE_CONTRACTS_PATH, "file missing", "Module contracts cannot be reviewed.", "Restore module contracts.")]

    missing_modules = [module for module, label in BOUNDARY_MODULES.items() if label not in module_contracts and module not in module_contracts]
    if missing_modules:
        return [_finding(as_of_date, "MODULE_BOUNDARY_CLARITY", "WARN", "WARN", MODULE_CONTRACTS_PATH, "; ".join(missing_modules), "One or more boundary-sensitive modules are not referenced in module contracts.", "Add conservative module-contract references.")]

    risky_lines: list[str] = []
    for line_no, line in enumerate(module_contracts.splitlines(), start=1):
        if any(label in line for label in BOUNDARY_MODULES.values()):
            lowered = line.lower()
            if "runtime-enforcement-engine" not in lowered and "runtime enforcement" in lowered and "keine" not in lowered and "does not" not in lowered:
                risky_lines.append(f"{line_no}:{line.strip()[:180]}")
    if risky_lines:
        return [_finding(as_of_date, "MODULE_BOUNDARY_CLARITY", "WARN", "WARN", MODULE_CONTRACTS_PATH, " | ".join(risky_lines), "A boundary-sensitive module line may imply runtime enforcement.", "Clarify that module is read-only/governance-only.")]

    return [_finding(as_of_date, "MODULE_BOUNDARY_CLARITY", "PASS", "PASS", MODULE_CONTRACTS_PATH, f"checked_modules={len(BOUNDARY_MODULES)}", "Boundary-sensitive modules are documented without runtime enforcement claims.", "Keep module contracts conservative.")]


def check_no_runtime_actions(as_of_date: str, repo_root: Path) -> list[Finding]:
    source_path = "src/runtime_enforcement_boundary_review.py"
    text = _read_text(repo_root, source_path)
    if text is None:
        return [_finding(as_of_date, "NO_RUNTIME_ACTIONS", "FAIL", "FAIL", source_path, "file missing", "Runtime enforcement boundary review source is missing.", "Restore the read-only producer.")]
    forbidden_imports = ["requests", "urllib", "httpx", "socket", "subprocess"]
    used = [name for name in forbidden_imports if re.search(rf"^\s*import\s+{re.escape(name)}\b|^\s*from\s+{re.escape(name)}\b", text, re.MULTILINE)]
    if used:
        return [_finding(as_of_date, "NO_RUNTIME_ACTIONS", "FAIL", "FAIL", source_path, "; ".join(used), "Producer imports network/process modules outside read-only scope.", "Remove network/process dependencies.")]
    return [_finding(as_of_date, "NO_RUNTIME_ACTIONS", "PASS", "PASS", source_path, "no network/process imports", "Producer is local-only and writes only deterministic CSV/Markdown review outputs.", "Keep this producer out of runtime pipelines.")]


def run_runtime_enforcement_boundary_review(as_of_date: str, repo_root: str | Path = ".") -> list[Finding]:
    root = Path(repo_root).resolve()
    findings: list[Finding] = []
    findings.extend(check_non_scope_present(as_of_date, root))
    findings.extend(check_runtime_language_overclaim(as_of_date, root))
    findings.extend(check_registry_alignment(as_of_date, root))
    findings.extend(check_sequence_alignment(as_of_date, root))
    findings.extend(check_module_boundary_clarity(as_of_date, root))
    findings.extend(check_no_runtime_actions(as_of_date, root))
    return _sort_findings(findings)


def _severity_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: SEVERITY_ORDER.get(item[0], 99)))


def _status_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.status] = counts.get(finding.status, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: STATUS_ORDER.get(item[0], 99)))


def write_csv(findings: list[Finding], output_path: str | Path) -> Path:
    path = ensure_parent_dir(output_path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for finding in findings:
            writer.writerow(finding.row())
    return path


def _section(findings: list[Finding], title: str, check_prefixes: tuple[str, ...]) -> list[str]:
    selected = [finding for finding in findings if finding.check_id.startswith(check_prefixes)]
    lines = [f"## {title}", ""]
    if not selected:
        lines.extend(["No findings in this section.", ""])
        return lines
    lines.extend(["| severity | status | check_id | file_path | evidence | finding |", "| --- | --- | --- | --- | --- | --- |"])
    for finding in selected:
        lines.append(f"| {finding.severity} | {finding.status} | `{finding.check_id}` | `{finding.file_path}` | {finding.evidence} | {finding.finding} |")
    lines.append("")
    return lines


def write_markdown_report(findings: list[Finding], as_of_date: str, output_path: str | Path) -> Path:
    path = ensure_parent_dir(output_path)
    lines = [
        "# Runtime Enforcement Boundary Review Report",
        "",
        "## Executive Summary",
        "",
        f"- as_of_date: `{as_of_date}`",
        f"- total_rows: `{len(findings)}`",
        f"- severity_counts: `{json.dumps(_severity_counts(findings), sort_keys=True)}`",
        f"- status_counts: `{json.dumps(_status_counts(findings), sort_keys=True)}`",
        "",
        "This is a read-only governance review. It is not runtime enforcement, not release acceptance, not product readiness and not investment readiness.",
        "",
        "Human Operator remains the final acceptance authority. This report distinguishes documentation, validation, review and reporting from runtime enforcement.",
        "",
        "## Scope",
        "",
        "- Review runtime-enforcement non-scope language.",
        "- Scan reviewed governance/status surfaces for overclaim wording.",
        "- Check gate registry and gate sequence alignment.",
        "- Check module boundary clarity for read-only governance producers and template validators.",
        "- Check that this producer has no network/process imports and writes only deterministic review outputs.",
        "",
        "## Non-Scope",
        "",
        "- No Runtime Enforcement Engine.",
        "- No automatic release acceptance.",
        "- No runtime LLM agents.",
        "- No broker import, broker parser, provider adapter, API integration or order execution.",
        "- No dashboard expansion, replay, backtesting, simulation, outcome attribution or valuation automation.",
        "- No product, production or investment readiness.",
        "",
    ]
    lines.extend(_section(findings, "Non-Scope Presence", ("RUNTIME_ENFORCEMENT_NON_SCOPE_PRESENT",)))
    lines.extend(_section(findings, "Language Overclaim Scan", ("RUNTIME_LANGUAGE_OVERCLAIM_SCAN",)))
    lines.extend(_section(findings, "Gate Alignment", ("REVIEW_GATE_",)))
    lines.extend(_section(findings, "Module Boundary Clarity", ("MODULE_BOUNDARY_CLARITY",)))
    lines.extend(_section(findings, "No Runtime Actions", ("NO_RUNTIME_ACTIONS",)))
    lines.extend(
        [
            "## Recommended Next Actions",
            "",
            "1. Treat this report as review evidence, not enforcement.",
            "2. Keep runtime-sensitive work blocked until the Human Operator accepts the relevant gate findings.",
            "3. Add implementation evidence only when runtime enforcement is explicitly scoped in a later patch.",
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
) -> dict[str, Any]:
    findings = run_runtime_enforcement_boundary_review(as_of_date=as_of_date, repo_root=repo_root)
    report_path = report_output or DEFAULT_REPORT_OUTPUT_TEMPLATE.format(as_of_date=as_of_date)
    write_csv(findings, csv_output)
    write_markdown_report(findings, as_of_date, report_path)
    status = "WARN" if any(finding.severity in {"WARN", "FAIL"} for finding in findings) else "OK"
    return {
        "status": status,
        "as_of_date": as_of_date,
        "findings": len(findings),
        "severity_counts": _severity_counts(findings),
        "status_counts": _status_counts(findings),
        "csv_output": Path(csv_output).as_posix(),
        "report_output": Path(report_path).as_posix(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run read-only runtime enforcement boundary review.")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--csv-output", default=DEFAULT_CSV_OUTPUT)
    parser.add_argument("--report-output")
    args = parser.parse_args()
    result = run_and_write(
        as_of_date=args.as_of_date,
        repo_root=args.repo_root,
        csv_output=args.csv_output,
        report_output=args.report_output,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
