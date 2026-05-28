from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, ensure_parent_dir, load_yaml_config, read_csv_rows, require_columns, require_unique_tickers, round2, to_float, write_csv_rows
from src.operator_surface_wording import margin_of_safety_evidence, operator_boundary_note, valuation_evidence_note
from src.portfolio_rules import load_portfolio_rules
from src.scoring_engine import DEFAULT_RULES_PATH, evaluate_purchase_readiness

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


def score_index(rows: list[dict[str, str]], source_name: str = "score input") -> dict[str, dict[str, str]]:
    require_unique_tickers(rows, source_name)
    return {
        canonicalize_ticker(row.get("ticker", "")): {**row, "ticker": canonicalize_ticker(row.get("ticker", ""))}
        for row in rows
        if canonicalize_ticker(row.get("ticker", ""))
    }


def determine_status(score_row: dict[str, str], watchlist_row: dict[str, str], rules: dict[str, Any]) -> str:
    sleeve = str(watchlist_row.get("sleeve") or score_row.get("sleeve") or "SINGLE_STOCK").upper()
    purchase_readiness = evaluate_purchase_readiness(score_row, rules)
    purchase_state = str(purchase_readiness["purchase_state"])

    if purchase_state == "BLOCKED":
        return "REJECT"
    if purchase_state == "REVIEW":
        return "REVIEW"
    if purchase_state == "TOO_EXPENSIVE":
        return "TOO_EXPENSIVE"
    if purchase_state == "BUYABLE":
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
    rules_path: str = DEFAULT_RULES_PATH,
    score_source_name: str = "scores input",
    watchlist_source_name: str = "watchlist input",
) -> list[dict[str, Any]]:
    config = load_yaml_config(config_path)
    rules = load_portfolio_rules(rules_path)
    require_unique_tickers(watchlist_rows, watchlist_source_name)
    scores = score_index(score_rows, score_source_name)
    status_priority = {status: index for index, status in enumerate(config["status_priority"])}
    ranked: list[dict[str, Any]] = []

    for row in watchlist_rows:
        ticker = canonicalize_ticker(row.get("ticker", ""))
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
                    "mandate_fit": f"Fundamentaldaten fehlen ({row.get('mandate_fit', '')})",
                    "business_score": 0.0,
                    "valuation_score": 0.0,
                    "buy_score": 0.0,
                    "fair_value_estimate": 0.0,
                    "margin_of_safety_pct": 0.0,
                    "status": "REVIEW",
                    "valuation_comment": "Kein Score-Datensatz vorhanden.",
                    "mandate_fit_comment": "Fundamentaldaten fehlen; Review erforderlich.",
                    "thesis_summary": row.get("thesis_summary", ""),
                    "main_risks": row.get("main_risks", ""),
                    "data_quality_flag": "MISSING_DATA",
                }
            )
            continue

        status = determine_status(score_row, row, rules)
        mandate_fit_score = round2(to_float(score_row.get("mandate_fit_score", row.get("mandate_fit", 0.0))))
        fit_summary = str(row.get("thesis_summary") or score_row.get("thesis_summary") or "").strip()
        mandate_fit_comment = f"Mandats-Fit {mandate_fit_score}/100."
        if fit_summary:
            mandate_fit_comment = f"{fit_summary}. {mandate_fit_comment}"
        ranked.append(
            {
                "ticker": ticker,
                "company_name": row.get("company_name") or score_row.get("company_name", ticker),
                "sector": row.get("sector") or score_row.get("sector", "Unknown"),
                "country": row.get("country") or score_row.get("country", "Unknown"),
                "asset_type": row.get("asset_type") or score_row.get("asset_type", "STOCK"),
                "sleeve": row.get("sleeve") or score_row.get("sleeve", "SINGLE_STOCK"),
                "mandate_fit": f"Hoch ({mandate_fit_score}/100)" if mandate_fit_score >= 80.0 else f"Mittel ({mandate_fit_score}/100)",
                "business_score": round2(to_float(score_row.get("business_score"))),
                "valuation_score": round2(to_float(score_row.get("valuation_score"))),
                "buy_score": round2(to_float(score_row.get("buy_score"))),
                "fair_value_estimate": round2(to_float(score_row.get("fair_value_estimate"))),
                "margin_of_safety_pct": round2(to_float(score_row.get("margin_of_safety_pct"))),
                "status": status,
                "valuation_comment": score_row.get("valuation_comment", ""),
                "mandate_fit_comment": mandate_fit_comment,
                "thesis_summary": row.get("thesis_summary") or score_row.get("thesis_summary", ""),
                "main_risks": row.get("main_risks") or score_row.get("main_risks", ""),
                "data_quality_flag": score_row.get("data_quality_flag", "OK"),
            }
        )

    ranked.sort(
        key=lambda item: (
            status_priority.get(str(item["status"]), 99),
            -to_float(item["buy_score"]),
            -to_float(item["margin_of_safety_pct"]),
            -to_float(item["business_score"]),
            str(item["ticker"]),
        )
    )
    return ranked


def build_watchlist_report(rows: list[dict[str, Any]], output_path: str) -> Path:
    report_lines = [
        "# Watchlist-Bericht",
        "",
        f"- {operator_boundary_note()}",
        "",
        "## Top Zielkandidaten",
        "",
        "| Ticker | Status | Buy Score | Bewertung | Indicative margin field | Mandats-Fit |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows[:8]:
        report_lines.append(
            f"| {row['ticker']} | {row['status']} | {row['buy_score']} | {row['valuation_score']} | {row['margin_of_safety_pct']}% | {row['mandate_fit']} |"
        )

    report_lines.extend(
        [
            "",
            "## Valuation Evidence Notes",
            "",
        ]
    )
    for row in rows[:5]:
        report_lines.append(
            f"- `{row['ticker']}`: {valuation_evidence_note(row.get('valuation_comment'))} {margin_of_safety_evidence(row.get('margin_of_safety_pct'))}. {row['mandate_fit_comment']}"
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
                f"- `{row['ticker']}`: Status={row['status']} Datenqualitaet={row['data_quality_flag']} Risiken={row['main_risks']}"
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
    parser.add_argument("--rules", default=DEFAULT_RULES_PATH, help="Portfolio rules config path.")
    parser.add_argument("--report-output", help="Optional Markdown watchlist report path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    watchlist_rows = read_csv_rows(args.input)
    score_rows = read_csv_rows(args.scores)
    require_columns(watchlist_rows, ["ticker"], f"watchlist CSV ({args.input})")
    require_columns(
        score_rows,
        ["ticker", "business_score", "valuation_score", "buy_score", "fair_value_estimate", "margin_of_safety_pct", "data_quality_flag"],
        f"scores CSV ({args.scores})",
    )
    ranked = build_watchlist_ranked(
        watchlist_rows,
        score_rows,
        args.config,
        args.rules,
        f"scores CSV ({args.scores})",
        f"watchlist CSV ({args.input})",
    )
    write_csv_rows(args.output, OUTPUT_FIELDS, ranked)
    if args.report_output:
        build_watchlist_report(ranked, args.report_output)


if __name__ == "__main__":
    main()
