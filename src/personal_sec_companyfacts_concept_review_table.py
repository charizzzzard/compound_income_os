from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, write_csv_rows

DEFAULT_GAP_MATRIX = "data/processed/personal_sec_kpi_extraction_gap_matrix.csv"
DEFAULT_CONCEPT_CANDIDATES = "data/processed/personal_sec_kpi_extraction_concept_candidates.csv"
DEFAULT_OUTPUT_DIR = "data/processed"
DEFAULT_PRIVATE_TEMPLATE_DIR = "data/raw/private/fundamentals"
DEFAULT_REPORT_DIR = f"reports/{date.today().isoformat()}"

REVIEW_TABLE_OUTPUT = "personal_sec_companyfacts_concept_review_table.csv"
REVIEW_SUMMARY_OUTPUT = "personal_sec_companyfacts_concept_review_summary.csv"
PRIVATE_APPROVAL_TEMPLATE_OUTPUT = "personal_sec_companyfacts_concept_approval_template.csv"
REPORT_OUTPUT = "personal_sec_companyfacts_concept_review_table_report.md"

REVIEW_TABLE_FIELDS = [
    "review_id",
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "formula_recipe",
    "formula_role",
    "candidate_sec_taxonomy",
    "candidate_sec_concept",
    "candidate_label_or_description",
    "candidate_unit",
    "candidate_years_available",
    "candidate_latest_fiscal_year",
    "candidate_periods_available",
    "candidate_forms_available",
    "candidate_source_artifact",
    "role_required",
    "role_status",
    "concept_confidence",
    "approval_status",
    "approval_reason",
    "reviewer_notes",
    "recommended_approval",
    "auto_apply_after_approval",
    "review_required",
    "next_action",
]

SUMMARY_FIELDS = [
    "total_review_rows",
    "total_missing_kpi_rows",
    "holdings_count",
    "kpi_fields_count",
    "rows_recommended_approve",
    "rows_recommended_review",
    "rows_recommended_reject",
    "rows_auto_apply_after_approval",
    "rows_review_required",
    "recipes_ready_after_approval",
    "recipes_incomplete",
    "no_network_confirmed",
    "no_value_apply_confirmed",
    "no_score_change_confirmed",
    "no_imputation_confirmed",
]

PRIVATE_TEMPLATE_FIELDS = [
    "review_id",
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "formula_recipe",
    "formula_role",
    "candidate_sec_concept",
    "candidate_unit",
    "candidate_years_available",
    "candidate_latest_fiscal_year",
    "recommended_approval",
    "approval_status",
    "approval_reason",
    "reviewer_notes",
]

REVENUE_CONCEPTS = {
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
    "SalesRevenueServicesNet",
}

RECIPE_REQUIRED_ROLES = {
    "revenue_cagr_5y": ("revenue_series",),
    "gross_margin": ("gross_profit", "revenue"),
    "operating_margin": ("operating_income", "revenue"),
    "eps_cagr_5y": ("eps_series",),
    "share_count_cagr_5y": ("share_count_series",),
}

RECIPE_NAMES = {
    "revenue_cagr_5y": "REVENUE_CAGR_5Y",
    "gross_margin": "GROSS_MARGIN",
    "operating_margin": "OPERATING_MARGIN",
    "eps_cagr_5y": "EPS_CAGR_5Y",
    "share_count_cagr_5y": "SHARE_COUNT_CAGR_5Y",
}

PREFERRED_CONCEPTS = {
    "revenue_cagr_5y": ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"),
    "gross_margin": ("GrossProfit", "RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"),
    "operating_margin": ("OperatingIncomeLoss", "RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"),
    "eps_cagr_5y": ("EarningsPerShareDiluted", "EarningsPerShareBasic"),
    "share_count_cagr_5y": ("EntityCommonStockSharesOutstanding", "WeightedAverageNumberOfDilutedSharesOutstanding"),
}

REJECT_CONCEPTS = {
    "CommonStocksIncludingAdditionalPaidInCapitalMember",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
}


@dataclass(frozen=True)
class SecCompanyfactsConceptReviewTableResult:
    review_table_output: Path
    review_summary_output: Path
    private_approval_template_output: Path
    report_output: Path
    review_rows: list[dict[str, str]]
    summary_rows: list[dict[str, str]]


def require_existing_input(path_value: str, label: str) -> Path:
    path = resolve_repo_path(path_value)
    if not path.exists():
        raise FileNotFoundError(f"MISSING_GAP_REVIEW_INPUTS: {label} missing at {path_value}")
    return path


def split_list(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").replace(",", ";").split(";") if item.strip()]


def safe_artifact_path(path_value: str) -> str:
    normalized = str(path_value).replace("\\", "/")
    if "data/raw/private" in normalized or "sec_user_agent" in normalized.lower():
        return "<private_path>"
    return normalized


def safe_id(value: Any) -> str:
    text = str(value or "").strip().upper()
    cleaned = [char if char.isalnum() else "_" for char in text]
    return "_".join("".join(cleaned).split("_")).strip("_")


def concept_to_role(kpi_field: str, concept: str) -> tuple[str, bool, str]:
    if kpi_field == "revenue_cagr_5y" and concept in REVENUE_CONCEPTS:
        return "revenue_series", True, "candidate revenue time series for CAGR"
    if kpi_field == "gross_margin":
        if concept == "GrossProfit":
            return "gross_profit", True, "preferred gross-profit numerator"
        if concept in REVENUE_CONCEPTS:
            return "revenue", True, "candidate revenue denominator"
        if concept in {"CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"}:
            return "cost_of_revenue_review", False, "alternative cost-based formula requires separate review"
    if kpi_field == "operating_margin":
        if concept == "OperatingIncomeLoss":
            return "operating_income", True, "preferred operating-income numerator"
        if concept in REVENUE_CONCEPTS:
            return "revenue", True, "candidate revenue denominator"
        if concept == "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest":
            return "pretax_income_review_proxy", False, "proxy concept is not approved for automatic operating margin"
    if kpi_field == "eps_cagr_5y":
        if concept in {"EarningsPerShareDiluted", "EarningsPerShareBasic"}:
            return "eps_series", True, "candidate EPS time series; diluted preferred when consistent"
        if concept in {"NetIncomeLoss", "WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"}:
            return "eps_component_review", False, "component-derived EPS requires a separate reviewed formula"
    if kpi_field == "share_count_cagr_5y":
        if concept in {
            "EntityCommonStockSharesOutstanding",
            "WeightedAverageNumberOfDilutedSharesOutstanding",
            "WeightedAverageNumberOfSharesOutstandingBasic",
        }:
            return "share_count_series", True, "candidate share-count series; period-end and weighted-average bases must not be mixed automatically"
        if concept == "CommonStocksIncludingAdditionalPaidInCapitalMember":
            return "reject_dimension_member", False, "dimension member is not a usable share-count fact"
    return "unmapped_review", False, "concept is outside the reviewed formula role map"


def row_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (row.get("isin", ""), row.get("ticker", ""), row.get("kpi_field", ""))


def candidate_years_available(row: dict[str, str]) -> str:
    fiscal_year = str(row.get("fiscal_year", "") or "").strip()
    if not fiscal_year:
        return "0"
    return "1"


def candidate_latest_year(row: dict[str, str]) -> str:
    return str(row.get("fiscal_year", "") or "").strip()


def candidate_forms(row: dict[str, str]) -> str:
    return str(row.get("form", "") or "").strip()


def role_status_for(role: str, required: bool, candidates_by_role: dict[str, list[dict[str, str]]]) -> str:
    if not required:
        return "NOT_APPLICABLE"
    count = len(candidates_by_role.get(role, []))
    if count == 0:
        return "MISSING"
    if count == 1:
        return "PRESENT"
    return "AMBIGUOUS"


def concept_confidence(kpi_field: str, concept: str, role_status: str, required: bool) -> str:
    if concept in REJECT_CONCEPTS or not required:
        return "LOW"
    preferred = PREFERRED_CONCEPTS.get(kpi_field, ())
    if concept and preferred and concept == preferred[0] and role_status in {"PRESENT", "AMBIGUOUS"}:
        return "HIGH"
    if concept in preferred:
        return "MEDIUM"
    return "LOW"


def recommended_approval(concept: str, role_status: str, required: bool, years_available: str) -> tuple[str, str]:
    try:
        years = int(str(years_available or "0"))
    except ValueError:
        years = 0
    if concept in REJECT_CONCEPTS:
        return "REJECT", "Candidate is a proxy/dimension concept that is not safe for the reviewed formula."
    if not required:
        return "REVIEW_REQUIRED", "Candidate belongs to an alternative or component formula that is not approved for automatic use."
    if role_status == "MISSING":
        return "REVIEW_REQUIRED", "Required formula role is missing."
    if role_status == "AMBIGUOUS":
        return "REVIEW_REQUIRED", "Multiple concepts can fill this formula role; manual concept selection is required."
    if years >= 6:
        return "APPROVE", "Single required concept with sufficient apparent annual history."
    return "REVIEW_REQUIRED", "Required role is present, but available processed artifacts do not prove sufficient annual history."


def recipe_ready_after_approval(required_roles: tuple[str, ...], candidates_by_role: dict[str, list[dict[str, str]]]) -> bool:
    return all(candidates_by_role.get(role) for role in required_roles)


def recipe_has_ambiguous_required_role(required_roles: tuple[str, ...], candidates_by_role: dict[str, list[dict[str, str]]]) -> bool:
    return any(len(candidates_by_role.get(role, [])) > 1 for role in required_roles)


def build_review_id(isin: str, ticker: str, kpi: str, role: str, concept: str) -> str:
    parts = [safe_id(isin or ticker), safe_id(kpi), safe_id(role), safe_id(concept or "missing")]
    return "__".join(part for part in parts if part)


def candidate_sort_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        row.get("isin", ""),
        row.get("kpi_field", ""),
        row.get("candidate_role", ""),
        row.get("sec_concept", ""),
    )


def build_review_rows(
    *,
    gap_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    candidates_by_gap: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in candidate_rows:
        candidates_by_gap[row_key(row)].append(row)

    review_rows: list[dict[str, str]] = []
    for gap_row in sorted(gap_rows, key=row_key):
        kpi = gap_row.get("kpi_field", "")
        recipe = RECIPE_NAMES.get(kpi, "UNKNOWN_RECIPE")
        required_roles = RECIPE_REQUIRED_ROLES.get(kpi, ())
        candidates = sorted(candidates_by_gap.get(row_key(gap_row), []), key=candidate_sort_key)
        candidates_by_role: dict[str, list[dict[str, str]]] = defaultdict(list)
        mapped_candidates: list[tuple[dict[str, str], str, bool, str]] = []
        for candidate in candidates:
            role, required, role_reason = concept_to_role(kpi, candidate.get("sec_concept", ""))
            mapped_candidates.append((candidate, role, required, role_reason))
            if required:
                candidates_by_role[role].append(candidate)
        ready_after_approval = recipe_ready_after_approval(required_roles, candidates_by_role)
        required_ambiguous = recipe_has_ambiguous_required_role(required_roles, candidates_by_role)

        for role in required_roles:
            if candidates_by_role.get(role):
                continue
            approval, reason = recommended_approval("", "MISSING", True, "0")
            review_rows.append(
                {
                    "review_id": build_review_id(gap_row.get("isin", ""), gap_row.get("ticker", ""), kpi, role, ""),
                    "holding_name": gap_row.get("holding_name", ""),
                    "ticker": gap_row.get("ticker", ""),
                    "isin": gap_row.get("isin", ""),
                    "kpi_field": kpi,
                    "formula_recipe": recipe,
                    "formula_role": role,
                    "candidate_sec_taxonomy": "",
                    "candidate_sec_concept": "",
                    "candidate_label_or_description": "",
                    "candidate_unit": "",
                    "candidate_years_available": "0",
                    "candidate_latest_fiscal_year": "",
                    "candidate_periods_available": "0",
                    "candidate_forms_available": "",
                    "candidate_source_artifact": "",
                    "role_required": "True",
                    "role_status": "MISSING",
                    "concept_confidence": "LOW",
                    "approval_status": "PENDING_REVIEW",
                    "approval_reason": reason,
                    "reviewer_notes": "",
                    "recommended_approval": approval,
                    "auto_apply_after_approval": "False",
                    "review_required": "True",
                    "next_action": "Provide or reject a reviewed SEC concept for this required formula role.",
                }
            )

        for candidate, role, required, role_reason in mapped_candidates:
            years = candidate_years_available(candidate)
            status = role_status_for(role, required, candidates_by_role)
            approval, reason = recommended_approval(candidate.get("sec_concept", ""), status, required, years)
            auto_apply = approval == "APPROVE" and ready_after_approval and not required_ambiguous
            review_rows.append(
                {
                    "review_id": build_review_id(
                        gap_row.get("isin", ""),
                        gap_row.get("ticker", ""),
                        kpi,
                        role,
                        candidate.get("sec_concept", ""),
                    ),
                    "holding_name": gap_row.get("holding_name", ""),
                    "ticker": gap_row.get("ticker", ""),
                    "isin": gap_row.get("isin", ""),
                    "kpi_field": kpi,
                    "formula_recipe": recipe,
                    "formula_role": role,
                    "candidate_sec_taxonomy": candidate.get("sec_taxonomy", ""),
                    "candidate_sec_concept": candidate.get("sec_concept", ""),
                    "candidate_label_or_description": candidate.get("sec_label_or_description", ""),
                    "candidate_unit": candidate.get("unit", ""),
                    "candidate_years_available": years,
                    "candidate_latest_fiscal_year": candidate_latest_year(candidate),
                    "candidate_periods_available": candidate.get("fiscal_period", ""),
                    "candidate_forms_available": candidate_forms(candidate),
                    "candidate_source_artifact": safe_artifact_path(candidate.get("source_artifact", "")),
                    "role_required": str(required),
                    "role_status": status,
                    "concept_confidence": concept_confidence(kpi, candidate.get("sec_concept", ""), status, required),
                    "approval_status": "PENDING_REVIEW",
                    "approval_reason": f"{reason} {role_reason}".strip(),
                    "reviewer_notes": "",
                    "recommended_approval": approval,
                    "auto_apply_after_approval": str(auto_apply),
                    "review_required": str(approval != "APPROVE" or not auto_apply),
                    "next_action": "Approve one concept per required role in the private template before any derived KPI compose step.",
                }
            )
    return sorted(review_rows, key=lambda row: (row["isin"], row["kpi_field"], row["formula_role"], row["candidate_sec_concept"]))


def build_summary_rows(review_rows: list[dict[str, str]], gap_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    approvals = Counter(row["recommended_approval"] for row in review_rows)
    recipe_groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in review_rows:
        recipe_groups[(row["isin"], row["ticker"], row["kpi_field"])].append(row)
    ready = 0
    incomplete = 0
    for (_isin, _ticker, kpi), rows in recipe_groups.items():
        required_roles = set(RECIPE_REQUIRED_ROLES.get(kpi, ()))
        present_roles = {row["formula_role"] for row in rows if row["role_required"] == "True" and row["role_status"] != "MISSING"}
        if required_roles and required_roles.issubset(present_roles):
            ready += 1
        else:
            incomplete += 1
    return [
        {
            "total_review_rows": str(len(review_rows)),
            "total_missing_kpi_rows": str(len(gap_rows)),
            "holdings_count": str(len({row.get("isin", "") for row in gap_rows if row.get("isin", "")})),
            "kpi_fields_count": str(len({row.get("kpi_field", "") for row in gap_rows if row.get("kpi_field", "")})),
            "rows_recommended_approve": str(approvals.get("APPROVE", 0)),
            "rows_recommended_review": str(approvals.get("REVIEW_REQUIRED", 0)),
            "rows_recommended_reject": str(approvals.get("REJECT", 0)),
            "rows_auto_apply_after_approval": str(sum(1 for row in review_rows if row["auto_apply_after_approval"] == "True")),
            "rows_review_required": str(sum(1 for row in review_rows if row["review_required"] == "True")),
            "recipes_ready_after_approval": str(ready),
            "recipes_incomplete": str(incomplete),
            "no_network_confirmed": "True",
            "no_value_apply_confirmed": "True",
            "no_score_change_confirmed": "True",
            "no_imputation_confirmed": "True",
        }
    ]


def private_template_rows(review_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [{field: row.get(field, "") for field in PRIVATE_TEMPLATE_FIELDS} for row in review_rows]


def render_report(
    *,
    review_rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
    input_paths: dict[str, str],
    private_template_path: str,
) -> str:
    summary = summary_rows[0] if summary_rows else {}
    lines = [
        "# Personal SEC CompanyFacts Concept Review Table",
        "",
        "## Executive Summary",
        f"- Review rows: `{summary.get('total_review_rows', '0')}`",
        f"- Missing KPI rows covered: `{summary.get('total_missing_kpi_rows', '0')}`",
        f"- Rows recommended approve: `{summary.get('rows_recommended_approve', '0')}`",
        f"- Rows recommended review: `{summary.get('rows_recommended_review', '0')}`",
        f"- Rows recommended reject: `{summary.get('rows_recommended_reject', '0')}`",
        f"- Recipes ready after approval: `{summary.get('recipes_ready_after_approval', '0')}`",
        "",
        "## Scope",
        "This review table prepares manual SEC concept approval only. It does not calculate KPI values or apply evidence.",
        "",
        "## Input Artefacts",
    ]
    for label, path_value in sorted(input_paths.items()):
        lines.append(f"- `{label}`: `{safe_artifact_path(path_value)}`")
    lines.extend(
        [
            "",
            "## Review Table Summary",
            f"- Auto-apply rows after approval: `{summary.get('rows_auto_apply_after_approval', '0')}`",
            f"- Review-required rows: `{summary.get('rows_review_required', '0')}`",
            f"- Recipes incomplete: `{summary.get('recipes_incomplete', '0')}`",
            "",
            "## Holding-level Review Needs",
            "| holding | isin | kpi | roles | concepts | recommended | auto_apply |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in review_rows:
        grouped[(row["holding_name"], row["isin"], row["kpi_field"])].append(row)
    for (holding, isin, kpi), rows in sorted(grouped.items(), key=lambda item: (item[0][1], item[0][2])):
        roles = ";".join(sorted({row["formula_role"] for row in rows if row["role_required"] == "True"}))
        concepts = ";".join(sorted({row["candidate_sec_concept"] for row in rows if row["candidate_sec_concept"]}))
        recommended = ";".join(sorted({row["recommended_approval"] for row in rows}))
        auto_apply = "True" if any(row["auto_apply_after_approval"] == "True" for row in rows) else "False"
        lines.append(f"| {holding} | {isin} | `{kpi}` | `{roles}` | `{concepts}` | `{recommended}` | `{auto_apply}` |")
    lines.extend(
        [
            "",
            "## Formula Recipes",
            "- `REVENUE_CAGR_5Y`: approve one consistent revenue series.",
            "- `GROSS_MARGIN`: approve gross profit and one consistent revenue concept.",
            "- `OPERATING_MARGIN`: approve operating income and one consistent revenue concept.",
            "- `EPS_CAGR_5Y`: approve one EPS series, preferably diluted when consistent.",
            "- `SHARE_COUNT_CAGR_5Y`: approve one share-count basis; do not mix period-end and weighted-average concepts automatically.",
            "",
            "## Approval Instructions",
            f"- Private approval template: `{safe_artifact_path(private_template_path)}`",
            "- Fill `approval_status` with one of `APPROVED`, `REJECTED`, or `REVIEW_REQUIRED`.",
            "- Do not add calculated KPI values to the approval template.",
            "",
            "## Guardrail Confirmation",
            "- No network fetch performed.",
            "- No value apply performed.",
            "- No score formula changes performed.",
            "- No imputation performed.",
            "- No website artifacts generated.",
            "",
            "## Next Recommended Patch",
            "`MANUAL SEC CONCEPT APPROVAL FILL / PRIVATE INPUT ONLY`",
        ]
    )
    return "\n".join(lines)


def run_personal_sec_companyfacts_concept_review_table(
    *,
    gap_matrix: str = DEFAULT_GAP_MATRIX,
    concept_candidates: str = DEFAULT_CONCEPT_CANDIDATES,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    private_template_dir: str = DEFAULT_PRIVATE_TEMPLATE_DIR,
    report_dir: str = DEFAULT_REPORT_DIR,
) -> SecCompanyfactsConceptReviewTableResult:
    require_existing_input(gap_matrix, "gap_matrix")
    require_existing_input(concept_candidates, "concept_candidates")
    gap_rows = read_csv_rows(gap_matrix)
    candidate_rows = read_csv_rows(concept_candidates)
    if not gap_rows or not candidate_rows:
        raise ValueError("MISSING_GAP_REVIEW_INPUTS: gap matrix and concept candidates must contain rows")
    review_rows = build_review_rows(gap_rows=gap_rows, candidate_rows=candidate_rows)
    summary_rows = build_summary_rows(review_rows, gap_rows)
    output_base = resolve_repo_path(output_dir)
    private_base = resolve_repo_path(private_template_dir)
    report_base = resolve_repo_path(report_dir)
    review_table_output = output_base / REVIEW_TABLE_OUTPUT
    review_summary_output = output_base / REVIEW_SUMMARY_OUTPUT
    private_approval_template_output = private_base / PRIVATE_APPROVAL_TEMPLATE_OUTPUT
    report_output = report_base / REPORT_OUTPUT
    write_csv_rows(review_table_output, REVIEW_TABLE_FIELDS, review_rows)
    write_csv_rows(review_summary_output, SUMMARY_FIELDS, summary_rows)
    write_csv_rows(private_approval_template_output, PRIVATE_TEMPLATE_FIELDS, private_template_rows(review_rows))
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        render_report(
            review_rows=review_rows,
            summary_rows=summary_rows,
            input_paths={"gap_matrix": gap_matrix, "concept_candidates": concept_candidates},
            private_template_path=str(private_approval_template_output),
        ),
        encoding="utf-8",
    )
    return SecCompanyfactsConceptReviewTableResult(
        review_table_output=review_table_output,
        review_summary_output=review_summary_output,
        private_approval_template_output=private_approval_template_output,
        report_output=report_output,
        review_rows=review_rows,
        summary_rows=summary_rows,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a manual SEC CompanyFacts concept approval table without applying values.")
    parser.add_argument("--gap-matrix", default=DEFAULT_GAP_MATRIX)
    parser.add_argument("--concept-candidates", default=DEFAULT_CONCEPT_CANDIDATES)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--private-template-dir", default=DEFAULT_PRIVATE_TEMPLATE_DIR)
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_companyfacts_concept_review_table(
        gap_matrix=args.gap_matrix,
        concept_candidates=args.concept_candidates,
        output_dir=args.output_dir,
        private_template_dir=args.private_template_dir,
        report_dir=args.report_dir,
    )
    summary = result.summary_rows[0] if result.summary_rows else {}
    print(f"review_table_output={result.review_table_output}")
    print(f"review_summary_output={result.review_summary_output}")
    print(f"private_approval_template_output={safe_artifact_path(str(result.private_approval_template_output))}")
    print(f"report_output={result.report_output}")
    print(f"total_review_rows={summary.get('total_review_rows', '0')}")
    print("no_network_confirmed=True")


if __name__ == "__main__":
    main()
