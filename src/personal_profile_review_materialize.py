from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, resolve_repo_path, safe_upper, write_csv_rows
from src.fundamentals_master import DEFAULT_PERSONAL_MASTER_PATH, VALID_COMPANY_TYPE_PROFILES
from src.fundamentals_profile_engine import PROFILE_REVIEW_INPUT_FIELDS, require_header_columns
from src.personal_sec_profile_seed import DEFAULT_PROFILE_SEED_OUTPUT

DEFAULT_REVIEW_OUTPUT = "data/raw/personal_fundamentals_profile_review.csv"
DEFAULT_EXACT_MAP_INPUT = "data/raw/private/fundamentals/personal_profile_review_exact_map.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_profile_review_materialization_report.md"

EXACT_MAP_FIELDS = [
    "ticker",
    "isin",
    "company_type_profile",
    "profile_reason",
    "review_status",
    "review_author",
    "review_as_of_date",
    "source_name",
    "source_reference",
    "notes",
]

VALID_MATERIALIZATION_REVIEW_STATUSES = {"REVIEW", "PENDING", "APPROVED", "REJECTED"}


@dataclass(frozen=True)
class ExactMapEntry:
    row_number: int
    ticker: str
    isin: str
    row: dict[str, str]


@dataclass(frozen=True)
class MaterializationResult:
    seed_rows_total: int
    mapped_rows_total: int
    review_rows_total: int
    approved_rows_total: int
    review_required_rows_total: int
    master_input_path: Path | None
    master_rows_total: int
    master_identity_matched_rows_total: int
    master_identity_missing_rows_total: int
    duplicate_master_isin_count: int
    output_path: Path
    report_path: Path | None
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class MasterIdentityContext:
    input_path: Path | None
    rows_total: int
    by_isin: dict[str, dict[str, str]]
    duplicate_isin_count: int


def read_csv_rows_with_header(path_value: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def canonical_isin(value: Any) -> str:
    return str(value or "").strip().upper()


def materialized_sort_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        canonicalize_ticker(row.get("ticker", "")),
        canonical_isin(row.get("isin", "")),
        str(row.get("company_name", "") or "").strip(),
    )


def append_note_token(notes: str, token: str) -> str:
    text = str(notes or "").strip()
    if not token or token in text:
        return text
    return f"{text} {token}".strip()


def build_master_identity_context(path_value: str | Path) -> MasterIdentityContext:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return MasterIdentityContext(input_path=path, rows_total=0, by_isin={}, duplicate_isin_count=0)

    fieldnames, rows = read_csv_rows_with_header(path)
    require_header_columns(fieldnames, ["ticker", "isin", "company_name"], f"personal fundamentals master ({path_value})")
    by_isin: dict[str, dict[str, str]] = {}
    duplicate_isins: set[str] = set()
    for row in rows:
        isin = canonical_isin(row.get("isin", ""))
        if not isin:
            continue
        if isin in by_isin:
            duplicate_isins.add(isin)
            continue
        by_isin[isin] = row
    if duplicate_isins:
        raise ValueError(
            "personal fundamentals master has duplicate isin value(s); profile review materialization would be ambiguous: "
            + ", ".join(sorted(duplicate_isins))
        )
    return MasterIdentityContext(input_path=path, rows_total=len(rows), by_isin=by_isin, duplicate_isin_count=len(duplicate_isins))


def parse_optional_iso_date(value: Any, source_name: str, row_number: int) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{source_name} row {row_number} has invalid review_as_of_date: {text!r}; expected YYYY-MM-DD") from exc
    return text


def validate_exact_map_row(row: dict[str, str], source_name: str, row_number: int) -> ExactMapEntry:
    ticker = canonicalize_ticker(row.get("ticker", ""))
    isin = canonical_isin(row.get("isin", ""))
    if not ticker and not isin:
        raise ValueError(f"{source_name} row {row_number} requires ticker or isin for exact matching")

    profile = safe_upper(row.get("company_type_profile", ""))
    if profile and profile not in VALID_COMPANY_TYPE_PROFILES:
        raise ValueError(
            f"{source_name} row {row_number} has invalid company_type_profile: {row.get('company_type_profile')!r}; "
            f"allowed: {', '.join(sorted(VALID_COMPANY_TYPE_PROFILES))}"
        )

    profile_reason = str(row.get("profile_reason", "") or "").strip()
    if profile == "OTHER" and not profile_reason:
        raise ValueError(f"{source_name} row {row_number} has company_type_profile=OTHER but blank profile_reason")

    review_status = safe_upper(row.get("review_status", "")) or "REVIEW"
    if review_status not in VALID_MATERIALIZATION_REVIEW_STATUSES:
        raise ValueError(
            f"{source_name} row {row_number} has invalid review_status: {row.get('review_status')!r}; "
            f"allowed: {', '.join(sorted(VALID_MATERIALIZATION_REVIEW_STATUSES))}"
        )

    review_as_of_date = parse_optional_iso_date(row.get("review_as_of_date", ""), source_name, row_number)
    if review_status == "APPROVED":
        if not profile:
            raise ValueError(f"{source_name} row {row_number} has review_status=APPROVED but blank company_type_profile")
        missing = []
        if not str(row.get("review_author", "") or "").strip():
            missing.append("review_author")
        if not review_as_of_date:
            missing.append("review_as_of_date")
        if not str(row.get("source_name", "") or "").strip() and not str(row.get("source_reference", "") or "").strip():
            missing.append("source_name or source_reference")
        if missing:
            raise ValueError(
                f"{source_name} row {row_number} has review_status=APPROVED but missing required review metadata: "
                f"{', '.join(missing)}"
            )

    normalized = {field: str(row.get(field, "") or "").strip() for field in EXACT_MAP_FIELDS}
    normalized["ticker"] = ticker
    normalized["isin"] = isin
    normalized["company_type_profile"] = profile
    normalized["review_status"] = review_status
    normalized["review_as_of_date"] = review_as_of_date
    return ExactMapEntry(row_number=row_number, ticker=ticker, isin=isin, row=normalized)


def exact_map_content_key(entry: ExactMapEntry) -> tuple[str, ...]:
    return tuple(entry.row.get(field, "") for field in EXACT_MAP_FIELDS)


def load_exact_map_entries(path_value: str | Path) -> list[ExactMapEntry]:
    fieldnames, rows = read_csv_rows_with_header(path_value)
    source_name = f"personal profile review exact map ({path_value})"
    require_header_columns(fieldnames, EXACT_MAP_FIELDS, source_name)
    entries = [validate_exact_map_row(row, source_name, row_number) for row_number, row in enumerate(rows, start=2)]

    seen_by_key: dict[tuple[str, str], tuple[str, ...]] = {}
    for entry in entries:
        for key in ((entry.ticker, ""), ("", entry.isin), (entry.ticker, entry.isin)):
            if not key[0] and not key[1]:
                continue
            content = exact_map_content_key(entry)
            existing = seen_by_key.get(key)
            if existing is None:
                seen_by_key[key] = content
                continue
            if existing != content:
                key_text = f"ticker={key[0] or '<blank>'}, isin={key[1] or '<blank>'}"
                raise ValueError(f"{source_name} has conflicting rows for exact key {key_text}")
    return entries


def entry_matches_seed(entry: ExactMapEntry, seed_row: dict[str, str]) -> bool:
    seed_ticker = canonicalize_ticker(seed_row.get("ticker", ""))
    seed_isin = canonical_isin(seed_row.get("isin", ""))
    if entry.ticker and entry.ticker != seed_ticker:
        return False
    if entry.isin and entry.isin != seed_isin:
        return False
    return bool(entry.ticker or entry.isin)


def find_exact_map_entry(seed_row: dict[str, str], entries: list[ExactMapEntry], source_name: str) -> ExactMapEntry | None:
    matches = [entry for entry in entries if entry_matches_seed(entry, seed_row)]
    if not matches:
        return None
    first_key = exact_map_content_key(matches[0])
    for entry in matches[1:]:
        if exact_map_content_key(entry) != first_key:
            ticker = canonicalize_ticker(seed_row.get("ticker", ""))
            isin = canonical_isin(seed_row.get("isin", ""))
            raise ValueError(
                f"{source_name} has conflicting exact map rows for seed identity ticker={ticker or '<blank>'}, isin={isin or '<blank>'}"
            )
    return matches[0]


def seed_review_row(seed_row: dict[str, str], master_row: dict[str, str] | None = None) -> dict[str, str]:
    seed_ticker = canonicalize_ticker(seed_row.get("ticker", ""))
    master_row = master_row or {}
    notes = str(seed_row.get("notes", "") or "").strip()
    if master_row and seed_ticker:
        notes = append_note_token(notes, f"sec_identity_ticker={seed_ticker}")
    return {
        "ticker": canonicalize_ticker(master_row.get("ticker", "")) if master_row else seed_ticker,
        "isin": canonical_isin(master_row.get("isin", "")) if master_row else canonical_isin(seed_row.get("isin", "")),
        "company_name": str(master_row.get("company_name", "") or "").strip() or str(seed_row.get("company_name", "") or "").strip(),
        "proposed_company_type_profile": "",
        "profile_reason": "",
        "review_status": "REVIEW",
        "review_author": "",
        "review_as_of_date": "",
        "source_name": "",
        "source_reference": "",
        "notes": notes,
    }


def apply_exact_map(row: dict[str, str], entry: ExactMapEntry) -> dict[str, str]:
    mapped = dict(row)
    mapped.update(
        {
            "proposed_company_type_profile": entry.row["company_type_profile"],
            "profile_reason": entry.row["profile_reason"],
            "review_status": entry.row["review_status"] or "REVIEW",
            "review_author": entry.row["review_author"],
            "review_as_of_date": entry.row["review_as_of_date"],
            "source_name": entry.row["source_name"],
            "source_reference": entry.row["source_reference"],
        }
    )
    if entry.row["notes"]:
        sec_identity_ticker = ""
        for part in str(row.get("notes", "") or "").split():
            if part.startswith("sec_identity_ticker="):
                sec_identity_ticker = part
                break
        mapped["notes"] = append_note_token(entry.row["notes"], sec_identity_ticker)
    return mapped


def build_review_rows(
    seed_rows: list[dict[str, str]],
    exact_map_entries: list[ExactMapEntry],
    master_context: MasterIdentityContext,
) -> tuple[list[dict[str, str]], int, int, int, tuple[str, ...]]:
    warnings: list[str] = []
    mapped_entry_row_numbers: set[int] = set()
    output_rows: list[dict[str, str]] = []
    source_name = "personal profile review exact map"
    master_identity_matched_rows_total = 0
    master_identity_missing_rows_total = 0

    for seed_row in seed_rows:
        seed_isin = canonical_isin(seed_row.get("isin", ""))
        master_row = master_context.by_isin.get(seed_isin) if seed_isin else None
        if master_row is not None:
            master_identity_matched_rows_total += 1
        else:
            master_identity_missing_rows_total += 1
            if seed_isin:
                warnings.append(f"master_identity_missing_for_isin={seed_isin}")
        row = seed_review_row(seed_row, master_row)
        entry = find_exact_map_entry(seed_row, exact_map_entries, source_name)
        if entry is not None:
            row = apply_exact_map(row, entry)
            mapped_entry_row_numbers.add(entry.row_number)
        output_rows.append(row)

    unmatched = [entry for entry in exact_map_entries if entry.row_number not in mapped_entry_row_numbers]
    if unmatched:
        warnings.append(
            "exact_map_unmatched_rows="
            + ",".join(str(entry.row_number) for entry in sorted(unmatched, key=lambda item: item.row_number))
        )

    output_rows.sort(key=materialized_sort_key)
    return output_rows, len(mapped_entry_row_numbers), master_identity_matched_rows_total, master_identity_missing_rows_total, tuple(warnings)


def write_report(path_value: str | Path, result: MaterializationResult) -> Path:
    lines = [
        "# Personal Profile Review Materialization Report",
        "",
        f"- seed_rows_total: {result.seed_rows_total}",
        f"- mapped_rows_total: {result.mapped_rows_total}",
        f"- review_rows_total: {result.review_rows_total}",
        f"- approved_rows_total: {result.approved_rows_total}",
        f"- review_required_rows_total: {result.review_required_rows_total}",
        f"- master_input_path: {result.master_input_path or ''}",
        f"- master_rows_total: {result.master_rows_total}",
        f"- master_identity_matched_rows_total: {result.master_identity_matched_rows_total}",
        f"- master_identity_missing_rows_total: {result.master_identity_missing_rows_total}",
        f"- duplicate_master_isin_count: {result.duplicate_master_isin_count}",
        f"- output_path: {result.output_path}",
        "- warnings:",
    ]
    if result.warnings:
        lines.extend(f"  - {warning}" for warning in result.warnings)
    else:
        lines.append("  - none")
    path = resolve_repo_path(path_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_personal_profile_review_materialize(
    *,
    seed_input: str = DEFAULT_PROFILE_SEED_OUTPUT,
    fundamentals_master_input: str = DEFAULT_PERSONAL_MASTER_PATH,
    output: str = DEFAULT_REVIEW_OUTPUT,
    exact_map_input: str = DEFAULT_EXACT_MAP_INPUT,
    overwrite: bool = False,
    dry_run: bool = False,
    report_output: str | None = None,
) -> MaterializationResult:
    output_path = resolve_repo_path(output)
    if output_path.exists() and not overwrite and not dry_run:
        raise ValueError(f"output already exists; pass --overwrite to replace it: {output_path}")

    seed_fieldnames, seed_rows = read_csv_rows_with_header(seed_input)
    require_header_columns(seed_fieldnames, PROFILE_REVIEW_INPUT_FIELDS, f"profile review seed ({seed_input})")
    master_context = build_master_identity_context(fundamentals_master_input)

    warnings: list[str] = []
    if master_context.input_path and not master_context.input_path.exists():
        warnings.append(f"optional_fundamentals_master_missing={master_context.input_path}")
    exact_map_path = resolve_repo_path(exact_map_input)
    exact_map_entries: list[ExactMapEntry] = []
    if exact_map_input and exact_map_path.exists():
        exact_map_entries = load_exact_map_entries(exact_map_path)
    elif exact_map_input:
        warnings.append(f"optional_exact_map_missing={exact_map_path}")

    review_rows, mapped_rows_total, master_matched_total, master_missing_total, row_warnings = build_review_rows(
        seed_rows,
        exact_map_entries,
        master_context,
    )
    warnings.extend(row_warnings)

    approved_rows_total = sum(1 for row in review_rows if safe_upper(row.get("review_status")) == "APPROVED")
    review_required_rows_total = len(review_rows) - approved_rows_total

    if not dry_run:
        write_csv_rows(output_path, PROFILE_REVIEW_INPUT_FIELDS, review_rows)

    result = MaterializationResult(
        seed_rows_total=len(seed_rows),
        mapped_rows_total=mapped_rows_total,
        review_rows_total=len(review_rows),
        approved_rows_total=approved_rows_total,
        review_required_rows_total=review_required_rows_total,
        master_input_path=master_context.input_path,
        master_rows_total=master_context.rows_total,
        master_identity_matched_rows_total=master_matched_total,
        master_identity_missing_rows_total=master_missing_total,
        duplicate_master_isin_count=master_context.duplicate_isin_count,
        output_path=output_path,
        report_path=None,
        warnings=tuple(warnings),
    )
    if report_output and not dry_run:
        report_path = write_report(report_output, result)
        result = MaterializationResult(
            seed_rows_total=result.seed_rows_total,
            mapped_rows_total=result.mapped_rows_total,
            review_rows_total=result.review_rows_total,
            approved_rows_total=result.approved_rows_total,
            review_required_rows_total=result.review_required_rows_total,
            master_input_path=result.master_input_path,
            master_rows_total=result.master_rows_total,
            master_identity_matched_rows_total=result.master_identity_matched_rows_total,
            master_identity_missing_rows_total=result.master_identity_missing_rows_total,
            duplicate_master_isin_count=result.duplicate_master_isin_count,
            output_path=result.output_path,
            report_path=report_path,
            warnings=result.warnings,
        )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize a review-first personal company_type_profile CSV from the SEC identity profile-review seed."
    )
    parser.add_argument("--seed-input", default=DEFAULT_PROFILE_SEED_OUTPUT, help="Processed SEC identity profile-review seed CSV.")
    parser.add_argument("--fundamentals-master-input", default=DEFAULT_PERSONAL_MASTER_PATH, help="Personal fundamentals master used to write downstream-compatible review identifiers.")
    parser.add_argument("--output", default=DEFAULT_REVIEW_OUTPUT, help="Canonical raw personal profile review CSV output.")
    parser.add_argument("--exact-map-input", default=DEFAULT_EXACT_MAP_INPUT, help="Optional private exact ticker/isin review map CSV.")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing an existing output file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and summarize without writing output files.")
    parser.add_argument("--report-output", default="", help="Optional Markdown materialization report output path.")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help=f"Write the default materialization report to {DEFAULT_REPORT_OUTPUT} unless --report-output is set.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report_output = args.report_output or (DEFAULT_REPORT_OUTPUT if args.write_report else None)
    run_personal_profile_review_materialize(
        seed_input=args.seed_input,
        fundamentals_master_input=args.fundamentals_master_input,
        output=args.output,
        exact_map_input=args.exact_map_input,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        report_output=report_output,
    )


if __name__ == "__main__":
    main()
