from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

from src.common import ensure_parent_dir, read_csv_rows, resolve_repo_path, round2, to_float, write_csv_rows
from src.performance_engine import (
    FULL_HISTORY,
    PARTIAL_HISTORY,
    PORTFOLIO_TIMESERIES_FIELDS,
    SNAPSHOT_ONLY,
    PortfolioPoint,
    build_portfolio_timeseries_rows,
    derive_snapshot_point,
    parse_iso_date,
)

DEFAULT_ARCHIVE_PATH = "data/processed/portfolio_snapshot_archive.csv"
DEFAULT_TIMESERIES_OUTPUT = "data/processed/portfolio_timeseries.csv"

ARCHIVE_FIELDS = [
    "as_of_date",
    "portfolio_nav_eur",
    "portfolio_value_eur",
    "cash_value_eur",
    "source_name",
    "history_source_type",
    "notes",
]

SUMMARY_FIELDS = [
    "snapshot_points",
    "first_as_of_date",
    "last_as_of_date",
    "latest_portfolio_nav_eur",
    "latest_portfolio_value_eur",
    "latest_cash_value_eur",
    "measurement_readiness",
    "notes",
]


def read_archive_rows(path_value: str | Path) -> list[dict[str, str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [field for field in ARCHIVE_FIELDS if field not in fieldnames]
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"portfolio snapshot archive ({path_value}) missing required columns: {missing_text}")
        rows = list(reader)
    validate_archive_rows(rows, str(path_value))
    return [{field: str(row.get(field, "")).strip() for field in ARCHIVE_FIELDS} for row in rows]


def validate_archive_rows(rows: list[dict[str, str]], source_name: str) -> None:
    seen_dates: set[str] = set()
    for index, row in enumerate(rows, start=2):
        as_of_date = str(row.get("as_of_date", "")).strip()
        if not as_of_date:
            raise ValueError(f"portfolio snapshot archive ({source_name}) row {index} has blank as_of_date.")
        parse_iso_date(as_of_date, "as_of_date")
        if as_of_date in seen_dates:
            raise ValueError(f"portfolio snapshot archive ({source_name}) contains duplicate as_of_date: {as_of_date}")
        seen_dates.add(as_of_date)
        for field in ["portfolio_nav_eur", "portfolio_value_eur", "cash_value_eur"]:
            raw_value = str(row.get(field, "")).strip()
            if not raw_value:
                raise ValueError(f"portfolio snapshot archive ({source_name}) row {index} has blank {field}.")
            if not math.isfinite(to_float(raw_value, float("nan"))):
                raise ValueError(f"portfolio snapshot archive ({source_name}) row {index} has non-numeric {field}: {raw_value!r}")


def archive_row_from_snapshot(
    snapshot_point: PortfolioPoint,
    history_source_type: str = "positions_snapshot",
    notes: str = "",
) -> dict[str, str]:
    source_type = str(history_source_type or "").strip() or "positions_snapshot"
    note_parts = [
        snapshot_point.notes,
        "Archived explicit positions snapshot; no external cashflows or missing history inferred.",
        str(notes or "").strip(),
    ]
    return {
        "as_of_date": snapshot_point.date.isoformat(),
        "portfolio_nav_eur": str(round2(snapshot_point.portfolio_nav_eur)),
        "portfolio_value_eur": str(round2(snapshot_point.portfolio_value_eur)),
        "cash_value_eur": str(round2(snapshot_point.cash_value_eur)),
        "source_name": snapshot_point.source_name,
        "history_source_type": source_type,
        "notes": " ".join(part for part in note_parts if part).strip(),
    }


def derive_archive_point(
    positions_rows: list[dict[str, str]],
    history_source_type: str = "positions_snapshot",
    notes: str = "",
) -> dict[str, str]:
    return archive_row_from_snapshot(derive_snapshot_point(positions_rows), history_source_type, notes)


def conflict_key(row: dict[str, str]) -> tuple[str, str, str, str, str, str]:
    return (
        str(row.get("as_of_date", "")).strip(),
        str(round2(to_float(row.get("portfolio_nav_eur")))),
        str(round2(to_float(row.get("portfolio_value_eur")))),
        str(round2(to_float(row.get("cash_value_eur")))),
        str(row.get("source_name", "")).strip(),
        str(row.get("history_source_type", "")).strip(),
    )


def merge_archive_rows(existing_rows: list[dict[str, str]], new_row: dict[str, str]) -> list[dict[str, str]]:
    validate_archive_rows(existing_rows, "existing archive")
    validate_archive_rows([new_row], "new snapshot point")
    new_date = str(new_row["as_of_date"]).strip()
    merged: list[dict[str, str]] = []
    matched_existing = False
    for row in existing_rows:
        if str(row.get("as_of_date", "")).strip() != new_date:
            merged.append({field: str(row.get(field, "")).strip() for field in ARCHIVE_FIELDS})
            continue
        matched_existing = True
        if conflict_key(row) != conflict_key(new_row):
            raise ValueError(
                "portfolio snapshot archive contains conflicting point for "
                f"as_of_date={new_date}; refusing to overwrite explicit history."
            )
        merged.append({field: str(row.get(field, "")).strip() for field in ARCHIVE_FIELDS})
    if not matched_existing:
        merged.append({field: str(new_row.get(field, "")).strip() for field in ARCHIVE_FIELDS})
    return sorted(merged, key=lambda row: parse_iso_date(row["as_of_date"], "as_of_date"))


def archive_rows_to_points(rows: list[dict[str, str]]) -> list[PortfolioPoint]:
    validate_archive_rows(rows, "portfolio snapshot archive")
    return [
        PortfolioPoint(
            date=parse_iso_date(row["as_of_date"], "as_of_date"),
            portfolio_nav_eur=round2(to_float(row["portfolio_nav_eur"])),
            portfolio_value_eur=round2(to_float(row["portfolio_value_eur"])),
            cash_value_eur=round2(to_float(row["cash_value_eur"])),
            net_external_cash_flow_eur="",
            source_name=str(row.get("source_name", "")).strip(),
            notes=str(row.get("notes", "")).strip(),
        )
        for row in sorted(rows, key=lambda item: parse_iso_date(item["as_of_date"], "as_of_date"))
    ]


def measurement_readiness(point_count: int) -> str:
    if point_count < 2:
        return SNAPSHOT_ONLY
    if point_count < 13:
        return PARTIAL_HISTORY
    return FULL_HISTORY


def build_history_summary_rows(archive_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not archive_rows:
        return [
            {
                "snapshot_points": "0",
                "first_as_of_date": "",
                "last_as_of_date": "",
                "latest_portfolio_nav_eur": "",
                "latest_portfolio_value_eur": "",
                "latest_cash_value_eur": "",
                "measurement_readiness": SNAPSHOT_ONLY,
                "notes": "No explicit portfolio snapshot points are archived.",
            }
        ]
    sorted_rows = sorted(archive_rows, key=lambda row: parse_iso_date(row["as_of_date"], "as_of_date"))
    first = sorted_rows[0]
    latest = sorted_rows[-1]
    return [
        {
            "snapshot_points": str(len(sorted_rows)),
            "first_as_of_date": first["as_of_date"],
            "last_as_of_date": latest["as_of_date"],
            "latest_portfolio_nav_eur": latest["portfolio_nav_eur"],
            "latest_portfolio_value_eur": latest["portfolio_value_eur"],
            "latest_cash_value_eur": latest["cash_value_eur"],
            "measurement_readiness": measurement_readiness(len(sorted_rows)),
            "notes": "Only explicit positions snapshots are archived; no TWR/IRR or cashflow reconstruction is inferred.",
        }
    ]


def build_history_report_text(summary_row: dict[str, str]) -> str:
    return "\n".join(
        [
            "# Portfolio History Report",
            "",
            "## Summary",
            "",
            f"- Snapshot-Punkte: {summary_row['snapshot_points']}",
            f"- Erster Punkt: {summary_row['first_as_of_date'] or 'NOT_AVAILABLE'}",
            f"- Letzter Punkt: {summary_row['last_as_of_date'] or 'NOT_AVAILABLE'}",
            f"- Latest NAV: {summary_row['latest_portfolio_nav_eur'] or 'NOT_AVAILABLE'} EUR",
            f"- Measurement Readiness: {summary_row['measurement_readiness']}",
            "",
            "## Methodische Grenzen",
            "",
            "- Es werden nur explizite Positions-Snapshots historisiert.",
            "- Es werden keine externen Cashflows, keine TWR/IRR und keine fehlende Historie rekonstruiert.",
            f"- Notes: {summary_row['notes']}",
            "",
        ]
    )


def run_portfolio_history_engine(
    positions_path: str,
    archive_path: str = DEFAULT_ARCHIVE_PATH,
    archive_output: str = DEFAULT_ARCHIVE_PATH,
    timeseries_output: str = DEFAULT_TIMESERIES_OUTPUT,
    summary_output: str | None = None,
    report_output: str | None = None,
    history_source_type: str = "positions_snapshot",
    notes: str = "",
) -> dict[str, Path]:
    positions_rows = read_csv_rows(positions_path)
    if not positions_rows:
        raise ValueError(f"positions snapshot ({positions_path}) contains no rows.")

    existing_rows = read_archive_rows(archive_path)
    new_row = derive_archive_point(positions_rows, history_source_type=history_source_type, notes=notes)
    archive_rows = merge_archive_rows(existing_rows, new_row)
    portfolio_points = archive_rows_to_points(archive_rows)
    summary_rows = build_history_summary_rows(archive_rows)

    outputs: dict[str, Path] = {
        "archive_output": write_csv_rows(archive_output, ARCHIVE_FIELDS, archive_rows),
        "timeseries_output": write_csv_rows(timeseries_output, PORTFOLIO_TIMESERIES_FIELDS, build_portfolio_timeseries_rows(portfolio_points)),
    }
    if summary_output:
        outputs["summary_output"] = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    if report_output:
        report_path = ensure_parent_dir(report_output)
        report_path.write_text(build_history_report_text(summary_rows[0]), encoding="utf-8")
        outputs["report_output"] = report_path
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build portfolio snapshot archive and normalized portfolio timeseries.")
    parser.add_argument("--positions", required=True, help="Explicit positions snapshot CSV.")
    parser.add_argument("--archive", default=DEFAULT_ARCHIVE_PATH, help="Existing portfolio snapshot archive CSV.")
    parser.add_argument("--archive-output", default=DEFAULT_ARCHIVE_PATH, help="Merged portfolio snapshot archive CSV output.")
    parser.add_argument("--timeseries-output", default=DEFAULT_TIMESERIES_OUTPUT, help="Normalized portfolio timeseries CSV output.")
    parser.add_argument("--summary-output", help="Optional portfolio history summary CSV output.")
    parser.add_argument("--report-output", help="Optional Markdown history report output.")
    parser.add_argument("--history-source-type", default="positions_snapshot", help="Source type label for the archived point.")
    parser.add_argument("--notes", default="", help="Optional notes appended to the archived point.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_portfolio_history_engine(
        positions_path=args.positions,
        archive_path=args.archive,
        archive_output=args.archive_output,
        timeseries_output=args.timeseries_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
        history_source_type=args.history_source_type,
        notes=args.notes,
    )


if __name__ == "__main__":
    main()
