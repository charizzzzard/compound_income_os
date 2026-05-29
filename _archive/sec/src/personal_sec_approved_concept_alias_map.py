from __future__ import annotations

import argparse
import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, read_csv_rows, resolve_repo_path, write_csv_rows

DEFAULT_PRIVATE_APPROVAL = "data/raw/private/fundamentals/personal_sec_concept_alias_approval_filled.csv"
DEFAULT_PROCESSED_APPROVAL = "data/processed/personal_sec_concept_alias_approval_filled.csv"
DEFAULT_APPROVAL_INPUT = "data/processed/personal_sec_concept_alias_approval_input.csv"
DEFAULT_OUTPUT = "data/processed/personal_sec_approved_concept_alias_map.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_sec_approved_concept_alias_map_summary.csv"
DEFAULT_INVALID_OUTPUT = "data/processed/personal_sec_approved_concept_alias_map_invalid_rows.csv"
DEFAULT_REPORT_OUTPUT = "reports/2026-04-28/personal_sec_approved_concept_alias_map_report.md"

MAP_FIELDS = [
    "approved_alias_id",
    "source_approval_input_id",
    "source_alias_review_id",
    "source_review_id",
    "ticker",
    "isin",
    "company_name",
    "kpi_field",
    "required_concept_role",
    "missing_required_concept",
    "approved_sec_concept",
    "approved_label",
    "approval_scope",
    "alias_risk_level",
    "human_approval_status",
    "approval_rationale",
    "reviewer_name",
    "review_date",
    "source_artifact",
    "active_for_period_selection",
    "notes",
]

SUMMARY_FIELDS = [
    "source_input_path",
    "source_input_sha256",
    "approval_input_rows",
    "approved_alias_rows",
    "pending_review_rows",
    "rejected_rows",
    "needs_more_evidence_rows",
    "invalid_approved_rows",
    "active_for_period_selection_rows",
    "candidate_values_applied",
    "no_values_applied_confirmed",
    "no_score_change_confirmed",
    "no_network_confirmed",
    "raw_master_mutation_performed",
]

INVALID_FIELDS = [
    "approval_input_id",
    "source_alias_review_id",
    "source_review_id",
    "ticker",
    "isin",
    "kpi_field",
    "candidate_sec_concept",
    "human_approval_status",
    "approval_scope",
    "alias_risk_level",
    "invalid_reason",
]

REQUIRED_COLUMNS = [
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
    "alias_risk_level",
    "human_approval_status",
    "approval_scope",
    "approval_rationale",
    "reviewer_name",
    "review_date",
    "source_artifact",
    "candidate_value_not_applied",
]


@dataclass(frozen=True)
class ApprovedConceptAliasMapResult:
    source_input_path: Path
    source_input_sha256: str
    map_path: Path
    summary_path: Path
    invalid_path: Path
    report_path: Path
    summary: dict[str, str]
    map_rows: list[dict[str, str]]
    invalid_rows: list[dict[str, str]]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _select_source_path(
    private_approval: str | Path = DEFAULT_PRIVATE_APPROVAL,
    processed_approval: str | Path = DEFAULT_PROCESSED_APPROVAL,
    approval_input: str | Path = DEFAULT_APPROVAL_INPUT,
) -> Path:
    for path_value in (private_approval, processed_approval, approval_input):
        path = resolve_repo_path(path_value)
        if path.exists():
            return path
    raise RuntimeError("MISSING_FILLED_ALIAS_APPROVAL_INPUT")


def _require_columns(rows: list[dict[str, str]], required: list[str], source_name: str) -> None:
    if not rows:
        raise ValueError(f"{source_name} contains no rows")
    available = set(rows[0].keys())
    missing = [column for column in required if column not in available]
    if missing:
        raise ValueError(f"{source_name} missing required columns: {', '.join(sorted(missing))}")


def _invalid_reason(row: dict[str, str]) -> str:
    reasons: list[str] = []
    if _clean(row.get("approval_scope")) == "DO_NOT_USE":
        reasons.append("APPROVAL_SCOPE_DO_NOT_USE")
    if not _clean(row.get("approval_rationale")):
        reasons.append("MISSING_APPROVAL_RATIONALE")
    if _clean(row.get("required_concept_role")) in {"", "UNKNOWN"}:
        reasons.append("UNKNOWN_REQUIRED_CONCEPT_ROLE")
    if _clean(row.get("alias_risk_level")) == "HIGH" and (_clean(row.get("approval_scope")) != "HOLDING_SPECIFIC" or not _clean(row.get("approval_rationale"))):
        reasons.append("HIGH_RISK_APPROVAL_REQUIRES_HOLDING_SCOPE_AND_RATIONALE")
    return ";".join(reasons)


def build_map_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    approved = [row for row in rows if _clean(row.get("human_approval_status")) == "APPROVED"]
    approved.sort(key=lambda row: (_clean(row.get("ticker")), _clean(row.get("isin")), _clean(row.get("kpi_field")), _clean(row.get("required_concept_role")), _clean(row.get("candidate_sec_concept"))))
    map_rows: list[dict[str, str]] = []
    invalid_rows: list[dict[str, str]] = []
    for index, row in enumerate(approved, start=1):
        invalid_reason = _invalid_reason(row)
        if invalid_reason:
            invalid_rows.append(
                {
                    "approval_input_id": _clean(row.get("approval_input_id")),
                    "source_alias_review_id": _clean(row.get("source_alias_review_id")),
                    "source_review_id": _clean(row.get("source_review_id")),
                    "ticker": _clean(row.get("ticker")),
                    "isin": _clean(row.get("isin")),
                    "kpi_field": _clean(row.get("kpi_field")),
                    "candidate_sec_concept": _clean(row.get("candidate_sec_concept")),
                    "human_approval_status": _clean(row.get("human_approval_status")),
                    "approval_scope": _clean(row.get("approval_scope")),
                    "alias_risk_level": _clean(row.get("alias_risk_level")),
                    "invalid_reason": invalid_reason,
                }
            )
        map_rows.append(
            {
                "approved_alias_id": f"SEC_APPROVED_ALIAS_{index:04d}",
                "source_approval_input_id": _clean(row.get("approval_input_id")),
                "source_alias_review_id": _clean(row.get("source_alias_review_id")),
                "source_review_id": _clean(row.get("source_review_id")),
                "ticker": _clean(row.get("ticker")),
                "isin": _clean(row.get("isin")),
                "company_name": _clean(row.get("company_name")),
                "kpi_field": _clean(row.get("kpi_field")),
                "required_concept_role": _clean(row.get("required_concept_role")),
                "missing_required_concept": _clean(row.get("missing_required_concept")),
                "approved_sec_concept": _clean(row.get("candidate_sec_concept")),
                "approved_label": _clean(row.get("candidate_label")),
                "approval_scope": _clean(row.get("approval_scope")),
                "alias_risk_level": _clean(row.get("alias_risk_level")),
                "human_approval_status": _clean(row.get("human_approval_status")),
                "approval_rationale": _clean(row.get("approval_rationale")),
                "reviewer_name": _clean(row.get("reviewer_name")),
                "review_date": _clean(row.get("review_date")),
                "source_artifact": _clean(row.get("source_artifact")),
                "active_for_period_selection": "False",
                "notes": "Approved semantic alias map only; inactive for period selection until a later explicit patch.",
            }
        )
    return map_rows, invalid_rows


def build_summary(source_path: Path, source_hash: str, rows: list[dict[str, str]], map_rows: list[dict[str, str]], invalid_rows: list[dict[str, str]]) -> dict[str, str]:
    counts = Counter(_clean(row.get("human_approval_status")) for row in rows)
    return {
        "source_input_path": str(source_path.relative_to(resolve_repo_path("."))).replace("\\", "/") if source_path.is_relative_to(resolve_repo_path(".")) else str(source_path),
        "source_input_sha256": source_hash,
        "approval_input_rows": str(len(rows)),
        "approved_alias_rows": str(len(map_rows)),
        "pending_review_rows": str(counts.get("PENDING_REVIEW", 0)),
        "rejected_rows": str(counts.get("REJECTED", 0)),
        "needs_more_evidence_rows": str(counts.get("NEEDS_MORE_EVIDENCE", 0)),
        "invalid_approved_rows": str(len(invalid_rows)),
        "active_for_period_selection_rows": str(sum(1 for row in map_rows if _clean(row.get("active_for_period_selection")) == "True")),
        "candidate_values_applied": "0",
        "no_values_applied_confirmed": "True",
        "no_score_change_confirmed": "True",
        "no_network_confirmed": "True",
        "raw_master_mutation_performed": "False",
    }


def render_report(summary: dict[str, str], map_rows: list[dict[str, str]], invalid_rows: list[dict[str, str]]) -> str:
    lines = [
        "# SEC Approved Concept Alias Map",
        "",
        "## Executive Summary",
        "",
        f"- Source input: `{summary['source_input_path']}`",
        f"- Approval input rows: {summary['approval_input_rows']}",
        f"- Approved alias rows: {summary['approved_alias_rows']}",
        f"- Invalid approved rows: {summary['invalid_approved_rows']}",
        "- Active for period selection rows: 0",
        "- No KPI values were applied.",
        "- No scores were changed.",
        "- No network fetch was used.",
        "",
        "## Approved Aliases",
        "",
    ]
    if map_rows:
        for row in map_rows:
            lines.append(f"- `{row['approved_alias_id']}` `{row['company_name']}` `{row['kpi_field']}` `{row['approved_sec_concept']}` scope={row['approval_scope']}")
    else:
        lines.append("- None.")
    lines.extend(["", "## Invalid Approved Rows", ""])
    if invalid_rows:
        for row in invalid_rows:
            lines.append(f"- `{row['approval_input_id']}` `{row['candidate_sec_concept']}`: {row['invalid_reason']}")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- active_for_period_selection=False for every row",
            "- candidate_values_applied=0",
            "- no_values_applied_confirmed=True",
            "- no_score_change_confirmed=True",
            "- no_network_confirmed=True",
            "",
            "## Next Recommended Patch",
            "",
            "SEC PERIOD-SELECTION ALIAS INTEGRATION / APPROVED MAP ONLY / NO VALUE APPLY",
        ]
    )
    return "\n".join(lines) + "\n"


def run_personal_sec_approved_concept_alias_map(
    *,
    private_approval: str | Path = DEFAULT_PRIVATE_APPROVAL,
    processed_approval: str | Path = DEFAULT_PROCESSED_APPROVAL,
    approval_input: str | Path = DEFAULT_APPROVAL_INPUT,
    output: str | Path = DEFAULT_OUTPUT,
    summary_output: str | Path = DEFAULT_SUMMARY_OUTPUT,
    invalid_output: str | Path = DEFAULT_INVALID_OUTPUT,
    report_output: str | Path = DEFAULT_REPORT_OUTPUT,
) -> ApprovedConceptAliasMapResult:
    source_path = _select_source_path(private_approval, processed_approval, approval_input)
    source_hash = _sha256(source_path)
    rows = read_csv_rows(source_path)
    _require_columns(rows, REQUIRED_COLUMNS, f"alias approval input ({source_path})")
    map_rows, invalid_rows = build_map_rows(rows)
    summary = build_summary(source_path, source_hash, rows, map_rows, invalid_rows)
    map_path = write_csv_rows(output, MAP_FIELDS, map_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, [summary])
    invalid_path = write_csv_rows(invalid_output, INVALID_FIELDS, invalid_rows)
    report_path = ensure_parent_dir(report_output)
    report_path.write_text(render_report(summary, map_rows, invalid_rows), encoding="utf-8")
    return ApprovedConceptAliasMapResult(
        source_input_path=source_path,
        source_input_sha256=source_hash,
        map_path=resolve_repo_path(map_path),
        summary_path=resolve_repo_path(summary_path),
        invalid_path=resolve_repo_path(invalid_path),
        report_path=resolve_repo_path(report_path),
        summary=summary,
        map_rows=map_rows,
        invalid_rows=invalid_rows,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate inactive approved SEC concept alias map from human-filled approval input.")
    parser.add_argument("--private-approval", default=DEFAULT_PRIVATE_APPROVAL)
    parser.add_argument("--processed-approval", default=DEFAULT_PROCESSED_APPROVAL)
    parser.add_argument("--approval-input", default=DEFAULT_APPROVAL_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--invalid-output", default=DEFAULT_INVALID_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_approved_concept_alias_map(
        private_approval=args.private_approval,
        processed_approval=args.processed_approval,
        approval_input=args.approval_input,
        output=args.output,
        summary_output=args.summary_output,
        invalid_output=args.invalid_output,
        report_output=args.report_output,
    )
    print(f"source_input_path={result.source_input_path}")
    print(f"source_input_sha256={result.source_input_sha256}")
    print(f"approved_alias_map={result.map_path}")
    print(f"approved_alias_rows={result.summary['approved_alias_rows']}")
    print(f"invalid_approved_rows={result.summary['invalid_approved_rows']}")


if __name__ == "__main__":
    main()
