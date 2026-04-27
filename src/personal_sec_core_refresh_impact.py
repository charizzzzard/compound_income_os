from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, write_csv_rows

DEFAULT_EXECUTION_SUMMARY_INPUT = "data/processed/personal_sec_core_refresh_execution_readiness_summary.csv"
DEFAULT_PLAN_INPUT = "data/processed/personal_sec_core_kpi_refresh_plan.csv"
DEFAULT_CORE_CLOSURE_SUMMARY_INPUT = "data/processed/personal_core_kpi_closure_summary.csv"
DEFAULT_KPI_TIER_COVERAGE_INPUT = "data/processed/personal_kpi_tier_coverage.csv"
DEFAULT_READINESS_SUMMARY_INPUT = "data/processed/personal_readiness_status_summary.csv"
DEFAULT_READINESS_BLOCKERS_INPUT = "data/processed/personal_readiness_blockers.csv"
DEFAULT_MONTHLY_INPUT = "data/processed/personal_monthly_buy_ranking.csv"
DEFAULT_EVIDENCE_DELTA_SUMMARY_INPUT = "data/processed/personal_evidence_applied_downstream_delta_summary.csv"
DEFAULT_EVIDENCE_DELTA_HOLDINGS_INPUT = "data/processed/personal_evidence_applied_downstream_delta_holdings.csv"
DEFAULT_PRIVATE_APPLY_SUMMARY_INPUT = "data/processed/personal_private_input_apply_candidates_summary.csv"
DEFAULT_IMPACT_SUMMARY_OUTPUT = "data/processed/personal_sec_core_refresh_impact_summary.csv"
DEFAULT_IMPACT_HOLDINGS_OUTPUT = "data/processed/personal_sec_core_refresh_impact_holdings.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_sec_core_refresh_impact_report.md"

HOLDING_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "execution_status",
    "missing_core_kpi_count_before",
    "missing_core_kpi_count_after",
    "score_data_quality_flag_before",
    "score_data_quality_flag_after",
    "monthly_action_before",
    "monthly_action_after",
    "holding_improved",
    "reason_codes",
]

SUMMARY_FIELDS = [
    "execution_status",
    "affected_holdings_count",
    "core_kpi_rows_before",
    "core_kpi_rows_after",
    "missing_core_kpi_count_before",
    "missing_core_kpi_count_after",
    "readiness_status_before",
    "readiness_status_after",
    "remaining_p0_blockers",
    "remaining_manual_input_required_count",
    "evidence_registry_rows_added",
    "evidence_apply_rows_added",
    "no_imputation_confirmed",
    "no_value_changes_confirmed",
    "master_mutation_performed",
    "score_formula_mutation_performed",
    "network_performed",
    "holdings_improved_count",
    "reason_codes",
]


@dataclass(frozen=True)
class SecCoreRefreshImpactResult:
    impact_summary_output: Path
    impact_holdings_output: Path
    report_output: Path
    summary_rows: list[dict[str, str]]
    holding_rows: list[dict[str, str]]


def optional_csv_rows(path_value: str) -> list[dict[str, str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return []
    return read_csv_rows(path)


def metric_value(rows: list[dict[str, str]], metric: str, default: str = "0") -> str:
    for row in rows:
        if row.get("metric") == metric:
            return str(row.get("value", default))
    return default


def readiness_status(rows: list[dict[str, str]], scope: str, default: str = "NOT_AVAILABLE") -> str:
    for row in rows:
        if row.get("readiness_scope") == scope:
            return row.get("readiness_status", default)
    return default


def split_list(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").replace(",", ";").split(";") if item.strip()]


def int_text(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value or "").strip()))
    except ValueError:
        return default


def monthly_index(rows: list[dict[str, str]]) -> dict[str, str]:
    index: dict[str, str] = {}
    for row in rows:
        ticker = str(row.get("ticker", "")).strip().upper()
        if ticker:
            index[ticker] = row.get("target_action", "") or row.get("monthly_action", "")
    return index


def coverage_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in rows:
        ticker = str(row.get("ticker", "")).strip().upper()
        isin = str(row.get("isin", "")).strip().upper()
        if ticker:
            index[ticker] = row
        if isin:
            index[isin] = row
    return index


def active_decision_p0_blockers(rows: list[dict[str, str]]) -> list[str]:
    blockers = []
    for row in rows:
        severity = row.get("blocker_severity", row.get("severity", ""))
        if row.get("readiness_scope") == "DECISION" and row.get("blocker_status") == "ACTIVE" and severity in {"P0", "P0_BLOCKER"}:
            blockers.append(row.get("blocker_code", ""))
    if not blockers:
        for row in rows:
            if row.get("readiness_scope") == "DECISION" and row.get("blocker_status") == "ACTIVE":
                blockers.append(row.get("blocker_code", ""))
    return sorted(code for code in blockers if code)


def manual_required_count(private_apply_summary_rows: list[dict[str, str]]) -> int:
    total = 0
    for row in private_apply_summary_rows:
        total += int_text(row.get("not_ready_rows_count", "0"))
    return total


def evidence_rows_added(execution_status: str, delta_summary_rows: list[dict[str, str]]) -> tuple[int, int]:
    if execution_status != "EXECUTED":
        return 0, 0
    registry = int_text(metric_value(delta_summary_rows, "evidence_registry_rows_added", "0"))
    apply_rows = int_text(metric_value(delta_summary_rows, "evidence_apply_rows_added", "0"))
    return registry, apply_rows


def build_impact(
    *,
    execution_summary_rows: list[dict[str, str]],
    plan_rows: list[dict[str, str]],
    core_summary_rows: list[dict[str, str]],
    kpi_tier_rows: list[dict[str, str]],
    readiness_summary_rows: list[dict[str, str]],
    readiness_blocker_rows: list[dict[str, str]],
    monthly_rows: list[dict[str, str]],
    evidence_delta_summary_rows: list[dict[str, str]],
    private_apply_summary_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    execution_summary = execution_summary_rows[0] if execution_summary_rows else {}
    execution_status = execution_summary.get("execution_status", "BLOCKED_NOT_EXECUTED")
    network_performed = execution_summary.get("network_performed", "False")
    master_mutation = execution_summary.get("master_mutation_performed", "False")
    score_mutation = execution_summary.get("score_formula_mutation_performed", "False")
    no_value_changes = execution_status != "EXECUTED"
    coverage = coverage_index(kpi_tier_rows)
    monthly = monthly_index(monthly_rows)
    holding_rows: list[dict[str, str]] = []
    for row in sorted(plan_rows, key=lambda item: (str(item.get("isin", "")), str(item.get("ticker", "")))):
        ticker = str(row.get("ticker", "")).strip().upper()
        isin = str(row.get("isin", "")).strip().upper()
        coverage_row = coverage.get(ticker) or coverage.get(isin) or {}
        before_missing = row.get("missing_core_kpi_count", "0")
        after_missing = before_missing if no_value_changes else coverage_row.get("missing_core_quality_kpis", before_missing)
        before_flag = coverage_row.get("resulting_score_data_quality_flag", "MISSING_DATA")
        before_action = coverage_row.get("resulting_monthly_action", "") or monthly.get(ticker, "")
        holding_rows.append(
            {
                "ticker": row.get("ticker", ""),
                "isin": row.get("isin", ""),
                "company_name": row.get("company_name", ""),
                "execution_status": execution_status,
                "missing_core_kpi_count_before": before_missing,
                "missing_core_kpi_count_after": after_missing,
                "score_data_quality_flag_before": before_flag,
                "score_data_quality_flag_after": before_flag if no_value_changes else coverage_row.get("resulting_score_data_quality_flag", before_flag),
                "monthly_action_before": before_action,
                "monthly_action_after": before_action if no_value_changes else monthly.get(ticker, before_action),
                "holding_improved": "False" if no_value_changes else "REVIEW",
                "reason_codes": "BLOCKED_NOT_EXECUTED;NO_VALUE_CHANGES;NO_IMPUTATION" if no_value_changes else "EXECUTED_REVIEW_REQUIRED",
            }
        )

    missing_before = sum(int_text(row.get("missing_core_kpi_count_before", "0")) for row in holding_rows)
    missing_after = sum(int_text(row.get("missing_core_kpi_count_after", "0")) for row in holding_rows)
    registry_added, apply_added = evidence_rows_added(execution_status, evidence_delta_summary_rows)
    blockers = active_decision_p0_blockers(readiness_blocker_rows)
    if not blockers:
        blockers = split_list(next((row.get("active_p0_blockers", "") for row in readiness_summary_rows if row.get("readiness_scope") == "DECISION"), ""))
    reason_codes = {
        "NO_IMPUTATION",
        "NO_SCORE_FORMULA_MUTATION" if score_mutation == "False" else "SCORE_FORMULA_MUTATION_REVIEW",
        "NO_MASTER_MUTATION" if master_mutation == "False" else "MASTER_MUTATION_REVIEW",
    }
    if no_value_changes:
        reason_codes.update({"BLOCKED_NOT_EXECUTED", "NO_VALUE_CHANGES_CONFIRMED"})
    summary_rows = [
        {
            "execution_status": execution_status,
            "affected_holdings_count": str(len(holding_rows)),
            "core_kpi_rows_before": metric_value(core_summary_rows, "review_rows_count", str(len(holding_rows))),
            "core_kpi_rows_after": metric_value(core_summary_rows, "review_rows_count", str(len(holding_rows))) if no_value_changes else str(len(holding_rows)),
            "missing_core_kpi_count_before": str(missing_before),
            "missing_core_kpi_count_after": str(missing_after),
            "readiness_status_before": readiness_status(readiness_summary_rows, "DECISION"),
            "readiness_status_after": readiness_status(readiness_summary_rows, "DECISION") if no_value_changes else "REVIEW",
            "remaining_p0_blockers": ";".join(blockers),
            "remaining_manual_input_required_count": str(manual_required_count(private_apply_summary_rows)),
            "evidence_registry_rows_added": str(registry_added),
            "evidence_apply_rows_added": str(apply_added),
            "no_imputation_confirmed": "True",
            "no_value_changes_confirmed": "True" if no_value_changes else "False",
            "master_mutation_performed": master_mutation,
            "score_formula_mutation_performed": score_mutation,
            "network_performed": network_performed,
            "holdings_improved_count": str(sum(1 for row in holding_rows if row["holding_improved"] == "True")),
            "reason_codes": ";".join(sorted(reason_codes)),
        }
    ]
    return summary_rows, holding_rows


def render_report(summary_rows: list[dict[str, str]], holding_rows: list[dict[str, str]]) -> str:
    summary = summary_rows[0] if summary_rows else {}
    lines = [
        "# Personal SEC Core Refresh Impact Report",
        "",
        "## Executive Summary",
        f"- Execution status: `{summary.get('execution_status', 'BLOCKED_NOT_EXECUTED')}`",
        f"- Affected holdings: `{summary.get('affected_holdings_count', '0')}`",
        f"- Missing core KPI count before/after: `{summary.get('missing_core_kpi_count_before', '0')}` / `{summary.get('missing_core_kpi_count_after', '0')}`",
        f"- Decision readiness before/after: `{summary.get('readiness_status_before', 'NOT_AVAILABLE')}` / `{summary.get('readiness_status_after', 'NOT_AVAILABLE')}`",
        f"- No value changes confirmed: `{summary.get('no_value_changes_confirmed', 'True')}`",
        "",
        "## Holdings Impact",
        "| ticker | isin | missing before | missing after | data quality before | data quality after | monthly before | monthly after |",
        "| --- | --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in holding_rows:
        lines.append(
            f"| {row['ticker']} | {row['isin']} | `{row['missing_core_kpi_count_before']}` | `{row['missing_core_kpi_count_after']}` | `{row['score_data_quality_flag_before']}` | `{row['score_data_quality_flag_after']}` | `{row['monthly_action_before']}` | `{row['monthly_action_after']}` |"
        )
    lines.extend(
        [
            "",
            "## Closure / Readiness Impact",
            f"- Core KPI rows before/after: `{summary.get('core_kpi_rows_before', '0')}` / `{summary.get('core_kpi_rows_after', '0')}`",
            f"- Remaining P0 blockers: `{summary.get('remaining_p0_blockers', '')}`",
            f"- Remaining manual input required count: `{summary.get('remaining_manual_input_required_count', '0')}`",
            "",
            "## Evidence / Provenance Impact",
            f"- Evidence registry rows added: `{summary.get('evidence_registry_rows_added', '0')}`",
            f"- Evidence apply rows added: `{summary.get('evidence_apply_rows_added', '0')}`",
            f"- No imputation confirmed: `{summary.get('no_imputation_confirmed', 'True')}`",
            f"- Master mutation performed: `{summary.get('master_mutation_performed', 'False')}`",
            f"- Score formula mutation performed: `{summary.get('score_formula_mutation_performed', 'False')}`",
            f"- Network performed: `{summary.get('network_performed', 'False')}`",
            "",
            "## Decision",
            f"`SEC_CORE_REFRESH_IMPACT_STATUS = {summary.get('execution_status', 'BLOCKED_NOT_EXECUTED')}`",
        ]
    )
    return "\n".join(lines)


def run_personal_sec_core_refresh_impact(
    *,
    execution_summary_input: str = DEFAULT_EXECUTION_SUMMARY_INPUT,
    plan_input: str = DEFAULT_PLAN_INPUT,
    core_closure_summary_input: str = DEFAULT_CORE_CLOSURE_SUMMARY_INPUT,
    kpi_tier_coverage_input: str = DEFAULT_KPI_TIER_COVERAGE_INPUT,
    readiness_summary_input: str = DEFAULT_READINESS_SUMMARY_INPUT,
    readiness_blockers_input: str = DEFAULT_READINESS_BLOCKERS_INPUT,
    monthly_input: str = DEFAULT_MONTHLY_INPUT,
    evidence_delta_summary_input: str = DEFAULT_EVIDENCE_DELTA_SUMMARY_INPUT,
    evidence_delta_holdings_input: str = DEFAULT_EVIDENCE_DELTA_HOLDINGS_INPUT,
    private_apply_summary_input: str = DEFAULT_PRIVATE_APPLY_SUMMARY_INPUT,
    impact_summary_output: str = DEFAULT_IMPACT_SUMMARY_OUTPUT,
    impact_holdings_output: str = DEFAULT_IMPACT_HOLDINGS_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> SecCoreRefreshImpactResult:
    summary_rows, holding_rows = build_impact(
        execution_summary_rows=optional_csv_rows(execution_summary_input),
        plan_rows=optional_csv_rows(plan_input),
        core_summary_rows=optional_csv_rows(core_closure_summary_input),
        kpi_tier_rows=optional_csv_rows(kpi_tier_coverage_input),
        readiness_summary_rows=optional_csv_rows(readiness_summary_input),
        readiness_blocker_rows=optional_csv_rows(readiness_blockers_input),
        monthly_rows=optional_csv_rows(monthly_input),
        evidence_delta_summary_rows=optional_csv_rows(evidence_delta_summary_input),
        private_apply_summary_rows=optional_csv_rows(private_apply_summary_input),
    )
    summary_path = write_csv_rows(impact_summary_output, SUMMARY_FIELDS, summary_rows)
    holdings_path = write_csv_rows(impact_holdings_output, HOLDING_FIELDS, holding_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(summary_rows, holding_rows), encoding="utf-8")
    return SecCoreRefreshImpactResult(summary_path, holdings_path, report_path, summary_rows, holding_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize SEC core refresh impact without imputation.")
    parser.add_argument("--execution-summary-input", default=DEFAULT_EXECUTION_SUMMARY_INPUT)
    parser.add_argument("--impact-summary-output", default=DEFAULT_IMPACT_SUMMARY_OUTPUT)
    parser.add_argument("--impact-holdings-output", default=DEFAULT_IMPACT_HOLDINGS_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_core_refresh_impact(
        execution_summary_input=args.execution_summary_input,
        impact_summary_output=args.impact_summary_output,
        impact_holdings_output=args.impact_holdings_output,
        report_output=args.report_output,
    )
    summary = result.summary_rows[0] if result.summary_rows else {}
    print(f"impact_summary_output={result.impact_summary_output}")
    print(f"impact_holdings_output={result.impact_holdings_output}")
    print(f"report_output={result.report_output}")
    print(f"execution_status={summary.get('execution_status', 'BLOCKED_NOT_EXECUTED')}")
    print(f"no_value_changes_confirmed={summary.get('no_value_changes_confirmed', 'True')}")


if __name__ == "__main__":
    main()
