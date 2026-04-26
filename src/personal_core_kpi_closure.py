from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_KPI_TIER_INPUT = "data/processed/personal_kpi_tier_coverage.csv"
DEFAULT_SCORES_INPUT = "data/processed/personal_company_scores.csv"
DEFAULT_EVIDENCE_REGISTRY_INPUT = "data/processed/personal_fundamentals_evidence_registry.csv"
DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT = "data/processed/personal_fundamentals_master_evidence_applied.csv"
DEFAULT_SEC_SCOPE_REVIEW_INPUT = "data/processed/personal_sec_scope_review.csv"
DEFAULT_SEC_IDENTITY_APPLY_INPUT = "data/processed/personal_sec_identity_apply_changes.csv"
DEFAULT_METRIC_DEFINITIONS_INPUT = "configs/fundamentals_metric_definitions.yaml"
DEFAULT_QUEUE_OUTPUT = "data/processed/personal_core_kpi_closure_queue.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_core_kpi_closure_summary.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_core_kpi_closure_report.md"

DEFAULT_CORE_KPIS = ("revenue_cagr_5y", "eps_cagr_5y", "gross_margin", "operating_margin", "share_count_cagr_5y")
SUMMARY_FIELDS = ["metric", "value", "notes"]
QUEUE_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "current_score_quality_flag",
    "current_kpi_tier_status",
    "core_kpi_closure_status",
    "missing_core_kpis",
    "missing_core_kpi_count",
    "covered_core_kpis",
    "covered_core_kpi_count",
    "required_core_kpi_count",
    "sec_scope_status",
    "evidence_registry_status",
    "evidence_applied_status",
    "recommended_closure_path",
    "next_review_action",
    "reason_code",
]


@dataclass(frozen=True)
class CoreKpiClosureResult:
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


def identity_keys(row: dict[str, str]) -> tuple[tuple[str, str], ...]:
    isin = str(row.get("isin", "") or row.get("original_isin", "") or "").strip().upper()
    ticker = str(row.get("ticker", "") or row.get("original_ticker", "") or row.get("current_ticker", "") or "").strip().upper()
    keys: list[tuple[str, str]] = []
    if isin:
        keys.append(("isin", isin))
    if ticker and not isin:
        keys.append(("ticker", ticker))
    return tuple(keys)


def has_value(row: dict[str, str], field: str) -> bool:
    return str(row.get(field, "") or "").strip() != ""


def load_core_kpis(path_value: str, warnings: list[str]) -> tuple[str, tuple[str, ...]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        warnings.append(f"missing_input=metric_definitions:{safe_display_path(path_value)}")
        return "REVIEW", DEFAULT_CORE_KPIS
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    kpis = data.get("kpis") if isinstance(data.get("kpis"), dict) else {}
    core = tuple(sorted(name for name, spec in kpis.items() if isinstance(spec, dict) and spec.get("kpi_tier") == "CORE_QUALITY_REQUIRED"))
    if not core:
        warnings.append("core_kpi_contract_unknown=metric_definitions")
        return "REVIEW", DEFAULT_CORE_KPIS
    return "OK", core


def build_score_index(scores_rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    index: dict[tuple[str, str], dict[str, str]] = {}
    for row in scores_rows:
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


def build_master_index(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return build_score_index(rows)


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


def classify_registry_status(row: dict[str, str], missing_core: list[str], evidence_index: dict[tuple[str, str], set[str]], registry_present: bool) -> str:
    if not registry_present:
        return "UNKNOWN"
    evidence_kpis: set[str] = set()
    for key in identity_keys(row):
        evidence_kpis.update(evidence_index.get(key, set()))
    hits = set(missing_core).intersection(evidence_kpis)
    if len(hits) == len(missing_core) and missing_core:
        return "HAS_EVIDENCE"
    if hits:
        return "PARTIAL_EVIDENCE"
    return "NO_EVIDENCE"


def classify_applied_status(row: dict[str, str], missing_core: list[str], master_index: dict[tuple[str, str], dict[str, str]], master_present: bool) -> str:
    if not master_present:
        return "UNKNOWN"
    master_row = find_index_row(master_index, row)
    if master_row is None:
        return "NO_APPLIED_VALUE"
    hits = [kpi for kpi in missing_core if has_value(master_row, kpi)]
    if len(hits) == len(missing_core) and missing_core:
        return "HAS_APPLIED_VALUE"
    if hits:
        return "PARTIAL_APPLIED_VALUE"
    return "NO_APPLIED_VALUE"


def classify_path(sec_status: str, registry_status: str, applied_status: str, missing_core: list[str]) -> tuple[str, set[str], str]:
    reasons = {"NO_VALUE_CHANGES"}
    if not missing_core:
        return "REVIEW_EXISTING_EVIDENCE", reasons, "Review current core status; no missing core KPIs were identified."
    reasons.update({"REVIEW_CORE_DATA", "CORE_KPI_MISSING"})
    if applied_status in {"HAS_APPLIED_VALUE", "PARTIAL_APPLIED_VALUE"}:
        reasons.add("EVIDENCE_APPLIED_VALUE_MISSING" if applied_status == "PARTIAL_APPLIED_VALUE" else "REVIEW_CORE_DATA")
        return "REVIEW_EXISTING_EVIDENCE", reasons, "Review existing applied values and rerun tier coverage if appropriate."
    if registry_status in {"HAS_EVIDENCE", "PARTIAL_EVIDENCE"}:
        reasons.add("EVIDENCE_APPLIED_VALUE_MISSING")
        return "REVIEW_EXISTING_EVIDENCE", reasons, "Review existing evidence registry entries and stage reviewed updates."
    if sec_status == "SEC_ELIGIBLE":
        reasons.add("SEC_IDENTITY_AVAILABLE")
        return "SEC_EVIDENCE_POSSIBLE", reasons, "Run reviewed SEC evidence workflow for missing core KPIs."
    if sec_status == "SEC_IDENTITY_MISSING":
        reasons.update({"SEC_IDENTITY_MISSING", "MANUAL_EVIDENCE_REQUIRED"})
        return "MANUAL_EVIDENCE_REQUIRED", reasons, "Add SEC identity review or provide reviewed manual evidence."
    reasons.update({"EVIDENCE_REGISTRY_MISSING", "MANUAL_EVIDENCE_REQUIRED"})
    return "SOURCE_UNKNOWN", reasons, "Confirm source path, then add reviewed SEC or manual evidence."


def build_closure(
    *,
    kpi_rows: list[dict[str, str]],
    scores_rows: list[dict[str, str]],
    evidence_rows: list[dict[str, str]],
    applied_rows: list[dict[str, str]],
    sec_scope_rows: list[dict[str, str]],
    sec_identity_rows: list[dict[str, str]],
    core_kpis: tuple[str, ...],
    core_contract_status: str,
    registry_present: bool,
    applied_present: bool,
    sec_artifacts_present: bool,
    warnings: list[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    scores_index = build_score_index(scores_rows)
    evidence_index = build_evidence_index(evidence_rows)
    applied_index = build_master_index(applied_rows)
    sec_keys = build_sec_identity_keys(sec_scope_rows, sec_identity_rows)
    queue_rows: list[dict[str, str]] = []
    reason_union: set[str] = set()
    path_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    affected_rows = [
        row for row in kpi_rows
        if safe_upper(row.get("company_type_profile", "")) == "STANDARD"
        and safe_upper(row.get("resulting_monthly_action", "")) == "REVIEW_CORE_DATA"
    ]
    for row in sorted(affected_rows, key=lambda item: (str(item.get("isin", "")), str(item.get("ticker", "")))):
        score_row = find_index_row(scores_index, row) or {}
        missing_core = [kpi for kpi in split_list(row.get("missing_core_quality_kpis", "")) if kpi in core_kpis]
        covered_core = [kpi for kpi in core_kpis if kpi not in missing_core]
        sec_status = classify_sec_status(row, sec_keys, sec_artifacts_present)
        registry_status = classify_registry_status(row, missing_core, evidence_index, registry_present)
        applied_status = classify_applied_status(row, missing_core, applied_index, applied_present)
        closure_path, reasons, next_action = classify_path(sec_status, registry_status, applied_status, missing_core)
        if core_contract_status != "OK":
            reasons.add("CORE_KPI_CONTRACT_UNKNOWN")
        status = "REVIEW" if missing_core else "OK"
        status_counts[status] += 1
        path_counts[closure_path] += 1
        reason_union.update(reasons)
        queue_rows.append(
            {
                "ticker": row.get("ticker", ""),
                "isin": row.get("isin", ""),
                "company_name": row.get("company_name", ""),
                "company_type_profile": row.get("company_type_profile", ""),
                "current_score_quality_flag": score_row.get("data_quality_flag", ""),
                "current_kpi_tier_status": row.get("resulting_monthly_action", ""),
                "core_kpi_closure_status": status,
                "missing_core_kpis": "; ".join(missing_core),
                "missing_core_kpi_count": str(len(missing_core)),
                "covered_core_kpis": "; ".join(covered_core),
                "covered_core_kpi_count": str(len(covered_core)),
                "required_core_kpi_count": str(len(core_kpis)),
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

    add_metric("core_kpi_contract_status", core_contract_status, "Core KPI contract status from metric definitions.")
    add_metric("required_core_kpis", "; ".join(core_kpis), "Core-quality KPI fields.")
    add_metric("affected_standard_rows_count", len(affected_rows), "STANDARD rows with REVIEW_CORE_DATA.")
    add_metric("queue_rows_count", len(queue_rows), "Rows in personal_core_kpi_closure_queue.csv.")
    add_metric("ok_rows_count", status_counts.get("OK", 0), "Rows with no missing core KPIs in this closure queue.")
    add_metric("review_rows_count", status_counts.get("REVIEW", 0), "Rows still requiring core KPI review.")
    add_metric("not_applicable_rows_count", len(non_standard_rows), "Non-STANDARD rows excluded from STANDARD core closure.")
    for path_name in ("SEC_EVIDENCE_POSSIBLE", "MANUAL_EVIDENCE_REQUIRED", "REVIEW_EXISTING_EVIDENCE", "SOURCE_UNKNOWN", "PROFILE_NOT_STANDARD"):
        add_metric(f"closure_path__{path_name}", path_counts.get(path_name, 0), "Recommended closure path count.")
    add_metric("sec_evidence_possible_count", path_counts.get("SEC_EVIDENCE_POSSIBLE", 0), "Rows where SEC evidence workflow may close missing core KPIs.")
    add_metric("manual_evidence_required_count", path_counts.get("MANUAL_EVIDENCE_REQUIRED", 0), "Rows requiring manual evidence or SEC identity review.")
    add_metric("review_existing_evidence_count", path_counts.get("REVIEW_EXISTING_EVIDENCE", 0), "Rows with existing evidence/applied signals requiring review.")
    add_metric("source_unknown_count", path_counts.get("SOURCE_UNKNOWN", 0), "Rows with unknown source path.")
    add_metric("reason_codes", joined(reason_union), "Union of core KPI closure reason codes.")
    add_metric("no_value_changes_confirmed", "True", "No master, score, or evidence-apply values were changed.")
    add_metric("warnings_total", len(warnings), "Missing input warnings.")
    return queue_rows, sorted(summary_rows, key=lambda row: row["metric"])


def render_report(summary_rows: list[dict[str, str]], queue_rows: list[dict[str, str]], input_paths: dict[str, str]) -> str:
    summary = {row["metric"]: row["value"] for row in summary_rows}
    reason_counts = Counter(
        reason
        for row in queue_rows
        for reason in str(row.get("reason_code", "")).split(";")
        if reason
    )
    lines = [
        "# Personal Core KPI Closure Report",
        "",
        "## Executive Summary",
        f"- Affected STANDARD rows: {summary.get('affected_standard_rows_count', '0')}",
        f"- Queue rows: {summary.get('queue_rows_count', '0')}",
        f"- SEC evidence possible: {summary.get('sec_evidence_possible_count', '0')}",
        f"- Manual evidence required: {summary.get('manual_evidence_required_count', '0')}",
        f"- Review existing evidence: {summary.get('review_existing_evidence_count', '0')}",
        f"- No value changes confirmed: {summary.get('no_value_changes_confirmed', 'True')}",
        "",
        "## Input Artifacts",
    ]
    for label, path_value in sorted(input_paths.items()):
        lines.append(f"- `{label}`: `{safe_display_path(path_value)}`")
    lines.extend(
        [
            "",
            "## Core KPI Contract",
            f"- Contract status: `{summary.get('core_kpi_contract_status', 'UNKNOWN')}`",
            f"- Required core KPIs: `{summary.get('required_core_kpis', '')}`",
            "- Non-STANDARD profiles are not evaluated against the STANDARD core KPI contract.",
            "",
            "## Affected STANDARD Rows",
            "| ticker | isin | company_name | missing_core_kpis | sec_scope_status | evidence_registry_status | evidence_applied_status | recommended_closure_path | reason_code |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in queue_rows:
        lines.append(
            f"| {row['ticker']} | {row['isin']} | {row['company_name']} | {row['missing_core_kpis']} | "
            f"{row['sec_scope_status']} | {row['evidence_registry_status']} | {row['evidence_applied_status']} | "
            f"{row['recommended_closure_path']} | {row['reason_code']} |"
        )
    lines.extend(
        [
            "",
            "## Missing Core KPI Matrix",
        ]
    )
    for row in queue_rows:
        lines.append(f"- `{row['ticker']}`: missing `{row['missing_core_kpis']}`; covered `{row['covered_core_kpis']}`")
    lines.extend(
        [
            "",
            "## Evidence / SEC / Manual Closure Diagnostics",
            "- `SEC_EVIDENCE_POSSIBLE` means a reviewed SEC identity exists structurally; no SEC network call was made.",
            "- `REVIEW_EXISTING_EVIDENCE` means exact existing registry/applied signals should be reviewed before any apply step.",
            "- `MANUAL_EVIDENCE_REQUIRED` means no sufficient structural evidence path was found.",
            "",
            "## Recommended Review Actions",
        ]
    )
    for row in queue_rows:
        lines.append(f"- `{row['ticker']}`: {row['next_review_action']}")
    lines.extend(
        [
            "",
            "## No-Value-Change Guardrail",
            "- This module does not fetch SEC data, calculate missing KPIs, impute values, or write to master/score/evidence-apply artifacts.",
            "",
            "## Reconciliation Impact",
            "- `REVIEW_CORE_DATA` remains active until missing core KPI values are reviewed and applied through a separate workflow.",
            "- This patch only makes the core closure path explicit.",
            "",
            "## Remaining Demo Readiness Blockers",
            "- Watchlist sample/review state, valuation gaps, dividend/FCF gaps, provenance gaps, and freshness metadata review remain outside this patch.",
            "",
            "## Remaining Decision Readiness Blockers",
            "- Core KPI gaps remain REVIEW while values are missing or only structurally indicated.",
            "",
            "## Reason Code Counts",
        ]
    )
    for reason, count in sorted(reason_counts.items()):
        lines.append(f"- `{reason}`: {count}")
    lines.extend(
        [
            "",
            "## Recommended Next Patch",
            "`PATCH / DIVIDEND FCF INPUT CONTRACT / REVIEWED EVIDENCE QUEUE / NO IMPUTATION`",
            "",
        ]
    )
    return "\n".join(lines)


def run_personal_core_kpi_closure(
    *,
    kpi_tier_input: str = DEFAULT_KPI_TIER_INPUT,
    scores_input: str = DEFAULT_SCORES_INPUT,
    evidence_registry_input: str = DEFAULT_EVIDENCE_REGISTRY_INPUT,
    evidence_applied_master_input: str = DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT,
    sec_scope_review_input: str = DEFAULT_SEC_SCOPE_REVIEW_INPUT,
    sec_identity_apply_input: str = DEFAULT_SEC_IDENTITY_APPLY_INPUT,
    metric_definitions_input: str = DEFAULT_METRIC_DEFINITIONS_INPUT,
    queue_output: str = DEFAULT_QUEUE_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> CoreKpiClosureResult:
    warnings: list[str] = []
    core_contract_status, core_kpis = load_core_kpis(metric_definitions_input, warnings)
    kpi_rows, kpi_warnings, _ = optional_csv_rows(kpi_tier_input, "kpi_tier")
    scores_rows, score_warnings, _ = optional_csv_rows(scores_input, "scores")
    evidence_rows, evidence_warnings, registry_present = optional_csv_rows(evidence_registry_input, "evidence_registry")
    applied_rows, applied_warnings, applied_present = optional_csv_rows(evidence_applied_master_input, "evidence_applied_master")
    sec_scope_rows, sec_scope_warnings, sec_scope_present = optional_csv_rows(sec_scope_review_input, "sec_scope_review")
    sec_identity_rows, sec_identity_warnings, sec_identity_present = optional_csv_rows(sec_identity_apply_input, "sec_identity_apply")
    warnings.extend(kpi_warnings)
    warnings.extend(score_warnings)
    warnings.extend(evidence_warnings)
    warnings.extend(applied_warnings)
    warnings.extend(sec_scope_warnings)
    warnings.extend(sec_identity_warnings)
    queue_rows, summary_rows = build_closure(
        kpi_rows=kpi_rows,
        scores_rows=scores_rows,
        evidence_rows=evidence_rows,
        applied_rows=applied_rows,
        sec_scope_rows=sec_scope_rows,
        sec_identity_rows=sec_identity_rows,
        core_kpis=core_kpis,
        core_contract_status=core_contract_status,
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
        "queue_output": queue_output,
        "summary_output": summary_output,
    }
    queue_path = write_csv_rows(queue_output, QUEUE_FIELDS, queue_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(summary_rows, queue_rows, input_paths), encoding="utf-8")
    return CoreKpiClosureResult(
        queue_output=queue_path,
        summary_output=summary_path,
        report_output=report_path,
        queue_rows=queue_rows,
        summary_rows=summary_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build core KPI closure diagnostics without value changes.")
    parser.add_argument("--kpi-tier-input", default=DEFAULT_KPI_TIER_INPUT)
    parser.add_argument("--scores-input", default=DEFAULT_SCORES_INPUT)
    parser.add_argument("--evidence-registry-input", default=DEFAULT_EVIDENCE_REGISTRY_INPUT)
    parser.add_argument("--evidence-applied-master-input", default=DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT)
    parser.add_argument("--sec-scope-review-input", default=DEFAULT_SEC_SCOPE_REVIEW_INPUT)
    parser.add_argument("--sec-identity-apply-input", default=DEFAULT_SEC_IDENTITY_APPLY_INPUT)
    parser.add_argument("--metric-definitions-input", default=DEFAULT_METRIC_DEFINITIONS_INPUT)
    parser.add_argument("--queue-output", default=DEFAULT_QUEUE_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_core_kpi_closure(
        kpi_tier_input=args.kpi_tier_input,
        scores_input=args.scores_input,
        evidence_registry_input=args.evidence_registry_input,
        evidence_applied_master_input=args.evidence_applied_master_input,
        sec_scope_review_input=args.sec_scope_review_input,
        sec_identity_apply_input=args.sec_identity_apply_input,
        metric_definitions_input=args.metric_definitions_input,
        queue_output=args.queue_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    summary = {row["metric"]: row["value"] for row in result.summary_rows}
    print(f"queue_output={result.queue_output}")
    print(f"summary_output={result.summary_output}")
    print(f"report_output={result.report_output}")
    print(f"affected_standard_rows_count={summary.get('affected_standard_rows_count', '0')}")
    print(f"warnings_total={summary.get('warnings_total', '0')}")


if __name__ == "__main__":
    main()
