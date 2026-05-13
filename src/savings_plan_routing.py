from __future__ import annotations

import argparse
import csv
import os
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, ensure_parent_dir, load_yaml_config, read_csv_rows, to_float
from src.savings_plan_registry import DEFAULT_INPUT as DEFAULT_REGISTRY_PATH
from src.savings_plan_registry import load_savings_plan_registry, validate_savings_plan_registry

DEFAULT_THRESHOLDS_PATH = "configs/savings_plan_routing_thresholds.yaml"
DEFAULT_RANKING_INPUT = "data/processed/monthly_buy_ranking.csv"
DEFAULT_ROUTING_OUTPUT = "data/processed/savings_plan_routing.csv"
ROUTING_FIELDS = ["ticker", "execution_mode", "execution_mode_reason"]

EXECUTION_MODES = {
    "SAVINGS_PLAN_EXISTING",
    "SAVINGS_PLAN_NEW",
    "SINGLE_ORDER",
    "NO_RECOMMENDATION",
}
REASONS = {
    "eligible_for_existing_plan",
    "eligible_for_new_plan",
    "savings_plan_not_eligible",
    "drawdown_opportunity_gate_passed",
    "candidate_amount_above_min",
    "next_execution_too_far",
    "missing_inputs",
    "not_a_buy_candidate",
    "invalid_candidate",
    "unknown_eligibility",
}
REQUIRED_THRESHOLDS = {
    "drawdown_opportunity_threshold": (0.0, 100.0, float),
    "material_underweight_gap_pct": (0.0, 100.0, float),
    "single_order_min_amount_eur": (0.0, None, float),
    "max_fee_ratio": (0.0, 1.0, float),
    "max_wait_days_for_savings_plan": (0, None, int),
    "buy_gate_business_score": (0.0, 100.0, float),
    "buy_gate_valuation_score": (0.0, 100.0, float),
    "position_weight_cap": (0.0, 1.0, float),
}


def default_report_output() -> str:
    return f"reports/{date.today().isoformat()}/savings_plan_routing_report.md"


def _parse_threshold(value: Any, key: str, minimum: float | int, maximum: float | int | None, parser: type) -> float | int:
    try:
        parsed = parser(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"threshold {key} must be a {parser.__name__}") from exc
    if parsed < minimum:
        raise ValueError(f"threshold {key} must be >= {minimum}")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"threshold {key} must be <= {maximum}")
    return parsed


def load_routing_thresholds(path: str | Path = DEFAULT_THRESHOLDS_PATH) -> dict[str, object]:
    config = load_yaml_config(path)
    if config.get("schema_version") != 1:
        raise ValueError("savings plan routing thresholds require schema_version=1")
    thresholds = config.get("thresholds")
    if not isinstance(thresholds, dict):
        raise ValueError("savings plan routing thresholds require a thresholds object")
    missing = [key for key in REQUIRED_THRESHOLDS if key not in thresholds]
    if missing:
        raise ValueError(f"savings plan routing thresholds missing required key(s): {', '.join(sorted(missing))}")
    normalized: dict[str, object] = {}
    for key, (minimum, maximum, parser) in REQUIRED_THRESHOLDS.items():
        normalized[key] = _parse_threshold(thresholds[key], key, minimum, maximum, parser)
    return normalized


def load_savings_plan_lookup(path: str | Path = DEFAULT_REGISTRY_PATH) -> dict[str, dict[str, str]]:
    rows = load_savings_plan_registry(path)
    normalized, _warnings = validate_savings_plan_registry(rows, str(path))
    lookup: dict[str, dict[str, str]] = {}
    for row in normalized:
        ticker = canonicalize_ticker(row.get("ticker", ""))
        if not ticker:
            continue
        active = str(row.get("active", "")).strip().upper()
        lookup[ticker] = {
            "savings_plan_active": "TRUE" if active == "TRUE" else "FALSE",
            "execution_day_of_month": str(row.get("execution_day_of_month", "")).strip(),
            "frequency": str(row.get("frequency", "")).strip().upper(),
        }
    return lookup


def _explicit_bool(value: Any) -> bool | None:
    text = str(value or "").strip().lower()
    if text in {"true", "yes", "ja", "1"}:
        return True
    if text in {"false", "no", "nein", "0"}:
        return False
    return None


def _optional_float(row: dict[str, str], *field_names: str) -> float | None:
    for field_name in field_names:
        text = str(row.get(field_name, "") or "").strip()
        if not text or text.upper() == "MISSING_DATA":
            continue
        try:
            return to_float(text)
        except (TypeError, ValueError):
            continue
    return None


def _next_execution_days(plan: dict[str, str], run_date: date | None) -> int | None:
    if run_date is None:
        return None
    try:
        execution_day = int(str(plan.get("execution_day_of_month", "")).strip())
    except ValueError:
        return None
    if execution_day < 1 or execution_day > 28:
        return None
    year = run_date.year
    month = run_date.month
    if run_date.day > execution_day:
        month += 1
        if month == 13:
            month = 1
            year += 1
    next_date = date(year, month, execution_day)
    return (next_date - run_date).days


def _direct_or_derived_wait_days(candidate: dict[str, str], plan: dict[str, str], run_date: date | None) -> int | None:
    direct = _optional_float(candidate, "next_savings_plan_execution_days")
    if direct is not None:
        return int(direct)
    if plan.get("savings_plan_active") == "TRUE":
        return _next_execution_days(plan, run_date)
    return None


def _condition_b_passes(candidate: dict[str, str], thresholds: dict[str, object]) -> bool:
    drawdown = _optional_float(candidate, "drawdown_opportunity_score")
    valuation = _optional_float(candidate, "valuation_score")
    business = _optional_float(candidate, "business_score")
    underweight_gap = _optional_float(candidate, "bucket_underweight_gap", "_bucket_underweight_gap")
    position_after_buy = _optional_float(candidate, "position_weight_after_buy", "_position_weight_after_buy")
    if None in {drawdown, valuation, business, underweight_gap, position_after_buy}:
        return False
    return (
        drawdown >= float(thresholds["drawdown_opportunity_threshold"])
        and valuation >= float(thresholds["buy_gate_valuation_score"])
        and business >= float(thresholds["buy_gate_business_score"])
        and underweight_gap >= float(thresholds["material_underweight_gap_pct"])
        and position_after_buy <= float(thresholds["position_weight_cap"])
    )


def _condition_c_passes(candidate: dict[str, str], thresholds: dict[str, object]) -> bool:
    amount = _optional_float(candidate, "candidate_amount_eur", "suggested_buy_amount_eur")
    fee_ratio = _optional_float(candidate, "order_fee_ratio")
    if amount is None or fee_ratio is None:
        return False
    return amount >= float(thresholds["single_order_min_amount_eur"]) and fee_ratio <= float(thresholds["max_fee_ratio"])


def evaluate_execution_mode(
    candidate: dict[str, str],
    savings_plan_lookup: dict[str, dict[str, str]],
    thresholds: dict[str, object],
    run_date: date | None = None,
) -> tuple[str, str]:
    ticker = canonicalize_ticker(candidate.get("ticker", ""))
    if not ticker:
        return "NO_RECOMMENDATION", "invalid_candidate"

    plan = savings_plan_lookup.get(
        ticker,
        {"savings_plan_active": "NO_PLAN", "execution_day_of_month": "", "frequency": ""},
    )
    explicit_eligibility = _explicit_bool(candidate.get("savings_plan_eligible"))
    if explicit_eligibility is False:
        return "SINGLE_ORDER", "savings_plan_not_eligible"
    if _condition_b_passes(candidate, thresholds):
        return "SINGLE_ORDER", "drawdown_opportunity_gate_passed"
    if _condition_c_passes(candidate, thresholds):
        return "SINGLE_ORDER", "candidate_amount_above_min"
    wait_days = _direct_or_derived_wait_days(candidate, plan, run_date)
    if wait_days is not None and wait_days > int(thresholds["max_wait_days_for_savings_plan"]):
        return "SINGLE_ORDER", "next_execution_too_far"

    if plan.get("savings_plan_active") == "TRUE":
        return "SAVINGS_PLAN_EXISTING", "eligible_for_existing_plan"
    if explicit_eligibility is True:
        return "SAVINGS_PLAN_NEW", "eligible_for_new_plan"
    if explicit_eligibility is None:
        return "NO_RECOMMENDATION", "missing_inputs"
    return "NO_RECOMMENDATION", "unknown_eligibility"


def route_candidates(
    rows: list[dict[str, str]],
    savings_plan_lookup: dict[str, dict[str, str]],
    thresholds: dict[str, object],
    buy_action_values: set[str],
    run_date: date | None = None,
) -> list[dict[str, str]]:
    routed: list[dict[str, str]] = []
    normalized_buy_actions = {str(value).strip().upper() for value in buy_action_values}
    for row in rows:
        copied = dict(row)
        action = str(copied.get("target_action", "")).strip().upper()
        if action not in normalized_buy_actions:
            copied["execution_mode"] = ""
            copied["execution_mode_reason"] = "not_a_buy_candidate"
        else:
            mode, reason = evaluate_execution_mode(copied, savings_plan_lookup, thresholds, run_date)
            copied["execution_mode"] = mode
            copied["execution_mode_reason"] = reason
        routed.append(copied)
    return routed


def write_routing_csv(rows: list[dict[str, str]], path: str | Path = DEFAULT_ROUTING_OUTPUT) -> Path:
    output_path = ensure_parent_dir(path)
    temp_path = output_path.with_name(f"{output_path.name}.tmp")
    try:
        with temp_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=ROUTING_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in ROUTING_FIELDS})
        os.replace(temp_path, output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return output_path


def write_routing_report(rows: list[dict[str, str]], path: str | Path | None = None) -> Path:
    output_path = ensure_parent_dir(path or default_report_output())
    counts = Counter(str(row.get("execution_mode", "") or "NON_BUY") for row in rows)
    missing_inputs = sum(1 for row in rows if row.get("execution_mode_reason") == "missing_inputs")
    lines = [
        "# Sparplan-Routing Report",
        "",
        "## Status",
        "",
        f"- Geroutete Zeilen: {len(rows)}",
        f"- Missing-Input-Faelle: {missing_inputs}",
        "",
        "## Execution Modes",
    ]
    for mode in ["SAVINGS_PLAN_EXISTING", "SAVINGS_PLAN_NEW", "SINGLE_ORDER", "NO_RECOMMENDATION", "NON_BUY"]:
        lines.append(f"- {mode}: {counts.get(mode, 0)}")
    lines.extend(
        [
            "",
            "## Methodische Grenzen",
            "",
            "- Diese Ausgabe ist eine read-only Routing-Empfehlung.",
            "- Es werden keine Orders, Broker-Schreibaktionen oder automatischen Ausfuehrungen erzeugt.",
            "- Fehlende Routing-Inputs werden nicht imputiert; sie bleiben als NO_RECOMMENDATION sichtbar.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def parse_run_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def run_savings_plan_routing(
    ranking_input: str = DEFAULT_RANKING_INPUT,
    registry_input: str = DEFAULT_REGISTRY_PATH,
    thresholds_path: str = DEFAULT_THRESHOLDS_PATH,
    routing_output: str = DEFAULT_ROUTING_OUTPUT,
    report_output: str | None = None,
    run_date: date | None = None,
) -> dict[str, Any]:
    rows = read_csv_rows(ranking_input)
    thresholds = load_routing_thresholds(thresholds_path)
    lookup = load_savings_plan_lookup(registry_input)
    routed = route_candidates(rows, lookup, thresholds, {"BUY", "TOP_UP"}, run_date)
    routing_path = write_routing_csv(routed, routing_output)
    report_path = write_routing_report(routed, report_output or default_report_output())
    return {"rows": routed, "routing_path": routing_path, "report_path": report_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route monthly buy candidates to read-only savings plan execution modes.")
    parser.add_argument("--ranking-input", default=DEFAULT_RANKING_INPUT, help="Monthly ranking CSV input.")
    parser.add_argument("--registry-input", default=DEFAULT_REGISTRY_PATH, help="Savings plan registry CSV input.")
    parser.add_argument("--thresholds", default=DEFAULT_THRESHOLDS_PATH, help="Savings plan routing thresholds config.")
    parser.add_argument("--routing-output", default=DEFAULT_ROUTING_OUTPUT, help="Savings plan routing CSV output.")
    parser.add_argument("--report-output", default=default_report_output(), help="Savings plan routing markdown report output.")
    parser.add_argument("--run-date", help="Optional ISO run date for next savings plan execution derivation.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_savings_plan_routing(
        ranking_input=args.ranking_input,
        registry_input=args.registry_input,
        thresholds_path=args.thresholds,
        routing_output=args.routing_output,
        report_output=args.report_output,
        run_date=parse_run_date(args.run_date),
    )


if __name__ == "__main__":
    main()
