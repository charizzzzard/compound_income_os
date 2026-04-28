from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, ensure_parent_dir, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_COVERAGE_INPUT = "data/processed/personal_fundamentals_coverage.csv"
DEFAULT_SCORES_INPUT = "data/processed/personal_company_scores.csv"
DEFAULT_MONTHLY_INPUT = "data/processed/personal_monthly_buy_ranking.csv"
DEFAULT_OUTPUT = "data/processed/personal_kpi_tier_coverage.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_kpi_tier_coverage_report.md"

OUTPUT_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "core_quality_data_status",
    "valuation_data_status",
    "dividend_fcf_data_status",
    "advanced_data_status",
    "missing_core_quality_kpis",
    "missing_valuation_kpis",
    "missing_dividend_fcf_kpis",
    "missing_advanced_optional_kpis",
    "resulting_score_data_quality_flag",
    "resulting_monthly_action",
    "recommended_next_action",
]


def optional_rows(path_value: str) -> list[dict[str, str]]:
    path = resolve_repo_path(path_value)
    return read_csv_rows(path) if path.exists() else []


def identity_keys(row: dict[str, Any]) -> list[str]:
    keys = [
        canonicalize_ticker(row.get("ticker", "")),
        canonicalize_ticker(row.get("matched_ticker", "")),
        str(row.get("isin", "") or "").strip().upper(),
        str(row.get("matched_isin", "") or "").strip().upper(),
    ]
    return [key for key in dict.fromkeys(keys) if key]


def build_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        for key in identity_keys(row):
            lookup.setdefault(key, row)
    return lookup


def lookup(row: dict[str, str], lookup_rows: dict[str, dict[str, str]]) -> dict[str, str]:
    for key in identity_keys(row):
        if key in lookup_rows:
            return lookup_rows[key]
    return {}


def recommended_next_action(row: dict[str, str]) -> str:
    profile = safe_upper(row.get("company_type_profile"))
    if profile == "FINANCIAL":
        return "add financial-company KPI profile or keep separate from STANDARD scoring"
    if profile == "OTHER":
        return "keep excluded unless explicit profile model exists"
    if safe_upper(row.get("core_quality_data_status")) == "MISSING":
        return "REVIEW_CORE_DATA"
    if safe_upper(row.get("valuation_data_status")) != "OK":
        return "WAIT_VALUATION"
    if safe_upper(row.get("dividend_fcf_data_status")) == "MISSING":
        return "REVIEW_FCF_DATA"
    if safe_upper(row.get("resulting_score_data_quality_flag")) != "OK":
        return "review remaining score data-quality gate"
    return "OK"


def build_kpi_tier_rows(
    coverage_rows: list[dict[str, str]],
    score_rows: list[dict[str, str]],
    monthly_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    score_lookup = build_lookup(score_rows)
    monthly_lookup = build_lookup(monthly_rows)
    rows: list[dict[str, str]] = []
    for coverage in coverage_rows:
        score = lookup(coverage, score_lookup)
        monthly = lookup(coverage, monthly_lookup)
        row = {
            "ticker": canonicalize_ticker(coverage.get("matched_ticker") or coverage.get("ticker", "")),
            "isin": str(coverage.get("matched_isin") or coverage.get("isin", "") or "").strip().upper(),
            "company_name": coverage.get("matched_company_name") or coverage.get("holding_name", ""),
            "company_type_profile": coverage.get("company_type_profile", ""),
            "core_quality_data_status": score.get("core_quality_data_status") or coverage.get("core_quality_data_status", ""),
            "valuation_data_status": score.get("valuation_data_status") or coverage.get("valuation_data_status", ""),
            "dividend_fcf_data_status": score.get("dividend_fcf_data_status") or coverage.get("dividend_fcf_data_status", ""),
            "advanced_data_status": score.get("advanced_data_status") or coverage.get("advanced_data_status", ""),
            "missing_core_quality_kpis": coverage.get("missing_core_quality_kpis", ""),
            "missing_valuation_kpis": coverage.get("missing_valuation_kpis", ""),
            "missing_dividend_fcf_kpis": coverage.get("missing_dividend_fcf_kpis", ""),
            "missing_advanced_optional_kpis": coverage.get("missing_advanced_optional_kpis", ""),
            "resulting_score_data_quality_flag": score.get("data_quality_flag") or coverage.get("derived_data_quality_flag", ""),
            "resulting_monthly_action": monthly.get("target_action", ""),
            "recommended_next_action": "",
        }
        row["recommended_next_action"] = recommended_next_action(row)
        rows.append(row)
    rows.sort(key=lambda item: (item["recommended_next_action"], item["isin"], item["ticker"]))
    return rows


def write_report(path_value: str, rows: list[dict[str, str]]) -> Path:
    status_counts = Counter(row["recommended_next_action"] for row in rows)
    lines = [
        "# Personal KPI Tier Coverage",
        "",
        "## Summary",
        "",
        f"- holdings_total: {len(rows)}",
    ]
    for key in sorted(status_counts):
        lines.append(f"- {key}: {status_counts[key]}")
    lines.extend(
        [
            "",
            "## Holdings",
            "",
            "| ticker | isin | profile | core | valuation | dividend_fcf | advanced | score_quality | monthly_action | next_action |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['ticker']} | {row['isin']} | {row['company_type_profile']} | {row['core_quality_data_status']} | "
            f"{row['valuation_data_status']} | {row['dividend_fcf_data_status']} | {row['advanced_data_status']} | "
            f"{row['resulting_score_data_quality_flag']} | {row['resulting_monthly_action']} | {row['recommended_next_action']} |"
        )
    path = ensure_parent_dir(path_value)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_kpi_tier_coverage(
    coverage_input: str = DEFAULT_COVERAGE_INPUT,
    scores_input: str = DEFAULT_SCORES_INPUT,
    monthly_input: str = DEFAULT_MONTHLY_INPUT,
    output: str = DEFAULT_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> tuple[Path, Path, list[dict[str, str]]]:
    rows = build_kpi_tier_rows(optional_rows(coverage_input), optional_rows(scores_input), optional_rows(monthly_input))
    output_path = write_csv_rows(output, OUTPUT_FIELDS, rows)
    report_path = write_report(report_output, rows)
    return output_path, report_path, rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build personal KPI tier coverage audit from processed artifacts.")
    parser.add_argument("--coverage-input", default=DEFAULT_COVERAGE_INPUT)
    parser.add_argument("--scores-input", default=DEFAULT_SCORES_INPUT)
    parser.add_argument("--monthly-input", default=DEFAULT_MONTHLY_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_kpi_tier_coverage(args.coverage_input, args.scores_input, args.monthly_input, args.output, args.report_output)


if __name__ == "__main__":
    main()
