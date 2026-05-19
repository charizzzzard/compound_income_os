from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, read_csv_rows, resolve_repo_path

CONTRACT_VERSION = "v1-design"

DEFAULT_INPUT_CLOSURE = "data/processed/personal_input_closure_report.csv"
DEFAULT_DECISION_CAPTURE = "data/processed/personal_decision_state_capture.csv"
DEFAULT_CASH_REFILL = "data/processed/personal_cash_refill_review.csv"
DEFAULT_REBALANCE = "data/processed/personal_rebalance_review.csv"
DEFAULT_RUN_MANIFEST = "data/processed/personal_run_manifest.json"
DEFAULT_RUN_USED_INPUTS = "data/processed/personal_run_used_inputs.csv"
DEFAULT_MONTHLY_RANKING = "data/processed/personal_monthly_buy_ranking.csv"
DEFAULT_SCORE_AUDIT = "data/processed/personal_score_audit.csv"
DEFAULT_OUT_CSV = "data/processed/decision_quality_state.csv"
DEFAULT_OUT_JSON = "data/processed/decision_quality_state.json"
DEFAULT_REPORT_PATTERN = "reports/{as_of_date}/decision_quality_report.md"

WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
UNC_PATH_RE = re.compile(r"^(?:\\\\|//)[^\\/]+[\\/][^\\/]+")

FIELDNAMES = [
    "run_id",
    "as_of_date",
    "generated_at",
    "source_commit_sha",
    "contract_version",
    "input_artifacts",
    "evidence_coverage_status",
    "evidence_coverage_pct",
    "data_quality_status",
    "missing_critical_fields",
    "stale_inputs",
    "conflicting_inputs",
    "decision_capture_status",
    "journal_quality_status",
    "portfolio_health_status",
    "cash_refill_status",
    "rebalance_status",
    "ranking_available",
    "ranking_stability_status",
    "sensitivity_status",
    "scenario_status",
    "tail_risk_status",
    "scenario_robustness_score",
    "decision_confidence_level",
    "confidence_reason_codes",
    "review_required",
    "review_reason_codes",
    "non_scope_confirmations",
]

NON_SCOPE_CONFIRMATIONS = [
    "NO_BROKER_LOGIC",
    "NO_ORDER_EXECUTION",
    "NO_AUTO_TRADING",
    "NO_SCORE_FORMULA_CHANGE",
    "NO_PORTFOLIO_RULE_CHANGE",
    "NO_SILENT_DATA_ENRICHMENT",
    "NO_SIMULATION_OR_BACKTESTING",
    "NO_OUTCOME_ATTRIBUTION",
    "NO_RUNTIME_LLM_DECISIONING",
    "NO_TAX_QUANTIFICATION",
    "NO_PORTFOLIO_EVENT_LEDGER",
    "NO_PRIVATE_RAW_DATA",
]


@dataclass(frozen=True)
class InputRead:
    label: str
    path: str
    mandatory: bool
    exists: bool
    readable: bool
    rows: list[dict[str, str]]
    error: str = ""
    external_path: bool = False


@dataclass(frozen=True)
class DecisionQualityResult:
    csv_output: Path
    json_output: Path
    report_output: Path
    state: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git_head() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=resolve_repo_path("."),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _read_json(path_value: str | Path) -> tuple[dict[str, Any], str]:
    path = resolve_repo_path(path_value)
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:  # noqa: BLE001 - error text is surfaced as lineage context only
        return {}, str(exc)
    return data if isinstance(data, dict) else {}, ""


def _repo_root() -> Path:
    return resolve_repo_path(".").resolve()


def _redacted_path(label: str) -> str:
    return f"EXTERNAL_PATH_REDACTED:{label}"


def _is_windows_absolute_path(raw: str) -> bool:
    return bool(WINDOWS_ABSOLUTE_RE.match(raw))


def _is_unc_path(raw: str) -> bool:
    return bool(UNC_PATH_RE.match(raw))


def _repo_relative_native_absolute(raw: str) -> str | None:
    path = Path(raw)
    if not path.is_absolute():
        return None
    try:
        return path.resolve().relative_to(_repo_root()).as_posix()
    except ValueError:
        return None


def _resolve_relative_candidate(raw: str) -> Path:
    return (_repo_root() / raw.replace("\\", "/")).resolve()


def _normalize_path_for_output(path_value: str | Path, label: str) -> tuple[str, bool]:
    raw = str(path_value)
    if _is_windows_absolute_path(raw) or _is_unc_path(raw):
        native_relative = _repo_relative_native_absolute(raw)
        if native_relative is not None:
            return native_relative, False
        return _redacted_path(label), True

    path = Path(raw)
    if path.is_absolute():
        native_relative = _repo_relative_native_absolute(raw)
        if native_relative is not None:
            return native_relative, False
        return _redacted_path(label), True

    try:
        rel = _resolve_relative_candidate(raw).relative_to(_repo_root())
    except ValueError:
        return _redacted_path(label), True
    return rel.as_posix(), False


def _is_private_or_absolute_lineage_value(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    lowered = text.replace("\\", "/").lower()
    if "data/raw/private" in lowered:
        return True
    if _is_windows_absolute_path(text) or _is_unc_path(text):
        return _repo_relative_native_absolute(text) is None
    if Path(text).is_absolute():
        return _repo_relative_native_absolute(text) is None
    try:
        _resolve_relative_candidate(text).relative_to(_repo_root())
    except ValueError:
        return True
    return False


def _read_input(label: str, path_value: str, *, mandatory: bool) -> InputRead:
    output_path, external_path = _normalize_path_for_output(path_value, label)
    if external_path:
        return InputRead(
            label=label,
            path=output_path,
            mandatory=mandatory,
            exists=False,
            readable=False,
            rows=[],
            error="external path redacted",
            external_path=True,
        )
    path = resolve_repo_path(path_value)
    if not path.exists():
        return InputRead(label=label, path=output_path, mandatory=mandatory, exists=False, readable=False, rows=[])
    try:
        rows = read_csv_rows(path)
    except Exception as exc:  # noqa: BLE001 - converted into deterministic state
        return InputRead(label=label, path=output_path, mandatory=mandatory, exists=True, readable=False, rows=[], error=str(exc))
    return InputRead(label=label, path=output_path, mandatory=mandatory, exists=True, readable=True, rows=rows)


def _artifact_status(item: InputRead) -> str:
    if item.readable:
        return "AVAILABLE"
    if item.exists:
        return "UNREADABLE"
    return "MISSING"


def _manifest_stage_executed(manifest: dict[str, Any], needle: str) -> bool:
    stages: list[str] = []
    for key in ("executed_stage_order", "selected_stages"):
        value = manifest.get(key)
        if isinstance(value, list):
            stages.extend(str(item) for item in value)
    lowered_needle = needle.lower()
    return any(lowered_needle in stage.lower() for stage in stages)


def _manifest_text_values(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            values.append(str(key))
            values.extend(_manifest_text_values(nested))
    elif isinstance(value, list):
        for nested in value:
            values.extend(_manifest_text_values(nested))
    else:
        values.append(str(value))
    return values


def _manifest_output_ref_exists(manifest: dict[str, Any], *needles: str) -> bool:
    haystack = "\n".join(_manifest_text_values(manifest)).replace("\\", "/").lower()
    return any(needle.lower() in haystack for needle in needles)


def _derive_run_id(manifest: dict[str, Any], fallback: str) -> str:
    value = str(manifest.get("run_id") or "").strip()
    if value:
        return value
    started = str(manifest.get("run_started_at") or "").strip()
    if started[:10]:
        return f"{started[:10]}-monthly"
    return fallback


def _derive_as_of_date(manifest: dict[str, Any], fallback: str) -> str:
    for key in ("as_of_date", "source_snapshot_date", "portfolio_date"):
        value = str(manifest.get(key) or "").strip()
        if len(value) >= 10:
            return value[:10]
    started = str(manifest.get("run_started_at") or "").strip()
    if len(started) >= 10:
        return started[:10]
    return fallback


def _derive_source_commit(manifest: dict[str, Any]) -> str:
    for key in ("source_commit_sha", "git_head", "repo_head", "commit_sha", "current_head"):
        value = str(manifest.get(key) or "").strip()
        if value:
            return value
    return _git_head()


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _input_closure_signals(item: InputRead) -> tuple[str, str, float | None, list[str], list[str], bool]:
    if not item.readable:
        return "MISSING", "MISSING", None, [item.label], ["EVIDENCE_MISSING"], True

    rows = item.rows
    if not rows:
        return "REVIEW", "REVIEW", None, [item.label], ["INPUT_CLOSURE_BLOCKED"], True

    blocking_statuses = {"BLOCKED", "MISSING", "SAMPLE_ONLY", "REVIEW_REQUIRED"}
    missing_statuses = {"BLOCKED", "MISSING", "SAMPLE_ONLY"}
    statuses = [str(row.get("status", "") or "").strip().upper() for row in rows]
    ready_count = sum(1 for status in statuses if status in {"READY", "NOT_APPLICABLE"})
    ratio = round(ready_count / len(rows), 6) if rows else None
    missing_fields = [
        str(row.get("input_area", "") or "").strip() or "UNKNOWN_INPUT_AREA"
        for row, status in zip(rows, statuses)
        if status in missing_statuses
    ]
    blocked = any(status in blocking_statuses for status in statuses)
    reason_codes: list[str] = []
    if blocked:
        reason_codes.append("INPUT_CLOSURE_BLOCKED")
    if missing_fields:
        reason_codes.append("EVIDENCE_MISSING")

    if ratio == 1.0:
        return "COVERED", "COVERED", 1.0, [], reason_codes, blocked
    return "PARTIAL", "REVIEW", ratio, missing_fields, reason_codes, blocked


def _status_from_single_row(item: InputRead, *, required_label: str) -> tuple[str, list[str], bool]:
    if not item.readable:
        return "MISSING", [required_label], True
    if not item.rows:
        return "REVIEW", [required_label], True
    return "PASS", [], False


def _cash_status(item: InputRead) -> tuple[str, list[str], bool]:
    base_status, missing, hard = _status_from_single_row(item, required_label=item.label)
    if base_status != "PASS":
        return base_status, missing, hard
    row = item.rows[0]
    quality = str(row.get("data_quality_flag", "") or "").strip().upper()
    status = str(row.get("status", "") or "").strip().upper()
    if quality and quality != "OK":
        return "REVIEW", [item.label], True
    if "REQUIRED" in status or "MARGINAL" in status:
        return "WARN", [], False
    return "PASS", [], False


def _rebalance_status(item: InputRead) -> tuple[str, list[str], bool]:
    base_status, missing, hard = _status_from_single_row(item, required_label=item.label)
    if base_status != "PASS":
        return base_status, missing, hard
    for row in item.rows:
        quality = str(row.get("data_quality_flag", "") or "").strip().upper()
        if quality and quality != "OK":
            return "REVIEW", [item.label], True
    if any(str(row.get("recommended_action", "") or "").strip().upper() == "TRIM_FOR_REBALANCE_REVIEW" for row in item.rows):
        return "WARN", [], False
    return "PASS", [], False


def _decision_capture_status(item: InputRead) -> tuple[str, str]:
    if not item.exists:
        return "MISSING", "MISSING"
    if not item.readable:
        return "FAIL", "FAIL"
    if not item.rows:
        return "MISSING", "WARN"
    return "PASS", "PASS"


def _run_used_inputs_findings(item: InputRead) -> tuple[list[str], list[str]]:
    if not item.readable:
        return [], []
    if not item.rows:
        return ["run_used_inputs"], ["LINEAGE_INCOMPLETE"]

    columns = list(item.rows[0].keys())
    path_columns = [
        column
        for column in columns
        if column.lower() in {"path", "input_path", "artifact", "artifact_path", "source", "resolved_path"}
        or "path" in column.lower()
        or "artifact" in column.lower()
    ]
    if not path_columns:
        return ["run_used_inputs_lineage"], ["LINEAGE_INCOMPLETE"]

    status_columns = [column for column in columns if column.lower() in {"status", "input_status", "artifact_status"}]
    missing: list[str] = []
    reasons: list[str] = []
    for row in item.rows:
        if any(_is_private_or_absolute_lineage_value(str(row.get(column, "") or "")) for column in path_columns):
            _append_unique(missing, "run_used_inputs_private_or_external_path")
            _append_unique(reasons, "LINEAGE_INCOMPLETE")
        for column in status_columns:
            status = str(row.get(column, "") or "").strip().upper()
            if status in {"MISSING", "UNREADABLE", "REVIEW", "INVALID"}:
                _append_unique(missing, "run_used_inputs_status")
                _append_unique(reasons, "LINEAGE_INCOMPLETE")
    return missing, reasons


def build_decision_quality_state(
    *,
    input_closure: str = DEFAULT_INPUT_CLOSURE,
    decision_capture: str = DEFAULT_DECISION_CAPTURE,
    cash_refill: str = DEFAULT_CASH_REFILL,
    rebalance: str = DEFAULT_REBALANCE,
    run_manifest: str = DEFAULT_RUN_MANIFEST,
    run_used_inputs: str = DEFAULT_RUN_USED_INPUTS,
    monthly_ranking: str = DEFAULT_MONTHLY_RANKING,
    score_audit: str = DEFAULT_SCORE_AUDIT,
    as_of_date: str | None = None,
    generated_at: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    manifest_output_path, manifest_external_path = _normalize_path_for_output(run_manifest, "run_manifest")
    manifest_path = resolve_repo_path(run_manifest)
    manifest_exists = manifest_path.exists()
    if manifest_external_path:
        manifest_exists = False
        manifest, manifest_error = {}, "external path redacted"
    else:
        manifest, manifest_error = _read_json(run_manifest) if manifest_exists else ({}, "missing")
    fallback_date = as_of_date or date.today().isoformat()
    effective_as_of = _derive_as_of_date(manifest, fallback_date)
    effective_run_id = run_id or _derive_run_id(manifest, f"{effective_as_of}-monthly")
    source_commit = _derive_source_commit(manifest)

    ranking_required = (
        _manifest_stage_executed(manifest, "monthly")
        or _manifest_stage_executed(manifest, "monthly_ranking")
        or _manifest_output_ref_exists(manifest, "monthly_buy_ranking", "personal_monthly_buy_ranking")
    )
    score_required = (
        _manifest_stage_executed(manifest, "scoring")
        or _manifest_stage_executed(manifest, "score")
        or _manifest_output_ref_exists(manifest, "score_audit", "personal_score_audit", "company_scores")
    )

    inputs = [
        _read_input("personal_input_closure_report", input_closure, mandatory=True),
        _read_input("decision_capture", decision_capture, mandatory=False),
        _read_input("cash_refill_review", cash_refill, mandatory=True),
        _read_input("rebalance_review", rebalance, mandatory=True),
        _read_input("run_used_inputs", run_used_inputs, mandatory=True),
        _read_input("monthly_ranking_output", monthly_ranking, mandatory=ranking_required),
        _read_input("score_audit_output", score_audit, mandatory=score_required),
    ]

    input_artifacts = [
        f"run_manifest={manifest_output_path}:{'AVAILABLE' if manifest_exists and not manifest_error else 'MISSING' if not manifest_exists else 'UNREADABLE'}"
    ]
    input_artifacts.extend(f"{item.label}={item.path}:{_artifact_status(item)}" for item in inputs)

    hard_blockers: list[str] = []
    missing_critical_fields: list[str] = []
    confidence_reason_codes: list[str] = []
    review_reason_codes: list[str] = []

    if not manifest_exists or manifest_error:
        _append_unique(hard_blockers, "LINEAGE_INCOMPLETE")
        _append_unique(missing_critical_fields, "personal_run_manifest")
        _append_unique(confidence_reason_codes, "LINEAGE_INCOMPLETE")
        _append_unique(review_reason_codes, "LINEAGE_INCOMPLETE")
    if not source_commit:
        _append_unique(hard_blockers, "LINEAGE_INCOMPLETE")
        _append_unique(missing_critical_fields, "source_commit_sha")
        _append_unique(confidence_reason_codes, "LINEAGE_INCOMPLETE")
        _append_unique(review_reason_codes, "LINEAGE_INCOMPLETE")

    for item in inputs:
        if item.mandatory and not item.readable:
            _append_unique(hard_blockers, "LINEAGE_INCOMPLETE" if item.label in {"run_used_inputs"} or item.external_path else "EVIDENCE_MISSING")
            _append_unique(missing_critical_fields, item.label)
            _append_unique(confidence_reason_codes, "LINEAGE_INCOMPLETE" if item.label == "run_used_inputs" or item.external_path else "EVIDENCE_MISSING")
            _append_unique(review_reason_codes, "LINEAGE_INCOMPLETE" if item.label == "run_used_inputs" or item.external_path else "EVIDENCE_MISSING")

    run_used_missing, run_used_reasons = _run_used_inputs_findings(inputs[4])
    for field in run_used_missing:
        _append_unique(missing_critical_fields, field)
    for reason in run_used_reasons:
        _append_unique(confidence_reason_codes, reason)
        _append_unique(review_reason_codes, reason)
        _append_unique(hard_blockers, reason)

    input_closure_item = inputs[0]
    evidence_status, data_quality_status, evidence_pct, closure_missing, closure_reasons, closure_blocked = _input_closure_signals(input_closure_item)
    for field in closure_missing:
        _append_unique(missing_critical_fields, field)
    for reason in closure_reasons:
        _append_unique(confidence_reason_codes, reason)
        if reason in {"INPUT_CLOSURE_BLOCKED", "EVIDENCE_MISSING"}:
            _append_unique(review_reason_codes, reason)
    if closure_blocked:
        _append_unique(hard_blockers, "INPUT_CLOSURE_BLOCKED")

    cash_status, cash_missing, cash_hard = _cash_status(inputs[2])
    rebalance_status, rebalance_missing, rebalance_hard = _rebalance_status(inputs[3])
    for field in cash_missing + rebalance_missing:
        _append_unique(missing_critical_fields, field)
        _append_unique(confidence_reason_codes, "EVIDENCE_MISSING")
        _append_unique(review_reason_codes, "EVIDENCE_MISSING")
    if cash_hard or rebalance_hard:
        _append_unique(hard_blockers, "EVIDENCE_MISSING")

    decision_capture_status, journal_quality_status = _decision_capture_status(inputs[1])
    if decision_capture_status == "MISSING":
        _append_unique(confidence_reason_codes, "DECISION_JOURNAL_INCOMPLETE")

    if cash_status == "REVIEW" or rebalance_status == "REVIEW":
        portfolio_health_status = "REVIEW"
    elif cash_status == "WARN" or rebalance_status == "WARN":
        portfolio_health_status = "WARN"
    elif cash_status == "MISSING" or rebalance_status == "MISSING":
        portfolio_health_status = "REVIEW"
    else:
        portfolio_health_status = "PASS"

    ranking_available = inputs[5].readable
    ranking_stability_status = "NOT_EVALUATED"
    sensitivity_status = "NOT_EVALUATED"
    scenario_status = "NOT_EVALUATED"
    tail_risk_status = "NOT_EVALUATED"
    scenario_robustness_score = "NOT_EVALUATED"
    _append_unique(confidence_reason_codes, "RANKING_STABILITY_NOT_EVALUATED")
    _append_unique(confidence_reason_codes, "SENSITIVITY_NOT_EVALUATED")

    if missing_critical_fields:
        _append_unique(confidence_reason_codes, "EVIDENCE_MISSING")
        _append_unique(review_reason_codes, "EVIDENCE_MISSING")
        _append_unique(hard_blockers, "EVIDENCE_MISSING")
    if data_quality_status == "MISSING":
        _append_unique(confidence_reason_codes, "EVIDENCE_MISSING")
        _append_unique(review_reason_codes, "EVIDENCE_MISSING")
        _append_unique(hard_blockers, "EVIDENCE_MISSING")

    if hard_blockers:
        decision_confidence_level = "REVIEW"
    elif data_quality_status == "REVIEW":
        decision_confidence_level = "LOW"
    elif evidence_status == "PARTIAL" or ranking_stability_status == "NOT_EVALUATED" or sensitivity_status == "NOT_EVALUATED":
        decision_confidence_level = "MEDIUM"
    else:
        decision_confidence_level = "HIGH"

    review_required = bool(hard_blockers)
    if not review_required:
        review_reason_codes = []

    if evidence_status in {"MISSING", "REVIEW"}:
        evidence_pct = None

    return {
        "run_id": effective_run_id,
        "as_of_date": effective_as_of,
        "generated_at": generated_at or _utc_now(),
        "source_commit_sha": source_commit,
        "contract_version": CONTRACT_VERSION,
        "input_artifacts": input_artifacts,
        "evidence_coverage_status": evidence_status,
        "evidence_coverage_pct": evidence_pct,
        "data_quality_status": data_quality_status,
        "missing_critical_fields": missing_critical_fields,
        "stale_inputs": [],
        "conflicting_inputs": [],
        "decision_capture_status": decision_capture_status,
        "journal_quality_status": journal_quality_status,
        "portfolio_health_status": portfolio_health_status,
        "cash_refill_status": cash_status,
        "rebalance_status": rebalance_status,
        "ranking_available": ranking_available,
        "ranking_stability_status": ranking_stability_status,
        "sensitivity_status": sensitivity_status,
        "scenario_status": scenario_status,
        "tail_risk_status": tail_risk_status,
        "scenario_robustness_score": scenario_robustness_score,
        "decision_confidence_level": decision_confidence_level,
        "confidence_reason_codes": confidence_reason_codes,
        "review_required": review_required,
        "review_reason_codes": review_reason_codes,
        "non_scope_confirmations": NON_SCOPE_CONFIRMATIONS,
    }


def _csv_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ";".join(str(item) for item in value)
    if value is None:
        return ""
    if isinstance(value, float):
        return str(value)
    return str(value)


def write_state_csv(state: dict[str, Any], path_value: str | Path) -> Path:
    path = ensure_parent_dir(path_value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerow({field: _csv_value(state.get(field)) for field in FIELDNAMES})
    return path


def write_state_json(state: dict[str, Any], path_value: str | Path) -> Path:
    path = ensure_parent_dir(path_value)
    path.write_text(json.dumps({field: state.get(field) for field in FIELDNAMES}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def render_report(state: dict[str, Any]) -> str:
    not_evaluated = [
        field
        for field in ("ranking_stability_status", "sensitivity_status", "scenario_status", "tail_risk_status", "scenario_robustness_score")
        if state.get(field) == "NOT_EVALUATED"
    ]
    lines = [
        "# Decision Quality Report",
        "",
        f"- run_id: `{state['run_id']}`",
        f"- as_of_date: `{state['as_of_date']}`",
        f"- source_commit_sha: `{state['source_commit_sha']}`",
        f"- decision_confidence_level: `{state['decision_confidence_level']}`",
        f"- review_required: `{'true' if state['review_required'] else 'false'}`",
        f"- evidence_coverage_status: `{state['evidence_coverage_status']}`",
        f"- evidence_coverage_pct: `{'' if state['evidence_coverage_pct'] is None else state['evidence_coverage_pct']}`",
        f"- data_quality_status: `{state['data_quality_status']}`",
        f"- portfolio_health_status: `{state['portfolio_health_status']}`",
        f"- cash_refill_status: `{state['cash_refill_status']}`",
        f"- rebalance_status: `{state['rebalance_status']}`",
        "",
        "## Missing Critical Fields",
        "",
        ";".join(state["missing_critical_fields"]) or "None",
        "",
        "## Confidence Reason Codes",
        "",
        ";".join(state["confidence_reason_codes"]) or "None",
        "",
        "## Review Reason Codes",
        "",
        ";".join(state["review_reason_codes"]) or "None",
        "",
        "## Phase 1.5 Not Evaluated Fields",
        "",
        ";".join(not_evaluated) or "None",
        "",
        "## Non-Scope",
        "",
        "- no broker/order/trading",
        "- no score formula change",
        "- no portfolio rule change",
        "- no silent data enrichment",
        "- no simulation/backtesting",
        "- no outcome attribution",
        "- no runtime LLM decisioning",
        "- no tax quantification",
        "- no portfolio event ledger",
        "- no private raw data",
        "",
    ]
    return "\n".join(lines)


def write_report(state: dict[str, Any], path_value: str | Path) -> Path:
    path = ensure_parent_dir(path_value)
    path.write_text(render_report(state), encoding="utf-8")
    return path


def run_decision_quality_state(
    *,
    input_closure: str = DEFAULT_INPUT_CLOSURE,
    decision_capture: str = DEFAULT_DECISION_CAPTURE,
    cash_refill: str = DEFAULT_CASH_REFILL,
    rebalance: str = DEFAULT_REBALANCE,
    run_manifest: str = DEFAULT_RUN_MANIFEST,
    run_used_inputs: str = DEFAULT_RUN_USED_INPUTS,
    monthly_ranking: str = DEFAULT_MONTHLY_RANKING,
    score_audit: str = DEFAULT_SCORE_AUDIT,
    out_csv: str = DEFAULT_OUT_CSV,
    out_json: str = DEFAULT_OUT_JSON,
    report: str | None = None,
    as_of_date: str | None = None,
    generated_at: str | None = None,
    run_id: str | None = None,
) -> DecisionQualityResult:
    state = build_decision_quality_state(
        input_closure=input_closure,
        decision_capture=decision_capture,
        cash_refill=cash_refill,
        rebalance=rebalance,
        run_manifest=run_manifest,
        run_used_inputs=run_used_inputs,
        monthly_ranking=monthly_ranking,
        score_audit=score_audit,
        as_of_date=as_of_date,
        generated_at=generated_at,
        run_id=run_id,
    )
    csv_path = write_state_csv(state, out_csv)
    json_path = write_state_json(state, out_json)
    effective_report = report or DEFAULT_REPORT_PATTERN.format(as_of_date=state["as_of_date"])
    report_path = write_report(state, effective_report)
    return DecisionQualityResult(csv_output=csv_path, json_output=json_path, report_output=report_path, state=state)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a minimal Decision Quality State from existing processed artifacts.")
    parser.add_argument("--input-closure", default=DEFAULT_INPUT_CLOSURE)
    parser.add_argument("--decision-capture", default=DEFAULT_DECISION_CAPTURE)
    parser.add_argument("--cash-refill", default=DEFAULT_CASH_REFILL)
    parser.add_argument("--rebalance", default=DEFAULT_REBALANCE)
    parser.add_argument("--run-manifest", default=DEFAULT_RUN_MANIFEST)
    parser.add_argument("--run-used-inputs", default=DEFAULT_RUN_USED_INPUTS)
    parser.add_argument("--monthly-ranking", default=DEFAULT_MONTHLY_RANKING)
    parser.add_argument("--score-audit", default=DEFAULT_SCORE_AUDIT)
    parser.add_argument("--out-csv", default=DEFAULT_OUT_CSV)
    parser.add_argument("--out-json", default=DEFAULT_OUT_JSON)
    parser.add_argument("--report", default=None)
    parser.add_argument("--as-of-date", default=None)
    parser.add_argument("--generated-at", default=None)
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_decision_quality_state(
        input_closure=args.input_closure,
        decision_capture=args.decision_capture,
        cash_refill=args.cash_refill,
        rebalance=args.rebalance,
        run_manifest=args.run_manifest,
        run_used_inputs=args.run_used_inputs,
        monthly_ranking=args.monthly_ranking,
        score_audit=args.score_audit,
        out_csv=args.out_csv,
        out_json=args.out_json,
        report=args.report,
        as_of_date=args.as_of_date,
        generated_at=args.generated_at,
        run_id=args.run_id,
    )
    print(f"csv_output={result.csv_output}")
    print(f"json_output={result.json_output}")
    print(f"report_output={result.report_output}")
    print(f"decision_confidence_level={result.state['decision_confidence_level']}")
    print(f"review_required={'true' if result.state['review_required'] else 'false'}")


if __name__ == "__main__":
    main()
