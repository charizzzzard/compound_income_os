from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from src.common import ensure_parent_dir, read_csv_rows, resolve_repo_path
from src.personal_decision_state_capture import FIELDS as DECISION_FIELDS
from src.personal_decision_state_capture import MANUAL_REQUIRED_FIELDS, parse_iso_date, row_validation_reasons

DEFAULT_JOURNAL = "data/processed/personal_decision_state_capture.csv"
DEFAULT_DECISION_QUALITY_CSV = "data/processed/decision_quality_state.csv"
DEFAULT_DECISION_QUALITY_JSON = "data/processed/decision_quality_state.json"
DEFAULT_RUN_MANIFEST = "data/processed/personal_run_manifest.json"
DEFAULT_RUN_USED_INPUTS = "data/processed/personal_run_used_inputs.csv"
DEFAULT_VALIDATION_OUTPUT = "data/processed/decision_journal_validation.csv"
DEFAULT_QUEUE_OUTPUT = "data/processed/decision_review_queue.csv"
DEFAULT_REPORT_PATTERN = "reports/{as_of_date}/decision_journal_validation_report.md"

WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
UNC_PATH_RE = re.compile(r"^(?:\\\\|//)[^\\/]+[\\/][^\\/]+")

VALIDATION_FIELDS = [
    "validation_id",
    "as_of_date",
    "validation_status",
    "decision_id",
    "field_name",
    "reason_code",
    "priority",
    "source_artifact",
    "message",
]

QUEUE_FIELDS = [
    "queue_id",
    "as_of_date",
    "decision_id",
    "decision_date",
    "symbol",
    "action",
    "priority",
    "queue_status",
    "reason_codes",
    "review_due_date",
    "days_overdue",
    "process_confidence_level",
    "decision_quality_status",
    "source_commit_sha",
    "run_id",
    "source_artifact",
    "recommended_operator_action",
]

NON_SCOPE_NOTES = [
    "no broker/order/trading",
    "no score formula change",
    "no portfolio rule change",
    "no silent data enrichment",
    "no simulation/backtesting",
    "no outcome attribution",
    "no runtime LLM decisioning",
    "no tax quantification",
    "no portfolio event ledger",
    "no private raw data",
]

PRIORITY_TAXONOMY = {
    "BLOCKER": "Missing/unreadable/empty journal, duplicate decision_id, broken active-decision lineage or schema/contract violation.",
    "HIGH": "Due review date, missing review_date for active decisions, incomplete rationale or Decision Quality review_required=true.",
    "MEDIUM": "Stale Decision Quality State, source_commit mismatch or process/review confidence follow-up.",
    "LOW": "Reserved for non-blocking cleanup hints.",
    "NOTE": "Reserved for informational hints.",
}
MAX_DECISION_QUALITY_AGE_DAYS = 0

ACTIVE_STATUSES = {"OPEN", "BLOCKED", "REVIEW_SCHEDULED", "NOT_AVAILABLE", "INSUFFICIENT_EVIDENCE"}
ACTIVE_HUMAN_DECISIONS = {"PENDING_REVIEW", "DEFERRED", "APPROVED_FOR_MANUAL_ACTION", "NOT_REVIEWED"}
ACTIVE_ACTIONS = {"HOLD_REVIEW", "TRIM_REVIEW", "EXIT_REVIEW", "WAIT_FOR_EVIDENCE", "WAIT_FOR_PRICE", "WAIT_FOR_REVIEW", "RESEARCH_MORE", "CASH_DEPLOYMENT"}
REQUIRED_ROW_FIELDS = ["decision_id", "decision_date", *MANUAL_REQUIRED_FIELDS]


@dataclass(frozen=True)
class DecisionJournalValidationResult:
    validation_output: Path
    queue_output: Path
    report_output: Path
    validation_rows: list[dict[str, str]]
    queue_rows: list[dict[str, str]]
    summary: dict[str, Any]


def _repo_root() -> Path:
    return resolve_repo_path(".").resolve()


def _git_head() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_repo_root(),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_windows_absolute_path(raw: str) -> bool:
    return bool(WINDOWS_ABSOLUTE_RE.match(raw))


def _is_unc_path(raw: str) -> bool:
    return bool(UNC_PATH_RE.match(raw))


def _sanitize_path(path_value: str | Path, label: str) -> tuple[str, bool]:
    raw = str(path_value or "").strip()
    if not raw:
        return "", False
    lowered = raw.replace("\\", "/").lower()
    if "data/raw/private" in lowered:
        return f"EXTERNAL_PATH_REDACTED:{label}", True
    if _is_windows_absolute_path(raw) or _is_unc_path(raw):
        path = Path(raw)
        if path.is_absolute():
            try:
                return path.resolve().relative_to(_repo_root()).as_posix(), False
            except ValueError:
                pass
        return f"EXTERNAL_PATH_REDACTED:{label}", True
    path = Path(raw)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(_repo_root()).as_posix(), False
        except ValueError:
            return f"EXTERNAL_PATH_REDACTED:{label}", True
    try:
        return (_repo_root() / raw.replace("\\", "/")).resolve().relative_to(_repo_root()).as_posix(), False
    except ValueError:
        return f"EXTERNAL_PATH_REDACTED:{label}", True


def _safe_artifact_path(path_value: str | Path, label: str) -> str:
    sanitized, _ = _sanitize_path(path_value, label)
    return sanitized


def _read_json(path_value: str | Path) -> tuple[dict[str, Any], str]:
    path = resolve_repo_path(path_value)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - surfaced as validation context
        return {}, str(exc)
    return data if isinstance(data, dict) else {}, ""


def _read_csv_optional(path_value: str | Path) -> tuple[list[dict[str, str]], str]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], "MISSING"
    try:
        return read_csv_rows(path), ""
    except Exception as exc:  # noqa: BLE001 - surfaced as validation context
        return [], str(exc)


def _read_journal(path_value: str) -> tuple[list[dict[str, str]], str]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], "MISSING"
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            missing_columns = [field for field in DECISION_FIELDS if field not in fieldnames]
            if missing_columns:
                return [], f"MISSING_COLUMNS:{';'.join(missing_columns)}"
            rows = [
                {field: str(row.get(field, "") or "").strip() for field in DECISION_FIELDS}
                for row in reader
                if any(str(value or "").strip() for value in row.values())
            ]
    except Exception as exc:  # noqa: BLE001 - surfaced as validation context
        return [], f"UNREADABLE:{exc}"
    return rows, ""


def _load_decision_quality(csv_path: str, json_path: str) -> tuple[dict[str, Any], str, str]:
    json_resolved = resolve_repo_path(json_path)
    if json_resolved.exists():
        data, error = _read_json(json_path)
        return data, _safe_artifact_path(json_path, "decision_quality_json"), error
    rows, error = _read_csv_optional(csv_path)
    if rows:
        return dict(rows[0]), _safe_artifact_path(csv_path, "decision_quality_csv"), ""
    return {}, "", error or "MISSING"


def _load_manifest(path_value: str) -> tuple[dict[str, Any], str]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return {}, "MISSING"
    return _read_json(path_value)


def _derive_as_of_date(
    *,
    requested_as_of_date: str | None,
    manifest: Mapping[str, Any],
    decision_quality: Mapping[str, Any],
    journal_rows: list[dict[str, str]],
) -> str:
    if requested_as_of_date:
        return requested_as_of_date
    for value in (
        decision_quality.get("as_of_date"),
        manifest.get("as_of_date"),
        manifest.get("source_snapshot_date"),
        manifest.get("portfolio_date"),
    ):
        text = str(value or "").strip()
        if len(text) >= 10:
            return text[:10]
    dates = sorted(str(row.get("decision_date", "") or "") for row in journal_rows if parse_iso_date(row.get("decision_date", "")))
    if dates:
        return dates[-1]
    return date.today().isoformat()


def _manifest_commit(manifest: Mapping[str, Any]) -> str:
    for key in ("source_commit_sha", "git_head", "repo_head", "commit_sha", "current_head"):
        value = str(manifest.get(key) or "").strip()
        if value:
            return value
    return _git_head()


def _active_decision(row: Mapping[str, str]) -> bool:
    status = str(row.get("decision_status", "")).upper()
    human = str(row.get("human_decision", "")).upper()
    action = str(row.get("proposed_action", "")).upper()
    if status in {"CLOSED", "SUPERSEDED", "INVALID"}:
        return False
    return status in ACTIVE_STATUSES or human in ACTIVE_HUMAN_DECISIONS or action in ACTIVE_ACTIONS


def _symbol(row: Mapping[str, str]) -> str:
    for field in ("ticker", "asset_id", "asset_name"):
        value = str(row.get(field, "") or "").strip()
        if value and value not in {"UNKNOWN", "MISSING_REFERENCE"}:
            return value
    return "UNKNOWN"


def _reasoning_incomplete(row: Mapping[str, str]) -> bool:
    text = str(row.get("reasoning_3_sentences", "") or "").strip()
    if not text:
        return True
    sentence_marks = sum(text.count(mark) for mark in ".!?")
    return len(text) < 30 or sentence_marks < 2


def _broken_source_refs(row: Mapping[str, str]) -> list[str]:
    broken: list[str] = []
    for field in ("run_id", "manifest_path", "primary_report_path", "source_snapshot_date", "policy_ref"):
        value = str(row.get(field, "") or "").strip()
        if value in {"", "UNKNOWN", "MISSING_REFERENCE"}:
            broken.append(field)
    for field in ("manifest_path", "primary_report_path"):
        value = str(row.get(field, "") or "").strip()
        if not value or value in {"UNKNOWN", "MISSING_REFERENCE"}:
            continue
        sanitized, external = _sanitize_path(value, field)
        if external or not resolve_repo_path(sanitized).exists():
            broken.append(field)
    return sorted(set(broken))


def _validation_row(
    *,
    index: int,
    as_of_date: str,
    status: str,
    decision_id: str = "",
    field_name: str = "",
    reason_code: str,
    priority: str,
    source_artifact: str,
    message: str,
) -> dict[str, str]:
    return {
        "validation_id": f"VAL_{as_of_date.replace('-', '')}_{index:04d}",
        "as_of_date": as_of_date,
        "validation_status": status,
        "decision_id": decision_id,
        "field_name": field_name,
        "reason_code": reason_code,
        "priority": priority,
        "source_artifact": source_artifact,
        "message": message,
    }


def _queue_row(
    *,
    index: int,
    as_of_date: str,
    decision: Mapping[str, str] | None,
    priority: str,
    reason_codes: list[str],
    review_due_date: str = "",
    days_overdue: str = "",
    process_confidence_level: str = "",
    decision_quality_status: str = "",
    source_commit_sha: str = "",
    source_artifact: str,
    recommended_operator_action: str,
) -> dict[str, str]:
    decision = decision or {}
    return {
        "queue_id": f"QUEUE_{as_of_date.replace('-', '')}_{index:04d}",
        "as_of_date": as_of_date,
        "decision_id": str(decision.get("decision_id", "") or ""),
        "decision_date": str(decision.get("decision_date", "") or ""),
        "symbol": _symbol(decision) if decision else "",
        "action": str(decision.get("proposed_action", "") or ""),
        "priority": priority,
        "queue_status": "OPEN",
        "reason_codes": ";".join(reason_codes),
        "review_due_date": review_due_date,
        "days_overdue": days_overdue,
        "process_confidence_level": process_confidence_level,
        "decision_quality_status": decision_quality_status,
        "source_commit_sha": source_commit_sha,
        "run_id": str(decision.get("run_id", "") or ""),
        "source_artifact": source_artifact,
        "recommended_operator_action": recommended_operator_action,
    }


def _append_validation(rows: list[dict[str, str]], **kwargs: Any) -> None:
    rows.append(_validation_row(index=len(rows) + 1, **kwargs))


def _append_queue(rows: list[dict[str, str]], **kwargs: Any) -> None:
    rows.append(_queue_row(index=len(rows) + 1, **kwargs))


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() == "true"


def _date_days_overdue(review_date: str, as_of_date: str) -> str:
    review = parse_iso_date(review_date)
    as_of = parse_iso_date(as_of_date)
    if not review or not as_of:
        return ""
    return str(max((as_of - review).days, 0))


def _summary_counts(validation_rows: list[dict[str, str]], queue_rows: list[dict[str, str]]) -> dict[str, int]:
    return {
        "validation_findings_count": len(validation_rows),
        "validation_blocker_count": sum(1 for row in validation_rows if row.get("priority") == "BLOCKER"),
        "validation_high_count": sum(1 for row in validation_rows if row.get("priority") == "HIGH"),
        "queue_items": len(queue_rows),
        "queue_blocker_count": sum(1 for row in queue_rows if row.get("priority") == "BLOCKER"),
        "queue_high_count": sum(1 for row in queue_rows if row.get("priority") == "HIGH"),
        "stale_state_count": sum(1 for row in queue_rows if "DECISION_QUALITY_STALE" in row.get("reason_codes", "")),
    }


def build_decision_journal_validation(
    *,
    journal: str = DEFAULT_JOURNAL,
    decision_quality_csv: str = DEFAULT_DECISION_QUALITY_CSV,
    decision_quality_json: str = DEFAULT_DECISION_QUALITY_JSON,
    run_manifest: str = DEFAULT_RUN_MANIFEST,
    run_used_inputs: str = DEFAULT_RUN_USED_INPUTS,
    as_of_date: str | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    journal_artifact = _safe_artifact_path(journal, "decision_journal")
    journal_rows, journal_error = _read_journal(journal)
    manifest, manifest_error = _load_manifest(run_manifest)
    decision_quality, decision_quality_artifact, decision_quality_error = _load_decision_quality(decision_quality_csv, decision_quality_json)
    effective_as_of = _derive_as_of_date(
        requested_as_of_date=as_of_date,
        manifest=manifest,
        decision_quality=decision_quality,
        journal_rows=journal_rows,
    )
    validation_rows: list[dict[str, str]] = []
    queue_rows: list[dict[str, str]] = []
    dq_status = "AVAILABLE" if decision_quality else "NOT_AVAILABLE"
    process_confidence = str(decision_quality.get("decision_confidence_level", "") or "")
    dq_source_commit = str(decision_quality.get("source_commit_sha", "") or "")
    source_commit = _manifest_commit(manifest)

    if journal_error == "MISSING":
        _append_validation(
            validation_rows,
            as_of_date=effective_as_of,
            status="REVIEW",
            reason_code="DECISION_JOURNAL_MISSING",
            priority="BLOCKER",
            source_artifact=journal_artifact,
            message="Decision journal artifact is missing.",
        )
        _append_queue(
            queue_rows,
            as_of_date=effective_as_of,
            decision=None,
            priority="BLOCKER",
            reason_codes=["DECISION_JOURNAL_MISSING"],
            process_confidence_level=process_confidence,
            decision_quality_status=dq_status,
            source_commit_sha=source_commit,
            source_artifact=journal_artifact,
            recommended_operator_action="Create or provide the append-only Decision Capture journal before relying on review readiness.",
        )
    elif journal_error:
        _append_validation(
            validation_rows,
            as_of_date=effective_as_of,
            status="REVIEW",
            reason_code="DECISION_JOURNAL_UNREADABLE",
            priority="BLOCKER",
            source_artifact=journal_artifact,
            message=journal_error,
        )
        _append_queue(
            queue_rows,
            as_of_date=effective_as_of,
            decision=None,
            priority="BLOCKER",
            reason_codes=["DECISION_JOURNAL_UNREADABLE"],
            process_confidence_level=process_confidence,
            decision_quality_status=dq_status,
            source_commit_sha=source_commit,
            source_artifact=journal_artifact,
            recommended_operator_action="Fix the Decision Capture CSV so it can be read and contract-validated.",
        )
    elif not journal_rows:
        _append_validation(
            validation_rows,
            as_of_date=effective_as_of,
            status="REVIEW",
            reason_code="DECISION_JOURNAL_EMPTY",
            priority="BLOCKER",
            source_artifact=journal_artifact,
            message="Decision journal has headers but no decision rows.",
        )
        _append_queue(
            queue_rows,
            as_of_date=effective_as_of,
            decision=None,
            priority="BLOCKER",
            reason_codes=["DECISION_JOURNAL_EMPTY"],
            process_confidence_level=process_confidence,
            decision_quality_status=dq_status,
            source_commit_sha=source_commit,
            source_artifact=journal_artifact,
            recommended_operator_action="Record reviewed decisions or an explicit no-action entry after the monthly review.",
        )

    seen_decision_ids: dict[str, int] = {}
    duplicate_decision_ids: set[str] = set()
    for row in journal_rows:
        decision_id = row.get("decision_id", "")
        if decision_id:
            seen_decision_ids[decision_id] = seen_decision_ids.get(decision_id, 0) + 1
            if seen_decision_ids[decision_id] == 2:
                duplicate_decision_ids.add(decision_id)
                duplicate_decision = {"decision_id": decision_id}
                _append_validation(
                    validation_rows,
                    as_of_date=effective_as_of,
                    status="REVIEW",
                    decision_id=decision_id,
                    field_name="decision_id",
                    reason_code="DECISION_ID_DUPLICATE",
                    priority="BLOCKER",
                    source_artifact=journal_artifact,
                    message="decision_id appears more than once in the append-only Decision Capture journal.",
                )
                _append_queue(
                    queue_rows,
                    as_of_date=effective_as_of,
                    decision=duplicate_decision,
                    priority="BLOCKER",
                    reason_codes=["DECISION_ID_DUPLICATE"],
                    process_confidence_level=process_confidence,
                    decision_quality_status=dq_status,
                    source_commit_sha=source_commit,
                    source_artifact=journal_artifact,
                    recommended_operator_action="Review duplicate decision_id entries and correct the append-only journal.",
                )
        for field in REQUIRED_ROW_FIELDS:
            if not str(row.get(field, "") or "").strip():
                _append_validation(
                    validation_rows,
                    as_of_date=effective_as_of,
                    status="REVIEW",
                    decision_id=decision_id,
                    field_name=field,
                    reason_code="DECISION_FIELD_MISSING",
                    priority="HIGH",
                    source_artifact=journal_artifact,
                    message=f"Decision row is missing required field {field}.",
                )
        for reason in row_validation_reasons(dict(row)):
            code = "REVIEW_DATE_MISSING" if reason == "MISSING_CONDITIONAL:review_date" else "DECISION_FIELD_MISSING"
            field_name = reason.split(":", 1)[-1].split("=", 1)[0] if ":" in reason else ""
            _append_validation(
                validation_rows,
                as_of_date=effective_as_of,
                status="REVIEW",
                decision_id=decision_id,
                field_name=field_name,
                reason_code=code,
                priority="HIGH",
                source_artifact=journal_artifact,
                message=reason,
            )

        if not _active_decision(row):
            continue

        review_date = str(row.get("review_date", "") or "").strip()
        if review_date and parse_iso_date(review_date) and parse_iso_date(review_date) <= parse_iso_date(effective_as_of):
            _append_queue(
                queue_rows,
                as_of_date=effective_as_of,
                decision=row,
                priority="HIGH",
                reason_codes=["REVIEW_DATE_DUE"],
                review_due_date=review_date,
                days_overdue=_date_days_overdue(review_date, effective_as_of),
                process_confidence_level=process_confidence,
                decision_quality_status=dq_status,
                source_commit_sha=source_commit,
                source_artifact=journal_artifact,
                recommended_operator_action="Review this open decision because its review date is due.",
            )
        if not review_date:
            _append_queue(
                queue_rows,
                as_of_date=effective_as_of,
                decision=row,
                priority="HIGH",
                reason_codes=["REVIEW_DATE_MISSING"],
                process_confidence_level=process_confidence,
                decision_quality_status=dq_status,
                source_commit_sha=source_commit,
                source_artifact=journal_artifact,
                recommended_operator_action="Add a review_date or close/supersede the decision with a reviewed journal entry.",
            )
        if _reasoning_incomplete(row):
            _append_queue(
                queue_rows,
                as_of_date=effective_as_of,
                decision=row,
                priority="HIGH",
                reason_codes=["DECISION_RATIONALE_INCOMPLETE"],
                review_due_date=review_date,
                process_confidence_level=process_confidence,
                decision_quality_status=dq_status,
                source_commit_sha=source_commit,
                source_artifact=journal_artifact,
                recommended_operator_action="Complete reasoning_3_sentences before relying on this journal entry.",
            )
        broken_refs = _broken_source_refs(row)
        if broken_refs:
            _append_queue(
                queue_rows,
                as_of_date=effective_as_of,
                decision=row,
                priority="BLOCKER",
                reason_codes=["DECISION_SOURCE_REF_BROKEN"],
                review_due_date=review_date,
                process_confidence_level=process_confidence,
                decision_quality_status=dq_status,
                source_commit_sha=source_commit,
                source_artifact=journal_artifact,
                recommended_operator_action=f"Fix missing or broken lineage fields: {';'.join(broken_refs)}.",
            )

    if decision_quality:
        dq_as_of = str(decision_quality.get("as_of_date", "") or "")
        # Phase 1.6B MVP is governance-conservative: any older Decision Quality
        # as_of_date is stale. MAX_DECISION_QUALITY_AGE_DAYS is intentionally 0.
        if dq_as_of and parse_iso_date(dq_as_of) and parse_iso_date(dq_as_of) < parse_iso_date(effective_as_of):
            _append_queue(
                queue_rows,
                as_of_date=effective_as_of,
                decision=None,
                priority="MEDIUM",
                reason_codes=["DECISION_QUALITY_STALE"],
                review_due_date=dq_as_of,
                days_overdue=_date_days_overdue(dq_as_of, effective_as_of),
                process_confidence_level=process_confidence,
                decision_quality_status=dq_status,
                source_commit_sha=dq_source_commit,
                source_artifact=decision_quality_artifact,
                recommended_operator_action="Refresh Decision Quality State for the current as_of_date.",
            )
        if source_commit and dq_source_commit and source_commit != dq_source_commit:
            _append_queue(
                queue_rows,
                as_of_date=effective_as_of,
                decision=None,
                priority="MEDIUM",
                reason_codes=["DECISION_QUALITY_LINEAGE_MISMATCH"],
                process_confidence_level=process_confidence,
                decision_quality_status=dq_status,
                source_commit_sha=dq_source_commit,
                source_artifact=decision_quality_artifact,
                recommended_operator_action="Regenerate Decision Quality State against the current run manifest/source commit.",
            )
        if _parse_bool(decision_quality.get("review_required")):
            _append_queue(
                queue_rows,
                as_of_date=effective_as_of,
                decision=None,
                priority="HIGH",
                reason_codes=["DECISION_QUALITY_REVIEW_REQUIRED"],
                process_confidence_level=process_confidence,
                decision_quality_status=dq_status,
                source_commit_sha=dq_source_commit,
                source_artifact=decision_quality_artifact,
                recommended_operator_action="Resolve Decision Quality review reasons before relying on monthly review readiness.",
            )
    elif decision_quality_error and decision_quality_error not in {"MISSING"}:
        _append_validation(
            validation_rows,
            as_of_date=effective_as_of,
            status="REVIEW",
            reason_code="DECISION_QUALITY_UNREADABLE",
            priority="MEDIUM",
            source_artifact=_safe_artifact_path(decision_quality_json or decision_quality_csv, "decision_quality"),
            message=decision_quality_error,
        )

    validation_status = "REVIEW" if validation_rows or any(row["priority"] in {"BLOCKER", "HIGH"} for row in queue_rows) else "PASS"
    counts = _summary_counts(validation_rows, queue_rows)
    summary = {
        "as_of_date": effective_as_of,
        "validation_status": validation_status,
        "total_decisions": len(journal_rows),
        **counts,
        "blocker_count": counts["queue_blocker_count"],
        "high_count": counts["queue_high_count"],
        "decision_quality_status": dq_status,
        "decision_quality_as_of_date": str(decision_quality.get("as_of_date", "") or ""),
        "decision_quality_source_commit_sha": dq_source_commit,
        "decision_quality_review_required": "true" if _parse_bool(decision_quality.get("review_required")) else "false",
        "process_confidence_level": process_confidence,
        "source_commit_sha": source_commit,
        "manifest_status": "AVAILABLE" if manifest and not manifest_error else "NOT_AVAILABLE",
        "run_used_inputs_status": "AVAILABLE" if resolve_repo_path(run_used_inputs).exists() else "NOT_AVAILABLE",
    }
    return validation_rows, queue_rows, summary


def _csv_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ";".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def write_validation_csv(rows: list[dict[str, str]], path_value: str | Path) -> Path:
    path = ensure_parent_dir(path_value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=VALIDATION_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: _csv_value(row.get(field, "")) for field in VALIDATION_FIELDS} for row in rows)
    return path


def write_queue_csv(rows: list[dict[str, str]], path_value: str | Path) -> Path:
    path = ensure_parent_dir(path_value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=QUEUE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: _csv_value(row.get(field, "")) for field in QUEUE_FIELDS} for row in rows)
    return path


def read_decision_journal_surface(validation_path: str | None, queue_path: str | None) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    validation_rows = read_csv_rows(validation_path) if validation_path and resolve_repo_path(validation_path).exists() else []
    queue_rows = read_csv_rows(queue_path) if queue_path and resolve_repo_path(queue_path).exists() else []
    return validation_rows, queue_rows


def summarize_surface(validation_rows: list[dict[str, str]], queue_rows: list[dict[str, str]]) -> dict[str, Any]:
    validation_status = "REVIEW" if validation_rows or queue_rows else "PASS"
    if validation_rows:
        validation_status = "REVIEW" if any(row.get("validation_status") == "REVIEW" for row in validation_rows) else validation_rows[0].get("validation_status", "PASS")
    counts = _summary_counts(validation_rows, queue_rows)
    return {
        "validation_status": validation_status,
        **counts,
        "blocker_count": counts["queue_blocker_count"],
        "high_count": counts["queue_high_count"],
    }


def build_decision_journal_surface_lines(
    validation_rows: list[dict[str, str]] | None = None,
    queue_rows: list[dict[str, str]] | None = None,
    *,
    validation_path: str | None = None,
    queue_path: str | None = None,
    include_heading: bool = True,
) -> list[str]:
    validation_rows = validation_rows or []
    queue_rows = queue_rows or []
    lines: list[str] = []
    if include_heading:
        lines.extend(["## Decision Journal Validation", ""])
    if not validation_rows and not queue_rows:
        lines.extend(
            [
                "- Decision Journal Validation: `NOT_AVAILABLE`",
                "- Grund: Validation-/Queue-Artefakt fehlt oder die Stage ist nicht gelaufen.",
            ]
        )
        return lines
    summary = summarize_surface(validation_rows, queue_rows)
    if validation_path:
        lines.append(f"- Validation artifact: `{validation_path}`")
    if queue_path:
        lines.append(f"- Review queue artifact: `{queue_path}`")
    lines.extend(
        [
            f"- validation_status: `{summary['validation_status']}`",
            f"- validation_findings_count: `{summary['validation_findings_count']}`",
            f"- validation_blocker_count: `{summary['validation_blocker_count']}`",
            f"- validation_high_count: `{summary['validation_high_count']}`",
            f"- queue_items: `{summary['queue_items']}`",
            f"- queue_blocker_count: `{summary['queue_blocker_count']}`",
            f"- queue_high_count: `{summary['queue_high_count']}`",
            f"- stale_state_count: `{summary['stale_state_count']}`",
            "- Semantik: Process/Review Confidence ist keine Investment Confidence, keine Erfolgswahrscheinlichkeit, keine Alpha-Prognose und keine Order-Freigabe.",
        ]
    )
    return lines


def render_report(
    *,
    validation_rows: list[dict[str, str]],
    queue_rows: list[dict[str, str]],
    summary: Mapping[str, Any],
) -> str:
    lines = [
        "# Decision Journal Validation Report",
        "",
        "## Summary",
        "",
        f"- validation_status: `{summary['validation_status']}`",
        f"- total_decisions: `{summary['total_decisions']}`",
        f"- validation_findings_count: `{summary['validation_findings_count']}`",
        f"- validation_blocker_count: `{summary['validation_blocker_count']}`",
        f"- validation_high_count: `{summary['validation_high_count']}`",
        f"- queue_items: `{summary['queue_items']}`",
        f"- queue_blocker_count: `{summary['queue_blocker_count']}`",
        f"- queue_high_count: `{summary['queue_high_count']}`",
        f"- stale_state_count: `{summary['stale_state_count']}`",
        f"- stale_state_semantics: Decision Quality as_of_date older than the effective as_of_date is stale in the Phase 1.6B MVP (`MAX_DECISION_QUALITY_AGE_DAYS={MAX_DECISION_QUALITY_AGE_DAYS}`).",
        "",
        "## Priority Taxonomy",
        "",
    ]
    lines.extend(f"- {priority}: {description}" for priority, description in PRIORITY_TAXONOMY.items())
    lines.extend(
        [
            "",
            "## Decision Quality Linkage",
            "",
            f"- decision_quality_status: `{summary['decision_quality_status']}`",
            f"- as_of_date: `{summary['decision_quality_as_of_date']}`",
            f"- source_commit_sha: `{summary['decision_quality_source_commit_sha']}`",
            f"- review_required: `{summary['decision_quality_review_required']}`",
            f"- process_confidence_level: `{summary['process_confidence_level']}`",
            "- Process/Review Confidence is not investment confidence, not a success probability, not an alpha forecast and not an order approval.",
            "",
            "## Review Queue",
            "",
        ]
    )
    if queue_rows:
        lines.extend(["| priority | decision_id | symbol | reason_codes | recommended_operator_action |", "| --- | --- | --- | --- | --- |"])
        for row in queue_rows:
            lines.append(
                f"| {row['priority']} | {row['decision_id']} | {row['symbol']} | {row['reason_codes']} | {row['recommended_operator_action']} |"
            )
    else:
        lines.append("- No review queue items.")
    lines.extend(["", "## Validation Findings", ""])
    if validation_rows:
        lines.extend(["| status | decision_id | field | reason_code | message |", "| --- | --- | --- | --- | --- |"])
        for row in validation_rows:
            lines.append(
                f"| {row['validation_status']} | {row['decision_id']} | {row['field_name']} | {row['reason_code']} | {row['message']} |"
            )
    else:
        lines.append("- No journal validation findings.")
    lines.extend(["", "## Non-Scope", ""])
    lines.extend(f"- {note}" for note in NON_SCOPE_NOTES)
    lines.append("")
    return "\n".join(lines)


def write_report(
    path_value: str | Path,
    *,
    validation_rows: list[dict[str, str]],
    queue_rows: list[dict[str, str]],
    summary: Mapping[str, Any],
) -> Path:
    path = ensure_parent_dir(path_value)
    path.write_text(render_report(validation_rows=validation_rows, queue_rows=queue_rows, summary=summary), encoding="utf-8")
    return path


def run_decision_journal_validation(
    *,
    journal: str = DEFAULT_JOURNAL,
    decision_quality_csv: str = DEFAULT_DECISION_QUALITY_CSV,
    decision_quality_json: str = DEFAULT_DECISION_QUALITY_JSON,
    run_manifest: str = DEFAULT_RUN_MANIFEST,
    run_used_inputs: str = DEFAULT_RUN_USED_INPUTS,
    validation_output: str = DEFAULT_VALIDATION_OUTPUT,
    queue_output: str = DEFAULT_QUEUE_OUTPUT,
    report: str | None = None,
    as_of_date: str | None = None,
) -> DecisionJournalValidationResult:
    validation_rows, queue_rows, summary = build_decision_journal_validation(
        journal=journal,
        decision_quality_csv=decision_quality_csv,
        decision_quality_json=decision_quality_json,
        run_manifest=run_manifest,
        run_used_inputs=run_used_inputs,
        as_of_date=as_of_date,
    )
    validation_path = write_validation_csv(validation_rows, validation_output)
    queue_path = write_queue_csv(queue_rows, queue_output)
    report_path = write_report(
        report or DEFAULT_REPORT_PATTERN.format(as_of_date=summary["as_of_date"]),
        validation_rows=validation_rows,
        queue_rows=queue_rows,
        summary=summary,
    )
    return DecisionJournalValidationResult(
        validation_output=validation_path,
        queue_output=queue_path,
        report_output=report_path,
        validation_rows=validation_rows,
        queue_rows=queue_rows,
        summary=dict(summary),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Decision Capture journal rows and build a human review queue.")
    parser.add_argument("--journal", default=DEFAULT_JOURNAL)
    parser.add_argument("--decision-quality-csv", default=DEFAULT_DECISION_QUALITY_CSV)
    parser.add_argument("--decision-quality-json", default=DEFAULT_DECISION_QUALITY_JSON)
    parser.add_argument("--run-manifest", default=DEFAULT_RUN_MANIFEST)
    parser.add_argument("--run-used-inputs", default=DEFAULT_RUN_USED_INPUTS)
    parser.add_argument("--validation-output", default=DEFAULT_VALIDATION_OUTPUT)
    parser.add_argument("--queue-output", default=DEFAULT_QUEUE_OUTPUT)
    parser.add_argument("--report", default=None)
    parser.add_argument("--as-of-date", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_decision_journal_validation(
        journal=args.journal,
        decision_quality_csv=args.decision_quality_csv,
        decision_quality_json=args.decision_quality_json,
        run_manifest=args.run_manifest,
        run_used_inputs=args.run_used_inputs,
        validation_output=args.validation_output,
        queue_output=args.queue_output,
        report=args.report,
        as_of_date=args.as_of_date,
    )
    print(f"validation_output={result.validation_output}")
    print(f"queue_output={result.queue_output}")
    print(f"report_output={result.report_output}")
    print(f"validation_status={result.summary['validation_status']}")
    print(f"queue_items={result.summary['queue_items']}")


if __name__ == "__main__":
    main()
