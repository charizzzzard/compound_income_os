from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.common import read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_MONTHLY_INPUT = "data/processed/personal_monthly_buy_ranking.csv"
DEFAULT_COMPATIBILITY_OUTPUT = "data/processed/personal_monthly_action_compatibility.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_monthly_action_compatibility_summary.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_monthly_action_schema_report.md"

MONTHLY_ACTION_VALUES = {
    "REVIEW_DATA",
    "WAIT_FOR_PRICE",
    "WAIT_FOR_VALUATION",
    "WAIT_FOR_COVERAGE",
    "HOLD_REVIEW",
    "ADD_CANDIDATE_REVIEW",
    "NOT_READY",
    "BLOCKED",
    "NO_ACTION",
    "NOT_AVAILABLE",
}
FORBIDDEN_MONTHLY_ACTION_VALUES = {"BUY", "SELL", "STRONG_BUY", "STRONG_SELL", "RECOMMEND", "DO_BUY", "TRADE", "TRADE_SIGNAL", "ORDER", "EXECUTE"}

COMPATIBILITY_FIELDS = [
    "rank",
    "ticker",
    "company_name",
    "legacy_target_action",
    "legacy_allocation_status",
    "monthly_action",
    "monthly_action_reason_code",
    "schema_status",
    "suggested_buy_amount_eur",
    "constraint_checks",
]
SUMMARY_FIELDS = ["metric", "value", "notes"]


@dataclass(frozen=True)
class MonthlyActionSchemaResult:
    compatibility_output: Path
    summary_output: Path
    report_output: Path
    compatibility_rows: list[dict[str, str]]
    summary_rows: list[dict[str, str]]
    warnings: tuple[str, ...]


def safe_display_path(path_value: str) -> str:
    normalized = str(path_value).replace("\\", "/")
    if "data/raw/private" in normalized:
        return "<private_path>"
    return path_value


def optional_csv_rows(path_value: str, label: str) -> tuple[list[dict[str, str]], list[str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], [f"missing_input={label}:{safe_display_path(path_value)}"]
    return read_csv_rows(path), []


def bool_text(value: bool) -> str:
    return "True" if value else "False"


def derive_monthly_action(row: dict[str, str]) -> tuple[str, str]:
    target_action = safe_upper(row.get("target_action", ""))
    allocation_status = safe_upper(row.get("allocation_status", ""))
    constraint_checks = safe_upper(row.get("constraint_checks", ""))

    if not target_action and not allocation_status:
        return "NOT_AVAILABLE", "MISSING_ACTION_INPUTS"
    if "VALUATION" in target_action or "VALUATION" in allocation_status or "VALUATION" in constraint_checks:
        return "WAIT_FOR_VALUATION", "VALUATION_REVIEW_OR_MISSING"
    if "COVERAGE" in target_action or "COVERAGE" in allocation_status or "COVERAGE" in constraint_checks:
        return "WAIT_FOR_COVERAGE", "COVERAGE_REVIEW_OR_MISSING"
    if target_action in {"REVIEW_CORE_DATA", "REVIEW_FCF_DATA"}:
        return "REVIEW_DATA", f"LEGACY_TARGET_ACTION_{target_action}"
    if allocation_status in {"BLOCKED", "NOT_ELIGIBLE"}:
        return "NOT_READY", f"LEGACY_ALLOCATION_STATUS_{allocation_status}"
    if target_action in {"DO_NOT_BUY", "NOT_ELIGIBLE"}:
        return "NOT_READY", f"LEGACY_TARGET_ACTION_{target_action}"
    if target_action in {"HOLD_CASH", "HOLD"}:
        return "NO_ACTION", f"LEGACY_TARGET_ACTION_{target_action}"
    if target_action in {"TOP_UP", "BUY", "ADD"}:
        return "ADD_CANDIDATE_REVIEW", f"LEGACY_TARGET_ACTION_{target_action}_REQUIRES_REVIEW"
    return "REVIEW_DATA", "UNMAPPED_LEGACY_ACTION_REVIEW_REQUIRED"


def build_compatibility_rows(monthly_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in monthly_rows:
        monthly_action, reason_code = derive_monthly_action(row)
        schema_status = "PASS" if monthly_action in MONTHLY_ACTION_VALUES and monthly_action not in FORBIDDEN_MONTHLY_ACTION_VALUES else "REVIEW"
        rows.append(
            {
                "rank": str(row.get("rank", "") or ""),
                "ticker": str(row.get("ticker", "") or ""),
                "company_name": str(row.get("company_name", "") or ""),
                "legacy_target_action": str(row.get("target_action", "") or ""),
                "legacy_allocation_status": str(row.get("allocation_status", "") or ""),
                "monthly_action": monthly_action,
                "monthly_action_reason_code": reason_code,
                "schema_status": schema_status,
                "suggested_buy_amount_eur": str(row.get("suggested_buy_amount_eur", "") or ""),
                "constraint_checks": str(row.get("constraint_checks", "") or ""),
            }
        )
    return sorted(rows, key=lambda item: (item["rank"].zfill(8), item["ticker"], item["monthly_action"]))


def build_summary(monthly_rows: list[dict[str, str]], compatibility_rows: list[dict[str, str]], warnings: list[str]) -> list[dict[str, str]]:
    monthly_fields = set(monthly_rows[0].keys()) if monthly_rows else set()
    action_counts = Counter(row["monthly_action"] for row in compatibility_rows)
    target_counts = Counter(safe_upper(row.get("target_action", "")) or "BLANK" for row in monthly_rows)
    allocation_counts = Counter(safe_upper(row.get("allocation_status", "")) or "BLANK" for row in monthly_rows)
    forbidden_rows = [row for row in compatibility_rows if row["monthly_action"] in FORBIDDEN_MONTHLY_ACTION_VALUES]
    schema_review_rows = [row for row in compatibility_rows if row["schema_status"] != "PASS"]
    drift_resolved = bool(compatibility_rows) and not forbidden_rows and not schema_review_rows

    rows: list[dict[str, str]] = []

    def add(metric: str, value: object, notes: str) -> None:
        rows.append({"metric": metric, "value": str(value), "notes": notes})

    add("implementation_path", "COMPANION_ADAPTER", "Monthly output is not modified; neutral compatibility artifact is generated.")
    add("monthly_rows_total", len(monthly_rows), "Rows read from monthly ranking input.")
    add("compatibility_rows_total", len(compatibility_rows), "Rows written to compatibility artifact.")
    add("monthly_has_target_action", bool_text("target_action" in monthly_fields), "Existing monthly schema field.")
    add("monthly_has_allocation_status", bool_text("allocation_status" in monthly_fields), "Existing monthly schema field.")
    add("monthly_has_monthly_action", bool_text("monthly_action" in monthly_fields), "Existing monthly schema field.")
    add("monthly_action_compatibility_available", bool_text(bool(compatibility_rows)), "Neutral monthly_action is available via companion artifact.")
    add("monthly_schema_drift_resolved", bool_text(drift_resolved), "True when compatibility rows exist and monthly_action values are allowed.")
    add("forbidden_monthly_action_values_total", len(forbidden_rows), "Forbidden advice/order action values in new monthly_action field.")
    add("schema_review_rows_total", len(schema_review_rows), "Compatibility rows that failed schema guardrail.")
    for action, count in sorted(action_counts.items()):
        add(f"monthly_action__{action}", count, "Neutral monthly_action count.")
    for action, count in sorted(target_counts.items()):
        add(f"legacy_target_action__{action}", count, "Legacy/internal target_action count from monthly ranking input.")
    for status, count in sorted(allocation_counts.items()):
        add(f"legacy_allocation_status__{status}", count, "Legacy/internal allocation_status count from monthly ranking input.")
    add("warnings_total", len(warnings), "Missing input warnings.")
    return sorted(rows, key=lambda row: row["metric"])


def summary_map(rows: list[dict[str, str]]) -> dict[str, str]:
    return {row["metric"]: row["value"] for row in rows}


def render_report(
    *,
    monthly_input: str,
    compatibility_output: str,
    summary_output: str,
    summary_rows: list[dict[str, str]],
    compatibility_rows: list[dict[str, str]],
    warnings: tuple[str, ...],
) -> str:
    summary = summary_map(summary_rows)
    action_counts = {row["metric"].replace("monthly_action__", ""): row["value"] for row in summary_rows if row["metric"].startswith("monthly_action__")}
    lines = [
        "# Personal Monthly Action Schema Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## 1. Executive Summary",
        "",
        f"- Implementation path: `{summary.get('implementation_path', 'NOT_AVAILABLE')}`",
        f"- Monthly rows: `{summary.get('monthly_rows_total', '0')}`",
        f"- Compatibility rows: `{summary.get('compatibility_rows_total', '0')}`",
        f"- Monthly schema drift resolved: `{summary.get('monthly_schema_drift_resolved', 'False')}`",
        f"- Forbidden monthly_action values: `{summary.get('forbidden_monthly_action_values_total', '0')}`",
        "",
        "This report creates a neutral `monthly_action` compatibility layer from existing monthly artifacts only. It does not change scores, formulas, fundamentals values, allocations, or ranking order.",
        "",
        "## 2. Input Artifacts",
        "",
        f"- Monthly input: `{safe_display_path(monthly_input)}`",
        f"- Compatibility output: `{safe_display_path(compatibility_output)}`",
        f"- Summary output: `{safe_display_path(summary_output)}`",
        "",
        "## 3. Existing Monthly Schema",
        "",
        f"- Has `target_action`: `{summary.get('monthly_has_target_action', 'False')}`",
        f"- Has `allocation_status`: `{summary.get('monthly_has_allocation_status', 'False')}`",
        f"- Has `monthly_action`: `{summary.get('monthly_has_monthly_action', 'False')}`",
        "",
        "`target_action` and `allocation_status` remain legacy/internal compatibility fields. The new product-facing action language is the neutral `monthly_action` field in the companion artifact.",
        "",
        "## 4. Chosen Implementation Path",
        "",
        "Option B: companion/adapter artifact. This avoids changing the dirty pre-existing monthly ranking engine or the legacy monthly CSV contract in this patch.",
        "",
        "## 5. Mapping Rules",
        "",
        "| Legacy condition | Neutral monthly_action |",
        "| --- | --- |",
        "| valuation review/missing in action, allocation, or constraints | `WAIT_FOR_VALUATION` |",
        "| coverage review/missing in action, allocation, or constraints | `WAIT_FOR_COVERAGE` |",
        "| `REVIEW_CORE_DATA` or `REVIEW_FCF_DATA` | `REVIEW_DATA` |",
        "| blocked/not eligible allocation | `NOT_READY` |",
        "| legacy do-not-enter-candidate action | `NOT_READY` |",
        "| cash/hold state | `NO_ACTION` |",
        "| legacy add/top-up candidate | `ADD_CANDIDATE_REVIEW` |",
        "| missing inputs | `NOT_AVAILABLE` |",
        "",
        "## 6. Generated Monthly Action Values",
        "",
        "| monthly_action | Count |",
        "| --- | ---: |",
    ]
    for action, count in sorted(action_counts.items()):
        lines.append(f"| `{action}` | {count} |")
    lines.extend(
        [
            "",
            "## 7. Advice-Language Guardrail",
            "",
            "The new `monthly_action` field permits only neutral review/wait/block/no-action states. Legacy/internal filenames and columns may still contain historical wording, but no new product-facing action value uses order, execution, trade, or direct advice language.",
            "",
            "## 8. Reconciliation Impact",
            "",
            "Reconciliation can treat `MONTHLY_SCHEMA_DRIFT` as resolved when `monthly_action_compatibility_available=True`, `monthly_schema_drift_resolved=True`, and forbidden monthly action count is zero.",
            "",
            "## 9. Remaining Demo Readiness Blockers",
            "",
            "- Artifact drift, sample watchlist input, valuation gaps, core-data review states, and provenance gaps remain outside this schema patch.",
            "",
            "## 10. Remaining Decision Readiness Blockers",
            "",
            "- This patch does not make any holding decision-ready. It only stabilizes neutral action terminology for downstream consumers.",
            "",
            "## 11. Recommended Next Patch",
            "",
            "`PATCH / WATCHLIST SAMPLE INPUT GATE / DEMO_ONLY LABELING / NO VALUE CHANGES`",
        ]
    )
    if warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in warnings:
            lines.append(f"- `{warning}`")
    # Include a tiny deterministic sample without dumping sensitive inputs.
    if compatibility_rows:
        lines.extend(["", "## Compatibility Sample", "", "| rank | ticker | monthly_action | reason |", "| --- | --- | --- | --- |"])
        for row in compatibility_rows[:5]:
            lines.append(f"| `{row['rank']}` | `{row['ticker']}` | `{row['monthly_action']}` | `{row['monthly_action_reason_code']}` |")
    return "\n".join(lines) + "\n"


def run_personal_monthly_action_schema(
    *,
    monthly_input: str = DEFAULT_MONTHLY_INPUT,
    compatibility_output: str = DEFAULT_COMPATIBILITY_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> MonthlyActionSchemaResult:
    monthly_rows, warnings = optional_csv_rows(monthly_input, "monthly")
    compatibility_rows = build_compatibility_rows(monthly_rows)
    summary_rows = build_summary(monthly_rows, compatibility_rows, warnings)
    compatibility_path = write_csv_rows(compatibility_output, COMPATIBILITY_FIELDS, compatibility_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_report(
            monthly_input=monthly_input,
            compatibility_output=compatibility_output,
            summary_output=summary_output,
            summary_rows=summary_rows,
            compatibility_rows=compatibility_rows,
            warnings=tuple(warnings),
        ),
        encoding="utf-8",
    )
    return MonthlyActionSchemaResult(
        compatibility_output=compatibility_path,
        summary_output=summary_path,
        report_output=report_path,
        compatibility_rows=compatibility_rows,
        summary_rows=summary_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a neutral monthly_action compatibility artifact from existing monthly ranking output.")
    parser.add_argument("--monthly-input", default=DEFAULT_MONTHLY_INPUT)
    parser.add_argument("--compatibility-output", default=DEFAULT_COMPATIBILITY_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_monthly_action_schema(
        monthly_input=args.monthly_input,
        compatibility_output=args.compatibility_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    summary = summary_map(result.summary_rows)
    print(f"compatibility_output={result.compatibility_output}")
    print(f"summary_output={result.summary_output}")
    print(f"report_output={result.report_output}")
    print(f"monthly_rows_total={summary.get('monthly_rows_total', '0')}")
    print(f"monthly_schema_drift_resolved={summary.get('monthly_schema_drift_resolved', 'False')}")
    print(f"forbidden_monthly_action_values_total={summary.get('forbidden_monthly_action_values_total', '0')}")
    print(f"warnings_total={len(result.warnings)}")


if __name__ == "__main__":
    main()
