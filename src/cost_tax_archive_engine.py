from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, load_yaml_config, read_csv_rows, resolve_repo_path, write_csv_rows
from src.cost_tax_engine import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_KPI_OUTPUT,
    DEFAULT_NORMALIZED_LEDGER_OUTPUT,
    DEFAULT_REPORT_OUTPUT,
    DEFAULT_SUMMARY_OUTPUT,
    KPI_FIELDS,
    NORMALIZED_LEDGER_FIELDS,
    SUMMARY_FIELDS,
    build_report_text,
    build_summary_values,
    determine_measurement_mode,
    load_document_rows,
    normalize_manual_ledger_rows,
    parse_iso_date,
)

DEFAULT_ARCHIVE_PATH = "data/processed/cost_tax_ledger_archive.csv"
DEFAULT_ARCHIVE_SUMMARY_OUTPUT = "data/processed/cost_tax_archive_summary.csv"

ARCHIVE_IDENTITY_FIELDS = [
    "broker",
    "reference_id",
    "record_granularity",
    "event_type",
    "event_date",
    "ticker",
    "isin",
    "document_period_start",
    "document_period_end",
]

ARCHIVE_REQUIRED_IDENTITY_FIELDS = [
    "broker",
    "reference_id",
    "record_granularity",
    "event_type",
    "event_date",
]

ARCHIVE_UPPERCASE_IDENTITY_FIELDS = {
    "broker",
    "record_granularity",
    "event_type",
    "ticker",
    "isin",
}

ARCHIVE_SORT_FIELDS = [
    "event_date",
    "broker",
    "reference_id",
    "record_granularity",
    "event_type",
    "ticker",
    "isin",
    "document_period_start",
    "document_period_end",
]

ARCHIVE_SUMMARY_FIELDS = [
    "archive_rows",
    "new_rows_considered",
    "new_rows_added",
    "duplicate_rows_skipped",
    "period_start",
    "period_end",
    "measurement_mode",
    "data_quality_flag",
    "notes",
]


@dataclass(frozen=True)
class ArchiveMergeResult:
    rows: list[dict[str, str]]
    new_rows_considered: int
    new_rows_added: int
    duplicate_rows_skipped: int


def canonical_archive_row(row: dict[str, Any]) -> dict[str, str]:
    return {field: str(row.get(field, "") or "").strip() for field in NORMALIZED_LEDGER_FIELDS}


def archive_identity(row: dict[str, str]) -> tuple[str, ...]:
    values: list[str] = []
    for field in ARCHIVE_IDENTITY_FIELDS:
        value = str(row.get(field, "") or "").strip()
        if field in ARCHIVE_UPPERCASE_IDENTITY_FIELDS:
            value = value.upper()
        values.append(value)
    return tuple(values)


def archive_identity_text(identity: tuple[str, ...]) -> str:
    return ", ".join(
        f"{field}={value or '<blank>'}"
        for field, value in zip(ARCHIVE_IDENTITY_FIELDS, identity, strict=True)
    )


def row_content_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "") or "").strip() for field in NORMALIZED_LEDGER_FIELDS)


def archive_sort_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "") or "").strip() for field in ARCHIVE_SORT_FIELDS)


def validate_archive_header(fieldnames: list[str] | None, source_name: str) -> None:
    available = set(fieldnames or [])
    missing = [field for field in NORMALIZED_LEDGER_FIELDS if field not in available]
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"{source_name} missing required columns: {missing_text}")


def validate_normalized_archive_rows(rows: list[dict[str, str]], source_name: str) -> None:
    for index, row in enumerate(rows, start=2):
        missing_columns = [field for field in NORMALIZED_LEDGER_FIELDS if field not in row]
        if missing_columns:
            missing_text = ", ".join(sorted(missing_columns))
            raise ValueError(f"{source_name} row {index} missing required columns: {missing_text}")
        blank_identity = [field for field in ARCHIVE_REQUIRED_IDENTITY_FIELDS if not str(row.get(field, "")).strip()]
        if blank_identity:
            missing_text = ", ".join(sorted(blank_identity))
            raise ValueError(f"{source_name} row {index} has blank archive identity field(s): {missing_text}")
        parse_iso_date(row.get("event_date"), "event_date")
        for period_field in ["document_period_start", "document_period_end"]:
            if str(row.get(period_field, "")).strip():
                parse_iso_date(row.get(period_field), period_field)


def read_archive_rows(path_value: str | None) -> list[dict[str, str]]:
    if not path_value:
        return []
    path = resolve_repo_path(path_value)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        source_name = f"cost/tax ledger archive ({path_value})"
        validate_archive_header(reader.fieldnames, source_name)
        rows = [canonical_archive_row(row) for row in reader]
    validate_normalized_archive_rows(rows, source_name)
    return rows


def index_archive_rows(rows: list[dict[str, str]], source_name: str) -> dict[tuple[str, ...], dict[str, str]]:
    indexed: dict[tuple[str, ...], dict[str, str]] = {}
    validate_normalized_archive_rows(rows, source_name)
    for row in rows:
        normalized = canonical_archive_row(row)
        identity = archive_identity(normalized)
        existing = indexed.get(identity)
        if existing is None:
            indexed[identity] = normalized
            continue
        if row_content_key(existing) != row_content_key(normalized):
            raise ValueError(f"cost/tax ledger archive conflict for identity {archive_identity_text(identity)} in {source_name}")
    return indexed


def merge_archive_rows(
    existing_rows: list[dict[str, str]],
    incoming_rows: list[dict[str, str]],
) -> ArchiveMergeResult:
    indexed = index_archive_rows(existing_rows, "existing cost/tax ledger archive")
    validate_normalized_archive_rows(incoming_rows, "incoming cost/tax archive rows")
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
            raise ValueError(f"cost/tax ledger archive conflict for identity {archive_identity_text(identity)}")
        duplicate_rows_skipped += 1

    return ArchiveMergeResult(
        rows=sorted(indexed.values(), key=archive_sort_key),
        new_rows_considered=len(incoming_rows),
        new_rows_added=new_rows_added,
        duplicate_rows_skipped=duplicate_rows_skipped,
    )


def load_incoming_rows(
    ledger_path: str | None,
    document_inputs: list[str] | None,
    config_path: str,
) -> list[dict[str, str]]:
    config = load_yaml_config(config_path)
    incoming_rows: list[dict[str, str]] = []
    if ledger_path:
        ledger_rows = read_csv_rows(ledger_path)
        if ledger_rows:
            incoming_rows.extend(normalize_manual_ledger_rows(ledger_rows, config, ledger_path))
    normalized_document_inputs = sorted(str(path) for path in (document_inputs or []) if str(path).strip())
    if normalized_document_inputs:
        incoming_rows.extend(load_document_rows(normalized_document_inputs, "document_summary_input"))
    return sorted((canonical_archive_row(row) for row in incoming_rows), key=archive_sort_key)


def build_archive_summary_row(
    merge_result: ArchiveMergeResult,
    summary_row: dict[str, str],
) -> dict[str, str]:
    return {
        "archive_rows": str(len(merge_result.rows)),
        "new_rows_considered": str(merge_result.new_rows_considered),
        "new_rows_added": str(merge_result.new_rows_added),
        "duplicate_rows_skipped": str(merge_result.duplicate_rows_skipped),
        "period_start": summary_row["period_start"],
        "period_end": summary_row["period_end"],
        "measurement_mode": summary_row["ledger_measurement_mode"],
        "data_quality_flag": summary_row["ledger_data_quality_flag"],
        "notes": "Persistent archive is built from normalized cost/tax ledger rows; duplicate identity with differing content fails fast.",
    }


def run_cost_tax_archive_engine(
    ledger_path: str | None = None,
    document_inputs: list[str] | None = None,
    archive_path: str | None = DEFAULT_ARCHIVE_PATH,
    archive_output: str = DEFAULT_ARCHIVE_PATH,
    normalized_ledger_output: str = DEFAULT_NORMALIZED_LEDGER_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    kpi_output: str = DEFAULT_KPI_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
    archive_summary_output: str | None = None,
    config_path: str = DEFAULT_CONFIG_PATH,
    measurement_mode: str = "auto",
) -> dict[str, Path]:
    existing_rows = read_archive_rows(archive_path)
    incoming_rows = load_incoming_rows(ledger_path, document_inputs, config_path)
    merge_result = merge_archive_rows(existing_rows, incoming_rows)
    if not merge_result.rows:
        raise ValueError("cost/tax archive engine requires an existing archive and/or --ledger/--document-input with at least one normalized row.")

    detected_measurement_mode = determine_measurement_mode(merge_result.rows, measurement_mode)
    summary_row, kpi_rows = build_summary_values(merge_result.rows, detected_measurement_mode)

    outputs = {
        "archive_output": write_csv_rows(archive_output, NORMALIZED_LEDGER_FIELDS, merge_result.rows),
        "normalized_ledger_output": write_csv_rows(normalized_ledger_output, NORMALIZED_LEDGER_FIELDS, merge_result.rows),
        "summary_output": write_csv_rows(summary_output, SUMMARY_FIELDS, [summary_row]),
        "kpi_output": write_csv_rows(kpi_output, KPI_FIELDS, kpi_rows),
    }
    report_path = ensure_parent_dir(report_output)
    report_path.write_text(build_report_text(summary_row, kpi_rows, merge_result.rows), encoding="utf-8")
    outputs["report_output"] = report_path

    if archive_summary_output:
        archive_summary_row = build_archive_summary_row(merge_result, summary_row)
        outputs["archive_summary_output"] = write_csv_rows(archive_summary_output, ARCHIVE_SUMMARY_FIELDS, [archive_summary_row])
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and reuse a persistent normalized cost/tax ledger archive.")
    parser.add_argument("--ledger", help="Manual cost/tax ledger CSV input.")
    parser.add_argument("--document-input", action="append", default=[], help="Optional supported document input; can be repeated.")
    parser.add_argument("--archive", default=DEFAULT_ARCHIVE_PATH, help="Existing normalized cost/tax ledger archive input.")
    parser.add_argument("--archive-output", default=DEFAULT_ARCHIVE_PATH, help="Merged normalized cost/tax ledger archive output.")
    parser.add_argument("--normalized-ledger-output", default=DEFAULT_NORMALIZED_LEDGER_OUTPUT, help="Normalized ledger CSV output derived from the archive.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT, help="Summary CSV output derived from the archive.")
    parser.add_argument("--kpi-output", default=DEFAULT_KPI_OUTPUT, help="KPI CSV output derived from the archive.")
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT, help="Markdown report output derived from the archive.")
    parser.add_argument("--archive-summary-output", help="Optional archive merge summary CSV output.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Cost/tax ledger config path.")
    parser.add_argument("--measurement-mode", choices=["auto", "summary", "partial", "full"], default="auto", help="Measurement mode override.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_cost_tax_archive_engine(
        ledger_path=args.ledger,
        document_inputs=args.document_input,
        archive_path=args.archive,
        archive_output=args.archive_output,
        normalized_ledger_output=args.normalized_ledger_output,
        summary_output=args.summary_output,
        kpi_output=args.kpi_output,
        report_output=args.report_output,
        archive_summary_output=args.archive_summary_output,
        config_path=args.config,
        measurement_mode=args.measurement_mode,
    )


if __name__ == "__main__":
    main()
