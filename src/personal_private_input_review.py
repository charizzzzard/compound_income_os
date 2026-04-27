from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import normalize_number_text, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_VALUATION_QUEUE_INPUT = "data/processed/personal_valuation_input_review_queue.csv"
DEFAULT_DIVIDEND_FCF_QUEUE_INPUT = "data/processed/personal_dividend_fcf_input_review_queue.csv"
DEFAULT_VALUATION_PRIVATE_INPUT = "data/raw/private/fundamentals/personal_valuation_review_input.csv"
DEFAULT_DIVIDEND_FCF_PRIVATE_INPUT = "data/raw/private/fundamentals/personal_dividend_fcf_review_input.csv"
DEFAULT_VALIDATION_OUTPUT = "data/processed/personal_private_input_review_validation.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_private_input_review_summary.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_private_input_review_report.md"

VALIDATION_FIELDS = [
    "review_domain",
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "required_kpis",
    "missing_kpi_count",
    "present_kpi_count",
    "approved_kpi_count",
    "invalid_kpi_count",
    "private_input_file_status",
    "row_validation_status",
    "apply_eligibility_status",
    "source_metadata_complete",
    "reason_codes",
]
SUMMARY_FIELDS = [
    "review_domain",
    "input_file_status",
    "queue_rows_count",
    "input_rows_count",
    "approved_rows_count",
    "review_rows_count",
    "missing_rows_count",
    "invalid_rows_count",
    "eligible_for_approved_apply_count",
    "no_imputation_confirmed",
    "private_values_sanitized",
    "reason_codes",
]
VALUATION_KPIS = ("normalized_fcf_yield_pct", "target_fcf_yield_pct")
DIVIDEND_FCF_KPIS = ("fcf_margin", "payout_ratio_fcf", "fcf_per_share_cagr_5y")
REVIEW_STATUSES = {"APPROVED", "REVIEW", "REJECTED", "MISSING"}


@dataclass(frozen=True)
class ReviewDomainSpec:
    name: str
    queue_input: str
    private_input: str
    required_kpis: tuple[str, ...]
    review_status_field: str
    source_type_field: str
    source_reference_field: str
    source_as_of_date_field: str
    required_missing_reason: str
    approved_reason: str
    review_pending_reason: str
    source_reference_missing_reason: str
    source_date_missing_reason: str
    value_invalid_reason: str
    value_out_of_range_reason: str
    min_value: float
    max_value: float


VALUATION_SPEC = ReviewDomainSpec(
    name="VALUATION",
    queue_input=DEFAULT_VALUATION_QUEUE_INPUT,
    private_input=DEFAULT_VALUATION_PRIVATE_INPUT,
    required_kpis=VALUATION_KPIS,
    review_status_field="valuation_review_status",
    source_type_field="valuation_source_type",
    source_reference_field="valuation_source_reference",
    source_as_of_date_field="valuation_source_as_of_date",
    required_missing_reason="VALUATION_REQUIRED_MISSING",
    approved_reason="VALUATION_APPROVED",
    review_pending_reason="VALUATION_REVIEW_PENDING",
    source_reference_missing_reason="VALUATION_SOURCE_REFERENCE_MISSING",
    source_date_missing_reason="VALUATION_SOURCE_DATE_MISSING",
    value_invalid_reason="VALUATION_VALUE_INVALID",
    value_out_of_range_reason="VALUATION_VALUE_OUT_OF_RANGE",
    min_value=-100.0,
    max_value=100.0,
)
DIVIDEND_FCF_SPEC = ReviewDomainSpec(
    name="DIVIDEND_FCF",
    queue_input=DEFAULT_DIVIDEND_FCF_QUEUE_INPUT,
    private_input=DEFAULT_DIVIDEND_FCF_PRIVATE_INPUT,
    required_kpis=DIVIDEND_FCF_KPIS,
    review_status_field="dividend_fcf_review_status",
    source_type_field="dividend_fcf_source_type",
    source_reference_field="dividend_fcf_source_reference",
    source_as_of_date_field="dividend_fcf_source_as_of_date",
    required_missing_reason="DIVIDEND_FCF_REQUIRED_MISSING",
    approved_reason="DIVIDEND_FCF_APPROVED",
    review_pending_reason="DIVIDEND_FCF_REVIEW_PENDING",
    source_reference_missing_reason="DIVIDEND_FCF_SOURCE_REFERENCE_MISSING",
    source_date_missing_reason="DIVIDEND_FCF_SOURCE_DATE_MISSING",
    value_invalid_reason="DIVIDEND_FCF_VALUE_INVALID",
    value_out_of_range_reason="DIVIDEND_FCF_VALUE_OUT_OF_RANGE",
    min_value=-100.0,
    max_value=300.0,
)


@dataclass(frozen=True)
class PrivateInputReviewResult:
    validation_output: Path
    summary_output: Path
    report_output: Path
    validation_rows: list[dict[str, str]]
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


def parse_decimal(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(normalize_number_text(text.replace("%", "")))
    except ValueError:
        return None


def is_blank(value: Any) -> bool:
    return str(value or "").strip() == ""


def identity_key(row: dict[str, str]) -> tuple[str, str]:
    isin = str(row.get("isin", "") or "").strip().upper()
    ticker = str(row.get("ticker", "") or "").strip().upper()
    if isin:
        return isin, ""
    return "", ticker


def row_display_identity(row: dict[str, str]) -> tuple[str, str]:
    return str(row.get("ticker", "") or "").strip(), str(row.get("isin", "") or "").strip()


def required_input_columns(spec: ReviewDomainSpec) -> set[str]:
    return {
        "ticker",
        "isin",
        *spec.required_kpis,
        spec.review_status_field,
        spec.source_type_field,
        spec.source_reference_field,
        spec.source_as_of_date_field,
    }


def schema_valid(rows: list[dict[str, str]], spec: ReviewDomainSpec) -> bool:
    if not rows:
        return True
    return required_input_columns(spec).issubset(set(rows[0].keys()))


def build_review_index(rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str], dict[str, str]], set[tuple[str, str]]]:
    index: dict[tuple[str, str], dict[str, str]] = {}
    duplicates: set[tuple[str, str]] = set()
    for row in rows:
        key = identity_key(row)
        if key == ("", ""):
            continue
        if key in index:
            duplicates.add(key)
        else:
            index[key] = row
    return index, duplicates


def find_review_row(queue_row: dict[str, str], index: dict[tuple[str, str], dict[str, str]]) -> tuple[dict[str, str] | None, tuple[str, str]]:
    key = identity_key(queue_row)
    if key in index:
        return index[key], key
    return None, key


def validate_row(
    *,
    spec: ReviewDomainSpec,
    queue_row: dict[str, str],
    review_row: dict[str, str] | None,
    matched_key: tuple[str, str],
    duplicate_keys: set[tuple[str, str]],
    input_exists: bool,
    input_schema_valid: bool,
) -> dict[str, str]:
    ticker, isin = row_display_identity(queue_row)
    reasons: set[str] = {"NO_IMPUTATION"}
    source_metadata_complete = False
    present_count = 0
    approved_count = 0
    invalid_count = 0

    company_type = safe_upper(queue_row.get("company_type_profile", ""))
    if company_type and company_type != "STANDARD":
        reasons.add("PROFILE_NOT_STANDARD")
        return validation_row(
            spec=spec,
            queue_row=queue_row,
            present_count=0,
            approved_count=0,
            invalid_count=0,
            file_status="PRESENT" if input_exists else "MISSING",
            row_status="NOT_APPLICABLE",
            eligibility="NOT_AVAILABLE",
            source_metadata_complete=False,
            reasons=reasons,
        )

    if not input_exists:
        reasons.add("INPUT_FILE_MISSING")
        reasons.add(spec.required_missing_reason)
        return validation_row(
            spec=spec,
            queue_row=queue_row,
            present_count=0,
            approved_count=0,
            invalid_count=0,
            file_status="MISSING",
            row_status="MISSING",
            eligibility="NOT_AVAILABLE",
            source_metadata_complete=False,
            reasons=reasons,
        )
    if not input_schema_valid:
        reasons.add("INPUT_SCHEMA_INVALID")
        return validation_row(
            spec=spec,
            queue_row=queue_row,
            present_count=0,
            approved_count=0,
            invalid_count=len(spec.required_kpis),
            file_status="INVALID_SCHEMA",
            row_status="INVALID",
            eligibility="NOT_ELIGIBLE",
            source_metadata_complete=False,
            reasons=reasons,
        )
    if matched_key in duplicate_keys:
        reasons.add("DUPLICATE_IDENTITY")
        return validation_row(
            spec=spec,
            queue_row=queue_row,
            present_count=0,
            approved_count=0,
            invalid_count=len(spec.required_kpis),
            file_status="PRESENT",
            row_status="INVALID",
            eligibility="NOT_ELIGIBLE",
            source_metadata_complete=False,
            reasons=reasons,
        )
    if review_row is None:
        reasons.add("INPUT_ROW_MISSING")
        reasons.add("IDENTITY_NOT_FOUND")
        reasons.add(spec.required_missing_reason)
        return validation_row(
            spec=spec,
            queue_row=queue_row,
            present_count=0,
            approved_count=0,
            invalid_count=0,
            file_status="PRESENT",
            row_status="MISSING",
            eligibility="NOT_ELIGIBLE",
            source_metadata_complete=False,
            reasons=reasons,
        )

    reasons.add("IDENTITY_MATCHED")
    missing_count = 0
    for field in spec.required_kpis:
        raw_value = review_row.get(field, "")
        numeric_value = parse_decimal(raw_value)
        if is_blank(raw_value):
            missing_count += 1
            continue
        present_count += 1
        if numeric_value is None:
            invalid_count += 1
            reasons.add(spec.value_invalid_reason)
        elif numeric_value < spec.min_value or numeric_value > spec.max_value:
            invalid_count += 1
            reasons.add(spec.value_out_of_range_reason)

    if missing_count:
        reasons.add(spec.required_missing_reason)
        return validation_row(
            spec=spec,
            queue_row=queue_row,
            present_count=present_count,
            approved_count=0,
            invalid_count=invalid_count,
            file_status="PRESENT",
            row_status="MISSING",
            eligibility="NOT_ELIGIBLE",
            source_metadata_complete=False,
            reasons=reasons,
        )
    if invalid_count:
        return validation_row(
            spec=spec,
            queue_row=queue_row,
            present_count=present_count,
            approved_count=0,
            invalid_count=invalid_count,
            file_status="PRESENT",
            row_status="INVALID",
            eligibility="NOT_ELIGIBLE",
            source_metadata_complete=False,
            reasons=reasons,
        )

    review_status = safe_upper(review_row.get(spec.review_status_field, ""))
    source_type = safe_upper(review_row.get(spec.source_type_field, ""))
    source_reference = str(review_row.get(spec.source_reference_field, "") or "").strip()
    source_as_of_date = str(review_row.get(spec.source_as_of_date_field, "") or "").strip()
    source_metadata_complete = bool(source_type and source_type != "UNKNOWN" and source_reference and source_as_of_date)
    if review_status != "APPROVED":
        reasons.add(spec.review_pending_reason)
        return validation_row(
            spec=spec,
            queue_row=queue_row,
            present_count=present_count,
            approved_count=0,
            invalid_count=0,
            file_status="PRESENT",
            row_status="REVIEW",
            eligibility="NOT_ELIGIBLE",
            source_metadata_complete=source_metadata_complete,
            reasons=reasons,
        )
    if not source_reference:
        reasons.add(spec.source_reference_missing_reason)
    if not source_as_of_date:
        reasons.add(spec.source_date_missing_reason)
    if not source_type or source_type == "UNKNOWN":
        reasons.add(spec.review_pending_reason)
    if not source_metadata_complete:
        return validation_row(
            spec=spec,
            queue_row=queue_row,
            present_count=present_count,
            approved_count=0,
            invalid_count=0,
            file_status="PRESENT",
            row_status="REVIEW",
            eligibility="NOT_ELIGIBLE",
            source_metadata_complete=False,
            reasons=reasons,
        )

    reasons.discard("NO_IMPUTATION")
    reasons.add(spec.approved_reason)
    approved_count = len(spec.required_kpis)
    return validation_row(
        spec=spec,
        queue_row=queue_row,
        present_count=present_count,
        approved_count=approved_count,
        invalid_count=0,
        file_status="PRESENT",
        row_status="APPROVED",
        eligibility="ELIGIBLE_FOR_APPROVED_APPLY",
        source_metadata_complete=True,
        reasons=reasons,
    )


def validation_row(
    *,
    spec: ReviewDomainSpec,
    queue_row: dict[str, str],
    present_count: int,
    approved_count: int,
    invalid_count: int,
    file_status: str,
    row_status: str,
    eligibility: str,
    source_metadata_complete: bool,
    reasons: set[str],
) -> dict[str, str]:
    return {
        "review_domain": spec.name,
        "ticker": str(queue_row.get("ticker", "") or "").strip(),
        "isin": str(queue_row.get("isin", "") or "").strip(),
        "company_name": str(queue_row.get("company_name", "") or "").strip(),
        "company_type_profile": str(queue_row.get("company_type_profile", "") or "").strip(),
        "required_kpis": joined(list(spec.required_kpis)),
        "missing_kpi_count": str(max(len(spec.required_kpis) - present_count, 0)),
        "present_kpi_count": str(present_count),
        "approved_kpi_count": str(approved_count),
        "invalid_kpi_count": str(invalid_count),
        "private_input_file_status": file_status,
        "row_validation_status": row_status,
        "apply_eligibility_status": eligibility,
        "source_metadata_complete": "yes" if source_metadata_complete else "no",
        "reason_codes": joined(reasons),
    }


def validate_domain(
    *,
    spec: ReviewDomainSpec,
    queue_rows: list[dict[str, str]],
    private_rows: list[dict[str, str]],
    private_exists: bool,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    input_schema_valid = schema_valid(private_rows, spec)
    review_index, duplicate_keys = build_review_index(private_rows) if input_schema_valid else ({}, set())
    validation_rows: list[dict[str, str]] = []
    for queue_row in queue_rows:
        review_row, key = find_review_row(queue_row, review_index)
        validation_rows.append(
            validate_row(
                spec=spec,
                queue_row=queue_row,
                review_row=review_row,
                matched_key=key,
                duplicate_keys=duplicate_keys,
                input_exists=private_exists,
                input_schema_valid=input_schema_valid,
            )
        )
    status_counts = {status: sum(1 for row in validation_rows if row["row_validation_status"] == status) for status in ("APPROVED", "REVIEW", "MISSING", "INVALID")}
    eligible_count = sum(1 for row in validation_rows if row["apply_eligibility_status"] == "ELIGIBLE_FOR_APPROVED_APPLY")
    reason_codes = set()
    for row in validation_rows:
        reason_codes.update(item for item in row["reason_codes"].split(";") if item)
    if not private_exists:
        input_file_status = "MISSING"
        reason_codes.add("INPUT_FILE_MISSING")
    elif not input_schema_valid:
        input_file_status = "INVALID_SCHEMA"
        reason_codes.add("INPUT_SCHEMA_INVALID")
    else:
        input_file_status = "PRESENT"
    summary = {
        "review_domain": spec.name,
        "input_file_status": input_file_status,
        "queue_rows_count": str(len(queue_rows)),
        "input_rows_count": str(len(private_rows) if private_exists else 0),
        "approved_rows_count": str(status_counts["APPROVED"]),
        "review_rows_count": str(status_counts["REVIEW"]),
        "missing_rows_count": str(status_counts["MISSING"]),
        "invalid_rows_count": str(status_counts["INVALID"]),
        "eligible_for_approved_apply_count": str(eligible_count),
        "no_imputation_confirmed": "True",
        "private_values_sanitized": "True",
        "reason_codes": joined(reason_codes),
    }
    return validation_rows, summary


def render_report(
    *,
    validation_rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
    input_paths: dict[str, str],
) -> str:
    lines = [
        "# Personal Private Input Review Report",
        "",
        "## 1. Executive Summary",
        "",
        "This workflow validates optional private Valuation and Dividend/FCF review inputs without applying values to fundamentals masters, evidence-applied masters, score audits, or score outputs.",
        "",
        "## 2. Input Queues",
        "",
        f"- Valuation queue: `{input_paths['valuation_queue']}`",
        f"- Dividend/FCF queue: `{input_paths['dividend_fcf_queue']}`",
        "",
        "## 3. Private Input Files",
        "",
        f"- Valuation private input: `{safe_display_path(input_paths['valuation_private'])}`",
        f"- Dividend/FCF private input: `{safe_display_path(input_paths['dividend_fcf_private'])}`",
        "",
        "## 4. Validation Results",
        "",
        "| Domain | Input Status | Queue Rows | Approved | Review | Missing | Invalid | Eligible Apply | Reasons |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary_rows:
        lines.append(
            f"| `{row['review_domain']}` | `{row['input_file_status']}` | `{row['queue_rows_count']}` | `{row['approved_rows_count']}` | `{row['review_rows_count']}` | `{row['missing_rows_count']}` | `{row['invalid_rows_count']}` | `{row['eligible_for_approved_apply_count']}` | `{row['reason_codes']}` |"
        )
    lines.extend(
        [
            "",
            "## 5. Approved Rows",
            "",
            "| Domain | Ticker | ISIN | Eligibility |",
            "| --- | --- | --- | --- |",
        ]
    )
    approved = [row for row in validation_rows if row["row_validation_status"] == "APPROVED"]
    if approved:
        for row in approved:
            lines.append(f"| `{row['review_domain']}` | `{row['ticker']}` | `{row['isin']}` | `{row['apply_eligibility_status']}` |")
    else:
        lines.append("| none |  |  |  |")
    lines.extend(
        [
            "",
            "## 6. Review / Missing / Invalid Rows",
            "",
            "| Domain | Ticker | ISIN | Status | Reasons |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in validation_rows:
        if row["row_validation_status"] != "APPROVED":
            lines.append(f"| `{row['review_domain']}` | `{row['ticker']}` | `{row['isin']}` | `{row['row_validation_status']}` | `{row['reason_codes']}` |")
    lines.extend(
        [
            "",
            "## 7. Sanitization Guarantee",
            "",
            "- Private numeric values are not written to processed validation outputs.",
            "- Private notes are not rendered in this report.",
            "- Private raw input paths are masked.",
            "",
            "## 8. No-Imputation Guardrail",
            "",
            "- Missing values remain missing.",
            "- Values are not calculated from other fields.",
            "- No fallback values are created.",
            "",
            "## 9. Apply Eligibility",
            "",
            "Rows are eligible only when every required field is numeric, in technical range, review status is APPROVED, and source metadata is complete. This patch does not apply eligible rows.",
            "",
            "## 10. Readiness Impact",
            "",
            "Without private inputs, Valuation and Dividend/FCF blockers remain active. Approved eligibility counts are materialized for a future approved-only apply candidate workflow.",
            "",
            "## 11. Remaining Blockers",
            "",
            "- `MISSING_VALUATION_REQUIRED` remains until approved valuation inputs exist and are applied by a future approved-only workflow.",
            "- `MISSING_DIVIDEND_FCF_REQUIRED` remains until approved Dividend/FCF inputs exist and are applied by a future approved-only workflow.",
            "- No master, score, or evidence-apply outputs were changed.",
            "",
            "## 12. Recommended Next Patch",
            "",
            "`PATCH / PRIVATE INPUT APPLY CANDIDATES / APPROVED ONLY / NO MASTER MUTATION`",
            "",
        ]
    )
    return "\n".join(lines)


def run_personal_private_input_review(
    *,
    valuation_queue_input: str = DEFAULT_VALUATION_QUEUE_INPUT,
    dividend_fcf_queue_input: str = DEFAULT_DIVIDEND_FCF_QUEUE_INPUT,
    valuation_private_input: str = DEFAULT_VALUATION_PRIVATE_INPUT,
    dividend_fcf_private_input: str = DEFAULT_DIVIDEND_FCF_PRIVATE_INPUT,
    validation_output: str = DEFAULT_VALIDATION_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> PrivateInputReviewResult:
    warnings: list[str] = []
    valuation_queue_rows, valuation_queue_exists, valuation_queue_warnings = optional_csv_rows(valuation_queue_input, "valuation_queue")
    dividend_queue_rows, dividend_queue_exists, dividend_queue_warnings = optional_csv_rows(dividend_fcf_queue_input, "dividend_fcf_queue")
    valuation_private_rows, valuation_private_exists, valuation_private_warnings = optional_csv_rows(valuation_private_input, "valuation_private_input")
    dividend_private_rows, dividend_private_exists, dividend_private_warnings = optional_csv_rows(dividend_fcf_private_input, "dividend_fcf_private_input")
    warnings.extend(valuation_queue_warnings)
    warnings.extend(dividend_queue_warnings)
    warnings.extend(valuation_private_warnings)
    warnings.extend(dividend_private_warnings)
    if not valuation_queue_exists:
        valuation_queue_rows = []
    if not dividend_queue_exists:
        dividend_queue_rows = []

    valuation_rows, valuation_summary = validate_domain(
        spec=VALUATION_SPEC,
        queue_rows=valuation_queue_rows,
        private_rows=valuation_private_rows,
        private_exists=valuation_private_exists,
    )
    dividend_rows, dividend_summary = validate_domain(
        spec=DIVIDEND_FCF_SPEC,
        queue_rows=dividend_queue_rows,
        private_rows=dividend_private_rows,
        private_exists=dividend_private_exists,
    )
    validation_rows = valuation_rows + dividend_rows
    summary_rows = [valuation_summary, dividend_summary]
    validation_path = write_csv_rows(validation_output, VALIDATION_FIELDS, validation_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_report(
            validation_rows=validation_rows,
            summary_rows=summary_rows,
            input_paths={
                "valuation_queue": valuation_queue_input,
                "dividend_fcf_queue": dividend_fcf_queue_input,
                "valuation_private": valuation_private_input,
                "dividend_fcf_private": dividend_fcf_private_input,
            },
        ),
        encoding="utf-8",
    )
    return PrivateInputReviewResult(
        validation_output=validation_path,
        summary_output=summary_path,
        report_output=report_path,
        validation_rows=validation_rows,
        summary_rows=summary_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate optional private Valuation and Dividend/FCF review inputs without applying values.")
    parser.add_argument("--validation-output", default=DEFAULT_VALIDATION_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_private_input_review(
        validation_output=args.validation_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    print(f"validation_output={result.validation_output}")
    print(f"summary_output={result.summary_output}")
    print(f"report_output={result.report_output}")
    print(f"validation_rows={len(result.validation_rows)}")
    print(f"warnings_total={len(result.warnings)}")


if __name__ == "__main__":
    main()
