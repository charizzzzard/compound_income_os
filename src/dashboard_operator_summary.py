from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, resolve_repo_path
from src.personal_decision_journal_validation import NON_SCOPE_NOTES, QUEUE_FIELDS, VALIDATION_FIELDS

DEFAULT_DECISION_QUALITY_STATE = "data/processed/decision_quality_state.json"
DEFAULT_DECISION_JOURNAL_VALIDATION = "data/processed/decision_journal_validation.csv"
DEFAULT_DECISION_REVIEW_QUEUE = "data/processed/decision_review_queue.csv"
DEFAULT_DATA_FRESHNESS_SUMMARY = "data/processed/data_freshness_summary.json"
DEFAULT_RUN_MANIFEST = "data/processed/personal_run_manifest.json"
DEFAULT_RUN_ARTIFACTS = "data/processed/personal_run_artifacts.csv"
DEFAULT_RUN_USED_INPUTS = "data/processed/personal_run_used_inputs.csv"
DEFAULT_OUT_JSON = "data/processed/review_queue_summary.json"

SCHEMA_VERSION = 1
ARTIFACT_STATUS_PRIORITY = ["UNREADABLE", "CONFLICTING", "NOT_AVAILABLE", "PARTIAL", "STALE", "COMPLETE"]
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
UNC_PATH_RE = re.compile(r"^(?:\\\\|//)[^\\/]+[\\/][^\\/]+")


@dataclass(frozen=True)
class DashboardOperatorSummaryResult:
    json_output: Path
    summary: dict[str, Any]


def _repo_root() -> Path:
    return resolve_repo_path(".").resolve()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_external_syntax(raw: str) -> bool:
    return bool(WINDOWS_ABSOLUTE_RE.match(raw) or UNC_PATH_RE.match(raw))


def _safe_path_for_output(path_value: str | Path, label: str) -> tuple[str, bool]:
    raw = str(path_value or "").strip()
    if not raw:
        return "", False
    lowered = raw.replace("\\", "/").lower()
    path = Path(raw)
    if "data/raw/private" in lowered:
        return f"EXTERNAL_PATH_REDACTED:{label}", True
    if _is_external_syntax(raw):
        if path.is_absolute():
            try:
                return path.resolve().relative_to(_repo_root()).as_posix(), False
            except ValueError:
                return f"EXTERNAL_PATH_REDACTED:{label}", True
        return f"EXTERNAL_PATH_REDACTED:{label}", True
    if path.is_absolute():
        try:
            return path.resolve().relative_to(_repo_root()).as_posix(), False
        except ValueError:
            return f"EXTERNAL_PATH_REDACTED:{label}", True
    try:
        return (_repo_root() / raw.replace("\\", "/")).resolve().relative_to(_repo_root()).as_posix(), False
    except ValueError:
        return f"EXTERNAL_PATH_REDACTED:{label}", True


def _sha256_or_none(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv_artifact(path_value: str | Path, *, required: bool, expected_fields: list[str], label: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    display_path, redacted = _safe_path_for_output(path_value, label)
    artifact_path = resolve_repo_path(path_value)
    base = {
        "path": display_path,
        "required": required,
        "status": "NOT_AVAILABLE",
        "row_count": None,
        "sha256": None,
        "reason": None,
    }
    if redacted:
        base.update({"status": "UNREADABLE", "reason": "EXTERNAL_PATH_REDACTED"})
        return [], base
    if not artifact_path.exists():
        base.update({"reason": "MISSING"})
        return [], base
    try:
        with artifact_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            rows = [
                {field: str(row.get(field, "") or "").strip() for field in fields}
                for row in reader
                if any(str(value or "").strip() for value in row.values())
            ]
    except Exception as exc:  # noqa: BLE001 - surfaced as operator artifact status
        base.update({"status": "UNREADABLE", "reason": f"UNREADABLE:{exc}"})
        return [], base
    missing_fields = [field for field in expected_fields if field not in fields]
    if missing_fields:
        base.update({"status": "UNREADABLE", "row_count": len(rows), "sha256": _sha256_or_none(artifact_path), "reason": f"MISSING_COLUMNS:{';'.join(missing_fields)}"})
        return rows, base
    base.update({"status": "COMPLETE", "row_count": len(rows), "sha256": _sha256_or_none(artifact_path)})
    return rows, base


def _read_json_artifact(path_value: str | Path, *, required: bool, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    display_path, redacted = _safe_path_for_output(path_value, label)
    artifact_path = resolve_repo_path(path_value)
    base = {
        "path": display_path,
        "required": required,
        "status": "NOT_AVAILABLE",
        "row_count": None,
        "sha256": None,
        "reason": None,
    }
    if redacted:
        base.update({"status": "UNREADABLE", "reason": "EXTERNAL_PATH_REDACTED"})
        return {}, base
    if not artifact_path.exists():
        base.update({"reason": "MISSING"})
        return {}, base
    try:
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - surfaced as operator artifact status
        base.update({"status": "UNREADABLE", "reason": f"UNREADABLE:{exc}", "sha256": _sha256_or_none(artifact_path)})
        return {}, base
    if not isinstance(data, dict):
        base.update({"status": "UNREADABLE", "reason": "JSON_ROOT_NOT_OBJECT", "sha256": _sha256_or_none(artifact_path)})
        return {}, base
    base.update({"status": "COMPLETE", "row_count": 1, "sha256": _sha256_or_none(artifact_path)})
    return data, base


def _aggregate_artifact_status(artifacts: list[dict[str, Any]]) -> str:
    required = [artifact for artifact in artifacts if artifact["required"]]
    if required and all(artifact["status"] == "NOT_AVAILABLE" for artifact in required):
        return "NOT_AVAILABLE"
    for status in ARTIFACT_STATUS_PRIORITY:
        if status == "NOT_AVAILABLE":
            if any(artifact["required"] and artifact["status"] == "NOT_AVAILABLE" for artifact in artifacts):
                return "PARTIAL"
            continue
        if any(artifact["status"] == status for artifact in artifacts):
            return status
    return "COMPLETE"


def _reason_codes_from_queue(row: dict[str, str]) -> list[str]:
    return [part.strip() for part in str(row.get("reason_codes", "")).split(";") if part.strip()]


def _top_reason_codes(validation_rows: list[dict[str, str]], queue_rows: list[dict[str, str]]) -> list[str]:
    counter: Counter[str] = Counter()
    for row in validation_rows:
        code = str(row.get("reason_code", "")).strip()
        if code:
            counter[code] += 1
    for row in queue_rows:
        counter.update(_reason_codes_from_queue(row))
    return [code for code, _count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))]


def _top_reason_codes_from_freshness(summary: dict[str, Any]) -> list[str]:
    counter: Counter[str] = Counter()
    for item in summary.get("items") or []:
        if not isinstance(item, dict):
            continue
        reason = str(item.get("reason") or "").strip()
        if reason and reason not in {"WITHIN_THRESHOLD", "NOT_APPLICABLE_MISSING_OPTIONAL_ARTIFACT"}:
            counter[reason] += 1
    return [code for code, _count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))]


def _count_reason(queue_rows: list[dict[str, str]], reason_code: str) -> int:
    return sum(1 for row in queue_rows if reason_code in _reason_codes_from_queue(row))


def _priority_count(rows: list[dict[str, str]], priority: str) -> int:
    return sum(1 for row in rows if str(row.get("priority", "")).upper() == priority)


def _attention_level(
    *,
    artifact_status: str,
    validation_rows: list[dict[str, str]],
    queue_rows: list[dict[str, str]],
    decision_quality_review_required: bool = False,
    data_freshness_attention_required: bool = False,
) -> str:
    if artifact_status in {"UNREADABLE", "NOT_AVAILABLE"}:
        return "BLOCKER"
    if artifact_status == "PARTIAL":
        return "HIGH"
    if _priority_count(validation_rows, "BLOCKER") or _priority_count(queue_rows, "BLOCKER"):
        return "BLOCKER"
    if _priority_count(validation_rows, "HIGH") or _priority_count(queue_rows, "HIGH"):
        return "HIGH"
    if _priority_count(validation_rows, "MEDIUM") or _priority_count(queue_rows, "MEDIUM"):
        return "MEDIUM"
    if decision_quality_review_required:
        return "MEDIUM"
    if data_freshness_attention_required:
        return "MEDIUM"
    return "NONE"


def _surface_status(
    *,
    artifact_status: str,
    validation_rows: list[dict[str, str]],
    queue_rows: list[dict[str, str]],
    decision_quality_review_required: bool = False,
    data_freshness_attention_required: bool = False,
) -> str:
    if artifact_status in {"UNREADABLE", "NOT_AVAILABLE"}:
        return "NOT_AVAILABLE"
    if artifact_status == "PARTIAL":
        return "PARTIAL"
    if decision_quality_review_required:
        return "REVIEW"
    if data_freshness_attention_required:
        return "REVIEW"
    if validation_rows or queue_rows:
        return "REVIEW"
    return "PASS"


def _manifest_value(manifest: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = str(manifest.get(key) or "").strip()
        if value:
            return value
    return None


def build_dashboard_operator_summary(
    *,
    decision_quality_state: str = DEFAULT_DECISION_QUALITY_STATE,
    decision_journal_validation: str = DEFAULT_DECISION_JOURNAL_VALIDATION,
    decision_review_queue: str = DEFAULT_DECISION_REVIEW_QUEUE,
    data_freshness_summary: str = DEFAULT_DATA_FRESHNESS_SUMMARY,
    run_manifest: str = DEFAULT_RUN_MANIFEST,
    run_artifacts: str = DEFAULT_RUN_ARTIFACTS,
    run_used_inputs: str = DEFAULT_RUN_USED_INPUTS,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    validation_rows, validation_artifact = _read_csv_artifact(
        decision_journal_validation,
        required=True,
        expected_fields=VALIDATION_FIELDS,
        label="decision_journal_validation",
    )
    queue_rows, queue_artifact = _read_csv_artifact(
        decision_review_queue,
        required=True,
        expected_fields=QUEUE_FIELDS,
        label="decision_review_queue",
    )
    manifest, manifest_artifact = _read_json_artifact(run_manifest, required=False, label="personal_run_manifest")
    expected_stages = set(manifest.get("selected_stages") or []) | set(manifest.get("executed_stage_order") or [])
    data_freshness_expected = "data_freshness" in expected_stages
    decision_quality, decision_quality_artifact = _read_json_artifact(decision_quality_state, required=False, label="decision_quality_state")
    data_freshness, data_freshness_artifact = _read_json_artifact(
        data_freshness_summary,
        required=data_freshness_expected,
        label="data_freshness_summary",
    )
    _artifacts, run_artifacts_artifact = _read_csv_artifact(run_artifacts, required=False, expected_fields=[], label="personal_run_artifacts")
    _used_inputs, run_used_inputs_artifact = _read_csv_artifact(run_used_inputs, required=False, expected_fields=[], label="personal_run_used_inputs")
    source_artifacts = [
        validation_artifact,
        queue_artifact,
        decision_quality_artifact,
        data_freshness_artifact,
        manifest_artifact,
        run_artifacts_artifact,
        run_used_inputs_artifact,
    ]
    artifact_status = _aggregate_artifact_status(source_artifacts)
    top_reasons = _top_reason_codes(validation_rows, queue_rows)
    validation_findings_count = len(validation_rows)
    queue_items = len(queue_rows)
    duplicate_count = sum(1 for row in validation_rows if row.get("reason_code") == "DECISION_ID_DUPLICATE") + _count_reason(queue_rows, "DECISION_ID_DUPLICATE")
    stale_count = sum(1 for row in validation_rows if row.get("reason_code") == "DECISION_QUALITY_STALE") + _count_reason(queue_rows, "DECISION_QUALITY_STALE")
    lineage_count = sum(1 for row in validation_rows if row.get("reason_code") == "DECISION_QUALITY_LINEAGE_MISMATCH") + _count_reason(queue_rows, "DECISION_QUALITY_LINEAGE_MISMATCH")
    missing_required = [artifact["path"] for artifact in source_artifacts if artifact["required"] and artifact["status"] != "COMPLETE"]
    partial_artifacts = [artifact["path"] for artifact in source_artifacts if artifact["status"] not in {"COMPLETE", "NOT_AVAILABLE"}]
    decision_quality_review_required = decision_quality_artifact["status"] == "COMPLETE" and decision_quality.get("review_required") is True
    freshness_counts = data_freshness.get("summary_counts") if data_freshness_artifact["status"] == "COMPLETE" else {}
    freshness_items = data_freshness.get("items") if data_freshness_artifact["status"] == "COMPLETE" else []
    if not isinstance(freshness_counts, dict):
        freshness_counts = {}
    if not isinstance(freshness_items, list):
        freshness_items = []
    data_freshness_review_required = data_freshness_artifact["status"] == "COMPLETE" and data_freshness.get("review_required") is True
    data_freshness_bad_count = sum(int(freshness_counts.get(status, 0) or 0) for status in ("STALE", "MISSING", "UNKNOWN", "REVIEW_REQUIRED"))
    data_freshness_attention_required = bool(data_freshness_review_required or data_freshness_bad_count)
    data_freshness_top_reasons = _top_reason_codes_from_freshness(data_freshness) if data_freshness_artifact["status"] == "COMPLETE" else []
    data_freshness_blocking_dashboard_count = sum(
        1
        for item in freshness_items
        if isinstance(item, dict)
        and item.get("blocks_dashboard") is True
        and item.get("freshness_status") in {"STALE", "MISSING", "UNKNOWN", "REVIEW_REQUIRED"}
    )
    attention_level = _attention_level(
        artifact_status=artifact_status,
        validation_rows=validation_rows,
        queue_rows=queue_rows,
        decision_quality_review_required=decision_quality_review_required,
        data_freshness_attention_required=data_freshness_attention_required,
    )
    surface_status = _surface_status(
        artifact_status=artifact_status,
        validation_rows=validation_rows,
        queue_rows=queue_rows,
        decision_quality_review_required=decision_quality_review_required,
        data_freshness_attention_required=data_freshness_attention_required,
    )
    validation_status = "PASS" if not validation_rows and artifact_status == "COMPLETE" else ("REVIEW" if validation_rows or queue_rows or decision_quality_review_required else surface_status)
    decision_quality_status = "NOT_AVAILABLE"
    if decision_quality_artifact["status"] == "COMPLETE":
        decision_quality_status = "REVIEW" if decision_quality.get("review_required") is True else "PASS"
    generated_at = _utc_now()
    effective_as_of_date = as_of_date or _manifest_value(manifest, "as_of_date", "portfolio_date", "source_snapshot_date") or str(decision_quality.get("as_of_date") or "") or date.today().isoformat()
    attention_reasons = []
    if missing_required:
        attention_reasons.append("REQUIRED_ARTIFACT_NOT_COMPLETE")
    attention_reasons.extend(top_reasons[:5])
    if decision_quality_review_required:
        attention_reasons.append("DECISION_QUALITY_REVIEW_REQUIRED")
    if data_freshness_attention_required:
        attention_reasons.append("DATA_FRESHNESS_REVIEW_REQUIRED")
        attention_reasons.extend(data_freshness_top_reasons[:5])
    attention_reasons = list(dict.fromkeys(attention_reasons))
    return {
        "schema_version": SCHEMA_VERSION,
        "as_of_date": effective_as_of_date,
        "generated_at_utc": generated_at,
        "surface_generated_at": generated_at,
        "run_id": _manifest_value(manifest, "run_id") or _manifest_value(decision_quality, "run_id"),
        "source_commit_sha": _manifest_value(manifest, "source_commit_sha", "git_head", "repo_head", "current_head") or _manifest_value(decision_quality, "source_commit_sha"),
        "surface_status": surface_status,
        "artifact_status": artifact_status,
        "decision_quality_status": decision_quality_status,
        "decision_quality_review_required": decision_quality.get("review_required") if decision_quality_artifact["status"] == "COMPLETE" else None,
        "process_confidence_level": decision_quality.get("decision_confidence_level") if decision_quality_artifact["status"] == "COMPLETE" else None,
        "data_freshness_status": data_freshness.get("overall_status") if data_freshness_artifact["status"] == "COMPLETE" else ("NOT_AVAILABLE" if data_freshness_artifact["status"] == "NOT_AVAILABLE" else data_freshness_artifact["status"]),
        "data_freshness_review_required": data_freshness.get("review_required") if data_freshness_artifact["status"] == "COMPLETE" else None,
        "data_freshness_fresh_count": int(freshness_counts.get("FRESH", 0) or 0),
        "data_freshness_stale_count": int(freshness_counts.get("STALE", 0) or 0),
        "data_freshness_missing_count": int(freshness_counts.get("MISSING", 0) or 0),
        "data_freshness_unknown_count": int(freshness_counts.get("UNKNOWN", 0) or 0),
        "data_freshness_review_required_count": int(freshness_counts.get("REVIEW_REQUIRED", 0) or 0),
        "data_freshness_not_applicable_count": int(freshness_counts.get("NOT_APPLICABLE", 0) or 0),
        "data_freshness_blocking_dashboard_count": data_freshness_blocking_dashboard_count,
        "data_freshness_top_reason_codes": data_freshness_top_reasons,
        "decision_journal_validation_status": validation_status,
        "validation_status": validation_status,
        "validation_findings_count": validation_findings_count,
        "validation_blocker_count": _priority_count(validation_rows, "BLOCKER"),
        "validation_high_count": _priority_count(validation_rows, "HIGH"),
        "validation_medium_count": _priority_count(validation_rows, "MEDIUM"),
        "queue_items": queue_items,
        "queue_blocker_count": _priority_count(queue_rows, "BLOCKER"),
        "queue_high_count": _priority_count(queue_rows, "HIGH"),
        "queue_medium_count": _priority_count(queue_rows, "MEDIUM"),
        "stale_state_count": stale_count,
        "duplicate_decision_id_count": duplicate_count,
        "missing_review_date_count": _count_reason(queue_rows, "REVIEW_DATE_MISSING"),
        "due_review_count": _count_reason(queue_rows, "REVIEW_DATE_DUE"),
        "decision_quality_review_required_count": _count_reason(queue_rows, "DECISION_QUALITY_REVIEW_REQUIRED") + (1 if decision_quality_review_required else 0),
        "lineage_mismatch_count": lineage_count,
        "top_reason_codes": top_reasons,
        "operator_attention_required": attention_level != "NONE",
        "operator_attention_level": attention_level,
        "operator_attention_reasons": attention_reasons,
        "missing_artifacts": missing_required,
        "missing_required_artifacts": missing_required,
        "partial_artifacts": partial_artifacts,
        "source_artifacts": source_artifacts,
        "non_scope_confirmations": NON_SCOPE_NOTES,
    }


def write_dashboard_operator_summary(summary: dict[str, Any], out_json: str | Path = DEFAULT_OUT_JSON) -> Path:
    path = ensure_parent_dir(out_json)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path


def run_dashboard_operator_summary(
    *,
    decision_quality_state: str = DEFAULT_DECISION_QUALITY_STATE,
    decision_journal_validation: str = DEFAULT_DECISION_JOURNAL_VALIDATION,
    decision_review_queue: str = DEFAULT_DECISION_REVIEW_QUEUE,
    data_freshness_summary: str = DEFAULT_DATA_FRESHNESS_SUMMARY,
    run_manifest: str = DEFAULT_RUN_MANIFEST,
    run_artifacts: str = DEFAULT_RUN_ARTIFACTS,
    run_used_inputs: str = DEFAULT_RUN_USED_INPUTS,
    out_json: str = DEFAULT_OUT_JSON,
    as_of_date: str | None = None,
) -> DashboardOperatorSummaryResult:
    summary = build_dashboard_operator_summary(
        decision_quality_state=decision_quality_state,
        decision_journal_validation=decision_journal_validation,
        decision_review_queue=decision_review_queue,
        data_freshness_summary=data_freshness_summary,
        run_manifest=run_manifest,
        run_artifacts=run_artifacts,
        run_used_inputs=run_used_inputs,
        as_of_date=as_of_date,
    )
    output_path = write_dashboard_operator_summary(summary, out_json)
    return DashboardOperatorSummaryResult(json_output=output_path, summary=summary)


def read_dashboard_operator_summary(path_value: str | None) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = resolve_repo_path(path_value)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def build_dashboard_operator_summary_surface_lines(summary: dict[str, Any] | None, *, source_path: str | None = None, include_heading: bool = True) -> list[str]:
    lines: list[str] = []
    if include_heading:
        lines.extend(["## Dashboard Operator Summary", ""])
    if not summary:
        lines.extend(["- Dashboard Operator Summary: `NOT_AVAILABLE`", "- Grund: Summary-Artefakt fehlt, ist nicht lesbar oder die Stage ist nicht gelaufen."])
        return lines
    if source_path:
        lines.append(f"- Summary artifact: `{source_path}`")
    for field in (
        "surface_status",
        "artifact_status",
        "operator_attention_level",
        "operator_attention_required",
        "validation_findings_count",
        "queue_items",
        "queue_blocker_count",
        "queue_high_count",
        "data_freshness_status",
        "data_freshness_review_required",
        "data_freshness_stale_count",
        "data_freshness_missing_count",
        "data_freshness_unknown_count",
    ):
        lines.append(f"- {field}: `{summary.get(field)}`")
    top_reasons = summary.get("top_reason_codes") or []
    missing = summary.get("missing_required_artifacts") or []
    lines.append(f"- top_reason_codes: `{';'.join(str(item) for item in top_reasons) if top_reasons else 'NONE'}`")
    lines.append(f"- missing_required_artifacts: `{';'.join(str(item) for item in missing) if missing else 'NONE'}`")
    lines.append("- Semantik: Operator Attention ist ein Governance-/Hygiene-Signal, keine Order-Freigabe und keine Investment-Confidence.")
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a read-only dashboard operator summary from existing governance artifacts.")
    parser.add_argument("--decision-quality-state", default=DEFAULT_DECISION_QUALITY_STATE)
    parser.add_argument("--decision-journal-validation", default=DEFAULT_DECISION_JOURNAL_VALIDATION)
    parser.add_argument("--decision-review-queue", default=DEFAULT_DECISION_REVIEW_QUEUE)
    parser.add_argument("--data-freshness-summary", default=DEFAULT_DATA_FRESHNESS_SUMMARY)
    parser.add_argument("--run-manifest", default=DEFAULT_RUN_MANIFEST)
    parser.add_argument("--run-artifacts", default=DEFAULT_RUN_ARTIFACTS)
    parser.add_argument("--run-used-inputs", default=DEFAULT_RUN_USED_INPUTS)
    parser.add_argument("--out-json", default=DEFAULT_OUT_JSON)
    parser.add_argument("--as-of-date")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dashboard_operator_summary(
        decision_quality_state=args.decision_quality_state,
        decision_journal_validation=args.decision_journal_validation,
        decision_review_queue=args.decision_review_queue,
        data_freshness_summary=args.data_freshness_summary,
        run_manifest=args.run_manifest,
        run_artifacts=args.run_artifacts,
        run_used_inputs=args.run_used_inputs,
        out_json=args.out_json,
        as_of_date=args.as_of_date,
    )


if __name__ == "__main__":
    main()
