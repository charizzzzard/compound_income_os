from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

from src.benchmark_history_engine import (
    BENCHMARK_REGISTRY_FIELDS,
    available_symbols,
    project_normalized_rows,
    read_archive_rows,
    select_benchmark_rows,
)
from src.common import ensure_parent_dir, read_csv_rows, resolve_repo_path, to_float, write_csv_rows
from src.performance_engine import (
    INSUFFICIENT_HISTORY,
    NOT_AVAILABLE,
    OK_FLAG,
    PortfolioPoint,
    build_comparison_row,
    build_portfolio_timeseries,
    choose_benchmark_row_for_date,
    combine_quality_flags,
    compute_benchmark_staleness,
    infer_method,
    normalize_measurement_mode,
)

DEFAULT_POSITIONS_PATH = "data/processed/personal_positions_snapshot.csv"
DEFAULT_PORTFOLIO_TIMESERIES_PATH = "data/processed/portfolio_timeseries.csv"
DEFAULT_BENCHMARK_ARCHIVE_PATH = "data/processed/benchmark_timeseries_archive.csv"
DEFAULT_BENCHMARK_REGISTRY_PATH = "data/processed/benchmark_registry.csv"
DEFAULT_BENCHMARK_CONFIG_PATH = "configs/benchmark.yaml"
DEFAULT_COMPARISON_OUTPUT = "data/processed/multi_benchmark_comparison.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/multi_benchmark_summary.csv"
DEFAULT_KPI_OUTPUT = "data/processed/multi_benchmark_kpis.csv"
DEFAULT_REPORT_OUTPUT = "reports/sample/multi_benchmark_report.md"

MULTI_BENCHMARK_COMPARISON_FIELDS = [
    "benchmark_name",
    "benchmark_symbol",
    "measurement_mode",
    "method_used",
    "period_start",
    "period_end",
    "as_of_date",
    "portfolio_nav_start_eur",
    "portfolio_nav_end_eur",
    "benchmark_reference_start",
    "benchmark_reference_end",
    "portfolio_return_period",
    "benchmark_return_period",
    "relative_performance_pct",
    "benchmark_return_basis_used",
    "benchmark_reference_end_date",
    "benchmark_staleness_days",
    "net_cash_flow_assumption",
    "data_quality_flag",
    "notes",
]

MULTI_BENCHMARK_SUMMARY_FIELDS = [
    "as_of_date",
    "measurement_mode",
    "method_used",
    "benchmarks_available",
    "benchmarks_requested",
    "benchmarks_evaluated",
    "benchmarks_restricted",
    "best_relative_benchmark_symbol",
    "best_relative_performance_pct",
    "weakest_relative_benchmark_symbol",
    "weakest_relative_performance_pct",
    "data_quality_flag",
    "notes",
]

MULTI_BENCHMARK_KPI_FIELDS = [
    "benchmark_symbol",
    "metric_name",
    "metric_value",
    "metric_unit",
    "measurement_mode",
    "method_used",
    "time_window",
    "data_quality_flag",
    "notes",
]


def read_registry_rows(path_value: str | Path) -> list[dict[str, str]]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in BENCHMARK_REGISTRY_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"benchmark registry ({path_value}) missing required columns: {missing_text}")
        rows = [
            {field: str(row.get(field, "") or "").strip() for field in BENCHMARK_REGISTRY_FIELDS}
            for row in reader
        ]
    if not rows:
        raise ValueError(f"benchmark registry ({path_value}) contains no rows.")
    return sorted(rows, key=lambda row: str(row.get("benchmark_symbol", "")).strip().upper())


def registry_by_symbol(registry_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    for row in registry_rows:
        symbol = str(row.get("benchmark_symbol", "")).strip().upper()
        if not symbol:
            raise ValueError("benchmark registry contains a row with blank benchmark_symbol.")
        if symbol in indexed:
            raise ValueError(f"benchmark registry contains duplicate benchmark_symbol={symbol}.")
        indexed[symbol] = row
    return indexed


def resolve_benchmark_selection(
    archive_rows: list[dict[str, str]],
    registry_rows: list[dict[str, str]],
    requested_symbols: list[str] | None,
) -> list[str]:
    archive_symbols = set(available_symbols(archive_rows))
    registry_symbols = set(registry_by_symbol(registry_rows))
    available = sorted(archive_symbols | registry_symbols)
    if not available:
        raise ValueError("benchmark archive and registry do not contain any benchmark_symbol rows.")

    requested = [str(symbol or "").strip().upper() for symbol in (requested_symbols or []) if str(symbol or "").strip()]
    duplicates = sorted({symbol for symbol in requested if requested.count(symbol) > 1})
    if duplicates:
        raise ValueError(f"duplicate --benchmark-symbol values are not allowed: {', '.join(duplicates)}")

    if not requested:
        if len(available) != 1:
            raise ValueError(
                "benchmark archive/registry contain multiple symbols "
                f"({', '.join(available)}); pass --benchmark-symbol for each selected series."
            )
        requested = [available[0]]

    selected = sorted(requested)
    for symbol in selected:
        if symbol not in archive_symbols:
            raise ValueError(f"benchmark archive contains no rows for benchmark_symbol={symbol}.")
        if symbol not in registry_symbols:
            raise ValueError(f"benchmark registry contains no row for benchmark_symbol={symbol}.")
    return selected


def validate_registry_against_archive(
    selected_symbols: list[str],
    registry_rows: list[dict[str, str]],
    archive_rows: list[dict[str, str]],
) -> None:
    registry_index = registry_by_symbol(registry_rows)
    for symbol in selected_symbols:
        _, symbol_rows = select_benchmark_rows(archive_rows, symbol)
        registry_row = registry_index[symbol]
        for field in ["benchmark_name", "currency", "benchmark_return_basis_used"]:
            archive_values = sorted({str(row.get(field, "")).strip() for row in symbol_rows if str(row.get(field, "")).strip()})
            registry_value = str(registry_row.get(field, "")).strip()
            if registry_value and archive_values and registry_value not in archive_values:
                raise ValueError(
                    f"benchmark registry drift for benchmark_symbol={symbol}: "
                    f"{field}={registry_value!r} not present in archive values {archive_values!r}"
                )


def is_numeric_metric(value: str) -> bool:
    text = str(value or "").strip()
    if text in {"", NOT_AVAILABLE, INSUFFICIENT_HISTORY}:
        return False
    return math.isfinite(to_float(text, float("nan")))


def build_unavailable_comparison_row(
    benchmark_symbol: str,
    registry_row: dict[str, str],
    normalized_benchmark_rows: list[dict[str, str]],
    portfolio_points: list[PortfolioPoint],
    measurement_mode: str,
    method_used: str,
    error_message: str,
) -> dict[str, str]:
    last_point = portfolio_points[-1]
    first_point = portfolio_points[0] if len(portfolio_points) >= 2 else None
    latest_benchmark = choose_benchmark_row_for_date(normalized_benchmark_rows, last_point.date)
    benchmark_reference_end_date = ""
    benchmark_staleness_days = ""
    benchmark_reference_end = ""
    quality = INSUFFICIENT_HISTORY
    benchmark_name = registry_row.get("benchmark_name", "")
    return_basis = registry_row.get("benchmark_return_basis_used", "")
    notes = f"Benchmark comparison not computed: {error_message}"

    if latest_benchmark is not None:
        benchmark_reference_end_date, benchmark_staleness_days, stale_flag = compute_benchmark_staleness(last_point.date, latest_benchmark)
        benchmark_reference_end = latest_benchmark.get("benchmark_reference_value", "")
        benchmark_name = latest_benchmark.get("benchmark_name", benchmark_name)
        return_basis = latest_benchmark.get("benchmark_return_basis_used", return_basis)
        quality = combine_quality_flags(INSUFFICIENT_HISTORY, latest_benchmark.get("data_quality_flag", ""), stale_flag)

    return {
        "benchmark_name": benchmark_name,
        "benchmark_symbol": benchmark_symbol,
        "measurement_mode": measurement_mode,
        "method_used": method_used,
        "period_start": first_point.date.isoformat() if first_point else "",
        "period_end": last_point.date.isoformat(),
        "as_of_date": last_point.date.isoformat(),
        "portfolio_nav_start_eur": str(first_point.portfolio_nav_eur) if first_point else "",
        "portfolio_nav_end_eur": str(last_point.portfolio_nav_eur),
        "benchmark_reference_start": "",
        "benchmark_reference_end": benchmark_reference_end,
        "portfolio_return_period": NOT_AVAILABLE,
        "benchmark_return_period": NOT_AVAILABLE,
        "relative_performance_pct": NOT_AVAILABLE,
        "benchmark_return_basis_used": return_basis,
        "benchmark_reference_end_date": benchmark_reference_end_date,
        "benchmark_staleness_days": benchmark_staleness_days,
        "net_cash_flow_assumption": "",
        "data_quality_flag": quality,
        "notes": notes,
    }


def build_multi_comparison_row(
    benchmark_symbol: str,
    registry_row: dict[str, str],
    portfolio_points: list[PortfolioPoint],
    normalized_benchmark_rows: list[dict[str, str]],
    measurement_mode: str,
    method_used: str,
) -> dict[str, str]:
    try:
        single_row = build_comparison_row(measurement_mode, method_used, portfolio_points, normalized_benchmark_rows)
    except ValueError as exc:
        return build_unavailable_comparison_row(
            benchmark_symbol=benchmark_symbol,
            registry_row=registry_row,
            normalized_benchmark_rows=normalized_benchmark_rows,
            portfolio_points=portfolio_points,
            measurement_mode=measurement_mode,
            method_used=method_used,
            error_message=str(exc),
        )

    return {
        "benchmark_name": single_row.get("benchmark_name", "") or registry_row.get("benchmark_name", ""),
        "benchmark_symbol": benchmark_symbol,
        "measurement_mode": single_row["measurement_mode"],
        "method_used": single_row["method_used"],
        "period_start": single_row["period_start"],
        "period_end": single_row["period_end"],
        "as_of_date": single_row["as_of_date"],
        "portfolio_nav_start_eur": single_row["portfolio_nav_start_eur"],
        "portfolio_nav_end_eur": single_row["portfolio_nav_end_eur"],
        "benchmark_reference_start": single_row["benchmark_reference_start"],
        "benchmark_reference_end": single_row["benchmark_reference_end"],
        "portfolio_return_period": single_row["portfolio_return_period"],
        "benchmark_return_period": single_row["benchmark_return_period"],
        "relative_performance_pct": single_row["active_return"],
        "benchmark_return_basis_used": single_row["benchmark_return_basis_used"] or registry_row.get("benchmark_return_basis_used", ""),
        "benchmark_reference_end_date": single_row["benchmark_reference_end_date"],
        "benchmark_staleness_days": single_row["benchmark_staleness_days"],
        "net_cash_flow_assumption": single_row["net_cash_flow_assumption"],
        "data_quality_flag": single_row["data_quality_flag"],
        "notes": single_row["notes"],
    }


def build_multi_comparison_rows(
    selected_symbols: list[str],
    registry_rows: list[dict[str, str]],
    archive_rows: list[dict[str, str]],
    portfolio_points: list[PortfolioPoint],
    measurement_mode: str,
    method_used: str,
) -> list[dict[str, str]]:
    registry_index = registry_by_symbol(registry_rows)
    comparison_rows: list[dict[str, str]] = []
    for symbol in selected_symbols:
        _, symbol_rows = select_benchmark_rows(archive_rows, symbol)
        normalized_rows = project_normalized_rows(symbol_rows)
        comparison_rows.append(
            build_multi_comparison_row(
                benchmark_symbol=symbol,
                registry_row=registry_index[symbol],
                portfolio_points=portfolio_points,
                normalized_benchmark_rows=normalized_rows,
                measurement_mode=measurement_mode,
                method_used=method_used,
            )
        )
    return sorted(comparison_rows, key=lambda row: row["benchmark_symbol"])


def numeric_relative_rows(comparison_rows: list[dict[str, str]]) -> list[tuple[float, str, dict[str, str]]]:
    rows: list[tuple[float, str, dict[str, str]]] = []
    for row in comparison_rows:
        if not is_numeric_metric(row.get("relative_performance_pct", "")):
            continue
        rows.append((to_float(row["relative_performance_pct"]), row["benchmark_symbol"], row))
    return rows


def build_summary_row(
    comparison_rows: list[dict[str, str]],
    selected_symbols: list[str],
    available_symbols_count: int,
    measurement_mode: str,
    method_used: str,
    as_of_date: str,
) -> dict[str, str]:
    numeric_rows = numeric_relative_rows(comparison_rows)
    restricted = [
        row
        for row in comparison_rows
        if row.get("data_quality_flag", OK_FLAG) != OK_FLAG or not is_numeric_metric(row.get("relative_performance_pct", ""))
    ]
    if numeric_rows:
        best_value, best_symbol, _ = sorted(numeric_rows, key=lambda item: (-item[0], item[1]))[0]
        weakest_value, weakest_symbol, _ = sorted(numeric_rows, key=lambda item: (item[0], item[1]))[0]
        notes = "Best/weakest relative performance ranks numeric rows by relative_performance_pct; ties break by benchmark_symbol."
    else:
        best_symbol = NOT_AVAILABLE
        best_value = NOT_AVAILABLE
        weakest_symbol = NOT_AVAILABLE
        weakest_value = NOT_AVAILABLE
        notes = "No benchmark produced a numeric relative_performance_pct; best/weakest ranking not computed."

    return {
        "as_of_date": as_of_date,
        "measurement_mode": measurement_mode,
        "method_used": method_used,
        "benchmarks_available": str(available_symbols_count),
        "benchmarks_requested": str(len(selected_symbols)),
        "benchmarks_evaluated": str(len(comparison_rows)),
        "benchmarks_restricted": str(len(restricted)),
        "best_relative_benchmark_symbol": best_symbol,
        "best_relative_performance_pct": str(best_value),
        "weakest_relative_benchmark_symbol": weakest_symbol,
        "weakest_relative_performance_pct": str(weakest_value),
        "data_quality_flag": combine_quality_flags(*(row["data_quality_flag"] for row in comparison_rows)),
        "notes": notes,
    }


def build_kpi_rows(
    comparison_rows: list[dict[str, str]],
    measurement_mode: str,
    method_used: str,
) -> list[dict[str, str]]:
    metric_specs = [
        ("portfolio_return_period", "PCT", "Portfolio period return from the reused single-benchmark comparison method."),
        ("benchmark_return_period", "PCT", "Benchmark period return from the reused single-benchmark comparison method."),
        ("relative_performance_pct", "PCT", "Portfolio return minus benchmark return, matching single-benchmark active_return semantics."),
        ("benchmark_staleness_days", "DAYS", "Calendar days between portfolio as-of and benchmark reference end date."),
    ]
    rows: list[dict[str, str]] = []
    for comparison_row in comparison_rows:
        for metric_name, metric_unit, notes in metric_specs:
            rows.append(
                {
                    "benchmark_symbol": comparison_row["benchmark_symbol"],
                    "metric_name": metric_name,
                    "metric_value": comparison_row.get(metric_name, ""),
                    "metric_unit": metric_unit,
                    "measurement_mode": measurement_mode,
                    "method_used": method_used,
                    "time_window": "PERIOD" if metric_name != "benchmark_staleness_days" else "",
                    "data_quality_flag": comparison_row["data_quality_flag"],
                    "notes": notes,
                }
            )
    return rows


def build_report_text(summary_row: dict[str, str], comparison_rows: list[dict[str, str]]) -> str:
    restricted_rows = [row for row in comparison_rows if row["data_quality_flag"] != OK_FLAG]
    lines = [
        "# Multi-Benchmark Performance Report",
        "",
        "## Datenlage",
        "",
        f"- As-of Date: {summary_row['as_of_date']}",
        f"- Measurement Mode: {summary_row['measurement_mode']}",
        f"- Method Used: {summary_row['method_used']}",
        f"- Benchmarks Available: {summary_row['benchmarks_available']}",
        f"- Benchmarks Evaluated: {summary_row['benchmarks_evaluated']}",
        f"- Benchmarks Restricted: {summary_row['benchmarks_restricted']}",
        f"- Data Quality Flag: {summary_row['data_quality_flag']}",
        "",
        "## Relative Entwicklung",
        "",
        f"- Beste relative Entwicklung: {summary_row['best_relative_benchmark_symbol']} ({summary_row['best_relative_performance_pct']}%)",
        f"- Schwaechste relative Entwicklung: {summary_row['weakest_relative_benchmark_symbol']} ({summary_row['weakest_relative_performance_pct']}%)",
        "",
        "## Vergleich je Benchmark",
        "",
        "| benchmark_symbol | benchmark_name | portfolio_return_period | benchmark_return_period | relative_performance_pct | benchmark_reference_end_date | staleness_days | data_quality_flag |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in comparison_rows:
        lines.append(
            "| "
            f"{row['benchmark_symbol']} | {row['benchmark_name']} | {row['portfolio_return_period']} | "
            f"{row['benchmark_return_period']} | {row['relative_performance_pct']} | "
            f"{row['benchmark_reference_end_date']} | {row['benchmark_staleness_days']} | {row['data_quality_flag']} |"
        )
    lines.extend(["", "## Eingeschraenkte Benchmark-Reihen", ""])
    if restricted_rows:
        for row in restricted_rows:
            lines.append(f"- `{row['benchmark_symbol']}`: {row['data_quality_flag']} - {row['notes']}")
    else:
        lines.append("- Keine eingeschraenkten Benchmark-Reihen.")
    lines.extend(
        [
            "",
            "## Methodik und Grenzen",
            "",
            "- Jede Benchmark-Reihe wird einzeln gegen dieselbe explizite Portfolio-Zeitreihe verglichen.",
            "- Die Semantik entspricht der Single-Benchmark-Engine: relative_performance_pct ist Portfolio-Return minus Benchmark-Return.",
            "- Es gibt keine externe API, keine FX-Schicht, keine Benchmark-Blends und keine Interpolation.",
            "- Bei mehreren verfuegbaren Symbolen ist eine explizite `--benchmark-symbol`-Auswahl erforderlich.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_multi_benchmark_performance_engine(
    positions_path: str = DEFAULT_POSITIONS_PATH,
    portfolio_timeseries_path: str | None = DEFAULT_PORTFOLIO_TIMESERIES_PATH,
    benchmark_archive_path: str = DEFAULT_BENCHMARK_ARCHIVE_PATH,
    benchmark_registry_path: str = DEFAULT_BENCHMARK_REGISTRY_PATH,
    comparison_output: str = DEFAULT_COMPARISON_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    kpi_output: str = DEFAULT_KPI_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
    benchmark_symbols: list[str] | None = None,
    measurement_mode: str = "auto",
    benchmark_config_path: str = DEFAULT_BENCHMARK_CONFIG_PATH,
) -> dict[str, Path]:
    _ = benchmark_config_path
    positions_rows = read_csv_rows(positions_path)
    portfolio_points = build_portfolio_timeseries(positions_rows, portfolio_timeseries_path)
    normalized_mode = normalize_measurement_mode(measurement_mode, portfolio_points)
    method_used = infer_method(normalized_mode)

    archive_rows = read_archive_rows(benchmark_archive_path)
    registry_rows = read_registry_rows(benchmark_registry_path)
    selected_symbols = resolve_benchmark_selection(archive_rows, registry_rows, benchmark_symbols)
    validate_registry_against_archive(selected_symbols, registry_rows, archive_rows)

    comparison_rows = build_multi_comparison_rows(
        selected_symbols=selected_symbols,
        registry_rows=registry_rows,
        archive_rows=archive_rows,
        portfolio_points=portfolio_points,
        measurement_mode=normalized_mode,
        method_used=method_used,
    )
    summary_row = build_summary_row(
        comparison_rows=comparison_rows,
        selected_symbols=selected_symbols,
        available_symbols_count=len(available_symbols(archive_rows)),
        measurement_mode=normalized_mode,
        method_used=method_used,
        as_of_date=portfolio_points[-1].date.isoformat(),
    )
    kpi_rows = build_kpi_rows(comparison_rows, normalized_mode, method_used)

    outputs = {
        "comparison_output": write_csv_rows(comparison_output, MULTI_BENCHMARK_COMPARISON_FIELDS, comparison_rows),
        "summary_output": write_csv_rows(summary_output, MULTI_BENCHMARK_SUMMARY_FIELDS, [summary_row]),
        "kpi_output": write_csv_rows(kpi_output, MULTI_BENCHMARK_KPI_FIELDS, kpi_rows),
    }
    report_path = ensure_parent_dir(report_output)
    report_path.write_text(build_report_text(summary_row, comparison_rows), encoding="utf-8")
    outputs["report_output"] = report_path
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare one portfolio timeseries against multiple archived benchmark series.")
    parser.add_argument("--positions", default=DEFAULT_POSITIONS_PATH, help="Positions snapshot CSV.")
    parser.add_argument("--portfolio-timeseries", default=DEFAULT_PORTFOLIO_TIMESERIES_PATH, help="Explicit portfolio timeseries CSV.")
    parser.add_argument("--benchmark-archive", default=DEFAULT_BENCHMARK_ARCHIVE_PATH, help="Benchmark archive CSV.")
    parser.add_argument("--benchmark-registry", default=DEFAULT_BENCHMARK_REGISTRY_PATH, help="Benchmark registry CSV.")
    parser.add_argument("--benchmark-config", default=DEFAULT_BENCHMARK_CONFIG_PATH, help="Benchmark config path; kept for CLI parity.")
    parser.add_argument("--benchmark-symbol", action="append", default=[], help="Benchmark symbol to compare; repeat for multiple symbols.")
    parser.add_argument("--comparison-output", default=DEFAULT_COMPARISON_OUTPUT, help="Multi-benchmark comparison CSV output.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT, help="Multi-benchmark summary CSV output.")
    parser.add_argument("--kpi-output", default=DEFAULT_KPI_OUTPUT, help="Multi-benchmark KPI CSV output.")
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT, help="Multi-benchmark markdown report output.")
    parser.add_argument("--measurement-mode", choices=["auto", "snapshot", "period"], default="auto", help="Measurement mode override.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_multi_benchmark_performance_engine(
        positions_path=args.positions,
        portfolio_timeseries_path=args.portfolio_timeseries,
        benchmark_archive_path=args.benchmark_archive,
        benchmark_registry_path=args.benchmark_registry,
        comparison_output=args.comparison_output,
        summary_output=args.summary_output,
        kpi_output=args.kpi_output,
        report_output=args.report_output,
        benchmark_symbols=args.benchmark_symbol,
        measurement_mode=args.measurement_mode,
        benchmark_config_path=args.benchmark_config,
    )


if __name__ == "__main__":
    main()
