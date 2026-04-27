from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_READINESS_SUMMARY_INPUT = "data/processed/personal_readiness_status_summary.csv"
DEFAULT_READINESS_BLOCKERS_INPUT = "data/processed/personal_readiness_blockers.csv"
DEFAULT_READINESS_NEXT_ACTIONS_INPUT = "data/processed/personal_readiness_next_actions.csv"
DEFAULT_SEC_PREFLIGHT_SUMMARY_INPUT = "data/processed/personal_sec_refresh_preflight_summary.csv"
DEFAULT_SEC_PLAN_SUMMARY_INPUT = "data/processed/personal_sec_core_kpi_refresh_plan_summary.csv"
DEFAULT_PRIVATE_INPUT_REVIEW_SUMMARY_INPUT = "data/processed/personal_private_input_review_summary.csv"
DEFAULT_PRIVATE_APPLY_CANDIDATES_SUMMARY_INPUT = "data/processed/personal_private_input_apply_candidates_summary.csv"
DEFAULT_WATCHLIST_GATE_SUMMARY_INPUT = "data/processed/personal_watchlist_input_gate_summary.csv"

DEFAULT_PANEL_OUTPUT = "data/processed/dashboard_readiness_panel.csv"
DEFAULT_BLOCKERS_OUTPUT = "data/processed/dashboard_readiness_blockers.csv"
DEFAULT_NEXT_ACTIONS_OUTPUT = "data/processed/dashboard_readiness_next_actions.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/dashboard_readiness_panel_report.md"

PANEL_FIELDS = [
    "panel_section",
    "metric_name",
    "metric_value",
    "status",
    "severity",
    "source_artifact",
    "reason_codes",
    "display_label",
    "display_hint",
    "safe_cta",
]

BLOCKER_FIELDS = [
    "blocker_code",
    "blocker_status",
    "blocker_severity",
    "readiness_scope",
    "display_title",
    "display_description",
    "source_artifact",
    "safe_next_action",
    "dashboard_priority",
    "show_on_dashboard",
]

NEXT_ACTION_FIELDS = [
    "priority",
    "action_title",
    "action_description",
    "blocker_code",
    "requires_private_input",
    "requires_external_api",
    "requires_value_change",
    "safe_next_patch",
    "source_artifact",
    "dashboard_cta_label",
]

FORBIDDEN_DISPLAY_TERMS = (
    "BUY",
    "SELL",
    "STRONG_BUY",
    "STRONG_SELL",
    "TRADE",
    "EXECUTE",
    "ORDER",
    "RECOMMENDATION",
    "DEPLOY CAPITAL",
    "ADD NOW",
)

BLOCKER_TITLES = {
    "MISSING_VALUATION_REQUIRED": "Valuation inputs missing",
    "MISSING_DIVIDEND_FCF_REQUIRED": "Dividend / FCF inputs missing",
    "PROVENANCE_INCOMPLETE": "Source provenance incomplete",
    "REVIEW_CORE_DATA": "Core KPI review open",
    "WATCHLIST_SAMPLE_INPUT": "Sample watchlist active",
    "WATCHLIST_REVIEW_OR_MISSING_DATA": "Watchlist review or missing data",
    "MISSING_METADATA": "Metadata review open",
    "STALE_ARTIFACT": "Stale artifact review open",
    "MONTHLY_SCHEMA_DRIFT": "Monthly schema drift resolved",
    "ARTIFACT_DRIFT": "Artifact drift resolved",
    "PUBLIC_LAUNCH_BLOCKERS": "Public launch blockers deferred",
    "NO_REAL_CTA_TARGETS": "Public call-to-action targets deferred",
    "NO_IMPRINT_PRIVACY": "Public legal links deferred",
    "SAMPLE_OR_SYNTHETIC_DEMO_DATA": "Sample or demo data visible",
}

CTA_BY_BLOCKER = {
    "MISSING_VALUATION_REQUIRED": "Review private valuation inputs",
    "MISSING_DIVIDEND_FCF_REQUIRED": "Review dividend / FCF inputs",
    "REVIEW_CORE_DATA": "Prepare explicit SEC refresh",
    "PROVENANCE_INCOMPLETE": "Inspect provenance gaps",
    "WATCHLIST_SAMPLE_INPUT": "Replace sample watchlist",
    "WATCHLIST_REVIEW_OR_MISSING_DATA": "Review watchlist data status",
    "MISSING_METADATA": "Inspect metadata gaps",
    "STALE_ARTIFACT": "Review stale artifacts",
}


@dataclass(frozen=True)
class DashboardReadinessPanelResult:
    panel_output: Path
    blockers_output: Path
    next_actions_output: Path
    report_output: Path
    panel_rows: list[dict[str, str]]
    blocker_rows: list[dict[str, str]]
    next_action_rows: list[dict[str, str]]
    warnings: tuple[str, ...]


def safe_display_path(path_value: str) -> str:
    normalized = str(path_value or "").replace("\\", "/")
    if "data/raw/private" in normalized or normalized == "<private_path>":
        return "<private_path>"
    return normalized


def optional_csv_rows(path_value: str, label: str) -> tuple[list[dict[str, str]], bool, list[str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], False, [f"missing_input={label}:{safe_display_path(path_value)}"]
    return read_csv_rows(path), True, []


def metric_summary(rows: list[dict[str, str]]) -> dict[str, str]:
    return {row.get("metric", ""): row.get("value", "") for row in rows if row.get("metric")}


def first_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return rows[0] if rows else {}


def split_list(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").replace(",", ";").split(";") if item.strip()]


def is_true(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def status_from_readiness(value: str) -> str:
    normalized = safe_upper(value)
    return normalized if normalized in {"PASS", "REVIEW", "BLOCKED", "NOT_AVAILABLE"} else "NOT_AVAILABLE"


def severity_for_status(status: str) -> str:
    if status == "BLOCKED":
        return "P0_BLOCKER"
    if status == "REVIEW":
        return "P1_REVIEW"
    if status == "PASS":
        return "INFO"
    return "P1_REVIEW"


def dashboard_priority(severity: str, status: str, code: str) -> str:
    if status == "ACTIVE" and severity == "P0_BLOCKER":
        return "10"
    if status == "ACTIVE" and severity == "P1_REVIEW":
        return "20"
    if status == "ACTIVE":
        return "30"
    if status == "RESOLVED":
        return "80"
    if status == "DEFERRED":
        return "90"
    return "70"


def sanitize_text(value: Any) -> str:
    text = str(value or "").replace("data/raw/private", "<private_path>")
    text = text.replace("\\", "/")
    return text


def assert_no_forbidden_display_terms(rows: list[dict[str, str]], fields: tuple[str, ...]) -> None:
    for row in rows:
        for field in fields:
            text = str(row.get(field, "") or "").upper()
            for term in FORBIDDEN_DISPLAY_TERMS:
                if term in text:
                    raise ValueError(f"dashboard readiness display field {field} contains forbidden term {term}: {row.get(field, '')}")


def make_panel_row(
    *,
    section: str,
    metric_name: str,
    metric_value: Any,
    status: str,
    severity: str,
    source_artifact: str,
    reason_codes: str = "",
    display_label: str,
    display_hint: str,
    safe_cta: str = "",
) -> dict[str, str]:
    return {
        "panel_section": section,
        "metric_name": metric_name,
        "metric_value": str(metric_value),
        "status": status,
        "severity": severity,
        "source_artifact": safe_display_path(source_artifact),
        "reason_codes": sanitize_text(reason_codes),
        "display_label": sanitize_text(display_label),
        "display_hint": sanitize_text(display_hint),
        "safe_cta": sanitize_text(safe_cta),
    }


def build_panel_rows(
    *,
    readiness_rows: list[dict[str, str]],
    blocker_rows: list[dict[str, str]],
    next_action_rows: list[dict[str, str]],
    sec_preflight: dict[str, str],
    sec_plan: dict[str, str],
    private_review_rows: list[dict[str, str]],
    private_candidates_rows: list[dict[str, str]],
    watchlist_summary: dict[str, str],
    sources: dict[str, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    readiness_by_scope = {safe_upper(row.get("readiness_scope")): row for row in readiness_rows}
    for scope in ("DEMO", "DECISION", "DASHBOARD", "HANDOFF"):
        current = readiness_by_scope.get(scope, {})
        status = status_from_readiness(current.get("readiness_status", "NOT_AVAILABLE"))
        rows.append(
            make_panel_row(
                section="READINESS_OVERVIEW",
                metric_name=f"{scope.lower()}_readiness",
                metric_value=status,
                status=status,
                severity=severity_for_status(status),
                source_artifact=sources["readiness_summary"],
                reason_codes=current.get("primary_reason_codes", ""),
                display_label=f"{scope.title()} readiness",
                display_hint=f"{scope.title()} readiness is {status}; this panel does not claim decision readiness.",
                safe_cta="Review active blockers" if status != "PASS" else "Inspect readiness evidence",
            )
        )

    active = [row for row in blocker_rows if safe_upper(row.get("blocker_status")) == "ACTIVE"]
    resolved = [row for row in blocker_rows if safe_upper(row.get("blocker_status")) == "RESOLVED"]
    severity_counts = Counter(row.get("blocker_severity", "") for row in active)
    for severity in ("P0_BLOCKER", "P1_REVIEW", "P2_BACKLOG"):
        count = severity_counts.get(severity, 0)
        rows.append(
            make_panel_row(
                section="BLOCKER_SUMMARY",
                metric_name=f"active_{severity.lower()}_count",
                metric_value=count,
                status="BLOCKED" if severity == "P0_BLOCKER" and count else "REVIEW" if count else "INFO",
                severity=severity if count else "INFO",
                source_artifact=sources["readiness_blockers"],
                reason_codes=";".join(sorted({reason for row in active for reason in split_list(row.get("reason_codes", ""))})),
                display_label=f"Active {severity} count",
                display_hint=f"{count} active blocker rows with severity {severity}.",
                safe_cta="Review active blockers",
            )
        )
    rows.append(
        make_panel_row(
            section="BLOCKER_SUMMARY",
            metric_name="resolved_blocker_count",
            metric_value=len(resolved),
            status="INFO",
            severity="INFO",
            source_artifact=sources["readiness_blockers"],
            reason_codes=";".join(sorted({row.get("blocker_code", "") for row in resolved})),
            display_label="Resolved blocker count",
            display_hint="Resolved blockers are shown separately from active blockers.",
            safe_cta="Inspect resolved blockers",
        )
    )

    sec_status = "REVIEW" if sec_preflight else "NOT_AVAILABLE"
    if sec_preflight and is_true(sec_preflight.get("sec_user_agent_present")) and int(sec_preflight.get("ready_for_explicit_network_run_count", "0") or 0) > 0:
        sec_status = "PASS"
    rows.extend(
        [
            make_panel_row(
                section="SEC_PREFLIGHT",
                metric_name="sec_preflight_status",
                metric_value="USER_AGENT_MISSING" if sec_preflight and not is_true(sec_preflight.get("sec_user_agent_present")) else sec_preflight.get("future_refresh_command_status", "NOT_AVAILABLE"),
                status=sec_status,
                severity="P1_REVIEW" if sec_status == "REVIEW" else "INFO",
                source_artifact=sources["sec_preflight"],
                reason_codes=sec_preflight.get("reason_codes", ""),
                display_label="SEC preflight",
                display_hint="SEC refresh remains gated; no network or fetch was performed.",
                safe_cta="Prepare explicit SEC refresh",
            ),
            make_panel_row(
                section="SEC_PREFLIGHT",
                metric_name="sec_core_plan_ready_rows",
                metric_value=sec_plan.get("ready_for_explicit_sec_refresh_count", "0"),
                status="INFO",
                severity="INFO",
                source_artifact=sources["sec_plan"],
                reason_codes=sec_plan.get("reason_codes", ""),
                display_label="SEC core KPI plan-ready rows",
                display_hint="Rows are structurally ready for a future explicit SEC refresh after gates are satisfied.",
                safe_cta="Review SEC preflight",
            ),
        ]
    )

    for row in private_review_rows:
        domain = row.get("review_domain", "UNKNOWN")
        rows.append(
            make_panel_row(
                section="PRIVATE_INPUTS",
                metric_name=f"{domain.lower()}_private_input_status",
                metric_value=row.get("input_file_status", "NOT_AVAILABLE"),
                status="BLOCKED" if safe_upper(row.get("input_file_status")) == "MISSING" else "REVIEW",
                severity="P0_BLOCKER" if safe_upper(row.get("input_file_status")) == "MISSING" else "P1_REVIEW",
                source_artifact=sources["private_review"],
                reason_codes=row.get("reason_codes", ""),
                display_label=f"{domain.replace('_', ' ').title()} private input",
                display_hint=f"Approved rows: {row.get('approved_rows_count', '0')}; missing rows: {row.get('missing_rows_count', '0')}.",
                safe_cta="Review private valuation inputs" if domain == "VALUATION" else "Review dividend / FCF inputs",
            )
        )
    for row in private_candidates_rows:
        domain = row.get("review_domain", "UNKNOWN")
        rows.append(
            make_panel_row(
                section="PRIVATE_INPUTS",
                metric_name=f"{domain.lower()}_candidate_rows",
                metric_value=row.get("candidate_rows_count", "0"),
                status="REVIEW" if row.get("candidate_rows_count", "0") == "0" else "INFO",
                severity="P1_REVIEW" if row.get("candidate_rows_count", "0") == "0" else "INFO",
                source_artifact=sources["private_candidates"],
                reason_codes=row.get("reason_codes", ""),
                display_label=f"{domain.replace('_', ' ').title()} apply candidates",
                display_hint="Public outputs are sanitized and candidate values remain private.",
                safe_cta="Review private input workflow",
            )
        )

    rows.append(
        make_panel_row(
            section="WATCHLIST",
            metric_name="watchlist_readiness_status",
            metric_value=watchlist_summary.get("watchlist_readiness_status", "NOT_AVAILABLE"),
            status="BLOCKED" if watchlist_summary.get("watchlist_readiness_status") == "BLOCKED" else "REVIEW",
            severity="P0_BLOCKER",
            source_artifact=sources["watchlist_gate"],
            reason_codes=watchlist_summary.get("watchlist_reason_codes", ""),
            display_label="Watchlist readiness",
            display_hint=f"Input status: {watchlist_summary.get('watchlist_input_status', 'NOT_AVAILABLE')}; data status: {watchlist_summary.get('watchlist_data_status', 'NOT_AVAILABLE')}.",
            safe_cta="Replace sample watchlist",
        )
    )

    handoff = readiness_by_scope.get("HANDOFF", {})
    handoff_status = status_from_readiness(handoff.get("readiness_status", "NOT_AVAILABLE"))
    rows.append(
        make_panel_row(
            section="HANDOFF",
            metric_name="handoff_readiness",
            metric_value=handoff_status,
            status=handoff_status,
            severity=severity_for_status(handoff_status),
            source_artifact=sources["readiness_summary"],
            reason_codes=handoff.get("primary_reason_codes", ""),
            display_label="Handoff readiness",
            display_hint="Handoff remains separate from decision readiness and is based on packaged evidence status.",
            safe_cta="Review handoff package",
        )
    )
    assert_no_forbidden_display_terms(rows, ("display_label", "display_hint", "safe_cta"))
    return rows


def build_blocker_dashboard_rows(blockers: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in blockers:
        code = row.get("blocker_code", "")
        status = safe_upper(row.get("blocker_status"))
        severity = row.get("blocker_severity", "")
        show = status == "ACTIVE" or status == "RESOLVED" or code in {"PUBLIC_LAUNCH_BLOCKERS", "NO_REAL_CTA_TARGETS", "NO_IMPRINT_PRIVACY"}
        rows.append(
            {
                "blocker_code": code,
                "blocker_status": row.get("blocker_status", ""),
                "blocker_severity": severity,
                "readiness_scope": row.get("readiness_scope", ""),
                "display_title": BLOCKER_TITLES.get(code, code.replace("_", " ").title()),
                "display_description": f"{status.title()} blocker for {row.get('readiness_scope', 'UNKNOWN')} scope.",
                "source_artifact": safe_display_path(row.get("source_artifact", "")),
                "safe_next_action": CTA_BY_BLOCKER.get(code, sanitize_text(row.get("recommended_next_action", "Review readiness evidence"))),
                "dashboard_priority": dashboard_priority(severity, status, code),
                "show_on_dashboard": "yes" if show else "no",
            }
        )
    rows.sort(key=lambda item: (int(item["dashboard_priority"]), item["blocker_code"], item["readiness_scope"]))
    assert_no_forbidden_display_terms(rows, ("display_title", "display_description", "safe_next_action"))
    return rows


def build_next_action_rows(actions: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in actions:
        code = row.get("blocker_code", "")
        cta = CTA_BY_BLOCKER.get(code, "Review readiness evidence")
        rows.append(
            {
                "priority": row.get("priority", ""),
                "action_title": cta,
                "action_description": sanitize_text(row.get("recommended_next_action", "")),
                "blocker_code": code,
                "requires_private_input": row.get("requires_private_input", ""),
                "requires_external_api": row.get("requires_external_api", ""),
                "requires_value_change": row.get("requires_value_change", ""),
                "safe_next_patch": sanitize_text(row.get("safe_next_patch", "")),
                "source_artifact": safe_display_path(row.get("output_artifact", "")),
                "dashboard_cta_label": cta,
            }
        )
    assert_no_forbidden_display_terms(rows, ("action_title", "action_description", "dashboard_cta_label"))
    return rows


def render_report(panel_rows: list[dict[str, str]], blocker_rows: list[dict[str, str]], action_rows: list[dict[str, str]], warnings: tuple[str, ...]) -> str:
    panel_index = {row["metric_name"]: row for row in panel_rows}
    active_blockers = [row for row in blocker_rows if row["blocker_status"] == "ACTIVE" and row["show_on_dashboard"] == "yes"]
    resolved_blockers = [row for row in blocker_rows if row["blocker_status"] == "RESOLVED"]
    severity_counts = Counter(row["blocker_severity"] for row in active_blockers)
    lines = [
        "# Dashboard Readiness Panel",
        "",
        "## 1. Executive Summary",
        f"- Demo readiness: `{panel_index.get('demo_readiness', {}).get('metric_value', 'NOT_AVAILABLE')}`",
        f"- Decision readiness: `{panel_index.get('decision_readiness', {}).get('metric_value', 'NOT_AVAILABLE')}`",
        f"- Dashboard readiness: `{panel_index.get('dashboard_readiness', {}).get('metric_value', 'NOT_AVAILABLE')}`",
        f"- Handoff readiness: `{panel_index.get('handoff_readiness', {}).get('metric_value', 'NOT_AVAILABLE')}`",
        f"- Active P0 blockers: `{severity_counts.get('P0_BLOCKER', 0)}`",
        f"- Active P1 reviews: `{severity_counts.get('P1_REVIEW', 0)}`",
        "",
        "## 2. Input Summary Artifacts",
        "- `personal_readiness_status_summary.csv`",
        "- `personal_readiness_blockers.csv`",
        "- `personal_readiness_next_actions.csv`",
        "- `personal_sec_refresh_preflight_summary.csv`",
        "- `personal_private_input_review_summary.csv`",
        "- `personal_private_input_apply_candidates_summary.csv`",
        "",
        "## 3. Readiness Overview",
    ]
    for metric in ("demo_readiness", "decision_readiness", "dashboard_readiness", "handoff_readiness"):
        row = panel_index.get(metric, {})
        lines.append(f"- {row.get('display_label', metric)}: `{row.get('metric_value', 'NOT_AVAILABLE')}`")
    lines.extend(["", "## 4. Active Blockers"])
    for row in active_blockers:
        lines.append(f"- `{row['blocker_code']}` ({row['blocker_severity']}): {row['display_title']}")
    lines.extend(["", "## 5. Resolved / Deferred Blockers"])
    if resolved_blockers:
        for row in resolved_blockers:
            lines.append(f"- `{row['blocker_code']}`: {row['display_title']}")
    else:
        lines.append("- None reported.")
    lines.extend(["", "## 6. Next Safe Actions"])
    for row in action_rows:
        lines.append(f"- `{row['blocker_code']}`: {row['dashboard_cta_label']}")
    lines.extend(
        [
            "",
            "## 7. SEC Preflight",
            f"- Status: `{panel_index.get('sec_preflight_status', {}).get('metric_value', 'NOT_AVAILABLE')}`",
            "- No network or fetch claim is made by this dashboard panel.",
            "",
            "## 8. Private Inputs",
            f"- Valuation private input: `{panel_index.get('valuation_private_input_status', {}).get('metric_value', 'NOT_AVAILABLE')}`",
            f"- Dividend / FCF private input: `{panel_index.get('dividend_fcf_private_input_status', {}).get('metric_value', 'NOT_AVAILABLE')}`",
            f"- Valuation candidates: `{panel_index.get('valuation_candidate_rows', {}).get('metric_value', '0')}`",
            f"- Dividend / FCF candidates: `{panel_index.get('dividend_fcf_candidate_rows', {}).get('metric_value', '0')}`",
            "",
            "## 9. No-Value-Change Guardrail",
            "- This panel reads processed readiness artifacts only.",
            "- It does not change scores, master data, evidence files, watchlist rows, or SEC artifacts.",
            "",
            "## 10. Display Guardrail",
            "- Display copy avoids transaction/execution language.",
            "- Private paths are masked and private values are not rendered.",
            "",
            "## 11. Next Patch",
            "`PATCH / DASHBOARD SERVER READINESS VIEW / STATIC LOCAL JSON ENDPOINT / NO DUMMY CLAIMS`",
        ]
    )
    if warnings:
        lines.extend(["", "## Warnings"])
        for warning in warnings:
            lines.append(f"- `{warning}`")
    return "\n".join(lines) + "\n"


def run_dashboard_readiness_panel(
    *,
    readiness_summary_input: str = DEFAULT_READINESS_SUMMARY_INPUT,
    readiness_blockers_input: str = DEFAULT_READINESS_BLOCKERS_INPUT,
    readiness_next_actions_input: str = DEFAULT_READINESS_NEXT_ACTIONS_INPUT,
    sec_preflight_summary_input: str = DEFAULT_SEC_PREFLIGHT_SUMMARY_INPUT,
    sec_plan_summary_input: str = DEFAULT_SEC_PLAN_SUMMARY_INPUT,
    private_input_review_summary_input: str = DEFAULT_PRIVATE_INPUT_REVIEW_SUMMARY_INPUT,
    private_apply_candidates_summary_input: str = DEFAULT_PRIVATE_APPLY_CANDIDATES_SUMMARY_INPUT,
    watchlist_gate_summary_input: str = DEFAULT_WATCHLIST_GATE_SUMMARY_INPUT,
    panel_output: str = DEFAULT_PANEL_OUTPUT,
    blockers_output: str = DEFAULT_BLOCKERS_OUTPUT,
    next_actions_output: str = DEFAULT_NEXT_ACTIONS_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> DashboardReadinessPanelResult:
    warnings: list[str] = []
    readiness_rows, _, readiness_warnings = optional_csv_rows(readiness_summary_input, "readiness_summary")
    blockers, _, blocker_warnings = optional_csv_rows(readiness_blockers_input, "readiness_blockers")
    actions, _, action_warnings = optional_csv_rows(readiness_next_actions_input, "readiness_next_actions")
    sec_preflight_rows, _, sec_preflight_warnings = optional_csv_rows(sec_preflight_summary_input, "sec_preflight_summary")
    sec_plan_rows, _, sec_plan_warnings = optional_csv_rows(sec_plan_summary_input, "sec_plan_summary")
    private_review_rows, _, private_review_warnings = optional_csv_rows(private_input_review_summary_input, "private_input_review_summary")
    private_candidate_rows, _, private_candidate_warnings = optional_csv_rows(private_apply_candidates_summary_input, "private_apply_candidates_summary")
    watchlist_rows, _, watchlist_warnings = optional_csv_rows(watchlist_gate_summary_input, "watchlist_gate_summary")
    for items in (
        readiness_warnings,
        blocker_warnings,
        action_warnings,
        sec_preflight_warnings,
        sec_plan_warnings,
        private_review_warnings,
        private_candidate_warnings,
        watchlist_warnings,
    ):
        warnings.extend(items)
    sources = {
        "readiness_summary": readiness_summary_input,
        "readiness_blockers": readiness_blockers_input,
        "readiness_next_actions": readiness_next_actions_input,
        "sec_preflight": sec_preflight_summary_input,
        "sec_plan": sec_plan_summary_input,
        "private_review": private_input_review_summary_input,
        "private_candidates": private_apply_candidates_summary_input,
        "watchlist_gate": watchlist_gate_summary_input,
    }
    blocker_dashboard_rows = build_blocker_dashboard_rows(blockers)
    next_dashboard_rows = build_next_action_rows(actions)
    panel_rows = build_panel_rows(
        readiness_rows=readiness_rows,
        blocker_rows=blockers,
        next_action_rows=next_dashboard_rows,
        sec_preflight=first_row(sec_preflight_rows),
        sec_plan=first_row(sec_plan_rows),
        private_review_rows=private_review_rows,
        private_candidates_rows=private_candidate_rows,
        watchlist_summary=metric_summary(watchlist_rows),
        sources=sources,
    )
    panel_path = write_csv_rows(panel_output, PANEL_FIELDS, panel_rows)
    blockers_path = write_csv_rows(blockers_output, BLOCKER_FIELDS, blocker_dashboard_rows)
    next_actions_path = write_csv_rows(next_actions_output, NEXT_ACTION_FIELDS, next_dashboard_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_text = render_report(panel_rows, blocker_dashboard_rows, next_dashboard_rows, tuple(warnings))
    for term in FORBIDDEN_DISPLAY_TERMS:
        if term in report_text.upper():
            raise ValueError(f"dashboard readiness report contains forbidden term {term}")
    report_path.write_text(report_text, encoding="utf-8")
    return DashboardReadinessPanelResult(
        panel_output=panel_path,
        blockers_output=blockers_path,
        next_actions_output=next_actions_path,
        report_output=report_path,
        panel_rows=panel_rows,
        blocker_rows=blocker_dashboard_rows,
        next_action_rows=next_dashboard_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build dashboard readiness panel from processed readiness artifacts.")
    parser.add_argument("--panel-output", default=DEFAULT_PANEL_OUTPUT)
    parser.add_argument("--blockers-output", default=DEFAULT_BLOCKERS_OUTPUT)
    parser.add_argument("--next-actions-output", default=DEFAULT_NEXT_ACTIONS_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_dashboard_readiness_panel(
        panel_output=args.panel_output,
        blockers_output=args.blockers_output,
        next_actions_output=args.next_actions_output,
        report_output=args.report_output,
    )
    overview = {row["metric_name"]: row["metric_value"] for row in result.panel_rows}
    print(f"panel_output={result.panel_output}")
    print(f"blockers_output={result.blockers_output}")
    print(f"next_actions_output={result.next_actions_output}")
    print(f"report_output={result.report_output}")
    print(f"demo_readiness={overview.get('demo_readiness', 'NOT_AVAILABLE')}")
    print(f"decision_readiness={overview.get('decision_readiness', 'NOT_AVAILABLE')}")


if __name__ == "__main__":
    main()
