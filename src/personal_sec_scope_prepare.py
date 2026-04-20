from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from src.common import canonicalize_ticker, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows
from src.external_sec_companyfacts_fetch import SUPPORTED_ASSET_TYPES, SUPPORTED_COUNTRIES, canonical_cik, canonical_isin, require_header_columns
from src.fundamentals_master import DEFAULT_PERSONAL_MASTER_PATH, PERSONAL_MASTER_FIELDS, validate_personal_fundamentals_master

DEFAULT_REVIEW_OUTPUT = "data/processed/personal_sec_scope_review.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_sec_scope_summary.csv"
DEFAULT_BLOCKERS_OUTPUT = "data/processed/personal_sec_scope_blockers.csv"

ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

REVIEW_STATUS_BLANK = "BLANK"
REVIEW_STATUS_APPROVE = "REVIEWED_APPROVE"
REVIEW_STATUS_REJECT = "REVIEWED_REJECT"
VALID_REVIEW_STATUSES = {REVIEW_STATUS_BLANK, REVIEW_STATUS_APPROVE, REVIEW_STATUS_REJECT}

AUDIT_FIELDS = [
    "master_row_number",
    "original_ticker",
    "original_isin",
    "company_name",
    "original_country",
    "original_asset_type",
    "ticker_equals_isin_flag",
    "ticker_looks_like_isin_flag",
    "sec_scope_supported_now_flag",
    "sec_scope_blocker_reason",
    "candidate_for_us_stock_review_flag",
]

REVIEW_FIELDS = [
    *AUDIT_FIELDS,
    "reviewed_asset_type_scope",
    "reviewed_country",
    "reviewed_canonical_ticker",
    "reviewed_cik",
    "reviewed_enabled",
    "reviewed_sec_entity_name",
    "review_status",
    "review_notes",
]

SUMMARY_FIELDS = [
    "master_rows_total",
    "stock_rows_total",
    "sec_scope_supported_now_total",
    "ticker_equals_isin_total",
    "ticker_looks_like_isin_total",
    "country_unknown_total",
    "reviewed_us_stock_scope_total",
    "reviewed_complete_sec_identity_total",
    "exportable_identity_rows_total",
    "notes",
]

BLOCKER_FIELDS = AUDIT_FIELDS


def read_csv_rows_with_header(path_value: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def looks_like_isin(value: str) -> bool:
    return bool(ISIN_RE.match(str(value or "").strip().upper()))


def country_unknown(value: str) -> bool:
    return safe_upper(value) in {"", "UNKNOWN"}


def sec_scope_blockers(row: dict[str, str]) -> list[str]:
    ticker = canonicalize_ticker(row.get("ticker", ""))
    isin = canonical_isin(row.get("isin", ""))
    asset_type = safe_upper(row.get("asset_type", ""))
    country = safe_upper(row.get("country", ""))
    blockers: list[str] = []
    if asset_type not in SUPPORTED_ASSET_TYPES:
        blockers.append("UNSUPPORTED_ASSET_TYPE")
    if country_unknown(country):
        blockers.append("COUNTRY_UNKNOWN")
    elif country not in SUPPORTED_COUNTRIES:
        blockers.append("COUNTRY_UNSUPPORTED")
    if not ticker:
        blockers.append("TICKER_BLANK")
    if ticker and isin and ticker == isin:
        blockers.append("TICKER_EQUALS_ISIN")
    if ticker and looks_like_isin(ticker):
        blockers.append("TICKER_LOOKS_LIKE_ISIN")
    if not asset_type or not country or not ticker:
        blockers.append("IDENTITY_INCOMPLETE_FOR_SEC_SCOPE")
    return blockers


def build_audit_rows(master_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row_number, row in enumerate(master_rows, start=2):
        ticker = canonicalize_ticker(row.get("ticker", ""))
        isin = canonical_isin(row.get("isin", ""))
        asset_type = safe_upper(row.get("asset_type", ""))
        country = safe_upper(row.get("country", ""))
        blockers = sec_scope_blockers(row)
        supported_now = not blockers
        rows.append(
            {
                "master_row_number": str(row_number),
                "original_ticker": ticker,
                "original_isin": isin,
                "company_name": str(row.get("company_name", "") or "").strip(),
                "original_country": country,
                "original_asset_type": asset_type,
                "ticker_equals_isin_flag": bool_text(bool(ticker and isin and ticker == isin)),
                "ticker_looks_like_isin_flag": bool_text(bool(ticker and looks_like_isin(ticker))),
                "sec_scope_supported_now_flag": bool_text(supported_now),
                "sec_scope_blocker_reason": ";".join(blockers),
                "candidate_for_us_stock_review_flag": bool_text(asset_type in SUPPORTED_ASSET_TYPES),
            }
        )
    return rows


def empty_review_fields() -> dict[str, str]:
    return {
        "reviewed_asset_type_scope": "",
        "reviewed_country": "",
        "reviewed_canonical_ticker": "",
        "reviewed_cik": "",
        "reviewed_enabled": "",
        "reviewed_sec_entity_name": "",
        "review_status": REVIEW_STATUS_BLANK,
        "review_notes": "",
    }


def build_review_rows(audit_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [{**row, **empty_review_fields()} for row in audit_rows]


def load_review_rows(path_value: str | Path | None) -> list[dict[str, str]]:
    if not path_value:
        return []
    path = resolve_repo_path(path_value)
    if not path.exists():
        return []
    fieldnames, rows = read_csv_rows_with_header(path)
    require_header_columns(fieldnames, REVIEW_FIELDS, f"SEC scope review ({path_value})")
    loaded: list[dict[str, str]] = []
    for row_number, row in enumerate(rows, start=2):
        if not any(str(value or "").strip() for value in row.values()):
            continue
        status = safe_upper(row.get("review_status", "")) or REVIEW_STATUS_BLANK
        if status not in VALID_REVIEW_STATUSES:
            raise ValueError(
                f"SEC scope review ({path_value}) row {row_number} has invalid review_status={status!r}; "
                f"allowed: {', '.join(sorted(VALID_REVIEW_STATUSES))}"
            )
        normalized = {field: str(row.get(field, "") or "").strip() for field in REVIEW_FIELDS}
        normalized["review_status"] = status
        loaded.append(normalized)
    return sorted(loaded, key=lambda row: int(row.get("master_row_number") or "0"))


def review_row_has_us_stock_scope(row: dict[str, str]) -> bool:
    return (
        safe_upper(row.get("review_status", "")) == REVIEW_STATUS_APPROVE
        and safe_upper(row.get("reviewed_asset_type_scope", "")) in SUPPORTED_ASSET_TYPES
        and safe_upper(row.get("reviewed_country", "")) in SUPPORTED_COUNTRIES
    )


def review_row_has_complete_sec_identity(row: dict[str, str]) -> bool:
    return (
        review_row_has_us_stock_scope(row)
        and bool(canonicalize_ticker(row.get("reviewed_canonical_ticker", "")))
        and bool(canonical_cik(row.get("reviewed_cik", "")))
    )


def parse_enabled(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def review_row_is_exportable(row: dict[str, str]) -> bool:
    return review_row_has_complete_sec_identity(row) and parse_enabled(row.get("reviewed_enabled", ""))


def build_summary_row(audit_rows: list[dict[str, str]], review_rows: list[dict[str, str]]) -> dict[str, str]:
    stock_rows = [row for row in audit_rows if row["original_asset_type"] in SUPPORTED_ASSET_TYPES]
    return {
        "master_rows_total": str(len(audit_rows)),
        "stock_rows_total": str(len(stock_rows)),
        "sec_scope_supported_now_total": str(sum(row["sec_scope_supported_now_flag"] == "true" for row in audit_rows)),
        "ticker_equals_isin_total": str(sum(row["ticker_equals_isin_flag"] == "true" for row in audit_rows)),
        "ticker_looks_like_isin_total": str(sum(row["ticker_looks_like_isin_flag"] == "true" for row in audit_rows)),
        "country_unknown_total": str(sum("COUNTRY_UNKNOWN" in row["sec_scope_blocker_reason"].split(";") for row in audit_rows)),
        "reviewed_us_stock_scope_total": str(sum(review_row_has_us_stock_scope(row) for row in review_rows)),
        "reviewed_complete_sec_identity_total": str(sum(review_row_has_complete_sec_identity(row) for row in review_rows)),
        "exportable_identity_rows_total": str(sum(review_row_is_exportable(row) for row in review_rows)),
        "notes": "Prepare/audit only; no SEC network call and no private identity map write.",
    }


def build_blocker_rows(audit_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in audit_rows if row["sec_scope_blocker_reason"]]


def run_personal_sec_scope_prepare(
    *,
    master_input: str = DEFAULT_PERSONAL_MASTER_PATH,
    review_output: str = DEFAULT_REVIEW_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    blockers_output: str = DEFAULT_BLOCKERS_OUTPUT,
    review_input: str | None = None,
    review_template_only: bool = False,
    summary_only: bool = False,
) -> dict[str, Path]:
    master_rows = [row for row in read_csv_rows(master_input) if any(str(value or "").strip() for value in row.values())]
    validate_personal_fundamentals_master(master_rows, f"personal fundamentals master ({master_input})")
    audit_rows = build_audit_rows(master_rows)
    outputs: dict[str, Path] = {}

    if not summary_only:
        outputs["sec_scope_review"] = write_csv_rows(review_output, REVIEW_FIELDS, build_review_rows(audit_rows))
        if review_template_only:
            return outputs

    effective_review_input = review_input or review_output
    review_rows = load_review_rows(effective_review_input)
    outputs["sec_scope_summary"] = write_csv_rows(summary_output, SUMMARY_FIELDS, [build_summary_row(audit_rows, review_rows)])
    outputs["sec_scope_blockers"] = write_csv_rows(blockers_output, BLOCKER_FIELDS, build_blocker_rows(audit_rows))
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Personal-Master rows for the reviewed SEC identity-map preparation workflow.")
    parser.add_argument("--master-input", default=DEFAULT_PERSONAL_MASTER_PATH, help="Personal fundamentals master CSV.")
    parser.add_argument("--review-output", default=DEFAULT_REVIEW_OUTPUT, help="Manual SEC scope review output.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT, help="SEC scope preparation summary output.")
    parser.add_argument("--blockers-output", default=DEFAULT_BLOCKERS_OUTPUT, help="SEC scope blocker output.")
    parser.add_argument("--review-input", default="", help="Existing reviewed SEC scope file for summary counts.")
    parser.add_argument("--review-template-only", action="store_true", help="Only write the manual SEC scope review template.")
    parser.add_argument("--summary-only", action="store_true", help="Write summary/blockers only; do not overwrite the review file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_personal_sec_scope_prepare(
        master_input=args.master_input,
        review_output=args.review_output,
        summary_output=args.summary_output,
        blockers_output=args.blockers_output,
        review_input=args.review_input or None,
        review_template_only=args.review_template_only,
        summary_only=args.summary_only,
    )


if __name__ == "__main__":
    main()
