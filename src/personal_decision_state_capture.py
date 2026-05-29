from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
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

AUTO_SYSTEM_WARNING_FIELDS = [
    "run_id",
    "manifest_path",
    "primary_report_path",
    "source_snapshot_date",
    "policy_ref",
    "asset_id",
    "ticker",
    "asset_name",
    "asset_type",
    "accounting_basis",
    "benchmark_ref_or_label",
]

ENUMS = {
    "decision_scope": {"ASSET", "HOLDING_REVIEW", "PORTFOLIO", "CASH", "MONTHLY_REVIEW", "WATCHLIST", "UNKNOWN"},
    "proposed_action": {
        "ADD_REVIEW",
        "HOLD_REVIEW",
        "TRIM_REVIEW",
        "EXIT_REVIEW",
        "WAIT_FOR_EVIDENCE",
        "WAIT_FOR_PRICE",
        "WAIT_FOR_REVIEW",
        "RESEARCH_MORE",
        "REJECT_CANDIDATE",
        "NO_ACTION",
        "SKIP_MONTH",
        "CASH_DEPLOYMENT",
        "UNKNOWN",
    },
    "human_decision": {"PENDING_REVIEW", "APPROVED_FOR_MANUAL_ACTION", "REJECTED", "DEFERRED", "NO_ACTION", "NOT_REVIEWED"},
    "decision_status": {"OPEN", "BLOCKED", "REVIEW_SCHEDULED", "CLOSED", "NOT_AVAILABLE", "INVALID", "INSUFFICIENT_EVIDENCE", "SUPERSEDED"},
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
        "WATCHLIST_TOP_CANDIDATE",
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

PRIVATE_PATH_MARKERS = [
    "data/raw/private/",
    "data\\raw\\private\\",
    "kontoauszug",
    "depotauszug",
]


@dataclass(frozen=True)
class DecisionCaptureResult:
    output_path: Path
    report_path: Path
    rows: list[dict[str, str]]
    invalid_rows: list[dict[str, str]]
    missing_replay_references: list[dict[str, str]]
    unresolved_auto_system_fields: list[dict[str, str]]
    input_status: str


@dataclass(frozen=True)
class CaptureAppendResult:
    output_path: Path
    report_path: Path
    appended_decision_id: str
    rows: list[dict[str, str]]
    validation_result: DecisionCaptureResult


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


def repo_relative_stored_path(value: str, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    normalized_for_guard = text.replace("\\", "/").lower()
    if any(marker in normalized_for_guard for marker in PRIVATE_PATH_MARKERS):
        raise ValueError(f"{field_name} must not reference private raw or broker document paths: {text}")
    path = Path(text)
    if not path.is_absolute():
        return path.as_posix()
    root = resolve_repo_path(".").resolve()
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a repo-relative path, got absolute local path: {text}") from exc


def normalize_source_paths(value: str) -> str:
    parts = [part.strip() for part in str(value or "").replace(",", ";").split(";") if part.strip()]
    return ";".join(repo_relative_stored_path(part, field_name="source_paths") for part in parts)


def normalize_stored_path_fields(row: dict[str, str]) -> dict[str, str]:
    normalized = dict(row)
    normalized["manifest_path"] = repo_relative_stored_path(normalized.get("manifest_path", ""), field_name="manifest_path")
    normalized["primary_report_path"] = repo_relative_stored_path(normalized.get("primary_report_path", ""), field_name="primary_report_path")
    normalized["source_paths"] = normalize_source_paths(normalized.get("source_paths", ""))
    return normalized


def load_input_rows(input_path: str | None) -> tuple[list[dict[str, str]], str]:
    if not input_path:
        return [], "NOT_PROVIDED"
    path = resolve_repo_path(input_path)
    if not path.exists():
        return [], "MISSING_INPUT_PATH"
    return [row for row in read_csv_rows(path) if not is_blank_row(row)], "LOADED"


def load_existing_output_rows(output_path: str) -> list[dict[str, str]]:
    path = resolve_repo_path(output_path)
    if not path.exists():
        return []
    return [{field: str(row.get(field, "") or "").strip() for field in FIELDS} for row in read_csv_rows(path) if not is_blank_row(row)]


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


def next_decision_id(rows: list[dict[str, str]], decision_date: str) -> str:
    date_token = decision_date.replace("-", "")
    pattern = re.compile(rf"^DECISION_{re.escape(date_token)}_(\d{{4}})$")
    max_sequence = 0
    used = {str(row.get("decision_id", "")).strip() for row in rows}
    for row in rows:
        match = pattern.match(str(row.get("decision_id", "")).strip())
        if match:
            max_sequence = max(max_sequence, int(match.group(1)))
    sequence = max_sequence + 1
    while True:
        candidate = f"DECISION_{date_token}_{sequence:04d}"
        if candidate not in used:
            return candidate
        sequence += 1


def build_capture_row(
    *,
    existing_rows: list[dict[str, str]],
    decision_id: str = "",
    decision_date: str,
    decision_scope: str,
    asset_id: str = "",
    ticker: str = "",
    asset_name: str = "",
    asset_type: str = "",
    proposed_action: str,
    human_decision: str,
    decision_status: str,
    reasoning_3_sentences: str,
    dominant_uncertainty: str,
    benchmark_alternative: str,
    benchmark_ref_or_label: str = "",
    review_date: str = "",
    run_id: str = "",
    manifest_path: str = "",
    primary_report_path: str = "",
    source_snapshot_date: str = "",
    accounting_basis: str = "",
    policy_ref: str = "",
    policy_version: str = "",
    operator_state: str = "",
    decision_pressure: str = "",
    market_context_tag: str = "",
    conviction: str = "",
    cash_context: str = "",
    source_paths: str = "",
    notes: str = "",
) -> dict[str, str]:
    effective_decision_date = decision_date.strip()
    if parse_iso_date(effective_decision_date) is None:
        raise ValueError(f"decision_date must be ISO YYYY-MM-DD, got: {decision_date}")
    row = {
        "decision_id": decision_id.strip() or next_decision_id(existing_rows, effective_decision_date),
        "decision_date": effective_decision_date,
        "decision_scope": normalize_enum(decision_scope),
        "asset_id": asset_id.strip() or "UNKNOWN",
        "ticker": ticker.strip() or "UNKNOWN",
        "asset_name": asset_name.strip() or "UNKNOWN",
        "asset_type": asset_type.strip() or "UNKNOWN",
        "proposed_action": normalize_enum(proposed_action),
        "human_decision": normalize_enum(human_decision),
        "decision_status": normalize_enum(decision_status),
        "reasoning_3_sentences": reasoning_3_sentences.strip(),
        "dominant_uncertainty": normalize_enum(dominant_uncertainty),
        "benchmark_alternative": normalize_enum(benchmark_alternative),
        "benchmark_ref_or_label": benchmark_ref_or_label.strip() or normalize_enum(benchmark_alternative),
        "review_date": review_date.strip(),
        "created_at": f"{effective_decision_date}T00:00:00",
        "run_id": run_id.strip() or "MISSING_REFERENCE",
        "manifest_path": manifest_path.strip() or "MISSING_REFERENCE",
        "primary_report_path": primary_report_path.strip() or "MISSING_REFERENCE",
        "source_snapshot_date": source_snapshot_date.strip() or "MISSING_REFERENCE",
        "accounting_basis": normalize_enum(accounting_basis or "SNAPSHOT_ONLY"),
        "policy_ref": policy_ref.strip() or "MISSING_REFERENCE",
        "policy_version": policy_version.strip(),
        "operator_state": normalize_enum(operator_state or "NOT_RECORDED"),
        "decision_pressure": normalize_enum(decision_pressure or "UNKNOWN"),
        "market_context_tag": market_context_tag.strip(),
        "conviction": conviction.strip(),
        "cash_context": normalize_enum(cash_context or "UNKNOWN"),
        "source_paths": source_paths.strip(),
        "notes": notes.strip(),
    }
    return normalize_stored_path_fields(row)


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
    if row.get("decision_date", "") and parse_iso_date(row["decision_date"]) is None:
        reasons.append("INVALID_DATE:decision_date")
    return reasons


def duplicate_decision_ids(rows: list[dict[str, str]]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in rows:
        decision_id = str(row.get("decision_id", "")).strip()
        if not decision_id:
            continue
        if decision_id in seen:
            duplicates.add(decision_id)
        seen.add(decision_id)
    return sorted(duplicates)


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


def validate_journal_rows(rows: list[dict[str, str]]) -> None:
    duplicates = duplicate_decision_ids(rows)
    if duplicates:
        raise ValueError(f"duplicate decision_id value(s): {', '.join(duplicates)}")
    invalid = invalid_row_records(rows)
    if invalid:
        details = "; ".join(f"row {row['csv_row_number']} {row['validation_reasons']}" for row in invalid)
        raise ValueError(f"decision capture validation failed: {details}")


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


def unresolved_auto_system_field_records(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    unresolved: list[dict[str, str]] = []
    for row in rows:
        fields = [
            field
            for field in AUTO_SYSTEM_WARNING_FIELDS
            if row.get(field, "") in {"", "UNKNOWN", "MISSING_REFERENCE"}
        ]
        if fields:
            unresolved.append(
                {
                    "decision_id": row.get("decision_id", ""),
                    "ticker": row.get("ticker", ""),
                    "unresolved_auto_system_fields": ",".join(fields),
                }
            )
    return unresolved


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
    unresolved_auto_system_fields: list[dict[str, str]],
    *,
    input_path: str | None,
    input_status: str,
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
        f"- unresolved_auto_system_field_rows: {len(unresolved_auto_system_fields)}",
        f"- input_status: {input_status}",
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
    lines.extend(["", "## Unresolved Auto/System Fields", ""])
    if unresolved_auto_system_fields:
        lines.extend(
            f"- `{row['decision_id']}` `{row['ticker']}` unresolved `{row['unresolved_auto_system_fields']}`"
            for row in unresolved_auto_system_fields
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
            f"- input_status: `{input_status}`",
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
    fail_on_invalid: bool = False,
) -> DecisionCaptureResult:
    effective_date = date.fromisoformat(report_date) if report_date else date.today()
    raw_rows, input_status = load_input_rows(input_path)
    rows = apply_defaults(
        raw_rows,
        report_date=effective_date,
        run_id=run_id,
        manifest_path=manifest_path,
        primary_report_path=primary_report_path,
        source_snapshot_date=source_snapshot_date,
    )
    invalid = invalid_row_records(rows)
    duplicates = duplicate_decision_ids(rows)
    if duplicates:
        invalid.append(
            {
                "csv_row_number": "MULTIPLE",
                "decision_id": ",".join(duplicates),
                "ticker": "",
                "decision_scope": "",
                "proposed_action": "",
                "validation_reasons": f"DUPLICATE_DECISION_ID:{','.join(duplicates)}",
            }
        )
    if fail_on_invalid and invalid:
        details = "; ".join(f"{row['decision_id']} {row['validation_reasons']}" for row in invalid)
        raise ValueError(f"decision capture validation failed: {details}")
    missing_refs = missing_replay_reference_records(rows)
    unresolved_auto_system_fields = unresolved_auto_system_field_records(rows)
    output_path = write_csv_rows(output, FIELDS, rows)
    report_path = write_report(
        report,
        rows,
        invalid,
        missing_refs,
        unresolved_auto_system_fields,
        input_path=input_path,
        input_status=input_status,
        output_path=output_path,
        report_date=effective_date,
    )
    return DecisionCaptureResult(output_path, report_path, rows, invalid, missing_refs, unresolved_auto_system_fields, input_status)


def append_decision_capture(
    *,
    output: str = DEFAULT_OUTPUT,
    report: str = DEFAULT_REPORT,
    report_date: str | None = None,
    **capture_fields: str,
) -> CaptureAppendResult:
    existing_rows = load_existing_output_rows(output)
    existing_ids = {str(row.get("decision_id", "")).strip() for row in existing_rows if str(row.get("decision_id", "")).strip()}
    row = build_capture_row(existing_rows=existing_rows, **capture_fields)
    if row["decision_id"] in existing_ids:
        raise ValueError(f"duplicate decision_id value: {row['decision_id']}")
    candidate_rows = existing_rows + [row]
    validate_journal_rows(candidate_rows)
    output_path = write_csv_rows(output, FIELDS, candidate_rows)
    validation = run_decision_state_capture(
        input_path=str(output_path),
        output=output,
        report=report,
        report_date=report_date or row["decision_date"],
        fail_on_invalid=True,
    )
    return CaptureAppendResult(output_path, validation.report_path, row["decision_id"], candidate_rows, validation)


def add_common_io_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", default="", help="Optional existing decision capture CSV to validate/normalize.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--manifest-path", default="")
    parser.add_argument("--primary-report-path", default="")
    parser.add_argument("--source-snapshot-date", default="")
    parser.add_argument("--report-date", default="")


def add_capture_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--decision-id", default="")
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--decision-scope", required=True)
    parser.add_argument("--asset-id", default="")
    parser.add_argument("--ticker", default="")
    parser.add_argument("--asset-name", default="")
    parser.add_argument("--asset-type", default="")
    parser.add_argument("--proposed-action", required=True)
    parser.add_argument("--human-decision", required=True)
    parser.add_argument("--decision-status", required=True)
    parser.add_argument("--reasoning-3-sentences", required=True)
    parser.add_argument("--dominant-uncertainty", required=True)
    parser.add_argument("--benchmark-alternative", required=True)
    parser.add_argument("--benchmark-ref-or-label", default="")
    parser.add_argument("--review-date", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--manifest-path", default="")
    parser.add_argument("--primary-report-path", default="")
    parser.add_argument("--source-snapshot-date", default="")
    parser.add_argument("--accounting-basis", default="SNAPSHOT_ONLY")
    parser.add_argument("--policy-ref", default="")
    parser.add_argument("--policy-version", default="")
    parser.add_argument("--operator-state", default="NOT_RECORDED")
    parser.add_argument("--decision-pressure", default="UNKNOWN")
    parser.add_argument("--market-context-tag", default="")
    parser.add_argument("--conviction", default="")
    parser.add_argument("--cash-context", default="UNKNOWN")
    parser.add_argument("--source-paths", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    parser.add_argument("--report-date", default="")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create, validate, or append to the personal decision state capture artifact. Decision Capture records human review state only; it does not execute trades."
    )
    subparsers = parser.add_subparsers(dest="command")
    capture_parser = subparsers.add_parser("capture", help="Append one human-operated Decision Capture row.")
    add_capture_args(capture_parser)
    validate_parser = subparsers.add_parser("validate-journal", help="Validate an existing Decision Capture CSV and write a report.")
    add_common_io_args(validate_parser)
    add_common_io_args(parser)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    try:
        if args.command == "capture":
            result = append_decision_capture(
                output=args.output,
                report=args.report,
                report_date=args.report_date or None,
                decision_id=args.decision_id,
                decision_date=args.decision_date,
                decision_scope=args.decision_scope,
                asset_id=args.asset_id,
                ticker=args.ticker,
                asset_name=args.asset_name,
                asset_type=args.asset_type,
                proposed_action=args.proposed_action,
                human_decision=args.human_decision,
                decision_status=args.decision_status,
                reasoning_3_sentences=args.reasoning_3_sentences,
                dominant_uncertainty=args.dominant_uncertainty,
                benchmark_alternative=args.benchmark_alternative,
                benchmark_ref_or_label=args.benchmark_ref_or_label,
                review_date=args.review_date,
                run_id=args.run_id,
                manifest_path=args.manifest_path,
                primary_report_path=args.primary_report_path,
                source_snapshot_date=args.source_snapshot_date,
                accounting_basis=args.accounting_basis,
                policy_ref=args.policy_ref,
                policy_version=args.policy_version,
                operator_state=args.operator_state,
                decision_pressure=args.decision_pressure,
                market_context_tag=args.market_context_tag,
                conviction=args.conviction,
                cash_context=args.cash_context,
                source_paths=args.source_paths,
                notes=args.notes,
            )
            print(f"appended_decision_id={result.appended_decision_id}")
            print(f"output={result.output_path}")
            print(f"report={result.report_path}")
            return
        run_decision_state_capture(
            input_path=args.input or None,
            output=args.output,
            report=args.report,
            run_id=args.run_id,
            manifest_path=args.manifest_path,
            primary_report_path=args.primary_report_path,
            source_snapshot_date=args.source_snapshot_date,
            report_date=args.report_date or None,
            fail_on_invalid=args.command == "validate-journal",
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
