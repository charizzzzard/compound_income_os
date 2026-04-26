from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import normalize_number_text, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_KPI_TIER_INPUT = "data/processed/personal_kpi_tier_coverage.csv"
DEFAULT_SCORES_INPUT = "data/processed/personal_company_scores.csv"
DEFAULT_EVIDENCE_REGISTRY_INPUT = "data/processed/personal_fundamentals_evidence_registry.csv"
DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT = "data/processed/personal_fundamentals_master_evidence_applied.csv"
DEFAULT_SEC_SCOPE_REVIEW_INPUT = "data/processed/personal_sec_scope_review.csv"
DEFAULT_SEC_IDENTITY_APPLY_INPUT = "data/processed/personal_sec_identity_apply_changes.csv"
DEFAULT_METRIC_DEFINITIONS_INPUT = "configs/fundamentals_metric_definitions.yaml"
DEFAULT_REVIEW_INPUT = "data/raw/private/fundamentals/personal_dividend_fcf_review_input.csv"
DEFAULT_QUEUE_OUTPUT = "data/processed/personal_dividend_fcf_input_review_queue.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_dividend_fcf_input_contract_summary.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_dividend_fcf_input_contract_report.md"

DEFAULT_DIVIDEND_FCF_KPIS = ("fcf_margin", "fcf_per_share_cagr_5y", "payout_ratio_fcf")
REVIEW_STATUSES = {"APPROVED", "REVIEW", "REJECTED", "MISSING"}
SOURCE_TYPES = {"MANUAL_REVIEW", "EVIDENCE_FILE", "PUBLIC_FILINGS", "SEC_COMPANYFACTS", "OTHER", "UNKNOWN"}
SUMMARY_FIELDS = ["metric", "value", "notes"]
QUEUE_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "missing_dividend_fcf_kpis",
    "missing_dividend_fcf_kpi_count",
    "covered_dividend_fcf_kpis",
    "covered_dividend_fcf_kpi_count",
    "required_dividend_fcf_kpi_count",
    "fcf_margin",
    "payout_ratio_fcf",
    "fcf_per_share_cagr_5y",
    "dividend_fcf_review_status",
    "dividend_fcf_source_type",
    "dividend_fcf_source_name",
    "dividend_fcf_source_reference",
    "dividend_fcf_source_as_of_date",
    "dividend_fcf_reviewed_by",
    "dividend_fcf_reviewed_at",
    "dividend_fcf_notes",
    "dividend_fcf_input_status",
    "sec_scope_status",
    "evidence_registry_status",
    "evidence_applied_status",
    "recommended_closure_path",
    "next_review_action",
    "reason_code",
]
REVIEW_INPUT_REQUIRED_FIELDS = [
    "ticker",
    "isin",
    "fcf_margin",
    "payout_ratio_fcf",
    "fcf_per_share_cagr_5y",
    "dividend_fcf_review_status",
    "dividend_fcf_source_type",
    "dividend_fcf_source_reference",
    "dividend_fcf_source_as_of_date",
]


@dataclass(frozen=True)
class DividendFcfInputContractResult:
    queue_output: Path
    summary_output: Path
    report_output: Path
    queue_rows: list[dict[str, str]]
    summary_rows: list[dict[str, str]]
    warnings: tuple[str, ...]


def safe_display_path(path_value: str) -> str:
    normalized = str(path_value).replace("\\", "/")
    if "data/raw/private" in normalized:
        return "<private_path>"
    return path_value


def optional_csv_rows(path_value: str, label: str) -> tuple[list[dict[str, str]], list[str], bool]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], [f"missing_input={label}:{safe_display_path(path_value)}"], False
    return read_csv_rows(path), [], True


def bool_text(value: bool) -> str:
    return "True" if value else "False"


def joined(items: set[str] | list[str] | tuple[str, ...]) -> str:
    return ";".join(sorted(item for item in items if item))


def split_list(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").replace(",", ";").split(";") if item.strip()]


def parse_decimal(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(normalize_number_text(text.replace("%", "")))
    except ValueError:
        return None


def is_missing(value: Any) -> bool:
    return str(value or "").strip() == ""


def identity_keys(row: dict[str, str]) -> tuple[tuple[str, str], ...]:
    isin = str(row.get("isin", "") or row.get("original_isin", "") or "").strip().upper()
    ticker = str(row.get("ticker", "") or row.get("original_ticker", "") or row.get("current_ticker", "") or "").strip().upper()
    keys: list[tuple[str, str]] = []
    if isin:
        keys.append(("isin", isin))
    if ticker and not isin:
        keys.append(("ticker", ticker))
    return tuple(keys)


def row_key(row: dict[str, str]) -> tuple[str, str]:
    isin = str(row.get("isin", "") or "").strip().upper()
    ticker = str(row.get("ticker", "") or "").strip().upper()
    return isin, ticker


def has_value(row: dict[str, str], field: str) -> bool:
    return str(row.get(field, "") or "").strip() != ""


def load_dividend_fcf_kpis(path_value: str, warnings: list[str]) -> tuple[str, tuple[str, ...]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        warnings.append(f"missing_input=metric_definitions:{safe_display_path(path_value)}")
        return "REVIEW", DEFAULT_DIVIDEND_FCF_KPIS
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    kpis = data.get("kpis") if isinstance(data.get("kpis"), dict) else {}
    dividend_fcf = tuple(sorted(name for name, spec in kpis.items() if isinstance(spec, dict) and spec.get("kpi_tier") == "DIVIDEND_FCF_REQUIRED"))
    if not dividend_fcf:
        warnings.append("dividend_fcf_kpi_contract_unknown=metric_definitions")
        return "REVIEW", DEFAULT_DIVIDEND_FCF_KPIS
    return "OK", dividend_fcf


def build_index(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    index: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        for key in identity_keys(row):
            index.setdefault(key, row)
    return index


def find_index_row(index: dict[tuple[str, str], dict[str, str]], row: dict[str, str]) -> dict[str, str] | None:
    for key in identity_keys(row):
        if key in index:
            return index[key]
    return None


def build_evidence_index(rows: list[dict[str, str]]) -> dict[tuple[str, str], set[str]]:
    index: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        kpi = str(row.get("kpi_name", "") or "").strip()
        if not kpi:
            continue
        for key in identity_keys(row):
            index.setdefault(key, set()).add(kpi)
    return index


def build_review_index(review_rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str], dict[str, str]], set[tuple[str, str]]]:
    index: dict[tuple[str, str], dict[str, str]] = {}
    duplicates: set[tuple[str, str]] = set()
    for row in review_rows:
        isin, ticker = row_key(row)
        key = (isin, ticker if not isin else "")
        if not isin and not ticker:
            continue
        if key in index:
            duplicates.add(key)
        else:
            index[key] = row
    return index, duplicates


def find_review_row(index: dict[tuple[str, str], dict[str, str]], row: dict[str, str]) -> dict[str, str] | None:
    isin, ticker = row_key(row)
    if isin and (isin, "") in index:
        return index[(isin, "")]
    if not isin and ticker and ("", ticker) in index:
        return index[("", ticker)]
    return None


def build_sec_identity_keys(scope_rows: list[dict[str, str]], identity_rows: list[dict[str, str]]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for row in scope_rows:
        enabled = safe_upper(row.get("reviewed_enabled", ""))
        cik = str(row.get("reviewed_cik", "") or "").strip()
        if enabled in {"TRUE", "YES", "1"} or cik:
            keys.update(identity_keys(row))
    for row in identity_rows:
        cik = str(row.get("reviewed_cik", "") or "").strip()
        if cik:
            keys.update(identity_keys(row))
    return keys


def classify_sec_status(row: dict[str, str], sec_keys: set[tuple[str, str]], sec_artifacts_present: bool) -> str:
    if any(key in sec_keys for key in identity_keys(row)):
        return "SEC_ELIGIBLE"
    if not sec_artifacts_present:
        return "UNKNOWN"
    return "SEC_IDENTITY_MISSING"


def classify_registry_status(row: dict[str, str], missing_kpis: list[str], evidence_index: dict[tuple[str, str], set[str]], registry_present: bool) -> str:
    if not registry_present:
        return "UNKNOWN"
    evidence_kpis: set[str] = set()
    for key in identity_keys(row):
        evidence_kpis.update(evidence_index.get(key, set()))
    hits = set(missing_kpis).intersection(evidence_kpis)
    if hits and len(hits) == len(missing_kpis):
        return "HAS_EVIDENCE"
    if hits:
        return "PARTIAL_EVIDENCE"
    return "NO_EVIDENCE"


def classify_applied_status(row: dict[str, str], missing_kpis: list[str], master_index: dict[tuple[str, str], dict[str, str]], master_present: bool) -> str:
    if not master_present:
        return "UNKNOWN"
    master_row = find_index_row(master_index, row)
    if master_row is None:
        return "NO_APPLIED_VALUE"
    hits = [kpi for kpi in missing_kpis if has_value(master_row, kpi)]
    if hits and len(hits) == len(missing_kpis):
        return "HAS_APPLIED_VALUE"
    if hits:
        return "PARTIAL_APPLIED_VALUE"
    return "NO_APPLIED_VALUE"


def validate_review_row(review_row: dict[str, str] | None, *, input_exists: bool, schema_valid: bool, required_kpis: tuple[str, ...]) -> tuple[str, set[str]]:
    reasons = {"NO_IMPUTATION"}
    if not input_exists:
        reasons.update({"INPUT_FILE_MISSING", "DIVIDEND_FCF_REQUIRED_MISSING"})
        return "MISSING", reasons
    if not schema_valid:
        reasons.add("INPUT_SCHEMA_INVALID")
        return "INVALID", reasons
    if review_row is None:
        reasons.add("DIVIDEND_FCF_REQUIRED_MISSING")
        return "MISSING", reasons
    values = {field: parse_decimal(review_row.get(field, "")) for field in required_kpis}
    missing_values = [field for field, value in values.items() if value is None and is_missing(review_row.get(field, ""))]
    invalid_values = [field for field, value in values.items() if value is None and not is_missing(review_row.get(field, ""))]
    out_of_range = [field for field, value in values.items() if value is not None and not -100.0 <= value <= 300.0]
    if missing_values:
        reasons.add("DIVIDEND_FCF_REQUIRED_MISSING")
        return "MISSING", reasons
    if invalid_values:
        reasons.add("DIVIDEND_FCF_VALUE_INVALID")
        return "INVALID", reasons
    if out_of_range:
        reasons.add("DIVIDEND_FCF_VALUE_OUT_OF_RANGE")
        return "INVALID", reasons
    review_status = safe_upper(review_row.get("dividend_fcf_review_status", ""))
    source_type = safe_upper(review_row.get("dividend_fcf_source_type", "")) or "UNKNOWN"
    if review_status not in REVIEW_STATUSES or source_type not in SOURCE_TYPES or review_status != "APPROVED":
        reasons.add("DIVIDEND_FCF_REVIEW_PENDING")
        return "REVIEW", reasons
    if not str(review_row.get("dividend_fcf_source_reference", "") or "").strip():
        reasons.add("DIVIDEND_FCF_SOURCE_REFERENCE_MISSING")
        return "REVIEW", reasons
    if not str(review_row.get("dividend_fcf_source_as_of_date", "") or "").strip():
        reasons.add("DIVIDEND_FCF_SOURCE_DATE_MISSING")
        return "REVIEW", reasons
    reasons.discard("NO_IMPUTATION")
    reasons.add("DIVIDEND_FCF_APPROVED")
    return "OK", reasons


def classify_path(sec_status: str, registry_status: str, applied_status: str) -> tuple[str, set[str], str]:
    reasons = {"NO_IMPUTATION"}
    if applied_status in {"HAS_APPLIED_VALUE", "PARTIAL_APPLIED_VALUE"}:
        reasons.add("EVIDENCE_APPLIED_VALUE_MISSING")
        return "REVIEW_EXISTING_EVIDENCE", reasons, "Review existing applied values and rerun tier coverage if appropriate."
    if registry_status in {"HAS_EVIDENCE", "PARTIAL_EVIDENCE"}:
        reasons.add("EVIDENCE_APPLIED_VALUE_MISSING")
        return "REVIEW_EXISTING_EVIDENCE", reasons, "Review existing dividend/FCF evidence and stage reviewed updates."
    if sec_status == "SEC_ELIGIBLE":
        reasons.add("SEC_IDENTITY_AVAILABLE")
        return "SEC_EVIDENCE_POSSIBLE", reasons, "Run reviewed SEC evidence workflow or provide reviewed manual dividend/FCF inputs."
    if sec_status == "SEC_IDENTITY_MISSING":
        reasons.update({"SEC_IDENTITY_MISSING", "MANUAL_EVIDENCE_REQUIRED"})
        return "MANUAL_EVIDENCE_REQUIRED", reasons, "Add SEC identity review or provide reviewed manual dividend/FCF evidence."
    reasons.update({"EVIDENCE_REGISTRY_MISSING", "MANUAL_EVIDENCE_REQUIRED"})
    return "SOURCE_UNKNOWN", reasons, "Confirm source path, then add reviewed SEC or manual dividend/FCF evidence."


def affected_standard_rows(kpi_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = [
        row for row in kpi_rows
        if safe_upper(row.get("company_type_profile", "")) == "STANDARD"
        and (str(row.get("missing_dividend_fcf_kpis", "") or "").strip() or safe_upper(row.get("dividend_fcf_data_status", "")) in {"MISSING", "PARTIAL"})
    ]
    return sorted(rows, key=lambda row: (str(row.get("isin", "")), str(row.get("ticker", ""))))


def build_contract(
    *,
    kpi_rows: list[dict[str, str]],
    evidence_rows: list[dict[str, str]],
    applied_rows: list[dict[str, str]],
    sec_scope_rows: list[dict[str, str]],
    sec_identity_rows: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    review_input_exists: bool,
    review_input_path: str,
    required_kpis: tuple[str, ...],
    contract_status: str,
    registry_present: bool,
    applied_present: bool,
    sec_artifacts_present: bool,
    warnings: list[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    review_fields = set(review_rows[0].keys()) if review_rows else set()
    schema_valid = not review_input_exists or set(REVIEW_INPUT_REQUIRED_FIELDS).issubset(review_fields)
    if review_input_exists and not schema_valid:
        warnings.append("invalid_input_schema=dividend_fcf_review_input")
    review_index, duplicate_keys = build_review_index(review_rows) if schema_valid else ({}, set())
    if duplicate_keys:
        warnings.append("duplicate_review_identity=dividend_fcf_review_input")
    evidence_index = build_evidence_index(evidence_rows)
    applied_index = build_index(applied_rows)
    sec_keys = build_sec_identity_keys(sec_scope_rows, sec_identity_rows)
    queue_rows: list[dict[str, str]] = []
    reason_union: set[str] = set()
    status_counts: Counter[str] = Counter()
    path_counts: Counter[str] = Counter()
    affected_rows = affected_standard_rows(kpi_rows)
    for row in affected_rows:
        missing_kpis = [kpi for kpi in split_list(row.get("missing_dividend_fcf_kpis", "")) if kpi in required_kpis] or list(required_kpis)
        covered_kpis = [kpi for kpi in required_kpis if kpi not in missing_kpis]
        review_row = find_review_row(review_index, row) if not duplicate_keys else None
        input_status, input_reasons = validate_review_row(review_row, input_exists=review_input_exists, schema_valid=schema_valid and not duplicate_keys, required_kpis=required_kpis)
        sec_status = classify_sec_status(row, sec_keys, sec_artifacts_present)
        registry_status = classify_registry_status(row, missing_kpis, evidence_index, registry_present)
        applied_status = classify_applied_status(row, missing_kpis, applied_index, applied_present)
        closure_path, closure_reasons, next_action = classify_path(sec_status, registry_status, applied_status)
        reasons = set(input_reasons)
        reasons.update(closure_reasons)
        reasons.add("DIVIDEND_FCF_REQUIRED_MISSING")
        if contract_status != "OK":
            reasons.add("DIVIDEND_FCF_KPI_CONTRACT_UNKNOWN")
        reason_union.update(reasons)
        status_counts[input_status] += 1
        path_counts[closure_path] += 1
        queue_rows.append(
            {
                "ticker": row.get("ticker", ""),
                "isin": row.get("isin", ""),
                "company_name": row.get("company_name", ""),
                "company_type_profile": row.get("company_type_profile", ""),
                "missing_dividend_fcf_kpis": "; ".join(missing_kpis),
                "missing_dividend_fcf_kpi_count": str(len(missing_kpis)),
                "covered_dividend_fcf_kpis": "; ".join(covered_kpis),
                "covered_dividend_fcf_kpi_count": str(len(covered_kpis)),
                "required_dividend_fcf_kpi_count": str(len(required_kpis)),
                "fcf_margin": "",
                "payout_ratio_fcf": "",
                "fcf_per_share_cagr_5y": "",
                "dividend_fcf_review_status": safe_upper(review_row.get("dividend_fcf_review_status", "")) if review_row else "",
                "dividend_fcf_source_type": safe_upper(review_row.get("dividend_fcf_source_type", "")) if review_row else "",
                "dividend_fcf_source_name": "",
                "dividend_fcf_source_reference": "",
                "dividend_fcf_source_as_of_date": "",
                "dividend_fcf_reviewed_by": "",
                "dividend_fcf_reviewed_at": "",
                "dividend_fcf_notes": "",
                "dividend_fcf_input_status": input_status,
                "sec_scope_status": sec_status,
                "evidence_registry_status": registry_status,
                "evidence_applied_status": applied_status,
                "recommended_closure_path": closure_path,
                "next_review_action": next_action,
                "reason_code": joined(reasons),
            }
        )
    non_standard_rows = [row for row in kpi_rows if safe_upper(row.get("company_type_profile", "")) and safe_upper(row.get("company_type_profile", "")) != "STANDARD"]
    if non_standard_rows:
        reason_union.add("PROFILE_NOT_STANDARD")
    summary_rows: list[dict[str, str]] = []

    def add_metric(metric: str, value: Any, notes: str) -> None:
        summary_rows.append({"metric": metric, "value": str(value), "notes": notes})

    input_status = "PRESENT" if review_input_exists else "MISSING"
    if review_input_exists and not schema_valid:
        input_status = "INVALID_SCHEMA"
    if duplicate_keys:
        input_status = "INVALID_DUPLICATE_IDENTITY"
        reason_union.add("INPUT_SCHEMA_INVALID")
    add_metric("dividend_fcf_contract_status", contract_status, "Dividend/FCF KPI contract status from metric definitions.")
    add_metric("required_kpis", "; ".join(required_kpis), "Dividend/FCF-required KPI fields.")
    add_metric("input_file_status", input_status, "Optional private reviewed dividend/FCF input status.")
    add_metric("review_input_path", safe_display_path(review_input_path), "Expected optional private reviewed dividend/FCF input.")
    add_metric("affected_standard_rows_count", len(affected_rows), "STANDARD rows missing dividend/FCF-required KPIs.")
    add_metric("queue_rows_count", len(queue_rows), "Rows in personal_dividend_fcf_input_review_queue.csv.")
    add_metric("approved_rows_count", status_counts.get("OK", 0), "Rows with approved, valid reviewed dividend/FCF input.")
    add_metric("review_rows_count", status_counts.get("REVIEW", 0), "Rows requiring dividend/FCF review/source metadata.")
    add_metric("missing_rows_count", status_counts.get("MISSING", 0), "Rows missing dividend/FCF input.")
    add_metric("invalid_rows_count", status_counts.get("INVALID", 0), "Rows with invalid dividend/FCF input.")
    add_metric("not_applicable_rows_count", len(non_standard_rows), "Non-STANDARD rows excluded from STANDARD dividend/FCF contract.")
    add_metric("sec_evidence_possible_count", path_counts.get("SEC_EVIDENCE_POSSIBLE", 0), "Rows where SEC evidence workflow may close missing dividend/FCF KPIs.")
    add_metric("manual_evidence_required_count", path_counts.get("MANUAL_EVIDENCE_REQUIRED", 0), "Rows requiring manual evidence or SEC identity review.")
    add_metric("review_existing_evidence_count", path_counts.get("REVIEW_EXISTING_EVIDENCE", 0), "Rows with existing evidence/applied signals requiring review.")
    add_metric("source_unknown_count", path_counts.get("SOURCE_UNKNOWN", 0), "Rows with unknown source path.")
    add_metric("reason_codes", joined(reason_union), "Union of dividend/FCF input contract reason codes.")
    add_metric("no_imputation_confirmed", "True", "Missing dividend/FCF values were not calculated or inferred.")
    add_metric("warnings_total", len(warnings), "Validation warnings.")
    return queue_rows, sorted(summary_rows, key=lambda row: row["metric"])


def render_report(summary_rows: list[dict[str, str]], queue_rows: list[dict[str, str]], input_paths: dict[str, str]) -> str:
    summary = {row["metric"]: row["value"] for row in summary_rows}
    reason_counts = Counter(reason for row in queue_rows for reason in str(row.get("reason_code", "")).split(";") if reason)
    lines = [
        "# Personal Dividend / FCF Input Contract Report",
        "",
        "## Executive Summary",
        f"- Affected STANDARD rows: {summary.get('affected_standard_rows_count', '0')}",
        f"- Queue rows: {summary.get('queue_rows_count', '0')}",
        f"- Approved rows: {summary.get('approved_rows_count', '0')}",
        f"- Missing rows: {summary.get('missing_rows_count', '0')}",
        f"- SEC evidence possible: {summary.get('sec_evidence_possible_count', '0')}",
        f"- No imputation confirmed: {summary.get('no_imputation_confirmed', 'True')}",
        "",
        "## Input Artifacts",
    ]
    for label, path_value in sorted(input_paths.items()):
        lines.append(f"- `{label}`: `{safe_display_path(path_value)}`")
    lines.extend(
        [
            "",
            "## Dividend / FCF Required KPI Contract",
            f"- Contract status: `{summary.get('dividend_fcf_contract_status', 'UNKNOWN')}`",
            f"- Required KPIs: `{summary.get('required_kpis', '')}`",
            "- Values are only valid when numeric, reviewed as `APPROVED`, and backed by source reference and source date.",
            "- Plausibility guardrail is technical only: numeric values must be between -100 and 300.",
            "",
            "## Affected STANDARD Rows",
            "| ticker | isin | company_name | missing_dividend_fcf_kpis | input_status | sec_scope_status | evidence_registry_status | evidence_applied_status | recommended_closure_path | reason_code |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in queue_rows:
        lines.append(
            f"| {row['ticker']} | {row['isin']} | {row['company_name']} | {row['missing_dividend_fcf_kpis']} | "
            f"{row['dividend_fcf_input_status']} | {row['sec_scope_status']} | {row['evidence_registry_status']} | "
            f"{row['evidence_applied_status']} | {row['recommended_closure_path']} | {row['reason_code']} |"
        )
    lines.extend(
        [
            "",
            "## Missing Dividend / FCF KPI Matrix",
        ]
    )
    for row in queue_rows:
        lines.append(f"- `{row['ticker']}`: missing `{row['missing_dividend_fcf_kpis']}`; covered `{row['covered_dividend_fcf_kpis']}`")
    lines.extend(
        [
            "",
            "## Optional Review Input Validation",
            f"- Input status: `{summary.get('input_file_status', 'NOT_AVAILABLE')}`",
            f"- Review input path: `{summary.get('review_input_path', '<private_path>')}`",
            "- Private reviewed dividend/FCF values are not printed in this report.",
            "",
            "## Evidence / SEC / Manual Closure Diagnostics",
            "- `SEC_EVIDENCE_POSSIBLE` means a reviewed SEC identity exists structurally; no SEC network call was made.",
            "- `REVIEW_EXISTING_EVIDENCE` means exact existing registry/applied signals should be reviewed before any apply step.",
            "- `MANUAL_EVIDENCE_REQUIRED` means no sufficient structural evidence path was found.",
            "",
            "## No-Imputation Guardrail",
            "- This module does not fetch SEC data, calculate dividend/FCF KPIs, impute values, or write to master/score/evidence-apply artifacts.",
            "",
            "## Reconciliation Impact",
            "- `MISSING_DIVIDEND_FCF_REQUIRED` remains active until approved dividend/FCF inputs exist and are applied through a separate reviewed workflow.",
            "- This patch only makes the dividend/FCF input contract and review queue explicit.",
            "",
            "## Remaining Demo Readiness Blockers",
            "- Watchlist sample/review state, valuation gaps, core-data review states, provenance gaps, and freshness metadata review remain outside this patch.",
            "",
            "## Remaining Decision Readiness Blockers",
            "- Dividend/FCF gaps remain blocked while reviewed inputs are missing or unapplied.",
            "",
            "## Reason Code Counts",
        ]
    )
    for reason, count in sorted(reason_counts.items()):
        lines.append(f"- `{reason}`: {count}")
    lines.extend(["", "## Recommended Next Patch", "`PATCH / READINESS STATUS CONSOLIDATION / BLOCKER SUMMARY / NO VALUE CHANGES`", ""])
    return "\n".join(lines)


def run_personal_dividend_fcf_input_contract(
    *,
    kpi_tier_input: str = DEFAULT_KPI_TIER_INPUT,
    scores_input: str = DEFAULT_SCORES_INPUT,
    evidence_registry_input: str = DEFAULT_EVIDENCE_REGISTRY_INPUT,
    evidence_applied_master_input: str = DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT,
    sec_scope_review_input: str = DEFAULT_SEC_SCOPE_REVIEW_INPUT,
    sec_identity_apply_input: str = DEFAULT_SEC_IDENTITY_APPLY_INPUT,
    metric_definitions_input: str = DEFAULT_METRIC_DEFINITIONS_INPUT,
    review_input: str = DEFAULT_REVIEW_INPUT,
    queue_output: str = DEFAULT_QUEUE_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> DividendFcfInputContractResult:
    warnings: list[str] = []
    contract_status, required_kpis = load_dividend_fcf_kpis(metric_definitions_input, warnings)
    kpi_rows, kpi_warnings, _ = optional_csv_rows(kpi_tier_input, "kpi_tier")
    _, score_warnings, _ = optional_csv_rows(scores_input, "scores")
    evidence_rows, evidence_warnings, registry_present = optional_csv_rows(evidence_registry_input, "evidence_registry")
    applied_rows, applied_warnings, applied_present = optional_csv_rows(evidence_applied_master_input, "evidence_applied_master")
    sec_scope_rows, sec_scope_warnings, sec_scope_present = optional_csv_rows(sec_scope_review_input, "sec_scope_review")
    sec_identity_rows, sec_identity_warnings, sec_identity_present = optional_csv_rows(sec_identity_apply_input, "sec_identity_apply")
    review_rows, review_warnings, review_exists = optional_csv_rows(review_input, "dividend_fcf_review_input")
    warnings.extend(kpi_warnings + score_warnings + evidence_warnings + applied_warnings + sec_scope_warnings + sec_identity_warnings)
    if review_exists:
        warnings.extend(review_warnings)
    queue_rows, summary_rows = build_contract(
        kpi_rows=kpi_rows,
        evidence_rows=evidence_rows,
        applied_rows=applied_rows,
        sec_scope_rows=sec_scope_rows,
        sec_identity_rows=sec_identity_rows,
        review_rows=review_rows,
        review_input_exists=review_exists,
        review_input_path=review_input,
        required_kpis=required_kpis,
        contract_status=contract_status,
        registry_present=registry_present,
        applied_present=applied_present,
        sec_artifacts_present=sec_scope_present or sec_identity_present,
        warnings=warnings,
    )
    input_paths = {
        "kpi_tier": kpi_tier_input,
        "scores": scores_input,
        "evidence_registry": evidence_registry_input,
        "evidence_applied_master": evidence_applied_master_input,
        "sec_scope_review": sec_scope_review_input,
        "sec_identity_apply": sec_identity_apply_input,
        "metric_definitions": metric_definitions_input,
        "dividend_fcf_review_input": review_input,
        "queue_output": queue_output,
        "summary_output": summary_output,
    }
    queue_path = write_csv_rows(queue_output, QUEUE_FIELDS, queue_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(summary_rows, queue_rows, input_paths), encoding="utf-8")
    return DividendFcfInputContractResult(queue_path, summary_path, report_path, queue_rows, summary_rows, tuple(warnings))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a reviewed dividend/FCF input contract without imputation.")
    parser.add_argument("--kpi-tier-input", default=DEFAULT_KPI_TIER_INPUT)
    parser.add_argument("--scores-input", default=DEFAULT_SCORES_INPUT)
    parser.add_argument("--evidence-registry-input", default=DEFAULT_EVIDENCE_REGISTRY_INPUT)
    parser.add_argument("--evidence-applied-master-input", default=DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT)
    parser.add_argument("--sec-scope-review-input", default=DEFAULT_SEC_SCOPE_REVIEW_INPUT)
    parser.add_argument("--sec-identity-apply-input", default=DEFAULT_SEC_IDENTITY_APPLY_INPUT)
    parser.add_argument("--metric-definitions-input", default=DEFAULT_METRIC_DEFINITIONS_INPUT)
    parser.add_argument("--review-input", default=DEFAULT_REVIEW_INPUT)
    parser.add_argument("--queue-output", default=DEFAULT_QUEUE_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_dividend_fcf_input_contract(
        kpi_tier_input=args.kpi_tier_input,
        scores_input=args.scores_input,
        evidence_registry_input=args.evidence_registry_input,
        evidence_applied_master_input=args.evidence_applied_master_input,
        sec_scope_review_input=args.sec_scope_review_input,
        sec_identity_apply_input=args.sec_identity_apply_input,
        metric_definitions_input=args.metric_definitions_input,
        review_input=args.review_input,
        queue_output=args.queue_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    summary = {row["metric"]: row["value"] for row in result.summary_rows}
    print(f"queue_output={result.queue_output}")
    print(f"summary_output={result.summary_output}")
    print(f"report_output={result.report_output}")
    print(f"affected_standard_rows_count={summary.get('affected_standard_rows_count', '0')}")
    print(f"input_file_status={summary.get('input_file_status', 'NOT_AVAILABLE')}")
    print(f"warnings_total={summary.get('warnings_total', '0')}")


if __name__ == "__main__":
    main()
