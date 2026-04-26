from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_SCORE_AUDIT_INPUT = "data/processed/personal_score_audit.csv"
DEFAULT_PROFILED_MASTER_INPUT = "data/processed/personal_fundamentals_master_profiled.csv"
DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT = "data/processed/personal_fundamentals_master_evidence_applied.csv"
DEFAULT_EVIDENCE_REGISTRY_INPUT = "data/processed/personal_fundamentals_evidence_registry.csv"
DEFAULT_RAW_MASTER_INPUT = "data/raw/personal_fundamentals_master.csv"
DEFAULT_OVERLAY_INPUT = "data/raw/personal_fundamentals_overlay.csv"
DEFAULT_METRIC_DEFINITIONS_INPUT = "configs/fundamentals_metric_definitions.yaml"
DEFAULT_RUN_USED_INPUTS_INPUT = "data/processed/personal_run_used_inputs.csv"
DEFAULT_RUN_MANIFEST_INPUT = "data/processed/personal_run_manifest.json"
DEFAULT_AUDIT_OUTPUT = "data/processed/personal_kpi_provenance_audit.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_kpi_provenance_summary.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_kpi_provenance_audit_report.md"

AUDIT_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "kpi_name",
    "kpi_tier",
    "kpi_required_status",
    "value_in_score_audit",
    "value_in_evidence_applied_master",
    "value_in_profiled_master",
    "source_layer",
    "source_name",
    "source_type",
    "source_reference",
    "source_as_of_date",
    "review_status",
    "applied_status",
    "provenance_status",
    "reason_code",
]
SUMMARY_FIELDS = ["metric", "value", "notes"]
IDENTITY_FIELDS = {"ticker", "isin", "company_name", "company_type_profile"}
SOURCE_STATUS_FIELDS = {"source_name", "source_as_of_date", "fundamentals_input_format", "data_quality_flag"}
NON_KPI_SCORE_AUDIT_FIELDS = {
    *IDENTITY_FIELDS,
    *SOURCE_STATUS_FIELDS,
    "source_type",
    "source_reference",
    "review_status",
    "applied_status",
    "quality_score",
    "dividend_score",
    "balance_sheet_score",
    "growth_quality_score",
    "capital_allocation_score",
    "business_score",
    "historical_multiple_score",
    "normalized_fcf_score",
    "dividend_yield_relative_score",
    "valuation_score",
    "expected_return_score",
    "drawdown_opportunity_score",
    "portfolio_fit_score",
    "buy_score",
    "business_score_contribution",
    "valuation_score_contribution",
    "expected_return_score_contribution",
    "drawdown_score_contribution",
    "portfolio_fit_score_contribution",
    "pe_relative_ratio",
    "ev_ebit_relative_ratio",
    "fcf_yield_relative_ratio",
    "normalized_fcf_gap",
    "dividend_yield_relative_ratio",
    "fair_value_estimate",
    "margin_of_safety_pct",
    "core_quality_data_status",
    "valuation_data_status",
    "dividend_fcf_data_status",
    "advanced_data_status",
    "missing_core_quality_kpis",
    "missing_valuation_kpis",
    "missing_dividend_fcf_kpis",
    "missing_advanced_optional_kpis",
    "missing_kpi_count",
    "missing_kpis",
    "not_applicable_kpis",
    "quality_score_inputs",
    "dividend_score_inputs",
    "balance_sheet_score_inputs",
    "growth_quality_score_inputs",
    "capital_allocation_score_inputs",
}


@dataclass(frozen=True)
class ProvenanceAuditResult:
    audit_output: Path
    summary_output: Path
    report_output: Path
    audit_rows: list[dict[str, str]]
    summary_rows: list[dict[str, str]]
    warnings: tuple[str, ...]


def safe_display_path(path_value: str) -> str:
    normalized = str(path_value).replace("\\", "/")
    if "data/raw/private" in normalized:
        return "<private_path>"
    return path_value


def optional_csv_rows(path_value: str, label: str) -> tuple[list[dict[str, str]], list[str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], [f"missing_input={label}:{safe_display_path(path_value)}"]
    return read_csv_rows(path), []


def optional_json(path_value: str, label: str) -> tuple[dict[str, Any], list[str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return {}, [f"missing_input={label}:{safe_display_path(path_value)}"]
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle), []


def load_metric_definitions(path_value: str) -> tuple[dict[str, dict[str, Any]], list[str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return {}, [f"missing_input=metric_definitions:{safe_display_path(path_value)}"]
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    kpis = data.get("kpis") if isinstance(data.get("kpis"), dict) else {}
    return {str(name): value for name, value in kpis.items() if isinstance(value, dict)}, []


def canonical_ticker(value: Any) -> str:
    return str(value or "").strip().upper().replace(" ", "")


def canonical_isin(value: Any) -> str:
    return str(value or "").strip().upper()


def value_present(value: Any) -> bool:
    return str(value or "").strip() != ""


def values_equal(left: str, right: str) -> bool:
    return str(left or "").strip() == str(right or "").strip()


def identity_key(row: dict[str, Any]) -> tuple[str, str]:
    return canonical_ticker(row.get("ticker", "")), canonical_isin(row.get("isin", ""))


def row_key(row: dict[str, Any], kpi_name: str) -> tuple[str, str, str]:
    ticker, isin = identity_key(row)
    return ticker, isin, kpi_name


def lookup_exact(rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str], list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    by_isin: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    by_ticker: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        ticker, isin = identity_key(row)
        if isin:
            by_isin[(ticker, isin)].append(row)
            by_isin[("", isin)].append(row)
        elif ticker:
            by_ticker[ticker].append(row)
    return by_isin, by_ticker


def find_identity(row: dict[str, str], by_isin: dict[tuple[str, str], list[dict[str, str]]], by_ticker: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    ticker, isin = identity_key(row)
    if isin:
        return by_isin.get((ticker, isin), []) or by_isin.get(("", isin), [])
    if ticker:
        return by_ticker.get(ticker, [])
    return []


def build_evidence_lookup(evidence_rows: list[dict[str, str]]) -> dict[tuple[str, str, str], list[dict[str, str]]]:
    lookup: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in evidence_rows:
        kpi_name = str(row.get("kpi_name", "") or "").strip()
        if not kpi_name:
            continue
        ticker, isin = identity_key(row)
        if isin:
            lookup[(ticker, isin, kpi_name)].append(row)
            lookup[("", isin, kpi_name)].append(row)
        elif ticker:
            lookup[(ticker, "", kpi_name)].append(row)
    return lookup


def evidence_candidates(row: dict[str, str], kpi_name: str, lookup: dict[tuple[str, str, str], list[dict[str, str]]]) -> list[dict[str, str]]:
    ticker, isin = identity_key(row)
    if isin:
        candidates = lookup.get((ticker, isin, kpi_name), []) or lookup.get(("", isin, kpi_name), [])
    elif ticker:
        candidates = lookup.get((ticker, "", kpi_name), [])
    else:
        candidates = []
    unique: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for candidate in candidates:
        key = (
            str(candidate.get("source_name", "") or ""),
            str(candidate.get("source_reference", "") or ""),
            str(candidate.get("source_as_of_date", "") or ""),
            str(candidate.get("reported_value", "") or ""),
        )
        unique[key] = candidate
    return list(unique.values())


def score_relevant_kpis(score_audit_rows: list[dict[str, str]], metric_definitions: dict[str, dict[str, Any]]) -> list[str]:
    if score_audit_rows:
        fields = set(score_audit_rows[0].keys())
    else:
        fields = set(metric_definitions)
    configured = set(metric_definitions)
    candidates = {
        field
        for field in fields
        if field not in NON_KPI_SCORE_AUDIT_FIELDS
        and not field.endswith("_inputs")
        and (field in configured or field not in IDENTITY_FIELDS)
    }
    if configured:
        candidates = {field for field in candidates if field in configured}
    return sorted(candidates)


def kpi_tier(kpi_name: str, metric_definitions: dict[str, dict[str, Any]]) -> tuple[str, str]:
    definition = metric_definitions.get(kpi_name, {})
    tier = str(definition.get("kpi_tier", "") or "").strip()
    if tier:
        return tier, tier
    return "UNKNOWN", "UNKNOWN"


def first_source_value(row: dict[str, str], *fields: str) -> str:
    for field in fields:
        value = str(row.get(field, "") or "").strip()
        if value:
            return value
    return ""


def source_from_master(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        str(row.get("source_name", "") or "").strip(),
        "",
        "",
        str(row.get("source_as_of_date", "") or "").strip(),
    )


def resolve_provenance(
    *,
    score_row: dict[str, str],
    kpi_name: str,
    profile: str,
    evidence_applied_rows: list[dict[str, str]],
    profiled_rows: list[dict[str, str]],
    raw_rows: list[dict[str, str]],
    overlay_rows: list[dict[str, str]],
    evidence_rows: list[dict[str, str]],
) -> dict[str, str]:
    score_value = str(score_row.get(kpi_name, "") or "").strip()
    applied_row = evidence_applied_rows[0] if len(evidence_applied_rows) == 1 else {}
    profiled_row = profiled_rows[0] if len(profiled_rows) == 1 else {}
    raw_row = raw_rows[0] if len(raw_rows) == 1 else {}
    overlay_row = overlay_rows[0] if len(overlay_rows) == 1 else {}
    applied_value = str(applied_row.get(kpi_name, "") or "").strip() if applied_row else ""
    profiled_value = str(profiled_row.get(kpi_name, "") or "").strip() if profiled_row else ""
    raw_value = str(raw_row.get(kpi_name, "") or "").strip() if raw_row else ""
    overlay_value = str(overlay_row.get(kpi_name, "") or "").strip() if overlay_row and kpi_name in overlay_row else ""

    base = {
        "value_in_score_audit": score_value,
        "value_in_evidence_applied_master": applied_value,
        "value_in_profiled_master": profiled_value,
        "source_layer": "NOT_FOUND",
        "source_name": "",
        "source_type": "",
        "source_reference": "",
        "source_as_of_date": "",
        "review_status": "",
        "applied_status": "",
        "provenance_status": "MISSING",
        "reason_code": "VALUE_MISSING",
    }

    if profile != "STANDARD":
        base.update(
            {
                "source_layer": "NOT_FOUND",
                "provenance_status": "NOT_APPLICABLE",
                "reason_code": "PROFILE_NOT_STANDARD",
            }
        )
        return base

    if len(evidence_rows) > 1:
        candidate = evidence_rows[0]
        base.update(
            {
                "source_layer": "AMBIGUOUS",
                "source_name": first_source_value(candidate, "source_name"),
                "source_type": first_source_value(candidate, "source_type"),
                "source_reference": first_source_value(candidate, "source_reference"),
                "source_as_of_date": first_source_value(candidate, "source_as_of_date"),
                "review_status": first_source_value(candidate, "verification_status", "data_quality_flag"),
                "applied_status": "APPLIED" if value_present(applied_value) else "NOT_APPLIED",
                "provenance_status": "AMBIGUOUS",
                "reason_code": "MULTIPLE_SOURCE_CANDIDATES",
            }
        )
        return base

    if evidence_rows:
        candidate = evidence_rows[0]
        source_reference = first_source_value(candidate, "source_reference", "evidence_identity")
        has_value = value_present(score_value) or value_present(applied_value) or value_present(candidate.get("reported_value", ""))
        base.update(
            {
                "source_layer": "EVIDENCE_REGISTRY",
                "source_name": first_source_value(candidate, "source_name"),
                "source_type": first_source_value(candidate, "source_type"),
                "source_reference": source_reference,
                "source_as_of_date": first_source_value(candidate, "source_as_of_date"),
                "review_status": first_source_value(candidate, "verification_status", "data_quality_flag"),
                "applied_status": "APPLIED" if value_present(applied_value) else "NOT_APPLIED",
                "provenance_status": "TRUSTED" if source_reference and has_value else "PARTIAL",
                "reason_code": "SOURCE_MATCHED" if source_reference and has_value else "VALUE_PRESENT_NO_SOURCE_REFERENCE",
            }
        )
        return base

    if value_present(applied_value):
        source_name, source_type, source_reference, source_date = source_from_master(applied_row)
        base.update(
            {
                "source_layer": "EVIDENCE_APPLIED_MASTER",
                "source_name": source_name,
                "source_type": source_type,
                "source_reference": source_reference,
                "source_as_of_date": source_date,
                "applied_status": "APPLIED",
                "provenance_status": "PARTIAL",
                "reason_code": "VALUE_PRESENT_NO_SOURCE_REFERENCE",
            }
        )
        return base

    if value_present(overlay_value):
        base.update(
            {
                "source_layer": "OVERLAY",
                "source_name": first_source_value(overlay_row, "overlay_source_name", "source_name"),
                "source_type": "manual_overlay",
                "source_reference": first_source_value(overlay_row, "source_reference"),
                "source_as_of_date": first_source_value(overlay_row, "overlay_as_of_date"),
                "review_status": first_source_value(overlay_row, "verification_status"),
                "applied_status": "OVERLAY_PRESENT",
                "provenance_status": "TRUSTED" if first_source_value(overlay_row, "source_reference") else "PARTIAL",
                "reason_code": "SOURCE_MATCHED" if first_source_value(overlay_row, "source_reference") else "VALUE_PRESENT_NO_SOURCE_REFERENCE",
            }
        )
        return base

    if value_present(profiled_value):
        source_name, source_type, source_reference, source_date = source_from_master(profiled_row)
        base.update(
            {
                "source_layer": "PROFILED_MASTER",
                "source_name": source_name,
                "source_type": source_type,
                "source_reference": source_reference,
                "source_as_of_date": source_date,
                "applied_status": "PROFILED_PRESENT",
                "provenance_status": "PARTIAL",
                "reason_code": "VALUE_PRESENT_NO_SOURCE_REFERENCE",
            }
        )
        return base

    if value_present(raw_value):
        source_name, source_type, source_reference, source_date = source_from_master(raw_row)
        base.update(
            {
                "source_layer": "RAW_MASTER",
                "source_name": source_name,
                "source_type": source_type,
                "source_reference": source_reference,
                "source_as_of_date": source_date,
                "applied_status": "RAW_PRESENT",
                "provenance_status": "PARTIAL",
                "reason_code": "VALUE_PRESENT_NO_SOURCE_REFERENCE",
            }
        )
        return base

    if value_present(score_value):
        base.update(
            {
                "source_layer": "SCORE_AUDIT",
                "source_name": str(score_row.get("source_name", "") or "").strip(),
                "source_as_of_date": str(score_row.get("source_as_of_date", "") or "").strip(),
                "applied_status": "SCORE_AUDIT_PRESENT",
                "provenance_status": "PARTIAL",
                "reason_code": "EVIDENCE_REGISTRY_MISSING",
            }
        )
        return base

    reason = "SCORE_AUDIT_VALUE_MISSING"
    if not evidence_rows:
        reason = "EVIDENCE_REGISTRY_MISSING"
    if not value_present(applied_value):
        reason = f"{reason};EVIDENCE_APPLIED_VALUE_MISSING"
    return {**base, "reason_code": reason}


def build_audit_rows(
    *,
    score_audit_rows: list[dict[str, str]],
    profiled_rows: list[dict[str, str]],
    evidence_applied_rows: list[dict[str, str]],
    evidence_registry_rows: list[dict[str, str]],
    raw_master_rows: list[dict[str, str]],
    overlay_rows: list[dict[str, str]],
    metric_definitions: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    kpis = score_relevant_kpis(score_audit_rows, metric_definitions)
    profiled_isin, profiled_ticker = lookup_exact(profiled_rows)
    applied_isin, applied_ticker = lookup_exact(evidence_applied_rows)
    raw_isin, raw_ticker = lookup_exact(raw_master_rows)
    overlay_isin, overlay_ticker = lookup_exact(overlay_rows)
    evidence_lookup = build_evidence_lookup(evidence_registry_rows)

    rows: list[dict[str, str]] = []
    for score_row in sorted(score_audit_rows, key=lambda row: (canonical_isin(row.get("isin", "")), canonical_ticker(row.get("ticker", "")))):
        ticker = canonical_ticker(score_row.get("ticker", ""))
        isin = canonical_isin(score_row.get("isin", ""))
        profile = safe_upper(score_row.get("company_type_profile", "")) or "UNKNOWN"
        for kpi_name in kpis:
            tier, required_status = kpi_tier(kpi_name, metric_definitions)
            provenance = resolve_provenance(
                score_row=score_row,
                kpi_name=kpi_name,
                profile=profile,
                evidence_applied_rows=find_identity(score_row, applied_isin, applied_ticker),
                profiled_rows=find_identity(score_row, profiled_isin, profiled_ticker),
                raw_rows=find_identity(score_row, raw_isin, raw_ticker),
                overlay_rows=find_identity(score_row, overlay_isin, overlay_ticker),
                evidence_rows=evidence_candidates(score_row, kpi_name, evidence_lookup),
            )
            rows.append(
                {
                    "ticker": ticker,
                    "isin": isin,
                    "company_name": str(score_row.get("company_name", "") or "").strip(),
                    "company_type_profile": profile,
                    "kpi_name": kpi_name,
                    "kpi_tier": tier,
                    "kpi_required_status": required_status,
                    **provenance,
                }
            )
    return sorted(rows, key=lambda row: (row["isin"], row["ticker"], row["kpi_name"]))


def build_summary_rows(audit_rows: list[dict[str, str]], warnings: list[str]) -> list[dict[str, str]]:
    summary: list[dict[str, str]] = []

    def add(metric: str, value: Any, notes: str) -> None:
        summary.append({"metric": metric, "value": str(value), "notes": notes})

    status_counts = Counter(row["provenance_status"] for row in audit_rows)
    layer_counts = Counter(row["source_layer"] for row in audit_rows)
    reason_counts = Counter(reason for row in audit_rows for reason in row["reason_code"].split(";") if reason)
    tier_status_counts = Counter((row["kpi_required_status"], row["provenance_status"]) for row in audit_rows)
    missing_holdings = {
        (row["ticker"], row["isin"])
        for row in audit_rows
        if row["provenance_status"] in {"MISSING", "AMBIGUOUS", "PARTIAL"}
    }

    add("audit_rows_total", len(audit_rows), "Rows in personal_kpi_provenance_audit.csv.")
    for status in ("TRUSTED", "PARTIAL", "MISSING", "AMBIGUOUS", "NOT_APPLICABLE"):
        add(f"provenance_status__{status}", status_counts.get(status, 0), "Provenance status count.")
    for layer, count in sorted(layer_counts.items()):
        add(f"source_layer__{layer}", count, "Source layer count.")
    for reason, count in sorted(reason_counts.items()):
        add(f"reason_code__{reason}", count, "Reason code count.")
    for (tier, status), count in sorted(tier_status_counts.items()):
        add(f"kpi_required_status__{tier}__{status}", count, "KPI tier by provenance status count.")
    add("holdings_with_incomplete_provenance_total", len(missing_holdings), "Distinct holdings with PARTIAL, MISSING, or AMBIGUOUS provenance.")
    add("provenance_incomplete_flag", str(any(row["provenance_status"] in {"PARTIAL", "MISSING", "AMBIGUOUS"} for row in audit_rows)), "Can feed future reconciliation PROVENANCE_INCOMPLETE.")
    add("warnings_total", len(warnings), "Missing input warnings.")
    for warning in sorted(warnings):
        add(f"warning__{warning}", "1", "Input warning.")
    return sorted(summary, key=lambda row: row["metric"])


def render_report(summary_rows: list[dict[str, str]], audit_rows: list[dict[str, str]], input_paths: dict[str, str]) -> str:
    summary = {row["metric"]: row["value"] for row in summary_rows}
    missing = [row for row in audit_rows if row["provenance_status"] == "MISSING"][:20]
    partial = [row for row in audit_rows if row["provenance_status"] == "PARTIAL"][:20]
    ambiguous = [row for row in audit_rows if row["provenance_status"] == "AMBIGUOUS"][:20]
    trusted = [row for row in audit_rows if row["provenance_status"] == "TRUSTED"][:10]

    lines = [
        "# Personal KPI Provenance Audit Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## 1. Executive Summary",
        "",
        f"- Audit rows: `{summary.get('audit_rows_total', '0')}`",
        f"- Trusted: `{summary.get('provenance_status__TRUSTED', '0')}`",
        f"- Partial: `{summary.get('provenance_status__PARTIAL', '0')}`",
        f"- Missing: `{summary.get('provenance_status__MISSING', '0')}`",
        f"- Ambiguous: `{summary.get('provenance_status__AMBIGUOUS', '0')}`",
        f"- Not applicable: `{summary.get('provenance_status__NOT_APPLICABLE', '0')}`",
        f"- Provenance incomplete flag: `{summary.get('provenance_incomplete_flag', 'False')}`",
        "",
        "This audit materializes score-relevant KPI provenance only. It does not add values, impute missing KPIs, change score formulas, or call external APIs.",
        "",
        "## 2. Input Artifacts",
        "",
        "| Label | Path |",
        "| --- | --- |",
    ]
    for label, path in sorted(input_paths.items()):
        lines.append(f"| {label} | `{safe_display_path(path)}` |")

    lines.extend(["", "## 3. Provenance Coverage Summary", "", "| Metric | Value | Notes |", "| --- | --- | --- |"])
    for row in summary_rows:
        lines.append(f"| `{row['metric']}` | `{row['value']}` | {row['notes']} |")

    lines.extend(["", "## 4. KPI Tier Coverage by Provenance Status", ""])
    tier_rows = [row for row in summary_rows if row["metric"].startswith("kpi_required_status__")]
    if tier_rows:
        lines.extend(["| Metric | Value |", "| --- | --- |"])
        for row in tier_rows:
            lines.append(f"| `{row['metric']}` | `{row['value']}` |")
    else:
        lines.append("No tier rows available.")

    def add_examples(title: str, rows: list[dict[str, str]]) -> None:
        lines.extend(["", title, ""])
        if not rows:
            lines.append("None.")
            return
        lines.extend(["| Ticker | ISIN | KPI | Layer | Reason |", "| --- | --- | --- | --- | --- |"])
        for row in rows:
            lines.append(f"| `{row['ticker']}` | `{row['isin']}` | `{row['kpi_name']}` | `{row['source_layer']}` | `{row['reason_code']}` |")

    add_examples("## 5. Holdings with Missing Provenance", missing)
    add_examples("## 6. Holdings with Partial Provenance", partial)
    add_examples("## 7. Ambiguous Source Cases", ambiguous)
    add_examples("## 8. Trusted KPI Examples", trusted)

    lines.extend(
        [
            "",
            "## 9. Impact on Demo Readiness",
            "",
            "Demo readiness remains REVIEW/BLOCKED while KPI values cannot be traced to source references for all decision-relevant rows. The summary metric `provenance_incomplete_flag` is intended for later reconciliation integration.",
            "",
            "## 10. Impact on Decision Readiness",
            "",
            "Decision readiness remains BLOCKED for KPIs with `MISSING`, `PARTIAL`, or `AMBIGUOUS` provenance. This is separate from KPI value availability and does not change scoring output.",
            "",
            "## 11. Recommended Next Patch",
            "",
            "Extend evidence/apply artifacts so score audit rows can carry per-KPI `source_reference`, `source_type`, and `source_as_of_date` without changing KPI values.",
            "",
        ]
    )
    return "\n".join(lines)


def run_personal_kpi_provenance_audit(
    *,
    score_audit_input: str = DEFAULT_SCORE_AUDIT_INPUT,
    profiled_master_input: str = DEFAULT_PROFILED_MASTER_INPUT,
    evidence_applied_master_input: str = DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT,
    evidence_registry_input: str = DEFAULT_EVIDENCE_REGISTRY_INPUT,
    raw_master_input: str = DEFAULT_RAW_MASTER_INPUT,
    overlay_input: str = DEFAULT_OVERLAY_INPUT,
    metric_definitions_input: str = DEFAULT_METRIC_DEFINITIONS_INPUT,
    run_used_inputs_input: str = DEFAULT_RUN_USED_INPUTS_INPUT,
    run_manifest_input: str = DEFAULT_RUN_MANIFEST_INPUT,
    audit_output: str = DEFAULT_AUDIT_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> ProvenanceAuditResult:
    warnings: list[str] = []
    score_rows, score_warnings = optional_csv_rows(score_audit_input, "score_audit")
    profiled_rows, profiled_warnings = optional_csv_rows(profiled_master_input, "profiled_master")
    applied_rows, applied_warnings = optional_csv_rows(evidence_applied_master_input, "evidence_applied_master")
    registry_rows, registry_warnings = optional_csv_rows(evidence_registry_input, "evidence_registry")
    raw_rows, raw_warnings = optional_csv_rows(raw_master_input, "raw_master")
    overlay_rows, overlay_warnings = optional_csv_rows(overlay_input, "overlay")
    _, used_warnings = optional_csv_rows(run_used_inputs_input, "run_used_inputs")
    _, manifest_warnings = optional_json(run_manifest_input, "run_manifest")
    metric_definitions, metric_warnings = load_metric_definitions(metric_definitions_input)
    for items in (score_warnings, profiled_warnings, applied_warnings, registry_warnings, raw_warnings, overlay_warnings, used_warnings, manifest_warnings, metric_warnings):
        warnings.extend(items)

    audit_rows = build_audit_rows(
        score_audit_rows=score_rows,
        profiled_rows=profiled_rows,
        evidence_applied_rows=applied_rows,
        evidence_registry_rows=registry_rows,
        raw_master_rows=raw_rows,
        overlay_rows=overlay_rows,
        metric_definitions=metric_definitions,
    )
    summary_rows = build_summary_rows(audit_rows, warnings)
    audit_path = write_csv_rows(audit_output, AUDIT_FIELDS, audit_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_report(
            summary_rows,
            audit_rows,
            {
                "score_audit": score_audit_input,
                "profiled_master": profiled_master_input,
                "evidence_applied_master": evidence_applied_master_input,
                "evidence_registry": evidence_registry_input,
                "raw_master": raw_master_input,
                "overlay": overlay_input,
                "metric_definitions": metric_definitions_input,
                "run_used_inputs": run_used_inputs_input,
                "run_manifest": run_manifest_input,
            },
        ),
        encoding="utf-8",
    )
    return ProvenanceAuditResult(
        audit_output=audit_path,
        summary_output=summary_path,
        report_output=report_path,
        audit_rows=audit_rows,
        summary_rows=summary_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize per-KPI provenance for score-relevant personal holdings.")
    parser.add_argument("--score-audit-input", default=DEFAULT_SCORE_AUDIT_INPUT)
    parser.add_argument("--profiled-master-input", default=DEFAULT_PROFILED_MASTER_INPUT)
    parser.add_argument("--evidence-applied-master-input", default=DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT)
    parser.add_argument("--evidence-registry-input", default=DEFAULT_EVIDENCE_REGISTRY_INPUT)
    parser.add_argument("--raw-master-input", default=DEFAULT_RAW_MASTER_INPUT)
    parser.add_argument("--overlay-input", default=DEFAULT_OVERLAY_INPUT)
    parser.add_argument("--metric-definitions-input", default=DEFAULT_METRIC_DEFINITIONS_INPUT)
    parser.add_argument("--run-used-inputs-input", default=DEFAULT_RUN_USED_INPUTS_INPUT)
    parser.add_argument("--run-manifest-input", default=DEFAULT_RUN_MANIFEST_INPUT)
    parser.add_argument("--audit-output", default=DEFAULT_AUDIT_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_kpi_provenance_audit(
        score_audit_input=args.score_audit_input,
        profiled_master_input=args.profiled_master_input,
        evidence_applied_master_input=args.evidence_applied_master_input,
        evidence_registry_input=args.evidence_registry_input,
        raw_master_input=args.raw_master_input,
        overlay_input=args.overlay_input,
        metric_definitions_input=args.metric_definitions_input,
        run_used_inputs_input=args.run_used_inputs_input,
        run_manifest_input=args.run_manifest_input,
        audit_output=args.audit_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    summary = {row["metric"]: row["value"] for row in result.summary_rows}
    print(f"audit_output={result.audit_output}")
    print(f"summary_output={result.summary_output}")
    print(f"report_output={result.report_output}")
    print(f"audit_rows_total={summary.get('audit_rows_total', '0')}")
    print(f"trusted={summary.get('provenance_status__TRUSTED', '0')}")
    print(f"partial={summary.get('provenance_status__PARTIAL', '0')}")
    print(f"missing={summary.get('provenance_status__MISSING', '0')}")
    print(f"ambiguous={summary.get('provenance_status__AMBIGUOUS', '0')}")
    print(f"warnings_total={len(result.warnings)}")


if __name__ == "__main__":
    main()
