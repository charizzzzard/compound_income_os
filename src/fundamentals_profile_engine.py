from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows
from src.fundamentals_master import DEFAULT_PERSONAL_MASTER_PATH, PERSONAL_MASTER_FIELDS, VALID_COMPANY_TYPE_PROFILES, validate_personal_fundamentals_master

DEFAULT_PROFILE_REVIEW_INPUT_PATH = "data/raw/personal_fundamentals_profile_review.csv"
DEFAULT_PROFILE_REVIEW_TEMPLATE_PATH = "data/raw/personal_fundamentals_profile_review_template.csv"
DEFAULT_PROFILE_REGISTRY_OUTPUT = "data/processed/personal_fundamentals_profile_registry.csv"
DEFAULT_PROFILE_REVIEW_BACKLOG_OUTPUT = "data/processed/personal_fundamentals_profile_review_backlog.csv"
DEFAULT_PROFILED_MASTER_OUTPUT = "data/processed/personal_fundamentals_master_profiled.csv"

VALID_REVIEW_STATUSES = {"APPROVED", "PENDING", "REJECTED"}

PROFILE_REVIEW_INPUT_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "proposed_company_type_profile",
    "profile_reason",
    "review_status",
    "review_author",
    "review_as_of_date",
    "source_name",
    "source_reference",
    "notes",
]

PROFILE_REVIEW_REQUIRED_FIELDS = PROFILE_REVIEW_INPUT_FIELDS

PROFILE_REVIEW_REGISTRY_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "asset_type",
    "current_company_type_profile",
    "proposed_company_type_profile",
    "profile_reason",
    "review_status",
    "review_author",
    "review_as_of_date",
    "source_name",
    "source_reference",
    "projection_applied",
    "review_identity",
    "notes",
]

PROFILE_REVIEW_BACKLOG_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "asset_type",
    "current_company_type_profile",
    "latest_review_status",
    "latest_proposed_company_type_profile",
    "latest_review_as_of_date",
    "latest_review_author",
    "needs_profile_review_flag",
    "backlog_reason",
    "notes",
]

PROFILE_REVIEW_IDENTITY_FIELDS = [
    "ticker",
    "isin",
    "review_as_of_date",
    "review_author",
    "source_name",
    "source_reference",
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


def master_identifier_key(row: dict[str, str]) -> tuple[str, str]:
    return canonicalize_ticker(row.get("ticker", "")), str(row.get("isin", "") or "").strip().upper()


def validate_master_identifier_uniqueness(master_rows: list[dict[str, str]]) -> None:
    for field, normalizer in [
        ("ticker", lambda row: canonicalize_ticker(row.get("ticker", ""))),
        ("isin", lambda row: str(row.get("isin", "") or "").strip().upper()),
    ]:
        counts = Counter(normalizer(row) for row in master_rows if normalizer(row))
        duplicates = sorted(value for value, count in counts.items() if count > 1)
        if duplicates:
            raise ValueError(
                f"personal fundamentals master has duplicate {field} value(s); profile review matching would be ambiguous: {', '.join(duplicates)}"
            )


def build_master_identifier_index(master_rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    validate_master_identifier_uniqueness(master_rows)
    index: dict[str, dict[str, dict[str, str]]] = {"ticker": {}, "isin": {}}
    for row in master_rows:
        ticker, isin = master_identifier_key(row)
        if ticker:
            index["ticker"][ticker] = row
        if isin:
            index["isin"][isin] = row
    return index


def match_review_to_master(
    row: dict[str, str],
    master_index: dict[str, dict[str, dict[str, str]]],
    source_name: str,
    row_number: int,
) -> dict[str, str]:
    ticker = canonicalize_ticker(row.get("ticker", ""))
    isin = str(row.get("isin", "") or "").strip().upper()
    if not ticker and not isin:
        raise ValueError(f"{source_name} row {row_number} requires ticker or isin for exact Personal-Master matching")

    ticker_match = master_index["ticker"].get(ticker) if ticker else None
    isin_match = master_index["isin"].get(isin) if isin else None
    if ticker and isin and (ticker_match is None or isin_match is None):
        raise ValueError(
            f"{source_name} row {row_number} requires ticker and isin to match the same personal fundamentals master row: "
            f"ticker={ticker}, isin={isin}"
        )
    if ticker_match is not None and isin_match is not None and id(ticker_match) != id(isin_match):
        raise ValueError(
            f"{source_name} row {row_number} has conflicting ticker/isin matches in personal fundamentals master: ticker={ticker}, isin={isin}"
        )

    matched = isin_match or ticker_match
    if matched is None:
        raise ValueError(
            f"{source_name} row {row_number} has no exact ticker/isin match in personal fundamentals master: "
            f"ticker={ticker or '<blank>'}, isin={isin or '<blank>'}"
        )
    return matched


def review_identity(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "") or "").strip() for field in PROFILE_REVIEW_IDENTITY_FIELDS)


def review_identity_text(identity: tuple[str, ...]) -> str:
    return ", ".join(f"{field}={value or '<blank>'}" for field, value in zip(PROFILE_REVIEW_IDENTITY_FIELDS, identity, strict=True))


def registry_content_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "") or "").strip() for field in PROFILE_REVIEW_REGISTRY_FIELDS)


def registry_sort_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        canonicalize_ticker(row.get("ticker", "")),
        str(row.get("isin", "") or "").strip().upper(),
        str(row.get("review_as_of_date", "") or "").strip(),
        str(row.get("review_status", "") or "").strip(),
        str(row.get("review_author", "") or "").strip(),
        str(row.get("source_name", "") or "").strip(),
        str(row.get("source_reference", "") or "").strip(),
    )


def canonical_profile_review_row(
    row: dict[str, str],
    master_row: dict[str, str],
    source_name: str,
    row_number: int,
) -> dict[str, str]:
    require_nonblank_value(row, "company_name", source_name, row_number)
    proposed_profile = safe_upper(require_nonblank_value(row, "proposed_company_type_profile", source_name, row_number))
    if proposed_profile not in VALID_COMPANY_TYPE_PROFILES:
        raise ValueError(
            f"{source_name} row {row_number} has invalid proposed_company_type_profile: {row.get('proposed_company_type_profile')!r}; "
            f"allowed: {', '.join(sorted(VALID_COMPANY_TYPE_PROFILES))}"
        )
    review_status = safe_upper(require_nonblank_value(row, "review_status", source_name, row_number))
    if review_status not in VALID_REVIEW_STATUSES:
        raise ValueError(
            f"{source_name} row {row_number} has invalid review_status: {row.get('review_status')!r}; "
            f"allowed: {', '.join(sorted(VALID_REVIEW_STATUSES))}"
        )
    review_author = require_nonblank_value(row, "review_author", source_name, row_number)
    review_as_of_date = parse_iso_date_text(row.get("review_as_of_date", ""), "review_as_of_date", source_name, row_number)
    source_name_text = require_nonblank_value(row, "source_name", source_name, row_number)
    source_reference = require_nonblank_value(row, "source_reference", source_name, row_number)
    profile_reason = str(row.get("profile_reason", "") or "").strip()
    if proposed_profile == "OTHER" and not profile_reason:
        raise ValueError(f"{source_name} row {row_number} has proposed_company_type_profile=OTHER but blank profile_reason")

    ticker, isin = master_identifier_key(master_row)
    registry_row = {
        "ticker": ticker,
        "isin": isin,
        "company_name": str(master_row.get("company_name", "") or "").strip(),
        "asset_type": str(master_row.get("asset_type", "") or "").strip(),
        "current_company_type_profile": safe_upper(master_row.get("company_type_profile", "")),
        "proposed_company_type_profile": proposed_profile,
        "profile_reason": profile_reason,
        "review_status": review_status,
        "review_author": review_author,
        "review_as_of_date": review_as_of_date,
        "source_name": source_name_text,
        "source_reference": source_reference,
        "projection_applied": str(review_status == "APPROVED"),
        "review_identity": "",
        "notes": str(row.get("notes", "") or "").strip(),
    }
    registry_row["review_identity"] = review_identity_text(review_identity(registry_row))
    return registry_row


def dedupe_registry_rows(rows: list[dict[str, str]], source_name: str) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: dict[tuple[str, ...], tuple[str, ...]] = {}
    for row in rows:
        identity = review_identity(row)
        content = registry_content_key(row)
        existing = seen.get(identity)
        if existing is None:
            seen[identity] = content
            deduped.append(row)
            continue
        if existing != content:
            raise ValueError(f"{source_name} has conflicting rows for the same review identity: {row['review_identity']}")
    deduped.sort(key=registry_sort_key)
    return deduped


def validate_approved_projection_conflicts(rows: list[dict[str, str]], source_name: str) -> None:
    approved_by_identity: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for row in rows:
        if row["review_status"] != "APPROVED":
            continue
        identity = (canonicalize_ticker(row.get("ticker", "")), str(row.get("isin", "") or "").strip().upper())
        approved_by_identity.setdefault(identity, set()).add(
            (
                str(row.get("proposed_company_type_profile", "") or "").strip(),
                str(row.get("profile_reason", "") or "").strip(),
            )
        )
    conflicts = sorted(identity for identity, values in approved_by_identity.items() if len(values) > 1)
    if conflicts:
        conflict_text = ", ".join(f"ticker={ticker or '<blank>'}, isin={isin or '<blank>'}" for ticker, isin in conflicts)
        raise ValueError(f"{source_name} has conflicting APPROVED profile review rows for the same master identity: {conflict_text}")


def build_profile_registry(
    review_rows: list[dict[str, str]],
    master_rows: list[dict[str, str]],
    source_name: str = "personal fundamentals profile review",
) -> list[dict[str, str]]:
    validate_personal_fundamentals_master(master_rows, f"personal fundamentals master ({source_name})")
    master_index = build_master_identifier_index(master_rows)
    registry_rows = [
        canonical_profile_review_row(row, match_review_to_master(row, master_index, source_name, row_number), source_name, row_number)
        for row_number, row in enumerate(review_rows, start=2)
    ]
    deduped_rows = dedupe_registry_rows(registry_rows, source_name)
    validate_approved_projection_conflicts(deduped_rows, source_name)
    return deduped_rows


def latest_registry_rows_by_identity(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    latest: dict[tuple[str, str], dict[str, str]] = {}
    status_priority = {"REJECTED": 0, "PENDING": 1, "APPROVED": 2}
    for row in rows:
        identity = (canonicalize_ticker(row.get("ticker", "")), str(row.get("isin", "") or "").strip().upper())
        current = latest.get(identity)
        if current is None:
            latest[identity] = row
            continue
        current_key = (
            str(current.get("review_as_of_date", "") or "").strip(),
            status_priority.get(str(current.get("review_status", "") or "").strip(), -1),
            str(current.get("source_name", "") or "").strip(),
            str(current.get("source_reference", "") or "").strip(),
            str(current.get("review_author", "") or "").strip(),
        )
        row_key = (
            str(row.get("review_as_of_date", "") or "").strip(),
            status_priority.get(str(row.get("review_status", "") or "").strip(), -1),
            str(row.get("source_name", "") or "").strip(),
            str(row.get("source_reference", "") or "").strip(),
            str(row.get("review_author", "") or "").strip(),
        )
        if row_key >= current_key:
            latest[identity] = row
    return latest


def latest_approved_rows_by_identity(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    approved_rows = [row for row in rows if row["review_status"] == "APPROVED"]
    return latest_registry_rows_by_identity(approved_rows)


def append_profile_review_note(existing_notes: str, approved_row: dict[str, str]) -> str:
    parts = [
        f"profile_review_applied_profile={approved_row['proposed_company_type_profile']}",
        f"profile_review_as_of_date={approved_row['review_as_of_date']}",
        f"profile_review_author={approved_row['review_author']}",
        f"profile_review_source_name={approved_row['source_name']}",
        f"profile_review_source_reference={approved_row['source_reference']}",
    ]
    profile_reason = str(approved_row.get("profile_reason", "") or "").strip()
    if profile_reason:
        if approved_row["proposed_company_type_profile"] == "OTHER":
            parts.append(f"company_type_profile_reason={profile_reason}")
        else:
            parts.append(f"profile_reason={profile_reason}")
    appended = "; ".join(parts)
    base = str(existing_notes or "").strip()
    return f"{base} | {appended}" if base else appended


def build_profiled_master_rows(master_rows: list[dict[str, str]], registry_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    approved_by_identity = latest_approved_rows_by_identity(registry_rows)
    profiled_rows: list[dict[str, str]] = []
    for master_row in master_rows:
        row = dict(master_row)
        identity = master_identifier_key(master_row)
        approved = approved_by_identity.get(identity)
        if approved:
            row["company_type_profile"] = approved["proposed_company_type_profile"]
            row["notes"] = append_profile_review_note(row.get("notes", ""), approved)
        profiled_rows.append(row)
    validate_personal_fundamentals_master(profiled_rows, "personal fundamentals profiled master")
    return profiled_rows


def backlog_sort_key(row: dict[str, str]) -> tuple[int, str, str]:
    reason = str(row.get("backlog_reason", "") or "")
    priority = 2
    if "Pending profile review" in reason:
        priority = 0
    elif "Latest profile review was rejected" in reason:
        priority = 1
    return (priority, canonicalize_ticker(row.get("ticker", "")), str(row.get("isin", "") or "").strip().upper())


def build_profile_review_backlog_rows(master_rows: list[dict[str, str]], registry_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    latest_by_identity = latest_registry_rows_by_identity(registry_rows)
    approved_by_identity = latest_approved_rows_by_identity(registry_rows)
    backlog_rows: list[dict[str, str]] = []
    for master_row in master_rows:
        identity = master_identifier_key(master_row)
        latest = latest_by_identity.get(identity)
        has_approved = identity in approved_by_identity
        current_profile = safe_upper(master_row.get("company_type_profile", ""))
        backlog_reason = ""
        if latest and latest["review_status"] == "PENDING":
            backlog_reason = "Pending profile review exists and has not been approved."
        elif latest and latest["review_status"] == "REJECTED" and current_profile == "OTHER" and not has_approved:
            backlog_reason = "Latest profile review was rejected; master profile remains OTHER without approved replacement."
        elif current_profile == "OTHER" and not has_approved:
            backlog_reason = "Master profile remains OTHER without APPROVED profile review."
        if not backlog_reason:
            continue
        backlog_rows.append(
            {
                "ticker": identity[0],
                "isin": identity[1],
                "company_name": str(master_row.get("company_name", "") or "").strip(),
                "asset_type": str(master_row.get("asset_type", "") or "").strip(),
                "current_company_type_profile": current_profile,
                "latest_review_status": str(latest.get("review_status", "") or "").strip() if latest else "",
                "latest_proposed_company_type_profile": str(latest.get("proposed_company_type_profile", "") or "").strip() if latest else "",
                "latest_review_as_of_date": str(latest.get("review_as_of_date", "") or "").strip() if latest else "",
                "latest_review_author": str(latest.get("review_author", "") or "").strip() if latest else "",
                "needs_profile_review_flag": "True",
                "backlog_reason": backlog_reason,
                "notes": str(latest.get("notes", "") or "").strip() if latest else "",
            }
        )
    backlog_rows.sort(key=backlog_sort_key)
    return backlog_rows


def load_validated_inputs(
    fundamentals_master_path: str,
    profile_review_input_path: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    master_rows = read_csv_rows(fundamentals_master_path)
    validate_personal_fundamentals_master(master_rows, f"personal fundamentals master ({fundamentals_master_path})")
    fieldnames, review_rows = read_csv_rows_with_header(profile_review_input_path)
    require_header_columns(fieldnames, PROFILE_REVIEW_REQUIRED_FIELDS, f"personal fundamentals profile review ({profile_review_input_path})")
    return master_rows, review_rows


def write_profile_review_template(path_value: str = DEFAULT_PROFILE_REVIEW_TEMPLATE_PATH) -> Path:
    return write_csv_rows(path_value, PROFILE_REVIEW_INPUT_FIELDS, [])


def run_fundamentals_profile_engine(
    fundamentals_master_path: str,
    profile_review_input_path: str,
    registry_output: str = DEFAULT_PROFILE_REGISTRY_OUTPUT,
    backlog_output: str = DEFAULT_PROFILE_REVIEW_BACKLOG_OUTPUT,
    profiled_master_output: str = DEFAULT_PROFILED_MASTER_OUTPUT,
    template_output: str | None = DEFAULT_PROFILE_REVIEW_TEMPLATE_PATH,
) -> dict[str, Path]:
    master_rows, review_rows = load_validated_inputs(fundamentals_master_path, profile_review_input_path)
    registry_rows = build_profile_registry(
        review_rows,
        master_rows,
        source_name=f"personal fundamentals profile review ({profile_review_input_path})",
    )
    backlog_rows = build_profile_review_backlog_rows(master_rows, registry_rows)
    profiled_master_rows = build_profiled_master_rows(master_rows, registry_rows)

    outputs = {
        "profile_registry": write_csv_rows(registry_output, PROFILE_REVIEW_REGISTRY_FIELDS, registry_rows),
        "profile_review_backlog": write_csv_rows(backlog_output, PROFILE_REVIEW_BACKLOG_FIELDS, backlog_rows),
        "profiled_master": write_csv_rows(profiled_master_output, PERSONAL_MASTER_FIELDS, profiled_master_rows),
    }
    if template_output:
        outputs["profile_review_template"] = write_profile_review_template(template_output)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a manual company_type_profile review registry, backlog and profiled master projection.")
    parser.add_argument("--fundamentals-master", default=DEFAULT_PERSONAL_MASTER_PATH, help="Personal fundamentals master CSV.")
    parser.add_argument("--profile-review-input", default=DEFAULT_PROFILE_REVIEW_INPUT_PATH, help="Manual personal profile review CSV.")
    parser.add_argument("--registry-output", default=DEFAULT_PROFILE_REGISTRY_OUTPUT, help="Normalized profile review registry output.")
    parser.add_argument("--backlog-output", default=DEFAULT_PROFILE_REVIEW_BACKLOG_OUTPUT, help="Profile review backlog output.")
    parser.add_argument("--profiled-master-output", default=DEFAULT_PROFILED_MASTER_OUTPUT, help="Projected profiled master output.")
    parser.add_argument("--template-output", default=DEFAULT_PROFILE_REVIEW_TEMPLATE_PATH, help="Profile review input template output.")
    parser.add_argument("--template-only", action="store_true", help="Only write the profile review template; do not require master or review input.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.template_only:
        write_profile_review_template(args.template_output)
        return
    run_fundamentals_profile_engine(
        fundamentals_master_path=args.fundamentals_master,
        profile_review_input_path=args.profile_review_input,
        registry_output=args.registry_output,
        backlog_output=args.backlog_output,
        profiled_master_output=args.profiled_master_output,
        template_output=args.template_output,
    )


if __name__ == "__main__":
    main()
