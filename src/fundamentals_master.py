from __future__ import annotations

import argparse
from datetime import date
import re
from typing import Any

from src.common import (
    canonicalize_ticker,
    ensure_parent_dir,
    load_yaml_config,
    normalize_number_text,
    read_csv_rows,
    require_columns,
    safe_upper,
    write_csv_rows,
)
from src.portfolio_rules import aggregate_positions_by_ticker

DEFAULT_METRIC_DEFINITIONS_PATH = "configs/fundamentals_metric_definitions.yaml"
DEFAULT_PERSONAL_MASTER_PATH = "data/raw/personal_fundamentals_master.csv"
DEFAULT_COVERAGE_OUTPUT = "data/processed/personal_fundamentals_coverage.csv"
DEFAULT_ENRICHED_OUTPUT = "data/processed/personal_fundamentals_enriched.csv"

VALID_COMPANY_TYPE_PROFILES = {"STANDARD", "FINANCIAL", "REIT", "OTHER"}
VALID_DATA_QUALITY_FLAGS = {"OK", "REVIEW", "MISSING_DATA"}
ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

IDENTITY_METADATA_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "currency",
    "sector",
    "country",
    "asset_type",
    "company_type_profile",
    "source_name",
    "source_as_of_date",
    "fiscal_period",
    "fiscal_year",
    "report_date",
    "filing_date",
    "market_price_date",
    "calculation_version",
    "data_quality_flag",
    "notes",
]

SCORING_COMPATIBILITY_FIELDS = [
    "sleeve",
    "current_price_eur",
    "mandate_fit_score",
]

CORE_KPI_FIELDS = [
    "revenue_cagr_5y",
    "eps_cagr_5y",
    "fcf_per_share_cagr_5y",
    "roic",
    "roce",
    "gross_margin",
    "operating_margin",
    "fcf_margin",
    "net_debt_to_ebitda",
    "interest_coverage",
    "dividend_yield_current_pct",
    "dividend_yield_hist_pct",
    "dividend_cagr_5y",
    "dividend_streak_years",
    "payout_ratio_eps",
    "payout_ratio_fcf",
    "share_count_cagr_5y",
    "buyback_yield",
    "pe_current",
    "pe_hist",
    "ev_ebit_current",
    "ev_ebit_hist",
    "fcf_yield_current_pct",
    "fcf_yield_hist_pct",
    "normalized_fcf_yield_pct",
    "target_fcf_yield_pct",
    "drawdown_from_high_pct",
    "expected_return_pct",
]

OVERLAY_FIELDS = [
    "overlay_thesis_robustness",
    "overlay_has_hard_risk_flag",
    "overlay_analyst_notes",
    "overlay_manual_override_flag",
    "overlay_manual_override_reason",
]

PERSONAL_MASTER_FIELDS = [
    *IDENTITY_METADATA_FIELDS,
    *SCORING_COMPATIBILITY_FIELDS,
    *CORE_KPI_FIELDS,
    *OVERLAY_FIELDS,
]

COVERAGE_OUTPUT_FIELDS = [
    "holding_name",
    "ticker",
    "isin",
    "asset_type",
    "company_type_profile",
    "match_status",
    "match_method",
    "matched_company_name",
    "matched_ticker",
    "matched_isin",
    "match_conflict_flag",
    "data_quality_flag",
    "required_kpis_expected",
    "required_kpis_present",
    "missing_required_kpis",
    "not_applicable_kpis",
    "optional_missing_kpis",
    "needs_research_flag",
    "notes",
]

SCORE_FIELDS = [
    "quality_score",
    "dividend_score",
    "balance_sheet_score",
    "growth_quality_score",
    "capital_allocation_score",
    "business_score",
    "valuation_score",
    "buy_score",
]

PERSONAL_ENRICHED_OUTPUT_FIELDS = [
    "holding_name",
    "holding_ticker",
    "holding_isin",
    "match_status",
    "match_method",
    "matched_company_name",
    "matched_ticker",
    "matched_isin",
    "match_conflict_flag",
    *IDENTITY_METADATA_FIELDS,
    *SCORING_COMPATIBILITY_FIELDS,
    *CORE_KPI_FIELDS,
    *SCORE_FIELDS,
    "fundamentals_input_format",
    "needs_research_flag",
    "missing_required_kpis",
    "not_applicable_kpis",
    "optional_missing_kpis",
    "coverage_notes",
]


def normalize_company_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def has_value(row: dict[str, Any], field: str) -> bool:
    return str(row.get(field, "")).strip() != ""


def parse_float_strict(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    cleaned = normalize_number_text(text.replace("%", ""))
    return float(cleaned)


def validate_date_text(value: Any, field: str, source_name: str, row_number: int) -> None:
    text = str(value or "").strip()
    if not text:
        return
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{source_name} row {row_number} has invalid {field}: {text!r}; expected YYYY-MM-DD") from exc


def validate_personal_fundamentals_master(rows: list[dict[str, str]], source_name: str = "personal fundamentals master") -> list[str]:
    require_columns(rows, PERSONAL_MASTER_FIELDS, source_name)
    warnings: list[str] = []
    date_fields = ["source_as_of_date", "report_date", "filing_date", "market_price_date"]
    numeric_fields = [*CORE_KPI_FIELDS, "current_price_eur", "mandate_fit_score"]

    for index, row in enumerate(rows, start=2):
        ticker = canonicalize_ticker(row.get("ticker", ""))
        isin = str(row.get("isin", "")).strip().upper()
        company_name = str(row.get("company_name", "")).strip()
        if not ticker and not isin and not company_name:
            raise ValueError(f"{source_name} row {index} has no identifier; ticker, isin or company_name is required")
        if isin and not ISIN_PATTERN.match(isin):
            raise ValueError(f"{source_name} row {index} has invalid isin: {isin!r}")
        profile = safe_upper(row.get("company_type_profile"))
        if profile not in VALID_COMPANY_TYPE_PROFILES:
            raise ValueError(
                f"{source_name} row {index} has invalid company_type_profile: {row.get('company_type_profile')!r}; "
                f"allowed: {', '.join(sorted(VALID_COMPANY_TYPE_PROFILES))}"
            )
        quality = safe_upper(row.get("data_quality_flag"))
        if quality not in VALID_DATA_QUALITY_FLAGS:
            raise ValueError(
                f"{source_name} row {index} has invalid data_quality_flag: {row.get('data_quality_flag')!r}; "
                f"allowed: {', '.join(sorted(VALID_DATA_QUALITY_FLAGS))}"
            )
        for field in date_fields:
            validate_date_text(row.get(field, ""), field, source_name, index)
        fiscal_year = str(row.get("fiscal_year", "")).strip()
        if fiscal_year:
            try:
                int(fiscal_year)
            except ValueError as exc:
                raise ValueError(f"{source_name} row {index} has invalid fiscal_year: {fiscal_year!r}") from exc
        for field in numeric_fields:
            try:
                parse_float_strict(row.get(field, ""))
            except ValueError as exc:
                raise ValueError(f"{source_name} row {index} has non-numeric {field}: {row.get(field)!r}") from exc

    warnings.extend(find_duplicate_identifier_warnings(rows, source_name))
    return warnings


def find_duplicate_identifier_warnings(rows: list[dict[str, str]], source_name: str) -> list[str]:
    warnings: list[str] = []
    specs = [
        ("isin", lambda row: str(row.get("isin", "")).strip().upper()),
        ("ticker", lambda row: canonicalize_ticker(row.get("ticker", ""))),
        ("company_name", lambda row: normalize_company_name(row.get("company_name", ""))),
    ]
    for label, normalizer in specs:
        seen: dict[str, int] = {}
        duplicates: set[str] = set()
        for index, row in enumerate(rows, start=2):
            key = normalizer(row)
            if not key:
                continue
            if key in seen:
                duplicates.add(key)
            else:
                seen[key] = index
        if duplicates:
            warnings.append(f"{source_name} duplicate {label} value(s) require match REVIEW: {', '.join(sorted(duplicates))}")
    return warnings


def build_fundamentals_match_index(rows: list[dict[str, str]]) -> dict[str, dict[str, list[dict[str, str]]]]:
    index = {"isin": {}, "ticker": {}, "company_name": {}}
    for row in rows:
        isin = str(row.get("isin", "")).strip().upper()
        ticker = canonicalize_ticker(row.get("ticker", ""))
        name = normalize_company_name(row.get("company_name", ""))
        if isin:
            index["isin"].setdefault(isin, []).append(row)
        if ticker:
            index["ticker"].setdefault(ticker, []).append(row)
        if name:
            index["company_name"].setdefault(name, []).append(row)
    return index


def candidate_label(row: dict[str, str]) -> str:
    return f"{canonicalize_ticker(row.get('ticker', ''))}|{str(row.get('isin', '')).strip().upper()}|{row.get('company_name', '')}"


def unique_candidate_or_conflict(candidates: list[dict[str, str]]) -> tuple[dict[str, str] | None, bool]:
    if not candidates:
        return None, False
    if len(candidates) == 1:
        return candidates[0], False
    return None, True


def match_holding_to_fundamentals(
    holding: dict[str, Any],
    match_index: dict[str, dict[str, list[dict[str, str]]]],
) -> dict[str, Any]:
    ticker = canonicalize_ticker(holding.get("ticker", ""))
    isin = str(holding.get("isin", "")).strip().upper()
    name = normalize_company_name(holding.get("company_name") or holding.get("raw_name", ""))

    candidates_by_method = {
        "ISIN": match_index["isin"].get(isin, []) if isin else [],
        "TICKER": match_index["ticker"].get(ticker, []) if ticker else [],
        "COMPANY_NAME": match_index["company_name"].get(name, []) if name else [],
    }
    unique_by_method: dict[str, dict[str, str]] = {}
    conflict_methods: list[str] = []
    for method, candidates in candidates_by_method.items():
        candidate, conflict = unique_candidate_or_conflict(candidates)
        if conflict:
            conflict_methods.append(method)
        if candidate is not None:
            unique_by_method[method] = candidate

    if conflict_methods:
        return {
            "match_status": "REVIEW",
            "match_method": "NO_MATCH",
            "matched_row": None,
            "match_conflict_flag": True,
            "notes": f"ambiguous {', '.join(conflict_methods)} match in personal fundamentals master",
        }

    selected_method = ""
    selected_row: dict[str, str] | None = None
    for method in ["ISIN", "TICKER", "COMPANY_NAME"]:
        if method in unique_by_method:
            selected_method = method
            selected_row = unique_by_method[method]
            break

    if selected_row is None:
        return {
            "match_status": "NO_MATCH",
            "match_method": "NO_MATCH",
            "matched_row": None,
            "match_conflict_flag": False,
            "notes": "no exact ISIN, ticker or normalized company_name match",
        }

    selected_id = id(selected_row)
    conflicting_unique = [
        f"{method}={candidate_label(row)}"
        for method, row in unique_by_method.items()
        if id(row) != selected_id
    ]
    if conflicting_unique:
        return {
            "match_status": "REVIEW",
            "match_method": "NO_MATCH",
            "matched_row": None,
            "match_conflict_flag": True,
            "notes": "conflicting exact matches across identifiers: " + "; ".join(conflicting_unique),
        }

    return {
        "match_status": "MATCHED",
        "match_method": selected_method,
        "matched_row": selected_row,
        "match_conflict_flag": False,
        "notes": "",
    }


def load_metric_definitions(path: str = DEFAULT_METRIC_DEFINITIONS_PATH) -> dict[str, Any]:
    config = load_yaml_config(path)
    definitions = dict(config.get("kpis", {}))
    validate_metric_definitions(definitions)
    return definitions


def validate_metric_definitions(metric_definitions: dict[str, Any]) -> None:
    missing = [kpi for kpi in CORE_KPI_FIELDS if kpi not in metric_definitions]
    if missing:
        raise ValueError(f"fundamentals metric definitions missing KPI definition(s): {', '.join(sorted(missing))}")


def kpi_applicability(kpi_definition: dict[str, Any], profile: str) -> str:
    applicable = set(kpi_definition.get("applicable_profiles", []))
    required = set(kpi_definition.get("required_for_profiles", []))
    if profile in required:
        return "REQUIRED"
    if profile in applicable:
        return "OPTIONAL"
    return "NOT_APPLICABLE"


def compute_kpi_coverage(row: dict[str, str], profile: str, metric_definitions: dict[str, Any]) -> dict[str, list[str]]:
    validate_metric_definitions(metric_definitions)
    required: list[str] = []
    required_present: list[str] = []
    missing_required: list[str] = []
    not_applicable: list[str] = []
    optional_missing: list[str] = []
    for kpi in CORE_KPI_FIELDS:
        definition = metric_definitions[kpi]
        applicability = kpi_applicability(definition, profile)
        if applicability == "NOT_APPLICABLE":
            not_applicable.append(kpi)
            continue
        if applicability == "REQUIRED":
            required.append(kpi)
            if has_value(row, kpi):
                required_present.append(kpi)
            else:
                missing_required.append(kpi)
            continue
        if not has_value(row, kpi):
            optional_missing.append(kpi)
    return {
        "required": required,
        "required_present": required_present,
        "missing_required": missing_required,
        "not_applicable": not_applicable,
        "optional_missing": optional_missing,
    }


def join_list(values: list[str]) -> str:
    return "; ".join(sorted(values))


def build_fundamentals_coverage(
    positions_rows: list[dict[str, str]],
    fundamentals_rows: list[dict[str, str]],
    metric_definitions: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    definitions = metric_definitions or load_metric_definitions()
    match_index = build_fundamentals_match_index(fundamentals_rows)
    rows: list[dict[str, Any]] = []
    for holding in aggregate_positions_by_ticker(positions_rows):
        if safe_upper(holding.get("asset_type")) == "CASH":
            continue
        match = match_holding_to_fundamentals(holding, match_index)
        matched_row = match.get("matched_row") or {}
        profile = safe_upper(matched_row.get("company_type_profile")) or "OTHER"
        quality = safe_upper(matched_row.get("data_quality_flag")) or "MISSING_DATA"
        kpi_coverage = compute_kpi_coverage(matched_row, profile, definitions) if matched_row else {
            "required": [],
            "required_present": [],
            "missing_required": [],
            "not_applicable": [],
            "optional_missing": [],
        }

        if match["match_status"] == "NO_MATCH":
            match_status = "NO_MATCH"
        elif match["match_status"] == "REVIEW":
            match_status = "REVIEW"
        elif quality == "OK" and not kpi_coverage["missing_required"]:
            match_status = "COVERED"
        else:
            match_status = "PARTIAL"

        notes = [str(match.get("notes", "")).strip(), str(matched_row.get("notes", "")).strip()]
        if kpi_coverage["missing_required"]:
            notes.append("MISSING_REQUIRED_KPI")
        if profile == "OTHER":
            notes.append("company_type_profile=OTHER; STANDARD KPI applicability is not assumed")
        needs_research = match_status != "COVERED" or bool(kpi_coverage["missing_required"]) or quality != "OK"

        rows.append(
            {
                "holding_name": holding.get("company_name") or holding.get("raw_name", ""),
                "ticker": canonicalize_ticker(holding.get("ticker", "")),
                "isin": str(holding.get("isin", "")).strip().upper(),
                "asset_type": holding.get("asset_type", ""),
                "company_type_profile": profile,
                "match_status": match_status,
                "match_method": match.get("match_method", "NO_MATCH"),
                "matched_company_name": matched_row.get("company_name", ""),
                "matched_ticker": canonicalize_ticker(matched_row.get("ticker", "")),
                "matched_isin": str(matched_row.get("isin", "")).strip().upper(),
                "match_conflict_flag": bool(match.get("match_conflict_flag")),
                "data_quality_flag": quality,
                "required_kpis_expected": len(kpi_coverage["required"]),
                "required_kpis_present": len(kpi_coverage["required_present"]),
                "missing_required_kpis": join_list(kpi_coverage["missing_required"]),
                "not_applicable_kpis": join_list(kpi_coverage["not_applicable"]),
                "optional_missing_kpis": join_list(kpi_coverage["optional_missing"]),
                "needs_research_flag": needs_research,
                "notes": "; ".join(note for note in notes if note),
            }
        )
    return rows


def build_master_seed_rows_from_positions(positions_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for holding in aggregate_positions_by_ticker(positions_rows):
        if safe_upper(holding.get("asset_type")) == "CASH":
            continue
        source_name = str(holding.get("source_name") or "positions_snapshot").strip()
        as_of = str(holding.get("portfolio_date") or "").strip()
        row = {field: "" for field in PERSONAL_MASTER_FIELDS}
        row.update(
            {
                "ticker": canonicalize_ticker(holding.get("ticker", "")),
                "isin": str(holding.get("isin", "")).strip().upper(),
                "company_name": holding.get("company_name") or holding.get("raw_name", ""),
                "currency": holding.get("currency", ""),
                "sector": holding.get("sector", "Unknown"),
                "country": holding.get("country", "Unknown"),
                "asset_type": holding.get("asset_type", ""),
                "company_type_profile": "OTHER",
                "source_name": f"{source_name}_identity_seed",
                "source_as_of_date": as_of,
                "market_price_date": as_of,
                "calculation_version": "phase2a1_personal_master_v1",
                "data_quality_flag": "MISSING_DATA",
                "notes": "Identity seed from personal_positions_snapshot; core fundamentals require manual research; ticker kept from broker snapshot.",
                "sleeve": holding.get("sleeve", ""),
                "current_price_eur": holding.get("price_eur") or holding.get("current_price") or "",
            }
        )
        rows.append(row)
    return rows


def build_source_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        for key in [
            "isin:" + str(row.get("isin", "")).strip().upper(),
            "ticker:" + canonicalize_ticker(row.get("ticker", "")),
            "name:" + normalize_company_name(row.get("company_name", "")),
        ]:
            if not key.endswith(":"):
                lookup.setdefault(key, row)
    return lookup


def build_score_lookup(score_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in score_rows:
        for key in [
            "isin:" + str(row.get("isin", "")).strip().upper(),
            "ticker:" + canonicalize_ticker(row.get("ticker", "")),
        ]:
            if not key.endswith(":"):
                lookup.setdefault(key, row)
    return lookup


def lookup_by_coverage(row: dict[str, Any], lookup: dict[str, dict[str, str]]) -> dict[str, str]:
    for key in [
        "isin:" + str(row.get("matched_isin", "")).strip().upper(),
        "ticker:" + canonicalize_ticker(row.get("matched_ticker", "")),
        "name:" + normalize_company_name(row.get("matched_company_name", "")),
        "isin:" + str(row.get("isin", "")).strip().upper(),
        "ticker:" + canonicalize_ticker(row.get("ticker", "")),
    ]:
        if not key.endswith(":") and key in lookup:
            return lookup[key]
    return {}


def build_personal_enriched_rows(
    coverage_rows: list[dict[str, Any]],
    fundamentals_rows: list[dict[str, str]],
    score_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    source_lookup = build_source_lookup(fundamentals_rows)
    score_lookup = build_score_lookup(score_rows or [])
    enriched_rows: list[dict[str, Any]] = []
    for coverage in coverage_rows:
        if coverage["match_status"] in {"NO_MATCH", "REVIEW"}:
            continue
        source = lookup_by_coverage(coverage, source_lookup)
        score = lookup_by_coverage(coverage, score_lookup)
        row: dict[str, Any] = {
            "holding_name": coverage.get("holding_name", ""),
            "holding_ticker": coverage.get("ticker", ""),
            "holding_isin": coverage.get("isin", ""),
            "match_status": coverage.get("match_status", ""),
            "match_method": coverage.get("match_method", ""),
            "matched_company_name": coverage.get("matched_company_name", ""),
            "matched_ticker": coverage.get("matched_ticker", ""),
            "matched_isin": coverage.get("matched_isin", ""),
            "match_conflict_flag": coverage.get("match_conflict_flag", ""),
            "needs_research_flag": coverage.get("needs_research_flag", ""),
            "missing_required_kpis": coverage.get("missing_required_kpis", ""),
            "not_applicable_kpis": coverage.get("not_applicable_kpis", ""),
            "optional_missing_kpis": coverage.get("optional_missing_kpis", ""),
            "fundamentals_input_format": score.get("fundamentals_input_format", "personal"),
            "coverage_notes": coverage.get("notes", ""),
        }
        for field in [*IDENTITY_METADATA_FIELDS, *SCORING_COMPATIBILITY_FIELDS, *CORE_KPI_FIELDS]:
            row[field] = source.get(field, "")
        for field in SCORE_FIELDS:
            row[field] = score.get(field, "")
        row["source_name"] = source.get("source_name", row.get("source_name", ""))
        row["source_as_of_date"] = source.get("source_as_of_date", row.get("source_as_of_date", ""))
        row["data_quality_flag"] = coverage.get("data_quality_flag", source.get("data_quality_flag", ""))
        row["company_type_profile"] = coverage.get("company_type_profile", source.get("company_type_profile", ""))
        enriched_rows.append(row)
    return enriched_rows


def coverage_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"COVERED": 0, "PARTIAL": 0, "NO_MATCH": 0, "REVIEW": 0, "MISSING_REQUIRED_KPIS": 0}
    for row in rows:
        status = str(row.get("match_status", "NO_MATCH"))
        counts[status] = counts.get(status, 0) + 1
        if str(row.get("missing_required_kpis", "")).strip():
            counts["MISSING_REQUIRED_KPIS"] += 1
    return counts


def render_coverage_item(row: dict[str, Any]) -> str:
    ticker = row.get("matched_ticker") or row.get("ticker") or row.get("isin")
    missing = row.get("missing_required_kpis") or "none"
    return (
        f"- `{ticker}` {row.get('holding_name', '')}: status={row.get('match_status')} "
        f"method={row.get('match_method')} quality={row.get('data_quality_flag')} missing_required={missing}"
    )


def write_coverage_report(
    coverage_rows: list[dict[str, Any]],
    output_path: str,
    fundamentals_input: str,
    warnings: list[str] | None = None,
) -> Path:
    counts = coverage_counts(coverage_rows)
    groups = {
        "COVERED": [row for row in coverage_rows if row["match_status"] == "COVERED"],
        "PARTIAL": [row for row in coverage_rows if row["match_status"] == "PARTIAL"],
        "NO_MATCH": [row for row in coverage_rows if row["match_status"] == "NO_MATCH"],
        "REVIEW": [row for row in coverage_rows if row["match_status"] == "REVIEW"],
        "MISSING_REQUIRED_KPIS": [row for row in coverage_rows if str(row.get("missing_required_kpis", "")).strip()],
    }
    research_gaps = [row for row in coverage_rows if str(row.get("needs_research_flag", "")).lower() == "true"]

    lines = [
        "# Personal Fundamentals Coverage",
        "",
        "## Input",
        "",
        f"- Fundamentals input: `{fundamentals_input}`",
        "- Fehlende Fundamentaldaten wurden nicht aufgefuellt und nicht geraten.",
        "- Matching-Prioritaet: ISIN exact > ticker exact > normalisierter company_name exact > NO_MATCH.",
        "",
        "## Summary Counts",
        "",
        f"- COVERED: {counts.get('COVERED', 0)}",
        f"- PARTIAL: {counts.get('PARTIAL', 0)}",
        f"- REVIEW: {counts.get('REVIEW', 0)}",
        f"- NO_MATCH: {counts.get('NO_MATCH', 0)}",
        f"- MISSING_REQUIRED_KPIS: {counts.get('MISSING_REQUIRED_KPIS', 0)}",
    ]
    if warnings:
        lines.extend(["", "## Validation Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)

    for title in ["COVERED", "PARTIAL", "REVIEW", "NO_MATCH", "MISSING_REQUIRED_KPIS"]:
        lines.extend(["", f"## {title}", ""])
        if groups[title]:
            lines.extend(render_coverage_item(row) for row in groups[title])
        else:
            lines.append("- Keine.")

    lines.extend(["", "## Research-Luecken", ""])
    if research_gaps:
        for row in research_gaps:
            lines.append(
                f"- `{row.get('ticker') or row.get('isin')}` {row.get('holding_name', '')}: "
                f"{row.get('notes', '') or 'Research erforderlich'}"
            )
    else:
        lines.append("- Keine offenen Research-Luecken.")

    path = ensure_parent_dir(output_path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and report personal fundamentals master coverage.")
    parser.add_argument("--positions", required=True, help="Personal positions snapshot CSV.")
    parser.add_argument("--fundamentals", help="Personal fundamentals master CSV.")
    parser.add_argument("--scores", help="Optional personal company scores CSV for enriched output.")
    parser.add_argument("--coverage-output", default=DEFAULT_COVERAGE_OUTPUT, help="Coverage CSV output.")
    parser.add_argument("--enriched-output", default=DEFAULT_ENRICHED_OUTPUT, help="Matched fundamentals enriched CSV output.")
    parser.add_argument("--report-output", help="Coverage Markdown report output.")
    parser.add_argument("--metric-definitions", default=DEFAULT_METRIC_DEFINITIONS_PATH, help="KPI definition config.")
    parser.add_argument("--init-master-output", help="Create an identity-only personal fundamentals master from positions and exit.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    positions_rows = read_csv_rows(args.positions)
    require_columns(
        positions_rows,
        ["ticker", "isin", "company_name", "asset_type", "sleeve"],
        f"positions CSV ({args.positions})",
    )

    if args.init_master_output:
        seed_rows = build_master_seed_rows_from_positions(positions_rows)
        write_csv_rows(args.init_master_output, PERSONAL_MASTER_FIELDS, seed_rows)
        return

    fundamentals_path = args.fundamentals or DEFAULT_PERSONAL_MASTER_PATH
    fundamentals_rows = read_csv_rows(fundamentals_path)
    warnings = validate_personal_fundamentals_master(fundamentals_rows, f"personal fundamentals master ({fundamentals_path})")
    definitions = load_metric_definitions(args.metric_definitions)
    coverage_rows = build_fundamentals_coverage(positions_rows, fundamentals_rows, definitions)
    write_csv_rows(args.coverage_output, COVERAGE_OUTPUT_FIELDS, coverage_rows)

    score_rows = read_csv_rows(args.scores) if args.scores else []
    enriched_rows = build_personal_enriched_rows(coverage_rows, fundamentals_rows, score_rows)
    write_csv_rows(args.enriched_output, PERSONAL_ENRICHED_OUTPUT_FIELDS, enriched_rows)

    if args.report_output:
        write_coverage_report(coverage_rows, args.report_output, fundamentals_path, warnings)


if __name__ == "__main__":
    main()
