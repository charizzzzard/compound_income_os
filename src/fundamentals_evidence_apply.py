from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, normalize_number_text, read_csv_rows, resolve_repo_path, write_csv_rows
from src.fundamentals_evidence_engine import DEFAULT_PROPOSED_UPDATES_OUTPUT, PROPOSED_UPDATES_FIELDS
from src.fundamentals_master import CORE_KPI_FIELDS, DEFAULT_PERSONAL_MASTER_PATH, PERSONAL_MASTER_FIELDS, validate_personal_fundamentals_master

DEFAULT_APPLY_REGISTRY_OUTPUT = "data/processed/personal_fundamentals_evidence_apply_registry.csv"
DEFAULT_EVIDENCE_APPLIED_MASTER_OUTPUT = "data/processed/personal_fundamentals_master_evidence_applied.csv"
DEFAULT_APPLY_SUMMARY_OUTPUT = "data/processed/personal_fundamentals_evidence_apply_summary.csv"

APPLY_REGISTRY_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "target_field",
    "kpi_name",
    "apply_status",
    "apply_value",
    "reported_unit",
    "currency",
    "source_type",
    "source_name",
    "source_reference",
    "source_as_of_date",
    "fiscal_year",
    "verification_status",
    "data_quality_flag",
    "proposal_reason",
    "notes",
]

APPLY_SUMMARY_FIELDS = [
    "base_master_rows_total",
    "proposed_updates_rows_total",
    "applied_rows_total",
    "applied_fields_total",
    "skipped_unsupported_fields_total",
    "skipped_no_match_total",
    "skipped_blank_value_total",
    "duplicate_identical_total",
    "notes",
]

SUPPORTED_APPLY_FIELDS = [field for field in CORE_KPI_FIELDS if field in PERSONAL_MASTER_FIELDS]


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


def canonical_company_name(value: Any) -> str:
    return str(value or "").strip()


def canonical_isin(value: Any) -> str:
    return str(value or "").strip().upper()


def entity_sort_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        canonicalize_ticker(row.get("ticker", "")),
        canonical_isin(row.get("isin", "")),
        canonical_company_name(row.get("company_name", "")),
    )


def registry_sort_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        canonicalize_ticker(row.get("ticker", "")),
        canonical_isin(row.get("isin", "")),
        canonical_company_name(row.get("company_name", "")),
        str(row.get("target_field", "") or "").strip(),
        str(row.get("apply_status", "") or "").strip(),
        str(row.get("source_as_of_date", "") or "").strip(),
        str(row.get("source_name", "") or "").strip(),
        str(row.get("source_reference", "") or "").strip(),
    )


def build_master_match_index(master_rows: list[dict[str, str]]) -> dict[str, dict[str, list[int]]]:
    index: dict[str, dict[str, list[int]]] = {"ticker": {}, "isin": {}, "company_name": {}}
    for idx, row in enumerate(master_rows):
        ticker = canonicalize_ticker(row.get("ticker", ""))
        isin = canonical_isin(row.get("isin", ""))
        company_name = canonical_company_name(row.get("company_name", ""))
        if ticker:
            index["ticker"].setdefault(ticker, []).append(idx)
        if isin:
            index["isin"].setdefault(isin, []).append(idx)
        if company_name:
            index["company_name"].setdefault(company_name, []).append(idx)
    return index


def match_proposed_update_to_master(
    row: dict[str, str],
    master_rows: list[dict[str, str]],
    match_index: dict[str, dict[str, list[int]]],
    source_name: str,
    row_number: int,
) -> int | None:
    ticker = canonicalize_ticker(row.get("ticker", ""))
    isin = canonical_isin(row.get("isin", ""))
    company_name = canonical_company_name(row.get("company_name", ""))
    if not ticker and not isin and not company_name:
        raise ValueError(f"{source_name} row {row_number} requires ticker, isin or company_name for exact master matching")

    candidate_sets: list[tuple[str, list[int]]] = []
    if ticker:
        candidate_sets.append(("ticker", match_index["ticker"].get(ticker, [])))
    if isin:
        candidate_sets.append(("isin", match_index["isin"].get(isin, [])))
    if company_name:
        candidate_sets.append(("company_name", match_index["company_name"].get(company_name, [])))

    ambiguous_fields = [field for field, candidates in candidate_sets if len(candidates) > 1]
    if ambiguous_fields:
        raise ValueError(
            f"{source_name} row {row_number} has ambiguous master match for identifier(s): {', '.join(sorted(ambiguous_fields))}"
        )

    matched_indexes = {candidates[0] for _field, candidates in candidate_sets if len(candidates) == 1}
    if not matched_indexes:
        return None
    if len(matched_indexes) > 1:
        raise ValueError(
            f"{source_name} row {row_number} has conflicting exact entity identifiers for master match: "
            f"ticker={ticker or '<blank>'}, isin={isin or '<blank>'}, company_name={company_name or '<blank>'}"
        )

    matched_index = matched_indexes.pop()
    matched_row = master_rows[matched_index]
    matched_ticker = canonicalize_ticker(matched_row.get("ticker", ""))
    matched_isin = canonical_isin(matched_row.get("isin", ""))
    matched_company_name = canonical_company_name(matched_row.get("company_name", ""))
    if ticker and matched_ticker and ticker != matched_ticker:
        raise ValueError(f"{source_name} row {row_number} ticker={ticker} conflicts with matched master ticker={matched_ticker}")
    if isin and matched_isin and isin != matched_isin:
        raise ValueError(f"{source_name} row {row_number} isin={isin} conflicts with matched master isin={matched_isin}")
    if company_name and matched_company_name and company_name != matched_company_name:
        raise ValueError(
            f"{source_name} row {row_number} company_name={company_name!r} conflicts with matched master company_name={matched_company_name!r}"
        )
    return matched_index


def canonical_apply_value(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    cleaned = normalize_number_text(text.replace("%", ""))
    try:
        return format(float(cleaned), ".15g")
    except ValueError:
        return text


def registry_row_from_update(row: dict[str, str], *, target_field: str, apply_status: str, notes: str = "") -> dict[str, str]:
    return {
        "ticker": canonicalize_ticker(row.get("ticker", "")),
        "isin": canonical_isin(row.get("isin", "")),
        "company_name": canonical_company_name(row.get("company_name", "")),
        "target_field": target_field,
        "kpi_name": str(row.get("kpi_name", "") or "").strip(),
        "apply_status": apply_status,
        "apply_value": str(row.get("reported_value", "") or "").strip(),
        "reported_unit": str(row.get("reported_unit", "") or "").strip(),
        "currency": str(row.get("currency", "") or "").strip().upper(),
        "source_type": str(row.get("source_type", "") or "").strip(),
        "source_name": str(row.get("source_name", "") or "").strip(),
        "source_reference": str(row.get("source_reference", "") or "").strip(),
        "source_as_of_date": str(row.get("source_as_of_date", "") or "").strip(),
        "fiscal_year": str(row.get("fiscal_year", "") or "").strip(),
        "verification_status": str(row.get("verification_status", "") or "").strip(),
        "data_quality_flag": str(row.get("data_quality_flag", "") or "").strip(),
        "proposal_reason": str(row.get("proposal_reason", "") or "").strip(),
        "notes": notes or str(row.get("notes", "") or "").strip(),
    }


def build_applied_master_projection(
    master_rows: list[dict[str, str]],
    proposed_update_rows: list[dict[str, str]],
    source_name: str = "personal fundamentals proposed updates",
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, int]]:
    applied_master_rows = [{field: str(row.get(field, "") or "").strip() for field in PERSONAL_MASTER_FIELDS} for row in master_rows]
    match_index = build_master_match_index(master_rows)
    registry_rows: list[dict[str, str]] = []
    applied_slot_values: dict[tuple[int, str], str] = {}
    applied_slot_rows: dict[tuple[int, str], dict[str, str]] = {}
    counters: Counter[str] = Counter()

    for row_number, row in enumerate(proposed_update_rows, start=2):
        kpi_name = str(row.get("kpi_name", "") or "").strip()
        if not kpi_name or kpi_name not in SUPPORTED_APPLY_FIELDS:
            registry_rows.append(
                registry_row_from_update(
                    row,
                    target_field=kpi_name,
                    apply_status="SKIPPED_UNSUPPORTED_FIELD",
                    notes="Apply skipped because kpi_name has no direct supported Personal-Master target field.",
                )
            )
            counters["skipped_unsupported_fields_total"] += 1
            continue

        reported_value = str(row.get("reported_value", "") or "").strip()
        if not reported_value:
            registry_rows.append(
                registry_row_from_update(
                    row,
                    target_field=kpi_name,
                    apply_status="SKIPPED_BLANK_VALUE",
                    notes="Apply skipped because reported_value is blank.",
                )
            )
            counters["skipped_blank_value_total"] += 1
            continue

        matched_index = match_proposed_update_to_master(row, master_rows, match_index, source_name, row_number)
        if matched_index is None:
            registry_rows.append(
                registry_row_from_update(
                    row,
                    target_field=kpi_name,
                    apply_status="SKIPPED_NO_MATCH",
                    notes="Apply skipped because no exact Personal-Master entity match exists for ticker/isin/company_name.",
                )
            )
            counters["skipped_no_match_total"] += 1
            continue

        slot_key = (matched_index, kpi_name)
        candidate_value = canonical_apply_value(reported_value)
        existing_value = applied_slot_values.get(slot_key)
        if existing_value is not None:
            if existing_value != candidate_value:
                previous_row = applied_slot_rows[slot_key]
                raise ValueError(
                    f"{source_name} row {row_number} conflicts for entity={canonicalize_ticker(row.get('ticker', '')) or canonical_isin(row.get('isin', '')) or canonical_company_name(row.get('company_name', ''))} "
                    f"target_field={kpi_name}: {previous_row.get('reported_value', '')!r} vs {reported_value!r}"
                )
            registry_rows.append(
                registry_row_from_update(
                    row,
                    target_field=kpi_name,
                    apply_status="DUPLICATE_IDENTICAL",
                    notes="Apply skipped because an identical entity+field+value proposal was already applied.",
                )
            )
            counters["duplicate_identical_total"] += 1
            continue

        applied_slot_values[slot_key] = candidate_value
        applied_slot_rows[slot_key] = row
        applied_master_rows[matched_index][kpi_name] = reported_value
        registry_rows.append(
            registry_row_from_update(
                row,
                target_field=kpi_name,
                apply_status="APPLIED",
                notes="Applied from validated proposed-updates artifact selected as the canonical field-level Evidence output with reported_value.",
            )
        )
        counters["applied_rows_total"] += 1

    counters["applied_fields_total"] = len(applied_slot_values)
    validate_personal_fundamentals_master(applied_master_rows, "personal fundamentals evidence-applied master")
    return sorted(registry_rows, key=registry_sort_key), applied_master_rows, dict(counters)


def build_summary_row(master_rows: list[dict[str, str]], proposed_update_rows: list[dict[str, str]], counters: dict[str, int]) -> list[dict[str, str]]:
    return [
        {
            "base_master_rows_total": str(len(master_rows)),
            "proposed_updates_rows_total": str(len(proposed_update_rows)),
            "applied_rows_total": str(counters.get("applied_rows_total", 0)),
            "applied_fields_total": str(counters.get("applied_fields_total", 0)),
            "skipped_unsupported_fields_total": str(counters.get("skipped_unsupported_fields_total", 0)),
            "skipped_no_match_total": str(counters.get("skipped_no_match_total", 0)),
            "skipped_blank_value_total": str(counters.get("skipped_blank_value_total", 0)),
            "duplicate_identical_total": str(counters.get("duplicate_identical_total", 0)),
            "notes": "apply_input_contract=personal_fundamentals_proposed_updates.csv; selected because fundamentals_evidence already validates evidence rows and emits field-level reported_value proposals for manual master projection.",
        }
    ]


def run_fundamentals_evidence_apply(
    fundamentals_master_path: str = DEFAULT_PERSONAL_MASTER_PATH,
    proposed_updates_input_path: str = DEFAULT_PROPOSED_UPDATES_OUTPUT,
    registry_output: str = DEFAULT_APPLY_REGISTRY_OUTPUT,
    evidence_applied_master_output: str = DEFAULT_EVIDENCE_APPLIED_MASTER_OUTPUT,
    summary_output: str = DEFAULT_APPLY_SUMMARY_OUTPUT,
) -> dict[str, Path]:
    master_rows = read_csv_rows(fundamentals_master_path)
    validate_personal_fundamentals_master(master_rows, f"personal fundamentals master ({fundamentals_master_path})")
    fieldnames, proposed_update_rows = read_csv_rows_with_header(proposed_updates_input_path)
    require_header_columns(
        fieldnames,
        PROPOSED_UPDATES_FIELDS,
        f"personal fundamentals proposed updates ({proposed_updates_input_path})",
    )
    registry_rows, applied_master_rows, counters = build_applied_master_projection(
        master_rows,
        proposed_update_rows,
        source_name=f"personal fundamentals proposed updates ({proposed_updates_input_path})",
    )
    outputs = {
        "evidence_apply_registry": write_csv_rows(registry_output, APPLY_REGISTRY_FIELDS, registry_rows),
        "evidence_applied_master": write_csv_rows(evidence_applied_master_output, PERSONAL_MASTER_FIELDS, applied_master_rows),
        "evidence_apply_summary": write_csv_rows(summary_output, APPLY_SUMMARY_FIELDS, build_summary_row(master_rows, proposed_update_rows, counters)),
    }
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project validated evidence proposed-updates into a separate evidence-applied Personal-Master.")
    parser.add_argument("--fundamentals-master", default=DEFAULT_PERSONAL_MASTER_PATH, help="Base personal fundamentals master CSV.")
    parser.add_argument("--proposed-updates-input", default=DEFAULT_PROPOSED_UPDATES_OUTPUT, help="Validated proposed-updates CSV from fundamentals_evidence.")
    parser.add_argument("--registry-output", default=DEFAULT_APPLY_REGISTRY_OUTPUT, help="Evidence-apply registry output.")
    parser.add_argument("--evidence-applied-master-output", default=DEFAULT_EVIDENCE_APPLIED_MASTER_OUTPUT, help="Evidence-applied Personal-Master output.")
    parser.add_argument("--summary-output", default=DEFAULT_APPLY_SUMMARY_OUTPUT, help="Evidence-apply summary output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_fundamentals_evidence_apply(
        fundamentals_master_path=args.fundamentals_master,
        proposed_updates_input_path=args.proposed_updates_input,
        registry_output=args.registry_output,
        evidence_applied_master_output=args.evidence_applied_master_output,
        summary_output=args.summary_output,
    )


if __name__ == "__main__":
    main()
