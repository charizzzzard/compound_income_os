from __future__ import annotations

from typing import Any

from src.common import canonicalize_ticker, clamp, load_yaml_config, round2, safe_upper, to_float

DEFAULT_SCHEMA_PATH = "configs/fundamentals_schema.yaml"
DEFAULT_SCORE_RULES_PATH = "configs/fundamentals_score_rules.yaml"

COMPONENT_SCORE_FIELDS = [
    "quality_score",
    "dividend_score",
    "balance_sheet_score",
    "growth_quality_score",
    "capital_allocation_score",
]

RAW_KPI_FIELDS = [
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

RAW_COMPONENT_KPI_FIELDS = [
    # Legacy files already contain valuation inputs. These fields identify
    # raw KPI files that can derive component scores instead of using legacy scores.
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
    "dividend_cagr_5y",
    "dividend_streak_years",
    "payout_ratio_eps",
    "payout_ratio_fcf",
    "share_count_cagr_5y",
    "buyback_yield",
]

PASSTHROUGH_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "currency",
    "sector",
    "country",
    "asset_type",
    "sleeve",
    "current_price_eur",
    "mandate_fit_score",
    "has_hard_risk_flag",
    "thesis_robustness",
    "thesis_summary",
    "main_risks",
    "data_quality_flag",
]

ENRICHED_OUTPUT_FIELDS = [
    *PASSTHROUGH_FIELDS,
    *RAW_KPI_FIELDS,
    *COMPONENT_SCORE_FIELDS,
    "fundamentals_input_format",
    "missing_kpi_count",
    "missing_kpis",
    "quality_score_inputs",
    "dividend_score_inputs",
    "balance_sheet_score_inputs",
    "growth_quality_score_inputs",
    "capital_allocation_score_inputs",
]

SCORE_AUDIT_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "fundamentals_input_format",
    *RAW_KPI_FIELDS,
    *COMPONENT_SCORE_FIELDS,
    "business_score",
    "historical_multiple_score",
    "normalized_fcf_score",
    "dividend_yield_relative_score",
    "valuation_score",
    "expected_return_score",
    "drawdown_opportunity_score",
    "portfolio_fit_score",
    "buy_score",
    "business_score_contribution",
    "valuation_score_contribution",
    "expected_return_score_contribution",
    "drawdown_score_contribution",
    "portfolio_fit_score_contribution",
    "pe_relative_ratio",
    "ev_ebit_relative_ratio",
    "fcf_yield_relative_ratio",
    "normalized_fcf_gap",
    "dividend_yield_relative_ratio",
    "fair_value_estimate",
    "margin_of_safety_pct",
    "data_quality_flag",
    "missing_kpi_count",
    "missing_kpis",
    "quality_score_inputs",
    "dividend_score_inputs",
    "balance_sheet_score_inputs",
    "growth_quality_score_inputs",
    "capital_allocation_score_inputs",
]


def has_value(row: dict[str, Any], field: str) -> bool:
    return str(row.get(field, "")).strip() != ""


def detect_fundamentals_format(rows: list[dict[str, str]], requested_format: str = "auto") -> str:
    requested = requested_format.strip().lower()
    if requested in {"raw", "legacy"}:
        return requested
    if requested != "auto":
        raise ValueError(f"unknown fundamentals format: {requested_format}")
    if any(any(has_value(row, field) for field in RAW_COMPONENT_KPI_FIELDS) for row in rows):
        return "raw"
    if any(any(has_value(row, field) for field in COMPONENT_SCORE_FIELDS) for row in rows):
        return "legacy"
    if any(any(has_value(row, field) for field in RAW_KPI_FIELDS) for row in rows):
        return "raw"
    return "legacy"


def validate_component_score_rules(rules: dict[str, Any], tolerance: float = 0.0001) -> None:
    component_scores = rules.get("component_scores", {})
    kpi_rules = rules.get("kpi_score_rules", {})
    for component_name, weights in component_scores.items():
        weight_sum = sum(to_float(weight) for weight in weights.values())
        if abs(weight_sum - 1.0) > tolerance:
            raise ValueError(
                f"fundamentals score rules component '{component_name}' weights sum to {round2(weight_sum)}; expected 1.0"
            )
        missing_rules = [kpi for kpi in weights if kpi not in kpi_rules]
        if missing_rules:
            missing_text = ", ".join(sorted(missing_rules))
            raise ValueError(f"fundamentals score rules component '{component_name}' references missing KPI rules: {missing_text}")


def required_raw_columns(schema: dict[str, Any], rules: dict[str, Any]) -> list[str]:
    if schema.get("raw_required_columns"):
        return list(schema["raw_required_columns"])
    identity_fields = [
        field
        for field, definition in schema.get("identity_fields", {}).items()
        if bool(definition.get("required"))
    ]
    component_kpis = sorted(
        {
            kpi
            for weights in rules.get("component_scores", {}).values()
            for kpi in weights
        }
    )
    return identity_fields + component_kpis


def validate_raw_fundamentals_schema(
    rows: list[dict[str, str]],
    schema: dict[str, Any],
    rules: dict[str, Any],
    source_name: str,
) -> None:
    if not rows:
        return
    raw_kpi_fields = set(schema.get("raw_kpi_fields", {}))
    component_kpis = {
        kpi
        for weights in rules.get("component_scores", {}).values()
        for kpi in weights
    }
    unknown_rule_kpis = sorted(component_kpis - raw_kpi_fields)
    if unknown_rule_kpis:
        unknown_text = ", ".join(unknown_rule_kpis)
        raise ValueError(f"{source_name} raw schema configuration references unknown KPI fields: {unknown_text}")

    available_columns = set(rows[0].keys())
    missing_columns = [column for column in required_raw_columns(schema, rules) if column not in available_columns]
    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"{source_name} missing required raw fundamentals columns: {missing_text}")


def load_and_validate_score_rules(rules_path: str = DEFAULT_SCORE_RULES_PATH) -> dict[str, Any]:
    rules = load_yaml_config(rules_path)
    validate_component_score_rules(rules)
    return rules


def score_kpi(value: Any, rule: dict[str, Any], missing_score: float) -> tuple[float, bool]:
    if str(value or "").strip() == "":
        return round2(missing_score), False
    numeric_value = to_float(value)
    lower = to_float(rule["lower"])
    upper = to_float(rule["upper"])
    if upper == lower:
        return round2(missing_score), False
    if bool(rule.get("higher_is_better", True)):
        score = ((numeric_value - lower) / (upper - lower)) * 100.0
    else:
        score = ((upper - numeric_value) / (upper - lower)) * 100.0
    return round2(clamp(score)), True


def compute_component_score(
    row: dict[str, Any],
    component_name: str,
    rules: dict[str, Any],
) -> tuple[float, str, list[str]]:
    component_weights = rules["component_scores"][component_name]
    kpi_rules = rules["kpi_score_rules"]
    missing_score = to_float(rules["missing_kpi_score"], 40.0)
    score = 0.0
    details: list[str] = []
    missing: list[str] = []
    for kpi, weight in component_weights.items():
        kpi_score, present = score_kpi(row.get(kpi), kpi_rules[kpi], missing_score)
        score += to_float(weight) * kpi_score
        present_label = "OK" if present else "MISSING"
        details.append(f"{kpi}={row.get(kpi, '')}|score={kpi_score}|weight={weight}|{present_label}")
        if not present:
            missing.append(kpi)
    return round2(score), "; ".join(details), missing


def merge_data_quality(existing_flag: str, missing_kpi_count: int, rules: dict[str, Any]) -> str:
    existing = safe_upper(existing_flag) or "OK"
    if existing == "MISSING_DATA":
        return "MISSING_DATA"
    if existing == "REVIEW":
        return "REVIEW"
    thresholds = rules["data_quality_thresholds"]
    if missing_kpi_count >= int(thresholds["missing_data_missing_kpi_count"]):
        return "MISSING_DATA"
    if missing_kpi_count >= int(thresholds["review_missing_kpi_count"]):
        return "REVIEW"
    return "OK"


def derive_raw_fundamental_row(row: dict[str, str], rules: dict[str, Any]) -> dict[str, Any]:
    enriched: dict[str, Any] = {field: row.get(field, "") for field in PASSTHROUGH_FIELDS}
    enriched["ticker"] = canonicalize_ticker(row.get("ticker", ""))
    enriched["fundamentals_input_format"] = "raw"
    for field in RAW_KPI_FIELDS:
        enriched[field] = row.get(field, "")

    missing_kpis: list[str] = []
    for component in COMPONENT_SCORE_FIELDS:
        component_score, details, missing = compute_component_score(row, component, rules)
        enriched[component] = component_score
        enriched[f"{component}_inputs"] = details
        missing_kpis.extend(missing)

    unique_missing = sorted(set(missing_kpis))
    enriched["missing_kpi_count"] = len(unique_missing)
    enriched["missing_kpis"] = "; ".join(unique_missing)
    enriched["data_quality_flag"] = merge_data_quality(str(row.get("data_quality_flag", "OK")), len(unique_missing), rules)
    return enriched


def enrich_legacy_fundamental_row(row: dict[str, str]) -> dict[str, Any]:
    enriched: dict[str, Any] = {field: row.get(field, "") for field in PASSTHROUGH_FIELDS}
    enriched["ticker"] = canonicalize_ticker(row.get("ticker", ""))
    for field in RAW_KPI_FIELDS:
        enriched[field] = row.get(field, "")
    for field in COMPONENT_SCORE_FIELDS:
        enriched[field] = row.get(field, "")
        enriched[f"{field}_inputs"] = "legacy_preaggregated_score"
    enriched["fundamentals_input_format"] = "legacy"
    enriched["missing_kpi_count"] = ""
    enriched["missing_kpis"] = ""
    for key, value in row.items():
        if key not in enriched:
            enriched[key] = value
    return enriched


def enrich_fundamentals_rows(
    rows: list[dict[str, str]],
    fundamentals_format: str = "auto",
    rules_path: str = DEFAULT_SCORE_RULES_PATH,
    schema_path: str = DEFAULT_SCHEMA_PATH,
    source_name: str = "fundamentals input",
) -> tuple[list[dict[str, Any]], str]:
    detected_format = detect_fundamentals_format(rows, fundamentals_format)
    rules = load_and_validate_score_rules(rules_path)
    if detected_format == "raw":
        schema = load_yaml_config(schema_path)
        validate_raw_fundamentals_schema(rows, schema, rules, source_name)
        return [derive_raw_fundamental_row(row, rules) for row in rows], detected_format
    return [enrich_legacy_fundamental_row(row) for row in rows], detected_format


def build_enriched_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        canonicalize_ticker(row.get("ticker", "")): row
        for row in rows
        if canonicalize_ticker(row.get("ticker", ""))
    }


def build_score_audit_rows(
    score_rows: list[dict[str, Any]],
    enriched_fundamentals_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched_index = build_enriched_index(enriched_fundamentals_rows)
    audit_rows: list[dict[str, Any]] = []
    for score_row in score_rows:
        source_row = enriched_index.get(canonicalize_ticker(score_row.get("ticker", "")), {})
        audit_rows.append(
            {
                **{field: source_row.get(field, "") for field in RAW_KPI_FIELDS},
                "ticker": score_row.get("ticker", ""),
                "isin": score_row.get("isin", source_row.get("isin", "")),
                "company_name": score_row.get("company_name", source_row.get("company_name", "")),
                "fundamentals_input_format": source_row.get("fundamentals_input_format", "missing_fundamentals"),
                "quality_score": score_row.get("quality_score", ""),
                "dividend_score": score_row.get("dividend_score", ""),
                "balance_sheet_score": score_row.get("balance_sheet_score", ""),
                "growth_quality_score": score_row.get("growth_quality_score", ""),
                "capital_allocation_score": score_row.get("capital_allocation_score", ""),
                "business_score": score_row.get("business_score", ""),
                "historical_multiple_score": score_row.get("historical_multiple_score", ""),
                "normalized_fcf_score": score_row.get("normalized_fcf_score", ""),
                "dividend_yield_relative_score": score_row.get("dividend_yield_relative_score", ""),
                "valuation_score": score_row.get("valuation_score", ""),
                "expected_return_score": score_row.get("expected_return_score", ""),
                "drawdown_opportunity_score": score_row.get("drawdown_opportunity_score", ""),
                "portfolio_fit_score": score_row.get("portfolio_fit_score", ""),
                "buy_score": score_row.get("buy_score", ""),
                "business_score_contribution": score_row.get("business_score_contribution", ""),
                "valuation_score_contribution": score_row.get("valuation_score_contribution", ""),
                "expected_return_score_contribution": score_row.get("expected_return_score_contribution", ""),
                "drawdown_score_contribution": score_row.get("drawdown_score_contribution", ""),
                "portfolio_fit_score_contribution": score_row.get("portfolio_fit_score_contribution", ""),
                "pe_relative_ratio": score_row.get("pe_relative_ratio", ""),
                "ev_ebit_relative_ratio": score_row.get("ev_ebit_relative_ratio", ""),
                "fcf_yield_relative_ratio": score_row.get("fcf_yield_relative_ratio", ""),
                "normalized_fcf_gap": score_row.get("normalized_fcf_gap", ""),
                "dividend_yield_relative_ratio": score_row.get("dividend_yield_relative_ratio", ""),
                "fair_value_estimate": score_row.get("fair_value_estimate", ""),
                "margin_of_safety_pct": score_row.get("margin_of_safety_pct", ""),
                "data_quality_flag": score_row.get("data_quality_flag", source_row.get("data_quality_flag", "")),
                "missing_kpi_count": source_row.get("missing_kpi_count", ""),
                "missing_kpis": source_row.get("missing_kpis", ""),
                "quality_score_inputs": source_row.get("quality_score_inputs", ""),
                "dividend_score_inputs": source_row.get("dividend_score_inputs", ""),
                "balance_sheet_score_inputs": source_row.get("balance_sheet_score_inputs", ""),
                "growth_quality_score_inputs": source_row.get("growth_quality_score_inputs", ""),
                "capital_allocation_score_inputs": source_row.get("capital_allocation_score_inputs", ""),
            }
        )
    return audit_rows
