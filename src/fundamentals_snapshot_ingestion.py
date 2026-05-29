from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, read_csv_rows, resolve_repo_path, write_csv_rows
from src.fundamentals_evidence_engine import EVIDENCE_INPUT_FIELDS
from src.fundamentals_master import CORE_KPI_FIELDS, DEFAULT_PERSONAL_MASTER_PATH, validate_personal_fundamentals_master

DEFAULT_SNAPSHOT_INPUT_PATH = "data/raw/private/fundamentals/personal_fundamentals_snapshot.csv"
DEFAULT_SNAPSHOT_TEMPLATE_PATH = "data/raw/personal_fundamentals_snapshot_template.csv"
DEFAULT_NORMALIZED_OUTPUT = "data/processed/personal_fundamentals_snapshot_normalized.csv"
DEFAULT_UNMATCHED_OUTPUT = "data/processed/personal_fundamentals_snapshot_unmatched.csv"
DEFAULT_EVIDENCE_STAGING_OUTPUT = "data/processed/personal_fundamentals_snapshot_evidence_staging.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_fundamentals_snapshot_summary.csv"

SNAPSHOT_REQUIRED_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "source_name",
    "source_as_of_date",
    "fiscal_year",
    "currency",
]

SNAPSHOT_OPTIONAL_METADATA_FIELDS = [
    "source_reference",
    "market_price_date",
    "notes",
]

SNAPSHOT_INPUT_FIELDS = [*SNAPSHOT_REQUIRED_FIELDS, *SNAPSHOT_OPTIONAL_METADATA_FIELDS, *CORE_KPI_FIELDS]

NORMALIZED_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "snapshot_company_name",
    "source_name",
    "source_reference",
    "source_as_of_date",
    "fiscal_year",
    "currency",
    "market_price_date",
    "match_method",
    "notes",
    *CORE_KPI_FIELDS,
]

UNMATCHED_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "source_name",
    "source_reference",
    "source_as_of_date",
    "fiscal_year",
    "currency",
    "market_price_date",
    "unmatched_reason",
    "notes",
    *CORE_KPI_FIELDS,
]

SUMMARY_FIELDS = [
    "snapshot_rows_total",
    "matched_rows",
    "unmatched_rows",
    "duplicate_rows_collapsed",
    "evidence_rows_generated",
    "kpis_with_values_total",
    "notes",
]

PERCENT_KPIS = {
    "revenue_cagr_5y",
    "eps_cagr_5y",
    "fcf_per_share_cagr_5y",
    "roic",
    "roce",
    "gross_margin",
    "operating_margin",
    "fcf_margin",
    "dividend_yield_current_pct",
    "dividend_yield_hist_pct",
    "dividend_cagr_5y",
    "payout_ratio_eps",
    "payout_ratio_fcf",
    "share_count_cagr_5y",
    "buyback_yield",
    "fcf_yield_current_pct",
    "fcf_yield_hist_pct",
    "normalized_fcf_yield_pct",
    "target_fcf_yield_pct",
    "drawdown_from_high_pct",
    "expected_return_pct",
}

MULTIPLE_KPIS = {
    "net_debt_to_ebitda",
    "interest_coverage",
    "pe_current",
    "pe_hist",
    "ev_ebit_current",
    "ev_ebit_hist",
}

COUNT_KPIS = {"dividend_streak_years"}


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


def parse_iso_date_text(value: Any, field: str, source_name: str, row_number: int, *, required: bool) -> str:
    text = str(value or "").strip()
    if not text:
        if required:
            raise ValueError(f"{source_name} row {row_number} has blank required field(s): {field}")
        return ""
    try:
        from datetime import date

        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{source_name} row {row_number} has invalid {field}: {text!r}; expected YYYY-MM-DD") from exc
    return text


def parse_numeric_text(value: Any, field: str, source_name: str, row_number: int) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        from src.fundamentals_master import parse_float_strict

        parse_float_strict(text)
    except ValueError as exc:
        raise ValueError(f"{source_name} row {row_number} has non-numeric {field}: {value!r}") from exc
    return text


def is_blank_snapshot_row(row: dict[str, str]) -> bool:
    return all(not str(value or "").strip() for value in row.values())


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
                f"personal fundamentals master has duplicate {field} value(s); snapshot ingestion matching would be ambiguous: {', '.join(duplicates)}"
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


def canonical_snapshot_row(
    row: dict[str, str],
    source_name: str,
    row_number: int,
) -> dict[str, str]:
    company_name = require_nonblank_value(row, "company_name", source_name, row_number)
    source_name_value = require_nonblank_value(row, "source_name", source_name, row_number)
    source_as_of_date = parse_iso_date_text(row.get("source_as_of_date", ""), "source_as_of_date", source_name, row_number, required=True)
    fiscal_year = require_nonblank_value(row, "fiscal_year", source_name, row_number)
    try:
        int(fiscal_year)
    except ValueError as exc:
        raise ValueError(f"{source_name} row {row_number} has invalid fiscal_year: {fiscal_year!r}") from exc
    currency = require_nonblank_value(row, "currency", source_name, row_number).upper()
    market_price_date = parse_iso_date_text(row.get("market_price_date", ""), "market_price_date", source_name, row_number, required=False)
    ticker = canonicalize_ticker(row.get("ticker", ""))
    isin = str(row.get("isin", "") or "").strip().upper()
    if not ticker and not isin:
        raise ValueError(f"{source_name} row {row_number} requires ticker or isin for exact Personal-Master matching")

    canonical_row = {field: "" for field in SNAPSHOT_INPUT_FIELDS}
    canonical_row.update(
        {
            "ticker": ticker,
            "isin": isin,
            "company_name": company_name,
            "source_name": source_name_value,
            "source_as_of_date": source_as_of_date,
            "fiscal_year": fiscal_year,
            "currency": currency,
            "source_reference": str(row.get("source_reference", "") or "").strip() or source_name_value,
            "market_price_date": market_price_date,
            "notes": str(row.get("notes", "") or "").strip(),
        }
    )
    for kpi_name in CORE_KPI_FIELDS:
        canonical_row[kpi_name] = parse_numeric_text(row.get(kpi_name, ""), kpi_name, source_name, row_number)
    return canonical_row


def snapshot_match_method(ticker: str, isin: str) -> str:
    if ticker and isin:
        return "TICKER+ISIN"
    if isin:
        return "ISIN"
    return "TICKER"


def match_snapshot_to_master(
    row: dict[str, str],
    master_index: dict[str, dict[str, dict[str, str]]],
    source_name: str,
    row_number: int,
) -> tuple[dict[str, str] | None, str, str]:
    ticker = canonicalize_ticker(row.get("ticker", ""))
    isin = str(row.get("isin", "") or "").strip().upper()
    ticker_match = master_index["ticker"].get(ticker) if ticker else None
    isin_match = master_index["isin"].get(isin) if isin else None

    if ticker and isin:
        if ticker_match is None and isin_match is None:
            return None, "", "No exact ticker/isin match in personal fundamentals master."
        if ticker_match is None or isin_match is None:
            raise ValueError(
                f"{source_name} row {row_number} requires ticker and isin to match the same personal fundamentals master row: "
                f"ticker={ticker}, isin={isin}"
            )
        if id(ticker_match) != id(isin_match):
            raise ValueError(
                f"{source_name} row {row_number} has conflicting ticker/isin matches in personal fundamentals master: "
                f"ticker={ticker}, isin={isin}"
            )
        return ticker_match, "TICKER+ISIN", ""

    matched = isin_match or ticker_match
    if matched is None:
        return None, "", "No exact ticker/isin match in personal fundamentals master."
    return matched, snapshot_match_method(ticker, isin), ""


def normalized_row(
    snapshot_row: dict[str, str],
    master_row: dict[str, str],
    *,
    match_method: str,
) -> dict[str, str]:
    ticker, isin = master_identifier_key(master_row)
    row = {field: "" for field in NORMALIZED_FIELDS}
    row.update(
        {
            "ticker": ticker,
            "isin": isin,
            "company_name": str(master_row.get("company_name", "") or "").strip(),
            "snapshot_company_name": snapshot_row["company_name"],
            "source_name": snapshot_row["source_name"],
            "source_reference": snapshot_row["source_reference"],
            "source_as_of_date": snapshot_row["source_as_of_date"],
            "fiscal_year": snapshot_row["fiscal_year"],
            "currency": snapshot_row["currency"],
            "market_price_date": snapshot_row["market_price_date"],
            "match_method": match_method,
            "notes": snapshot_row["notes"],
        }
    )
    for kpi_name in CORE_KPI_FIELDS:
        row[kpi_name] = snapshot_row[kpi_name]
    return row


def unmatched_row(snapshot_row: dict[str, str], reason: str) -> dict[str, str]:
    row = {field: "" for field in UNMATCHED_FIELDS}
    row.update(
        {
            "ticker": snapshot_row["ticker"],
            "isin": snapshot_row["isin"],
            "company_name": snapshot_row["company_name"],
            "source_name": snapshot_row["source_name"],
            "source_reference": snapshot_row["source_reference"],
            "source_as_of_date": snapshot_row["source_as_of_date"],
            "fiscal_year": snapshot_row["fiscal_year"],
            "currency": snapshot_row["currency"],
            "market_price_date": snapshot_row["market_price_date"],
            "unmatched_reason": reason,
            "notes": snapshot_row["notes"],
        }
    )
    for kpi_name in CORE_KPI_FIELDS:
        row[kpi_name] = snapshot_row[kpi_name]
    return row


def row_content_signature(row: dict[str, str], fields: list[str]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "") or "").strip() for field in fields)


def dedupe_rows_by_identity(
    rows: list[dict[str, str]],
    *,
    identity_fields: list[str],
    content_fields: list[str],
    source_name: str,
    conflict_label: str,
) -> tuple[list[dict[str, str]], int]:
    deduped: list[dict[str, str]] = []
    seen: dict[tuple[str, ...], tuple[str, ...]] = {}
    duplicates_collapsed = 0
    for row in rows:
        identity = row_content_signature(row, identity_fields)
        content = row_content_signature(row, content_fields)
        existing = seen.get(identity)
        if existing is None:
            seen[identity] = content
            deduped.append(row)
            continue
        if existing != content:
            identity_text = ", ".join(f"{field}={value or '<blank>'}" for field, value in zip(identity_fields, identity, strict=True))
            raise ValueError(f"{source_name} has conflicting duplicate {conflict_label} row(s): {identity_text}")
        duplicates_collapsed += 1
    return deduped, duplicates_collapsed


def sort_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        canonicalize_ticker(row.get("ticker", "")),
        str(row.get("isin", "") or "").strip().upper(),
        str(row.get("source_as_of_date", "") or "").strip(),
        str(row.get("source_name", "") or "").strip(),
        str(row.get("source_reference", "") or "").strip(),
    )


def evidence_unit_for_kpi(kpi_name: str) -> str:
    if kpi_name in PERCENT_KPIS:
        return "percent"
    if kpi_name in MULTIPLE_KPIS:
        return "multiple"
    if kpi_name in COUNT_KPIS:
        return "years"
    return ""


def build_evidence_staging_rows(normalized_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for normalized in normalized_rows:
        for kpi_name in CORE_KPI_FIELDS:
            reported_value = str(normalized.get(kpi_name, "") or "").strip()
            if not reported_value:
                continue
            row = {field: "" for field in EVIDENCE_INPUT_FIELDS}
            row.update(
                {
                    "ticker": normalized["ticker"],
                    "isin": normalized["isin"],
                    "company_name": normalized["company_name"],
                    "kpi_name": kpi_name,
                    "source_type": "SNAPSHOT_IMPORT",
                    "source_name": normalized["source_name"],
                    "source_reference": normalized["source_reference"],
                    "source_as_of_date": normalized["source_as_of_date"],
                    "fiscal_year": normalized["fiscal_year"],
                    "verification_status": "UNVERIFIED",
                    "data_quality_flag": "REVIEW",
                    "notes": normalized["notes"] or "Local fundamentals snapshot import staged for manual evidence review.",
                    "reported_value": reported_value,
                    "reported_unit": evidence_unit_for_kpi(kpi_name),
                    "currency": normalized["currency"],
                }
            )
            rows.append(row)
    return rows


def build_summary_rows(
    *,
    snapshot_rows_total: int,
    matched_rows: int,
    unmatched_rows: int,
    duplicate_rows_collapsed: int,
    evidence_rows_generated: int,
    kpis_with_values_total: int,
) -> list[dict[str, str]]:
    return [
        {
            "snapshot_rows_total": str(snapshot_rows_total),
            "matched_rows": str(matched_rows),
            "unmatched_rows": str(unmatched_rows),
            "duplicate_rows_collapsed": str(duplicate_rows_collapsed),
            "evidence_rows_generated": str(evidence_rows_generated),
            "kpis_with_values_total": str(kpis_with_values_total),
            "notes": "Local fundamentals snapshot staged for later explicit evidence review; no raw master or evidence input was mutated.",
        }
    ]


def write_snapshot_template(output_path: str = DEFAULT_SNAPSHOT_TEMPLATE_PATH) -> Path:
    return write_csv_rows(output_path, SNAPSHOT_INPUT_FIELDS, [])


def run_fundamentals_snapshot_ingestion(
    *,
    fundamentals_master_path: str = DEFAULT_PERSONAL_MASTER_PATH,
    snapshot_input_path: str = DEFAULT_SNAPSHOT_INPUT_PATH,
    normalized_output: str = DEFAULT_NORMALIZED_OUTPUT,
    unmatched_output: str = DEFAULT_UNMATCHED_OUTPUT,
    evidence_staging_output: str = DEFAULT_EVIDENCE_STAGING_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    template_output: str | None = DEFAULT_SNAPSHOT_TEMPLATE_PATH,
) -> dict[str, Path]:
    master_rows = read_csv_rows(fundamentals_master_path)
    validate_personal_fundamentals_master(master_rows, f"personal fundamentals master ({fundamentals_master_path})")
    fieldnames, raw_rows = read_csv_rows_with_header(snapshot_input_path)
    require_header_columns(fieldnames, SNAPSHOT_REQUIRED_FIELDS, f"fundamentals snapshot input ({snapshot_input_path})")
    master_index = build_master_identifier_index(master_rows)

    canonical_rows: list[dict[str, str]] = []
    for row_number, row in enumerate(raw_rows, start=2):
        if is_blank_snapshot_row(row):
            continue
        canonical_rows.append(
            canonical_snapshot_row(row, f"fundamentals snapshot input ({snapshot_input_path})", row_number)
        )

    snapshot_rows_total = len(canonical_rows)
    deduped_snapshot_rows, duplicate_rows_collapsed = dedupe_rows_by_identity(
        canonical_rows,
        identity_fields=["ticker", "isin", "company_name"],
        content_fields=SNAPSHOT_INPUT_FIELDS,
        source_name=f"fundamentals snapshot input ({snapshot_input_path})",
        conflict_label="snapshot identity",
    )

    normalized_rows: list[dict[str, str]] = []
    unmatched_rows: list[dict[str, str]] = []
    for row_number, snapshot_row in enumerate(deduped_snapshot_rows, start=2):
        matched_master_row, match_method, unmatched_reason = match_snapshot_to_master(
            snapshot_row,
            master_index,
            f"fundamentals snapshot input ({snapshot_input_path})",
            row_number,
        )
        if matched_master_row is None:
            unmatched_rows.append(unmatched_row(snapshot_row, unmatched_reason))
            continue
        normalized_rows.append(normalized_row(snapshot_row, matched_master_row, match_method=match_method))

    normalized_rows, normalized_duplicates_collapsed = dedupe_rows_by_identity(
        sorted(normalized_rows, key=sort_key),
        identity_fields=["ticker", "isin"],
        content_fields=NORMALIZED_FIELDS,
        source_name=f"fundamentals snapshot input ({snapshot_input_path})",
        conflict_label="matched snapshot identity",
    )
    unmatched_rows, unmatched_duplicates_collapsed = dedupe_rows_by_identity(
        sorted(unmatched_rows, key=sort_key),
        identity_fields=["ticker", "isin", "company_name"],
        content_fields=UNMATCHED_FIELDS,
        source_name=f"fundamentals snapshot input ({snapshot_input_path})",
        conflict_label="unmatched snapshot identity",
    )

    duplicate_rows_collapsed += normalized_duplicates_collapsed + unmatched_duplicates_collapsed
    normalized_rows = sorted(normalized_rows, key=sort_key)
    unmatched_rows = sorted(unmatched_rows, key=sort_key)
    evidence_rows = build_evidence_staging_rows(normalized_rows)
    kpis_with_values_total = len(evidence_rows)

    outputs: dict[str, Path] = {}
    outputs["snapshot_normalized"] = write_csv_rows(normalized_output, NORMALIZED_FIELDS, normalized_rows)
    outputs["snapshot_unmatched"] = write_csv_rows(unmatched_output, UNMATCHED_FIELDS, unmatched_rows)
    outputs["snapshot_evidence_staging"] = write_csv_rows(evidence_staging_output, EVIDENCE_INPUT_FIELDS, evidence_rows)
    outputs["snapshot_summary"] = write_csv_rows(
        summary_output,
        SUMMARY_FIELDS,
        build_summary_rows(
            snapshot_rows_total=snapshot_rows_total,
            matched_rows=len(normalized_rows),
            unmatched_rows=len(unmatched_rows),
            duplicate_rows_collapsed=duplicate_rows_collapsed,
            evidence_rows_generated=len(evidence_rows),
            kpis_with_values_total=kpis_with_values_total,
        ),
    )
    if template_output:
        outputs["snapshot_template"] = write_snapshot_template(template_output)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest a local external fundamentals snapshot and stage evidence rows.")
    parser.add_argument("--fundamentals-master", default=DEFAULT_PERSONAL_MASTER_PATH, help="Personal fundamentals master CSV.")
    parser.add_argument("--snapshot-input", default=DEFAULT_SNAPSHOT_INPUT_PATH, help="Local external fundamentals snapshot CSV.")
    parser.add_argument("--normalized-output", default=DEFAULT_NORMALIZED_OUTPUT, help="Normalized matched snapshot output.")
    parser.add_argument("--unmatched-output", default=DEFAULT_UNMATCHED_OUTPUT, help="Unmatched snapshot output.")
    parser.add_argument("--evidence-staging-output", default=DEFAULT_EVIDENCE_STAGING_OUTPUT, help="Evidence staging CSV output.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT, help="Snapshot ingest summary output.")
    parser.add_argument("--template-output", default=DEFAULT_SNAPSHOT_TEMPLATE_PATH, help="Snapshot input template output.")
    parser.add_argument("--template-only", action="store_true", help="Only write the snapshot template; do not require master or snapshot input.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.template_only:
        write_snapshot_template(args.template_output)
        return
    run_fundamentals_snapshot_ingestion(
        fundamentals_master_path=args.fundamentals_master,
        snapshot_input_path=args.snapshot_input,
        normalized_output=args.normalized_output,
        unmatched_output=args.unmatched_output,
        evidence_staging_output=args.evidence_staging_output,
        summary_output=args.summary_output,
        template_output=args.template_output,
    )


if __name__ == "__main__":
    main()
