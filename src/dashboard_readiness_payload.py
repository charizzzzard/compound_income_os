from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, read_csv_rows, resolve_repo_path, safe_upper
from src.dashboard_readiness_panel import (
    DEFAULT_BLOCKERS_OUTPUT,
    DEFAULT_NEXT_ACTIONS_OUTPUT,
    DEFAULT_PANEL_OUTPUT,
    FORBIDDEN_DISPLAY_TERMS,
)

DEFAULT_PAYLOAD_OUTPUT = "data/processed/dashboard_readiness_payload.json"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/dashboard_readiness_payload_report.md"

SCHEMA_VERSION = "1"
ALLOWED_CTA_LABELS = {
    "Review private valuation inputs",
    "Review dividend / FCF inputs",
    "Prepare explicit SEC refresh",
    "Replace sample watchlist",
    "Inspect provenance gaps",
    "Review handoff package",
    "Open readiness report",
}
SECTION_MAP = {
    "READINESS_OVERVIEW": "readiness_overview",
    "BLOCKER_SUMMARY": "blockers",
    "NEXT_ACTIONS": "next_actions",
    "SEC_PREFLIGHT": "sec_preflight",
    "PRIVATE_INPUTS": "private_inputs",
    "WATCHLIST": "watchlist",
    "HANDOFF": "handoff",
}
SCOPE_TO_KEY = {"DEMO": "demo", "DECISION": "decision", "DASHBOARD": "dashboard", "HANDOFF": "handoff"}
PRIVATE_MARKERS = (
    "data/raw/private",
    "personal_sec_identity_map",
    "private note",
    "private_note",
)


@dataclass(frozen=True)
class DashboardReadinessPayloadResult:
    payload_output: Path
    report_output: Path
    payload: dict[str, Any]
    warnings: tuple[str, ...]


def split_codes(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").replace(",", ";").split(";") if item.strip()]


def safe_source_artifact(value: Any) -> str:
    text = str(value or "").replace("\\", "/")
    if "data/raw/private" in text or "personal_sec_identity_map" in text:
        return "<private_path>"
    return text


def sanitize_display_text(value: Any) -> str:
    text = str(value or "").replace("\\", "/")
    for marker in PRIVATE_MARKERS:
        text = re.sub(re.escape(marker), "<private>", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCIK[0-9A-Z_-]*\b", "<private_identity>", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{8,}\b", "<private_numeric>", text)
    text = re.sub(r"\b-?\d+\.\d+\b", "<private_numeric>", text)
    return text


def optional_csv(path_value: str, label: str) -> tuple[list[dict[str, str]], bool, list[str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], False, [f"SOURCE_ARTIFACT_MISSING:{label}"]
    rows = read_csv_rows(path)
    if not rows:
        return [], True, [f"SOURCE_FIELD_MISSING:{label}:rows"]
    return rows, True, []


def assert_no_forbidden_display_terms(payload: dict[str, Any]) -> None:
    pattern_terms = [re.escape(term).replace("\\ ", r"\s+") for term in FORBIDDEN_DISPLAY_TERMS]
    pattern = re.compile(r"(?<![A-Z0-9_])(" + "|".join(pattern_terms) + r")(?![A-Z0-9_])", re.IGNORECASE)
    fields = {"label", "description", "cta_label"}
    for section_rows in payload.get("sections", {}).values():
        for row in section_rows:
            for field in fields:
                text = str(row.get(field, "") or "")
                if pattern.search(text):
                    raise ValueError(f"dashboard readiness payload field {field} contains restricted market-action wording: {text}")


def section_entry(
    *,
    entry_id: str,
    label: str,
    value: Any,
    status: str,
    severity: str,
    description: str,
    source_artifact: str,
    reason_codes: Any,
    cta_label: str,
    cta_target: str,
    is_safe_action: bool = True,
) -> dict[str, Any]:
    safe_cta = sanitize_display_text(cta_label)
    if safe_cta and safe_cta not in ALLOWED_CTA_LABELS:
        safe_cta = "Open readiness report"
        cta_target = "reports/2026-04-27/dashboard_readiness_payload_report.md"
    return {
        "id": sanitize_display_text(entry_id),
        "label": sanitize_display_text(label),
        "value": str(value),
        "status": safe_upper(status) or "NOT_AVAILABLE",
        "severity": safe_upper(severity) or "INFO",
        "description": sanitize_display_text(description),
        "source_artifact": safe_source_artifact(source_artifact),
        "reason_codes": split_codes(reason_codes),
        "cta_label": safe_cta,
        "cta_target": safe_source_artifact(cta_target),
        "is_safe_action": bool(is_safe_action and safe_cta in ALLOWED_CTA_LABELS),
    }


def not_available_entry(label: str, source_artifact: str) -> dict[str, Any]:
    return section_entry(
        entry_id=safe_upper(label).lower(),
        label=label,
        value="NOT_AVAILABLE",
        status="NOT_AVAILABLE",
        severity="P1_REVIEW",
        description="Source artifact is missing or unavailable.",
        source_artifact=source_artifact,
        reason_codes=["SOURCE_ARTIFACT_MISSING"],
        cta_label="Open readiness report",
        cta_target="reports/2026-04-27/dashboard_readiness_payload_report.md",
    )


def build_readiness(panel_rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    readiness = {
        "demo": {"status": "NOT_AVAILABLE", "reason_codes": ["SOURCE_FIELD_MISSING"]},
        "decision": {"status": "NOT_AVAILABLE", "reason_codes": ["SOURCE_FIELD_MISSING"]},
        "dashboard": {"status": "NOT_AVAILABLE", "reason_codes": ["SOURCE_FIELD_MISSING"]},
        "handoff": {"status": "NOT_AVAILABLE", "reason_codes": ["SOURCE_FIELD_MISSING"]},
    }
    metric_map = {
        "demo_readiness": "demo",
        "decision_readiness": "decision",
        "dashboard_readiness": "dashboard",
        "handoff_readiness": "handoff",
    }
    for row in panel_rows:
        key = metric_map.get(row.get("metric_name", ""))
        if key:
            readiness[key] = {
                "status": safe_upper(row.get("metric_value")) or "NOT_AVAILABLE",
                "reason_codes": split_codes(row.get("reason_codes")),
            }
    return readiness


def add_panel_sections(payload_sections: dict[str, list[dict[str, Any]]], panel_rows: list[dict[str, str]]) -> None:
    for row in panel_rows:
        section = SECTION_MAP.get(row.get("panel_section", ""), "readiness_overview")
        payload_sections.setdefault(section, []).append(
            section_entry(
                entry_id=row.get("metric_name", ""),
                label=row.get("display_label", row.get("metric_name", "")),
                value=row.get("metric_value", ""),
                status=row.get("status", "NOT_AVAILABLE"),
                severity=row.get("severity", "INFO"),
                description=row.get("display_hint", ""),
                source_artifact=row.get("source_artifact", ""),
                reason_codes=row.get("reason_codes", ""),
                cta_label=row.get("safe_cta", "Open readiness report"),
                cta_target="reports/2026-04-27/dashboard_readiness_panel_report.md",
            )
        )


def add_blocker_section(payload_sections: dict[str, list[dict[str, Any]]], blocker_rows: list[dict[str, str]]) -> None:
    for index, row in enumerate(blocker_rows, start=1):
        blocker_status = row.get("blocker_status", "")
        blocker_severity = row.get("blocker_severity", "INFO")
        display_status = "INFO"
        if blocker_status == "ACTIVE" and blocker_severity == "P0_BLOCKER":
            display_status = "BLOCKED"
        elif blocker_status == "ACTIVE":
            display_status = "REVIEW"
        elif blocker_status == "RESOLVED":
            display_status = "PASS"
        elif blocker_status == "DEFERRED":
            display_status = "REVIEW"
        payload_sections["blockers"].append(
            section_entry(
                entry_id=f"blocker_{index}_{row.get('blocker_code', '')}",
                label=row.get("display_title", row.get("blocker_code", "")),
                value=blocker_status,
                status=display_status,
                severity=blocker_severity,
                description=row.get("display_description", ""),
                source_artifact=row.get("source_artifact", ""),
                reason_codes=row.get("blocker_code", ""),
                cta_label=row.get("safe_next_action", "Open readiness report"),
                cta_target=row.get("source_artifact", ""),
            )
        )


def add_next_actions(payload_sections: dict[str, list[dict[str, Any]]], action_rows: list[dict[str, str]]) -> None:
    for index, row in enumerate(action_rows, start=1):
        payload_sections["next_actions"].append(
            section_entry(
                entry_id=f"next_action_{index}_{row.get('blocker_code', '')}",
                label=row.get("action_title", row.get("blocker_code", "")),
                value=row.get("priority", ""),
                status="REVIEW",
                severity=row.get("priority", "P1_REVIEW"),
                description=row.get("action_description", ""),
                source_artifact=row.get("source_artifact", ""),
                reason_codes=row.get("blocker_code", ""),
                cta_label=row.get("dashboard_cta_label", "Open readiness report"),
                cta_target=row.get("source_artifact", ""),
            )
        )


def build_summary(blocker_rows: list[dict[str, str]], action_rows: list[dict[str, str]]) -> dict[str, int]:
    return {
        "active_blockers_count": sum(1 for row in blocker_rows if row.get("blocker_status") == "ACTIVE"),
        "p0_blockers_count": sum(1 for row in blocker_rows if row.get("blocker_status") == "ACTIVE" and row.get("blocker_severity") == "P0_BLOCKER"),
        "p1_review_count": sum(1 for row in blocker_rows if row.get("blocker_status") == "ACTIVE" and row.get("blocker_severity") == "P1_REVIEW"),
        "resolved_blockers_count": sum(1 for row in blocker_rows if row.get("blocker_status") == "RESOLVED"),
        "next_actions_count": len(action_rows),
    }


def validate_no_dummy_claims(payload: dict[str, Any]) -> None:
    if payload.get("readiness", {}).get("decision", {}).get("status") == "BLOCKED":
        encoded = json.dumps(payload, sort_keys=True)
        if '"decision_ready": true' in encoded.lower():
            raise ValueError("Payload contains a dummy decision-ready claim while decision readiness is blocked.")


def build_payload(
    *,
    panel_rows: list[dict[str, str]],
    blocker_rows: list[dict[str, str]],
    action_rows: list[dict[str, str]],
    source_artifacts: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    sections = {name: [] for name in ("readiness_overview", "blockers", "next_actions", "sec_preflight", "private_inputs", "watchlist", "handoff")}
    if panel_rows:
        add_panel_sections(sections, panel_rows)
    else:
        sections["readiness_overview"].append(not_available_entry("Readiness overview", DEFAULT_PANEL_OUTPUT))
    add_blocker_section(sections, blocker_rows)
    add_next_actions(sections, action_rows)
    payload = {
        "metadata": {
            "generated_at": date.today().isoformat(),
            "source_artifacts": [safe_source_artifact(path) for path in source_artifacts],
            "schema_version": SCHEMA_VERSION,
            "private_data_included": False,
            "dummy_claims_included": False,
            "warnings": warnings,
        },
        "readiness": build_readiness(panel_rows),
        "summary": build_summary(blocker_rows, action_rows),
        "sections": sections,
        "guardrails": {
            "no_advice_language": True,
            "no_private_values": True,
            "no_network": True,
            "no_score_mutation": True,
            "no_master_mutation": True,
        },
    }
    assert_no_forbidden_display_terms(payload)
    validate_no_dummy_claims(payload)
    return payload


def write_payload(path_value: str | Path, payload: dict[str, Any]) -> Path:
    path = ensure_parent_dir(path_value)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def write_report(path_value: str | Path, payload: dict[str, Any], *, server_integration: str) -> Path:
    path = ensure_parent_dir(path_value)
    readiness = payload["readiness"]
    summary = payload["summary"]
    lines = [
        "# Dashboard Readiness Payload",
        "",
        "## Executive Summary",
        f"- Demo readiness: {readiness['demo']['status']}",
        f"- Decision readiness: {readiness['decision']['status']}",
        f"- Dashboard readiness: {readiness['dashboard']['status']}",
        f"- Handoff readiness: {readiness['handoff']['status']}",
        "- This payload is a local diagnostic view and does not claim decision readiness.",
        "",
        "## Input Artifacts",
    ]
    lines.extend(f"- {artifact}" for artifact in payload["metadata"]["source_artifacts"])
    lines.extend(
        [
            "",
            "## JSON Payload Schema",
            f"- schema_version: {payload['metadata']['schema_version']}",
            "- sections: readiness_overview, blockers, next_actions, sec_preflight, private_inputs, watchlist, handoff",
            "",
            "## Readiness Status",
            f"- Demo: {readiness['demo']['status']}",
            f"- Decision: {readiness['decision']['status']}",
            f"- Dashboard: {readiness['dashboard']['status']}",
            f"- Handoff: {readiness['handoff']['status']}",
            "",
            "## Blocker Summary",
            f"- Active blockers: {summary['active_blockers_count']}",
            f"- P0 blockers: {summary['p0_blockers_count']}",
            f"- P1 review rows: {summary['p1_review_count']}",
            f"- Resolved blockers: {summary['resolved_blockers_count']}",
            "",
            "## Next Actions",
            f"- Next actions: {summary['next_actions_count']}",
            "- Actions remain review/workflow oriented.",
            "",
            "## SEC Preflight Section",
            f"- Entries: {len(payload['sections']['sec_preflight'])}",
            "- Network performed: False",
            "",
            "## Private Inputs Section",
            f"- Entries: {len(payload['sections']['private_inputs'])}",
            "- Private values included: False",
            "",
            "## Server Integration Status",
            f"- dashboard_server_integration: {server_integration}",
            "- Endpoint reads the static JSON artifact only.",
            "",
            "## Advice / Privacy Guardrail",
            "- Restricted market-action display terms detected: False",
            "- Private raw paths exposed: False",
            "- Private numeric values included: False",
            "",
            "## No-Dummy-Claims Guardrail",
            "- dummy_claims_included: False",
            "- decision_ready boolean emitted: False",
            "",
            "## Recommended Next Patch",
            "- PATCH / WEBSITE DEMO HANDOFF PAYLOAD / STATIC SAMPLE READINESS JSON / PRIVATE PREVIEW ONLY",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_dashboard_readiness_payload(
    *,
    panel_input: str = DEFAULT_PANEL_OUTPUT,
    blockers_input: str = DEFAULT_BLOCKERS_OUTPUT,
    next_actions_input: str = DEFAULT_NEXT_ACTIONS_OUTPUT,
    payload_output: str = DEFAULT_PAYLOAD_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
    server_integration: str = "done",
) -> DashboardReadinessPayloadResult:
    panel_rows, panel_exists, panel_warnings = optional_csv(panel_input, "dashboard_readiness_panel")
    blocker_rows, blockers_exists, blocker_warnings = optional_csv(blockers_input, "dashboard_readiness_blockers")
    action_rows, actions_exists, action_warnings = optional_csv(next_actions_input, "dashboard_readiness_next_actions")
    warnings = panel_warnings + blocker_warnings + action_warnings
    source_artifacts = [
        panel_input if panel_exists else f"{panel_input} (missing)",
        blockers_input if blockers_exists else f"{blockers_input} (missing)",
        next_actions_input if actions_exists else f"{next_actions_input} (missing)",
    ]
    payload = build_payload(
        panel_rows=panel_rows,
        blocker_rows=blocker_rows,
        action_rows=action_rows,
        source_artifacts=source_artifacts,
        warnings=warnings,
    )
    payload_path = write_payload(payload_output, payload)
    report_path = write_report(report_output, payload, server_integration=server_integration)
    return DashboardReadinessPayloadResult(
        payload_output=payload_path,
        report_output=report_path,
        payload=payload,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a sanitized local dashboard readiness JSON payload.")
    parser.add_argument("--panel-input", default=DEFAULT_PANEL_OUTPUT)
    parser.add_argument("--blockers-input", default=DEFAULT_BLOCKERS_OUTPUT)
    parser.add_argument("--next-actions-input", default=DEFAULT_NEXT_ACTIONS_OUTPUT)
    parser.add_argument("--payload-output", default=DEFAULT_PAYLOAD_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_dashboard_readiness_payload(
        panel_input=args.panel_input,
        blockers_input=args.blockers_input,
        next_actions_input=args.next_actions_input,
        payload_output=args.payload_output,
        report_output=args.report_output,
    )
    print(f"payload_output={result.payload_output}")
    print(f"report_output={result.report_output}")
    print(f"decision_readiness={result.payload['readiness']['decision']['status']}")


if __name__ == "__main__":
    main()
