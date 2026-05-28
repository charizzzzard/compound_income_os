from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import normalize_number_text, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_QUEUE_INPUT = "data/processed/personal_valuation_input_review_queue.csv"
DEFAULT_REVIEW_INPUT = "data/raw/private/fundamentals/personal_valuation_review_input.csv"
DEFAULT_EVIDENCE_INPUT = "data/processed/personal_fundamentals_master_evidence_applied.csv"
DEFAULT_REVIEW_OUTPUT = "data/processed/personal_valuation_input_provenance_review.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_valuation_input_provenance_summary.csv"

REVIEW_INPUT_REQUIRED_FIELDS = [
    "ticker",
    "isin",
    "normalized_fcf_yield_pct",
    "target_fcf_yield_pct",
    "valuation_review_status",
    "valuation_source_type",
    "valuation_source_name",
    "valuation_source_reference",
    "valuation_source_as_of_date",
    "valuation_reviewed_by",
    "valuation_reviewed_at",
    "valuation_notes",
]
REQUIRED_VALUE_FIELDS = ("normalized_fcf_yield_pct", "target_fcf_yield_pct")
SOURCE_TYPES = {"MANUAL_REVIEW", "EVIDENCE_FILE", "BROKER_EXPORT", "PUBLIC_FILINGS", "OTHER"}
REVIEW_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "normalized_fcf_yield_pct",
    "target_fcf_yield_pct",
    "valuation_review_status",
    "valuation_source_type",
    "valuation_source_name",
    "valuation_source_reference",
    "valuation_source_as_of_date",
    "valuation_reviewed_by",
    "valuation_reviewed_at",
    "valuation_provenance_status",
    "valuation_conflict_status",
    "valuation_input_provenance_status",
    "reason_code",
    "recommended_next_action",
]
SUMMARY_FIELDS = ["metric", "value", "notes"]


@dataclass(frozen=True)
class ValuationInputProvenanceReviewResult:
    review_output: Path
    summary_output: Path
    report_output: Path
    review_rows: list[dict[str, str]]
    summary_rows: list[dict[str, str]]
    warnings: tuple[str, ...]


def safe_display_path(path_value: str) -> str:
    normalized = str(path_value).replace("\\", "/")
    if "data/raw/private" in normalized:
        return "<private_path>"
    path = Path(path_value)
    if path.is_absolute():
        return f"<local_path>/{path.name}"
    return path_value


def optional_csv_rows(path_value: str, label: str) -> tuple[list[dict[str, str]], list[str], bool]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], [f"missing_input={label}:{safe_display_path(path_value)}"], False
    return read_csv_rows(path), [], True


def parse_decimal(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(normalize_number_text(text.replace("%", "")))
    except ValueError:
        return None


def canonical_identity(row: dict[str, str]) -> tuple[str, str]:
    isin = str(row.get("isin", "") or "").strip().upper()
    ticker = str(row.get("ticker", "") or "").strip().upper()
    return (isin, "") if isin else ("", ticker)


def joined_reasons(reasons: set[str]) -> str:
    return ";".join(sorted(reason for reason in reasons if reason))


def parse_iso_date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def source_age_days(source_date: date, as_of_date: date) -> int:
    return (as_of_date - source_date).days


def review_index(review_rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    by_identity: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in review_rows:
        identity = canonical_identity(row)
        if identity == ("", ""):
            continue
        by_identity[identity].append(row)
    return dict(by_identity)


def rows_conflict(rows: list[dict[str, str]], field: str) -> bool:
    values = {str(row.get(field, "") or "").strip() for row in rows}
    return len(values) > 1


def conflict_reasons(rows: list[dict[str, str]]) -> set[str]:
    if len(rows) <= 1:
        return set()
    reasons = {"DUPLICATE_VALUATION_IDENTITY"}
    if rows_conflict(rows, "normalized_fcf_yield_pct") or rows_conflict(rows, "target_fcf_yield_pct"):
        reasons.add("CONFLICTING_VALUATION_VALUES")
    if (
        rows_conflict(rows, "valuation_source_reference")
        or rows_conflict(rows, "valuation_source_as_of_date")
        or rows_conflict(rows, "valuation_source_type")
    ):
        reasons.add("CONFLICTING_SOURCE_METADATA")
    return reasons


def validate_review_row(
    review_row: dict[str, str] | None,
    *,
    input_exists: bool,
    schema_valid: bool,
    as_of_date: date,
    max_source_age_days: int,
) -> tuple[str, set[str]]:
    reasons: set[str] = {"NO_IMPUTATION"}
    if not input_exists:
        reasons.add("VALUATION_REQUIRED_MISSING")
        return "MISSING", reasons
    if not schema_valid:
        reasons.add("VALUATION_VALUE_INVALID")
        return "INVALID", reasons
    if review_row is None:
        reasons.add("VALUATION_REQUIRED_MISSING")
        return "MISSING", reasons

    for field in REQUIRED_VALUE_FIELDS:
        raw_value = str(review_row.get(field, "") or "").strip()
        value = parse_decimal(raw_value)
        if value is None and not raw_value:
            reasons.add("VALUATION_REQUIRED_MISSING")
            return "MISSING", reasons
        if value is None:
            reasons.add("VALUATION_VALUE_INVALID")
            return "INVALID", reasons
        if not -100.0 <= value <= 100.0:
            reasons.add("VALUATION_VALUE_OUT_OF_RANGE")
            return "INVALID", reasons

    review_status = safe_upper(review_row.get("valuation_review_status"))
    source_type = safe_upper(review_row.get("valuation_source_type"))
    source_reference = str(review_row.get("valuation_source_reference", "") or "").strip()
    source_date_text = str(review_row.get("valuation_source_as_of_date", "") or "").strip()

    if review_status != "APPROVED":
        reasons.add("VALUATION_REVIEW_PENDING")
        return "REVIEW", reasons
    if source_type not in SOURCE_TYPES:
        reasons.add("VALUATION_SOURCE_TYPE_UNKNOWN")
        return "REVIEW", reasons
    if not source_reference:
        reasons.add("VALUATION_SOURCE_REFERENCE_MISSING")
        return "REVIEW", reasons
    if not source_date_text:
        reasons.add("VALUATION_SOURCE_DATE_MISSING")
        return "REVIEW", reasons

    parsed_date = parse_iso_date(source_date_text)
    if parsed_date is None or parsed_date > as_of_date:
        reasons.add("VALUATION_SOURCE_DATE_INVALID")
        return "INVALID", reasons
    if source_age_days(parsed_date, as_of_date) > max_source_age_days:
        reasons.add("VALUATION_SOURCE_STALE")
        return "STALE", reasons

    reasons.discard("NO_IMPUTATION")
    reasons.add("VALUATION_PROVENANCE_OK")
    return "OK", reasons


def overall_status(provenance_status: str, conflict_status: str) -> str:
    if conflict_status == "CONFLICT":
        return "CONFLICT"
    return provenance_status


def recommended_action(status: str, reasons: set[str]) -> str:
    if status == "OK":
        return "Provenance is reviewable; downstream valuation automation remains outside this patch."
    if status == "NOT_APPLICABLE":
        return "No valuation provenance action required for non-STANDARD row."
    if status == "CONFLICT":
        return "Resolve duplicate or conflicting valuation review rows before use."
    if status == "MISSING":
        return "Add reviewed valuation values and provenance; do not impute missing values."
    if status == "INVALID":
        return "Fix invalid valuation values or source date metadata before review."
    if status == "STALE":
        return "Refresh or re-review stale valuation source evidence before use."
    if "VALUATION_SOURCE_REFERENCE_MISSING" in reasons or "VALUATION_SOURCE_DATE_MISSING" in reasons:
        return "Add source reference and source as-of date before use."
    return "Complete valuation provenance review before use."


def build_review_rows(
    *,
    queue_rows: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    review_input_exists: bool,
    review_schema_valid: bool,
    as_of_date: date,
    max_source_age_days: int,
) -> list[dict[str, str]]:
    by_identity = review_index(review_rows) if review_schema_valid else {}
    output_rows: list[dict[str, str]] = []
    for queue_row in queue_rows:
        profile = safe_upper(queue_row.get("company_type_profile"))
        identity = canonical_identity(queue_row)
        matched_rows = by_identity.get(identity, [])
        review_row = matched_rows[0] if matched_rows else None
        reasons = conflict_reasons(matched_rows)
        conflict_status = "CONFLICT" if reasons else "OK"

        if profile and profile != "STANDARD":
            provenance_status = "NOT_APPLICABLE"
            reasons.add("PROFILE_NOT_STANDARD")
        else:
            provenance_status, provenance_reasons = validate_review_row(
                review_row,
                input_exists=review_input_exists,
                schema_valid=review_schema_valid,
                as_of_date=as_of_date,
                max_source_age_days=max_source_age_days,
            )
            reasons.update(provenance_reasons)

        input_status = overall_status(provenance_status, conflict_status)
        source = review_row or {}
        output_rows.append(
            {
                "ticker": queue_row.get("ticker", source.get("ticker", "")),
                "isin": queue_row.get("isin", source.get("isin", "")),
                "company_name": queue_row.get("company_name", ""),
                "company_type_profile": queue_row.get("company_type_profile", ""),
                "normalized_fcf_yield_pct": source.get("normalized_fcf_yield_pct", ""),
                "target_fcf_yield_pct": source.get("target_fcf_yield_pct", ""),
                "valuation_review_status": safe_upper(source.get("valuation_review_status", "")),
                "valuation_source_type": safe_upper(source.get("valuation_source_type", "")),
                "valuation_source_name": source.get("valuation_source_name", ""),
                "valuation_source_reference": source.get("valuation_source_reference", ""),
                "valuation_source_as_of_date": source.get("valuation_source_as_of_date", ""),
                "valuation_reviewed_by": source.get("valuation_reviewed_by", ""),
                "valuation_reviewed_at": source.get("valuation_reviewed_at", ""),
                "valuation_provenance_status": provenance_status,
                "valuation_conflict_status": conflict_status,
                "valuation_input_provenance_status": input_status,
                "reason_code": joined_reasons(reasons),
                "recommended_next_action": recommended_action(input_status, reasons),
            }
        )
    return sorted(output_rows, key=lambda row: (row["isin"], row["ticker"], row["company_name"]))


def build_summary_rows(
    *,
    review_rows: list[dict[str, str]],
    reviewed_input_rows_count: int,
    optional_evidence_input_exists: bool,
    warnings: list[str],
) -> list[dict[str, str]]:
    counts = Counter(row["valuation_input_provenance_status"] for row in review_rows)
    reason_union = {
        reason
        for row in review_rows
        for reason in str(row.get("reason_code", "")).split(";")
        if reason
    }
    if not optional_evidence_input_exists:
        reason_union.add("OPTIONAL_EVIDENCE_INPUT_MISSING")

    rows = [
        {
            "metric": "valuation_input_provenance_review_available",
            "value": "True",
            "notes": "Read-only valuation input provenance review generated.",
        },
        {"metric": "queue_rows_count", "value": str(len(review_rows)), "notes": "Rows read from valuation review queue."},
        {
            "metric": "reviewed_input_rows_count",
            "value": str(reviewed_input_rows_count),
            "notes": "Rows read from optional private reviewed valuation input.",
        },
        {"metric": "ok_rows_count", "value": str(counts.get("OK", 0)), "notes": "Rows with complete provenance evidence."},
        {"metric": "review_rows_count", "value": str(counts.get("REVIEW", 0)), "notes": "Rows requiring provenance review."},
        {"metric": "missing_rows_count", "value": str(counts.get("MISSING", 0)), "notes": "Rows missing valuation provenance or values."},
        {"metric": "invalid_rows_count", "value": str(counts.get("INVALID", 0)), "notes": "Rows with invalid values or date metadata."},
        {"metric": "conflict_rows_count", "value": str(counts.get("CONFLICT", 0)), "notes": "Rows with duplicate/conflicting valuation identity or metadata."},
        {"metric": "stale_rows_count", "value": str(counts.get("STALE", 0)), "notes": "Rows with stale source as-of dates."},
        {
            "metric": "not_applicable_rows_count",
            "value": str(counts.get("NOT_APPLICABLE", 0)),
            "notes": "Non-STANDARD rows outside valuation provenance review.",
        },
        {
            "metric": "optional_evidence_input_status",
            "value": "PRESENT" if optional_evidence_input_exists else "MISSING",
            "notes": "Optional evidence-applied master status.",
        },
        {"metric": "no_imputation_confirmed", "value": "True", "notes": "Missing valuation values were not filled."},
        {"metric": "reason_codes", "value": joined_reasons(reason_union), "notes": "Union of emitted reason codes."},
        {"metric": "warnings_total", "value": str(len(warnings)), "notes": "Input availability or schema warnings."},
    ]
    return sorted(rows, key=lambda row: row["metric"])


def render_report(summary_rows: list[dict[str, str]], review_rows: list[dict[str, str]], input_paths: dict[str, str]) -> str:
    summary = {row["metric"]: row["value"] for row in summary_rows}
    lines = [
        "# Personal Valuation Input Provenance Review",
        "",
        "## Executive Summary",
        f"- Queue rows: {summary.get('queue_rows_count', '0')}",
        f"- Reviewed input rows: {summary.get('reviewed_input_rows_count', '0')}",
        f"- OK rows: {summary.get('ok_rows_count', '0')}",
        f"- Review rows: {summary.get('review_rows_count', '0')}",
        f"- Missing rows: {summary.get('missing_rows_count', '0')}",
        f"- Invalid rows: {summary.get('invalid_rows_count', '0')}",
        f"- Conflict rows: {summary.get('conflict_rows_count', '0')}",
        f"- Stale rows: {summary.get('stale_rows_count', '0')}",
        f"- No imputation confirmed: {summary.get('no_imputation_confirmed', 'True')}",
        "",
        "## Boundary",
        "- This report is read-only governance evidence.",
        "- It does not implement valuation automation, investment readiness, investment advice, order execution or buy/sell recommendation changes.",
        "- Missing, stale, unknown, invalid and conflict states remain visible.",
        "",
        "## Input Artifacts",
    ]
    for label, path_value in sorted(input_paths.items()):
        lines.append(f"- `{label}`: `{safe_display_path(path_value)}`")
    lines.extend(
        [
            "",
            "## Review Rows",
            "| ticker | isin | profile | status | conflict | reason_code | recommended_next_action |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in review_rows:
        lines.append(
            f"| {row['ticker']} | {row['isin']} | {row['company_type_profile']} | "
            f"{row['valuation_input_provenance_status']} | {row['valuation_conflict_status']} | "
            f"{row['reason_code']} | {row['recommended_next_action']} |"
        )
    lines.extend(["", "## Reason Codes", f"- {summary.get('reason_codes', '')}", ""])
    return "\n".join(lines)


def run_valuation_input_provenance_review(
    *,
    as_of_date: str,
    max_source_age_days: int = 365,
    queue_input: str = DEFAULT_QUEUE_INPUT,
    review_input: str = DEFAULT_REVIEW_INPUT,
    evidence_input: str = DEFAULT_EVIDENCE_INPUT,
    review_output: str = DEFAULT_REVIEW_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str | None = None,
) -> ValuationInputProvenanceReviewResult:
    effective_date = date.fromisoformat(as_of_date)
    warnings: list[str] = []
    queue_rows, queue_warnings, _ = optional_csv_rows(queue_input, "valuation_review_queue")
    warnings.extend(queue_warnings)
    reviewed_rows, review_warnings, review_exists = optional_csv_rows(review_input, "valuation_review_input")
    warnings.extend(review_warnings)
    _, evidence_warnings, evidence_exists = optional_csv_rows(evidence_input, "evidence_applied_master")
    warnings.extend(evidence_warnings)

    review_schema_valid = not review_exists or (
        bool(reviewed_rows) and set(REVIEW_INPUT_REQUIRED_FIELDS).issubset(set(reviewed_rows[0].keys()))
    )
    if review_exists and not review_schema_valid:
        warnings.append("invalid_input_schema=valuation_review_input")

    review_result_rows = build_review_rows(
        queue_rows=queue_rows,
        review_rows=reviewed_rows,
        review_input_exists=review_exists,
        review_schema_valid=review_schema_valid,
        as_of_date=effective_date,
        max_source_age_days=max_source_age_days,
    )
    summary_rows = build_summary_rows(
        review_rows=review_result_rows,
        reviewed_input_rows_count=len(reviewed_rows),
        optional_evidence_input_exists=evidence_exists,
        warnings=warnings,
    )
    review_path = write_csv_rows(review_output, REVIEW_FIELDS, review_result_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    input_paths = {
        "valuation_review_queue": queue_input,
        "valuation_review_input": review_input,
        "evidence_applied_master": evidence_input,
        "review_output": review_output,
        "summary_output": summary_output,
    }
    report_target = report_output or f"reports/{as_of_date}/personal_valuation_input_provenance_review.md"
    report_path = resolve_repo_path(report_target)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(summary_rows, review_result_rows, input_paths), encoding="utf-8")
    return ValuationInputProvenanceReviewResult(
        review_output=review_path,
        summary_output=summary_path,
        report_output=report_path,
        review_rows=review_result_rows,
        summary_rows=summary_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review valuation input provenance and conflicts without applying values.")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--max-source-age-days", type=int, default=365)
    parser.add_argument("--queue-input", default=DEFAULT_QUEUE_INPUT)
    parser.add_argument("--review-input", default=DEFAULT_REVIEW_INPUT)
    parser.add_argument("--evidence-input", default=DEFAULT_EVIDENCE_INPUT)
    parser.add_argument("--review-output", default=DEFAULT_REVIEW_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_valuation_input_provenance_review(
        as_of_date=args.as_of_date,
        max_source_age_days=args.max_source_age_days,
        queue_input=args.queue_input,
        review_input=args.review_input,
        evidence_input=args.evidence_input,
        review_output=args.review_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    summary = {row["metric"]: row["value"] for row in result.summary_rows}
    print(f"review_output={result.review_output}")
    print(f"summary_output={result.summary_output}")
    print(f"report_output={result.report_output}")
    print(f"queue_rows_count={summary.get('queue_rows_count', '0')}")
    print(f"conflict_rows_count={summary.get('conflict_rows_count', '0')}")
    print(f"warnings_total={summary.get('warnings_total', '0')}")


if __name__ == "__main__":
    main()
