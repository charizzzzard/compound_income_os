from __future__ import annotations

import argparse
import os
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, write_csv_rows

DEFAULT_SEC_PLAN_INPUT = "data/processed/personal_sec_core_kpi_refresh_plan.csv"
DEFAULT_SEC_PLAN_SUMMARY_INPUT = "data/processed/personal_sec_core_kpi_refresh_plan_summary.csv"
DEFAULT_SEC_IDENTITY_MAP_INPUT = "data/raw/private/fundamentals/personal_sec_identity_map.csv"
DEFAULT_FETCH_MODULE_PATH = "src/external_sec_companyfacts_fetch.py"
DEFAULT_REFRESH_CLI_MODULE_PATH = "src/personal_sec_refresh_pipeline.py"
DEFAULT_PREFLIGHT_OUTPUT = "data/processed/personal_sec_refresh_preflight.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_sec_refresh_preflight_summary.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_sec_refresh_preflight_report.md"

IDENTITY_MAP_REQUIRED_COLUMNS = ("ticker", "isin", "company_name", "cik", "sec_entity_name", "asset_type", "country", "enabled", "notes")

PREFLIGHT_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "missing_core_kpis",
    "sec_identity_status",
    "sec_refresh_plan_status",
    "preflight_status",
    "identity_map_status",
    "sec_user_agent_status",
    "network_gate_status",
    "fetch_module_status",
    "refresh_cli_status",
    "network_performed",
    "fetch_performed",
    "raw_sec_snapshot_written",
    "evidence_apply_performed",
    "master_mutation_performed",
    "score_mutation_performed",
    "reason_codes",
]

SUMMARY_FIELDS = [
    "plan_rows_count",
    "ready_for_explicit_network_run_count",
    "review_required_count",
    "blocked_count",
    "identity_map_present",
    "identity_schema_valid",
    "sec_user_agent_present",
    "network_gate_required_for_future_refresh",
    "network_performed",
    "fetch_performed",
    "raw_sec_snapshot_written",
    "evidence_apply_performed",
    "master_mutation_performed",
    "score_mutation_performed",
    "future_refresh_command_status",
    "reason_codes",
]


@dataclass(frozen=True)
class SecRefreshPreflightResult:
    preflight_output: Path
    summary_output: Path
    report_output: Path
    preflight_rows: list[dict[str, str]]
    summary_rows: list[dict[str, str]]
    warnings: tuple[str, ...]


def safe_display_path(path_value: str) -> str:
    normalized = str(path_value).replace("\\", "/")
    if "data/raw/private" in normalized:
        return "<private_path>"
    return path_value


def optional_csv_rows(path_value: str, label: str) -> tuple[list[dict[str, str]], bool, list[str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], False, [f"missing_input={label}:{safe_display_path(path_value)}"]
    return read_csv_rows(path), True, []


def joined(values: set[str] | list[str] | tuple[str, ...]) -> str:
    return ";".join(sorted(value for value in values if value))


def split_list(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").replace(",", ";").split(";") if item.strip()]


def env_user_agent_present(explicit_user_agent: str = "") -> bool:
    return bool(
        str(explicit_user_agent or "").strip()
        or os.environ.get("SEC_USER_AGENT")
        or os.environ.get("SEC_COMPANYFACTS_USER_AGENT")
    )


def identity_map_status(identity_map_input: str) -> tuple[str, bool, bool, set[str], int]:
    path = resolve_repo_path(identity_map_input)
    if not path.exists():
        return "MISSING", False, False, {"SEC_IDENTITY_MAP_MISSING"}, 0
    rows = read_csv_rows(path)
    columns = set(rows[0].keys()) if rows else set()
    missing = [column for column in IDENTITY_MAP_REQUIRED_COLUMNS if column not in columns]
    if missing:
        return "INVALID_SCHEMA", True, False, {"SEC_IDENTITY_SCHEMA_INVALID"}, len(rows)
    return "PRESENT", True, True, {"SEC_IDENTITY_MAP_PRESENT"}, len(rows)


def module_cli_status(module_path: str, *, require_fetch_gates: bool, module_kind: str) -> tuple[str, set[str]]:
    path = resolve_repo_path(module_path)
    missing_reason = "FETCH_MODULE_MISSING" if module_kind == "fetch" else "REFRESH_CLI_MISSING"
    available_reason = "FETCH_MODULE_AVAILABLE" if module_kind == "fetch" else "REFRESH_CLI_AVAILABLE"
    if not path.exists():
        return "MISSING", {missing_reason}
    text = path.read_text(encoding="utf-8")
    if require_fetch_gates and ("--allow-network" not in text or "--sec-user-agent" not in text or "def main" not in text):
        return "UNKNOWN", {missing_reason}
    return "AVAILABLE", {available_reason}


def future_command_status(fetch_module_status: str, refresh_cli_status: str) -> str:
    if fetch_module_status == "AVAILABLE" and refresh_cli_status == "AVAILABLE":
        return "AVAILABLE"
    if fetch_module_status == "MISSING" or refresh_cli_status == "MISSING":
        return "MISSING"
    return "REVIEW"


def classify_preflight_status(
    *,
    plan_status: str,
    identity_status: str,
    identity_map_state: str,
    user_agent_present: bool,
    fetch_module_status: str,
    refresh_cli_status: str,
) -> tuple[str, set[str]]:
    reasons: set[str] = {
        "ALLOW_NETWORK_REQUIRED_FOR_FUTURE_REFRESH",
        "NO_NETWORK_BY_DEFAULT",
        "NO_NETWORK_PERFORMED",
        "NO_FETCH_PERFORMED",
        "NO_RAW_SEC_SNAPSHOT_WRITTEN",
        "NO_EVIDENCE_APPLY",
        "NO_MASTER_MUTATION",
        "NO_SCORE_MUTATION",
    }
    if plan_status != "READY_FOR_EXPLICIT_SEC_REFRESH":
        reasons.add("REVIEW_REQUIRED")
        return "REVIEW_REQUIRED", reasons
    reasons.add("SEC_REFRESH_PLAN_READY")
    if identity_status != "APPROVED_IDENTITY" or identity_map_state == "MISSING":
        reasons.update({"SEC_IDENTITY_MAP_MISSING" if identity_map_state == "MISSING" else "REVIEW_REQUIRED", "BLOCKED"})
        return "BLOCKED", reasons
    if identity_map_state == "INVALID_SCHEMA":
        reasons.update({"SEC_IDENTITY_SCHEMA_INVALID", "BLOCKED"})
        return "BLOCKED", reasons
    if fetch_module_status != "AVAILABLE" or refresh_cli_status != "AVAILABLE":
        reasons.add("REVIEW_REQUIRED")
        return "REVIEW_REQUIRED", reasons
    if not user_agent_present:
        reasons.update({"SEC_USER_AGENT_MISSING", "REVIEW_REQUIRED"})
        return "REVIEW_REQUIRED", reasons
    reasons.update({"SEC_USER_AGENT_PRESENT", "READY_FOR_EXPLICIT_NETWORK_RUN"})
    return "READY_FOR_EXPLICIT_NETWORK_RUN", reasons


def build_preflight(
    *,
    plan_rows: list[dict[str, str]],
    identity_map_state: str,
    identity_present: bool,
    identity_schema_valid: bool,
    user_agent_present: bool,
    fetch_module_status: str,
    fetch_reasons: set[str],
    refresh_cli_status: str,
    refresh_reasons: set[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    preflight_rows: list[dict[str, str]] = []
    for row in sorted(plan_rows, key=lambda item: (str(item.get("isin", "")), str(item.get("ticker", "")))):
        status, reasons = classify_preflight_status(
            plan_status=row.get("sec_refresh_plan_status", ""),
            identity_status=row.get("sec_identity_status", ""),
            identity_map_state=identity_map_state,
            user_agent_present=user_agent_present,
            fetch_module_status=fetch_module_status,
            refresh_cli_status=refresh_cli_status,
        )
        reasons.update(fetch_reasons)
        reasons.update(refresh_reasons)
        if identity_present:
            reasons.add("SEC_IDENTITY_MAP_PRESENT")
        if not identity_schema_valid and identity_present:
            reasons.add("SEC_IDENTITY_SCHEMA_INVALID")
        preflight_rows.append(
            {
                "ticker": row.get("ticker", ""),
                "isin": row.get("isin", ""),
                "company_name": row.get("company_name", ""),
                "company_type_profile": row.get("company_type_profile", ""),
                "missing_core_kpis": row.get("missing_core_kpis", ""),
                "sec_identity_status": row.get("sec_identity_status", ""),
                "sec_refresh_plan_status": row.get("sec_refresh_plan_status", ""),
                "preflight_status": status,
                "identity_map_status": identity_map_state,
                "sec_user_agent_status": "PRESENT" if user_agent_present else "MISSING",
                "network_gate_status": "REQUIRED_FOR_REFRESH",
                "fetch_module_status": fetch_module_status,
                "refresh_cli_status": refresh_cli_status,
                "network_performed": "False",
                "fetch_performed": "False",
                "raw_sec_snapshot_written": "False",
                "evidence_apply_performed": "False",
                "master_mutation_performed": "False",
                "score_mutation_performed": "False",
                "reason_codes": joined(reasons),
            }
        )

    counts = Counter(row["preflight_status"] for row in preflight_rows)
    reason_union: set[str] = set()
    for row in preflight_rows:
        reason_union.update(split_list(row.get("reason_codes", "")))
    if not plan_rows:
        reason_union.update({"SEC_REFRESH_PLAN_MISSING", "NO_NETWORK_BY_DEFAULT", "NO_NETWORK_PERFORMED", "NO_FETCH_PERFORMED"})
    command_status = future_command_status(fetch_module_status, refresh_cli_status)
    summary_rows = [
        {
            "plan_rows_count": str(len(plan_rows)),
            "ready_for_explicit_network_run_count": str(counts.get("READY_FOR_EXPLICIT_NETWORK_RUN", 0)),
            "review_required_count": str(counts.get("REVIEW_REQUIRED", 0)),
            "blocked_count": str(counts.get("BLOCKED", 0)),
            "identity_map_present": str(bool(identity_present)),
            "identity_schema_valid": str(bool(identity_schema_valid)),
            "sec_user_agent_present": str(bool(user_agent_present)),
            "network_gate_required_for_future_refresh": "True",
            "network_performed": "False",
            "fetch_performed": "False",
            "raw_sec_snapshot_written": "False",
            "evidence_apply_performed": "False",
            "master_mutation_performed": "False",
            "score_mutation_performed": "False",
            "future_refresh_command_status": command_status,
            "reason_codes": joined(reason_union),
        }
    ]
    return preflight_rows, summary_rows


def render_report(
    *,
    preflight_rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
    input_paths: dict[str, str],
    warnings: tuple[str, ...],
) -> str:
    summary = summary_rows[0] if summary_rows else {}
    lines = [
        "# Personal SEC Refresh Preflight Report",
        "",
        "## 1. Executive Summary",
        f"- Plan rows: `{summary.get('plan_rows_count', '0')}`",
        f"- Ready for explicit network run: `{summary.get('ready_for_explicit_network_run_count', '0')}`",
        f"- Review required: `{summary.get('review_required_count', '0')}`",
        f"- Blocked: `{summary.get('blocked_count', '0')}`",
        f"- Future refresh command status: `{summary.get('future_refresh_command_status', 'NOT_AVAILABLE')}`",
        f"- Network performed: `{summary.get('network_performed', 'False')}`",
        "",
        "## 2. Input SEC Plan",
    ]
    for label, path_value in sorted(input_paths.items()):
        lines.append(f"- `{label}`: `{safe_display_path(path_value)}`")
    lines.extend(
        [
            "",
            "## 3. Identity Map Preflight",
            f"- Identity map present: `{summary.get('identity_map_present', 'False')}`",
            f"- Identity schema valid: `{summary.get('identity_schema_valid', 'False')}`",
            "- Private identity-map rows, CIKs, entity names, and notes are not rendered.",
            "",
            "## 4. SEC User-Agent / Network Gate",
            f"- SEC user-agent present: `{summary.get('sec_user_agent_present', 'False')}`",
            f"- Network gate required for future refresh: `{summary.get('network_gate_required_for_future_refresh', 'True')}`",
            "- No network gate is enabled or used by this preflight.",
            "",
            "## 5. Fetch Module / CLI Availability",
            "| ticker | preflight_status | fetch_module_status | refresh_cli_status | reason_codes |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    if preflight_rows:
        for row in preflight_rows:
            lines.append(
                f"| {row['ticker']} | `{row['preflight_status']}` | `{row['fetch_module_status']}` | `{row['refresh_cli_status']}` | `{row['reason_codes']}` |"
            )
    else:
        lines.append("| none | `NOT_AVAILABLE` |  |  | `SEC_REFRESH_PLAN_MISSING` |")
    lines.extend(
        [
            "",
            "## 6. Future Explicit Refresh Command Plan",
            "- Stable module path detected only when the committed module file exposes explicit `--allow-network` and `--sec-user-agent` gates.",
            "- Future refresh must provide approved identity map path, SEC user-agent, and explicit allow-network flag.",
            "- Expected follow-up remains separate: SEC snapshot, evidence review, evidence compose/apply, downstream run.",
            "",
            "## 7. Network Guardrail",
            "- `network_performed=False`.",
            "- `fetch_performed=False`.",
            "- No HTTP request, CompanyFacts download, or raw SEC snapshot write was performed.",
            "",
            "## 8. No-Value-Change Guardrail",
            "- `raw_sec_snapshot_written=False`.",
            "- `evidence_apply_performed=False`.",
            "- `master_mutation_performed=False`.",
            "- `score_mutation_performed=False`.",
            "",
            "## 9. Readiness Impact",
            "- `REVIEW_CORE_DATA` is not resolved by preflight.",
            "- Preflight only confirms whether a later explicit network run would be gate-ready.",
            "",
            "## 10. Remaining Blockers",
            "- `MISSING_VALUATION_REQUIRED`",
            "- `MISSING_DIVIDEND_FCF_REQUIRED`",
            "- `PROVENANCE_INCOMPLETE`",
            "- `REVIEW_CORE_DATA`",
            "- `WATCHLIST_SAMPLE_INPUT`",
            "- `WATCHLIST_REVIEW_OR_MISSING_DATA`",
            "",
            "## 11. Recommended Next Patch",
            "`PATCH / DASHBOARD READINESS PANEL / REAL BLOCKER DATA / NO DUMMY CLAIMS`",
        ]
    )
    if warnings:
        lines.extend(["", "## Warnings"])
        for warning in warnings:
            lines.append(f"- `{warning}`")
    lines.append("")
    return "\n".join(lines)


def run_personal_sec_refresh_preflight(
    *,
    sec_plan_input: str = DEFAULT_SEC_PLAN_INPUT,
    sec_plan_summary_input: str = DEFAULT_SEC_PLAN_SUMMARY_INPUT,
    sec_identity_map_input: str = DEFAULT_SEC_IDENTITY_MAP_INPUT,
    fetch_module_path: str = DEFAULT_FETCH_MODULE_PATH,
    refresh_cli_module_path: str = DEFAULT_REFRESH_CLI_MODULE_PATH,
    sec_user_agent: str = "",
    preflight_output: str = DEFAULT_PREFLIGHT_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> SecRefreshPreflightResult:
    warnings: list[str] = []
    plan_rows, plan_present, plan_warnings = optional_csv_rows(sec_plan_input, "sec_refresh_plan")
    _, _, summary_warnings = optional_csv_rows(sec_plan_summary_input, "sec_refresh_plan_summary")
    warnings.extend(plan_warnings)
    warnings.extend(summary_warnings)
    if not plan_present:
        plan_rows = []
    identity_state, identity_present, schema_valid, identity_reasons, _identity_row_count = identity_map_status(sec_identity_map_input)
    fetch_status, fetch_reasons = module_cli_status(fetch_module_path, require_fetch_gates=True, module_kind="fetch")
    refresh_status, refresh_reasons = module_cli_status(refresh_cli_module_path, require_fetch_gates=True, module_kind="refresh")
    preflight_rows, summary_rows = build_preflight(
        plan_rows=plan_rows,
        identity_map_state=identity_state,
        identity_present=identity_present,
        identity_schema_valid=schema_valid,
        user_agent_present=env_user_agent_present(sec_user_agent),
        fetch_module_status=fetch_status,
        fetch_reasons=fetch_reasons.union(identity_reasons),
        refresh_cli_status=refresh_status,
        refresh_reasons=refresh_reasons,
    )
    preflight_path = write_csv_rows(preflight_output, PREFLIGHT_FIELDS, preflight_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    input_paths = {
        "sec_plan": sec_plan_input,
        "sec_plan_summary": sec_plan_summary_input,
        "sec_identity_map": sec_identity_map_input,
        "fetch_module": fetch_module_path,
        "refresh_cli_module": refresh_cli_module_path,
        "preflight_output": preflight_output,
        "summary_output": summary_output,
    }
    report_path.write_text(
        render_report(
            preflight_rows=preflight_rows,
            summary_rows=summary_rows,
            input_paths=input_paths,
            warnings=tuple(warnings),
        ),
        encoding="utf-8",
    )
    return SecRefreshPreflightResult(
        preflight_output=preflight_path,
        summary_output=summary_path,
        report_output=report_path,
        preflight_rows=preflight_rows,
        summary_rows=summary_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SEC refresh preflight without network or fetch.")
    parser.add_argument("--sec-plan-input", default=DEFAULT_SEC_PLAN_INPUT)
    parser.add_argument("--sec-plan-summary-input", default=DEFAULT_SEC_PLAN_SUMMARY_INPUT)
    parser.add_argument("--sec-identity-map-input", default=DEFAULT_SEC_IDENTITY_MAP_INPUT)
    parser.add_argument("--fetch-module-path", default=DEFAULT_FETCH_MODULE_PATH)
    parser.add_argument("--refresh-cli-module-path", default=DEFAULT_REFRESH_CLI_MODULE_PATH)
    parser.add_argument("--sec-user-agent", default="")
    parser.add_argument("--preflight-output", default=DEFAULT_PREFLIGHT_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_refresh_preflight(
        sec_plan_input=args.sec_plan_input,
        sec_plan_summary_input=args.sec_plan_summary_input,
        sec_identity_map_input=args.sec_identity_map_input,
        fetch_module_path=args.fetch_module_path,
        refresh_cli_module_path=args.refresh_cli_module_path,
        sec_user_agent=args.sec_user_agent,
        preflight_output=args.preflight_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    summary = result.summary_rows[0] if result.summary_rows else {}
    print(f"preflight_output={result.preflight_output}")
    print(f"summary_output={result.summary_output}")
    print(f"report_output={result.report_output}")
    print(f"plan_rows_count={summary.get('plan_rows_count', '0')}")
    print(f"ready_for_explicit_network_run_count={summary.get('ready_for_explicit_network_run_count', '0')}")
    print(f"network_performed={summary.get('network_performed', 'False')}")


if __name__ == "__main__":
    main()
