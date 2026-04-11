from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, load_yaml_config, read_csv_rows, require_columns, require_non_blank_fields, round2, to_float, write_csv_rows
from src.portfolio_rules import classify_sleeve, compute_cash_value, compute_portfolio_value

SNAPSHOT_ONLY = "SNAPSHOT_ONLY"
PARTIAL_HISTORY = "PARTIAL_HISTORY"
FULL_HISTORY = "FULL_HISTORY"

SNAPSHOT_COMPARISON = "SNAPSHOT_COMPARISON"
SIMPLE_PERIOD_RETURN = "SIMPLE_PERIOD_RETURN"

NOT_AVAILABLE = "NOT_AVAILABLE"
INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
UNKNOWN_OR_ZERO_ASSUMED = "UNKNOWN_OR_ZERO_ASSUMED"
OK_FLAG = "OK"
STALE_BENCHMARK = "STALE_BENCHMARK"
BENCHMARK_STALENESS_THRESHOLD_DAYS = 2

BENCHMARK_NORMALIZED_FIELDS = [
    "date",
    "benchmark_name",
    "benchmark_symbol",
    "currency",
    "close",
    "adjusted_close",
    "total_return_index",
    "benchmark_return_basis_used",
    "benchmark_reference_value",
    "data_quality_flag",
    "notes",
]

PORTFOLIO_TIMESERIES_FIELDS = [
    "date",
    "portfolio_nav_eur",
    "portfolio_value_eur",
    "cash_value_eur",
    "net_external_cash_flow_eur",
    "source_name",
    "notes",
]

PERFORMANCE_SUMMARY_FIELDS = [
    "as_of_date",
    "benchmark_reference_end_date",
    "benchmark_staleness_days",
    "measurement_mode",
    "method_used",
    "benchmark_name",
    "benchmark_symbol",
    "benchmark_return_basis_used",
    "portfolio_value_eur",
    "cash_value_eur",
    "portfolio_nav_eur",
    "invested_assets_eur",
    "current_cash_weight",
    "current_equity_weight",
    "portfolio_timeseries_points",
    "net_cash_flow_assumption",
    "data_quality_flag",
    "notes",
]

PERFORMANCE_COMPARISON_FIELDS = [
    "period_start",
    "period_end",
    "as_of_date",
    "benchmark_reference_end_date",
    "benchmark_staleness_days",
    "portfolio_nav_start_eur",
    "portfolio_nav_end_eur",
    "benchmark_reference_start",
    "benchmark_reference_end",
    "portfolio_return_period",
    "benchmark_return_period",
    "active_return",
    "measurement_mode",
    "method_used",
    "benchmark_name",
    "benchmark_return_basis_used",
    "net_cash_flow_assumption",
    "data_quality_flag",
    "notes",
]

PERFORMANCE_KPI_FIELDS = [
    "metric_name",
    "metric_value",
    "metric_unit",
    "measurement_mode",
    "method_used",
    "time_window",
    "data_quality_flag",
    "notes",
]


@dataclass(frozen=True)
class PortfolioPoint:
    date: date
    portfolio_nav_eur: float
    portfolio_value_eur: float
    cash_value_eur: float
    net_external_cash_flow_eur: str
    source_name: str
    notes: str


def parse_iso_date(value: Any, field_name: str) -> date:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"Missing required date field: {field_name}")
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Invalid date '{text}' in field {field_name}; expected YYYY-MM-DD") from exc


def format_optional_number(value: Any) -> str:
    if value in ("", None):
        return ""
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ""
        return str(round2(to_float(stripped)))
    return str(round2(float(value)))


def normalize_measurement_mode(requested_mode: str, points: list[PortfolioPoint]) -> str:
    if requested_mode == "snapshot":
        return SNAPSHOT_ONLY
    if requested_mode == "period":
        if len(points) < 2:
            raise ValueError("measurement mode 'period' requires at least 2 explicit portfolio time points.")
        return PARTIAL_HISTORY
    if len(points) < 2:
        return SNAPSHOT_ONLY
    if len(points) < 13:
        return PARTIAL_HISTORY
    return FULL_HISTORY


def derive_snapshot_point(positions_rows: list[dict[str, str]]) -> PortfolioPoint:
    require_columns(
        positions_rows,
        ["portfolio_date", "market_value_eur", "asset_type", "sleeve", "source_name"],
        "positions snapshot",
    )
    non_blank_dates = sorted(
        {
            parse_iso_date(str(row.get("portfolio_date", "")).strip(), "portfolio_date")
            for row in positions_rows
            if str(row.get("portfolio_date", "")).strip()
        }
    )
    if not non_blank_dates:
        raise ValueError("positions snapshot must contain at least one non-blank portfolio_date for performance measurement.")
    snapshot_date = non_blank_dates[-1]
    portfolio_value = compute_portfolio_value(positions_rows)
    cash_value = compute_cash_value(positions_rows)
    nav = round2(portfolio_value + cash_value)
    source_name = str(next((row.get("source_name", "") for row in positions_rows if str(row.get("source_name", "")).strip()), "positions_snapshot"))
    notes = "Derived from positions snapshot; no additional historical points inferred."
    if len(non_blank_dates) > 1:
        notes += " Snapshot contains mixed portfolio_date values; latest date is used as as-of anchor."
    return PortfolioPoint(
        date=snapshot_date,
        portfolio_nav_eur=nav,
        portfolio_value_eur=portfolio_value,
        cash_value_eur=cash_value,
        net_external_cash_flow_eur="",
        source_name=source_name,
        notes=notes,
    )


def load_portfolio_timeseries(path_value: str) -> list[PortfolioPoint]:
    rows = read_csv_rows(path_value)
    require_columns(rows, ["date", "portfolio_nav_eur"], f"portfolio timeseries ({path_value})")
    require_non_blank_fields(rows, ["date", "portfolio_nav_eur"], f"portfolio timeseries ({path_value})")
    seen_dates: set[date] = set()
    points: list[PortfolioPoint] = []
    for row in rows:
        point_date = parse_iso_date(row.get("date"), "date")
        if point_date in seen_dates:
            raise ValueError(f"portfolio timeseries ({path_value}) contains duplicate date: {point_date.isoformat()}")
        seen_dates.add(point_date)
        nav = round2(to_float(row.get("portfolio_nav_eur")))
        portfolio_value = row.get("portfolio_value_eur")
        cash_value = row.get("cash_value_eur")
        cash = round2(to_float(cash_value)) if str(cash_value or "").strip() else 0.0
        invested = round2(to_float(portfolio_value)) if str(portfolio_value or "").strip() else round2(nav - cash)
        points.append(
            PortfolioPoint(
                date=point_date,
                portfolio_nav_eur=nav,
                portfolio_value_eur=invested,
                cash_value_eur=cash,
                net_external_cash_flow_eur=str(row.get("net_external_cash_flow_eur", "")).strip(),
                source_name=str(row.get("source_name", "")).strip(),
                notes=str(row.get("notes", "")).strip(),
            )
        )
    return sorted(points, key=lambda point: point.date)


def select_benchmark_basis(config: dict[str, Any], rows: list[dict[str, str]]) -> tuple[str, str]:
    priority = list(config.get("return_basis_priority", ["total_return_index", "adjusted_close", "close"]))
    for basis_name in priority:
        column_name = str(config.get(f"{basis_name}_column", basis_name)).strip()
        if column_name and any(str(row.get(column_name, "")).strip() for row in rows):
            return basis_name, column_name
    raise ValueError("benchmark input does not contain any usable return basis column.")


def validate_global_benchmark_basis_rows(rows: list[dict[str, str]], date_column: str, basis_name: str, basis_column: str) -> None:
    for index, row in enumerate(rows, start=2):
        raw_value = str(row.get(basis_column, "")).strip()
        row_date = str(row.get(date_column, "")).strip() or f"row {index}"
        if not raw_value:
            raise ValueError(
                f"benchmark timeseries missing globally selected basis '{basis_name}' "
                f"for date {row_date} (column: {basis_column})"
            )
        numeric_value = to_float(raw_value, float("nan"))
        if not math.isfinite(numeric_value):
            raise ValueError(
                f"benchmark timeseries has non-numeric globally selected basis '{basis_name}' "
                f"for date {row_date} (column: {basis_column})"
            )


def normalize_benchmark_timeseries(rows: list[dict[str, str]], config: dict[str, Any]) -> list[dict[str, str]]:
    date_column = str(config.get("date_column", "date"))
    benchmark_name = str(config.get("benchmark_name", ""))
    benchmark_symbol = str(config.get("benchmark_symbol", ""))
    benchmark_currency = str(config.get("benchmark_currency", ""))
    source_name = str(config.get("source_name", ""))
    require_columns(rows, [date_column, str(config.get("close_column", "close"))], "benchmark timeseries")
    require_non_blank_fields(rows, [date_column], "benchmark timeseries")
    basis_name, basis_column = select_benchmark_basis(config, rows)
    validate_global_benchmark_basis_rows(rows, date_column, basis_name, basis_column)

    seen_dates: set[date] = set()
    normalized: list[dict[str, str]] = []
    for row in rows:
        point_date = parse_iso_date(row.get(date_column), date_column)
        if point_date in seen_dates:
            raise ValueError(f"benchmark timeseries contains duplicate date: {point_date.isoformat()}")
        seen_dates.add(point_date)
        currency = str(row.get("currency", benchmark_currency)).strip() or benchmark_currency
        quality_flags: list[str] = []
        notes: list[str] = []
        if basis_name == "close":
            quality_flags.append(config["data_quality_policy"]["price_only_flag"])
            notes.append("Benchmark uses close prices because total return index and adjusted close are unavailable.")
        if currency and benchmark_currency and currency != benchmark_currency:
            quality_flags.append(config["data_quality_policy"]["currency_mismatch_flag"])
            notes.append("Benchmark row currency differs from configured benchmark currency.")
        reference_value = round2(to_float(row.get(basis_column)))
        normalized.append(
            {
                "date": point_date.isoformat(),
                "benchmark_name": str(row.get("benchmark_name", "")).strip() or benchmark_name,
                "benchmark_symbol": str(row.get("benchmark_symbol", "")).strip() or benchmark_symbol,
                "currency": currency,
                "close": format_optional_number(row.get(config.get("close_column", "close"))),
                "adjusted_close": format_optional_number(row.get(config.get("adjusted_close_column", "adjusted_close"))),
                "total_return_index": format_optional_number(row.get(config.get("total_return_index_column", "total_return_index"))),
                "benchmark_return_basis_used": basis_name,
                "benchmark_reference_value": str(reference_value),
                "data_quality_flag": "|".join(quality_flags) if quality_flags else OK_FLAG,
                "notes": " ".join(notes).strip() or f"Normalized from local benchmark CSV source {source_name}.",
            }
        )
    return sorted(normalized, key=lambda row: row["date"])


def choose_benchmark_row_for_date(rows: list[dict[str, str]], target_date: date) -> dict[str, str] | None:
    eligible = [row for row in rows if parse_iso_date(row.get("date"), "date") <= target_date]
    if not eligible:
        return None
    return eligible[-1]


def compute_benchmark_staleness(portfolio_as_of_date: date, benchmark_row: dict[str, str]) -> tuple[str, str, str]:
    benchmark_end_date = parse_iso_date(benchmark_row.get("date"), "date")
    staleness_days = max((portfolio_as_of_date - benchmark_end_date).days, 0)
    stale_flag = STALE_BENCHMARK if staleness_days >= BENCHMARK_STALENESS_THRESHOLD_DAYS else OK_FLAG
    return benchmark_end_date.isoformat(), str(staleness_days), stale_flag


def build_portfolio_timeseries(
    positions_rows: list[dict[str, str]],
    explicit_timeseries_path: str | None,
) -> list[PortfolioPoint]:
    snapshot_point = derive_snapshot_point(positions_rows)
    if not explicit_timeseries_path:
        return [snapshot_point]
    explicit_points = load_portfolio_timeseries(explicit_timeseries_path)
    if not explicit_points:
        return [snapshot_point]
    latest_explicit_date = explicit_points[-1].date
    if latest_explicit_date > snapshot_point.date:
        raise ValueError(
            "explicit portfolio timeseries cannot extend beyond positions snapshot "
            f"(snapshot_as_of_date={snapshot_point.date.isoformat()}, "
            f"latest_portfolio_timeseries_date={latest_explicit_date.isoformat()})"
        )
    if explicit_points[-1].date != snapshot_point.date:
        explicit_points.append(snapshot_point)
    elif explicit_points[-1].portfolio_nav_eur != snapshot_point.portfolio_nav_eur:
        explicit_points[-1] = snapshot_point
    return sorted(explicit_points, key=lambda point: point.date)


def pct_return(start_value: float, end_value: float) -> float | None:
    if not math.isfinite(start_value) or start_value <= 0.0:
        return None
    return round2(((end_value / start_value) - 1.0) * 100.0)


def compute_snapshot_kpis(snapshot_point: PortfolioPoint, measurement_mode: str, method_used: str) -> list[dict[str, str]]:
    nav = snapshot_point.portfolio_nav_eur
    cash_weight = round2((snapshot_point.cash_value_eur / nav) * 100.0) if nav else 0.0
    equity_weight = round2((snapshot_point.portfolio_value_eur / nav) * 100.0) if nav else 0.0
    metrics = [
        ("portfolio_nav_eur", snapshot_point.portfolio_nav_eur, "EUR", "", OK_FLAG, "Current portfolio NAV from positions snapshot."),
        ("portfolio_value_eur", snapshot_point.portfolio_value_eur, "EUR", "", OK_FLAG, "Invested non-cash assets from positions snapshot."),
        ("cash_value_eur", snapshot_point.cash_value_eur, "EUR", "", OK_FLAG, "Cash positions from positions snapshot."),
        ("invested_assets_eur", snapshot_point.portfolio_value_eur, "EUR", "", OK_FLAG, "Alias for invested non-cash assets."),
        ("current_cash_weight", cash_weight, "PCT", "", OK_FLAG, "Cash divided by portfolio NAV."),
        ("current_equity_weight", equity_weight, "PCT", "", OK_FLAG, "Invested non-cash assets divided by portfolio NAV."),
    ]
    unavailable_metrics = [
        "rolling_return_1m",
        "rolling_return_3m",
        "rolling_return_6m",
        "rolling_return_12m",
        "max_drawdown",
        "volatility",
    ]
    rows = [
        {
            "metric_name": name,
            "metric_value": str(round2(value)),
            "metric_unit": unit,
            "measurement_mode": measurement_mode,
            "method_used": method_used,
            "time_window": window,
            "data_quality_flag": flag,
            "notes": notes,
        }
        for name, value, unit, window, flag, notes in metrics
    ]
    for metric_name in unavailable_metrics:
        rows.append(
            {
                "metric_name": metric_name,
                "metric_value": INSUFFICIENT_HISTORY,
                "metric_unit": "",
                "measurement_mode": measurement_mode,
                "method_used": method_used,
                "time_window": metric_name.replace("rolling_return_", "").upper(),
                "data_quality_flag": INSUFFICIENT_HISTORY,
                "notes": "Requires explicit fuller portfolio history; not derived in Phase 2B.",
            }
        )
    return rows


def combine_quality_flags(*values: str) -> str:
    flags: list[str] = []
    for value in values:
        for flag in str(value or "").split("|"):
            cleaned = flag.strip()
            if cleaned and cleaned not in flags:
                flags.append(cleaned)
    non_ok_flags = [flag for flag in flags if flag != OK_FLAG]
    if non_ok_flags:
        return "|".join(non_ok_flags)
    return OK_FLAG


def build_comparison_row(
    measurement_mode: str,
    method_used: str,
    points: list[PortfolioPoint],
    normalized_benchmark_rows: list[dict[str, str]],
) -> dict[str, str]:
    last_point = points[-1]
    latest_benchmark = choose_benchmark_row_for_date(normalized_benchmark_rows, last_point.date)
    if latest_benchmark is None:
        raise ValueError("benchmark timeseries does not contain a row on or before the portfolio as-of date.")
    benchmark_reference_end_date, benchmark_staleness_days, stale_flag = compute_benchmark_staleness(last_point.date, latest_benchmark)

    if measurement_mode == SNAPSHOT_ONLY or len(points) < 2:
        notes = "Only one explicit portfolio snapshot is available; no period return comparison is reported."
        if stale_flag == STALE_BENCHMARK:
            notes += (
                f" Benchmark reference end date {benchmark_reference_end_date} is stale versus portfolio as-of "
                f"{last_point.date.isoformat()} ({benchmark_staleness_days} days)."
            )
        return {
            "period_start": "",
            "period_end": last_point.date.isoformat(),
            "as_of_date": last_point.date.isoformat(),
            "benchmark_reference_end_date": benchmark_reference_end_date,
            "benchmark_staleness_days": benchmark_staleness_days,
            "portfolio_nav_start_eur": "",
            "portfolio_nav_end_eur": str(last_point.portfolio_nav_eur),
            "benchmark_reference_start": "",
            "benchmark_reference_end": latest_benchmark["benchmark_reference_value"],
            "portfolio_return_period": NOT_AVAILABLE,
            "benchmark_return_period": NOT_AVAILABLE,
            "active_return": NOT_AVAILABLE,
            "measurement_mode": measurement_mode,
            "method_used": method_used,
            "benchmark_name": latest_benchmark["benchmark_name"],
            "benchmark_return_basis_used": latest_benchmark["benchmark_return_basis_used"],
            "net_cash_flow_assumption": "",
            "data_quality_flag": combine_quality_flags(latest_benchmark["data_quality_flag"], stale_flag),
            "notes": notes,
        }

    start_point = points[0]
    benchmark_start = choose_benchmark_row_for_date(normalized_benchmark_rows, start_point.date)
    if benchmark_start is None:
        raise ValueError("benchmark timeseries does not contain a row on or before the portfolio period start.")
    portfolio_return = pct_return(start_point.portfolio_nav_eur, last_point.portfolio_nav_eur)
    benchmark_return = pct_return(
        to_float(benchmark_start["benchmark_reference_value"]),
        to_float(latest_benchmark["benchmark_reference_value"]),
    )
    active_return = round2(portfolio_return - benchmark_return) if portfolio_return is not None and benchmark_return is not None else None
    net_cash_assumption = UNKNOWN_OR_ZERO_ASSUMED
    notes = "Simple period return comparison from explicit dated portfolio NAV points."
    if any(point.net_external_cash_flow_eur for point in points):
        net_cash_assumption = "EXPLICIT_CASH_FLOW_COLUMN_PRESENT_BUT_NOT_USED_FOR_TWR"
        notes += " Explicit external cash flow fields are present, but Phase 2B still avoids TWR/IRR."
    if stale_flag == STALE_BENCHMARK:
        notes += (
            f" Benchmark reference end date {benchmark_reference_end_date} is stale versus portfolio as-of "
            f"{last_point.date.isoformat()} ({benchmark_staleness_days} days)."
        )
    return {
        "period_start": start_point.date.isoformat(),
        "period_end": last_point.date.isoformat(),
        "as_of_date": last_point.date.isoformat(),
        "benchmark_reference_end_date": benchmark_reference_end_date,
        "benchmark_staleness_days": benchmark_staleness_days,
        "portfolio_nav_start_eur": str(start_point.portfolio_nav_eur),
        "portfolio_nav_end_eur": str(last_point.portfolio_nav_eur),
        "benchmark_reference_start": benchmark_start["benchmark_reference_value"],
        "benchmark_reference_end": latest_benchmark["benchmark_reference_value"],
        "portfolio_return_period": str(portfolio_return) if portfolio_return is not None else NOT_AVAILABLE,
        "benchmark_return_period": str(benchmark_return) if benchmark_return is not None else NOT_AVAILABLE,
        "active_return": str(active_return) if active_return is not None else NOT_AVAILABLE,
        "measurement_mode": measurement_mode,
        "method_used": method_used,
        "benchmark_name": latest_benchmark["benchmark_name"],
        "benchmark_return_basis_used": latest_benchmark["benchmark_return_basis_used"],
        "net_cash_flow_assumption": net_cash_assumption,
        "data_quality_flag": combine_quality_flags(benchmark_start["data_quality_flag"], latest_benchmark["data_quality_flag"], stale_flag),
        "notes": notes,
    }


def build_summary_row(
    snapshot_point: PortfolioPoint,
    comparison_row: dict[str, str],
    normalized_benchmark_rows: list[dict[str, str]],
    measurement_mode: str,
    method_used: str,
    portfolio_points: list[PortfolioPoint],
) -> dict[str, str]:
    benchmark_row = choose_benchmark_row_for_date(normalized_benchmark_rows, snapshot_point.date)
    nav = snapshot_point.portfolio_nav_eur
    cash_weight = round2((snapshot_point.cash_value_eur / nav) * 100.0) if nav else 0.0
    equity_weight = round2((snapshot_point.portfolio_value_eur / nav) * 100.0) if nav else 0.0
    notes = "Phase 2B reports only snapshot KPIs plus simple period returns when explicit dated NAV points exist."
    return {
        "as_of_date": snapshot_point.date.isoformat(),
        "benchmark_reference_end_date": comparison_row["benchmark_reference_end_date"],
        "benchmark_staleness_days": comparison_row["benchmark_staleness_days"],
        "measurement_mode": measurement_mode,
        "method_used": method_used,
        "benchmark_name": benchmark_row["benchmark_name"],
        "benchmark_symbol": benchmark_row["benchmark_symbol"],
        "benchmark_return_basis_used": benchmark_row["benchmark_return_basis_used"],
        "portfolio_value_eur": str(snapshot_point.portfolio_value_eur),
        "cash_value_eur": str(snapshot_point.cash_value_eur),
        "portfolio_nav_eur": str(snapshot_point.portfolio_nav_eur),
        "invested_assets_eur": str(snapshot_point.portfolio_value_eur),
        "current_cash_weight": str(cash_weight),
        "current_equity_weight": str(equity_weight),
        "portfolio_timeseries_points": str(len(portfolio_points)),
        "net_cash_flow_assumption": comparison_row["net_cash_flow_assumption"],
        "data_quality_flag": combine_quality_flags(comparison_row["data_quality_flag"], benchmark_row["data_quality_flag"]),
        "notes": notes,
    }


def build_portfolio_timeseries_rows(points: list[PortfolioPoint]) -> list[dict[str, str]]:
    return [
        {
            "date": point.date.isoformat(),
            "portfolio_nav_eur": str(point.portfolio_nav_eur),
            "portfolio_value_eur": str(point.portfolio_value_eur),
            "cash_value_eur": str(point.cash_value_eur),
            "net_external_cash_flow_eur": point.net_external_cash_flow_eur,
            "source_name": point.source_name,
            "notes": point.notes,
        }
        for point in points
    ]


def build_benchmark_quality_kpis(
    comparison_row: dict[str, str],
    measurement_mode: str,
    method_used: str,
) -> list[dict[str, str]]:
    return [
        {
            "metric_name": "portfolio_as_of_date",
            "metric_value": comparison_row["as_of_date"],
            "metric_unit": "DATE",
            "measurement_mode": measurement_mode,
            "method_used": method_used,
            "time_window": "",
            "data_quality_flag": comparison_row["data_quality_flag"],
            "notes": "Portfolio as-of date used for the benchmark alignment check.",
        },
        {
            "metric_name": "benchmark_reference_end_date",
            "metric_value": comparison_row["benchmark_reference_end_date"],
            "metric_unit": "DATE",
            "measurement_mode": measurement_mode,
            "method_used": method_used,
            "time_window": "",
            "data_quality_flag": comparison_row["data_quality_flag"],
            "notes": "Last benchmark date actually used for the portfolio comparison.",
        },
        {
            "metric_name": "benchmark_staleness_days",
            "metric_value": comparison_row["benchmark_staleness_days"],
            "metric_unit": "DAYS",
            "measurement_mode": measurement_mode,
            "method_used": method_used,
            "time_window": "",
            "data_quality_flag": comparison_row["data_quality_flag"],
            "notes": (
                f"Difference in calendar days between portfolio as-of and benchmark reference end date. "
                f"Flagged as {STALE_BENCHMARK} when >= {BENCHMARK_STALENESS_THRESHOLD_DAYS} days."
            ),
        },
    ]


def infer_method(measurement_mode: str) -> str:
    return SNAPSHOT_COMPARISON if measurement_mode == SNAPSHOT_ONLY else SIMPLE_PERIOD_RETURN


def build_report_text(summary_row: dict[str, str], comparison_row: dict[str, str], kpi_rows: list[dict[str, str]]) -> str:
    lines = [
        "# Performance Report",
        "",
        "## Datenlage",
        "",
        f"- Measurement Mode: {summary_row['measurement_mode']}",
        f"- Method Used: {summary_row['method_used']}",
        f"- As-of Date: {summary_row['as_of_date']}",
        f"- Benchmark: {summary_row['benchmark_name']} ({summary_row['benchmark_symbol']})",
        f"- Benchmark Return Basis Used: {summary_row['benchmark_return_basis_used']}",
        f"- Benchmark Reference End Date: {summary_row['benchmark_reference_end_date']}",
        f"- Benchmark Staleness Days: {summary_row['benchmark_staleness_days']}",
        f"- Data Quality Flag: {summary_row['data_quality_flag']}",
        f"- Net Cash Flow Assumption: {summary_row['net_cash_flow_assumption'] or NOT_AVAILABLE}",
        "",
        "## Snapshot KPIs",
        "",
        f"- Portfolio NAV: {summary_row['portfolio_nav_eur']} EUR",
        f"- Invested Assets: {summary_row['portfolio_value_eur']} EUR",
        f"- Cash: {summary_row['cash_value_eur']} EUR",
        f"- Current Equity Weight: {summary_row['current_equity_weight']}%",
        f"- Current Cash Weight: {summary_row['current_cash_weight']}%",
        "",
        "## Vergleich",
        "",
    ]
    if comparison_row["portfolio_return_period"] in {NOT_AVAILABLE, INSUFFICIENT_HISTORY, ""}:
        lines.append("- Nur Struktur-/NAV-Snapshot verfuegbar. Kein belastbarer Renditevergleich moeglich.")
    else:
        lines.extend(
            [
                f"- Period Start: {comparison_row['period_start']}",
                f"- Period End: {comparison_row['period_end']}",
                f"- Portfolio Return Period: {comparison_row['portfolio_return_period']}%",
                f"- Benchmark Return Period: {comparison_row['benchmark_return_period']}%",
                f"- Active Return: {comparison_row['active_return']}%",
            ]
        )
    lines.extend(
        [
            "",
            "## Methodische Grenzen",
            "",
            "- Phase 2B berechnet bewusst kein TIME_WEIGHTED_RETURN und kein MONEY_WEIGHTED_RETURN ohne sauberen externen Cashflow-Ledger.",
            "- `monthly_new_cash_eur` aus der Konfiguration wird nicht als realisierter historischer Cashflow unterstellt.",
            "- `avg_cost`, `cost_basis_eur` und `unrealized_pnl_eur` ersetzen keine explizite historische Performance-Zeitreihe.",
            "- Rolling Returns, Max Drawdown und Volatilitaet bleiben `INSUFFICIENT_HISTORY`, solange keine ausreichende explizite Historie vorliegt.",
            "",
            "## KPI Detail",
            "",
            "| metric_name | metric_value | metric_unit | data_quality_flag | notes |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in kpi_rows:
        lines.append(
            f"| {row['metric_name']} | {row['metric_value']} | {row['metric_unit']} | {row['data_quality_flag']} | {row['notes']} |"
        )
    return "\n".join(lines) + "\n"


def run_performance_engine(
    positions_path: str,
    benchmark_path: str,
    benchmark_config_path: str,
    comparison_output: str,
    kpi_output: str,
    report_output: str,
    portfolio_timeseries_path: str | None = None,
    summary_output: str = "data/processed/performance_summary.csv",
    normalized_benchmark_output: str = "data/processed/benchmark_timeseries_normalized.csv",
    portfolio_timeseries_output: str = "data/processed/portfolio_timeseries.csv",
    measurement_mode: str = "auto",
) -> dict[str, Path]:
    positions_rows = read_csv_rows(positions_path)
    benchmark_rows = read_csv_rows(benchmark_path)
    benchmark_config = load_yaml_config(benchmark_config_path)

    portfolio_points = build_portfolio_timeseries(positions_rows, portfolio_timeseries_path)
    normalized_mode = normalize_measurement_mode(measurement_mode, portfolio_points)
    method_used = infer_method(normalized_mode)
    normalized_benchmark_rows = normalize_benchmark_timeseries(benchmark_rows, benchmark_config)

    snapshot_point = portfolio_points[-1]
    comparison_row = build_comparison_row(normalized_mode, method_used, portfolio_points, normalized_benchmark_rows)
    summary_row = build_summary_row(snapshot_point, comparison_row, normalized_benchmark_rows, normalized_mode, method_used, portfolio_points)
    kpi_rows = compute_snapshot_kpis(snapshot_point, normalized_mode, method_used)
    kpi_rows.extend(build_benchmark_quality_kpis(comparison_row, normalized_mode, method_used))

    outputs = {
        "normalized_benchmark_output": write_csv_rows(normalized_benchmark_output, BENCHMARK_NORMALIZED_FIELDS, normalized_benchmark_rows),
        "portfolio_timeseries_output": write_csv_rows(portfolio_timeseries_output, PORTFOLIO_TIMESERIES_FIELDS, build_portfolio_timeseries_rows(portfolio_points)),
        "summary_output": write_csv_rows(summary_output, PERFORMANCE_SUMMARY_FIELDS, [summary_row]),
        "comparison_output": write_csv_rows(comparison_output, PERFORMANCE_COMPARISON_FIELDS, [comparison_row]),
        "kpi_output": write_csv_rows(kpi_output, PERFORMANCE_KPI_FIELDS, kpi_rows),
    }
    report_path = ensure_parent_dir(report_output)
    report_path.write_text(build_report_text(summary_row, comparison_row, kpi_rows), encoding="utf-8")
    outputs["report_output"] = report_path
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build benchmark and performance comparison artifacts.")
    parser.add_argument("--positions", required=True, help="Positions snapshot CSV.")
    parser.add_argument("--benchmark", required=True, help="Benchmark timeseries CSV.")
    parser.add_argument("--benchmark-config", default="configs/benchmark.yaml", help="Benchmark config path.")
    parser.add_argument("--portfolio-timeseries", help="Optional explicit portfolio timeseries CSV.")
    parser.add_argument("--comparison-output", default="data/processed/performance_comparison.csv", help="Performance comparison CSV output.")
    parser.add_argument("--kpi-output", default="data/processed/performance_kpis.csv", help="Performance KPI CSV output.")
    parser.add_argument("--summary-output", default="data/processed/performance_summary.csv", help="Performance summary CSV output.")
    parser.add_argument("--normalized-benchmark-output", default="data/processed/benchmark_timeseries_normalized.csv", help="Normalized benchmark CSV output.")
    parser.add_argument("--portfolio-timeseries-output", default="data/processed/portfolio_timeseries.csv", help="Normalized portfolio timeseries CSV output.")
    parser.add_argument("--report-output", required=True, help="Markdown report output.")
    parser.add_argument("--measurement-mode", choices=["auto", "snapshot", "period"], default="auto", help="Measurement mode override.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_performance_engine(
        positions_path=args.positions,
        benchmark_path=args.benchmark,
        benchmark_config_path=args.benchmark_config,
        portfolio_timeseries_path=args.portfolio_timeseries,
        comparison_output=args.comparison_output,
        kpi_output=args.kpi_output,
        summary_output=args.summary_output,
        normalized_benchmark_output=args.normalized_benchmark_output,
        portfolio_timeseries_output=args.portfolio_timeseries_output,
        report_output=args.report_output,
        measurement_mode=args.measurement_mode,
    )


if __name__ == "__main__":
    main()
