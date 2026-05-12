from __future__ import annotations

import argparse
import csv
import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, ensure_parent_dir, read_csv_rows, resolve_repo_path, write_csv_rows
from src.fundamentals_master import DEFAULT_PERSONAL_MASTER_PATH, PERSONAL_MASTER_FIELDS, validate_personal_fundamentals_master

DEFAULT_BASELINE_MASTER = DEFAULT_PERSONAL_MASTER_PATH
DEFAULT_EVIDENCE_APPLIED_MASTER = "data/processed/personal_fundamentals_master_sec_derived_kpi_applied.csv"
DEFAULT_APPLY_SUMMARY = "data/processed/personal_sec_derived_kpi_reviewed_evidence_apply_summary.csv"
DEFAULT_APPLY_DETAIL = "data/processed/personal_sec_derived_kpi_reviewed_evidence_apply.csv"
DEFAULT_EVIDENCE_PROPOSALS = "data/processed/personal_sec_derived_kpi_evidence_proposals.csv"
DEFAULT_REGISTRY_APPEND = "data/processed/personal_sec_derived_kpi_evidence_registry_append.csv"
DEFAULT_CLOSURE_QUEUE = "data/processed/personal_core_kpi_closure_queue.csv"
DEFAULT_OUTPUT = "data/processed/personal_sec_core_kpi_closure_impact_after_reviewed_apply.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_sec_core_kpi_closure_impact_after_reviewed_apply_summary.csv"
DEFAULT_REPORT_OUTPUT = "reports/2026-04-28/personal_sec_core_kpi_closure_impact_after_reviewed_apply_report.md"

CORE_KPI_FIELDS = [
    "revenue_cagr_5y",
    "eps_cagr_5y",
    "gross_margin",
    "operating_margin",
    "share_count_cagr_5y",
]

IMPACT_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "kpi_field",
    "baseline_value",
    "evidence_applied_value",
    "value_changed",
    "closure_status",
    "evidence_id",
    "evidence_confidence",
    "fiscal_year_end",
    "source_as_of_date",
    "source_forms",
    "stale_or_old_fiscal_year",
    "stale_reason",
    "notes",
]

SUMMARY_FIELDS = [
    "baseline_missing_required_kpi_count",
    "evidence_applied_missing_required_kpi_count",
    "missing_required_kpi_delta",
    "closed_kpi_count",
    "holdings_with_any_closure",
    "applied_value_count",
    "distinct_kpi_fields_closed",
    "stale_or_old_fiscal_year_count",
    "raw_master_sha256_before",
    "raw_master_sha256_after",
    "raw_master_mutation_performed",
    "score_mutation_performed",
    "no_score_change_confirmed",
    "no_network_confirmed",
]

BASELINE_REQUIRED_COLUMNS = ["ticker", "isin", "company_name", *CORE_KPI_FIELDS]
APPLY_DETAIL_REQUIRED_COLUMNS = [
    "evidence_id",
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "old_value",
    "new_value",
    "apply_status",
    "confidence",
]
APPLY_SUMMARY_REQUIRED_COLUMNS = ["proposals_applied", "raw_master_mutation_performed", "score_mutation_performed", "no_network_confirmed"]
PROPOSAL_REQUIRED_COLUMNS = ["evidence_id", "fiscal_year_end", "source_filed_dates", "source_forms"]
CLOSURE_QUEUE_REQUIRED_COLUMNS = ["ticker", "isin", "company_name", "missing_core_kpis"]


@dataclass(frozen=True)
class ClosureImpactRerunResult:
    impact_path: Path
    summary_path: Path
    report_path: Path
    summary: dict[str, str]
    impact_rows: list[dict[str, str]]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _upper(value: Any) -> str:
    return _clean(value).upper()


def _sha256(path_value: str | Path) -> str:
    path = resolve_repo_path(path_value)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_header(path_value: str | Path) -> list[str]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or [])


def _require_file(path_value: str | Path, reason: str) -> Path:
    path = resolve_repo_path(path_value)
    if not path.exists():
        raise RuntimeError(reason)
    return path


def _require_columns(rows: list[dict[str, str]], required: list[str], source_name: str) -> None:
    if not rows:
        raise ValueError(f"{source_name} contains no rows")
    available = set(rows[0].keys())
    missing = [column for column in required if column not in available]
    if missing:
        raise ValueError(f"{source_name} missing required columns: {', '.join(sorted(missing))}")


def _identity(row: dict[str, str]) -> tuple[str, str]:
    return canonicalize_ticker(row.get("ticker", "")), _upper(row.get("isin"))


def _build_master_index(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    index: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        ticker, isin = _identity(row)
        if isin:
            index[("", isin)] = row
        if ticker:
            index[(ticker, "")] = row
        if ticker or isin:
            index[(ticker, isin)] = row
    return index


def _lookup(row: dict[str, str], index: dict[tuple[str, str], dict[str, str]]) -> dict[str, str]:
    ticker, isin = _identity(row)
    for key in [(ticker, isin), ("", isin), (ticker, "")]:
        if key in index:
            return index[key]
    return {}


def _split_kpis(value: str) -> list[str]:
    return [part.strip() for part in _clean(value).replace(",", ";").split(";") if part.strip()]


def _scope_rows_from_closure_queue(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    scope: list[dict[str, str]] = []
    for row in queue_rows:
        for kpi in _split_kpis(row.get("missing_core_kpis", "")):
            if kpi in CORE_KPI_FIELDS:
                scope.append(
                    {
                        "ticker": _clean(row.get("ticker")),
                        "isin": _upper(row.get("isin")),
                        "company_name": _clean(row.get("company_name")),
                        "kpi_field": kpi,
                    }
                )
    return scope


def _scope_rows_from_apply_detail(apply_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "ticker": _clean(row.get("ticker")),
            "isin": _upper(row.get("isin")),
            "company_name": _clean(row.get("holding_name")),
            "kpi_field": _clean(row.get("kpi_field")),
        }
        for row in apply_rows
        if _clean(row.get("kpi_field")) in CORE_KPI_FIELDS
    ]


def _latest_date(dates_text: str) -> str:
    dates = sorted(part for part in _split_kpis(dates_text) if part)
    return dates[-1] if dates else ""


def _proposal_by_evidence_id(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {_clean(row.get("evidence_id")): row for row in rows if _clean(row.get("evidence_id"))}


def _apply_by_entity_kpi(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    index: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        isin = _upper(row.get("isin"))
        kpi = _clean(row.get("kpi_field"))
        if isin and kpi:
            index[(isin, kpi)] = row
    return index


def _is_missing(value: str) -> bool:
    return _upper(value) in {"", "MISSING", "MISSING_DATA", "REVIEW", "N/A", "NA"}


def _stale_status(fiscal_year_end: str, source_as_of_date: str, *, as_of_year: int) -> tuple[str, str]:
    fiscal_text = _clean(fiscal_year_end)
    if not fiscal_text:
        return "False", ""
    try:
        fiscal_year = int(float(fiscal_text))
    except ValueError:
        return "True", f"Fiscal year `{fiscal_text}` is not parseable."
    age = as_of_year - fiscal_year
    if age > 2:
        return "True", f"Fiscal year {fiscal_year} is {age} years before {as_of_year}; source_as_of_date={source_as_of_date or 'unknown'}."
    return "False", ""


def build_impact_rows(
    *,
    scope_rows: list[dict[str, str]],
    baseline_rows: list[dict[str, str]],
    applied_rows: list[dict[str, str]],
    apply_detail_rows: list[dict[str, str]],
    proposal_rows: list[dict[str, str]],
    as_of_year: int,
) -> list[dict[str, str]]:
    baseline_index = _build_master_index(baseline_rows)
    applied_index = _build_master_index(applied_rows)
    apply_index = _apply_by_entity_kpi(apply_detail_rows)
    proposal_index = _proposal_by_evidence_id(proposal_rows)
    impact_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for scope in sorted(scope_rows, key=lambda row: (_upper(row.get("isin")), _clean(row.get("kpi_field")))):
        isin = _upper(scope.get("isin"))
        kpi = _clean(scope.get("kpi_field"))
        key = (isin, kpi)
        if key in seen:
            continue
        seen.add(key)
        baseline = _lookup(scope, baseline_index)
        applied = _lookup(scope, applied_index)
        baseline_value = _clean(baseline.get(kpi, ""))
        applied_value = _clean(applied.get(kpi, ""))
        apply_row = apply_index.get(key, {})
        evidence_id = _clean(apply_row.get("evidence_id"))
        proposal = proposal_index.get(evidence_id, {})
        fiscal_year_end = _clean(proposal.get("fiscal_year_end"))
        source_as_of_date = _latest_date(proposal.get("source_filed_dates", ""))
        source_forms = _clean(proposal.get("source_forms"))
        stale_flag, stale_reason = _stale_status(fiscal_year_end, source_as_of_date, as_of_year=as_of_year)

        if _is_missing(baseline_value) and not _is_missing(applied_value) and evidence_id:
            closure_status = "CLOSED_BY_SEC_DERIVED_KPI"
            notes = "Blank baseline KPI was filled in the processed evidence-applied master copy."
        elif _is_missing(applied_value):
            closure_status = "STILL_MISSING"
            notes = "KPI remains missing in the processed evidence-applied master copy."
        elif baseline_value == applied_value:
            closure_status = "UNCHANGED_EXISTING"
            notes = "KPI value existed before this reviewed SEC-derived apply step."
        else:
            closure_status = "REVIEW"
            notes = "Value changed without a matching SEC-derived apply evidence row."

        impact_rows.append(
            {
                "ticker": _clean(scope.get("ticker")) or _clean(applied.get("ticker")) or _clean(baseline.get("ticker")),
                "isin": isin or _upper(applied.get("isin")) or _upper(baseline.get("isin")),
                "company_name": _clean(scope.get("company_name")) or _clean(applied.get("company_name")) or _clean(baseline.get("company_name")),
                "kpi_field": kpi,
                "baseline_value": baseline_value,
                "evidence_applied_value": applied_value,
                "value_changed": str(baseline_value != applied_value),
                "closure_status": closure_status,
                "evidence_id": evidence_id,
                "evidence_confidence": _clean(apply_row.get("confidence")),
                "fiscal_year_end": fiscal_year_end,
                "source_as_of_date": source_as_of_date,
                "source_forms": source_forms,
                "stale_or_old_fiscal_year": stale_flag if closure_status == "CLOSED_BY_SEC_DERIVED_KPI" else "False",
                "stale_reason": stale_reason if closure_status == "CLOSED_BY_SEC_DERIVED_KPI" else "",
                "notes": notes,
            }
        )
    return impact_rows


def build_summary(
    *,
    impact_rows: list[dict[str, str]],
    apply_summary_rows: list[dict[str, str]],
    raw_master_sha_before: str,
    raw_master_sha_after: str,
) -> dict[str, str]:
    closed_rows = [row for row in impact_rows if row["closure_status"] == "CLOSED_BY_SEC_DERIVED_KPI"]
    baseline_missing = sum(1 for row in impact_rows if _is_missing(row["baseline_value"]))
    applied_missing = sum(1 for row in impact_rows if _is_missing(row["evidence_applied_value"]))
    apply_summary = apply_summary_rows[0] if apply_summary_rows else {}
    return {
        "baseline_missing_required_kpi_count": str(baseline_missing),
        "evidence_applied_missing_required_kpi_count": str(applied_missing),
        "missing_required_kpi_delta": str(applied_missing - baseline_missing),
        "closed_kpi_count": str(len(closed_rows)),
        "holdings_with_any_closure": str(len({_upper(row.get("isin")) for row in closed_rows})),
        "applied_value_count": _clean(apply_summary.get("proposals_applied")) or str(len(closed_rows)),
        "distinct_kpi_fields_closed": str(len({_clean(row.get("kpi_field")) for row in closed_rows})),
        "stale_or_old_fiscal_year_count": str(sum(1 for row in closed_rows if row["stale_or_old_fiscal_year"] == "True")),
        "raw_master_sha256_before": raw_master_sha_before,
        "raw_master_sha256_after": raw_master_sha_after,
        "raw_master_mutation_performed": str(raw_master_sha_before != raw_master_sha_after),
        "score_mutation_performed": _clean(apply_summary.get("score_mutation_performed")) or "False",
        "no_score_change_confirmed": "True" if _clean(apply_summary.get("score_mutation_performed")) != "True" else "False",
        "no_network_confirmed": _clean(apply_summary.get("no_network_confirmed")) or "True",
    }


def render_report(summary: dict[str, str], impact_rows: list[dict[str, str]]) -> str:
    closed_rows = [row for row in impact_rows if row["closure_status"] == "CLOSED_BY_SEC_DERIVED_KPI"]
    missing_rows = [row for row in impact_rows if row["closure_status"] == "STILL_MISSING"]
    stale_rows = [row for row in closed_rows if row["stale_or_old_fiscal_year"] == "True"]
    lines = [
        "# SEC Core KPI Closure Impact After Reviewed Apply",
        "",
        "## Executive Summary",
        "",
        f"- Closed KPI count: {summary['closed_kpi_count']}",
        f"- Missing required KPI count before/after: {summary['baseline_missing_required_kpi_count']} / {summary['evidence_applied_missing_required_kpi_count']}",
        f"- Missing required KPI delta: {summary['missing_required_kpi_delta']}",
        f"- Holdings with any closure: {summary['holdings_with_any_closure']}",
        f"- No scores were regenerated: {summary['no_score_change_confirmed']}",
        f"- No network fetch was performed: {summary['no_network_confirmed']}",
        "",
        "## What Changed",
        "",
    ]
    if closed_rows:
        for row in closed_rows:
            lines.append(
                f"- `{row['company_name']}` `{row['kpi_field']}`: "
                f"{row['baseline_value'] or '<blank>'} -> {row['evidence_applied_value']} "
                f"via `{row['evidence_id']}`."
            )
    else:
        lines.append("- No KPI closures detected.")
    lines.extend(["", "## What Did Not Change", ""])
    lines.append("- Raw fundamentals master was not mutated.")
    lines.append("- Score formulas, score artifacts, monthly rankings, watchlists, dashboards, and website files were not regenerated by this rerun.")
    lines.extend(["", "## Remaining Gaps", ""])
    if missing_rows:
        for row in missing_rows:
            lines.append(f"- `{row['company_name']}` `{row['kpi_field']}` remains missing.")
    else:
        lines.append("- No remaining gaps in the scoped SEC core KPI closure queue.")
    lines.extend(["", "## Stale/Old Fiscal-Year Warnings", ""])
    if stale_rows:
        for row in stale_rows:
            lines.append(f"- `{row['company_name']}` `{row['kpi_field']}`: {row['stale_reason']}")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            f"- raw_master_sha256_before: `{summary['raw_master_sha256_before']}`",
            f"- raw_master_sha256_after: `{summary['raw_master_sha256_after']}`",
            f"- raw_master_mutation_performed: `{summary['raw_master_mutation_performed']}`",
            f"- score_mutation_performed: `{summary['score_mutation_performed']}`",
            "- No imputation and no fabricated KPI values were introduced.",
            "",
            "## Recommended Next Step",
            "",
            "SEC CORE KPI CLOSURE REVIEW / STALE FY WARNINGS + REMAINING MISSING KPIS / NO SCORE CHANGES",
        ]
    )
    return "\n".join(lines) + "\n"


def run_personal_sec_core_kpi_closure_impact_rerun(
    *,
    baseline_master: str | Path = DEFAULT_BASELINE_MASTER,
    evidence_applied_master: str | Path = DEFAULT_EVIDENCE_APPLIED_MASTER,
    apply_summary: str | Path = DEFAULT_APPLY_SUMMARY,
    apply_detail: str | Path = DEFAULT_APPLY_DETAIL,
    evidence_proposals: str | Path = DEFAULT_EVIDENCE_PROPOSALS,
    registry_append: str | Path = DEFAULT_REGISTRY_APPEND,
    closure_queue: str | Path = DEFAULT_CLOSURE_QUEUE,
    impact_output: str | Path = DEFAULT_OUTPUT,
    summary_output: str | Path = DEFAULT_SUMMARY_OUTPUT,
    report_output: str | Path = DEFAULT_REPORT_OUTPUT,
    as_of_date: date | None = None,
) -> ClosureImpactRerunResult:
    baseline_path = _require_file(baseline_master, "MISSING_BASELINE_MASTER")
    applied_path = _require_file(evidence_applied_master, "MISSING_EVIDENCE_APPLIED_MASTER")
    apply_summary_path = _require_file(apply_summary, "MISSING_REVIEWED_APPLY_SUMMARY")
    apply_detail_path = _require_file(apply_detail, "MISSING_REVIEWED_APPLY_DETAIL")
    proposals_path = resolve_repo_path(evidence_proposals)
    closure_queue_path = resolve_repo_path(closure_queue)
    resolve_repo_path(registry_append)

    raw_sha_before = _sha256(baseline_path)

    baseline_rows = read_csv_rows(baseline_path)
    applied_rows = read_csv_rows(applied_path)
    apply_summary_rows = read_csv_rows(apply_summary_path)
    apply_detail_rows = read_csv_rows(apply_detail_path)
    proposal_rows = read_csv_rows(proposals_path) if proposals_path.exists() else []

    _require_columns(baseline_rows, BASELINE_REQUIRED_COLUMNS, f"baseline master ({baseline_master})")
    _require_columns(applied_rows, BASELINE_REQUIRED_COLUMNS, f"evidence-applied master ({evidence_applied_master})")
    _require_columns(apply_summary_rows, APPLY_SUMMARY_REQUIRED_COLUMNS, f"reviewed apply summary ({apply_summary})")
    _require_columns(apply_detail_rows, APPLY_DETAIL_REQUIRED_COLUMNS, f"reviewed apply detail ({apply_detail})")
    if proposal_rows:
        _require_columns(proposal_rows, PROPOSAL_REQUIRED_COLUMNS, f"evidence proposals ({evidence_proposals})")

    validate_personal_fundamentals_master(baseline_rows, f"baseline master ({baseline_master})")
    validate_personal_fundamentals_master(applied_rows, f"evidence-applied master ({evidence_applied_master})")

    if closure_queue_path.exists():
        queue_rows = read_csv_rows(closure_queue_path)
        _require_columns(queue_rows, CLOSURE_QUEUE_REQUIRED_COLUMNS, f"closure queue ({closure_queue})")
        scope_rows = _scope_rows_from_closure_queue(queue_rows)
    else:
        scope_rows = _scope_rows_from_apply_detail(apply_detail_rows)

    today = as_of_date or date.today()
    impact_rows = build_impact_rows(
        scope_rows=scope_rows,
        baseline_rows=baseline_rows,
        applied_rows=applied_rows,
        apply_detail_rows=apply_detail_rows,
        proposal_rows=proposal_rows,
        as_of_year=today.year,
    )

    raw_sha_after = _sha256(baseline_path)
    summary = build_summary(
        impact_rows=impact_rows,
        apply_summary_rows=apply_summary_rows,
        raw_master_sha_before=raw_sha_before,
        raw_master_sha_after=raw_sha_after,
    )

    write_csv_rows(impact_output, IMPACT_FIELDS, impact_rows)
    write_csv_rows(summary_output, SUMMARY_FIELDS, [summary])
    report_path = ensure_parent_dir(report_output)
    report_path.write_text(render_report(summary, impact_rows), encoding="utf-8")

    if summary["raw_master_mutation_performed"] == "True":
        raise RuntimeError("RAW_MASTER_MUTATION_DETECTED")

    return ClosureImpactRerunResult(
        impact_path=resolve_repo_path(impact_output),
        summary_path=resolve_repo_path(summary_output),
        report_path=resolve_repo_path(report_output),
        summary=summary,
        impact_rows=impact_rows,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quantify SEC core KPI closure impact after reviewed SEC-derived evidence apply.")
    parser.add_argument("--baseline-master", default=DEFAULT_BASELINE_MASTER)
    parser.add_argument("--evidence-applied-master", default=DEFAULT_EVIDENCE_APPLIED_MASTER)
    parser.add_argument("--apply-summary", default=DEFAULT_APPLY_SUMMARY)
    parser.add_argument("--apply-detail", default=DEFAULT_APPLY_DETAIL)
    parser.add_argument("--evidence-proposals", default=DEFAULT_EVIDENCE_PROPOSALS)
    parser.add_argument("--registry-append", default=DEFAULT_REGISTRY_APPEND)
    parser.add_argument("--closure-queue", default=DEFAULT_CLOSURE_QUEUE)
    parser.add_argument("--impact-output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_core_kpi_closure_impact_rerun(
        baseline_master=args.baseline_master,
        evidence_applied_master=args.evidence_applied_master,
        apply_summary=args.apply_summary,
        apply_detail=args.apply_detail,
        evidence_proposals=args.evidence_proposals,
        registry_append=args.registry_append,
        closure_queue=args.closure_queue,
        impact_output=args.impact_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    print(f"impact_output={result.impact_path}")
    print(f"summary_output={result.summary_path}")
    print(f"report_output={result.report_path}")
    print(f"closed_kpi_count={result.summary['closed_kpi_count']}")
    print(f"evidence_applied_missing_required_kpi_count={result.summary['evidence_applied_missing_required_kpi_count']}")


if __name__ == "__main__":
    main()
