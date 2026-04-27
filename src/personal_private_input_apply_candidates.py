from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_REVIEW_VALIDATION_INPUT = "data/processed/personal_private_input_review_validation.csv"
DEFAULT_REVIEW_SUMMARY_INPUT = "data/processed/personal_private_input_review_summary.csv"
DEFAULT_VALUATION_PRIVATE_INPUT = "data/raw/private/fundamentals/personal_valuation_review_input.csv"
DEFAULT_DIVIDEND_FCF_PRIVATE_INPUT = "data/raw/private/fundamentals/personal_dividend_fcf_review_input.csv"
DEFAULT_PRIVATE_CANDIDATE_OUTPUT = "data/raw/private/fundamentals/personal_private_input_apply_candidates.csv"
DEFAULT_SANITIZED_OUTPUT = "data/processed/personal_private_input_apply_candidates_sanitized.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_private_input_apply_candidates_summary.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_private_input_apply_candidates_report.md"

VALUATION_KPIS = ("normalized_fcf_yield_pct", "target_fcf_yield_pct")
DIVIDEND_FCF_KPIS = ("fcf_margin", "payout_ratio_fcf", "fcf_per_share_cagr_5y")
SANITIZED_FIELDS = [
    "review_domain",
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "required_kpis",
    "approved_kpi_count",
    "candidate_kpi_count",
    "private_value_present",
    "source_metadata_complete",
    "apply_candidate_status",
    "apply_candidate_scope",
    "would_update_fields",
    "reason_codes",
]
SUMMARY_FIELDS = [
    "review_domain",
    "input_file_status",
    "review_rows_count",
    "approved_rows_count",
    "candidate_rows_count",
    "candidate_fields_count",
    "not_ready_rows_count",
    "invalid_rows_count",
    "private_candidate_file_created",
    "private_values_in_public_outputs",
    "master_mutation_performed",
    "score_mutation_performed",
    "no_imputation_confirmed",
    "reason_codes",
]
PRIVATE_FIELDS = [
    "review_domain",
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "kpi_name",
    "approved_value",
    "source_type",
    "source_name",
    "source_reference",
    "source_as_of_date",
    "reviewed_by",
    "reviewed_at",
    "apply_candidate_status",
]


@dataclass(frozen=True)
class DomainSpec:
    name: str
    required_kpis: tuple[str, ...]
    review_status_field: str
    source_type_field: str
    source_name_field: str
    source_reference_field: str
    source_as_of_date_field: str
    reviewed_by_field: str
    reviewed_at_field: str


VALUATION_SPEC = DomainSpec(
    name="VALUATION",
    required_kpis=VALUATION_KPIS,
    review_status_field="valuation_review_status",
    source_type_field="valuation_source_type",
    source_name_field="valuation_source_name",
    source_reference_field="valuation_source_reference",
    source_as_of_date_field="valuation_source_as_of_date",
    reviewed_by_field="valuation_reviewed_by",
    reviewed_at_field="valuation_reviewed_at",
)
DIVIDEND_FCF_SPEC = DomainSpec(
    name="DIVIDEND_FCF",
    required_kpis=DIVIDEND_FCF_KPIS,
    review_status_field="dividend_fcf_review_status",
    source_type_field="dividend_fcf_source_type",
    source_name_field="dividend_fcf_source_name",
    source_reference_field="dividend_fcf_source_reference",
    source_as_of_date_field="dividend_fcf_source_as_of_date",
    reviewed_by_field="dividend_fcf_reviewed_by",
    reviewed_at_field="dividend_fcf_reviewed_at",
)


@dataclass(frozen=True)
class PrivateInputApplyCandidatesResult:
    sanitized_output: Path
    summary_output: Path
    report_output: Path
    private_candidate_output: Path | None
    sanitized_rows: list[dict[str, str]]
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


def split_reasons(value: Any) -> set[str]:
    return {item.strip() for item in str(value or "").split(";") if item.strip()}


def identity_key(row: dict[str, str]) -> tuple[str, str]:
    isin = str(row.get("isin", "") or "").strip().upper()
    ticker = str(row.get("ticker", "") or "").strip().upper()
    if isin:
        return isin, ""
    return "", ticker


def build_private_index(rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str], dict[str, str]], set[tuple[str, str]]]:
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


def rows_for_domain(rows: list[dict[str, str]], domain: str) -> list[dict[str, str]]:
    return [row for row in rows if safe_upper(row.get("review_domain", "")) == domain]


def domain_summary(rows: list[dict[str, str]], domain: str) -> dict[str, str]:
    for row in rows:
        if safe_upper(row.get("review_domain", "")) == domain:
            return row
    return {}


def make_sanitized_row(
    validation_row: dict[str, str],
    *,
    status: str,
    scope: str,
    candidate_kpi_count: int,
    private_value_present: bool,
    would_update_fields: tuple[str, ...],
    reasons: set[str],
) -> dict[str, str]:
    return {
        "review_domain": validation_row.get("review_domain", ""),
        "ticker": validation_row.get("ticker", ""),
        "isin": validation_row.get("isin", ""),
        "company_name": validation_row.get("company_name", ""),
        "company_type_profile": validation_row.get("company_type_profile", ""),
        "required_kpis": validation_row.get("required_kpis", ""),
        "approved_kpi_count": validation_row.get("approved_kpi_count", "0"),
        "candidate_kpi_count": str(candidate_kpi_count),
        "private_value_present": "yes" if private_value_present else "no",
        "source_metadata_complete": validation_row.get("source_metadata_complete", "no"),
        "apply_candidate_status": status,
        "apply_candidate_scope": scope,
        "would_update_fields": joined(list(would_update_fields)),
        "reason_codes": joined(reasons),
    }


def source_metadata_complete(private_row: dict[str, str], spec: DomainSpec) -> bool:
    return bool(
        str(private_row.get(spec.source_type_field, "") or "").strip()
        and safe_upper(private_row.get(spec.source_type_field, "")) != "UNKNOWN"
        and str(private_row.get(spec.source_reference_field, "") or "").strip()
        and str(private_row.get(spec.source_as_of_date_field, "") or "").strip()
    )


def build_private_candidate_rows(
    *,
    validation_row: dict[str, str],
    private_row: dict[str, str],
    spec: DomainSpec,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for field in spec.required_kpis:
        rows.append(
            {
                "review_domain": spec.name,
                "ticker": validation_row.get("ticker", ""),
                "isin": validation_row.get("isin", ""),
                "company_name": validation_row.get("company_name", ""),
                "company_type_profile": validation_row.get("company_type_profile", ""),
                "kpi_name": field,
                "approved_value": private_row.get(field, ""),
                "source_type": private_row.get(spec.source_type_field, ""),
                "source_name": private_row.get(spec.source_name_field, ""),
                "source_reference": private_row.get(spec.source_reference_field, ""),
                "source_as_of_date": private_row.get(spec.source_as_of_date_field, ""),
                "reviewed_by": private_row.get(spec.reviewed_by_field, ""),
                "reviewed_at": private_row.get(spec.reviewed_at_field, ""),
                "apply_candidate_status": "READY_FOR_PRIVATE_APPLY_REVIEW",
            }
        )
    return rows


def build_candidates_for_domain(
    *,
    spec: DomainSpec,
    validation_rows: list[dict[str, str]],
    review_summary_rows: list[dict[str, str]],
    private_rows: list[dict[str, str]],
    private_exists: bool,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, str]]:
    review_summary = domain_summary(review_summary_rows, spec.name)
    private_index, duplicate_keys = build_private_index(private_rows)
    sanitized_rows: list[dict[str, str]] = []
    private_candidate_rows: list[dict[str, str]] = []
    for row in rows_for_domain(validation_rows, spec.name):
        reasons = split_reasons(row.get("reason_codes", ""))
        reasons.update({"PUBLIC_OUTPUT_SANITIZED", "NO_MASTER_MUTATION", "NO_SCORE_MUTATION", "NO_IMPUTATION"})
        key = identity_key(row)
        private_row = private_index.get(key)
        if key in duplicate_keys:
            reasons.add("DUPLICATE_IDENTITY")
            sanitized_rows.append(
                make_sanitized_row(
                    row,
                    status="INVALID",
                    scope="NONE",
                    candidate_kpi_count=0,
                    private_value_present=False,
                    would_update_fields=(),
                    reasons=reasons,
                )
            )
            continue
        if not private_exists:
            reasons.add("INPUT_FILE_MISSING")
            reasons.add("NO_APPROVED_INPUTS")
            sanitized_rows.append(
                make_sanitized_row(
                    row,
                    status="NOT_AVAILABLE",
                    scope="NONE",
                    candidate_kpi_count=0,
                    private_value_present=False,
                    would_update_fields=(),
                    reasons=reasons,
                )
            )
            continue
        if row.get("row_validation_status") != "APPROVED" or row.get("apply_eligibility_status") != "ELIGIBLE_FOR_APPROVED_APPLY":
            if row.get("row_validation_status") == "INVALID":
                status = "INVALID"
            else:
                status = "NOT_READY"
            if "SOURCE_REFERENCE_MISSING" in joined(reasons) or "SOURCE_DATE_MISSING" in joined(reasons):
                reasons.add("SOURCE_METADATA_MISSING")
            sanitized_rows.append(
                make_sanitized_row(
                    row,
                    status=status,
                    scope="NONE",
                    candidate_kpi_count=0,
                    private_value_present=False,
                    would_update_fields=(),
                    reasons=reasons,
                )
            )
            continue
        if private_row is None:
            reasons.add("IDENTITY_NOT_FOUND")
            sanitized_rows.append(
                make_sanitized_row(
                    row,
                    status="NOT_READY",
                    scope="NONE",
                    candidate_kpi_count=0,
                    private_value_present=False,
                    would_update_fields=(),
                    reasons=reasons,
                )
            )
            continue
        if not source_metadata_complete(private_row, spec):
            reasons.add("SOURCE_METADATA_MISSING")
            sanitized_rows.append(
                make_sanitized_row(
                    row,
                    status="NOT_READY",
                    scope="NONE",
                    candidate_kpi_count=0,
                    private_value_present=False,
                    would_update_fields=(),
                    reasons=reasons,
                )
            )
            continue
        missing_value_fields = tuple(field for field in spec.required_kpis if not str(private_row.get(field, "") or "").strip())
        if missing_value_fields:
            reasons.add("VALUE_MISSING")
            sanitized_rows.append(
                make_sanitized_row(
                    row,
                    status="NOT_READY",
                    scope="NONE",
                    candidate_kpi_count=0,
                    private_value_present=False,
                    would_update_fields=(),
                    reasons=reasons,
                )
            )
            continue
        reasons.add("APPROVED_INPUT_READY")
        sanitized_rows.append(
            make_sanitized_row(
                row,
                status="READY_FOR_PRIVATE_APPLY_REVIEW",
                scope="PRIVATE_ONLY",
                candidate_kpi_count=len(spec.required_kpis),
                private_value_present=True,
                would_update_fields=spec.required_kpis,
                reasons=reasons,
            )
        )
        private_candidate_rows.extend(build_private_candidate_rows(validation_row=row, private_row=private_row, spec=spec))

    counts = Counter(row["apply_candidate_status"] for row in sanitized_rows)
    reason_codes: set[str] = set()
    for row in sanitized_rows:
        reason_codes.update(split_reasons(row.get("reason_codes", "")))
    if not private_candidate_rows:
        reason_codes.add("NO_APPROVED_INPUTS")
    summary = {
        "review_domain": spec.name,
        "input_file_status": review_summary.get("input_file_status", "NOT_AVAILABLE"),
        "review_rows_count": str(len(rows_for_domain(validation_rows, spec.name))),
        "approved_rows_count": review_summary.get("approved_rows_count", "0"),
        "candidate_rows_count": str(counts.get("READY_FOR_PRIVATE_APPLY_REVIEW", 0)),
        "candidate_fields_count": str(sum(int(row["candidate_kpi_count"]) for row in sanitized_rows)),
        "not_ready_rows_count": str(counts.get("NOT_READY", 0) + counts.get("NOT_AVAILABLE", 0)),
        "invalid_rows_count": str(counts.get("INVALID", 0)),
        "private_candidate_file_created": "False",
        "private_values_in_public_outputs": "False",
        "master_mutation_performed": "False",
        "score_mutation_performed": "False",
        "no_imputation_confirmed": "True",
        "reason_codes": joined(reason_codes),
    }
    return sanitized_rows, private_candidate_rows, summary


def render_report(
    *,
    sanitized_rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
    private_candidate_output: str,
    private_file_created: bool,
) -> str:
    lines = [
        "# Personal Private Input Apply Candidates Report",
        "",
        "## 1. Executive Summary",
        "",
        "This companion layer derives approved-only private apply candidates from the sanitized private input review validation. It does not apply values to fundamentals masters, evidence-applied masters, score audits, scores, or watchlist outputs.",
        "",
        "## 2. Input Review Summary",
        "",
        "| Domain | Input Status | Review Rows | Approved Rows | Candidate Rows | Candidate Fields | Reasons |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary_rows:
        lines.append(
            f"| `{row['review_domain']}` | `{row['input_file_status']}` | `{row['review_rows_count']}` | `{row['approved_rows_count']}` | `{row['candidate_rows_count']}` | `{row['candidate_fields_count']}` | `{row['reason_codes']}` |"
        )
    lines.extend(
        [
            "",
            "## 3. Candidate Generation Rules",
            "",
            "- `row_validation_status` must be `APPROVED`.",
            "- `apply_eligibility_status` must be `ELIGIBLE_FOR_APPROVED_APPLY`.",
            "- Source metadata must be complete.",
            "- Private values must be present in the private input file.",
            "- Public candidate outputs contain field names and statuses only, never private numeric values.",
            "",
            "## 4. Sanitized Public Candidate Outputs",
            "",
            "| Domain | Ticker | ISIN | Status | Scope | Fields | Reasons |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    if sanitized_rows:
        for row in sanitized_rows:
            lines.append(
                f"| `{row['review_domain']}` | `{row['ticker']}` | `{row['isin']}` | `{row['apply_candidate_status']}` | `{row['apply_candidate_scope']}` | `{row['would_update_fields']}` | `{row['reason_codes']}` |"
            )
    else:
        lines.append("| none |  |  |  |  |  |  |")
    lines.extend(
        [
            "",
            "## 5. Private Candidate File Status",
            "",
            f"- Private candidate file path: `{safe_display_path(private_candidate_output)}`",
            f"- Private candidate file created: `{private_file_created}`",
            "",
            "## 6. Approved Candidate Counts",
            "",
        ]
    )
    for row in summary_rows:
        lines.append(f"- `{row['review_domain']}`: `{row['candidate_rows_count']}` candidate rows, `{row['candidate_fields_count']}` candidate fields.")
    lines.extend(
        [
            "",
            "## 7. Not Ready / Missing / Invalid Rows",
            "",
        ]
    )
    not_ready = [row for row in sanitized_rows if row["apply_candidate_status"] != "READY_FOR_PRIVATE_APPLY_REVIEW"]
    if not_ready:
        for row in not_ready:
            lines.append(f"- `{row['review_domain']}` `{row['ticker']}` `{row['isin']}`: `{row['apply_candidate_status']}` because `{row['reason_codes']}`.")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## 8. No-Master-Mutation Guardrail",
            "",
            "- `master_mutation_performed=False`.",
            "- `score_mutation_performed=False`.",
            "- Evidence-applied masters and score audits are not written by this layer.",
            "",
            "## 9. No-Private-Value-Leakage Check",
            "",
            "- Public CSV and Markdown outputs are sanitized.",
            "- Private candidate values, when present, are written only to the private raw path.",
            "",
            "## 10. Readiness Impact",
            "",
            "This patch does not resolve valuation or Dividend/FCF readiness blockers. It only prepares approved private candidates for a future explicit apply workflow.",
            "",
            "## 11. Remaining Blockers",
            "",
            "- `MISSING_VALUATION_REQUIRED` remains until approved values are applied by a future explicit patch.",
            "- `MISSING_DIVIDEND_FCF_REQUIRED` remains until approved values are applied by a future explicit patch.",
            "",
            "## 12. Recommended Next Patch",
            "",
            "`PATCH / SEC CORE KPI REFRESH PLAN / APPROVED IDENTITIES ONLY / NO NETWORK BY DEFAULT`",
            "",
        ]
    )
    return "\n".join(lines)


def run_personal_private_input_apply_candidates(
    *,
    review_validation_input: str = DEFAULT_REVIEW_VALIDATION_INPUT,
    review_summary_input: str = DEFAULT_REVIEW_SUMMARY_INPUT,
    valuation_private_input: str = DEFAULT_VALUATION_PRIVATE_INPUT,
    dividend_fcf_private_input: str = DEFAULT_DIVIDEND_FCF_PRIVATE_INPUT,
    private_candidate_output: str = DEFAULT_PRIVATE_CANDIDATE_OUTPUT,
    sanitized_output: str = DEFAULT_SANITIZED_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> PrivateInputApplyCandidatesResult:
    warnings: list[str] = []
    validation_rows, validation_exists, validation_warnings = optional_csv_rows(review_validation_input, "review_validation")
    review_summary_rows, summary_exists, summary_warnings = optional_csv_rows(review_summary_input, "review_summary")
    valuation_private_rows, valuation_private_exists, valuation_warnings = optional_csv_rows(valuation_private_input, "valuation_private_input")
    dividend_private_rows, dividend_private_exists, dividend_warnings = optional_csv_rows(dividend_fcf_private_input, "dividend_fcf_private_input")
    warnings.extend(validation_warnings)
    warnings.extend(summary_warnings)
    warnings.extend(valuation_warnings)
    warnings.extend(dividend_warnings)
    if not validation_exists:
        validation_rows = []
    if not summary_exists:
        review_summary_rows = []

    valuation_sanitized, valuation_private_candidates, valuation_summary = build_candidates_for_domain(
        spec=VALUATION_SPEC,
        validation_rows=validation_rows,
        review_summary_rows=review_summary_rows,
        private_rows=valuation_private_rows,
        private_exists=valuation_private_exists,
    )
    dividend_sanitized, dividend_private_candidates, dividend_summary = build_candidates_for_domain(
        spec=DIVIDEND_FCF_SPEC,
        validation_rows=validation_rows,
        review_summary_rows=review_summary_rows,
        private_rows=dividend_private_rows,
        private_exists=dividend_private_exists,
    )
    sanitized_rows = valuation_sanitized + dividend_sanitized
    private_candidate_rows = valuation_private_candidates + dividend_private_candidates
    private_file_created = bool(private_candidate_rows)
    if private_file_created:
        for summary in (valuation_summary, dividend_summary):
            summary["private_candidate_file_created"] = "True" if int(summary["candidate_rows_count"]) > 0 else "False"
            if summary["private_candidate_file_created"] == "True":
                reasons = split_reasons(summary["reason_codes"])
                reasons.add("PRIVATE_CANDIDATE_FILE_CREATED")
                summary["reason_codes"] = joined(reasons)
        write_csv_rows(private_candidate_output, PRIVATE_FIELDS, private_candidate_rows)

    summary_rows = [valuation_summary, dividend_summary]
    sanitized_path = write_csv_rows(sanitized_output, SANITIZED_FIELDS, sanitized_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_report(
            sanitized_rows=sanitized_rows,
            summary_rows=summary_rows,
            private_candidate_output=private_candidate_output,
            private_file_created=private_file_created,
        ),
        encoding="utf-8",
    )
    return PrivateInputApplyCandidatesResult(
        sanitized_output=sanitized_path,
        summary_output=summary_path,
        report_output=report_path,
        private_candidate_output=resolve_repo_path(private_candidate_output) if private_file_created else None,
        sanitized_rows=sanitized_rows,
        summary_rows=summary_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Derive approved-only private input apply candidates without mutating masters or scores.")
    parser.add_argument("--sanitized-output", default=DEFAULT_SANITIZED_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--private-candidate-output", default=DEFAULT_PRIVATE_CANDIDATE_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_private_input_apply_candidates(
        sanitized_output=args.sanitized_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
        private_candidate_output=args.private_candidate_output,
    )
    candidate_rows = sum(int(row["candidate_rows_count"]) for row in result.summary_rows)
    print(f"sanitized_output={result.sanitized_output}")
    print(f"summary_output={result.summary_output}")
    print(f"report_output={result.report_output}")
    print(f"candidate_rows={candidate_rows}")
    print(f"private_candidate_output={result.private_candidate_output or 'NOT_CREATED'}")
    print(f"warnings_total={len(result.warnings)}")


if __name__ == "__main__":
    main()
