from __future__ import annotations

import argparse
from pathlib import Path

from src.common import ensure_parent_dir, format_eur, format_pct, read_csv_rows, require_columns
from src.portfolio_rules import (
    allocation_summary,
    compute_cash_value,
    compute_portfolio_value,
    compute_top10_weights,
    compute_total_assets,
    find_rule_violations,
    load_portfolio_rules,
)


def build_portfolio_snapshot_report(
    positions_rows: list[dict[str, str]],
    output_path: str,
    scores_rows: list[dict[str, str]] | None = None,
    rules_path: str = "configs/portfolio_rules.yaml",
) -> Path:
    rules = load_portfolio_rules(rules_path)
    total_assets = compute_total_assets(positions_rows)
    portfolio_value = compute_portfolio_value(positions_rows)
    cash_value = compute_cash_value(positions_rows)
    cash_quote = (cash_value / total_assets) * 100.0 if total_assets else 0.0
    allocation = allocation_summary(positions_rows)
    top10 = compute_top10_weights(positions_rows)
    violations = find_rule_violations(positions_rows, rules)

    mandate_notes = []
    if allocation["core_etf_weight"] < rules["target_core_etf_min"]:
        mandate_notes.append("Core ETF sleeve is materially underweight.")
    if allocation["cash_weight"] > rules["target_cash_max"]:
        mandate_notes.append("Cash is above corridor and should only remain elevated if no attractive ideas exist.")
    if any(str(row.get("classification", "")).upper() in {"REDUCE", "EXIT_REVIEW"} for row in (scores_rows or [])):
        mandate_notes.append("There are problematic legacy holdings requiring review.")
    if not mandate_notes:
        mandate_notes.append("Current allocation broadly matches the mandate.")

    lines = [
        "# Portfolio Snapshot",
        "",
        "## Uebersicht",
        "",
        f"- Gesamtvermoegen: {format_eur(total_assets)}",
        f"- Portfoliowert: {format_eur(portfolio_value)}",
        f"- Cash: {format_eur(cash_value)}",
        f"- Cash-Quote: {format_pct(cash_quote)}",
        f"- Benchmark-Referenz: {rules['benchmark_name']}",
        "",
        "## Positionen",
        "",
        "| Ticker | Name | Sleeve | Marktwert | Gewicht gesamt |",
        "| --- | --- | --- | ---: | ---: |",
    ]

    sorted_rows = sorted(positions_rows, key=lambda row: float(row.get("market_value_eur", 0.0)), reverse=True)
    for row in sorted_rows:
        lines.append(
            f"| {row['ticker']} | {row['company_name']} | {row['sleeve']} | {row['market_value_eur']} | {row['weight_total_assets_pct']}% |"
        )

    lines.extend(
        [
            "",
            "## Korridorabgleich",
            "",
            "| Bucket | Aktuell | Ziel |",
            "| --- | ---: | ---: |",
            f"| Core ETF | {round(allocation['core_etf_weight'] * 100.0, 2)}% | {rules['target_core_etf_min'] * 100:.0f}-{rules['target_core_etf_max'] * 100:.0f}% |",
            f"| Dividend/Quality ETF | {round(allocation['dividend_quality_etf_weight'] * 100.0, 2)}% | {rules['target_dividend_quality_etf_min'] * 100:.0f}-{rules['target_dividend_quality_etf_max'] * 100:.0f}% |",
            f"| Einzelaktien | {round(allocation['single_stocks_weight'] * 100.0, 2)}% | {rules['target_single_stocks_min'] * 100:.0f}-{rules['target_single_stocks_max'] * 100:.0f}% |",
            f"| Cash | {round(allocation['cash_weight'] * 100.0, 2)}% | {rules['target_cash_min'] * 100:.0f}-{rules['target_cash_max'] * 100:.0f}% |",
            "",
            "## Regelpruefung",
            "",
            f"- Top-10-Konzentration auf Total-Assets-Basis: {round(top10['top10_weight_total_assets'] * 100.0, 2)}%",
            f"- Top-10-Konzentration auf Invested-Assets-Basis: {round(top10['top10_weight_invested_assets'] * 100.0, 2)}%",
        ]
    )

    if violations:
        for violation in violations:
            lines.append(f"- {violation}")
    else:
        lines.append("- Keine Regelverletzungen erkannt.")

    lines.extend(
        [
            "",
            "## Erste Mandat-Einschaetzung",
            "",
        ]
    )
    for note in mandate_notes:
        lines.append(f"- {note}")

    path = ensure_parent_dir(output_path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build markdown portfolio snapshot report.")
    parser.add_argument("--positions", required=True, help="Positions snapshot CSV.")
    parser.add_argument("--output", required=True, help="Markdown output path.")
    parser.add_argument("--scores", help="Optional company scores CSV for mandate fit commentary.")
    parser.add_argument("--rules", default="configs/portfolio_rules.yaml", help="Portfolio rules config path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    positions_rows = read_csv_rows(args.positions)
    scores_rows = read_csv_rows(args.scores) if args.scores else None
    require_columns(
        positions_rows,
        ["ticker", "company_name", "sleeve", "market_value_eur", "weight_total_assets_pct"],
        f"positions CSV ({args.positions})",
    )
    build_portfolio_snapshot_report(positions_rows, args.output, scores_rows, args.rules)


if __name__ == "__main__":
    main()
