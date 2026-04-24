from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, read_csv_rows, require_columns, safe_upper, to_bool, write_csv_rows
from src.fundamentals_master import (
    CORE_KPI_FIELDS,
    COVERAGE_OUTPUT_FIELDS,
    DEFAULT_COVERAGE_OUTPUT,
    DEFAULT_PERSONAL_MASTER_PATH,
    DEFAULT_RESEARCH_PRIORITY_OUTPUT,
    PERSONAL_MASTER_FIELDS,
    compute_kpi_coverage,
    count_present_core_kpis,
    derive_fundamentals_data_quality,
    has_company_type_profile_reason,
    join_list,
    load_metric_definitions,
    validate_personal_fundamentals_master,
)
from src.fundamentals_profile_engine import PROFILE_REVIEW_INPUT_FIELDS

DEFAULT_FETCH_REGISTRY_INPUT = "data/processed/external_sec_fetch_registry.csv"
DEFAULT_PROPOSED_UPDATES_INPUT = "data/processed/personal_fundamentals_proposed_updates.csv"
DEFAULT_PROFILE_REVIEW_INPUT = "data/raw/personal_fundamentals_profile_review.csv"
DEFAULT_MASTER_INPUT = "data/processed/personal_fundamentals_master_evidence_identity_applied.csv"
DEFAULT_DIAGNOSTICS_OUTPUT = "data/processed/personal_fundamentals_gap_diagnostics.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_fundamentals_gap_summary.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_fundamentals_gap_diagnostics.md"

DIAGNOSTIC_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "asset_type",
    "country",
    "company_type_profile",
    "current_data_quality_flag",
    "has_sec_identity_flag",
    "sec_fetch_status",
    "sec_kpi_fields_present_count",
    "sec_kpi_fields_present",
    "core_kpi_fields_present_count",
    "missing_required_kpis_under_current_profile",
    "profile_review_status",
    "profile_gap_flag",
    "profile_gap_reason",
    "quality_gap_type",
    "quality_gap_reason",
    "recommended_next_action",
]

SUMMARY_FIELDS = ["summary_metric", "summary_value", "notes"]
MARKET_DATA_GAP_KPIS = {"drawdown_from_high_pct", "expected_return_pct"}
MINIMAL_COVERAGE_FIELDS = ["ticker", "isin", "data_quality_flag"]


def read_csv_rows_with_header(path_value: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    path = Path(path_value)
    resolved = path if path.is_absolute() else Path(__file__).resolve().parent.parent / path
    with resolved.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def require_header_columns(fieldnames: list[str], required_columns: list[str], source_name: str) -> None:
    available = set(fieldnames)
    missing = [field for field in required_columns if field not in available]
    if missing:
        raise ValueError(f"{source_name} missing required columns: {', '.join(sorted(missing))}")


def identity_key(row: dict[str, Any]) -> tuple[str, str]:
    return (
        str(row.get("isin", "") or "").strip().upper(),
        canonicalize_ticker(row.get("ticker", "")),
    )


def lookup_key_candidates(row: dict[str, Any]) -> list[tuple[str, str]]:
    isin, ticker = identity_key(row)
    keys = []
    if isin or ticker:
        keys.append((isin, ticker))
    if isin:
        keys.append((isin, ""))
    if ticker:
        keys.append(("", ticker))
    return keys


def build_single_row_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        isin, ticker = identity_key(row)
        if isin or ticker:
            lookup.setdefault((isin, ticker), row)
            if isin:
                lookup.setdefault((isin, ""), row)
            if ticker:
                lookup.setdefault(("", ticker), row)
    return lookup


def lookup_identity_row(row: dict[str, Any], lookup: dict[tuple[str, str], dict[str, str]]) -> dict[str, str]:
    for key in lookup_key_candidates(row):
        matched = lookup.get(key)
        if matched:
            return matched
    return {}


def build_fetch_registry_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    require_columns(rows, ["ticker", "isin", "fetch_status"], "external sec fetch registry")
    return build_single_row_lookup(rows)


def build_sec_kpi_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[str]]:
    require_columns(rows, ["ticker", "isin", "kpi_name"], "personal fundamentals proposed updates")
    grouped: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        key = identity_key(row)
        kpi_name = str(row.get("kpi_name", "") or "").strip()
        if not key[0] and not key[1]:
            continue
        if kpi_name:
            grouped.setdefault(key, set()).add(kpi_name)

    lookup: dict[tuple[str, str], set[str]] = {}
    for (isin, ticker), kpi_names in grouped.items():
        aliases = [(isin, ticker)]
        if isin:
            aliases.append((isin, ""))
        if ticker:
            aliases.append(("", ticker))
        for alias in aliases:
            lookup.setdefault(alias, set()).update(kpi_names)
    return {key: sorted(values) for key, values in lookup.items()}


def lookup_sec_kpi_fields(row: dict[str, Any], sec_kpi_lookup: dict[tuple[str, str], list[str]]) -> list[str]:
    for key in lookup_key_candidates(row):
        matched = sec_kpi_lookup.get(key)
        if matched:
            return matched
    return []


def build_profile_review_status_lookup(
    profile_review_input_path: str,
) -> tuple[dict[tuple[str, str], str], str]:
    fieldnames, review_rows = read_csv_rows_with_header(profile_review_input_path)
    require_header_columns(fieldnames, PROFILE_REVIEW_INPUT_FIELDS, f"personal fundamentals profile review ({profile_review_input_path})")
    if not review_rows:
        return {}, "PROFILE_REVIEW_INPUT_EMPTY"

    status_priority = {"REJECTED": 0, "PENDING": 1, "APPROVED": 2}
    latest_rows: dict[tuple[str, str], dict[str, str]] = {}
    for row in review_rows:
        key = identity_key(row)
        if not key[0] and not key[1]:
            continue
        current = latest_rows.get(key)
        row_status = safe_upper(row.get("review_status"))
        row_key = (
            str(row.get("review_as_of_date", "") or "").strip(),
            status_priority.get(row_status, -1),
            str(row.get("review_author", "") or "").strip(),
        )
        if current is None:
            latest_rows[key] = row
            continue
        current_key = (
            str(current.get("review_as_of_date", "") or "").strip(),
            status_priority.get(safe_upper(current.get("review_status")), -1),
            str(current.get("review_author", "") or "").strip(),
        )
        if row_key >= current_key:
            latest_rows[key] = row
    return {key: safe_upper(row.get("review_status")) or "NOT_REVIEWED" for key, row in latest_rows.items()}, "POPULATED"


def detect_sec_identity(master_row: dict[str, str], fetch_row: dict[str, str]) -> bool:
    if fetch_row:
        return True
    notes = str(master_row.get("notes", "") or "").lower()
    return "sec_identity_apply_cik=" in notes


def classify_quality_gap(
    *,
    master_row: dict[str, str],
    coverage_row: dict[str, str],
    has_sec_identity: bool,
    sec_fetch_status: str,
    sec_kpi_fields: list[str],
    profile_review_status: str,
    profile_gap_flag: bool,
    profile_gap_reason: str,
    derived_quality_flag: str,
    derived_quality_reason: str,
    kpi_coverage: dict[str, list[str]],
) -> tuple[str, str, str]:
    asset_type = safe_upper(master_row.get("asset_type"))
    country = safe_upper(master_row.get("country"))
    profile = safe_upper(master_row.get("company_type_profile"))
    current_quality = safe_upper(coverage_row.get("data_quality_flag") or master_row.get("data_quality_flag"))
    sec_kpi_count = len(sec_kpi_fields)
    missing_required = kpi_coverage["missing_required"]
    optional_missing = set(kpi_coverage["optional_missing"])

    if asset_type == "ETF":
        return (
            "ETF_OR_NON_COMPANY_FUNDAMENTALS",
            "ETF holdings stay outside the current SEC company-facts profile path.",
            "Use ETF-specific or market-data workflows; do not force SEC company KPI expectations.",
        )

    if asset_type != "STOCK":
        return (
            "ETF_OR_NON_COMPANY_FUNDAMENTALS",
            f"asset_type={asset_type or '<blank>'} is outside the current SEC company KPI path.",
            "Review via the non-company fundamentals workflow; do not infer company KPI coverage.",
        )

    if country not in {"US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"} and not has_sec_identity:
        return (
            "NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE",
            f"country={country or '<blank>'} and no reviewed SEC identity is available under the current US STOCK scope.",
            "Keep the holding outside the current SEC scope or extend coverage in a separate non-US workflow.",
        )

    if profile_gap_flag:
        gap_reason = profile_gap_reason
        if profile_review_status == "PROFILE_REVIEW_INPUT_EMPTY":
            gap_reason = f"{gap_reason}; data/raw/personal_fundamentals_profile_review.csv is still header-only."
        return (
            "PROFILE_REVIEW_MISSING",
            gap_reason,
            "Manually review company_type_profile and then rerun fundamentals_profile_engine on the evidence+identity-applied master.",
        )

    if profile in {"STANDARD", "FINANCIAL", "REIT"} and missing_required:
        if sec_kpi_count > 0:
            if len(missing_required) == len(kpi_coverage["required"]):
                return (
                    "SEC_KPI_MISSING",
                    f"SEC evidence exists but none of the required KPIs for profile {profile} are currently present: {join_list(missing_required)}",
                    "Keep SEC evidence applied, but close the remaining KPI gap in a separate evidence or market-data workflow.",
                )
            return (
                "SEC_KPI_PARTIAL",
                f"SEC evidence partially covers profile {profile}; missing required KPIs: {join_list(missing_required)}",
                "Complete the remaining required KPI set before expecting full coverage or OK quality.",
            )
        return (
            "SEC_KPI_MISSING",
            f"No SEC KPI values are available for the required KPI set under profile {profile}: {join_list(missing_required)}",
            "Use explicit non-SEC evidence for the missing required KPIs or leave the holding in REVIEW/MISSING_DATA.",
        )

    if not missing_required and optional_missing.intersection(MARKET_DATA_GAP_KPIS):
        return (
            "MARKET_DATA_REQUIRED_NOT_SEC",
            f"Remaining valuation or market-data gaps are outside the current SEC facts path: {join_list(sorted(optional_missing.intersection(MARKET_DATA_GAP_KPIS)))}",
            "Source market-data or valuation inputs separately; do not expect SEC CompanyFacts to fill them.",
        )

    if has_sec_identity and sec_fetch_status == "FETCHED" and sec_kpi_count > 0 and current_quality != derived_quality_flag:
        return (
            "SEC_EVIDENCE_AVAILABLE_NOT_DOWNSTREAM_READY",
            f"SEC KPI evidence is present ({sec_kpi_count} field(s)), but current coverage quality still reflects the older source flag {current_quality}; derived quality is {derived_quality_flag}.",
            "Rerun coverage/scoring/watchlist/monthly/portfolio_review with the selected evidence+identity or profiled master.",
        )

    if derived_quality_flag == "OK":
        return ("COVERED", derived_quality_reason, "No immediate fundamentals gap remains under the current profile.")

    if has_sec_identity and sec_fetch_status == "FETCHED" and sec_kpi_count == 0:
        return (
            "SEC_KPI_MISSING",
            "SEC identity exists and the fetch succeeded, but no supported KPI field reached the current evidence-apply path.",
            "Treat this as a separate SEC KPI extraction gap; do not mark quality OK.",
        )

    return ("REVIEW_REQUIRED", derived_quality_reason, "Inspect coverage, profile and market-data gaps before changing downstream expectations.")


def diagnostic_sort_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        str(row.get("quality_gap_type", "") or ""),
        str(row.get("isin", "") or ""),
        str(row.get("ticker", "") or ""),
    )


def build_gap_diagnostics_rows(
    master_rows: list[dict[str, str]],
    coverage_rows: list[dict[str, str]],
    fetch_registry_rows: list[dict[str, str]],
    proposed_update_rows: list[dict[str, str]],
    profile_review_statuses: dict[tuple[str, str], str],
    profile_review_input_status: str,
) -> list[dict[str, str]]:
    coverage_lookup = build_single_row_lookup(coverage_rows)
    fetch_lookup = build_fetch_registry_lookup(fetch_registry_rows) if fetch_registry_rows else {}
    sec_kpi_lookup = build_sec_kpi_lookup(proposed_update_rows) if proposed_update_rows else {}
    definitions = load_metric_definitions()
    diagnostics: list[dict[str, str]] = []

    for master_row in master_rows:
        coverage_row = lookup_identity_row(master_row, coverage_lookup)
        fetch_row = lookup_identity_row(master_row, fetch_lookup)
        key = identity_key(master_row)
        sec_kpi_fields = lookup_sec_kpi_fields(master_row, sec_kpi_lookup)
        profile = safe_upper(master_row.get("company_type_profile")) or "OTHER"
        kpi_coverage = compute_kpi_coverage(master_row, profile, definitions)
        derived_quality_flag, derived_quality_reason = derive_fundamentals_data_quality(master_row, profile, definitions)
        has_sec_identity = detect_sec_identity(master_row, fetch_row)
        sec_fetch_status = safe_upper(fetch_row.get("fetch_status")) or "NOT_AVAILABLE"
        profile_review_status = profile_review_statuses.get(key, "NOT_REVIEWED")
        if profile_review_input_status == "PROFILE_REVIEW_INPUT_EMPTY":
            profile_review_status = "PROFILE_REVIEW_INPUT_EMPTY"
        asset_type = safe_upper(master_row.get("asset_type"))
        profile_gap_flag = asset_type == "STOCK" and profile == "OTHER" and not has_company_type_profile_reason(master_row)
        profile_gap_reason = ""
        if profile_gap_flag:
            profile_gap_reason = "asset_type=STOCK with company_type_profile=OTHER and no explicit profile reason in notes or optional field"
        gap_type, gap_reason, next_action = classify_quality_gap(
            master_row=master_row,
            coverage_row=coverage_row or {},
            has_sec_identity=has_sec_identity,
            sec_fetch_status=sec_fetch_status,
            sec_kpi_fields=sec_kpi_fields,
            profile_review_status=profile_review_status,
            profile_gap_flag=profile_gap_flag,
            profile_gap_reason=profile_gap_reason,
            derived_quality_flag=derived_quality_flag,
            derived_quality_reason=derived_quality_reason,
            kpi_coverage=kpi_coverage,
        )
        diagnostics.append(
            {
                "ticker": canonicalize_ticker(master_row.get("ticker", "")),
                "isin": str(master_row.get("isin", "") or "").strip().upper(),
                "company_name": str(master_row.get("company_name", "") or "").strip(),
                "asset_type": str(master_row.get("asset_type", "") or "").strip(),
                "country": str(master_row.get("country", "") or "").strip(),
                "company_type_profile": profile,
                "current_data_quality_flag": safe_upper((coverage_row or {}).get("data_quality_flag") or master_row.get("data_quality_flag")) or "MISSING_DATA",
                "has_sec_identity_flag": str(has_sec_identity),
                "sec_fetch_status": sec_fetch_status,
                "sec_kpi_fields_present_count": str(len(sec_kpi_fields)),
                "sec_kpi_fields_present": join_list(sec_kpi_fields),
                "core_kpi_fields_present_count": str(count_present_core_kpis(master_row)),
                "missing_required_kpis_under_current_profile": join_list(kpi_coverage["missing_required"]),
                "profile_review_status": profile_review_status,
                "profile_gap_flag": str(profile_gap_flag),
                "profile_gap_reason": profile_gap_reason,
                "quality_gap_type": gap_type,
                "quality_gap_reason": gap_reason,
                "recommended_next_action": next_action,
            }
        )

    diagnostics.sort(key=diagnostic_sort_key)
    return diagnostics


def build_gap_summary_rows(
    diagnostics_rows: list[dict[str, str]],
    *,
    profile_review_input_status: str,
    fetch_registry_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    gap_counts = Counter(str(row.get("quality_gap_type", "") or "") for row in diagnostics_rows)
    profile_counts = Counter(str(row.get("profile_review_status", "") or "") for row in diagnostics_rows)
    summary_rows = [
        {
            "summary_metric": "master_rows_total",
            "summary_value": str(len(diagnostics_rows)),
            "notes": "Rows in diagnostics output.",
        },
        {
            "summary_metric": "profile_review_input_status",
            "summary_value": profile_review_input_status,
            "notes": "PROFILE_REVIEW_INPUT_EMPTY means the canonical raw profile review file is header-only.",
        },
        {
            "summary_metric": "sec_fetch_identity_rows_total",
            "summary_value": str(len(fetch_registry_rows)),
            "notes": "Rows from external_sec_fetch_registry.csv.",
        },
    ]
    for key in sorted(gap_counts):
        summary_rows.append(
            {
                "summary_metric": f"quality_gap_type__{key}",
                "summary_value": str(gap_counts[key]),
                "notes": "Count of diagnostics rows with this quality_gap_type.",
            }
        )
    for key in sorted(profile_counts):
        summary_rows.append(
            {
                "summary_metric": f"profile_review_status__{key}",
                "summary_value": str(profile_counts[key]),
                "notes": "Count of diagnostics rows with this profile_review_status.",
            }
        )
    return summary_rows


def write_gap_report(path_value: str, diagnostics_rows: list[dict[str, str]], summary_rows: list[dict[str, str]]) -> Path:
    lines = [
        "# Personal Fundamentals Gap Diagnostics",
        "",
        "## Summary",
        "",
    ]
    for row in summary_rows:
        lines.append(f"- `{row['summary_metric']}` = {row['summary_value']} ({row['notes']})")
    lines.extend(["", "## Diagnostics", ""])
    for row in diagnostics_rows:
        lines.append(
            f"- `{row['ticker'] or row['isin']}` {row['company_name']}: "
            f"{row['quality_gap_type']} | profile={row['company_type_profile']} | "
            f"sec_fetch={row['sec_fetch_status']} | sec_kpis={row['sec_kpi_fields_present_count']} | "
            f"next={row['recommended_next_action']}"
        )
    report_path = Path(path_value)
    resolved = report_path if report_path.is_absolute() else Path(__file__).resolve().parent.parent / report_path
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return resolved


def run_fundamentals_gap_diagnostics(
    *,
    master_input: str = DEFAULT_MASTER_INPUT,
    coverage_input: str = DEFAULT_COVERAGE_OUTPUT,
    fetch_registry_input: str = DEFAULT_FETCH_REGISTRY_INPUT,
    proposed_updates_input: str = DEFAULT_PROPOSED_UPDATES_INPUT,
    profile_review_input: str = DEFAULT_PROFILE_REVIEW_INPUT,
    diagnostics_output: str = DEFAULT_DIAGNOSTICS_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str | None = None,
) -> dict[str, Path]:
    master_rows = read_csv_rows(master_input)
    validate_personal_fundamentals_master(master_rows, f"personal fundamentals master ({master_input})")
    coverage_rows = read_csv_rows(coverage_input)
    if coverage_rows:
        require_columns(coverage_rows, MINIMAL_COVERAGE_FIELDS, f"personal fundamentals coverage ({coverage_input})")
    fetch_registry_rows = read_csv_rows(fetch_registry_input)
    proposed_update_rows = read_csv_rows(proposed_updates_input)
    profile_review_statuses, profile_review_input_status = build_profile_review_status_lookup(profile_review_input)

    diagnostics_rows = build_gap_diagnostics_rows(
        master_rows,
        coverage_rows,
        fetch_registry_rows,
        proposed_update_rows,
        profile_review_statuses,
        profile_review_input_status,
    )
    summary_rows = build_gap_summary_rows(
        diagnostics_rows,
        profile_review_input_status=profile_review_input_status,
        fetch_registry_rows=fetch_registry_rows,
    )

    outputs = {
        "gap_diagnostics": write_csv_rows(diagnostics_output, DIAGNOSTIC_FIELDS, diagnostics_rows),
        "gap_summary": write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows),
    }
    if report_output:
        outputs["gap_report"] = write_gap_report(report_output, diagnostics_rows, summary_rows)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose remaining personal fundamentals data gaps without mutating raw or processed masters.")
    parser.add_argument("--master-input", default=DEFAULT_MASTER_INPUT, help="Evidence+identity-applied or profiled personal fundamentals master CSV.")
    parser.add_argument("--coverage-input", default=DEFAULT_COVERAGE_OUTPUT, help="Current personal fundamentals coverage CSV.")
    parser.add_argument("--fetch-registry-input", default=DEFAULT_FETCH_REGISTRY_INPUT, help="SEC fetch registry CSV.")
    parser.add_argument("--proposed-updates-input", default=DEFAULT_PROPOSED_UPDATES_INPUT, help="Evidence apply proposed updates CSV.")
    parser.add_argument("--profile-review-input", default=DEFAULT_PROFILE_REVIEW_INPUT, help="Canonical manual profile review CSV.")
    parser.add_argument("--diagnostics-output", default=DEFAULT_DIAGNOSTICS_OUTPUT, help="Gap diagnostics CSV output.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT, help="Gap summary CSV output.")
    parser.add_argument("--report-output", default="", help="Optional Markdown report output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_fundamentals_gap_diagnostics(
        master_input=args.master_input,
        coverage_input=args.coverage_input,
        fetch_registry_input=args.fetch_registry_input,
        proposed_updates_input=args.proposed_updates_input,
        profile_review_input=args.profile_review_input,
        diagnostics_output=args.diagnostics_output,
        summary_output=args.summary_output,
        report_output=args.report_output or None,
    )


if __name__ == "__main__":
    main()
