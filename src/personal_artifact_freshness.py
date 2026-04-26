from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_SCORES_INPUT = "data/processed/personal_company_scores.csv"
DEFAULT_EVIDENCE_DELTA_SUMMARY_INPUT = "data/processed/personal_evidence_applied_downstream_delta_summary.csv"
DEFAULT_EVIDENCE_DELTA_HOLDINGS_INPUT = "data/processed/personal_evidence_applied_downstream_delta_holdings.csv"
DEFAULT_KPI_TIER_INPUT = "data/processed/personal_kpi_tier_coverage.csv"
DEFAULT_MISSING_KPI_SUMMARY_INPUT = "data/processed/personal_missing_kpi_closure_summary.csv"
DEFAULT_RUN_USED_INPUTS_INPUT = "data/processed/personal_run_used_inputs.csv"
DEFAULT_RUN_MANIFEST_INPUT = "data/processed/personal_run_manifest.json"
DEFAULT_CHECKS_OUTPUT = "data/processed/personal_artifact_freshness_checks.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_artifact_freshness_summary.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_artifact_freshness_report.md"

STATUS_KEYS = ("OK", "REVIEW", "MISSING_DATA", "BLOCKED")
CHECK_FIELDS = [
    "check_id",
    "artifact_label",
    "compared_to",
    "artifact_path",
    "artifact_exists",
    "artifact_rows_total",
    "artifact_freshness_status",
    "artifact_drift_status",
    "reason_codes",
    "observed_value",
    "expected_value",
    "metadata_status",
    "run_id",
    "generated_at",
    "source_mode",
    "input_lineage",
    "recommended_next_action",
]
SUMMARY_FIELDS = ["metric", "value", "notes"]


@dataclass(frozen=True)
class ArtifactSnapshot:
    label: str
    path: str
    exists: bool
    rows: list[dict[str, str]]
    rows_total: int
    metadata: dict[str, str]
    metadata_status: str


@dataclass(frozen=True)
class ArtifactFreshnessResult:
    checks_output: Path
    summary_output: Path
    report_output: Path
    check_rows: list[dict[str, str]]
    summary_rows: list[dict[str, str]]
    warnings: tuple[str, ...]


def safe_display_path(path_value: str) -> str:
    normalized = str(path_value).replace("\\", "/")
    if "data/raw/private" in normalized:
        return "<private_path>"
    return path_value


def optional_csv_rows(path_value: str, label: str) -> tuple[list[dict[str, str]], list[str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], [f"missing_artifact={label}:{safe_display_path(path_value)}"]
    return read_csv_rows(path), []


def optional_json(path_value: str, label: str) -> tuple[dict[str, Any], list[str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return {}, [f"missing_artifact={label}:{safe_display_path(path_value)}"]
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle), []


def summary_map(rows: list[dict[str, str]]) -> dict[str, str]:
    return {str(row.get("metric", "") or "").strip(): str(row.get("value", "") or "").strip() for row in rows}


def int_value(value: Any) -> int:
    try:
        return int(str(value or "0").strip())
    except ValueError:
        return 0


def count_upper(rows: list[dict[str, str]], column: str) -> Counter[str]:
    return Counter(safe_upper(row.get(column, "")) or "BLANK" for row in rows)


def bool_text(value: bool) -> str:
    return "True" if value else "False"


def joined_reasons(reasons: set[str] | list[str] | tuple[str, ...]) -> str:
    return ";".join(sorted(reason for reason in reasons if reason))


def run_git_tracked(path_value: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", path_value],
            cwd=resolve_repo_path("."),
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.returncode == 0


def extract_metadata(rows: list[dict[str, str]], *, manifest: dict[str, Any] | None = None) -> tuple[dict[str, str], str]:
    metadata: dict[str, str] = {}
    if rows:
        first = rows[0]
        for key in ("run_id", "generated_at", "source_mode", "fundamentals_source_mode", "input_path", "upstream_artifact", "manifest_reference"):
            if first.get(key):
                metadata[key] = str(first.get(key, "")).strip()
    metrics = summary_map(rows)
    for metric_key, metadata_key in (
        ("run_id", "run_id"),
        ("generated_at", "generated_at"),
        ("source_mode", "source_mode"),
        ("fundamentals_source_mode", "source_mode"),
        ("scoring_fundamentals_source_mode", "source_mode"),
        ("scoring_fundamentals_master_path", "input_lineage"),
    ):
        if metrics.get(metric_key):
            metadata[metadata_key] = metrics[metric_key]
    if manifest:
        if manifest.get("run_id"):
            metadata.setdefault("run_id", str(manifest.get("run_id")))
        if manifest.get("run_finished_at"):
            metadata.setdefault("generated_at", str(manifest.get("run_finished_at")))
    has_comparable = bool(metadata.get("run_id") and metadata.get("generated_at"))
    if has_comparable:
        return metadata, "PRESENT"
    if metadata:
        return metadata, "PARTIAL_METADATA"
    return metadata, "MISSING_METADATA"


def artifact_snapshot(path_value: str, label: str, *, manifest: dict[str, Any] | None = None) -> tuple[ArtifactSnapshot, list[str]]:
    rows, warnings = optional_csv_rows(path_value, label)
    exists = resolve_repo_path(path_value).exists()
    metadata, metadata_status = extract_metadata(rows, manifest=manifest)
    if not exists:
        metadata_status = "MISSING"
    return (
        ArtifactSnapshot(
            label=label,
            path=path_value,
            exists=exists,
            rows=rows,
            rows_total=len(rows),
            metadata=metadata,
            metadata_status=metadata_status,
        ),
        warnings,
    )


def score_counts_from_scores(rows: list[dict[str, str]]) -> dict[str, int]:
    counts = count_upper(rows, "data_quality_flag")
    return {key: int(counts.get(key, 0)) for key in STATUS_KEYS}


def score_counts_from_summary(rows: list[dict[str, str]]) -> dict[str, int] | None:
    metrics = summary_map(rows)
    if not any(f"score_data_quality__{key}" in metrics for key in STATUS_KEYS):
        return None
    return {key: int_value(metrics.get(f"score_data_quality__{key}")) for key in STATUS_KEYS}


def compare_score_delta(
    *,
    scores: ArtifactSnapshot,
    delta_summary: ArtifactSnapshot,
    deferred_labels: set[str],
) -> dict[str, str]:
    reasons: set[str] = set()
    if not scores.exists or not delta_summary.exists:
        missing = scores if not scores.exists else delta_summary
        return {
            "check_id": "score_vs_evidence_delta_status_counters",
            "artifact_label": delta_summary.label,
            "compared_to": scores.label,
            "artifact_path": safe_display_path(delta_summary.path),
            "artifact_exists": bool_text(delta_summary.exists),
            "artifact_rows_total": str(delta_summary.rows_total),
            "artifact_freshness_status": "MISSING",
            "artifact_drift_status": "NOT_AVAILABLE",
            "reason_codes": "MISSING_ARTIFACT",
            "observed_value": f"missing={missing.label}",
            "expected_value": "Both score and derived delta artifacts exist.",
            "metadata_status": delta_summary.metadata_status,
            "run_id": delta_summary.metadata.get("run_id", ""),
            "generated_at": delta_summary.metadata.get("generated_at", ""),
            "source_mode": delta_summary.metadata.get("source_mode", ""),
            "input_lineage": delta_summary.metadata.get("input_lineage", ""),
            "recommended_next_action": "Generate missing artifact before freshness reconciliation.",
        }

    score_counts = score_counts_from_scores(scores.rows)
    delta_counts = score_counts_from_summary(delta_summary.rows)
    if delta_counts is None:
        return {
            "check_id": "score_vs_evidence_delta_status_counters",
            "artifact_label": delta_summary.label,
            "compared_to": scores.label,
            "artifact_path": safe_display_path(delta_summary.path),
            "artifact_exists": "True",
            "artifact_rows_total": str(delta_summary.rows_total),
            "artifact_freshness_status": "UNKNOWN",
            "artifact_drift_status": "REVIEW",
            "reason_codes": "STATUS_COUNTER_UNAVAILABLE",
            "observed_value": f"scores={score_counts}; delta=NOT_AVAILABLE",
            "expected_value": "Comparable score_data_quality counters in both artifacts.",
            "metadata_status": delta_summary.metadata_status,
            "run_id": delta_summary.metadata.get("run_id", ""),
            "generated_at": delta_summary.metadata.get("generated_at", ""),
            "source_mode": delta_summary.metadata.get("source_mode", ""),
            "input_lineage": delta_summary.metadata.get("input_lineage", ""),
            "recommended_next_action": "Regenerate or extend derived summary with status counters.",
        }
    mismatch = score_counts != delta_counts
    if not mismatch:
        freshness = "FRESH" if scores.metadata_status == "PRESENT" and delta_summary.metadata_status == "PRESENT" else "MISSING_METADATA"
        reason = "COUNTER_MATCH" if freshness == "FRESH" else "COUNTER_MATCH;MISSING_METADATA"
        return {
            "check_id": "score_vs_evidence_delta_status_counters",
            "artifact_label": delta_summary.label,
            "compared_to": scores.label,
            "artifact_path": safe_display_path(delta_summary.path),
            "artifact_exists": "True",
            "artifact_rows_total": str(delta_summary.rows_total),
            "artifact_freshness_status": freshness,
            "artifact_drift_status": "PASS",
            "reason_codes": reason,
            "observed_value": f"scores={score_counts}; delta={delta_counts}",
            "expected_value": "Score CSV counters match evidence-applied delta summary counters.",
            "metadata_status": delta_summary.metadata_status,
            "run_id": delta_summary.metadata.get("run_id", ""),
            "generated_at": delta_summary.metadata.get("generated_at", ""),
            "source_mode": delta_summary.metadata.get("source_mode", ""),
            "input_lineage": delta_summary.metadata.get("input_lineage", ""),
            "recommended_next_action": "No action.",
        }

    if delta_summary.label in deferred_labels:
        freshness_status = "DEFERRED"
        drift_status = "REVIEW"
        reasons.add("DERIVED_ARTIFACT_DEFERRED")
    elif scores.metadata_status != "PRESENT" or delta_summary.metadata_status != "PRESENT":
        freshness_status = "MISSING_METADATA"
        drift_status = "REVIEW"
        reasons.add("MISSING_METADATA")
        reasons.add("STALE_DERIVED_ARTIFACT")
    elif scores.metadata.get("run_id") != delta_summary.metadata.get("run_id"):
        freshness_status = "STALE"
        drift_status = "REVIEW"
        reasons.add("RUN_ID_MISMATCH")
    elif scores.metadata.get("source_mode") and delta_summary.metadata.get("source_mode") and scores.metadata.get("source_mode") != delta_summary.metadata.get("source_mode"):
        freshness_status = "INCONSISTENT"
        drift_status = "BLOCKED"
        reasons.add("SOURCE_MODE_MISMATCH")
        reasons.add("COUNTER_MISMATCH")
    else:
        freshness_status = "INCONSISTENT"
        drift_status = "BLOCKED"
        reasons.add("COUNTER_MISMATCH")

    return {
        "check_id": "score_vs_evidence_delta_status_counters",
        "artifact_label": delta_summary.label,
        "compared_to": scores.label,
        "artifact_path": safe_display_path(delta_summary.path),
        "artifact_exists": "True",
        "artifact_rows_total": str(delta_summary.rows_total),
        "artifact_freshness_status": freshness_status,
        "artifact_drift_status": drift_status,
        "reason_codes": joined_reasons(reasons),
        "observed_value": f"scores={score_counts}; delta={delta_counts}",
        "expected_value": "Score CSV counters match evidence-applied delta summary counters when artifacts are comparable.",
        "metadata_status": delta_summary.metadata_status,
        "run_id": delta_summary.metadata.get("run_id", ""),
        "generated_at": delta_summary.metadata.get("generated_at", ""),
        "source_mode": delta_summary.metadata.get("source_mode", ""),
        "input_lineage": delta_summary.metadata.get("input_lineage", ""),
        "recommended_next_action": "Regenerate derived delta with comparable run metadata, or keep it marked stale/deferred.",
    }


def inventory_row(snapshot: ArtifactSnapshot) -> dict[str, str]:
    status = "MISSING" if not snapshot.exists else ("MISSING_METADATA" if snapshot.metadata_status != "PRESENT" else "FRESH")
    drift_status = "NOT_AVAILABLE" if not snapshot.exists else ("REVIEW" if snapshot.metadata_status != "PRESENT" else "PASS")
    reason = "MISSING_ARTIFACT" if not snapshot.exists else ("MISSING_METADATA" if snapshot.metadata_status != "PRESENT" else "COUNTER_MATCH")
    return {
        "check_id": f"metadata_inventory__{snapshot.label}",
        "artifact_label": snapshot.label,
        "compared_to": "",
        "artifact_path": safe_display_path(snapshot.path),
        "artifact_exists": bool_text(snapshot.exists),
        "artifact_rows_total": str(snapshot.rows_total),
        "artifact_freshness_status": status,
        "artifact_drift_status": drift_status,
        "reason_codes": reason,
        "observed_value": f"metadata_status={snapshot.metadata_status}",
        "expected_value": "Artifact exists with comparable run_id and generated_at metadata.",
        "metadata_status": snapshot.metadata_status,
        "run_id": snapshot.metadata.get("run_id", ""),
        "generated_at": snapshot.metadata.get("generated_at", ""),
        "source_mode": snapshot.metadata.get("source_mode", ""),
        "input_lineage": snapshot.metadata.get("input_lineage", ""),
        "recommended_next_action": "Add explicit run metadata to derived artifact contracts." if snapshot.exists and snapshot.metadata_status != "PRESENT" else "No action.",
    }


def build_summary(check_rows: list[dict[str, str]], warnings: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    freshness_counts = Counter(row["artifact_freshness_status"] for row in check_rows)
    drift_counts = Counter(row["artifact_drift_status"] for row in check_rows)
    reasons = {
        reason
        for row in check_rows
        for reason in row["reason_codes"].split(";")
        if reason
    }
    unresolved = [
        row
        for row in check_rows
        if row["check_id"] == "score_vs_evidence_delta_status_counters"
        and row["artifact_drift_status"] == "BLOCKED"
        and "COUNTER_MISMATCH" in row["reason_codes"].split(";")
    ]

    def add(metric: str, value: Any, notes: str) -> None:
        rows.append({"metric": metric, "value": str(value), "notes": notes})

    add("freshness_checks_total", len(check_rows), "Rows in personal_artifact_freshness_checks.csv.")
    add("unresolved_current_artifact_drift_total", len(unresolved), "Current unexplained counter mismatches with comparable metadata.")
    add("artifact_drift_active", bool_text(bool(unresolved)), "True only for current unexplained drift.")
    add("artifact_drift_explained_by_metadata", bool_text("MISSING_METADATA" in reasons or "STALE_DERIVED_ARTIFACT" in reasons), "Counter mismatch explained by missing/stale metadata.")
    add("freshness_reason_codes", joined_reasons(reasons), "Union of freshness reason codes.")
    for status, count in sorted(freshness_counts.items()):
        add(f"artifact_freshness_status__{status}", count, "Artifact freshness status count.")
    for status, count in sorted(drift_counts.items()):
        add(f"artifact_drift_status__{status}", count, "Artifact drift status count.")
    add("warnings_total", len(warnings), "Missing input warnings.")
    return sorted(rows, key=lambda row: row["metric"])


def render_report(check_rows: list[dict[str, str]], summary_rows: list[dict[str, str]], input_paths: dict[str, str]) -> str:
    summary = summary_map(summary_rows)
    lines = [
        "# Personal Artifact Freshness Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## 1. Executive Summary",
        "",
        f"- Artifact drift active: `{summary.get('artifact_drift_active', 'False')}`",
        f"- Unresolved current artifact drift total: `{summary.get('unresolved_current_artifact_drift_total', '0')}`",
        f"- Reason codes: `{summary.get('freshness_reason_codes', '') or 'none'}`",
        "",
        "This report classifies artifact freshness and drift from existing processed artifacts only. It does not change scores, formulas, fundamentals values, watchlist values, or ranking outputs.",
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
            "## 3. Artifact Metadata Inventory",
            "",
            "| Artifact | Exists | Rows | Metadata | Freshness | Reasons |",
            "| --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for row in check_rows:
        if row["check_id"].startswith("metadata_inventory__"):
            lines.append(
                f"| `{row['artifact_label']}` | `{row['artifact_exists']}` | {row['artifact_rows_total']} | `{row['metadata_status']}` | `{row['artifact_freshness_status']}` | `{row['reason_codes']}` |"
            )
    lines.extend(
        [
            "",
            "## 4. Status Counter Comparison",
            "",
            "| Check | Drift Status | Freshness | Reasons | Observed |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in check_rows:
        if row["check_id"] == "score_vs_evidence_delta_status_counters":
            lines.append(
                f"| `{row['check_id']}` | `{row['artifact_drift_status']}` | `{row['artifact_freshness_status']}` | `{row['reason_codes']}` | `{row['observed_value']}` |"
            )
    lines.extend(
        [
            "",
            "## 5. Freshness Findings",
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
            "## 6. Drift Findings",
            "",
            "- Counter mismatches are treated as current `ARTIFACT_DRIFT` only when both artifacts have comparable metadata and the mismatch is not otherwise explained.",
            "- In the current repository state, the score-vs-delta mismatch is classified through missing/stale metadata rather than accepted as current truth.",
            "",
            "## 7. Resolved vs Unresolved Drift",
            "",
            f"- Current unexplained drift: `{summary.get('unresolved_current_artifact_drift_total', '0')}`",
            f"- Drift explained by metadata/staleness: `{summary.get('artifact_drift_explained_by_metadata', 'False')}`",
            "",
            "## 8. Reconciliation Impact",
            "",
            "Reconciliation can consume `personal_artifact_freshness_summary.csv` to replace broad `ARTIFACT_DRIFT` with precise freshness blockers such as `MISSING_METADATA`, `STALE_ARTIFACT`, or `DERIVED_ARTIFACT_DEFERRED`.",
            "",
            "## 9. Remaining Demo Readiness Blockers",
            "",
            "- Watchlist sample input, valuation-required gaps, core-data review states, dividend/FCF gaps, and provenance gaps remain outside this patch.",
            "",
            "## 10. Remaining Decision Readiness Blockers",
            "",
            "- Decision readiness remains blocked until valuation, dividend/FCF, core data, provenance, and reviewed watchlist inputs are resolved.",
            "",
            "## 11. Recommended Next Patch",
            "",
            "`PATCH / VALUATION INPUT CONTRACT / REVIEWED MANUAL EVIDENCE / NO IMPUTATION`",
        ]
    )
    return "\n".join(lines) + "\n"


def run_personal_artifact_freshness(
    *,
    scores_input: str = DEFAULT_SCORES_INPUT,
    evidence_delta_summary_input: str = DEFAULT_EVIDENCE_DELTA_SUMMARY_INPUT,
    evidence_delta_holdings_input: str = DEFAULT_EVIDENCE_DELTA_HOLDINGS_INPUT,
    kpi_tier_input: str = DEFAULT_KPI_TIER_INPUT,
    missing_kpi_summary_input: str = DEFAULT_MISSING_KPI_SUMMARY_INPUT,
    run_used_inputs_input: str = DEFAULT_RUN_USED_INPUTS_INPUT,
    run_manifest_input: str = DEFAULT_RUN_MANIFEST_INPUT,
    checks_output: str = DEFAULT_CHECKS_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
    deferred_artifact_labels: set[str] | None = None,
) -> ArtifactFreshnessResult:
    deferred_labels = set(deferred_artifact_labels or set())
    warnings: list[str] = []
    manifest, manifest_warnings = optional_json(run_manifest_input, "run_manifest")
    warnings.extend(manifest_warnings)
    snapshots: dict[str, ArtifactSnapshot] = {}
    input_paths = {
        "scores": scores_input,
        "evidence_delta_summary": evidence_delta_summary_input,
        "evidence_delta_holdings": evidence_delta_holdings_input,
        "kpi_tier": kpi_tier_input,
        "missing_kpi_summary": missing_kpi_summary_input,
        "run_used_inputs": run_used_inputs_input,
        "run_manifest": run_manifest_input,
    }
    for label, path in input_paths.items():
        if label == "run_manifest":
            continue
        snapshot, snapshot_warnings = artifact_snapshot(path, label, manifest=manifest if label == "scores" else None)
        snapshots[label] = snapshot
        warnings.extend(snapshot_warnings)

    check_rows = [
        compare_score_delta(
            scores=snapshots["scores"],
            delta_summary=snapshots["evidence_delta_summary"],
            deferred_labels=deferred_labels,
        )
    ]
    for label in ("scores", "evidence_delta_summary", "evidence_delta_holdings", "kpi_tier", "missing_kpi_summary", "run_used_inputs"):
        check_rows.append(inventory_row(snapshots[label]))
    check_rows = sorted(check_rows, key=lambda row: row["check_id"])
    summary_rows = build_summary(check_rows, warnings)
    checks_path = write_csv_rows(checks_output, CHECK_FIELDS, check_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(check_rows, summary_rows, input_paths), encoding="utf-8")
    return ArtifactFreshnessResult(
        checks_output=checks_path,
        summary_output=summary_path,
        report_output=report_path,
        check_rows=check_rows,
        summary_rows=summary_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify processed artifact freshness and drift without changing values.")
    parser.add_argument("--scores-input", default=DEFAULT_SCORES_INPUT)
    parser.add_argument("--evidence-delta-summary-input", default=DEFAULT_EVIDENCE_DELTA_SUMMARY_INPUT)
    parser.add_argument("--evidence-delta-holdings-input", default=DEFAULT_EVIDENCE_DELTA_HOLDINGS_INPUT)
    parser.add_argument("--kpi-tier-input", default=DEFAULT_KPI_TIER_INPUT)
    parser.add_argument("--missing-kpi-summary-input", default=DEFAULT_MISSING_KPI_SUMMARY_INPUT)
    parser.add_argument("--run-used-inputs-input", default=DEFAULT_RUN_USED_INPUTS_INPUT)
    parser.add_argument("--run-manifest-input", default=DEFAULT_RUN_MANIFEST_INPUT)
    parser.add_argument("--checks-output", default=DEFAULT_CHECKS_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--deferred-artifact-label", action="append", default=[])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_artifact_freshness(
        scores_input=args.scores_input,
        evidence_delta_summary_input=args.evidence_delta_summary_input,
        evidence_delta_holdings_input=args.evidence_delta_holdings_input,
        kpi_tier_input=args.kpi_tier_input,
        missing_kpi_summary_input=args.missing_kpi_summary_input,
        run_used_inputs_input=args.run_used_inputs_input,
        run_manifest_input=args.run_manifest_input,
        checks_output=args.checks_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
        deferred_artifact_labels=set(args.deferred_artifact_label),
    )
    summary = summary_map(result.summary_rows)
    print(f"checks_output={result.checks_output}")
    print(f"summary_output={result.summary_output}")
    print(f"report_output={result.report_output}")
    print(f"artifact_drift_active={summary.get('artifact_drift_active', 'False')}")
    print(f"unresolved_current_artifact_drift_total={summary.get('unresolved_current_artifact_drift_total', '0')}")
    print(f"warnings_total={len(result.warnings)}")


if __name__ == "__main__":
    main()
