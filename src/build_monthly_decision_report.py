from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Mapping

from src.common import ensure_parent_dir, read_csv_rows, require_columns, require_unique_tickers, resolve_repo_path, round2, to_bool, to_float
from src.personal_decision_journal_validation import build_decision_journal_surface_lines, read_decision_journal_surface
from src.portfolio_rules import load_portfolio_rules

COVERAGE_REQUIRED_COLUMNS = [
    "holding_name",
    "ticker",
    "match_status",
    "match_method",
    "missing_required_kpis",
    "needs_research_flag",
]

DECISION_QUALITY_SURFACE_FIELDS = [
    "decision_confidence_level",
    "review_required",
    "evidence_coverage_status",
    "evidence_coverage_pct",
    "data_quality_status",
    "portfolio_health_status",
    "cash_refill_status",
    "rebalance_status",
    "missing_critical_fields",
    "confidence_reason_codes",
    "review_reason_codes",
    "ranking_stability_status",
    "sensitivity_status",
    "scenario_status",
    "tail_risk_status",
]

DECISION_QUALITY_NOT_EVALUATED_FIELDS = [
    "ranking_stability_status",
    "sensitivity_status",
    "scenario_status",
    "tail_risk_status",
    "scenario_robustness_score",
]

DECISION_QUALITY_NON_SCOPE_NOTES = [
    "no broker/order/trading",
    "no score formula change",
    "no portfolio rule change",
    "no silent data enrichment",
    "no simulation/backtesting",
    "no outcome attribution",
    "no runtime LLM decisioning",
    "no tax quantification",
    "no portfolio event ledger",
    "no private raw data",
]


def _display_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ";".join(str(item) for item in value) or "None"
    if value is None:
        return ""
    text = str(value).strip()
    return text or "None"


def read_decision_quality_state(path_value: str | None) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = resolve_repo_path(path_value)
    if not path.exists():
        return None
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        return rows[0] if rows else None
    except (OSError, json.JSONDecodeError, csv.Error):
        return None


def build_decision_quality_surface_lines(
    decision_quality_state: Mapping[str, Any] | None = None,
    *,
    source_path: str | None = None,
    include_heading: bool = True,
) -> list[str]:
    lines: list[str] = []
    if include_heading:
        lines.extend(["## Decision Quality", ""])

    if not decision_quality_state:
        lines.extend(
            [
                "- Decision Quality: `NOT_AVAILABLE`",
                "- Grund: Decision-Quality-State-Artefakt fehlt, ist nicht lesbar oder die Stage ist nicht gelaufen.",
                "- Semantik: `decision_confidence_level` ist Prozess-/Review-Confidence, keine Investment-Confidence, keine Erfolgswahrscheinlichkeit, keine Alpha-Prognose und keine Order-Freigabe.",
            ]
        )
    else:
        if source_path:
            lines.append(f"- Source artifact: `{source_path}`")
        lines.append("- Semantik: `decision_confidence_level` ist Prozess-/Review-Confidence, keine Investment-Confidence, keine Erfolgswahrscheinlichkeit, keine Alpha-Prognose und keine Order-Freigabe.")
        lines.extend(["", "| Field | Value |", "| --- | --- |"])
        for field in DECISION_QUALITY_SURFACE_FIELDS:
            lines.append(f"| `{field}` | `{_display_value(decision_quality_state.get(field))}` |")
        not_evaluated = [
            field
            for field in DECISION_QUALITY_NOT_EVALUATED_FIELDS
            if str(decision_quality_state.get(field, "")).upper() == "NOT_EVALUATED"
        ]
        lines.extend(
            [
                "",
                f"- phase_1_5_not_evaluated_fields: `{';'.join(not_evaluated) or 'None'}`",
            ]
        )

    lines.extend(["", "### Decision Quality Non-Scope", ""])
    lines.extend(f"- {note}" for note in DECISION_QUALITY_NON_SCOPE_NOTES)
    return lines


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


def execution_mode_text(row: dict[str, str]) -> str:
    action = str(row.get("target_action", "")).upper()
    mode = str(row.get("execution_mode", "")).strip()
    if action not in {"BUY", "TOP_UP"} or not mode:
        return ""
    reason = str(row.get("execution_mode_reason", "")).strip()
    if reason:
        return f"Empfohlene Ausfuehrung: {mode} ({reason})"
    return f"Empfohlene Ausfuehrung: {mode}"


def build_portfolio_health_lines(
    cash_refill_rows: list[dict[str, str]] | None = None,
    rebalance_rows: list[dict[str, str]] | None = None,
) -> list[str]:
    lines = [
        "## Portfolio Health",
        "",
        "### Cash-Refill",
        "",
    ]
    if cash_refill_rows:
        row = cash_refill_rows[0]
        lines.extend(
            [
                f"Status: `{row.get('status', '')}`",
                "",
                "| Current cash EUR | Min reserve EUR | Current cash pct | Target cash min pct | Trigger | Data quality |",
                "| ---: | ---: | ---: | ---: | --- | --- |",
                f"| {row.get('current_cash_eur', '')} | {row.get('min_cash_reserve_eur', '')} | {row.get('current_cash_pct', '')} | "
                f"{row.get('target_cash_min_pct', '')} | {row.get('trigger', '')} | {row.get('data_quality_flag', '')} |",
            ]
        )
    else:
        lines.append("Cash-Refill Review: not available")

    lines.extend(["", "### Rebalance", ""])
    if rebalance_rows:
        lines.extend(
            [
                "| Bucket | Current pct | Target min pct | Target max pct | Band status | Recommended action | Reason |",
                "| --- | ---: | ---: | ---: | --- | --- | --- |",
            ]
        )
        for row in rebalance_rows:
            lines.append(
                f"| {row.get('bucket', '')} | {row.get('current_pct', '')} | {row.get('target_min_pct', '')} | "
                f"{row.get('target_max_pct', '')} | {row.get('band_status', '')} | {row.get('recommended_action', '')} | {row.get('reason', '')} |"
            )
    else:
        lines.append("Rebalance Review: not available")
    return lines


def build_monthly_decision_report(
    positions_rows: list[dict[str, str]],
    score_rows: list[dict[str, str]],
    ranking_rows: list[dict[str, str]],
    output_path: str,
    rules_path: str = "configs/portfolio_rules.yaml",
    coverage_rows: list[dict[str, str]] | None = None,
    cash_refill_rows: list[dict[str, str]] | None = None,
    rebalance_rows: list[dict[str, str]] | None = None,
    decision_quality_state: Mapping[str, Any] | None = None,
    decision_quality_source_path: str | None = None,
    decision_journal_validation_rows: list[dict[str, str]] | None = None,
    decision_review_queue_rows: list[dict[str, str]] | None = None,
    decision_journal_validation_source_path: str | None = None,
    decision_review_queue_source_path: str | None = None,
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
    ]
    lines.extend(build_portfolio_health_lines(cash_refill_rows, rebalance_rows))
    lines.extend([""])
    lines.extend(
        build_decision_quality_surface_lines(
            decision_quality_state,
            source_path=decision_quality_source_path,
            include_heading=True,
        )
    )
    lines.extend([""])
    lines.extend(
        build_decision_journal_surface_lines(
            decision_journal_validation_rows,
            decision_review_queue_rows,
            validation_path=decision_journal_validation_source_path,
            queue_path=decision_review_queue_source_path,
            include_heading=True,
        )
    )
    lines.extend(
        [
        "",
        "## Bestes Kauf-Ranking",
        "",
        "| Rank | Ticker | Aktion | Status | Betrag EUR | Kommentar |",
        "| --- | --- | --- | --- | ---: | --- |",
        ]
    )

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
        execution_line = execution_mode_text(row)
        if execution_line:
            lines.append(f"- `{row['ticker']}`: {execution_line}.")

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
    parser.add_argument("--cash-refill-review", help="Optional Cash-Refill Review CSV.")
    parser.add_argument("--rebalance-review", help="Optional Rebalance Review CSV.")
    parser.add_argument("--decision-quality-state", help="Optional Decision Quality State CSV or JSON.")
    parser.add_argument("--decision-journal-validation", help="Optional Decision Journal Validation CSV.")
    parser.add_argument("--decision-review-queue", help="Optional Decision Review Queue CSV.")
    parser.add_argument("--rules", default="configs/portfolio_rules.yaml", help="Portfolio rules config path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    positions_rows = read_csv_rows(args.positions)
    score_rows = read_csv_rows(args.scores)
    ranking_rows = read_csv_rows(args.ranking)
    coverage_rows = read_coverage_rows(args.coverage) if args.coverage else None
    cash_refill_rows = read_csv_rows(args.cash_refill_review) if args.cash_refill_review and resolve_repo_path(args.cash_refill_review).exists() else None
    rebalance_rows = read_csv_rows(args.rebalance_review) if args.rebalance_review and resolve_repo_path(args.rebalance_review).exists() else None
    decision_quality_state = read_decision_quality_state(args.decision_quality_state) if args.decision_quality_state else None
    decision_journal_validation_rows, decision_review_queue_rows = read_decision_journal_surface(args.decision_journal_validation, args.decision_review_queue)
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
    build_monthly_decision_report(
        positions_rows,
        score_rows,
        ranking_rows,
        args.output,
        args.rules,
        coverage_rows,
        cash_refill_rows=cash_refill_rows,
        rebalance_rows=rebalance_rows,
        decision_quality_state=decision_quality_state,
        decision_quality_source_path=args.decision_quality_state,
        decision_journal_validation_rows=decision_journal_validation_rows,
        decision_review_queue_rows=decision_review_queue_rows,
        decision_journal_validation_source_path=args.decision_journal_validation,
        decision_review_queue_source_path=args.decision_review_queue,
    )


if __name__ == "__main__":
    main()
