from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_PROFILE_REVIEW_INPUT = "data/raw/personal_fundamentals_profile_review.csv"
DEFAULT_PROFILE_REGISTRY_INPUT = "data/processed/personal_fundamentals_profile_registry.csv"
DEFAULT_PROFILE_BACKLOG_INPUT = "data/processed/personal_fundamentals_profile_review_backlog.csv"
DEFAULT_GAP_SUMMARY_INPUT = "data/processed/personal_fundamentals_gap_summary.csv"
DEFAULT_GAP_DIAGNOSTICS_INPUT = "data/processed/personal_fundamentals_gap_diagnostics.csv"
DEFAULT_SCORES_INPUT = "data/processed/personal_company_scores.csv"
DEFAULT_WATCHLIST_INPUT = "data/processed/personal_watchlist_ranked.csv"
DEFAULT_MONTHLY_INPUT = "data/processed/personal_monthly_buy_ranking.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_profile_review_unlock_summary.csv"
DEFAULT_HOLDINGS_OUTPUT = "data/processed/personal_profile_review_unlock_holdings.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_profile_review_unlock_report.md"

SUMMARY_FIELDS = ["metric", "value", "notes"]
HOLDING_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "asset_type",
    "company_type_profile",
    "profile_review_status",
    "data_quality_flag",
    "quality_gap_type",
    "monthly_action",
    "recommended_next_action",
]

MISSING_REQUIRED_GAP_TYPES = {"MISSING_REQUIRED_KPI", "SEC_KPI_MISSING", "SEC_KPI_PARTIAL"}


@dataclass(frozen=True)
class UnlockReportResult:
    summary_output: Path
    holdings_output: Path
    report_output: Path
    summary_rows: list[dict[str, str]]
    holding_rows: list[dict[str, str]]
    warnings: tuple[str, ...]


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


def identity_key(row: dict[str, Any]) -> tuple[str, str]:
    return canonicalize_ticker(row.get("ticker", "")), str(row.get("isin", "") or "").strip().upper()


def row_count(rows: list[dict[str, str]]) -> int:
    return len(rows)


def counter_rows(prefix: str, counter: Counter[str], notes: str) -> list[dict[str, str]]:
    if not counter:
        return [{"metric": f"{prefix}__NONE", "value": "0", "notes": notes}]
    return [{"metric": f"{prefix}__{key or '<blank>'}", "value": str(counter[key]), "notes": notes} for key in sorted(counter)]


def ensure_metric(rows: list[dict[str, str]], metric: str, value: str, notes: str) -> None:
    if not any(row["metric"] == metric for row in rows):
        rows.append({"metric": metric, "value": value, "notes": notes})


def count_by(rows: list[dict[str, str]], field: str, *, upper: bool = True) -> Counter[str]:
    values = []
    for row in rows:
        value = str(row.get(field, "") or "").strip()
        values.append(value.upper() if upper else value)
    return Counter(values)


def gap_summary_status(gap_summary_rows: list[dict[str, str]], warnings: list[str]) -> str:
    if warnings:
        return "MISSING"
    if not gap_summary_rows:
        return "EMPTY"
    status_row = next((row for row in gap_summary_rows if row.get("summary_metric") == "profile_review_input_status"), None)
    if status_row:
        return str(status_row.get("summary_value", "") or "").strip() or "POPULATED"
    return "POPULATED"


def monthly_ranking_status(monthly_rows: list[dict[str, str]], warnings: list[str]) -> str:
    if warnings:
        return "MISSING"
    return "POPULATED" if monthly_rows else "EMPTY"


def build_score_lookup(score_rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for row in score_rows:
        ticker, isin = identity_key(row)
        for key in ((ticker, isin), (ticker, ""), ("", isin)):
            if key[0] or key[1]:
                lookup.setdefault(key, row)
    return lookup


def lookup_row(row: dict[str, str], lookup: dict[tuple[str, str], dict[str, str]]) -> dict[str, str]:
    ticker, isin = identity_key(row)
    for key in ((ticker, isin), (ticker, ""), ("", isin)):
        if key in lookup:
            return lookup[key]
    return {}


def build_monthly_action_lookup(monthly_rows: list[dict[str, str]]) -> dict[str, str]:
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


def missing_required_kpi_gap(row: dict[str, str]) -> bool:
    quality_gap = safe_upper(row.get("quality_gap_type", ""))
    missing_required = str(row.get("missing_required_kpis_under_current_profile", "") or "").strip()
    return quality_gap in MISSING_REQUIRED_GAP_TYPES or bool(missing_required)


def recommended_next_action(row: dict[str, str], monthly_action: str) -> str:
    quality_gap = safe_upper(row.get("quality_gap_type", ""))
    profile = safe_upper(row.get("company_type_profile", ""))
    if quality_gap == "PROFILE_REVIEW_MISSING":
        return "complete profile review"
    if quality_gap == "NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE":
        return "add non-US/manual fundamentals workflow"
    if quality_gap == "ETF_OR_NON_COMPANY_FUNDAMENTALS":
        return "add ETF/fund facts workflow"
    if profile == "FINANCIAL":
        return "add financial-company KPI profile or keep reviewed separate"
    if profile == "OTHER":
        return "keep excluded from STANDARD scoring unless explicit profile model exists"
    if missing_required_kpi_gap(row):
        return "run/extend SEC evidence or manual overlay"
    if quality_gap == "COVERED" and not monthly_action:
        return "inspect valuation/score/ranking rules"
    return str(row.get("recommended_next_action", "") or "").strip() or "inspect remaining coverage and ranking constraints"


def holding_sort_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        str(row.get("quality_gap_type", "") or ""),
        str(row.get("ticker", "") or ""),
        str(row.get("isin", "") or ""),
    )


def build_holding_rows(
    gap_rows: list[dict[str, str]],
    score_rows: list[dict[str, str]],
    monthly_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    score_lookup = build_score_lookup(score_rows)
    monthly_lookup = build_monthly_action_lookup(monthly_rows)
    holdings: list[dict[str, str]] = []
    for row in gap_rows:
        ticker = canonicalize_ticker(row.get("ticker", ""))
        score_row = lookup_row(row, score_lookup)
        monthly_action = monthly_lookup.get(ticker, "")
        data_quality_flag = safe_upper(score_row.get("data_quality_flag") or row.get("current_data_quality_flag")) or "MISSING_DATA"
        holdings.append(
            {
                "ticker": ticker,
                "isin": str(row.get("isin", "") or "").strip().upper(),
                "company_name": str(row.get("company_name", "") or "").strip(),
                "asset_type": str(row.get("asset_type", "") or "").strip(),
                "company_type_profile": safe_upper(row.get("company_type_profile", "")),
                "profile_review_status": safe_upper(row.get("profile_review_status", "")),
                "data_quality_flag": data_quality_flag,
                "quality_gap_type": safe_upper(row.get("quality_gap_type", "")),
                "monthly_action": monthly_action,
                "recommended_next_action": recommended_next_action(row, monthly_action),
            }
        )
    holdings.sort(key=holding_sort_key)
    return holdings


def build_summary_rows(
    *,
    review_rows: list[dict[str, str]],
    registry_rows: list[dict[str, str]],
    backlog_rows: list[dict[str, str]],
    gap_summary_rows: list[dict[str, str]],
    gap_rows: list[dict[str, str]],
    score_rows: list[dict[str, str]],
    watchlist_rows: list[dict[str, str]],
    monthly_rows: list[dict[str, str]],
    warnings: list[str],
    gap_summary_warnings: list[str],
    monthly_warnings: list[str],
) -> list[dict[str, str]]:
    approved_rows = [row for row in review_rows if safe_upper(row.get("review_status", "")) == "APPROVED"]
    registry_projected_count = sum(1 for row in registry_rows if safe_upper(row.get("projection_applied", "")) == "TRUE")
    missing_required_count = sum(1 for row in gap_rows if missing_required_kpi_gap(row))
    quality_gap_counter = count_by(gap_rows, "quality_gap_type")
    profile_counter = count_by(gap_rows, "company_type_profile")
    rows = [
        {"metric": "review_rows_total", "value": str(row_count(review_rows)), "notes": "Rows in canonical profile review CSV."},
        {"metric": "approved_profile_rows_total", "value": str(row_count(approved_rows)), "notes": "Rows with review_status=APPROVED."},
        {"metric": "profile_review_unlocked_rows_total", "value": str(registry_projected_count or row_count(approved_rows)), "notes": "Approved profile rows projected into the registry when projection flag is available."},
        {"metric": "registry_rows_total", "value": str(row_count(registry_rows)), "notes": "Rows in profile registry."},
        {"metric": "backlog_rows_total", "value": str(row_count(backlog_rows)), "notes": "Rows in profile review backlog."},
        {"metric": "gap_summary_status", "value": gap_summary_status(gap_summary_rows, gap_summary_warnings), "notes": "Status of gap summary input."},
        {"metric": "monthly_ranking_status", "value": monthly_ranking_status(monthly_rows, monthly_warnings), "notes": "Status of monthly ranking input."},
        {"metric": "score_rows_total", "value": str(row_count(score_rows)), "notes": "Rows in personal company scores."},
        {"metric": "watchlist_rows_total", "value": str(row_count(watchlist_rows)), "notes": "Rows in ranked watchlist."},
        {"metric": "monthly_actions_total", "value": str(row_count(monthly_rows)), "notes": "Rows in monthly ranking."},
        {"metric": "remaining_blocker__MISSING_REQUIRED_KPI", "value": str(missing_required_count), "notes": "Rows with missing required KPI evidence under current profile."},
        {"metric": "warnings_total", "value": str(len(warnings)), "notes": "Warnings produced while reading optional inputs."},
    ]
    rows.extend(counter_rows("review_status", count_by(review_rows, "review_status"), "Canonical profile review status counts."))
    rows.extend(counter_rows("approved_profile", count_by(approved_rows, "proposed_company_type_profile"), "Approved profile counts."))
    rows.extend(counter_rows("registry_profile", count_by(registry_rows, "proposed_company_type_profile"), "Registry proposed profile counts."))
    rows.extend(counter_rows("quality_gap_type", quality_gap_counter, "Gap diagnostics quality gap counts."))
    rows.extend(counter_rows("company_type_profile", profile_counter, "Diagnostics profile counts."))
    rows.extend(counter_rows("score_data_quality", count_by(score_rows, "data_quality_flag"), "Score data quality counts."))
    rows.extend(counter_rows("watchlist_status", count_by(watchlist_rows, "status"), "Watchlist status counts."))
    rows.extend(counter_rows("monthly_action", count_by(monthly_rows, "target_action"), "Monthly target action counts."))
    ensure_metric(rows, "remaining_blocker__PROFILE_REVIEW_MISSING", str(quality_gap_counter.get("PROFILE_REVIEW_MISSING", 0)), "Remaining profile review missing blockers.")
    ensure_metric(rows, "remaining_blocker__NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE", str(quality_gap_counter.get("NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE", 0)), "Remaining non-US or unsupported SEC-scope blockers.")
    ensure_metric(rows, "remaining_blocker__ETF_OR_NON_COMPANY_FUNDAMENTALS", str(quality_gap_counter.get("ETF_OR_NON_COMPANY_FUNDAMENTALS", 0)), "Remaining ETF or non-company fundamentals blockers.")
    ensure_metric(rows, "profile_handling__FINANCIAL", str(profile_counter.get("FINANCIAL", 0)), "Rows requiring financial-company profile handling.")
    ensure_metric(rows, "profile_handling__OTHER", str(profile_counter.get("OTHER", 0)), "Rows requiring OTHER profile handling.")
    for data_quality_flag in ("OK", "REVIEW", "MISSING_DATA", "BLOCKED"):
        ensure_metric(rows, f"score_data_quality__{data_quality_flag}", "0", "Score data quality counts.")
    for monthly_action in ("HOLD_CASH", "DO_NOT_BUY", "BUY_CANDIDATE"):
        ensure_metric(rows, f"monthly_action__{monthly_action}", "0", "Monthly target action counts.")
    rows.sort(key=lambda row: row["metric"])
    return rows


def markdown_count_lines(prefix: str, rows: list[dict[str, str]]) -> list[str]:
    selected = [row for row in rows if row["metric"].startswith(prefix)]
    if not selected:
        return ["- none"]
    return [f"- `{row['metric'].removeprefix(prefix)}` = {row['value']}" for row in selected]


def build_markdown_report(summary_rows: list[dict[str, str]], holding_rows: list[dict[str, str]], warnings: list[str]) -> str:
    summary = {row["metric"]: row["value"] for row in summary_rows}

    def md_cell(value: str) -> str:
        return str(value or "").replace("|", "/").replace("\n", " ").strip()

    lines = [
        "# Personal Profile Review Unlock Report",
        "",
        "## Executive Summary",
        "",
        f"- `review_rows_total` = {summary.get('review_rows_total', '0')}",
        f"- `approved_profile_rows_total` = {summary.get('approved_profile_rows_total', '0')}",
        f"- `registry_rows_total` = {summary.get('registry_rows_total', '0')}",
        f"- `backlog_rows_total` = {summary.get('backlog_rows_total', '0')}",
        f"- `gap_summary_status` = {summary.get('gap_summary_status', 'MISSING')}",
        f"- `monthly_ranking_status` = {summary.get('monthly_ranking_status', 'MISSING')}",
        "",
        "## Profile Review Ergebnis",
        "",
        "### APPROVED nach company_type_profile",
        "",
        *markdown_count_lines("approved_profile__", summary_rows),
        "",
        "### Review Status",
        "",
        *markdown_count_lines("review_status__", summary_rows),
        "",
        "### Separat Markierte Profile",
        "",
        f"- `FINANCIAL` = {summary.get('approved_profile__FINANCIAL', '0')}",
        f"- `OTHER` = {summary.get('approved_profile__OTHER', '0')}",
        "",
        "## Verbleibende Blocker",
        "",
        f"- `PROFILE_REVIEW_MISSING` = {summary.get('remaining_blocker__PROFILE_REVIEW_MISSING', '0')}",
        f"- `MISSING_REQUIRED_KPI` = {summary.get('remaining_blocker__MISSING_REQUIRED_KPI', '0')}",
        f"- `NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE` = {summary.get('remaining_blocker__NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE', '0')}",
        f"- `ETF_OR_NON_COMPANY_FUNDAMENTALS` = {summary.get('remaining_blocker__ETF_OR_NON_COMPANY_FUNDAMENTALS', '0')}",
        f"- `FINANCIAL profile handling` = {summary.get('profile_handling__FINANCIAL', '0')}",
        f"- `OTHER profile handling` = {summary.get('profile_handling__OTHER', '0')}",
        "",
        "## Downstream-Auswirkung",
        "",
        f"- `score_rows_total` = {summary.get('score_rows_total', '0')}",
        f"- `score OK` = {summary.get('score_data_quality__OK', '0')}",
        f"- `score REVIEW` = {summary.get('score_data_quality__REVIEW', '0')}",
        f"- `score MISSING_DATA` = {summary.get('score_data_quality__MISSING_DATA', '0')}",
        f"- `score BLOCKED` = {summary.get('score_data_quality__BLOCKED', '0')}",
        f"- `watchlist_rows_total` = {summary.get('watchlist_rows_total', '0')}",
        f"- `monthly_actions_total` = {summary.get('monthly_actions_total', '0')}",
        f"- `HOLD_CASH` = {summary.get('monthly_action__HOLD_CASH', '0')}",
        f"- `DO_NOT_BUY` = {summary.get('monthly_action__DO_NOT_BUY', '0')}",
        f"- `BUY_CANDIDATE` = {summary.get('monthly_action__BUY_CANDIDATE', '0')}",
        "",
        "## Next Action Table",
        "",
        "| ticker | isin | company_name | asset_type | profile | profile_review_status | data_quality_flag | quality_gap_type | monthly_action | recommended_next_action |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in holding_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["ticker"],
                    row["isin"],
                    md_cell(row["company_name"]),
                    row["asset_type"],
                    row["company_type_profile"],
                    row["profile_review_status"],
                    row["data_quality_flag"],
                    row["quality_gap_type"],
                    row["monthly_action"],
                    md_cell(row["recommended_next_action"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.extend(f"- `{warning}`" for warning in warnings)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def run_personal_profile_review_unlock_report(
    *,
    profile_review_input: str = DEFAULT_PROFILE_REVIEW_INPUT,
    profile_registry_input: str = DEFAULT_PROFILE_REGISTRY_INPUT,
    profile_backlog_input: str = DEFAULT_PROFILE_BACKLOG_INPUT,
    gap_summary_input: str = DEFAULT_GAP_SUMMARY_INPUT,
    gap_diagnostics_input: str = DEFAULT_GAP_DIAGNOSTICS_INPUT,
    scores_input: str = DEFAULT_SCORES_INPUT,
    watchlist_input: str = DEFAULT_WATCHLIST_INPUT,
    monthly_input: str = DEFAULT_MONTHLY_INPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    holdings_output: str = DEFAULT_HOLDINGS_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> UnlockReportResult:
    warnings: list[str] = []
    review_rows, row_warnings = optional_csv_rows(profile_review_input, "profile_review_input")
    warnings.extend(row_warnings)
    registry_rows, row_warnings = optional_csv_rows(profile_registry_input, "profile_registry_input")
    warnings.extend(row_warnings)
    backlog_rows, row_warnings = optional_csv_rows(profile_backlog_input, "profile_backlog_input")
    warnings.extend(row_warnings)
    gap_summary_rows, gap_summary_warnings = optional_csv_rows(gap_summary_input, "gap_summary_input")
    warnings.extend(gap_summary_warnings)
    gap_rows, row_warnings = optional_csv_rows(gap_diagnostics_input, "gap_diagnostics_input")
    warnings.extend(row_warnings)
    score_rows, row_warnings = optional_csv_rows(scores_input, "scores_input")
    warnings.extend(row_warnings)
    watchlist_rows, row_warnings = optional_csv_rows(watchlist_input, "watchlist_input")
    warnings.extend(row_warnings)
    monthly_rows, monthly_warnings = optional_csv_rows(monthly_input, "monthly_input")
    warnings.extend(monthly_warnings)

    holding_rows = build_holding_rows(gap_rows, score_rows, monthly_rows)
    summary_rows = build_summary_rows(
        review_rows=review_rows,
        registry_rows=registry_rows,
        backlog_rows=backlog_rows,
        gap_summary_rows=gap_summary_rows,
        gap_rows=gap_rows,
        score_rows=score_rows,
        watchlist_rows=watchlist_rows,
        monthly_rows=monthly_rows,
        warnings=warnings,
        gap_summary_warnings=gap_summary_warnings,
        monthly_warnings=monthly_warnings,
    )

    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    holdings_path = write_csv_rows(holdings_output, HOLDING_FIELDS, holding_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_markdown_report(summary_rows, holding_rows, warnings), encoding="utf-8")

    return UnlockReportResult(
        summary_output=summary_path,
        holdings_output=holdings_path,
        report_output=report_path,
        summary_rows=summary_rows,
        holding_rows=holding_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a profile-review unlock delta report from existing personal processed artifacts.")
    parser.add_argument("--profile-review-input", default=DEFAULT_PROFILE_REVIEW_INPUT)
    parser.add_argument("--profile-registry-input", default=DEFAULT_PROFILE_REGISTRY_INPUT)
    parser.add_argument("--profile-backlog-input", default=DEFAULT_PROFILE_BACKLOG_INPUT)
    parser.add_argument("--gap-summary-input", default=DEFAULT_GAP_SUMMARY_INPUT)
    parser.add_argument("--gap-diagnostics-input", default=DEFAULT_GAP_DIAGNOSTICS_INPUT)
    parser.add_argument("--scores-input", default=DEFAULT_SCORES_INPUT)
    parser.add_argument("--watchlist-input", default=DEFAULT_WATCHLIST_INPUT)
    parser.add_argument("--monthly-input", default=DEFAULT_MONTHLY_INPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--holdings-output", default=DEFAULT_HOLDINGS_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_personal_profile_review_unlock_report(
        profile_review_input=args.profile_review_input,
        profile_registry_input=args.profile_registry_input,
        profile_backlog_input=args.profile_backlog_input,
        gap_summary_input=args.gap_summary_input,
        gap_diagnostics_input=args.gap_diagnostics_input,
        scores_input=args.scores_input,
        watchlist_input=args.watchlist_input,
        monthly_input=args.monthly_input,
        summary_output=args.summary_output,
        holdings_output=args.holdings_output,
        report_output=args.report_output,
    )


if __name__ == "__main__":
    main()
