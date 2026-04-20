from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from src.common import canonicalize_ticker, read_csv_rows, safe_upper, write_csv_rows
from src.external_sec_companyfacts_fetch import (
    DEFAULT_SEC_IDENTITY_MAP_INPUT,
    IDENTITY_MAP_FIELDS,
    canonical_cik,
    canonical_isin,
    validate_identity_map_rows,
)
from src.fundamentals_master import validate_personal_fundamentals_master
from src.fundamentals_profile_engine import PROFILE_REVIEW_INPUT_FIELDS
from src.personal_sec_identity_apply import (
    DEFAULT_IDENTITY_APPLIED_MASTER_OUTPUT,
    assert_consistent_review_and_identity_map,
    build_master_isin_index,
    build_unique_identity_index,
    read_csv_rows_with_header,
    require_header_columns,
    validate_supported_identity_row,
)
from src.personal_sec_identity_export import build_identity_map_rows
from src.personal_sec_scope_prepare import DEFAULT_REVIEW_OUTPUT, load_review_rows

DEFAULT_PROFILE_SEED_OUTPUT = "data/processed/personal_fundamentals_profile_review_seed_from_sec_identity.csv"
DEFAULT_PROFILE_SEED_SUMMARY_OUTPUT = "data/processed/personal_profile_seed_summary.csv"

PROFILE_SEED_SUMMARY_FIELDS = [
    "identity_applied_master_rows_total",
    "review_rows_total",
    "exportable_review_rows_total",
    "identity_map_rows_total",
    "matched_review_identity_rows_total",
    "seeded_rows_total",
    "skipped_no_identity_map_total",
    "skipped_no_master_match_total",
    "notes",
]


def assert_consistent_identity_applied_master(master_row: dict[str, str], identity_row: dict[str, str], isin: str) -> None:
    master_ticker = canonicalize_ticker(master_row.get("ticker", ""))
    identity_ticker = canonicalize_ticker(identity_row.get("ticker", ""))
    if master_ticker != identity_ticker:
        raise ValueError(
            f"identity-applied master disagrees with reviewed SEC identity for isin={isin}: "
            f"ticker {master_ticker!r} != {identity_ticker!r}"
        )
    master_country = safe_upper(master_row.get("country", ""))
    identity_country = safe_upper(identity_row.get("country", ""))
    if master_country != identity_country:
        raise ValueError(
            f"identity-applied master disagrees with reviewed SEC identity for isin={isin}: "
            f"country {master_country!r} != {identity_country!r}"
        )
    master_asset_type = safe_upper(master_row.get("asset_type", ""))
    identity_asset_type = safe_upper(identity_row.get("asset_type", ""))
    if master_asset_type != identity_asset_type:
        raise ValueError(
            f"identity-applied master disagrees with reviewed SEC identity for isin={isin}: "
            f"asset_type {master_asset_type!r} != {identity_asset_type!r}"
        )


def build_seed_notes(master_row: dict[str, str], identity_row: dict[str, str]) -> str:
    parts = [
        "Manual profile review seed from reviewed/exported SEC identity-applied US STOCK scope.",
        "company_type_profile must be reviewed manually.",
        f"current_company_type_profile={safe_upper(master_row.get('company_type_profile', '')) or '<blank>'}",
        f"sec_identity_ticker={canonicalize_ticker(identity_row.get('ticker', ''))}",
        f"sec_identity_country={safe_upper(identity_row.get('country', ''))}",
        f"sec_identity_cik={canonical_cik(identity_row.get('cik', ''))}",
    ]
    return " ".join(parts)


def profile_seed_row(master_row: dict[str, str], identity_row: dict[str, str]) -> dict[str, str]:
    return {
        "ticker": canonicalize_ticker(master_row.get("ticker", "")),
        "isin": canonical_isin(master_row.get("isin", "")),
        "company_name": str(master_row.get("company_name", "") or "").strip(),
        "proposed_company_type_profile": "",
        "profile_reason": "",
        "review_status": "",
        "review_author": "",
        "review_as_of_date": "",
        "source_name": "",
        "source_reference": "",
        "notes": build_seed_notes(master_row, identity_row),
    }


def seed_sort_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        canonicalize_ticker(row.get("ticker", "")),
        canonical_isin(row.get("isin", "")),
        str(row.get("company_name", "") or "").strip(),
    )


def build_profile_seed_rows(
    master_rows: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    identity_map_rows: list[dict[str, str]],
    *,
    review_source_name: str,
    identity_map_source_name: str,
    master_source_name: str,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    exportable_review_identity_rows = build_identity_map_rows(review_rows)
    review_index = build_unique_identity_index(exportable_review_identity_rows, review_source_name)
    identity_index = build_unique_identity_index(identity_map_rows, identity_map_source_name)
    master_index = build_master_isin_index(master_rows, master_source_name)

    counters: Counter[str] = Counter()
    counters["review_rows_total"] = len(review_rows)
    counters["exportable_review_rows_total"] = len(exportable_review_identity_rows)
    counters["identity_map_rows_total"] = len(identity_map_rows)

    seed_rows: list[dict[str, str]] = []
    for isin in sorted(review_index):
        review_identity_row = review_index[isin]
        identity_map_row = identity_index.get(isin)
        if identity_map_row is None:
            counters["skipped_no_identity_map_total"] += 1
            continue

        validate_supported_identity_row(review_identity_row, review_source_name)
        validate_supported_identity_row(identity_map_row, identity_map_source_name)
        assert_consistent_review_and_identity_map(review_identity_row, identity_map_row, isin)
        counters["matched_review_identity_rows_total"] += 1

        matched_index = master_index.get(isin)
        if matched_index is None:
            counters["skipped_no_master_match_total"] += 1
            continue

        master_row = master_rows[matched_index]
        assert_consistent_identity_applied_master(master_row, identity_map_row, isin)
        seed_rows.append(profile_seed_row(master_row, identity_map_row))
        counters["seeded_rows_total"] += 1

    seed_rows.sort(key=seed_sort_key)
    return seed_rows, dict(counters)


def build_summary_row(master_rows: list[dict[str, str]], counters: dict[str, int]) -> list[dict[str, str]]:
    return [
        {
            "identity_applied_master_rows_total": str(len(master_rows)),
            "review_rows_total": str(counters.get("review_rows_total", 0)),
            "exportable_review_rows_total": str(counters.get("exportable_review_rows_total", 0)),
            "identity_map_rows_total": str(counters.get("identity_map_rows_total", 0)),
            "matched_review_identity_rows_total": str(counters.get("matched_review_identity_rows_total", 0)),
            "seeded_rows_total": str(counters.get("seeded_rows_total", 0)),
            "skipped_no_identity_map_total": str(counters.get("skipped_no_identity_map_total", 0)),
            "skipped_no_master_match_total": str(counters.get("skipped_no_master_match_total", 0)),
            "notes": (
                "Profile seed only. proposed_company_type_profile, profile_reason, review_status, review_author, "
                "review_as_of_date, source_name and source_reference remain intentionally blank for manual review."
            ),
        }
    ]


def run_personal_sec_profile_seed(
    *,
    identity_applied_master_input: str = DEFAULT_IDENTITY_APPLIED_MASTER_OUTPUT,
    review_input: str = DEFAULT_REVIEW_OUTPUT,
    identity_map_input: str = DEFAULT_SEC_IDENTITY_MAP_INPUT,
    seed_output: str = DEFAULT_PROFILE_SEED_OUTPUT,
    summary_output: str = DEFAULT_PROFILE_SEED_SUMMARY_OUTPUT,
) -> dict[str, Path]:
    master_rows = read_csv_rows(identity_applied_master_input)
    validate_personal_fundamentals_master(master_rows, f"identity-applied personal fundamentals master ({identity_applied_master_input})")
    review_rows = load_review_rows(review_input)
    identity_fieldnames, raw_identity_rows = read_csv_rows_with_header(identity_map_input)
    require_header_columns(identity_fieldnames, IDENTITY_MAP_FIELDS, f"private SEC identity-map ({identity_map_input})")
    identity_map_rows = validate_identity_map_rows(raw_identity_rows, f"private SEC identity-map ({identity_map_input})")

    seed_rows, counters = build_profile_seed_rows(
        master_rows,
        review_rows,
        identity_map_rows,
        review_source_name=f"SEC scope review ({review_input})",
        identity_map_source_name=f"private SEC identity-map ({identity_map_input})",
        master_source_name=f"identity-applied personal fundamentals master ({identity_applied_master_input})",
    )
    return {
        "profile_review_seed": write_csv_rows(seed_output, PROFILE_REVIEW_INPUT_FIELDS, seed_rows),
        "profile_seed_summary": write_csv_rows(summary_output, PROFILE_SEED_SUMMARY_FIELDS, build_summary_row(master_rows, counters)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a manual profile-review seed from reviewed/exported SEC US STOCK identities on top of the identity-applied master."
    )
    parser.add_argument(
        "--identity-applied-master-input",
        default=DEFAULT_IDENTITY_APPLIED_MASTER_OUTPUT,
        help="Evidence+identity-applied personal fundamentals master CSV.",
    )
    parser.add_argument("--review-input", default=DEFAULT_REVIEW_OUTPUT, help="Manual SEC scope review CSV.")
    parser.add_argument("--identity-map-input", default=DEFAULT_SEC_IDENTITY_MAP_INPUT, help="Reviewed private SEC identity-map CSV.")
    parser.add_argument("--seed-output", default=DEFAULT_PROFILE_SEED_OUTPUT, help="Processed manual profile-review seed output.")
    parser.add_argument("--summary-output", default=DEFAULT_PROFILE_SEED_SUMMARY_OUTPUT, help="Profile seed summary output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_personal_sec_profile_seed(
        identity_applied_master_input=args.identity_applied_master_input,
        review_input=args.review_input,
        identity_map_input=args.identity_map_input,
        seed_output=args.seed_output,
        summary_output=args.summary_output,
    )


if __name__ == "__main__":
    main()
