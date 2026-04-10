from __future__ import annotations

import argparse
import math
import re
from typing import Any

from src.common import (
    canonicalize_ticker,
    clamp,
    load_yaml_config,
    read_csv_rows,
    require_columns,
    round2,
    score_linear,
    to_bool,
    to_float,
    write_csv_rows,
    require_unique_tickers,
    safe_upper,
)
from src.fundamentals_engine import (
    ENRICHED_OUTPUT_FIELDS,
    SCORE_AUDIT_FIELDS,
    build_score_audit_rows,
    enrich_fundamentals_rows,
)
from src.portfolio_rules import aggregate_positions_by_ticker, compute_position_weights, compute_sector_weights, load_portfolio_rules
from src.valuation_engine import compute_valuation_metrics

DEFAULT_RULES_PATH = "configs/portfolio_rules.yaml"
DEFAULT_SCORING_PATH = "configs/scoring_weights.yaml"
DEFAULT_FUNDAMENTALS_SCORE_RULES_PATH = "configs/fundamentals_score_rules.yaml"
BUY_SCORE_WEIGHT_KEYS = (
    "business_score",
    "valuation_score",
    "expected_return_score",
    "drawdown_opportunity_score",
    "portfolio_fit_score",
)
ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

OUTPUT_FIELDS = [
    "ticker",
    "isin",
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
    "mandate_fit",
    "thesis_summary",
    "main_risks",
    "data_quality_flag",
    "has_hard_risk_flag",
    "purchase_readiness",
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
    "fundamentals_input_format",
    "classification",
]


def normalize_match_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def is_probable_isin(value: Any) -> bool:
    return bool(ISIN_PATTERN.match(str(value or "").strip().upper()))


def build_fundamentals_isin_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    duplicates: set[str] = set()
    for row in rows:
        isin = str(row.get("isin", "")).strip().upper()
        if not isin:
            continue
        if isin in index:
            duplicates.add(isin)
        index[isin] = row
    if duplicates:
        duplicate_text = ", ".join(sorted(duplicates))
        raise ValueError(f"fundamentals input contains duplicate ISIN values: {duplicate_text}")
    return index


def build_fundamentals_name_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    index: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        name_key = normalize_match_text(row.get("company_name"))
        if name_key:
            index.setdefault(name_key, []).append(row)
    return index


def find_unique_name_match(position_row: dict[str, Any], fundamentals_name_index: dict[str, list[dict[str, str]]]) -> dict[str, str] | None:
    position_name = normalize_match_text(position_row.get("company_name") or position_row.get("raw_name"))
    if not position_name:
        return None
    matches = [
        row for name_key, rows in fundamentals_name_index.items()
        if len(name_key) >= 4 and (name_key in position_name or position_name in name_key)
        for row in rows
    ]
    return matches[0] if len(matches) == 1 else None


def resolve_position_key(
    row: dict[str, Any],
    fundamentals_by_isin: dict[str, dict[str, str]],
    fundamentals_by_name: dict[str, list[dict[str, str]]],
) -> str:
    ticker = canonicalize_ticker(row.get("ticker", ""))
    isin = str(row.get("isin", "")).strip().upper()
    if ticker and not is_probable_isin(ticker):
        return ticker
    if isin and isin in fundamentals_by_isin:
        return canonicalize_ticker(fundamentals_by_isin[isin].get("ticker", "")) or ticker or isin
    name_match = find_unique_name_match(row, fundamentals_by_name)
    if name_match:
        return canonicalize_ticker(name_match.get("ticker", "")) or ticker or isin
    return ticker or isin


def build_position_index(
    rows: list[dict[str, str]],
    fundamentals_by_isin: dict[str, dict[str, str]] | None = None,
    fundamentals_by_name: dict[str, list[dict[str, str]]] | None = None,
) -> dict[str, dict[str, Any]]:
    isin_index = fundamentals_by_isin or {}
    name_index = fundamentals_by_name or {}
    canonical_rows: list[dict[str, Any]] = []
    for row in aggregate_positions_by_ticker(rows):
        ticker = resolve_position_key(row, isin_index, name_index)
        if ticker and str(row.get("asset_type", "")).upper() != "CASH":
            current = dict(row)
            current["ticker"] = ticker
            canonical_rows.append(current)
    return {
        canonicalize_ticker(row.get("ticker", "")): row
        for row in aggregate_positions_by_ticker(canonical_rows)
        if canonicalize_ticker(row.get("ticker", ""))
    }


def build_fundamentals_index(rows: list[dict[str, str]], source_name: str = "fundamentals input") -> dict[str, dict[str, str]]:
    require_unique_tickers(rows, source_name)
    return {
        canonicalize_ticker(row.get("ticker", "")): {**row, "ticker": canonicalize_ticker(row.get("ticker", ""))}
        for row in rows
        if canonicalize_ticker(row.get("ticker", ""))
    }


def build_missing_fundamentals_row(
    position_row: dict[str, Any],
    scoring_config: dict[str, Any],
) -> dict[str, Any]:
    fallback_business = to_float(scoring_config["fallback_scores"]["business_component_missing"], 40.0)
    fallback_fit = to_float(scoring_config["fallback_scores"]["portfolio_fit_missing"], 50.0)
    ticker = canonicalize_ticker(position_row.get("ticker", ""))
    company_name = str(position_row.get("company_name", ticker))
    return {
        "ticker": ticker,
        "isin": position_row.get("isin", ""),
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
        "thesis_summary": "Fundamentaldaten fuer die gehaltene Position fehlen; manuelle Pruefung erforderlich.",
        "main_risks": "Fundamentaldaten und Bewertungsinputs fehlen.",
        "data_quality_flag": "MISSING_DATA",
        "fundamentals_input_format": "missing_fundamentals",
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


def load_buy_score_weights(config: dict[str, Any] | None = None, scoring_path: str = DEFAULT_SCORING_PATH) -> dict[str, float]:
    config = config or load_yaml_config(scoring_path)
    raw_weights = config.get("buy_score_weights")
    if not isinstance(raw_weights, dict):
        raise ValueError("scoring config missing buy_score_weights mapping")

    weights: dict[str, float] = {}
    missing_keys = [key for key in BUY_SCORE_WEIGHT_KEYS if key not in raw_weights]
    if missing_keys:
        missing_text = ", ".join(sorted(missing_keys))
        raise ValueError(f"buy_score_weights missing keys: {missing_text}")

    for key in BUY_SCORE_WEIGHT_KEYS:
        value = to_float(raw_weights.get(key), float("nan"))
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"buy_score_weights contains invalid value for {key}: {raw_weights.get(key)!r}")
        weights[key] = value

    total_weight = sum(weights.values())
    if not math.isclose(total_weight, 1.0, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError(f"buy_score_weights must sum to 1.0, got {round2(total_weight)}")
    return weights


def compute_buy_score(
    business_score: float,
    valuation_score: float,
    expected_return_score: float,
    drawdown_score: float,
    portfolio_fit_score: float,
    scoring_config: dict[str, Any] | None = None,
) -> float:
    return round2(
        sum(
            compute_buy_score_contributions(
                business_score,
                valuation_score,
                expected_return_score,
                drawdown_score,
                portfolio_fit_score,
                scoring_config,
            ).values()
        )
    )


def compute_buy_score_contributions(
    business_score: float,
    valuation_score: float,
    expected_return_score: float,
    drawdown_score: float,
    portfolio_fit_score: float,
    scoring_config: dict[str, Any],
) -> dict[str, float]:
    weights = load_buy_score_weights(scoring_config)
    return {
        "business_score_contribution": round2(weights["business_score"] * business_score),
        "valuation_score_contribution": round2(weights["valuation_score"] * valuation_score),
        "expected_return_score_contribution": round2(weights["expected_return_score"] * expected_return_score),
        "drawdown_score_contribution": round2(weights["drawdown_opportunity_score"] * drawdown_score),
        "portfolio_fit_score_contribution": round2(weights["portfolio_fit_score"] * portfolio_fit_score),
    }


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


def evaluate_purchase_readiness(score_row: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    buy_rules = rules["buy_rules"]
    business_score = to_float(score_row.get("business_score"))
    valuation_score = to_float(score_row.get("valuation_score"))
    buy_score = to_float(score_row.get("buy_score"))
    classification = safe_upper(score_row.get("classification", "WATCHLIST"))
    data_quality_flag = safe_upper(score_row.get("data_quality_flag", "OK")) or "OK"
    hard_risk = to_bool(score_row.get("has_hard_risk_flag"))

    business_ok = business_score >= to_float(buy_rules["min_business_score"])
    valuation_ok = valuation_score >= to_float(buy_rules["min_valuation_score"])
    buy_ok = buy_score >= to_float(buy_rules["min_buy_score"])
    reject_business = business_score < to_float(buy_rules["reject_business_score_below"])
    reject_valuation = valuation_score < to_float(buy_rules["reject_valuation_score_below"])
    data_ok = data_quality_flag == "OK"
    blocked_classification = classification in {"REJECT", "EXIT_REVIEW", "REDUCE"}
    watchlist_window = business_ok and 45.0 <= valuation_score <= 59.99

    if hard_risk or blocked_classification or reject_business or reject_valuation:
        purchase_state = "BLOCKED"
    elif not data_ok:
        purchase_state = "REVIEW"
    elif business_ok and valuation_ok and buy_ok:
        purchase_state = "BUYABLE"
    elif watchlist_window:
        purchase_state = "TOO_EXPENSIVE"
    else:
        purchase_state = "REVIEW"

    return {
        "business_score": business_score,
        "valuation_score": valuation_score,
        "buy_score": buy_score,
        "classification": classification,
        "data_quality_flag": data_quality_flag,
        "hard_risk": hard_risk,
        "business_ok": business_ok,
        "valuation_ok": valuation_ok,
        "buy_ok": buy_ok,
        "data_ok": data_ok,
        "purchase_state": purchase_state,
        "eligible_for_purchase": purchase_state == "BUYABLE",
    }


def summarize_mandate_fit(
    sleeve: str,
    mandate_fit_score: float,
    data_quality_flag: str,
) -> str:
    if data_quality_flag != "OK":
        return "REVIEW"
    if sleeve == "CASH":
        return "CASH_RESERVE"
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


def build_scores_with_audit(
    positions_rows: list[dict[str, str]],
    fundamentals_rows: list[dict[str, str]],
    rules_path: str = DEFAULT_RULES_PATH,
    scoring_path: str = DEFAULT_SCORING_PATH,
    fundamentals_source_name: str = "fundamentals input",
    fundamentals_format: str = "auto",
    fundamentals_score_rules_path: str = DEFAULT_FUNDAMENTALS_SCORE_RULES_PATH,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    scoring_config = load_yaml_config(scoring_path)
    rules = load_portfolio_rules(rules_path)
    enriched_fundamentals_rows, _ = enrich_fundamentals_rows(
        fundamentals_rows,
        fundamentals_format,
        fundamentals_score_rules_path,
        source_name=fundamentals_source_name,
    )
    fundamentals_rows = enriched_fundamentals_rows
    fundamentals_index = build_fundamentals_index(fundamentals_rows, fundamentals_source_name)
    fundamentals_isin_index = build_fundamentals_isin_index(fundamentals_rows)
    fundamentals_name_index = build_fundamentals_name_index(fundamentals_rows)
    position_index = build_position_index(positions_rows, fundamentals_isin_index, fundamentals_name_index)
    total_assets = sum(to_float(row.get("market_value_eur")) for row in positions_rows) or 1.0
    position_weights = {
        ticker: round2(to_float(row.get("market_value_eur")) / total_assets)
        for ticker, row in position_index.items()
    }
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
            scoring_config,
        )
        buy_score_contributions = compute_buy_score_contributions(
            business_score,
            valuation_score,
            expected_return_score,
            drawdown_score,
            portfolio_fit_score,
            scoring_config,
        )
        has_hard_risk_flag = to_bool(row.get("has_hard_risk_flag"))
        thesis_robustness = str(row.get("thesis_robustness", "REVIEW")).strip().upper()
        data_quality_flag = str(valuation_metrics["data_quality_flag"]).upper()
        if ticker in position_index and ticker not in fundamentals_index:
            data_quality_flag = "MISSING_DATA"
            valuation_metrics["valuation_comment"] = "Fundamentaldaten fuer die gehaltene Position fehlen; manuelle Pruefung erforderlich."
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
        mandate_fit_score = round2(to_float(row.get("mandate_fit_score"), 50.0))
        purchase_readiness = evaluate_purchase_readiness(
            {
                "business_score": business_score,
                "valuation_score": valuation_score,
                "buy_score": buy_score,
                "classification": classification,
                "data_quality_flag": data_quality_flag,
                "has_hard_risk_flag": has_hard_risk_flag,
            },
            rules,
        )["purchase_state"]
        results.append(
            {
                "ticker": ticker,
                "isin": row.get("isin", held_position.get("isin", "") if held_position else ""),
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
                "mandate_fit_score": mandate_fit_score,
                "mandate_fit": summarize_mandate_fit(str(row.get("sleeve", "SINGLE_STOCK")).upper(), mandate_fit_score, data_quality_flag),
                "thesis_summary": row.get("thesis_summary", ""),
                "main_risks": row.get("main_risks", ""),
                "data_quality_flag": data_quality_flag,
                "has_hard_risk_flag": has_hard_risk_flag,
                "purchase_readiness": purchase_readiness,
                "buy_score": buy_score,
                **buy_score_contributions,
                "pe_relative_ratio": valuation_metrics["pe_relative_ratio"],
                "ev_ebit_relative_ratio": valuation_metrics["ev_ebit_relative_ratio"],
                "fcf_yield_relative_ratio": valuation_metrics["fcf_yield_relative_ratio"],
                "normalized_fcf_gap": valuation_metrics["normalized_fcf_gap"],
                "dividend_yield_relative_ratio": valuation_metrics["dividend_yield_relative_ratio"],
                "fundamentals_input_format": row.get("fundamentals_input_format", "legacy"),
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
    return results, fundamentals_rows, build_score_audit_rows(results, fundamentals_rows)


def build_scores(
    positions_rows: list[dict[str, str]],
    fundamentals_rows: list[dict[str, str]],
    rules_path: str = DEFAULT_RULES_PATH,
    scoring_path: str = DEFAULT_SCORING_PATH,
    fundamentals_source_name: str = "fundamentals input",
    fundamentals_format: str = "auto",
    fundamentals_score_rules_path: str = DEFAULT_FUNDAMENTALS_SCORE_RULES_PATH,
) -> list[dict[str, Any]]:
    results, _, _ = build_scores_with_audit(
        positions_rows,
        fundamentals_rows,
        rules_path,
        scoring_path,
        fundamentals_source_name,
        fundamentals_format,
        fundamentals_score_rules_path,
    )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build company-level quality and valuation scores.")
    parser.add_argument("--positions", required=True, help="Normalized positions snapshot CSV.")
    parser.add_argument("--fundamentals", required=True, help="Fundamentals and valuation CSV.")
    parser.add_argument("--output", required=True, help="Output scores CSV.")
    parser.add_argument("--audit-output", help="Optional transparent score audit CSV output.")
    parser.add_argument("--enriched-output", help="Optional enriched fundamentals CSV output.")
    parser.add_argument("--fundamentals-format", choices=["auto", "raw", "legacy"], default="auto", help="Fundamentals input format.")
    parser.add_argument("--rules", default=DEFAULT_RULES_PATH, help="Portfolio rules config path.")
    parser.add_argument("--scoring-config", default=DEFAULT_SCORING_PATH, help="Scoring config path.")
    parser.add_argument("--fundamentals-score-rules", default=DEFAULT_FUNDAMENTALS_SCORE_RULES_PATH, help="Raw KPI scoring rules config path.")
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
    results, enriched_rows, audit_rows = build_scores_with_audit(
        positions_rows,
        fundamentals_rows,
        args.rules,
        args.scoring_config,
        f"fundamentals CSV ({args.fundamentals})",
        args.fundamentals_format,
        args.fundamentals_score_rules,
    )
    write_csv_rows(args.output, OUTPUT_FIELDS, results)
    if args.enriched_output:
        write_csv_rows(args.enriched_output, ENRICHED_OUTPUT_FIELDS, enriched_rows)
    if args.audit_output:
        write_csv_rows(args.audit_output, SCORE_AUDIT_FIELDS, audit_rows)


if __name__ == "__main__":
    main()
