from __future__ import annotations

import argparse
import csv
from typing import Any

from src.common import canonicalize_ticker, read_csv_rows, require_columns, require_unique_tickers, resolve_repo_path, round2, safe_upper, to_bool, to_float, write_csv_rows
from src.portfolio_rules import (
    aggregate_positions_by_ticker,
    allocation_summary,
    compute_cash_value,
    compute_sector_weights,
    compute_total_assets,
    load_portfolio_rules,
)
from src.scoring_engine import evaluate_purchase_readiness

DEFAULT_RULES_PATH = "configs/portfolio_rules.yaml"
COVERAGE_REQUIRED_COLUMNS = [
    "ticker",
    "match_status",
    "match_method",
    "missing_required_kpis",
    "needs_research_flag",
]
PURCHASE_STATE_LABELS = {
    "BUYABLE": "KAUFBAR",
    "TOO_EXPENSIVE": "ZU_TEUER",
    "REVIEW": "REVIEW",
    "BLOCKED": "GEBLOCKT",
}

OUTPUT_FIELDS = [
    "rank",
    "ticker",
    "company_name",
    "current_weight",
    "target_action",
    "allocation_status",
    "suggested_buy_amount_eur",
    "rationale",
    "constraint_checks",
    "valuation_comment",
    "mandate_fit_comment",
]

REBALANCE_FIELDS = [
    "ticker",
    "company_name",
    "action",
    "current_weight_pct",
    "reason",
]


def index_by_ticker(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {
        canonicalize_ticker(row.get("ticker", "")): {**row, "ticker": canonicalize_ticker(row.get("ticker", ""))}
        for row in rows
        if canonicalize_ticker(row.get("ticker", ""))
    }


def positions_index_by_ticker(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in aggregate_positions_by_ticker(rows):
        for key in {canonicalize_ticker(row.get("ticker", "")), str(row.get("isin", "")).strip().upper()}:
            if key:
                index[key] = row
    return index


def coverage_identity_keys(row: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for field_name in ("ticker", "matched_ticker"):
        ticker = canonicalize_ticker(row.get(field_name, ""))
        if ticker:
            keys.append(ticker)
    for field_name in ("isin", "matched_isin"):
        isin = str(row.get(field_name, "")).strip().upper()
        if isin:
            keys.append(isin)
    return list(dict.fromkeys(keys))


def build_coverage_index(rows: list[dict[str, Any]] | None, source_name: str = "coverage input") -> dict[str, dict[str, Any]]:
    if not rows:
        return {}
    require_columns(rows, COVERAGE_REQUIRED_COLUMNS, source_name)
    index: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    for row in rows:
        for key in coverage_identity_keys(row):
            if key in index and index[key] is not row:
                duplicates.add(key)
                continue
            index[key] = row
    if duplicates:
        duplicate_text = ", ".join(sorted(duplicates))
        raise ValueError(f"{source_name} contains duplicate identifiers: {duplicate_text}")
    return index


def find_coverage_row(
    position_row: dict[str, str],
    candidate: dict[str, str],
    score_row: dict[str, str],
    coverage_index: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    lookup_keys: list[str] = []
    for row in (score_row, candidate, position_row):
        ticker = canonicalize_ticker(row.get("ticker", ""))
        isin = str(row.get("isin", "")).strip().upper()
        if ticker:
            lookup_keys.append(ticker)
        if isin:
            lookup_keys.append(isin)
    for key in dict.fromkeys(lookup_keys):
        if key in coverage_index:
            return coverage_index[key]
    return None


def coverage_guardrail_applies(coverage_row: dict[str, Any] | None) -> bool:
    if not coverage_row:
        return False
    status = safe_upper(coverage_row.get("match_status"))
    return (
        status in {"REVIEW", "NO_MATCH"}
        or to_bool(coverage_row.get("needs_research_flag"))
        or bool(str(coverage_row.get("missing_required_kpis", "")).strip())
    )


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


def find_position_row(
    positions_index: dict[str, dict[str, str]],
    candidate: dict[str, str],
    score_row: dict[str, str],
) -> dict[str, str]:
    keys = [
        canonicalize_ticker(score_row.get("ticker", "")),
        str(score_row.get("isin", "")).strip().upper(),
        canonicalize_ticker(candidate.get("ticker", "")),
        str(candidate.get("isin", "")).strip().upper(),
    ]
    for key in keys:
        if key and key in positions_index:
            return positions_index[key]
    return {}


def corridor_gap_bonus(sleeve: str, summary: dict[str, float], rules: dict[str, Any]) -> float:
    sleeve = sleeve.upper()
    mapping = {
        "CORE_ETF": ("core_etf_weight", "target_core_etf_min", "target_core_etf_max"),
        "DIVIDEND_QUALITY_ETF": (
            "dividend_quality_etf_weight",
            "target_dividend_quality_etf_min",
            "target_dividend_quality_etf_max",
        ),
        "SINGLE_STOCK": ("single_stocks_weight", "target_single_stocks_min", "target_single_stocks_max"),
        "CASH": ("cash_weight", "target_cash_min", "target_cash_max"),
    }
    weight_key, min_key, max_key = mapping.get(sleeve, mapping["SINGLE_STOCK"])
    current = summary[weight_key]
    minimum = to_float(rules[min_key])
    maximum = to_float(rules[max_key])
    if current < minimum:
        return min(20.0, (minimum - current) * 100.0 * 0.6)
    if current > maximum:
        return -20.0
    return 4.0


def build_candidate_rows(
    score_rows: list[dict[str, str]],
    watchlist_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    used: set[str] = set()

    for row in watchlist_rows:
        ticker = canonicalize_ticker(row.get("ticker", ""))
        if ticker:
            candidates.append({**row, "ticker": ticker})
            used.add(ticker)

    for row in score_rows:
        ticker = canonicalize_ticker(row.get("ticker", ""))
        if ticker and ticker not in used and str(row.get("held_in_portfolio", "")).lower() == "true":
            candidates.append({**row, "ticker": ticker})
    return candidates


def evaluate_candidate(
    candidate: dict[str, str],
    score_row: dict[str, str],
    positions_index: dict[str, dict[str, str]],
    sector_weights: dict[str, float],
    summary: dict[str, float],
    rules: dict[str, Any],
    budget: float,
    total_assets: float,
    coverage_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ticker = canonicalize_ticker(score_row.get("ticker") or candidate.get("ticker"))
    company_name = str(candidate.get("company_name") or score_row.get("company_name") or ticker)
    sleeve = str(candidate.get("sleeve") or score_row.get("sleeve") or "SINGLE_STOCK").upper()
    sector = str(candidate.get("sector") or score_row.get("sector") or "Unknown")
    position_row = find_position_row(positions_index, candidate, score_row)
    current_value = to_float(position_row.get("market_value_eur"))
    current_weight_pct = round2((current_value / total_assets) * 100.0) if total_assets else 0.0
    projected_total_assets = total_assets + budget
    sector_current_value = round2(sector_weights.get(sector, 0.0) * total_assets)
    position_cap = max(0.0, (to_float(rules["max_single_position_weight"]) * projected_total_assets) - current_value)
    sector_cap = max(0.0, (to_float(rules["max_sector_weight"]) * projected_total_assets) - sector_current_value)
    if sleeve in {"CORE_ETF", "DIVIDEND_QUALITY_ETF"} or sector == "ETF":
        sector_cap = budget
    allowed_amount = max(0.0, min(budget, position_cap, sector_cap))
    business_score = to_float(score_row.get("business_score"))
    valuation_score = to_float(score_row.get("valuation_score"))
    buy_score = to_float(score_row.get("buy_score"))
    corridor_bonus = corridor_gap_bonus(sleeve, summary, rules)
    priority_score = buy_score + corridor_bonus + max(0.0, to_float(score_row.get("margin_of_safety_pct")) * 0.15)
    purchase_readiness = evaluate_purchase_readiness(score_row, rules)

    business_ok = bool(purchase_readiness["business_ok"])
    valuation_ok = bool(purchase_readiness["valuation_ok"])
    buy_ok = bool(purchase_readiness["buy_ok"])
    position_cap_ok = allowed_amount >= to_float(rules["buy_rules"]["min_candidate_amount_eur"])
    data_ok = bool(purchase_readiness["data_ok"])
    purchase_state = str(purchase_readiness["purchase_state"])
    eligible = bool(purchase_readiness["eligible_for_purchase"]) and position_cap_ok
    coverage_row = find_coverage_row(position_row, candidate, score_row, coverage_index or {}) if current_value > 0.0 else None
    coverage_blocked = coverage_guardrail_applies(coverage_row)
    if coverage_blocked:
        eligible = False

    target_action = "TOP_UP" if current_value > 0.0 else "BUY"
    if not eligible:
        target_action = "DO_NOT_BUY"

    rationale = (
        f"Business={round2(business_score)} Bewertung={round2(valuation_score)} Buy-Score={round2(buy_score)} "
        f"Korridorbonus={round2(corridor_bonus)} Portfolio-Sleeve={sleeve}"
    )
    constraint_checks = "; ".join(
        [
            f"kaufbarkeit={PURCHASE_STATE_LABELS.get(purchase_state, purchase_state)}",
            f"business_score_ok={'JA' if business_ok else 'NEIN'}",
            f"valuation_score_ok={'JA' if valuation_ok else 'NEIN'}",
            f"buy_score_ok={'JA' if buy_ok else 'NEIN'}",
            f"positionslimit_ok={'JA' if position_cap_ok else 'NEIN'}",
            f"datenqualitaet_ok={'JA' if data_ok else 'NEIN'}",
            f"allowed_amount_eur={round2(allowed_amount)}",
        ]
    )
    if coverage_blocked:
        assert coverage_row is not None
        status = safe_upper(coverage_row.get("match_status")) or "UNKNOWN"
        method = safe_upper(coverage_row.get("match_method")) or "UNKNOWN"
        missing_required = str(coverage_row.get("missing_required_kpis", "")).strip() or "keine"
        needs_research = to_bool(coverage_row.get("needs_research_flag"))
        constraint_checks = (
            f"{constraint_checks}; fundamentals_coverage_guardrail=AKTIV "
            f"status={status} method={method} missing_required={missing_required} "
            f"needs_research={needs_research}"
        )
        rationale = f"{rationale} Fundamentals-Coverage-Guardrail blockiert frisches Kapital fuer bestehende Holding."

    return {
        "ticker": ticker,
        "company_name": company_name,
        "current_weight": round2(current_weight_pct),
        "target_action": target_action,
        "allocation_status": "ELIGIBLE" if eligible else "NOT_ELIGIBLE",
        "suggested_buy_amount_eur": round2(allowed_amount if eligible else 0.0),
        "rationale": rationale,
        "constraint_checks": constraint_checks,
        "valuation_comment": score_row.get("valuation_comment", ""),
        "mandate_fit_comment": candidate.get(
            "mandate_fit_comment",
            f"Mandats-Fit {score_row.get('mandate_fit_score', 'n/a')} und Portfolio-Sleeve {sleeve}.",
        ),
        "_eligible": eligible,
        "_priority_score": priority_score,
    }


def build_rebalance_proposals(
    positions_rows: list[dict[str, str]],
    score_rows: list[dict[str, str]],
    rules: dict[str, Any],
) -> list[dict[str, Any]]:
    summary = allocation_summary(positions_rows)
    proposals: list[dict[str, Any]] = []

    if summary["core_etf_weight"] < to_float(rules["target_core_etf_min"]):
        proposals.append(
            {
                "ticker": "CORE_ETF_SLEEVE",
                "company_name": "Portfolio Sleeve",
                "action": "ADD_CORE_ETF",
                "current_weight_pct": round2(summary["core_etf_weight"] * 100.0),
                "reason": "Core-ETF-Quote liegt unter dem Zielkorridor.",
            }
        )
    if summary["cash_weight"] > to_float(rules["target_cash_max"]):
        proposals.append(
            {
                "ticker": "CASH",
                "company_name": "Cash Reserve",
                "action": "DEPLOY_CASH",
                "current_weight_pct": round2(summary["cash_weight"] * 100.0),
                "reason": "Cash liegt ueber dem Zielkorridor.",
            }
        )

    for row in score_rows:
        if str(row.get("held_in_portfolio", "")).lower() != "true":
            continue
        classification = str(row.get("classification", "")).upper()
        if classification in {"REDUCE", "EXIT_REVIEW"}:
            proposals.append(
                {
                    "ticker": row.get("ticker", ""),
                    "company_name": row.get("company_name", ""),
                    "action": classification,
                    "current_weight_pct": round2(to_float(row.get("current_weight_pct"))),
                    "reason": f"classification={classification}; {row.get('main_risks', '')}",
                }
            )
    return proposals


def build_monthly_ranking(
    positions_rows: list[dict[str, str]],
    score_rows: list[dict[str, str]],
    watchlist_rows: list[dict[str, str]],
    rules_path: str = DEFAULT_RULES_PATH,
    score_source_name: str = "scores input",
    watchlist_source_name: str = "watchlist input",
    coverage_rows: list[dict[str, Any]] | None = None,
    coverage_source_name: str = "coverage input",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rules = load_portfolio_rules(rules_path)
    require_unique_tickers(score_rows, score_source_name)
    require_unique_tickers(watchlist_rows, watchlist_source_name)
    positions_index = positions_index_by_ticker(positions_rows)
    scores_index = index_by_ticker(score_rows)
    coverage_index = build_coverage_index(coverage_rows, coverage_source_name)
    candidates = build_candidate_rows(score_rows, watchlist_rows)
    total_assets = compute_total_assets(positions_rows)
    current_cash = compute_cash_value(positions_rows)
    available_budget = max(0.0, min(
        to_float(rules["monthly_new_cash_eur"]),
        current_cash + to_float(rules["monthly_new_cash_eur"]) - to_float(rules["min_cash_reserve_eur"]),
    ))
    summary = allocation_summary(positions_rows)
    sector_weights = compute_sector_weights(positions_rows)
    hold_cash_allowed = to_bool(rules.get("allow_hold_cash_if_no_opportunity", True))

    ranking_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        ticker = canonicalize_ticker(candidate.get("ticker", ""))
        if not ticker or ticker not in scores_index:
            continue
        ranking_rows.append(
            evaluate_candidate(
                candidate,
                scores_index[ticker],
                positions_index,
                sector_weights,
                summary,
                rules,
                available_budget,
                total_assets,
                coverage_index,
            )
        )

    ranking_rows.sort(
        key=lambda item: (
            not bool(item["_eligible"]),
            -float(item["_priority_score"]),
            str(item["ticker"]),
        )
    )

    if ranking_rows:
        selected = ranking_rows[0]
        if selected["_eligible"]:
            selected["allocation_status"] = "SELECTED_THIS_MONTH"
            for row in ranking_rows[1:]:
                row["suggested_buy_amount_eur"] = 0.0
                if row["_eligible"]:
                    row["allocation_status"] = "ELIGIBLE_NOT_FUNDED"
        elif hold_cash_allowed:
            ranking_rows.insert(
                0,
                {
                    "ticker": "HOLD_CASH",
                    "company_name": "Cash halten",
                    "current_weight": round2(summary["cash_weight"] * 100.0),
                    "target_action": "HOLD_CASH",
                    "allocation_status": "SELECTED_THIS_MONTH",
                    "suggested_buy_amount_eur": round2(available_budget),
                    "rationale": "Kein Kandidat hat Schwellenwerte und Restriktionen erfuellt; Cash bleibt als Opportunitaetsreserve stehen.",
                    "constraint_checks": "portfolio_rule=hold_cash_allowed",
                    "valuation_comment": "Cash bleibt stehen, bis Bewertung und Qualitaet attraktiver sind.",
                    "mandate_fit_comment": "Durch die Konfiguration erlaubt, wenn aktuell keine attraktive Opportunitaet vorliegt.",
                    "_eligible": True,
                    "_priority_score": 999.0,
                },
            )
    else:
        if hold_cash_allowed:
            ranking_rows = [
                {
                    "ticker": "HOLD_CASH",
                    "company_name": "Cash halten",
                    "current_weight": round2(summary["cash_weight"] * 100.0),
                    "target_action": "HOLD_CASH",
                    "allocation_status": "SELECTED_THIS_MONTH",
                    "suggested_buy_amount_eur": round2(available_budget),
                    "rationale": "Keine gerankten Kandidaten verfuegbar.",
                    "constraint_checks": "portfolio_rule=hold_cash_allowed",
                    "valuation_comment": "Cash bleibt stehen, bis ein investierbares Universum vorliegt.",
                    "mandate_fit_comment": "Durch die Konfiguration erlaubt, wenn die Datenlage noch nicht ausreicht.",
                    "_eligible": True,
                    "_priority_score": 999.0,
                }
            ]
        else:
            ranking_rows = [
                {
                    "ticker": "NO_ELIGIBLE_CANDIDATES",
                    "company_name": "Keine kaufbaren Kandidaten",
                    "current_weight": round2(summary["cash_weight"] * 100.0),
                    "target_action": "NO_ACTION",
                    "allocation_status": "NOT_ELIGIBLE",
                    "suggested_buy_amount_eur": 0.0,
                    "rationale": "Keine gerankten Kandidaten verfuegbar und synthetisches HOLD_CASH ist deaktiviert.",
                    "constraint_checks": "portfolio_rule=hold_cash_disallowed",
                    "valuation_comment": "Es wird kein Kauf vorgeschlagen, weil kein Kandidat die Restriktionen erfuellt.",
                    "mandate_fit_comment": "Die Konfiguration verbietet synthetisches HOLD_CASH, erzwingt aber weiterhin keinen schlechten Kauf.",
                    "_eligible": False,
                    "_priority_score": -999.0,
                }
            ]

    for rank, row in enumerate(ranking_rows, start=1):
        row["rank"] = rank

    rebalance = build_rebalance_proposals(positions_rows, score_rows, rules)
    return ranking_rows, rebalance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build monthly buy ranking for configurable monthly cash inflows.")
    parser.add_argument("--positions", required=True, help="Positions snapshot CSV.")
    parser.add_argument("--scores", required=True, help="Company scores CSV.")
    parser.add_argument("--watchlist", required=True, help="Ranked watchlist CSV.")
    parser.add_argument("--output", required=True, help="Monthly ranking CSV output.")
    parser.add_argument("--coverage", help="Optional personal fundamentals coverage CSV.")
    parser.add_argument("--rebalance-output", default="data/processed/rebalance_proposals.csv", help="Rebalance CSV output.")
    parser.add_argument("--rules", default=DEFAULT_RULES_PATH, help="Portfolio rules config path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    positions_rows = read_csv_rows(args.positions)
    score_rows = read_csv_rows(args.scores)
    watchlist_rows = read_csv_rows(args.watchlist)
    coverage_rows = read_coverage_rows(args.coverage) if args.coverage else None
    require_columns(
        positions_rows,
        ["ticker", "market_value_eur", "asset_type", "sleeve", "sector"],
        f"positions CSV ({args.positions})",
    )
    require_columns(
        score_rows,
        ["ticker", "business_score", "valuation_score", "buy_score", "classification", "data_quality_flag"],
        f"scores CSV ({args.scores})",
    )
    if watchlist_rows:
        require_columns(watchlist_rows, ["ticker"], f"watchlist CSV ({args.watchlist})")
    ranking, rebalance = build_monthly_ranking(
        positions_rows,
        score_rows,
        watchlist_rows,
        args.rules,
        f"scores CSV ({args.scores})",
        f"watchlist CSV ({args.watchlist})",
        coverage_rows,
        f"coverage CSV ({args.coverage})",
    )
    cleaned_ranking = [{key: row.get(key, "") for key in OUTPUT_FIELDS} for row in ranking]
    write_csv_rows(args.output, OUTPUT_FIELDS, cleaned_ranking)
    write_csv_rows(args.rebalance_output, REBALANCE_FIELDS, rebalance)


if __name__ == "__main__":
    main()
