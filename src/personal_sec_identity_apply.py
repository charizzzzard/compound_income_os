from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows
from src.external_sec_companyfacts_fetch import (
    DEFAULT_SEC_IDENTITY_MAP_INPUT,
    IDENTITY_MAP_FIELDS,
    SUPPORTED_ASSET_TYPES,
    SUPPORTED_COUNTRIES,
    canonical_cik,
    canonical_isin,
    validate_identity_map_rows,
)
from src.fundamentals_evidence_apply import DEFAULT_EVIDENCE_APPLIED_MASTER_OUTPUT
from src.fundamentals_master import PERSONAL_MASTER_FIELDS, validate_personal_fundamentals_master
from src.personal_sec_identity_export import build_identity_map_rows
from src.personal_sec_scope_prepare import DEFAULT_REVIEW_OUTPUT, load_review_rows, parse_enabled

DEFAULT_IDENTITY_APPLIED_MASTER_OUTPUT = "data/processed/personal_fundamentals_master_evidence_identity_applied.csv"
DEFAULT_IDENTITY_APPLY_CHANGES_OUTPUT = "data/processed/personal_sec_identity_apply_changes.csv"
DEFAULT_IDENTITY_APPLY_SUMMARY_OUTPUT = "data/processed/personal_sec_identity_apply_summary.csv"

IDENTITY_APPLY_CHANGE_FIELDS = [
    "isin",
    "company_name",
    "current_ticker",
    "projected_ticker",
    "current_country",
    "projected_country",
    "current_asset_type",
    "projected_asset_type",
    "reviewed_cik",
    "sec_entity_name",
    "projection_status",
    "changed_fields",
    "notes",
]

IDENTITY_APPLY_SUMMARY_FIELDS = [
    "base_master_rows_total",
    "review_rows_total",
    "exportable_review_rows_total",
    "identity_map_rows_total",
    "matched_review_identity_rows_total",
    "applied_rows_total",
    "ticker_projected_total",
    "country_projected_total",
    "asset_type_projected_total",
    "notes_updated_total",
    "skipped_no_identity_map_total",
    "skipped_no_master_match_total",
    "unchanged_rows_total",
    "notes",
]

IDENTITY_APPLY_NOTE_PREFIX = "sec_identity_apply"


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


def company_name_text(value: Any) -> str:
    return str(value or "").strip()


def identity_content_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        canonicalize_ticker(row.get("ticker", "")),
        canonical_isin(row.get("isin", "")),
        company_name_text(row.get("company_name", "")),
        canonical_cik(row.get("cik", "")),
        company_name_text(row.get("sec_entity_name", "")),
        safe_upper(row.get("asset_type", "")),
        safe_upper(row.get("country", "")),
        str(parse_enabled(row.get("enabled", ""))),
    )


def build_unique_identity_index(rows: list[dict[str, str]], source_name: str) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    seen_content: dict[str, tuple[str, ...]] = {}
    for row in rows:
        isin = canonical_isin(row.get("isin", ""))
        if not isin:
            raise ValueError(f"{source_name} has row without isin; exact SEC identity projection requires isin")
        content = identity_content_key(row)
        existing = seen_content.get(isin)
        if existing is None:
            seen_content[isin] = content
            index[isin] = row
            continue
        if existing != content:
            raise ValueError(f"{source_name} has conflicting rows for isin={isin}")
    return index


def build_master_isin_index(master_rows: list[dict[str, str]], source_name: str) -> dict[str, int]:
    index: dict[str, int] = {}
    for row_number, row in enumerate(master_rows, start=2):
        isin = canonical_isin(row.get("isin", ""))
        if not isin:
            continue
        if isin in index:
            raise ValueError(f"{source_name} has duplicate isin value(s); exact SEC identity projection would be ambiguous: {isin}")
        index[isin] = row_number - 2
    return index


def validate_supported_identity_row(identity_row: dict[str, str], source_name: str) -> None:
    asset_type = safe_upper(identity_row.get("asset_type", ""))
    country = safe_upper(identity_row.get("country", ""))
    if asset_type not in SUPPORTED_ASSET_TYPES:
        raise ValueError(f"{source_name} has unsupported asset_type for SEC identity projection: {asset_type or '<blank>'}")
    if country not in SUPPORTED_COUNTRIES:
        raise ValueError(f"{source_name} has unsupported country for SEC identity projection: {country or '<blank>'}")
    if not parse_enabled(identity_row.get("enabled", "")):
        raise ValueError(f"{source_name} requires enabled=true for reviewed SEC identity projection")
    if not canonicalize_ticker(identity_row.get("ticker", "")):
        raise ValueError(f"{source_name} requires non-blank canonical ticker for reviewed SEC identity projection")
    if not canonical_cik(identity_row.get("cik", "")):
        raise ValueError(f"{source_name} requires non-blank cik for reviewed SEC identity projection")


def assert_consistent_review_and_identity_map(review_identity_row: dict[str, str], identity_map_row: dict[str, str], isin: str) -> None:
    review_ticker = canonicalize_ticker(review_identity_row.get("ticker", ""))
    map_ticker = canonicalize_ticker(identity_map_row.get("ticker", ""))
    if review_ticker != map_ticker:
        raise ValueError(f"reviewed SEC identity and private identity-map disagree for isin={isin}: ticker {review_ticker!r} != {map_ticker!r}")
    review_cik = canonical_cik(review_identity_row.get("cik", ""))
    map_cik = canonical_cik(identity_map_row.get("cik", ""))
    if review_cik != map_cik:
        raise ValueError(f"reviewed SEC identity and private identity-map disagree for isin={isin}: cik {review_cik!r} != {map_cik!r}")
    review_asset_type = safe_upper(review_identity_row.get("asset_type", ""))
    map_asset_type = safe_upper(identity_map_row.get("asset_type", ""))
    if review_asset_type != map_asset_type:
        raise ValueError(
            f"reviewed SEC identity and private identity-map disagree for isin={isin}: asset_type {review_asset_type!r} != {map_asset_type!r}"
        )
    review_country = safe_upper(review_identity_row.get("country", ""))
    map_country = safe_upper(identity_map_row.get("country", ""))
    if review_country != map_country:
        raise ValueError(f"reviewed SEC identity and private identity-map disagree for isin={isin}: country {review_country!r} != {map_country!r}")
    review_enabled = parse_enabled(review_identity_row.get("enabled", ""))
    map_enabled = parse_enabled(identity_map_row.get("enabled", ""))
    if review_enabled != map_enabled:
        raise ValueError(f"reviewed SEC identity and private identity-map disagree for isin={isin}: enabled {review_enabled!r} != {map_enabled!r}")


def append_identity_apply_note(existing_notes: str, identity_row: dict[str, str]) -> tuple[str, bool]:
    marker = (
        f"{IDENTITY_APPLY_NOTE_PREFIX}_ticker={canonicalize_ticker(identity_row.get('ticker', ''))}; "
        f"{IDENTITY_APPLY_NOTE_PREFIX}_country={safe_upper(identity_row.get('country', ''))}; "
        f"{IDENTITY_APPLY_NOTE_PREFIX}_asset_type={safe_upper(identity_row.get('asset_type', ''))}; "
        f"{IDENTITY_APPLY_NOTE_PREFIX}_cik={canonical_cik(identity_row.get('cik', ''))}"
    )
    base = str(existing_notes or "").strip()
    if marker in base:
        return base, False
    if not base:
        return marker, True
    return f"{base}; {marker}", True


def change_row(
    *,
    master_row: dict[str, str],
    identity_row: dict[str, str] | None,
    projection_status: str,
    changed_fields: list[str],
    notes: str,
) -> dict[str, str]:
    identity = identity_row or {}
    return {
        "isin": canonical_isin(master_row.get("isin", "")),
        "company_name": company_name_text(master_row.get("company_name", "")),
        "current_ticker": canonicalize_ticker(master_row.get("ticker", "")),
        "projected_ticker": canonicalize_ticker(identity.get("ticker", "")),
        "current_country": safe_upper(master_row.get("country", "")),
        "projected_country": safe_upper(identity.get("country", "")),
        "current_asset_type": safe_upper(master_row.get("asset_type", "")),
        "projected_asset_type": safe_upper(identity.get("asset_type", "")),
        "reviewed_cik": canonical_cik(identity.get("cik", "")),
        "sec_entity_name": company_name_text(identity.get("sec_entity_name", "")),
        "projection_status": projection_status,
        "changed_fields": ";".join(changed_fields),
        "notes": notes,
    }


def change_sort_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        canonical_isin(row.get("isin", "")),
        canonicalize_ticker(row.get("projected_ticker", "")),
        company_name_text(row.get("company_name", "")),
    )


def build_identity_applied_master_projection(
    master_rows: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    identity_map_rows: list[dict[str, str]],
    *,
    review_source_name: str,
    identity_map_source_name: str,
    master_source_name: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, int]]:
    exportable_review_identity_rows = build_identity_map_rows(review_rows)
    review_index = build_unique_identity_index(exportable_review_identity_rows, review_source_name)
    identity_index = build_unique_identity_index(identity_map_rows, identity_map_source_name)
    master_index = build_master_isin_index(master_rows, master_source_name)
    applied_master_rows = [{field: str(row.get(field, "") or "").strip() for field in PERSONAL_MASTER_FIELDS} for row in master_rows]
    counters: Counter[str] = Counter()
    change_rows: list[dict[str, str]] = []

    counters["review_rows_total"] = len(review_rows)
    counters["exportable_review_rows_total"] = len(exportable_review_identity_rows)
    counters["identity_map_rows_total"] = len(identity_map_rows)

    for isin in sorted(review_index):
        review_identity_row = review_index[isin]
        identity_map_row = identity_index.get(isin)
        if identity_map_row is None:
            counters["skipped_no_identity_map_total"] += 1
            if isin in master_index:
                change_rows.append(
                    change_row(
                        master_row=applied_master_rows[master_index[isin]],
                        identity_row=review_identity_row,
                        projection_status="SKIPPED_NO_IDENTITY_MAP",
                        changed_fields=[],
                        notes="Projection skipped because the approved reviewed SEC identity is missing in the private identity-map.",
                    )
                )
            continue

        validate_supported_identity_row(review_identity_row, review_source_name)
        validate_supported_identity_row(identity_map_row, identity_map_source_name)
        assert_consistent_review_and_identity_map(review_identity_row, identity_map_row, isin)
        counters["matched_review_identity_rows_total"] += 1

        matched_index = master_index.get(isin)
        if matched_index is None:
            counters["skipped_no_master_match_total"] += 1
            change_rows.append(
                change_row(
                    master_row={field: "" for field in PERSONAL_MASTER_FIELDS} | {"isin": isin, "company_name": review_identity_row.get("company_name", "")},
                    identity_row=identity_map_row,
                    projection_status="SKIPPED_NO_MASTER_MATCH",
                    changed_fields=[],
                    notes="Projection skipped because no exact ISIN match exists in the evidence-applied master.",
                )
            )
            continue

        master_row = applied_master_rows[matched_index]
        changed_fields: list[str] = []
        projected_ticker = canonicalize_ticker(identity_map_row.get("ticker", ""))
        if canonicalize_ticker(master_row.get("ticker", "")) != projected_ticker:
            master_row["ticker"] = projected_ticker
            changed_fields.append("ticker")
            counters["ticker_projected_total"] += 1

        projected_country = safe_upper(identity_map_row.get("country", ""))
        if safe_upper(master_row.get("country", "")) != projected_country:
            master_row["country"] = projected_country
            changed_fields.append("country")
            counters["country_projected_total"] += 1

        projected_asset_type = safe_upper(identity_map_row.get("asset_type", ""))
        if safe_upper(master_row.get("asset_type", "")) != projected_asset_type:
            master_row["asset_type"] = projected_asset_type
            changed_fields.append("asset_type")
            counters["asset_type_projected_total"] += 1

        updated_notes, notes_changed = append_identity_apply_note(master_row.get("notes", ""), identity_map_row)
        if notes_changed:
            master_row["notes"] = updated_notes
            changed_fields.append("notes")
            counters["notes_updated_total"] += 1

        if changed_fields:
            counters["applied_rows_total"] += 1
            status = "APPLIED"
            note_text = "Applied reviewed/exported SEC identity and supported US STOCK scope by exact ISIN bridge."
        else:
            counters["unchanged_rows_total"] += 1
            status = "NO_CHANGES"
            note_text = "Reviewed/exported SEC identity already matched the evidence-applied master."

        change_rows.append(
            change_row(
                master_row=master_rows[matched_index],
                identity_row=identity_map_row,
                projection_status=status,
                changed_fields=changed_fields,
                notes=note_text,
            )
        )

    validate_personal_fundamentals_master(applied_master_rows, "personal fundamentals SEC identity-applied master")
    return applied_master_rows, sorted(change_rows, key=change_sort_key), dict(counters)


def build_summary_row(master_rows: list[dict[str, str]], counters: dict[str, int]) -> list[dict[str, str]]:
    return [
        {
            "base_master_rows_total": str(len(master_rows)),
            "review_rows_total": str(counters.get("review_rows_total", 0)),
            "exportable_review_rows_total": str(counters.get("exportable_review_rows_total", 0)),
            "identity_map_rows_total": str(counters.get("identity_map_rows_total", 0)),
            "matched_review_identity_rows_total": str(counters.get("matched_review_identity_rows_total", 0)),
            "applied_rows_total": str(counters.get("applied_rows_total", 0)),
            "ticker_projected_total": str(counters.get("ticker_projected_total", 0)),
            "country_projected_total": str(counters.get("country_projected_total", 0)),
            "asset_type_projected_total": str(counters.get("asset_type_projected_total", 0)),
            "notes_updated_total": str(counters.get("notes_updated_total", 0)),
            "skipped_no_identity_map_total": str(counters.get("skipped_no_identity_map_total", 0)),
            "skipped_no_master_match_total": str(counters.get("skipped_no_master_match_total", 0)),
            "unchanged_rows_total": str(counters.get("unchanged_rows_total", 0)),
            "notes": "Projection uses reviewed/exported SEC identities via exact ISIN bridge into a separate evidence+identity-applied master; company_type_profile remains untouched.",
        }
    ]


def run_personal_sec_identity_apply(
    *,
    evidence_applied_master_input: str = DEFAULT_EVIDENCE_APPLIED_MASTER_OUTPUT,
    review_input: str = DEFAULT_REVIEW_OUTPUT,
    identity_map_input: str = DEFAULT_SEC_IDENTITY_MAP_INPUT,
    changes_output: str = DEFAULT_IDENTITY_APPLY_CHANGES_OUTPUT,
    identity_applied_master_output: str = DEFAULT_IDENTITY_APPLIED_MASTER_OUTPUT,
    summary_output: str = DEFAULT_IDENTITY_APPLY_SUMMARY_OUTPUT,
) -> dict[str, Path]:
    master_rows = read_csv_rows(evidence_applied_master_input)
    validate_personal_fundamentals_master(master_rows, f"personal fundamentals evidence-applied master ({evidence_applied_master_input})")
    review_rows = load_review_rows(review_input)
    identity_fieldnames, raw_identity_rows = read_csv_rows_with_header(identity_map_input)
    require_header_columns(identity_fieldnames, IDENTITY_MAP_FIELDS, f"private SEC identity-map ({identity_map_input})")
    identity_map_rows = validate_identity_map_rows(raw_identity_rows, f"private SEC identity-map ({identity_map_input})")

    applied_master_rows, change_rows, counters = build_identity_applied_master_projection(
        master_rows,
        review_rows,
        identity_map_rows,
        review_source_name=f"SEC scope review ({review_input})",
        identity_map_source_name=f"private SEC identity-map ({identity_map_input})",
        master_source_name=f"personal fundamentals evidence-applied master ({evidence_applied_master_input})",
    )
    return {
        "identity_apply_changes": write_csv_rows(changes_output, IDENTITY_APPLY_CHANGE_FIELDS, change_rows),
        "identity_applied_master": write_csv_rows(identity_applied_master_output, PERSONAL_MASTER_FIELDS, applied_master_rows),
        "identity_apply_summary": write_csv_rows(summary_output, IDENTITY_APPLY_SUMMARY_FIELDS, build_summary_row(master_rows, counters)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project reviewed/exported SEC identity fields into a separate evidence+identity-applied Personal-Master.")
    parser.add_argument(
        "--evidence-applied-master-input",
        default=DEFAULT_EVIDENCE_APPLIED_MASTER_OUTPUT,
        help="Existing evidence-applied Personal-Master input.",
    )
    parser.add_argument("--review-input", default=DEFAULT_REVIEW_OUTPUT, help="Reviewed SEC scope review CSV.")
    parser.add_argument("--identity-map-input", default=DEFAULT_SEC_IDENTITY_MAP_INPUT, help="Reviewed private SEC identity-map CSV.")
    parser.add_argument("--changes-output", default=DEFAULT_IDENTITY_APPLY_CHANGES_OUTPUT, help="SEC identity-apply changes output.")
    parser.add_argument(
        "--identity-applied-master-output",
        default=DEFAULT_IDENTITY_APPLIED_MASTER_OUTPUT,
        help="Evidence+identity-applied Personal-Master output.",
    )
    parser.add_argument("--summary-output", default=DEFAULT_IDENTITY_APPLY_SUMMARY_OUTPUT, help="SEC identity-apply summary output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_personal_sec_identity_apply(
        evidence_applied_master_input=args.evidence_applied_master_input,
        review_input=args.review_input,
        identity_map_input=args.identity_map_input,
        changes_output=args.changes_output,
        identity_applied_master_output=args.identity_applied_master_output,
        summary_output=args.summary_output,
    )


if __name__ == "__main__":
    main()
