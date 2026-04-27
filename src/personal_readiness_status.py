from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_RECONCILIATION_SUMMARY_INPUT = "data/processed/personal_artifact_reconciliation_summary.csv"
DEFAULT_RECONCILIATION_CHECKS_INPUT = "data/processed/personal_artifact_reconciliation_checks.csv"
DEFAULT_ARTIFACT_FRESHNESS_SUMMARY_INPUT = "data/processed/personal_artifact_freshness_summary.csv"
DEFAULT_WATCHLIST_GATE_SUMMARY_INPUT = "data/processed/personal_watchlist_input_gate_summary.csv"
DEFAULT_MONTHLY_ACTION_SUMMARY_INPUT = "data/processed/personal_monthly_action_compatibility_summary.csv"
DEFAULT_SCORE_AUDIT_PROVENANCE_SUMMARY_INPUT = "data/processed/personal_score_audit_provenance_summary.csv"
DEFAULT_KPI_PROVENANCE_SUMMARY_INPUT = "data/processed/personal_kpi_provenance_summary.csv"
DEFAULT_VALUATION_CONTRACT_SUMMARY_INPUT = "data/processed/personal_valuation_input_contract_summary.csv"
DEFAULT_CORE_KPI_CLOSURE_SUMMARY_INPUT = "data/processed/personal_core_kpi_closure_summary.csv"
DEFAULT_DIVIDEND_FCF_CONTRACT_SUMMARY_INPUT = "data/processed/personal_dividend_fcf_input_contract_summary.csv"
DEFAULT_USED_INPUTS_INPUT = "data/processed/personal_run_used_inputs.csv"
DEFAULT_MANIFEST_INPUT = "data/processed/personal_run_manifest.json"
DEFAULT_DEPLOYMENT_NOTES_INPUT = "website/compound-income-os-landing/DEPLOYMENT_NOTES.md"
DEFAULT_ENV_EXAMPLE_INPUT = "website/compound-income-os-landing/.env.example"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_readiness_status_summary.csv"
DEFAULT_BLOCKERS_OUTPUT = "data/processed/personal_readiness_blockers.csv"
DEFAULT_NEXT_ACTIONS_OUTPUT = "data/processed/personal_readiness_next_actions.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_readiness_status_report.md"

SUMMARY_FIELDS = [
    "readiness_scope",
    "readiness_status",
    "active_p0_blockers",
    "active_p1_reviews",
    "active_p2_backlog",
    "resolved_blockers",
    "deferred_blockers",
    "primary_reason_codes",
    "evidence",
    "recommended_next_action",
]
BLOCKER_FIELDS = [
    "blocker_code",
    "blocker_status",
    "blocker_severity",
    "readiness_scope",
    "reason_codes",
    "source_artifact",
    "observed_value",
    "recommended_next_action",
    "requires_private_input",
    "requires_value_change",
    "requires_external_api",
]
NEXT_ACTION_FIELDS = [
    "priority",
    "blocker_code",
    "readiness_scope",
    "recommended_next_action",
    "input_artifact",
    "output_artifact",
    "requires_private_input",
    "requires_value_change",
    "requires_external_api",
    "safe_next_patch",
    "reason",
]
VALID_SCOPES = ("DEMO", "DECISION", "DASHBOARD", "HANDOFF")
ADVICE_TERMS = ("BUY", "SELL", "STRONG_BUY", "STRONG_SELL", "RECOMMEND", "TRADE_SIGNAL", "ORDER", "EXECUTE")


@dataclass(frozen=True)
class ReadinessStatusResult:
    summary_output: Path
    blockers_output: Path
    next_actions_output: Path
    report_output: Path
    summary_rows: list[dict[str, str]]
    blocker_rows: list[dict[str, str]]
    next_action_rows: list[dict[str, str]]
    warnings: tuple[str, ...]


def safe_display_path(path_value: str) -> str:
    normalized = str(path_value).replace("\\", "/")
    if "data/raw/private" in normalized:
        return "<private_path>"
    return path_value


def optional_csv_rows(path_value: str, label: str) -> tuple[list[dict[str, str]], bool, list[str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], False, [f"missing_input={label}:{safe_display_path(path_value)}"]
    return read_csv_rows(path), True, []


def optional_json(path_value: str, label: str) -> tuple[dict[str, Any], bool, list[str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return {}, False, [f"missing_input={label}:{safe_display_path(path_value)}"]
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle), True, []


def optional_text(path_value: str) -> tuple[str, bool]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return "", False
    return path.read_text(encoding="utf-8"), True


def summary_map(rows: list[dict[str, str]]) -> dict[str, str]:
    return {str(row.get("metric", "") or "").strip(): str(row.get("value", "") or "").strip() for row in rows}


def int_value(value: Any) -> int:
    try:
        return int(str(value or "0").strip())
    except ValueError:
        return 0


def bool_value(value: Any) -> bool:
    return safe_upper(value) in {"TRUE", "YES", "1"}


def joined(values: set[str] | list[str] | tuple[str, ...]) -> str:
    return ";".join(sorted(value for value in values if value))


def split_reasons(value: Any) -> set[str]:
    return {item.strip() for item in str(value or "").split(";") if item.strip()}


def add_blocker(
    rows: list[dict[str, str]],
    *,
    code: str,
    status: str,
    severity: str,
    scope: str,
    reason_codes: set[str],
    source_artifact: str,
    observed_value: str,
    recommended_next_action: str,
    requires_private_input: str = "no",
    requires_value_change: str = "no",
    requires_external_api: str = "no",
) -> None:
    rows.append(
        {
            "blocker_code": code,
            "blocker_status": status,
            "blocker_severity": severity,
            "readiness_scope": scope,
            "reason_codes": joined(reason_codes),
            "source_artifact": source_artifact,
            "observed_value": safe_display_path(observed_value),
            "recommended_next_action": recommended_next_action,
            "requires_private_input": requires_private_input,
            "requires_value_change": requires_value_change,
            "requires_external_api": requires_external_api,
        }
    )


def add_next_action(
    rows: list[dict[str, str]],
    *,
    priority: str,
    blocker_code: str,
    scope: str,
    action: str,
    input_artifact: str,
    output_artifact: str,
    requires_private_input: str,
    requires_value_change: str,
    requires_external_api: str,
    safe_next_patch: str,
    reason: str,
) -> None:
    rows.append(
        {
            "priority": priority,
            "blocker_code": blocker_code,
            "readiness_scope": scope,
            "recommended_next_action": action,
            "input_artifact": safe_display_path(input_artifact),
            "output_artifact": output_artifact,
            "requires_private_input": requires_private_input,
            "requires_value_change": requires_value_change,
            "requires_external_api": requires_external_api,
            "safe_next_patch": safe_next_patch,
            "reason": reason,
        }
    )


def source_exists(inventory: dict[str, dict[str, str]], label: str) -> bool:
    return inventory.get(label, {}).get("exists") == "yes"


def build_inventory(
    csv_inputs: dict[str, tuple[str, list[dict[str, str]], bool]],
    *,
    manifest_exists: bool,
    deployment_notes_exists: bool,
    env_example_exists: bool,
) -> dict[str, dict[str, str]]:
    inventory: dict[str, dict[str, str]] = {}
    for label, (path_value, rows, exists) in csv_inputs.items():
        columns = ";".join(rows[0].keys()) if rows else ""
        inventory[label] = {
            "path": path_value,
            "exists": "yes" if exists else "no",
            "row_count": str(len(rows)),
            "columns": columns,
        }
    inventory["manifest"] = {
        "path": DEFAULT_MANIFEST_INPUT,
        "exists": "yes" if manifest_exists else "no",
        "row_count": "",
        "columns": "json",
    }
    inventory["deployment_notes"] = {
        "path": DEFAULT_DEPLOYMENT_NOTES_INPUT,
        "exists": "yes" if deployment_notes_exists else "no",
        "row_count": "",
        "columns": "markdown",
    }
    inventory["env_example"] = {
        "path": DEFAULT_ENV_EXAMPLE_INPUT,
        "exists": "yes" if env_example_exists else "no",
        "row_count": "",
        "columns": "env",
    }
    return inventory


def env_value_is_unset(env_text: str, key: str) -> bool:
    for line in env_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name.strip() == key:
            return value.strip() == ""
    return True


def add_contract_blockers(
    blockers: list[dict[str, str]],
    next_actions: list[dict[str, str]],
    *,
    code: str,
    source_artifact: str,
    affected_count: int,
    approved_count: int,
    reason_codes: set[str],
    action: str,
    input_artifact: str,
    output_artifact: str,
    safe_next_patch: str,
) -> None:
    if affected_count <= 0 or approved_count >= affected_count:
        add_blocker(
            blockers,
            code=code,
            status="RESOLVED",
            severity="INFO",
            scope="DECISION",
            reason_codes={f"{code}_RESOLVED"},
            source_artifact=source_artifact,
            observed_value=f"affected_rows={affected_count}; approved_rows={approved_count}",
            recommended_next_action="No action.",
        )
        return
    add_blocker(
        blockers,
        code=code,
        status="ACTIVE",
        severity="P0_BLOCKER",
        scope="DECISION",
        reason_codes=reason_codes,
        source_artifact=source_artifact,
        observed_value=f"affected_rows={affected_count}; approved_rows={approved_count}",
        recommended_next_action=action,
        requires_private_input="yes",
        requires_value_change="yes_reviewed_input_only",
        requires_external_api="no",
    )
    add_next_action(
        next_actions,
        priority="P0_BLOCKER",
        blocker_code=code,
        scope="DECISION",
        action=action,
        input_artifact=input_artifact,
        output_artifact=output_artifact,
        requires_private_input="yes",
        requires_value_change="yes_reviewed_input_only",
        requires_external_api="no",
        safe_next_patch=safe_next_patch,
        reason=joined(reason_codes),
    )


def build_readiness(
    *,
    reconciliation_summary_rows: list[dict[str, str]],
    reconciliation_checks_rows: list[dict[str, str]],
    freshness_summary_rows: list[dict[str, str]],
    watchlist_gate_summary_rows: list[dict[str, str]],
    monthly_action_summary_rows: list[dict[str, str]],
    score_audit_provenance_summary_rows: list[dict[str, str]],
    kpi_provenance_summary_rows: list[dict[str, str]],
    valuation_contract_summary_rows: list[dict[str, str]],
    core_kpi_closure_summary_rows: list[dict[str, str]],
    dividend_fcf_contract_summary_rows: list[dict[str, str]],
    used_inputs_rows: list[dict[str, str]],
    manifest: dict[str, Any],
    inventory: dict[str, dict[str, str]],
    deployment_notes_text: str,
    env_example_text: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    del reconciliation_checks_rows, kpi_provenance_summary_rows, used_inputs_rows, manifest
    rec = summary_map(reconciliation_summary_rows)
    freshness = summary_map(freshness_summary_rows)
    watchlist = summary_map(watchlist_gate_summary_rows)
    monthly = summary_map(monthly_action_summary_rows)
    score_provenance = summary_map(score_audit_provenance_summary_rows)
    valuation = summary_map(valuation_contract_summary_rows)
    core = summary_map(core_kpi_closure_summary_rows)
    dividend_fcf = summary_map(dividend_fcf_contract_summary_rows)

    blockers: list[dict[str, str]] = []
    next_actions: list[dict[str, str]] = []

    critical_labels = [
        "reconciliation_summary",
        "reconciliation_checks",
        "watchlist_gate_summary",
        "monthly_action_summary",
        "score_audit_provenance_summary",
        "valuation_contract_summary",
        "core_kpi_closure_summary",
        "dividend_fcf_contract_summary",
    ]
    missing_labels = [label for label in critical_labels if not source_exists(inventory, label)]
    if missing_labels:
        add_blocker(
            blockers,
            code="MISSING_METADATA",
            status="ACTIVE",
            severity="P1_REVIEW",
            scope="HANDOFF",
            reason_codes={"SUMMARY_ARTIFACT_MISSING"},
            source_artifact=";".join(missing_labels),
            observed_value=f"missing_summary_artifacts={';'.join(missing_labels)}",
            recommended_next_action="Regenerate missing summary artifacts before relying on consolidated readiness.",
        )

    add_contract_blockers(
        blockers,
        next_actions,
        code="MISSING_VALUATION_REQUIRED",
        source_artifact=DEFAULT_VALUATION_CONTRACT_SUMMARY_INPUT,
        affected_count=int_value(valuation.get("affected_standard_rows_count", rec.get("standard_missing_valuation_required_rows_total"))),
        approved_count=int_value(valuation.get("approved_rows_count")),
        reason_codes=split_reasons(valuation.get("reason_codes")) or {"VALUATION_REQUIRED_MISSING"},
        action="Fill reviewed private valuation input or keep readiness blocked.",
        input_artifact="data/raw/private/fundamentals/personal_valuation_review_input.csv",
        output_artifact=DEFAULT_VALUATION_CONTRACT_SUMMARY_INPUT,
        safe_next_patch="VALUATION REVIEW INPUT APPLY / APPROVED ONLY / NO IMPUTATION",
    )
    add_contract_blockers(
        blockers,
        next_actions,
        code="MISSING_DIVIDEND_FCF_REQUIRED",
        source_artifact=DEFAULT_DIVIDEND_FCF_CONTRACT_SUMMARY_INPUT,
        affected_count=int_value(dividend_fcf.get("affected_standard_rows_count", rec.get("standard_missing_dividend_fcf_required_rows_total"))),
        approved_count=int_value(dividend_fcf.get("approved_rows_count")),
        reason_codes=split_reasons(dividend_fcf.get("reason_codes")) or {"DIVIDEND_FCF_REQUIRED_MISSING"},
        action="Fill reviewed private dividend/fcf input or use the reviewed SEC evidence path.",
        input_artifact="data/raw/private/fundamentals/personal_dividend_fcf_review_input.csv",
        output_artifact=DEFAULT_DIVIDEND_FCF_CONTRACT_SUMMARY_INPUT,
        safe_next_patch="DIVIDEND FCF REVIEW INPUT APPLY / APPROVED ONLY / NO IMPUTATION",
    )

    core_affected = int_value(core.get("affected_standard_rows_count", rec.get("standard_review_core_data_rows_total")))
    if core_affected > 0:
        core_reasons = split_reasons(core.get("reason_codes")) or {"REVIEW_CORE_DATA", "CORE_KPI_MISSING"}
        add_blocker(
            blockers,
            code="REVIEW_CORE_DATA",
            status="ACTIVE",
            severity="P0_BLOCKER",
            scope="DECISION",
            reason_codes=core_reasons,
            source_artifact=DEFAULT_CORE_KPI_CLOSURE_SUMMARY_INPUT,
            observed_value=f"affected_rows={core_affected}; sec_evidence_possible={core.get('sec_evidence_possible_count', '')}",
            recommended_next_action="Review core KPI closure queue through SEC or manual evidence; do not impute values.",
            requires_private_input="maybe",
            requires_value_change="yes_reviewed_input_only",
            requires_external_api="no",
        )
        add_next_action(
            next_actions,
            priority="P0_BLOCKER",
            blocker_code="REVIEW_CORE_DATA",
            scope="DECISION",
            action="Review core KPI closure queue through SEC or manual evidence; do not impute values.",
            input_artifact=DEFAULT_CORE_KPI_CLOSURE_SUMMARY_INPUT,
            output_artifact=DEFAULT_CORE_KPI_CLOSURE_SUMMARY_INPUT,
            requires_private_input="maybe",
            requires_value_change="yes_reviewed_input_only",
            requires_external_api="no",
            safe_next_patch="CORE KPI REVIEW INPUT APPLY / APPROVED ONLY / NO IMPUTATION",
            reason=joined(core_reasons),
        )

    provenance_incomplete = bool_value(score_provenance.get("provenance_incomplete_flag")) or int_value(
        score_provenance.get("holdings_with_incomplete_provenance_total")
    ) > 0
    if provenance_incomplete:
        add_blocker(
            blockers,
            code="PROVENANCE_INCOMPLETE",
            status="ACTIVE",
            severity="P0_BLOCKER",
            scope="DECISION",
            reason_codes={"PROVENANCE_INCOMPLETE"},
            source_artifact=DEFAULT_SCORE_AUDIT_PROVENANCE_SUMMARY_INPUT,
            observed_value=f"holdings_with_incomplete_provenance={score_provenance.get('holdings_with_incomplete_provenance_total', '')}",
            recommended_next_action="Increase source metadata coverage through the reviewed evidence registry and apply path.",
            requires_private_input="maybe",
            requires_value_change="no",
            requires_external_api="no",
        )
        add_next_action(
            next_actions,
            priority="P0_BLOCKER",
            blocker_code="PROVENANCE_INCOMPLETE",
            scope="DECISION",
            action="Increase source metadata coverage through the reviewed evidence registry and apply path.",
            input_artifact=DEFAULT_SCORE_AUDIT_PROVENANCE_SUMMARY_INPUT,
            output_artifact=DEFAULT_SCORE_AUDIT_PROVENANCE_SUMMARY_INPUT,
            requires_private_input="maybe",
            requires_value_change="no",
            requires_external_api="no",
            safe_next_patch="EVIDENCE REGISTRY SOURCE METADATA CLOSURE / NO VALUE CHANGES",
            reason="PROVENANCE_INCOMPLETE",
        )

    watchlist_reasons = split_reasons(watchlist.get("watchlist_reason_codes"))
    if watchlist.get("watchlist_input_status") == "SAMPLE_DEMO_ONLY" or "WATCHLIST_SAMPLE_INPUT" in watchlist_reasons:
        add_blocker(
            blockers,
            code="WATCHLIST_SAMPLE_INPUT",
            status="ACTIVE",
            severity="P0_BLOCKER",
            scope="DEMO",
            reason_codes={"WATCHLIST_SAMPLE_INPUT"},
            source_artifact=DEFAULT_WATCHLIST_GATE_SUMMARY_INPUT,
            observed_value=f"watchlist_input_status={watchlist.get('watchlist_input_status', '')}; path={watchlist.get('watchlist_input_path', '')}",
            recommended_next_action="Replace sample watchlist with reviewed personal watchlist input or keep demo-only gate.",
            requires_private_input="yes",
            requires_value_change="yes_reviewed_input_only",
            requires_external_api="no",
        )
        add_blocker(
            blockers,
            code="WATCHLIST_SAMPLE_INPUT",
            status="ACTIVE",
            severity="P0_BLOCKER",
            scope="DECISION",
            reason_codes={"WATCHLIST_SAMPLE_INPUT"},
            source_artifact=DEFAULT_WATCHLIST_GATE_SUMMARY_INPUT,
            observed_value=f"watchlist_readiness_status={watchlist.get('watchlist_readiness_status', '')}",
            recommended_next_action="Replace sample watchlist with reviewed personal watchlist input or keep decision readiness blocked.",
            requires_private_input="yes",
            requires_value_change="yes_reviewed_input_only",
            requires_external_api="no",
        )
        add_next_action(
            next_actions,
            priority="P0_BLOCKER",
            blocker_code="WATCHLIST_SAMPLE_INPUT",
            scope="DEMO;DECISION",
            action="Replace sample watchlist with reviewed personal watchlist input or keep demo-only gate.",
            input_artifact="data/raw/private/<personal_watchlist>.csv",
            output_artifact=DEFAULT_WATCHLIST_GATE_SUMMARY_INPUT,
            requires_private_input="yes",
            requires_value_change="yes_reviewed_input_only",
            requires_external_api="no",
            safe_next_patch="PRIVATE WATCHLIST INPUT REVIEW / DEMO GATE PRESERVED",
            reason="WATCHLIST_SAMPLE_INPUT",
        )
    if "WATCHLIST_REVIEW_OR_MISSING_DATA" in watchlist_reasons or watchlist.get("watchlist_data_status") in {"REVIEW", "MISSING_DATA", "PARTIAL"}:
        add_blocker(
            blockers,
            code="WATCHLIST_REVIEW_OR_MISSING_DATA",
            status="ACTIVE",
            severity="P1_REVIEW",
            scope="DECISION",
            reason_codes={"WATCHLIST_REVIEW_OR_MISSING_DATA"},
            source_artifact=DEFAULT_WATCHLIST_GATE_SUMMARY_INPUT,
            observed_value=f"watchlist_data_status={watchlist.get('watchlist_data_status', '')}",
            recommended_next_action="Review watchlist data quality before using it for decision workflow outputs.",
            requires_private_input="yes",
            requires_value_change="yes_reviewed_input_only",
            requires_external_api="no",
        )
        add_blocker(
            blockers,
            code="WATCHLIST_REVIEW_OR_MISSING_DATA",
            status="ACTIVE",
            severity="P1_REVIEW",
            scope="DASHBOARD",
            reason_codes={"WATCHLIST_REVIEW_OR_MISSING_DATA"},
            source_artifact=DEFAULT_WATCHLIST_GATE_SUMMARY_INPUT,
            observed_value=f"watchlist_data_status={watchlist.get('watchlist_data_status', '')}",
            recommended_next_action="Render dashboard watchlist state as diagnostic review, not decision-ready status.",
            requires_private_input="yes",
            requires_value_change="yes_reviewed_input_only",
            requires_external_api="no",
        )

    monthly_resolved = bool_value(monthly.get("monthly_schema_drift_resolved")) or bool_value(rec.get("monthly_schema_drift_resolved"))
    add_blocker(
        blockers,
        code="MONTHLY_SCHEMA_DRIFT",
        status="RESOLVED" if monthly_resolved else "ACTIVE",
        severity="INFO" if monthly_resolved else "P0_BLOCKER",
        scope="DASHBOARD",
        reason_codes={"MONTHLY_SCHEMA_DRIFT_RESOLVED"} if monthly_resolved else {"MONTHLY_SCHEMA_DRIFT"},
        source_artifact=DEFAULT_MONTHLY_ACTION_SUMMARY_INPUT,
        observed_value=f"monthly_schema_drift_resolved={monthly.get('monthly_schema_drift_resolved', rec.get('monthly_schema_drift_resolved', ''))}",
        recommended_next_action="No action." if monthly_resolved else "Regenerate neutral monthly action compatibility output.",
    )

    artifact_drift_active = bool_value(freshness.get("artifact_drift_active", rec.get("artifact_drift_active")))
    add_blocker(
        blockers,
        code="ARTIFACT_DRIFT",
        status="ACTIVE" if artifact_drift_active else "RESOLVED",
        severity="P0_BLOCKER" if artifact_drift_active else "INFO",
        scope="HANDOFF",
        reason_codes={"ARTIFACT_DRIFT"} if artifact_drift_active else {"ARTIFACT_DRIFT_RESOLVED"},
        source_artifact=DEFAULT_ARTIFACT_FRESHNESS_SUMMARY_INPUT,
        observed_value=f"artifact_drift_active={freshness.get('artifact_drift_active', rec.get('artifact_drift_active', ''))}",
        recommended_next_action="Resolve unexplained current artifact drift." if artifact_drift_active else "No action.",
    )
    freshness_reasons = split_reasons(freshness.get("freshness_reason_codes", rec.get("artifact_freshness_reason_codes")))
    if "MISSING_METADATA" in freshness_reasons:
        add_blocker(
            blockers,
            code="MISSING_METADATA",
            status="ACTIVE",
            severity="P1_REVIEW",
            scope="HANDOFF",
            reason_codes={"MISSING_METADATA"},
            source_artifact=DEFAULT_ARTIFACT_FRESHNESS_SUMMARY_INPUT,
            observed_value=f"freshness_reason_codes={joined(freshness_reasons)}",
            recommended_next_action="Add comparable run metadata or regenerate stale derived artifacts before external review.",
            requires_private_input="no",
            requires_value_change="no",
            requires_external_api="no",
        )
    if "STALE_DERIVED_ARTIFACT" in freshness_reasons:
        add_blocker(
            blockers,
            code="STALE_ARTIFACT",
            status="ACTIVE",
            severity="P1_REVIEW",
            scope="HANDOFF",
            reason_codes={"STALE_DERIVED_ARTIFACT"},
            source_artifact=DEFAULT_ARTIFACT_FRESHNESS_SUMMARY_INPUT,
            observed_value=f"freshness_reason_codes={joined(freshness_reasons)}",
            recommended_next_action="Regenerate stale derived artifacts only through committed deterministic modules.",
            requires_private_input="no",
            requires_value_change="no",
            requires_external_api="no",
        )

    deployment_notes_present = "not ready for public deployment" in deployment_notes_text.lower() or bool(deployment_notes_text)
    if deployment_notes_present:
        add_blocker(
            blockers,
            code="PUBLIC_LAUNCH_BLOCKERS",
            status="DEFERRED",
            severity="P1_REVIEW",
            scope="HANDOFF",
            reason_codes={"PRIVATE_PREVIEW_ONLY"},
            source_artifact=DEFAULT_DEPLOYMENT_NOTES_INPUT,
            observed_value="public_launch_blockers_documented=True",
            recommended_next_action="Keep public launch deferred until legal pages, real targets, and scope are verified.",
        )
    if env_example_text and any(env_value_is_unset(env_example_text, key) for key in ("VITE_SAMPLE_REPORT_URL", "VITE_EARLY_ACCESS_URL", "VITE_SETUP_SERVICE_URL", "VITE_GITHUB_URL")):
        add_blocker(
            blockers,
            code="NO_REAL_CTA_TARGETS",
            status="DEFERRED",
            severity="P1_REVIEW",
            scope="HANDOFF",
            reason_codes={"PRIVATE_PREVIEW_CTA_PENDING"},
            source_artifact=DEFAULT_ENV_EXAMPLE_INPUT,
            observed_value="cta_targets_unset_in_template=True",
            recommended_next_action="Configure real CTA targets before public launch.",
        )
    if env_example_text and any(env_value_is_unset(env_example_text, key) for key in ("VITE_PRIVACY_URL", "VITE_IMPRINT_URL")):
        add_blocker(
            blockers,
            code="NO_IMPRINT_PRIVACY",
            status="DEFERRED",
            severity="P1_REVIEW",
            scope="HANDOFF",
            reason_codes={"PUBLIC_LEGAL_LINKS_PENDING"},
            source_artifact=DEFAULT_ENV_EXAMPLE_INPUT,
            observed_value="imprint_or_privacy_url_unset_in_template=True",
            recommended_next_action="Configure verified imprint and privacy URLs before public launch.",
        )
    add_blocker(
        blockers,
        code="SAMPLE_OR_SYNTHETIC_DEMO_DATA",
        status="ACTIVE",
        severity="INFO",
        scope="DEMO",
        reason_codes={"SYNTHETIC_OR_SAMPLE_DATA_VISIBLE"},
        source_artifact="website/compound-income-os-landing/DEPLOYMENT_NOTES.md;data/processed/personal_watchlist_input_gate_summary.csv",
        observed_value="sample_or_synthetic_demo_data_present=True",
        recommended_next_action="Keep sample and synthetic data labels visible in demos.",
    )

    summary_rows = build_scope_summary(blockers, missing_labels)
    return summary_rows, blockers, next_actions


def build_scope_summary(blockers: list[dict[str, str]], missing_labels: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for scope in VALID_SCOPES:
        scope_rows = [row for row in blockers if row["readiness_scope"] == scope]
        active_rows = [row for row in scope_rows if row["blocker_status"] == "ACTIVE"]
        active_p0 = [row["blocker_code"] for row in active_rows if row["blocker_severity"] == "P0_BLOCKER"]
        active_p1 = [row["blocker_code"] for row in active_rows if row["blocker_severity"] == "P1_REVIEW"]
        active_p2 = [row["blocker_code"] for row in active_rows if row["blocker_severity"] == "P2_BACKLOG"]
        resolved = [row["blocker_code"] for row in scope_rows if row["blocker_status"] == "RESOLVED"]
        deferred = [row["blocker_code"] for row in scope_rows if row["blocker_status"] == "DEFERRED"]
        if missing_labels and scope in {"DEMO", "DECISION", "DASHBOARD"}:
            status = "NOT_AVAILABLE"
        elif active_p0:
            status = "BLOCKED"
        elif active_p1 or active_p2:
            status = "REVIEW"
        else:
            status = "PASS"
        reasons = set()
        for row in active_rows:
            reasons.update(split_reasons(row.get("reason_codes", "")))
        rows.append(
            {
                "readiness_scope": scope,
                "readiness_status": status,
                "active_p0_blockers": joined(set(active_p0)),
                "active_p1_reviews": joined(set(active_p1)),
                "active_p2_backlog": joined(set(active_p2)),
                "resolved_blockers": joined(set(resolved)),
                "deferred_blockers": joined(set(deferred)),
                "primary_reason_codes": joined(reasons),
                "evidence": "personal_readiness_blockers.csv",
                "recommended_next_action": scope_next_action(scope, status, active_p0, active_p1),
            }
        )
    return rows


def scope_next_action(scope: str, status: str, active_p0: list[str], active_p1: list[str]) -> str:
    if status == "NOT_AVAILABLE":
        return "Regenerate missing summary artifacts before relying on this readiness scope."
    if status == "BLOCKED":
        return f"Resolve or explicitly keep blocked: {joined(set(active_p0))}."
    if status == "REVIEW":
        return f"Review open items: {joined(set(active_p1))}."
    if scope == "HANDOFF":
        return "Proceed with handoff only after fresh ZIP validation."
    return "No action."


def validate_next_actions(next_action_rows: list[dict[str, str]]) -> None:
    text = "\n".join(
        " ".join(str(row.get(field, "")) for field in ("recommended_next_action", "safe_next_patch", "reason"))
        for row in next_action_rows
    ).upper()
    forbidden = [term for term in ADVICE_TERMS if term in text]
    if forbidden:
        raise ValueError(f"readiness next actions contain forbidden advice/order terms: {', '.join(sorted(forbidden))}")


def render_report(
    *,
    summary_rows: list[dict[str, str]],
    blocker_rows: list[dict[str, str]],
    next_action_rows: list[dict[str, str]],
    inventory: dict[str, dict[str, str]],
) -> str:
    active = [row for row in blocker_rows if row["blocker_status"] == "ACTIVE"]
    non_active = [row for row in blocker_rows if row["blocker_status"] != "ACTIVE"]
    lines = [
        "# Personal Readiness Status Report",
        "",
        "## 1. Executive Summary",
        "",
        "This companion layer consolidates existing readiness, trust-chain, schema, freshness, watchlist, and input-contract summaries. It does not change scores, fundamentals, master files, watchlist rows, or evidence-apply outputs.",
        "",
        "## 2. Input Summary Artifacts",
        "",
        "| Artifact | Exists | Rows | Columns |",
        "| --- | --- | ---: | --- |",
    ]
    for label, row in sorted(inventory.items()):
        lines.append(f"| `{row['path']}` | `{row['exists']}` | `{row['row_count']}` | `{row['columns']}` |")
    lines.extend(["", "## 3. Demo Readiness", ""])
    append_scope(lines, summary_rows, "DEMO")
    lines.extend(["", "## 4. Decision Readiness", ""])
    append_scope(lines, summary_rows, "DECISION")
    lines.extend(["", "## 5. Dashboard Readiness", ""])
    append_scope(lines, summary_rows, "DASHBOARD")
    lines.extend(["", "## 6. Handoff Readiness", ""])
    append_scope(lines, summary_rows, "HANDOFF")
    lines.extend(["", "## 7. Active Blockers", "", "| Code | Scope | Severity | Reasons | Next Action |", "| --- | --- | --- | --- | --- |"])
    if active:
        for row in active:
            lines.append(
                f"| `{row['blocker_code']}` | `{row['readiness_scope']}` | `{row['blocker_severity']}` | `{row['reason_codes']}` | {row['recommended_next_action']} |"
            )
    else:
        lines.append("| none |  |  |  |  |")
    lines.extend(["", "## 8. Resolved / Deferred Blockers", "", "| Code | Status | Scope | Reasons |", "| --- | --- | --- | --- |"])
    if non_active:
        for row in non_active:
            lines.append(f"| `{row['blocker_code']}` | `{row['blocker_status']}` | `{row['readiness_scope']}` | `{row['reason_codes']}` |")
    else:
        lines.append("| none |  |  |  |")
    lines.extend(["", "## 9. Blocker Priority Matrix", "", "| Priority | Code | Scope | Status |", "| --- | --- | --- | --- |"])
    for row in sorted(blocker_rows, key=lambda item: (item["blocker_severity"], item["blocker_code"], item["readiness_scope"])):
        lines.append(f"| `{row['blocker_severity']}` | `{row['blocker_code']}` | `{row['readiness_scope']}` | `{row['blocker_status']}` |")
    lines.extend(["", "## 10. Next Actions", "", "| Priority | Blocker | Action | Safe Patch |", "| --- | --- | --- | --- |"])
    if next_action_rows:
        for row in next_action_rows:
            lines.append(f"| `{row['priority']}` | `{row['blocker_code']}` | {row['recommended_next_action']} | `{row['safe_next_patch']}` |")
    else:
        lines.append("| none |  |  |  |")
    lines.extend(
        [
            "",
            "## 11. No-Value-Change Guardrail",
            "",
            "- No missing values were filled.",
            "- No scores, score weights, master files, watchlist rows, evidence-apply outputs, or website files were changed by this layer.",
            "- Next actions are review/workflow oriented and are not trading instructions.",
            "",
            "## 12. Recommended Next Patch",
            "",
            "`PATCH / PRIVATE INPUT REVIEW WORKFLOW / VALUATION + DIVIDEND FCF / APPROVED ONLY / NO IMPUTATION`",
            "",
        ]
    )
    return "\n".join(lines)


def append_scope(lines: list[str], summary_rows: list[dict[str, str]], scope: str) -> None:
    row = next((item for item in summary_rows if item["readiness_scope"] == scope), None)
    if not row:
        lines.append("Status: `NOT_AVAILABLE`")
        return
    lines.append(f"Status: `{row['readiness_status']}`")
    lines.append("")
    lines.append(f"- Active P0: `{row['active_p0_blockers']}`")
    lines.append(f"- Active P1: `{row['active_p1_reviews']}`")
    lines.append(f"- Resolved: `{row['resolved_blockers']}`")
    lines.append(f"- Deferred: `{row['deferred_blockers']}`")
    lines.append(f"- Next action: {row['recommended_next_action']}")


def run_personal_readiness_status(
    *,
    reconciliation_summary_input: str = DEFAULT_RECONCILIATION_SUMMARY_INPUT,
    reconciliation_checks_input: str = DEFAULT_RECONCILIATION_CHECKS_INPUT,
    artifact_freshness_summary_input: str = DEFAULT_ARTIFACT_FRESHNESS_SUMMARY_INPUT,
    watchlist_gate_summary_input: str = DEFAULT_WATCHLIST_GATE_SUMMARY_INPUT,
    monthly_action_summary_input: str = DEFAULT_MONTHLY_ACTION_SUMMARY_INPUT,
    score_audit_provenance_summary_input: str = DEFAULT_SCORE_AUDIT_PROVENANCE_SUMMARY_INPUT,
    kpi_provenance_summary_input: str = DEFAULT_KPI_PROVENANCE_SUMMARY_INPUT,
    valuation_contract_summary_input: str = DEFAULT_VALUATION_CONTRACT_SUMMARY_INPUT,
    core_kpi_closure_summary_input: str = DEFAULT_CORE_KPI_CLOSURE_SUMMARY_INPUT,
    dividend_fcf_contract_summary_input: str = DEFAULT_DIVIDEND_FCF_CONTRACT_SUMMARY_INPUT,
    used_inputs_input: str = DEFAULT_USED_INPUTS_INPUT,
    manifest_input: str = DEFAULT_MANIFEST_INPUT,
    deployment_notes_input: str = DEFAULT_DEPLOYMENT_NOTES_INPUT,
    env_example_input: str = DEFAULT_ENV_EXAMPLE_INPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    blockers_output: str = DEFAULT_BLOCKERS_OUTPUT,
    next_actions_output: str = DEFAULT_NEXT_ACTIONS_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> ReadinessStatusResult:
    warnings: list[str] = []
    input_specs = {
        "reconciliation_summary": reconciliation_summary_input,
        "reconciliation_checks": reconciliation_checks_input,
        "artifact_freshness_summary": artifact_freshness_summary_input,
        "watchlist_gate_summary": watchlist_gate_summary_input,
        "monthly_action_summary": monthly_action_summary_input,
        "score_audit_provenance_summary": score_audit_provenance_summary_input,
        "kpi_provenance_summary": kpi_provenance_summary_input,
        "valuation_contract_summary": valuation_contract_summary_input,
        "core_kpi_closure_summary": core_kpi_closure_summary_input,
        "dividend_fcf_contract_summary": dividend_fcf_contract_summary_input,
        "used_inputs": used_inputs_input,
    }
    loaded: dict[str, list[dict[str, str]]] = {}
    csv_inputs: dict[str, tuple[str, list[dict[str, str]], bool]] = {}
    for label, path_value in input_specs.items():
        rows, exists, row_warnings = optional_csv_rows(path_value, label)
        loaded[label] = rows
        csv_inputs[label] = (path_value, rows, exists)
        warnings.extend(row_warnings)
    manifest, manifest_exists, manifest_warnings = optional_json(manifest_input, "manifest")
    warnings.extend(manifest_warnings)
    deployment_notes_text, deployment_notes_exists = optional_text(deployment_notes_input)
    env_example_text, env_example_exists = optional_text(env_example_input)
    inventory = build_inventory(
        csv_inputs,
        manifest_exists=manifest_exists,
        deployment_notes_exists=deployment_notes_exists,
        env_example_exists=env_example_exists,
    )

    summary_rows, blocker_rows, next_action_rows = build_readiness(
        reconciliation_summary_rows=loaded["reconciliation_summary"],
        reconciliation_checks_rows=loaded["reconciliation_checks"],
        freshness_summary_rows=loaded["artifact_freshness_summary"],
        watchlist_gate_summary_rows=loaded["watchlist_gate_summary"],
        monthly_action_summary_rows=loaded["monthly_action_summary"],
        score_audit_provenance_summary_rows=loaded["score_audit_provenance_summary"],
        kpi_provenance_summary_rows=loaded["kpi_provenance_summary"],
        valuation_contract_summary_rows=loaded["valuation_contract_summary"],
        core_kpi_closure_summary_rows=loaded["core_kpi_closure_summary"],
        dividend_fcf_contract_summary_rows=loaded["dividend_fcf_contract_summary"],
        used_inputs_rows=loaded["used_inputs"],
        manifest=manifest,
        inventory=inventory,
        deployment_notes_text=deployment_notes_text,
        env_example_text=env_example_text,
    )
    validate_next_actions(next_action_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    blockers_path = write_csv_rows(blockers_output, BLOCKER_FIELDS, blocker_rows)
    next_actions_path = write_csv_rows(next_actions_output, NEXT_ACTION_FIELDS, next_action_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_report(summary_rows=summary_rows, blocker_rows=blocker_rows, next_action_rows=next_action_rows, inventory=inventory),
        encoding="utf-8",
    )
    return ReadinessStatusResult(
        summary_output=summary_path,
        blockers_output=blockers_path,
        next_actions_output=next_actions_path,
        report_output=report_path,
        summary_rows=summary_rows,
        blocker_rows=blocker_rows,
        next_action_rows=next_action_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consolidate personal demo, decision, dashboard, and handoff readiness status.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--blockers-output", default=DEFAULT_BLOCKERS_OUTPUT)
    parser.add_argument("--next-actions-output", default=DEFAULT_NEXT_ACTIONS_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_readiness_status(
        summary_output=args.summary_output,
        blockers_output=args.blockers_output,
        next_actions_output=args.next_actions_output,
        report_output=args.report_output,
    )
    statuses = {row["readiness_scope"]: row["readiness_status"] for row in result.summary_rows}
    print(f"summary_output={result.summary_output}")
    print(f"blockers_output={result.blockers_output}")
    print(f"next_actions_output={result.next_actions_output}")
    print(f"report_output={result.report_output}")
    print(f"demo_readiness_status={statuses.get('DEMO', 'NOT_AVAILABLE')}")
    print(f"decision_readiness_status={statuses.get('DECISION', 'NOT_AVAILABLE')}")
    print(f"dashboard_readiness_status={statuses.get('DASHBOARD', 'NOT_AVAILABLE')}")
    print(f"handoff_readiness_status={statuses.get('HANDOFF', 'NOT_AVAILABLE')}")
    print(f"warnings_total={len(result.warnings)}")


if __name__ == "__main__":
    main()
