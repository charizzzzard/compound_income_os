from __future__ import annotations

import argparse
import csv
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, resolve_repo_path

DEFAULT_CSV_OUTPUT = "data/processed/external_review_cross_patch_regression.csv"
DEFAULT_REPORT_OUTPUT_TEMPLATE = "reports/{as_of_date}/external_review_cross_patch_regression_report.md"

REGISTRY_PATH = "docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml"
SEQUENCE_PATH = "docs/governance/EXTERNAL_REVIEW_GATE_SEQUENCE.md"
COVERAGE_STANDARD_PATH = "docs/governance/EXTERNAL_REVIEW_COVERAGE_STANDARD.md"
FEATURE_STATUS_PATH = "docs/architecture/CIOS_FEATURE_STATUS.yaml"
KNOWN_GAPS_PATH = "docs/architecture/CURRENT_KNOWN_GAPS.md"
SYSTEM_MAP_PATH = "docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md"
MATURITY_MODEL_PATH = "docs/architecture/CIOS_MATURITY_MODEL.yaml"
MODULE_CONTRACTS_PATH = "docs/MODULE_CONTRACTS.md"
CONTEXT_ROADMAP_PATH = "docs/CONTEXT_AND_ROADMAP.md"
README_PATH = "README.md"
EXTERNAL_README_PATH = "external_review_packet/00_READ_ME_FIRST.md"
EXTERNAL_CONTEXT_PATH = "external_review_packet/HANDOFF_LATEST_CONTEXT.md"
EXTERNAL_SHA_PATH = "external_review_packet/HANDOFF_LATEST.sha256"
EXTERNAL_ZIP_PATH = "external_review_packet/HANDOFF_LATEST.zip"

REQUIRED_GATE_FIELDS = [
    "gate_id",
    "priority",
    "purpose",
    "trigger_condition",
    "required_inputs",
    "required_outputs",
    "acceptance_criteria",
    "non_scope",
    "blocks_features",
    "evidence_required",
    "operator_acceptance_required",
]

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

NON_SCOPE_PHRASES = {
    "keine Investmentlogik": ["keine Investmentlogik", "Investment logic"],
    "kein produktiver Portfolio Event Ledger": ["kein produktiver Portfolio Event Ledger", "no production event ledger", "production Event Ledger"],
    "keine Event-Ledger-Runtime": ["keine Event-Ledger-Runtime", "Event-Ledger-Runtime", "Event Ledger Runtime"],
    "kein Broker Import": ["kein Broker Import", "Broker Import"],
    "kein Broker Parser": ["kein Broker Parser", "Broker Parser"],
    "kein Provider Adapter": ["kein Provider Adapter", "Provider Adapter"],
    "keine API-Anbindung": ["keine API-Anbindung", "API"],
    "kein Scraping oder Web-Crawling": ["Scraping", "Web-Crawling", "web crawling"],
    "keine automatische Transaktionsklassifikation": ["automatische Transaktionsklassifikation", "automatic transaction classification"],
    "keine Corporate Actions Engine": ["Corporate Actions Engine"],
    "keine FX Engine": ["FX Engine"],
    "kein Replay": ["kein Replay", "Replay"],
    "kein Backtesting": ["Backtesting"],
    "keine Simulation": ["Simulation"],
    "keine Outcome Attribution": ["Outcome Attribution"],
    "kein Dashboard": ["kein Dashboard", "Dashboard"],
    "keine Valuation Automation": ["Valuation Automation"],
    "keine Buy/Sell Recommendation Änderungen": ["Buy/Sell Recommendation", "Buy/Sell"],
    "keine Steuerberechnung": ["Steuerberechnung", "tax"],
    "keine Legal-/Commercial-Freigabe": ["Legal-/Commercial-Freigabe", "legal", "commercial"],
    "keine Order Execution": ["Order Execution", "order execution"],
    "keine Runtime-LLM-Agentenlogik": ["Runtime-LLM-Agentenlogik", "runtime LLM"],
    "keine Runtime-Enforcement-Engine": ["Runtime-Enforcement-Engine", "runtime enforcement"],
    "keine Clean-Room-Automation": ["Clean-Room-Automation", "clean-room automation"],
    "keine vollautomatische Cross-Patch-Regression": ["vollautomatische Cross-Patch-Regression", "fully automated Cross-Patch", "vollautomatische"],
}

GAP_GATE_HINTS = {
    "clean-room": "CLEAN_ROOM_REPRODUCTION_REVIEW",
    "clean room": "CLEAN_ROOM_REPRODUCTION_REVIEW",
    "cross-patch": "CROSS_PATCH_REGRESSION_REVIEW",
    "regression": "CROSS_PATCH_REGRESSION_REVIEW",
    "runtime enforcement": "RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW",
    "runtime-enforcement": "RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW",
    "semantic": "SEMANTIC_DECISION_QUALITY_REVIEW",
    "investment logic": "SEMANTIC_DECISION_QUALITY_REVIEW",
    "broker import": "BROKER_IMPORT_STAGING_READINESS_REVIEW",
    "event ledger runtime": "PORTFOLIO_EVENT_LEDGER_RUNTIME_READINESS_REVIEW",
    "temporal": "AS_OF_TEMPORAL_INTEGRITY_REVIEW",
    "as_of": "AS_OF_TEMPORAL_INTEGRITY_REVIEW",
    "ci": "RELEASE_CI_ENVIRONMENT_PARITY_REVIEW",
    "environment parity": "RELEASE_CI_ENVIRONMENT_PARITY_REVIEW",
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


def _repo_path(repo_root: Path, relative_path: str) -> Path:
    return repo_root / relative_path


def _read_text(repo_root: Path, relative_path: str) -> str | None:
    path = _repo_path(repo_root, relative_path)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8-sig")


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


def _extract_gate_ids(text: str) -> set[str]:
    return set(re.findall(r"\b[A-Z0-9_]+_REVIEW\b", text))


def _explicitly_not_sequenced(sequence_text: str, gate_id: str) -> bool:
    pattern = re.compile(rf"{re.escape(gate_id)}.*(?:not sequenced|nicht sequenziert|not currently sequenced)", re.IGNORECASE)
    return bool(pattern.search(sequence_text))


def check_gate_registry(as_of_date: str, repo_root: Path) -> tuple[list[Finding], list[dict[str, Any]], set[str]]:
    findings: list[Finding] = []
    data, error = _load_json_file(repo_root, REGISTRY_PATH)
    if error:
        findings.append(_finding(as_of_date, "GATE_REGISTRY_LOAD", "P0", "MISSING", REGISTRY_PATH, error, "Gate registry is not loadable.", "Restore a valid machine-readable gate registry."))
        return findings, [], set()

    gates = data.get("gates", [])
    if not isinstance(gates, list):
        findings.append(_finding(as_of_date, "GATE_REGISTRY_SCHEMA", "P0", "FAIL", REGISTRY_PATH, "gates is not a list", "Gate registry does not expose a list of gates.", "Represent gates as a list of mappings."))
        return findings, [], set()

    gate_ids: set[str] = set()
    for index, gate in enumerate(gates):
        if not isinstance(gate, dict):
            findings.append(_finding(as_of_date, "GATE_REGISTRY_SCHEMA", "P0", "FAIL", REGISTRY_PATH, f"index={index}", "Gate entry is not a mapping.", "Use mapping entries for all gates."))
            continue
        gate_id = str(gate.get("gate_id", f"<missing-{index}>"))
        if gate_id in gate_ids:
            findings.append(_finding(as_of_date, "GATE_REGISTRY_DUPLICATE", "P0", "FAIL", REGISTRY_PATH, gate_id, "Duplicate gate_id in registry.", "Use unique gate_id values."))
        gate_ids.add(gate_id)
        for field in REQUIRED_GATE_FIELDS:
            if field not in gate:
                findings.append(_finding(as_of_date, "GATE_REGISTRY_REQUIRED_FIELDS", "P0", "FAIL", REGISTRY_PATH, f"{gate_id} missing {field}", "Gate entry misses a required field.", "Add the missing field to the gate entry."))
    if not any(item.check_id == "GATE_REGISTRY_REQUIRED_FIELDS" and item.status == "FAIL" for item in findings):
        findings.append(_finding(as_of_date, "GATE_REGISTRY_REQUIRED_FIELDS", "INFO", "PASS", REGISTRY_PATH, f"gate_count={len(gates)}", "All gate entries contain required fields.", "Keep registry schema covered by tests."))
    return findings, gates, gate_ids


def check_gate_sequence(as_of_date: str, repo_root: Path, gates: list[dict[str, Any]], gate_ids: set[str]) -> list[Finding]:
    findings: list[Finding] = []
    sequence_text = _read_text(repo_root, SEQUENCE_PATH)
    if sequence_text is None:
        return [_finding(as_of_date, "GATE_SEQUENCE_LOAD", "P0", "MISSING", SEQUENCE_PATH, "missing", "Gate sequence document is missing.", "Restore the gate sequence document.")]

    referenced_ids = _extract_gate_ids(sequence_text)
    for referenced_id in sorted(referenced_ids - gate_ids):
        findings.append(_finding(as_of_date, "GATE_SEQUENCE_UNKNOWN_GATE", "P0", "FAIL", SEQUENCE_PATH, referenced_id, "Gate sequence references a gate not present in the registry.", "Add the gate to the registry or remove the stale sequence reference."))

    for gate in gates:
        gate_id = str(gate.get("gate_id", ""))
        if gate.get("priority") == "P0" and gate_id and gate_id not in referenced_ids and not _explicitly_not_sequenced(sequence_text, gate_id):
            findings.append(_finding(as_of_date, "GATE_SEQUENCE_P0_COVERAGE", "P0", "WARN", SEQUENCE_PATH, gate_id, "P0 gate is not referenced in the gate sequence.", "Reference the P0 gate in the sequence or document why it is intentionally not sequenced."))

    release_gate = "RELEASE_CI_ENVIRONMENT_PARITY_REVIEW"
    if release_gate not in referenced_ids and not _explicitly_not_sequenced(sequence_text, release_gate):
        findings.append(_finding(as_of_date, "GATE_SEQUENCE_RELEASE_CI_PARITY", "P1", "WARN", SEQUENCE_PATH, release_gate, "Release CI Environment Parity gate is not sequenced or explicitly justified as not sequenced.", "Add the gate to release/public packaging sequencing or document why it is not sequenced."))
    else:
        findings.append(_finding(as_of_date, "GATE_SEQUENCE_RELEASE_CI_PARITY", "INFO", "PASS", SEQUENCE_PATH, release_gate, "Release CI Environment Parity gate is sequenced or explicitly justified.", "Keep CI parity visible in release sequencing."))

    if not any(item.check_id.startswith("GATE_SEQUENCE_") and item.status in {"FAIL", "WARN"} for item in findings):
        findings.append(_finding(as_of_date, "GATE_SEQUENCE_CROSS_REFERENCES", "INFO", "PASS", SEQUENCE_PATH, f"referenced_gate_count={len(referenced_ids)}", "Gate sequence references resolve to registry entries.", "Keep sequence and registry aligned."))
    return findings


def _gap_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        if line.startswith("| GAP-") and not line.startswith("| gap_id"):
            lines.append(line)
    return lines


def check_known_gaps(as_of_date: str, repo_root: Path, gate_ids: set[str]) -> list[Finding]:
    findings: list[Finding] = []
    text = _read_text(repo_root, KNOWN_GAPS_PATH)
    if text is None:
        return [_finding(as_of_date, "KNOWN_GAPS_LOAD", "P0", "MISSING", KNOWN_GAPS_PATH, "missing", "Known Gaps file is missing.", "Restore CURRENT_KNOWN_GAPS.md.")]

    for line in _gap_lines(text):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        gap_id, title, severity, current_status = cells[:4]
        line_lower = line.lower()
        if severity in {"P0", "P1"} and any(keyword in line_lower for keyword in GAP_GATE_HINTS):
            mapped = {gate for keyword, gate in GAP_GATE_HINTS.items() if keyword in line_lower and gate in gate_ids}
            explicit = {gate for gate in gate_ids if gate in line}
            if not (mapped or explicit):
                findings.append(_finding(as_of_date, "KNOWN_GAPS_UNMAPPED_GAP", severity, "WARN", KNOWN_GAPS_PATH, f"{gap_id} {title}", "Review-related P0/P1 gap is not mappable to a registered gate.", "Reference a matching gate_id or update gate hints."))
        if current_status in {"addressed_by_this_patch", "reduced_by_this_patch"} and not re.search(r"\b[0-9a-f]{7,40}\b", line, re.IGNORECASE):
            findings.append(_finding(as_of_date, "KNOWN_GAPS_AMBIGUOUS_PATCH_REFERENCE", "P1", "WARN", KNOWN_GAPS_PATH, f"{gap_id} status={current_status}", "Known gap uses a historically ambiguous patch-relative status without a concrete commit/head in the row.", "Replace patch-relative wording with a stable status or add commit evidence."))

    if not any(item.check_id.startswith("KNOWN_GAPS_") and item.status == "WARN" for item in findings):
        findings.append(_finding(as_of_date, "KNOWN_GAPS_MAPPING", "INFO", "PASS", KNOWN_GAPS_PATH, "P0/P1 review gaps checked", "Review-related known gaps map to gate coverage or avoid ambiguous patch-relative wording.", "Keep known gaps stable across future patches."))
    return findings


def check_feature_status(as_of_date: str, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    text = _read_text(repo_root, FEATURE_STATUS_PATH)
    if text is None:
        return [_finding(as_of_date, "FEATURE_STATUS_LOAD", "P0", "MISSING", FEATURE_STATUS_PATH, "missing", "Feature status file is missing.", "Restore CIOS_FEATURE_STATUS.yaml.")]

    lower = text.lower()
    if "external_review_coverage_standard" not in text:
        findings.append(_finding(as_of_date, "FEATURE_STATUS_COVERAGE_CAPABILITY", "P1", "WARN", FEATURE_STATUS_PATH, "capability missing", "External review coverage capability is not visible in feature status.", "Add the governance capability to feature status."))
    if "production_ready" in lower:
        findings.append(_finding(as_of_date, "FEATURE_STATUS_OVERCLAIM", "P0", "FAIL", FEATURE_STATUS_PATH, "production_ready", "Feature status contains a production_ready marker.", "Remove or qualify production-readiness language."))
    if "runtime_enforced" in lower:
        findings.append(_finding(as_of_date, "FEATURE_STATUS_RUNTIME_ENFORCEMENT_OVERCLAIM", "P0", "FAIL", FEATURE_STATUS_PATH, "runtime_enforced", "Feature status implies runtime enforcement.", "Keep governance gates distinct from runtime enforcement."))
    if "clean-room" in lower and "not fully automated" not in lower and "not implement" not in lower:
        findings.append(_finding(as_of_date, "FEATURE_STATUS_CLEAN_ROOM_AUTOMATION_OVERCLAIM", "P1", "WARN", FEATURE_STATUS_PATH, "clean-room without limitation", "Clean-room reproduction appears without a clear non-automation limitation.", "State that clean-room reproduction is not fully automated unless implemented."))

    producer_exists = _repo_path(repo_root, "src/external_review_cross_patch_regression.py").exists()
    tests_exist = _repo_path(repo_root, "tests/test_external_review_cross_patch_regression.py").exists()
    if "cross_patch_regression_review" in lower and not (producer_exists and tests_exist):
        findings.append(_finding(as_of_date, "FEATURE_STATUS_CROSS_PATCH_OPERATIONALIZED_EVIDENCE", "P0", "FAIL", FEATURE_STATUS_PATH, "cross_patch_regression_review without producer/tests", "Cross-Patch Regression appears operationalized without producer and tests.", "Only mark the gate operationalized when producer and tests exist."))
    else:
        findings.append(_finding(as_of_date, "FEATURE_STATUS_OVERCLAIM", "INFO", "PASS", FEATURE_STATUS_PATH, "no production_ready/runtime_enforced overclaim detected", "Feature status keeps review coverage governance conservative.", "Keep product/readiness claims out of governance status."))
    return findings


def _read_zip_validation(repo_root: Path) -> tuple[str | None, str]:
    zip_path = _repo_path(repo_root, EXTERNAL_ZIP_PATH)
    if not zip_path.exists():
        return None, "ZIP_NOT_AVAILABLE"
    try:
        with zipfile.ZipFile(zip_path) as archive:
            if "HANDOFF_VALIDATION.txt" not in archive.namelist():
                return None, "HANDOFF_VALIDATION_NOT_AVAILABLE"
            return archive.read("HANDOFF_VALIDATION.txt").decode("utf-8", errors="replace"), "OK"
    except zipfile.BadZipFile:
        return None, "ZIP_BAD"


def check_validation_reality(as_of_date: str, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    context = _read_text(repo_root, EXTERNAL_CONTEXT_PATH) or ""
    readme = _read_text(repo_root, EXTERNAL_README_PATH) or ""
    combined = f"{context}\n{readme}"

    if "python -m pytest -q" in combined and "No module named pytest" in combined and "No full test suite is claimed" in combined:
        findings.append(_finding(as_of_date, "VALIDATION_REALITY_PYTEST", "INFO", "PASS", EXTERNAL_CONTEXT_PATH, "pytest missing and no full suite claimed", "pytest failure is not represented as full-suite success.", "Install pytest only if the repo decides to make it required."))
    elif "python -m pytest -q" in combined and "No module named pytest" in combined:
        findings.append(_finding(as_of_date, "VALIDATION_REALITY_PYTEST", "P1", "WARN", EXTERNAL_CONTEXT_PATH, "pytest missing", "pytest is unavailable but full-suite limitation is not clearly stated.", "State that pytest was not available and no full-suite success is claimed."))

    if "python -m ruff check ." in combined and "No module named ruff" in combined:
        findings.append(_finding(as_of_date, "VALIDATION_REALITY_RUFF", "INFO", "PASS", EXTERNAL_CONTEXT_PATH, "ruff missing documented", "ruff failure is visible and not represented as lint success.", "Install ruff only if lint becomes a required gate."))

    validation_text, status = _read_zip_validation(repo_root)
    if status != "OK":
        findings.append(_finding(as_of_date, "VALIDATION_REALITY_ZIP_VALIDATION", "P1", "NOT_AVAILABLE", EXTERNAL_ZIP_PATH, status, "ZIP validation text is not available.", "Regenerate handoff ZIP when packet validation is required."))
    elif validation_text and "status: RECORDED" in validation_text:
        findings.append(_finding(as_of_date, "VALIDATION_REALITY_RECORDED_COMMANDS", "P2", "WARN", EXTERNAL_ZIP_PATH, "HANDOFF_VALIDATION.txt contains status: RECORDED", "Handoff validation records commands but does not embed real exit-code results.", "Do not treat RECORDED as PASSED; keep real command results in external context or future validation logs."))
    elif validation_text:
        findings.append(_finding(as_of_date, "VALIDATION_REALITY_RECORDED_COMMANDS", "INFO", "PASS", EXTERNAL_ZIP_PATH, "no RECORDED command markers", "Handoff validation does not use RECORDED command status.", "Keep command result semantics explicit."))
    return findings


def check_source_of_truth(as_of_date: str, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in [EXTERNAL_README_PATH, EXTERNAL_CONTEXT_PATH]:
        text = _read_text(repo_root, path)
        if text is None:
            findings.append(_finding(as_of_date, "SOURCE_OF_TRUTH_LOAD", "P0", "MISSING", path, "missing", "Handoff source-of-truth file is missing.", "Regenerate handoff metadata."))
            continue
        precedence_text = text
        marker = "Bei Konflikten gilt"
        if marker in text:
            precedence_text = text[text.find(marker) :]
        positions = [precedence_text.find(item) for item in SOURCE_OF_TRUTH_ORDER]
        if any(position < 0 for position in positions) or positions != sorted(positions):
            findings.append(_finding(as_of_date, "SOURCE_OF_TRUTH_ORDER", "P0", "FAIL", path, "source-of-truth order missing or out of order", "Handoff source-of-truth precedence is inconsistent.", "Restore the canonical precedence order."))
        else:
            findings.append(_finding(as_of_date, "SOURCE_OF_TRUTH_ORDER", "INFO", "PASS", path, "canonical precedence order found", "Handoff source-of-truth precedence is consistent.", "Keep precedence synchronized across packet files."))
    return findings


def check_non_scope(as_of_date: str, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    paths = [
        EXTERNAL_README_PATH,
        EXTERNAL_CONTEXT_PATH,
        COVERAGE_STANDARD_PATH,
        SEQUENCE_PATH,
        FEATURE_STATUS_PATH,
        KNOWN_GAPS_PATH,
    ]
    combined = "\n".join(_read_text(repo_root, path) or "" for path in paths)
    lower = combined.lower()
    missing = []
    for required, variants in NON_SCOPE_PHRASES.items():
        if not any(variant.lower() in lower for variant in variants):
            missing.append(required)
    if missing:
        findings.append(_finding(as_of_date, "NON_SCOPE_PRESERVATION", "P0", "WARN", "multiple", "; ".join(missing), "One or more required non-scope boundaries are not visible in reviewed governance/handoff texts.", "Restore explicit non-scope language."))
    else:
        findings.append(_finding(as_of_date, "NON_SCOPE_PRESERVATION", "INFO", "PASS", "multiple", f"checked={len(NON_SCOPE_PHRASES)}", "Required non-scope boundaries remain visible.", "Keep non-scope language explicit in future handoffs."))
    return findings


def check_required_files(as_of_date: str, repo_root: Path) -> list[Finding]:
    findings = []
    for path in [
        COVERAGE_STANDARD_PATH,
        REGISTRY_PATH,
        SEQUENCE_PATH,
        FEATURE_STATUS_PATH,
        KNOWN_GAPS_PATH,
        SYSTEM_MAP_PATH,
        MATURITY_MODEL_PATH,
        MODULE_CONTRACTS_PATH,
        CONTEXT_ROADMAP_PATH,
        README_PATH,
        EXTERNAL_README_PATH,
        EXTERNAL_CONTEXT_PATH,
        EXTERNAL_SHA_PATH,
    ]:
        if _repo_path(repo_root, path).exists():
            findings.append(_finding(as_of_date, "REQUIRED_FILE_PRESENT", "INFO", "PASS", path, "exists", "Required governance input is present.", "Keep file in future handoffs."))
        else:
            findings.append(_finding(as_of_date, "REQUIRED_FILE_PRESENT", "P1", "MISSING", path, "missing", "Required governance input is missing.", "Restore or document omission."))
    if not _repo_path(repo_root, EXTERNAL_ZIP_PATH).exists():
        findings.append(_finding(as_of_date, "REQUIRED_FILE_PRESENT", "P1", "NOT_AVAILABLE", EXTERNAL_ZIP_PATH, "ZIP_NOT_AVAILABLE", "Handoff ZIP is not available.", "Regenerate handoff ZIP for external review."))
    return findings


def run_cross_patch_regression(as_of_date: str, repo_root: str | Path = ".") -> list[Finding]:
    root = Path(repo_root).resolve()
    findings: list[Finding] = []
    findings.extend(check_required_files(as_of_date, root))
    registry_findings, gates, gate_ids = check_gate_registry(as_of_date, root)
    findings.extend(registry_findings)
    findings.extend(check_gate_sequence(as_of_date, root, gates, gate_ids))
    findings.extend(check_known_gaps(as_of_date, root, gate_ids))
    findings.extend(check_feature_status(as_of_date, root))
    findings.extend(check_validation_reality(as_of_date, root))
    findings.extend(check_source_of_truth(as_of_date, root))
    findings.extend(check_non_scope(as_of_date, root))
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


def _section_rows(findings: list[Finding], title: str, prefixes: tuple[str, ...]) -> list[str]:
    rows = [f"## {title}", ""]
    selected = [finding for finding in findings if finding.check_id.startswith(prefixes)]
    if not selected:
        rows.extend(["No findings for this section.", ""])
        return rows
    rows.extend(["| severity | status | check_id | file_path | finding | recommended_action |", "| --- | --- | --- | --- | --- | --- |"])
    for finding in selected:
        rows.append(
            f"| {finding.severity} | {finding.status} | `{finding.check_id}` | `{finding.file_path}` | {finding.finding} | {finding.recommended_action} |"
        )
    rows.append("")
    return rows


def write_markdown_report(findings: list[Finding], as_of_date: str, output_path: str | Path) -> Path:
    path = ensure_parent_dir(output_path)
    counts = _status_counts(findings)
    lines = [
        "# External Review Cross-Patch Regression Report",
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
        "This is a read-only governance regression check. It does not implement runtime enforcement, broker import, investment logic, release acceptance or product readiness.",
        "",
        "## Repo/Run Context",
        "",
        "- repo_relative_inputs_only: `true`",
        "- no_network_access_required: `true`",
        "- no_private_raw_inputs_required: `true`",
        "",
        "## Checked Files",
        "",
    ]
    checked = sorted({finding.file_path for finding in findings if finding.file_path != "multiple"})
    for file_path in checked:
        lines.append(f"- `{file_path}`")
    lines.append("")
    lines.extend(_section_rows(findings, "Findings by Severity", ("",)))
    lines.extend(_section_rows(findings, "Gate Registry / Sequence Consistency", ("GATE_REGISTRY", "GATE_SEQUENCE")))
    lines.extend(_section_rows(findings, "Known Gaps Mapping", ("KNOWN_GAPS",)))
    lines.extend(_section_rows(findings, "Feature Status Overclaim Check", ("FEATURE_STATUS",)))
    lines.extend(_section_rows(findings, "Validation Reality Check", ("VALIDATION_REALITY", "SOURCE_OF_TRUTH")))
    lines.extend(_section_rows(findings, "Non-Scope Preservation", ("NON_SCOPE",)))
    lines.extend(
        [
            "## Recommended Next Actions",
            "",
            "1. Resolve P0/P1 `FAIL`, `MISSING` or `WARN` rows before claiming a stronger governance baseline.",
            "2. Keep `RECORDED` handoff commands distinct from executed command pass/fail results.",
            "3. Operationalize clean-room reproduction only in a separate patch.",
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
    findings = run_cross_patch_regression(as_of_date=as_of_date, repo_root=repo_root)
    report_path = report_output or DEFAULT_REPORT_OUTPUT_TEMPLATE.format(as_of_date=as_of_date)
    csv_path = write_csv(findings, csv_output)
    markdown_path = write_markdown_report(findings, as_of_date, report_path)
    counts = _status_counts(findings)
    return {
        "status": "WARN" if counts.get("FAIL", 0) or counts.get("WARN", 0) or counts.get("MISSING", 0) or counts.get("NOT_AVAILABLE", 0) else "OK",
        "as_of_date": as_of_date,
        "findings": len(findings),
        "counts": counts,
        "csv_output": str(Path(csv_output).as_posix()),
        "report_output": str(Path(report_path).as_posix()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run read-only external review cross-patch regression checks.")
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
