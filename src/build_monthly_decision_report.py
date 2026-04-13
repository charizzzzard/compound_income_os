from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.common import ensure_parent_dir, read_csv_rows, require_columns, require_unique_tickers, resolve_repo_path, round2, to_bool, to_float
from src.portfolio_rules import load_portfolio_rules

COVERAGE_REQUIRED_COLUMNS = [
    "holding_name",
    "ticker",
    "match_status",
    "match_method",
    "missing_required_kpis",
    "needs_research_flag",
]


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


def prioritized_coverage_gaps(coverage_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    gap_rows = [
        row for row in coverage_rows
        if to_bool(row.get("needs_research_flag"))
        or str(row.get("missing_required_kpis", "")).strip()
        or str(row.get("match_status", "")).upper() in {"REVIEW", "NO_MATCH"}
    ]
    priority = {"REVIEW": 0, "NO_MATCH": 0, "PARTIAL": 1, "COVERED": 2}
    return sorted(
        gap_rows,
        key=lambda row: (
            0 if str(row.get("missing_required_kpis", "")).strip() else 1,
            priority.get(str(row.get("match_status", "")).upper(), 9),
            coverage_label(row),
        ),
    )


def describe_allocation_status(row: dict[str, str]) -> str:
    status = str(row.get("allocation_status", "")).upper()
    if not status:
        if str(row.get("target_action", "")).upper() == "HOLD_CASH":
            status = "SELECTED_THIS_MONTH"
        elif to_float(row.get("suggested_buy_amount_eur")) > 0.0 and str(row.get("target_action", "")).upper() not in {"DO_NOT_BUY", "NO_ACTION"}:
            status = "SELECTED_THIS_MONTH"
        elif str(row.get("target_action", "")).upper() in {"BUY", "TOP_UP"}:
            status = "ELIGIBLE_NOT_FUNDED"
        else:
            status = "NOT_ELIGIBLE"

    labels = {
        "SELECTED_THIS_MONTH": "Diesen Monat ausgewaehlt",
        "ELIGIBLE_NOT_FUNDED": "Kaufbar, aber nicht finanziert",
        "NOT_ELIGIBLE": "Aktuell nicht kaufbar",
    }
    if str(row.get("target_action", "")).upper() == "HOLD_CASH":
        return "Cash halten"
    return labels.get(status, status)


def build_monthly_decision_report(
    positions_rows: list[dict[str, str]],
    score_rows: list[dict[str, str]],
    ranking_rows: list[dict[str, str]],
    output_path: str,
    rules_path: str = "configs/portfolio_rules.yaml",
    coverage_rows: list[dict[str, str]] | None = None,
) -> Path:
    rules = load_portfolio_rules(rules_path)
    monthly_cash = to_float(rules["monthly_new_cash_eur"])
    top_rows = ranking_rows[:5]
    problematic = [
        row for row in score_rows if str(row.get("held_in_portfolio", "")).lower() == "true"
        and str(row.get("classification", "")).upper() in {"REDUCE", "EXIT_REVIEW"}
    ]
    review_rows = [
        row for row in score_rows if str(row.get("data_quality_flag", "OK")).upper() != "OK"
        or str(row.get("classification", "")).upper() in {"EXIT_REVIEW", "REDUCE"}
    ]
    top_pick = ranking_rows[0] if ranking_rows else None

    lines = [
        "# Monatlicher Entscheidungsbericht",
        "",
        "## Konfiguration",
        "",
        f"- Monatlicher Cash-Zufluss: {monthly_cash} EUR",
        f"- Mindest-Cash-Reserve: {rules['min_cash_reserve_eur']} EUR",
        f"- Cash halten ohne Opportunitaet erlaubt: {rules['allow_hold_cash_if_no_opportunity']}",
        "",
        "## Bestes Kauf-Ranking",
        "",
        "| Rank | Ticker | Aktion | Status | Betrag EUR | Kommentar |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]

    for row in top_rows:
        lines.append(
            f"| {row['rank']} | {row['ticker']} | {row['target_action']} | {describe_allocation_status(row)} | {row['suggested_buy_amount_eur']} | {row['rationale']} |"
        )

    lines.extend(
        [
            "",
            f"## Vorschlag fuer die naechsten {round2(monthly_cash)} EUR",
            "",
        ]
    )
    if top_pick:
        if str(top_pick.get("target_action")) == "HOLD_CASH":
            lines.append(
                f"- Cash halten fuer {top_pick['suggested_buy_amount_eur']} EUR: {top_pick['rationale']}"
            )
        elif to_float(top_pick.get("suggested_buy_amount_eur")) <= 0.0:
            lines.append("- Kein kaufbarer Kandidat im aktuellen Lauf. Es wird kein Kauf vorgeschlagen.")
            if rules["allow_hold_cash_if_no_opportunity"]:
                lines.append("- Cash halten bleibt explizit erlaubt, weil kein Kandidat die Kriterien erfuellt.")
            else:
                lines.append("- allow_hold_cash_if_no_opportunity ist deaktiviert; das System erzwingt trotzdem keinen schlechten Kauf.")
        else:
            lines.append(
                f"- {top_pick['ticker']} mit {top_pick['suggested_buy_amount_eur']} EUR ({top_pick['target_action']}): {top_pick['valuation_comment']}"
            )
            lines.append("- Cash halten bleibt explizit erlaubt, falls sich Bewertungen oder Datenqualitaet verschlechtern.")
    else:
        lines.append("- Kein Ranking verfuegbar. Cash halten.")

    lines.extend(
        [
            "",
            "## Warum Kandidaten kaufbar oder nicht kaufbar sind",
            "",
        ]
    )
    for row in top_rows:
        lines.append(
            f"- `{row['ticker']}`: {describe_allocation_status(row)}. {row['constraint_checks']}. {row['valuation_comment']} {row['mandate_fit_comment']}"
        )

    lines.extend(
        [
            "",
            "## Offene REVIEW-Faelle",
            "",
        ]
    )
    if review_rows:
        for row in review_rows[:10]:
            lines.append(
                f"- `{row['ticker']}`: Klassifikation={row['classification']} Datenqualitaet={row['data_quality_flag']} Risiken={row['main_risks']}"
            )
    else:
        lines.append("- Keine offenen REVIEW-Faelle.")

    if coverage_rows is not None:
        coverage_gaps = prioritized_coverage_gaps(coverage_rows)
        lines.extend(
            [
                "",
                "## Offene Fundamentals-Research-Luecken",
                "",
            ]
        )
        if coverage_gaps:
            for row in coverage_gaps:
                missing = str(row.get("missing_required_kpis", "")).strip() or "keine"
                lines.append(
                    f"- `{coverage_label(row)}` {row.get('holding_name', '')}: status={row.get('match_status')} "
                    f"method={row.get('match_method')} missing_required={missing}"
                )
        else:
            lines.append("- Keine offenen Fundamentals-Research-Luecken aus Coverage.")

    lines.extend(
        [
            "",
            "## Problematische Bestandspositionen",
            "",
        ]
    )
    if problematic:
        for row in problematic:
            lines.append(
                f"- `{row['ticker']}`: Aktion={row['classification']} aktuelles_Gewicht={row['current_weight_pct']}% Risiken={row['main_risks']}"
            )
    else:
        lines.append("- Keine Bestandspositionen mit ACTION=REDUCE oder EXIT_REVIEW.")

    path = ensure_parent_dir(output_path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build markdown monthly decision report.")
    parser.add_argument("--positions", required=True, help="Positions snapshot CSV.")
    parser.add_argument("--scores", required=True, help="Company scores CSV.")
    parser.add_argument("--ranking", required=True, help="Monthly ranking CSV.")
    parser.add_argument("--output", required=True, help="Markdown output path.")
    parser.add_argument("--coverage", help="Optional personal fundamentals coverage CSV.")
    parser.add_argument("--rules", default="configs/portfolio_rules.yaml", help="Portfolio rules config path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    positions_rows = read_csv_rows(args.positions)
    score_rows = read_csv_rows(args.scores)
    ranking_rows = read_csv_rows(args.ranking)
    coverage_rows = read_coverage_rows(args.coverage) if args.coverage else None
    require_columns(
        score_rows,
        ["ticker", "classification", "data_quality_flag", "held_in_portfolio", "main_risks"],
        f"scores CSV ({args.scores})",
    )
    require_unique_tickers(score_rows, f"scores CSV ({args.scores})")
    require_columns(
        ranking_rows,
        ["rank", "ticker", "target_action", "suggested_buy_amount_eur", "rationale", "constraint_checks"],
        f"ranking CSV ({args.ranking})",
    )
    require_unique_tickers(ranking_rows, f"ranking CSV ({args.ranking})")
    build_monthly_decision_report(positions_rows, score_rows, ranking_rows, args.output, args.rules, coverage_rows)


if __name__ == "__main__":
    main()
