from __future__ import annotations

import argparse
import html
import json
import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from src.common import read_csv_rows, resolve_repo_path
from src.dashboard_engine import (
    DASHBOARD_KPI_FIELDS,
    DASHBOARD_SECTION_FIELDS,
    DASHBOARD_SUMMARY_FIELDS,
    DEFAULT_KPI_OUTPUT,
    DEFAULT_SECTIONS_OUTPUT,
    DEFAULT_SUMMARY_OUTPUT,
    NOT_AVAILABLE,
)

LOGGER = logging.getLogger(__name__)
JSON_CONTENT_TYPE = "application/json; charset=utf-8"
HTML_CONTENT_TYPE = "text/html; charset=utf-8"
DEFAULT_POSITIONS_OUTPUT = "data/processed/personal_positions_snapshot.csv"
DEFAULT_HOLDINGS_OUTPUT = "data/processed/personal_portfolio_holdings_action_table.csv"
DEFAULT_MONTHLY_BUY_RANKING_OUTPUT = "data/processed/personal_monthly_buy_ranking.csv"
DEFAULT_REBALANCE_PROPOSALS_OUTPUT = "data/processed/personal_rebalance_proposals.csv"
DEFAULT_WATCHLIST_OUTPUT = "data/processed/personal_watchlist_ranked.csv"
DEFAULT_FUNDAMENTALS_COVERAGE_OUTPUT = "data/processed/personal_fundamentals_coverage.csv"
DEFAULT_RESEARCH_PRIORITY_OUTPUT = "data/processed/personal_research_priority.csv"
DEFAULT_COST_TAX_LEDGER_OUTPUT = "data/processed/cost_tax_ledger_normalized.csv"
DEFAULT_PORTFOLIO_TIMESERIES_OUTPUT = "data/processed/portfolio_timeseries.csv"
DEFAULT_BENCHMARK_TIMESERIES_OUTPUT = "data/processed/benchmark_timeseries_normalized.csv"
DEFAULT_READINESS_PAYLOAD_OUTPUT = "data/processed/dashboard_readiness_payload.json"

POSITIONS_FIELDS = [
    "portfolio_date",
    "isin",
    "ticker",
    "company_name",
    "asset_type",
    "sleeve",
    "market_value",
    "market_value_eur",
    "mandate_fit",
    "data_quality_flag",
    "review_flag",
    "weight_total_assets_pct",
]
HOLDINGS_FIELDS = [
    "ticker",
    "company_name",
    "asset_type",
    "sleeve",
    "market_value",
    "current_weight",
    "business_score",
    "valuation_score",
    "buy_score",
    "mandate_fit",
    "purchase_readiness",
    "portfolio_action",
    "portfolio_action_reason",
    "data_quality_flag",
    "review_flag",
]
MONTHLY_BUY_RANKING_FIELDS = [
    "rank",
    "ticker",
    "company_name",
    "current_weight",
    "target_action",
    "allocation_status",
    "suggested_buy_amount_eur",
    "rationale",
    "constraint_checks",
    "valuation_comment",
    "mandate_fit_comment",
]
REBALANCE_PROPOSALS_FIELDS = ["ticker", "company_name", "action", "current_weight_pct", "reason"]
WATCHLIST_FIELDS = [
    "ticker",
    "company_name",
    "sector",
    "country",
    "asset_type",
    "sleeve",
    "business_score",
    "valuation_score",
    "buy_score",
    "mandate_fit",
    "status",
    "data_quality_flag",
    "thesis_summary",
    "main_risks",
]
FUNDAMENTALS_COVERAGE_FIELDS = [
    "holding_name",
    "ticker",
    "isin",
    "asset_type",
    "company_type_profile",
    "match_status",
    "match_method",
    "data_quality_flag",
    "missing_required_kpis",
    "optional_missing_kpis",
    "needs_research_flag",
    "profile_classification_warning_flag",
    "profile_classification_warning_reason",
    "notes",
]
RESEARCH_PRIORITY_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "asset_type",
    "company_type_profile",
    "market_value_eur",
    "weight_total_assets_pct",
    "missing_required_kpi_count",
    "needs_research_flag",
    "coverage_status",
    "research_priority",
    "research_priority_reason",
]
LEDGER_FIELDS = [
    "event_date",
    "broker",
    "document_type",
    "event_type",
    "instrument_name",
    "ticker",
    "isin",
    "currency",
    "gross_amount",
    "net_amount",
    "fee_amount",
    "tax_amount",
    "withholding_tax_amount",
    "verification_status",
    "data_quality_flag",
    "notes",
]


@dataclass(frozen=True)
class DashboardPaths:
    kpis: str = DEFAULT_KPI_OUTPUT
    sections: str = DEFAULT_SECTIONS_OUTPUT
    summary: str = DEFAULT_SUMMARY_OUTPUT
    positions: str = DEFAULT_POSITIONS_OUTPUT
    holdings: str = DEFAULT_HOLDINGS_OUTPUT
    monthly_buy_ranking: str = DEFAULT_MONTHLY_BUY_RANKING_OUTPUT
    rebalance_proposals: str = DEFAULT_REBALANCE_PROPOSALS_OUTPUT
    watchlist: str = DEFAULT_WATCHLIST_OUTPUT
    fundamentals_coverage: str = DEFAULT_FUNDAMENTALS_COVERAGE_OUTPUT
    research_priority: str = DEFAULT_RESEARCH_PRIORITY_OUTPUT
    cost_tax_ledger: str = DEFAULT_COST_TAX_LEDGER_OUTPUT
    portfolio_timeseries: str = DEFAULT_PORTFOLIO_TIMESERIES_OUTPUT
    benchmark_timeseries: str = DEFAULT_BENCHMARK_TIMESERIES_OUTPUT
    readiness_payload: str = DEFAULT_READINESS_PAYLOAD_OUTPUT

    def all_paths(self) -> list[str]:
        return [
            self.kpis,
            self.sections,
            self.summary,
            self.positions,
            self.holdings,
            self.monthly_buy_ranking,
            self.rebalance_proposals,
            self.watchlist,
            self.fundamentals_coverage,
            self.research_priority,
            self.cost_tax_ledger,
            self.portfolio_timeseries,
            self.benchmark_timeseries,
            self.readiness_payload,
        ]


@dataclass
class CacheEntry:
    mtime: float | None
    payload: Any


def validate_host(host: str) -> str:
    normalized = str(host or "").strip()
    if not normalized:
        raise ValueError("dashboard_server requires --host 127.0.0.1; blank host is not allowed.")
    if normalized != "127.0.0.1":
        raise ValueError(f"dashboard_server only supports --host 127.0.0.1 for local-only usage; got {normalized!r}.")
    return normalized


def not_available_payload(path_value: str | Path) -> dict[str, str]:
    return {"status": NOT_AVAILABLE, "path": str(resolve_repo_path(path_value))}


def artifact_mtime(path_value: str | Path) -> float | None:
    resolved = resolve_repo_path(path_value)
    try:
        return os.path.getmtime(resolved)
    except FileNotFoundError:
        return None


def latest_mtime(paths: list[str | Path]) -> str:
    mtimes = [mtime for mtime in (artifact_mtime(path) for path in paths) if mtime is not None]
    if not mtimes:
        return NOT_AVAILABLE
    return datetime.fromtimestamp(max(mtimes)).astimezone().isoformat()


def load_csv_table(
    path_value: str | Path,
    required_columns: list[str] | tuple[str, ...] | None = None,
    source_name: str | None = None,
) -> list[dict[str, str]] | dict[str, str]:
    resolved = resolve_repo_path(path_value)
    if not resolved.exists():
        return not_available_payload(path_value)
    rows = read_csv_rows(path_value)
    if not rows:
        return not_available_payload(path_value)
    required = list(required_columns or [])
    if required:
        missing = [field for field in required if field not in rows[0]]
        if missing:
            label = source_name or "CSV"
            raise ValueError(f"{label} ({resolved}) missing required columns: {', '.join(missing)}")
    return rows


def load_json_payload(path_value: str | Path) -> dict[str, Any]:
    resolved = resolve_repo_path(path_value)
    if not resolved.exists():
        return not_available_payload(path_value)
    with resolved.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload ({resolved}) must contain an object.")
    return payload


def load_kpis(path_value: str | Path) -> list[dict[str, str]] | dict[str, str]:
    return load_csv_table(path_value, DASHBOARD_KPI_FIELDS, "dashboard KPI CSV")


def load_sections(path_value: str | Path) -> list[dict[str, str]] | dict[str, str]:
    return load_csv_table(path_value, DASHBOARD_SECTION_FIELDS, "dashboard sections CSV")


def load_summary(path_value: str | Path) -> dict[str, str]:
    rows = load_csv_table(path_value, DASHBOARD_SUMMARY_FIELDS, "dashboard summary CSV")
    if is_not_available(rows):
        return rows
    return rows[0]


def load_positions(path_value: str | Path) -> list[dict[str, str]] | dict[str, str]:
    return load_csv_table(path_value, POSITIONS_FIELDS, "positions snapshot CSV")


def load_holdings(path_value: str | Path) -> list[dict[str, str]] | dict[str, str]:
    return load_csv_table(path_value, HOLDINGS_FIELDS, "holdings action table CSV")


def load_monthly_buy_ranking(path_value: str | Path) -> list[dict[str, str]] | dict[str, str]:
    return load_csv_table(path_value, MONTHLY_BUY_RANKING_FIELDS, "monthly buy ranking CSV")


def load_rebalance_proposals(path_value: str | Path) -> list[dict[str, str]] | dict[str, str]:
    return load_csv_table(path_value, REBALANCE_PROPOSALS_FIELDS, "rebalance proposals CSV")


def load_watchlist(path_value: str | Path) -> list[dict[str, str]] | dict[str, str]:
    return load_csv_table(path_value, WATCHLIST_FIELDS, "watchlist CSV")


def load_fundamentals_coverage(path_value: str | Path) -> list[dict[str, str]] | dict[str, str]:
    return load_csv_table(path_value, FUNDAMENTALS_COVERAGE_FIELDS, "fundamentals coverage CSV")


def load_research_priority(path_value: str | Path) -> list[dict[str, str]] | dict[str, str]:
    return load_csv_table(path_value, RESEARCH_PRIORITY_FIELDS, "research priority CSV")


def load_cost_tax_ledger(path_value: str | Path) -> list[dict[str, str]] | dict[str, str]:
    return load_csv_table(path_value, LEDGER_FIELDS, "cost tax ledger CSV")


def load_portfolio_timeseries(path_value: str | Path) -> list[dict[str, str]] | dict[str, str]:
    return load_csv_table(path_value, ["date"], "portfolio timeseries CSV")


def load_benchmark_timeseries(path_value: str | Path) -> list[dict[str, str]] | dict[str, str]:
    return load_csv_table(path_value, ["date"], "benchmark timeseries CSV")


class ArtifactCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, CacheEntry] = {}

    def get(self, path_value: str | Path, loader: Callable[[str | Path], Any]) -> Any:
        resolved = str(resolve_repo_path(path_value))
        observed_mtime = artifact_mtime(path_value)
        with self._lock:
            entry = self._entries.get(resolved)
            if entry is not None and entry.mtime == observed_mtime:
                return entry.payload
            payload = loader(path_value)
            self._entries[resolved] = CacheEntry(mtime=observed_mtime, payload=payload)
            return payload


def is_not_available(payload: Any) -> bool:
    return isinstance(payload, dict) and payload.get("status") == NOT_AVAILABLE


def section_sort_key(row: dict[str, str]) -> tuple[int, str, str]:
    raw_order = str(row.get("display_order", "") or "").strip()
    try:
        order = int(raw_order)
    except ValueError:
        order = 10**9
    return (
        order,
        str(row.get("section_name", "") or "").strip(),
        str(row.get("display_label", "") or "").strip(),
    )


def row_count(payload: Any) -> int:
    if is_not_available(payload):
        return 0
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        return 1
    return 0


def text_value(row: dict[str, Any], field: str) -> str:
    return str(row.get(field, "") or "").strip()


def first_non_blank(row: dict[str, Any], fields: list[str] | tuple[str, ...], default: str = "") -> str:
    for field in fields:
        value = text_value(row, field)
        if value:
            return value
    return default


def parse_number(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def normalize_class_suffix(value: str) -> str:
    return "".join(character.lower() if character.isalnum() else "-" for character in value).strip("-") or "empty"


def bool_badge_text(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"true", "1", "yes"}:
        return "TRUE"
    if normalized in {"false", "0", "no"}:
        return "FALSE"
    return str(value or NOT_AVAILABLE).strip() or NOT_AVAILABLE


def render_badge(value: str, family: str = "status") -> str:
    normalized_value = str(value or NOT_AVAILABLE).strip() or NOT_AVAILABLE
    label = bool_badge_text(normalized_value) if family == "bool" else normalized_value
    classes = f"badge {family} {family}-{normalize_class_suffix(label)}"
    return f"<span class='{classes}'>{html.escape(label)}</span>"


def render_summary_block(summary: dict[str, str]) -> str:
    if is_not_available(summary):
        return (
            "<section class='summary unavailable'>"
            "<h2>Summary</h2>"
            f"<p>{html.escape(summary['status'])}: {html.escape(summary['path'])}</p>"
            "</section>"
        )
    cards = [
        ("Snapshot Date", summary.get("snapshot_date", "")),
        ("Dashboard Quality", summary.get("dashboard_data_quality_flag", "")),
        ("Performance Mode", summary.get("performance_measurement_mode", "")),
        ("Ledger Mode", summary.get("ledger_measurement_mode", "")),
        ("Total Assets", summary.get("total_assets", "")),
        ("Weighted Buy Score", summary.get("weighted_buy_score", "")),
        ("Missing Blocks", summary.get("missing_block_count", "")),
    ]
    body = "".join(
        "<div class='summary-card'>"
        f"<div class='summary-label'>{html.escape(label)}</div>"
        f"<div class='summary-value'>{html.escape(value or NOT_AVAILABLE)}</div>"
        "</div>"
        for label, value in cards
    )
    return f"<section class='summary'><h2>Summary</h2><div class='summary-grid'>{body}</div></section>"


def render_not_available_block(title: str, payload: dict[str, str]) -> str:
    return (
        "<section class='panel unavailable'>"
        f"<h2>{html.escape(title)}</h2>"
        f"<p>{html.escape(payload['status'])}: {html.escape(payload['path'])}</p>"
        "</section>"
    )


def render_legacy_sections(sections: list[dict[str, str]] | dict[str, str]) -> str:
    if is_not_available(sections):
        return render_not_available_block("Processed KPI Blocks", sections)

    grouped: dict[str, list[dict[str, str]]] = {}
    ordered_rows = sorted(sections, key=section_sort_key)
    for row in ordered_rows:
        grouped.setdefault(text_value(row, "section_name"), []).append(row)

    blocks: list[str] = []
    for section_name, rows in grouped.items():
        block_status = text_value(rows[0], "block_status") or NOT_AVAILABLE
        table_rows = "".join(
            "<tr>"
            f"<th>{html.escape(text_value(row, 'display_label'))}</th>"
            f"<td>{html.escape(text_value(row, 'value_display') or NOT_AVAILABLE)}</td>"
            f"<td>{render_badge(text_value(row, 'data_quality_flag') or NOT_AVAILABLE, 'quality')}</td>"
            "</tr>"
            for row in rows
        )
        blocks.append(
            "<section class='panel'>"
            f"<h2><span>{html.escape(section_name)}</span>{render_badge(block_status)}</h2>"
            "<table>"
            "<thead><tr><th>Metric</th><th>Value</th><th>Data Quality</th></tr></thead>"
            f"<tbody>{table_rows}</tbody>"
            "</table>"
            "</section>"
        )
    return (
        "<section class='panel-stack'>"
        "<div class='panel-intro'><h2>Processed KPI Blocks</h2><p>Original dashboard KPI sections from dashboard_sections.csv.</p></div>"
        f"{''.join(blocks)}"
        "</section>"
    )


def build_action_counts(rows: list[dict[str, str]] | dict[str, str]) -> dict[str, int]:
    if is_not_available(rows):
        return {}
    counts: dict[str, int] = {}
    for row in rows:
        action = text_value(row, "portfolio_action") or NOT_AVAILABLE
        counts[action] = counts.get(action, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def build_sleeve_allocation(positions: list[dict[str, str]] | dict[str, str]) -> tuple[list[dict[str, str]], str, str]:
    if is_not_available(positions):
        return [], "NOT_AVAILABLE", "NOT_AVAILABLE"
    grouped: dict[str, dict[str, float]] = {}
    value_field_used = "market_value_eur"
    weight_field_used = "weight_total_assets_pct"
    for row in positions:
        sleeve = text_value(row, "sleeve") or NOT_AVAILABLE
        grouped.setdefault(sleeve, {"market_value": 0.0, "weight": 0.0})
        value = parse_number(first_non_blank(row, ["market_value_eur", "market_value"]))
        weight = parse_number(first_non_blank(row, ["weight_total_assets_pct", "current_weight"]))
        if value is not None:
            grouped[sleeve]["market_value"] += value
        if weight is not None:
            grouped[sleeve]["weight"] += weight
    rows = [
        {
            "sleeve": sleeve,
            "market_value": f"{values['market_value']:.2f}",
            "weight": f"{values['weight']:.2f}",
        }
        for sleeve, values in sorted(grouped.items(), key=lambda item: (-item[1]["weight"], item[0]))
    ]
    return rows, value_field_used, weight_field_used


def build_concentration_rows(positions: list[dict[str, str]] | dict[str, str], top_n: int = 10) -> tuple[list[dict[str, str]], str]:
    if is_not_available(positions):
        return [], "NOT_AVAILABLE"
    sortable_rows: list[tuple[float, dict[str, str]]] = []
    weight_field_used = "weight_total_assets_pct"
    for row in positions:
        weight_text = first_non_blank(row, ["weight_total_assets_pct", "current_weight"])
        weight_value = parse_number(weight_text)
        if weight_value is None:
            continue
        sortable_rows.append(
            (
                weight_value,
                {
                    "ticker": text_value(row, "ticker") or text_value(row, "isin") or NOT_AVAILABLE,
                    "company_name": text_value(row, "company_name") or text_value(row, "raw_name") or NOT_AVAILABLE,
                    "asset_type": text_value(row, "asset_type") or NOT_AVAILABLE,
                    "weight": weight_text,
                },
            )
        )
    sortable_rows.sort(key=lambda item: (-item[0], item[1]["ticker"]))
    return [row for _weight, row in sortable_rows[:top_n]], weight_field_used


def build_history_status(
    portfolio_rows: list[dict[str, str]] | dict[str, str],
    benchmark_rows: list[dict[str, str]] | dict[str, str],
    min_points: int = 12,
) -> dict[str, Any]:
    portfolio_points = row_count(portfolio_rows) if not is_not_available(portfolio_rows) else 0
    benchmark_points = row_count(benchmark_rows) if not is_not_available(benchmark_rows) else 0
    chart_status = "AVAILABLE" if portfolio_points >= min_points and benchmark_points >= min_points else "INSUFFICIENT_HISTORY"
    message = (
        f"Zeitreihen-Chart wird erst ab {min_points} Datenpunkten dargestellt. "
        f"Aktuell: portfolio={portfolio_points}, benchmark={benchmark_points}."
    )
    if chart_status == "AVAILABLE":
        message = f"Zeitreihen-Chart basiert auf realen Punkten. Aktuell: portfolio={portfolio_points}, benchmark={benchmark_points}."
    return {
        "portfolio_points": portfolio_points,
        "benchmark_points": benchmark_points,
        "min_required_points": min_points,
        "chart_status": chart_status,
        "message": message,
    }


def build_history_series(
    portfolio_rows: list[dict[str, str]] | dict[str, str],
    benchmark_rows: list[dict[str, str]] | dict[str, str],
) -> dict[str, list[tuple[str, float]]]:
    if is_not_available(portfolio_rows) or is_not_available(benchmark_rows):
        return {"portfolio": [], "benchmark": []}
    portfolio_series: list[tuple[str, float]] = []
    benchmark_series: list[tuple[str, float]] = []
    for row in portfolio_rows:
        value = parse_number(first_non_blank(row, ["portfolio_nav_eur", "portfolio_value_eur"]))
        date = text_value(row, "date")
        if value is not None and date:
            portfolio_series.append((date, value))
    for row in benchmark_rows:
        value = parse_number(first_non_blank(row, ["benchmark_reference_value", "total_return_index", "adjusted_close", "close"]))
        date = text_value(row, "date")
        if value is not None and date:
            benchmark_series.append((date, value))
    return {"portfolio": portfolio_series, "benchmark": benchmark_series}


def render_history_chart(history_series: dict[str, list[tuple[str, float]]]) -> str:
    all_points = history_series["portfolio"] + history_series["benchmark"]
    if not all_points:
        return "<p class='muted'>Keine darstellbaren Zeitreihenpunkte vorhanden.</p>"
    values = [point[1] for point in all_points]
    min_value = min(values)
    max_value = max(values)
    span = max(max_value - min_value, 1.0)
    width = 720
    height = 240
    padding = 24

    def to_polyline(points: list[tuple[str, float]]) -> str:
        if len(points) == 1:
            x = width / 2
            y = padding + (max_value - points[0][1]) / span * (height - (padding * 2))
            return f"{x:.1f},{y:.1f}"
        parts: list[str] = []
        denominator = max(len(points) - 1, 1)
        for index, (_date, value) in enumerate(points):
            x = padding + (index / denominator) * (width - (padding * 2))
            y = padding + (max_value - value) / span * (height - (padding * 2))
            parts.append(f"{x:.1f},{y:.1f}")
        return " ".join(parts)

    portfolio_polyline = to_polyline(history_series["portfolio"])
    benchmark_polyline = to_polyline(history_series["benchmark"])
    return (
        "<div class='chart-shell'>"
        f"<svg viewBox='0 0 {width} {height}' role='img' aria-label='Portfolio and benchmark history chart'>"
        f"<polyline class='chart-line portfolio' fill='none' points='{portfolio_polyline}'></polyline>"
        f"<polyline class='chart-line benchmark' fill='none' points='{benchmark_polyline}'></polyline>"
        "</svg>"
        "<div class='chart-legend'>"
        "<span><span class='legend-swatch portfolio'></span>Portfolio</span>"
        "<span><span class='legend-swatch benchmark'></span>Benchmark</span>"
        "</div>"
        "</div>"
    )


def render_cards(title: str, cards: list[tuple[str, str, str]]) -> str:
    body = "".join(
        "<div class='summary-card'>"
        f"<div class='summary-label'>{html.escape(label)}</div>"
        f"<div class='summary-value'>{html.escape(value)}</div>"
        f"<div class='summary-detail'>{html.escape(detail)}</div>"
        "</div>"
        for label, value, detail in cards
    )
    return f"<section class='panel'><h2>{html.escape(title)}</h2><div class='summary-grid'>{body}</div></section>"


def render_action_counts(action_counts: dict[str, int]) -> str:
    if not action_counts:
        return "<p class='muted'>Keine Holdings-Action-Daten verfuegbar.</p>"
    cards = "".join(
        "<div class='action-card'>"
        f"{render_badge(action, 'action')}"
        f"<div class='summary-value'>{count}</div>"
        "</div>"
        for action, count in action_counts.items()
    )
    return f"<div class='action-grid'>{cards}</div>"


def render_bar_list(title: str, rows: list[dict[str, str]], label_field: str, value_field: str, unit: str, note: str) -> str:
    if not rows:
        return (
            "<section class='panel'>"
            f"<h2>{html.escape(title)}</h2>"
            "<p class='muted'>Keine Daten verfuegbar.</p>"
            "</section>"
        )
    numeric_values = [parse_number(row.get(value_field, "")) or 0.0 for row in rows]
    max_value = max(numeric_values) if numeric_values else 1.0
    items = []
    for row, numeric_value in zip(rows, numeric_values):
        width_pct = 0.0 if max_value <= 0 else (numeric_value / max_value) * 100.0
        label = text_value(row, label_field) or NOT_AVAILABLE
        display_value = text_value(row, value_field) or NOT_AVAILABLE
        items.append(
            "<li class='bar-item'>"
            "<div class='bar-copy'>"
            f"<strong>{html.escape(label)}</strong>"
            f"<span>{html.escape(display_value)} {html.escape(unit)}</span>"
            "</div>"
            f"<div class='bar-track'><div class='bar-fill' style='width:{width_pct:.1f}%'></div></div>"
            "</li>"
        )
    return (
        "<section class='panel'>"
        f"<h2>{html.escape(title)}</h2>"
        f"<p class='muted'>{html.escape(note)}</p>"
        f"<ol class='bar-list'>{''.join(items)}</ol>"
        "</section>"
    )


def render_table(
    table_id: str,
    title: str,
    rows: list[dict[str, str]] | dict[str, str],
    columns: list[tuple[str, str]],
    *,
    badge_columns: dict[str, str] | None = None,
    searchable: bool = True,
    default_sort_column: str | None = None,
) -> str:
    if is_not_available(rows):
        return render_not_available_block(title, rows)
    if not rows:
        return (
            "<section class='panel'>"
            f"<h2>{html.escape(title)}</h2>"
            "<p class='muted'>Leere Tabelle.</p>"
            "</section>"
        )
    badges = badge_columns or {}
    search_html = (
        f"<input class='table-filter' type='search' aria-label='Filter {html.escape(title)}' placeholder='Filter {html.escape(title)}' data-table-target='{html.escape(table_id)}'>"
        if searchable
        else ""
    )
    headers = "".join(
        "<th>"
        f"<button type='button' class='sort-button' data-table-target='{html.escape(table_id)}' data-sort-key='{html.escape(key)}'>{html.escape(label)}</button>"
        "</th>"
        for key, label in columns
    )
    body_rows: list[str] = []
    for row in rows:
        cells = []
        for key, _label in columns:
            value = text_value(row, key) or NOT_AVAILABLE
            family = badges.get(key)
            rendered = render_badge(value, family) if family else html.escape(value)
            cells.append(f"<td data-column='{html.escape(key)}'>{rendered}</td>")
        sort_value = html.escape(text_value(row, default_sort_column or columns[0][0]) or NOT_AVAILABLE)
        text_blob = html.escape(" ".join(text_value(row, key) for key, _label in columns))
        body_rows.append(
            f"<tr data-sort-value='{sort_value}' data-row-search='{text_blob}'>"
            f"{''.join(cells)}"
            "</tr>"
        )
    return (
        "<section class='panel'>"
        f"<h2>{html.escape(title)}</h2>"
        f"<div class='table-toolbar'>{search_html}</div>"
        f"<div class='table-wrap'><table id='{html.escape(table_id)}'>"
        f"<thead><tr>{headers}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table></div>"
        "</section>"
    )


def render_decision_overview(
    holdings: list[dict[str, str]] | dict[str, str],
    positions: list[dict[str, str]] | dict[str, str],
) -> str:
    action_counts = build_action_counts(holdings)
    sleeve_rows, value_field_used, weight_field_used = build_sleeve_allocation(positions)
    concentration_rows, concentration_weight_field = build_concentration_rows(positions)
    holdings_count = str(row_count(holdings))
    positions_count = str(row_count(positions))
    overview_cards = render_cards(
        "Decision Overview",
        [
            ("Holdings Rows", holdings_count, "Rows aus personal_portfolio_holdings_action_table.csv"),
            ("Positions Rows", positions_count, "Rows aus personal_positions_snapshot.csv"),
            ("Action Types", str(len(action_counts)), "Abgeleitet aus portfolio_action"),
        ],
    )
    actions_html = (
        "<section class='panel'>"
        "<h2>Action Counts</h2>"
        f"{render_action_counts(action_counts)}"
        "</section>"
    )
    sleeve_html = render_bar_list(
        "Sleeve Allocation",
        [{"label": row["sleeve"], "value": row["weight"]} for row in sleeve_rows],
        "label",
        "value",
        "%",
        f"Quelle: {weight_field_used}; Marktwerte aus {value_field_used}.",
    )
    concentration_html = render_bar_list(
        "Concentration Top 10",
        [{"label": f"{row['ticker']} - {row['company_name']}", "value": row["weight"]} for row in concentration_rows],
        "label",
        "value",
        "%",
        f"Gewichtsfeld: {concentration_weight_field}. Cash wird nicht entfernt.",
    )
    return overview_cards + actions_html + sleeve_html + concentration_html


def render_history_panel(
    portfolio_rows: list[dict[str, str]] | dict[str, str],
    benchmark_rows: list[dict[str, str]] | dict[str, str],
) -> str:
    history_status = build_history_status(portfolio_rows, benchmark_rows)
    body = (
        "<section class='panel'>"
        "<h2>Performance History</h2>"
        f"<p>{html.escape(history_status['message'])}</p>"
        f"<p class='muted'>Status: {history_status['chart_status']} | min_required_points={history_status['min_required_points']}</p>"
    )
    if history_status["chart_status"] == "AVAILABLE":
        body += render_history_chart(build_history_series(portfolio_rows, benchmark_rows))
    body += "</section>"
    return body


def render_index_html(
    kpis: list[dict[str, str]] | dict[str, str],
    sections: list[dict[str, str]] | dict[str, str],
    summary: dict[str, str],
    holdings: list[dict[str, str]] | dict[str, str],
    positions: list[dict[str, str]] | dict[str, str],
    monthly_buy_ranking: list[dict[str, str]] | dict[str, str],
    rebalance_proposals: list[dict[str, str]] | dict[str, str],
    watchlist: list[dict[str, str]] | dict[str, str],
    fundamentals_coverage: list[dict[str, str]] | dict[str, str],
    research_priority: list[dict[str, str]] | dict[str, str],
    cost_tax_ledger: list[dict[str, str]] | dict[str, str],
    portfolio_timeseries: list[dict[str, str]] | dict[str, str],
    benchmark_timeseries: list[dict[str, str]] | dict[str, str],
    data_mtime: str,
) -> str:
    kpi_count = "NOT_AVAILABLE" if is_not_available(kpis) else str(len(kpis))
    decision_overview_html = render_decision_overview(holdings, positions)
    holdings_html = render_table(
        "holdings-detail",
        "Holdings Detail",
        holdings,
        [
            ("ticker", "Ticker"),
            ("company_name", "Company"),
            ("asset_type", "Asset Type"),
            ("sleeve", "Sleeve"),
            ("market_value", "Market Value"),
            ("current_weight", "Current Weight"),
            ("business_score", "Business"),
            ("valuation_score", "Valuation"),
            ("buy_score", "Buy"),
            ("mandate_fit", "Mandate Fit"),
            ("purchase_readiness", "Readiness"),
            ("portfolio_action", "Action"),
            ("data_quality_flag", "Data Quality"),
            ("review_flag", "Review Flag"),
            ("portfolio_action_reason", "Reason"),
        ],
        badge_columns={"portfolio_action": "action", "data_quality_flag": "quality", "review_flag": "bool"},
        default_sort_column="ticker",
    )
    monthly_html = render_table(
        "monthly-buy-ranking",
        "Monthly Buy Ranking",
        monthly_buy_ranking,
        [
            ("rank", "Rank"),
            ("ticker", "Ticker"),
            ("company_name", "Company"),
            ("current_weight", "Current Weight"),
            ("target_action", "Target Action"),
            ("allocation_status", "Allocation Status"),
            ("suggested_buy_amount_eur", "Suggested Buy EUR"),
            ("rationale", "Rationale"),
            ("constraint_checks", "Constraint Checks"),
            ("valuation_comment", "Valuation Comment"),
            ("mandate_fit_comment", "Mandate Fit Comment"),
        ],
        badge_columns={"target_action": "action", "allocation_status": "status"},
        default_sort_column="rank",
    )
    watchlist_html = render_table(
        "watchlist",
        "Watchlist",
        watchlist,
        [
            ("ticker", "Ticker"),
            ("company_name", "Company"),
            ("sector", "Sector"),
            ("country", "Country"),
            ("asset_type", "Asset Type"),
            ("sleeve", "Sleeve"),
            ("business_score", "Business"),
            ("valuation_score", "Valuation"),
            ("buy_score", "Buy"),
            ("mandate_fit", "Mandate Fit"),
            ("status", "Status"),
            ("data_quality_flag", "Data Quality"),
            ("thesis_summary", "Thesis"),
            ("main_risks", "Main Risks"),
        ],
        badge_columns={"status": "status", "data_quality_flag": "quality"},
        default_sort_column="ticker",
    )
    rebalance_html = render_table(
        "rebalance-proposals",
        "Rebalance Proposals",
        rebalance_proposals,
        [
            ("ticker", "Ticker"),
            ("company_name", "Company"),
            ("action", "Action"),
            ("current_weight_pct", "Current Weight %"),
            ("reason", "Reason"),
        ],
        badge_columns={"action": "action"},
        default_sort_column="ticker",
    )
    coverage_html = render_table(
        "fundamentals-coverage",
        "Fundamentals Coverage",
        fundamentals_coverage,
        [
            ("holding_name", "Holding"),
            ("ticker", "Ticker"),
            ("isin", "ISIN"),
            ("asset_type", "Asset Type"),
            ("company_type_profile", "Profile"),
            ("match_status", "Match Status"),
            ("match_method", "Match Method"),
            ("data_quality_flag", "Data Quality"),
            ("missing_required_kpis", "Missing Required KPIs"),
            ("optional_missing_kpis", "Optional Missing KPIs"),
            ("needs_research_flag", "Needs Research"),
            ("profile_classification_warning_flag", "Profile Warning"),
            ("profile_classification_warning_reason", "Profile Warning Reason"),
            ("notes", "Notes"),
        ],
        badge_columns={
            "match_status": "status",
            "data_quality_flag": "quality",
            "needs_research_flag": "bool",
            "profile_classification_warning_flag": "bool",
        },
        default_sort_column="ticker",
    )
    research_html = render_table(
        "research-priority",
        "Research Priority",
        research_priority,
        [
            ("ticker", "Ticker"),
            ("isin", "ISIN"),
            ("company_name", "Company"),
            ("asset_type", "Asset Type"),
            ("company_type_profile", "Profile"),
            ("market_value_eur", "Market Value EUR"),
            ("weight_total_assets_pct", "Weight %"),
            ("missing_required_kpi_count", "Missing KPI Count"),
            ("needs_research_flag", "Needs Research"),
            ("coverage_status", "Coverage Status"),
            ("research_priority", "Priority"),
            ("research_priority_reason", "Priority Reason"),
        ],
        badge_columns={"needs_research_flag": "bool", "coverage_status": "status", "research_priority": "status"},
        default_sort_column="ticker",
    )
    ledger_html = render_table(
        "cost-tax-ledger",
        "Cost/Tax Ledger",
        cost_tax_ledger,
        [
            ("event_date", "Event Date"),
            ("broker", "Broker"),
            ("document_type", "Document Type"),
            ("event_type", "Event Type"),
            ("instrument_name", "Instrument"),
            ("ticker", "Ticker"),
            ("isin", "ISIN"),
            ("currency", "Currency"),
            ("gross_amount", "Gross Amount"),
            ("net_amount", "Net Amount"),
            ("fee_amount", "Fee Amount"),
            ("tax_amount", "Tax Amount"),
            ("withholding_tax_amount", "Withholding Tax"),
            ("verification_status", "Verification"),
            ("data_quality_flag", "Data Quality"),
            ("notes", "Notes"),
        ],
        badge_columns={"verification_status": "status", "data_quality_flag": "quality"},
        default_sort_column="event_date",
    )
    history_html = render_history_panel(portfolio_timeseries, benchmark_timeseries)
    legacy_sections_html = render_legacy_sections(sections)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Compound Income OS Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f1e8;
      --panel: #fffdf7;
      --ink: #1f2430;
      --muted: #5b6472;
      --line: #d5ccb9;
      --available: #1d6f42;
      --partial: #8a5a00;
      --not-available: #8c2f39;
      --neutral: #455468;
      --ok: #1d6f42;
      --review: #8a5a00;
      --missing: #8c2f39;
      --accent: #284c7d;
      --cash: #355c7d;
      --chart-portfolio: #284c7d;
      --chart-benchmark: #8a5a00;
    }}
    body {{
      margin: 0;
      padding: 24px;
      background: linear-gradient(180deg, #ece5d3 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
    }}
    main {{ max-width: 1320px; margin: 0 auto; }}
    h1 {{ margin-bottom: 8px; }}
    p.meta {{ color: var(--muted); margin-top: 0; }}
    .summary, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 18px 20px;
      margin-bottom: 18px;
      box-shadow: 0 8px 24px rgba(31, 36, 48, 0.06);
    }}
    .panel-stack .panel {{ margin-bottom: 16px; }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }}
    .summary-card, .action-card {{
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 12px;
      background: #fffaf0;
    }}
    .summary-label, .summary-detail, .muted {{ font-size: 0.9rem; color: var(--muted); }}
    .summary-value {{ font-size: 1.15rem; font-weight: bold; margin-top: 4px; }}
    .action-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 10px;
    }}
    h2 {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 0 0 14px;
      font-size: 1.15rem;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.75rem;
      letter-spacing: 0.04em;
      color: #fff;
      white-space: nowrap;
    }}
    .status-available, .status-selected-this-month, .status-verified, .quality-ok, .bool-true, .action-add, .action-hold {{ background: var(--ok); }}
    .status-partial, .quality-partial, .quality-review, .status-review, .status-high, .action-watch, .action-reduce, .action-do-not-buy, .action-hold-cash {{ background: var(--review); }}
    .status-not-available, .quality-missing-data, .quality-insufficient-history, .bool-false, .status-not-eligible, .action-exit-review {{ background: var(--missing); }}
    .action-cash, .action-review, .status-pending, .quality-not-available {{ background: var(--neutral); }}
    .status-empty, .quality-empty, .action-empty, .bool-empty {{ background: var(--neutral); }}
    .table-wrap {{ overflow-x: auto; }}
    .table-toolbar {{ display: flex; justify-content: flex-end; margin-bottom: 12px; }}
    .table-filter {{
      width: min(320px, 100%);
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid var(--line);
      font: inherit;
      background: #fffaf0;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{
      text-align: left;
      padding: 10px 8px;
      border-top: 1px solid var(--line);
      vertical-align: top;
      font-size: 0.95rem;
    }}
    thead th {{ border-top: none; color: var(--muted); font-size: 0.9rem; }}
    .sort-button {{
      border: none;
      background: transparent;
      color: inherit;
      font: inherit;
      padding: 0;
      cursor: pointer;
    }}
    .bar-list {{
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      gap: 10px;
    }}
    .bar-copy {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 4px;
      font-size: 0.95rem;
    }}
    .bar-track {{
      height: 14px;
      border-radius: 999px;
      background: #efe6d4;
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--accent) 0%, #9fbad0 100%);
    }}
    .chart-shell {{
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 12px;
      background: #fffaf0;
    }}
    .chart-line {{
      stroke-width: 3;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}
    .chart-line.portfolio {{ stroke: var(--chart-portfolio); }}
    .chart-line.benchmark {{ stroke: var(--chart-benchmark); }}
    .chart-legend {{
      display: flex;
      gap: 16px;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .legend-swatch {{
      display: inline-block;
      width: 12px;
      height: 12px;
      border-radius: 999px;
      margin-right: 6px;
    }}
    .legend-swatch.portfolio {{ background: var(--chart-portfolio); }}
    .legend-swatch.benchmark {{ background: var(--chart-benchmark); }}
    footer {{ color: var(--muted); font-size: 0.9rem; padding-top: 8px; }}
    @media (max-width: 800px) {{
      body {{ padding: 14px; }}
      .bar-copy {{ display: block; }}
      h2 {{ display: block; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Compound Income OS Decision Dashboard</h1>
    <p class="meta">Read-only localhost viewer for processed dashboard and decision artifacts. KPI rows loaded: {html.escape(kpi_count)}.</p>
    {render_summary_block(summary)}
    {decision_overview_html}
    {holdings_html}
    {monthly_html}
    {watchlist_html}
    {rebalance_html}
    {coverage_html}
    {research_html}
    {ledger_html}
    {history_html}
    {legacy_sections_html}
    <footer>Data mtime: {html.escape(data_mtime)}</footer>
  </main>
  <script>
    (() => {{
      const tableState = new Map();
      function sortRows(table, key) {{
        const tbody = table.querySelector("tbody");
        const rows = Array.from(tbody.querySelectorAll("tr"));
        const stateKey = table.id + "::" + key;
        const current = tableState.get(stateKey) || "asc";
        const next = current === "asc" ? "desc" : "asc";
        rows.sort((left, right) => {{
          const leftCell = left.querySelector(`td[data-column="${{key}}"]`);
          const rightCell = right.querySelector(`td[data-column="${{key}}"]`);
          const leftText = (leftCell ? leftCell.textContent : left.dataset.sortValue || "").trim();
          const rightText = (rightCell ? rightCell.textContent : right.dataset.sortValue || "").trim();
          const leftNumber = Number(leftText.replace(/[^0-9.-]+/g, ""));
          const rightNumber = Number(rightText.replace(/[^0-9.-]+/g, ""));
          const bothNumeric = !Number.isNaN(leftNumber) && !Number.isNaN(rightNumber) && leftText !== "" && rightText !== "";
          if (bothNumeric) {{
            return next === "asc" ? leftNumber - rightNumber : rightNumber - leftNumber;
          }}
          return next === "asc" ? leftText.localeCompare(rightText) : rightText.localeCompare(leftText);
        }});
        rows.forEach((row) => tbody.appendChild(row));
        tableState.set(stateKey, next);
      }}
      document.querySelectorAll(".sort-button").forEach((button) => {{
        button.addEventListener("click", () => {{
          const table = document.getElementById(button.dataset.tableTarget);
          if (table) {{
            sortRows(table, button.dataset.sortKey);
          }}
        }});
      }});
      document.querySelectorAll(".table-filter").forEach((input) => {{
        input.addEventListener("input", () => {{
          const table = document.getElementById(input.dataset.tableTarget);
          if (!table) {{
            return;
          }}
          const query = input.value.trim().toLowerCase();
          table.querySelectorAll("tbody tr").forEach((row) => {{
            const haystack = (row.dataset.rowSearch || row.textContent || "").toLowerCase();
            row.hidden = query !== "" && !haystack.includes(query);
          }});
        }});
      }});
    }})();
  </script>
</body>
</html>
"""


class DashboardRequestHandler(BaseHTTPRequestHandler):
    server: "DashboardHTTPServer"

    def do_GET(self) -> None:  # noqa: N802
        data_mtime = latest_mtime(self.server.dashboard_paths.all_paths())
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._serve_index(data_mtime)
                return
            if parsed.path == "/api/kpis.json":
                self._serve_json(self.server.artifact_cache.get(self.server.dashboard_paths.kpis, load_kpis), data_mtime)
                return
            if parsed.path == "/api/sections.json":
                self._serve_json(self.server.artifact_cache.get(self.server.dashboard_paths.sections, load_sections), data_mtime)
                return
            if parsed.path == "/api/summary.json":
                self._serve_json(self.server.artifact_cache.get(self.server.dashboard_paths.summary, load_summary), data_mtime)
                return
            if parsed.path == "/api/positions.json":
                self._serve_json(self.server.artifact_cache.get(self.server.dashboard_paths.positions, load_positions), data_mtime)
                return
            if parsed.path == "/api/holdings.json":
                self._serve_json(self.server.artifact_cache.get(self.server.dashboard_paths.holdings, load_holdings), data_mtime)
                return
            if parsed.path == "/api/monthly-buy-ranking.json":
                self._serve_json(self.server.artifact_cache.get(self.server.dashboard_paths.monthly_buy_ranking, load_monthly_buy_ranking), data_mtime)
                return
            if parsed.path == "/api/rebalance-proposals.json":
                self._serve_json(self.server.artifact_cache.get(self.server.dashboard_paths.rebalance_proposals, load_rebalance_proposals), data_mtime)
                return
            if parsed.path == "/api/watchlist.json":
                self._serve_json(self.server.artifact_cache.get(self.server.dashboard_paths.watchlist, load_watchlist), data_mtime)
                return
            if parsed.path == "/api/fundamentals-coverage.json":
                self._serve_json(self.server.artifact_cache.get(self.server.dashboard_paths.fundamentals_coverage, load_fundamentals_coverage), data_mtime)
                return
            if parsed.path == "/api/research-priority.json":
                self._serve_json(self.server.artifact_cache.get(self.server.dashboard_paths.research_priority, load_research_priority), data_mtime)
                return
            if parsed.path == "/api/cost-tax-ledger.json":
                self._serve_json(self.server.artifact_cache.get(self.server.dashboard_paths.cost_tax_ledger, load_cost_tax_ledger), data_mtime)
                return
            if parsed.path == "/api/history-status.json":
                self._serve_json(self._history_status_payload(), data_mtime)
                return
            if parsed.path in {"/api/readiness", "/api/readiness.json"}:
                self._serve_json(
                    self.server.artifact_cache.get(self.server.dashboard_paths.readiness_payload, load_json_payload),
                    data_mtime,
                )
                return
            if parsed.path == "/healthz":
                self._serve_json({"status": "OK"}, data_mtime)
                return
            self._serve_json({"status": "NOT_FOUND", "path": parsed.path}, data_mtime, status_code=404)
        except Exception as exc:  # pragma: no cover - defensive HTTP path
            LOGGER.exception("dashboard_server request failed")
            self._serve_json({"status": "ERROR", "message": str(exc)}, data_mtime, status_code=500)

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)

    def _history_status_payload(self) -> dict[str, Any]:
        portfolio_rows = self.server.artifact_cache.get(self.server.dashboard_paths.portfolio_timeseries, load_portfolio_timeseries)
        benchmark_rows = self.server.artifact_cache.get(self.server.dashboard_paths.benchmark_timeseries, load_benchmark_timeseries)
        return build_history_status(portfolio_rows, benchmark_rows)

    def _serve_index(self, data_mtime: str) -> None:
        kpis = self.server.artifact_cache.get(self.server.dashboard_paths.kpis, load_kpis)
        sections = self.server.artifact_cache.get(self.server.dashboard_paths.sections, load_sections)
        summary = self.server.artifact_cache.get(self.server.dashboard_paths.summary, load_summary)
        holdings = self.server.artifact_cache.get(self.server.dashboard_paths.holdings, load_holdings)
        positions = self.server.artifact_cache.get(self.server.dashboard_paths.positions, load_positions)
        monthly_buy_ranking = self.server.artifact_cache.get(self.server.dashboard_paths.monthly_buy_ranking, load_monthly_buy_ranking)
        rebalance_proposals = self.server.artifact_cache.get(self.server.dashboard_paths.rebalance_proposals, load_rebalance_proposals)
        watchlist = self.server.artifact_cache.get(self.server.dashboard_paths.watchlist, load_watchlist)
        fundamentals_coverage = self.server.artifact_cache.get(self.server.dashboard_paths.fundamentals_coverage, load_fundamentals_coverage)
        research_priority = self.server.artifact_cache.get(self.server.dashboard_paths.research_priority, load_research_priority)
        cost_tax_ledger = self.server.artifact_cache.get(self.server.dashboard_paths.cost_tax_ledger, load_cost_tax_ledger)
        portfolio_timeseries = self.server.artifact_cache.get(self.server.dashboard_paths.portfolio_timeseries, load_portfolio_timeseries)
        benchmark_timeseries = self.server.artifact_cache.get(self.server.dashboard_paths.benchmark_timeseries, load_benchmark_timeseries)
        body = render_index_html(
            kpis,
            sections,
            summary,
            holdings,
            positions,
            monthly_buy_ranking,
            rebalance_proposals,
            watchlist,
            fundamentals_coverage,
            research_priority,
            cost_tax_ledger,
            portfolio_timeseries,
            benchmark_timeseries,
            data_mtime,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", HTML_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Dashboard-Data-Mtime", data_mtime)
        self.end_headers()
        self.wfile.write(body)

    def _serve_json(self, payload: Any, data_mtime: str, status_code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", JSON_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Dashboard-Data-Mtime", data_mtime)
        self.end_headers()
        self.wfile.write(body)


class DashboardHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], paths: DashboardPaths) -> None:
        super().__init__(server_address, DashboardRequestHandler)
        self.dashboard_paths = paths
        self.artifact_cache = ArtifactCache()


def build_server(host: str, port: int, paths: DashboardPaths) -> DashboardHTTPServer:
    return DashboardHTTPServer((validate_host(host), int(port)), paths)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve dashboard CSV artifacts as a local read-only localhost UI.")
    parser.add_argument("--kpis", default=DEFAULT_KPI_OUTPUT, help="Dashboard KPI CSV.")
    parser.add_argument("--sections", default=DEFAULT_SECTIONS_OUTPUT, help="Dashboard sections CSV.")
    parser.add_argument("--summary", default=DEFAULT_SUMMARY_OUTPUT, help="Dashboard summary CSV.")
    parser.add_argument("--positions", default=DEFAULT_POSITIONS_OUTPUT, help="Positions snapshot CSV.")
    parser.add_argument("--holdings", default=DEFAULT_HOLDINGS_OUTPUT, help="Portfolio holdings action table CSV.")
    parser.add_argument("--monthly-buy-ranking", default=DEFAULT_MONTHLY_BUY_RANKING_OUTPUT, help="Monthly buy ranking CSV.")
    parser.add_argument("--rebalance-proposals", default=DEFAULT_REBALANCE_PROPOSALS_OUTPUT, help="Rebalance proposals CSV.")
    parser.add_argument("--watchlist", default=DEFAULT_WATCHLIST_OUTPUT, help="Watchlist ranked CSV.")
    parser.add_argument("--fundamentals-coverage", default=DEFAULT_FUNDAMENTALS_COVERAGE_OUTPUT, help="Fundamentals coverage CSV.")
    parser.add_argument("--research-priority", default=DEFAULT_RESEARCH_PRIORITY_OUTPUT, help="Research priority CSV.")
    parser.add_argument("--cost-tax-ledger", default=DEFAULT_COST_TAX_LEDGER_OUTPUT, help="Cost tax ledger CSV.")
    parser.add_argument("--portfolio-timeseries", default=DEFAULT_PORTFOLIO_TIMESERIES_OUTPUT, help="Portfolio timeseries CSV.")
    parser.add_argument("--benchmark-timeseries", default=DEFAULT_BENCHMARK_TIMESERIES_OUTPUT, help="Benchmark timeseries CSV.")
    parser.add_argument("--readiness-payload", default=DEFAULT_READINESS_PAYLOAD_OUTPUT, help="Dashboard readiness payload JSON.")
    parser.add_argument("--host", default="127.0.0.1", help="Local bind host. Only 127.0.0.1 is allowed.")
    parser.add_argument("--port", type=int, default=8765, help="Local bind port.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    host = validate_host(args.host)
    paths = DashboardPaths(
        kpis=args.kpis,
        sections=args.sections,
        summary=args.summary,
        positions=args.positions,
        holdings=args.holdings,
        monthly_buy_ranking=args.monthly_buy_ranking,
        rebalance_proposals=args.rebalance_proposals,
        watchlist=args.watchlist,
        fundamentals_coverage=args.fundamentals_coverage,
        research_priority=args.research_priority,
        cost_tax_ledger=args.cost_tax_ledger,
        portfolio_timeseries=args.portfolio_timeseries,
        benchmark_timeseries=args.benchmark_timeseries,
        readiness_payload=args.readiness_payload,
    )
    server = build_server(host, args.port, paths)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    LOGGER.info("Serving dashboard on http://%s:%s", host, server.server_address[1])
    LOGGER.info("Changes to the configured processed CSV artifacts become visible on the next request; no restart is required.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - manual stop path
        LOGGER.info("Stopping dashboard server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
