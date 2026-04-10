from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.common import load_yaml_config, round2, safe_upper, to_float

DEFAULT_RULES_PATH = "configs/portfolio_rules.yaml"


def load_portfolio_rules(path: str = DEFAULT_RULES_PATH) -> dict[str, Any]:
    return load_yaml_config(path)


def classify_sleeve(row: dict[str, Any]) -> str:
    sleeve = safe_upper(row.get("sleeve"))
    asset_type = safe_upper(row.get("asset_type"))
    company_name = str(row.get("company_name", "")).lower()
    if sleeve:
        return sleeve
    if asset_type == "CASH":
        return "CASH"
    if asset_type == "ETF":
        if "quality" in company_name or "dividend" in company_name or "income" in company_name:
            return "DIVIDEND_QUALITY_ETF"
        return "CORE_ETF"
    return "SINGLE_STOCK"


def compute_total_assets(rows: list[dict[str, Any]]) -> float:
    return round2(sum(to_float(row.get("market_value_eur")) for row in rows))


def aggregate_positions_by_ticker(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregated: dict[str, dict[str, Any]] = {}
    numeric_fields = {"quantity", "market_value_eur", "cost_basis_eur", "unrealized_pnl_eur"}

    for row in rows:
        ticker = str(row.get("ticker", "")).strip()
        if not ticker:
            continue
        if ticker not in aggregated:
            aggregated[ticker] = dict(row)
            for field in numeric_fields:
                if field in aggregated[ticker]:
                    aggregated[ticker][field] = round2(to_float(aggregated[ticker].get(field)))
            continue

        current = aggregated[ticker]
        for field in numeric_fields:
            if field in row or field in current:
                current[field] = round2(to_float(current.get(field)) + to_float(row.get(field)))
        for key, value in row.items():
            if key in numeric_fields:
                continue
            if current.get(key) in ("", None) and value not in ("", None):
                current[key] = value

    return list(aggregated.values())


def compute_portfolio_value(rows: list[dict[str, Any]]) -> float:
    return round2(
        sum(
            to_float(row.get("market_value_eur"))
            for row in rows
            if classify_sleeve(row) != "CASH"
        )
    )


def compute_cash_value(rows: list[dict[str, Any]]) -> float:
    return round2(
        sum(
            to_float(row.get("market_value_eur"))
            for row in rows
            if classify_sleeve(row) == "CASH"
        )
    )


def allocation_summary(rows: list[dict[str, Any]]) -> dict[str, float]:
    total_assets = compute_total_assets(rows) or 1.0
    grouped = defaultdict(float)
    for row in rows:
        grouped[classify_sleeve(row)] += to_float(row.get("market_value_eur"))
    return {
        "core_etf_weight": round2(grouped["CORE_ETF"] / total_assets),
        "dividend_quality_etf_weight": round2(grouped["DIVIDEND_QUALITY_ETF"] / total_assets),
        "single_stocks_weight": round2(grouped["SINGLE_STOCK"] / total_assets),
        "cash_weight": round2(grouped["CASH"] / total_assets),
    }


def compute_position_weights(rows: list[dict[str, Any]]) -> dict[str, float]:
    total_assets = compute_total_assets(rows) or 1.0
    result: dict[str, float] = {}
    for row in aggregate_positions_by_ticker(rows):
        ticker = str(row.get("ticker", "")).strip()
        if not ticker:
            continue
        result[ticker] = round2(to_float(row.get("market_value_eur")) / total_assets)
    return result


def compute_sector_weights(rows: list[dict[str, Any]]) -> dict[str, float]:
    total_assets = compute_total_assets(rows) or 1.0
    grouped = defaultdict(float)
    for row in rows:
        if classify_sleeve(row) == "CASH":
            continue
        grouped[str(row.get("sector", "Unknown"))] += to_float(row.get("market_value_eur"))
    return {sector: round2(value / total_assets) for sector, value in grouped.items()}


def compute_top10_weights(rows: list[dict[str, Any]]) -> dict[str, float]:
    aggregated_rows = aggregate_positions_by_ticker(rows)
    total_assets = compute_total_assets(rows) or 1.0
    invested_assets = compute_portfolio_value(rows) or 1.0
    investable = sorted(
        (
            to_float(row.get("market_value_eur"))
            for row in aggregated_rows
            if classify_sleeve(row) != "CASH"
        ),
        reverse=True,
    )
    top10_value = sum(investable[:10])
    return {
        "top10_weight_total_assets": round2(top10_value / total_assets),
        "top10_weight_invested_assets": round2(top10_value / invested_assets) if invested_assets else 0.0,
    }


def compute_top10_weight(rows: list[dict[str, Any]]) -> float:
    return compute_top10_weights(rows)["top10_weight_total_assets"]


def check_corridor_breaches(
    rows: list[dict[str, Any]],
    rules: dict[str, Any] | None = None,
) -> list[str]:
    config = rules or load_portfolio_rules()
    summary = allocation_summary(rows)
    breaches: list[str] = []
    checks = [
        ("core_etf_weight", "target_core_etf_min", "target_core_etf_max", "Core ETF"),
        (
            "dividend_quality_etf_weight",
            "target_dividend_quality_etf_min",
            "target_dividend_quality_etf_max",
            "Dividend/Quality ETF",
        ),
        ("single_stocks_weight", "target_single_stocks_min", "target_single_stocks_max", "Single Stocks"),
        ("cash_weight", "target_cash_min", "target_cash_max", "Cash"),
    ]
    for weight_key, min_key, max_key, label in checks:
        current = summary[weight_key]
        lower = to_float(config.get(min_key))
        upper = to_float(config.get(max_key))
        if current < lower:
            breaches.append(f"{label} below corridor ({round2(current * 100)}% < {round2(lower * 100)}%)")
        if current > upper:
            breaches.append(f"{label} above corridor ({round2(current * 100)}% > {round2(upper * 100)}%)")
    return breaches


def find_rule_violations(
    rows: list[dict[str, Any]],
    rules: dict[str, Any] | None = None,
) -> list[str]:
    config = rules or load_portfolio_rules()
    violations = list(check_corridor_breaches(rows, config))
    position_weights = compute_position_weights(rows)
    row_index = {str(row.get("ticker", "")).strip(): row for row in aggregate_positions_by_ticker(rows)}
    sector_weights = compute_sector_weights(rows)
    max_position = to_float(config.get("max_single_position_weight"))
    max_sector = to_float(config.get("max_sector_weight"))
    max_top10 = to_float(config.get("max_top10_weight"))

    for ticker, weight in position_weights.items():
        if classify_sleeve(row_index.get(ticker, {})) == "CASH":
            continue
        if weight > max_position:
            violations.append(
                f"{ticker} exceeds max single position ({round2(weight * 100)}% > {round2(max_position * 100)}%)"
            )

    for sector, weight in sector_weights.items():
        if weight > max_sector:
            violations.append(
                f"{sector} exceeds max sector weight ({round2(weight * 100)}% > {round2(max_sector * 100)}%)"
            )

    top10_weight = compute_top10_weight(rows)
    if top10_weight > max_top10:
        violations.append(
            f"Top 10 concentration exceeds limit ({round2(top10_weight * 100)}% > {round2(max_top10 * 100)}%)"
        )
    return violations
