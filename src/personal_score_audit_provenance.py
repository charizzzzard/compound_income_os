from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import resolve_repo_path, write_csv_rows
from src.personal_kpi_provenance_audit import (
    build_audit_rows,
    load_metric_definitions,
    optional_csv_rows,
    optional_json,
    safe_display_path,
)

DEFAULT_SCORE_AUDIT_INPUT = "data/processed/personal_score_audit.csv"
DEFAULT_PROFILED_MASTER_INPUT = "data/processed/personal_fundamentals_master_profiled.csv"
DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT = "data/processed/personal_fundamentals_master_evidence_applied.csv"
DEFAULT_EVIDENCE_REGISTRY_INPUT = "data/processed/personal_fundamentals_evidence_registry.csv"
DEFAULT_RAW_MASTER_INPUT = "data/raw/personal_fundamentals_master.csv"
DEFAULT_OVERLAY_INPUT = "data/raw/personal_fundamentals_overlay.csv"
DEFAULT_METRIC_DEFINITIONS_INPUT = "configs/fundamentals_metric_definitions.yaml"
DEFAULT_RUN_USED_INPUTS_INPUT = "data/processed/personal_run_used_inputs.csv"
DEFAULT_RUN_MANIFEST_INPUT = "data/processed/personal_run_manifest.json"
DEFAULT_PROVENANCE_OUTPUT = "data/processed/personal_score_audit_provenance.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_score_audit_provenance_summary.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_score_audit_provenance_report.md"

PROVENANCE_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "kpi_name",
    "kpi_tier",
    "kpi_required_status",
    "score_audit_value",
    "evidence_applied_value",
    "profiled_master_value",
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


@dataclass(frozen=True)
class ScoreAuditProvenanceResult:
    provenance_output: Path
    summary_output: Path
    report_output: Path
    provenance_rows: list[dict[str, str]]
    summary_rows: list[dict[str, str]]
    warnings: tuple[str, ...]


def normalize_source_layer(row: dict[str, str]) -> str:
    if row.get("provenance_status") == "NOT_APPLICABLE":
        return "NOT_APPLICABLE"
    layer = str(row.get("source_layer", "") or "").strip()
    if layer == "SCORE_AUDIT":
        return "SCORE_AUDIT_ONLY"
    return layer or "NOT_FOUND"


def normalize_provenance_status(row: dict[str, str]) -> tuple[str, str]:
    status = str(row.get("provenance_status", "") or "").strip() or "MISSING"
    reason = str(row.get("reason_code", "") or "").strip() or "VALUE_MISSING"
    layer = normalize_source_layer(row)
    if status == "TRUSTED" and layer == "EVIDENCE_REGISTRY":
        if not str(row.get("source_reference", "") or "").strip() or not str(row.get("source_as_of_date", "") or "").strip():
            return "PARTIAL", "VALUE_PRESENT_NO_SOURCE_REFERENCE"
    return status, reason


def to_score_provenance_row(row: dict[str, str]) -> dict[str, str]:
    status, reason = normalize_provenance_status(row)
    return {
        "ticker": row.get("ticker", ""),
        "isin": row.get("isin", ""),
        "company_name": row.get("company_name", ""),
        "company_type_profile": row.get("company_type_profile", ""),
        "kpi_name": row.get("kpi_name", ""),
        "kpi_tier": row.get("kpi_tier", ""),
        "kpi_required_status": row.get("kpi_required_status", ""),
        "score_audit_value": row.get("value_in_score_audit", ""),
        "evidence_applied_value": row.get("value_in_evidence_applied_master", ""),
        "profiled_master_value": row.get("value_in_profiled_master", ""),
        "source_layer": normalize_source_layer(row),
        "source_name": row.get("source_name", ""),
        "source_type": row.get("source_type", ""),
        "source_reference": row.get("source_reference", ""),
        "source_as_of_date": row.get("source_as_of_date", ""),
        "review_status": row.get("review_status", ""),
        "applied_status": row.get("applied_status", ""),
        "provenance_status": status,
        "reason_code": reason,
    }


def build_summary_rows(rows: list[dict[str, str]], warnings: list[str]) -> list[dict[str, str]]:
    summary_rows: list[dict[str, str]] = []

    def add(metric: str, value: Any, notes: str) -> None:
        summary_rows.append({"metric": metric, "value": str(value), "notes": notes})

    status_counts = Counter(row["provenance_status"] for row in rows)
    layer_counts = Counter(row["source_layer"] for row in rows)
    tier_status_counts = Counter((row["kpi_required_status"], row["provenance_status"]) for row in rows)
    reason_counts = Counter(reason for row in rows for reason in row["reason_code"].split(";") if reason)
    incomplete_holdings = {
        (row["ticker"], row["isin"])
        for row in rows
        if row["provenance_status"] in {"PARTIAL", "MISSING", "AMBIGUOUS"}
    }
    propagated_rows = [
        row
        for row in rows
        if any(str(row.get(field, "") or "").strip() for field in ("source_name", "source_type", "source_reference", "source_as_of_date"))
    ]

    add("implementation_path", "COMPANION_AUDIT", "Existing personal_score_audit.csv contract remains unchanged.")
    add("provenance_rows_total", len(rows), "Rows in personal_score_audit_provenance.csv.")
    add("source_metadata_propagated_total", len(propagated_rows), "Rows carrying at least one source metadata field.")
    for status in ("TRUSTED", "PARTIAL", "MISSING", "AMBIGUOUS", "NOT_APPLICABLE"):
        add(f"provenance_status__{status}", status_counts.get(status, 0), "Provenance status count.")
    for layer, count in sorted(layer_counts.items()):
        add(f"source_layer__{layer}", count, "Source layer count.")
    for reason, count in sorted(reason_counts.items()):
        add(f"reason_code__{reason}", count, "Reason code count.")
    for (tier, status), count in sorted(tier_status_counts.items()):
        add(f"kpi_required_status__{tier}__{status}", count, "KPI tier by provenance status count.")
    add("holdings_with_incomplete_provenance_total", len(incomplete_holdings), "Distinct holdings with PARTIAL, MISSING, or AMBIGUOUS provenance.")
    add("provenance_incomplete_flag", str(any(row["provenance_status"] in {"PARTIAL", "MISSING", "AMBIGUOUS"} for row in rows)), "Can feed future reconciliation PROVENANCE_INCOMPLETE.")
    add("warnings_total", len(warnings), "Missing input warnings.")
    for warning in sorted(warnings):
        add(f"warning__{warning}", "1", "Input warning.")
    return sorted(summary_rows, key=lambda row: row["metric"])


def render_report(summary_rows: list[dict[str, str]], rows: list[dict[str, str]], input_paths: dict[str, str]) -> str:
    summary = {row["metric"]: row["value"] for row in summary_rows}

    def sample(status: str, limit: int = 16) -> list[dict[str, str]]:
        return [row for row in rows if row["provenance_status"] == status][:limit]

    lines = [
        "# Personal Score Audit Provenance Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## 1. Executive Summary",
        "",
        f"- Implementation path: `{summary.get('implementation_path', 'COMPANION_AUDIT')}`",
        f"- Provenance rows: `{summary.get('provenance_rows_total', '0')}`",
        f"- Trusted: `{summary.get('provenance_status__TRUSTED', '0')}`",
        f"- Partial: `{summary.get('provenance_status__PARTIAL', '0')}`",
        f"- Missing: `{summary.get('provenance_status__MISSING', '0')}`",
        f"- Ambiguous: `{summary.get('provenance_status__AMBIGUOUS', '0')}`",
        f"- Not applicable: `{summary.get('provenance_status__NOT_APPLICABLE', '0')}`",
        f"- Source metadata propagated rows: `{summary.get('source_metadata_propagated_total', '0')}`",
        "",
        "This companion audit propagates source metadata beside score-relevant KPI values without changing the existing score audit, scores, formulas, weights, or fundamentals values.",
        "",
        "## 2. Input Artifacts",
        "",
        "| Label | Path |",
        "| --- | --- |",
    ]
    for label, path in sorted(input_paths.items()):
        lines.append(f"| {label} | `{safe_display_path(path)}` |")

    lines.extend(
        [
            "",
            "## 3. Chosen Implementation Path",
            "",
            "Companion Audit. The existing `personal_score_audit.csv` remains unchanged to avoid breaking downstream consumers. `personal_score_audit_provenance.csv` carries one row per score-relevant KPI per holding with source metadata and provenance status.",
            "",
            "## 4. Source Metadata Coverage",
            "",
            "| Metric | Value | Notes |",
            "| --- | --- | --- |",
        ]
    )
    for row in summary_rows:
        lines.append(f"| `{row['metric']}` | `{row['value']}` | {row['notes']} |")

    lines.extend(["", "## 5. KPI Tier Coverage by Provenance Status", ""])
    tier_rows = [row for row in summary_rows if row["metric"].startswith("kpi_required_status__")]
    if tier_rows:
        lines.extend(["| Metric | Value |", "| --- | --- |"])
        for row in tier_rows:
            lines.append(f"| `{row['metric']}` | `{row['value']}` |")
    else:
        lines.append("No tier coverage rows available.")

    def add_section(title: str, examples: list[dict[str, str]]) -> None:
        lines.extend(["", title, ""])
        if not examples:
            lines.append("None.")
            return
        lines.extend(["| Ticker | ISIN | KPI | Layer | Reason |", "| --- | --- | --- | --- | --- |"])
        for row in examples:
            lines.append(f"| `{row['ticker']}` | `{row['isin']}` | `{row['kpi_name']}` | `{row['source_layer']}` | `{row['reason_code']}` |")

    add_section("## 6. Holdings with Missing Provenance", sample("MISSING"))
    add_section("## 7. Holdings with Trusted Provenance", sample("TRUSTED"))
    add_section("## 8. Ambiguous Cases", sample("AMBIGUOUS"))

    lines.extend(
        [
            "",
            "## 9. Compatibility Notes",
            "",
            "- Existing `personal_score_audit.csv` is not modified.",
            "- Existing score formulas, weights, and KPI values are not modified.",
            "- Downstream tools can join by `ticker`, `isin`, and `kpi_name` when they need source metadata.",
            "",
            "## 10. Impact on Demo Readiness",
            "",
            "`provenance_incomplete_flag` remains available for later reconciliation integration. Demo readiness remains REVIEW/BLOCKED while missing provenance remains visible.",
            "",
            "## 11. Impact on Decision Readiness",
            "",
            "Decision readiness remains blocked for score-relevant KPIs with MISSING, PARTIAL, or AMBIGUOUS provenance. This report does not change candidate status.",
            "",
            "## 12. Recommended Next Patch",
            "",
            "PATCH / MONTHLY SCHEMA STABILIZATION / TARGET_ACTION TO MONTHLY_ACTION COMPATIBILITY / NO ADVICE LANGUAGE",
            "",
        ]
    )
    return "\n".join(lines)


def run_personal_score_audit_provenance(
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
    provenance_output: str = DEFAULT_PROVENANCE_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> ScoreAuditProvenanceResult:
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

    kpi_rows = build_audit_rows(
        score_audit_rows=score_rows,
        profiled_rows=profiled_rows,
        evidence_applied_rows=applied_rows,
        evidence_registry_rows=registry_rows,
        raw_master_rows=raw_rows,
        overlay_rows=overlay_rows,
        metric_definitions=metric_definitions,
    )
    provenance_rows = sorted((to_score_provenance_row(row) for row in kpi_rows), key=lambda row: (row["isin"], row["ticker"], row["kpi_name"]))
    summary_rows = build_summary_rows(provenance_rows, warnings)
    provenance_path = write_csv_rows(provenance_output, PROVENANCE_FIELDS, provenance_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_report(
            summary_rows,
            provenance_rows,
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
    return ScoreAuditProvenanceResult(
        provenance_output=provenance_path,
        summary_output=summary_path,
        report_output=report_path,
        provenance_rows=provenance_rows,
        summary_rows=summary_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a score-audit companion artifact carrying per-KPI source provenance.")
    parser.add_argument("--score-audit-input", default=DEFAULT_SCORE_AUDIT_INPUT)
    parser.add_argument("--profiled-master-input", default=DEFAULT_PROFILED_MASTER_INPUT)
    parser.add_argument("--evidence-applied-master-input", default=DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT)
    parser.add_argument("--evidence-registry-input", default=DEFAULT_EVIDENCE_REGISTRY_INPUT)
    parser.add_argument("--raw-master-input", default=DEFAULT_RAW_MASTER_INPUT)
    parser.add_argument("--overlay-input", default=DEFAULT_OVERLAY_INPUT)
    parser.add_argument("--metric-definitions-input", default=DEFAULT_METRIC_DEFINITIONS_INPUT)
    parser.add_argument("--run-used-inputs-input", default=DEFAULT_RUN_USED_INPUTS_INPUT)
    parser.add_argument("--run-manifest-input", default=DEFAULT_RUN_MANIFEST_INPUT)
    parser.add_argument("--provenance-output", default=DEFAULT_PROVENANCE_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_score_audit_provenance(
        score_audit_input=args.score_audit_input,
        profiled_master_input=args.profiled_master_input,
        evidence_applied_master_input=args.evidence_applied_master_input,
        evidence_registry_input=args.evidence_registry_input,
        raw_master_input=args.raw_master_input,
        overlay_input=args.overlay_input,
        metric_definitions_input=args.metric_definitions_input,
        run_used_inputs_input=args.run_used_inputs_input,
        run_manifest_input=args.run_manifest_input,
        provenance_output=args.provenance_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    summary = {row["metric"]: row["value"] for row in result.summary_rows}
    print(f"provenance_output={result.provenance_output}")
    print(f"summary_output={result.summary_output}")
    print(f"report_output={result.report_output}")
    print(f"provenance_rows_total={summary.get('provenance_rows_total', '0')}")
    print(f"trusted={summary.get('provenance_status__TRUSTED', '0')}")
    print(f"partial={summary.get('provenance_status__PARTIAL', '0')}")
    print(f"missing={summary.get('provenance_status__MISSING', '0')}")
    print(f"ambiguous={summary.get('provenance_status__AMBIGUOUS', '0')}")
    print(f"warnings_total={len(result.warnings)}")


if __name__ == "__main__":
    main()
