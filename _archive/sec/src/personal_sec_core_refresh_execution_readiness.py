from __future__ import annotations

import argparse
import os
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows
from src.personal_sec_refresh_preflight import IDENTITY_MAP_REQUIRED_COLUMNS

DEFAULT_PLAN_INPUT = "data/processed/personal_sec_core_kpi_refresh_plan.csv"
DEFAULT_PREFLIGHT_SUMMARY_INPUT = "data/processed/personal_sec_refresh_preflight_summary.csv"
DEFAULT_IDENTITY_MAP_INPUT = "data/raw/private/fundamentals/personal_sec_identity_map.csv"
DEFAULT_READINESS_OUTPUT = "data/processed/personal_sec_core_refresh_execution_readiness.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_sec_core_refresh_execution_readiness_summary.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_sec_core_refresh_execution_readiness_report.md"

VALID_DOWNSTREAM_STAGES = ("scoring", "coverage", "watchlist", "monthly", "dashboard")

READINESS_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "sec_identity_status",
    "sec_refresh_plan_status",
    "mapping_review_required",
    "sec_user_agent_status",
    "execution_readiness_status",
    "network_would_be_required",
    "network_performed",
    "fetch_performed",
    "evidence_apply_performed",
    "master_mutation_performed",
    "score_formula_mutation_performed",
    "reason_codes",
]

SUMMARY_FIELDS = [
    "refresh_scope_count",
    "ready_count",
    "blocked_count",
    "missing_user_agent_count",
    "identity_map_status",
    "network_would_be_required",
    "network_performed",
    "fetch_performed",
    "evidence_apply_performed",
    "master_mutation_performed",
    "score_formula_mutation_performed",
    "execution_status",
    "recommended_command_if_not_executed",
    "reason_codes",
]


@dataclass(frozen=True)
class SecCoreRefreshExecutionReadinessResult:
    readiness_output: Path
    summary_output: Path
    report_output: Path
    readiness_rows: list[dict[str, str]]
    summary_rows: list[dict[str, str]]


def safe_display_path(path_value: str) -> str:
    normalized = str(path_value).replace("\\", "/")
    if "data/raw/private" in normalized or normalized.startswith("personal_sec_"):
        return "<private_path>"
    return path_value


def optional_csv_rows(path_value: str) -> list[dict[str, str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return []
    return read_csv_rows(path)


def split_list(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").replace(",", ";").split(";") if item.strip()]


def joined(values: set[str] | list[str] | tuple[str, ...]) -> str:
    return ";".join(sorted(value for value in values if value))


def env_user_agent_present(explicit_user_agent: str = "") -> bool:
    return bool(
        str(explicit_user_agent or "").strip()
        or os.environ.get("SEC_USER_AGENT")
        or os.environ.get("SEC_COMPANYFACTS_USER_AGENT")
    )


def identity_map_status(identity_map_input: str, preflight_summary_rows: list[dict[str, str]]) -> tuple[str, set[str]]:
    path = resolve_repo_path(identity_map_input)
    if path.exists():
        rows = read_csv_rows(path)
        columns = set(rows[0].keys()) if rows else set()
        missing = [column for column in IDENTITY_MAP_REQUIRED_COLUMNS if column not in columns]
        if missing:
            return "INVALID_SCHEMA", {"SEC_IDENTITY_SCHEMA_INVALID"}
        return "PRESENT_VALID", {"SEC_IDENTITY_MAP_PRESENT", "SEC_IDENTITY_SCHEMA_VALID"}
    if preflight_summary_rows:
        summary = preflight_summary_rows[0]
        if summary.get("identity_map_present") == "True" and summary.get("identity_schema_valid") == "True":
            return "PRESENT_VALID", {"SEC_IDENTITY_MAP_PRESENT", "SEC_IDENTITY_SCHEMA_VALID"}
        if summary.get("identity_map_present") == "True":
            return "INVALID_SCHEMA", {"SEC_IDENTITY_SCHEMA_INVALID"}
    return "MISSING", {"SEC_IDENTITY_MAP_MISSING"}


def recommended_command() -> str:
    stage_args = " ".join(f"--downstream-stage {stage}" for stage in VALID_DOWNSTREAM_STAGES)
    return (
        "python -m src.personal_sec_refresh_pipeline "
        "--allow-network "
        "--sec-user-agent \"<SEC_USER_AGENT>\" "
        "--run-downstream "
        f"{stage_args}"
    )


def row_is_refresh_ready(row: dict[str, str]) -> bool:
    return (
        safe_upper(row.get("company_type_profile", "")) == "STANDARD"
        and row.get("sec_identity_status") == "APPROVED_IDENTITY"
        and row.get("sec_refresh_plan_status") == "READY_FOR_EXPLICIT_SEC_REFRESH"
        and str(row.get("mapping_review_required", "")).strip().lower() == "no"
    )


def build_readiness(
    *,
    plan_rows: list[dict[str, str]],
    preflight_summary_rows: list[dict[str, str]],
    identity_map_input: str,
    sec_user_agent: str = "",
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    identity_status, identity_reasons = identity_map_status(identity_map_input, preflight_summary_rows)
    user_agent_present = env_user_agent_present(sec_user_agent)
    readiness_rows: list[dict[str, str]] = []
    for row in sorted(plan_rows, key=lambda item: (str(item.get("isin", "")), str(item.get("ticker", "")))):
        reasons = {
            "NO_NETWORK_PERFORMED",
            "NO_FETCH_PERFORMED",
            "NO_EVIDENCE_APPLY",
            "NO_MASTER_MUTATION",
            "NO_SCORE_FORMULA_MUTATION",
            "NETWORK_REQUIRED_FOR_REFRESH",
        }
        reasons.update(identity_reasons)
        if row_is_refresh_ready(row):
            reasons.add("READY_PLAN_ROW")
        else:
            reasons.add("PLAN_ROW_NOT_READY")
        if user_agent_present:
            reasons.add("SEC_USER_AGENT_PRESENT")
        else:
            reasons.add("SEC_USER_AGENT_MISSING")
        if identity_status != "PRESENT_VALID":
            status = "BLOCKED_IDENTITY_MAP"
        elif not row_is_refresh_ready(row):
            status = "BLOCKED_PLAN_NOT_READY"
        elif not user_agent_present:
            status = "BLOCKED_USER_AGENT_MISSING"
        else:
            status = "READY_FOR_EXPLICIT_RUN"
        readiness_rows.append(
            {
                "ticker": row.get("ticker", ""),
                "isin": row.get("isin", ""),
                "company_name": row.get("company_name", ""),
                "company_type_profile": row.get("company_type_profile", ""),
                "sec_identity_status": row.get("sec_identity_status", ""),
                "sec_refresh_plan_status": row.get("sec_refresh_plan_status", ""),
                "mapping_review_required": row.get("mapping_review_required", ""),
                "sec_user_agent_status": "PRESENT" if user_agent_present else "MISSING",
                "execution_readiness_status": status,
                "network_would_be_required": "True",
                "network_performed": "False",
                "fetch_performed": "False",
                "evidence_apply_performed": "False",
                "master_mutation_performed": "False",
                "score_formula_mutation_performed": "False",
                "reason_codes": joined(reasons),
            }
        )

    counts = Counter(row["execution_readiness_status"] for row in readiness_rows)
    reason_union: set[str] = set()
    for row in readiness_rows:
        reason_union.update(split_list(row.get("reason_codes", "")))
    blocked = len(readiness_rows) - counts.get("READY_FOR_EXPLICIT_RUN", 0)
    execution_status = "READY_FOR_EXPLICIT_RUN" if readiness_rows and blocked == 0 else "BLOCKED_NOT_EXECUTED"
    if not readiness_rows:
        execution_status = "BLOCKED_NOT_EXECUTED"
        reason_union.add("NO_REFRESH_SCOPE_ROWS")
    summary_rows = [
        {
            "refresh_scope_count": str(len(readiness_rows)),
            "ready_count": str(counts.get("READY_FOR_EXPLICIT_RUN", 0)),
            "blocked_count": str(blocked),
            "missing_user_agent_count": str(sum(1 for row in readiness_rows if row["sec_user_agent_status"] == "MISSING")),
            "identity_map_status": identity_status,
            "network_would_be_required": "True",
            "network_performed": "False",
            "fetch_performed": "False",
            "evidence_apply_performed": "False",
            "master_mutation_performed": "False",
            "score_formula_mutation_performed": "False",
            "execution_status": execution_status,
            "recommended_command_if_not_executed": recommended_command() if execution_status != "READY_FOR_EXPLICIT_RUN" else "",
            "reason_codes": joined(reason_union),
        }
    ]
    return readiness_rows, summary_rows


def render_report(
    *,
    readiness_rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
    input_paths: dict[str, str],
) -> str:
    summary = summary_rows[0] if summary_rows else {}
    lines = [
        "# Personal SEC Core Refresh Execution Readiness",
        "",
        "## Executive Summary",
        f"- Execution status: `{summary.get('execution_status', 'BLOCKED_NOT_EXECUTED')}`",
        f"- Refresh scope count: `{summary.get('refresh_scope_count', '0')}`",
        f"- Ready count: `{summary.get('ready_count', '0')}`",
        f"- Blocked count: `{summary.get('blocked_count', '0')}`",
        f"- Missing user-agent count: `{summary.get('missing_user_agent_count', '0')}`",
        f"- Identity map status: `{summary.get('identity_map_status', 'NOT_AVAILABLE')}`",
        "",
        "## Inputs",
    ]
    for label, path_value in sorted(input_paths.items()):
        lines.append(f"- `{label}`: `{safe_display_path(path_value)}`")
    lines.extend(
        [
            "",
            "## Refresh Scope",
            "| ticker | isin | profile | plan_status | readiness_status |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in readiness_rows:
        lines.append(
            f"| {row['ticker']} | {row['isin']} | `{row['company_type_profile']}` | `{row['sec_refresh_plan_status']}` | `{row['execution_readiness_status']}` |"
        )
    if not readiness_rows:
        lines.append("| none |  |  |  | `BLOCKED_NOT_EXECUTED` |")
    lines.extend(
        [
            "",
            "## Network / Mutation Guardrails",
            f"- Network would be required: `{summary.get('network_would_be_required', 'True')}`",
            f"- Network performed: `{summary.get('network_performed', 'False')}`",
            f"- Fetch performed: `{summary.get('fetch_performed', 'False')}`",
            f"- Evidence apply performed: `{summary.get('evidence_apply_performed', 'False')}`",
            f"- Master mutation performed: `{summary.get('master_mutation_performed', 'False')}`",
            f"- Score formula mutation performed: `{summary.get('score_formula_mutation_performed', 'False')}`",
            "",
            "## Recommended Command If Not Executed",
            f"`{summary.get('recommended_command_if_not_executed', '')}`",
            "",
            "## Decision",
            f"`SEC_CORE_REFRESH_EXECUTION_STATUS = {summary.get('execution_status', 'BLOCKED_NOT_EXECUTED')}`",
        ]
    )
    return "\n".join(lines)


def run_personal_sec_core_refresh_execution_readiness(
    *,
    plan_input: str = DEFAULT_PLAN_INPUT,
    preflight_summary_input: str = DEFAULT_PREFLIGHT_SUMMARY_INPUT,
    identity_map_input: str = DEFAULT_IDENTITY_MAP_INPUT,
    readiness_output: str = DEFAULT_READINESS_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
    sec_user_agent: str = "",
) -> SecCoreRefreshExecutionReadinessResult:
    plan_rows = optional_csv_rows(plan_input)
    preflight_summary_rows = optional_csv_rows(preflight_summary_input)
    readiness_rows, summary_rows = build_readiness(
        plan_rows=plan_rows,
        preflight_summary_rows=preflight_summary_rows,
        identity_map_input=identity_map_input,
        sec_user_agent=sec_user_agent,
    )
    readiness_path = write_csv_rows(readiness_output, READINESS_FIELDS, readiness_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_report(
            readiness_rows=readiness_rows,
            summary_rows=summary_rows,
            input_paths={
                "plan_input": plan_input,
                "preflight_summary_input": preflight_summary_input,
                "identity_map_input": identity_map_input,
            },
        ),
        encoding="utf-8",
    )
    return SecCoreRefreshExecutionReadinessResult(readiness_path, summary_path, report_path, readiness_rows, summary_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check SEC core KPI refresh execution readiness without network.")
    parser.add_argument("--plan-input", default=DEFAULT_PLAN_INPUT)
    parser.add_argument("--preflight-summary-input", default=DEFAULT_PREFLIGHT_SUMMARY_INPUT)
    parser.add_argument("--identity-map-input", default=DEFAULT_IDENTITY_MAP_INPUT)
    parser.add_argument("--readiness-output", default=DEFAULT_READINESS_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--sec-user-agent", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_core_refresh_execution_readiness(
        plan_input=args.plan_input,
        preflight_summary_input=args.preflight_summary_input,
        identity_map_input=args.identity_map_input,
        readiness_output=args.readiness_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
        sec_user_agent=args.sec_user_agent,
    )
    summary = result.summary_rows[0] if result.summary_rows else {}
    print(f"readiness_output={result.readiness_output}")
    print(f"summary_output={result.summary_output}")
    print(f"report_output={result.report_output}")
    print(f"execution_status={summary.get('execution_status', 'BLOCKED_NOT_EXECUTED')}")
    print(f"network_performed={summary.get('network_performed', 'False')}")


if __name__ == "__main__":
    main()
