from __future__ import annotations

from typing import Any

from src.common import round2, safe_upper, to_bool, to_float
from src.portfolio_rules import aggregate_positions_by_ticker, classify_sleeve, load_portfolio_rules
from src.scoring_engine import evaluate_purchase_readiness

DEFAULT_RULES_PATH = "configs/portfolio_rules.yaml"

HOLDINGS_ACTION_FIELDS = [
    "ticker",
    "company_name",
    "asset_type",
    "sleeve",
    "market_value",
    "current_weight",
    "business_score",
    "valuation_score",
    "buy_score",
    "mandate_fit",
    "purchase_readiness",
    "portfolio_action",
    "portfolio_action_reason",
    "data_quality_flag",
    "review_flag",
]


def build_positions_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("ticker", "")).strip(): row
        for row in aggregate_positions_by_ticker(rows)
        if str(row.get("ticker", "")).strip()
    }


def build_scores_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not to_bool(row.get("held_in_portfolio", True)):
            continue
        for key in {str(row.get("ticker", "")).strip(), str(row.get("isin", "")).strip().upper()}:
            if key:
                index[key] = row
    return index


def describe_mandate_fit(position_row: dict[str, Any], score_row: dict[str, Any]) -> str:
    sleeve = classify_sleeve({**position_row, **score_row})
    mandate_fit_score = to_float(score_row.get("mandate_fit_score"), to_float(position_row.get("mandate_fit_score"), 0.0))
    data_quality_flag = safe_upper(score_row.get("data_quality_flag", position_row.get("data_quality_flag", "OK")))
    review_flag = to_bool(position_row.get("review_flag")) or data_quality_flag != "OK"

    if sleeve == "CASH":
        return "CASH_RESERVE"
    if review_flag:
        return "REVIEW"
    if sleeve == "CORE_ETF":
        return "CORE"
    if sleeve == "DIVIDEND_QUALITY_ETF":
        return "DG_QUALITY"
    if sleeve == "NON_CORE":
        return "NON_CORE"
    if sleeve == "REVIEW":
        return "REVIEW"
    if mandate_fit_score >= 75.0:
        return "MANDATE_FIT"
    if mandate_fit_score >= 60.0:
        return "WATCH"
    return "LOW_FIT"


def build_missing_score_row(position_row: dict[str, Any]) -> dict[str, Any]:
    if classify_sleeve(position_row) == "CASH":
        return {
            "ticker": position_row.get("ticker", ""),
            "company_name": position_row.get("company_name", ""),
            "asset_type": "CASH",
            "sleeve": "CASH",
            "current_weight_pct": position_row.get("weight_total_assets_pct", 0.0),
            "business_score": 0.0,
            "valuation_score": 0.0,
            "buy_score": 0.0,
            "mandate_fit_score": 0.0,
            "classification": "HOLD",
            "data_quality_flag": "OK",
            "has_hard_risk_flag": "false",
        }
    return {
        "ticker": position_row.get("ticker", ""),
        "company_name": position_row.get("company_name", ""),
        "asset_type": position_row.get("asset_type", "OTHER"),
        "sleeve": position_row.get("sleeve", "REVIEW"),
        "current_weight_pct": position_row.get("weight_total_assets_pct", 0.0),
        "business_score": 0.0,
        "valuation_score": 0.0,
        "buy_score": 0.0,
        "mandate_fit_score": 0.0,
        "classification": "EXIT_REVIEW",
        "data_quality_flag": "MISSING_DATA",
        "has_hard_risk_flag": "false",
    }


def classify_portfolio_action(
    position_row: dict[str, Any],
    score_row: dict[str, Any],
    rules: dict[str, Any],
) -> tuple[str, str, str]:
    sleeve = classify_sleeve({**position_row, **score_row})
    classification = safe_upper(score_row.get("classification"))
    data_quality_flag = safe_upper(score_row.get("data_quality_flag", position_row.get("data_quality_flag", "OK"))) or "OK"
    review_flag = to_bool(position_row.get("review_flag")) or data_quality_flag != "OK"
    current_weight = to_float(score_row.get("current_weight_pct"), to_float(position_row.get("weight_total_assets_pct")))
    mandate_fit = describe_mandate_fit(position_row, score_row)
    purchase = evaluate_purchase_readiness(score_row, rules)
    purchase_state = str(purchase["purchase_state"])
    max_position_pct = to_float(rules["max_single_position_weight"]) * 100.0
    reduce_threshold_pct = to_float(rules["sell_rules"]["reduce_if_weight_above"]) * 100.0
    near_position_cap = current_weight >= (max_position_pct * 0.9)

    if sleeve == "CASH":
        return "HOLD", "Liquiditaetsreserve bleibt als Cash-Puffer verfuegbar.", purchase_state
    if classification == "REDUCE" or current_weight > reduce_threshold_pct:
        return "REDUCE", "Position ist uebergewichtet oder klar ueberdehnt und sollte reduziert werden.", purchase_state
    if classification == "EXIT_REVIEW" or review_flag or mandate_fit in {"NON_CORE", "REVIEW", "LOW_FIT"}:
        return "EXIT_REVIEW", "Mandats-Fit, Datenlage oder Positionscharakter erfordern eine Exit-Pruefung.", purchase_state
    if purchase["eligible_for_purchase"] and not near_position_cap and mandate_fit in {"CORE", "DG_QUALITY", "MANDATE_FIT"}:
        return "ADD", "Mandatkonform, kaufbar und nicht uebergewichtet.", purchase_state
    if purchase_state in {"TOO_EXPENSIVE", "REVIEW"} or mandate_fit == "WATCH":
        return "WATCH", "Grundsaetzlich haltbar, aber aktuell kein klarer Ausbau oder Exit.", purchase_state
    return "HOLD", "Mandatkonform ohne akuten Kauf- oder Reduktionsbedarf.", purchase_state


def build_holdings_action_table(
    positions_rows: list[dict[str, Any]],
    score_rows: list[dict[str, Any]],
    rules_path: str = DEFAULT_RULES_PATH,
) -> list[dict[str, Any]]:
    rules = load_portfolio_rules(rules_path)
    positions_index = build_positions_index(positions_rows)
    scores_index = build_scores_index(score_rows)
    action_rows: list[dict[str, Any]] = []

    for ticker in sorted(positions_index):
        position_row = positions_index[ticker]
        score_row = scores_index.get(ticker, build_missing_score_row(position_row))
        portfolio_action, action_reason, purchase_state = classify_portfolio_action(position_row, score_row, rules)
        review_flag = to_bool(position_row.get("review_flag")) or safe_upper(score_row.get("data_quality_flag", "OK")) != "OK"
        display_ticker = str(score_row.get("ticker") or ticker).strip()
        action_rows.append(
            {
                "ticker": display_ticker,
                "company_name": score_row.get("company_name") or position_row.get("company_name", ticker),
                "asset_type": position_row.get("asset_type", score_row.get("asset_type", "OTHER")),
                "sleeve": classify_sleeve(position_row),
                "market_value": round2(to_float(position_row.get("market_value_eur"))),
                "current_weight": round2(to_float(score_row.get("current_weight_pct"), to_float(position_row.get("weight_total_assets_pct")))),
                "business_score": round2(to_float(score_row.get("business_score"))),
                "valuation_score": round2(to_float(score_row.get("valuation_score"))),
                "buy_score": round2(to_float(score_row.get("buy_score"))),
                "mandate_fit": describe_mandate_fit(position_row, score_row),
                "purchase_readiness": purchase_state,
                "portfolio_action": portfolio_action,
                "portfolio_action_reason": action_reason,
                "data_quality_flag": safe_upper(score_row.get("data_quality_flag", position_row.get("data_quality_flag", "OK"))) or "OK",
                "review_flag": review_flag,
            }
        )

    action_priority = {"ADD": 0, "HOLD": 1, "WATCH": 2, "REDUCE": 3, "EXIT_REVIEW": 4}
    action_rows.sort(
        key=lambda row: (
            action_priority.get(str(row["portfolio_action"]), 9),
            -to_float(row.get("market_value")),
            str(row["ticker"]),
        )
    )
    return action_rows
