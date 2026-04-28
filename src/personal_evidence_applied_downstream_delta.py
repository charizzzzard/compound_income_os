from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_PROFILED_MASTER_INPUT = "data/processed/personal_fundamentals_master_profiled.csv"
DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT = "data/processed/personal_fundamentals_master_evidence_applied.csv"
DEFAULT_EVIDENCE_APPLY_SUMMARY_INPUT = "data/processed/personal_fundamentals_evidence_apply_summary.csv"
DEFAULT_CLOSURE_SUMMARY_INPUT = "data/processed/personal_missing_kpi_closure_summary.csv"
DEFAULT_CLOSURE_HOLDINGS_INPUT = "data/processed/personal_missing_kpi_closure_holdings.csv"
DEFAULT_SCORES_INPUT = "data/processed/personal_company_scores.csv"
DEFAULT_COVERAGE_INPUT = "data/processed/personal_fundamentals_coverage.csv"
DEFAULT_MONTHLY_INPUT = "data/processed/personal_monthly_buy_ranking.csv"
DEFAULT_RUN_MANIFEST_INPUT = "data/processed/personal_run_manifest.json"
DEFAULT_RUN_USED_INPUTS_INPUT = "data/processed/personal_run_used_inputs.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_evidence_applied_downstream_delta_summary.csv"
DEFAULT_HOLDINGS_OUTPUT = "data/processed/personal_evidence_applied_downstream_delta_holdings.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_evidence_applied_downstream_delta_report.md"

SUMMARY_FIELDS = ["metric", "value", "notes"]
HOLDING_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "previous_likely_blocker",
    "current_likely_blocker",
    "previous_missing_required_kpis",
    "current_missing_required_kpis",
    "newly_available_kpis",
    "data_quality_flag",
    "monthly_action",
    "recommended_next_action",
]

MASTER_METADATA_COLUMNS = {
    "ticker",
    "isin",
    "company_name",
    "currency",
    "sector",
    "country",
    "asset_type",
    "company_type_profile",
    "source_name",
    "source_as_of_date",
    "fiscal_period",
    "fiscal_year",
    "report_date",
    "filing_date",
    "market_price_date",
    "calculation_version",
    "data_quality_flag",
    "notes",
    "sleeve",
    "overlay_thesis_robustness",
    "overlay_has_hard_risk_flag",
    "overlay_analyst_notes",
    "overlay_manual_override_flag",
    "overlay_manual_override_reason",
}


@dataclass(frozen=True)
class MasterUsage:
    source_mode: str
    scoring_master_path: str
    use_evidence_applied_master: str
    use_profiled_master: str


@dataclass(frozen=True)
class EvidenceAppliedDeltaResult:
    summary_output: Path
    holdings_output: Path
    report_output: Path
    summary_rows: list[dict[str, str]]
    holding_rows: list[dict[str, str]]
    warnings: tuple[str, ...]
    master_usage: MasterUsage


def safe_display_path(path_value: str) -> str:
    normalized = str(path_value).replace("\\", "/")
    if "data/raw/private" in normalized:
        return "<private_path>"
    return path_value


def optional_csv_rows(path_value: str, label: str) -> tuple[list[dict[str, str]], list[str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], [f"missing_optional_input={label}:{safe_display_path(path_value)}"]
    return read_csv_rows(path), []


def optional_json(path_value: str, label: str) -> tuple[dict[str, Any], list[str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return {}, [f"missing_optional_input={label}:{safe_display_path(path_value)}"]
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle), []


def identity_key(row: dict[str, Any]) -> tuple[str, str]:
    return canonicalize_ticker(row.get("ticker", "")), str(row.get("isin", "") or "").strip().upper()


def identity_keys(row: dict[str, Any]) -> list[tuple[str, str]]:
    ticker, isin = identity_key(row)
    keys = [(ticker, isin)]
    if ticker:
        keys.append((ticker, ""))
    if isin:
        keys.append(("", isin))
    return [key for key in keys if key[0] or key[1]]


def build_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        for key in identity_keys(row):
            lookup.setdefault(key, row)
    return lookup


def lookup_identity(row: dict[str, str], lookup: dict[tuple[str, str], dict[str, str]]) -> dict[str, str]:
    for key in identity_keys(row):
        if key in lookup:
            return lookup[key]
    return {}


def split_semicolon(value: Any) -> list[str]:
    parts = [part.strip() for part in str(value or "").replace(",", ";").split(";")]
    return sorted({part for part in parts if part})


def master_available_kpis(row: dict[str, str]) -> set[str]:
    available: set[str] = set()
    for key, value in row.items():
        if key in MASTER_METADATA_COLUMNS:
            continue
        if str(value or "").strip():
            available.add(key)
    return available


def determine_master_usage(manifest: dict[str, Any], used_input_rows: list[dict[str, str]]) -> MasterUsage:
    inputs = manifest.get("inputs") if isinstance(manifest.get("inputs"), dict) else {}
    use_evidence = str(bool(inputs.get("use_evidence_applied_master")) if "use_evidence_applied_master" in inputs else "REVIEW")
    use_profiled = str(bool(inputs.get("use_profiled_master")) if "use_profiled_master" in inputs else "REVIEW")
    source_mode = "REVIEW"
    scoring_master_path = ""
    for row in used_input_rows:
        if str(row.get("stage_name", "") or "").strip() != "scoring":
            continue
        if str(row.get("input_role", "") or "").strip() == "fundamentals_master":
            scoring_master_path = str(row.get("input_path", "") or "").strip()
        notes = str(row.get("notes", "") or "")
        if "fundamentals_source_mode=" in notes:
            source_mode = notes.split("fundamentals_source_mode=", 1)[1].split(";", 1)[0].split(",", 1)[0].strip()
    stages = manifest.get("stages") if isinstance(manifest.get("stages"), list) else []
    for stage in stages:
        if not isinstance(stage, dict) or stage.get("stage_name") != "scoring":
            continue
        used_inputs = stage.get("used_inputs") if isinstance(stage.get("used_inputs"), dict) else {}
        source_mode = str(used_inputs.get("fundamentals_source_mode", source_mode) or source_mode)
        scoring_master_path = str(used_inputs.get("fundamentals_master", scoring_master_path) or scoring_master_path)
    return MasterUsage(
        source_mode=source_mode or "REVIEW",
        scoring_master_path=scoring_master_path,
        use_evidence_applied_master=use_evidence,
        use_profiled_master=use_profiled,
    )


def monthly_action_lookup(monthly_rows: list[dict[str, str]]) -> dict[str, str]:
    lookup: dict[str, str] = {}

    def sort_key(row: dict[str, str]) -> tuple[int, str]:
        rank_text = str(row.get("rank", "") or "").strip()
        rank = int(rank_text) if rank_text.isdigit() else 999999
        return rank, canonicalize_ticker(row.get("ticker", ""))

    for row in sorted(monthly_rows, key=sort_key):
        ticker = canonicalize_ticker(row.get("ticker", ""))
        if ticker:
            lookup.setdefault(ticker, str(row.get("target_action", "") or "").strip())
    return lookup


def current_blocker(
    *,
    previous_blocker: str,
    profile: str,
    asset_type: str,
    current_missing: list[str],
    newly_available: list[str],
    data_quality_flag: str,
    monthly_action: str,
) -> tuple[str, str]:
    if previous_blocker == "NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE":
        return "still_blocked_non_us", "add non-US/manual fundamentals workflow"
    if previous_blocker == "ETF_OR_ADR_OR_NON_COMPANY" or asset_type in {"ETF", "ADR", "FUND"}:
        return "still_blocked_etf_or_adr", "add ETF/fund facts workflow"
    if profile == "FINANCIAL" or previous_blocker == "FINANCIAL_PROFILE":
        return "still_blocked_financial", "add financial-company KPI profile or keep separate from STANDARD scoring"
    if profile == "OTHER" or previous_blocker == "OTHER_PROFILE":
        return "still_blocked_other", "keep excluded unless explicit profile model exists"
    if data_quality_flag not in {"MISSING_DATA", "BLOCKED"}:
        if monthly_action and monthly_action not in {"DO_NOT_BUY", "HOLD_CASH"}:
            return "monthly_candidate_possible", "review ranking output and constraints"
        return "scoring_unlocked", "review score, valuation and monthly ranking constraints"
    if previous_blocker == "EVIDENCE_AVAILABLE_NOT_APPLIED" and newly_available and current_missing:
        return "still_missing_after_evidence", "add manual overlay or extend KPI mapping"
    if previous_blocker == "EVIDENCE_AVAILABLE_NOT_APPLIED" and newly_available:
        return "evidence_available_not_applied_resolved", "rerun downstream checks and verify score/monthly gates"
    if current_missing:
        return "still_missing_after_evidence", "add manual overlay or extend KPI mapping"
    return "REVIEW", "review remaining downstream data-quality gate"


def build_holding_rows(
    *,
    closure_rows: list[dict[str, str]],
    profiled_rows: list[dict[str, str]],
    evidence_applied_rows: list[dict[str, str]],
    coverage_rows: list[dict[str, str]],
    score_rows: list[dict[str, str]],
    monthly_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    profiled_lookup = build_lookup(profiled_rows)
    evidence_lookup = build_lookup(evidence_applied_rows)
    coverage_lookup = build_lookup(coverage_rows)
    score_lookup = build_lookup(score_rows)
    monthly_lookup = monthly_action_lookup(monthly_rows)
    holdings: list[dict[str, str]] = []
    for row in closure_rows:
        ticker, isin = identity_key(row)
        profiled_row = lookup_identity(row, profiled_lookup)
        evidence_row = lookup_identity(row, evidence_lookup)
        coverage_row = lookup_identity(row, coverage_lookup)
        score_row = lookup_identity(row, score_lookup)
        previous_missing = split_semicolon(row.get("missing_required_kpis"))
        current_missing = split_semicolon(coverage_row.get("missing_required_kpis"))
        newly_available = sorted(master_available_kpis(evidence_row) - master_available_kpis(profiled_row))
        data_quality_flag = safe_upper(score_row.get("data_quality_flag") or row.get("data_quality_flag"))
        monthly_action = monthly_lookup.get(ticker, "")
        profile = safe_upper(row.get("company_type_profile") or coverage_row.get("company_type_profile") or evidence_row.get("company_type_profile"))
        asset_type = safe_upper(coverage_row.get("asset_type") or row.get("asset_type") or evidence_row.get("asset_type"))
        current_likely, action = current_blocker(
            previous_blocker=safe_upper(row.get("likely_blocker")),
            profile=profile,
            asset_type=asset_type,
            current_missing=current_missing,
            newly_available=newly_available,
            data_quality_flag=data_quality_flag,
            monthly_action=monthly_action,
        )
        holdings.append(
            {
                "ticker": ticker,
                "isin": isin,
                "company_name": str(row.get("company_name") or coverage_row.get("holding_name") or evidence_row.get("company_name") or "").strip(),
                "company_type_profile": profile,
                "previous_likely_blocker": safe_upper(row.get("likely_blocker")),
                "current_likely_blocker": current_likely,
                "previous_missing_required_kpis": "; ".join(previous_missing),
                "current_missing_required_kpis": "; ".join(current_missing),
                "newly_available_kpis": "; ".join(newly_available),
                "data_quality_flag": data_quality_flag,
                "monthly_action": monthly_action,
                "recommended_next_action": action,
            }
        )
    holdings.sort(key=lambda item: (item["current_likely_blocker"], item["ticker"], item["isin"]))
    return holdings


def metric_value(rows: list[dict[str, str]], metric: str) -> str:
    for row in rows:
        if row.get("metric") == metric:
            return str(row.get("value", "") or "")
    return "0"


def build_summary_rows(
    *,
    closure_summary_rows: list[dict[str, str]],
    holding_rows: list[dict[str, str]],
    score_rows: list[dict[str, str]],
    master_usage: MasterUsage,
    warnings: list[str],
) -> list[dict[str, str]]:
    blocker_counts = Counter(row["current_likely_blocker"] for row in holding_rows)
    score_counts = Counter(safe_upper(row.get("data_quality_flag")) for row in score_rows)
    rows = [
        {"metric": "scoring_fundamentals_source_mode", "value": master_usage.source_mode, "notes": "Observed from manifest/used-inputs."},
        {"metric": "scoring_fundamentals_master_path", "value": master_usage.scoring_master_path, "notes": "Observed scoring fundamentals master path."},
        {"metric": "use_evidence_applied_master", "value": master_usage.use_evidence_applied_master, "notes": "Observed run option from manifest."},
        {"metric": "use_profiled_master", "value": master_usage.use_profiled_master, "notes": "Observed run option from manifest."},
        {"metric": "before_evidence_available_not_applied_total", "value": metric_value(closure_summary_rows, "evidence_available_not_applied_total"), "notes": "Baseline from missing-KPI closure summary."},
        {"metric": "before_evidence_applied_but_still_missing_total", "value": metric_value(closure_summary_rows, "evidence_applied_but_still_missing_total"), "notes": "Baseline from missing-KPI closure summary."},
        {"metric": "before_missing_required_kpi_total", "value": metric_value(closure_summary_rows, "missing_required_kpi_total"), "notes": "Baseline from missing-KPI closure summary."},
        {"metric": "current_missing_required_kpi_total", "value": str(sum(1 for row in holding_rows if row["current_missing_required_kpis"])), "notes": "Current closure holdings with required KPI gaps."},
        {"metric": "score_data_quality__MISSING_DATA", "value": str(score_counts.get("MISSING_DATA", 0)), "notes": "Current score data-quality count."},
        {"metric": "score_data_quality__OK", "value": str(score_counts.get("OK", 0)), "notes": "Current score data-quality count."},
        {"metric": "score_data_quality__REVIEW", "value": str(score_counts.get("REVIEW", 0)), "notes": "Current score data-quality count."},
        {"metric": "score_data_quality__BLOCKED", "value": str(score_counts.get("BLOCKED", 0)), "notes": "Current score data-quality count."},
        {"metric": "warnings_total", "value": str(len(warnings)), "notes": "Warnings produced while reading optional inputs."},
    ]
    for blocker in sorted(blocker_counts):
        rows.append({"metric": f"current_likely_blocker__{blocker}", "value": str(blocker_counts[blocker]), "notes": "Current likely blocker counts."})
    rows.sort(key=lambda row: row["metric"])
    return rows


def build_markdown(summary_rows: list[dict[str, str]], holding_rows: list[dict[str, str]], warnings: list[str]) -> str:
    summary = {row["metric"]: row["value"] for row in summary_rows}
    lines = [
        "# Personal Evidence-Applied Downstream Delta Report",
        "",
        "## Master Usage",
        "",
        f"- `scoring_fundamentals_source_mode` = {summary.get('scoring_fundamentals_source_mode', 'REVIEW')}",
        f"- `scoring_fundamentals_master_path` = {summary.get('scoring_fundamentals_master_path', 'REVIEW')}",
        f"- `use_evidence_applied_master` = {summary.get('use_evidence_applied_master', 'REVIEW')}",
        f"- `use_profiled_master` = {summary.get('use_profiled_master', 'REVIEW')}",
        "",
        "## Before/After Closure",
        "",
        f"- `evidence_available_not_applied_total_before` = {summary.get('before_evidence_available_not_applied_total', '0')}",
        f"- `evidence_applied_but_still_missing_total_before` = {summary.get('before_evidence_applied_but_still_missing_total', '0')}",
        f"- `missing_required_kpi_total_before` = {summary.get('before_missing_required_kpi_total', '0')}",
        f"- `missing_required_kpi_total_current` = {summary.get('current_missing_required_kpi_total', '0')}",
        f"- `score MISSING_DATA` = {summary.get('score_data_quality__MISSING_DATA', '0')}",
        f"- `score OK` = {summary.get('score_data_quality__OK', '0')}",
        f"- `score REVIEW` = {summary.get('score_data_quality__REVIEW', '0')}",
        f"- `score BLOCKED` = {summary.get('score_data_quality__BLOCKED', '0')}",
        "",
        "## Current Blockers",
        "",
    ]
    blocker_rows = [row for row in summary_rows if row["metric"].startswith("current_likely_blocker__")]
    lines.extend(f"- `{row['metric'].removeprefix('current_likely_blocker__')}` = {row['value']}" for row in blocker_rows) if blocker_rows else lines.append("- none")
    lines.extend(
        [
            "",
            "## Holding Delta Table",
            "",
            "| ticker | isin | profile | previous_blocker | current_blocker | previous_missing_required_kpis | current_missing_required_kpis | newly_available_kpis | data_quality_flag | monthly_action | recommended_next_action |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in holding_rows:
        def cell(value: str) -> str:
            return str(value or "").replace("|", "/").replace("\n", " ").strip()

        lines.append(
            "| "
            + " | ".join(
                [
                    cell(row["ticker"]),
                    cell(row["isin"]),
                    cell(row["company_type_profile"]),
                    cell(row["previous_likely_blocker"]),
                    cell(row["current_likely_blocker"]),
                    cell(row["previous_missing_required_kpis"]),
                    cell(row["current_missing_required_kpis"]),
                    cell(row["newly_available_kpis"]),
                    cell(row["data_quality_flag"]),
                    cell(row["monthly_action"]),
                    cell(row["recommended_next_action"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- `{warning}`" for warning in warnings) if warnings else lines.append("- none")
    return "\n".join(lines) + "\n"


def run_personal_evidence_applied_downstream_delta(
    *,
    profiled_master_input: str = DEFAULT_PROFILED_MASTER_INPUT,
    evidence_applied_master_input: str = DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT,
    evidence_apply_summary_input: str = DEFAULT_EVIDENCE_APPLY_SUMMARY_INPUT,
    closure_summary_input: str = DEFAULT_CLOSURE_SUMMARY_INPUT,
    closure_holdings_input: str = DEFAULT_CLOSURE_HOLDINGS_INPUT,
    scores_input: str = DEFAULT_SCORES_INPUT,
    coverage_input: str = DEFAULT_COVERAGE_INPUT,
    monthly_input: str = DEFAULT_MONTHLY_INPUT,
    run_manifest_input: str = DEFAULT_RUN_MANIFEST_INPUT,
    run_used_inputs_input: str = DEFAULT_RUN_USED_INPUTS_INPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    holdings_output: str = DEFAULT_HOLDINGS_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> EvidenceAppliedDeltaResult:
    warnings: list[str] = []
    profiled_rows, row_warnings = optional_csv_rows(profiled_master_input, "profiled_master_input")
    warnings.extend(row_warnings)
    evidence_applied_rows, row_warnings = optional_csv_rows(evidence_applied_master_input, "evidence_applied_master_input")
    warnings.extend(row_warnings)
    _, row_warnings = optional_csv_rows(evidence_apply_summary_input, "evidence_apply_summary_input")
    warnings.extend(row_warnings)
    closure_summary_rows, row_warnings = optional_csv_rows(closure_summary_input, "closure_summary_input")
    warnings.extend(row_warnings)
    closure_rows, row_warnings = optional_csv_rows(closure_holdings_input, "closure_holdings_input")
    warnings.extend(row_warnings)
    score_rows, row_warnings = optional_csv_rows(scores_input, "scores_input")
    warnings.extend(row_warnings)
    coverage_rows, row_warnings = optional_csv_rows(coverage_input, "coverage_input")
    warnings.extend(row_warnings)
    monthly_rows, row_warnings = optional_csv_rows(monthly_input, "monthly_input")
    warnings.extend(row_warnings)
    manifest, row_warnings = optional_json(run_manifest_input, "run_manifest_input")
    warnings.extend(row_warnings)
    used_input_rows, row_warnings = optional_csv_rows(run_used_inputs_input, "run_used_inputs_input")
    warnings.extend(row_warnings)

    master_usage = determine_master_usage(manifest, used_input_rows)
    holding_rows = build_holding_rows(
        closure_rows=closure_rows,
        profiled_rows=profiled_rows,
        evidence_applied_rows=evidence_applied_rows,
        coverage_rows=coverage_rows,
        score_rows=score_rows,
        monthly_rows=monthly_rows,
    )
    summary_rows = build_summary_rows(
        closure_summary_rows=closure_summary_rows,
        holding_rows=holding_rows,
        score_rows=score_rows,
        master_usage=master_usage,
        warnings=warnings,
    )
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    holdings_path = write_csv_rows(holdings_output, HOLDING_FIELDS, holding_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_markdown(summary_rows, holding_rows, warnings), encoding="utf-8")
    return EvidenceAppliedDeltaResult(
        summary_output=summary_path,
        holdings_output=holdings_path,
        report_output=report_path,
        summary_rows=summary_rows,
        holding_rows=holding_rows,
        warnings=tuple(warnings),
        master_usage=master_usage,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a controlled evidence-applied downstream delta report.")
    parser.add_argument("--profiled-master-input", default=DEFAULT_PROFILED_MASTER_INPUT)
    parser.add_argument("--evidence-applied-master-input", default=DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT)
    parser.add_argument("--evidence-apply-summary-input", default=DEFAULT_EVIDENCE_APPLY_SUMMARY_INPUT)
    parser.add_argument("--closure-summary-input", default=DEFAULT_CLOSURE_SUMMARY_INPUT)
    parser.add_argument("--closure-holdings-input", default=DEFAULT_CLOSURE_HOLDINGS_INPUT)
    parser.add_argument("--scores-input", default=DEFAULT_SCORES_INPUT)
    parser.add_argument("--coverage-input", default=DEFAULT_COVERAGE_INPUT)
    parser.add_argument("--monthly-input", default=DEFAULT_MONTHLY_INPUT)
    parser.add_argument("--run-manifest-input", default=DEFAULT_RUN_MANIFEST_INPUT)
    parser.add_argument("--run-used-inputs-input", default=DEFAULT_RUN_USED_INPUTS_INPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--holdings-output", default=DEFAULT_HOLDINGS_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_personal_evidence_applied_downstream_delta(
        profiled_master_input=args.profiled_master_input,
        evidence_applied_master_input=args.evidence_applied_master_input,
        evidence_apply_summary_input=args.evidence_apply_summary_input,
        closure_summary_input=args.closure_summary_input,
        closure_holdings_input=args.closure_holdings_input,
        scores_input=args.scores_input,
        coverage_input=args.coverage_input,
        monthly_input=args.monthly_input,
        run_manifest_input=args.run_manifest_input,
        run_used_inputs_input=args.run_used_inputs_input,
        summary_output=args.summary_output,
        holdings_output=args.holdings_output,
        report_output=args.report_output,
    )


if __name__ == "__main__":
    main()
