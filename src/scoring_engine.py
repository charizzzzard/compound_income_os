from __future__ import annotations

import argparse
from typing import Any

from src.common import (
    clamp,
    load_yaml_config,
    read_csv_rows,
    require_columns,
    round2,
    score_linear,
    to_bool,
    to_float,
    write_csv_rows,
)
from src.portfolio_rules import aggregate_positions_by_ticker, compute_position_weights, compute_sector_weights, load_portfolio_rules
from src.valuation_engine import compute_valuation_metrics

DEFAULT_RULES_PATH = "configs/portfolio_rules.yaml"
DEFAULT_SCORING_PATH = "configs/scoring_weights.yaml"

OUTPUT_FIELDS = [
    "ticker",
    "company_name",
    "sector",
    "country",
    "asset_type",
    "sleeve",
    "held_in_portfolio",
    "position_market_value_eur",
    "current_weight_pct",
    "sector_weight_pct",
    "quality_score",
    "dividend_score",
    "balance_sheet_score",
    "growth_quality_score",
    "capital_allocation_score",
    "business_score",
    "historical_multiple_score",
    "normalized_fcf_score",
    "dividend_yield_relative_score",
    "valuation_score",
    "expected_return_score",
    "portfolio_fit_score",
    "drawdown_opportunity_score",
    "expected_return_pct",
    "fair_value_estimate",
    "margin_of_safety_pct",
    "valuation_comment",
    "mandate_fit_score",
    "thesis_summary",
    "main_risks",
    "data_quality_flag",
    "has_hard_risk_flag",
    "buy_score",
    "classification",
]


def build_position_index(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in aggregate_positions_by_ticker(rows):
        ticker = str(row.get("ticker", "")).strip()
        if ticker and str(row.get("asset_type", "")).upper() != "CASH":
            index[ticker] = row
    return index


def build_fundamentals_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {str(row.get("ticker", "")).strip(): row for row in rows if str(row.get("ticker", "")).strip()}


def build_missing_fundamentals_row(
    position_row: dict[str, Any],
    scoring_config: dict[str, Any],
) -> dict[str, Any]:
    fallback_business = to_float(scoring_config["fallback_scores"]["business_component_missing"], 40.0)
    fallback_fit = to_float(scoring_config["fallback_scores"]["portfolio_fit_missing"], 50.0)
    ticker = str(position_row.get("ticker", "")).strip()
    company_name = str(position_row.get("company_name", ticker))
    return {
        "ticker": ticker,
        "company_name": company_name,
        "sector": position_row.get("sector", "Unknown"),
        "country": position_row.get("country", "Unknown"),
        "asset_type": position_row.get("asset_type", "STOCK"),
        "sleeve": position_row.get("sleeve", "SINGLE_STOCK"),
        "current_price_eur": to_float(position_row.get("price_eur")),
        "quality_score": fallback_business,
        "dividend_score": fallback_business,
        "balance_sheet_score": fallback_business,
        "growth_quality_score": fallback_business,
        "capital_allocation_score": fallback_business,
        "mandate_fit_score": fallback_fit,
        "expected_return_pct": "",
        "drawdown_from_high_pct": 0.0,
        "has_hard_risk_flag": "false",
        "thesis_robustness": "REVIEW",
        "thesis_summary": "Missing fundamentals for held position; manual review required.",
        "main_risks": "Missing fundamentals / valuation inputs.",
        "data_quality_flag": "MISSING_DATA",
    }


def compute_business_score(row: dict[str, Any], config: dict[str, Any]) -> float:
    weights = config["business_score_weights"]
    return round2(
        (weights["quality_score"] * to_float(row.get("quality_score"), 40.0))
        + (weights["dividend_score"] * to_float(row.get("dividend_score"), 40.0))
        + (weights["balance_sheet_score"] * to_float(row.get("balance_sheet_score"), 40.0))
        + (weights["growth_quality_score"] * to_float(row.get("growth_quality_score"), 40.0))
        + (weights["capital_allocation_score"] * to_float(row.get("capital_allocation_score"), 40.0))
    )


def compute_expected_return_score(row: dict[str, Any], fallback: float) -> float:
    expected_return = to_float(row.get("expected_return_pct"))
    if expected_return == 0.0 and str(row.get("expected_return_pct", "")).strip() == "":
        return fallback
    return round2(score_linear(expected_return, -5.0, 15.0))


def compute_portfolio_fit_score(
    row: dict[str, Any],
    current_weight_pct: float,
    sector_weight_pct: float,
    rules: dict[str, Any],
    fallback: float,
) -> float:
    base = to_float(row.get("mandate_fit_score"), fallback)
    max_position_pct = to_float(rules["max_single_position_weight"]) * 100.0
    max_sector_pct = to_float(rules["max_sector_weight"]) * 100.0
    if current_weight_pct > max_position_pct * 0.9:
        base -= 20.0
    if sector_weight_pct > max_sector_pct * 0.9:
        base -= 10.0
    if str(row.get("sleeve", "")).upper() == "CORE_ETF":
        base += 5.0
    return round2(clamp(base))


def compute_drawdown_score(row: dict[str, Any]) -> float:
    drawdown = to_float(row.get("drawdown_from_high_pct"))
    return round2(score_linear(drawdown, 0.0, 50.0))


def compute_buy_score(
    business_score: float,
    valuation_score: float,
    expected_return_score: float,
    drawdown_score: float,
    portfolio_fit_score: float,
) -> float:
    return round2(
        0.55 * business_score
        + 0.45
        * (
            0.40 * valuation_score
            + 0.25 * expected_return_score
            + 0.20 * drawdown_score
            + 0.15 * portfolio_fit_score
        )
    )


def classify_company(
    business_score: float,
    valuation_score: float,
    buy_score: float,
    held_in_portfolio: bool,
    current_weight_pct: float,
    has_hard_risk_flag: bool,
    thesis_robustness: str,
    data_quality_flag: str,
    rules: dict[str, Any],
) -> str:
    buy_rules = rules["buy_rules"]
    sell_rules = rules["sell_rules"]
    if held_in_portfolio:
        if has_hard_risk_flag or thesis_robustness in {"FRAGILE", "BROKEN"}:
            return "EXIT_REVIEW"
        if data_quality_flag != "OK":
            return "EXIT_REVIEW"
        if business_score < to_float(buy_rules["reject_business_score_below"]) or valuation_score < to_float(
            buy_rules["reject_valuation_score_below"]
        ):
            return "EXIT_REVIEW"
        if (
            current_weight_pct > (to_float(sell_rules["reduce_if_weight_above"]) * 100.0)
            or valuation_score < to_float(sell_rules["reduce_if_extreme_overvaluation_score_below"])
        ):
            return "REDUCE"
        return "HOLD"

    if has_hard_risk_flag or thesis_robustness in {"FRAGILE", "BROKEN"}:
        return "REJECT"
    if business_score < to_float(buy_rules["reject_business_score_below"]) or valuation_score < to_float(
        buy_rules["reject_valuation_score_below"]
    ):
        return "REJECT"
    if (
        business_score >= to_float(buy_rules["min_business_score"])
        and valuation_score >= to_float(buy_rules["min_valuation_score"])
        and buy_score >= to_float(buy_rules["min_buy_score"])
    ):
        return "BUY_CANDIDATE"
    if business_score >= to_float(buy_rules["min_business_score"]) and 45.0 <= valuation_score <= 59.99:
        return "WATCHLIST"
    return "WATCHLIST"


def build_scores(
    positions_rows: list[dict[str, str]],
    fundamentals_rows: list[dict[str, str]],
    rules_path: str = DEFAULT_RULES_PATH,
    scoring_path: str = DEFAULT_SCORING_PATH,
) -> list[dict[str, Any]]:
    scoring_config = load_yaml_config(scoring_path)
    rules = load_portfolio_rules(rules_path)
    position_index = build_position_index(positions_rows)
    fundamentals_index = build_fundamentals_index(fundamentals_rows)
    position_weights = compute_position_weights(positions_rows)
    sector_weights = compute_sector_weights(positions_rows)
    universe_tickers = sorted(set(position_index) | set(fundamentals_index))

    results: list[dict[str, Any]] = []
    for ticker in universe_tickers:
        row = fundamentals_index.get(ticker) or build_missing_fundamentals_row(position_index[ticker], scoring_config)
        held_position = position_index.get(ticker)
        current_weight_pct = round2(position_weights.get(ticker, 0.0) * 100.0)
        sector_weight_pct = round2(sector_weights.get(str(row.get("sector", "Unknown")), 0.0) * 100.0)
        business_score = compute_business_score(row, scoring_config)
        valuation_metrics = compute_valuation_metrics(row, scoring_path)
        expected_return_score = compute_expected_return_score(
            row,
            to_float(scoring_config["fallback_scores"]["expected_return_missing"]),
        )
        portfolio_fit_score = compute_portfolio_fit_score(
            row,
            current_weight_pct,
            sector_weight_pct,
            rules,
            to_float(scoring_config["fallback_scores"]["portfolio_fit_missing"]),
        )
        drawdown_score = compute_drawdown_score(row)
        valuation_score = valuation_metrics["fair_value_score"]
        buy_score = compute_buy_score(
            business_score,
            valuation_score,
            expected_return_score,
            drawdown_score,
            portfolio_fit_score,
        )
        has_hard_risk_flag = to_bool(row.get("has_hard_risk_flag"))
        thesis_robustness = str(row.get("thesis_robustness", "REVIEW")).strip().upper()
        data_quality_flag = str(valuation_metrics["data_quality_flag"]).upper()
        if ticker in position_index and ticker not in fundamentals_index:
            data_quality_flag = "MISSING_DATA"
            valuation_metrics["valuation_comment"] = "Missing fundamentals for held position; manual review required."
        classification = classify_company(
            business_score,
            valuation_score,
            buy_score,
            held_position is not None,
            current_weight_pct,
            has_hard_risk_flag,
            thesis_robustness,
            data_quality_flag,
            rules,
        )
        results.append(
            {
                "ticker": ticker,
                "company_name": row.get("company_name", ticker),
                "sector": row.get("sector", "Unknown"),
                "country": row.get("country", "Unknown"),
                "asset_type": row.get("asset_type", "STOCK"),
                "sleeve": row.get("sleeve", "SINGLE_STOCK"),
                "held_in_portfolio": held_position is not None,
                "position_market_value_eur": round2(to_float(held_position.get("market_value_eur")) if held_position else 0.0),
                "current_weight_pct": current_weight_pct,
                "sector_weight_pct": sector_weight_pct,
                "quality_score": round2(to_float(row.get("quality_score"), 40.0)),
                "dividend_score": round2(to_float(row.get("dividend_score"), 40.0)),
                "balance_sheet_score": round2(to_float(row.get("balance_sheet_score"), 40.0)),
                "growth_quality_score": round2(to_float(row.get("growth_quality_score"), 40.0)),
                "capital_allocation_score": round2(to_float(row.get("capital_allocation_score"), 40.0)),
                "business_score": business_score,
                "historical_multiple_score": valuation_metrics["historical_multiple_score"],
                "normalized_fcf_score": valuation_metrics["normalized_fcf_score"],
                "dividend_yield_relative_score": valuation_metrics["dividend_yield_relative_score"],
                "valuation_score": valuation_metrics["fair_value_score"],
                "expected_return_score": expected_return_score,
                "portfolio_fit_score": portfolio_fit_score,
                "drawdown_opportunity_score": drawdown_score,
                "expected_return_pct": round2(to_float(row.get("expected_return_pct"))),
                "fair_value_estimate": valuation_metrics["fair_value_estimate"],
                "margin_of_safety_pct": valuation_metrics["margin_of_safety_pct"],
                "valuation_comment": valuation_metrics["valuation_comment"],
                "mandate_fit_score": round2(to_float(row.get("mandate_fit_score"), 50.0)),
                "thesis_summary": row.get("thesis_summary", ""),
                "main_risks": row.get("main_risks", ""),
                "data_quality_flag": data_quality_flag,
                "has_hard_risk_flag": has_hard_risk_flag,
                "buy_score": buy_score,
                "classification": classification,
            }
        )

    classification_order = {
        "BUY_CANDIDATE": 0,
        "WATCHLIST": 1,
        "HOLD": 2,
        "REDUCE": 3,
        "EXIT_REVIEW": 4,
        "REJECT": 5,
    }
    results.sort(
        key=lambda row: (
            not bool(row["held_in_portfolio"]),
            classification_order.get(str(row["classification"]), 9),
            -float(row["buy_score"]),
            -float(row["valuation_score"]),
            str(row["ticker"]),
        )
    )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build company-level quality and valuation scores.")
    parser.add_argument("--positions", required=True, help="Normalized positions snapshot CSV.")
    parser.add_argument("--fundamentals", required=True, help="Fundamentals and valuation CSV.")
    parser.add_argument("--output", required=True, help="Output scores CSV.")
    parser.add_argument("--rules", default=DEFAULT_RULES_PATH, help="Portfolio rules config path.")
    parser.add_argument("--scoring-config", default=DEFAULT_SCORING_PATH, help="Scoring config path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    positions_rows = read_csv_rows(args.positions)
    fundamentals_rows = read_csv_rows(args.fundamentals)
    require_columns(
        positions_rows,
        ["ticker", "market_value_eur", "asset_type", "sleeve", "sector"],
        f"positions CSV ({args.positions})",
    )
    if fundamentals_rows:
        require_columns(
            fundamentals_rows,
            ["ticker", "company_name", "sector", "country", "asset_type", "sleeve"],
            f"fundamentals CSV ({args.fundamentals})",
        )
    results = build_scores(positions_rows, fundamentals_rows, args.rules, args.scoring_config)
    write_csv_rows(args.output, OUTPUT_FIELDS, results)


if __name__ == "__main__":
    main()
