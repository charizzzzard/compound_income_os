from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, read_csv_rows, resolve_repo_path, write_csv_rows

DEFAULT_CLOSURE_QUEUE = "data/processed/personal_core_kpi_closure_queue.csv"
DEFAULT_SEC_NORMALIZED = "data/processed/personal_fundamentals_snapshot_normalized.csv"
DEFAULT_SEC_STAGING = "data/processed/personal_fundamentals_snapshot_evidence_staging.csv"
DEFAULT_SEC_FETCH_REGISTRY = "data/processed/external_sec_fetch_registry.csv"
DEFAULT_SEC_FETCH_FAILURES = "data/processed/external_sec_fetch_failures.csv"
DEFAULT_EVIDENCE_REGISTRY = "data/processed/personal_fundamentals_evidence_registry.csv"
DEFAULT_EVIDENCE_APPLY = "data/processed/personal_fundamentals_evidence_apply_registry.csv"
DEFAULT_PROPOSED_UPDATES = "data/processed/personal_fundamentals_proposed_updates.csv"
DEFAULT_OUTPUT_DIR = "data/processed"
DEFAULT_REPORT_DIR = f"reports/{date.today().isoformat()}"

GAP_MATRIX_OUTPUT = "personal_sec_kpi_extraction_gap_matrix.csv"
CONCEPT_CANDIDATES_OUTPUT = "personal_sec_kpi_extraction_concept_candidates.csv"
GAP_SUMMARY_OUTPUT = "personal_sec_kpi_extraction_gap_summary.csv"
REPORT_OUTPUT = "personal_sec_kpi_extraction_gap_review_report.md"

MATRIX_FIELDS = [
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "current_status",
    "missing_reason_from_closure",
    "sec_identity_status",
    "companyfacts_fetch_status",
    "normalized_fact_available",
    "candidate_sec_concepts",
    "candidate_fact_count",
    "candidate_periods_available",
    "latest_candidate_fiscal_year",
    "required_period_window",
    "evidence_registry_match_status",
    "evidence_apply_match_status",
    "proposed_update_match_status",
    "extraction_gap_type",
    "extraction_gap_reason",
    "recommended_next_action",
    "auto_fix_safe",
    "review_required",
]

CANDIDATE_FIELDS = [
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "sec_taxonomy",
    "sec_concept",
    "sec_label_or_description",
    "unit",
    "fiscal_year",
    "fiscal_period",
    "form",
    "filed_date",
    "frame",
    "value_present",
    "value_is_numeric",
    "candidate_role",
    "usable_for_metric",
    "rejection_reason",
    "source_artifact",
]

SUMMARY_FIELDS = [
    "total_missing_kpi_rows",
    "rows_with_companyfacts_fetch",
    "rows_with_any_candidate_fact",
    "rows_with_no_candidate_fact",
    "rows_blocked_by_missing_concept_mapping",
    "rows_blocked_by_period_window",
    "rows_blocked_by_unit_or_numeric_issue",
    "rows_blocked_by_review_gate",
    "rows_blocked_by_derived_metric_logic",
    "rows_potentially_auto_mappable",
    "rows_review_required",
    "rows_manual_only",
    "no_score_change_confirmed",
    "no_imputation_confirmed",
    "network_performed",
]

KPI_CONCEPTS: dict[str, list[tuple[str, str, str]]] = {
    "revenue_cagr_5y": [
        ("Revenues", "USD", "revenue_series"),
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "USD", "revenue_series"),
        ("SalesRevenueNet", "USD", "revenue_series"),
        ("SalesRevenueGoodsNet", "USD", "revenue_series"),
        ("SalesRevenueServicesNet", "USD", "revenue_series"),
    ],
    "gross_margin": [
        ("Revenues", "USD", "denominator_revenue"),
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "USD", "denominator_revenue"),
        ("SalesRevenueNet", "USD", "denominator_revenue"),
        ("CostOfRevenue", "USD", "cost_input"),
        ("CostOfGoodsAndServicesSold", "USD", "cost_input"),
        ("CostOfGoodsSold", "USD", "cost_input"),
        ("GrossProfit", "USD", "numerator_gross_profit"),
    ],
    "operating_margin": [
        ("OperatingIncomeLoss", "USD", "numerator_operating_income"),
        ("IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest", "USD", "review_only_income_proxy"),
        ("Revenues", "USD", "denominator_revenue"),
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "USD", "denominator_revenue"),
        ("SalesRevenueNet", "USD", "denominator_revenue"),
    ],
    "eps_cagr_5y": [
        ("EarningsPerShareDiluted", "USD/shares", "eps_series"),
        ("EarningsPerShareBasic", "USD/shares", "eps_series_review"),
        ("NetIncomeLoss", "USD", "net_income_input"),
        ("WeightedAverageNumberOfDilutedSharesOutstanding", "shares", "share_input"),
        ("WeightedAverageNumberOfSharesOutstandingBasic", "shares", "share_input_review"),
    ],
    "share_count_cagr_5y": [
        ("EntityCommonStockSharesOutstanding", "shares", "period_end_share_series"),
        ("WeightedAverageNumberOfDilutedSharesOutstanding", "shares", "weighted_average_share_series"),
        ("WeightedAverageNumberOfSharesOutstandingBasic", "shares", "weighted_average_share_series_review"),
        ("CommonStocksIncludingAdditionalPaidInCapitalMember", "", "reject_dimension_member"),
    ],
}

REQUIRED_PERIOD_WINDOW = {
    "revenue_cagr_5y": "six annual revenue observations ending at latest fiscal year",
    "gross_margin": "latest annual gross profit or cost plus revenue with consistent unit",
    "operating_margin": "latest annual operating income plus revenue with consistent unit",
    "eps_cagr_5y": "six annual EPS observations or net income/share observations",
    "share_count_cagr_5y": "six annual share-count observations with consistent basis",
}

DERIVED_KPIS = {"revenue_cagr_5y", "gross_margin", "operating_margin", "eps_cagr_5y", "share_count_cagr_5y"}


@dataclass(frozen=True)
class SecKpiExtractionGapReviewResult:
    gap_matrix_output: Path
    concept_candidates_output: Path
    gap_summary_output: Path
    report_output: Path
    matrix_rows: list[dict[str, str]]
    candidate_rows: list[dict[str, str]]
    summary_rows: list[dict[str, str]]


def optional_csv_rows(path_value: str | Path) -> list[dict[str, str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return []
    return read_csv_rows(path)


def split_list(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").replace(",", ";").split(";") if item.strip()]


def joined(values: list[str] | set[str] | tuple[str, ...]) -> str:
    return ";".join(sorted(value for value in values if value))


def canonical_isin(value: Any) -> str:
    return str(value or "").strip().upper()


def identifier_keys(row: dict[str, str]) -> list[str]:
    keys = []
    ticker = canonicalize_ticker(row.get("ticker", ""))
    isin = canonical_isin(row.get("isin", ""))
    if ticker:
        keys.append(f"ticker:{ticker}")
    if isin:
        keys.append(f"isin:{isin}")
    return keys


def index_first_by_identifier(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in rows:
        for key in identifier_keys(row):
            index.setdefault(key, row)
    return index


def index_rows_by_identifier_kpi(rows: list[dict[str, str]], kpi_fields: tuple[str, ...]) -> dict[tuple[str, str], list[dict[str, str]]]:
    index: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        kpi = next((str(row.get(field, "")).strip() for field in kpi_fields if str(row.get(field, "")).strip()), "")
        if not kpi:
            continue
        for key in identifier_keys(row):
            index.setdefault((key, kpi), []).append(row)
    return index


def lookup_identifier(index: dict[str, dict[str, str]], row: dict[str, str]) -> dict[str, str]:
    for key in identifier_keys(row):
        if key in index:
            return index[key]
    return {}


def lookup_identifier_kpi(index: dict[tuple[str, str], list[dict[str, str]]], row: dict[str, str], kpi: str) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    seen: set[int] = set()
    for key in identifier_keys(row):
        for match in index.get((key, kpi), []):
            marker = id(match)
            if marker not in seen:
                seen.add(marker)
                matches.append(match)
    return matches


def is_numeric_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    try:
        float(text.replace(",", ""))
    except ValueError:
        return False
    return True


def source_artifact_label(path_value: str) -> str:
    normalized = str(path_value).replace("\\", "/")
    if "data/raw/private" in normalized or "sec_user_agent" in normalized.lower():
        return "<private_path>"
    return normalized


def fiscal_year_from_reference(value: str) -> str:
    text = str(value or "")
    marker = "FY"
    if marker not in text:
        return ""
    suffix = text.split(marker, 1)[1]
    year = "".join(char for char in suffix[:4] if char.isdigit())
    return year if len(year) == 4 else ""


def fetch_status_for(row: dict[str, str], registry_index: dict[str, dict[str, str]], failures_index: dict[str, dict[str, str]]) -> str:
    registry = lookup_identifier(registry_index, row)
    if registry:
        return registry.get("fetch_status", "FETCHED") or "FETCHED"
    failure = lookup_identifier(failures_index, row)
    if failure:
        return failure.get("failure_reason", "FAILED")
    return "NOT_FOUND"


def normalized_value(row: dict[str, str], normalized_index: dict[str, dict[str, str]], kpi: str) -> str:
    normalized = lookup_identifier(normalized_index, row)
    return str(normalized.get(kpi, "") or "").strip()


def match_status(matches: list[dict[str, str]], *, empty_status: str, status_field: str = "") -> str:
    if not matches:
        return empty_status
    if status_field:
        statuses = sorted({str(row.get(status_field, "") or "").strip() for row in matches if str(row.get(status_field, "") or "").strip()})
        if statuses:
            return "MATCHED_" + ";".join(statuses)
    return "MATCHED"


def classify_gap(
    *,
    fetch_status: str,
    normalized_row_present: bool,
    normalized_fact_available: bool,
    candidate_count: int,
    evidence_matches: list[dict[str, str]],
    apply_matches: list[dict[str, str]],
    proposed_matches: list[dict[str, str]],
    kpi: str,
) -> tuple[str, str, str]:
    if fetch_status != "FETCHED":
        return "NO_COMPANYFACTS_FETCH", f"CompanyFacts fetch status is {fetch_status}.", "Review SEC identity/fetch status before extraction."
    if not normalized_row_present:
        return "NO_NORMALIZED_FACTS_FOR_HOLDING", "No normalized SEC snapshot row matched the holding.", "Review identity matching between fetch registry and normalized snapshot."
    if candidate_count == 0:
        return "MISSING_CONCEPT_MAPPING", f"No SEC concept candidate allowlist exists for {kpi}.", "Add an explicit reviewed concept mapping before any extraction."
    if normalized_fact_available and not evidence_matches and not proposed_matches and not apply_matches:
        return (
            "CANDIDATE_FACTS_FOUND_NOT_MAPPED",
            "A normalized snapshot value exists, but no evidence/proposed/apply row matches this holding KPI.",
            "Review snapshot-review and evidence-compose gates for this KPI.",
        )
    if evidence_matches and not apply_matches:
        return (
            "EVIDENCE_COMPOSED_NOT_APPLIED",
            "Evidence rows exist, but no apply-registry row matched this holding KPI.",
            "Review evidence-apply gating for this KPI.",
        )
    if kpi in DERIVED_KPIS:
        return (
            "DERIVED_METRIC_LOGIC_MISSING",
            "The current processed artifacts expose only KPI-level snapshot outputs; the missing KPI has candidate SEC concepts but no persisted concept-level annual series or approved derived-KPI composition.",
            "Create a reviewed SEC concept table and derived KPI compose step before applying evidence.",
        )
    return "UNKNOWN_REVIEW_REQUIRED", "No deterministic extraction reason could be proven from processed artifacts.", "Manual review required."


def build_candidate_rows(
    *,
    closure_row: dict[str, str],
    kpi: str,
    normalized_row: dict[str, str],
    normalized_fact_available: bool,
    normalized_input: str,
) -> list[dict[str, str]]:
    fiscal_year = normalized_row.get("fiscal_year", "") or fiscal_year_from_reference(normalized_row.get("source_reference", ""))
    filed_date = normalized_row.get("source_as_of_date", "")
    value_is_numeric = is_numeric_text(normalized_row.get(kpi, ""))
    rows: list[dict[str, str]] = []
    for concept, unit, role in KPI_CONCEPTS.get(kpi, []):
        usable = normalized_fact_available and value_is_numeric
        if usable:
            rejection = "review gate required before score-relevant evidence use"
        else:
            rejection = "processed artifacts do not expose a usable concept-level annual fact for this missing KPI"
        rows.append(
            {
                "holding_name": closure_row.get("company_name", ""),
                "ticker": closure_row.get("ticker", ""),
                "isin": closure_row.get("isin", ""),
                "kpi_field": kpi,
                "sec_taxonomy": "us-gaap",
                "sec_concept": concept,
                "sec_label_or_description": concept,
                "unit": unit,
                "fiscal_year": fiscal_year,
                "fiscal_period": "FY" if fiscal_year else "",
                "form": "10-K/10-K-A candidate",
                "filed_date": filed_date,
                "frame": "",
                "value_present": str(normalized_fact_available),
                "value_is_numeric": str(value_is_numeric),
                "candidate_role": role,
                "usable_for_metric": "False",
                "rejection_reason": rejection,
                "source_artifact": source_artifact_label(normalized_input),
            }
        )
    return rows


def build_gap_review(
    *,
    closure_rows: list[dict[str, str]],
    normalized_rows: list[dict[str, str]],
    staging_rows: list[dict[str, str]],
    fetch_registry_rows: list[dict[str, str]],
    fetch_failure_rows: list[dict[str, str]],
    evidence_registry_rows: list[dict[str, str]],
    evidence_apply_rows: list[dict[str, str]],
    proposed_update_rows: list[dict[str, str]],
    normalized_input: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    normalized_index = index_first_by_identifier(normalized_rows)
    fetch_registry_index = index_first_by_identifier(fetch_registry_rows)
    fetch_failure_index = index_first_by_identifier(fetch_failure_rows)
    evidence_index = index_rows_by_identifier_kpi(evidence_registry_rows, ("kpi_name", "target_field"))
    apply_index = index_rows_by_identifier_kpi(evidence_apply_rows, ("target_field", "kpi_name"))
    proposed_index = index_rows_by_identifier_kpi(proposed_update_rows, ("kpi_name", "target_field"))
    staging_index = index_rows_by_identifier_kpi(staging_rows, ("kpi_name", "target_field"))

    matrix_rows: list[dict[str, str]] = []
    candidate_rows: list[dict[str, str]] = []
    sorted_closure_rows = sorted(closure_rows, key=lambda row: (canonical_isin(row.get("isin", "")), canonicalize_ticker(row.get("ticker", ""))))
    for closure_row in sorted_closure_rows:
        for kpi in split_list(closure_row.get("missing_core_kpis", "")):
            normalized_row = lookup_identifier(normalized_index, closure_row)
            normalized_row_present = bool(normalized_row)
            normalized_fact_available = bool(normalized_value(closure_row, normalized_index, kpi))
            concepts = [concept for concept, _unit, _role in KPI_CONCEPTS.get(kpi, [])]
            candidate_count = len(concepts) if normalized_row_present else 0
            evidence_matches = lookup_identifier_kpi(evidence_index, closure_row, kpi)
            apply_matches = lookup_identifier_kpi(apply_index, closure_row, kpi)
            proposed_matches = lookup_identifier_kpi(proposed_index, closure_row, kpi)
            staging_matches = lookup_identifier_kpi(staging_index, closure_row, kpi)
            fetch_status = fetch_status_for(closure_row, fetch_registry_index, fetch_failure_index)
            gap_type, gap_reason, next_action = classify_gap(
                fetch_status=fetch_status,
                normalized_row_present=normalized_row_present,
                normalized_fact_available=normalized_fact_available,
                candidate_count=candidate_count,
                evidence_matches=evidence_matches or staging_matches,
                apply_matches=apply_matches,
                proposed_matches=proposed_matches,
                kpi=kpi,
            )
            fiscal_year = normalized_row.get("fiscal_year", "") or fiscal_year_from_reference(normalized_row.get("source_reference", ""))
            matrix_rows.append(
                {
                    "holding_name": closure_row.get("company_name", ""),
                    "ticker": closure_row.get("ticker", ""),
                    "isin": closure_row.get("isin", ""),
                    "kpi_field": kpi,
                    "current_status": closure_row.get("core_kpi_closure_status", ""),
                    "missing_reason_from_closure": closure_row.get("reason_code", ""),
                    "sec_identity_status": closure_row.get("sec_scope_status", ""),
                    "companyfacts_fetch_status": fetch_status,
                    "normalized_fact_available": str(normalized_fact_available),
                    "candidate_sec_concepts": joined(concepts),
                    "candidate_fact_count": str(candidate_count),
                    "candidate_periods_available": "1" if fiscal_year else "0",
                    "latest_candidate_fiscal_year": fiscal_year,
                    "required_period_window": REQUIRED_PERIOD_WINDOW.get(kpi, ""),
                    "evidence_registry_match_status": match_status(evidence_matches or staging_matches, empty_status="NO_EVIDENCE"),
                    "evidence_apply_match_status": match_status(apply_matches, empty_status="NO_APPLIED_VALUE", status_field="apply_status"),
                    "proposed_update_match_status": match_status(proposed_matches, empty_status="NO_PROPOSED_UPDATE"),
                    "extraction_gap_type": gap_type,
                    "extraction_gap_reason": gap_reason,
                    "recommended_next_action": next_action,
                    "auto_fix_safe": "False",
                    "review_required": "True",
                }
            )
            candidate_rows.extend(
                build_candidate_rows(
                    closure_row=closure_row,
                    kpi=kpi,
                    normalized_row=normalized_row,
                    normalized_fact_available=normalized_fact_available,
                    normalized_input=normalized_input,
                )
            )

    gap_counts = Counter(row["extraction_gap_type"] for row in matrix_rows)
    summary_rows = [
        {
            "total_missing_kpi_rows": str(len(matrix_rows)),
            "rows_with_companyfacts_fetch": str(sum(1 for row in matrix_rows if row["companyfacts_fetch_status"] == "FETCHED")),
            "rows_with_any_candidate_fact": str(sum(1 for row in matrix_rows if int(row["candidate_fact_count"] or "0") > 0)),
            "rows_with_no_candidate_fact": str(sum(1 for row in matrix_rows if int(row["candidate_fact_count"] or "0") == 0)),
            "rows_blocked_by_missing_concept_mapping": str(gap_counts.get("MISSING_CONCEPT_MAPPING", 0)),
            "rows_blocked_by_period_window": str(gap_counts.get("PERIOD_WINDOW_INSUFFICIENT", 0)),
            "rows_blocked_by_unit_or_numeric_issue": str(gap_counts.get("UNIT_OR_NUMERIC_VALIDATION_FAILED", 0)),
            "rows_blocked_by_review_gate": str(sum(1 for row in matrix_rows if row["review_required"] == "True")),
            "rows_blocked_by_derived_metric_logic": str(gap_counts.get("DERIVED_METRIC_LOGIC_MISSING", 0)),
            "rows_potentially_auto_mappable": str(sum(1 for row in matrix_rows if row["auto_fix_safe"] == "True")),
            "rows_review_required": str(sum(1 for row in matrix_rows if row["review_required"] == "True")),
            "rows_manual_only": str(sum(1 for row in matrix_rows if row["candidate_fact_count"] == "0")),
            "no_score_change_confirmed": "True",
            "no_imputation_confirmed": "True",
            "network_performed": "False",
        }
    ]
    return matrix_rows, candidate_rows, summary_rows


def render_report(
    *,
    matrix_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
    input_paths: dict[str, str],
) -> str:
    summary = summary_rows[0] if summary_rows else {}
    lines = [
        "# Personal SEC KPI Extraction Gap Review",
        "",
        "## Executive Summary",
        f"- Total missing KPI rows: `{summary.get('total_missing_kpi_rows', '0')}`",
        f"- Rows with CompanyFacts fetch: `{summary.get('rows_with_companyfacts_fetch', '0')}`",
        f"- Rows with candidate concepts: `{summary.get('rows_with_any_candidate_fact', '0')}`",
        f"- Rows blocked by derived metric logic: `{summary.get('rows_blocked_by_derived_metric_logic', '0')}`",
        f"- Rows review required: `{summary.get('rows_review_required', '0')}`",
        f"- Network performed: `{summary.get('network_performed', 'False')}`",
        "",
        "## Scope",
        "This report reads existing processed SEC, snapshot, evidence and closure artifacts only.",
        "",
        "## Input Artefacts",
    ]
    for label, path_value in sorted(input_paths.items()):
        lines.append(f"- `{label}`: `{source_artifact_label(path_value)}`")
    lines.extend(
        [
            "",
            "## Gap Matrix",
            "| holding | isin | kpi | fetch | candidates | gap_type | next_action |",
            "| --- | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for row in matrix_rows:
        lines.append(
            f"| {row['holding_name']} | {row['isin']} | `{row['kpi_field']}` | `{row['companyfacts_fetch_status']}` | `{row['candidate_fact_count']}` | `{row['extraction_gap_type']}` | {row['recommended_next_action']} |"
        )
    gap_counts = Counter(row["extraction_gap_type"] for row in matrix_rows)
    lines.extend(["", "## Gap Types"])
    for gap_type, count in sorted(gap_counts.items()):
        lines.append(f"- `{gap_type}`: `{count}`")
    top_candidates = Counter(row["sec_concept"] for row in candidate_rows)
    lines.extend(["", "## Candidate SEC Concepts"])
    for concept, count in sorted(top_candidates.items()):
        lines.append(f"- `{concept}`: `{count}`")
    lines.extend(
        [
            "",
            "## Auto-fix-safe vs Review-required",
            f"- Auto-fix-safe rows: `{summary.get('rows_potentially_auto_mappable', '0')}`",
            f"- Review-required rows: `{summary.get('rows_review_required', '0')}`",
            "",
            "## Recommended Next Patch",
            "`SEC COMPANYFACTS CONCEPT REVIEW TABLE / MANUAL APPROVAL INPUT`",
            "",
            "## Guardrail Confirmation",
            "- No network fetch performed.",
            "- No score formula changes performed.",
            "- No imputation performed.",
            "- No raw master mutation performed.",
            "- No website artifacts generated.",
        ]
    )
    return "\n".join(lines)


def run_personal_sec_kpi_extraction_gap_review(
    *,
    closure_queue: str = DEFAULT_CLOSURE_QUEUE,
    sec_normalized: str = DEFAULT_SEC_NORMALIZED,
    sec_staging: str = DEFAULT_SEC_STAGING,
    sec_fetch_registry: str = DEFAULT_SEC_FETCH_REGISTRY,
    sec_fetch_failures: str = DEFAULT_SEC_FETCH_FAILURES,
    evidence_registry: str = DEFAULT_EVIDENCE_REGISTRY,
    evidence_apply: str = DEFAULT_EVIDENCE_APPLY,
    proposed_updates: str = DEFAULT_PROPOSED_UPDATES,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    report_dir: str = DEFAULT_REPORT_DIR,
) -> SecKpiExtractionGapReviewResult:
    matrix_rows, candidate_rows, summary_rows = build_gap_review(
        closure_rows=optional_csv_rows(closure_queue),
        normalized_rows=optional_csv_rows(sec_normalized),
        staging_rows=optional_csv_rows(sec_staging),
        fetch_registry_rows=optional_csv_rows(sec_fetch_registry),
        fetch_failure_rows=optional_csv_rows(sec_fetch_failures),
        evidence_registry_rows=optional_csv_rows(evidence_registry),
        evidence_apply_rows=optional_csv_rows(evidence_apply),
        proposed_update_rows=optional_csv_rows(proposed_updates),
        normalized_input=sec_normalized,
    )
    output_base = resolve_repo_path(output_dir)
    report_base = resolve_repo_path(report_dir)
    gap_matrix_output = output_base / GAP_MATRIX_OUTPUT
    concept_candidates_output = output_base / CONCEPT_CANDIDATES_OUTPUT
    gap_summary_output = output_base / GAP_SUMMARY_OUTPUT
    report_output = report_base / REPORT_OUTPUT
    write_csv_rows(gap_matrix_output, MATRIX_FIELDS, matrix_rows)
    write_csv_rows(concept_candidates_output, CANDIDATE_FIELDS, candidate_rows)
    write_csv_rows(gap_summary_output, SUMMARY_FIELDS, summary_rows)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        render_report(
            matrix_rows=matrix_rows,
            candidate_rows=candidate_rows,
            summary_rows=summary_rows,
            input_paths={
                "closure_queue": closure_queue,
                "sec_normalized": sec_normalized,
                "sec_staging": sec_staging,
                "sec_fetch_registry": sec_fetch_registry,
                "sec_fetch_failures": sec_fetch_failures,
                "evidence_registry": evidence_registry,
                "evidence_apply": evidence_apply,
                "proposed_updates": proposed_updates,
            },
        ),
        encoding="utf-8",
    )
    return SecKpiExtractionGapReviewResult(
        gap_matrix_output=gap_matrix_output,
        concept_candidates_output=concept_candidates_output,
        gap_summary_output=gap_summary_output,
        report_output=report_output,
        matrix_rows=matrix_rows,
        candidate_rows=candidate_rows,
        summary_rows=summary_rows,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review SEC KPI extraction gaps without network or score changes.")
    parser.add_argument("--closure-queue", default=DEFAULT_CLOSURE_QUEUE)
    parser.add_argument("--sec-normalized", default=DEFAULT_SEC_NORMALIZED)
    parser.add_argument("--sec-staging", default=DEFAULT_SEC_STAGING)
    parser.add_argument("--sec-fetch-registry", default=DEFAULT_SEC_FETCH_REGISTRY)
    parser.add_argument("--sec-fetch-failures", default=DEFAULT_SEC_FETCH_FAILURES)
    parser.add_argument("--evidence-registry", default=DEFAULT_EVIDENCE_REGISTRY)
    parser.add_argument("--evidence-apply", default=DEFAULT_EVIDENCE_APPLY)
    parser.add_argument("--proposed-updates", default=DEFAULT_PROPOSED_UPDATES)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_kpi_extraction_gap_review(
        closure_queue=args.closure_queue,
        sec_normalized=args.sec_normalized,
        sec_staging=args.sec_staging,
        sec_fetch_registry=args.sec_fetch_registry,
        sec_fetch_failures=args.sec_fetch_failures,
        evidence_registry=args.evidence_registry,
        evidence_apply=args.evidence_apply,
        proposed_updates=args.proposed_updates,
        output_dir=args.output_dir,
        report_dir=args.report_dir,
    )
    summary = result.summary_rows[0] if result.summary_rows else {}
    print(f"gap_matrix_output={result.gap_matrix_output}")
    print(f"concept_candidates_output={result.concept_candidates_output}")
    print(f"gap_summary_output={result.gap_summary_output}")
    print(f"report_output={result.report_output}")
    print(f"total_missing_kpi_rows={summary.get('total_missing_kpi_rows', '0')}")
    print(f"network_performed={summary.get('network_performed', 'False')}")


if __name__ == "__main__":
    main()
