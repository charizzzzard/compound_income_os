from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, load_yaml_config, read_csv_rows, resolve_repo_path, write_csv_rows
from src.performance_engine import (
    BENCHMARK_NORMALIZED_FIELDS,
    combine_quality_flags,
    normalize_benchmark_timeseries,
    parse_iso_date,
)

DEFAULT_BENCHMARK_CONFIG_PATH = "configs/benchmark.yaml"
DEFAULT_ARCHIVE_PATH = "data/processed/benchmark_timeseries_archive.csv"
DEFAULT_NORMALIZED_OUTPUT = "data/processed/benchmark_timeseries_normalized.csv"
DEFAULT_REGISTRY_OUTPUT = "data/processed/benchmark_registry.csv"
DEFAULT_ARCHIVE_SUMMARY_OUTPUT = "data/processed/benchmark_archive_summary.csv"

BENCHMARK_ARCHIVE_FIELDS = [*BENCHMARK_NORMALIZED_FIELDS, "source_name"]

BENCHMARK_REGISTRY_FIELDS = [
    "benchmark_name",
    "benchmark_symbol",
    "currency",
    "first_date",
    "last_date",
    "points_count",
    "benchmark_return_basis_used",
    "source_name",
    "data_quality_flag",
    "notes",
]

BENCHMARK_ARCHIVE_SUMMARY_FIELDS = [
    "archive_rows",
    "benchmark_symbols_count",
    "selected_benchmark_symbol",
    "normalized_rows",
    "new_rows_considered",
    "new_rows_added",
    "duplicate_rows_skipped",
    "data_quality_flag",
    "notes",
]

ARCHIVE_IDENTITY_FIELDS = ["benchmark_symbol", "date"]
SYMBOL_METADATA_FIELDS = ["benchmark_name", "currency", "benchmark_return_basis_used"]


@dataclass(frozen=True)
class BenchmarkArchiveMergeResult:
    rows: list[dict[str, str]]
    new_rows_considered: int
    new_rows_added: int
    duplicate_rows_skipped: int


def canonical_archive_row(row: dict[str, Any]) -> dict[str, str]:
    return {field: str(row.get(field, "") or "").strip() for field in BENCHMARK_ARCHIVE_FIELDS}


def archive_identity(row: dict[str, str]) -> tuple[str, str]:
    return str(row.get("benchmark_symbol", "")).strip().upper(), str(row.get("date", "")).strip()


def archive_identity_text(identity: tuple[str, str]) -> str:
    benchmark_symbol, point_date = identity
    return f"benchmark_symbol={benchmark_symbol or '<blank>'}, date={point_date or '<blank>'}"


def row_content_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "") or "").strip() for field in BENCHMARK_ARCHIVE_FIELDS)


def archive_sort_key(row: dict[str, str]) -> tuple[str, str]:
    benchmark_symbol, point_date = archive_identity(row)
    return benchmark_symbol, point_date


def validate_archive_header(fieldnames: list[str] | None, source_name: str) -> None:
    available = set(fieldnames or [])
    missing = [field for field in BENCHMARK_ARCHIVE_FIELDS if field not in available]
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"{source_name} missing required columns: {missing_text}")


def validate_archive_rows(rows: list[dict[str, str]], source_name: str) -> None:
    for index, row in enumerate(rows, start=2):
        missing_columns = [field for field in BENCHMARK_ARCHIVE_FIELDS if field not in row]
        if missing_columns:
            missing_text = ", ".join(sorted(missing_columns))
            raise ValueError(f"{source_name} row {index} missing required columns: {missing_text}")
        if not str(row.get("benchmark_symbol", "")).strip():
            raise ValueError(f"{source_name} row {index} has blank required field(s): benchmark_symbol")
        parse_iso_date(row.get("date"), "date")


def read_archive_rows(path_value: str | None) -> list[dict[str, str]]:
    if not path_value:
        return []
    path = resolve_repo_path(path_value)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        source_name = f"benchmark archive ({path_value})"
        validate_archive_header(reader.fieldnames, source_name)
        rows = [canonical_archive_row(row) for row in reader]
    validate_archive_rows(rows, source_name)
    return rows


def input_source_index(rows: list[dict[str, str]], config: dict[str, Any]) -> dict[tuple[str, str], str]:
    date_column = str(config.get("date_column", "date"))
    default_symbol = str(config.get("benchmark_symbol", "")).strip()
    default_source = str(config.get("source_name", "")).strip()
    source_by_identity: dict[tuple[str, str], str] = {}
    for row in rows:
        point_date = parse_iso_date(row.get(date_column), date_column).isoformat()
        benchmark_symbol = str(row.get("benchmark_symbol", "")).strip() or default_symbol
        source_name = str(row.get("source_name", "")).strip() or default_source
        source_by_identity[(benchmark_symbol.strip().upper(), point_date)] = source_name
    return source_by_identity


def normalize_input_rows(benchmark_input: str | None, benchmark_config_path: str) -> list[dict[str, str]]:
    if not benchmark_input:
        return []
    config = load_yaml_config(benchmark_config_path)
    rows = read_csv_rows(benchmark_input)
    normalized_rows = normalize_benchmark_timeseries(rows, config)
    source_by_identity = input_source_index(rows, config)
    archive_rows: list[dict[str, str]] = []
    for row in normalized_rows:
        archive_row = canonical_archive_row(row)
        archive_row["source_name"] = source_by_identity.get(archive_identity(archive_row), str(config.get("source_name", "")).strip())
        archive_rows.append(archive_row)
    validate_archive_rows(archive_rows, f"benchmark input ({benchmark_input})")
    return sorted(archive_rows, key=archive_sort_key)


def validate_symbol_metadata(rows: list[dict[str, str]], source_name: str) -> None:
    by_symbol: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_symbol.setdefault(str(row.get("benchmark_symbol", "")).strip().upper(), []).append(row)

    for benchmark_symbol, symbol_rows in by_symbol.items():
        for field in SYMBOL_METADATA_FIELDS:
            values = sorted({str(row.get(field, "")).strip() for row in symbol_rows if str(row.get(field, "")).strip()})
            if len(values) > 1:
                values_text = ", ".join(values)
                raise ValueError(
                    f"{source_name} has conflicting {field} for benchmark_symbol={benchmark_symbol}: {values_text}"
                )


def index_archive_rows(rows: list[dict[str, str]], source_name: str) -> dict[tuple[str, str], dict[str, str]]:
    validate_archive_rows(rows, source_name)
    validate_symbol_metadata(rows, source_name)
    indexed: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        normalized = canonical_archive_row(row)
        identity = archive_identity(normalized)
        existing = indexed.get(identity)
        if existing is None:
            indexed[identity] = normalized
            continue
        if row_content_key(existing) != row_content_key(normalized):
            raise ValueError(f"benchmark archive conflict for identity {archive_identity_text(identity)} in {source_name}")
    return indexed


def merge_archive_rows(
    existing_rows: list[dict[str, str]],
    incoming_rows: list[dict[str, str]],
) -> BenchmarkArchiveMergeResult:
    indexed = index_archive_rows(existing_rows, "existing benchmark archive")
    validate_archive_rows(incoming_rows, "incoming benchmark archive rows")
    new_rows_added = 0
    duplicate_rows_skipped = 0

    for row in incoming_rows:
        normalized = canonical_archive_row(row)
        identity = archive_identity(normalized)
        existing = indexed.get(identity)
        if existing is None:
            indexed[identity] = normalized
            new_rows_added += 1
            continue
        if row_content_key(existing) != row_content_key(normalized):
            raise ValueError(f"benchmark archive conflict for identity {archive_identity_text(identity)}")
        duplicate_rows_skipped += 1

    rows = sorted(indexed.values(), key=archive_sort_key)
    validate_symbol_metadata(rows, "merged benchmark archive")
    return BenchmarkArchiveMergeResult(
        rows=rows,
        new_rows_considered=len(incoming_rows),
        new_rows_added=new_rows_added,
        duplicate_rows_skipped=duplicate_rows_skipped,
    )


def available_symbols(rows: list[dict[str, str]]) -> list[str]:
    return sorted({str(row.get("benchmark_symbol", "")).strip().upper() for row in rows if str(row.get("benchmark_symbol", "")).strip()})


def select_benchmark_rows(rows: list[dict[str, str]], benchmark_symbol: str | None) -> tuple[str, list[dict[str, str]]]:
    symbols = available_symbols(rows)
    if not symbols:
        raise ValueError("benchmark archive does not contain any benchmark_symbol rows.")
    selected_symbol = str(benchmark_symbol or "").strip().upper()
    if not selected_symbol:
        if len(symbols) != 1:
            symbols_text = ", ".join(symbols)
            raise ValueError(f"benchmark archive contains multiple symbols ({symbols_text}); pass --benchmark-symbol.")
        selected_symbol = symbols[0]
    selected_rows = [row for row in rows if str(row.get("benchmark_symbol", "")).strip().upper() == selected_symbol]
    if not selected_rows:
        raise ValueError(f"benchmark archive contains no rows for benchmark_symbol={selected_symbol}.")
    return selected_symbol, sorted(selected_rows, key=lambda row: str(row.get("date", "")).strip())


def project_normalized_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [{field: row.get(field, "") for field in BENCHMARK_NORMALIZED_FIELDS} for row in rows]


def build_registry_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    validate_symbol_metadata(rows, "benchmark registry")
    registry_rows: list[dict[str, str]] = []
    for benchmark_symbol in available_symbols(rows):
        symbol_rows = sorted(
            [row for row in rows if str(row.get("benchmark_symbol", "")).strip().upper() == benchmark_symbol],
            key=lambda row: str(row.get("date", "")).strip(),
        )
        dates = [row["date"] for row in symbol_rows]
        source_values = sorted({row["source_name"] for row in symbol_rows if row["source_name"]})
        source_name = source_values[0] if len(source_values) == 1 else "MULTIPLE_SOURCES" if source_values else ""
        notes = ""
        if len(source_values) > 1:
            notes = f"Multiple source_name values for symbol: {', '.join(source_values)}."
        registry_rows.append(
            {
                "benchmark_name": next((row["benchmark_name"] for row in symbol_rows if row["benchmark_name"]), ""),
                "benchmark_symbol": benchmark_symbol,
                "currency": next((row["currency"] for row in symbol_rows if row["currency"]), ""),
                "first_date": dates[0],
                "last_date": dates[-1],
                "points_count": str(len(symbol_rows)),
                "benchmark_return_basis_used": next((row["benchmark_return_basis_used"] for row in symbol_rows if row["benchmark_return_basis_used"]), ""),
                "source_name": source_name,
                "data_quality_flag": combine_quality_flags(*(row["data_quality_flag"] for row in symbol_rows)),
                "notes": notes,
            }
        )
    return registry_rows


def build_archive_summary_row(
    merge_result: BenchmarkArchiveMergeResult,
    selected_symbol: str,
    selected_rows: list[dict[str, str]],
    registry_rows: list[dict[str, str]],
) -> dict[str, str]:
    quality_flag = combine_quality_flags(*(row["data_quality_flag"] for row in merge_result.rows))
    return {
        "archive_rows": str(len(merge_result.rows)),
        "benchmark_symbols_count": str(len(registry_rows)),
        "selected_benchmark_symbol": selected_symbol,
        "normalized_rows": str(len(selected_rows)),
        "new_rows_considered": str(merge_result.new_rows_considered),
        "new_rows_added": str(merge_result.new_rows_added),
        "duplicate_rows_skipped": str(merge_result.duplicate_rows_skipped),
        "data_quality_flag": quality_flag,
        "notes": "Benchmark archive uses benchmark_symbol+date identity; duplicate identity with differing normalized values fails fast.",
    }


def build_report_text(
    registry_rows: list[dict[str, str]],
    summary_row: dict[str, str],
) -> str:
    lines = [
        "# Benchmark History Report",
        "",
        "## Datenlage",
        "",
        f"- Archivzeilen: {summary_row['archive_rows']}",
        f"- Benchmark-Reihen: {summary_row['benchmark_symbols_count']}",
        f"- Ausgewaehlte Benchmark-Reihe fuer Normalized-Output: {summary_row['selected_benchmark_symbol']}",
        f"- Normalized-Output-Zeilen: {summary_row['normalized_rows']}",
        f"- Data Quality Flag: {summary_row['data_quality_flag']}",
        "",
        "## Registry",
        "",
        "| benchmark_symbol | benchmark_name | currency | first_date | last_date | points_count | basis | source_name | data_quality_flag |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in registry_rows:
        lines.append(
            "| "
            f"{row['benchmark_symbol']} | {row['benchmark_name']} | {row['currency']} | "
            f"{row['first_date']} | {row['last_date']} | {row['points_count']} | "
            f"{row['benchmark_return_basis_used']} | {row['source_name']} | {row['data_quality_flag']} |"
        )
    lines.extend(
        [
            "",
            "## Methodik und Grenzen",
            "",
            "- Das Archiv nutzt nur explizite lokale Benchmark-Zeitreihen.",
            "- Es gibt keine externe API, keine FX-Konvertierung und keine Interpolation fehlender Punkte.",
            "- `benchmark_timeseries_normalized.csv` bleibt eine explizit ausgewaehlte Einzelreihe im bestehenden Performance-Format.",
            "- Gleiche `benchmark_symbol`+`date`-Identitaet mit abweichenden normalisierten Werten wird hart abgewiesen.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_benchmark_history_engine(
    benchmark_input: str | None = None,
    benchmark_config_path: str = DEFAULT_BENCHMARK_CONFIG_PATH,
    archive_path: str | None = DEFAULT_ARCHIVE_PATH,
    archive_output: str = DEFAULT_ARCHIVE_PATH,
    normalized_output: str = DEFAULT_NORMALIZED_OUTPUT,
    registry_output: str = DEFAULT_REGISTRY_OUTPUT,
    archive_summary_output: str | None = None,
    report_output: str | None = None,
    benchmark_symbol: str | None = None,
) -> dict[str, Path]:
    existing_rows = read_archive_rows(archive_path)
    incoming_rows = normalize_input_rows(benchmark_input, benchmark_config_path)
    merge_result = merge_archive_rows(existing_rows, incoming_rows)
    if not merge_result.rows:
        raise ValueError("benchmark history engine requires an existing archive or --benchmark-input with at least one normalized row.")

    selected_symbol, selected_rows = select_benchmark_rows(merge_result.rows, benchmark_symbol)
    registry_rows = build_registry_rows(merge_result.rows)
    summary_row = build_archive_summary_row(merge_result, selected_symbol, selected_rows, registry_rows)

    outputs = {
        "archive_output": write_csv_rows(archive_output, BENCHMARK_ARCHIVE_FIELDS, merge_result.rows),
        "registry_output": write_csv_rows(registry_output, BENCHMARK_REGISTRY_FIELDS, registry_rows),
        "normalized_output": write_csv_rows(normalized_output, BENCHMARK_NORMALIZED_FIELDS, project_normalized_rows(selected_rows)),
    }
    if archive_summary_output:
        outputs["archive_summary_output"] = write_csv_rows(archive_summary_output, BENCHMARK_ARCHIVE_SUMMARY_FIELDS, [summary_row])
    if report_output:
        report_path = ensure_parent_dir(report_output)
        report_path.write_text(build_report_text(registry_rows, summary_row), encoding="utf-8")
        outputs["report_output"] = report_path
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and reuse a persistent local benchmark timeseries archive.")
    parser.add_argument("--benchmark-input", help="Explicit local benchmark CSV input.")
    parser.add_argument("--benchmark-config", default=DEFAULT_BENCHMARK_CONFIG_PATH, help="Benchmark config path.")
    parser.add_argument("--archive", default=DEFAULT_ARCHIVE_PATH, help="Existing benchmark archive input.")
    parser.add_argument("--archive-output", default=DEFAULT_ARCHIVE_PATH, help="Merged benchmark archive output.")
    parser.add_argument("--normalized-output", default=DEFAULT_NORMALIZED_OUTPUT, help="Single-symbol normalized benchmark output for performance_engine.")
    parser.add_argument("--registry-output", default=DEFAULT_REGISTRY_OUTPUT, help="Benchmark registry CSV output.")
    parser.add_argument("--archive-summary-output", help="Optional benchmark archive summary CSV output.")
    parser.add_argument("--report-output", help="Optional benchmark history markdown report output.")
    parser.add_argument("--benchmark-symbol", help="Explicit benchmark_symbol to project into normalized-output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_benchmark_history_engine(
        benchmark_input=args.benchmark_input,
        benchmark_config_path=args.benchmark_config,
        archive_path=args.archive,
        archive_output=args.archive_output,
        normalized_output=args.normalized_output,
        registry_output=args.registry_output,
        archive_summary_output=args.archive_summary_output,
        report_output=args.report_output,
        benchmark_symbol=args.benchmark_symbol,
    )


if __name__ == "__main__":
    main()
