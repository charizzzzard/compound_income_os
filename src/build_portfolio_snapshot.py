from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.common import ensure_parent_dir, format_eur, format_pct, read_csv_rows, require_columns, require_unique_tickers, resolve_repo_path, to_bool, to_float, write_csv_rows
from src.portfolio_rules import (
    allocation_summary,
    compute_cash_value,
    compute_portfolio_value,
    compute_top10_weights,
    compute_total_assets,
    find_rule_violations,
    load_portfolio_rules,
)
from src.portfolio_review import HOLDINGS_ACTION_FIELDS, build_holdings_action_table

COVERAGE_REQUIRED_COLUMNS = [
    "holding_name",
    "ticker",
    "match_status",
    "match_method",
    "missing_required_kpis",
    "needs_research_flag",
]


def coverage_status_counts(coverage_rows: list[dict[str, str]]) -> dict[str, int]:
    counts = {"COVERED": 0, "PARTIAL": 0, "REVIEW": 0, "NO_MATCH": 0}
    for row in coverage_rows:
        status = str(row.get("match_status", "")).upper()
        if status in counts:
            counts[status] += 1
    return counts


def coverage_label(row: dict[str, str]) -> str:
    return row.get("ticker") or row.get("matched_ticker") or row.get("isin") or row.get("holding_name") or "UNKNOWN"


def read_coverage_rows(path_value: str) -> list[dict[str, str]]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [column for column in COVERAGE_REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"coverage CSV ({path_value}) missing required columns: {missing_text}")
        return list(reader)


def build_portfolio_snapshot_report(
    positions_rows: list[dict[str, str]],
    output_path: str,
    scores_rows: list[dict[str, str]] | None = None,
    rules_path: str = "configs/portfolio_rules.yaml",
    holdings_output: str | None = None,
    coverage_rows: list[dict[str, str]] | None = None,
) -> Path:
    rules = load_portfolio_rules(rules_path)
    total_assets = compute_total_assets(positions_rows)
    portfolio_value = compute_portfolio_value(positions_rows)
    cash_value = compute_cash_value(positions_rows)
    cash_quote = (cash_value / total_assets) * 100.0 if total_assets else 0.0
    allocation = allocation_summary(positions_rows)
    top10 = compute_top10_weights(positions_rows)
    violations = find_rule_violations(positions_rows, rules)
    action_rows = build_holdings_action_table(positions_rows, scores_rows or [], rules_path) if scores_rows is not None else []
    if holdings_output and action_rows:
        write_csv_rows(holdings_output, HOLDINGS_ACTION_FIELDS, action_rows)

    mandate_notes = []
    if allocation["core_etf_weight"] < rules["target_core_etf_min"]:
        mandate_notes.append("Die Core-ETF-Quote ist materiell untergewichtet.")
    if allocation["cash_weight"] > rules["target_cash_max"]:
        mandate_notes.append("Die Cash-Quote liegt ueber dem Zielkorridor und sollte nur bei fehlenden Opportunitaeten hoch bleiben.")
    if any(str(row.get("classification", "")).upper() in {"REDUCE", "EXIT_REVIEW"} for row in (scores_rows or [])):
        mandate_notes.append("Es gibt problematische Bestandspositionen mit Review-Bedarf.")
    if not mandate_notes:
        mandate_notes.append("Die aktuelle Allokation passt im Wesentlichen zum Mandat.")

    lines = [
        "# Portfolio-Ueberblick",
        "",
        "## Uebersicht",
        "",
        f"- Gesamtvermoegen: {format_eur(total_assets)}",
        f"- Portfoliowert: {format_eur(portfolio_value)}",
        f"- Cash: {format_eur(cash_value)}",
        f"- Cash-Quote: {format_pct(cash_quote)}",
        f"- Anzahl Positionen inkl. Cash: {len(positions_rows)}",
        f"- Benchmark-Referenz: {rules['benchmark_name']}",
        "",
        "## Positionen",
        "",
        "| Ticker | Name | Sleeve | Marktwert | Gewicht gesamt |",
        "| --- | --- | --- | ---: | ---: |",
    ]

    sorted_rows = sorted(positions_rows, key=lambda row: to_float(row.get("market_value_eur")), reverse=True)
    for row in sorted_rows:
        lines.append(
            f"| {row['ticker']} | {row['company_name']} | {row['sleeve']} | {row['market_value_eur']} | {row['weight_total_assets_pct']}% |"
        )

    strongest_positions = [row for row in sorted_rows if str(row.get("asset_type", "")).upper() != "CASH"][:5]
    lines.extend(
        [
            "",
            "## Staerkste Positionen",
            "",
        ]
    )
    if strongest_positions:
        for row in strongest_positions:
            lines.append(
                f"- `{row['ticker']}`: {format_eur(to_float(row.get('market_value_eur')))} bei {row.get('weight_total_assets_pct')}% Gesamtgewicht"
            )
    else:
        lines.append("- Keine investierten Titel vorhanden.")

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

    if action_rows:
        action_groups = {
            "ADD": [row for row in action_rows if row["portfolio_action"] == "ADD"],
            "HOLD": [row for row in action_rows if row["portfolio_action"] == "HOLD"],
            "WATCH": [row for row in action_rows if row["portfolio_action"] == "WATCH"],
            "REDUCE": [row for row in action_rows if row["portfolio_action"] == "REDUCE"],
            "EXIT_REVIEW": [row for row in action_rows if row["portfolio_action"] == "EXIT_REVIEW"],
        }
        mandate_ok_rows = [row for row in action_rows if row["portfolio_action"] in {"ADD", "HOLD"}]
        review_rows = [
            row for row in action_rows if str(row.get("data_quality_flag", "OK")).upper() != "OK" or str(row.get("review_flag")).lower() == "true"
        ]
        lines.extend(
            [
                "",
                "## Operatives Bestandsrating",
                "",
                "- Regelbasis: ADD nur bei mandatkonformen, kaufbaren und nicht uebergewichteten Bestandspositionen.",
                "- HOLD fuer mandatkonforme Titel ohne akuten Ausbau- oder Reduktionsbedarf.",
                "- WATCH fuer haltbare Positionen ohne klare Kauf- oder Exit-Entscheidung.",
                "- REDUCE bei Uebergewichtung oder klarer struktureller Ueberdehnung.",
                "- EXIT_REVIEW bei schwachem Mandats-Fit, NON_CORE-Charakter oder kritischer Datenlage.",
                "",
                f"- Titel mit ACTION=ADD: {len(action_groups['ADD'])}",
                f"- Titel mit ACTION=HOLD: {len(action_groups['HOLD'])}",
                f"- Titel mit ACTION=WATCH: {len(action_groups['WATCH'])}",
                f"- Titel mit ACTION=REDUCE: {len(action_groups['REDUCE'])}",
                f"- Titel mit ACTION=EXIT_REVIEW: {len(action_groups['EXIT_REVIEW'])}",
            ]
        )

        lines.extend(["", "## Mandatkonforme Titel", ""])
        if mandate_ok_rows:
            for row in mandate_ok_rows[:10]:
                lines.append(
                    f"- `{row['ticker']}`: ACTION={row['portfolio_action']} Mandats-Fit={row['mandate_fit']} Buy-Score={row['buy_score']}"
                )
        else:
            lines.append("- Keine klar mandatkonformen Bestandspositionen identifiziert.")

        for section_title, action_key in [
            ("## Positionen mit ACTION=ADD", "ADD"),
            ("## Positionen mit ACTION=REDUCE", "REDUCE"),
            ("## Positionen mit ACTION=EXIT_REVIEW", "EXIT_REVIEW"),
            ("## Positionen mit ACTION=WATCH", "WATCH"),
        ]:
            lines.extend(["", section_title, ""])
            if action_groups[action_key]:
                for row in action_groups[action_key]:
                    lines.append(
                        f"- `{row['ticker']}`: {row['portfolio_action_reason']} Gewicht={row['current_weight']}% Datenqualitaet={row['data_quality_flag']}"
                    )
            else:
                lines.append(f"- Keine Positionen mit ACTION={action_key}.")

        lines.extend(["", "## Datenluecken und Review-Faelle", ""])
        if review_rows:
            for row in review_rows:
                lines.append(
                    f"- `{row['ticker']}`: Datenqualitaet={row['data_quality_flag']} Review-Flag={row['review_flag']} Aktion={row['portfolio_action']}"
                )
        else:
            lines.append("- Keine Positionen mit offenen MISSING_DATA/REVIEW-Faellen.")

    if coverage_rows is not None:
        counts = coverage_status_counts(coverage_rows)
        research_rows = [row for row in coverage_rows if to_bool(row.get("needs_research_flag"))]
        missing_kpi_rows = [row for row in coverage_rows if str(row.get("missing_required_kpis", "")).strip()]
        lines.extend(
            [
                "",
                "## Fundamentals-Abdeckung",
                "",
                f"- COVERED: {counts['COVERED']}",
                f"- PARTIAL: {counts['PARTIAL']}",
                f"- REVIEW: {counts['REVIEW']}",
                f"- NO_MATCH: {counts['NO_MATCH']}",
                f"- Holdings mit Fundamentals-Research-Bedarf: {len(research_rows)}",
                f"- Holdings mit Pflicht-KPI-Luecken: {len(missing_kpi_rows)}",
                "",
                "## Fundamentals-Research-Luecken",
                "",
            ]
        )
        if research_rows:
            for row in research_rows:
                missing = str(row.get("missing_required_kpis", "")).strip() or "keine"
                lines.append(
                    f"- `{coverage_label(row)}` {row.get('holding_name', '')}: status={row.get('match_status')} "
                    f"method={row.get('match_method')} missing_required={missing}"
                )
        else:
            lines.append("- Keine offenen Fundamentals-Research-Luecken.")

    path = ensure_parent_dir(output_path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build markdown portfolio snapshot report.")
    parser.add_argument("--positions", required=True, help="Positions snapshot CSV.")
    parser.add_argument("--output", required=True, help="Markdown output path.")
    parser.add_argument("--scores", help="Optional company scores CSV for mandate fit commentary.")
    parser.add_argument("--coverage", help="Optional personal fundamentals coverage CSV.")
    parser.add_argument("--rules", default="configs/portfolio_rules.yaml", help="Portfolio rules config path.")
    parser.add_argument("--holdings-output", help="Optional CSV output for holdings action table.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    positions_rows = read_csv_rows(args.positions)
    scores_rows = read_csv_rows(args.scores) if args.scores else None
    coverage_rows = read_coverage_rows(args.coverage) if args.coverage else None
    require_columns(
        positions_rows,
        ["ticker", "company_name", "sleeve", "market_value_eur", "weight_total_assets_pct"],
        f"positions CSV ({args.positions})",
    )
    if scores_rows:
        require_columns(scores_rows, ["ticker"], f"scores CSV ({args.scores})")
        require_unique_tickers(scores_rows, f"scores CSV ({args.scores})")
    build_portfolio_snapshot_report(positions_rows, args.output, scores_rows, args.rules, args.holdings_output, coverage_rows)


if __name__ == "__main__":
    main()
