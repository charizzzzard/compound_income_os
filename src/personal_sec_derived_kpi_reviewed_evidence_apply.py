from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, ensure_parent_dir, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows
from src.fundamentals_master import DEFAULT_PERSONAL_MASTER_PATH, PERSONAL_MASTER_FIELDS, validate_personal_fundamentals_master

DEFAULT_EVIDENCE_PROPOSALS = "data/processed/personal_sec_derived_kpi_evidence_proposals.csv"
DEFAULT_REGISTRY_APPEND = "data/processed/personal_sec_derived_kpi_evidence_registry_append.csv"
DEFAULT_OUTPUT_DIR = "data/processed"
DEFAULT_REPORT_DIR = "reports/2026-04-27"
DEFAULT_EVIDENCE_APPLIED_MASTER = "data/processed/personal_fundamentals_master_sec_derived_kpi_applied.csv"

APPLY_FILENAME = "personal_sec_derived_kpi_reviewed_evidence_apply.csv"
SUMMARY_FILENAME = "personal_sec_derived_kpi_reviewed_evidence_apply_summary.csv"
SKIPPED_FILENAME = "personal_sec_derived_kpi_reviewed_evidence_apply_skipped.csv"
REPORT_FILENAME = "personal_sec_derived_kpi_reviewed_evidence_apply_report.md"

APPLY_FIELDS = [
    "evidence_id",
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "old_value",
    "new_value",
    "proposed_value",
    "value_unit",
    "apply_status",
    "apply_reason",
    "evidence_source_type",
    "evidence_source_artifact",
    "confidence",
    "no_imputation_confirmed",
    "master_mutation_performed",
    "raw_master_mutation_performed",
    "score_mutation_performed",
]

SUMMARY_FIELDS = [
    "evidence_proposals_input",
    "proposals_eligible_for_apply",
    "proposals_applied",
    "proposals_skipped",
    "holdings_updated",
    "kpi_fields_updated",
    "raw_master_mutation_performed",
    "evidence_applied_master_written",
    "score_mutation_performed",
    "no_score_change_confirmed",
    "no_imputation_confirmed",
    "no_network_confirmed",
]

SKIPPED_FIELDS = [
    "evidence_id",
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "skip_reason",
    "confidence",
    "apply_status",
    "review_status",
    "next_action",
]

REQUIRED_PROPOSAL_COLUMNS = [
    "evidence_id",
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "proposed_value",
    "proposed_value_unit",
    "evidence_source_type",
    "evidence_source_artifact",
    "confidence",
    "evidence_status",
    "apply_status",
    "review_status",
    "no_imputation_confirmed",
]

ALLOWED_EXISTING_TARGET_VALUES = {"", "MISSING", "MISSING_DATA", "REVIEW", "N/A", "NA"}


@dataclass(frozen=True)
class ReviewedEvidenceApplyResult:
    apply_path: Path
    summary_path: Path
    skipped_path: Path
    evidence_applied_master_path: Path
    report_path: Path
    summary: dict[str, str]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _upper(value: Any) -> str:
    return safe_upper(value)


def _is_true(value: Any) -> bool:
    return _clean(value).lower() in {"1", "true", "yes", "y"}


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


def _read_csv_header(path_value: str | Path) -> list[str]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or [])


def _require_columns(rows: list[dict[str, str]], required_columns: list[str], source_name: str) -> None:
    if not rows:
        raise RuntimeError("NO_APPROVED_SEC_DERIVED_KPI_EVIDENCE_PROPOSALS")
    available = set(rows[0].keys())
    missing = [column for column in required_columns if column not in available]
    if missing:
        raise ValueError(f"{source_name} missing required columns: {', '.join(sorted(missing))}")


def _is_eligible(row: dict[str, str]) -> bool:
    if _upper(row.get("evidence_status")) != "COMPOSED_PROPOSAL_ONLY":
        return False
    if _upper(row.get("apply_status")) != "NOT_APPLIED":
        return False
    if _upper(row.get("review_status")) != "READY_FOR_REVIEWED_EVIDENCE_APPLY":
        return False
    if _upper(row.get("confidence")) != "HIGH":
        return False
    if not _is_true(row.get("no_imputation_confirmed")):
        return False
    if not _clean(row.get("isin")) or not _clean(row.get("kpi_field")):
        return False
    try:
        float(_clean(row.get("proposed_value")))
    except ValueError:
        return False
    return True


def _skip_row(row: dict[str, str], reason: str, next_action: str = "SEC_EVIDENCE_APPLY_CONFLICT_REVIEW") -> dict[str, str]:
    return {
        "evidence_id": _clean(row.get("evidence_id")),
        "holding_name": _clean(row.get("holding_name")),
        "ticker": _clean(row.get("ticker")),
        "isin": _upper(row.get("isin")),
        "kpi_field": _clean(row.get("kpi_field")),
        "skip_reason": reason,
        "confidence": _clean(row.get("confidence")),
        "apply_status": _clean(row.get("apply_status")),
        "review_status": _clean(row.get("review_status")),
        "next_action": next_action,
    }


def _master_index(master_rows: list[dict[str, str]]) -> tuple[dict[str, int], dict[str, list[int]]]:
    isin_index: dict[str, int] = {}
    ticker_index: dict[str, list[int]] = {}
    duplicate_isins: set[str] = set()
    for idx, row in enumerate(master_rows):
        isin = _upper(row.get("isin"))
        ticker = canonicalize_ticker(row.get("ticker", ""))
        if isin:
            if isin in isin_index:
                duplicate_isins.add(isin)
            else:
                isin_index[isin] = idx
        if ticker:
            ticker_index.setdefault(ticker, []).append(idx)
    for isin in duplicate_isins:
        isin_index.pop(isin, None)
    return isin_index, ticker_index


def _match_master_row(row: dict[str, str], master_rows: list[dict[str, str]], isin_index: dict[str, int], ticker_index: dict[str, list[int]]) -> int | None:
    isin = _upper(row.get("isin"))
    if isin and isin in isin_index:
        return isin_index[isin]

    ticker = canonicalize_ticker(row.get("ticker", ""))
    if not ticker:
        return None
    candidates = ticker_index.get(ticker, [])
    if len(candidates) != 1:
        return None
    candidate = master_rows[candidates[0]]
    if _clean(candidate.get("isin")):
        return None
    return candidates[0]


def _target_allows_update(value: Any) -> bool:
    return _upper(value) in ALLOWED_EXISTING_TARGET_VALUES


def _apply_sort_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (_upper(row.get("isin")), _clean(row.get("kpi_field")), _clean(row.get("evidence_id")))


def _write_report(
    path_value: str | Path,
    *,
    summary: dict[str, str],
    apply_rows: list[dict[str, str]],
    skipped_rows: list[dict[str, str]],
    evidence_proposals: str | Path,
    registry_append: str | Path,
    master_input: str | Path,
    evidence_applied_master: str | Path,
) -> Path:
    lines = [
        "# SEC Derived KPI Reviewed Evidence Apply",
        "",
        "## Executive Summary",
        "",
        f"- Evidence proposals input: {summary['evidence_proposals_input']}",
        f"- Eligible proposals: {summary['proposals_eligible_for_apply']}",
        f"- Applied proposals: {summary['proposals_applied']}",
        f"- Skipped proposals: {summary['proposals_skipped']}",
        "- Raw fundamentals master was not mutated.",
        "- Scores, monthly, watchlist, dashboard, and website artifacts were not regenerated.",
        "",
        "## Scope",
        "",
        f"- Evidence proposals: `{_sanitize_report_text(str(evidence_proposals))}`",
        f"- Registry append: `{_sanitize_report_text(str(registry_append))}`",
        f"- Master input: `{_sanitize_report_text(str(master_input))}`",
        f"- Evidence-applied master output: `{_sanitize_report_text(str(evidence_applied_master))}`",
        "",
        "## Applied Proposals",
        "",
    ]
    if apply_rows:
        for row in apply_rows:
            lines.append(
                f"- `{row['holding_name']}` `{row['kpi_field']}`: "
                f"{row['old_value'] or '<blank>'} -> {row['new_value']} ({row['confidence']})"
            )
    else:
        lines.append("- None.")

    lines.extend(["", "## Updated Holdings/KPIs", ""])
    if apply_rows:
        for row in sorted(apply_rows, key=_apply_sort_key):
            lines.append(f"- `{row['isin']}` `{row['kpi_field']}` apply_status={row['apply_status']}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Skipped Proposals", ""])
    if skipped_rows:
        for row in skipped_rows:
            lines.append(f"- `{row.get('holding_name', '')}` `{row.get('kpi_field', '')}`: {row.get('skip_reason', '')}")
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Master/Evidence Contract",
            "",
            "- Strict ISIN matching is used when possible.",
            "- Existing non-empty target KPI fields are not overwritten.",
            "- The output is a processed evidence-applied master copy, not a raw master mutation.",
            "",
            "## Guardrail Confirmation",
            "",
            "- no_network_confirmed=True",
            "- no_score_change_confirmed=True",
            "- raw_master_mutation_performed=False",
            "- score_mutation_performed=False",
            "- no_imputation_confirmed=True",
            "- no_private_raw_paths_in_report=True",
            "",
            "## Next Recommended Patch",
            "",
            "SEC CORE KPI CLOSURE IMPACT RERUN / EVIDENCE-APPLIED MASTER ONLY / NO SCORE CHANGES",
        ]
    )
    path = ensure_parent_dir(path_value)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_personal_sec_derived_kpi_reviewed_evidence_apply(
    *,
    evidence_proposals: str | Path = DEFAULT_EVIDENCE_PROPOSALS,
    registry_append: str | Path = DEFAULT_REGISTRY_APPEND,
    fundamentals_master: str | Path = DEFAULT_PERSONAL_MASTER_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    evidence_applied_master: str | Path = DEFAULT_EVIDENCE_APPLIED_MASTER,
) -> ReviewedEvidenceApplyResult:
    proposals_path = resolve_repo_path(evidence_proposals)
    registry_append_path = resolve_repo_path(registry_append)
    master_path = resolve_repo_path(fundamentals_master)
    if not proposals_path.exists():
        raise RuntimeError("MISSING_SEC_DERIVED_KPI_EVIDENCE_PROPOSALS")
    if not registry_append_path.exists():
        raise RuntimeError("MISSING_SEC_DERIVED_KPI_EVIDENCE_REGISTRY_APPEND")
    if not master_path.exists():
        raise RuntimeError("MISSING_FUNDAMENTALS_MASTER")

    proposal_rows = read_csv_rows(proposals_path)
    _require_columns(proposal_rows, REQUIRED_PROPOSAL_COLUMNS, f"SEC derived KPI evidence proposals ({evidence_proposals})")
    _read_csv_header(registry_append_path)

    eligible_rows = [row for row in proposal_rows if _is_eligible(row)]
    if not eligible_rows:
        raise RuntimeError("NO_APPROVED_SEC_DERIVED_KPI_EVIDENCE_PROPOSALS")

    master_rows = [{field: _clean(row.get(field)) for field in PERSONAL_MASTER_FIELDS} for row in read_csv_rows(master_path)]
    validate_personal_fundamentals_master(master_rows, f"personal fundamentals master ({fundamentals_master})")
    applied_master_rows = [dict(row) for row in master_rows]
    isin_index, ticker_index = _master_index(master_rows)

    apply_rows: list[dict[str, str]] = []
    skipped_rows: list[dict[str, str]] = []
    for row in proposal_rows:
        if not _is_eligible(row):
            skipped_rows.append(_skip_row(row, "NOT_ELIGIBLE_FOR_REVIEWED_EVIDENCE_APPLY"))
            continue
        kpi_field = _clean(row.get("kpi_field"))
        if kpi_field not in PERSONAL_MASTER_FIELDS:
            skipped_rows.append(_skip_row(row, "TARGET_KPI_FIELD_MISSING", "SEC_EVIDENCE_APPLY_SCHEMA_ALIGNMENT"))
            continue
        matched_index = _match_master_row(row, master_rows, isin_index, ticker_index)
        if matched_index is None:
            skipped_rows.append(_skip_row(row, "IDENTITY_MATCH_FAILED"))
            continue
        old_value = _clean(applied_master_rows[matched_index].get(kpi_field))
        if not _target_allows_update(old_value):
            skipped_rows.append(_skip_row(row, "TARGET_ALREADY_HAS_VALUE"))
            continue

        proposed_value = _clean(row.get("proposed_value"))
        applied_master_rows[matched_index][kpi_field] = proposed_value
        apply_rows.append(
            {
                "evidence_id": _clean(row.get("evidence_id")),
                "holding_name": _clean(row.get("holding_name")),
                "ticker": _clean(row.get("ticker")),
                "isin": _upper(row.get("isin")),
                "kpi_field": kpi_field,
                "old_value": old_value,
                "new_value": proposed_value,
                "proposed_value": proposed_value,
                "value_unit": _clean(row.get("proposed_value_unit")),
                "apply_status": "APPLIED_TO_EVIDENCE_MASTER_COPY",
                "apply_reason": "HIGH-confidence reviewed SEC-derived KPI evidence proposal applied to processed evidence-applied master copy.",
                "evidence_source_type": _clean(row.get("evidence_source_type")),
                "evidence_source_artifact": sanitize_artifact_reference(row.get("evidence_source_artifact", "")),
                "confidence": _clean(row.get("confidence")),
                "no_imputation_confirmed": "True",
                "master_mutation_performed": "False",
                "raw_master_mutation_performed": "False",
                "score_mutation_performed": "False",
            }
        )

    apply_rows = sorted(apply_rows, key=_apply_sort_key)
    skipped_rows = sorted(skipped_rows, key=lambda row: (_upper(row.get("isin")), _clean(row.get("kpi_field")), _clean(row.get("skip_reason"))))
    validate_personal_fundamentals_master(applied_master_rows, "personal fundamentals master SEC derived KPI evidence-applied copy")

    output_root = resolve_repo_path(output_dir)
    report_root = resolve_repo_path(report_dir)
    apply_path = output_root / APPLY_FILENAME
    summary_path = output_root / SUMMARY_FILENAME
    skipped_path = output_root / SKIPPED_FILENAME
    master_output_path = resolve_repo_path(evidence_applied_master)
    report_path = report_root / REPORT_FILENAME

    summary = {
        "evidence_proposals_input": str(len(proposal_rows)),
        "proposals_eligible_for_apply": str(len(eligible_rows)),
        "proposals_applied": str(len(apply_rows)),
        "proposals_skipped": str(len(skipped_rows)),
        "holdings_updated": str(len({_upper(row.get("isin")) for row in apply_rows})),
        "kpi_fields_updated": str(len({_clean(row.get("kpi_field")) for row in apply_rows})),
        "raw_master_mutation_performed": "False",
        "evidence_applied_master_written": "True",
        "score_mutation_performed": "False",
        "no_score_change_confirmed": "True",
        "no_imputation_confirmed": "True",
        "no_network_confirmed": "True",
    }

    write_csv_rows(apply_path, APPLY_FIELDS, apply_rows)
    write_csv_rows(summary_path, SUMMARY_FIELDS, [summary])
    write_csv_rows(skipped_path, SKIPPED_FIELDS, skipped_rows)
    write_csv_rows(master_output_path, PERSONAL_MASTER_FIELDS, applied_master_rows)
    _write_report(
        report_path,
        summary=summary,
        apply_rows=apply_rows,
        skipped_rows=skipped_rows,
        evidence_proposals=evidence_proposals,
        registry_append=registry_append,
        master_input=fundamentals_master,
        evidence_applied_master=evidence_applied_master,
    )

    return ReviewedEvidenceApplyResult(
        apply_path=resolve_repo_path(apply_path),
        summary_path=resolve_repo_path(summary_path),
        skipped_path=resolve_repo_path(skipped_path),
        evidence_applied_master_path=resolve_repo_path(master_output_path),
        report_path=resolve_repo_path(report_path),
        summary=summary,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply reviewed SEC-derived KPI evidence proposals to a processed evidence-applied master copy.")
    parser.add_argument("--evidence-proposals", default=DEFAULT_EVIDENCE_PROPOSALS, help="SEC-derived KPI evidence proposals CSV.")
    parser.add_argument("--registry-append", default=DEFAULT_REGISTRY_APPEND, help="SEC-derived KPI evidence registry append CSV.")
    parser.add_argument("--fundamentals-master", default=DEFAULT_PERSONAL_MASTER_PATH, help="Base personal fundamentals master CSV, read-only.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Processed output directory.")
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR, help="Report output directory.")
    parser.add_argument("--evidence-applied-master", default=DEFAULT_EVIDENCE_APPLIED_MASTER, help="Processed evidence-applied master output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_personal_sec_derived_kpi_reviewed_evidence_apply(
        evidence_proposals=args.evidence_proposals,
        registry_append=args.registry_append,
        fundamentals_master=args.fundamentals_master,
        output_dir=args.output_dir,
        report_dir=args.report_dir,
        evidence_applied_master=args.evidence_applied_master,
    )


if __name__ == "__main__":
    main()
