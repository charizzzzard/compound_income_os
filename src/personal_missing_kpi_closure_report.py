from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_PROFILED_MASTER_INPUT = "data/processed/personal_fundamentals_master_profiled.csv"
DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT = "data/processed/personal_fundamentals_master_evidence_applied.csv"
DEFAULT_OVERLAY_APPLIED_MASTER_INPUT = "data/processed/personal_fundamentals_master_applied.csv"
DEFAULT_COVERAGE_INPUT = "data/processed/personal_fundamentals_coverage.csv"
DEFAULT_SCORES_INPUT = "data/processed/personal_company_scores.csv"
DEFAULT_GAP_DIAGNOSTICS_INPUT = "data/processed/personal_fundamentals_gap_diagnostics.csv"
DEFAULT_GAP_SUMMARY_INPUT = "data/processed/personal_fundamentals_gap_summary.csv"
DEFAULT_EVIDENCE_REGISTRY_INPUT = "data/processed/personal_fundamentals_evidence_registry.csv"
DEFAULT_EVIDENCE_APPLY_SUMMARY_INPUT = "data/processed/personal_fundamentals_evidence_apply_summary.csv"
DEFAULT_SNAPSHOT_SUMMARY_INPUT = "data/processed/personal_fundamentals_snapshot_summary.csv"
DEFAULT_UNLOCK_HOLDINGS_INPUT = "data/processed/personal_profile_review_unlock_holdings.csv"
DEFAULT_RUN_MANIFEST_INPUT = "data/processed/personal_run_manifest.json"
DEFAULT_RUN_USED_INPUTS = "data/processed/personal_run_used_inputs.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_missing_kpi_closure_summary.csv"
DEFAULT_HOLDINGS_OUTPUT = "data/processed/personal_missing_kpi_closure_holdings.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_missing_kpi_closure_report.md"

SUMMARY_FIELDS = ["metric", "value", "notes"]
HOLDING_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "asset_type",
    "company_type_profile",
    "data_quality_flag",
    "quality_gap_type",
    "missing_required_kpis",
    "available_kpis",
    "evidence_registry_hits_count",
    "evidence_applied_flag",
    "present_in_profiled_master",
    "present_in_evidence_applied_master",
    "present_in_overlay_applied_master",
    "likely_blocker",
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
    use_profiled_master: str
    use_evidence_applied_master: str
    finding: str


@dataclass(frozen=True)
class MissingKpiClosureResult:
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


def split_semicolon(value: Any) -> list[str]:
    parts = [part.strip() for part in str(value or "").replace(",", ";").split(";")]
    return sorted({part for part in parts if part})


def bool_text(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


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


def master_available_kpis(row: dict[str, str]) -> set[str]:
    available: set[str] = set()
    for key, value in row.items():
        if key in MASTER_METADATA_COLUMNS:
            continue
        if str(value or "").strip():
            available.add(key)
    return available


def build_evidence_kpi_lookup(evidence_rows: list[dict[str, str]]) -> dict[tuple[str, str], set[str]]:
    lookup: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in evidence_rows:
        kpi_name = str(row.get("kpi_name", "") or "").strip()
        if not kpi_name:
            continue
        has_evidence = bool_text(row.get("evidence_present")) or bool(str(row.get("reported_value", "") or "").strip())
        if not has_evidence:
            continue
        for key in identity_keys(row):
            lookup[key].add(kpi_name)
    return lookup


def lookup_kpis(row: dict[str, str], lookup: dict[tuple[str, str], set[str]]) -> set[str]:
    result: set[str] = set()
    for key in identity_keys(row):
        result.update(lookup.get(key, set()))
    return result


def determine_master_usage(manifest: dict[str, Any], used_input_rows: list[dict[str, str]], evidence_available_not_applied_count: int) -> MasterUsage:
    inputs = manifest.get("inputs") if isinstance(manifest.get("inputs"), dict) else {}
    use_profiled = str(bool(inputs.get("use_profiled_master")) if "use_profiled_master" in inputs else "REVIEW")
    use_evidence_applied = str(bool(inputs.get("use_evidence_applied_master")) if "use_evidence_applied_master" in inputs else "REVIEW")
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
    if source_mode == "REVIEW":
        stages = manifest.get("stages") if isinstance(manifest.get("stages"), list) else []
        for stage in stages:
            if not isinstance(stage, dict) or stage.get("stage_name") != "scoring":
                continue
            used_inputs = stage.get("used_inputs") if isinstance(stage.get("used_inputs"), dict) else {}
            source_mode = str(used_inputs.get("fundamentals_source_mode", "REVIEW") or "REVIEW")
            scoring_master_path = str(used_inputs.get("fundamentals_master", scoring_master_path) or scoring_master_path)

    if source_mode == "PROFILED" and use_evidence_applied == "False" and evidence_available_not_applied_count > 0:
        finding = "LIKELY_PROFILED_MASTER_INSTEAD_OF_EVIDENCE_APPLIED_FOR_EVIDENCE_ROWS"
    elif source_mode in {"PROFILED", "EVIDENCE_APPLIED", "APPLIED", "BASE"}:
        finding = "NO_MASTER_USAGE_BLOCKER_CONFIRMED"
    else:
        finding = "REVIEW"
    return MasterUsage(
        source_mode=source_mode or "REVIEW",
        scoring_master_path=scoring_master_path,
        use_profiled_master=use_profiled,
        use_evidence_applied_master=use_evidence_applied,
        finding=finding,
    )


def likely_blocker_and_action(
    *,
    profile: str,
    asset_type: str,
    quality_gap: str,
    missing_kpis: list[str],
    evidence_hits_count: int,
    evidence_applied_flag: bool,
    current_source_mode: str,
) -> tuple[str, str]:
    if quality_gap == "NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE":
        return "NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE", "add non-US/manual fundamentals workflow"
    if quality_gap == "ETF_OR_NON_COMPANY_FUNDAMENTALS" or asset_type in {"ETF", "FUND", "ADR"}:
        return "ETF_OR_ADR_OR_NON_COMPANY", "add ETF/fund facts workflow"
    if profile == "FINANCIAL":
        return "FINANCIAL_PROFILE", "add financial-company KPI profile or keep separate from STANDARD scoring"
    if profile == "OTHER":
        return "OTHER_PROFILE", "keep excluded unless explicit profile model exists"
    if quality_gap == "MARKET_DATA_REQUIRED_NOT_SEC":
        return "MARKET_DATA_REQUIRED_NOT_SEC", "add market data input/source contract"
    if profile == "STANDARD" and quality_gap == "SEC_KPI_PARTIAL" and evidence_hits_count > 0 and current_source_mode != "EVIDENCE_APPLIED":
        return "EVIDENCE_AVAILABLE_NOT_APPLIED", "run evidence apply and rerun scoring with --use-evidence-applied-master"
    if profile == "STANDARD" and quality_gap == "SEC_KPI_PARTIAL" and evidence_applied_flag and missing_kpis:
        return "EVIDENCE_APPLIED_BUT_STILL_MISSING", "add manual overlay or extend KPI mapping"
    if profile == "STANDARD" and quality_gap == "SEC_KPI_MISSING":
        return "SEC_KPI_MISSING", "run SEC snapshot/evidence pipeline or manual overlay"
    if profile == "STANDARD" and missing_kpis:
        return "MISSING_REQUIRED_KPI", "run SEC snapshot/evidence pipeline or manual overlay"
    return "REVIEW", "review remaining data-quality gate"


def build_holding_rows(
    *,
    gap_rows: list[dict[str, str]],
    coverage_rows: list[dict[str, str]],
    score_rows: list[dict[str, str]],
    profiled_rows: list[dict[str, str]],
    evidence_applied_rows: list[dict[str, str]],
    overlay_applied_rows: list[dict[str, str]],
    evidence_rows: list[dict[str, str]],
    unlock_rows: list[dict[str, str]],
    source_mode: str,
) -> list[dict[str, str]]:
    coverage_lookup = build_lookup(coverage_rows)
    score_lookup = build_lookup(score_rows)
    profiled_lookup = build_lookup(profiled_rows)
    evidence_applied_lookup = build_lookup(evidence_applied_rows)
    overlay_applied_lookup = build_lookup(overlay_applied_rows)
    evidence_kpi_lookup = build_evidence_kpi_lookup(evidence_rows)
    unlock_lookup = build_lookup(unlock_rows)

    holdings: list[dict[str, str]] = []
    for row in gap_rows:
        coverage_row = lookup_identity(row, coverage_lookup)
        score_row = lookup_identity(row, score_lookup)
        unlock_row = lookup_identity(row, unlock_lookup)
        profiled_row = lookup_identity(row, profiled_lookup)
        evidence_applied_row = lookup_identity(row, evidence_applied_lookup)
        overlay_applied_row = lookup_identity(row, overlay_applied_lookup)

        ticker, isin = identity_key(row)
        profile = safe_upper(row.get("company_type_profile") or coverage_row.get("company_type_profile") or unlock_row.get("company_type_profile"))
        asset_type = safe_upper(row.get("asset_type") or coverage_row.get("asset_type") or unlock_row.get("asset_type"))
        quality_gap = safe_upper(row.get("quality_gap_type") or unlock_row.get("quality_gap_type"))
        missing_kpis = split_semicolon(
            row.get("missing_required_kpis_under_current_profile") or coverage_row.get("missing_required_kpis")
        )
        evidence_kpis = lookup_kpis(row, evidence_kpi_lookup)
        available_kpis = set(evidence_kpis)
        available_kpis.update(master_available_kpis(profiled_row))
        available_kpis.update(master_available_kpis(evidence_applied_row))
        available_kpis.update(master_available_kpis(overlay_applied_row))
        relevant_evidence_kpis = evidence_kpis.intersection(set(missing_kpis)) if missing_kpis else evidence_kpis
        evidence_applied_flag = bool(evidence_applied_row) and bool(
            relevant_evidence_kpis.intersection(master_available_kpis(evidence_applied_row))
            or set(missing_kpis).intersection(master_available_kpis(evidence_applied_row))
        )
        likely_blocker, action = likely_blocker_and_action(
            profile=profile,
            asset_type=asset_type,
            quality_gap=quality_gap,
            missing_kpis=missing_kpis,
            evidence_hits_count=len(evidence_kpis),
            evidence_applied_flag=evidence_applied_flag,
            current_source_mode=source_mode,
        )
        holdings.append(
            {
                "ticker": ticker,
                "isin": isin,
                "company_name": str(row.get("company_name") or coverage_row.get("holding_name") or coverage_row.get("company_name") or "").strip(),
                "asset_type": asset_type,
                "company_type_profile": profile,
                "data_quality_flag": safe_upper(score_row.get("data_quality_flag") or row.get("current_data_quality_flag") or unlock_row.get("data_quality_flag")),
                "quality_gap_type": quality_gap,
                "missing_required_kpis": "; ".join(missing_kpis),
                "available_kpis": "; ".join(sorted(available_kpis)),
                "evidence_registry_hits_count": str(len(evidence_kpis)),
                "evidence_applied_flag": str(evidence_applied_flag),
                "present_in_profiled_master": str(bool(profiled_row)),
                "present_in_evidence_applied_master": str(bool(evidence_applied_row)),
                "present_in_overlay_applied_master": str(bool(overlay_applied_row)),
                "likely_blocker": likely_blocker,
                "recommended_next_action": action,
            }
        )
    holdings.sort(key=lambda item: (item["likely_blocker"], item["ticker"], item["isin"]))
    return holdings


def count_standard_missing_rows(holding_rows: list[dict[str, str]]) -> int:
    return sum(1 for row in holding_rows if row["company_type_profile"] == "STANDARD" and bool(row["missing_required_kpis"]))


def build_summary_rows(holding_rows: list[dict[str, str]], warnings: list[str], master_usage: MasterUsage) -> list[dict[str, str]]:
    blocker_counter = Counter(row["likely_blocker"] for row in holding_rows)
    profile_counter = Counter(row["company_type_profile"] for row in holding_rows)
    asset_counter = Counter(row["asset_type"] for row in holding_rows)
    rows = [
        {"metric": "holdings_total", "value": str(len(holding_rows)), "notes": "Rows in closure holdings output."},
        {"metric": "standard_profile_total", "value": str(profile_counter.get("STANDARD", 0)), "notes": "Rows with company_type_profile=STANDARD."},
        {"metric": "financial_profile_total", "value": str(profile_counter.get("FINANCIAL", 0)), "notes": "Rows with company_type_profile=FINANCIAL."},
        {"metric": "other_profile_total", "value": str(profile_counter.get("OTHER", 0)), "notes": "Rows with company_type_profile=OTHER."},
        {"metric": "non_us_total", "value": str(blocker_counter.get("NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE", 0)), "notes": "Rows outside current SEC US-company scope."},
        {"metric": "etf_or_adr_total", "value": str(blocker_counter.get("ETF_OR_ADR_OR_NON_COMPANY", 0) or asset_counter.get("ETF", 0) + asset_counter.get("ADR", 0)), "notes": "ETF/ADR/non-company rows."},
        {"metric": "missing_required_kpi_total", "value": str(count_standard_missing_rows(holding_rows)), "notes": "STANDARD rows with missing required KPIs."},
        {"metric": "evidence_available_not_applied_total", "value": str(blocker_counter.get("EVIDENCE_AVAILABLE_NOT_APPLIED", 0)), "notes": "Rows with evidence hits while current scoring is not evidence-applied."},
        {"metric": "evidence_applied_but_still_missing_total", "value": str(blocker_counter.get("EVIDENCE_APPLIED_BUT_STILL_MISSING", 0)), "notes": "Rows where evidence-applied fields exist but required KPIs remain missing."},
        {"metric": "market_data_required_total", "value": str(blocker_counter.get("MARKET_DATA_REQUIRED_NOT_SEC", 0)), "notes": "Rows needing market data source contract."},
        {"metric": "manual_overlay_required_total", "value": str(sum(1 for row in holding_rows if "manual overlay" in row["recommended_next_action"])), "notes": "Rows whose next action includes manual overlay."},
        {"metric": "scoring_fundamentals_source_mode", "value": master_usage.source_mode, "notes": "Observed from manifest/used-inputs when available."},
        {"metric": "scoring_fundamentals_master_path", "value": master_usage.scoring_master_path, "notes": "Observed scoring fundamentals master path."},
        {"metric": "use_profiled_master", "value": master_usage.use_profiled_master, "notes": "Observed run option from manifest."},
        {"metric": "use_evidence_applied_master", "value": master_usage.use_evidence_applied_master, "notes": "Observed run option from manifest."},
        {"metric": "profiled_vs_evidence_applied_master_finding", "value": master_usage.finding, "notes": "Inference only; REVIEW when not inferable."},
        {"metric": "warnings_total", "value": str(len(warnings)), "notes": "Warnings produced while reading optional inputs."},
    ]
    for blocker in sorted(blocker_counter):
        rows.append({"metric": f"likely_blocker__{blocker}", "value": str(blocker_counter[blocker]), "notes": "Likely blocker counts."})
    rows.sort(key=lambda row: row["metric"])
    return rows


def markdown_table(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "| ticker | isin | profile | gap | missing_required_kpis | available_kpis | evidence_hits | evidence_applied | likely_blocker | next_action |",
        "|---|---|---|---|---|---|---:|---|---|---|",
    ]
    for row in rows:
        def cell(value: str) -> str:
            return str(value or "").replace("|", "/").replace("\n", " ").strip()

        lines.append(
            "| "
            + " | ".join(
                [
                    cell(row["ticker"]),
                    cell(row["isin"]),
                    cell(row["company_type_profile"]),
                    cell(row["quality_gap_type"]),
                    cell(row["missing_required_kpis"]),
                    cell(row["available_kpis"]),
                    cell(row["evidence_registry_hits_count"]),
                    cell(row["evidence_applied_flag"]),
                    cell(row["likely_blocker"]),
                    cell(row["recommended_next_action"]),
                ]
            )
            + " |"
        )
    return lines


def build_markdown(summary_rows: list[dict[str, str]], holding_rows: list[dict[str, str]], warnings: list[str], master_usage: MasterUsage) -> str:
    summary = {row["metric"]: row["value"] for row in summary_rows}
    lines = [
        "# Personal Missing KPI Closure Report",
        "",
        "## Executive Summary",
        "",
        f"- `holdings_total` = {summary.get('holdings_total', '0')}",
        f"- `missing_required_kpi_total` = {summary.get('missing_required_kpi_total', '0')}",
        f"- `evidence_available_not_applied_total` = {summary.get('evidence_available_not_applied_total', '0')}",
        f"- `evidence_applied_but_still_missing_total` = {summary.get('evidence_applied_but_still_missing_total', '0')}",
        f"- `manual_overlay_required_total` = {summary.get('manual_overlay_required_total', '0')}",
        f"- `market_data_required_total` = {summary.get('market_data_required_total', '0')}",
        "",
        "## Master Usage Findings",
        "",
        f"- `scoring_fundamentals_source_mode` = {master_usage.source_mode}",
        f"- `scoring_fundamentals_master_path` = {master_usage.scoring_master_path or 'REVIEW'}",
        f"- `use_profiled_master` = {master_usage.use_profiled_master}",
        f"- `use_evidence_applied_master` = {master_usage.use_evidence_applied_master}",
        f"- `profiled_vs_evidence_applied_master_finding` = {master_usage.finding}",
        "",
        "## Blocker Counts",
        "",
    ]
    blocker_rows = [row for row in summary_rows if row["metric"].startswith("likely_blocker__")]
    if blocker_rows:
        lines.extend(f"- `{row['metric'].removeprefix('likely_blocker__')}` = {row['value']}" for row in blocker_rows)
    else:
        lines.append("- none")
    lines.extend(["", "## Holding Closure Table", "", *markdown_table(holding_rows), "", "## Warnings", ""])
    lines.extend(f"- `{warning}`" for warning in warnings) if warnings else lines.append("- none")
    return "\n".join(lines) + "\n"


def run_personal_missing_kpi_closure_report(
    *,
    profiled_master_input: str = DEFAULT_PROFILED_MASTER_INPUT,
    evidence_applied_master_input: str = DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT,
    overlay_applied_master_input: str = DEFAULT_OVERLAY_APPLIED_MASTER_INPUT,
    coverage_input: str = DEFAULT_COVERAGE_INPUT,
    scores_input: str = DEFAULT_SCORES_INPUT,
    gap_diagnostics_input: str = DEFAULT_GAP_DIAGNOSTICS_INPUT,
    gap_summary_input: str = DEFAULT_GAP_SUMMARY_INPUT,
    evidence_registry_input: str = DEFAULT_EVIDENCE_REGISTRY_INPUT,
    evidence_apply_summary_input: str = DEFAULT_EVIDENCE_APPLY_SUMMARY_INPUT,
    snapshot_summary_input: str = DEFAULT_SNAPSHOT_SUMMARY_INPUT,
    unlock_holdings_input: str = DEFAULT_UNLOCK_HOLDINGS_INPUT,
    run_manifest_input: str = DEFAULT_RUN_MANIFEST_INPUT,
    run_used_inputs: str = DEFAULT_RUN_USED_INPUTS,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    holdings_output: str = DEFAULT_HOLDINGS_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> MissingKpiClosureResult:
    warnings: list[str] = []
    profiled_rows, row_warnings = optional_csv_rows(profiled_master_input, "profiled_master_input")
    warnings.extend(row_warnings)
    evidence_applied_rows, row_warnings = optional_csv_rows(evidence_applied_master_input, "evidence_applied_master_input")
    warnings.extend(row_warnings)
    overlay_applied_rows, row_warnings = optional_csv_rows(overlay_applied_master_input, "overlay_applied_master_input")
    warnings.extend(row_warnings)
    coverage_rows, row_warnings = optional_csv_rows(coverage_input, "coverage_input")
    warnings.extend(row_warnings)
    score_rows, row_warnings = optional_csv_rows(scores_input, "scores_input")
    warnings.extend(row_warnings)
    gap_rows, row_warnings = optional_csv_rows(gap_diagnostics_input, "gap_diagnostics_input")
    warnings.extend(row_warnings)
    _, row_warnings = optional_csv_rows(gap_summary_input, "gap_summary_input")
    warnings.extend(row_warnings)
    evidence_rows, row_warnings = optional_csv_rows(evidence_registry_input, "evidence_registry_input")
    warnings.extend(row_warnings)
    _, row_warnings = optional_csv_rows(evidence_apply_summary_input, "evidence_apply_summary_input")
    warnings.extend(row_warnings)
    _, row_warnings = optional_csv_rows(snapshot_summary_input, "snapshot_summary_input")
    warnings.extend(row_warnings)
    unlock_rows, row_warnings = optional_csv_rows(unlock_holdings_input, "unlock_holdings_input")
    warnings.extend(row_warnings)
    manifest, row_warnings = optional_json(run_manifest_input, "run_manifest_input")
    warnings.extend(row_warnings)
    used_input_rows, row_warnings = optional_csv_rows(run_used_inputs, "run_used_inputs")
    warnings.extend(row_warnings)

    provisional_holdings = build_holding_rows(
        gap_rows=gap_rows,
        coverage_rows=coverage_rows,
        score_rows=score_rows,
        profiled_rows=profiled_rows,
        evidence_applied_rows=evidence_applied_rows,
        overlay_applied_rows=overlay_applied_rows,
        evidence_rows=evidence_rows,
        unlock_rows=unlock_rows,
        source_mode="REVIEW",
    )
    evidence_available_not_applied_count = sum(
        1 for row in provisional_holdings if row["likely_blocker"] == "EVIDENCE_AVAILABLE_NOT_APPLIED"
    )
    master_usage = determine_master_usage(manifest, used_input_rows, evidence_available_not_applied_count)
    holding_rows = build_holding_rows(
        gap_rows=gap_rows,
        coverage_rows=coverage_rows,
        score_rows=score_rows,
        profiled_rows=profiled_rows,
        evidence_applied_rows=evidence_applied_rows,
        overlay_applied_rows=overlay_applied_rows,
        evidence_rows=evidence_rows,
        unlock_rows=unlock_rows,
        source_mode=master_usage.source_mode,
    )
    summary_rows = build_summary_rows(holding_rows, warnings, master_usage)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    holdings_path = write_csv_rows(holdings_output, HOLDING_FIELDS, holding_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_markdown(summary_rows, holding_rows, warnings, master_usage), encoding="utf-8")
    return MissingKpiClosureResult(
        summary_output=summary_path,
        holdings_output=holdings_path,
        report_output=report_path,
        summary_rows=summary_rows,
        holding_rows=holding_rows,
        warnings=tuple(warnings),
        master_usage=master_usage,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a missing-KPI/evidence closure report for personal fundamentals artifacts.")
    parser.add_argument("--profiled-master-input", default=DEFAULT_PROFILED_MASTER_INPUT)
    parser.add_argument("--evidence-applied-master-input", default=DEFAULT_EVIDENCE_APPLIED_MASTER_INPUT)
    parser.add_argument("--overlay-applied-master-input", default=DEFAULT_OVERLAY_APPLIED_MASTER_INPUT)
    parser.add_argument("--coverage-input", default=DEFAULT_COVERAGE_INPUT)
    parser.add_argument("--scores-input", default=DEFAULT_SCORES_INPUT)
    parser.add_argument("--gap-diagnostics-input", default=DEFAULT_GAP_DIAGNOSTICS_INPUT)
    parser.add_argument("--gap-summary-input", default=DEFAULT_GAP_SUMMARY_INPUT)
    parser.add_argument("--evidence-registry-input", default=DEFAULT_EVIDENCE_REGISTRY_INPUT)
    parser.add_argument("--evidence-apply-summary-input", default=DEFAULT_EVIDENCE_APPLY_SUMMARY_INPUT)
    parser.add_argument("--snapshot-summary-input", default=DEFAULT_SNAPSHOT_SUMMARY_INPUT)
    parser.add_argument("--unlock-holdings-input", default=DEFAULT_UNLOCK_HOLDINGS_INPUT)
    parser.add_argument("--run-manifest-input", default=DEFAULT_RUN_MANIFEST_INPUT)
    parser.add_argument("--run-used-inputs", default=DEFAULT_RUN_USED_INPUTS)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--holdings-output", default=DEFAULT_HOLDINGS_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_personal_missing_kpi_closure_report(
        profiled_master_input=args.profiled_master_input,
        evidence_applied_master_input=args.evidence_applied_master_input,
        overlay_applied_master_input=args.overlay_applied_master_input,
        coverage_input=args.coverage_input,
        scores_input=args.scores_input,
        gap_diagnostics_input=args.gap_diagnostics_input,
        gap_summary_input=args.gap_summary_input,
        evidence_registry_input=args.evidence_registry_input,
        evidence_apply_summary_input=args.evidence_apply_summary_input,
        snapshot_summary_input=args.snapshot_summary_input,
        unlock_holdings_input=args.unlock_holdings_input,
        run_manifest_input=args.run_manifest_input,
        run_used_inputs=args.run_used_inputs,
        summary_output=args.summary_output,
        holdings_output=args.holdings_output,
        report_output=args.report_output,
    )


if __name__ == "__main__":
    main()
