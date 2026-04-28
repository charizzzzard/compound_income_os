from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_DIAGNOSTICS = "data/processed/personal_sec_companyfacts_concept_coverage_diagnostics.csv"
DEFAULT_DIAGNOSTICS_SUMMARY = "data/processed/personal_sec_companyfacts_concept_coverage_diagnostics_summary.csv"
DEFAULT_PERIOD_REVIEW = "data/processed/personal_sec_companyfacts_period_selection_review.csv"
DEFAULT_GAP_REVIEW_QUEUE = "data/processed/personal_sec_core_kpi_gap_review_queue.csv"
DEFAULT_APPROVED_FACTS = "data/processed/personal_sec_companyfacts_approved_facts.csv"
DEFAULT_CONCEPT_CANDIDATES = "data/processed/personal_sec_kpi_extraction_concept_candidates.csv"
DEFAULT_OUTPUT = "data/processed/personal_sec_concept_alias_review_table.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_sec_concept_alias_review_table_summary.csv"
DEFAULT_REPORT_OUTPUT = "reports/2026-04-28/personal_sec_concept_alias_review_table_report.md"

ALIAS_REVIEW_FIELDS = [
    "alias_review_id",
    "source_review_id",
    "ticker",
    "isin",
    "company_name",
    "kpi_field",
    "required_concept_role",
    "missing_required_concept",
    "candidate_sec_concept",
    "candidate_label",
    "candidate_description",
    "available_annual_periods",
    "first_available_fiscal_year",
    "last_available_fiscal_year",
    "available_period_count",
    "alias_candidate_status",
    "alias_risk_level",
    "semantic_match_reason",
    "semantic_risk_reason",
    "recommended_action",
    "source_artifact",
    "candidate_value_not_applied",
    "apply_status",
    "notes",
]

SUMMARY_FIELDS = [
    "total_alias_review_rows",
    "source_concept_alias_gap_rows",
    "approve_candidate_rows",
    "review_required_rows",
    "reject_candidate_rows",
    "insufficient_evidence_rows",
    "low_risk_rows",
    "medium_risk_rows",
    "high_risk_rows",
    "affected_holdings",
    "affected_kpi_fields",
    "rows_potentially_ready_for_alias_approval",
    "no_aliases_applied_confirmed",
    "no_values_applied_confirmed",
    "no_score_change_confirmed",
    "no_network_confirmed",
    "raw_master_mutation_performed",
]

DIAGNOSTICS_REQUIRED_COLUMNS = [
    "review_id",
    "ticker",
    "isin",
    "company_name",
    "kpi_field",
    "required_concepts",
    "missing_concepts",
    "available_related_concepts",
    "diagnostic_blocker_class",
    "source_artifact",
]
DIAGNOSTICS_SUMMARY_REQUIRED_COLUMNS = ["no_score_change_confirmed", "no_network_confirmed", "raw_master_mutation_performed"]
PERIOD_REVIEW_REQUIRED_COLUMNS = ["review_id", "period_selection_status"]
GAP_QUEUE_REQUIRED_COLUMNS = ["review_id", "ticker", "isin", "kpi_field"]

STATUS_ORDER = {"APPROVE_CANDIDATE": 0, "REVIEW_REQUIRED": 1, "REJECT_CANDIDATE": 2, "INSUFFICIENT_EVIDENCE": 3}

ROLE_BY_MISSING = {
    "revenue": "REVENUE",
    "revenue_series": "REVENUE",
    "gross_profit": "GROSS_PROFIT",
    "operating_income": "OPERATING_INCOME",
    "share_count_series": "SHARE_COUNT",
}

REVENUE_CONCEPTS = {
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
    "SalesRevenueServicesNet",
}
GROSS_PROFIT_CONCEPTS = {"GrossProfit", "CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"}
OPERATING_INCOME_CONCEPTS = {
    "OperatingIncomeLoss",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    "NetIncomeLoss",
}
SHARE_COUNT_CONCEPTS = {
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic",
    "EntityCommonStockSharesOutstanding",
    "CommonStocksIncludingAdditionalPaidInCapitalMember",
}
EPS_CONCEPTS = {"EarningsPerShareDiluted", "EarningsPerShareBasic", "NetIncomeLoss"}


@dataclass(frozen=True)
class SecConceptAliasReviewResult:
    table_path: Path
    summary_path: Path
    report_path: Path
    summary: dict[str, str]
    rows: list[dict[str, str]]


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


def _split_list(value: Any) -> list[str]:
    text = _clean(value).replace(",", ";")
    return [part.strip() for part in text.split(";") if part.strip()]


def _parse_required_concepts(value: str) -> dict[str, list[str]]:
    roles: dict[str, list[str]] = {}
    for group in _clean(value).split("|"):
        if ":" not in group:
            continue
        role, concepts = group.split(":", 1)
        roles[_clean(role)] = [part.strip() for part in concepts.split("/") if part.strip()]
    return roles


def _missing_roles(value: str) -> list[str]:
    roles = _split_list(value)
    return roles if roles else ["UNKNOWN"]


def _role_for_missing(missing: str) -> str:
    return ROLE_BY_MISSING.get(_clean(missing), "UNKNOWN")


def _role_candidate_set(role: str) -> set[str]:
    if role == "REVENUE":
        return set(REVENUE_CONCEPTS)
    if role == "GROSS_PROFIT":
        return set(GROSS_PROFIT_CONCEPTS)
    if role == "OPERATING_INCOME":
        return set(OPERATING_INCOME_CONCEPTS)
    if role == "SHARE_COUNT":
        return set(SHARE_COUNT_CONCEPTS)
    return set(EPS_CONCEPTS)


def _is_annual_fact(row: dict[str, str]) -> bool:
    annual_basis = _upper(row.get("annual_basis"))
    if annual_basis in {"FY_10K", "FY_10KA"}:
        return True
    return _upper(row.get("fiscal_period")) == "FY" and _upper(row.get("form")) in {"10-K", "10-K/A"}


def _year_from_row(row: dict[str, str]) -> int | None:
    for key in ("period_end", "fiscal_year"):
        value = _clean(row.get(key))
        if len(value) >= 4 and value[:4].isdigit():
            return int(value[:4])
    return None


def _approved_fact_index(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        isin = _upper(row.get("isin"))
        kpi = _clean(row.get("kpi_field"))
        concept = _clean(row.get("sec_concept"))
        if not isin or not kpi or not concept:
            continue
        key = (isin, kpi, concept)
        entry = index.setdefault(
            key,
            {
                "label": _clean(row.get("sec_label")),
                "description": _clean(row.get("sec_description")),
                "years": set(),
                "source_artifact": "data/processed/personal_sec_companyfacts_approved_facts.csv",
            },
        )
        if _clean(row.get("sec_label")) and not entry["label"]:
            entry["label"] = _clean(row.get("sec_label"))
        if _clean(row.get("sec_description")) and not entry["description"]:
            entry["description"] = _clean(row.get("sec_description"))
        year = _year_from_row(row)
        if year is not None and _is_annual_fact(row):
            entry["years"].add(year)
    return index


def _candidate_index(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, dict[str, str]]]:
    index: dict[tuple[str, str], dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        isin = _upper(row.get("isin"))
        kpi = _clean(row.get("kpi_field"))
        concept = _clean(row.get("sec_concept"))
        if not isin or not kpi or not concept:
            continue
        index[(isin, kpi)][concept] = {
            "label": _clean(row.get("sec_label_or_description")) or concept,
            "description": _clean(row.get("sec_label_or_description")),
            "source_artifact": _clean(row.get("source_artifact")) or DEFAULT_CONCEPT_CANDIDATES,
        }
    return index


def _candidate_concepts_for_role(row: dict[str, str], missing_role: str, candidate_surface: set[str]) -> list[str]:
    role = _role_for_missing(missing_role)
    required = _parse_required_concepts(row.get("required_concepts", ""))
    expected = set(required.get(missing_role, [])) or _role_candidate_set(role)
    available_related = set(_split_list(row.get("available_related_concepts")))
    candidate_pool = set(candidate_surface) | available_related
    selected = (candidate_pool & expected) | (candidate_pool & _role_candidate_set(role))
    return sorted(selected)


def _period_fields(entry: dict[str, Any] | None) -> tuple[str, str, str, str]:
    years = sorted(entry.get("years", set())) if entry else []
    if not years:
        return "", "", "", "0"
    return ";".join(str(year) for year in years), str(years[0]), str(years[-1]), str(len(years))


def _candidate_metadata(
    isin: str,
    kpi: str,
    concept: str,
    fact_index: dict[tuple[str, str, str], dict[str, Any]],
    candidate_index: dict[tuple[str, str], dict[str, dict[str, str]]],
) -> dict[str, str]:
    fact_entry = fact_index.get((isin, kpi, concept))
    candidate_entry = candidate_index.get((isin, kpi), {}).get(concept, {})
    return {
        "label": _clean((fact_entry or {}).get("label")) or _clean(candidate_entry.get("label")) or concept,
        "description": _clean((fact_entry or {}).get("description")) or _clean(candidate_entry.get("description")),
        "source_artifact": _clean((fact_entry or {}).get("source_artifact")) or _clean(candidate_entry.get("source_artifact")) or DEFAULT_CONCEPT_CANDIDATES,
    }


def classify_alias_candidate(required_role: str, concept: str, has_metadata: bool) -> tuple[str, str, str, str, str]:
    if not has_metadata:
        return (
            "INSUFFICIENT_EVIDENCE",
            "HIGH",
            "Candidate concept is named but local metadata is insufficient.",
            "The local surface does not provide enough label or fact context for alias review.",
            "Collect concept metadata or inspect the SEC snapshot before alias approval.",
        )
    if required_role == "REVENUE":
        if concept == "RevenueFromContractWithCustomerExcludingAssessedTax":
            return (
                "APPROVE_CANDIDATE",
                "LOW",
                "SEC concept is a direct total revenue-from-contract concept.",
                "Low risk if the holding reports consolidated revenue through this concept.",
                "Human approval can add this as a revenue alias for the affected role.",
            )
        if concept in {"Revenues", "SalesRevenueNet"}:
            return (
                "APPROVE_CANDIDATE",
                "MEDIUM",
                "SEC concept is a standard revenue concept.",
                "Medium risk because company-specific presentation can differ from contract revenue.",
                "Review annual facts, then approve only if it is consolidated revenue.",
            )
        if concept in {"SalesRevenueGoodsNet", "SalesRevenueServicesNet"}:
            return (
                "REVIEW_REQUIRED",
                "HIGH",
                "SEC concept may represent a partial goods/services revenue stream.",
                "High risk of treating segment or component revenue as total revenue.",
                "Do not approve without confirming it represents total company revenue.",
            )
    if required_role == "GROSS_PROFIT":
        if concept == "GrossProfit":
            return (
                "APPROVE_CANDIDATE",
                "LOW",
                "SEC concept directly matches gross profit.",
                "Low semantic risk for gross margin numerator.",
                "Human approval can add this as the gross profit alias.",
            )
        if concept in {"CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"}:
            return (
                "REJECT_CANDIDATE",
                "HIGH",
                "Cost concepts are not gross profit.",
                "Using cost as a numerator would invert or distort gross margin.",
                "Reject as automatic alias; use only in a separately reviewed derived gross-profit formula.",
            )
    if required_role == "OPERATING_INCOME":
        if concept == "OperatingIncomeLoss":
            return (
                "APPROVE_CANDIDATE",
                "LOW",
                "SEC concept directly matches operating income or loss.",
                "Low semantic risk for operating margin numerator.",
                "Human approval can add this as the operating income alias.",
            )
        if "IncomeLoss" in concept or "NetIncome" in concept:
            return (
                "REVIEW_REQUIRED",
                "HIGH",
                "Income concept is related but not equivalent to operating income.",
                "High risk because pre-tax, continuing-operations, or net income can include non-operating items.",
                "Do not approve as operating income without human accounting review.",
            )
    if required_role == "SHARE_COUNT":
        if concept == "WeightedAverageNumberOfDilutedSharesOutstanding":
            return (
                "REVIEW_REQUIRED",
                "MEDIUM",
                "Diluted weighted-average shares may fit a share-count series but must match the intended basis.",
                "Share-count concepts are not interchangeable across diluted/basic/period-end bases.",
                "Review whether diluted weighted-average shares are the canonical basis before approval.",
            )
        if concept in {"WeightedAverageNumberOfSharesOutstandingBasic", "EntityCommonStockSharesOutstanding"}:
            return (
                "REVIEW_REQUIRED",
                "HIGH",
                "Share-count concept is related but uses a different basis.",
                "High risk of mixing weighted-average, basic, diluted, or period-end share series.",
                "Keep as review-required unless the canonical share-count basis is confirmed.",
            )
        if concept == "CommonStocksIncludingAdditionalPaidInCapitalMember":
            return (
                "REJECT_CANDIDATE",
                "HIGH",
                "Concept is a stock/APIC member, not a usable share-count series.",
                "High risk because it is not a numeric share count time series.",
                "Reject as share-count alias.",
            )
    if concept == "EarningsPerShareDiluted":
        return (
            "APPROVE_CANDIDATE",
            "LOW",
            "SEC concept directly matches diluted EPS.",
            "Low semantic risk for an EPS series if annual endpoints are valid.",
            "Human approval can add this as the EPS alias.",
        )
    if concept == "EarningsPerShareBasic":
        return (
            "REVIEW_REQUIRED",
            "MEDIUM",
            "Basic EPS is related but not identical to diluted EPS.",
            "Medium risk if mixed with diluted EPS or used where diluted EPS exists.",
            "Approve only if diluted EPS is unavailable or intentionally excluded.",
        )
    if "Income" in concept or "Loss" in concept:
        return (
            "REVIEW_REQUIRED",
            "HIGH",
            "Concept is income-related but not the required per-share metric.",
            "High risk of replacing EPS with income without a separate shares denominator.",
            "Do not approve as an EPS alias without a separate reviewed formula.",
        )
    return (
        "INSUFFICIENT_EVIDENCE",
        "HIGH",
        "No conservative semantic alias rule matched this concept.",
        "Insufficient evidence to treat the concept as equivalent to the missing role.",
        "Keep for manual concept review.",
    )


def build_alias_review_rows(
    diagnostics_rows: list[dict[str, str]],
    approved_facts_rows: list[dict[str, str]],
    concept_candidate_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    fact_index = _approved_fact_index(approved_facts_rows)
    candidates = _candidate_index(concept_candidate_rows)
    rows: list[dict[str, str]] = []
    for diag in diagnostics_rows:
        if _clean(diag.get("diagnostic_blocker_class")) != "CONCEPT_ALIAS_GAP":
            continue
        isin = _upper(diag.get("isin"))
        kpi = _clean(diag.get("kpi_field"))
        candidate_surface = set(candidates.get((isin, kpi), {}))
        for missing in _missing_roles(diag.get("missing_concepts")):
            role = _role_for_missing(missing)
            for concept in _candidate_concepts_for_role(diag, missing, candidate_surface):
                metadata = _candidate_metadata(isin, kpi, concept, fact_index, candidates)
                fact_entry = fact_index.get((isin, kpi, concept))
                periods, first_year, last_year, period_count = _period_fields(fact_entry)
                has_metadata = bool(metadata["label"] or metadata["description"] or fact_entry)
                status, risk, match_reason, risk_reason, action = classify_alias_candidate(role, concept, has_metadata)
                rows.append(
                    {
                        "alias_review_id": "",
                        "source_review_id": _clean(diag.get("review_id")),
                        "ticker": _clean(diag.get("ticker")),
                        "isin": isin,
                        "company_name": _clean(diag.get("company_name")),
                        "kpi_field": kpi,
                        "required_concept_role": role,
                        "missing_required_concept": _clean(missing),
                        "candidate_sec_concept": concept,
                        "candidate_label": metadata["label"],
                        "candidate_description": metadata["description"],
                        "available_annual_periods": periods,
                        "first_available_fiscal_year": first_year,
                        "last_available_fiscal_year": last_year,
                        "available_period_count": period_count,
                        "alias_candidate_status": status,
                        "alias_risk_level": risk,
                        "semantic_match_reason": match_reason,
                        "semantic_risk_reason": risk_reason,
                        "recommended_action": action,
                        "source_artifact": metadata["source_artifact"],
                        "candidate_value_not_applied": "True",
                        "apply_status": "REVIEW_ONLY",
                        "notes": "Alias review only; no alias, KPI value, score, or master mutation was applied.",
                    }
                )
    rows.sort(
        key=lambda row: (
            row["ticker"],
            row["isin"],
            row["kpi_field"],
            row["required_concept_role"],
            STATUS_ORDER.get(row["alias_candidate_status"], 99),
            row["candidate_sec_concept"],
        )
    )
    for index, row in enumerate(rows, start=1):
        row["alias_review_id"] = f"SEC_ALIAS_REVIEW_{index:04d}"
    return rows


def build_summary(rows: list[dict[str, str]], diagnostics_rows: list[dict[str, str]], diagnostics_summary_rows: list[dict[str, str]]) -> dict[str, str]:
    status_counts = Counter(row["alias_candidate_status"] for row in rows)
    risk_counts = Counter(row["alias_risk_level"] for row in rows)
    source_alias_rows = [row for row in diagnostics_rows if _clean(row.get("diagnostic_blocker_class")) == "CONCEPT_ALIAS_GAP"]
    summary_source = diagnostics_summary_rows[0] if diagnostics_summary_rows else {}
    return {
        "total_alias_review_rows": str(len(rows)),
        "source_concept_alias_gap_rows": str(len(source_alias_rows)),
        "approve_candidate_rows": str(status_counts.get("APPROVE_CANDIDATE", 0)),
        "review_required_rows": str(status_counts.get("REVIEW_REQUIRED", 0)),
        "reject_candidate_rows": str(status_counts.get("REJECT_CANDIDATE", 0)),
        "insufficient_evidence_rows": str(status_counts.get("INSUFFICIENT_EVIDENCE", 0)),
        "low_risk_rows": str(risk_counts.get("LOW", 0)),
        "medium_risk_rows": str(risk_counts.get("MEDIUM", 0)),
        "high_risk_rows": str(risk_counts.get("HIGH", 0)),
        "affected_holdings": str(len({row["isin"] for row in rows if row["isin"]})),
        "affected_kpi_fields": str(len({row["kpi_field"] for row in rows if row["kpi_field"]})),
        "rows_potentially_ready_for_alias_approval": str(status_counts.get("APPROVE_CANDIDATE", 0)),
        "no_aliases_applied_confirmed": "True",
        "no_values_applied_confirmed": "True",
        "no_score_change_confirmed": _clean(summary_source.get("no_score_change_confirmed")) or "True",
        "no_network_confirmed": _clean(summary_source.get("no_network_confirmed")) or "True",
        "raw_master_mutation_performed": _clean(summary_source.get("raw_master_mutation_performed")) or "False",
    }


def render_report(summary: dict[str, str], rows: list[dict[str, str]]) -> str:
    source_ids = sorted({row["source_review_id"] for row in rows})
    lines = [
        "# SEC Concept Alias Review Table",
        "",
        "## Executive Summary",
        "",
        f"- Source concept-alias-gap rows inspected: {summary['source_concept_alias_gap_rows']}",
        f"- Alias review rows: {summary['total_alias_review_rows']}",
        f"- Approve candidates: {summary['approve_candidate_rows']}",
        f"- Review-required candidates: {summary['review_required_rows']}",
        f"- Rejected candidates: {summary['reject_candidate_rows']}",
        f"- Insufficient-evidence candidates: {summary['insufficient_evidence_rows']}",
        "- No aliases were applied.",
        "- No KPI values were applied.",
        f"- No scores were changed: {summary['no_score_change_confirmed']}",
        f"- No network fetch was used: {summary['no_network_confirmed']}",
        "",
        "## Inspected Concept-Alias-Gap Rows",
        "",
    ]
    for review_id in source_ids:
        lines.append(f"- `{review_id}`")
    lines.extend(["", "## Alias Candidates By Holding/KPI", ""])
    for row in rows:
        lines.append(
            f"- `{row['alias_review_id']}` `{row['company_name']}` `{row['kpi_field']}` "
            f"`{row['candidate_sec_concept']}` status={row['alias_candidate_status']} risk={row['alias_risk_level']}"
        )
    lines.extend(["", "## Low-Risk Candidates", ""])
    low_rows = [row for row in rows if row["alias_risk_level"] == "LOW"]
    if low_rows:
        for row in low_rows:
            lines.append(f"- `{row['alias_review_id']}` `{row['candidate_sec_concept']}` for `{row['kpi_field']}`")
    else:
        lines.append("- None.")
    lines.extend(["", "## Review-Required Candidates", ""])
    review_rows = [row for row in rows if row["alias_candidate_status"] == "REVIEW_REQUIRED"]
    if review_rows:
        for row in review_rows:
            lines.append(f"- `{row['alias_review_id']}` `{row['candidate_sec_concept']}`: {row['semantic_risk_reason']}")
    else:
        lines.append("- None.")
    lines.extend(["", "## Rejected / High-Risk Candidates", ""])
    risky_rows = [row for row in rows if row["alias_candidate_status"] == "REJECT_CANDIDATE" or row["alias_risk_level"] == "HIGH"]
    if risky_rows:
        for row in risky_rows:
            lines.append(f"- `{row['alias_review_id']}` `{row['candidate_sec_concept']}` status={row['alias_candidate_status']}: {row['semantic_risk_reason']}")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Affected KPI Fields",
            "",
            f"- affected_holdings={summary['affected_holdings']}",
            f"- affected_kpi_fields={summary['affected_kpi_fields']}",
            "",
            "## Recommended Next Patch",
            "",
            "SEC CONCEPT ALIAS APPROVAL INPUT / HUMAN-CONFIRMED ONLY / NO VALUE APPLY",
            "",
            "## Guardrails",
            "",
            "- no_aliases_applied_confirmed=True",
            "- no_values_applied_confirmed=True",
            "- no_score_change_confirmed=True",
            "- no_network_confirmed=True",
            "- raw_master_mutation_performed=False",
        ]
    )
    return "\n".join(lines) + "\n"


def run_personal_sec_concept_alias_review_table(
    *,
    diagnostics: str | Path = DEFAULT_DIAGNOSTICS,
    diagnostics_summary: str | Path = DEFAULT_DIAGNOSTICS_SUMMARY,
    period_review: str | Path = DEFAULT_PERIOD_REVIEW,
    gap_review_queue: str | Path = DEFAULT_GAP_REVIEW_QUEUE,
    approved_facts: str | Path = DEFAULT_APPROVED_FACTS,
    concept_candidates: str | Path = DEFAULT_CONCEPT_CANDIDATES,
    output: str | Path = DEFAULT_OUTPUT,
    summary_output: str | Path = DEFAULT_SUMMARY_OUTPUT,
    report_output: str | Path = DEFAULT_REPORT_OUTPUT,
) -> SecConceptAliasReviewResult:
    _require_file(diagnostics, "MISSING_CONCEPT_COVERAGE_DIAGNOSTICS")
    _require_file(diagnostics_summary, "MISSING_CONCEPT_COVERAGE_DIAGNOSTICS_SUMMARY")
    _require_file(period_review, "MISSING_PERIOD_SELECTION_REVIEW")
    _require_file(gap_review_queue, "MISSING_SEC_CORE_KPI_GAP_REVIEW_QUEUE")
    diagnostics_rows = read_csv_rows(diagnostics)
    diagnostics_summary_rows = read_csv_rows(diagnostics_summary)
    period_rows = read_csv_rows(period_review)
    queue_rows = read_csv_rows(gap_review_queue)
    _require_columns(diagnostics_rows, DIAGNOSTICS_REQUIRED_COLUMNS, f"diagnostics ({diagnostics})")
    _require_columns(diagnostics_summary_rows, DIAGNOSTICS_SUMMARY_REQUIRED_COLUMNS, f"diagnostics summary ({diagnostics_summary})")
    _require_columns(period_rows, PERIOD_REVIEW_REQUIRED_COLUMNS, f"period review ({period_review})")
    _require_columns(queue_rows, GAP_QUEUE_REQUIRED_COLUMNS, f"gap review queue ({gap_review_queue})")
    rows = build_alias_review_rows(diagnostics_rows, _read_optional(approved_facts), _read_optional(concept_candidates))
    summary = build_summary(rows, diagnostics_rows, diagnostics_summary_rows)
    table_path = write_csv_rows(output, ALIAS_REVIEW_FIELDS, rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, [summary])
    report_path = ensure_parent_dir(report_output)
    report_path.write_text(render_report(summary, rows), encoding="utf-8")
    return SecConceptAliasReviewResult(
        table_path=resolve_repo_path(table_path),
        summary_path=resolve_repo_path(summary_path),
        report_path=resolve_repo_path(report_path),
        summary=summary,
        rows=rows,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SEC concept alias review table without applying aliases or KPI values.")
    parser.add_argument("--diagnostics", default=DEFAULT_DIAGNOSTICS)
    parser.add_argument("--diagnostics-summary", default=DEFAULT_DIAGNOSTICS_SUMMARY)
    parser.add_argument("--period-review", default=DEFAULT_PERIOD_REVIEW)
    parser.add_argument("--gap-review-queue", default=DEFAULT_GAP_REVIEW_QUEUE)
    parser.add_argument("--approved-facts", default=DEFAULT_APPROVED_FACTS)
    parser.add_argument("--concept-candidates", default=DEFAULT_CONCEPT_CANDIDATES)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_concept_alias_review_table(
        diagnostics=args.diagnostics,
        diagnostics_summary=args.diagnostics_summary,
        period_review=args.period_review,
        gap_review_queue=args.gap_review_queue,
        approved_facts=args.approved_facts,
        concept_candidates=args.concept_candidates,
        output=args.output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    print(f"alias_review_table={result.table_path}")
    print(f"alias_review_summary={result.summary_path}")
    print(f"alias_review_report={result.report_path}")
    print(f"total_alias_review_rows={result.summary['total_alias_review_rows']}")


if __name__ == "__main__":
    main()
