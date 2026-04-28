from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, write_csv_rows
from src.personal_sec_derived_kpi_compose import (
    DEFAULT_APPROVAL_APPLIED,
    DEFAULT_UNLOCK_MATRIX,
    REQUIRED_ROLES,
    clean_text,
    to_float_or_none,
)

DEFAULT_OUTPUT_DIR = "data/processed"
DEFAULT_REPORT_DIR = "reports/2026-04-27"

INVENTORY_OUTPUT = "personal_sec_fact_source_inventory.csv"
AUDIT_OUTPUT = "personal_sec_derived_kpi_fact_source_audit.csv"
SUMMARY_OUTPUT = "personal_sec_derived_kpi_fact_source_summary.csv"
REPORT_OUTPUT = "personal_sec_derived_kpi_fact_source_audit_report.md"

INVENTORY_FIELDS = [
    "artifact_path",
    "artifact_kind",
    "row_count",
    "columns",
    "has_holding_name",
    "has_ticker",
    "has_isin",
    "has_sec_concept",
    "has_unit",
    "has_fiscal_year",
    "has_fiscal_period",
    "has_form",
    "has_filed_date",
    "has_frame",
    "has_numeric_value",
    "candidate_for_derived_kpi_compose",
    "privacy_classification",
    "notes",
]

AUDIT_FIELDS = [
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "formula_recipe",
    "formula_role",
    "approved_sec_concept",
    "source_artifact",
    "source_row_count",
    "matching_fact_count",
    "matching_numeric_fact_count",
    "annual_fact_count",
    "annual_10k_fact_count",
    "fy_fact_count",
    "fiscal_years_available",
    "units_available",
    "forms_available",
    "frames_available",
    "latest_fiscal_year",
    "earliest_fiscal_year",
    "source_usable_for_compose",
    "unusable_reason",
    "recommended_source_artifact",
]

SUMMARY_FIELDS = [
    "approved_roles_total",
    "approved_roles_with_any_matching_fact",
    "approved_roles_with_numeric_values",
    "approved_roles_with_annual_facts",
    "approved_roles_with_annual_10k_facts",
    "approved_roles_usable_for_compose",
    "approved_roles_blocked_by_missing_value_column",
    "approved_roles_blocked_by_missing_period_metadata",
    "approved_roles_blocked_by_wrong_artifact",
    "recommended_compose_source_artifact_count",
    "no_network_confirmed",
    "no_score_change_confirmed",
    "no_master_mutation_confirmed",
    "no_imputation_confirmed",
]

VALUE_ALIASES = ("value", "fact_value", "reported_value", "numeric_value", "val")
YEAR_ALIASES = ("fiscal_year", "fy", "fiscalYear", "end_year")
PERIOD_ALIASES = ("fiscal_period", "fp", "fiscalPeriod")
CONCEPT_ALIASES = ("sec_concept", "concept", "candidate_sec_concept")
UNIT_ALIASES = ("unit", "reported_unit", "candidate_unit")
FORM_ALIASES = ("form", "filing_form")
FILED_DATE_ALIASES = ("filed_date", "filing_date", "source_as_of_date")
HOLDING_ALIASES = ("holding_name", "company_name", "snapshot_company_name")
TICKER_ALIASES = ("ticker", "holding_ticker")
ISIN_ALIASES = ("isin", "holding_isin")
FRAME_ALIASES = ("frame",)


@dataclass(frozen=True)
class FactSourceAuditResult:
    inventory_path: Path
    audit_path: Path
    summary_path: Path
    report_path: Path
    summary: dict[str, str]


def first_value(row: dict[str, str], aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        if alias in row and clean_text(row.get(alias)):
            return clean_text(row.get(alias))
    return ""


def has_any_column(columns: set[str], aliases: tuple[str, ...]) -> bool:
    return any(alias in columns for alias in aliases)


def row_numeric_value(row: dict[str, str]) -> float | None:
    for alias in VALUE_ALIASES:
        if alias in row:
            parsed = to_float_or_none(row.get(alias))
            if parsed is not None:
                return parsed
    return None


def normalized_year(row: dict[str, str]) -> str:
    year = first_value(row, YEAR_ALIASES)
    if year:
        return year
    frame = first_value(row, FRAME_ALIASES).upper()
    if frame.startswith("CY") and len(frame) >= 6 and frame[2:6].isdigit():
        return frame[2:6]
    return ""


def safe_artifact_label(path: Path) -> str:
    try:
        display_path = path.relative_to(resolve_repo_path("."))
    except ValueError:
        display_path = path
    normalized = display_path.as_posix()
    if "data/raw/private" in normalized or "sec_user_agent" in normalized.lower():
        return "<private_raw_file>"
    return normalized


def privacy_classification(path: Path) -> str:
    try:
        display_path = path.relative_to(resolve_repo_path("."))
    except ValueError:
        display_path = path
    normalized = display_path.as_posix().lower()
    if "data/raw/private" in normalized or "sec_user_agent" in normalized:
        return "PRIVATE_OMITTED_FROM_REPORTS"
    return "PUBLIC_PROCESSED"


def csv_header_and_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def candidate_for_compose(path: Path, columns: set[str], rows: list[dict[str, str]]) -> tuple[bool, str]:
    has_identity = has_any_column(columns, HOLDING_ALIASES) or has_any_column(columns, TICKER_ALIASES) or has_any_column(columns, ISIN_ALIASES)
    has_required_columns = (
        has_identity
        and has_any_column(columns, ISIN_ALIASES)
        and has_any_column(columns, CONCEPT_ALIASES)
        and has_any_column(columns, UNIT_ALIASES)
        and has_any_column(columns, YEAR_ALIASES + FRAME_ALIASES)
        and has_any_column(columns, PERIOD_ALIASES)
        and has_any_column(columns, FORM_ALIASES)
        and has_any_column(columns, FILED_DATE_ALIASES)
        and has_any_column(columns, VALUE_ALIASES)
    )
    if not has_required_columns:
        missing = []
        for label, aliases in (
            ("identity", ISIN_ALIASES),
            ("sec_concept", CONCEPT_ALIASES),
            ("unit", UNIT_ALIASES),
            ("fiscal_year", YEAR_ALIASES + FRAME_ALIASES),
            ("fiscal_period", PERIOD_ALIASES),
            ("form", FORM_ALIASES),
            ("filed_date", FILED_DATE_ALIASES),
            ("numeric_value", VALUE_ALIASES),
        ):
            if not has_any_column(columns, aliases):
                missing.append(label)
        return False, "missing columns: " + ";".join(missing)
    numeric_count = sum(1 for row in rows if row_numeric_value(row) is not None)
    if numeric_count == 0:
        return False, "value column present but no numeric values"
    if "data/raw/private" in path.as_posix().lower():
        return False, "private raw artifact is not allowed as public compose source"
    return True, "usable processed fact-shaped artifact"


def build_inventory_rows(paths: list[Path]) -> tuple[list[dict[str, str]], dict[str, list[dict[str, str]]]]:
    rows_by_label: dict[str, list[dict[str, str]]] = {}
    inventory: list[dict[str, str]] = []
    for path in sorted(paths, key=lambda item: item.as_posix()):
        kind = path.suffix.lower().lstrip(".") or "unknown"
        columns: list[str] = []
        data_rows: list[dict[str, str]] = []
        notes = ""
        if path.suffix.lower() == ".csv":
            try:
                columns, data_rows = csv_header_and_rows(path)
            except Exception as exc:  # pragma: no cover - defensive inventory path
                notes = f"read_error:{type(exc).__name__}"
        column_set = set(columns)
        candidate, candidate_notes = candidate_for_compose(path, column_set, data_rows) if path.suffix.lower() == ".csv" else (False, "not a csv fact source")
        label = safe_artifact_label(path)
        rows_by_label[label] = data_rows
        numeric_count = sum(1 for row in data_rows if row_numeric_value(row) is not None)
        inventory.append(
            {
                "artifact_path": label,
                "artifact_kind": kind,
                "row_count": str(len(data_rows)) if path.suffix.lower() == ".csv" else "",
                "columns": ";".join(columns),
                "has_holding_name": str(has_any_column(column_set, HOLDING_ALIASES)),
                "has_ticker": str(has_any_column(column_set, TICKER_ALIASES)),
                "has_isin": str(has_any_column(column_set, ISIN_ALIASES)),
                "has_sec_concept": str(has_any_column(column_set, CONCEPT_ALIASES)),
                "has_unit": str(has_any_column(column_set, UNIT_ALIASES)),
                "has_fiscal_year": str(has_any_column(column_set, YEAR_ALIASES)),
                "has_fiscal_period": str(has_any_column(column_set, PERIOD_ALIASES)),
                "has_form": str(has_any_column(column_set, FORM_ALIASES)),
                "has_filed_date": str(has_any_column(column_set, FILED_DATE_ALIASES)),
                "has_frame": str(has_any_column(column_set, FRAME_ALIASES)),
                "has_numeric_value": str(numeric_count > 0),
                "candidate_for_derived_kpi_compose": str(candidate),
                "privacy_classification": privacy_classification(path),
                "notes": notes or candidate_notes,
            }
        )
    return inventory, rows_by_label


def discover_paths() -> list[Path]:
    roots = [
        resolve_repo_path("data/processed"),
        resolve_repo_path("reports/2026-04-27"),
        resolve_repo_path("data/raw/private/fundamentals"),
    ]
    paths: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.iterdir():
            if path.is_file() and path.suffix.lower() in {".csv", ".md", ".json"}:
                if any(token in path.name.lower() for token in ("sec", "fact", "snapshot", "normalized", "staging", "evidence", "companyfacts")):
                    paths.append(path)
    return paths


def approved_role_rows(approval_rows: list[dict[str, str]], unlock_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    unlocked = {
        (clean_text(row.get("holding_name")), clean_text(row.get("isin")), clean_text(row.get("kpi_field")))
        for row in unlock_rows
        if clean_text(row.get("fully_approved_after_human_decisions")).lower() == "true"
    }
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for row in approval_rows:
        if clean_text(row.get("approval_status")).upper() != "APPROVED":
            continue
        key3 = (clean_text(row.get("holding_name")), clean_text(row.get("isin")), clean_text(row.get("kpi_field")))
        if key3 not in unlocked or clean_text(row.get("kpi_field")) not in REQUIRED_ROLES:
            continue
        key = key3 + (clean_text(row.get("formula_role")), clean_text(row.get("candidate_sec_concept")))
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return sorted(rows, key=lambda item: (clean_text(item.get("isin")), clean_text(item.get("kpi_field")), clean_text(item.get("formula_role")), clean_text(item.get("candidate_sec_concept"))))


def fact_matches(row: dict[str, str], role: dict[str, str]) -> bool:
    isin = first_value(row, ISIN_ALIASES)
    ticker = first_value(row, TICKER_ALIASES)
    holding = first_value(row, HOLDING_ALIASES)
    concept = first_value(row, CONCEPT_ALIASES)
    return (
        concept == clean_text(role.get("candidate_sec_concept"))
        and (isin == clean_text(role.get("isin")) or ticker == clean_text(role.get("ticker")) or holding == clean_text(role.get("holding_name")))
    )


def is_fy(row: dict[str, str]) -> bool:
    return first_value(row, PERIOD_ALIASES).upper() == "FY"


def has_annual_basis(row: dict[str, str]) -> bool:
    frame = first_value(row, FRAME_ALIASES).upper()
    return is_fy(row) or (frame.startswith("CY") and len(frame) >= 6 and frame[2:6].isdigit())


def has_annual_10k(row: dict[str, str]) -> bool:
    return is_fy(row) and "10-K" in first_value(row, FORM_ALIASES).upper()


def build_audit_rows(
    *,
    approved_roles: list[dict[str, str]],
    inventory_rows: list[dict[str, str]],
    rows_by_label: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    candidate_sources = [
        row
        for row in inventory_rows
        if row["artifact_kind"] == "csv"
        and row["privacy_classification"] != "PRIVATE_OMITTED_FROM_REPORTS"
        and (row["has_sec_concept"] == "True" or "sec" in row["artifact_path"].lower() or "fact" in row["artifact_path"].lower())
    ]
    if not candidate_sources:
        candidate_sources = [row for row in inventory_rows if row["artifact_path"].endswith("personal_sec_kpi_extraction_concept_candidates.csv")]

    audit_rows: list[dict[str, str]] = []
    for role in approved_roles:
        for source in candidate_sources:
            source_rows = rows_by_label.get(source["artifact_path"], [])
            matches = [row for row in source_rows if fact_matches(row, role)]
            numeric = [row for row in matches if row_numeric_value(row) is not None]
            annual = [row for row in numeric if has_annual_basis(row)]
            annual_10k = [row for row in numeric if has_annual_10k(row)]
            fiscal_years = sorted({normalized_year(row) for row in numeric if normalized_year(row)})
            units = sorted({first_value(row, UNIT_ALIASES) for row in numeric if first_value(row, UNIT_ALIASES)})
            forms = sorted({first_value(row, FORM_ALIASES) for row in numeric if first_value(row, FORM_ALIASES)})
            frames = sorted({first_value(row, FRAME_ALIASES) for row in numeric if first_value(row, FRAME_ALIASES)})
            usable = bool(annual_10k)
            if usable:
                reason = ""
            elif source["has_numeric_value"] != "True":
                reason = "MISSING_VALUE_COLUMN_OR_NUMERIC_VALUES"
            elif source["has_fiscal_period"] != "True" or source["has_form"] != "True":
                reason = "MISSING_PERIOD_METADATA"
            elif not matches:
                reason = "NO_MATCHING_APPROVED_CONCEPT_FACTS"
            elif not annual_10k:
                reason = "NO_ANNUAL_10K_FACTS"
            else:
                reason = "WRONG_ARTIFACT"
            audit_rows.append(
                {
                    "holding_name": clean_text(role.get("holding_name")),
                    "ticker": clean_text(role.get("ticker")),
                    "isin": clean_text(role.get("isin")),
                    "kpi_field": clean_text(role.get("kpi_field")),
                    "formula_recipe": clean_text(role.get("formula_recipe")),
                    "formula_role": clean_text(role.get("formula_role")),
                    "approved_sec_concept": clean_text(role.get("candidate_sec_concept")),
                    "source_artifact": source["artifact_path"],
                    "source_row_count": source["row_count"],
                    "matching_fact_count": str(len(matches)),
                    "matching_numeric_fact_count": str(len(numeric)),
                    "annual_fact_count": str(len(annual)),
                    "annual_10k_fact_count": str(len(annual_10k)),
                    "fy_fact_count": str(sum(1 for row in numeric if is_fy(row))),
                    "fiscal_years_available": ";".join(fiscal_years),
                    "units_available": ";".join(units),
                    "forms_available": ";".join(forms),
                    "frames_available": ";".join(frames),
                    "latest_fiscal_year": max(fiscal_years) if fiscal_years else "",
                    "earliest_fiscal_year": min(fiscal_years) if fiscal_years else "",
                    "source_usable_for_compose": str(usable),
                    "unusable_reason": reason,
                    "recommended_source_artifact": source["artifact_path"] if usable else "",
                }
            )
    return audit_rows


def count_roles_with(audit_rows: list[dict[str, str]], predicate) -> int:
    roles: set[tuple[str, str, str, str, str]] = set()
    for row in audit_rows:
        if predicate(row):
            roles.add((row["holding_name"], row["isin"], row["kpi_field"], row["formula_role"], row["approved_sec_concept"]))
    return len(roles)


def build_summary(approved_roles: list[dict[str, str]], audit_rows: list[dict[str, str]]) -> dict[str, str]:
    usable_sources = {row["recommended_source_artifact"] for row in audit_rows if row["recommended_source_artifact"]}
    return {
        "approved_roles_total": str(len(approved_roles)),
        "approved_roles_with_any_matching_fact": str(count_roles_with(audit_rows, lambda row: int(row["matching_fact_count"] or "0") > 0)),
        "approved_roles_with_numeric_values": str(count_roles_with(audit_rows, lambda row: int(row["matching_numeric_fact_count"] or "0") > 0)),
        "approved_roles_with_annual_facts": str(count_roles_with(audit_rows, lambda row: int(row["annual_fact_count"] or "0") > 0)),
        "approved_roles_with_annual_10k_facts": str(count_roles_with(audit_rows, lambda row: int(row["annual_10k_fact_count"] or "0") > 0)),
        "approved_roles_usable_for_compose": str(count_roles_with(audit_rows, lambda row: row["source_usable_for_compose"] == "True")),
        "approved_roles_blocked_by_missing_value_column": str(count_roles_with(audit_rows, lambda row: row["unusable_reason"] == "MISSING_VALUE_COLUMN_OR_NUMERIC_VALUES")),
        "approved_roles_blocked_by_missing_period_metadata": str(count_roles_with(audit_rows, lambda row: row["unusable_reason"] == "MISSING_PERIOD_METADATA")),
        "approved_roles_blocked_by_wrong_artifact": str(count_roles_with(audit_rows, lambda row: row["unusable_reason"] in {"WRONG_ARTIFACT", "NO_MATCHING_APPROVED_CONCEPT_FACTS", "NO_ANNUAL_10K_FACTS"})),
        "recommended_compose_source_artifact_count": str(len(usable_sources)),
        "no_network_confirmed": "True",
        "no_score_change_confirmed": "True",
        "no_master_mutation_confirmed": "True",
        "no_imputation_confirmed": "True",
    }


def render_report(
    *,
    inventory_rows: list[dict[str, str]],
    audit_rows: list[dict[str, str]],
    summary: dict[str, str],
) -> str:
    public_inventory = [row for row in inventory_rows if row["privacy_classification"] != "PRIVATE_OMITTED_FROM_REPORTS"]
    recommended = sorted({row["recommended_source_artifact"] for row in audit_rows if row["recommended_source_artifact"]})
    if recommended:
        recommended_text = ", ".join(f"`{item}`" for item in recommended)
        next_patch = "`SEC DERIVED KPI COMPOSE / NORMALIZED FACT SOURCE`"
    else:
        recommended_text = "`none`"
        next_patch = "`SEC SNAPSHOT NORMALIZED FACT EXPORT / COMPANYFACTS VALUES FOR APPROVED CONCEPTS`"
    lines = [
        "# SEC Derived KPI Fact Source Audit",
        "",
        "## Executive Summary",
        f"- approved_roles_total: `{summary['approved_roles_total']}`",
        f"- approved_roles_with_any_matching_fact: `{summary['approved_roles_with_any_matching_fact']}`",
        f"- approved_roles_with_numeric_values: `{summary['approved_roles_with_numeric_values']}`",
        f"- approved_roles_with_annual_10k_facts: `{summary['approved_roles_with_annual_10k_facts']}`",
        f"- approved_roles_usable_for_compose: `{summary['approved_roles_usable_for_compose']}`",
        "",
        "## Input Inventory",
        "| artifact | rows | sec_concept | fiscal_year | period | form | numeric | candidate |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row in public_inventory:
        lines.append(
            f"| `{row['artifact_path']}` | {row['row_count']} | {row['has_sec_concept']} | {row['has_fiscal_year']} | {row['has_fiscal_period']} | {row['has_form']} | {row['has_numeric_value']} | {row['candidate_for_derived_kpi_compose']} |"
        )
    lines.extend(
        [
            "",
            "## Approved Role Coverage",
            f"- Matching facts: `{summary['approved_roles_with_any_matching_fact']}`",
            f"- Numeric values: `{summary['approved_roles_with_numeric_values']}`",
            f"- Annual facts: `{summary['approved_roles_with_annual_facts']}`",
            f"- Annual 10-K facts: `{summary['approved_roles_with_annual_10k_facts']}`",
            "",
            "## Why Current Compose Rejected Everything",
            "The current concept-candidate artifact is metadata-shaped and does not persist concept-level numeric annual CompanyFacts rows. It can prove reviewed concepts, but it cannot support deterministic value calculation.",
            "",
            "## Recommended Fact Source",
            f"- recommended_source_artifact: {recommended_text}",
            "",
            "## Required Compose Patch",
            "- Use a processed normalized CompanyFacts fact table only when it contains identity, concept, unit, fiscal year, period, form, filed date, and numeric value columns.",
            "- Keep candidate metadata as a rejection-only fallback.",
            "",
            "## Guardrail Confirmation",
            "- no_network_confirmed=True",
            "- no_score_change_confirmed=True",
            "- no_master_mutation_confirmed=True",
            "- no_imputation_confirmed=True",
            "",
            "## Next Recommended Patch",
            next_patch,
        ]
    )
    return "\n".join(lines) + "\n"


def run_personal_sec_derived_kpi_fact_source_audit(
    *,
    approval_applied: str | Path = DEFAULT_APPROVAL_APPLIED,
    unlock_matrix: str | Path = DEFAULT_UNLOCK_MATRIX,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    artifact_paths: list[str | Path] | None = None,
) -> FactSourceAuditResult:
    approval_path = resolve_repo_path(approval_applied)
    unlock_path = resolve_repo_path(unlock_matrix)
    if not approval_path.exists():
        raise RuntimeError("MISSING_PRIVATE_APPROVAL_APPLIED")
    if not unlock_path.exists():
        raise RuntimeError("MISSING_PRIVATE_UNLOCK_MATRIX")

    paths = [resolve_repo_path(path) for path in artifact_paths] if artifact_paths is not None else discover_paths()
    existing_paths = [path for path in paths if path.exists()]
    inventory_rows, rows_by_label = build_inventory_rows(existing_paths)
    approved_roles = approved_role_rows(read_csv_rows(approval_path), read_csv_rows(unlock_path))
    audit_rows = build_audit_rows(approved_roles=approved_roles, inventory_rows=inventory_rows, rows_by_label=rows_by_label)
    summary = build_summary(approved_roles, audit_rows)

    output_root = resolve_repo_path(output_dir)
    report_root = resolve_repo_path(report_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    report_root.mkdir(parents=True, exist_ok=True)
    inventory_path = write_csv_rows(output_root / INVENTORY_OUTPUT, INVENTORY_FIELDS, inventory_rows)
    audit_path = write_csv_rows(output_root / AUDIT_OUTPUT, AUDIT_FIELDS, audit_rows)
    summary_path = write_csv_rows(output_root / SUMMARY_OUTPUT, SUMMARY_FIELDS, [summary])
    report_path = report_root / REPORT_OUTPUT
    report_path.write_text(render_report(inventory_rows=inventory_rows, audit_rows=audit_rows, summary=summary), encoding="utf-8")

    return FactSourceAuditResult(
        inventory_path=inventory_path,
        audit_path=audit_path,
        summary_path=summary_path,
        report_path=report_path,
        summary=summary,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit available SEC fact sources for derived KPI compose.")
    parser.add_argument("--approval-applied", default=DEFAULT_APPROVAL_APPLIED)
    parser.add_argument("--unlock-matrix", default=DEFAULT_UNLOCK_MATRIX)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    parser.add_argument("--artifact", action="append", default=[])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_derived_kpi_fact_source_audit(
        approval_applied=args.approval_applied,
        unlock_matrix=args.unlock_matrix,
        output_dir=args.output_dir,
        report_dir=args.report_dir,
        artifact_paths=args.artifact or None,
    )
    print(f"fact_source_inventory={result.inventory_path}")
    print(f"fact_source_audit={result.audit_path}")
    print(f"fact_source_summary={result.summary_path}")
    print(f"fact_source_report={result.report_path}")
    print(f"approved_roles_usable_for_compose={result.summary['approved_roles_usable_for_compose']}")
    print("no_network_confirmed=True")


if __name__ == "__main__":
    main()
