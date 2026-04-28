from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, normalize_number_text, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_REVIEW_QUEUE = "data/processed/personal_sec_core_kpi_gap_review_queue.csv"
DEFAULT_REVIEW_QUEUE_SUMMARY = "data/processed/personal_sec_core_kpi_gap_review_queue_summary.csv"
DEFAULT_EVIDENCE_APPLIED_MASTER = "data/processed/personal_fundamentals_master_sec_derived_kpi_applied.csv"
DEFAULT_APPROVED_FACTS = "data/processed/personal_sec_companyfacts_approved_facts.csv"
DEFAULT_OUTPUT = "data/processed/personal_sec_companyfacts_period_selection_review.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_sec_companyfacts_period_selection_review_summary.csv"
DEFAULT_REPORT_OUTPUT = "reports/2026-04-28/personal_sec_companyfacts_period_selection_review_report.md"

REVENUE_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
    "SalesRevenueServicesNet",
]
GROSS_PROFIT_CONCEPTS = ["GrossProfit"]
OPERATING_INCOME_CONCEPTS = ["OperatingIncomeLoss"]
EPS_CONCEPTS = ["EarningsPerShareDiluted", "EarningsPerShareBasic"]
SHARE_COUNT_CONCEPTS = [
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic",
    "EntityCommonStockSharesOutstanding",
]

KPI_REQUIREMENTS = {
    "gross_margin": {
        "recipe": "margin",
        "roles": {"gross_profit": GROSS_PROFIT_CONCEPTS, "revenue": REVENUE_CONCEPTS},
    },
    "operating_margin": {
        "recipe": "margin",
        "roles": {"operating_income": OPERATING_INCOME_CONCEPTS, "revenue": REVENUE_CONCEPTS},
    },
    "revenue_cagr_5y": {
        "recipe": "cagr",
        "roles": {"revenue_series": REVENUE_CONCEPTS},
    },
    "eps_cagr_5y": {
        "recipe": "cagr",
        "roles": {"eps_series": EPS_CONCEPTS},
    },
    "share_count_cagr_5y": {
        "recipe": "cagr",
        "roles": {"share_count_series": SHARE_COUNT_CONCEPTS},
    },
}

SELECTED_REVIEW_BUCKETS = {"SEC_REFRESH_CANDIDATE", "STALE_VALUE_REVIEW"}
ANNUAL_BASES = {"FY_10K", "FY_10KA"}

REVIEW_FIELDS = [
    "review_id",
    "ticker",
    "isin",
    "company_name",
    "kpi_field",
    "review_bucket",
    "current_value",
    "stale_or_old_fiscal_year",
    "stale_reason",
    "required_concepts",
    "available_concepts",
    "missing_concepts",
    "selected_start_fiscal_year",
    "selected_end_fiscal_year",
    "selected_start_period",
    "selected_end_period",
    "selected_start_value",
    "selected_end_value",
    "candidate_value",
    "candidate_value_not_applied",
    "period_selection_status",
    "confidence",
    "blocking_reason",
    "recommended_action",
    "source_artifact",
    "notes",
]

SUMMARY_FIELDS = [
    "total_review_rows",
    "sec_refresh_candidate_rows",
    "stale_value_review_rows",
    "ready_for_derived_kpi_review_rows",
    "missing_required_concept_rows",
    "insufficient_period_history_rows",
    "period_ambiguity_review_rows",
    "local_sec_snapshot_missing_rows",
    "stale_value_refresh_candidate_rows",
    "stale_value_no_refresh_available_rows",
    "candidate_values_previewed",
    "candidate_values_applied",
    "no_values_applied_confirmed",
    "no_score_change_confirmed",
    "no_network_confirmed",
    "raw_master_mutation_performed",
]

QUEUE_REQUIRED_COLUMNS = [
    "review_id",
    "ticker",
    "isin",
    "company_name",
    "kpi_field",
    "review_bucket",
    "current_value",
    "stale_or_old_fiscal_year",
    "stale_reason",
    "fiscal_year_end",
]
QUEUE_SUMMARY_REQUIRED_COLUMNS = ["no_score_change_confirmed", "no_network_confirmed", "raw_master_mutation_performed"]
FACT_REQUIRED_COLUMNS = [
    "isin",
    "sec_concept",
    "unit",
    "fiscal_year",
    "fiscal_period",
    "form",
    "filed_date",
    "period_start",
    "period_end",
    "value",
    "value_is_numeric",
    "annual_basis",
]


@dataclass(frozen=True)
class PeriodSelectionReviewResult:
    review_path: Path
    summary_path: Path
    report_path: Path
    summary: dict[str, str]
    review_rows: list[dict[str, str]]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _upper(value: Any) -> str:
    return safe_upper(value)


def _is_true(value: Any) -> bool:
    return _clean(value).lower() in {"1", "true", "yes", "y"}


def _format_float(value: float) -> str:
    return format(value, ".12g")


def _to_float(value: Any) -> float | None:
    text = normalize_number_text(_clean(value))
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return number


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


def _concept_list_text(roles: dict[str, list[str]]) -> str:
    return " | ".join(f"{role}: {'/'.join(concepts)}" for role, concepts in roles.items())


def _year_from_fact(row: dict[str, str]) -> int | None:
    period_end = _clean(row.get("period_end"))
    if len(period_end) >= 4 and period_end[:4].isdigit():
        return int(period_end[:4])
    fiscal_year = _clean(row.get("fiscal_year"))
    if fiscal_year.isdigit():
        return int(fiscal_year)
    return None


def _is_annual_fact(row: dict[str, str]) -> bool:
    if _upper(row.get("annual_basis")) in ANNUAL_BASES:
        return True
    return _upper(row.get("fiscal_period")) == "FY" and _upper(row.get("form")) in {"10-K", "10-K/A"}


def _fact_sort_key(row: dict[str, str]) -> tuple[str, str]:
    return (_clean(row.get("filed_date")), _clean(row.get("accession")))


def _annual_facts_for_concepts(facts: list[dict[str, str]], concepts: list[str]) -> dict[str, dict[int, dict[str, str]]]:
    concept_set = set(concepts)
    grouped: dict[str, dict[int, dict[str, str]]] = {}
    for row in facts:
        concept = _clean(row.get("sec_concept"))
        if concept not in concept_set:
            continue
        if not _is_true(row.get("value_is_numeric")) or _to_float(row.get("value")) is None:
            continue
        if not _is_annual_fact(row):
            continue
        year = _year_from_fact(row)
        if year is None:
            continue
        bucket = grouped.setdefault(concept, {})
        existing = bucket.get(year)
        if existing is None or _fact_sort_key(row) >= _fact_sort_key(existing):
            bucket[year] = row
    return grouped


def _available_concepts(role_facts: dict[str, dict[int, dict[str, str]]]) -> list[str]:
    return sorted(concept for concept, by_year in role_facts.items() if by_year)


def _period_text(row: dict[str, str] | None, year: int | None) -> str:
    if row is None or year is None:
        return ""
    start = _clean(row.get("period_start"))
    end = _clean(row.get("period_end"))
    if start or end:
        return f"{start or '?'}..{end or '?'}"
    return f"FY{year}"


def _source_artifact(facts_path: str | Path, facts_present: bool) -> str:
    return str(facts_path).replace("\\", "/") if facts_present else ""


def _evaluate_margin(
    *,
    queue_row: dict[str, str],
    facts: list[dict[str, str]],
    roles: dict[str, list[str]],
    facts_path: str | Path,
) -> dict[str, str]:
    role_facts = {role: _annual_facts_for_concepts(facts, concepts) for role, concepts in roles.items()}
    available_by_role = {role: _available_concepts(grouped) for role, grouped in role_facts.items()}
    missing_roles = [role for role, concepts in available_by_role.items() if not concepts]
    if missing_roles:
        return _result_row(queue_row, roles, available_by_role, [], "MISSING_REQUIRED_CONCEPT", "HIGH", f"Missing annual facts for role(s): {'; '.join(missing_roles)}", "", facts_path, bool(facts))
    ambiguous_roles = [role for role, concepts in available_by_role.items() if len(concepts) > 1]
    if ambiguous_roles:
        return _result_row(queue_row, roles, available_by_role, [], "PERIOD_AMBIGUITY_REVIEW", "MEDIUM", f"Multiple annual concepts available for role(s): {'; '.join(ambiguous_roles)}", "", facts_path, True)

    selected_concepts = {role: concepts[0] for role, concepts in available_by_role.items()}
    year_sets = [set(role_facts[role][concept].keys()) for role, concept in selected_concepts.items()]
    common_years = sorted(set.intersection(*year_sets)) if year_sets else []
    if not common_years:
        return _result_row(queue_row, roles, available_by_role, [], "INSUFFICIENT_PERIOD_HISTORY", "HIGH", "No common annual period exists across required roles.", "", facts_path, True)
    selected_year = common_years[-1]
    selected_rows = {role: role_facts[role][concept][selected_year] for role, concept in selected_concepts.items()}
    numerator_role = "gross_profit" if "gross_profit" in selected_rows else "operating_income"
    numerator = _to_float(selected_rows[numerator_role].get("value"))
    denominator = _to_float(selected_rows["revenue"].get("value"))
    if numerator is None or denominator is None or denominator <= 0:
        return _result_row(queue_row, roles, available_by_role, [], "PERIOD_AMBIGUITY_REVIEW", "MEDIUM", "Required annual values are nonnumeric or revenue is non-positive.", "", facts_path, True)
    candidate_value = _format_float(numerator / denominator)
    status = _status_for_queue_row(queue_row, selected_year, ready_status="READY_FOR_DERIVED_KPI_REVIEW")
    blocking = "" if status in {"READY_FOR_DERIVED_KPI_REVIEW", "STALE_VALUE_REFRESH_CANDIDATE"} else "No newer annual period than stale current value is available."
    return _result_row(
        queue_row,
        roles,
        available_by_role,
        [selected_year],
        status,
        "HIGH",
        blocking,
        candidate_value if status != "STALE_VALUE_NO_REFRESH_AVAILABLE" else "",
        facts_path,
        True,
        selected_start_year=selected_year,
        selected_end_year=selected_year,
        selected_start_row=selected_rows[numerator_role],
        selected_end_row=selected_rows["revenue"],
    )


def _evaluate_cagr(
    *,
    queue_row: dict[str, str],
    facts: list[dict[str, str]],
    roles: dict[str, list[str]],
    facts_path: str | Path,
) -> dict[str, str]:
    role, concepts = next(iter(roles.items()))
    role_facts = {role: _annual_facts_for_concepts(facts, concepts)}
    available = _available_concepts(role_facts[role])
    if not available:
        return _result_row(queue_row, roles, {role: []}, [], "MISSING_REQUIRED_CONCEPT", "HIGH", f"Missing annual facts for role: {role}", "", facts_path, bool(facts))
    if len(available) > 1:
        return _result_row(queue_row, roles, {role: available}, [], "PERIOD_AMBIGUITY_REVIEW", "MEDIUM", f"Multiple annual concepts available for role: {role}", "", facts_path, True)
    concept = available[0]
    by_year = role_facts[role][concept]
    years = sorted(by_year)
    if len(years) < 2 or years[-1] - years[0] < 4:
        return _result_row(queue_row, roles, {role: available}, years, "INSUFFICIENT_PERIOD_HISTORY", "HIGH", "Annual history does not meet minimum 4-year span.", "", facts_path, True)
    start_year, end_year = years[0], years[-1]
    start_row, end_row = by_year[start_year], by_year[end_year]
    start_value = _to_float(start_row.get("value"))
    end_value = _to_float(end_row.get("value"))
    if start_value is None or end_value is None or start_value <= 0 or end_value <= 0:
        return _result_row(queue_row, roles, {role: available}, years, "PERIOD_AMBIGUITY_REVIEW", "MEDIUM", "CAGR endpoint is non-positive or nonnumeric; human review required.", "", facts_path, True)
    years_between = end_year - start_year
    candidate_value = _format_float((end_value / start_value) ** (1 / years_between) - 1)
    status = _status_for_queue_row(queue_row, end_year, ready_status="READY_FOR_DERIVED_KPI_REVIEW")
    blocking = "" if status in {"READY_FOR_DERIVED_KPI_REVIEW", "STALE_VALUE_REFRESH_CANDIDATE"} else "No newer annual period than stale current value is available."
    return _result_row(
        queue_row,
        roles,
        {role: available},
        years,
        status,
        "HIGH",
        blocking,
        candidate_value if status != "STALE_VALUE_NO_REFRESH_AVAILABLE" else "",
        facts_path,
        True,
        selected_start_year=start_year,
        selected_end_year=end_year,
        selected_start_row=start_row,
        selected_end_row=end_row,
    )


def _status_for_queue_row(queue_row: dict[str, str], selected_end_year: int, *, ready_status: str) -> str:
    if _clean(queue_row.get("review_bucket")) != "STALE_VALUE_REVIEW":
        return ready_status
    stale_year_text = _clean(queue_row.get("fiscal_year_end"))
    try:
        stale_year = int(float(stale_year_text))
    except ValueError:
        stale_year = selected_end_year
    return "STALE_VALUE_REFRESH_CANDIDATE" if selected_end_year > stale_year else "STALE_VALUE_NO_REFRESH_AVAILABLE"


def _result_row(
    queue_row: dict[str, str],
    roles: dict[str, list[str]],
    available_by_role: dict[str, list[str]],
    years: list[int],
    status: str,
    confidence: str,
    blocking_reason: str,
    candidate_value: str,
    facts_path: str | Path,
    facts_present: bool,
    *,
    selected_start_year: int | None = None,
    selected_end_year: int | None = None,
    selected_start_row: dict[str, str] | None = None,
    selected_end_row: dict[str, str] | None = None,
) -> dict[str, str]:
    missing = []
    for role in roles:
        if not available_by_role.get(role):
            missing.append(role)
    if status == "LOCAL_SEC_SNAPSHOT_MISSING":
        blocking_reason = "No local processed SEC CompanyFacts approved-facts artifact is available for this holding."
    selected_start_value = _clean(selected_start_row.get("value")) if selected_start_row else ""
    selected_end_value = _clean(selected_end_row.get("value")) if selected_end_row else ""
    return {
        "review_id": _clean(queue_row.get("review_id")),
        "ticker": _clean(queue_row.get("ticker")),
        "isin": _upper(queue_row.get("isin")),
        "company_name": _clean(queue_row.get("company_name")),
        "kpi_field": _clean(queue_row.get("kpi_field")),
        "review_bucket": _clean(queue_row.get("review_bucket")),
        "current_value": _clean(queue_row.get("current_value")),
        "stale_or_old_fiscal_year": str(_is_true(queue_row.get("stale_or_old_fiscal_year"))),
        "stale_reason": _clean(queue_row.get("stale_reason")),
        "required_concepts": _concept_list_text(roles),
        "available_concepts": " | ".join(f"{role}: {'/'.join(concepts)}" for role, concepts in available_by_role.items() if concepts),
        "missing_concepts": "; ".join(missing),
        "selected_start_fiscal_year": str(selected_start_year or (years[0] if years else "")),
        "selected_end_fiscal_year": str(selected_end_year or (years[-1] if years else "")),
        "selected_start_period": _period_text(selected_start_row, selected_start_year),
        "selected_end_period": _period_text(selected_end_row, selected_end_year),
        "selected_start_value": selected_start_value,
        "selected_end_value": selected_end_value,
        "candidate_value": candidate_value,
        "candidate_value_not_applied": str(bool(candidate_value)),
        "period_selection_status": status,
        "confidence": confidence,
        "blocking_reason": blocking_reason,
        "recommended_action": _recommended_action(status),
        "source_artifact": _source_artifact(facts_path, facts_present),
        "notes": "Period-selection review only; candidate values are previews and were not applied.",
    }


def _recommended_action(status: str) -> str:
    return {
        "READY_FOR_DERIVED_KPI_REVIEW": "Review candidate periods and approve a derived KPI compose rerun if acceptable.",
        "MISSING_REQUIRED_CONCEPT": "Review SEC concept mapping or add manual/non-SEC evidence.",
        "INSUFFICIENT_PERIOD_HISTORY": "Review available annual history and decide whether a shorter-window/manual source is acceptable.",
        "PERIOD_AMBIGUITY_REVIEW": "Human review required for competing concepts, periods, or non-positive CAGR endpoints.",
        "LOCAL_SEC_SNAPSHOT_MISSING": "Rerun SEC snapshot retention for this holding before period selection.",
        "STALE_VALUE_REFRESH_CANDIDATE": "Review newer local SEC annual periods before replacing stale value.",
        "STALE_VALUE_NO_REFRESH_AVAILABLE": "Keep stale warning open; collect newer evidence manually or via SEC refresh.",
    }.get(status, "Human review required.")


def evaluate_queue_row(row: dict[str, str], facts_by_isin: dict[str, list[dict[str, str]]], facts_path: str | Path, facts_artifact_exists: bool) -> dict[str, str]:
    kpi = _clean(row.get("kpi_field"))
    roles = KPI_REQUIREMENTS.get(kpi, {}).get("roles")
    recipe = KPI_REQUIREMENTS.get(kpi, {}).get("recipe")
    facts = facts_by_isin.get(_upper(row.get("isin")), [])
    if not facts_artifact_exists or not facts:
        return _result_row(row, roles or {}, {}, [], "LOCAL_SEC_SNAPSHOT_MISSING", "LOW", "", "", facts_path, False)
    if not roles:
        return _result_row(row, {}, {}, [], "MISSING_REQUIRED_CONCEPT", "MEDIUM", f"No period-selection mapping exists for KPI {kpi}.", "", facts_path, True)
    if recipe == "margin":
        return _evaluate_margin(queue_row=row, facts=facts, roles=roles, facts_path=facts_path)
    return _evaluate_cagr(queue_row=row, facts=facts, roles=roles, facts_path=facts_path)


def build_facts_by_isin(facts_rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in facts_rows:
        isin = _upper(row.get("isin"))
        if isin:
            grouped.setdefault(isin, []).append(row)
    return grouped


def build_summary(rows: list[dict[str, str]], queue_summary_rows: list[dict[str, str]]) -> dict[str, str]:
    queue_summary = queue_summary_rows[0] if queue_summary_rows else {}

    def count_status(status: str) -> int:
        return sum(1 for row in rows if row["period_selection_status"] == status)

    def count_bucket(bucket: str) -> int:
        return sum(1 for row in rows if row["review_bucket"] == bucket)

    return {
        "total_review_rows": str(len(rows)),
        "sec_refresh_candidate_rows": str(count_bucket("SEC_REFRESH_CANDIDATE")),
        "stale_value_review_rows": str(count_bucket("STALE_VALUE_REVIEW")),
        "ready_for_derived_kpi_review_rows": str(count_status("READY_FOR_DERIVED_KPI_REVIEW")),
        "missing_required_concept_rows": str(count_status("MISSING_REQUIRED_CONCEPT")),
        "insufficient_period_history_rows": str(count_status("INSUFFICIENT_PERIOD_HISTORY")),
        "period_ambiguity_review_rows": str(count_status("PERIOD_AMBIGUITY_REVIEW")),
        "local_sec_snapshot_missing_rows": str(count_status("LOCAL_SEC_SNAPSHOT_MISSING")),
        "stale_value_refresh_candidate_rows": str(count_status("STALE_VALUE_REFRESH_CANDIDATE")),
        "stale_value_no_refresh_available_rows": str(count_status("STALE_VALUE_NO_REFRESH_AVAILABLE")),
        "candidate_values_previewed": str(sum(1 for row in rows if _clean(row.get("candidate_value")))),
        "candidate_values_applied": "0",
        "no_values_applied_confirmed": "True",
        "no_score_change_confirmed": _clean(queue_summary.get("no_score_change_confirmed")) or "True",
        "no_network_confirmed": _clean(queue_summary.get("no_network_confirmed")) or "True",
        "raw_master_mutation_performed": _clean(queue_summary.get("raw_master_mutation_performed")) or "False",
    }


def render_report(summary: dict[str, str], rows: list[dict[str, str]]) -> str:
    lines = [
        "# SEC CompanyFacts Period Selection Review",
        "",
        "## Executive Summary",
        "",
        f"- Total review rows: {summary['total_review_rows']}",
        f"- Ready for derived KPI review: {summary['ready_for_derived_kpi_review_rows']}",
        f"- Stale refresh candidates: {summary['stale_value_refresh_candidate_rows']}",
        f"- Candidate values previewed: {summary['candidate_values_previewed']}",
        "- No KPI values were applied.",
        f"- No scores were changed: {summary['no_score_change_confirmed']}",
        f"- No network fetch was used: {summary['no_network_confirmed']}",
        "",
        "## Period-Selection Result By Holding/KPI",
        "",
    ]
    for row in rows:
        lines.append(
            f"- `{row['company_name']}` `{row['kpi_field']}`: {row['period_selection_status']} "
            f"candidate={row['candidate_value'] or 'none'} not_applied={row['candidate_value_not_applied']}"
        )
    lines.extend(["", "## Ready-for-Review Candidates", ""])
    ready_rows = [row for row in rows if row["period_selection_status"] in {"READY_FOR_DERIVED_KPI_REVIEW", "STALE_VALUE_REFRESH_CANDIDATE"}]
    if ready_rows:
        for row in ready_rows:
            lines.append(f"- `{row['review_id']}` `{row['kpi_field']}` periods {row['selected_start_fiscal_year']} -> {row['selected_end_fiscal_year']}")
    else:
        lines.append("- None.")
    lines.extend(["", "## Blockers By Reason", ""])
    blocker_rows = [row for row in rows if row["blocking_reason"]]
    if blocker_rows:
        for row in blocker_rows:
            lines.append(f"- `{row['review_id']}` {row['period_selection_status']}: {row['blocking_reason']}")
    else:
        lines.append("- None.")
    lines.extend(["", "## Stale Value Refresh Candidates", ""])
    stale_ready = [row for row in rows if row["period_selection_status"] == "STALE_VALUE_REFRESH_CANDIDATE"]
    if stale_ready:
        for row in stale_ready:
            lines.append(f"- `{row['company_name']}` `{row['kpi_field']}` current={row['current_value']} preview={row['candidate_value']} not_applied=True")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- no_value_apply_confirmed=True",
            "- no_score_change_confirmed=True",
            "- no_network_confirmed=True",
            "- raw_master_mutation_performed=False",
            "- no_imputation_confirmed=True",
            "",
            "## Recommended Next Patch",
            "",
            "SEC DERIVED KPI REVIEW INPUT TABLE / PERIOD-SELECTION CANDIDATES ONLY / NO SCORE CHANGES",
        ]
    )
    return "\n".join(lines) + "\n"


def run_personal_sec_companyfacts_period_selection_review(
    *,
    review_queue: str | Path = DEFAULT_REVIEW_QUEUE,
    review_queue_summary: str | Path = DEFAULT_REVIEW_QUEUE_SUMMARY,
    evidence_applied_master: str | Path = DEFAULT_EVIDENCE_APPLIED_MASTER,
    approved_facts: str | Path = DEFAULT_APPROVED_FACTS,
    output: str | Path = DEFAULT_OUTPUT,
    summary_output: str | Path = DEFAULT_SUMMARY_OUTPUT,
    report_output: str | Path = DEFAULT_REPORT_OUTPUT,
) -> PeriodSelectionReviewResult:
    _require_file(review_queue, "MISSING_SEC_CORE_KPI_GAP_REVIEW_QUEUE")
    _require_file(review_queue_summary, "MISSING_SEC_CORE_KPI_GAP_REVIEW_QUEUE_SUMMARY")
    _require_file(evidence_applied_master, "MISSING_EVIDENCE_APPLIED_MASTER")
    _read_header(evidence_applied_master)

    queue_rows = read_csv_rows(review_queue)
    queue_summary_rows = read_csv_rows(review_queue_summary)
    _require_columns(queue_rows, QUEUE_REQUIRED_COLUMNS, f"review queue ({review_queue})")
    _require_columns(queue_summary_rows, QUEUE_SUMMARY_REQUIRED_COLUMNS, f"review queue summary ({review_queue_summary})")

    facts_path = resolve_repo_path(approved_facts)
    facts_artifact_exists = facts_path.exists()
    facts_rows: list[dict[str, str]] = []
    if facts_artifact_exists:
        facts_rows = read_csv_rows(facts_path)
        if facts_rows:
            _require_columns(facts_rows, FACT_REQUIRED_COLUMNS, f"approved facts ({approved_facts})")
    facts_by_isin = build_facts_by_isin(facts_rows)

    selected_queue_rows = [row for row in queue_rows if _clean(row.get("review_bucket")) in SELECTED_REVIEW_BUCKETS]
    review_rows = [evaluate_queue_row(row, facts_by_isin, approved_facts, facts_artifact_exists) for row in selected_queue_rows]
    review_rows.sort(
        key=lambda row: (
            row["period_selection_status"],
            row["review_bucket"],
            row["ticker"],
            row["isin"],
            row["kpi_field"],
        )
    )
    summary = build_summary(review_rows, queue_summary_rows)

    review_path = write_csv_rows(output, REVIEW_FIELDS, review_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, [summary])
    report_path = ensure_parent_dir(report_output)
    report_path.write_text(render_report(summary, review_rows), encoding="utf-8")
    return PeriodSelectionReviewResult(
        review_path=resolve_repo_path(review_path),
        summary_path=resolve_repo_path(summary_path),
        report_path=resolve_repo_path(report_path),
        summary=summary,
        review_rows=review_rows,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review local SEC CompanyFacts annual period selection for remaining core KPI gaps.")
    parser.add_argument("--review-queue", default=DEFAULT_REVIEW_QUEUE)
    parser.add_argument("--review-queue-summary", default=DEFAULT_REVIEW_QUEUE_SUMMARY)
    parser.add_argument("--evidence-applied-master", default=DEFAULT_EVIDENCE_APPLIED_MASTER)
    parser.add_argument("--approved-facts", default=DEFAULT_APPROVED_FACTS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_companyfacts_period_selection_review(
        review_queue=args.review_queue,
        review_queue_summary=args.review_queue_summary,
        evidence_applied_master=args.evidence_applied_master,
        approved_facts=args.approved_facts,
        output=args.output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    print(f"review_output={result.review_path}")
    print(f"summary_output={result.summary_path}")
    print(f"report_output={result.report_path}")
    print(f"total_review_rows={result.summary['total_review_rows']}")


if __name__ == "__main__":
    main()
