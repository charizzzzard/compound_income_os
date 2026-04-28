from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, read_csv_rows, resolve_repo_path, write_csv_rows

DEFAULT_ALIAS_REVIEW_TABLE = "data/processed/personal_sec_concept_alias_review_table.csv"
DEFAULT_ALIAS_REVIEW_SUMMARY = "data/processed/personal_sec_concept_alias_review_table_summary.csv"
DEFAULT_OUTPUT = "data/processed/personal_sec_concept_alias_approval_input.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_sec_concept_alias_approval_input_summary.csv"
DEFAULT_REPORT_OUTPUT = "reports/2026-04-28/personal_sec_concept_alias_approval_input_report.md"

INCLUDED_STATUSES = {"APPROVE_CANDIDATE", "REVIEW_REQUIRED"}
ALLOWED_HUMAN_STATUSES = {"PENDING_REVIEW", "APPROVED", "REJECTED", "NEEDS_MORE_EVIDENCE"}
RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
MACHINE_ORDER = {"YES": 0, "NO": 1}

APPROVAL_INPUT_FIELDS = [
    "approval_input_id",
    "source_alias_review_id",
    "source_review_id",
    "ticker",
    "isin",
    "company_name",
    "kpi_field",
    "required_concept_role",
    "missing_required_concept",
    "candidate_sec_concept",
    "candidate_label",
    "candidate_description",
    "available_annual_periods",
    "first_available_fiscal_year",
    "last_available_fiscal_year",
    "available_period_count",
    "alias_candidate_status",
    "alias_risk_level",
    "machine_suggested_approval",
    "human_approval_status",
    "approval_scope",
    "approval_rationale",
    "reviewer_notes",
    "reviewer_name",
    "review_date",
    "semantic_match_reason",
    "semantic_risk_reason",
    "recommended_action",
    "source_artifact",
    "candidate_value_not_applied",
    "apply_status",
    "notes",
]

SUMMARY_FIELDS = [
    "total_approval_input_rows",
    "source_alias_review_rows",
    "machine_suggested_approval_rows",
    "pending_review_rows",
    "approved_rows",
    "rejected_rows",
    "needs_more_evidence_rows",
    "low_risk_rows",
    "medium_risk_rows",
    "high_risk_rows",
    "kpi_specific_default_scope_rows",
    "do_not_use_default_scope_rows",
    "excluded_reject_candidate_rows",
    "no_aliases_applied_confirmed",
    "no_values_applied_confirmed",
    "no_score_change_confirmed",
    "no_network_confirmed",
    "raw_master_mutation_performed",
]

ALIAS_REVIEW_REQUIRED_COLUMNS = [
    "alias_review_id",
    "source_review_id",
    "ticker",
    "isin",
    "company_name",
    "kpi_field",
    "required_concept_role",
    "missing_required_concept",
    "candidate_sec_concept",
    "candidate_label",
    "candidate_description",
    "available_annual_periods",
    "first_available_fiscal_year",
    "last_available_fiscal_year",
    "available_period_count",
    "alias_candidate_status",
    "alias_risk_level",
    "semantic_match_reason",
    "semantic_risk_reason",
    "recommended_action",
    "source_artifact",
    "candidate_value_not_applied",
    "apply_status",
    "notes",
]
ALIAS_SUMMARY_REQUIRED_COLUMNS = ["no_aliases_applied_confirmed", "no_values_applied_confirmed", "no_score_change_confirmed", "no_network_confirmed", "raw_master_mutation_performed"]


@dataclass(frozen=True)
class SecConceptAliasApprovalInputResult:
    approval_input_path: Path
    summary_path: Path
    report_path: Path
    summary: dict[str, str]
    rows: list[dict[str, str]]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _require_file(path_value: str | Path, error_code: str) -> Path:
    path = resolve_repo_path(path_value)
    if not path.exists():
        raise RuntimeError(error_code)
    return path


def _require_columns(rows: list[dict[str, str]], required: list[str], source_name: str) -> None:
    if not rows:
        raise ValueError(f"{source_name} contains no rows")
    available = set(rows[0].keys())
    missing = [column for column in required if column not in available]
    if missing:
        raise ValueError(f"{source_name} missing required columns: {', '.join(sorted(missing))}")


def _machine_suggestion(alias_candidate_status: str) -> str:
    return "YES" if alias_candidate_status == "APPROVE_CANDIDATE" else "NO"


def _default_scope(alias_candidate_status: str, alias_risk_level: str) -> str:
    if alias_candidate_status == "APPROVE_CANDIDATE" and alias_risk_level == "LOW":
        return "KPI_SPECIFIC"
    return "DO_NOT_USE"


def build_approval_input_rows(alias_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for source in alias_rows:
        status = _clean(source.get("alias_candidate_status"))
        risk = _clean(source.get("alias_risk_level"))
        if status not in INCLUDED_STATUSES:
            continue
        machine_suggested = _machine_suggestion(status)
        rows.append(
            {
                "approval_input_id": "",
                "source_alias_review_id": _clean(source.get("alias_review_id")),
                "source_review_id": _clean(source.get("source_review_id")),
                "ticker": _clean(source.get("ticker")),
                "isin": _clean(source.get("isin")),
                "company_name": _clean(source.get("company_name")),
                "kpi_field": _clean(source.get("kpi_field")),
                "required_concept_role": _clean(source.get("required_concept_role")),
                "missing_required_concept": _clean(source.get("missing_required_concept")),
                "candidate_sec_concept": _clean(source.get("candidate_sec_concept")),
                "candidate_label": _clean(source.get("candidate_label")),
                "candidate_description": _clean(source.get("candidate_description")),
                "available_annual_periods": _clean(source.get("available_annual_periods")),
                "first_available_fiscal_year": _clean(source.get("first_available_fiscal_year")),
                "last_available_fiscal_year": _clean(source.get("last_available_fiscal_year")),
                "available_period_count": _clean(source.get("available_period_count")),
                "alias_candidate_status": status,
                "alias_risk_level": risk,
                "machine_suggested_approval": machine_suggested,
                "human_approval_status": "PENDING_REVIEW",
                "approval_scope": _default_scope(status, risk),
                "approval_rationale": "",
                "reviewer_notes": "",
                "reviewer_name": "",
                "review_date": "",
                "semantic_match_reason": _clean(source.get("semantic_match_reason")),
                "semantic_risk_reason": _clean(source.get("semantic_risk_reason")),
                "recommended_action": _clean(source.get("recommended_action")),
                "source_artifact": _clean(source.get("source_artifact")),
                "candidate_value_not_applied": "True",
                "apply_status": "PENDING_HUMAN_REVIEW",
                "notes": "Human approval input only; no alias, KPI value, score, or master mutation was applied.",
            }
        )
    rows.sort(
        key=lambda row: (
            MACHINE_ORDER.get(row["machine_suggested_approval"], 99),
            RISK_ORDER.get(row["alias_risk_level"], 99),
            row["ticker"],
            row["isin"],
            row["kpi_field"],
            row["required_concept_role"],
            row["candidate_sec_concept"],
        )
    )
    for index, row in enumerate(rows, start=1):
        row["approval_input_id"] = f"SEC_ALIAS_APPROVAL_INPUT_{index:04d}"
    return rows


def build_summary(rows: list[dict[str, str]], alias_rows: list[dict[str, str]], alias_summary_rows: list[dict[str, str]]) -> dict[str, str]:
    risk_counts = Counter(row["alias_risk_level"] for row in rows)
    human_counts = Counter(row["human_approval_status"] for row in rows)
    scope_counts = Counter(row["approval_scope"] for row in rows)
    source_summary = alias_summary_rows[0] if alias_summary_rows else {}
    return {
        "total_approval_input_rows": str(len(rows)),
        "source_alias_review_rows": str(len(alias_rows)),
        "machine_suggested_approval_rows": str(sum(1 for row in rows if row["machine_suggested_approval"] == "YES")),
        "pending_review_rows": str(human_counts.get("PENDING_REVIEW", 0)),
        "approved_rows": str(human_counts.get("APPROVED", 0)),
        "rejected_rows": str(human_counts.get("REJECTED", 0)),
        "needs_more_evidence_rows": str(human_counts.get("NEEDS_MORE_EVIDENCE", 0)),
        "low_risk_rows": str(risk_counts.get("LOW", 0)),
        "medium_risk_rows": str(risk_counts.get("MEDIUM", 0)),
        "high_risk_rows": str(risk_counts.get("HIGH", 0)),
        "kpi_specific_default_scope_rows": str(scope_counts.get("KPI_SPECIFIC", 0)),
        "do_not_use_default_scope_rows": str(scope_counts.get("DO_NOT_USE", 0)),
        "excluded_reject_candidate_rows": str(sum(1 for row in alias_rows if _clean(row.get("alias_candidate_status")) == "REJECT_CANDIDATE")),
        "no_aliases_applied_confirmed": "True",
        "no_values_applied_confirmed": "True",
        "no_score_change_confirmed": _clean(source_summary.get("no_score_change_confirmed")) or "True",
        "no_network_confirmed": _clean(source_summary.get("no_network_confirmed")) or "True",
        "raw_master_mutation_performed": _clean(source_summary.get("raw_master_mutation_performed")) or "False",
    }


def render_report(summary: dict[str, str], rows: list[dict[str, str]]) -> str:
    lines = [
        "# SEC Concept Alias Approval Input",
        "",
        "## Executive Summary",
        "",
        f"- Rows prepared for human review: {summary['total_approval_input_rows']}",
        f"- Machine-suggested approval rows: {summary['machine_suggested_approval_rows']}",
        f"- Pending-review rows: {summary['pending_review_rows']}",
        f"- Low-risk rows: {summary['low_risk_rows']}",
        f"- Medium-risk rows: {summary['medium_risk_rows']}",
        f"- High-risk rows: {summary['high_risk_rows']}",
        f"- Excluded reject-candidate rows: {summary['excluded_reject_candidate_rows']}",
        "- No aliases were applied.",
        "- No KPI values were applied.",
        f"- No scores were changed: {summary['no_score_change_confirmed']}",
        f"- No network fetch was used: {summary['no_network_confirmed']}",
        "",
        "## Manual Fill Instructions",
        "",
        "- Set `human_approval_status` to one of `APPROVED`, `REJECTED`, or `NEEDS_MORE_EVIDENCE` after review.",
        "- Keep `PENDING_REVIEW` until the alias decision is complete.",
        "- Fill `approval_rationale`, `reviewer_notes`, `reviewer_name`, and `review_date` manually.",
        "- Keep `approval_scope=DO_NOT_USE` unless the alias is explicitly approved for the stated KPI/role scope.",
        "- Do not enter KPI values in this file.",
        "",
        "## Rows Prepared",
        "",
    ]
    for row in rows:
        lines.append(
            f"- `{row['approval_input_id']}` `{row['company_name']}` `{row['kpi_field']}` "
            f"`{row['candidate_sec_concept']}` machine={row['machine_suggested_approval']} "
            f"risk={row['alias_risk_level']} scope={row['approval_scope']}"
        )
    lines.extend(
        [
            "",
            "## Recommended Next Patch",
            "",
            "PRIVATE SEC CONCEPT ALIAS APPROVAL FILL / HUMAN DECISIONS ONLY / NO VALUE APPLY",
            "",
            "## Guardrails",
            "",
            "- no_aliases_applied_confirmed=True",
            "- no_values_applied_confirmed=True",
            "- no_score_change_confirmed=True",
            "- no_network_confirmed=True",
            "- raw_master_mutation_performed=False",
        ]
    )
    return "\n".join(lines) + "\n"


def run_personal_sec_concept_alias_approval_input(
    *,
    alias_review_table: str | Path = DEFAULT_ALIAS_REVIEW_TABLE,
    alias_review_summary: str | Path = DEFAULT_ALIAS_REVIEW_SUMMARY,
    output: str | Path = DEFAULT_OUTPUT,
    summary_output: str | Path = DEFAULT_SUMMARY_OUTPUT,
    report_output: str | Path = DEFAULT_REPORT_OUTPUT,
) -> SecConceptAliasApprovalInputResult:
    _require_file(alias_review_table, "MISSING_SEC_CONCEPT_ALIAS_REVIEW_TABLE")
    _require_file(alias_review_summary, "MISSING_SEC_CONCEPT_ALIAS_REVIEW_TABLE_SUMMARY")
    alias_rows = read_csv_rows(alias_review_table)
    alias_summary_rows = read_csv_rows(alias_review_summary)
    _require_columns(alias_rows, ALIAS_REVIEW_REQUIRED_COLUMNS, f"alias review table ({alias_review_table})")
    _require_columns(alias_summary_rows, ALIAS_SUMMARY_REQUIRED_COLUMNS, f"alias review summary ({alias_review_summary})")
    rows = build_approval_input_rows(alias_rows)
    summary = build_summary(rows, alias_rows, alias_summary_rows)
    approval_input_path = write_csv_rows(output, APPROVAL_INPUT_FIELDS, rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, [summary])
    report_path = ensure_parent_dir(report_output)
    report_path.write_text(render_report(summary, rows), encoding="utf-8")
    return SecConceptAliasApprovalInputResult(
        approval_input_path=resolve_repo_path(approval_input_path),
        summary_path=resolve_repo_path(summary_path),
        report_path=resolve_repo_path(report_path),
        summary=summary,
        rows=rows,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SEC concept alias human approval input without applying aliases.")
    parser.add_argument("--alias-review-table", default=DEFAULT_ALIAS_REVIEW_TABLE)
    parser.add_argument("--alias-review-summary", default=DEFAULT_ALIAS_REVIEW_SUMMARY)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_concept_alias_approval_input(
        alias_review_table=args.alias_review_table,
        alias_review_summary=args.alias_review_summary,
        output=args.output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    print(f"approval_input={result.approval_input_path}")
    print(f"approval_input_summary={result.summary_path}")
    print(f"approval_input_report={result.report_path}")
    print(f"total_approval_input_rows={result.summary['total_approval_input_rows']}")


if __name__ == "__main__":
    main()
