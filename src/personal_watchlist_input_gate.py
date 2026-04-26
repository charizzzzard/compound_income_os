from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_USED_INPUTS_INPUT = "data/processed/personal_run_used_inputs.csv"
DEFAULT_WATCHLIST_INPUT = "data/processed/personal_watchlist_ranked.csv"
DEFAULT_GATE_OUTPUT = "data/processed/personal_watchlist_input_gate.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_watchlist_input_gate_summary.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_watchlist_input_gate_report.md"

GATE_FIELDS = [
    "watchlist_input_path",
    "watchlist_input_exists",
    "watchlist_input_status",
    "watchlist_data_status",
    "watchlist_readiness_status",
    "watchlist_rows_total",
    "status_counts",
    "data_quality_counts",
    "reason_codes",
    "recommended_next_action",
]
SUMMARY_FIELDS = ["metric", "value", "notes"]


@dataclass(frozen=True)
class WatchlistInputGateResult:
    gate_output: Path
    summary_output: Path
    report_output: Path
    gate_rows: list[dict[str, str]]
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
        return [], [f"missing_input={label}:{safe_display_path(path_value)}"]
    return read_csv_rows(path), []


def normalize_path(path_value: str) -> str:
    return str(path_value or "").strip().replace("\\", "/")


def bool_text(value: bool) -> str:
    return "True" if value else "False"


def joined_reasons(reasons: set[str]) -> str:
    return ";".join(sorted(reason for reason in reasons if reason))


def find_watchlist_input(used_input_rows: list[dict[str, str]]) -> tuple[str, str, str]:
    for row in used_input_rows:
        if str(row.get("input_role", "") or "").strip() == "watchlist_input":
            return (
                normalize_path(row.get("input_path", "")),
                str(row.get("input_exists", "") or "").strip(),
                str(row.get("notes", "") or "").strip(),
            )
    return "", "", ""


def is_reviewed_watchlist_input(path_value: str, notes: str) -> bool:
    marker_text = f"{path_value} {notes}".lower()
    return any(marker in marker_text for marker in ("reviewed", "approved", "personal_watchlist_review"))


def classify_data_status(watchlist_rows: list[dict[str, str]]) -> tuple[str, set[str], Counter[str], Counter[str]]:
    if not watchlist_rows:
        return "NOT_AVAILABLE", {"WATCHLIST_ROWS_MISSING"}, Counter(), Counter()

    status_counts = Counter(safe_upper(row.get("status", "")) or "BLANK" for row in watchlist_rows)
    quality_counts = Counter(safe_upper(row.get("data_quality_flag", "")) or "BLANK" for row in watchlist_rows)
    reasons: set[str] = set()

    if "BLANK" in status_counts and len(status_counts) == 1:
        reasons.add("WATCHLIST_STATUS_MISSING")
        return "NOT_AVAILABLE", reasons, status_counts, quality_counts

    weak_statuses = {"REVIEW", "MISSING_DATA", "BLOCKED"}
    weak_quality = {"REVIEW", "MISSING_DATA", "BLOCKED"}
    all_status_weak = sum(status_counts.get(status, 0) for status in weak_statuses) == len(watchlist_rows)
    all_quality_weak = sum(quality_counts.get(status, 0) for status in weak_quality) == len(watchlist_rows)
    if all_status_weak or all_quality_weak:
        reasons.add("WATCHLIST_REVIEW_OR_MISSING_DATA")
        if quality_counts.get("MISSING_DATA", 0) == len(watchlist_rows):
            return "MISSING_DATA", reasons, status_counts, quality_counts
        return "REVIEW", reasons, status_counts, quality_counts

    if any(status_counts.get(status, 0) for status in weak_statuses) or any(quality_counts.get(status, 0) for status in weak_quality):
        reasons.add("WATCHLIST_REVIEW_OR_MISSING_DATA")
        return "PARTIAL", reasons, status_counts, quality_counts

    return "OK", reasons, status_counts, quality_counts


def classify_gate(used_input_rows: list[dict[str, str]], watchlist_rows: list[dict[str, str]], warnings: list[str]) -> dict[str, str]:
    watchlist_input_path, input_exists, notes = find_watchlist_input(used_input_rows)
    reasons: set[str] = set()
    input_status = "UNKNOWN"

    data_status, data_reasons, status_counts, quality_counts = classify_data_status(watchlist_rows)
    reasons.update(data_reasons)

    if any(warning.startswith("missing_input=watchlist:") for warning in warnings):
        input_status = "NOT_AVAILABLE"
        readiness = "NOT_AVAILABLE"
        reasons.add("WATCHLIST_ARTIFACT_MISSING")
    elif not watchlist_input_path:
        input_status = "MISSING"
        readiness = "NOT_AVAILABLE"
        reasons.add("WATCHLIST_INPUT_MISSING")
    elif watchlist_input_path == "data/raw/sample_watchlist.csv":
        input_status = "SAMPLE_DEMO_ONLY"
        readiness = "BLOCKED"
        reasons.add("WATCHLIST_SAMPLE_INPUT")
    elif is_reviewed_watchlist_input(watchlist_input_path, notes):
        input_status = "PERSONAL_REVIEWED"
        readiness = "PASS" if data_status == "OK" else ("BLOCKED" if data_status == "MISSING_DATA" else "REVIEW")
        reasons.add("WATCHLIST_PERSONAL_REVIEWED")
    else:
        input_status = "PERSONAL_UNREVIEWED"
        readiness = "REVIEW"
        reasons.add("WATCHLIST_PERSONAL_UNREVIEWED")

    if data_status == "NOT_AVAILABLE" and readiness == "PASS":
        readiness = "NOT_AVAILABLE"

    action = "No action."
    if "WATCHLIST_SAMPLE_INPUT" in reasons:
        action = "Use a reviewed personal watchlist input or keep outputs explicitly demo-only."
    elif "WATCHLIST_ARTIFACT_MISSING" in reasons or "WATCHLIST_INPUT_MISSING" in reasons:
        action = "Generate watchlist artifacts from an explicit reviewed input."
    elif "WATCHLIST_PERSONAL_UNREVIEWED" in reasons:
        action = "Add an explicit reviewed watchlist input marker before decision use."
    elif "WATCHLIST_REVIEW_OR_MISSING_DATA" in reasons:
        action = "Resolve watchlist review/data-quality gaps or keep readiness blocked."

    return {
        "watchlist_input_path": safe_display_path(watchlist_input_path or "NOT_AVAILABLE"),
        "watchlist_input_exists": input_exists or bool_text(bool(watchlist_input_path)),
        "watchlist_input_status": input_status,
        "watchlist_data_status": data_status,
        "watchlist_readiness_status": readiness,
        "watchlist_rows_total": str(len(watchlist_rows)),
        "status_counts": ";".join(f"{key}={value}" for key, value in sorted(status_counts.items())),
        "data_quality_counts": ";".join(f"{key}={value}" for key, value in sorted(quality_counts.items())),
        "reason_codes": joined_reasons(reasons),
        "recommended_next_action": action,
    }


def build_summary(gate_row: dict[str, str], warnings: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(metric: str, value: Any, notes: str) -> None:
        rows.append({"metric": metric, "value": str(value), "notes": notes})

    add("watchlist_input_path", gate_row["watchlist_input_path"], "Observed watchlist input path, private paths masked.")
    add("watchlist_input_status", gate_row["watchlist_input_status"], "Classified input status.")
    add("watchlist_data_status", gate_row["watchlist_data_status"], "Classified watchlist row data status.")
    add("watchlist_readiness_status", gate_row["watchlist_readiness_status"], "Conservative watchlist readiness status.")
    add("watchlist_rows_total", gate_row["watchlist_rows_total"], "Rows in watchlist artifact.")
    add("watchlist_reason_codes", gate_row["reason_codes"], "Machine-readable reason codes.")
    add("watchlist_sample_input_active", bool_text("WATCHLIST_SAMPLE_INPUT" in gate_row["reason_codes"].split(";")), "True when sample watchlist input is active.")
    add("watchlist_review_or_missing_data_active", bool_text("WATCHLIST_REVIEW_OR_MISSING_DATA" in gate_row["reason_codes"].split(";")), "True when watchlist rows are all/partly REVIEW or MISSING_DATA.")
    add("warnings_total", len(warnings), "Missing input warnings.")
    return sorted(rows, key=lambda row: row["metric"])


def summary_map(rows: list[dict[str, str]]) -> dict[str, str]:
    return {row["metric"]: row["value"] for row in rows}


def render_report(
    *,
    used_inputs_input: str,
    watchlist_input: str,
    gate_output: str,
    summary_output: str,
    gate_row: dict[str, str],
    summary_rows: list[dict[str, str]],
    warnings: tuple[str, ...],
) -> str:
    summary = summary_map(summary_rows)
    lines = [
        "# Personal Watchlist Input Gate Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## 1. Executive Summary",
        "",
        f"- Watchlist input status: `{summary.get('watchlist_input_status', 'NOT_AVAILABLE')}`",
        f"- Watchlist data status: `{summary.get('watchlist_data_status', 'NOT_AVAILABLE')}`",
        f"- Watchlist readiness status: `{summary.get('watchlist_readiness_status', 'NOT_AVAILABLE')}`",
        f"- Reason codes: `{summary.get('watchlist_reason_codes', '') or 'none'}`",
        "",
        "This gate reads existing artifacts only. It does not change watchlist rows, scores, rankings, fundamentals values, or monthly outputs.",
        "",
        "## 2. Input Artifacts",
        "",
        f"- Used inputs: `{safe_display_path(used_inputs_input)}`",
        f"- Watchlist artifact: `{safe_display_path(watchlist_input)}`",
        f"- Gate output: `{safe_display_path(gate_output)}`",
        f"- Summary output: `{safe_display_path(summary_output)}`",
        "",
        "## 3. Watchlist Input Source",
        "",
        f"- Input path: `{gate_row['watchlist_input_path']}`",
        f"- Input exists: `{gate_row['watchlist_input_exists']}`",
        f"- Input status: `{gate_row['watchlist_input_status']}`",
        "",
        "## 4. Watchlist Row Status Summary",
        "",
        f"- Rows: `{gate_row['watchlist_rows_total']}`",
        f"- Status counts: `{gate_row['status_counts'] or 'none'}`",
        f"- Data-quality counts: `{gate_row['data_quality_counts'] or 'none'}`",
        "",
        "## 5. Watchlist Input Gate Result",
        "",
        f"- Data status: `{gate_row['watchlist_data_status']}`",
        f"- Readiness status: `{gate_row['watchlist_readiness_status']}`",
        f"- Reasons: `{gate_row['reason_codes'] or 'none'}`",
        f"- Next action: {gate_row['recommended_next_action']}",
        "",
        "## 6. Demo Readiness Impact",
        "",
        "Sample watchlist input keeps demo readiness blocked unless explicitly labeled as demo-only. Current gate status remains conservative.",
        "",
        "## 7. Decision Readiness Impact",
        "",
        "A sample or unreviewed watchlist is not decision-ready. REVIEW and MISSING_DATA rows remain visible and blocked from decision-quality interpretation.",
        "",
        "## 8. Reconciliation Impact",
        "",
        "Reconciliation can consume `personal_watchlist_input_gate_summary.csv` to report precise watchlist reason codes instead of relying only on inline heuristics.",
        "",
        "## 9. Remaining Blockers",
        "",
        "- Artifact drift, valuation-required data gaps, dividend/FCF gaps, core-data review states, and provenance gaps remain outside this watchlist gate patch.",
        "",
        "## 10. Recommended Next Patch",
        "",
        "`PATCH / RECONCILIATION FRESHNESS + ARTIFACT DRIFT RESOLUTION / NO VALUE CHANGES`",
    ]
    if warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in warnings:
            lines.append(f"- `{warning}`")
    return "\n".join(lines) + "\n"


def run_personal_watchlist_input_gate(
    *,
    used_inputs_input: str = DEFAULT_USED_INPUTS_INPUT,
    watchlist_input: str = DEFAULT_WATCHLIST_INPUT,
    gate_output: str = DEFAULT_GATE_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> WatchlistInputGateResult:
    warnings: list[str] = []
    used_input_rows, used_warnings = optional_csv_rows(used_inputs_input, "used_inputs")
    watchlist_rows, watchlist_warnings = optional_csv_rows(watchlist_input, "watchlist")
    warnings.extend(used_warnings)
    warnings.extend(watchlist_warnings)
    gate_row = classify_gate(used_input_rows, watchlist_rows, warnings)
    gate_rows = [gate_row]
    summary_rows = build_summary(gate_row, warnings)
    gate_path = write_csv_rows(gate_output, GATE_FIELDS, gate_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_report(
            used_inputs_input=used_inputs_input,
            watchlist_input=watchlist_input,
            gate_output=gate_output,
            summary_output=summary_output,
            gate_row=gate_row,
            summary_rows=summary_rows,
            warnings=tuple(warnings),
        ),
        encoding="utf-8",
    )
    return WatchlistInputGateResult(
        gate_output=gate_path,
        summary_output=summary_path,
        report_output=report_path,
        gate_rows=gate_rows,
        summary_rows=summary_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify personal watchlist input readiness without changing watchlist values.")
    parser.add_argument("--used-inputs-input", default=DEFAULT_USED_INPUTS_INPUT)
    parser.add_argument("--watchlist-input", default=DEFAULT_WATCHLIST_INPUT)
    parser.add_argument("--gate-output", default=DEFAULT_GATE_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_watchlist_input_gate(
        used_inputs_input=args.used_inputs_input,
        watchlist_input=args.watchlist_input,
        gate_output=args.gate_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    summary = summary_map(result.summary_rows)
    print(f"gate_output={result.gate_output}")
    print(f"summary_output={result.summary_output}")
    print(f"report_output={result.report_output}")
    print(f"watchlist_input_status={summary.get('watchlist_input_status', 'NOT_AVAILABLE')}")
    print(f"watchlist_data_status={summary.get('watchlist_data_status', 'NOT_AVAILABLE')}")
    print(f"watchlist_readiness_status={summary.get('watchlist_readiness_status', 'NOT_AVAILABLE')}")
    print(f"warnings_total={len(result.warnings)}")


if __name__ == "__main__":
    main()
