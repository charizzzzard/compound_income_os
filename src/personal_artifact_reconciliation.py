from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_SCORES_INPUT = "data/processed/personal_company_scores.csv"
DEFAULT_SCORE_AUDIT_INPUT = "data/processed/personal_score_audit.csv"
DEFAULT_KPI_TIER_INPUT = "data/processed/personal_kpi_tier_coverage.csv"
DEFAULT_MISSING_KPI_SUMMARY_INPUT = "data/processed/personal_missing_kpi_closure_summary.csv"
DEFAULT_MISSING_KPI_HOLDINGS_INPUT = "data/processed/personal_missing_kpi_closure_holdings.csv"
DEFAULT_EVIDENCE_DELTA_SUMMARY_INPUT = "data/processed/personal_evidence_applied_downstream_delta_summary.csv"
DEFAULT_EVIDENCE_DELTA_HOLDINGS_INPUT = "data/processed/personal_evidence_applied_downstream_delta_holdings.csv"
DEFAULT_ARTIFACT_FRESHNESS_SUMMARY_INPUT = "data/processed/personal_artifact_freshness_summary.csv"
DEFAULT_MONTHLY_INPUT = "data/processed/personal_monthly_buy_ranking.csv"
DEFAULT_MONTHLY_ACTION_SUMMARY_INPUT = "data/processed/personal_monthly_action_compatibility_summary.csv"
DEFAULT_WATCHLIST_INPUT = "data/processed/personal_watchlist_ranked.csv"
DEFAULT_WATCHLIST_GATE_SUMMARY_INPUT = "data/processed/personal_watchlist_input_gate_summary.csv"
DEFAULT_USED_INPUTS_INPUT = "data/processed/personal_run_used_inputs.csv"
DEFAULT_MANIFEST_INPUT = "data/processed/personal_run_manifest.json"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_artifact_reconciliation_summary.csv"
DEFAULT_CHECKS_OUTPUT = "data/processed/personal_artifact_reconciliation_checks.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_artifact_reconciliation_report.md"

SUMMARY_FIELDS = ["metric", "value", "notes"]
CHECK_FIELDS = [
    "check_id",
    "category",
    "status",
    "reason_codes",
    "observed_value",
    "expected_value",
    "evidence",
    "recommended_next_action",
]
READINESS_ORDER = {"PASS": 0, "REVIEW": 1, "BLOCKED": 2, "NOT_AVAILABLE": 3}


@dataclass(frozen=True)
class ArtifactReconciliationResult:
    summary_output: Path
    checks_output: Path
    report_output: Path
    summary_rows: list[dict[str, str]]
    check_rows: list[dict[str, str]]
    demo_status: str
    decision_status: str
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


def count_upper(rows: list[dict[str, str]], column: str) -> Counter[str]:
    return Counter(safe_upper(row.get(column, "")) or "BLANK" for row in rows)


def summary_map(rows: list[dict[str, str]]) -> dict[str, str]:
    return {str(row.get("metric", "") or "").strip(): str(row.get("value", "") or "").strip() for row in rows}


def int_value(value: Any) -> int:
    try:
        return int(str(value or "0").strip())
    except ValueError:
        return 0


def bool_text(value: bool) -> str:
    return "True" if value else "False"


def joined_reasons(reasons: set[str] | list[str] | tuple[str, ...]) -> str:
    return ";".join(sorted(reason for reason in reasons if reason))


def status_max(statuses: list[str]) -> str:
    if not statuses:
        return "PASS"
    return max(statuses, key=lambda status: READINESS_ORDER.get(status, 99))


def add_check(
    checks: list[dict[str, str]],
    *,
    check_id: str,
    category: str,
    status: str,
    reason_codes: set[str] | list[str] | tuple[str, ...],
    observed_value: str,
    expected_value: str,
    evidence: str,
    recommended_next_action: str,
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "category": category,
            "status": status,
            "reason_codes": joined_reasons(reason_codes),
            "observed_value": observed_value,
            "expected_value": expected_value,
            "evidence": evidence,
            "recommended_next_action": recommended_next_action,
        }
    )


def extract_fundamentals_source_mode(used_input_rows: list[dict[str, str]], manifest: dict[str, Any]) -> tuple[str, str]:
    source_mode = ""
    scoring_master = ""
    for row in used_input_rows:
        if str(row.get("stage_name", "") or "").strip() != "scoring":
            continue
        if str(row.get("input_role", "") or "").strip() == "fundamentals_master":
            scoring_master = str(row.get("input_path", "") or "").strip()
        notes = str(row.get("notes", "") or "")
        if "fundamentals_source_mode=" in notes:
            source_mode = notes.split("fundamentals_source_mode=", 1)[1].split(";", 1)[0].split(",", 1)[0].strip()
    stages = manifest.get("stages") if isinstance(manifest.get("stages"), list) else []
    for stage in stages:
        if not isinstance(stage, dict) or stage.get("stage_name") != "scoring":
            continue
        used_inputs = stage.get("used_inputs") if isinstance(stage.get("used_inputs"), dict) else {}
        source_mode = str(used_inputs.get("fundamentals_source_mode", source_mode) or source_mode)
        scoring_master = str(used_inputs.get("fundamentals_master", scoring_master) or scoring_master)
    return source_mode or "NOT_AVAILABLE", scoring_master


def watchlist_input_path(used_input_rows: list[dict[str, str]]) -> str:
    for row in used_input_rows:
        if str(row.get("stage_name", "") or "").strip() == "watchlist" and str(row.get("input_role", "") or "").strip() == "watchlist_input":
            return str(row.get("input_path", "") or "").strip()
    return ""


def build_reconciliation(
    *,
    scores_rows: list[dict[str, str]],
    score_audit_rows: list[dict[str, str]],
    kpi_tier_rows: list[dict[str, str]],
    missing_kpi_summary_rows: list[dict[str, str]],
    missing_kpi_holdings_rows: list[dict[str, str]],
    evidence_delta_summary_rows: list[dict[str, str]],
    evidence_delta_holdings_rows: list[dict[str, str]],
    artifact_freshness_summary_rows: list[dict[str, str]],
    monthly_rows: list[dict[str, str]],
    monthly_action_summary_rows: list[dict[str, str]],
    watchlist_rows: list[dict[str, str]],
    watchlist_gate_summary_rows: list[dict[str, str]],
    used_input_rows: list[dict[str, str]],
    manifest: dict[str, Any],
    warnings: list[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]], str, str]:
    checks: list[dict[str, str]] = []
    summary_rows: list[dict[str, str]] = []

    score_counts = count_upper(scores_rows, "data_quality_flag")
    tier_action_counts = count_upper(kpi_tier_rows, "resulting_monthly_action")
    watchlist_status_counts = count_upper(watchlist_rows, "status")
    watchlist_quality_counts = count_upper(watchlist_rows, "data_quality_flag")
    monthly_target_counts = count_upper(monthly_rows, "target_action")
    monthly_action_summary = summary_map(monthly_action_summary_rows)
    watchlist_gate_summary = summary_map(watchlist_gate_summary_rows)
    missing_summary = summary_map(missing_kpi_summary_rows)
    delta_summary = summary_map(evidence_delta_summary_rows)
    freshness_summary = summary_map(artifact_freshness_summary_rows)
    source_mode, scoring_master = extract_fundamentals_source_mode(used_input_rows, manifest)
    watchlist_path = watchlist_input_path(used_input_rows)

    delta_score_counts = {
        "OK": int_value(delta_summary.get("score_data_quality__OK")),
        "REVIEW": int_value(delta_summary.get("score_data_quality__REVIEW")),
        "MISSING_DATA": int_value(delta_summary.get("score_data_quality__MISSING_DATA")),
        "BLOCKED": int_value(delta_summary.get("score_data_quality__BLOCKED")),
    }
    score_count_mismatches = {
        key
        for key, delta_value in delta_score_counts.items()
        if int(score_counts.get(key, 0)) != delta_value
    }
    freshness_reason_codes = {
        reason for reason in str(freshness_summary.get("freshness_reason_codes", "")).split(";") if reason
    }
    artifact_drift_active = freshness_summary.get("artifact_drift_active") == "True"
    freshness_explains_mismatch = bool(freshness_summary) and score_count_mismatches and not artifact_drift_active
    score_delta_reason_codes: set[str] = set()
    if score_count_mismatches:
        if artifact_drift_active:
            score_delta_reason_codes.add("ARTIFACT_DRIFT")
        elif freshness_explains_mismatch:
            if "MISSING_METADATA" in freshness_reason_codes:
                score_delta_reason_codes.add("MISSING_METADATA")
            if "STALE_DERIVED_ARTIFACT" in freshness_reason_codes or "RUN_ID_MISMATCH" in freshness_reason_codes:
                score_delta_reason_codes.add("STALE_ARTIFACT")
            if "DERIVED_ARTIFACT_DEFERRED" in freshness_reason_codes:
                score_delta_reason_codes.add("DERIVED_ARTIFACT_DEFERRED")
            if not score_delta_reason_codes:
                score_delta_reason_codes.add("FRESHNESS_UNKNOWN")
        else:
            score_delta_reason_codes.add("ARTIFACT_DRIFT")
    add_check(
        checks,
        check_id="score_vs_delta_data_quality",
        category="counter_reconciliation",
        status=("BLOCKED" if "ARTIFACT_DRIFT" in score_delta_reason_codes else "REVIEW") if score_count_mismatches else "PASS",
        reason_codes=score_delta_reason_codes,
        observed_value=(
            f"scores={dict(sorted(score_counts.items()))}; delta={dict(sorted(delta_score_counts.items()))}; "
            f"artifact_drift_active={artifact_drift_active}; freshness_reasons={joined_reasons(freshness_reason_codes)}"
        ),
        expected_value="score CSV data_quality_flag counts match evidence-applied delta summary counts",
        evidence="personal_company_scores.csv; personal_evidence_applied_downstream_delta_summary.csv; personal_artifact_freshness_summary.csv",
        recommended_next_action="Add comparable metadata or regenerate stale derived delta; do not treat stale counters as current truth." if score_count_mismatches else "No action.",
    )

    standard_rows = [row for row in kpi_tier_rows if safe_upper(row.get("company_type_profile", "")) == "STANDARD"]
    valuation_missing_rows = [row for row in standard_rows if safe_upper(row.get("valuation_data_status", "")) in {"MISSING", "PARTIAL"}]
    dividend_missing_rows = [row for row in standard_rows if safe_upper(row.get("dividend_fcf_data_status", "")) in {"MISSING", "PARTIAL"}]
    core_review_rows = [row for row in standard_rows if safe_upper(row.get("resulting_monthly_action", "")) == "REVIEW_CORE_DATA"]
    add_check(
        checks,
        check_id="standard_valuation_required",
        category="decision_readiness",
        status="BLOCKED" if valuation_missing_rows else "PASS",
        reason_codes={"MISSING_VALUATION_REQUIRED"} if valuation_missing_rows else set(),
        observed_value=f"{len(valuation_missing_rows)}/{len(standard_rows)} STANDARD rows missing valuation-required data",
        expected_value="0 STANDARD rows missing valuation-required data before decision-ready ranking",
        evidence="personal_kpi_tier_coverage.csv",
        recommended_next_action="Add reviewed valuation input contract or manual overlay; do not impute values." if valuation_missing_rows else "No action.",
    )
    add_check(
        checks,
        check_id="standard_dividend_fcf_required",
        category="decision_readiness",
        status="REVIEW" if dividend_missing_rows else "PASS",
        reason_codes={"MISSING_DIVIDEND_FCF_REQUIRED"} if dividend_missing_rows else set(),
        observed_value=f"{len(dividend_missing_rows)}/{len(standard_rows)} STANDARD rows missing dividend/FCF-required data",
        expected_value="Dividend/FCF gaps visible and blocked for dividend-growth decision use",
        evidence="personal_kpi_tier_coverage.csv",
        recommended_next_action="Add reviewed FCF/dividend evidence or keep rows in REVIEW." if dividend_missing_rows else "No action.",
    )
    add_check(
        checks,
        check_id="standard_core_review",
        category="decision_readiness",
        status="BLOCKED" if core_review_rows else "PASS",
        reason_codes={"REVIEW_CORE_DATA"} if core_review_rows else set(),
        observed_value=f"{len(core_review_rows)} STANDARD rows with REVIEW_CORE_DATA",
        expected_value="0 STANDARD rows with REVIEW_CORE_DATA before decision-ready ranking",
        evidence="personal_kpi_tier_coverage.csv",
        recommended_next_action="Close core-quality KPI evidence or keep blocked." if core_review_rows else "No action.",
    )

    monthly_fields = set(monthly_rows[0].keys()) if monthly_rows else set()
    has_target_action = "target_action" in monthly_fields
    has_allocation_status = "allocation_status" in monthly_fields
    has_monthly_action = "monthly_action" in monthly_fields
    monthly_compat_available = monthly_action_summary.get("monthly_action_compatibility_available") == "True"
    monthly_compat_resolved = monthly_action_summary.get("monthly_schema_drift_resolved") == "True"
    monthly_compat_forbidden_total = int_value(monthly_action_summary.get("forbidden_monthly_action_values_total"))
    monthly_schema_drift = has_target_action and has_allocation_status and not has_monthly_action and not (
        monthly_compat_available and monthly_compat_resolved and monthly_compat_forbidden_total == 0
    )
    add_check(
        checks,
        check_id="monthly_schema_contract",
        category="schema",
        status="REVIEW" if monthly_schema_drift else ("NOT_AVAILABLE" if not monthly_rows else "PASS"),
        reason_codes={"MONTHLY_SCHEMA_DRIFT"} if monthly_schema_drift else set(),
        observed_value=f"fields={','.join(sorted(monthly_fields))}; compatibility_available={monthly_compat_available}; compatibility_resolved={monthly_compat_resolved}; forbidden_monthly_action_values_total={monthly_compat_forbidden_total}",
        expected_value="Monthly ranking exposes monthly_action directly or through a neutral compatibility summary",
        evidence="personal_monthly_buy_ranking.csv; personal_monthly_action_compatibility_summary.csv",
        recommended_next_action="Generate neutral monthly_action compatibility artifact or update report readers in a dedicated schema patch." if monthly_schema_drift else "No action.",
    )

    gate_reason_codes = {
        reason for reason in str(watchlist_gate_summary.get("watchlist_reason_codes", "")).split(";") if reason
    }
    gate_status = watchlist_gate_summary.get("watchlist_readiness_status", "")
    sample_watchlist = watchlist_path.replace("\\", "/") == "data/raw/sample_watchlist.csv"
    watchlist_not_ready = bool(watchlist_rows) and (
        sum(watchlist_status_counts.get(status, 0) for status in ("REVIEW", "BLOCKED")) == len(watchlist_rows)
        or sum(watchlist_quality_counts.get(status, 0) for status in ("REVIEW", "MISSING_DATA", "BLOCKED")) == len(watchlist_rows)
    )
    watchlist_reasons = set(gate_reason_codes)
    if not watchlist_reasons:
        if sample_watchlist:
            watchlist_reasons.add("WATCHLIST_SAMPLE_INPUT")
        if watchlist_not_ready:
            watchlist_reasons.add("WATCHLIST_REVIEW_OR_MISSING_DATA")
    if gate_status in {"BLOCKED", "REVIEW", "NOT_AVAILABLE", "PASS"}:
        watchlist_status = gate_status
    else:
        watchlist_status = "BLOCKED" if sample_watchlist else ("REVIEW" if watchlist_not_ready else "PASS")
    add_check(
        checks,
        check_id="watchlist_demo_decision_readiness",
        category="watchlist",
        status=watchlist_status,
        reason_codes=watchlist_reasons,
        observed_value=(
            f"watchlist_input={watchlist_path or 'NOT_AVAILABLE'}; "
            f"gate_input_status={watchlist_gate_summary.get('watchlist_input_status', 'NOT_AVAILABLE')}; "
            f"gate_data_status={watchlist_gate_summary.get('watchlist_data_status', 'NOT_AVAILABLE')}; "
            f"gate_readiness_status={watchlist_gate_summary.get('watchlist_readiness_status', 'NOT_AVAILABLE')}; "
            f"status_counts={dict(sorted(watchlist_status_counts.items()))}; "
            f"data_quality_counts={dict(sorted(watchlist_quality_counts.items()))}"
        ),
        expected_value="Reviewed non-sample watchlist with rows not all REVIEW/MISSING_DATA for product-like decision use",
        evidence="personal_run_used_inputs.csv; personal_watchlist_ranked.csv; personal_watchlist_input_gate_summary.csv",
        recommended_next_action="Use a reviewed watchlist input or label current output as sample/demo-only." if watchlist_reasons else "No action.",
    )

    add_check(
        checks,
        check_id="fundamentals_source_mode",
        category="used_inputs",
        status="PASS" if source_mode == "EVIDENCE_APPLIED" else "REVIEW",
        reason_codes=set() if source_mode == "EVIDENCE_APPLIED" else {"FUNDAMENTALS_SOURCE_MODE_REVIEW"},
        observed_value=f"fundamentals_source_mode={source_mode}; scoring_master={scoring_master}",
        expected_value="fundamentals_source_mode=EVIDENCE_APPLIED for current evidence-applied baseline",
        evidence="personal_run_used_inputs.csv; personal_run_manifest.json",
        recommended_next_action="Run downstream with --use-evidence-applied-master." if source_mode != "EVIDENCE_APPLIED" else "No action.",
    )

    add_check(
        checks,
        check_id="per_kpi_provenance",
        category="trust_chain",
        status="REVIEW",
        reason_codes={"PROVENANCE_INCOMPLETE"},
        observed_value=f"score_audit_rows={len(score_audit_rows)}; evidence_delta_holdings_rows={len(evidence_delta_holdings_rows)}; missing_kpi_holdings_rows={len(missing_kpi_holdings_rows)}",
        expected_value="Each score-relevant KPI can be traced to raw/profiled/evidence/overlay source metadata",
        evidence="personal_score_audit.csv exists, but per-KPI source-reference join is not fully materialized",
        recommended_next_action="Add a dedicated KPI provenance audit artifact.",
    )

    if warnings:
        add_check(
            checks,
            check_id="input_availability",
            category="inputs",
            status="NOT_AVAILABLE",
            reason_codes={"INPUT_NOT_AVAILABLE"},
            observed_value=";".join(sorted(warnings)),
            expected_value="All reconciliation inputs exist",
            evidence="input path checks",
            recommended_next_action="Generate missing upstream artifacts before relying on readiness status.",
        )

    blocking_reasons = {
        reason
        for row in checks
        if row["status"] in {"BLOCKED", "REVIEW", "NOT_AVAILABLE"}
        for reason in row["reason_codes"].split(";")
        if reason
    }
    demo_blockers = {"ARTIFACT_DRIFT", "MONTHLY_SCHEMA_DRIFT", "WATCHLIST_SAMPLE_INPUT", "INPUT_NOT_AVAILABLE"}
    decision_blockers = {
        "ARTIFACT_DRIFT",
        "MISSING_VALUATION_REQUIRED",
        "REVIEW_CORE_DATA",
        "WATCHLIST_SAMPLE_INPUT",
        "MONTHLY_SCHEMA_DRIFT",
        "PROVENANCE_INCOMPLETE",
    }
    demo_status = "BLOCKED" if blocking_reasons.intersection(demo_blockers) else status_max([row["status"] for row in checks])
    decision_status = "BLOCKED" if blocking_reasons.intersection(decision_blockers) else status_max([row["status"] for row in checks])

    def add_metric(metric: str, value: Any, notes: str) -> None:
        summary_rows.append({"metric": metric, "value": str(value), "notes": notes})

    add_metric("demo_readiness_status", demo_status, "Conservative status from reconciliation checks.")
    add_metric("decision_readiness_status", decision_status, "Conservative status from reconciliation checks.")
    add_metric("readiness_reason_codes", joined_reasons(blocking_reasons), "Union of BLOCKED/REVIEW/NOT_AVAILABLE reason codes.")
    add_metric("score_rows_total", len(scores_rows), "Rows in personal_company_scores.csv.")
    for status in ("OK", "REVIEW", "MISSING_DATA", "BLOCKED"):
        add_metric(f"score_data_quality__{status}", score_counts.get(status, 0), "Current score CSV data-quality count.")
        add_metric(f"delta_score_data_quality__{status}", delta_score_counts.get(status, 0), "Evidence-applied delta summary data-quality count.")
    add_metric("score_delta_mismatch_statuses", joined_reasons(score_count_mismatches), "Statuses whose score CSV and delta summary counts differ.")
    add_metric("artifact_drift_active", bool_text(artifact_drift_active), "Observed from artifact freshness summary when present.")
    add_metric("artifact_freshness_reason_codes", joined_reasons(freshness_reason_codes), "Freshness reason codes from artifact freshness summary.")
    add_metric("artifact_freshness_summary_available", bool_text(bool(freshness_summary)), "Artifact freshness summary was loaded.")
    if "unresolved_current_artifact_drift_total" in freshness_summary:
        add_metric("unresolved_current_artifact_drift_total", freshness_summary["unresolved_current_artifact_drift_total"], "Current unexplained drift count from freshness summary.")
    add_metric("standard_rows_total", len(standard_rows), "Rows in KPI tier coverage with company_type_profile=STANDARD.")
    add_metric("standard_missing_valuation_required_rows_total", len(valuation_missing_rows), "STANDARD rows missing valuation-required data.")
    add_metric("standard_missing_dividend_fcf_required_rows_total", len(dividend_missing_rows), "STANDARD rows missing dividend/FCF-required data.")
    add_metric("standard_review_core_data_rows_total", len(core_review_rows), "STANDARD rows with resulting_monthly_action=REVIEW_CORE_DATA.")
    for action, count in sorted(tier_action_counts.items()):
        add_metric(f"kpi_tier_resulting_monthly_action__{action}", count, "KPI tier resulting monthly action count.")
    add_metric("missing_kpi_closure_missing_required_kpi_total", missing_summary.get("missing_required_kpi_total", "NOT_AVAILABLE"), "Baseline from missing-KPI closure summary.")
    add_metric("evidence_delta_current_missing_required_kpi_total", delta_summary.get("current_missing_required_kpi_total", "NOT_AVAILABLE"), "Current missing required KPI count from evidence-applied delta summary.")
    add_metric("monthly_rows_total", len(monthly_rows), "Rows in personal_monthly_buy_ranking.csv.")
    add_metric("monthly_has_target_action", bool_text(has_target_action), "Schema check.")
    add_metric("monthly_has_allocation_status", bool_text(has_allocation_status), "Schema check.")
    add_metric("monthly_has_monthly_action", bool_text(has_monthly_action), "Schema check.")
    add_metric("monthly_action_compatibility_available", bool_text(monthly_compat_available), "Neutral monthly_action compatibility artifact available.")
    add_metric("monthly_schema_drift_resolved", bool_text(not monthly_schema_drift and bool(monthly_rows)), "Monthly schema drift check resolved by direct field or companion compatibility artifact.")
    add_metric("monthly_action_forbidden_values_total", monthly_compat_forbidden_total, "Forbidden monthly_action values in compatibility summary.")
    for row in monthly_action_summary_rows:
        metric = row.get("metric", "")
        if metric.startswith("monthly_action__"):
            add_metric(metric, row.get("value", "0"), "Neutral monthly_action count from compatibility summary.")
    for action, count in sorted(monthly_target_counts.items()):
        add_metric(f"monthly_target_action__{action}", count, "Monthly target_action count.")
    add_metric("watchlist_rows_total", len(watchlist_rows), "Rows in personal_watchlist_ranked.csv.")
    add_metric("watchlist_input_path", safe_display_path(watchlist_path or "NOT_AVAILABLE"), "Observed watchlist input path from used inputs.")
    for metric in (
        "watchlist_input_status",
        "watchlist_data_status",
        "watchlist_readiness_status",
        "watchlist_sample_input_active",
        "watchlist_review_or_missing_data_active",
    ):
        if metric in watchlist_gate_summary:
            add_metric(metric, watchlist_gate_summary[metric], "Watchlist input gate summary metric.")
    for status, count in sorted(watchlist_status_counts.items()):
        add_metric(f"watchlist_status__{status}", count, "Watchlist status count.")
    for status, count in sorted(watchlist_quality_counts.items()):
        add_metric(f"watchlist_data_quality__{status}", count, "Watchlist data-quality count.")
    add_metric("scoring_fundamentals_source_mode", source_mode, "Observed from used-inputs/manifest.")
    add_metric("scoring_fundamentals_master_path", safe_display_path(scoring_master), "Observed scoring fundamentals master path.")
    add_metric("checks_total", len(checks), "Number of reconciliation checks.")
    add_metric("blocked_checks_total", sum(1 for row in checks if row["status"] == "BLOCKED"), "Checks with BLOCKED status.")
    add_metric("review_checks_total", sum(1 for row in checks if row["status"] == "REVIEW"), "Checks with REVIEW status.")
    add_metric("not_available_checks_total", sum(1 for row in checks if row["status"] == "NOT_AVAILABLE"), "Checks with NOT_AVAILABLE status.")
    add_metric("warnings_total", len(warnings), "Missing input warnings.")

    return sorted(summary_rows, key=lambda row: row["metric"]), sorted(checks, key=lambda row: row["check_id"]), demo_status, decision_status


def render_report(summary_rows: list[dict[str, str]], check_rows: list[dict[str, str]], input_paths: dict[str, str]) -> str:
    summary = summary_map(summary_rows)
    blocked = [row for row in check_rows if row["status"] == "BLOCKED"]
    review = [row for row in check_rows if row["status"] == "REVIEW"]

    lines = [
        "# Personal Artifact Reconciliation Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## 1. Executive Summary",
        "",
        f"- Demo readiness: `{summary.get('demo_readiness_status', 'NOT_AVAILABLE')}`",
        f"- Decision readiness: `{summary.get('decision_readiness_status', 'NOT_AVAILABLE')}`",
        f"- Reason codes: `{summary.get('readiness_reason_codes', '') or 'none'}`",
        f"- Scoring fundamentals source mode: `{summary.get('scoring_fundamentals_source_mode', 'NOT_AVAILABLE')}`",
        "",
        "This report reconciles existing processed artifacts only. It does not change scores, formulas, fundamentals values, watchlist values, or monthly ranking outputs.",
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
            "## 3. Counter Reconciliation",
            "",
            "| Metric | Value | Notes |",
            "| --- | --- | --- |",
        ]
    )
    for row in summary_rows:
        lines.append(f"| `{row['metric']}` | `{row['value']}` | {row['notes']} |")

    lines.extend(
        [
            "",
            "## 4. Drift Findings",
            "",
            "| Check | Status | Reasons | Evidence |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in check_rows:
        if row["status"] in {"BLOCKED", "REVIEW", "NOT_AVAILABLE"}:
            lines.append(f"| `{row['check_id']}` | `{row['status']}` | `{row['reason_codes']}` | {row['evidence']} |")

    lines.extend(
        [
            "",
            "## 5. Demo Readiness",
            "",
            f"Status: `{summary.get('demo_readiness_status', 'NOT_AVAILABLE')}`",
            "",
            "Demo readiness is blocked when processed artifacts disagree, schema drift can hide action states, or sample inputs are used without explicit labeling.",
            "",
            "## 6. Decision Readiness",
            "",
            f"Status: `{summary.get('decision_readiness_status', 'NOT_AVAILABLE')}`",
            "",
            "Decision readiness remains blocked while valuation-required data, core review data, sample watchlist inputs, schema drift, or incomplete KPI provenance remain unresolved.",
            "",
            "## 7. Blockers",
            "",
        ]
    )
    if blocked:
        for row in blocked:
            lines.append(f"- `{row['check_id']}`: `{row['reason_codes']}`. {row['recommended_next_action']}")
    else:
        lines.append("- None.")

    lines.extend(["", "## 8. Review Items", ""])
    if review:
        for row in review:
            lines.append(f"- `{row['check_id']}`: `{row['reason_codes']}`. {row['recommended_next_action']}")
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## 9. Can Remain Review",
            "",
            "- Advanced optional KPI gaps can remain visible if they do not drive candidate status.",
            "- FINANCIAL, OTHER, ETF, ADR, and non-US rows can remain separate from STANDARD scoring until explicit profile models exist.",
            "- Dividend/FCF gaps can remain REVIEW for a data-quality demo, but not for a decision-quality demo.",
            "",
            "## 10. Recommended Next Patch",
            "",
            "Implement a KPI provenance audit that maps score-relevant KPI values to raw/profiled/evidence/overlay source metadata, then address valuation-required input contracts without imputation.",
            "",
        ]
    )
    return "\n".join(lines)


def run_personal_artifact_reconciliation(
    *,
    scores_input: str = DEFAULT_SCORES_INPUT,
    score_audit_input: str = DEFAULT_SCORE_AUDIT_INPUT,
    kpi_tier_input: str = DEFAULT_KPI_TIER_INPUT,
    missing_kpi_summary_input: str = DEFAULT_MISSING_KPI_SUMMARY_INPUT,
    missing_kpi_holdings_input: str = DEFAULT_MISSING_KPI_HOLDINGS_INPUT,
    evidence_delta_summary_input: str = DEFAULT_EVIDENCE_DELTA_SUMMARY_INPUT,
    evidence_delta_holdings_input: str = DEFAULT_EVIDENCE_DELTA_HOLDINGS_INPUT,
    artifact_freshness_summary_input: str = DEFAULT_ARTIFACT_FRESHNESS_SUMMARY_INPUT,
    monthly_input: str = DEFAULT_MONTHLY_INPUT,
    monthly_action_summary_input: str = DEFAULT_MONTHLY_ACTION_SUMMARY_INPUT,
    watchlist_input: str = DEFAULT_WATCHLIST_INPUT,
    watchlist_gate_summary_input: str = DEFAULT_WATCHLIST_GATE_SUMMARY_INPUT,
    used_inputs_input: str = DEFAULT_USED_INPUTS_INPUT,
    manifest_input: str = DEFAULT_MANIFEST_INPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    checks_output: str = DEFAULT_CHECKS_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> ArtifactReconciliationResult:
    warnings: list[str] = []
    input_specs = {
        "scores": scores_input,
        "score_audit": score_audit_input,
        "kpi_tier": kpi_tier_input,
        "missing_kpi_summary": missing_kpi_summary_input,
        "missing_kpi_holdings": missing_kpi_holdings_input,
        "evidence_delta_summary": evidence_delta_summary_input,
        "evidence_delta_holdings": evidence_delta_holdings_input,
        "artifact_freshness_summary": artifact_freshness_summary_input,
        "monthly": monthly_input,
        "monthly_action_summary": monthly_action_summary_input,
        "watchlist": watchlist_input,
        "watchlist_gate_summary": watchlist_gate_summary_input,
        "used_inputs": used_inputs_input,
    }
    loaded: dict[str, list[dict[str, str]]] = {}
    for label, path in input_specs.items():
        rows, row_warnings = optional_csv_rows(path, label)
        loaded[label] = rows
        warnings.extend(row_warnings)
    manifest, manifest_warnings = optional_json(manifest_input, "manifest")
    warnings.extend(manifest_warnings)

    summary_rows, check_rows, demo_status, decision_status = build_reconciliation(
        scores_rows=loaded["scores"],
        score_audit_rows=loaded["score_audit"],
        kpi_tier_rows=loaded["kpi_tier"],
        missing_kpi_summary_rows=loaded["missing_kpi_summary"],
        missing_kpi_holdings_rows=loaded["missing_kpi_holdings"],
        evidence_delta_summary_rows=loaded["evidence_delta_summary"],
        evidence_delta_holdings_rows=loaded["evidence_delta_holdings"],
        artifact_freshness_summary_rows=loaded["artifact_freshness_summary"],
        monthly_rows=loaded["monthly"],
        monthly_action_summary_rows=loaded["monthly_action_summary"],
        watchlist_rows=loaded["watchlist"],
        watchlist_gate_summary_rows=loaded["watchlist_gate_summary"],
        used_input_rows=loaded["used_inputs"],
        manifest=manifest,
        warnings=warnings,
    )
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    checks_path = write_csv_rows(checks_output, CHECK_FIELDS, check_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_report(summary_rows, check_rows, {**input_specs, "manifest": manifest_input}),
        encoding="utf-8",
    )
    return ArtifactReconciliationResult(
        summary_output=summary_path,
        checks_output=checks_path,
        report_output=report_path,
        summary_rows=summary_rows,
        check_rows=check_rows,
        demo_status=demo_status,
        decision_status=decision_status,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconcile personal processed artifacts and produce conservative readiness status.")
    parser.add_argument("--scores-input", default=DEFAULT_SCORES_INPUT)
    parser.add_argument("--score-audit-input", default=DEFAULT_SCORE_AUDIT_INPUT)
    parser.add_argument("--kpi-tier-input", default=DEFAULT_KPI_TIER_INPUT)
    parser.add_argument("--missing-kpi-summary-input", default=DEFAULT_MISSING_KPI_SUMMARY_INPUT)
    parser.add_argument("--missing-kpi-holdings-input", default=DEFAULT_MISSING_KPI_HOLDINGS_INPUT)
    parser.add_argument("--evidence-delta-summary-input", default=DEFAULT_EVIDENCE_DELTA_SUMMARY_INPUT)
    parser.add_argument("--evidence-delta-holdings-input", default=DEFAULT_EVIDENCE_DELTA_HOLDINGS_INPUT)
    parser.add_argument("--artifact-freshness-summary-input", default=DEFAULT_ARTIFACT_FRESHNESS_SUMMARY_INPUT)
    parser.add_argument("--monthly-input", default=DEFAULT_MONTHLY_INPUT)
    parser.add_argument("--monthly-action-summary-input", default=DEFAULT_MONTHLY_ACTION_SUMMARY_INPUT)
    parser.add_argument("--watchlist-input", default=DEFAULT_WATCHLIST_INPUT)
    parser.add_argument("--watchlist-gate-summary-input", default=DEFAULT_WATCHLIST_GATE_SUMMARY_INPUT)
    parser.add_argument("--used-inputs-input", default=DEFAULT_USED_INPUTS_INPUT)
    parser.add_argument("--manifest-input", default=DEFAULT_MANIFEST_INPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--checks-output", default=DEFAULT_CHECKS_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_artifact_reconciliation(
        scores_input=args.scores_input,
        score_audit_input=args.score_audit_input,
        kpi_tier_input=args.kpi_tier_input,
        missing_kpi_summary_input=args.missing_kpi_summary_input,
        missing_kpi_holdings_input=args.missing_kpi_holdings_input,
        evidence_delta_summary_input=args.evidence_delta_summary_input,
        evidence_delta_holdings_input=args.evidence_delta_holdings_input,
        artifact_freshness_summary_input=args.artifact_freshness_summary_input,
        monthly_input=args.monthly_input,
        monthly_action_summary_input=args.monthly_action_summary_input,
        watchlist_input=args.watchlist_input,
        watchlist_gate_summary_input=args.watchlist_gate_summary_input,
        used_inputs_input=args.used_inputs_input,
        manifest_input=args.manifest_input,
        summary_output=args.summary_output,
        checks_output=args.checks_output,
        report_output=args.report_output,
    )
    print(f"summary_output={result.summary_output}")
    print(f"checks_output={result.checks_output}")
    print(f"report_output={result.report_output}")
    print(f"demo_readiness_status={result.demo_status}")
    print(f"decision_readiness_status={result.decision_status}")
    print(f"warnings_total={len(result.warnings)}")


if __name__ == "__main__":
    main()
