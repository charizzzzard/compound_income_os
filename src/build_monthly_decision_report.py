from __future__ import annotations

import argparse
from pathlib import Path

from src.common import ensure_parent_dir, read_csv_rows, require_columns, round2, to_float
from src.portfolio_rules import load_portfolio_rules


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
        f"- monthly_new_cash_eur: {monthly_cash}",
        f"- min_cash_reserve_eur: {rules['min_cash_reserve_eur']}",
            f"- allow_hold_cash_if_no_opportunity: {rules['allow_hold_cash_if_no_opportunity']}",
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
    parser.add_argument("--rules", default="configs/portfolio_rules.yaml", help="Portfolio rules config path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    positions_rows = read_csv_rows(args.positions)
    score_rows = read_csv_rows(args.scores)
    ranking_rows = read_csv_rows(args.ranking)
    require_columns(
        score_rows,
        ["ticker", "classification", "data_quality_flag", "held_in_portfolio", "main_risks"],
        f"scores CSV ({args.scores})",
    )
    require_columns(
        ranking_rows,
        ["rank", "ticker", "target_action", "suggested_buy_amount_eur", "rationale", "constraint_checks"],
        f"ranking CSV ({args.ranking})",
    )
    build_monthly_decision_report(positions_rows, score_rows, ranking_rows, args.output, args.rules)


if __name__ == "__main__":
    main()
