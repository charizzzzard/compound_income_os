from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, write_csv_rows

DEFAULT_WATCHLIST_SUMMARY = "data/processed/personal_watchlist_input_gate_summary.csv"
DEFAULT_VALUATION_SUMMARY = "data/processed/personal_valuation_input_contract_summary.csv"
DEFAULT_DIVIDEND_FCF_SUMMARY = "data/processed/personal_dividend_fcf_input_contract_summary.csv"
DEFAULT_KPI_PROVENANCE_SUMMARY = "data/processed/personal_kpi_provenance_summary.csv"
DEFAULT_CORE_KPI_SUMMARY = "data/processed/personal_core_kpi_closure_summary.csv"
DEFAULT_OUTPUT = "data/processed/personal_input_closure_report.csv"
DEFAULT_REPORT = f"reports/{date.today().isoformat()}/personal_input_closure_report.md"

STATUS_READY = "READY"
STATUS_REVIEW_REQUIRED = "REVIEW_REQUIRED"
STATUS_BLOCKED = "BLOCKED"
STATUS_MISSING = "MISSING"
STATUS_SAMPLE_ONLY = "SAMPLE_ONLY"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"

FIELDNAMES = [
    "input_area",
    "artifact_path",
    "status",
    "blocker_severity",
    "missing_or_review_items_count",
    "sample_or_synthetic_flag",
    "reason_codes",
    "required_operator_action",
    "downstream_impact",
    "next_recommended_step",
]

REQUIRED_AREAS = ("WATCHLIST", "VALUATION", "DIVIDEND_FCF", "KPI_PROVENANCE")
OPTIONAL_AREAS = ("CORE_KPI_CLOSURE",)


@dataclass(frozen=True)
class SummaryArtifact:
    path: str
    exists: bool
    metrics: dict[str, str]


@dataclass(frozen=True)
class PersonalInputClosureResult:
    output: Path
    report: Path
    rows: list[dict[str, str]]
    missing_artifacts: tuple[str, ...]


def _summary_artifact(path_value: str) -> SummaryArtifact:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return SummaryArtifact(path=path_value, exists=False, metrics={})
    rows = read_csv_rows(path)
    metrics = {
        str(row.get("metric", "") or "").strip(): str(row.get("value", "") or "").strip()
        for row in rows
        if str(row.get("metric", "") or "").strip()
    }
    return SummaryArtifact(path=path_value, exists=True, metrics=metrics)


def _bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"true", "yes", "1", "y"}


def _int(value: Any) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _metric(artifact: SummaryArtifact, name: str, default: str = "") -> str:
    return artifact.metrics.get(name, default)


def _missing_row(input_area: str, artifact_path: str, action: str, impact: str, next_step: str) -> dict[str, str]:
    return {
        "input_area": input_area,
        "artifact_path": artifact_path,
        "status": STATUS_MISSING,
        "blocker_severity": "P0_BLOCKER",
        "missing_or_review_items_count": "1",
        "sample_or_synthetic_flag": "False",
        "reason_codes": "INPUT_ARTIFACT_MISSING",
        "required_operator_action": action,
        "downstream_impact": impact,
        "next_recommended_step": next_step,
    }


def _row(
    *,
    input_area: str,
    artifact_path: str,
    status: str,
    blocker_severity: str,
    count: int,
    sample_flag: bool,
    reason_codes: str,
    action: str,
    impact: str,
    next_step: str,
) -> dict[str, str]:
    return {
        "input_area": input_area,
        "artifact_path": artifact_path,
        "status": status,
        "blocker_severity": blocker_severity,
        "missing_or_review_items_count": str(max(count, 0)),
        "sample_or_synthetic_flag": "True" if sample_flag else "False",
        "reason_codes": reason_codes,
        "required_operator_action": action,
        "downstream_impact": impact,
        "next_recommended_step": next_step,
    }


def _watchlist_row(artifact: SummaryArtifact) -> dict[str, str]:
    impact = "Monthly decision readiness and watchlist candidate interpretation remain blocked until the input is reviewed."
    if not artifact.exists:
        return _missing_row(
            "WATCHLIST",
            artifact.path,
            "Generate watchlist gate artifacts from an explicit reviewed personal watchlist input.",
            impact,
            "Run the watchlist input gate after replacing demo input with reviewed personal watchlist data.",
        )

    input_status = _metric(artifact, "watchlist_input_status", "UNKNOWN")
    readiness = _metric(artifact, "watchlist_readiness_status", "UNKNOWN")
    reason_codes = _metric(artifact, "watchlist_reason_codes")
    rows_total = _int(_metric(artifact, "watchlist_rows_total"))
    sample_flag = _bool(_metric(artifact, "watchlist_sample_input_active")) or input_status == "SAMPLE_DEMO_ONLY"
    review_active = _bool(_metric(artifact, "watchlist_review_or_missing_data_active"))

    if sample_flag:
        return _row(
            input_area="WATCHLIST",
            artifact_path=artifact.path,
            status=STATUS_SAMPLE_ONLY,
            blocker_severity="P0_BLOCKER",
            count=max(rows_total, 1),
            sample_flag=True,
            reason_codes=reason_codes or "WATCHLIST_SAMPLE_INPUT",
            action="Replace sample watchlist with reviewed personal watchlist input.",
            impact=impact,
            next_step="Create or point the run to a reviewed personal watchlist, then rerun watchlist gate and monthly artifacts.",
        )
    if readiness in {"BLOCKED", "NOT_AVAILABLE"}:
        return _row(
            input_area="WATCHLIST",
            artifact_path=artifact.path,
            status=STATUS_BLOCKED,
            blocker_severity="P0_BLOCKER",
            count=max(rows_total, 1),
            sample_flag=False,
            reason_codes=reason_codes or readiness,
            action="Resolve watchlist review or missing-data rows before decision use.",
            impact=impact,
            next_step="Review watchlist candidate rows and regenerate the watchlist input gate.",
        )
    if review_active or readiness == "REVIEW":
        return _row(
            input_area="WATCHLIST",
            artifact_path=artifact.path,
            status=STATUS_REVIEW_REQUIRED,
            blocker_severity="P1_REVIEW",
            count=max(rows_total, 1),
            sample_flag=False,
            reason_codes=reason_codes or "WATCHLIST_REVIEW_OR_MISSING_DATA",
            action="Review watchlist data quality before using it for decision workflow outputs.",
            impact="Decision Capture can record a human state, but candidate quality remains under review.",
            next_step="Mark the watchlist input as reviewed only after row-level review and missing-data resolution.",
        )
    if readiness == "PASS" and input_status == "PERSONAL_REVIEWED":
        return _row(
            input_area="WATCHLIST",
            artifact_path=artifact.path,
            status=STATUS_READY,
            blocker_severity="NONE",
            count=0,
            sample_flag=False,
            reason_codes=reason_codes or "WATCHLIST_PERSONAL_REVIEWED",
            action="No input closure action required.",
            impact="Watchlist input can support monthly decision review.",
            next_step="Keep reviewed watchlist input current before the next monthly run.",
        )
    return _row(
        input_area="WATCHLIST",
        artifact_path=artifact.path,
        status=STATUS_REVIEW_REQUIRED,
        blocker_severity="P1_REVIEW",
        count=max(rows_total, 1),
        sample_flag=False,
        reason_codes=reason_codes or "WATCHLIST_STATUS_REVIEW",
        action="Confirm that the watchlist input is personal and reviewed.",
        impact="Decision readiness remains under review until the input source is explicit.",
        next_step="Add a reviewed personal watchlist marker and rerun the watchlist input gate.",
    )


def _valuation_row(artifact: SummaryArtifact) -> dict[str, str]:
    impact = "Monthly decision readiness and valuation-sensitive Decision Capture quality remain blocked."
    if not artifact.exists:
        return _missing_row(
            "VALUATION",
            artifact.path,
            "Generate valuation input contract summary from existing KPI-tier artifacts.",
            impact,
            "Run the valuation input contract before relying on valuation readiness.",
        )

    missing = _int(_metric(artifact, "missing_rows_count"))
    review = _int(_metric(artifact, "review_rows_count"))
    invalid = _int(_metric(artifact, "invalid_rows_count"))
    approved = _int(_metric(artifact, "approved_rows_count"))
    input_status = _metric(artifact, "input_file_status", "UNKNOWN")
    affected = _int(_metric(artifact, "affected_standard_rows_count"))
    reason_codes = _metric(artifact, "reason_codes")
    open_count = missing + review + invalid

    if missing > 0 or input_status in {"MISSING", "INVALID_SCHEMA", "INVALID_DUPLICATE_IDENTITY"}:
        status = STATUS_BLOCKED if approved == 0 or input_status == "MISSING" else STATUS_REVIEW_REQUIRED
        return _row(
            input_area="VALUATION",
            artifact_path=artifact.path,
            status=status,
            blocker_severity="P0_BLOCKER" if status == STATUS_BLOCKED else "P1_REVIEW",
            count=open_count or affected,
            sample_flag=False,
            reason_codes=reason_codes or "VALUATION_REQUIRED_MISSING",
            action="Provide reviewed valuation input with source reference and as-of date.",
            impact=impact,
            next_step="Populate the private valuation review input, then rerun the valuation input contract.",
        )
    if review > 0 or invalid > 0:
        return _row(
            input_area="VALUATION",
            artifact_path=artifact.path,
            status=STATUS_REVIEW_REQUIRED,
            blocker_severity="P1_REVIEW",
            count=open_count,
            sample_flag=False,
            reason_codes=reason_codes or "VALUATION_REVIEW_PENDING",
            action="Complete valuation review and fix invalid valuation source metadata.",
            impact="Decision readiness remains under review while valuation input is not fully approved.",
            next_step="Approve or reject valuation rows with source reference and source date.",
        )
    return _row(
        input_area="VALUATION",
        artifact_path=artifact.path,
        status=STATUS_READY if approved > 0 or affected == 0 else STATUS_NOT_APPLICABLE,
        blocker_severity="NONE",
        count=0,
        sample_flag=False,
        reason_codes=reason_codes or "VALUATION_APPROVED",
        action="No valuation input closure action required.",
        impact="Valuation input does not block monthly decision readiness.",
        next_step="Keep valuation source references current before the next monthly run.",
    )


def _dividend_fcf_row(artifact: SummaryArtifact) -> dict[str, str]:
    impact = "Monthly decision readiness and Dividend/FCF interpretation remain blocked."
    if not artifact.exists:
        return _missing_row(
            "DIVIDEND_FCF",
            artifact.path,
            "Generate Dividend/FCF input contract summary from existing KPI-tier and evidence artifacts.",
            impact,
            "Run the Dividend/FCF input contract before relying on Dividend/FCF readiness.",
        )

    missing = _int(_metric(artifact, "missing_rows_count"))
    review = _int(_metric(artifact, "review_rows_count"))
    invalid = _int(_metric(artifact, "invalid_rows_count"))
    approved = _int(_metric(artifact, "approved_rows_count"))
    affected = _int(_metric(artifact, "affected_standard_rows_count"))
    sec_possible = _int(_metric(artifact, "sec_evidence_possible_count"))
    input_status = _metric(artifact, "input_file_status", "UNKNOWN")
    reason_codes = _metric(artifact, "reason_codes")
    open_count = missing + review + invalid

    if missing > 0 or input_status in {"MISSING", "INVALID_SCHEMA", "INVALID_DUPLICATE_IDENTITY"}:
        action = "Provide reviewed Dividend/FCF input or run reviewed SEC evidence workflow."
        if sec_possible > 0:
            action = f"{action} SEC evidence is structurally possible for {sec_possible} row(s)."
        status = STATUS_BLOCKED if approved == 0 or input_status == "MISSING" else STATUS_REVIEW_REQUIRED
        return _row(
            input_area="DIVIDEND_FCF",
            artifact_path=artifact.path,
            status=status,
            blocker_severity="P0_BLOCKER" if status == STATUS_BLOCKED else "P1_REVIEW",
            count=open_count or affected,
            sample_flag=False,
            reason_codes=reason_codes or "DIVIDEND_FCF_REQUIRED_MISSING",
            action=action,
            impact=impact,
            next_step="Close Dividend/FCF review inputs through manual evidence or reviewed SEC evidence; do not impute values.",
        )
    if review > 0 or invalid > 0:
        return _row(
            input_area="DIVIDEND_FCF",
            artifact_path=artifact.path,
            status=STATUS_REVIEW_REQUIRED,
            blocker_severity="P1_REVIEW",
            count=open_count,
            sample_flag=False,
            reason_codes=reason_codes or "DIVIDEND_FCF_REVIEW_PENDING",
            action="Complete Dividend/FCF review and source metadata before decision use.",
            impact="Decision readiness remains under review while Dividend/FCF input is not fully approved.",
            next_step="Approve or reject Dividend/FCF rows with source reference and source date.",
        )
    return _row(
        input_area="DIVIDEND_FCF",
        artifact_path=artifact.path,
        status=STATUS_READY if approved > 0 or affected == 0 else STATUS_NOT_APPLICABLE,
        blocker_severity="NONE",
        count=0,
        sample_flag=False,
        reason_codes=reason_codes or "DIVIDEND_FCF_APPROVED",
        action="No Dividend/FCF input closure action required.",
        impact="Dividend/FCF input does not block monthly decision readiness.",
        next_step="Keep Dividend/FCF source references current before the next monthly run.",
    )


def _kpi_provenance_row(artifact: SummaryArtifact) -> dict[str, str]:
    impact = "Score interpretation and Decision Capture evidence quality remain blocked by incomplete KPI provenance."
    if not artifact.exists:
        return _missing_row(
            "KPI_PROVENANCE",
            artifact.path,
            "Generate KPI provenance audit summary before relying on score interpretation.",
            impact,
            "Run the KPI provenance audit from existing score-audit, master and evidence artifacts.",
        )

    missing = _int(_metric(artifact, "provenance_status__MISSING"))
    partial = _int(_metric(artifact, "provenance_status__PARTIAL"))
    ambiguous = _int(_metric(artifact, "provenance_status__AMBIGUOUS"))
    incomplete = _bool(_metric(artifact, "provenance_incomplete_flag"))
    holdings = _int(_metric(artifact, "holdings_with_incomplete_provenance_total"))
    reason_codes = "PROVENANCE_INCOMPLETE" if incomplete else _metric(artifact, "reason_codes", "PROVENANCE_COMPLETE")
    open_count = missing + partial + ambiguous

    if incomplete or open_count > 0:
        return _row(
            input_area="KPI_PROVENANCE",
            artifact_path=artifact.path,
            status=STATUS_BLOCKED,
            blocker_severity="P0_BLOCKER",
            count=holdings or open_count,
            sample_flag=False,
            reason_codes=reason_codes,
            action="Review KPI provenance gaps before relying on score interpretation.",
            impact=impact,
            next_step="Increase source metadata coverage through the reviewed evidence registry and apply path; do not change KPI values here.",
        )
    return _row(
        input_area="KPI_PROVENANCE",
        artifact_path=artifact.path,
        status=STATUS_READY,
        blocker_severity="NONE",
        count=0,
        sample_flag=False,
        reason_codes=_metric(artifact, "reason_codes", "PROVENANCE_COMPLETE"),
        action="No KPI provenance closure action required.",
        impact="KPI provenance does not block score interpretation.",
        next_step="Keep evidence metadata current before the next score audit.",
    )


def _core_kpi_row(artifact: SummaryArtifact) -> dict[str, str]:
    affected = _int(_metric(artifact, "affected_standard_rows_count"))
    review_rows = _int(_metric(artifact, "review_rows_count"))
    sec_possible = _int(_metric(artifact, "sec_evidence_possible_count"))
    reason_codes = _metric(artifact, "reason_codes")
    status = STATUS_BLOCKED if affected > 0 or review_rows > 0 else STATUS_READY
    action = "No core KPI closure action required."
    if status != STATUS_READY:
        action = "Review core KPI closure queue through SEC or manual evidence; do not impute values."
        if sec_possible > 0:
            action = f"{action} SEC evidence is structurally possible for {sec_possible} row(s)."
    return _row(
        input_area="CORE_KPI_CLOSURE",
        artifact_path=artifact.path,
        status=status,
        blocker_severity="P0_BLOCKER" if status == STATUS_BLOCKED else "NONE",
        count=affected or review_rows,
        sample_flag=False,
        reason_codes=reason_codes or ("REVIEW_CORE_DATA" if status == STATUS_BLOCKED else "CORE_KPI_CLOSURE_READY"),
        action=action,
        impact="Core-quality data gaps can affect monthly action interpretation; this row is additional to KPI provenance.",
        next_step="Use reviewed evidence workflows for missing core KPI rows; keep values unchanged in this aggregator.",
    )


def build_input_closure_rows(
    *,
    watchlist_summary: str = DEFAULT_WATCHLIST_SUMMARY,
    valuation_summary: str = DEFAULT_VALUATION_SUMMARY,
    dividend_fcf_summary: str = DEFAULT_DIVIDEND_FCF_SUMMARY,
    kpi_provenance_summary: str = DEFAULT_KPI_PROVENANCE_SUMMARY,
    core_kpi_summary: str = DEFAULT_CORE_KPI_SUMMARY,
) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    artifacts = {
        "WATCHLIST": _summary_artifact(watchlist_summary),
        "VALUATION": _summary_artifact(valuation_summary),
        "DIVIDEND_FCF": _summary_artifact(dividend_fcf_summary),
        "KPI_PROVENANCE": _summary_artifact(kpi_provenance_summary),
        "CORE_KPI_CLOSURE": _summary_artifact(core_kpi_summary),
    }
    rows = [
        _watchlist_row(artifacts["WATCHLIST"]),
        _valuation_row(artifacts["VALUATION"]),
        _dividend_fcf_row(artifacts["DIVIDEND_FCF"]),
        _kpi_provenance_row(artifacts["KPI_PROVENANCE"]),
    ]
    if artifacts["CORE_KPI_CLOSURE"].exists:
        rows.append(_core_kpi_row(artifacts["CORE_KPI_CLOSURE"]))
    missing = tuple(area for area in REQUIRED_AREAS if not artifacts[area].exists)
    return rows, missing


def overall_status(rows: list[dict[str, str]]) -> str:
    statuses = {row["status"] for row in rows}
    if statuses.intersection({STATUS_BLOCKED, STATUS_MISSING, STATUS_SAMPLE_ONLY}):
        return STATUS_BLOCKED
    if STATUS_REVIEW_REQUIRED in statuses:
        return STATUS_REVIEW_REQUIRED
    return STATUS_READY


def render_report(rows: list[dict[str, str]], *, as_of_date: str, missing_artifacts: tuple[str, ...]) -> str:
    status_counts = Counter(row["status"] for row in rows)
    overall = overall_status(rows)
    lines = [
        "# Personal Input Closure Report",
        "",
        f"As of date: `{as_of_date}`",
        "",
        "## Executive Summary",
        "",
        f"- Overall readiness status: `{overall}`",
    ]
    for status in (STATUS_BLOCKED, STATUS_MISSING, STATUS_REVIEW_REQUIRED, STATUS_SAMPLE_ONLY, STATUS_READY, STATUS_NOT_APPLICABLE):
        lines.append(f"- {status}: `{status_counts.get(status, 0)}`")
    if missing_artifacts:
        lines.append(f"- Missing required artifact groups: `{';'.join(missing_artifacts)}`")
    lines.extend(
        [
            "",
            "## Input Closure Matrix",
            "",
            "| Input Area | Artifact | Status | Severity | Open Items | Sample/Synthetic | Reasons |",
            "| --- | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['input_area']} | `{row['artifact_path']}` | `{row['status']}` | `{row['blocker_severity']}` | "
            f"{row['missing_or_review_items_count']} | `{row['sample_or_synthetic_flag']}` | `{row['reason_codes']}` |"
        )
    lines.extend(["", "## Operator Actions", ""])
    for row in rows:
        lines.append(f"- `{row['input_area']}`: {row['required_operator_action']}")
    lines.extend(["", "## Downstream Impact", ""])
    for row in rows:
        lines.append(f"- `{row['input_area']}`: {row['downstream_impact']}")
    lines.extend(
        [
            "- Monthly decision readiness remains blocked while P0 input rows are `BLOCKED`, `MISSING` or `SAMPLE_ONLY`.",
            "- Decision Capture quality improves only after the human operator closes or consciously records these input gaps.",
            "- Research Case readiness depends on reviewed source evidence, not this aggregator.",
            "- Outcome Attribution remains deferred.",
            "",
            "## Next Recommended Steps",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- `{row['input_area']}`: {row['next_recommended_step']}")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- No imputation of missing fundamentals, KPIs, valuations, dividend or FCF data.",
            "- No scoring formula or scoring weight changes.",
            "- No portfolio-rule changes.",
            "- No broker, order execution or auto-trading logic.",
            "- No sample, synthetic or demo data is converted into real personal input.",
            "- This report reads existing processed readiness artifacts and writes only the explicit output CSV and Markdown report.",
            "",
        ]
    )
    return "\n".join(lines)


def run_personal_input_closure(
    *,
    as_of_date: str | None = None,
    output: str = DEFAULT_OUTPUT,
    report: str = DEFAULT_REPORT,
    watchlist_summary: str = DEFAULT_WATCHLIST_SUMMARY,
    valuation_summary: str = DEFAULT_VALUATION_SUMMARY,
    dividend_fcf_summary: str = DEFAULT_DIVIDEND_FCF_SUMMARY,
    kpi_provenance_summary: str = DEFAULT_KPI_PROVENANCE_SUMMARY,
    core_kpi_summary: str = DEFAULT_CORE_KPI_SUMMARY,
) -> PersonalInputClosureResult:
    effective_date = as_of_date or date.today().isoformat()
    rows, missing_artifacts = build_input_closure_rows(
        watchlist_summary=watchlist_summary,
        valuation_summary=valuation_summary,
        dividend_fcf_summary=dividend_fcf_summary,
        kpi_provenance_summary=kpi_provenance_summary,
        core_kpi_summary=core_kpi_summary,
    )
    output_path = write_csv_rows(output, FIELDNAMES, rows)
    report_path = resolve_repo_path(report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(rows, as_of_date=effective_date, missing_artifacts=missing_artifacts), encoding="utf-8")
    return PersonalInputClosureResult(output=output_path, report=report_path, rows=rows, missing_artifacts=missing_artifacts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate personal input closure readiness from existing processed artifacts without creating investment data."
    )
    parser.add_argument("--as-of-date", default=date.today().isoformat())
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    parser.add_argument("--watchlist-summary", default=DEFAULT_WATCHLIST_SUMMARY)
    parser.add_argument("--valuation-summary", default=DEFAULT_VALUATION_SUMMARY)
    parser.add_argument("--dividend-fcf-summary", default=DEFAULT_DIVIDEND_FCF_SUMMARY)
    parser.add_argument("--kpi-provenance-summary", default=DEFAULT_KPI_PROVENANCE_SUMMARY)
    parser.add_argument("--core-kpi-summary", default=DEFAULT_CORE_KPI_SUMMARY)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_input_closure(
        as_of_date=args.as_of_date,
        output=args.output,
        report=args.report,
        watchlist_summary=args.watchlist_summary,
        valuation_summary=args.valuation_summary,
        dividend_fcf_summary=args.dividend_fcf_summary,
        kpi_provenance_summary=args.kpi_provenance_summary,
        core_kpi_summary=args.core_kpi_summary,
    )
    print(f"output={result.output}")
    print(f"report={result.report}")
    print(f"overall_status={overall_status(result.rows)}")
    print(f"rows_total={len(result.rows)}")
    print(f"missing_required_artifacts={';'.join(result.missing_artifacts)}")


if __name__ == "__main__":
    main()
