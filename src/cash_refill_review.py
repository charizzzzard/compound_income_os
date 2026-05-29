from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, load_yaml_config, read_csv_rows, round2, to_float
from src.portfolio_rules import classify_sleeve, load_portfolio_rules

DEFAULT_POSITIONS_INPUT = "data/processed/personal_positions_snapshot.csv"
DEFAULT_RULES_PATH = "configs/portfolio_rules.yaml"
DEFAULT_THRESHOLDS_PATH = "configs/portfolio_health_thresholds.yaml"
DEFAULT_CSV_OUTPUT = "data/processed/personal_cash_refill_review.csv"
DEFAULT_REPORT_OUTPUT = "reports/latest/personal_cash_refill_review.md"

CASH_REFILL_FIELDS = [
    "review_date",
    "status",
    "trigger",
    "current_cash_eur",
    "min_cash_reserve_eur",
    "current_cash_pct",
    "target_cash_min_pct",
    "gap_to_min_reserve_eur",
    "gap_to_bucket_floor_eur",
    "months_to_floor_at_monthly_inflow",
    "reason",
    "data_quality_flag",
]

STATUS_REQUIRED = "CASH_REFILL_REQUIRED"
STATUS_NOT_REQUIRED = "CASH_REFILL_NOT_REQUIRED"
STATUS_MARGINAL = "CASH_REFILL_MARGINAL"


def load_health_thresholds(path: str | Path = DEFAULT_THRESHOLDS_PATH) -> dict[str, Any]:
    config = dict(load_yaml_config(path))
    if "rebalance_action_thresholds" not in config or not isinstance(config["rebalance_action_thresholds"], dict):
        raise ValueError("portfolio health thresholds missing rebalance_action_thresholds mapping")
    config.setdefault("tolerance_band_multiplier", 2.0)
    config.setdefault("cash_refill_margin_pct", 0.01)
    config.setdefault("months_to_floor_warning_threshold", 3)
    config["rebalance_action_thresholds"].setdefault("underweight_action_threshold_pct", 0.02)
    config["rebalance_action_thresholds"].setdefault("overweight_trim_band_multiplier", 2.0)

    tolerance = to_float(config.get("tolerance_band_multiplier"), -1.0)
    margin = to_float(config.get("cash_refill_margin_pct"), -1.0)
    months = int(to_float(config.get("months_to_floor_warning_threshold"), 0.0))
    if tolerance < 1.0:
        raise ValueError("tolerance_band_multiplier must be >= 1.0")
    if margin < 0.0 or margin > 1.0:
        raise ValueError("cash_refill_margin_pct must be between 0 and 1")
    if months < 1:
        raise ValueError("months_to_floor_warning_threshold must be >= 1")
    return config


def _review_date(rows: list[dict[str, Any]]) -> str:
    dates = [
        str(row.get(field, "")).strip()
        for row in rows
        for field in ("portfolio_date", "snapshot_date")
        if str(row.get(field, "")).strip()
    ]
    return max(dates) if dates else ""


def _sum_market_value(rows: list[dict[str, Any]]) -> float:
    return round2(sum(to_float(row.get("market_value_eur")) for row in rows))


def _format_number(value: float) -> str:
    rounded = round2(value)
    if float(rounded).is_integer():
        return str(int(rounded))
    return str(rounded)


def evaluate_cash_refill(
    positions: list[dict[str, Any]],
    portfolio_rules: dict[str, Any],
    health_thresholds: dict[str, Any],
) -> dict[str, str]:
    total_eur = _sum_market_value(positions)
    cash_rows = [row for row in positions if classify_sleeve(row) == "CASH"]
    current_cash_eur = round2(sum(to_float(row.get("market_value_eur")) for row in cash_rows))
    min_cash_reserve_eur = round2(to_float(portfolio_rules.get("min_cash_reserve_eur")))
    target_cash_min_pct = to_float(portfolio_rules.get("target_cash_min"))
    current_cash_pct = round2(current_cash_eur / total_eur) if total_eur > 0.0 else 0.0
    bucket_floor_eur = round2(target_cash_min_pct * total_eur)
    gap_to_min_reserve_eur = round2(max(0.0, min_cash_reserve_eur - current_cash_eur))
    gap_to_bucket_floor_eur = round2(max(0.0, bucket_floor_eur - current_cash_eur))

    below_min_reserve = current_cash_eur < min_cash_reserve_eur
    below_bucket_floor = current_cash_pct < target_cash_min_pct
    margin_pct = to_float(health_thresholds.get("cash_refill_margin_pct"), 0.01)
    near_reserve = not below_min_reserve and (current_cash_eur - min_cash_reserve_eur) <= round2(margin_pct * total_eur)
    near_floor = not below_bucket_floor and (current_cash_pct - target_cash_min_pct) <= margin_pct

    if below_min_reserve and below_bucket_floor:
        status = STATUS_REQUIRED
        trigger = "BOTH"
    elif below_min_reserve:
        status = STATUS_REQUIRED
        trigger = "BELOW_MIN_RESERVE"
    elif below_bucket_floor:
        status = STATUS_REQUIRED
        trigger = "BELOW_BUCKET_FLOOR"
    elif near_reserve or near_floor:
        status = STATUS_MARGINAL
        trigger = "NEAR_THRESHOLD"
    else:
        status = STATUS_NOT_REQUIRED
        trigger = "NONE"

    if not positions:
        data_quality = "POSITIONS_MISSING"
    elif not cash_rows:
        data_quality = "CASH_SLEEVE_NOT_FOUND"
    else:
        data_quality = "OK"

    reason_parts = [f"trigger={trigger}", f"cash_gap_reserve={gap_to_min_reserve_eur}", f"cash_gap_floor={gap_to_bucket_floor_eur}"]
    if status != STATUS_REQUIRED:
        reason_parts.append("NO_BURN_RATE_AVAILABLE")
    if data_quality != "OK":
        reason_parts.append(data_quality)

    return {
        "review_date": _review_date(positions),
        "status": status,
        "trigger": trigger,
        "current_cash_eur": _format_number(current_cash_eur),
        "min_cash_reserve_eur": _format_number(min_cash_reserve_eur),
        "current_cash_pct": _format_number(current_cash_pct),
        "target_cash_min_pct": _format_number(target_cash_min_pct),
        "gap_to_min_reserve_eur": _format_number(gap_to_min_reserve_eur),
        "gap_to_bucket_floor_eur": _format_number(gap_to_bucket_floor_eur),
        "months_to_floor_at_monthly_inflow": "0" if status == STATUS_REQUIRED else "",
        "reason": ";".join(reason_parts),
        "data_quality_flag": data_quality,
    }


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


def write_cash_refill_csv(record: dict[str, Any], path: str | Path) -> Path:
    return _atomic_write_rows(path, CASH_REFILL_FIELDS, [record])


def build_cash_refill_report(record: dict[str, Any], path: str | Path) -> Path:
    output = ensure_parent_dir(path)
    lines = [
        "# Cash-Refill Review",
        "",
        f"Status: `{record.get('status', '')}`",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Current cash EUR | {record.get('current_cash_eur', '')} |",
        f"| Min cash reserve EUR | {record.get('min_cash_reserve_eur', '')} |",
        f"| Current cash pct | {record.get('current_cash_pct', '')} |",
        f"| Target cash min pct | {record.get('target_cash_min_pct', '')} |",
        f"| Gap to reserve EUR | {record.get('gap_to_min_reserve_eur', '')} |",
        f"| Gap to bucket floor EUR | {record.get('gap_to_bucket_floor_eur', '')} |",
        "",
        f"- Trigger: `{record.get('trigger', '')}`",
        f"- Data quality: `{record.get('data_quality_flag', '')}`",
        f"- Reason: `{record.get('reason', '')}`",
        "",
        "Read-only review; no sell/order action is generated.",
    ]
    if record.get("data_quality_flag") == "POSITIONS_MISSING":
        lines.extend(["", "EMPTY_STATE"])
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def run_cash_refill_review(
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
    record = evaluate_cash_refill(positions, rules, thresholds)
    csv_path = write_cash_refill_csv(record, csv_output)
    report_path = build_cash_refill_report(record, report_output)
    return {"record": record, "csv_output": csv_path, "report_output": report_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build read-only Cash-Refill Review artifacts.")
    parser.add_argument("--positions", default=DEFAULT_POSITIONS_INPUT, help="Positions snapshot CSV input.")
    parser.add_argument("--rules", default=DEFAULT_RULES_PATH, help="Portfolio rules config path.")
    parser.add_argument("--thresholds", default=DEFAULT_THRESHOLDS_PATH, help="Portfolio health thresholds config path.")
    parser.add_argument("--csv-output", default=DEFAULT_CSV_OUTPUT, help="Cash-Refill summary CSV output.")
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT, help="Cash-Refill markdown report output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_cash_refill_review(
        positions_input=args.positions,
        rules_input=args.rules,
        thresholds_input=args.thresholds,
        csv_output=args.csv_output,
        report_output=args.report_output,
    )


if __name__ == "__main__":
    main()
