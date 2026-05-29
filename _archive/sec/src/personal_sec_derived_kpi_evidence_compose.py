from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, read_csv_rows, resolve_repo_path, write_csv_rows
from src.fundamentals_evidence_engine import EVIDENCE_REGISTRY_FIELDS

DEFAULT_PROPOSALS = "data/processed/personal_sec_derived_kpi_proposals.csv"
DEFAULT_PROPOSAL_INPUTS = "data/processed/personal_sec_derived_kpi_proposal_inputs.csv"
DEFAULT_OUTPUT_DIR = "data/processed"
DEFAULT_REPORT_DIR = "reports/2026-04-27"

EVIDENCE_PROPOSALS_FILENAME = "personal_sec_derived_kpi_evidence_proposals.csv"
REGISTRY_APPEND_FILENAME = "personal_sec_derived_kpi_evidence_registry_append.csv"
SUMMARY_FILENAME = "personal_sec_derived_kpi_evidence_compose_summary.csv"
SKIPPED_FILENAME = "personal_sec_derived_kpi_evidence_compose_skipped.csv"
REPORT_FILENAME = "personal_sec_derived_kpi_evidence_compose_report.md"

READY_STATUS = "READY_FOR_EVIDENCE_COMPOSE"
SOURCE_STATUS = "APPROVED_COMPANYFACTS_CONCEPTS_ONLY"
SOURCE_TYPE = "SEC_COMPANYFACTS_DERIVED_KPI"
SOURCE_NAME = "SEC CompanyFacts"

PROPOSAL_FIELDS = [
    "evidence_id",
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "proposed_value",
    "proposed_value_unit",
    "proposed_value_format",
    "evidence_source_type",
    "evidence_source_name",
    "evidence_source_artifact",
    "source_sec_concepts",
    "source_units",
    "source_forms",
    "source_filed_dates",
    "fiscal_year_start",
    "fiscal_year_end",
    "periods_used",
    "calculation_method",
    "calculation_inputs_summary",
    "confidence",
    "evidence_status",
    "apply_status",
    "review_status",
    "no_imputation_confirmed",
    "no_master_mutation_confirmed",
    "notes",
]

REGISTRY_APPEND_EXTRA_FIELDS = [
    "proposal_evidence_id",
    "apply_status",
    "review_status",
    "sec_lineage_source_artifact",
    "source_sec_concepts",
    "source_units",
    "source_forms",
    "source_filed_dates",
    "calculation_method",
    "calculation_inputs_summary",
    "no_master_mutation_confirmed",
    "no_imputation_confirmed",
]

REGISTRY_APPEND_FIELDS = [*EVIDENCE_REGISTRY_FIELDS, *REGISTRY_APPEND_EXTRA_FIELDS]

SUMMARY_FIELDS = [
    "ready_proposals_input",
    "evidence_proposals_created",
    "registry_append_rows",
    "proposals_skipped",
    "proposals_rejected",
    "holdings_count",
    "kpi_fields_count",
    "no_network_confirmed",
    "no_score_change_confirmed",
    "no_master_mutation_confirmed",
    "no_imputation_confirmed",
]

SKIPPED_FIELDS = [
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "skip_reason",
    "source_proposal_status",
    "source_review_required",
    "next_action",
]

REQUIRED_PROPOSAL_COLUMNS = [
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "derived_value",
    "derived_value_unit",
    "derived_value_format",
    "fiscal_year_start",
    "fiscal_year_end",
    "periods_used",
    "source_sec_concepts",
    "source_units",
    "source_forms",
    "source_filed_dates",
    "calculation_method",
    "calculation_inputs_summary",
    "approval_source_status",
    "evidence_status",
    "proposal_status",
    "review_required",
    "no_imputation_confirmed",
    "source_artifact",
]


@dataclass(frozen=True)
class EvidenceComposeResult:
    evidence_proposals_path: Path
    registry_append_path: Path
    summary_path: Path
    skipped_path: Path
    report_path: Path
    summary: dict[str, str]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _upper(value: Any) -> str:
    return _clean(value).upper()


def _is_true(value: Any) -> bool:
    return _clean(value).lower() in {"1", "true", "yes", "y"}


def _split_list(value: str) -> list[str]:
    return [part.strip() for part in _clean(value).split(";") if part.strip()]


def _is_private_or_sensitive_path(value: str) -> bool:
    text = _clean(value).replace("\\", "/").lower()
    return (
        "data/raw/private/" in text
        or "sec_user_agent" in text
        or "user_agent" in text
        or text.endswith(".env")
        or "/.env" in text
    )


def sanitize_artifact_reference(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    if _is_private_or_sensitive_path(text):
        return "<private_artifact>"
    return text.replace("\\", "/")


def _sanitize_report_text(value: str) -> str:
    text = sanitize_artifact_reference(value)
    text = re.sub(r"data/raw/private/[^`\s,;)]+", "<private_artifact>", text, flags=re.IGNORECASE)
    text = re.sub(r"[^`\s,;)]+sec_user_agent[^`\s,;)]*", "<private_artifact>", text, flags=re.IGNORECASE)
    return text


def _require_columns(rows: list[dict[str, str]], required_columns: list[str], source_name: str) -> None:
    if not rows:
        raise RuntimeError("NO_READY_SEC_DERIVED_KPI_PROPOSALS")
    available = set(rows[0].keys())
    missing = [column for column in required_columns if column not in available]
    if missing:
        raise ValueError(f"{source_name} missing required columns: {', '.join(sorted(missing))}")


def _is_ready_candidate(row: dict[str, str]) -> bool:
    return (
        _upper(row.get("proposal_status")) == READY_STATUS
        and _upper(row.get("evidence_status")) == "PROPOSAL_ONLY_NOT_APPLIED"
        and not _is_true(row.get("review_required"))
        and _is_true(row.get("no_imputation_confirmed"))
    )


def _validate_ready_row(row: dict[str, str]) -> str:
    for field in ["holding_name", "isin", "kpi_field", "derived_value", "source_sec_concepts", "source_artifact"]:
        if not _clean(row.get(field)):
            return f"MISSING_{field.upper()}"
    try:
        float(_clean(row.get("derived_value")))
    except ValueError:
        return "NON_NUMERIC_DERIVED_VALUE"
    if _upper(row.get("approval_source_status")) != SOURCE_STATUS:
        return "APPROVAL_SOURCE_STATUS_NOT_APPROVED"
    if _upper(row.get("proposal_status")) != READY_STATUS:
        return "SOURCE_PROPOSAL_NOT_READY"
    return ""


def _evidence_id(row: dict[str, str]) -> str:
    isin = re.sub(r"[^A-Za-z0-9]+", "_", _upper(row.get("isin"))).strip("_")
    kpi = re.sub(r"[^A-Za-z0-9]+", "_", _clean(row.get("kpi_field"))).strip("_").lower()
    fiscal_year = re.sub(r"[^0-9]+", "", _clean(row.get("fiscal_year_end"))) or "na"
    return f"SEC_DERIVED__{isin}__{kpi}__FY{fiscal_year}"


def _latest_filed_date(row: dict[str, str]) -> str:
    dates = sorted(_split_list(row.get("source_filed_dates", "")))
    return dates[-1] if dates else ""


def _confidence(row: dict[str, str]) -> str:
    forms = {_upper(form) for form in _split_list(row.get("source_forms", ""))}
    if forms and forms <= {"10-K", "10-K/A"} and _is_true(row.get("no_imputation_confirmed")):
        return "HIGH"
    if _clean(row.get("periods_used")) and _is_true(row.get("no_imputation_confirmed")):
        return "MEDIUM"
    return "LOW"


def build_evidence_proposal_row(row: dict[str, str]) -> dict[str, str]:
    confidence = _confidence(row)
    return {
        "evidence_id": _evidence_id(row),
        "holding_name": _clean(row.get("holding_name")),
        "ticker": _clean(row.get("ticker")),
        "isin": _upper(row.get("isin")),
        "kpi_field": _clean(row.get("kpi_field")),
        "proposed_value": _clean(row.get("derived_value")),
        "proposed_value_unit": _clean(row.get("derived_value_unit")),
        "proposed_value_format": _clean(row.get("derived_value_format")),
        "evidence_source_type": SOURCE_TYPE,
        "evidence_source_name": SOURCE_NAME,
        "evidence_source_artifact": sanitize_artifact_reference(row.get("source_artifact", "")),
        "source_sec_concepts": _clean(row.get("source_sec_concepts")),
        "source_units": _clean(row.get("source_units")),
        "source_forms": _clean(row.get("source_forms")),
        "source_filed_dates": _clean(row.get("source_filed_dates")),
        "fiscal_year_start": _clean(row.get("fiscal_year_start")),
        "fiscal_year_end": _clean(row.get("fiscal_year_end")),
        "periods_used": _clean(row.get("periods_used")),
        "calculation_method": _clean(row.get("calculation_method")),
        "calculation_inputs_summary": _clean(row.get("calculation_inputs_summary")),
        "confidence": confidence,
        "evidence_status": "COMPOSED_PROPOSAL_ONLY",
        "apply_status": "NOT_APPLIED",
        "review_status": "READY_FOR_REVIEWED_EVIDENCE_APPLY" if confidence in {"HIGH", "MEDIUM"} else "REVIEW_REQUIRED",
        "no_imputation_confirmed": "True",
        "no_master_mutation_confirmed": "True",
        "notes": "SEC derived KPI evidence proposal only; no evidence apply, master mutation, score change, or imputation performed.",
    }


def build_registry_append_row(proposal: dict[str, str]) -> dict[str, str]:
    source_reference = (
        f"{proposal['kpi_field']} from {proposal['source_sec_concepts']} "
        f"FY{proposal['fiscal_year_end']} periods={proposal['periods_used']}"
    )
    registry_row = {
        "ticker": proposal["ticker"],
        "isin": proposal["isin"],
        "company_name": proposal["holding_name"],
        "company_type_profile": "",
        "kpi_name": proposal["kpi_field"],
        "applicability": "REQUIRED",
        "source_type": SOURCE_TYPE,
        "source_name": SOURCE_NAME,
        "source_reference": source_reference,
        "source_section": "",
        "source_page": "",
        "source_as_of_date": _latest_filed_date(
            {
                "source_filed_dates": proposal["source_filed_dates"],
            }
        ),
        "fiscal_year": proposal["fiscal_year_end"],
        "verification_status": "REVIEW",
        "data_quality_flag": "REVIEW",
        "evidence_present": "True",
        "reported_value": proposal["proposed_value"],
        "reported_unit": proposal["proposed_value_unit"],
        "currency": "",
        "evidence_identity": proposal["evidence_id"],
        "notes": "Append-ready SEC derived KPI evidence proposal. Review required before any apply step.",
        "proposal_evidence_id": proposal["evidence_id"],
        "apply_status": proposal["apply_status"],
        "review_status": proposal["review_status"],
        "sec_lineage_source_artifact": proposal["evidence_source_artifact"],
        "source_sec_concepts": proposal["source_sec_concepts"],
        "source_units": proposal["source_units"],
        "source_forms": proposal["source_forms"],
        "source_filed_dates": proposal["source_filed_dates"],
        "calculation_method": proposal["calculation_method"],
        "calculation_inputs_summary": proposal["calculation_inputs_summary"],
        "no_master_mutation_confirmed": proposal["no_master_mutation_confirmed"],
        "no_imputation_confirmed": proposal["no_imputation_confirmed"],
    }
    return registry_row


def _sort_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (_upper(row.get("isin")), _clean(row.get("kpi_field")), _clean(row.get("evidence_id")))


def _write_report(
    path_value: str | Path,
    *,
    summary: dict[str, str],
    proposals: list[dict[str, str]],
    skipped: list[dict[str, str]],
    proposals_path: str | Path,
    proposal_inputs_path: str | Path,
) -> Path:
    lines = [
        "# SEC Derived KPI Evidence Compose",
        "",
        "## Executive Summary",
        "",
        f"- Ready SEC derived KPI proposals input: {summary['ready_proposals_input']}",
        f"- Evidence proposals created: {summary['evidence_proposals_created']}",
        f"- Registry append rows: {summary['registry_append_rows']}",
        "- Evidence apply was not executed.",
        "- Fundamentals master, scoring, website, and private raw files were not mutated.",
        "",
        "## Scope",
        "",
        f"- Proposals input: `{_sanitize_report_text(str(proposals_path))}`",
        f"- Proposal inputs lineage: `{_sanitize_report_text(str(proposal_inputs_path))}`",
        "- Filter: proposal_status=READY_FOR_EVIDENCE_COMPOSE, evidence_status=PROPOSAL_ONLY_NOT_APPLIED, review_required=False, no_imputation_confirmed=True.",
        "",
        "## Ready Proposals Used",
        "",
    ]
    if proposals:
        for row in proposals:
            lines.append(
                f"- `{row['holding_name']}` `{row['kpi_field']}` value={row['proposed_value']} "
                f"confidence={row['confidence']} apply_status={row['apply_status']}"
            )
    else:
        lines.append("- None.")

    lines.extend(["", "## Evidence Proposals Created", ""])
    if proposals:
        for row in proposals:
            lines.append(f"- `{row['evidence_id']}` source={row['source_sec_concepts']} forms={row['source_forms']}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Skipped/Rejections", ""])
    if skipped:
        for row in skipped:
            lines.append(f"- `{row.get('holding_name', '')}` `{row.get('kpi_field', '')}`: {row.get('skip_reason', '')}")
    else:
        lines.append("- No source proposal rows were skipped by this compose step.")

    lines.extend(
        [
            "",
            "## Existing Evidence-System Compatibility",
            "",
            "- The registry append artifact preserves the existing fundamentals evidence registry fields.",
            "- SEC lineage fields are appended after the existing registry contract fields.",
            "- The existing registry and apply artifacts are not mutated.",
            "",
            "## Guardrail Confirmation",
            "",
            "- no_network_confirmed=True",
            "- no_score_change_confirmed=True",
            "- no_master_mutation_confirmed=True",
            "- no_imputation_confirmed=True",
            "- no_evidence_apply_confirmed=True",
            "- no_private_raw_paths_in_report=True",
            "",
            "## Next Recommended Patch",
            "",
            "SEC DERIVED KPI REVIEWED EVIDENCE APPLY / APPROVED PROPOSALS ONLY / NO SCORE CHANGES",
        ]
    )
    path = ensure_parent_dir(path_value)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_personal_sec_derived_kpi_evidence_compose(
    *,
    proposals: str | Path = DEFAULT_PROPOSALS,
    proposal_inputs: str | Path = DEFAULT_PROPOSAL_INPUTS,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> EvidenceComposeResult:
    proposal_path = resolve_repo_path(proposals)
    proposal_inputs_path = resolve_repo_path(proposal_inputs)
    if not proposal_path.exists():
        raise RuntimeError("MISSING_SEC_DERIVED_KPI_PROPOSALS")
    if not proposal_inputs_path.exists():
        raise RuntimeError("MISSING_SEC_DERIVED_KPI_PROPOSAL_INPUTS")

    source_rows = read_csv_rows(proposal_path)
    _require_columns(source_rows, REQUIRED_PROPOSAL_COLUMNS, f"SEC derived KPI proposals ({proposals})")

    ready_candidates = [row for row in source_rows if _is_ready_candidate(row)]
    if not ready_candidates:
        raise RuntimeError("NO_READY_SEC_DERIVED_KPI_PROPOSALS")

    evidence_rows: list[dict[str, str]] = []
    skipped_rows: list[dict[str, str]] = []
    rejected_count = 0
    for row in source_rows:
        if not _is_ready_candidate(row):
            skipped_rows.append(
                {
                    "holding_name": _clean(row.get("holding_name")),
                    "ticker": _clean(row.get("ticker")),
                    "isin": _upper(row.get("isin")),
                    "kpi_field": _clean(row.get("kpi_field")),
                    "skip_reason": "SOURCE_PROPOSAL_NOT_READY_FOR_EVIDENCE_COMPOSE",
                    "source_proposal_status": _clean(row.get("proposal_status")),
                    "source_review_required": _clean(row.get("review_required")),
                    "next_action": "SEC_DERIVED_KPI_CALCULATION_GAP_REVIEW",
                }
            )
            continue
        invalid_reason = _validate_ready_row(row)
        if invalid_reason:
            rejected_count += 1
            skipped_rows.append(
                {
                    "holding_name": _clean(row.get("holding_name")),
                    "ticker": _clean(row.get("ticker")),
                    "isin": _upper(row.get("isin")),
                    "kpi_field": _clean(row.get("kpi_field")),
                    "skip_reason": invalid_reason,
                    "source_proposal_status": _clean(row.get("proposal_status")),
                    "source_review_required": _clean(row.get("review_required")),
                    "next_action": "SEC_DERIVED_KPI_EVIDENCE_COMPOSE_GAP_REVIEW",
                }
            )
            continue
        evidence_rows.append(build_evidence_proposal_row(row))

    evidence_rows = sorted(evidence_rows, key=_sort_key)
    registry_rows = [build_registry_append_row(row) for row in evidence_rows]
    registry_rows = sorted(registry_rows, key=lambda row: (_upper(row.get("isin")), _clean(row.get("kpi_name"))))
    skipped_rows = sorted(skipped_rows, key=lambda row: (_upper(row.get("isin")), _clean(row.get("kpi_field")), _clean(row.get("skip_reason"))))

    output_root = resolve_repo_path(output_dir)
    report_root = resolve_repo_path(report_dir)
    evidence_path = output_root / EVIDENCE_PROPOSALS_FILENAME
    registry_path = output_root / REGISTRY_APPEND_FILENAME
    summary_path = output_root / SUMMARY_FILENAME
    skipped_path = output_root / SKIPPED_FILENAME
    report_path = report_root / REPORT_FILENAME

    summary = {
        "ready_proposals_input": str(len(ready_candidates)),
        "evidence_proposals_created": str(len(evidence_rows)),
        "registry_append_rows": str(len(registry_rows)),
        "proposals_skipped": str(len(skipped_rows)),
        "proposals_rejected": str(rejected_count),
        "holdings_count": str(len({_upper(row.get("isin")) for row in evidence_rows})),
        "kpi_fields_count": str(len({_clean(row.get("kpi_field")) for row in evidence_rows})),
        "no_network_confirmed": "True",
        "no_score_change_confirmed": "True",
        "no_master_mutation_confirmed": "True",
        "no_imputation_confirmed": "True",
    }

    write_csv_rows(evidence_path, PROPOSAL_FIELDS, evidence_rows)
    write_csv_rows(registry_path, REGISTRY_APPEND_FIELDS, registry_rows)
    write_csv_rows(summary_path, SUMMARY_FIELDS, [summary])
    write_csv_rows(skipped_path, SKIPPED_FIELDS, skipped_rows)
    _write_report(
        report_path,
        summary=summary,
        proposals=evidence_rows,
        skipped=skipped_rows,
        proposals_path=proposals,
        proposal_inputs_path=proposal_inputs,
    )
    return EvidenceComposeResult(
        evidence_proposals_path=resolve_repo_path(evidence_path),
        registry_append_path=resolve_repo_path(registry_path),
        summary_path=resolve_repo_path(summary_path),
        skipped_path=resolve_repo_path(skipped_path),
        report_path=resolve_repo_path(report_path),
        summary=summary,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose SEC derived KPI proposals into review-gated fundamentals evidence proposals.")
    parser.add_argument("--proposals", default=DEFAULT_PROPOSALS, help="SEC derived KPI proposals CSV.")
    parser.add_argument("--proposal-inputs", default=DEFAULT_PROPOSAL_INPUTS, help="SEC derived KPI proposal-inputs lineage CSV.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Processed output directory.")
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR, help="Report output directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_personal_sec_derived_kpi_evidence_compose(
        proposals=args.proposals,
        proposal_inputs=args.proposal_inputs,
        output_dir=args.output_dir,
        report_dir=args.report_dir,
    )


if __name__ == "__main__":
    main()
