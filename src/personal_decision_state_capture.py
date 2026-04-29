from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from src.common import ensure_parent_dir, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_OUTPUT = "data/processed/personal_decision_state_capture.csv"
DEFAULT_REPORT = f"reports/{date.today().isoformat()}/personal_decision_state_capture_report.md"

FIELDS = [
    "decision_id",
    "decision_date",
    "decision_scope",
    "asset_id",
    "ticker",
    "asset_name",
    "asset_type",
    "proposed_action",
    "human_decision",
    "decision_status",
    "reasoning_3_sentences",
    "dominant_uncertainty",
    "benchmark_alternative",
    "benchmark_ref_or_label",
    "review_date",
    "created_at",
    "run_id",
    "manifest_path",
    "primary_report_path",
    "source_snapshot_date",
    "accounting_basis",
    "policy_ref",
    "policy_version",
    "operator_state",
    "decision_pressure",
    "market_context_tag",
    "conviction",
    "cash_context",
    "source_paths",
    "notes",
]

MANUAL_REQUIRED_FIELDS = [
    "decision_scope",
    "proposed_action",
    "human_decision",
    "decision_status",
    "reasoning_3_sentences",
    "dominant_uncertainty",
    "benchmark_alternative",
]

REPLAY_REFERENCE_FIELDS = [
    "run_id",
    "manifest_path",
    "primary_report_path",
    "source_snapshot_date",
    "policy_ref",
]

UNKNOWN_AUTO_FIELDS = ["asset_id", "ticker", "asset_name", "asset_type"]

ENUMS = {
    "decision_scope": {"ASSET", "PORTFOLIO", "CASH", "MONTHLY_REVIEW", "WATCHLIST", "UNKNOWN"},
    "proposed_action": {
        "BUY_REVIEW",
        "HOLD_REVIEW",
        "WAIT_FOR_EVIDENCE",
        "WAIT_FOR_PRICE",
        "WAIT_FOR_REVIEW",
        "RESEARCH_MORE",
        "NO_ACTION",
        "SKIP_MONTH",
        "CASH_DEPLOYMENT",
        "UNKNOWN",
    },
    "human_decision": {"PENDING_REVIEW", "APPROVED_FOR_MANUAL_ACTION", "REJECTED", "DEFERRED", "NO_ACTION", "NOT_REVIEWED"},
    "decision_status": {"OPEN", "BLOCKED", "REVIEW_SCHEDULED", "CLOSED", "NOT_AVAILABLE", "INVALID"},
    "dominant_uncertainty": {
        "MISSING_DATA",
        "VALUATION",
        "PORTFOLIO_FIT",
        "CASH_CONTEXT",
        "TAX_CONTEXT",
        "EVIDENCE_QUALITY",
        "BEHAVIOURAL_RISK",
        "UNKNOWN",
    },
    "benchmark_alternative": {
        "CASH",
        "CORE_ETF",
        "DIVIDEND_GROWTH_ETF",
        "QUALITY_ETF",
        "EXISTING_HOLDING",
        "WATCHLIST_CANDIDATE",
        "NO_ACTION",
        "UNKNOWN",
    },
    "accounting_basis": {"SNAPSHOT_ONLY", "PARTIAL_LEDGER", "RECONCILED_LEDGER", "UNKNOWN"},
    "cash_context": {"AVAILABLE_CASH", "RESERVED_CASH", "TAX_RESERVE", "NO_CASH", "UNKNOWN"},
    "operator_state": {"NORMAL", "MARKET_STRESS", "DRAWDOWN_STRESS", "EUPHORIA", "TIME_CONSTRAINED", "UNCERTAIN", "NOT_RECORDED"},
    "decision_pressure": {"NORMAL", "TIME_CONSTRAINED", "MARKET_STRESS", "UNKNOWN"},
}

V1_EXCLUSIONS = [
    "trading or broker/order execution",
    "outcome attribution",
    "benchmark return calculation",
    "tax lot tracking",
    "FX attribution",
    "simulation",
    "backtesting",
    "policy feedback",
    "Portfolio Event Ledger",
]


@dataclass(frozen=True)
class DecisionCaptureResult:
    output_path: Path
    report_path: Path
    rows: list[dict[str, str]]
    invalid_rows: list[dict[str, str]]
    missing_replay_references: list[dict[str, str]]


def is_blank_row(row: dict[str, str]) -> bool:
    return not any(str(value or "").strip() for value in row.values())


def normalize_enum(value: str) -> str:
    return safe_upper(value)


def requires_review_date(row: dict[str, str]) -> bool:
    action = safe_upper(row.get("proposed_action", ""))
    status = safe_upper(row.get("decision_status", ""))
    return action == "HOLD_REVIEW" or action.startswith("WAIT_") or action == "RESEARCH_MORE" or status == "REVIEW_SCHEDULED"


def parse_iso_date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def load_input_rows(input_path: str | None) -> list[dict[str, str]]:
    if not input_path:
        return []
    path = resolve_repo_path(input_path)
    if not path.exists():
        return []
    return [row for row in read_csv_rows(path) if not is_blank_row(row)]


def apply_defaults(
    raw_rows: list[dict[str, str]],
    *,
    report_date: date,
    run_id: str = "",
    manifest_path: str = "",
    primary_report_path: str = "",
    source_snapshot_date: str = "",
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, raw in enumerate(raw_rows, start=1):
        row = {field: str(raw.get(field, "") or "").strip() for field in FIELDS}
        row["decision_date"] = row["decision_date"] or report_date.isoformat()
        row["decision_id"] = row["decision_id"] or f"DECISION_{row['decision_date'].replace('-', '')}_{index:04d}"
        row["created_at"] = row["created_at"] or f"{row['decision_date']}T00:00:00"
        row["run_id"] = row["run_id"] or run_id or "MISSING_REFERENCE"
        row["manifest_path"] = row["manifest_path"] or manifest_path or "MISSING_REFERENCE"
        row["primary_report_path"] = row["primary_report_path"] or primary_report_path or "MISSING_REFERENCE"
        row["source_snapshot_date"] = row["source_snapshot_date"] or source_snapshot_date or "MISSING_REFERENCE"
        row["policy_ref"] = row["policy_ref"] or "MISSING_REFERENCE"
        for field in UNKNOWN_AUTO_FIELDS:
            row[field] = row[field] or "UNKNOWN"
        row["accounting_basis"] = normalize_enum(row["accounting_basis"] or "SNAPSHOT_ONLY")
        row["operator_state"] = normalize_enum(row["operator_state"] or "NOT_RECORDED")
        row["decision_pressure"] = normalize_enum(row["decision_pressure"] or "UNKNOWN")
        row["cash_context"] = normalize_enum(row["cash_context"] or "UNKNOWN")
        for field in ("decision_scope", "proposed_action", "human_decision", "decision_status", "dominant_uncertainty", "benchmark_alternative"):
            row[field] = normalize_enum(row[field])
        row["benchmark_ref_or_label"] = row["benchmark_ref_or_label"] or row["benchmark_alternative"] or "MISSING_REFERENCE"
        rows.append(row)
    return rows


def row_validation_reasons(row: dict[str, str]) -> list[str]:
    reasons: list[str] = []
    for field in MANUAL_REQUIRED_FIELDS:
        if not str(row.get(field, "")).strip():
            reasons.append(f"MISSING_REQUIRED:{field}")
    for field, allowed in ENUMS.items():
        value = safe_upper(row.get(field, ""))
        if value and value not in allowed:
            reasons.append(f"INVALID_ENUM:{field}={value}")
    if requires_review_date(row) and not row.get("review_date", ""):
        reasons.append("MISSING_CONDITIONAL:review_date")
    if row.get("review_date", "") and parse_iso_date(row["review_date"]) is None:
        reasons.append("INVALID_DATE:review_date")
    return reasons


def invalid_row_records(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    invalid: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=2):
        reasons = row_validation_reasons(row)
        if reasons:
            invalid.append(
                {
                    "csv_row_number": str(index),
                    "decision_id": row.get("decision_id", ""),
                    "ticker": row.get("ticker", ""),
                    "decision_scope": row.get("decision_scope", ""),
                    "proposed_action": row.get("proposed_action", ""),
                    "validation_reasons": ";".join(reasons),
                }
            )
    return invalid


def missing_replay_reference_records(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for row in rows:
        fields = [
            field
            for field in REPLAY_REFERENCE_FIELDS
            if row.get(field, "") in {"", "UNKNOWN", "MISSING_REFERENCE"}
        ]
        if fields:
            missing.append(
                {
                    "decision_id": row.get("decision_id", ""),
                    "ticker": row.get("ticker", ""),
                    "missing_reference_fields": ",".join(fields),
                }
            )
    return missing


def overdue_rows(rows: list[dict[str, str]], report_date: date) -> list[dict[str, str]]:
    overdue: list[dict[str, str]] = []
    for row in rows:
        review = parse_iso_date(row.get("review_date", ""))
        if review is not None and review < report_date and safe_upper(row.get("decision_status", "")) != "CLOSED":
            overdue.append(row)
    return overdue


def table_lines(rows: Iterable[dict[str, str]]) -> list[str]:
    lines = [
        "| decision_id | ticker | proposed_action | human_decision | decision_status | review_date |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    items = list(rows)
    if not items:
        lines.append("| none |  |  |  |  |  |")
        return lines
    for row in items:
        lines.append(
            f"| {row.get('decision_id', '')} | {row.get('ticker', '')} | {row.get('proposed_action', '')} | "
            f"{row.get('human_decision', '')} | {row.get('decision_status', '')} | {row.get('review_date', '')} |"
        )
    return lines


def write_report(
    report_path: str,
    rows: list[dict[str, str]],
    invalid_rows: list[dict[str, str]],
    missing_refs: list[dict[str, str]],
    *,
    input_path: str | None,
    output_path: Path,
    report_date: date,
) -> Path:
    status_counts = Counter(row["decision_status"] for row in rows)
    open_rows = [row for row in rows if row["decision_status"] == "OPEN"]
    blocked_rows = [row for row in rows if row["decision_status"] == "BLOCKED"]
    no_action_rows = [row for row in rows if row["proposed_action"] in {"NO_ACTION", "SKIP_MONTH"} or row["human_decision"] == "NO_ACTION"]
    wait_review_rows = [row for row in rows if row["proposed_action"].startswith("WAIT_") or row["proposed_action"] == "RESEARCH_MORE" or row["decision_status"] == "REVIEW_SCHEDULED"]
    overdue = overdue_rows(rows, report_date)
    state = "EMPTY_STATE" if not rows else ("INVALID_ROWS_PRESENT" if invalid_rows else "OK")
    lines = [
        "# Personal Decision State Capture Report",
        "",
        "This is a research and decision-support artifact. `APPROVED_FOR_MANUAL_ACTION` is not order execution.",
        "",
        "## Summary",
        "",
        f"- capture_status: {state}",
        f"- decision_rows: {len(rows)}",
        f"- invalid_rows: {len(invalid_rows)}",
        f"- missing_replay_reference_rows: {len(missing_refs)}",
        "",
        "## Row Counts",
        "",
    ]
    if status_counts:
        lines.extend(f"- {key}: {status_counts[key]}" for key in sorted(status_counts))
    else:
        lines.append("- NOT_AVAILABLE: 0")
    sections = [
        ("Open Decisions", open_rows),
        ("Blocked Decisions", blocked_rows),
        ("No-Action Entries", no_action_rows),
        ("Wait / Review Scheduled Entries", wait_review_rows),
        ("Overdue Review Items", overdue),
    ]
    for title, section_rows in sections:
        lines.extend(["", f"## {title}", ""])
        lines.extend(table_lines(section_rows))
    lines.extend(["", "## Missing Replay References", ""])
    if missing_refs:
        lines.extend(
            f"- `{row['decision_id']}` `{row['ticker']}` missing `{row['missing_reference_fields']}`"
            for row in missing_refs
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Invalid Rows", ""])
    if invalid_rows:
        lines.extend(
            f"- csv_row_number={row['csv_row_number']} decision_id=`{row['decision_id']}` reasons=`{row['validation_reasons']}`"
            for row in invalid_rows
        )
    else:
        lines.append("- none")
    lines.extend(["", "## V1 Exclusions", ""])
    lines.extend(f"- no {item}" for item in V1_EXCLUSIONS)
    lines.extend(
        [
            "",
            "No trading, broker/order execution, outcome attribution, benchmark return calculation, tax lot tracking, FX attribution, simulation or backtesting is performed.",
            "",
            "## Input / Output Paths",
            "",
            f"- input: `{input_path or 'NOT_PROVIDED'}`",
            f"- output: `{output_path.as_posix()}`",
            f"- report: `{resolve_repo_path(report_path).as_posix()}`",
        ]
    )
    path = ensure_parent_dir(report_path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_decision_state_capture(
    *,
    input_path: str | None = None,
    output: str = DEFAULT_OUTPUT,
    report: str = DEFAULT_REPORT,
    run_id: str = "",
    manifest_path: str = "",
    primary_report_path: str = "",
    source_snapshot_date: str = "",
    report_date: str | None = None,
) -> DecisionCaptureResult:
    effective_date = date.fromisoformat(report_date) if report_date else date.today()
    raw_rows = load_input_rows(input_path)
    rows = apply_defaults(
        raw_rows,
        report_date=effective_date,
        run_id=run_id,
        manifest_path=manifest_path,
        primary_report_path=primary_report_path,
        source_snapshot_date=source_snapshot_date,
    )
    invalid = invalid_row_records(rows)
    missing_refs = missing_replay_reference_records(rows)
    output_path = write_csv_rows(output, FIELDS, rows)
    report_path = write_report(report, rows, invalid, missing_refs, input_path=input_path, output_path=output_path, report_date=effective_date)
    return DecisionCaptureResult(output_path, report_path, rows, invalid, missing_refs)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or validate the personal decision state capture artifact.")
    parser.add_argument("--input", default="", help="Optional existing decision capture CSV to validate/normalize.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--manifest-path", default="")
    parser.add_argument("--primary-report-path", default="")
    parser.add_argument("--source-snapshot-date", default="")
    parser.add_argument("--report-date", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_decision_state_capture(
        input_path=args.input or None,
        output=args.output,
        report=args.report,
        run_id=args.run_id,
        manifest_path=args.manifest_path,
        primary_report_path=args.primary_report_path,
        source_snapshot_date=args.source_snapshot_date,
        report_date=args.report_date or None,
    )


if __name__ == "__main__":
    main()
