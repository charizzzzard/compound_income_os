from __future__ import annotations

import argparse
import csv
import math
import os
from pathlib import Path
from typing import Any

from src.cash_refill_review import DEFAULT_THRESHOLDS_PATH, load_health_thresholds
from src.common import ensure_parent_dir, read_csv_rows, round2, to_float
from src.portfolio_rules import classify_sleeve, load_portfolio_rules

DEFAULT_POSITIONS_INPUT = "data/processed/personal_positions_snapshot.csv"
DEFAULT_RULES_PATH = "configs/portfolio_rules.yaml"
DEFAULT_CSV_OUTPUT = "data/processed/personal_rebalance_review.csv"
DEFAULT_REPORT_OUTPUT = "reports/latest/personal_rebalance_review.md"

REBALANCE_BUCKETS = ["CORE_ETF", "DIVIDEND_QUALITY_ETF", "SINGLE_STOCK", "CASH"]

REBALANCE_REVIEW_FIELDS = [
    "review_date",
    "bucket",
    "current_pct",
    "current_eur",
    "target_min_pct",
    "target_max_pct",
    "band_status",
    "drift_pct",
    "tolerance_band_pct",
    "recommended_action",
    "recommended_cash_deployment_eur",
    "estimated_months_to_correct_via_cashflow",
    "reason",
    "data_quality_flag",
]

TARGET_RULE_KEYS = {
    "CORE_ETF": ("target_core_etf_min", "target_core_etf_max"),
    "DIVIDEND_QUALITY_ETF": ("target_dividend_quality_etf_min", "target_dividend_quality_etf_max"),
    "SINGLE_STOCK": ("target_single_stocks_min", "target_single_stocks_max"),
    "CASH": ("target_cash_min", "target_cash_max"),
}


def _review_date(rows: list[dict[str, Any]]) -> str:
    dates = [
        str(row.get(field, "")).strip()
        for row in rows
        for field in ("portfolio_date", "snapshot_date")
        if str(row.get(field, "")).strip()
    ]
    return max(dates) if dates else ""


def _format_number(value: float) -> str:
    rounded = round2(value)
    if float(rounded).is_integer():
        return str(int(rounded))
    return str(rounded)


def _output_bucket(row: dict[str, Any]) -> str:
    sleeve = classify_sleeve(row)
    if sleeve == "NON_CORE":
        return "SINGLE_STOCK"
    if sleeve in REBALANCE_BUCKETS:
        return sleeve
    return "REVIEW"


def _aggregate_by_bucket(positions: list[dict[str, Any]]) -> tuple[dict[str, float], float, float]:
    grouped = {bucket: 0.0 for bucket in REBALANCE_BUCKETS}
    review_value = 0.0
    total = 0.0
    for row in positions:
        value = to_float(row.get("market_value_eur"))
        total += value
        bucket = _output_bucket(row)
        if bucket in grouped:
            grouped[bucket] += value
        else:
            review_value += value
    return {bucket: round2(value) for bucket, value in grouped.items()}, round2(total), round2(review_value)


def evaluate_rebalance(
    positions: list[dict[str, Any]],
    portfolio_rules: dict[str, Any],
    health_thresholds: dict[str, Any],
    monthly_new_cash_eur: float,
) -> list[dict[str, str]]:
    grouped, total_eur, review_value = _aggregate_by_bucket(positions)
    review_date = _review_date(positions)
    thresholds = health_thresholds.get("rebalance_action_thresholds", {})
    tolerance_multiplier = to_float(health_thresholds.get("tolerance_band_multiplier"), 2.0)
    underweight_action_threshold = to_float(thresholds.get("underweight_action_threshold_pct"), 0.02)
    overweight_multiplier = to_float(thresholds.get("overweight_trim_band_multiplier"), tolerance_multiplier)
    rows: list[dict[str, str]] = []

    for bucket in REBALANCE_BUCKETS:
        min_key, max_key = TARGET_RULE_KEYS[bucket]
        current_eur = grouped[bucket]
        current_pct = round2(current_eur / total_eur) if total_eur > 0.0 else 0.0
        data_quality = "OK"
        reason_parts: list[str] = []
        if not positions:
            data_quality = "POSITIONS_MISSING"
            reason_parts.append("POSITIONS_MISSING")
        if review_value > 0.0:
            data_quality = "RULE_GAP"
            reason_parts.append("review_sleeve_excluded")
        if min_key not in portfolio_rules or max_key not in portfolio_rules:
            target_min = 0.0
            target_max = 0.0
            band = 0.0
            band_status = "WITHIN_BAND"
            drift = 0.0
            action = "HOLD"
            cash_deployment = 0.0
            months = ""
            data_quality = "RULE_GAP"
            reason_parts.append("RULE_GAP")
        else:
            target_min = to_float(portfolio_rules.get(min_key))
            target_max = to_float(portfolio_rules.get(max_key))
            band = round2(target_max - target_min)
            cash_deployment = 0.0
            months = ""

            if target_min <= current_pct <= target_max:
                band_status = "WITHIN_BAND"
                drift = 0.0
                action = "HOLD"
                reason_parts.append("within_band")
            elif current_pct < target_min:
                underweight_gap = round2(target_min - current_pct)
                drift = -underweight_gap
                cash_deployment = round2(max(0.0, target_min * total_eur - current_eur))
                if underweight_gap > tolerance_multiplier * band:
                    band_status = "EXTREMELY_UNDERWEIGHT"
                    action = "DEPLOY_NEW_CASH"
                    reason_parts.append("extreme_underweight_deploy_new_cash")
                elif underweight_gap > underweight_action_threshold:
                    band_status = "UNDERWEIGHT"
                    action = "DEPLOY_NEW_CASH"
                    reason_parts.append("underweight_deploy_new_cash")
                else:
                    band_status = "UNDERWEIGHT"
                    action = "HOLD"
                    reason_parts.append("underweight_below_action_threshold")
                if action == "DEPLOY_NEW_CASH" and monthly_new_cash_eur > 0.0 and cash_deployment > 0.0:
                    months = str(int(math.ceil(cash_deployment / monthly_new_cash_eur)))
            else:
                overweight_gap = round2(current_pct - target_max)
                drift = overweight_gap
                if overweight_gap > overweight_multiplier * band:
                    band_status = "EXTREMELY_OVERWEIGHT"
                    action = "TRIM_FOR_REBALANCE_REVIEW"
                    reason_parts.append("qualitative_review_marker")
                else:
                    band_status = "OVERWEIGHT"
                    action = "HOLD"
                    reason_parts.append("deploy_new_cash_first")

        rows.append(
            {
                "review_date": review_date,
                "bucket": bucket,
                "current_pct": _format_number(current_pct),
                "current_eur": _format_number(current_eur),
                "target_min_pct": _format_number(target_min),
                "target_max_pct": _format_number(target_max),
                "band_status": band_status,
                "drift_pct": _format_number(drift),
                "tolerance_band_pct": _format_number(band),
                "recommended_action": action,
                "recommended_cash_deployment_eur": _format_number(cash_deployment),
                "estimated_months_to_correct_via_cashflow": months,
                "reason": ";".join(dict.fromkeys(reason_parts)),
                "data_quality_flag": data_quality,
            }
        )
    return rows


def _atomic_write_rows(path_value: str | Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> Path:
    path = ensure_parent_dir(path_value)
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise
    return path


def write_rebalance_csv(rows: list[dict[str, Any]], path: str | Path) -> Path:
    return _atomic_write_rows(path, REBALANCE_REVIEW_FIELDS, rows)


def build_rebalance_report(rows: list[dict[str, Any]], path: str | Path) -> Path:
    output = ensure_parent_dir(path)
    lines = [
        "# Rebalance Review",
        "",
        "| Bucket | Current pct | Target min | Target max | Status | Action | Reason | Data quality |",
        "| --- | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('bucket', '')} | {row.get('current_pct', '')} | {row.get('target_min_pct', '')} | "
            f"{row.get('target_max_pct', '')} | {row.get('band_status', '')} | {row.get('recommended_action', '')} | "
            f"{row.get('reason', '')} | {row.get('data_quality_flag', '')} |"
        )
    lines.extend(
        [
            "",
            "Read-only review; no order action is generated.",
        ]
    )
    if any(row.get("data_quality_flag") == "POSITIONS_MISSING" for row in rows):
        lines.extend(["", "EMPTY_STATE"])
    if any(row.get("recommended_action") == "TRIM_FOR_REBALANCE_REVIEW" for row in rows):
        lines.extend(["", "Qualitative review marker only; no tax or order amount is calculated."])
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def run_rebalance_review(
    *,
    positions_input: str | Path = DEFAULT_POSITIONS_INPUT,
    rules_input: str | Path = DEFAULT_RULES_PATH,
    thresholds_input: str | Path = DEFAULT_THRESHOLDS_PATH,
    csv_output: str | Path = DEFAULT_CSV_OUTPUT,
    report_output: str | Path = DEFAULT_REPORT_OUTPUT,
) -> dict[str, Any]:
    positions = read_csv_rows(positions_input)
    rules = load_portfolio_rules(str(rules_input))
    thresholds = load_health_thresholds(thresholds_input)
    rows = evaluate_rebalance(positions, rules, thresholds, to_float(rules.get("monthly_new_cash_eur")))
    csv_path = write_rebalance_csv(rows, csv_output)
    report_path = build_rebalance_report(rows, report_output)
    return {"rows": rows, "csv_output": csv_path, "report_output": report_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build read-only Rebalance Review artifacts.")
    parser.add_argument("--positions", default=DEFAULT_POSITIONS_INPUT, help="Positions snapshot CSV input.")
    parser.add_argument("--rules", default=DEFAULT_RULES_PATH, help="Portfolio rules config path.")
    parser.add_argument("--thresholds", default=DEFAULT_THRESHOLDS_PATH, help="Portfolio health thresholds config path.")
    parser.add_argument("--csv-output", default=DEFAULT_CSV_OUTPUT, help="Rebalance Review CSV output.")
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT, help="Rebalance Review markdown report output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_rebalance_review(
        positions_input=args.positions,
        rules_input=args.rules,
        thresholds_input=args.thresholds,
        csv_output=args.csv_output,
        report_output=args.report_output,
    )


if __name__ == "__main__":
    main()
