from __future__ import annotations

import argparse
import csv
import os
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, load_yaml_config, read_csv_rows, resolve_repo_path, round2, to_bool, to_float, write_csv_rows
from src.savings_plan_registry import DEFAULT_INPUT as DEFAULT_SAVINGS_PLAN_INPUT
from src.savings_plan_registry import load_savings_plan_registry, validate_savings_plan_registry

AVAILABLE = "AVAILABLE"
PARTIAL = "PARTIAL"
NOT_AVAILABLE = "NOT_AVAILABLE"
INSUFFICIENT_INPUTS = "INSUFFICIENT_INPUTS"
OK_FLAG = "OK"
SNAPSHOT_ONLY = "SNAPSHOT_ONLY"
STALE_PERFORMANCE_SOURCE = "STALE_PERFORMANCE_SOURCE"
STALE_COST_TAX_SOURCE = "STALE_COST_TAX_SOURCE"
SOURCE_DATE_STALENESS_THRESHOLD_DAYS = 2

DEFAULT_CONFIG_PATH = "configs/dashboard_kpis.yaml"
DEFAULT_POSITIONS_PATH = "data/processed/personal_positions_snapshot.csv"
DEFAULT_SCORES_PATH = "data/processed/personal_company_scores.csv"
DEFAULT_HOLDINGS_PATH = "data/processed/personal_portfolio_holdings_action_table.csv"
DEFAULT_WATCHLIST_PATH = "data/processed/personal_watchlist_ranked.csv"
DEFAULT_SCORE_AUDIT_PATH = "data/processed/personal_score_audit.csv"
DEFAULT_COVERAGE_PATH = ""
DEFAULT_PERFORMANCE_KPIS_PATH = "data/processed/performance_kpis.csv"
DEFAULT_PERFORMANCE_SUMMARY_PATH = "data/processed/performance_summary.csv"
DEFAULT_PERFORMANCE_COMPARISON_PATH = "data/processed/performance_comparison.csv"
DEFAULT_COST_TAX_KPIS_PATH = "data/processed/cost_tax_kpis.csv"
DEFAULT_COST_TAX_SUMMARY_PATH = "data/processed/cost_tax_summary.csv"
DEFAULT_KPI_OUTPUT = "data/processed/dashboard_kpis.csv"
DEFAULT_SECTIONS_OUTPUT = "data/processed/dashboard_sections.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/dashboard_summary.csv"
DEFAULT_REPORT_OUTPUT = "reports/sample/dashboard_report.md"
DEFAULT_UNIVERSE_OUTPUT = "data/processed/dashboard_universe_section.csv"

DASHBOARD_KPI_FIELDS = [
    "metric_name",
    "metric_group",
    "metric_value",
    "metric_unit",
    "source_name",
    "source_file",
    "measurement_mode",
    "data_quality_flag",
    "availability_status",
    "notes",
]

DASHBOARD_SECTION_FIELDS = [
    "section_name",
    "block_status",
    "metric_name",
    "display_order",
    "display_label",
    "value_display",
    "data_quality_flag",
]

DASHBOARD_SUMMARY_FIELDS = [
    "snapshot_date",
    "performance_source_date",
    "cost_tax_source_date",
    "cross_source_data_quality_flag",
    "dashboard_data_quality_flag",
    "portfolio_measurement_mode",
    "performance_measurement_mode",
    "ledger_measurement_mode",
    "total_assets",
    "weighted_buy_score",
    "active_return",
    "total_fees",
    "total_taxes",
    "notes_count",
    "missing_block_count",
]

DASHBOARD_UNIVERSE_FIELDS = [
    "ticker",
    "instrument_name",
    "sector",
    "bucket",
    "sleeve",
    "business_score",
    "valuation_score",
    "buy_score",
    "watchlist_status",
    "savings_plan_active",
    "last_score_update_date",
    "stale_marker",
    "data_quality_flag",
]

PRIMARY_GROUPS = [
    "Portfolio / Struktur",
    "Score / Fundamentals",
    "Benchmark / Performance",
    "Kosten / Steuern",
]

COVERAGE_REQUIRED_COLUMNS = [
    "match_status",
    "match_method",
    "missing_required_kpis",
    "not_applicable_kpis",
    "needs_research_flag",
]

DASHBOARD_DERIVED_METRICS = {
    "performance_source_date",
    "cost_tax_source_date",
    "cross_source_data_quality_flag",
    "dashboard_data_quality_flag",
    "methodology_notes_count",
    "missing_block_count",
}

SLEEVE_ORDER = {
    "CORE_ETF": 0,
    "DIVIDEND_QUALITY_ETF": 1,
    "SINGLE_STOCK": 2,
    "CASH": 3,
    "UNKNOWN_SLEEVE": 4,
}
BUCKET_ORDER = {
    "HOLDING": 0,
    "HOLDING_AND_WATCHLIST": 1,
    "WATCHLIST": 2,
    "UNKNOWN_BUCKET": 3,
}
VALID_SLEEVES = set(SLEEVE_ORDER)
VALID_WATCHLIST_STATUSES = {
    "CORE_CANDIDATE",
    "DG_CANDIDATE",
    "QUALITY_COMPOUNDER_CANDIDATE",
    "TOO_EXPENSIVE",
    "REVIEW",
    "REJECT",
    "NOT_ON_WATCHLIST",
}


@dataclass(frozen=True)
class SourceTable:
    source_key: str
    path_value: str
    rows: list[dict[str, str]]
    exists: bool


def format_optional_number(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return ""
        return str(round2(to_float(text)))
    return str(round2(float(value)))


def combine_quality_flags(*values: str, default: str = NOT_AVAILABLE) -> str:
    flags: list[str] = []
    for value in values:
        for part in str(value or "").split("|"):
            flag = part.strip()
            if flag and flag not in flags:
                flags.append(flag)
    if not flags:
        return default
    non_ok = [flag for flag in flags if flag != OK_FLAG]
    if non_ok:
        return "|".join(non_ok)
    return OK_FLAG


def load_optional_source(source_key: str, path_value: str) -> SourceTable:
    if not path_value:
        return SourceTable(source_key=source_key, path_value="", rows=[], exists=False)
    resolved = resolve_repo_path(path_value)
    if not resolved.exists():
        return SourceTable(source_key=source_key, path_value=path_value, rows=[], exists=False)
    return SourceTable(source_key=source_key, path_value=path_value, rows=read_csv_rows(path_value), exists=True)


def load_optional_coverage_source(source_key: str, path_value: str) -> SourceTable:
    if not path_value:
        return SourceTable(source_key=source_key, path_value="", rows=[], exists=False)
    resolved = resolve_repo_path(path_value)
    if not resolved.exists():
        return SourceTable(source_key=source_key, path_value=path_value, rows=[], exists=False)
    with resolved.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [column for column in COVERAGE_REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"coverage CSV ({path_value}) missing required columns: {missing_text}")
        return SourceTable(source_key=source_key, path_value=path_value, rows=list(reader), exists=True)


def parse_iso_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def canonical_ticker(value: Any) -> str:
    return str(value or "").strip().upper().replace(" ", "")


def first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def canonical_sleeve(value: Any) -> str:
    sleeve = str(value or "").strip().upper()
    return sleeve if sleeve in VALID_SLEEVES and sleeve != "UNKNOWN_SLEEVE" else "UNKNOWN_SLEEVE"


def score_text(row: dict[str, str] | None, field_name: str) -> str:
    if row is None:
        return "MISSING_DATA"
    text = str(row.get(field_name, "")).strip()
    if not text:
        return "MISSING_DATA"
    value = to_float(text, float("nan"))
    if value != value or value < 0.0 or value > 100.0:
        return "MISSING_DATA"
    return text


def universe_data_quality(business_score: str, valuation_score: str, buy_score: str) -> str:
    missing_core = business_score == "MISSING_DATA"
    missing_valuation = valuation_score == "MISSING_DATA" or buy_score == "MISSING_DATA"
    if missing_core and missing_valuation:
        return "MULTIPLE_GAPS"
    if missing_core:
        return "MISSING_CORE_KPIS"
    if missing_valuation:
        return "MISSING_VALUATION_KPIS"
    return "OK"


def stale_marker(score_row: dict[str, str] | None, today: date | None = None) -> tuple[str, str]:
    if score_row is None:
        return "", "NEVER_SCORED"
    date_text = str(score_row.get("source_as_of_date", "")).strip()
    score_date = parse_iso_date(date_text)
    if score_date is None:
        return "", "NEVER_SCORED"
    anchor = today or date.today()
    age_days = (anchor - score_date).days
    if age_days <= 7:
        return date_text, "FRESH"
    if age_days <= 30:
        return date_text, "STALE_7D"
    return date_text, "STALE_30D"


def index_by_ticker(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in rows:
        ticker = canonical_ticker(row.get("ticker", ""))
        if ticker and ticker not in index:
            index[ticker] = row
    return index


def savings_plan_status_index(rows: list[dict[str, str]]) -> dict[str, str]:
    index: dict[str, str] = {}
    for row in rows:
        ticker = canonical_ticker(row.get("ticker", ""))
        if not ticker:
            continue
        active = str(row.get("active", "")).strip().upper()
        if active in {"TRUE", "FALSE"}:
            index[ticker] = active
    return index


def load_savings_plan_rows(path_value: str) -> list[dict[str, str]]:
    if not path_value:
        return []
    resolved = resolve_repo_path(path_value)
    if not resolved.exists():
        return []
    rows = load_savings_plan_registry(path_value)
    normalized_rows, _warnings = validate_savings_plan_registry(rows, path_value)
    return normalized_rows


def build_universe_section(
    positions_rows: list[dict[str, str]] | None = None,
    holdings_rows: list[dict[str, str]] | None = None,
    scores_rows: list[dict[str, str]] | None = None,
    watchlist_rows: list[dict[str, str]] | None = None,
    savings_plan_rows: list[dict[str, str]] | None = None,
    today: date | None = None,
) -> list[dict[str, str]]:
    positions_index = index_by_ticker(positions_rows or [])
    holdings_index = index_by_ticker(holdings_rows or [])
    scores_index = index_by_ticker(scores_rows or [])
    watchlist_index = index_by_ticker(watchlist_rows or [])
    plan_index = savings_plan_status_index(savings_plan_rows or [])
    holding_tickers = set(positions_index) | set(holdings_index)
    watchlist_tickers = set(watchlist_index)
    tickers = sorted(holding_tickers | watchlist_tickers | set(scores_index))
    rows: list[dict[str, str]] = []
    for ticker in tickers:
        position = positions_index.get(ticker, {})
        holding = holdings_index.get(ticker, {})
        score = scores_index.get(ticker)
        score_source = score or {}
        watchlist = watchlist_index.get(ticker, {})
        if ticker in holding_tickers and ticker in watchlist_tickers:
            bucket = "HOLDING_AND_WATCHLIST"
        elif ticker in holding_tickers:
            bucket = "HOLDING"
        elif ticker in watchlist_tickers:
            bucket = "WATCHLIST"
        else:
            bucket = "UNKNOWN_BUCKET"
        business = score_text(score, "business_score")
        valuation = score_text(score, "valuation_score")
        buy = score_text(score, "buy_score")
        score_date, marker = stale_marker(score, today)
        watch_status = str(watchlist.get("status", "")).strip().upper() if watchlist else "NOT_ON_WATCHLIST"
        if watch_status not in VALID_WATCHLIST_STATUSES:
            watch_status = "REVIEW"
        rows.append(
            {
                "ticker": ticker,
                "instrument_name": first_text(
                    position.get("company_name"),
                    position.get("instrument_name"),
                    holding.get("company_name"),
                    holding.get("instrument_name"),
                    watchlist.get("company_name"),
                    watchlist.get("instrument_name"),
                    score_source.get("company_name"),
                    score_source.get("instrument_name"),
                    ticker,
                ),
                "sector": first_text(position.get("sector"), watchlist.get("sector"), score_source.get("sector")),
                "bucket": bucket,
                "sleeve": canonical_sleeve(first_text(position.get("sleeve"), holding.get("sleeve"), watchlist.get("sleeve"), score_source.get("sleeve"))),
                "business_score": business,
                "valuation_score": valuation,
                "buy_score": buy,
                "watchlist_status": watch_status,
                "savings_plan_active": plan_index.get(ticker, "NO_PLAN"),
                "last_score_update_date": score_date,
                "stale_marker": marker,
                "data_quality_flag": universe_data_quality(business, valuation, buy),
            }
        )
    rows.sort(
        key=lambda row: (
            SLEEVE_ORDER.get(row["sleeve"], SLEEVE_ORDER["UNKNOWN_SLEEVE"]),
            BUCKET_ORDER.get(row["bucket"], BUCKET_ORDER["UNKNOWN_BUCKET"]),
            -(to_float(row["buy_score"], -1.0) if row["buy_score"] != "MISSING_DATA" else -1.0),
            row["ticker"],
        )
    )
    return rows


def write_universe_csv(path_value: str | Path, rows: list[dict[str, str]]) -> Path:
    output_path = ensure_parent_dir(path_value)
    temp_path = output_path.with_name(f"{output_path.name}.tmp")
    try:
        with temp_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=DASHBOARD_UNIVERSE_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in DASHBOARD_UNIVERSE_FIELDS})
        os.replace(temp_path, output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return output_path


def validate_metric_rows(rows: list[dict[str, str]], source_name: str) -> None:
    if not rows or "metric_name" not in rows[0]:
        return
    seen: set[str] = set()
    duplicates: set[str] = set()
    for index, row in enumerate(rows, start=2):
        metric_name = str(row.get("metric_name", "")).strip()
        if not metric_name:
            raise ValueError(f"{source_name} row {index} has blank required field(s): metric_name")
        if metric_name in seen:
            duplicates.add(metric_name)
        seen.add(metric_name)
    if duplicates:
        duplicate_text = ", ".join(sorted(duplicates))
        raise ValueError(f"{source_name} contains duplicate metric_name values: {duplicate_text}")


def build_metric_index(rows: list[dict[str, str]], source_name: str) -> dict[str, dict[str, str]]:
    validate_metric_rows(rows, source_name)
    index: dict[str, dict[str, str]] = {}
    for row in rows:
        metric_name = str(row.get("metric_name", "")).strip()
        if metric_name and metric_name not in index:
            index[metric_name] = row
    return index


def source_measurement_mode(source_key: str, row: dict[str, str] | None = None) -> str:
    current = row or {}
    if source_key in {"positions", "scores", "holdings", "score_audit", "coverage"}:
        return SNAPSHOT_ONLY
    if source_key in {"performance_kpis", "performance_summary", "performance_comparison", "cost_tax_kpis"}:
        return str(current.get("measurement_mode", "")).strip()
    if source_key == "cost_tax_summary":
        return str(current.get("ledger_measurement_mode", "")).strip()
    return ""


def metric_availability(value: str, unavailable_values: set[str]) -> str:
    if str(value or "").strip() in unavailable_values:
        return NOT_AVAILABLE
    return AVAILABLE


def make_metric_row(
    metric_name: str,
    metric_group: str,
    metric_value: str,
    metric_unit: str,
    source_name: str,
    source_file: str,
    measurement_mode: str,
    data_quality_flag: str,
    availability_status: str,
    notes: str,
) -> dict[str, str]:
    return {
        "metric_name": metric_name,
        "metric_group": metric_group,
        "metric_value": str(metric_value or "").strip(),
        "metric_unit": metric_unit,
        "source_name": source_name,
        "source_file": source_file,
        "measurement_mode": measurement_mode,
        "data_quality_flag": data_quality_flag,
        "availability_status": availability_status,
        "notes": notes,
    }


def is_cash_row(row: dict[str, str]) -> bool:
    asset_type = str(row.get("asset_type", "")).strip().upper()
    sleeve = str(row.get("sleeve", "")).strip().upper()
    ticker = str(row.get("ticker", "")).strip().upper()
    return asset_type == "CASH" or sleeve == "CASH" or ticker.endswith("CASH")


def row_market_value_eur(row: dict[str, str]) -> float:
    return to_float(row.get("market_value_eur", row.get("market_value", "")))


def row_total_asset_weight(row: dict[str, str], total_assets: float) -> float:
    raw_weight = str(row.get("weight_total_assets_pct", "")).strip()
    if raw_weight:
        return round2(to_float(raw_weight))
    if total_assets <= 0.0:
        return 0.0
    return round2((row_market_value_eur(row) / total_assets) * 100.0)


def count_true_flags(rows: list[dict[str, str]], field_name: str) -> int:
    return sum(1 for row in rows if to_bool(row.get(field_name)))


def derive_positions_metrics(source: SourceTable) -> dict[str, dict[str, str]]:
    if not source.rows:
        return {}
    total_assets = round2(sum(row_market_value_eur(row) for row in source.rows))
    cash_rows = [row for row in source.rows if is_cash_row(row)]
    non_cash_rows = [row for row in source.rows if not is_cash_row(row)]
    cash_value = round2(sum(row_market_value_eur(row) for row in cash_rows))
    portfolio_value = round2(sum(row_market_value_eur(row) for row in non_cash_rows))
    weighted_rows = [
        {
            "row": row,
            "weight": row_total_asset_weight(row, total_assets),
        }
        for row in non_cash_rows
    ]
    weighted_rows.sort(key=lambda item: item["weight"], reverse=True)
    quality_flag = combine_quality_flags(*(row.get("data_quality_flag", "") for row in source.rows), default=OK_FLAG)
    snapshot_dates = sorted(
        {
            str(row.get("portfolio_date", "")).strip()
            for row in source.rows
            if str(row.get("portfolio_date", "")).strip()
        }
    )
    snapshot_date = snapshot_dates[-1] if snapshot_dates else ""

    def metric(value: Any, notes: str = "") -> dict[str, str]:
        return {
            "value": str(value),
            "measurement_mode": SNAPSHOT_ONLY,
            "data_quality_flag": quality_flag,
            "notes": notes,
        }

    return {
        "total_assets": metric(format_optional_number(total_assets)),
        "portfolio_value": metric(format_optional_number(portfolio_value)),
        "cash_value": metric(format_optional_number(cash_value)),
        "cash_weight": metric(format_optional_number((cash_value / total_assets) * 100.0 if total_assets else 0.0)),
        "invested_assets": metric(format_optional_number(portfolio_value)),
        "number_of_positions": metric(str(len(non_cash_rows)), "Count of non-cash snapshot rows."),
        "top_5_weight": metric(format_optional_number(sum(item["weight"] for item in weighted_rows[:5])), "Uses weight_total_assets_pct and excludes cash."),
        "top_10_weight": metric(format_optional_number(sum(item["weight"] for item in weighted_rows[:10])), "Uses weight_total_assets_pct and excludes cash."),
        "equity_weight": metric(format_optional_number(sum(item["weight"] for item in weighted_rows))),
        "core_etf_weight": metric(format_optional_number(sum(item["weight"] for item in weighted_rows if str(item["row"].get("sleeve", "")).strip().upper() == "CORE_ETF"))),
        "dg_quality_etf_weight": metric(format_optional_number(sum(item["weight"] for item in weighted_rows if str(item["row"].get("sleeve", "")).strip().upper() == "DIVIDEND_QUALITY_ETF"))),
        "single_stock_weight": metric(format_optional_number(sum(item["weight"] for item in weighted_rows if str(item["row"].get("sleeve", "")).strip().upper() == "SINGLE_STOCK"))),
        "non_core_weight": metric(
            format_optional_number(
                sum(
                    item["weight"]
                    for item in weighted_rows
                    if str(item["row"].get("sleeve", "")).strip().upper() not in {"CORE_ETF", "DIVIDEND_QUALITY_ETF", "SINGLE_STOCK"}
                )
            )
        ),
        "review_count": metric(str(count_true_flags(non_cash_rows, "review_flag"))),
        "portfolio_measurement_mode": metric(SNAPSHOT_ONLY),
        "snapshot_date": metric(snapshot_date),
    }


def select_weight_basis(rows: list[dict[str, str]]) -> str:
    if any(to_float(row.get("position_market_value_eur", "")) > 0.0 for row in rows):
        return "position_market_value_eur"
    if any(to_float(row.get("current_weight_pct", "")) > 0.0 for row in rows):
        return "current_weight_pct"
    return ""


def derive_scores_metrics(source: SourceTable) -> dict[str, dict[str, str]]:
    if not source.rows:
        return {}
    held_rows = [row for row in source.rows if to_bool(row.get("held_in_portfolio"))]
    if not held_rows:
        held_rows = source.rows
    quality_flag = combine_quality_flags(*(row.get("data_quality_flag", "") for row in source.rows), default=OK_FLAG)
    weight_field = select_weight_basis(held_rows)

    def weighted_metric(field_name: str) -> dict[str, str]:
        eligible_rows = [row for row in held_rows if str(row.get(field_name, "")).strip()]
        if not eligible_rows:
            return {
                "value": NOT_AVAILABLE,
                "measurement_mode": SNAPSHOT_ONLY,
                "data_quality_flag": quality_flag,
                "notes": f"No held score rows with explicit {field_name}.",
            }
        if weight_field:
            weights = [max(to_float(row.get(weight_field, "")), 0.0) for row in eligible_rows]
            total_weight = sum(weights)
            if total_weight <= 0.0:
                weight_mode = "equal weight"
                weighted_value = sum(to_float(row.get(field_name, "")) for row in eligible_rows) / len(eligible_rows)
            else:
                weight_mode = weight_field
                weighted_value = sum(to_float(row.get(field_name, "")) * weights[index] for index, row in enumerate(eligible_rows)) / total_weight
        else:
            weight_mode = "equal weight"
            weighted_value = sum(to_float(row.get(field_name, "")) for row in eligible_rows) / len(eligible_rows)
        return {
            "value": format_optional_number(weighted_value),
            "measurement_mode": SNAPSHOT_ONLY,
            "data_quality_flag": quality_flag,
            "notes": f"Weighted across held score rows using {weight_mode}.",
        }

    missing_data_count = sum(
        1
        for row in source.rows
        if str(row.get("data_quality_flag", "")).strip().upper() not in {"", OK_FLAG}
    )

    return {
        "weighted_business_score": weighted_metric("business_score"),
        "weighted_valuation_score": weighted_metric("valuation_score"),
        "weighted_buy_score": weighted_metric("buy_score"),
        "missing_data_count": {
            "value": str(missing_data_count),
            "measurement_mode": SNAPSHOT_ONLY,
            "data_quality_flag": quality_flag,
            "notes": "Fallback from company_scores data_quality_flag.",
        },
        "score_data_quality_flag": {
            "value": quality_flag,
            "measurement_mode": SNAPSHOT_ONLY,
            "data_quality_flag": quality_flag,
            "notes": "Combined company_scores data_quality_flag values.",
        },
    }


def derive_score_audit_metrics(source: SourceTable) -> dict[str, dict[str, str]]:
    if not source.rows:
        return {}
    quality_flag = combine_quality_flags(*(row.get("data_quality_flag", "") for row in source.rows), default=OK_FLAG)
    missing_count = 0
    for row in source.rows:
        if str(row.get("data_quality_flag", "")).strip().upper() not in {"", OK_FLAG}:
            missing_count += 1
            continue
        if to_float(row.get("missing_kpi_count", "")) > 0.0:
            missing_count += 1
    return {
        "missing_data_count": {
            "value": str(missing_count),
            "measurement_mode": SNAPSHOT_ONLY,
            "data_quality_flag": quality_flag,
            "notes": "Derived from score_audit data_quality_flag and missing_kpi_count.",
        },
        "score_data_quality_flag": {
            "value": quality_flag,
            "measurement_mode": SNAPSHOT_ONLY,
            "data_quality_flag": quality_flag,
            "notes": "Combined score_audit data_quality_flag values.",
        },
    }


def derive_coverage_metrics(source: SourceTable) -> dict[str, dict[str, str]]:
    if not source.exists:
        return {}
    counts = Counter(str(row.get("match_status", "")).strip().upper() for row in source.rows)
    quality_flag = combine_quality_flags(*(row.get("data_quality_flag", "") for row in source.rows), default=OK_FLAG)

    def metric(value: int, notes: str) -> dict[str, str]:
        return {
            "value": str(value),
            "measurement_mode": SNAPSHOT_ONLY,
            "data_quality_flag": quality_flag,
            "notes": notes,
        }

    research_needed_count = count_true_flags(source.rows, "needs_research_flag")
    missing_required_count = sum(1 for row in source.rows if str(row.get("missing_required_kpis", "")).strip())
    return {
        "fundamentals_covered_count": metric(counts.get("COVERED", 0), "Derived from coverage match_status=COVERED."),
        "fundamentals_partial_count": metric(counts.get("PARTIAL", 0), "Derived from coverage match_status=PARTIAL."),
        "fundamentals_review_count": metric(counts.get("REVIEW", 0), "Derived from coverage match_status=REVIEW."),
        "fundamentals_no_match_count": metric(counts.get("NO_MATCH", 0), "Derived from coverage match_status=NO_MATCH."),
        "fundamentals_research_needed_count": metric(research_needed_count, "Derived from coverage needs_research_flag=True."),
        "fundamentals_missing_required_count": metric(missing_required_count, "Derived from non-empty coverage missing_required_kpis."),
    }


def derive_holdings_metrics(source: SourceTable) -> dict[str, dict[str, str]]:
    if not source.rows:
        return {}
    counts = Counter(str(row.get("portfolio_action", "")).strip().upper() for row in source.rows)
    quality_flag = combine_quality_flags(*(row.get("data_quality_flag", "") for row in source.rows), default=OK_FLAG)
    return {
        "add_count": {"value": str(counts.get("ADD", 0)), "measurement_mode": SNAPSHOT_ONLY, "data_quality_flag": quality_flag, "notes": ""},
        "hold_count": {"value": str(counts.get("HOLD", 0)), "measurement_mode": SNAPSHOT_ONLY, "data_quality_flag": quality_flag, "notes": ""},
        "watch_count": {"value": str(counts.get("WATCH", 0)), "measurement_mode": SNAPSHOT_ONLY, "data_quality_flag": quality_flag, "notes": ""},
        "reduce_count": {"value": str(counts.get("REDUCE", 0)), "measurement_mode": SNAPSHOT_ONLY, "data_quality_flag": quality_flag, "notes": ""},
        "exit_review_count": {"value": str(counts.get("EXIT_REVIEW", 0)), "measurement_mode": SNAPSHOT_ONLY, "data_quality_flag": quality_flag, "notes": ""},
        "review_count": {"value": str(count_true_flags(source.rows, "review_flag")), "measurement_mode": SNAPSHOT_ONLY, "data_quality_flag": quality_flag, "notes": ""},
    }


def select_performance_source_date(
    sources: dict[str, SourceTable],
    metric_indexes: dict[str, dict[str, dict[str, str]]],
) -> tuple[str, str]:
    if sources["performance_summary"].rows:
        as_of_date = str(sources["performance_summary"].rows[0].get("as_of_date", "")).strip()
        if as_of_date:
            return as_of_date, "performance_summary.as_of_date"
    if sources["performance_comparison"].rows:
        as_of_date = str(sources["performance_comparison"].rows[0].get("as_of_date", "")).strip()
        if as_of_date:
            return as_of_date, "performance_comparison.as_of_date"
    row = metric_indexes.get("performance_kpis", {}).get("portfolio_as_of_date")
    if row:
        as_of_date = str(row.get("metric_value", "")).strip()
        if as_of_date:
            return as_of_date, "performance_kpis.portfolio_as_of_date"
    return "", ""


def select_cost_tax_source_date(
    sources: dict[str, SourceTable],
    metric_indexes: dict[str, dict[str, dict[str, str]]],
) -> tuple[str, str]:
    if sources["cost_tax_summary"].rows:
        period_end = str(sources["cost_tax_summary"].rows[0].get("period_end", "")).strip()
        if period_end:
            return period_end, "cost_tax_summary.period_end"
    row = metric_indexes.get("cost_tax_kpis", {}).get("period_end")
    if row:
        period_end = str(row.get("metric_value", "")).strip()
        if period_end:
            return period_end, "cost_tax_kpis.period_end"
    return "", ""


def build_cross_source_date_metrics(
    sources: dict[str, SourceTable],
    metric_indexes: dict[str, dict[str, dict[str, str]]],
    snapshot_date_text: str,
) -> dict[str, dict[str, str]]:
    snapshot_date = parse_iso_date(snapshot_date_text)
    performance_source_date, performance_source_ref = select_performance_source_date(sources, metric_indexes)
    cost_tax_source_date, cost_tax_source_ref = select_cost_tax_source_date(sources, metric_indexes)

    flags: list[str] = []
    performance_notes = ""
    cost_tax_notes = ""

    performance_date = parse_iso_date(performance_source_date)
    if snapshot_date and performance_date:
        performance_lag = (snapshot_date - performance_date).days
        if performance_lag >= SOURCE_DATE_STALENESS_THRESHOLD_DAYS:
            flags.append(STALE_PERFORMANCE_SOURCE)
            performance_notes = (
                f"Performance source date is older than snapshot by {performance_lag} calendar days "
                f"({performance_source_ref})."
            )
        else:
            performance_notes = f"Performance source date aligns with snapshot tolerance ({performance_source_ref})."
    elif performance_source_date:
        performance_notes = f"Performance source date available but not comparable to snapshot ({performance_source_ref})."

    cost_tax_date = parse_iso_date(cost_tax_source_date)
    if snapshot_date and cost_tax_date:
        cost_tax_lag = (snapshot_date - cost_tax_date).days
        if cost_tax_lag >= SOURCE_DATE_STALENESS_THRESHOLD_DAYS:
            flags.append(STALE_COST_TAX_SOURCE)
            cost_tax_notes = (
                f"Cost/tax source date is older than snapshot by {cost_tax_lag} calendar days "
                f"({cost_tax_source_ref})."
            )
        else:
            cost_tax_notes = f"Cost/tax source date aligns with snapshot tolerance ({cost_tax_source_ref})."
    elif cost_tax_source_date:
        cost_tax_notes = f"Cost/tax source date available but not comparable to snapshot ({cost_tax_source_ref})."

    cross_source_flag = combine_quality_flags(*flags, default=OK_FLAG)
    cross_source_note_parts = [
        note for note in [performance_notes, cost_tax_notes] if note
    ]
    cross_source_notes = " ".join(cross_source_note_parts)
    return {
        "performance_source_date": {
            "value": performance_source_date or NOT_AVAILABLE,
            "measurement_mode": "",
            "data_quality_flag": cross_source_flag,
            "notes": performance_notes,
        },
        "cost_tax_source_date": {
            "value": cost_tax_source_date or NOT_AVAILABLE,
            "measurement_mode": "",
            "data_quality_flag": cross_source_flag,
            "notes": cost_tax_notes,
        },
        "cross_source_data_quality_flag": {
            "value": cross_source_flag,
            "measurement_mode": "",
            "data_quality_flag": cross_source_flag,
            "notes": cross_source_notes or "Cross-source snapshot date consistency check.",
        },
    }


def resolve_metric_from_priority(
    spec: dict[str, Any],
    sources: dict[str, SourceTable],
    derived_metrics: dict[str, dict[str, dict[str, str]]],
    metric_indexes: dict[str, dict[str, dict[str, str]]],
    unavailable_values: set[str],
) -> dict[str, str]:
    metric_name = str(spec["metric_name"])
    metric_group = str(spec["metric_group"])
    missing_policy = str(spec.get("missing_policy", NOT_AVAILABLE))
    priorities = list(spec.get("source_priority", []))
    attempted: list[str] = []

    for priority in priorities:
        source_key = str(priority.get("source_key", "")).strip()
        lookup_type = str(priority.get("lookup_type", "")).strip()
        attempted.append(f"{source_key}:{lookup_type}")
        source = sources.get(source_key, SourceTable(source_key=source_key, path_value="", rows=[], exists=False))

        if lookup_type == "derived_metric":
            metric_info = derived_metrics.get(source_key, {}).get(str(priority.get("field_name", "")).strip())
            if not metric_info:
                continue
            metric_value = str(metric_info.get("value", "")).strip()
            if not metric_value:
                continue
            return make_metric_row(
                metric_name=metric_name,
                metric_group=metric_group,
                metric_value=metric_value,
                metric_unit=str(spec.get("unit", "")),
                source_name=source_key,
                source_file=source.path_value,
                measurement_mode=str(metric_info.get("measurement_mode", "")),
                data_quality_flag=str(metric_info.get("data_quality_flag", NOT_AVAILABLE)),
                availability_status=metric_availability(metric_value, unavailable_values),
                notes=str(metric_info.get("notes", "")),
            )

        if not source.exists or not source.rows:
            continue

        if lookup_type == "metric_row":
            lookup_metric = str(priority.get("metric_name", metric_name)).strip()
            row = metric_indexes.get(source_key, {}).get(lookup_metric)
            if not row:
                continue
            metric_value = str(row.get("metric_value", "")).strip()
            if not metric_value:
                continue
            return make_metric_row(
                metric_name=metric_name,
                metric_group=metric_group,
                metric_value=metric_value,
                metric_unit=str(row.get("metric_unit", spec.get("unit", ""))).strip(),
                source_name=source_key,
                source_file=source.path_value,
                measurement_mode=source_measurement_mode(source_key, row),
                data_quality_flag=str(row.get("data_quality_flag", OK_FLAG)).strip() or OK_FLAG,
                availability_status=metric_availability(metric_value, unavailable_values),
                notes=str(row.get("notes", "")).strip(),
            )

        if lookup_type == "summary_field":
            row = source.rows[0]
            field_name = str(priority.get("field_name", metric_name)).strip()
            metric_value = str(row.get(field_name, "")).strip()
            if not metric_value:
                continue
            data_quality_flag = str(row.get("data_quality_flag", "")).strip()
            if source_key == "cost_tax_summary":
                data_quality_flag = str(row.get("ledger_data_quality_flag", data_quality_flag)).strip()
            if not data_quality_flag:
                data_quality_flag = OK_FLAG
            return make_metric_row(
                metric_name=metric_name,
                metric_group=metric_group,
                metric_value=metric_value,
                metric_unit=str(spec.get("unit", "")),
                source_name=source_key,
                source_file=source.path_value,
                measurement_mode=source_measurement_mode(source_key, row),
                data_quality_flag=data_quality_flag,
                availability_status=metric_availability(metric_value, unavailable_values),
                notes=str(row.get("notes", "")).strip(),
            )

    missing_note = "No non-blank value found in configured source priority."
    if attempted:
        missing_note = f"{missing_note} Tried: {', '.join(attempted)}."
    first_source_key = str(priorities[0].get("source_key", "dashboard")).strip() if priorities else "dashboard"
    first_source = sources.get(first_source_key, SourceTable(source_key=first_source_key, path_value="", rows=[], exists=False))
    return make_metric_row(
        metric_name=metric_name,
        metric_group=metric_group,
        metric_value=missing_policy,
        metric_unit=str(spec.get("unit", "")),
        source_name=first_source_key,
        source_file=first_source.path_value,
        measurement_mode="",
        data_quality_flag=NOT_AVAILABLE,
        availability_status=NOT_AVAILABLE,
        notes=missing_note,
    )


def skip_missing_optional_coverage_metric(spec: dict[str, Any], sources: dict[str, SourceTable]) -> bool:
    priorities = list(spec.get("source_priority", []))
    if not priorities:
        return False
    source_keys = {str(priority.get("source_key", "")).strip() for priority in priorities}
    return source_keys == {"coverage"} and not sources["coverage"].exists


def build_group_statuses(metric_rows: list[dict[str, str]], config: dict[str, Any]) -> dict[str, str]:
    statuses = config["block_status_rules"]
    metrics_by_group: dict[str, list[dict[str, str]]] = {}
    for row in metric_rows:
        metrics_by_group.setdefault(row["metric_group"], []).append(row)

    group_statuses: dict[str, str] = {}
    for group_config in config["groups"]:
        group_name = str(group_config["metric_group"])
        group_rows = metrics_by_group.get(group_name, [])
        if not group_rows:
            group_statuses[group_name] = statuses["all_missing"]
            continue
        availability = {row["availability_status"] for row in group_rows}
        if availability == {AVAILABLE}:
            group_statuses[group_name] = statuses["all_available"]
        elif availability == {NOT_AVAILABLE}:
            group_statuses[group_name] = statuses["all_missing"]
        else:
            group_statuses[group_name] = statuses["mixed"]
    return group_statuses


def build_dashboard_derived_metrics(
    metric_rows: list[dict[str, str]],
    group_statuses: dict[str, str],
    sources: dict[str, SourceTable],
    derived_metrics: dict[str, dict[str, dict[str, str]]],
    metric_indexes: dict[str, dict[str, dict[str, str]]],
) -> dict[str, dict[str, str]]:
    metric_index = {row["metric_name"]: row for row in metric_rows}
    notes_count = len({row["notes"] for row in metric_rows if str(row.get("notes", "")).strip()})
    missing_block_count = sum(1 for group in PRIMARY_GROUPS if group_statuses.get(group) == NOT_AVAILABLE)
    snapshot_date = derived_metrics.get("positions", {}).get("snapshot_date", {}).get("value", "")
    if not snapshot_date and sources["performance_summary"].rows:
        snapshot_date = str(sources["performance_summary"].rows[0].get("as_of_date", "")).strip()
    cross_source_metrics = build_cross_source_date_metrics(sources, metric_indexes, snapshot_date)
    cross_source_flag = cross_source_metrics["cross_source_data_quality_flag"]["value"]
    dashboard_quality = combine_quality_flags(
        metric_index.get("score_data_quality_flag", {}).get("metric_value", ""),
        metric_index.get("performance_data_quality_flag", {}).get("metric_value", ""),
        metric_index.get("cost_tax_data_quality_flag", {}).get("metric_value", ""),
        cross_source_flag,
        default=NOT_AVAILABLE,
    )
    derived = {
        **cross_source_metrics,
        "dashboard_data_quality_flag": {
            "value": dashboard_quality,
            "measurement_mode": "",
            "data_quality_flag": dashboard_quality,
            "notes": "Combined from score, performance, cost/tax, and cross-source date quality flags.",
        },
        "methodology_notes_count": {
            "value": str(notes_count),
            "measurement_mode": "",
            "data_quality_flag": OK_FLAG,
            "notes": "Counts unique non-empty notes across dashboard KPI rows.",
        },
        "missing_block_count": {
            "value": str(missing_block_count),
            "measurement_mode": "",
            "data_quality_flag": OK_FLAG,
            "notes": "Counts primary KPI blocks with status NOT_AVAILABLE.",
        },
    }
    return derived


def metric_display_value(row: dict[str, str]) -> str:
    value = str(row.get("metric_value", "")).strip() or NOT_AVAILABLE
    if row.get("availability_status") != AVAILABLE:
        return value
    unit = str(row.get("metric_unit", "")).strip()
    if unit == "EUR":
        return f"{value} EUR"
    if unit == "PCT":
        return f"{value}%"
    return value


def build_section_rows(metric_rows: list[dict[str, str]], config: dict[str, Any], group_statuses: dict[str, str]) -> list[dict[str, str]]:
    display_order_map = {str(group["metric_group"]): int(group["display_order"]) for group in config["groups"]}
    spec_by_name = {str(spec["metric_name"]): spec for spec in config["metrics"]}
    rows: list[dict[str, str]] = []
    for index, metric_row in enumerate(metric_rows, start=1):
        group_name = metric_row["metric_group"]
        base_order = display_order_map.get(group_name, 99) * 100
        spec = spec_by_name.get(metric_row["metric_name"], {})
        rows.append(
            {
                "section_name": group_name,
                "block_status": group_statuses.get(group_name, NOT_AVAILABLE),
                "metric_name": metric_row["metric_name"],
                "display_order": str(base_order + index),
                "display_label": str(spec.get("display_label", metric_row["metric_name"])),
                "value_display": metric_display_value(metric_row),
                "data_quality_flag": metric_row["data_quality_flag"],
            }
        )
    return rows


def build_summary_row(
    metric_rows: list[dict[str, str]],
    group_statuses: dict[str, str],
    derived_metrics: dict[str, dict[str, dict[str, str]]],
    sources: dict[str, SourceTable],
) -> dict[str, str]:
    metric_index = {row["metric_name"]: row for row in metric_rows}
    snapshot_date = derived_metrics.get("positions", {}).get("snapshot_date", {}).get("value", "")
    if not snapshot_date:
        snapshot_date = metric_index.get("portfolio_as_of_date", {}).get("metric_value", "")
    if not snapshot_date and sources["performance_summary"].rows:
        snapshot_date = str(sources["performance_summary"].rows[0].get("as_of_date", "")).strip()

    return {
        "snapshot_date": snapshot_date,
        "performance_source_date": metric_index.get("performance_source_date", {}).get("metric_value", NOT_AVAILABLE),
        "cost_tax_source_date": metric_index.get("cost_tax_source_date", {}).get("metric_value", NOT_AVAILABLE),
        "cross_source_data_quality_flag": metric_index.get("cross_source_data_quality_flag", {}).get("metric_value", NOT_AVAILABLE),
        "dashboard_data_quality_flag": metric_index.get("dashboard_data_quality_flag", {}).get("metric_value", NOT_AVAILABLE),
        "portfolio_measurement_mode": derived_metrics.get("positions", {}).get("portfolio_measurement_mode", {}).get("value", NOT_AVAILABLE),
        "performance_measurement_mode": metric_index.get("performance_measurement_mode", {}).get("metric_value", NOT_AVAILABLE),
        "ledger_measurement_mode": metric_index.get("ledger_measurement_mode", {}).get("metric_value", NOT_AVAILABLE),
        "total_assets": metric_index.get("total_assets", {}).get("metric_value", NOT_AVAILABLE),
        "weighted_buy_score": metric_index.get("weighted_buy_score", {}).get("metric_value", NOT_AVAILABLE),
        "active_return": metric_index.get("active_return", {}).get("metric_value", NOT_AVAILABLE),
        "total_fees": metric_index.get("total_fees", {}).get("metric_value", NOT_AVAILABLE),
        "total_taxes": metric_index.get("total_taxes", {}).get("metric_value", NOT_AVAILABLE),
        "notes_count": metric_index.get("methodology_notes_count", {}).get("metric_value", "0"),
        "missing_block_count": metric_index.get("missing_block_count", {}).get("metric_value", str(sum(1 for group in PRIMARY_GROUPS if group_statuses.get(group) == NOT_AVAILABLE))),
    }


def build_alerts(metric_rows: list[dict[str, str]], group_statuses: dict[str, str], config: dict[str, Any]) -> list[str]:
    metric_index = {row["metric_name"]: row for row in metric_rows}
    alerts: list[str] = []

    exit_review_count = to_float(metric_index.get("exit_review_count", {}).get("metric_value", "0"))
    if exit_review_count > 0.0:
        alerts.append(f"EXIT_REVIEW-Bestandspositionen offen: {int(exit_review_count)}.")

    reduce_count = to_float(metric_index.get("reduce_count", {}).get("metric_value", "0"))
    if reduce_count > 0.0:
        alerts.append(f"REDUCE-Positionen offen: {int(reduce_count)}.")

    cash_weight = to_float(metric_index.get("cash_weight", {}).get("metric_value", "0"))
    if cash_weight >= to_float(config["alert_rules"].get("high_cash_weight_threshold_pct", 25.0)):
        alerts.append(f"Cash-Anteil hoch: {format_optional_number(cash_weight)}%.")

    if metric_index.get("performance_measurement_mode", {}).get("metric_value") == SNAPSHOT_ONLY:
        alerts.append("Performance-Block ist nur im Modus SNAPSHOT_ONLY verfuegbar.")

    if metric_index.get("ledger_measurement_mode", {}).get("metric_value") == "DOCUMENT_SUMMARY_ONLY":
        alerts.append("Cost-/Tax-Block basiert nur auf DOCUMENT_SUMMARY_ONLY.")

    cross_source_flag = metric_index.get("cross_source_data_quality_flag", {}).get("metric_value", "")
    if STALE_PERFORMANCE_SOURCE in cross_source_flag:
        alerts.append(
            "Performance-Quellstichtag ist aelter als der Snapshot-Stichtag: "
            f"{metric_index.get('performance_source_date', {}).get('metric_value', NOT_AVAILABLE)}."
        )
    if STALE_COST_TAX_SOURCE in cross_source_flag:
        alerts.append(
            "Cost-/Tax-Quellstichtag ist aelter als der Snapshot-Stichtag: "
            f"{metric_index.get('cost_tax_source_date', {}).get('metric_value', NOT_AVAILABLE)}."
        )

    partial_or_missing = sum(1 for group in PRIMARY_GROUPS if group_statuses.get(group) in {PARTIAL, NOT_AVAILABLE})
    if partial_or_missing >= int(config["alert_rules"].get("multiple_partial_blocks_threshold", 2)):
        alerts.append(f"Mehrere KPI-Bloecke sind nur PARTIAL oder NOT_AVAILABLE: {partial_or_missing}.")

    if not alerts:
        alerts.append("Keine zusaetzlichen Dashboard-Alerts aus den konfigurierten Guardrails.")
    return alerts


def build_report_text(
    summary_row: dict[str, str],
    metric_rows: list[dict[str, str]],
    section_rows: list[dict[str, str]],
    group_statuses: dict[str, str],
    alerts: list[str],
) -> str:
    metric_index = {row["metric_name"]: row for row in metric_rows}
    sections_by_name: dict[str, list[dict[str, str]]] = {}
    for row in section_rows:
        sections_by_name.setdefault(row["section_name"], []).append(row)
    unique_sources = sorted({row["source_file"] for row in metric_rows if str(row.get("source_file", "")).strip()})

    def section_lines(section_name: str) -> list[str]:
        lines = [f"## {section_name} ({group_statuses.get(section_name, NOT_AVAILABLE)})"]
        for row in sections_by_name.get(section_name, []):
            lines.append(f"- {row['display_label']}: {row['value_display']} [{row['data_quality_flag']}]")
        if not sections_by_name.get(section_name):
            lines.append("- Keine strukturierten KPI-Quellen verfuegbar.")
        return lines

    lines = [
        "# KPI-Dashboard",
        "",
        f"Stichtag: {summary_row.get('snapshot_date', '') or NOT_AVAILABLE}",
        "",
        "Kurzmethodik:",
        "- Das Dashboard konsolidiert strukturierte CSV-Artefakte aus Snapshot, Score, Performance und Cost/Tax.",
        "- Markdown-Reports werden nicht als primaere KPI-Quelle verwendet.",
        "- Fehlende oder unzureichende Inputs bleiben explizit als NOT_AVAILABLE oder INSUFFICIENT_HISTORY sichtbar.",
        "",
        "## Alerts / Hinweise",
    ]
    lines.extend(f"- {alert}" for alert in alerts)
    lines.append("")
    lines.extend(section_lines("Portfolio / Struktur"))
    lines.append("")
    lines.extend(section_lines("Score / Fundamentals"))
    lines.append("")
    lines.extend(section_lines("Benchmark / Performance"))
    lines.append("")
    lines.extend(section_lines("Kosten / Steuern"))
    lines.append("")
    lines.extend(section_lines("Datenqualitaet / Methodik"))
    lines.append("")
    lines.append("## Datenqualitaet / offene Luecken")
    lines.append(f"- Snapshot-Stichtag: {summary_row.get('snapshot_date', NOT_AVAILABLE)}")
    lines.append(f"- Performance-Quellstichtag: {summary_row.get('performance_source_date', NOT_AVAILABLE)}")
    lines.append(f"- Cost-/Tax-Quellstichtag: {summary_row.get('cost_tax_source_date', NOT_AVAILABLE)}")
    lines.append(f"- Cross-Source-Date-Qualitaet: {summary_row.get('cross_source_data_quality_flag', NOT_AVAILABLE)}")
    lines.append(f"- Dashboard-Datenqualitaet: {metric_index.get('dashboard_data_quality_flag', {}).get('metric_value', NOT_AVAILABLE)}")
    lines.append(f"- Fehlende Hauptbloecke: {metric_index.get('missing_block_count', {}).get('metric_value', '0')}")
    lines.append(f"- Methodik-Hinweise: {metric_index.get('methodology_notes_count', {}).get('metric_value', '0')}")
    lines.append("")
    lines.append("## Quellen")
    if unique_sources:
        lines.extend(f"- {source}" for source in unique_sources)
    else:
        lines.append("- Keine CSV-Quellen geladen.")
    return "\n".join(lines) + "\n"


def run_dashboard_engine(
    positions_path: str = DEFAULT_POSITIONS_PATH,
    scores_path: str = DEFAULT_SCORES_PATH,
    holdings_path: str = DEFAULT_HOLDINGS_PATH,
    score_audit_path: str = DEFAULT_SCORE_AUDIT_PATH,
    coverage_path: str = DEFAULT_COVERAGE_PATH,
    performance_kpis_path: str = DEFAULT_PERFORMANCE_KPIS_PATH,
    performance_summary_path: str = DEFAULT_PERFORMANCE_SUMMARY_PATH,
    performance_comparison_path: str = DEFAULT_PERFORMANCE_COMPARISON_PATH,
    cost_tax_kpis_path: str = DEFAULT_COST_TAX_KPIS_PATH,
    cost_tax_summary_path: str = DEFAULT_COST_TAX_SUMMARY_PATH,
    config_path: str = DEFAULT_CONFIG_PATH,
    kpi_output: str = DEFAULT_KPI_OUTPUT,
    sections_output: str = DEFAULT_SECTIONS_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
    watchlist_path: str = DEFAULT_WATCHLIST_PATH,
    savings_plan_input: str = DEFAULT_SAVINGS_PLAN_INPUT,
    universe_output: str = DEFAULT_UNIVERSE_OUTPUT,
) -> dict[str, Any]:
    config = load_yaml_config(config_path)
    unavailable_values = {str(value).strip() for value in config["data_quality_rules"]["unavailable_values"]}

    sources = {
        "positions": load_optional_source("positions", positions_path),
        "scores": load_optional_source("scores", scores_path),
        "holdings": load_optional_source("holdings", holdings_path),
        "watchlist": load_optional_source("watchlist", watchlist_path),
        "score_audit": load_optional_source("score_audit", score_audit_path),
        "coverage": load_optional_coverage_source("coverage", coverage_path),
        "performance_kpis": load_optional_source("performance_kpis", performance_kpis_path),
        "performance_summary": load_optional_source("performance_summary", performance_summary_path),
        "performance_comparison": load_optional_source("performance_comparison", performance_comparison_path),
        "cost_tax_kpis": load_optional_source("cost_tax_kpis", cost_tax_kpis_path),
        "cost_tax_summary": load_optional_source("cost_tax_summary", cost_tax_summary_path),
        "dashboard": SourceTable(source_key="dashboard", path_value="", rows=[], exists=True),
    }
    metric_indexes = {
        source_key: build_metric_index(source.rows, source.path_value or source_key)
        for source_key, source in sources.items()
    }
    derived_metrics = {
        "positions": derive_positions_metrics(sources["positions"]),
        "scores": derive_scores_metrics(sources["scores"]),
        "holdings": derive_holdings_metrics(sources["holdings"]),
        "score_audit": derive_score_audit_metrics(sources["score_audit"]),
        "coverage": derive_coverage_metrics(sources["coverage"]),
        "dashboard": {},
    }

    metric_rows: list[dict[str, str]] = []
    deferred_specs: list[dict[str, Any]] = []
    for spec in config["metrics"]:
        if skip_missing_optional_coverage_metric(spec, sources):
            continue
        if str(spec["metric_name"]) in DASHBOARD_DERIVED_METRICS:
            deferred_specs.append(spec)
            continue
        metric_rows.append(resolve_metric_from_priority(spec, sources, derived_metrics, metric_indexes, unavailable_values))

    preliminary_group_statuses = build_group_statuses(metric_rows, config)
    derived_metrics["dashboard"] = build_dashboard_derived_metrics(metric_rows, preliminary_group_statuses, sources, derived_metrics, metric_indexes)
    for spec in deferred_specs:
        metric_rows.append(resolve_metric_from_priority(spec, sources, derived_metrics, metric_indexes, unavailable_values))

    order_map = {str(spec["metric_name"]): index for index, spec in enumerate(config["metrics"])}
    metric_rows.sort(key=lambda row: order_map.get(row["metric_name"], 999))
    group_statuses = build_group_statuses(metric_rows, config)
    section_rows = build_section_rows(metric_rows, config, group_statuses)
    summary_row = build_summary_row(metric_rows, group_statuses, derived_metrics, sources)
    alerts = build_alerts(metric_rows, group_statuses, config)
    report_text = build_report_text(summary_row, metric_rows, section_rows, group_statuses, alerts)
    savings_plan_rows = load_savings_plan_rows(savings_plan_input)
    universe_rows = build_universe_section(
        positions_rows=sources["positions"].rows,
        holdings_rows=sources["holdings"].rows,
        scores_rows=sources["scores"].rows,
        watchlist_rows=sources["watchlist"].rows,
        savings_plan_rows=savings_plan_rows,
    )

    write_csv_rows(kpi_output, DASHBOARD_KPI_FIELDS, metric_rows)
    write_csv_rows(sections_output, DASHBOARD_SECTION_FIELDS, section_rows)
    write_csv_rows(summary_output, DASHBOARD_SUMMARY_FIELDS, [summary_row])
    universe_path = write_universe_csv(universe_output, universe_rows)
    report_path = ensure_parent_dir(report_output)
    report_path.write_text(report_text, encoding="utf-8")

    return {
        "metric_rows": metric_rows,
        "section_rows": section_rows,
        "summary_row": summary_row,
        "universe_rows": universe_rows,
        "universe_path": universe_path,
        "group_statuses": group_statuses,
        "alerts": alerts,
        "report_path": report_path,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a consolidated KPI dashboard from processed CSV artifacts.")
    parser.add_argument("--positions", default=DEFAULT_POSITIONS_PATH, help="Positions snapshot CSV.")
    parser.add_argument("--scores", default=DEFAULT_SCORES_PATH, help="Company scores CSV.")
    parser.add_argument("--holdings", default=DEFAULT_HOLDINGS_PATH, help="Holdings action table CSV.")
    parser.add_argument("--watchlist", default=DEFAULT_WATCHLIST_PATH, help="Watchlist ranked CSV for Universe consolidation.")
    parser.add_argument("--savings-plan-input", default=DEFAULT_SAVINGS_PLAN_INPUT, help="Read-only savings plan registry CSV for Universe consolidation.")
    parser.add_argument("--score-audit", default=DEFAULT_SCORE_AUDIT_PATH, help="Score audit CSV.")
    parser.add_argument("--coverage", default=DEFAULT_COVERAGE_PATH, help="Optional personal fundamentals coverage CSV.")
    parser.add_argument("--performance-kpis", default=DEFAULT_PERFORMANCE_KPIS_PATH, help="Performance KPI CSV.")
    parser.add_argument("--performance-summary", default=DEFAULT_PERFORMANCE_SUMMARY_PATH, help="Performance summary CSV.")
    parser.add_argument("--performance-comparison", default=DEFAULT_PERFORMANCE_COMPARISON_PATH, help="Performance comparison CSV.")
    parser.add_argument("--cost-tax-kpis", default=DEFAULT_COST_TAX_KPIS_PATH, help="Cost/tax KPI CSV.")
    parser.add_argument("--cost-tax-summary", default=DEFAULT_COST_TAX_SUMMARY_PATH, help="Cost/tax summary CSV.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Dashboard KPI config.")
    parser.add_argument("--kpi-output", default=DEFAULT_KPI_OUTPUT, help="Consolidated KPI output CSV.")
    parser.add_argument("--sections-output", default=DEFAULT_SECTIONS_OUTPUT, help="Dashboard sections output CSV.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT, help="Dashboard summary output CSV.")
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT, help="Dashboard markdown report output.")
    parser.add_argument("--universe-output", default=DEFAULT_UNIVERSE_OUTPUT, help="Dashboard Universe section output CSV.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dashboard_engine(
        positions_path=args.positions,
        scores_path=args.scores,
        holdings_path=args.holdings,
        watchlist_path=args.watchlist,
        savings_plan_input=args.savings_plan_input,
        score_audit_path=args.score_audit,
        coverage_path=args.coverage,
        performance_kpis_path=args.performance_kpis,
        performance_summary_path=args.performance_summary,
        performance_comparison_path=args.performance_comparison,
        cost_tax_kpis_path=args.cost_tax_kpis,
        cost_tax_summary_path=args.cost_tax_summary,
        config_path=args.config,
        kpi_output=args.kpi_output,
        sections_output=args.sections_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
        universe_output=args.universe_output,
    )


if __name__ == "__main__":
    main()
