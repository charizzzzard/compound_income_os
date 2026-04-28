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
    to_bool,
    to_float,
    write_csv_rows,
)
from src.portfolio_rules import aggregate_positions_by_ticker

DEFAULT_METRIC_DEFINITIONS_PATH = "configs/fundamentals_metric_definitions.yaml"
DEFAULT_PERSONAL_MASTER_PATH = "data/raw/personal_fundamentals_master.csv"
DEFAULT_COVERAGE_OUTPUT = "data/processed/personal_fundamentals_coverage.csv"
DEFAULT_ENRICHED_OUTPUT = "data/processed/personal_fundamentals_enriched.csv"
DEFAULT_RESEARCH_PRIORITY_OUTPUT = "data/processed/personal_research_priority.csv"

VALID_COMPANY_TYPE_PROFILES = {"STANDARD", "FINANCIAL", "REIT", "OTHER"}
VALID_DATA_QUALITY_FLAGS = {"OK", "REVIEW", "MISSING_DATA"}
VALID_KPI_TIERS = {
    "CORE_QUALITY_REQUIRED",
    "DECISION_REQUIRED",
    "VALUATION_REQUIRED",
    "DIVIDEND_FCF_REQUIRED",
    "ADVANCED_OPTIONAL",
    "PROFILE_SPECIFIC",
}
DEFAULT_STANDARD_KPI_TIERS = {
    "CORE_QUALITY_REQUIRED": [
        "revenue_cagr_5y",
        "eps_cagr_5y",
        "gross_margin",
        "operating_margin",
        "share_count_cagr_5y",
    ],
    "VALUATION_REQUIRED": [
        "normalized_fcf_yield_pct",
        "target_fcf_yield_pct",
    ],
    "DIVIDEND_FCF_REQUIRED": [
        "fcf_margin",
        "payout_ratio_fcf",
        "fcf_per_share_cagr_5y",
    ],
    "ADVANCED_OPTIONAL": [
        "buyback_yield",
        "interest_coverage",
        "net_debt_to_ebitda",
        "roce",
        "roic",
    ],
}
MIN_CORE_QUALITY_PRESENT_FOR_SCORING = 3
PROFILE_REASON_MARKERS = (
    "company_type_profile_reason=",
    "profile_reason=",
    "other_profile_reason=",
)
HIGH_RESEARCH_WEIGHT_TOTAL_ASSETS_PCT = 5.0
MEDIUM_RESEARCH_WEIGHT_TOTAL_ASSETS_PCT = 1.0
HIGH_RESEARCH_MISSING_REQUIRED_KPI_COUNT = 3
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
    "derived_data_quality_flag",
    "derived_data_quality_reason",
    "core_kpis_present_count",
    "required_kpis_expected",
    "required_kpis_present",
    "required_kpis_missing_count",
    "missing_required_kpis",
    "missing_core_quality_kpis",
    "missing_valuation_kpis",
    "missing_dividend_fcf_kpis",
    "missing_advanced_optional_kpis",
    "core_quality_data_status",
    "valuation_data_status",
    "dividend_fcf_data_status",
    "advanced_data_status",
    "not_applicable_kpis",
    "optional_missing_kpis",
    "profile_classification_warning_flag",
    "profile_classification_warning_reason",
    "needs_research_flag",
    "notes",
]

RESEARCH_PRIORITY_OUTPUT_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "asset_type",
    "company_type_profile",
    "profile_classification_warning_flag",
    "profile_classification_warning_reason",
    "market_value_eur",
    "weight_total_assets_pct",
    "weight_portfolio_pct",
    "missing_required_kpi_count",
    "missing_required_kpis",
    "needs_research_flag",
    "coverage_status",
    "research_priority",
    "research_priority_reason",
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
    "missing_core_quality_kpis",
    "missing_valuation_kpis",
    "missing_dividend_fcf_kpis",
    "missing_advanced_optional_kpis",
    "core_quality_data_status",
    "valuation_data_status",
    "dividend_fcf_data_status",
    "advanced_data_status",
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
    invalid_tiers = [
        f"{kpi}={definition.get('kpi_tier')}"
        for kpi, definition in metric_definitions.items()
        if str(definition.get("kpi_tier", "") or "").strip()
        and safe_upper(definition.get("kpi_tier")) not in VALID_KPI_TIERS
    ]
    if invalid_tiers:
        raise ValueError(f"fundamentals metric definitions contain invalid KPI tier(s): {', '.join(sorted(invalid_tiers))}")


def default_kpi_tier(kpi: str) -> str:
    for tier, kpis in DEFAULT_STANDARD_KPI_TIERS.items():
        if kpi in kpis:
            return tier
    return "PROFILE_SPECIFIC"


def kpi_tier(kpi: str, metric_definitions: dict[str, Any]) -> str:
    configured = safe_upper(metric_definitions.get(kpi, {}).get("kpi_tier"))
    return configured if configured in VALID_KPI_TIERS else default_kpi_tier(kpi)


def kpis_for_tier(tier: str, metric_definitions: dict[str, Any]) -> list[str]:
    tier = safe_upper(tier)
    return sorted(kpi for kpi in CORE_KPI_FIELDS if kpi_tier(kpi, metric_definitions) == tier)


def tier_status(expected: list[str], present: list[str], *, min_present_for_partial: int = 1) -> str:
    if not expected:
        return "NOT_APPLICABLE"
    if len(present) == len(expected):
        return "OK"
    if len(present) >= min_present_for_partial:
        return "PARTIAL"
    return "MISSING"


def compute_kpi_tier_coverage(row: dict[str, Any], profile: str, metric_definitions: dict[str, Any]) -> dict[str, Any]:
    validate_metric_definitions(metric_definitions)
    normalized_profile = safe_upper(profile) or "OTHER"
    result: dict[str, Any] = {
        "missing_core_quality_kpis": [],
        "missing_valuation_kpis": [],
        "missing_dividend_fcf_kpis": [],
        "missing_advanced_optional_kpis": [],
        "core_quality_data_status": "NOT_APPLICABLE",
        "valuation_data_status": "NOT_APPLICABLE",
        "dividend_fcf_data_status": "NOT_APPLICABLE",
        "advanced_data_status": "NOT_APPLICABLE",
        "core_quality_present_count": 0,
        "core_quality_expected_count": 0,
    }
    if normalized_profile != "STANDARD":
        return result

    tier_specs = [
        ("CORE_QUALITY_REQUIRED", "missing_core_quality_kpis", "core_quality_data_status"),
        ("VALUATION_REQUIRED", "missing_valuation_kpis", "valuation_data_status"),
        ("DIVIDEND_FCF_REQUIRED", "missing_dividend_fcf_kpis", "dividend_fcf_data_status"),
        ("ADVANCED_OPTIONAL", "missing_advanced_optional_kpis", "advanced_data_status"),
    ]
    for tier_name, missing_field, status_field in tier_specs:
        expected = kpis_for_tier(tier_name, metric_definitions)
        present = [kpi for kpi in expected if has_value(row, kpi)]
        missing = [kpi for kpi in expected if kpi not in present]
        result[missing_field] = missing
        result[status_field] = tier_status(
            expected,
            present,
            min_present_for_partial=MIN_CORE_QUALITY_PRESENT_FOR_SCORING if tier_name == "CORE_QUALITY_REQUIRED" else 1,
        )
        if tier_name == "CORE_QUALITY_REQUIRED":
            result["core_quality_present_count"] = len(present)
            result["core_quality_expected_count"] = len(expected)
    return result


def tier_list_text(tier_coverage: dict[str, Any], field: str) -> str:
    return join_list([str(item) for item in tier_coverage.get(field, [])])


def tiered_score_data_quality(existing_flag: str, profile: str, tier_coverage: dict[str, Any]) -> str:
    existing = safe_upper(existing_flag) or "OK"
    if safe_upper(profile) != "STANDARD":
        return existing
    core_present = int(tier_coverage.get("core_quality_present_count") or 0)
    core_expected = int(tier_coverage.get("core_quality_expected_count") or 0)
    if core_expected and core_present < MIN_CORE_QUALITY_PRESENT_FOR_SCORING:
        return "MISSING_DATA"
    if core_expected and core_present >= MIN_CORE_QUALITY_PRESENT_FOR_SCORING:
        if (
            tier_coverage.get("core_quality_data_status") == "OK"
            and tier_coverage.get("valuation_data_status") == "OK"
            and tier_coverage.get("dividend_fcf_data_status") == "OK"
            and existing == "OK"
        ):
            return "OK"
        return "REVIEW"
    return existing


def kpi_applicability(kpi_definition: dict[str, Any], profile: str) -> str:
    applicable = set(kpi_definition.get("applicable_profiles", []))
    required = set(kpi_definition.get("required_for_profiles", []))
    if safe_upper(kpi_definition.get("kpi_tier")) == "ADVANCED_OPTIONAL" and profile in applicable:
        return "OPTIONAL"
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


def count_present_core_kpis(row: dict[str, Any]) -> int:
    return sum(1 for field in CORE_KPI_FIELDS if has_value(row, field))


def derive_fundamentals_data_quality(
    row: dict[str, Any],
    profile: str,
    metric_definitions: dict[str, Any],
) -> tuple[str, str]:
    coverage = compute_kpi_coverage(row, profile, metric_definitions)
    tier_coverage = compute_kpi_tier_coverage(row, profile, metric_definitions)
    asset_type = safe_upper(row.get("asset_type"))
    core_present_count = count_present_core_kpis(row)
    required_missing_count = len(coverage["missing_required"])
    profile_has_reason = has_company_type_profile_reason(row)

    if asset_type == "STOCK" and profile == "OTHER" and not profile_has_reason:
        if core_present_count > 0:
            return "REVIEW", "company_type_profile=OTHER without explicit reason; SEC or evidence values exist but profile review is still required"
        return "MISSING_DATA", "company_type_profile=OTHER without explicit reason and no applicable KPI coverage is available"

    if asset_type == "STOCK" and profile == "OTHER" and profile_has_reason:
        return "OK", "company_type_profile=OTHER is explicitly justified; no unsupported STANDARD KPI assumptions are applied"

    if profile in {"STANDARD", "FINANCIAL", "REIT"} and not coverage["required"]:
        return "REVIEW", f"profile={profile} has no required KPI definitions configured; manual review required"

    if profile == "STANDARD":
        core_present = int(tier_coverage.get("core_quality_present_count") or 0)
        core_expected = int(tier_coverage.get("core_quality_expected_count") or 0)
        if core_expected and core_present < MIN_CORE_QUALITY_PRESENT_FOR_SCORING:
            return (
                "MISSING_DATA",
                f"insufficient CORE_QUALITY_REQUIRED KPI coverage for STANDARD: present={core_present}, expected={core_expected}",
            )
        if required_missing_count > 0:
            return (
                "REVIEW",
                "tiered STANDARD KPI coverage is sufficient for core scoring but incomplete for full decision quality: "
                f"core_quality={tier_coverage['core_quality_data_status']}, "
                f"valuation={tier_coverage['valuation_data_status']}, "
                f"dividend_fcf={tier_coverage['dividend_fcf_data_status']}, "
                f"advanced={tier_coverage['advanced_data_status']}",
            )

    if required_missing_count == 0 and coverage["required"]:
        return "OK", f"all {len(coverage['required'])} required KPIs are present for profile {profile}"

    if core_present_count > 0 or coverage["required_present"]:
        return "REVIEW", (
            f"partial KPI coverage under profile {profile}: required_present={len(coverage['required_present'])}, "
            f"required_missing={required_missing_count}, core_present={core_present_count}"
        )

    return "MISSING_DATA", f"no relevant KPI coverage is available for profile {profile}"


def join_list(values: list[str]) -> str:
    return "; ".join(sorted(values))


def split_kpi_list(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(";") if item.strip()]


def has_company_type_profile_reason(row: dict[str, Any]) -> bool:
    explicit_reason = str(row.get("company_type_profile_reason", "")).strip()
    if explicit_reason:
        return True
    notes = str(row.get("notes", "")).strip().lower()
    return any(marker in notes for marker in PROFILE_REASON_MARKERS)


def profile_classification_warning(
    holding: dict[str, Any],
    matched_row: dict[str, Any],
    profile: str,
) -> tuple[bool, str]:
    if not matched_row:
        return False, ""
    asset_type = safe_upper(matched_row.get("asset_type") or holding.get("asset_type"))
    if asset_type != "STOCK" or profile != "OTHER":
        return False, ""
    if has_company_type_profile_reason(matched_row):
        return False, ""
    return (
        True,
        "asset_type=STOCK mit company_type_profile=OTHER ohne explizite company_type_profile_reason in notes oder optionalem Feld",
    )


def validate_research_priority_positions(rows: list[dict[str, Any]], source_name: str) -> None:
    require_columns(
        rows,
        ["ticker", "isin", "company_name", "asset_type", "market_value_eur", "weight_total_assets_pct"],
        source_name,
    )
    for index, row in enumerate(rows, start=2):
        for field in ["market_value_eur", "weight_total_assets_pct"]:
            try:
                value = parse_float_strict(row.get(field, ""))
            except ValueError as exc:
                raise ValueError(f"{source_name} row {index} has non-numeric {field}: {row.get(field)!r}") from exc
            if value is None:
                raise ValueError(f"{source_name} row {index} has blank required field: {field}")


def build_position_relevance_lookup(positions_rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    validate_research_priority_positions(positions_rows, "positions CSV for research priority")
    lookup: dict[str, dict[str, Any]] = {}
    for row in aggregate_positions_by_ticker(positions_rows):
        for key in [
            "isin:" + str(row.get("isin", "")).strip().upper(),
            "ticker:" + canonicalize_ticker(row.get("ticker", "")),
        ]:
            if not key.endswith(":"):
                lookup.setdefault(key, row)
    return lookup


def lookup_position_for_coverage(row: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for key in [
        "isin:" + str(row.get("isin", "")).strip().upper(),
        "ticker:" + canonicalize_ticker(row.get("ticker", "")),
    ]:
        if not key.endswith(":") and key in lookup:
            return lookup[key]
    return {}


def compute_research_priority(row: dict[str, Any], weight_total_assets_pct: float, missing_count: int) -> tuple[str, str]:
    profile_warning = to_bool(row.get("profile_classification_warning_flag"))
    needs_research = to_bool(row.get("needs_research_flag"))
    match_status = safe_upper(row.get("match_status"))

    if profile_warning:
        return "HIGH", "Unbegruendetes company_type_profile=OTHER fuer asset_type=STOCK."
    if needs_research and weight_total_assets_pct >= HIGH_RESEARCH_WEIGHT_TOTAL_ASSETS_PCT:
        return "HIGH", f"Hohe Portfoliorelevanz ({weight_total_assets_pct:g}% total assets) mit offenem Research-Signal."
    if missing_count >= HIGH_RESEARCH_MISSING_REQUIRED_KPI_COUNT and weight_total_assets_pct >= MEDIUM_RESEARCH_WEIGHT_TOTAL_ASSETS_PCT:
        return "HIGH", f"{missing_count} Pflicht-KPI-Luecken bei relevanter Portfolio-Groesse."
    if needs_research and weight_total_assets_pct >= MEDIUM_RESEARCH_WEIGHT_TOTAL_ASSETS_PCT:
        return "MEDIUM", f"Mittlere Portfoliorelevanz ({weight_total_assets_pct:g}% total assets) mit offenem Research-Signal."
    if missing_count > 0:
        return "MEDIUM", f"{missing_count} offene Pflicht-KPI-Luecke(n)."
    if match_status in {"REVIEW", "NO_MATCH", "PARTIAL"}:
        return "MEDIUM", f"Coverage-Status {match_status} erfordert Sichtpruefung."
    if needs_research:
        return "LOW", "Offenes Research-Signal bei geringer Portfoliorelevanz."
    return "LOW", "Keine unmittelbare Fundamentals-Nachpflege aus Coverage ableitbar."


def build_research_priority_rows(
    positions_rows: list[dict[str, str]],
    coverage_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    position_lookup = build_position_relevance_lookup(positions_rows)
    if coverage_rows:
        require_columns(
            coverage_rows,
            [
                "ticker",
                "isin",
                "holding_name",
                "asset_type",
                "company_type_profile",
                "match_status",
                "missing_required_kpis",
                "needs_research_flag",
                "profile_classification_warning_flag",
                "profile_classification_warning_reason",
            ],
            "fundamentals coverage rows for research priority",
        )
    priority_rows: list[dict[str, Any]] = []
    for coverage in coverage_rows:
        position = lookup_position_for_coverage(coverage, position_lookup)
        market_value = to_float(position.get("market_value_eur"))
        weight_total = to_float(position.get("weight_total_assets_pct"))
        missing_kpis = split_kpi_list(coverage.get("missing_required_kpis", ""))
        priority, reason = compute_research_priority(coverage, weight_total, len(missing_kpis))
        priority_rows.append(
            {
                "ticker": canonicalize_ticker(coverage.get("ticker", "")),
                "isin": str(coverage.get("isin", "")).strip().upper(),
                "company_name": coverage.get("holding_name", ""),
                "asset_type": coverage.get("asset_type", ""),
                "company_type_profile": coverage.get("company_type_profile", ""),
                "profile_classification_warning_flag": coverage.get("profile_classification_warning_flag", ""),
                "profile_classification_warning_reason": coverage.get("profile_classification_warning_reason", ""),
                "market_value_eur": position.get("market_value_eur", ""),
                "weight_total_assets_pct": position.get("weight_total_assets_pct", ""),
                "weight_portfolio_pct": position.get("weight_portfolio_pct", ""),
                "missing_required_kpi_count": len(missing_kpis),
                "missing_required_kpis": coverage.get("missing_required_kpis", ""),
                "needs_research_flag": coverage.get("needs_research_flag", ""),
                "coverage_status": coverage.get("match_status", ""),
                "research_priority": priority,
                "research_priority_reason": reason,
                "_sort_market_value_eur": market_value,
            }
        )
    priority_rows.sort(
        key=lambda row: (
            -to_float(row.get("_sort_market_value_eur")),
            -int(row.get("missing_required_kpi_count") or 0),
            str(row.get("ticker", "")),
            str(row.get("isin", "")),
        )
    )
    for row in priority_rows:
        row.pop("_sort_market_value_eur", None)
    return priority_rows


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
        tier_coverage = compute_kpi_tier_coverage(matched_row, profile, definitions) if matched_row else {
            "missing_core_quality_kpis": [],
            "missing_valuation_kpis": [],
            "missing_dividend_fcf_kpis": [],
            "missing_advanced_optional_kpis": [],
            "core_quality_data_status": "NOT_APPLICABLE",
            "valuation_data_status": "NOT_APPLICABLE",
            "dividend_fcf_data_status": "NOT_APPLICABLE",
            "advanced_data_status": "NOT_APPLICABLE",
        }
        derived_quality, derived_reason = (
            derive_fundamentals_data_quality(matched_row, profile, definitions)
            if matched_row
            else ("MISSING_DATA", "no exact fundamentals master match is available")
        )
        core_present_count = count_present_core_kpis(matched_row) if matched_row else 0
        profile_warning_flag, profile_warning_reason = profile_classification_warning(holding, matched_row, profile)

        if match["match_status"] == "NO_MATCH":
            match_status = "NO_MATCH"
        elif match["match_status"] == "REVIEW":
            match_status = "REVIEW"
        elif derived_quality == "OK" and not kpi_coverage["missing_required"] and not profile_warning_flag:
            match_status = "COVERED"
        else:
            match_status = "PARTIAL"

        notes = [str(match.get("notes", "")).strip(), str(matched_row.get("notes", "")).strip()]
        if kpi_coverage["missing_required"]:
            notes.append("MISSING_REQUIRED_KPI")
        if profile == "OTHER":
            notes.append("company_type_profile=OTHER; STANDARD KPI applicability is not assumed")
        if profile_warning_flag:
            notes.append(profile_warning_reason)
        needs_research = (
            match_status != "COVERED"
            or bool(kpi_coverage["missing_required"])
            or derived_quality != "OK"
            or profile_warning_flag
        )

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
                "derived_data_quality_flag": derived_quality,
                "derived_data_quality_reason": derived_reason,
                "core_kpis_present_count": core_present_count,
                "required_kpis_expected": len(kpi_coverage["required"]),
                "required_kpis_present": len(kpi_coverage["required_present"]),
                "required_kpis_missing_count": len(kpi_coverage["missing_required"]),
                "missing_required_kpis": join_list(kpi_coverage["missing_required"]),
                "missing_core_quality_kpis": tier_list_text(tier_coverage, "missing_core_quality_kpis"),
                "missing_valuation_kpis": tier_list_text(tier_coverage, "missing_valuation_kpis"),
                "missing_dividend_fcf_kpis": tier_list_text(tier_coverage, "missing_dividend_fcf_kpis"),
                "missing_advanced_optional_kpis": tier_list_text(tier_coverage, "missing_advanced_optional_kpis"),
                "core_quality_data_status": tier_coverage["core_quality_data_status"],
                "valuation_data_status": tier_coverage["valuation_data_status"],
                "dividend_fcf_data_status": tier_coverage["dividend_fcf_data_status"],
                "advanced_data_status": tier_coverage["advanced_data_status"],
                "not_applicable_kpis": join_list(kpi_coverage["not_applicable"]),
                "optional_missing_kpis": join_list(kpi_coverage["optional_missing"]),
                "profile_classification_warning_flag": profile_warning_flag,
                "profile_classification_warning_reason": profile_warning_reason,
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
            "missing_core_quality_kpis": coverage.get("missing_core_quality_kpis", ""),
            "missing_valuation_kpis": coverage.get("missing_valuation_kpis", ""),
            "missing_dividend_fcf_kpis": coverage.get("missing_dividend_fcf_kpis", ""),
            "missing_advanced_optional_kpis": coverage.get("missing_advanced_optional_kpis", ""),
            "core_quality_data_status": coverage.get("core_quality_data_status", ""),
            "valuation_data_status": coverage.get("valuation_data_status", ""),
            "dividend_fcf_data_status": coverage.get("dividend_fcf_data_status", ""),
            "advanced_data_status": coverage.get("advanced_data_status", ""),
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
    counts = {
        "COVERED": 0,
        "PARTIAL": 0,
        "NO_MATCH": 0,
        "REVIEW": 0,
        "MISSING_REQUIRED_KPIS": 0,
        "PROFILE_CLASSIFICATION_WARNINGS": 0,
    }
    for row in rows:
        status = str(row.get("match_status", "NO_MATCH"))
        counts[status] = counts.get(status, 0) + 1
        if str(row.get("missing_required_kpis", "")).strip():
            counts["MISSING_REQUIRED_KPIS"] += 1
        if to_bool(row.get("profile_classification_warning_flag")):
            counts["PROFILE_CLASSIFICATION_WARNINGS"] += 1
    return counts


def render_coverage_item(row: dict[str, Any]) -> str:
    ticker = row.get("matched_ticker") or row.get("ticker") or row.get("isin")
    missing = row.get("missing_required_kpis") or "none"
    profile_warning = (
        " profile_warning=true"
        if to_bool(row.get("profile_classification_warning_flag"))
        else ""
    )
    return (
        f"- `{ticker}` {row.get('holding_name', '')}: status={row.get('match_status')} "
        f"method={row.get('match_method')} quality={row.get('data_quality_flag')} missing_required={missing}{profile_warning}"
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
        "PROFILE_CLASSIFICATION_WARNINGS": [row for row in coverage_rows if to_bool(row.get("profile_classification_warning_flag"))],
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
        f"- PROFILE_CLASSIFICATION_WARNINGS: {counts.get('PROFILE_CLASSIFICATION_WARNINGS', 0)}",
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

    lines.extend(["", "## Profile-Classification Guardrail", ""])
    if groups["PROFILE_CLASSIFICATION_WARNINGS"]:
        for row in groups["PROFILE_CLASSIFICATION_WARNINGS"]:
            lines.append(
                f"- `{row.get('ticker') or row.get('isin')}` {row.get('holding_name', '')}: "
                f"{row.get('profile_classification_warning_reason', '')}"
            )
    else:
        lines.append("- Keine unbegruendeten OTHER-Profile fuer STOCK-Holdings.")

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
    parser.add_argument("--research-priority-output", help="Optional research priority CSV output.")
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
    if args.research_priority_output:
        research_priority_rows = build_research_priority_rows(positions_rows, coverage_rows)
        write_csv_rows(args.research_priority_output, RESEARCH_PRIORITY_OUTPUT_FIELDS, research_priority_rows)

    score_rows = read_csv_rows(args.scores) if args.scores else []
    enriched_rows = build_personal_enriched_rows(coverage_rows, fundamentals_rows, score_rows)
    write_csv_rows(args.enriched_output, PERSONAL_ENRICHED_OUTPUT_FIELDS, enriched_rows)

    if args.report_output:
        write_coverage_report(coverage_rows, args.report_output, fundamentals_path, warnings)


if __name__ == "__main__":
    main()
