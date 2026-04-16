from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, resolve_repo_path, safe_upper, write_csv_rows
from src.fundamentals_evidence_engine import (
    DEFAULT_EVIDENCE_INPUT_PATH,
    EVIDENCE_IDENTITY_FIELDS,
    EVIDENCE_INPUT_FIELDS,
    evidence_identity_text,
)

DEFAULT_PROMOTED_EVIDENCE_INPUT_PATH = "data/processed/personal_fundamentals_snapshot_evidence_promoted.csv"
DEFAULT_COMPOSED_OUTPUT = "data/processed/personal_fundamentals_evidence_composed.csv"
DEFAULT_CONFLICTS_OUTPUT = "data/processed/personal_fundamentals_evidence_compose_conflicts.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_fundamentals_evidence_compose_summary.csv"

INPUT_SOURCE_MANUAL = "MANUAL"
INPUT_SOURCE_PROMOTED = "PROMOTED_SNAPSHOT"

COMPOSE_CONFLICT_FIELDS = ["conflict_type", "input_source", "evidence_identity", *EVIDENCE_INPUT_FIELDS]
COMPOSE_SUMMARY_FIELDS = [
    "manual_rows_total",
    "promoted_rows_total",
    "composed_rows_total",
    "identical_duplicates_removed",
    "conflict_rows_total",
    "notes",
]


def read_csv_rows_with_header(path_value: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def require_exact_evidence_header(fieldnames: list[str], source_name: str) -> None:
    available = set(fieldnames)
    expected = set(EVIDENCE_INPUT_FIELDS)
    missing = [field for field in EVIDENCE_INPUT_FIELDS if field not in available]
    unexpected = [field for field in fieldnames if field not in expected]
    if missing or unexpected:
        message_parts: list[str] = []
        if missing:
            message_parts.append(f"missing column(s): {', '.join(sorted(missing))}")
        if unexpected:
            message_parts.append(f"unexpected column(s): {', '.join(sorted(unexpected))}")
        raise ValueError(f"{source_name} does not match the evidence input contract: {'; '.join(message_parts)}")


def is_blank_row(row: dict[str, str]) -> bool:
    return all(not str(value or "").strip() for value in row.values())


def canonical_evidence_value(field: str, value: Any) -> str:
    text = str(value or "").strip()
    if field == "ticker":
        return canonicalize_ticker(text)
    if field == "isin":
        return text.upper()
    if field in {"source_type", "verification_status", "data_quality_flag"}:
        return safe_upper(text)
    if field == "currency":
        return text.upper()
    return text


def canonical_evidence_row(row: dict[str, str]) -> dict[str, str]:
    canonical_row = {field: "" for field in EVIDENCE_INPUT_FIELDS}
    for field in EVIDENCE_INPUT_FIELDS:
        canonical_row[field] = canonical_evidence_value(field, row.get(field, ""))
    return canonical_row


def compose_identity(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "") or "").strip() for field in EVIDENCE_IDENTITY_FIELDS)


def evidence_content_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "") or "").strip() for field in EVIDENCE_INPUT_FIELDS)


def compose_sort_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        canonicalize_ticker(row.get("ticker", "")),
        str(row.get("isin", "") or "").strip().upper(),
        str(row.get("kpi_name", "") or "").strip(),
        str(row.get("source_type", "") or "").strip(),
        str(row.get("source_as_of_date", "") or "").strip(),
        str(row.get("source_name", "") or "").strip(),
        str(row.get("source_reference", "") or "").strip(),
    )


def compose_conflict_sort_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        str(row.get("evidence_identity", "") or "").strip(),
        str(row.get("input_source", "") or "").strip(),
        *compose_sort_key(row),
    )


def load_canonical_evidence_rows(path_value: str | Path, source_name: str) -> list[dict[str, str]]:
    fieldnames, raw_rows = read_csv_rows_with_header(path_value)
    require_exact_evidence_header(fieldnames, source_name)
    canonical_rows: list[dict[str, str]] = []
    for row in raw_rows:
        if is_blank_row(row):
            continue
        canonical_rows.append(canonical_evidence_row(row))
    return canonical_rows


def build_conflict_row(identity: tuple[str, ...], input_source: str, row: dict[str, str]) -> dict[str, str]:
    conflict_row = {
        "conflict_type": "EVIDENCE_CONFLICT",
        "input_source": input_source,
        "evidence_identity": evidence_identity_text(identity),
    }
    for field in EVIDENCE_INPUT_FIELDS:
        conflict_row[field] = row.get(field, "")
    return conflict_row


def write_summary(
    output_path: str,
    *,
    manual_rows_total: int,
    promoted_rows_total: int,
    composed_rows_total: int,
    identical_duplicates_removed: int,
    conflict_rows_total: int,
    notes: str,
) -> Path:
    return write_csv_rows(
        output_path,
        COMPOSE_SUMMARY_FIELDS,
        [
            {
                "manual_rows_total": str(manual_rows_total),
                "promoted_rows_total": str(promoted_rows_total),
                "composed_rows_total": str(composed_rows_total),
                "identical_duplicates_removed": str(identical_duplicates_removed),
                "conflict_rows_total": str(conflict_rows_total),
                "notes": notes,
            }
        ],
    )


def run_fundamentals_evidence_compose(
    *,
    manual_evidence_input_path: str = DEFAULT_EVIDENCE_INPUT_PATH,
    promoted_evidence_input_path: str = DEFAULT_PROMOTED_EVIDENCE_INPUT_PATH,
    composed_output: str = DEFAULT_COMPOSED_OUTPUT,
    conflicts_output: str = DEFAULT_CONFLICTS_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
) -> dict[str, Path]:
    manual_rows = load_canonical_evidence_rows(
        manual_evidence_input_path,
        f"manual personal fundamentals evidence ({manual_evidence_input_path})",
    )
    promoted_rows = load_canonical_evidence_rows(
        promoted_evidence_input_path,
        f"promoted snapshot evidence ({promoted_evidence_input_path})",
    )

    grouped_entries: dict[tuple[str, ...], list[tuple[str, dict[str, str]]]] = {}
    for input_source, rows in ((INPUT_SOURCE_MANUAL, manual_rows), (INPUT_SOURCE_PROMOTED, promoted_rows)):
        for row in rows:
            grouped_entries.setdefault(compose_identity(row), []).append((input_source, row))

    composed_rows: list[dict[str, str]] = []
    conflict_rows: list[dict[str, str]] = []
    identical_duplicates_removed = 0
    for identity, entries in sorted(grouped_entries.items()):
        unique_entries: dict[tuple[str, ...], list[tuple[str, dict[str, str]]]] = {}
        for input_source, row in entries:
            unique_entries.setdefault(evidence_content_key(row), []).append((input_source, row))
        identical_duplicates_removed += len(entries) - len(unique_entries)
        if len(unique_entries) == 1:
            composed_rows.append(next(iter(unique_entries.values()))[0][1])
            continue
        for bucket in unique_entries.values():
            for input_source, row in bucket:
                conflict_rows.append(build_conflict_row(identity, input_source, row))

    composed_rows = sorted(composed_rows, key=compose_sort_key)
    conflict_rows = sorted(conflict_rows, key=compose_conflict_sort_key)

    if conflict_rows:
        composed_path = write_csv_rows(composed_output, EVIDENCE_INPUT_FIELDS, [])
        conflicts_path = write_csv_rows(conflicts_output, COMPOSE_CONFLICT_FIELDS, conflict_rows)
        summary_path = write_summary(
            summary_output,
            manual_rows_total=len(manual_rows),
            promoted_rows_total=len(promoted_rows),
            composed_rows_total=0,
            identical_duplicates_removed=identical_duplicates_removed,
            conflict_rows_total=len(conflict_rows),
            notes="Compose conflicts detected; composed evidence output was left empty and no silent precedence rule was applied.",
        )
        raise ValueError(
            f"personal fundamentals evidence compose found conflicting row(s); see {conflicts_path} and {summary_path}"
        )

    composed_path = write_csv_rows(composed_output, EVIDENCE_INPUT_FIELDS, composed_rows)
    conflicts_path = write_csv_rows(conflicts_output, COMPOSE_CONFLICT_FIELDS, [])
    summary_path = write_summary(
        summary_output,
        manual_rows_total=len(manual_rows),
        promoted_rows_total=len(promoted_rows),
        composed_rows_total=len(composed_rows),
        identical_duplicates_removed=identical_duplicates_removed,
        conflict_rows_total=0,
        notes="Manual raw evidence and promoted snapshot evidence were composed without silent conflict resolution.",
    )
    return {
        "evidence_composed": composed_path,
        "evidence_compose_conflicts": conflicts_path,
        "evidence_compose_summary": summary_path,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose manual raw evidence and promoted snapshot evidence into a separate evidence artifact.")
    parser.add_argument("--manual-evidence-input", default=DEFAULT_EVIDENCE_INPUT_PATH, help="Manual raw personal evidence input CSV.")
    parser.add_argument(
        "--promoted-evidence-input",
        default=DEFAULT_PROMOTED_EVIDENCE_INPUT_PATH,
        help="Promoted snapshot evidence input CSV.",
    )
    parser.add_argument("--composed-output", default=DEFAULT_COMPOSED_OUTPUT, help="Composed personal evidence output CSV.")
    parser.add_argument("--conflicts-output", default=DEFAULT_CONFLICTS_OUTPUT, help="Evidence compose conflicts CSV output.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT, help="Evidence compose summary CSV output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_fundamentals_evidence_compose(
        manual_evidence_input_path=args.manual_evidence_input,
        promoted_evidence_input_path=args.promoted_evidence_input,
        composed_output=args.composed_output,
        conflicts_output=args.conflicts_output,
        summary_output=args.summary_output,
    )


if __name__ == "__main__":
    main()
