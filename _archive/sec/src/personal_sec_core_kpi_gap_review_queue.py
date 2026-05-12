from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_IMPACT_INPUT = "data/processed/personal_sec_core_kpi_closure_impact_after_reviewed_apply.csv"
DEFAULT_IMPACT_SUMMARY_INPUT = "data/processed/personal_sec_core_kpi_closure_impact_after_reviewed_apply_summary.csv"
DEFAULT_EVIDENCE_APPLIED_MASTER = "data/processed/personal_fundamentals_master_sec_derived_kpi_applied.csv"
DEFAULT_QUEUE_OUTPUT = "data/processed/personal_sec_core_kpi_gap_review_queue.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_sec_core_kpi_gap_review_queue_summary.csv"
DEFAULT_REPORT_OUTPUT = "reports/2026-04-28/personal_sec_core_kpi_gap_review_queue_report.md"

SEC_SOURCEABLE_CORE_KPIS = {
    "revenue_cagr_5y",
    "eps_cagr_5y",
    "gross_margin",
    "operating_margin",
    "share_count_cagr_5y",
}

PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

QUEUE_FIELDS = [
    "review_id",
    "ticker",
    "isin",
    "company_name",
    "kpi_field",
    "current_value",
    "baseline_value",
    "evidence_applied_value",
    "closure_status",
    "stale_or_old_fiscal_year",
    "stale_reason",
    "fiscal_year_end",
    "source_as_of_date",
    "source_forms",
    "review_bucket",
    "priority",
    "recommended_action",
    "evidence_id",
    "evidence_confidence",
    "notes",
]

SUMMARY_FIELDS = [
    "total_review_rows",
    "still_missing_rows",
    "stale_value_rows",
    "high_priority_rows",
    "medium_priority_rows",
    "low_priority_rows",
    "sec_refresh_candidate_rows",
    "manual_review_required_rows",
    "non_sec_source_required_rows",
    "stale_value_review_rows",
    "blocked_by_missing_identity_rows",
    "no_score_change_confirmed",
    "no_network_confirmed",
    "raw_master_mutation_performed",
]

IMPACT_REQUIRED_COLUMNS = [
    "ticker",
    "isin",
    "company_name",
    "kpi_field",
    "baseline_value",
    "evidence_applied_value",
    "closure_status",
    "stale_or_old_fiscal_year",
    "stale_reason",
    "fiscal_year_end",
    "source_as_of_date",
    "source_forms",
    "evidence_id",
    "evidence_confidence",
]

SUMMARY_REQUIRED_COLUMNS = ["no_score_change_confirmed", "no_network_confirmed", "raw_master_mutation_performed"]


@dataclass(frozen=True)
class GapReviewQueueResult:
    queue_path: Path
    summary_path: Path
    report_path: Path
    summary: dict[str, str]
    queue_rows: list[dict[str, str]]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _upper(value: Any) -> str:
    return safe_upper(value)


def _is_true(value: Any) -> bool:
    return _clean(value).lower() in {"1", "true", "yes", "y"}


def _is_missing_value(value: Any) -> bool:
    return _upper(value) in {"", "MISSING", "MISSING_DATA", "REVIEW", "N/A", "NA"}


def _require_file(path_value: str | Path, error_code: str) -> Path:
    path = resolve_repo_path(path_value)
    if not path.exists():
        raise RuntimeError(error_code)
    return path


def _read_header(path_value: str | Path) -> list[str]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or [])


def _require_columns(rows: list[dict[str, str]], required: list[str], source_name: str) -> None:
    if not rows:
        raise ValueError(f"{source_name} contains no rows")
    available = set(rows[0].keys())
    missing = [column for column in required if column not in available]
    if missing:
        raise ValueError(f"{source_name} missing required columns: {', '.join(sorted(missing))}")


def classify_review_bucket(row: dict[str, str]) -> str:
    if not _clean(row.get("isin")) and not _clean(row.get("ticker")):
        return "BLOCKED_BY_MISSING_IDENTITY"
    if _is_true(row.get("stale_or_old_fiscal_year")):
        return "STALE_VALUE_REVIEW"
    kpi = _clean(row.get("kpi_field"))
    if _upper(row.get("closure_status")) == "STILL_MISSING":
        if kpi in SEC_SOURCEABLE_CORE_KPIS:
            return "SEC_REFRESH_CANDIDATE"
        return "NON_SEC_SOURCE_REQUIRED"
    return "MANUAL_REVIEW_REQUIRED"


def priority_for_bucket(row: dict[str, str], bucket: str) -> str:
    if bucket in {"STALE_VALUE_REVIEW", "SEC_REFRESH_CANDIDATE", "BLOCKED_BY_MISSING_IDENTITY"}:
        return "HIGH"
    if bucket in {"MANUAL_REVIEW_REQUIRED", "NON_SEC_SOURCE_REQUIRED"}:
        return "MEDIUM"
    return "LOW"


def recommended_action(bucket: str, row: dict[str, str]) -> str:
    if bucket == "STALE_VALUE_REVIEW":
        return "Review stale SEC-derived KPI before treating it as current; refresh or replace with newer fiscal-year evidence."
    if bucket == "SEC_REFRESH_CANDIDATE":
        return "Run targeted SEC CompanyFacts extraction/period-selection review for this missing required KPI."
    if bucket == "BLOCKED_BY_MISSING_IDENTITY":
        return "Resolve ticker/ISIN/SEC identity before any downstream SEC workflow."
    if bucket == "NON_SEC_SOURCE_REQUIRED":
        return "Use manual or non-SEC fundamentals evidence; do not infer this KPI from SEC CompanyFacts alone."
    return "Human review required to classify source path and KPI semantics."


def select_review_rows(impact_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in impact_rows
        if _upper(row.get("closure_status")) == "STILL_MISSING" or _is_true(row.get("stale_or_old_fiscal_year"))
    ]


def build_queue_rows(impact_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for row in select_review_rows(impact_rows):
        bucket = classify_review_bucket(row)
        priority = priority_for_bucket(row, bucket)
        current_value = _clean(row.get("evidence_applied_value"))
        candidates.append(
            {
                "review_id": "",
                "ticker": _clean(row.get("ticker")),
                "isin": _upper(row.get("isin")),
                "company_name": _clean(row.get("company_name")),
                "kpi_field": _clean(row.get("kpi_field")),
                "current_value": current_value,
                "baseline_value": _clean(row.get("baseline_value")),
                "evidence_applied_value": _clean(row.get("evidence_applied_value")),
                "closure_status": _clean(row.get("closure_status")),
                "stale_or_old_fiscal_year": str(_is_true(row.get("stale_or_old_fiscal_year"))),
                "stale_reason": _clean(row.get("stale_reason")),
                "fiscal_year_end": _clean(row.get("fiscal_year_end")),
                "source_as_of_date": _clean(row.get("source_as_of_date")),
                "source_forms": _clean(row.get("source_forms")),
                "review_bucket": bucket,
                "priority": priority,
                "recommended_action": recommended_action(bucket, row),
                "evidence_id": _clean(row.get("evidence_id")),
                "evidence_confidence": _clean(row.get("evidence_confidence")),
                "notes": "Review-only queue row; no KPI value applied, no score recalculated, no network fetch used.",
            }
        )
    candidates.sort(
        key=lambda row: (
            PRIORITY_ORDER.get(row["priority"], 9),
            row["review_bucket"],
            row["isin"],
            row["ticker"],
            row["kpi_field"],
        )
    )
    for idx, row in enumerate(candidates, start=1):
        row["review_id"] = f"SEC_GAP_REVIEW_{idx:04d}"
    return candidates


def build_summary(queue_rows: list[dict[str, str]], impact_summary_rows: list[dict[str, str]]) -> dict[str, str]:
    impact_summary = impact_summary_rows[0] if impact_summary_rows else {}

    def count(field: str, value: str) -> int:
        return sum(1 for row in queue_rows if row.get(field) == value)

    return {
        "total_review_rows": str(len(queue_rows)),
        "still_missing_rows": str(count("closure_status", "STILL_MISSING")),
        "stale_value_rows": str(count("stale_or_old_fiscal_year", "True")),
        "high_priority_rows": str(count("priority", "HIGH")),
        "medium_priority_rows": str(count("priority", "MEDIUM")),
        "low_priority_rows": str(count("priority", "LOW")),
        "sec_refresh_candidate_rows": str(count("review_bucket", "SEC_REFRESH_CANDIDATE")),
        "manual_review_required_rows": str(count("review_bucket", "MANUAL_REVIEW_REQUIRED")),
        "non_sec_source_required_rows": str(count("review_bucket", "NON_SEC_SOURCE_REQUIRED")),
        "stale_value_review_rows": str(count("review_bucket", "STALE_VALUE_REVIEW")),
        "blocked_by_missing_identity_rows": str(count("review_bucket", "BLOCKED_BY_MISSING_IDENTITY")),
        "no_score_change_confirmed": _clean(impact_summary.get("no_score_change_confirmed")) or "True",
        "no_network_confirmed": _clean(impact_summary.get("no_network_confirmed")) or "True",
        "raw_master_mutation_performed": _clean(impact_summary.get("raw_master_mutation_performed")) or "False",
    }


def render_report(summary: dict[str, str], queue_rows: list[dict[str, str]]) -> str:
    missing_rows = [row for row in queue_rows if row["closure_status"] == "STILL_MISSING"]
    stale_rows = [row for row in queue_rows if row["stale_or_old_fiscal_year"] == "True"]
    lines = [
        "# SEC Core KPI Gap Review Queue",
        "",
        "## Executive Summary",
        "",
        f"- Total review rows: {summary['total_review_rows']}",
        f"- Still missing rows: {summary['still_missing_rows']}",
        f"- Stale value rows: {summary['stale_value_rows']}",
        f"- High priority rows: {summary['high_priority_rows']}",
        "- No KPI values were applied by this queue.",
        f"- No scores were changed: {summary['no_score_change_confirmed']}",
        f"- No network fetch was used: {summary['no_network_confirmed']}",
        "",
        "## Remaining Missing KPIs",
        "",
    ]
    if missing_rows:
        for row in missing_rows:
            lines.append(f"- `{row['company_name']}` `{row['kpi_field']}` -> {row['review_bucket']} / {row['priority']}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Stale Value Warnings", ""])
    if stale_rows:
        for row in stale_rows:
            lines.append(f"- `{row['company_name']}` `{row['kpi_field']}` current_value={row['current_value']}: {row['stale_reason']}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Review Buckets", ""])
    for bucket in [
        "SEC_REFRESH_CANDIDATE",
        "MANUAL_REVIEW_REQUIRED",
        "NON_SEC_SOURCE_REQUIRED",
        "STALE_VALUE_REVIEW",
        "BLOCKED_BY_MISSING_IDENTITY",
    ]:
        key = f"{bucket.lower()}_rows"
        lines.append(f"- `{bucket}`: {summary[key]}")

    lines.extend(
        [
            "",
            "## Priority Breakdown",
            "",
            f"- HIGH: {summary['high_priority_rows']}",
            f"- MEDIUM: {summary['medium_priority_rows']}",
            f"- LOW: {summary['low_priority_rows']}",
            "",
            "## Recommended Next Action",
            "",
            "SEC COMPANYFACTS PERIOD SELECTION REVIEW / REMAINING CORE KPI GAPS / NO SCORE CHANGES",
            "",
            "## Guardrails",
            "",
            "- no_value_apply_confirmed=True",
            "- no_score_change_confirmed=True",
            "- no_network_confirmed=True",
            "- raw_master_mutation_performed=False",
            "- no_imputation_confirmed=True",
        ]
    )
    return "\n".join(lines) + "\n"


def run_personal_sec_core_kpi_gap_review_queue(
    *,
    impact_input: str | Path = DEFAULT_IMPACT_INPUT,
    impact_summary_input: str | Path = DEFAULT_IMPACT_SUMMARY_INPUT,
    evidence_applied_master: str | Path = DEFAULT_EVIDENCE_APPLIED_MASTER,
    queue_output: str | Path = DEFAULT_QUEUE_OUTPUT,
    summary_output: str | Path = DEFAULT_SUMMARY_OUTPUT,
    report_output: str | Path = DEFAULT_REPORT_OUTPUT,
) -> GapReviewQueueResult:
    _require_file(impact_input, "MISSING_SEC_CORE_KPI_CLOSURE_IMPACT")
    _require_file(impact_summary_input, "MISSING_SEC_CORE_KPI_CLOSURE_IMPACT_SUMMARY")
    _require_file(evidence_applied_master, "MISSING_EVIDENCE_APPLIED_MASTER")
    _read_header(evidence_applied_master)

    impact_rows = read_csv_rows(impact_input)
    impact_summary_rows = read_csv_rows(impact_summary_input)
    _require_columns(impact_rows, IMPACT_REQUIRED_COLUMNS, f"impact input ({impact_input})")
    _require_columns(impact_summary_rows, SUMMARY_REQUIRED_COLUMNS, f"impact summary ({impact_summary_input})")

    queue_rows = build_queue_rows(impact_rows)
    summary = build_summary(queue_rows, impact_summary_rows)

    queue_path = write_csv_rows(queue_output, QUEUE_FIELDS, queue_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, [summary])
    report_path = ensure_parent_dir(report_output)
    report_path.write_text(render_report(summary, queue_rows), encoding="utf-8")

    return GapReviewQueueResult(
        queue_path=resolve_repo_path(queue_path),
        summary_path=resolve_repo_path(summary_path),
        report_path=resolve_repo_path(report_path),
        summary=summary,
        queue_rows=queue_rows,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a review queue for remaining SEC core KPI gaps and stale SEC-derived values.")
    parser.add_argument("--impact-input", default=DEFAULT_IMPACT_INPUT)
    parser.add_argument("--impact-summary-input", default=DEFAULT_IMPACT_SUMMARY_INPUT)
    parser.add_argument("--evidence-applied-master", default=DEFAULT_EVIDENCE_APPLIED_MASTER)
    parser.add_argument("--queue-output", default=DEFAULT_QUEUE_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_core_kpi_gap_review_queue(
        impact_input=args.impact_input,
        impact_summary_input=args.impact_summary_input,
        evidence_applied_master=args.evidence_applied_master,
        queue_output=args.queue_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    print(f"queue_output={result.queue_path}")
    print(f"summary_output={result.summary_path}")
    print(f"report_output={result.report_path}")
    print(f"total_review_rows={result.summary['total_review_rows']}")


if __name__ == "__main__":
    main()
