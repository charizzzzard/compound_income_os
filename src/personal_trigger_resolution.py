from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from src.canonical_record import (
    GENESIS_PREVIOUS_RECORD_HASH,
    HASH_SCHEMA_VERSION,
    build_hashed_record,
    verify_hash_chain,
)
from src.common import ensure_parent_dir, resolve_repo_path
from src.personal_decision_state_capture import repo_relative_stored_path
from src.personal_decision_trigger_capture import (
    DECIMAL_FIELDS as TRIGGER_DECIMAL_FIELDS,
    DEFAULT_LEDGER as DEFAULT_TRIGGER_LEDGER,
    load_trigger_ledger,
)


DEFAULT_RESOLUTION_LEDGER = "data/processed/personal_trigger_resolutions.csv"
DEFAULT_DUE_REVIEW = "data/processed/personal_due_trigger_review.csv"

FINAL_RESOLUTION_STATUSES = {
    "RESOLVED_TRUE",
    "RESOLVED_FALSE",
    "UNRESOLVABLE_DEFINITION",
    "UNRESOLVABLE_CORPORATE",
}

FIELDS = [
    "trigger_id",
    "resolution_status",
    "resolved_value",
    "resolution_date",
    "resolution_source",
    "resolution_evidence_path",
    "resolution_reason",
    "created_at",
    "hash_schema_version",
    "record_hash",
    "previous_record_hash",
]

DUE_FIELDS = [
    "as_of_date",
    "review_status",
    "days_overdue",
    "trigger_id",
    "decision_id",
    "claim",
    "claim_type",
    "metric_name",
    "expected_resolution_date",
    "resolution_deadline",
    "source_document_type",
    "source_section",
    "line_item",
    "source_paths",
]


def _parse_date(value: Any, field_name: str) -> date:
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO YYYY-MM-DD") from exc


def _parse_datetime(value: Any, field_name: str) -> datetime:
    text = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO timestamp with timezone") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone")
    return parsed


def _required_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} must not be blank")
    return text


def _normalize_evidence_path(value: Any, status: str) -> str:
    text = _required_text(value, "resolution_evidence_path")
    if text == "NOT_APPLICABLE":
        if status in {"RESOLVED_TRUE", "RESOLVED_FALSE"}:
            raise ValueError("binary resolutions require a resolution_evidence_path")
        return text
    return repo_relative_stored_path(text, field_name="resolution_evidence_path")


def load_resolution_ledger(path_value: str = DEFAULT_RESOLUTION_LEDGER) -> list[dict[str, str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [field for field in FIELDS if field not in fieldnames]
        if missing:
            raise ValueError(f"resolution ledger missing required columns: {', '.join(missing)}")
        return [
            {field: str(row.get(field, "") or "").strip() for field in FIELDS}
            for row in reader
            if any(str(value or "").strip() for value in row.values())
        ]


def _write_resolution_ledger(path_value: str, rows: Iterable[Mapping[str, str]]) -> Path:
    path = ensure_parent_dir(path_value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in FIELDS} for row in rows)
    return path


def _validate_trigger_chain(trigger_rows: list[dict[str, str]]) -> None:
    if not trigger_rows:
        raise ValueError("trigger ledger contains no locked triggers")
    trigger_ids = [row.get("trigger_id", "") for row in trigger_rows]
    duplicates = sorted(trigger_id for trigger_id, count in Counter(trigger_ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"trigger ledger contains duplicate trigger_id value(s): {', '.join(duplicates)}")
    verify_hash_chain(trigger_rows, decimal_fields=TRIGGER_DECIMAL_FIELDS)


def validate_resolution_ledger(
    rows: list[dict[str, str]],
    *,
    trigger_rows: list[dict[str, str]],
) -> str:
    _validate_trigger_chain(trigger_rows)
    triggers = {row["trigger_id"]: row for row in trigger_rows}
    ids = [row.get("trigger_id", "") for row in rows]
    duplicates = sorted(trigger_id for trigger_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate trigger resolution(s): {', '.join(duplicates)}")

    for index, row in enumerate(rows, start=1):
        trigger_id = _required_text(row.get("trigger_id"), "trigger_id")
        if trigger_id not in triggers:
            raise ValueError(f"resolution row {index} references unknown trigger_id: {trigger_id}")
        status = _required_text(row.get("resolution_status"), "resolution_status")
        if status not in FINAL_RESOLUTION_STATUSES:
            raise ValueError(
                "resolution_status must be a final state; OVERDUE is derived and cannot be persisted"
            )
        _required_text(row.get("resolved_value"), "resolved_value")
        _required_text(row.get("resolution_source"), "resolution_source")
        _required_text(row.get("resolution_reason"), "resolution_reason")
        _normalize_evidence_path(row.get("resolution_evidence_path"), status)
        resolution_date = _parse_date(row.get("resolution_date"), "resolution_date")
        created_at = _parse_datetime(row.get("created_at"), "created_at")
        locked_at = _parse_datetime(triggers[trigger_id].get("locked_at"), "locked_at")
        if resolution_date < locked_at.date():
            raise ValueError("resolution_date must not be before trigger locked_at")
        if created_at < locked_at:
            raise ValueError("resolution created_at must not be before trigger locked_at")
        if created_at.date() < resolution_date:
            raise ValueError("resolution created_at must not be before resolution_date")
        if status.startswith("UNRESOLVABLE_") and row.get("resolved_value") != "NOT_APPLICABLE":
            raise ValueError("unresolvable resolutions require resolved_value=NOT_APPLICABLE")

    return verify_hash_chain(rows)


def append_trigger_resolution(
    *,
    trigger_id: str,
    resolution_status: str,
    resolved_value: str,
    resolution_date: str,
    resolution_source: str,
    resolution_evidence_path: str,
    resolution_reason: str,
    created_at: str,
    trigger_ledger: str = DEFAULT_TRIGGER_LEDGER,
    resolution_ledger: str = DEFAULT_RESOLUTION_LEDGER,
) -> dict[str, str]:
    trigger_rows = load_trigger_ledger(trigger_ledger)
    _validate_trigger_chain(trigger_rows)
    triggers = {row["trigger_id"]: row for row in trigger_rows}
    normalized_trigger_id = _required_text(trigger_id, "trigger_id")
    if normalized_trigger_id not in triggers:
        raise ValueError(f"trigger_id does not exist in locked trigger ledger: {normalized_trigger_id}")

    existing = load_resolution_ledger(resolution_ledger)
    if existing:
        validate_resolution_ledger(existing, trigger_rows=trigger_rows)
    if normalized_trigger_id in {row["trigger_id"] for row in existing}:
        raise ValueError(f"duplicate trigger resolution: {normalized_trigger_id}")

    status = _required_text(resolution_status, "resolution_status").upper()
    if status not in FINAL_RESOLUTION_STATUSES:
        raise ValueError("resolution_status must be a final state; OVERDUE is derived and cannot be persisted")
    normalized_value = _required_text(resolved_value, "resolved_value")
    if status.startswith("UNRESOLVABLE_") and normalized_value != "NOT_APPLICABLE":
        raise ValueError("unresolvable resolutions require resolved_value=NOT_APPLICABLE")
    normalized_date = _parse_date(resolution_date, "resolution_date").isoformat()
    normalized_created = _parse_datetime(created_at, "created_at").isoformat().replace("+00:00", "Z")
    record = {
        "trigger_id": normalized_trigger_id,
        "resolution_status": status,
        "resolved_value": normalized_value,
        "resolution_date": normalized_date,
        "resolution_source": _required_text(resolution_source, "resolution_source"),
        "resolution_evidence_path": _normalize_evidence_path(resolution_evidence_path, status),
        "resolution_reason": _required_text(resolution_reason, "resolution_reason"),
        "created_at": normalized_created,
        "hash_schema_version": HASH_SCHEMA_VERSION,
    }
    head = verify_hash_chain(existing) if existing else GENESIS_PREVIOUS_RECORD_HASH
    hashed = build_hashed_record(record, previous_record_hash=head)
    candidate = existing + [{field: hashed.get(field, "") for field in FIELDS}]
    validate_resolution_ledger(candidate, trigger_rows=trigger_rows)
    _write_resolution_ledger(resolution_ledger, candidate)
    return candidate[-1]


def build_due_review_rows(
    *,
    trigger_rows: list[dict[str, str]],
    resolution_rows: list[dict[str, str]],
    as_of_date: str,
) -> list[dict[str, str]]:
    if not trigger_rows:
        if resolution_rows:
            raise ValueError("resolution ledger cannot contain rows without a trigger ledger")
        _parse_date(as_of_date, "as_of_date")
        return []
    _validate_trigger_chain(trigger_rows)
    if resolution_rows:
        validate_resolution_ledger(resolution_rows, trigger_rows=trigger_rows)
    as_of = _parse_date(as_of_date, "as_of_date")
    resolved_ids = {row["trigger_id"] for row in resolution_rows}
    due_rows: list[dict[str, str]] = []
    for trigger in trigger_rows:
        if trigger["trigger_id"] in resolved_ids:
            continue
        expected = _parse_date(trigger["expected_resolution_date"], "expected_resolution_date")
        if as_of < expected:
            continue
        deadline = _parse_date(trigger["resolution_deadline"], "resolution_deadline")
        overdue = as_of > deadline
        due_rows.append(
            {
                "as_of_date": as_of.isoformat(),
                "review_status": "OVERDUE" if overdue else "DUE",
                "days_overdue": str((as_of - deadline).days) if overdue else "0",
                "trigger_id": trigger["trigger_id"],
                "decision_id": trigger["decision_id"],
                "claim": trigger["claim"],
                "claim_type": trigger["claim_type"],
                "metric_name": trigger["metric_name"],
                "expected_resolution_date": expected.isoformat(),
                "resolution_deadline": deadline.isoformat(),
                "source_document_type": trigger["source_document_type"],
                "source_section": trigger["source_section"],
                "line_item": trigger["line_item"],
                "source_paths": trigger["source_paths"],
            }
        )
    return sorted(
        due_rows,
        key=lambda row: (row["resolution_deadline"], row["decision_id"], row["trigger_id"]),
    )


def scan_due_triggers(
    *,
    as_of_date: str,
    trigger_ledger: str = DEFAULT_TRIGGER_LEDGER,
    resolution_ledger: str = DEFAULT_RESOLUTION_LEDGER,
    output: str = DEFAULT_DUE_REVIEW,
) -> Path:
    trigger_rows = load_trigger_ledger(trigger_ledger)
    resolution_rows = load_resolution_ledger(resolution_ledger)
    rows = build_due_review_rows(
        trigger_rows=trigger_rows,
        resolution_rows=resolution_rows,
        as_of_date=as_of_date,
    )
    path = ensure_parent_dir(output)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DUE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan locked triggers or append an explicitly human-confirmed final resolution."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan-due")
    scan.add_argument("--as-of-date", required=True)
    scan.add_argument("--trigger-ledger", default=DEFAULT_TRIGGER_LEDGER)
    scan.add_argument("--resolution-ledger", default=DEFAULT_RESOLUTION_LEDGER)
    scan.add_argument("--output", default=DEFAULT_DUE_REVIEW)

    confirm = subparsers.add_parser("confirm")
    confirm.add_argument("--trigger-id", required=True)
    confirm.add_argument("--resolution-status", required=True)
    confirm.add_argument("--resolved-value", required=True)
    confirm.add_argument("--resolution-date", required=True)
    confirm.add_argument("--resolution-source", required=True)
    confirm.add_argument("--resolution-evidence-path", required=True)
    confirm.add_argument("--resolution-reason", required=True)
    confirm.add_argument("--created-at", required=True)
    confirm.add_argument("--trigger-ledger", default=DEFAULT_TRIGGER_LEDGER)
    confirm.add_argument("--resolution-ledger", default=DEFAULT_RESOLUTION_LEDGER)

    validate = subparsers.add_parser("validate-ledger")
    validate.add_argument("--trigger-ledger", default=DEFAULT_TRIGGER_LEDGER)
    validate.add_argument("--resolution-ledger", default=DEFAULT_RESOLUTION_LEDGER)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    try:
        if args.command == "scan-due":
            path = scan_due_triggers(
                as_of_date=args.as_of_date,
                trigger_ledger=args.trigger_ledger,
                resolution_ledger=args.resolution_ledger,
                output=args.output,
            )
            print(f"due_review={path}")
            return
        if args.command == "confirm":
            row = append_trigger_resolution(
                trigger_id=args.trigger_id,
                resolution_status=args.resolution_status,
                resolved_value=args.resolved_value,
                resolution_date=args.resolution_date,
                resolution_source=args.resolution_source,
                resolution_evidence_path=args.resolution_evidence_path,
                resolution_reason=args.resolution_reason,
                created_at=args.created_at,
                trigger_ledger=args.trigger_ledger,
                resolution_ledger=args.resolution_ledger,
            )
            print(f"confirmed_trigger_id={row['trigger_id']}")
            print(f"resolution_status={row['resolution_status']}")
            return
        trigger_rows = load_trigger_ledger(args.trigger_ledger)
        resolution_rows = load_resolution_ledger(args.resolution_ledger)
        head = (
            validate_resolution_ledger(resolution_rows, trigger_rows=trigger_rows)
            if resolution_rows
            else GENESIS_PREVIOUS_RECORD_HASH
        )
        print(f"row_count={len(resolution_rows)}")
        print(f"head_hash={head}")
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
