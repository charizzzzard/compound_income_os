from __future__ import annotations

from typing import Any

from src.common import clamp, load_yaml_config, mean, round2, to_float

DEFAULT_SCORING_PATH = "configs/scoring_weights.yaml"


def relative_score(current: float, reference: float, higher_is_better: bool) -> tuple[float, bool]:
    if current <= 0 or reference <= 0:
        return 35.0, False
    ratio = current / reference if higher_is_better else reference / current
    score = 60.0 + ((ratio - 1.0) * 80.0)
    return clamp(score), True


def fair_value_from_ratio(current_price: float, numerator: float, denominator: float) -> tuple[float | None, bool]:
    if current_price <= 0 or numerator <= 0 or denominator <= 0:
        return None, False
    return current_price * (numerator / denominator), True


def safe_ratio(numerator: float, denominator: float) -> float:
    if numerator <= 0.0 or denominator <= 0.0:
        return 0.0
    return round2(numerator / denominator)


def compute_valuation_metrics(
    row: dict[str, Any],
    config_path: str = DEFAULT_SCORING_PATH,
) -> dict[str, Any]:
    config = load_yaml_config(config_path)
    weights = config["fair_value_weights"]
    fallback_score = to_float(config["fallback_scores"]["valuation_component_missing"], 35.0)

    current_price = to_float(row.get("current_price_eur"))

    pe_current = to_float(row.get("pe_current"))
    pe_hist = to_float(row.get("pe_hist"))
    ev_ebit_current = to_float(row.get("ev_ebit_current"))
    ev_ebit_hist = to_float(row.get("ev_ebit_hist"))
    fcf_yield_current = to_float(row.get("fcf_yield_current_pct"))
    fcf_yield_hist = to_float(row.get("fcf_yield_hist_pct"))
    normalized_fcf_yield = to_float(row.get("normalized_fcf_yield_pct"))
    target_fcf_yield = to_float(row.get("target_fcf_yield_pct"))
    dividend_yield_current = to_float(row.get("dividend_yield_current_pct"))
    dividend_yield_hist = to_float(row.get("dividend_yield_hist_pct"))

    pe_score, pe_ok = relative_score(pe_current, pe_hist, False)
    ev_score, ev_ok = relative_score(
        ev_ebit_current,
        ev_ebit_hist,
        False,
    )
    fcf_hist_score, fcf_hist_ok = relative_score(
        fcf_yield_current,
        fcf_yield_hist,
        True,
    )
    hist_scores = [score for score, ok in [(pe_score, pe_ok), (ev_score, ev_ok), (fcf_hist_score, fcf_hist_ok)] if ok]
    historical_multiple_score = round2(mean(hist_scores, fallback_score))

    normalized_fcf_score, normalized_fcf_ok = relative_score(
        normalized_fcf_yield,
        target_fcf_yield,
        True,
    )
    if not normalized_fcf_ok:
        normalized_fcf_score = fallback_score

    dividend_yield_relative_score, dividend_ok = relative_score(
        dividend_yield_current,
        dividend_yield_hist,
        True,
    )
    if not dividend_ok:
        dividend_yield_relative_score = fallback_score

    fair_value_score = round2(
        (weights["historical_multiple_score"] * historical_multiple_score)
        + (weights["normalized_fcf_score"] * normalized_fcf_score)
        + (weights["dividend_yield_relative_score"] * dividend_yield_relative_score)
    )

    pe_fair_value, _ = fair_value_from_ratio(current_price, pe_hist, pe_current)
    ev_fair_value, _ = fair_value_from_ratio(
        current_price,
        ev_ebit_hist,
        ev_ebit_current,
    )
    fcf_hist_fair_value, _ = fair_value_from_ratio(
        current_price,
        fcf_yield_current,
        fcf_yield_hist,
    )
    normalized_fcf_fair_value, _ = fair_value_from_ratio(
        current_price,
        normalized_fcf_yield,
        target_fcf_yield,
    )
    dividend_fair_value, _ = fair_value_from_ratio(
        current_price,
        dividend_yield_current,
        dividend_yield_hist,
    )

    historical_fair_values = [value for value in [pe_fair_value, ev_fair_value, fcf_hist_fair_value] if value is not None]
    historical_fair_value = mean(historical_fair_values, current_price) if historical_fair_values else current_price
    dividend_component = dividend_fair_value if dividend_fair_value is not None else current_price
    fair_value_estimate = round2(
        (weights["historical_multiple_score"] * historical_fair_value)
        + (weights["normalized_fcf_score"] * (normalized_fcf_fair_value or current_price))
        + (weights["dividend_yield_relative_score"] * dividend_component)
    )
    margin_of_safety_pct = round2(((fair_value_estimate / current_price) - 1.0) * 100.0) if current_price > 0 else 0.0

    missing_fields = 0
    for key in [
        "pe_current",
        "pe_hist",
        "ev_ebit_current",
        "ev_ebit_hist",
        "normalized_fcf_yield_pct",
        "target_fcf_yield_pct",
    ]:
        if to_float(row.get(key)) == 0.0:
            missing_fields += 1

    existing_flag = str(row.get("data_quality_flag", "OK")).strip().upper() or "OK"
    if missing_fields >= 3:
        data_quality_flag = "MISSING_DATA"
    elif missing_fields > 0 or existing_flag in {"REVIEW", "MISSING_DATA"}:
        data_quality_flag = existing_flag if existing_flag != "OK" else "REVIEW"
    else:
        data_quality_flag = "OK"

    if data_quality_flag == "MISSING_DATA":
        valuation_comment = "Bewertungsinputs fehlen; Fair Value bleibt konservativ angesetzt."
    elif margin_of_safety_pct >= 10:
        valuation_comment = "Die hybride Fair-Value-Sicht signalisiert Unterbewertung."
    elif margin_of_safety_pct <= -10:
        valuation_comment = "Der Kurs liegt ueber der hybriden Fair-Value-Spanne."
    else:
        valuation_comment = "Der Kurs liegt nahe am geschaetzten Fair Value."

    return {
        "historical_multiple_score": historical_multiple_score,
        "normalized_fcf_score": round2(normalized_fcf_score),
        "dividend_yield_relative_score": round2(dividend_yield_relative_score),
        "fair_value_score": fair_value_score,
        "fair_value_estimate": fair_value_estimate,
        "margin_of_safety_pct": margin_of_safety_pct,
        "valuation_comment": valuation_comment,
        "data_quality_flag": data_quality_flag,
        "pe_relative_ratio": safe_ratio(pe_hist, pe_current),
        "ev_ebit_relative_ratio": safe_ratio(ev_ebit_hist, ev_ebit_current),
        "fcf_yield_relative_ratio": safe_ratio(fcf_yield_current, fcf_yield_hist),
        "normalized_fcf_gap": round2(normalized_fcf_yield - target_fcf_yield),
        "dividend_yield_relative_ratio": safe_ratio(dividend_yield_current, dividend_yield_hist),
    }
