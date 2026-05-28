from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.common import read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows
from src.valuation_input_provenance_review import safe_display_path

DEFAULT_QUEUE_INPUT = "data/processed/personal_valuation_input_review_queue.csv"
DEFAULT_REVIEW_INPUT = "data/raw/private/fundamentals/personal_valuation_review_input.csv"
DEFAULT_PROVENANCE_INPUT = "data/processed/personal_valuation_input_provenance_review.csv"
DEFAULT_EVIDENCE_INPUT = "data/processed/personal_fundamentals_master_evidence_applied.csv"
DEFAULT_REVIEW_OUTPUT = "data/processed/personal_valuation_input_temporal_integrity_review.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_valuation_input_temporal_integrity_summary.csv"

REVIEW_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "run_as_of_date",
    "valuation_source_as_of_date",
    "valuation_reviewed_at",
    "source_age_days",
    "review_age_days",
    "source_after_run_as_of",
    "review_after_run_as_of",
    "review_before_source_as_of",
    "temporal_integrity_status",
    "upstream_provenance_status",
    "reason_code",
    "recommended_next_action",
]
SUMMARY_FIELDS = ["metric", "value", "notes"]
NON_OK_UPSTREAM_STATUSES = {"MISSING", "INVALID", "REVIEW", "CONFLICT", "STALE"}


@dataclass(frozen=True)
class ValuationInputTemporalIntegrityReviewResult:
    review_output: Path
    summary_output: Path
    report_output: Path
    review_rows: list[dict[str, str]]
    summary_rows: list[dict[str, str]]
    warnings: tuple[str, ...]


def optional_csv_rows(path_value: str, label: str) -> tuple[list[dict[str, str]], list[str], bool]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], [f"missing_input={label}:{safe_display_path(path_value)}"], False
    return read_csv_rows(path), [], True


def parse_iso_date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def canonical_identity(row: dict[str, str]) -> tuple[str, str]:
    isin = str(row.get("isin", "") or "").strip().upper()
    ticker = str(row.get("ticker", "") or "").strip().upper()
    return (isin, "") if isin else ("", ticker)


def index_by_identity(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    indexed: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        identity = canonical_identity(row)
        if identity != ("", "") and identity not in indexed:
            indexed[identity] = row
    return indexed


def joined_reasons(reasons: set[str]) -> str:
    return ";".join(sorted(reason for reason in reasons if reason))


def bool_text(value: bool) -> str:
    return "True" if value else "False"


def age_text(value: date | None, run_date: date) -> str:
    if value is None:
        return ""
    return str((run_date - value).days)


def status_from_reasons(reasons: set[str], *, profile: str, upstream_status: str) -> str:
    if profile and profile != "STANDARD":
        return "NOT_APPLICABLE"
    if "VALUATION_SOURCE_DATE_INVALID" in reasons or "VALUATION_SOURCE_DATE_AFTER_AS_OF" in reasons:
        return "INVALID"
    if "VALUATION_REVIEWED_AT_INVALID" in reasons or "VALUATION_REVIEWED_AT_AFTER_AS_OF" in reasons:
        return "INVALID"
    if "VALUATION_REVIEWED_AT_BEFORE_SOURCE_DATE" in reasons:
        return "INCONSISTENT"
    if "VALUATION_SOURCE_DATE_MISSING" in reasons or "VALUATION_REVIEWED_AT_MISSING" in reasons:
        return "MISSING"
    if upstream_status in NON_OK_UPSTREAM_STATUSES:
        return "REVIEW"
    return "OK"


def recommended_action(status: str, reasons: set[str]) -> str:
    if status == "OK":
        return "Temporal evidence is reviewable; valuation automation remains outside this patch."
    if status == "NOT_APPLICABLE":
        return "No temporal valuation action required for non-STANDARD row."
    if status == "MISSING":
        return "Add explicit valuation source and review dates; do not infer dates."
    if status == "INVALID":
        return "Fix invalid or future valuation temporal evidence before use."
    if status == "INCONSISTENT":
        return "Correct review/source date ordering before use."
    if "UPSTREAM_PROVENANCE_NOT_OK" in reasons:
        return "Resolve upstream valuation provenance status before temporal acceptance."
    return "Complete valuation temporal review before use."


def build_review_rows(
    *,
    queue_rows: list[dict[str, str]],
    reviewed_rows: list[dict[str, str]],
    provenance_rows: list[dict[str, str]],
    review_input_exists: bool,
    provenance_input_exists: bool,
    run_date: date,
) -> list[dict[str, str]]:
    reviewed_index = index_by_identity(reviewed_rows)
    provenance_index = index_by_identity(provenance_rows)
    output: list[dict[str, str]] = []
    for queue_row in queue_rows:
        profile = safe_upper(queue_row.get("company_type_profile"))
        identity = canonical_identity(queue_row)
        reviewed = reviewed_index.get(identity, {})
        provenance = provenance_index.get(identity, {})
        upstream_status = safe_upper(provenance.get("valuation_input_provenance_status", ""))
        reasons: set[str] = {"NO_IMPUTATION"}
        if not review_input_exists:
            reasons.add("OPTIONAL_INPUT_MISSING")
        if not provenance_input_exists:
            reasons.add("OPTIONAL_INPUT_MISSING")
        if profile and profile != "STANDARD":
            reasons.add("PROFILE_NOT_STANDARD")

        source_text = str(reviewed.get("valuation_source_as_of_date", "") or "").strip()
        review_text = str(reviewed.get("valuation_reviewed_at", "") or "").strip()
        source_date = parse_iso_date(source_text)
        review_date = parse_iso_date(review_text)

        if not source_text:
            reasons.add("TEMPORAL_EVIDENCE_MISSING")
            reasons.add("VALUATION_SOURCE_DATE_MISSING")
        elif source_date is None:
            reasons.add("VALUATION_SOURCE_DATE_INVALID")
        elif source_date > run_date:
            reasons.add("VALUATION_SOURCE_DATE_AFTER_AS_OF")

        if not review_text:
            reasons.add("TEMPORAL_EVIDENCE_MISSING")
            reasons.add("VALUATION_REVIEWED_AT_MISSING")
        elif review_date is None:
            reasons.add("VALUATION_REVIEWED_AT_INVALID")
        elif review_date > run_date:
            reasons.add("VALUATION_REVIEWED_AT_AFTER_AS_OF")

        if source_date is not None and review_date is not None and review_date < source_date:
            reasons.add("VALUATION_REVIEWED_AT_BEFORE_SOURCE_DATE")

        if upstream_status in NON_OK_UPSTREAM_STATUSES:
            reasons.add("UPSTREAM_PROVENANCE_NOT_OK")

        status = status_from_reasons(reasons, profile=profile, upstream_status=upstream_status)
        if status == "OK":
            reasons.discard("NO_IMPUTATION")
            reasons.add("TEMPORAL_INTEGRITY_OK")

        source_after = source_date is not None and source_date > run_date
        review_after = review_date is not None and review_date > run_date
        review_before_source = source_date is not None and review_date is not None and review_date < source_date

        output.append(
            {
                "ticker": queue_row.get("ticker", reviewed.get("ticker", "")),
                "isin": queue_row.get("isin", reviewed.get("isin", "")),
                "company_name": queue_row.get("company_name", ""),
                "company_type_profile": queue_row.get("company_type_profile", ""),
                "run_as_of_date": run_date.isoformat(),
                "valuation_source_as_of_date": source_text,
                "valuation_reviewed_at": review_text,
                "source_age_days": age_text(source_date, run_date) if not source_after else "",
                "review_age_days": age_text(review_date, run_date) if not review_after else "",
                "source_after_run_as_of": bool_text(source_after),
                "review_after_run_as_of": bool_text(review_after),
                "review_before_source_as_of": bool_text(review_before_source),
                "temporal_integrity_status": status,
                "upstream_provenance_status": upstream_status,
                "reason_code": joined_reasons(reasons),
                "recommended_next_action": recommended_action(status, reasons),
            }
        )
    return sorted(output, key=lambda row: (row["isin"], row["ticker"], row["company_name"]))


def build_summary_rows(review_rows: list[dict[str, str]], warnings: list[str]) -> list[dict[str, str]]:
    counts = Counter(row["temporal_integrity_status"] for row in review_rows)
    reason_union = {
        reason
        for row in review_rows
        for reason in str(row.get("reason_code", "")).split(";")
        if reason
    }
    rows = [
        {
            "metric": "valuation_input_temporal_integrity_review_available",
            "value": "True",
            "notes": "Read-only valuation input temporal integrity review generated.",
        },
        {"metric": "queue_rows_count", "value": str(len(review_rows)), "notes": "Rows read from valuation review queue."},
        {"metric": "ok_rows_count", "value": str(counts.get("OK", 0)), "notes": "Rows with temporally consistent evidence."},
        {"metric": "review_rows_count", "value": str(counts.get("REVIEW", 0)), "notes": "Rows requiring temporal/provenance review."},
        {"metric": "missing_rows_count", "value": str(counts.get("MISSING", 0)), "notes": "Rows missing temporal evidence."},
        {"metric": "invalid_rows_count", "value": str(counts.get("INVALID", 0)), "notes": "Rows with invalid or future temporal evidence."},
        {
            "metric": "inconsistent_rows_count",
            "value": str(counts.get("INCONSISTENT", 0)),
            "notes": "Rows where reviewed_at is before source as-of date.",
        },
        {
            "metric": "not_applicable_rows_count",
            "value": str(counts.get("NOT_APPLICABLE", 0)),
            "notes": "Non-STANDARD rows outside valuation temporal review.",
        },
        {"metric": "no_imputation_confirmed", "value": "True", "notes": "Missing temporal values were not filled."},
        {"metric": "reason_codes", "value": joined_reasons(reason_union), "notes": "Union of emitted reason codes."},
        {"metric": "warnings_total", "value": str(len(warnings)), "notes": "Input availability warnings."},
    ]
    return sorted(rows, key=lambda row: row["metric"])


def render_report(summary_rows: list[dict[str, str]], review_rows: list[dict[str, str]], input_paths: dict[str, str]) -> str:
    summary = {row["metric"]: row["value"] for row in summary_rows}
    lines = [
        "# Personal Valuation Input Temporal Integrity Review",
        "",
        "## Executive Summary",
        f"- Queue rows: {summary.get('queue_rows_count', '0')}",
        f"- OK rows: {summary.get('ok_rows_count', '0')}",
        f"- Missing rows: {summary.get('missing_rows_count', '0')}",
        f"- Invalid rows: {summary.get('invalid_rows_count', '0')}",
        f"- Inconsistent rows: {summary.get('inconsistent_rows_count', '0')}",
        f"- Review rows: {summary.get('review_rows_count', '0')}",
        f"- No imputation confirmed: {summary.get('no_imputation_confirmed', 'True')}",
        "",
        "## Boundary",
        "- This report is read-only governance evidence.",
        "- It does not implement valuation automation, investment readiness, investment advice, order execution, scoring changes or buy/sell recommendation changes.",
        "- Missing, future, invalid and inconsistent temporal evidence remains visible.",
        "",
        "## Input Artifacts",
    ]
    for label, path_value in sorted(input_paths.items()):
        lines.append(f"- `{label}`: `{safe_display_path(path_value)}`")
    lines.extend(
        [
            "",
            "## Review Rows",
            "| ticker | isin | profile | temporal_status | upstream_status | reason_code | recommended_next_action |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in review_rows:
        lines.append(
            f"| {row['ticker']} | {row['isin']} | {row['company_type_profile']} | "
            f"{row['temporal_integrity_status']} | {row['upstream_provenance_status']} | "
            f"{row['reason_code']} | {row['recommended_next_action']} |"
        )
    lines.extend(["", "## Reason Codes", f"- {summary.get('reason_codes', '')}", ""])
    return "\n".join(lines)


def default_report_output(as_of_date: str) -> str:
    return f"reports/{as_of_date}/personal_valuation_input_temporal_integrity_review.md"


def run_valuation_input_temporal_integrity_review(
    *,
    as_of_date: str,
    queue_input: str = DEFAULT_QUEUE_INPUT,
    review_input: str = DEFAULT_REVIEW_INPUT,
    provenance_input: str = DEFAULT_PROVENANCE_INPUT,
    evidence_input: str = DEFAULT_EVIDENCE_INPUT,
    review_output: str = DEFAULT_REVIEW_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str | None = None,
) -> ValuationInputTemporalIntegrityReviewResult:
    run_date = date.fromisoformat(as_of_date)
    warnings: list[str] = []
    queue_rows, queue_warnings, _ = optional_csv_rows(queue_input, "valuation_review_queue")
    warnings.extend(queue_warnings)
    reviewed_rows, review_warnings, review_exists = optional_csv_rows(review_input, "valuation_review_input")
    warnings.extend(review_warnings)
    provenance_rows, provenance_warnings, provenance_exists = optional_csv_rows(provenance_input, "valuation_provenance_review")
    warnings.extend(provenance_warnings)
    _, evidence_warnings, _ = optional_csv_rows(evidence_input, "evidence_applied_master")
    warnings.extend(evidence_warnings)

    review_rows = build_review_rows(
        queue_rows=queue_rows,
        reviewed_rows=reviewed_rows,
        provenance_rows=provenance_rows,
        review_input_exists=review_exists,
        provenance_input_exists=provenance_exists,
        run_date=run_date,
    )
    summary_rows = build_summary_rows(review_rows, warnings)
    review_path = write_csv_rows(review_output, REVIEW_FIELDS, review_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    report_target = report_output or default_report_output(as_of_date)
    input_paths = {
        "valuation_review_queue": queue_input,
        "valuation_review_input": review_input,
        "valuation_provenance_review": provenance_input,
        "evidence_applied_master": evidence_input,
        "review_output": review_output,
        "summary_output": summary_output,
    }
    report_path = resolve_repo_path(report_target)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(summary_rows, review_rows, input_paths), encoding="utf-8")
    return ValuationInputTemporalIntegrityReviewResult(
        review_output=review_path,
        summary_output=summary_path,
        report_output=report_path,
        review_rows=review_rows,
        summary_rows=summary_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review valuation input as-of temporal integrity without applying values.")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--queue-input", default=DEFAULT_QUEUE_INPUT)
    parser.add_argument("--review-input", default=DEFAULT_REVIEW_INPUT)
    parser.add_argument("--provenance-input", default=DEFAULT_PROVENANCE_INPUT)
    parser.add_argument("--evidence-input", default=DEFAULT_EVIDENCE_INPUT)
    parser.add_argument("--review-output", default=DEFAULT_REVIEW_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_valuation_input_temporal_integrity_review(
        as_of_date=args.as_of_date,
        queue_input=args.queue_input,
        review_input=args.review_input,
        provenance_input=args.provenance_input,
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
    print(f"invalid_rows_count={summary.get('invalid_rows_count', '0')}")
    print(f"warnings_total={summary.get('warnings_total', '0')}")


if __name__ == "__main__":
    main()
