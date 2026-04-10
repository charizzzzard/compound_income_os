from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, load_yaml_config, read_csv_rows, round2, write_csv_rows

DEFAULT_WATCHLIST_CONFIG = "configs/watchlist.yaml"

OUTPUT_FIELDS = [
    "ticker",
    "company_name",
    "sector",
    "country",
    "asset_type",
    "sleeve",
    "mandate_fit",
    "business_score",
    "valuation_score",
    "buy_score",
    "fair_value_estimate",
    "margin_of_safety_pct",
    "status",
    "valuation_comment",
    "mandate_fit_comment",
    "thesis_summary",
    "main_risks",
    "data_quality_flag",
]


def score_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {str(row.get("ticker", "")).strip(): row for row in rows if str(row.get("ticker", "")).strip()}


def determine_status(score_row: dict[str, str], watchlist_row: dict[str, str]) -> str:
    business_score = float(score_row.get("business_score", 0.0))
    valuation_score = float(score_row.get("valuation_score", 0.0))
    buy_score = float(score_row.get("buy_score", 0.0))
    sleeve = str(watchlist_row.get("sleeve") or score_row.get("sleeve") or "SINGLE_STOCK").upper()
    data_quality_flag = str(score_row.get("data_quality_flag", "OK")).upper()
    classification = str(score_row.get("classification", "WATCHLIST")).upper()

    if classification in {"REJECT", "EXIT_REVIEW"} or business_score < 65.0 or valuation_score < 40.0:
        return "REJECT"
    if data_quality_flag in {"REVIEW", "MISSING_DATA"} and buy_score < 72.0:
        return "REVIEW"
    if business_score >= 75.0 and valuation_score < 60.0:
        return "TOO_EXPENSIVE"
    if business_score >= 75.0 and valuation_score >= 60.0 and buy_score >= 72.0:
        if sleeve == "CORE_ETF":
            return "CORE_CANDIDATE"
        if sleeve == "DIVIDEND_QUALITY_ETF" or str(score_row.get("asset_type", "")).upper() == "ETF":
            return "DG_CANDIDATE"
        return "QUALITY_COMPOUNDER_CANDIDATE"
    return "REVIEW"


def build_watchlist_ranked(
    watchlist_rows: list[dict[str, str]],
    score_rows: list[dict[str, str]],
    config_path: str = DEFAULT_WATCHLIST_CONFIG,
) -> list[dict[str, Any]]:
    config = load_yaml_config(config_path)
    scores = score_index(score_rows)
    status_priority = {status: index for index, status in enumerate(config["status_priority"])}
    ranked: list[dict[str, Any]] = []

    for row in watchlist_rows:
        ticker = str(row.get("ticker", "")).strip()
        score_row = scores.get(ticker)
        if not score_row:
            ranked.append(
                {
                    "ticker": ticker,
                    "company_name": row.get("company_name", ticker),
                    "sector": row.get("sector", "Unknown"),
                    "country": row.get("country", "Unknown"),
                    "asset_type": row.get("asset_type", "STOCK"),
                    "sleeve": row.get("sleeve", "SINGLE_STOCK"),
                    "mandate_fit": f"Needs fundamentals ({row.get('mandate_fit', '')})",
                    "business_score": 0.0,
                    "valuation_score": 0.0,
                    "buy_score": 0.0,
                    "fair_value_estimate": 0.0,
                    "margin_of_safety_pct": 0.0,
                    "status": "REVIEW",
                    "valuation_comment": "Missing score record.",
                    "mandate_fit_comment": "Fundamental data missing; review required.",
                    "thesis_summary": row.get("thesis_summary", ""),
                    "main_risks": row.get("main_risks", ""),
                    "data_quality_flag": "MISSING_DATA",
                }
            )
            continue

        status = determine_status(score_row, row)
        mandate_fit_score = round(float(score_row.get("mandate_fit_score", row.get("mandate_fit", 0.0))), 2)
        ranked.append(
            {
                "ticker": ticker,
                "company_name": row.get("company_name") or score_row.get("company_name", ticker),
                "sector": row.get("sector") or score_row.get("sector", "Unknown"),
                "country": row.get("country") or score_row.get("country", "Unknown"),
                "asset_type": row.get("asset_type") or score_row.get("asset_type", "STOCK"),
                "sleeve": row.get("sleeve") or score_row.get("sleeve", "SINGLE_STOCK"),
                "mandate_fit": f"High ({mandate_fit_score}/100)" if mandate_fit_score >= 80.0 else f"Medium ({mandate_fit_score}/100)",
                "business_score": round(float(score_row.get("business_score", 0.0)), 2),
                "valuation_score": round(float(score_row.get("valuation_score", 0.0)), 2),
                "buy_score": round(float(score_row.get("buy_score", 0.0)), 2),
                "fair_value_estimate": round(float(score_row.get("fair_value_estimate", 0.0)), 2),
                "margin_of_safety_pct": round(float(score_row.get("margin_of_safety_pct", 0.0)), 2),
                "status": status,
                "valuation_comment": score_row.get("valuation_comment", ""),
                "mandate_fit_comment": f"{row.get('thesis_summary', score_row.get('thesis_summary', ''))}; mandate fit {mandate_fit_score}/100.",
                "thesis_summary": row.get("thesis_summary") or score_row.get("thesis_summary", ""),
                "main_risks": row.get("main_risks") or score_row.get("main_risks", ""),
                "data_quality_flag": score_row.get("data_quality_flag", "OK"),
            }
        )

    ranked.sort(
        key=lambda item: (
            status_priority.get(str(item["status"]), 99),
            -float(item["buy_score"]),
            -float(item["margin_of_safety_pct"]),
            -float(item["business_score"]),
            str(item["ticker"]),
        )
    )
    return ranked


def build_watchlist_report(rows: list[dict[str, Any]], output_path: str) -> Path:
    report_lines = [
        "# Watchlist Report",
        "",
        "## Top Zielkandidaten",
        "",
        "| Ticker | Status | Buy Score | Valuation | Margin of Safety | Mandate Fit |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows[:8]:
        report_lines.append(
            f"| {row['ticker']} | {row['status']} | {row['buy_score']} | {row['valuation_score']} | {row['margin_of_safety_pct']}% | {row['mandate_fit']} |"
        )

    report_lines.extend(
        [
            "",
            "## Bewertungskommentare",
            "",
        ]
    )
    for row in rows[:5]:
        report_lines.append(
            f"- `{row['ticker']}`: {row['valuation_comment']} Margin of safety {row['margin_of_safety_pct']}%. {row['mandate_fit_comment']}"
        )

    review_rows = [row for row in rows if row["status"] in {"REVIEW", "REJECT"} or row["data_quality_flag"] != "OK"]
    report_lines.extend(
        [
            "",
            "## Review-Faelle",
            "",
        ]
    )
    if review_rows:
        for row in review_rows:
            report_lines.append(
                f"- `{row['ticker']}`: status={row['status']} data_quality={row['data_quality_flag']} risks={row['main_risks']}"
            )
    else:
        report_lines.append("- Keine offenen Review-Faelle.")

    path = ensure_parent_dir(output_path)
    path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank watchlist candidates against mandate and valuation.")
    parser.add_argument("--input", required=True, help="Watchlist input CSV.")
    parser.add_argument("--scores", required=True, help="Company scores CSV.")
    parser.add_argument("--output", required=True, help="Ranked watchlist CSV.")
    parser.add_argument("--config", default=DEFAULT_WATCHLIST_CONFIG, help="Watchlist config path.")
    parser.add_argument("--report-output", help="Optional Markdown watchlist report path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    watchlist_rows = read_csv_rows(args.input)
    score_rows = read_csv_rows(args.scores)
    ranked = build_watchlist_ranked(watchlist_rows, score_rows, args.config)
    write_csv_rows(args.output, OUTPUT_FIELDS, ranked)
    if args.report_output:
        build_watchlist_report(ranked, args.report_output)


if __name__ == "__main__":
    main()
