from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_PERIOD_REVIEW = "data/processed/personal_sec_companyfacts_period_selection_review.csv"
DEFAULT_PERIOD_REVIEW_SUMMARY = "data/processed/personal_sec_companyfacts_period_selection_review_summary.csv"
DEFAULT_GAP_REVIEW_QUEUE = "data/processed/personal_sec_core_kpi_gap_review_queue.csv"
DEFAULT_APPROVED_FACTS = "data/processed/personal_sec_companyfacts_approved_facts.csv"
DEFAULT_CONCEPT_CANDIDATES = "data/processed/personal_sec_kpi_extraction_concept_candidates.csv"
DEFAULT_OUTPUT = "data/processed/personal_sec_companyfacts_concept_coverage_diagnostics.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_sec_companyfacts_concept_coverage_diagnostics_summary.csv"
DEFAULT_REPORT_OUTPUT = "reports/2026-04-28/personal_sec_companyfacts_concept_coverage_diagnostics_report.md"

BLOCKER_STATUSES = {
    "MISSING_REQUIRED_CONCEPT",
    "INSUFFICIENT_PERIOD_HISTORY",
    "PERIOD_AMBIGUITY_REVIEW",
    "STALE_VALUE_NO_REFRESH_AVAILABLE",
    "LOCAL_SEC_SNAPSHOT_MISSING",
}

DIAGNOSTIC_FIELDS = [
    "review_id",
    "ticker",
    "isin",
    "company_name",
    "kpi_field",
    "period_selection_status",
    "review_bucket",
    "required_concepts",
    "missing_concepts",
    "available_related_concepts",
    "available_concepts_count",
    "available_annual_periods",
    "minimum_required_period_span",
    "actual_available_period_span",
    "diagnostic_blocker_class",
    "likely_fix_type",
    "recommended_action",
    "source_artifact",
    "candidate_value_not_applied",
    "apply_status",
    "notes",
]

SUMMARY_FIELDS = [
    "total_diagnostic_rows",
    "true_sec_data_gap_rows",
    "concept_alias_gap_rows",
    "period_history_gap_rows",
    "period_ambiguity_rows",
    "stale_refresh_not_available_rows",
    "snapshot_missing_rows",
    "review_required_rows",
    "rows_potentially_fixable_by_alias_expansion",
    "rows_potentially_fixable_by_sec_refresh",
    "rows_requiring_manual_review",
    "candidate_values_applied",
    "no_values_applied_confirmed",
    "no_score_change_confirmed",
    "no_network_confirmed",
    "raw_master_mutation_performed",
]

PERIOD_REVIEW_REQUIRED_COLUMNS = [
    "review_id",
    "ticker",
    "isin",
    "company_name",
    "kpi_field",
    "period_selection_status",
    "review_bucket",
    "required_concepts",
    "missing_concepts",
    "available_concepts",
    "selected_start_fiscal_year",
    "selected_end_fiscal_year",
    "source_artifact",
    "candidate_value_not_applied",
]
PERIOD_SUMMARY_REQUIRED_COLUMNS = ["no_score_change_confirmed", "no_network_confirmed", "raw_master_mutation_performed"]
GAP_QUEUE_REQUIRED_COLUMNS = ["review_id", "ticker", "isin", "kpi_field"]


@dataclass(frozen=True)
class ConceptCoverageDiagnosticsResult:
    diagnostics_path: Path
    summary_path: Path
    report_path: Path
    summary: dict[str, str]
    diagnostics_rows: list[dict[str, str]]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _upper(value: Any) -> str:
    return safe_upper(value)


def _require_file(path_value: str | Path, error_code: str) -> Path:
    path = resolve_repo_path(path_value)
    if not path.exists():
        raise RuntimeError(error_code)
    return path


def _read_optional(path_value: str | Path) -> list[dict[str, str]]:
    path = resolve_repo_path(path_value)
    return read_csv_rows(path) if path.exists() else []


def _require_columns(rows: list[dict[str, str]], required: list[str], source_name: str) -> None:
    if not rows:
        raise ValueError(f"{source_name} contains no rows")
    available = set(rows[0].keys())
    missing = [column for column in required if column not in available]
    if missing:
        raise ValueError(f"{source_name} missing required columns: {', '.join(sorted(missing))}")


def _split_semicolon(value: Any) -> list[str]:
    return [part.strip() for part in _clean(value).replace(",", ";").split(";") if part.strip()]


def _parse_required_concepts(value: str) -> dict[str, list[str]]:
    roles: dict[str, list[str]] = {}
    for group in _clean(value).split("|"):
        if ":" not in group:
            continue
        role, concepts = group.split(":", 1)
        roles[_clean(role)] = [part.strip() for part in concepts.split("/") if part.strip()]
    return roles


def _year_from_fact(row: dict[str, str]) -> int | None:
    period_end = _clean(row.get("period_end"))
    if len(period_end) >= 4 and period_end[:4].isdigit():
        return int(period_end[:4])
    fiscal_year = _clean(row.get("fiscal_year"))
    if fiscal_year.isdigit():
        return int(fiscal_year)
    return None


def _is_annual_fact(row: dict[str, str]) -> bool:
    annual_basis = _upper(row.get("annual_basis"))
    if annual_basis in {"FY_10K", "FY_10KA"}:
        return True
    return _upper(row.get("fiscal_period")) == "FY" and _upper(row.get("form")) in {"10-K", "10-K/A"}


def _approved_annual_periods(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, set[int]]]:
    periods: dict[tuple[str, str], dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    for row in rows:
        isin = _upper(row.get("isin"))
        kpi = _clean(row.get("kpi_field"))
        concept = _clean(row.get("sec_concept"))
        year = _year_from_fact(row)
        if isin and kpi and concept and year is not None and _is_annual_fact(row):
            periods[(isin, kpi)][concept].add(year)
    return periods


def _candidate_concepts(rows: list[dict[str, str]]) -> dict[tuple[str, str], set[str]]:
    concepts: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        isin = _upper(row.get("isin"))
        kpi = _clean(row.get("kpi_field"))
        concept = _clean(row.get("sec_concept"))
        if isin and kpi and concept:
            concepts[(isin, kpi)].add(concept)
    return concepts


def _available_period_text(concept_periods: dict[str, set[int]]) -> str:
    parts: list[str] = []
    for concept in sorted(concept_periods):
        years = sorted(concept_periods[concept])
        if years:
            parts.append(f"{concept}:{';'.join(str(year) for year in years)}")
    return " | ".join(parts)


def _period_span(concept_periods: dict[str, set[int]]) -> int:
    years = sorted({year for values in concept_periods.values() for year in values})
    return years[-1] - years[0] if len(years) >= 2 else 0


def _minimum_span(kpi_field: str) -> str:
    return "4" if kpi_field.endswith("_cagr_5y") else "0"


def _related_concepts_for_row(row: dict[str, str], concept_periods: dict[str, set[int]], candidate_concepts: set[str]) -> list[str]:
    required = _parse_required_concepts(row.get("required_concepts", ""))
    required_flat = {concept for concepts in required.values() for concept in concepts}
    approved = set(concept_periods)
    related = sorted(approved | (candidate_concepts & required_flat))
    return related


def _classify(row: dict[str, str], related_concepts: list[str], concept_periods: dict[str, set[int]]) -> str:
    status = _clean(row.get("period_selection_status"))
    if status == "LOCAL_SEC_SNAPSHOT_MISSING":
        return "SNAPSHOT_MISSING"
    if status == "STALE_VALUE_NO_REFRESH_AVAILABLE":
        return "STALE_REFRESH_NOT_AVAILABLE"
    if status == "PERIOD_AMBIGUITY_REVIEW":
        return "PERIOD_AMBIGUITY"
    if status == "INSUFFICIENT_PERIOD_HISTORY":
        return "PERIOD_HISTORY_GAP"
    if status == "MISSING_REQUIRED_CONCEPT":
        if related_concepts:
            return "CONCEPT_ALIAS_GAP"
        if concept_periods:
            return "CONCEPT_ALIAS_GAP"
        return "TRUE_SEC_DATA_GAP"
    return "REVIEW_REQUIRED"


def _likely_fix_type(blocker_class: str) -> str:
    return {
        "TRUE_SEC_DATA_GAP": "SEC_REFRESH_OR_NON_SEC_EVIDENCE_REQUIRED",
        "CONCEPT_ALIAS_GAP": "SEC_CONCEPT_ALIAS_OR_ROLE_MAPPING_REVIEW",
        "PERIOD_HISTORY_GAP": "SEC_REFRESH_OR_PERIOD_WINDOW_REVIEW",
        "PERIOD_AMBIGUITY": "HUMAN_CONCEPT_PERIOD_SELECTION",
        "STALE_REFRESH_NOT_AVAILABLE": "NEWER_SEC_PERIOD_OR_MANUAL_EVIDENCE_REQUIRED",
        "SNAPSHOT_MISSING": "SEC_SNAPSHOT_RETENTION_RERUN_REQUIRED",
        "REVIEW_REQUIRED": "MANUAL_REVIEW_REQUIRED",
    }.get(blocker_class, "MANUAL_REVIEW_REQUIRED")


def _recommended_action(blocker_class: str) -> str:
    return {
        "TRUE_SEC_DATA_GAP": "Confirm whether the SEC filing omits the required concept, then use manual/non-SEC evidence if needed.",
        "CONCEPT_ALIAS_GAP": "Review concept aliases or derived role mapping before another derived KPI compose attempt.",
        "PERIOD_HISTORY_GAP": "Review period window requirements or refresh SEC history; do not shorten the window automatically.",
        "PERIOD_AMBIGUITY": "Human review required for conflicting concepts, periods, or non-positive endpoints.",
        "STALE_REFRESH_NOT_AVAILABLE": "Keep stale warning open and collect newer SEC/manual evidence before replacing the value.",
        "SNAPSHOT_MISSING": "Rerun SEC snapshot retention with raw snapshot retention enabled.",
        "REVIEW_REQUIRED": "Manual diagnostic review required.",
    }.get(blocker_class, "Manual diagnostic review required.")


def build_diagnostic_rows(
    period_rows: list[dict[str, str]],
    approved_facts_rows: list[dict[str, str]],
    concept_candidate_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    period_index = _approved_annual_periods(approved_facts_rows)
    candidate_index = _candidate_concepts(concept_candidate_rows)
    diagnostics: list[dict[str, str]] = []
    for row in period_rows:
        if _clean(row.get("period_selection_status")) not in BLOCKER_STATUSES:
            continue
        key = (_upper(row.get("isin")), _clean(row.get("kpi_field")))
        concept_periods = period_index.get(key, {})
        related = _related_concepts_for_row(row, concept_periods, candidate_index.get(key, set()))
        blocker_class = _classify(row, related, concept_periods)
        actual_span = _period_span(concept_periods)
        diagnostics.append(
            {
                "review_id": _clean(row.get("review_id")),
                "ticker": _clean(row.get("ticker")),
                "isin": _upper(row.get("isin")),
                "company_name": _clean(row.get("company_name")),
                "kpi_field": _clean(row.get("kpi_field")),
                "period_selection_status": _clean(row.get("period_selection_status")),
                "review_bucket": _clean(row.get("review_bucket")),
                "required_concepts": _clean(row.get("required_concepts")),
                "missing_concepts": _clean(row.get("missing_concepts")),
                "available_related_concepts": "; ".join(related),
                "available_concepts_count": str(len(related)),
                "available_annual_periods": _available_period_text(concept_periods),
                "minimum_required_period_span": _minimum_span(_clean(row.get("kpi_field"))),
                "actual_available_period_span": str(actual_span),
                "diagnostic_blocker_class": blocker_class,
                "likely_fix_type": _likely_fix_type(blocker_class),
                "recommended_action": _recommended_action(blocker_class),
                "source_artifact": _clean(row.get("source_artifact")),
                "candidate_value_not_applied": "True",
                "apply_status": "DIAGNOSTIC_ONLY",
                "notes": "Diagnostics only; no KPI value applied, no score change, no network fetch.",
            }
        )
    diagnostics.sort(key=lambda item: (item["diagnostic_blocker_class"], item["ticker"], item["isin"], item["kpi_field"]))
    return diagnostics


def build_summary(rows: list[dict[str, str]], period_summary_rows: list[dict[str, str]]) -> dict[str, str]:
    counts = Counter(row["diagnostic_blocker_class"] for row in rows)
    period_summary = period_summary_rows[0] if period_summary_rows else {}
    alias = counts.get("CONCEPT_ALIAS_GAP", 0)
    sec_refresh = counts.get("PERIOD_HISTORY_GAP", 0) + counts.get("SNAPSHOT_MISSING", 0)
    manual = counts.get("PERIOD_AMBIGUITY", 0) + counts.get("STALE_REFRESH_NOT_AVAILABLE", 0) + counts.get("TRUE_SEC_DATA_GAP", 0) + counts.get("REVIEW_REQUIRED", 0)
    return {
        "total_diagnostic_rows": str(len(rows)),
        "true_sec_data_gap_rows": str(counts.get("TRUE_SEC_DATA_GAP", 0)),
        "concept_alias_gap_rows": str(alias),
        "period_history_gap_rows": str(counts.get("PERIOD_HISTORY_GAP", 0)),
        "period_ambiguity_rows": str(counts.get("PERIOD_AMBIGUITY", 0)),
        "stale_refresh_not_available_rows": str(counts.get("STALE_REFRESH_NOT_AVAILABLE", 0)),
        "snapshot_missing_rows": str(counts.get("SNAPSHOT_MISSING", 0)),
        "review_required_rows": str(counts.get("REVIEW_REQUIRED", 0)),
        "rows_potentially_fixable_by_alias_expansion": str(alias),
        "rows_potentially_fixable_by_sec_refresh": str(sec_refresh),
        "rows_requiring_manual_review": str(manual),
        "candidate_values_applied": "0",
        "no_values_applied_confirmed": "True",
        "no_score_change_confirmed": _clean(period_summary.get("no_score_change_confirmed")) or "True",
        "no_network_confirmed": _clean(period_summary.get("no_network_confirmed")) or "True",
        "raw_master_mutation_performed": _clean(period_summary.get("raw_master_mutation_performed")) or "False",
    }


def render_report(summary: dict[str, str], rows: list[dict[str, str]]) -> str:
    lines = [
        "# SEC CompanyFacts Concept Coverage Diagnostics",
        "",
        "## Executive Summary",
        "",
        f"- Total diagnostic rows: {summary['total_diagnostic_rows']}",
        f"- Concept alias gap rows: {summary['concept_alias_gap_rows']}",
        f"- True SEC data gap rows: {summary['true_sec_data_gap_rows']}",
        f"- Period history gap rows: {summary['period_history_gap_rows']}",
        f"- Period ambiguity rows: {summary['period_ambiguity_rows']}",
        f"- Stale refresh unavailable rows: {summary['stale_refresh_not_available_rows']}",
        "- No KPI values were applied.",
        f"- No scores were changed: {summary['no_score_change_confirmed']}",
        f"- No network fetch was used: {summary['no_network_confirmed']}",
        "",
        "## Why Zero Rows Were Ready",
        "",
        "The period-selection layer found no rows with complete, unambiguous annual concepts and periods suitable for reviewed derived KPI compose.",
        "",
        "## Blocker Breakdown",
        "",
    ]
    for key in [
        "concept_alias_gap_rows",
        "true_sec_data_gap_rows",
        "period_history_gap_rows",
        "period_ambiguity_rows",
        "stale_refresh_not_available_rows",
        "snapshot_missing_rows",
        "review_required_rows",
    ]:
        lines.append(f"- `{key}`: {summary[key]}")
    lines.extend(["", "## Likely Concept-Alias Gaps", ""])
    alias_rows = [row for row in rows if row["diagnostic_blocker_class"] == "CONCEPT_ALIAS_GAP"]
    if alias_rows:
        for row in alias_rows:
            lines.append(f"- `{row['review_id']}` `{row['company_name']}` `{row['kpi_field']}` missing={row['missing_concepts']} related={row['available_related_concepts']}")
    else:
        lines.append("- None.")
    lines.extend(["", "## True SEC Data Gaps", ""])
    true_rows = [row for row in rows if row["diagnostic_blocker_class"] == "TRUE_SEC_DATA_GAP"]
    if true_rows:
        for row in true_rows:
            lines.append(f"- `{row['review_id']}` `{row['company_name']}` `{row['kpi_field']}`")
    else:
        lines.append("- None.")
    lines.extend(["", "## Insufficient-History Cases", ""])
    hist_rows = [row for row in rows if row["diagnostic_blocker_class"] == "PERIOD_HISTORY_GAP"]
    if hist_rows:
        for row in hist_rows:
            lines.append(f"- `{row['review_id']}` `{row['kpi_field']}` span={row['actual_available_period_span']} required={row['minimum_required_period_span']}")
    else:
        lines.append("- None.")
    lines.extend(["", "## Ambiguity Cases", ""])
    ambiguity_rows = [row for row in rows if row["diagnostic_blocker_class"] == "PERIOD_AMBIGUITY"]
    if ambiguity_rows:
        for row in ambiguity_rows:
            lines.append(f"- `{row['review_id']}` `{row['company_name']}` `{row['kpi_field']}`")
    else:
        lines.append("- None.")
    lines.extend(["", "## Stale Block Value Assessment", ""])
    stale_rows = [row for row in rows if row["diagnostic_blocker_class"] == "STALE_REFRESH_NOT_AVAILABLE"]
    if stale_rows:
        for row in stale_rows:
            lines.append(f"- `{row['review_id']}` `{row['company_name']}` `{row['kpi_field']}`: no newer usable local annual period.")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Recommended Next Patch",
            "",
            "SEC CONCEPT ALIAS REVIEW TABLE / APPROVED FACTS + COMPANYFACTS SNAPSHOT SURFACE / NO SCORE CHANGES",
            "",
            "## Guardrails",
            "",
            "- no_value_apply_confirmed=True",
            "- no_score_change_confirmed=True",
            "- no_network_confirmed=True",
            "- raw_master_mutation_performed=False",
            "- candidate_values_applied=0",
        ]
    )
    return "\n".join(lines) + "\n"


def run_personal_sec_companyfacts_concept_coverage_diagnostics(
    *,
    period_review: str | Path = DEFAULT_PERIOD_REVIEW,
    period_review_summary: str | Path = DEFAULT_PERIOD_REVIEW_SUMMARY,
    gap_review_queue: str | Path = DEFAULT_GAP_REVIEW_QUEUE,
    approved_facts: str | Path = DEFAULT_APPROVED_FACTS,
    concept_candidates: str | Path = DEFAULT_CONCEPT_CANDIDATES,
    output: str | Path = DEFAULT_OUTPUT,
    summary_output: str | Path = DEFAULT_SUMMARY_OUTPUT,
    report_output: str | Path = DEFAULT_REPORT_OUTPUT,
) -> ConceptCoverageDiagnosticsResult:
    _require_file(period_review, "MISSING_PERIOD_SELECTION_REVIEW")
    _require_file(period_review_summary, "MISSING_PERIOD_SELECTION_REVIEW_SUMMARY")
    _require_file(gap_review_queue, "MISSING_SEC_CORE_KPI_GAP_REVIEW_QUEUE")
    period_rows = read_csv_rows(period_review)
    summary_rows = read_csv_rows(period_review_summary)
    queue_rows = read_csv_rows(gap_review_queue)
    _require_columns(period_rows, PERIOD_REVIEW_REQUIRED_COLUMNS, f"period review ({period_review})")
    _require_columns(summary_rows, PERIOD_SUMMARY_REQUIRED_COLUMNS, f"period review summary ({period_review_summary})")
    _require_columns(queue_rows, GAP_QUEUE_REQUIRED_COLUMNS, f"gap review queue ({gap_review_queue})")
    diagnostics_rows = build_diagnostic_rows(period_rows, _read_optional(approved_facts), _read_optional(concept_candidates))
    summary = build_summary(diagnostics_rows, summary_rows)
    diagnostics_path = write_csv_rows(output, DIAGNOSTIC_FIELDS, diagnostics_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, [summary])
    report_path = ensure_parent_dir(report_output)
    report_path.write_text(render_report(summary, diagnostics_rows), encoding="utf-8")
    return ConceptCoverageDiagnosticsResult(
        diagnostics_path=resolve_repo_path(diagnostics_path),
        summary_path=resolve_repo_path(summary_path),
        report_path=resolve_repo_path(report_path),
        summary=summary,
        diagnostics_rows=diagnostics_rows,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose SEC CompanyFacts concept coverage blockers without applying KPI values.")
    parser.add_argument("--period-review", default=DEFAULT_PERIOD_REVIEW)
    parser.add_argument("--period-review-summary", default=DEFAULT_PERIOD_REVIEW_SUMMARY)
    parser.add_argument("--gap-review-queue", default=DEFAULT_GAP_REVIEW_QUEUE)
    parser.add_argument("--approved-facts", default=DEFAULT_APPROVED_FACTS)
    parser.add_argument("--concept-candidates", default=DEFAULT_CONCEPT_CANDIDATES)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_companyfacts_concept_coverage_diagnostics(
        period_review=args.period_review,
        period_review_summary=args.period_review_summary,
        gap_review_queue=args.gap_review_queue,
        approved_facts=args.approved_facts,
        concept_candidates=args.concept_candidates,
        output=args.output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    print(f"diagnostics_output={result.diagnostics_path}")
    print(f"summary_output={result.summary_path}")
    print(f"report_output={result.report_path}")
    print(f"total_diagnostic_rows={result.summary['total_diagnostic_rows']}")


if __name__ == "__main__":
    main()
