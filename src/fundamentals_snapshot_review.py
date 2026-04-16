from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, resolve_repo_path, safe_upper, write_csv_rows
from src.fundamentals_evidence_engine import EVIDENCE_IDENTITY_FIELDS, EVIDENCE_INPUT_FIELDS
from src.fundamentals_snapshot_ingestion import DEFAULT_EVIDENCE_STAGING_OUTPUT

DEFAULT_REVIEW_INPUT_PATH = "data/raw/personal_fundamentals_snapshot_review.csv"
DEFAULT_REVIEW_TEMPLATE_PATH = "data/raw/personal_fundamentals_snapshot_review_template.csv"
DEFAULT_REVIEW_REGISTRY_OUTPUT = "data/processed/personal_fundamentals_snapshot_review_registry.csv"
DEFAULT_PROMOTED_EVIDENCE_OUTPUT = "data/processed/personal_fundamentals_snapshot_evidence_promoted.csv"
DEFAULT_REVIEW_BACKLOG_OUTPUT = "data/processed/personal_fundamentals_snapshot_review_backlog.csv"
DEFAULT_REVIEW_SUMMARY_OUTPUT = "data/processed/personal_fundamentals_snapshot_review_summary.csv"

VALID_REVIEW_DECISIONS = {"APPROVE", "REJECT", "PENDING"}
SNAPSHOT_SOURCE_TYPE = "SNAPSHOT_IMPORT"

SNAPSHOT_REVIEW_INPUT_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "kpi_name",
    "source_name",
    "source_reference",
    "source_as_of_date",
    "fiscal_year",
    "review_decision",
    "review_reason",
    "review_author",
    "review_as_of_date",
    "notes",
]

SNAPSHOT_REVIEW_REQUIRED_FIELDS = SNAPSHOT_REVIEW_INPUT_FIELDS

STAGING_MATCH_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "kpi_name",
    "source_name",
    "source_reference",
    "source_as_of_date",
    "fiscal_year",
]

SNAPSHOT_REVIEW_REGISTRY_FIELDS = [
    *STAGING_MATCH_FIELDS,
    "source_type",
    "review_decision",
    "review_reason",
    "review_author",
    "review_as_of_date",
    "promotion_status",
    "notes",
]

SNAPSHOT_REVIEW_BACKLOG_FIELDS = [
    *STAGING_MATCH_FIELDS,
    "source_type",
    "backlog_status",
    "latest_review_decision",
    "latest_review_reason",
    "latest_review_author",
    "latest_review_as_of_date",
    "notes",
]

SNAPSHOT_REVIEW_SUMMARY_FIELDS = [
    "staging_rows_total",
    "review_rows_total",
    "approved_rows",
    "rejected_rows",
    "pending_rows",
    "promoted_rows",
    "backlog_rows",
    "notes",
]


def read_csv_rows_with_header(path_value: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def require_header_columns(fieldnames: list[str], required_columns: list[str], source_name: str) -> None:
    available = set(fieldnames)
    missing = [field for field in required_columns if field not in available]
    if missing:
        raise ValueError(f"{source_name} missing required columns: {', '.join(sorted(missing))}")


def require_nonblank_value(row: dict[str, str], field: str, source_name: str, row_number: int) -> str:
    text = str(row.get(field, "") or "").strip()
    if not text:
        raise ValueError(f"{source_name} row {row_number} has blank required field(s): {field}")
    return text


def parse_iso_date_text(value: Any, field: str, source_name: str, row_number: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{source_name} row {row_number} has blank required field(s): {field}")
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{source_name} row {row_number} has invalid {field}: {text!r}; expected YYYY-MM-DD") from exc
    return text


def parse_required_fiscal_year(value: Any, source_name: str, row_number: int) -> str:
    text = require_nonblank_value({"fiscal_year": value}, "fiscal_year", source_name, row_number)
    try:
        int(text)
    except ValueError as exc:
        raise ValueError(f"{source_name} row {row_number} has invalid fiscal_year: {text!r}") from exc
    return text


def is_blank_row(row: dict[str, str]) -> bool:
    return all(not str(value or "").strip() for value in row.values())


def canonical_match_value(field: str, value: Any) -> str:
    text = str(value or "").strip()
    if field == "ticker":
        return canonicalize_ticker(text)
    if field == "isin":
        return text.upper()
    return text


def row_signature(row: dict[str, str], fields: list[str]) -> tuple[str, ...]:
    return tuple(canonical_match_value(field, row.get(field, "")) for field in fields)


def dedupe_rows_by_identity(
    rows: list[dict[str, str]],
    *,
    identity_fields: list[str],
    content_fields: list[str],
    source_name: str,
    conflict_label: str,
) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: dict[tuple[str, ...], tuple[str, ...]] = {}
    for row in rows:
        identity = row_signature(row, identity_fields)
        content = tuple(str(row.get(field, "") or "").strip() for field in content_fields)
        existing = seen.get(identity)
        if existing is None:
            seen[identity] = content
            deduped.append(row)
            continue
        if existing != content:
            identity_text = ", ".join(f"{field}={value or '<blank>'}" for field, value in zip(identity_fields, identity, strict=True))
            raise ValueError(f"{source_name} has conflicting duplicate {conflict_label} row(s): {identity_text}")
    return deduped


def staging_identity(row: dict[str, str]) -> tuple[str, ...]:
    return row_signature(row, STAGING_MATCH_FIELDS)


def promoted_identity(row: dict[str, str]) -> tuple[str, ...]:
    return row_signature(row, EVIDENCE_IDENTITY_FIELDS)


def sort_identity_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        canonical_match_value("ticker", row.get("ticker", "")),
        canonical_match_value("isin", row.get("isin", "")),
        str(row.get("kpi_name", "") or "").strip(),
        str(row.get("source_as_of_date", "") or "").strip(),
        str(row.get("source_name", "") or "").strip(),
        str(row.get("source_reference", "") or "").strip(),
    )


def canonical_staging_row(row: dict[str, str], source_name: str, row_number: int) -> dict[str, str]:
    require_nonblank_value(row, "company_name", source_name, row_number)
    require_nonblank_value(row, "kpi_name", source_name, row_number)
    require_nonblank_value(row, "source_name", source_name, row_number)
    require_nonblank_value(row, "source_reference", source_name, row_number)
    parse_iso_date_text(row.get("source_as_of_date", ""), "source_as_of_date", source_name, row_number)
    parse_required_fiscal_year(row.get("fiscal_year", ""), source_name, row_number)
    source_type = safe_upper(require_nonblank_value(row, "source_type", source_name, row_number))
    if source_type != SNAPSHOT_SOURCE_TYPE:
        raise ValueError(
            f"{source_name} row {row_number} has invalid source_type: {row.get('source_type')!r}; expected {SNAPSHOT_SOURCE_TYPE}"
        )

    canonical_row = {field: "" for field in EVIDENCE_INPUT_FIELDS}
    for field in EVIDENCE_INPUT_FIELDS:
        value = row.get(field, "")
        if field == "ticker":
            canonical_row[field] = canonicalize_ticker(value)
        elif field == "isin":
            canonical_row[field] = str(value or "").strip().upper()
        else:
            canonical_row[field] = str(value or "").strip()
    return canonical_row


def canonical_review_row(row: dict[str, str], source_name: str, row_number: int) -> dict[str, str]:
    review_decision = safe_upper(require_nonblank_value(row, "review_decision", source_name, row_number))
    if review_decision not in VALID_REVIEW_DECISIONS:
        raise ValueError(
            f"{source_name} row {row_number} has invalid review_decision: {row.get('review_decision')!r}; "
            f"allowed: {', '.join(sorted(VALID_REVIEW_DECISIONS))}"
        )

    canonical_row = {field: "" for field in SNAPSHOT_REVIEW_INPUT_FIELDS}
    for field in SNAPSHOT_REVIEW_INPUT_FIELDS:
        value = row.get(field, "")
        if field == "ticker":
            canonical_row[field] = canonicalize_ticker(value)
        elif field == "isin":
            canonical_row[field] = str(value or "").strip().upper()
        else:
            canonical_row[field] = str(value or "").strip()

    require_nonblank_value(canonical_row, "company_name", source_name, row_number)
    require_nonblank_value(canonical_row, "kpi_name", source_name, row_number)
    require_nonblank_value(canonical_row, "source_name", source_name, row_number)
    require_nonblank_value(canonical_row, "source_reference", source_name, row_number)
    parse_iso_date_text(canonical_row.get("source_as_of_date", ""), "source_as_of_date", source_name, row_number)
    parse_required_fiscal_year(canonical_row.get("fiscal_year", ""), source_name, row_number)
    require_nonblank_value(canonical_row, "review_author", source_name, row_number)
    parse_iso_date_text(canonical_row.get("review_as_of_date", ""), "review_as_of_date", source_name, row_number)
    canonical_row["review_decision"] = review_decision
    return canonical_row


def build_staging_index(staging_rows: list[dict[str, str]], source_name: str) -> dict[tuple[str, ...], dict[str, str]]:
    deduped_rows = dedupe_rows_by_identity(
        staging_rows,
        identity_fields=STAGING_MATCH_FIELDS,
        content_fields=EVIDENCE_INPUT_FIELDS,
        source_name=source_name,
        conflict_label="staging identity",
    )
    return {staging_identity(row): row for row in sorted(deduped_rows, key=sort_identity_key)}


def build_review_index(review_rows: list[dict[str, str]], source_name: str) -> dict[tuple[str, ...], dict[str, str]]:
    deduped_rows = dedupe_rows_by_identity(
        review_rows,
        identity_fields=STAGING_MATCH_FIELDS,
        content_fields=SNAPSHOT_REVIEW_INPUT_FIELDS,
        source_name=source_name,
        conflict_label="snapshot review identity",
    )
    return {staging_identity(row): row for row in sorted(deduped_rows, key=sort_identity_key)}


def registry_row(staging_row: dict[str, str], review_row: dict[str, str]) -> dict[str, str]:
    decision = review_row["review_decision"]
    promotion_status = {
        "APPROVE": "PROMOTED",
        "REJECT": "REJECTED",
        "PENDING": "PENDING",
    }[decision]
    return {
        "ticker": staging_row["ticker"],
        "isin": staging_row["isin"],
        "company_name": staging_row["company_name"],
        "kpi_name": staging_row["kpi_name"],
        "source_name": staging_row["source_name"],
        "source_reference": staging_row["source_reference"],
        "source_as_of_date": staging_row["source_as_of_date"],
        "fiscal_year": staging_row["fiscal_year"],
        "source_type": staging_row["source_type"],
        "review_decision": decision,
        "review_reason": review_row["review_reason"],
        "review_author": review_row["review_author"],
        "review_as_of_date": review_row["review_as_of_date"],
        "promotion_status": promotion_status,
        "notes": review_row["notes"],
    }


def append_review_note(staging_notes: str, review_row: dict[str, str]) -> str:
    review_parts = [
        "snapshot_review_decision=APPROVE",
        f"snapshot_review_author={review_row['review_author']}",
        f"snapshot_review_as_of_date={review_row['review_as_of_date']}",
    ]
    review_reason = str(review_row.get("review_reason", "") or "").strip()
    if review_reason:
        review_parts.append(f"snapshot_review_reason={review_reason}")
    review_note = "; ".join(review_parts)
    base = str(staging_notes or "").strip()
    return f"{base} | {review_note}" if base else review_note


def promoted_row(staging_row: dict[str, str], review_row: dict[str, str]) -> dict[str, str]:
    row = {field: str(staging_row.get(field, "") or "").strip() for field in EVIDENCE_INPUT_FIELDS}
    row["notes"] = append_review_note(row.get("notes", ""), review_row)
    return row


def backlog_row(
    staging_row: dict[str, str],
    *,
    backlog_status: str,
    latest_review: dict[str, str] | None,
) -> dict[str, str]:
    return {
        "ticker": staging_row["ticker"],
        "isin": staging_row["isin"],
        "company_name": staging_row["company_name"],
        "kpi_name": staging_row["kpi_name"],
        "source_name": staging_row["source_name"],
        "source_reference": staging_row["source_reference"],
        "source_as_of_date": staging_row["source_as_of_date"],
        "fiscal_year": staging_row["fiscal_year"],
        "source_type": staging_row["source_type"],
        "backlog_status": backlog_status,
        "latest_review_decision": str(latest_review.get("review_decision", "") or "").strip() if latest_review else "",
        "latest_review_reason": str(latest_review.get("review_reason", "") or "").strip() if latest_review else "",
        "latest_review_author": str(latest_review.get("review_author", "") or "").strip() if latest_review else "",
        "latest_review_as_of_date": str(latest_review.get("review_as_of_date", "") or "").strip() if latest_review else "",
        "notes": (
            str(latest_review.get("notes", "") or "").strip()
            if latest_review
            else "Snapshot evidence staging row has no manual review decision yet."
        ),
    }


def build_summary_rows(
    *,
    staging_rows_total: int,
    review_rows_total: int,
    approved_rows: int,
    rejected_rows: int,
    pending_rows: int,
    promoted_rows: int,
    backlog_rows: int,
) -> list[dict[str, str]]:
    return [
        {
            "staging_rows_total": str(staging_rows_total),
            "review_rows_total": str(review_rows_total),
            "approved_rows": str(approved_rows),
            "rejected_rows": str(rejected_rows),
            "pending_rows": str(pending_rows),
            "promoted_rows": str(promoted_rows),
            "backlog_rows": str(backlog_rows),
            "notes": "Snapshot review decisions remain an explicit promote step; no raw evidence input or master was modified.",
        }
    ]


def write_snapshot_review_template(path_value: str = DEFAULT_REVIEW_TEMPLATE_PATH) -> Path:
    return write_csv_rows(path_value, SNAPSHOT_REVIEW_INPUT_FIELDS, [])


def load_validated_inputs(
    staging_input_path: str,
    review_input_path: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    staging_fieldnames, raw_staging_rows = read_csv_rows_with_header(staging_input_path)
    require_header_columns(
        staging_fieldnames,
        EVIDENCE_INPUT_FIELDS,
        f"snapshot evidence staging ({staging_input_path})",
    )
    review_fieldnames, raw_review_rows = read_csv_rows_with_header(review_input_path)
    require_header_columns(
        review_fieldnames,
        SNAPSHOT_REVIEW_REQUIRED_FIELDS,
        f"snapshot review input ({review_input_path})",
    )

    staging_rows = [
        canonical_staging_row(row, f"snapshot evidence staging ({staging_input_path})", row_number)
        for row_number, row in enumerate(raw_staging_rows, start=2)
        if not is_blank_row(row)
    ]
    review_rows = [
        canonical_review_row(row, f"snapshot review input ({review_input_path})", row_number)
        for row_number, row in enumerate(raw_review_rows, start=2)
        if not is_blank_row(row)
    ]
    return staging_rows, review_rows


def run_fundamentals_snapshot_review(
    *,
    staging_input_path: str = DEFAULT_EVIDENCE_STAGING_OUTPUT,
    review_input_path: str = DEFAULT_REVIEW_INPUT_PATH,
    registry_output: str = DEFAULT_REVIEW_REGISTRY_OUTPUT,
    promoted_output: str = DEFAULT_PROMOTED_EVIDENCE_OUTPUT,
    backlog_output: str = DEFAULT_REVIEW_BACKLOG_OUTPUT,
    summary_output: str = DEFAULT_REVIEW_SUMMARY_OUTPUT,
    template_output: str | None = DEFAULT_REVIEW_TEMPLATE_PATH,
) -> dict[str, Path]:
    staging_rows, review_rows = load_validated_inputs(staging_input_path, review_input_path)
    staging_index = build_staging_index(staging_rows, f"snapshot evidence staging ({staging_input_path})")
    review_index = build_review_index(review_rows, f"snapshot review input ({review_input_path})")

    registry_rows: list[dict[str, str]] = []
    promoted_rows: list[dict[str, str]] = []
    for identity, review_row in review_index.items():
        staging_row = staging_index.get(identity)
        if staging_row is None:
            identity_text = ", ".join(
                f"{field}={value or '<blank>'}" for field, value in zip(STAGING_MATCH_FIELDS, identity, strict=True)
            )
            raise ValueError(
                f"snapshot review input ({review_input_path}) has no matching staging row for identity: {identity_text}"
            )
        registry_rows.append(registry_row(staging_row, review_row))
        if review_row["review_decision"] == "APPROVE":
            promoted_rows.append(promoted_row(staging_row, review_row))

    backlog_rows: list[dict[str, str]] = []
    for identity, staging_row in sorted(staging_index.items(), key=lambda item: sort_identity_key(item[1])):
        review_row = review_index.get(identity)
        if review_row is None:
            backlog_rows.append(backlog_row(staging_row, backlog_status="NO_REVIEW", latest_review=None))
            continue
        if review_row["review_decision"] == "PENDING":
            backlog_rows.append(backlog_row(staging_row, backlog_status="PENDING", latest_review=review_row))

    registry_rows.sort(key=sort_identity_key)
    promoted_rows = dedupe_rows_by_identity(
        sorted(promoted_rows, key=sort_identity_key),
        identity_fields=EVIDENCE_IDENTITY_FIELDS,
        content_fields=EVIDENCE_INPUT_FIELDS,
        source_name=f"snapshot review input ({review_input_path})",
        conflict_label="promoted evidence identity",
    )
    backlog_rows.sort(key=sort_identity_key)

    decision_counts = Counter(row["review_decision"] for row in review_index.values())
    outputs = {
        "snapshot_review_registry": write_csv_rows(
            registry_output,
            SNAPSHOT_REVIEW_REGISTRY_FIELDS,
            registry_rows,
        ),
        "snapshot_evidence_promoted": write_csv_rows(
            promoted_output,
            EVIDENCE_INPUT_FIELDS,
            promoted_rows,
        ),
        "snapshot_review_backlog": write_csv_rows(
            backlog_output,
            SNAPSHOT_REVIEW_BACKLOG_FIELDS,
            backlog_rows,
        ),
        "snapshot_review_summary": write_csv_rows(
            summary_output,
            SNAPSHOT_REVIEW_SUMMARY_FIELDS,
            build_summary_rows(
                staging_rows_total=len(staging_index),
                review_rows_total=len(review_index),
                approved_rows=decision_counts.get("APPROVE", 0),
                rejected_rows=decision_counts.get("REJECT", 0),
                pending_rows=decision_counts.get("PENDING", 0),
                promoted_rows=len(promoted_rows),
                backlog_rows=len(backlog_rows),
            ),
        ),
    }
    if template_output:
        outputs["snapshot_review_template"] = write_snapshot_review_template(template_output)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review and promote staged local snapshot evidence into an explicit promoted evidence artifact.")
    parser.add_argument("--staging-input", default=DEFAULT_EVIDENCE_STAGING_OUTPUT, help="Snapshot evidence staging CSV input.")
    parser.add_argument("--review-input", default=DEFAULT_REVIEW_INPUT_PATH, help="Manual snapshot review CSV input.")
    parser.add_argument("--registry-output", default=DEFAULT_REVIEW_REGISTRY_OUTPUT, help="Snapshot review registry output.")
    parser.add_argument("--promoted-output", default=DEFAULT_PROMOTED_EVIDENCE_OUTPUT, help="Promoted snapshot evidence output.")
    parser.add_argument("--backlog-output", default=DEFAULT_REVIEW_BACKLOG_OUTPUT, help="Snapshot review backlog output.")
    parser.add_argument("--summary-output", default=DEFAULT_REVIEW_SUMMARY_OUTPUT, help="Snapshot review summary output.")
    parser.add_argument("--template-output", default=DEFAULT_REVIEW_TEMPLATE_PATH, help="Snapshot review input template output.")
    parser.add_argument("--template-only", action="store_true", help="Only write the snapshot review template; do not require staging or review input.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.template_only:
        write_snapshot_review_template(args.template_output)
        return
    run_fundamentals_snapshot_review(
        staging_input_path=args.staging_input,
        review_input_path=args.review_input,
        registry_output=args.registry_output,
        promoted_output=args.promoted_output,
        backlog_output=args.backlog_output,
        summary_output=args.summary_output,
        template_output=args.template_output,
    )


if __name__ == "__main__":
    main()
