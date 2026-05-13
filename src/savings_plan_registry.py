from __future__ import annotations

import argparse
import csv
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_INPUT = "data/raw/savings_plan_registry.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/savings_plan_registry_summary.csv"
SUMMARY_FIELDS = [
    "row_count",
    "active_count",
    "inactive_count",
    "total_monthly_eur",
    "next_execution_day",
    "warning_count",
    "drift_warnings",
    "data_quality_flag",
]
REGISTRY_FIELDS = [
    "ticker",
    "isin",
    "broker",
    "instrument_name",
    "monthly_amount_eur",
    "frequency",
    "execution_day_of_month",
    "active",
    "started_at",
    "last_modified",
    "notes",
]
REQUIRED_FIELDS = [
    "ticker",
    "broker",
    "instrument_name",
    "monthly_amount_eur",
    "frequency",
    "execution_day_of_month",
    "active",
    "started_at",
    "last_modified",
]
BROKERS = {"TRADE_REPUBLIC", "OTHER"}
FREQUENCIES = {"MONTHLY", "BI_WEEKLY", "QUARTERLY"}
ACTIVE_VALUES = {"TRUE", "FALSE"}
ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")


def default_report_output() -> str:
    return f"reports/{date.today().isoformat()}/savings_plan_registry_report.md"


def resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def ensure_parent(path_value: str | Path) -> Path:
    path = resolve_path(path_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _read_fieldnames(path_value: str | Path) -> list[str]:
    path = resolve_path(path_value)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or [])


def validate_header(fieldnames: list[str], source_name: str) -> None:
    missing = [field for field in REGISTRY_FIELDS if field not in fieldnames]
    unknown = [field for field in fieldnames if field not in REGISTRY_FIELDS]
    if missing:
        raise ValueError(f"{source_name} missing required columns: {', '.join(missing)}")
    if unknown:
        raise ValueError(f"{source_name} contains unknown columns: {', '.join(unknown)}")


def load_savings_plan_registry(path: str | Path = DEFAULT_INPUT) -> list[dict[str, str]]:
    source_name = str(path)
    fieldnames = _read_fieldnames(path)
    validate_header(fieldnames, source_name)
    with resolve_path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_float(value: Any, field_name: str, row_index: int) -> float:
    text = str(value or "").strip().replace(",", ".")
    try:
        parsed = float(text)
    except ValueError as exc:
        raise ValueError(f"row {row_index} field {field_name} must be a float") from exc
    if parsed < 0.0:
        raise ValueError(f"row {row_index} field {field_name} must be non-negative")
    return parsed


def _parse_execution_day(value: Any, row_index: int) -> int:
    try:
        parsed = int(str(value or "").strip())
    except ValueError as exc:
        raise ValueError(f"row {row_index} field execution_day_of_month must be an int") from exc
    if parsed < 1 or parsed > 28:
        raise ValueError(f"row {row_index} field execution_day_of_month must be between 1 and 28")
    return parsed


def _parse_iso_date(value: Any, field_name: str, row_index: int) -> str:
    text = str(value or "").strip()
    try:
        datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"row {row_index} field {field_name} must be YYYY-MM-DD") from exc
    return text


def validate_savings_plan_registry(
    rows: list[dict[str, Any]],
    source_name: str = "savings_plan_registry",
) -> tuple[list[dict[str, str]], list[str]]:
    if rows:
        fieldnames = list(rows[0].keys())
        validate_header(fieldnames, source_name)
    normalized_rows: list[dict[str, str]] = []
    warnings: list[str] = []
    seen_tickers: set[str] = set()
    duplicates: set[str] = set()
    for index, row in enumerate(rows, start=2):
        blank = [field for field in REQUIRED_FIELDS if not str(row.get(field, "")).strip()]
        if blank:
            raise ValueError(f"{source_name} row {index} has blank required field(s): {', '.join(sorted(blank))}")
        ticker = str(row.get("ticker", "")).strip().upper().replace(" ", "")
        if ticker in seen_tickers:
            duplicates.add(ticker)
        seen_tickers.add(ticker)
        broker = str(row.get("broker", "")).strip().upper()
        if broker not in BROKERS:
            raise ValueError(f"{source_name} row {index} field broker has invalid enum value: {broker}")
        frequency = str(row.get("frequency", "")).strip().upper()
        if frequency not in FREQUENCIES:
            raise ValueError(f"{source_name} row {index} field frequency has invalid enum value: {frequency}")
        active = str(row.get("active", "")).strip().upper()
        if active not in ACTIVE_VALUES:
            raise ValueError(f"{source_name} row {index} field active has invalid enum value: {active}")
        isin = str(row.get("isin", "")).strip().upper()
        if isin and not ISIN_PATTERN.match(isin):
            warnings.append(f"INVALID_ISIN:{ticker}")
        normalized_rows.append(
            {
                "ticker": ticker,
                "isin": isin,
                "broker": broker,
                "instrument_name": str(row.get("instrument_name", "")).strip(),
                "monthly_amount_eur": f"{_parse_float(row.get('monthly_amount_eur'), 'monthly_amount_eur', index):.2f}",
                "frequency": frequency,
                "execution_day_of_month": str(_parse_execution_day(row.get("execution_day_of_month"), index)),
                "active": active,
                "started_at": _parse_iso_date(row.get("started_at"), "started_at", index),
                "last_modified": _parse_iso_date(row.get("last_modified"), "last_modified", index),
                "notes": str(row.get("notes", "")).strip(),
            }
        )
    if duplicates:
        raise ValueError(f"{source_name} contains duplicate tickers: {', '.join(sorted(duplicates))}")
    return normalized_rows, warnings


def summarize_savings_plan_registry(rows: list[dict[str, str]], warnings: list[str] | None = None) -> dict[str, str]:
    warning_items = list(warnings or [])
    active_rows = [row for row in rows if str(row.get("active", "")).strip().upper() == "TRUE"]
    inactive_rows = [row for row in rows if str(row.get("active", "")).strip().upper() == "FALSE"]
    active_days = [int(row["execution_day_of_month"]) for row in active_rows if str(row.get("execution_day_of_month", "")).strip()]
    total_monthly = sum(float(row.get("monthly_amount_eur", "0") or 0.0) for row in active_rows)
    if not rows:
        quality = "EMPTY_REGISTRY"
    elif warning_items:
        quality = "WARNINGS_PRESENT"
    else:
        quality = "OK"
    return {
        "row_count": str(len(rows)),
        "active_count": str(len(active_rows)),
        "inactive_count": str(len(inactive_rows)),
        "total_monthly_eur": f"{total_monthly:.2f}",
        "next_execution_day": str(min(active_days)) if active_days else "",
        "warning_count": str(len(warning_items)),
        "drift_warnings": ";".join(warning_items),
        "data_quality_flag": quality,
    }


def write_summary_csv(summary: dict[str, str], path: str | Path = DEFAULT_SUMMARY_OUTPUT) -> Path:
    output_path = ensure_parent(path)
    temp_path = output_path.with_name(f"{output_path.name}.tmp")
    try:
        with temp_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
            writer.writeheader()
            writer.writerow({field: summary.get(field, "") for field in SUMMARY_FIELDS})
        os.replace(temp_path, output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return output_path


def build_report(
    rows: list[dict[str, str]],
    summary: dict[str, str],
    warnings: list[str],
    path: str | Path | None = None,
) -> Path:
    output_path = ensure_parent(path or default_report_output())
    state = "EMPTY_STATE" if not rows else summary.get("data_quality_flag", "OK")
    lines = [
        "# Sparplan-Register Report",
        "",
        "## Status",
        "",
        f"- Zustand: {state}",
        f"- Register-Zeilen: {summary.get('row_count', '0')}",
        f"- Aktive Sparplaene: {summary.get('active_count', '0')}",
        f"- Inaktive Sparplaene: {summary.get('inactive_count', '0')}",
        f"- Monatlicher Betrag aktiv: {summary.get('total_monthly_eur', '0.00')} EUR",
        f"- Naechster Ausfuehrungstag: {summary.get('next_execution_day', '') or 'NOT_AVAILABLE'}",
        "",
        "## Warnungen",
    ]
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- Keine Warnungen.")
    lines.extend(
        [
            "",
            "## Methodische Grenzen",
            "",
            "- Das Sparplan-Register ist ein manueller read-only Spiegel lokaler Sparplan-Daten.",
            "- Es erzeugt keine Routing-, Kauf-, Verkaufs- oder Broker-Schreibaktionen.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def run_savings_plan_registry(
    input_path: str = DEFAULT_INPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str | None = None,
) -> dict[str, Any]:
    loaded_rows = load_savings_plan_registry(input_path)
    rows, warnings = validate_savings_plan_registry(loaded_rows, str(input_path))
    summary = summarize_savings_plan_registry(rows, warnings)
    summary_path = write_summary_csv(summary, summary_output)
    report_path = build_report(rows, summary, warnings, report_output or default_report_output())
    return {
        "rows": rows,
        "summary": summary,
        "warnings": warnings,
        "summary_path": summary_path,
        "report_path": report_path,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a read-only local savings plan registry and write summary artifacts.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Savings plan registry CSV input.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT, help="Savings plan summary CSV output.")
    parser.add_argument("--report-output", default=default_report_output(), help="Savings plan markdown report output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_savings_plan_registry(args.input, args.summary_output, args.report_output)


if __name__ == "__main__":
    main()
