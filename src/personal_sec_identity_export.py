from __future__ import annotations

import argparse
from pathlib import Path

from src.common import canonicalize_ticker, safe_upper, write_csv_rows
from src.external_sec_companyfacts_fetch import (
    DEFAULT_SEC_IDENTITY_MAP_INPUT,
    IDENTITY_MAP_FIELDS,
    SUPPORTED_ASSET_TYPES,
    SUPPORTED_COUNTRIES,
    canonical_cik,
    canonical_isin,
    validate_identity_map_rows,
)
from src.personal_sec_scope_prepare import DEFAULT_REVIEW_OUTPUT, REVIEW_STATUS_APPROVE, load_review_rows, parse_enabled


def is_exportable_review_row(row: dict[str, str]) -> bool:
    return (
        safe_upper(row.get("review_status", "")) == REVIEW_STATUS_APPROVE
        and safe_upper(row.get("reviewed_asset_type_scope", "")) in SUPPORTED_ASSET_TYPES
        and safe_upper(row.get("reviewed_country", "")) in SUPPORTED_COUNTRIES
        and bool(canonicalize_ticker(row.get("reviewed_canonical_ticker", "")))
        and bool(canonical_cik(row.get("reviewed_cik", "")))
        and parse_enabled(row.get("reviewed_enabled", ""))
    )


def identity_row_from_review(row: dict[str, str]) -> dict[str, str]:
    notes = str(row.get("review_notes", "") or "").strip()
    return {
        "ticker": canonicalize_ticker(row.get("reviewed_canonical_ticker", "")),
        "isin": canonical_isin(row.get("original_isin", "")),
        "company_name": str(row.get("company_name", "") or "").strip(),
        "cik": canonical_cik(row.get("reviewed_cik", "")),
        "sec_entity_name": str(row.get("reviewed_sec_entity_name", "") or "").strip(),
        "asset_type": safe_upper(row.get("reviewed_asset_type_scope", "")),
        "country": safe_upper(row.get("reviewed_country", "")),
        "enabled": "true",
        "notes": notes or "Reviewed SEC identity export from personal_sec_scope_review.",
    }


def build_identity_map_rows(review_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    raw_rows = [identity_row_from_review(row) for row in review_rows if is_exportable_review_row(row)]
    return validate_identity_map_rows(raw_rows, "SEC scope reviewed identity export")


def run_personal_sec_identity_export(
    *,
    review_input: str = DEFAULT_REVIEW_OUTPUT,
    output: str = DEFAULT_SEC_IDENTITY_MAP_INPUT,
    dry_run: bool = False,
) -> dict[str, Path | int]:
    review_rows = load_review_rows(review_input)
    identity_rows = build_identity_map_rows(review_rows)
    result: dict[str, Path | int] = {
        "review_rows_total": len(review_rows),
        "exportable_identity_rows_total": len(identity_rows),
    }
    if not dry_run:
        result["identity_map"] = write_csv_rows(output, IDENTITY_MAP_FIELDS, identity_rows)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export explicitly reviewed SEC scope rows into the private SEC identity-map contract.")
    parser.add_argument("--review-input", default=DEFAULT_REVIEW_OUTPUT, help="Manual SEC scope review CSV.")
    parser.add_argument("--output", default=DEFAULT_SEC_IDENTITY_MAP_INPUT, help="Private SEC identity map output.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and count exportable rows without writing the identity map.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_personal_sec_identity_export(review_input=args.review_input, output=args.output, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
