from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import normalize_number_text, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_KPI_TIER_INPUT = "data/processed/personal_kpi_tier_coverage.csv"
DEFAULT_SCORES_INPUT = "data/processed/personal_company_scores.csv"
DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT = "data/processed/personal_fundamentals_master_evidence_applied.csv"
DEFAULT_REVIEW_INPUT = "data/raw/private/fundamentals/personal_valuation_review_input.csv"
DEFAULT_QUEUE_OUTPUT = "data/processed/personal_valuation_input_review_queue.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_valuation_input_contract_summary.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_valuation_input_contract_report.md"

VALUATION_REQUIRED_KPIS = ("normalized_fcf_yield_pct", "target_fcf_yield_pct")
REVIEW_STATUSES = {"APPROVED", "REVIEW", "REJECTED", "MISSING"}
SOURCE_TYPES = {"MANUAL_REVIEW", "EVIDENCE_FILE", "BROKER_EXPORT", "PUBLIC_FILINGS", "OTHER", "UNKNOWN"}
REVIEW_INPUT_REQUIRED_FIELDS = [
    "ticker",
    "isin",
    "normalized_fcf_yield_pct",
    "target_fcf_yield_pct",
    "valuation_review_status",
    "valuation_source_type",
    "valuation_source_reference",
    "valuation_source_as_of_date",
]
QUEUE_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "missing_valuation_kpis",
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
    "valuation_input_status",
    "reason_code",
    "recommended_next_action",
]
SUMMARY_FIELDS = ["metric", "value", "notes"]


@dataclass(frozen=True)
class ValuationInputContractResult:
    queue_output: Path
    summary_output: Path
    report_output: Path
    queue_rows: list[dict[str, str]]
    summary_rows: list[dict[str, str]]
    warnings: tuple[str, ...]


def safe_display_path(path_value: str) -> str:
    normalized = str(path_value).replace("\\", "/")
    if "data/raw/private" in normalized:
        return "<private_path>"
    return path_value


def optional_csv_rows(path_value: str, label: str) -> tuple[list[dict[str, str]], list[str], bool]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], [f"missing_input={label}:{safe_display_path(path_value)}"], False
    return read_csv_rows(path), [], True


def joined_reasons(reasons: set[str] | list[str] | tuple[str, ...]) -> str:
    return ";".join(sorted(reason for reason in reasons if reason))


def bool_text(value: bool) -> str:
    return "True" if value else "False"


def parse_decimal(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(normalize_number_text(text.replace("%", "")))
    except ValueError:
        return None


def is_missing(value: Any) -> bool:
    return str(value or "").strip() == ""


def row_key(row: dict[str, str]) -> tuple[str, str]:
    isin = str(row.get("isin", "") or "").strip().upper()
    ticker = str(row.get("ticker", "") or "").strip().upper()
    return isin, ticker


def build_review_index(review_rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str], dict[str, str]], set[tuple[str, str]]]:
    seen: dict[tuple[str, str], dict[str, str]] = {}
    duplicates: set[tuple[str, str]] = set()
    for row in review_rows:
        isin, ticker = row_key(row)
        key = (isin, ticker if not isin else "")
        if not isin and not ticker:
            continue
        if key in seen:
            duplicates.add(key)
        else:
            seen[key] = row
    return seen, duplicates


def find_review_row(index: dict[tuple[str, str], dict[str, str]], row: dict[str, str]) -> dict[str, str] | None:
    isin, ticker = row_key(row)
    if isin and (isin, "") in index:
        return index[(isin, "")]
    if not isin and ticker and ("", ticker) in index:
        return index[("", ticker)]
    return None


def validate_review_row(review_row: dict[str, str] | None, *, input_exists: bool, schema_valid: bool) -> tuple[str, set[str]]:
    reasons: set[str] = {"NO_IMPUTATION"}
    if not input_exists:
        reasons.add("INPUT_FILE_MISSING")
        reasons.add("VALUATION_REQUIRED_MISSING")
        return "MISSING", reasons
    if not schema_valid:
        reasons.add("INPUT_SCHEMA_INVALID")
        return "INVALID", reasons
    if review_row is None:
        reasons.add("VALUATION_REQUIRED_MISSING")
        return "MISSING", reasons

    values: dict[str, float | None] = {field: parse_decimal(review_row.get(field, "")) for field in VALUATION_REQUIRED_KPIS}
    missing_values = [field for field, value in values.items() if value is None and is_missing(review_row.get(field, ""))]
    invalid_values = [field for field, value in values.items() if value is None and not is_missing(review_row.get(field, ""))]
    out_of_range = [field for field, value in values.items() if value is not None and not -100.0 <= value <= 100.0]
    if missing_values:
        reasons.add("VALUATION_REQUIRED_MISSING")
        return "MISSING", reasons
    if invalid_values:
        reasons.add("VALUATION_VALUE_INVALID")
        return "INVALID", reasons
    if out_of_range:
        reasons.add("VALUATION_VALUE_OUT_OF_RANGE")
        return "INVALID", reasons

    review_status = safe_upper(review_row.get("valuation_review_status", ""))
    source_type = safe_upper(review_row.get("valuation_source_type", "")) or "UNKNOWN"
    source_reference = str(review_row.get("valuation_source_reference", "") or "").strip()
    source_as_of_date = str(review_row.get("valuation_source_as_of_date", "") or "").strip()
    if review_status not in REVIEW_STATUSES:
        reasons.add("VALUATION_REVIEW_PENDING")
        return "REVIEW", reasons
    if source_type not in SOURCE_TYPES:
        reasons.add("VALUATION_REVIEW_PENDING")
        return "REVIEW", reasons
    if review_status != "APPROVED":
        reasons.add("VALUATION_REVIEW_PENDING")
        return "REVIEW", reasons
    if not source_reference:
        reasons.add("VALUATION_SOURCE_REFERENCE_MISSING")
        return "REVIEW", reasons
    if not source_as_of_date:
        reasons.add("VALUATION_SOURCE_DATE_MISSING")
        return "REVIEW", reasons

    reasons.discard("NO_IMPUTATION")
    reasons.add("VALUATION_APPROVED")
    return "OK", reasons


def affected_standard_rows(kpi_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in kpi_rows:
        if safe_upper(row.get("company_type_profile", "")) != "STANDARD":
            continue
        missing = str(row.get("missing_valuation_kpis", "") or "").strip()
        valuation_status = safe_upper(row.get("valuation_data_status", ""))
        if missing or valuation_status in {"MISSING", "PARTIAL"}:
            rows.append(row)
    return sorted(rows, key=lambda row: (str(row.get("isin", "")), str(row.get("ticker", ""))))


def build_contract(
    *,
    kpi_rows: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    review_input_exists: bool,
    review_input_path: str,
    warnings: list[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    review_fields = set(review_rows[0].keys()) if review_rows else set()
    schema_valid = not review_input_exists or set(REVIEW_INPUT_REQUIRED_FIELDS).issubset(review_fields)
    if review_input_exists and not schema_valid:
        warnings.append("invalid_input_schema=valuation_review_input")
    review_index, duplicate_keys = build_review_index(review_rows) if schema_valid else ({}, set())
    if duplicate_keys:
        warnings.append("duplicate_review_identity=valuation_review_input")

    queue_rows: list[dict[str, str]] = []
    reason_union: set[str] = set()
    status_counts: Counter[str] = Counter()
    affected_rows = affected_standard_rows(kpi_rows)
    for row in affected_rows:
        review_row = find_review_row(review_index, row) if not duplicate_keys else None
        status, reasons = validate_review_row(review_row, input_exists=review_input_exists, schema_valid=schema_valid and not duplicate_keys)
        reason_union.update(reasons)
        status_counts[status] += 1
        missing_kpis = str(row.get("missing_valuation_kpis", "") or "").strip() or "; ".join(VALUATION_REQUIRED_KPIS)
        queue_rows.append(
            {
                "ticker": row.get("ticker", ""),
                "isin": row.get("isin", ""),
                "company_name": row.get("company_name", ""),
                "company_type_profile": row.get("company_type_profile", ""),
                "missing_valuation_kpis": missing_kpis,
                "normalized_fcf_yield_pct": "",
                "target_fcf_yield_pct": "",
                "valuation_review_status": safe_upper(review_row.get("valuation_review_status", "")) if review_row else "",
                "valuation_source_type": safe_upper(review_row.get("valuation_source_type", "")) if review_row else "",
                "valuation_source_name": "",
                "valuation_source_reference": "",
                "valuation_source_as_of_date": "",
                "valuation_reviewed_by": "",
                "valuation_reviewed_at": "",
                "valuation_notes": "",
                "valuation_input_status": status,
                "reason_code": joined_reasons(reasons),
                "recommended_next_action": recommended_action(status, reasons),
            }
        )

    non_standard_rows = [row for row in kpi_rows if safe_upper(row.get("company_type_profile", "")) and safe_upper(row.get("company_type_profile", "")) != "STANDARD"]
    if non_standard_rows:
        reason_union.add("PROFILE_NOT_STANDARD")

    summary_rows: list[dict[str, str]] = []

    def add_metric(metric: str, value: Any, notes: str) -> None:
        summary_rows.append({"metric": metric, "value": str(value), "notes": notes})

    input_status = "PRESENT" if review_input_exists else "MISSING"
    if review_input_exists and not schema_valid:
        input_status = "INVALID_SCHEMA"
    if duplicate_keys:
        input_status = "INVALID_DUPLICATE_IDENTITY"
        reason_union.add("INPUT_SCHEMA_INVALID")
    add_metric("valuation_contract_available", "True", "Companion valuation input contract generated.")
    add_metric("review_input_path", safe_display_path(review_input_path), "Expected optional private reviewed valuation input.")
    add_metric("input_file_status", input_status, "Optional reviewed valuation input status.")
    add_metric("affected_standard_rows_count", len(affected_rows), "STANDARD rows missing valuation-required KPIs.")
    add_metric("queue_rows_count", len(queue_rows), "Rows in personal_valuation_input_review_queue.csv.")
    add_metric("approved_rows_count", status_counts.get("OK", 0), "Rows with approved, valid reviewed valuation input.")
    add_metric("review_rows_count", status_counts.get("REVIEW", 0), "Rows requiring valuation review/source metadata.")
    add_metric("missing_rows_count", status_counts.get("MISSING", 0), "Rows missing valuation input.")
    add_metric("invalid_rows_count", status_counts.get("INVALID", 0), "Rows with invalid valuation input.")
    add_metric("not_applicable_rows_count", len(non_standard_rows), "Non-STANDARD rows are outside this valuation contract.")
    add_metric("required_kpis", "; ".join(VALUATION_REQUIRED_KPIS), "Valuation-required KPI fields.")
    add_metric("reason_codes", joined_reasons(reason_union), "Union of valuation contract reason codes.")
    add_metric("no_imputation_confirmed", "True", "Missing valuation values were not calculated or inferred.")
    add_metric("warnings_total", len(warnings), "Validation warnings.")
    return queue_rows, sorted(summary_rows, key=lambda row: row["metric"])


def recommended_action(status: str, reasons: set[str]) -> str:
    if status == "OK":
        return "Reviewed valuation input is valid; downstream apply remains outside this contract patch."
    if "INPUT_FILE_MISSING" in reasons:
        return "Populate a private reviewed valuation input file; do not impute values."
    if "VALUATION_SOURCE_REFERENCE_MISSING" in reasons or "VALUATION_SOURCE_DATE_MISSING" in reasons:
        return "Add reviewed source reference and source date before use."
    if status == "INVALID":
        return "Fix invalid valuation input values or schema before review."
    return "Complete valuation review with approved values and source metadata."


def render_report(summary_rows: list[dict[str, str]], queue_rows: list[dict[str, str]], input_paths: dict[str, str]) -> str:
    summary = {row["metric"]: row["value"] for row in summary_rows}
    status_counts = Counter(row.get("valuation_input_status", "") for row in queue_rows)
    reason_counts = Counter(
        reason
        for row in queue_rows
        for reason in str(row.get("reason_code", "")).split(";")
        if reason
    )
    lines = [
        "# Personal Valuation Input Contract Report",
        "",
        "## Executive Summary",
        f"- Affected STANDARD rows: {summary.get('affected_standard_rows_count', '0')}",
        f"- Queue rows: {summary.get('queue_rows_count', '0')}",
        f"- Approved rows: {summary.get('approved_rows_count', '0')}",
        f"- Missing rows: {summary.get('missing_rows_count', '0')}",
        f"- Invalid rows: {summary.get('invalid_rows_count', '0')}",
        f"- No imputation confirmed: {summary.get('no_imputation_confirmed', 'True')}",
        "",
        "## Input Artifacts",
    ]
    for label, path_value in sorted(input_paths.items()):
        lines.append(f"- `{label}`: `{safe_display_path(path_value)}`")
    lines.extend(
        [
            "",
            "## Valuation Required KPI Contract",
            "- Required fields: `normalized_fcf_yield_pct`, `target_fcf_yield_pct`.",
            "- Values are only valid when numeric, reviewed as `APPROVED`, and backed by source reference and source date.",
            "- Plausibility guardrail is technical only: numeric values must be between -100 and 100.",
            "- Missing values are not calculated, inferred, or written into master/score artifacts by this module.",
            "",
            "## Affected STANDARD Rows",
            "| ticker | isin | company_name | missing_valuation_kpis | valuation_input_status | reason_code |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in queue_rows:
        lines.append(
            f"| {row['ticker']} | {row['isin']} | {row['company_name']} | {row['missing_valuation_kpis']} | "
            f"{row['valuation_input_status']} | {row['reason_code']} |"
        )
    lines.extend(
        [
            "",
            "## Review Queue Summary",
        ]
    )
    for status, count in sorted(status_counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend(
        [
            "",
            "## Optional Review Input Validation",
            f"- Input status: `{summary.get('input_file_status', 'NOT_AVAILABLE')}`",
            f"- Review input path: `{summary.get('review_input_path', '<private_path>')}`",
            "- Private reviewed valuation values are not printed in this report.",
            "",
            "## No-Imputation Guardrail",
            "- This module does not calculate valuation values from price, FCF, or any other field.",
            "- This module does not update the fundamentals master, score audit, company scores, monthly ranking, or watchlist.",
            "",
            "## Reconciliation Impact",
            "- `MISSING_VALUATION_REQUIRED` remains active until approved valuation inputs exist and are applied through a separate reviewed workflow.",
            "- This patch only makes the missing valuation contract and review queue explicit.",
            "",
            "## Remaining Demo Readiness Blockers",
            "- Watchlist sample/review state, provenance gaps, core-data review states, and stale metadata remain outside this patch.",
            "",
            "## Remaining Decision Readiness Blockers",
            "- Valuation-required gaps remain blocked while reviewed inputs are missing or unapplied.",
            "- Dividend/FCF gaps and provenance gaps remain separate blockers.",
            "",
            "## Reason Code Counts",
        ]
    )
    for reason, count in sorted(reason_counts.items()):
        lines.append(f"- `{reason}`: {count}")
    lines.extend(
        [
            "",
            "## Recommended Next Patch",
            "`PATCH / CORE KPI CLOSURE REPORT / REVIEW_CORE_DATA / SEC + MANUAL REVIEW / NO VALUE CHANGES`",
            "",
        ]
    )
    return "\n".join(lines)


def run_personal_valuation_input_contract(
    *,
    kpi_tier_input: str = DEFAULT_KPI_TIER_INPUT,
    scores_input: str = DEFAULT_SCORES_INPUT,
    evidence_applied_master_input: str = DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT,
    review_input: str = DEFAULT_REVIEW_INPUT,
    queue_output: str = DEFAULT_QUEUE_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> ValuationInputContractResult:
    warnings: list[str] = []
    kpi_rows, kpi_warnings, _ = optional_csv_rows(kpi_tier_input, "kpi_tier")
    warnings.extend(kpi_warnings)
    _, score_warnings, _ = optional_csv_rows(scores_input, "scores")
    warnings.extend(score_warnings)
    _, master_warnings, _ = optional_csv_rows(evidence_applied_master_input, "evidence_applied_master")
    warnings.extend(master_warnings)
    review_rows, review_warnings, review_exists = optional_csv_rows(review_input, "valuation_review_input")
    if review_exists:
        warnings.extend(review_warnings)

    queue_rows, summary_rows = build_contract(
        kpi_rows=kpi_rows,
        review_rows=review_rows,
        review_input_exists=review_exists,
        review_input_path=review_input,
        warnings=warnings,
    )
    input_paths = {
        "kpi_tier": kpi_tier_input,
        "scores": scores_input,
        "evidence_applied_master": evidence_applied_master_input,
        "valuation_review_input": review_input,
        "queue_output": queue_output,
        "summary_output": summary_output,
    }
    queue_path = write_csv_rows(queue_output, QUEUE_FIELDS, queue_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(summary_rows, queue_rows, input_paths), encoding="utf-8")
    return ValuationInputContractResult(
        queue_output=queue_path,
        summary_output=summary_path,
        report_output=report_path,
        queue_rows=queue_rows,
        summary_rows=summary_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a reviewed valuation input contract without imputation.")
    parser.add_argument("--kpi-tier-input", default=DEFAULT_KPI_TIER_INPUT)
    parser.add_argument("--scores-input", default=DEFAULT_SCORES_INPUT)
    parser.add_argument("--evidence-applied-master-input", default=DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT)
    parser.add_argument("--review-input", default=DEFAULT_REVIEW_INPUT)
    parser.add_argument("--queue-output", default=DEFAULT_QUEUE_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_valuation_input_contract(
        kpi_tier_input=args.kpi_tier_input,
        scores_input=args.scores_input,
        evidence_applied_master_input=args.evidence_applied_master_input,
        review_input=args.review_input,
        queue_output=args.queue_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    summary = {row["metric"]: row["value"] for row in result.summary_rows}
    print(f"queue_output={result.queue_output}")
    print(f"summary_output={result.summary_output}")
    print(f"report_output={result.report_output}")
    print(f"affected_standard_rows_count={summary.get('affected_standard_rows_count', '0')}")
    print(f"input_file_status={summary.get('input_file_status', 'NOT_AVAILABLE')}")
    print(f"warnings_total={summary.get('warnings_total', '0')}")


if __name__ == "__main__":
    main()
