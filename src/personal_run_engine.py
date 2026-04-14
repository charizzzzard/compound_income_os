from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src import import_broker
from src import monthly_ranking_engine
from src import scoring_engine
from src import watchlist_engine
from src.benchmark_history_engine import run_benchmark_history_engine
from src.build_monthly_decision_report import build_monthly_decision_report, read_coverage_rows as read_report_coverage_rows
from src.build_portfolio_snapshot import build_portfolio_snapshot_report, read_coverage_rows as read_snapshot_coverage_rows
from src.common import ensure_parent_dir, read_csv_rows, require_columns, require_non_blank_fields, resolve_repo_path, write_csv_rows
from src.cost_tax_archive_engine import run_cost_tax_archive_engine
from src.dashboard_engine import run_dashboard_engine
from src.fundamentals_master import (
    COVERAGE_OUTPUT_FIELDS,
    DEFAULT_METRIC_DEFINITIONS_PATH,
    DEFAULT_RESEARCH_PRIORITY_OUTPUT,
    PERSONAL_ENRICHED_OUTPUT_FIELDS,
    PERSONAL_MASTER_FIELDS,
    RESEARCH_PRIORITY_OUTPUT_FIELDS,
    build_fundamentals_coverage,
    build_master_seed_rows_from_positions,
    build_personal_enriched_rows,
    build_research_priority_rows,
    load_metric_definitions,
    validate_personal_fundamentals_master,
    write_coverage_report,
)
from src.fundamentals_evidence_engine import (
    DEFAULT_BACKLOG_OUTPUT,
    DEFAULT_EVIDENCE_INPUT_PATH,
    DEFAULT_EVIDENCE_TEMPLATE_PATH,
    DEFAULT_REGISTRY_OUTPUT,
    DEFAULT_SUMMARY_OUTPUT as DEFAULT_EVIDENCE_SUMMARY_OUTPUT,
    run_fundamentals_evidence_engine,
)
from src.fundamentals_overlay_engine import (
    DEFAULT_APPLIED_MASTER_OUTPUT,
    DEFAULT_OVERLAY_INPUT_PATH,
    DEFAULT_OVERLAY_REGISTRY_OUTPUT,
    DEFAULT_OVERLAY_SUMMARY_OUTPUT,
    DEFAULT_OVERLAY_TEMPLATE_PATH,
    run_fundamentals_overlay_engine,
)
from src.multi_benchmark_performance_engine import run_multi_benchmark_performance_engine
from src.performance_engine import run_performance_engine
from src.portfolio_history_engine import run_portfolio_history_engine
from src.traderepublic_documents import load_trade_republic_pdf_rows

SUCCESS = "SUCCESS"
FAILED = "FAILED"
SKIPPED = "SKIPPED"
NOT_REQUESTED = "NOT_REQUESTED"

STAGE_ORDER = [
    "import",
    "fundamentals_seed",
    "scoring",
    "coverage",
    "fundamentals_evidence",
    "fundamentals_overlay",
    "watchlist",
    "monthly",
    "portfolio_review",
    "history",
    "benchmark_archive",
    "performance",
    "multi_benchmark",
    "cost_tax",
    "dashboard",
]

ARTIFACT_FIELDS = ["artifact_role", "artifact_path", "stage_name", "produced", "notes"]

DEFAULT_PATHS = {
    "positions_output": "data/processed/personal_positions_snapshot.csv",
    "fundamentals_master": "data/raw/personal_fundamentals_master.csv",
    "scores_output": "data/processed/personal_company_scores.csv",
    "score_audit_output": "data/processed/personal_score_audit.csv",
    "coverage_output": "data/processed/personal_fundamentals_coverage.csv",
    "fundamentals_enriched_output": "data/processed/personal_fundamentals_enriched.csv",
    "research_priority_output": DEFAULT_RESEARCH_PRIORITY_OUTPUT,
    "fundamentals_evidence_input": DEFAULT_EVIDENCE_INPUT_PATH,
    "fundamentals_evidence_registry_output": DEFAULT_REGISTRY_OUTPUT,
    "fundamentals_research_backlog_output": DEFAULT_BACKLOG_OUTPUT,
    "fundamentals_evidence_summary_output": DEFAULT_EVIDENCE_SUMMARY_OUTPUT,
    "fundamentals_evidence_template_output": DEFAULT_EVIDENCE_TEMPLATE_PATH,
    "fundamentals_overlay_input": DEFAULT_OVERLAY_INPUT_PATH,
    "fundamentals_overlay_registry_output": DEFAULT_OVERLAY_REGISTRY_OUTPUT,
    "fundamentals_applied_master_output": DEFAULT_APPLIED_MASTER_OUTPUT,
    "fundamentals_overlay_summary_output": DEFAULT_OVERLAY_SUMMARY_OUTPUT,
    "fundamentals_overlay_template_output": DEFAULT_OVERLAY_TEMPLATE_PATH,
    "watchlist_output": "data/processed/personal_watchlist_ranked.csv",
    "watchlist_report_output": "reports/sample/personal_watchlist_report.md",
    "monthly_ranking_output": "data/processed/personal_monthly_buy_ranking.csv",
    "rebalance_output": "data/processed/personal_rebalance_proposals.csv",
    "monthly_report_output": "reports/sample/personal_monthly_decision_report.md",
    "portfolio_review_output": "reports/sample/personal_portfolio_review.md",
    "holdings_output": "data/processed/personal_portfolio_holdings_action_table.csv",
    "portfolio_archive": "data/processed/portfolio_snapshot_archive.csv",
    "portfolio_timeseries_output": "data/processed/portfolio_timeseries.csv",
    "portfolio_history_summary_output": "data/processed/portfolio_history_summary.csv",
    "benchmark_archive": "data/processed/benchmark_timeseries_archive.csv",
    "benchmark_registry_output": "data/processed/benchmark_registry.csv",
    "benchmark_normalized_output": "data/processed/benchmark_timeseries_normalized.csv",
    "benchmark_archive_summary_output": "data/processed/benchmark_archive_summary.csv",
    "performance_summary_output": "data/processed/performance_summary.csv",
    "performance_comparison_output": "data/processed/performance_comparison.csv",
    "performance_kpi_output": "data/processed/performance_kpis.csv",
    "multi_benchmark_comparison_output": "data/processed/multi_benchmark_comparison.csv",
    "multi_benchmark_summary_output": "data/processed/multi_benchmark_summary.csv",
    "multi_benchmark_kpi_output": "data/processed/multi_benchmark_kpis.csv",
    "cost_tax_archive": "data/processed/cost_tax_ledger_archive.csv",
    "cost_tax_normalized_ledger_output": "data/processed/cost_tax_ledger_normalized.csv",
    "cost_tax_summary_output": "data/processed/cost_tax_summary.csv",
    "cost_tax_kpi_output": "data/processed/cost_tax_kpis.csv",
    "cost_tax_archive_summary_output": "data/processed/cost_tax_archive_summary.csv",
    "dashboard_kpi_output": "data/processed/dashboard_kpis.csv",
    "dashboard_sections_output": "data/processed/dashboard_sections.csv",
    "dashboard_summary_output": "data/processed/dashboard_summary.csv",
    "manifest_output": "data/processed/personal_run_manifest.json",
    "artifacts_output": "data/processed/personal_run_artifacts.csv",
}


def default_dated_report_path(file_name: str) -> str:
    return f"reports/{date.today().isoformat()}/{file_name}"


@dataclass
class StageResult:
    stage_name: str
    status: str
    required_inputs: list[str]
    used_inputs: dict[str, str]
    produced_outputs: dict[str, str]
    warnings: list[str]
    notes: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "status": self.status,
            "required_inputs": self.required_inputs,
            "used_inputs": self.used_inputs,
            "produced_outputs": self.produced_outputs,
            "warnings": self.warnings,
            "notes": self.notes,
        }


@dataclass
class PersonalRunOptions:
    stages: list[str]
    positions_raw_input: str | None = None
    cash_input: str | None = None
    import_mode: str = "real"
    source_name: str = "personal_depot"
    portfolio_date: str | None = None
    positions_output: str = DEFAULT_PATHS["positions_output"]
    fundamentals_master: str = DEFAULT_PATHS["fundamentals_master"]
    overwrite_fundamentals_master: bool = False
    metric_definitions: str = DEFAULT_METRIC_DEFINITIONS_PATH
    scores_output: str = DEFAULT_PATHS["scores_output"]
    score_audit_output: str = DEFAULT_PATHS["score_audit_output"]
    coverage_output: str = DEFAULT_PATHS["coverage_output"]
    fundamentals_enriched_output: str = DEFAULT_PATHS["fundamentals_enriched_output"]
    research_priority_output: str = DEFAULT_PATHS["research_priority_output"]
    fundamentals_coverage_report_output: str | None = None
    fundamentals_evidence_input: str = DEFAULT_PATHS["fundamentals_evidence_input"]
    fundamentals_evidence_registry_output: str = DEFAULT_PATHS["fundamentals_evidence_registry_output"]
    fundamentals_research_backlog_output: str = DEFAULT_PATHS["fundamentals_research_backlog_output"]
    fundamentals_evidence_summary_output: str = DEFAULT_PATHS["fundamentals_evidence_summary_output"]
    fundamentals_evidence_template_output: str = DEFAULT_PATHS["fundamentals_evidence_template_output"]
    fundamentals_evidence_report_output: str | None = None
    fundamentals_overlay_input: str = DEFAULT_PATHS["fundamentals_overlay_input"]
    fundamentals_overlay_registry_output: str = DEFAULT_PATHS["fundamentals_overlay_registry_output"]
    fundamentals_applied_master_output: str = DEFAULT_PATHS["fundamentals_applied_master_output"]
    fundamentals_overlay_summary_output: str = DEFAULT_PATHS["fundamentals_overlay_summary_output"]
    fundamentals_overlay_template_output: str = DEFAULT_PATHS["fundamentals_overlay_template_output"]
    fundamentals_overlay_report_output: str | None = None
    watchlist_input: str | None = None
    watchlist_output: str = DEFAULT_PATHS["watchlist_output"]
    watchlist_report_output: str = DEFAULT_PATHS["watchlist_report_output"]
    monthly_ranking_output: str = DEFAULT_PATHS["monthly_ranking_output"]
    rebalance_output: str = DEFAULT_PATHS["rebalance_output"]
    monthly_report_output: str = DEFAULT_PATHS["monthly_report_output"]
    portfolio_review_output: str = DEFAULT_PATHS["portfolio_review_output"]
    holdings_output: str = DEFAULT_PATHS["holdings_output"]
    portfolio_archive: str = DEFAULT_PATHS["portfolio_archive"]
    portfolio_timeseries_output: str = DEFAULT_PATHS["portfolio_timeseries_output"]
    portfolio_history_summary_output: str = DEFAULT_PATHS["portfolio_history_summary_output"]
    portfolio_history_report_output: str | None = None
    benchmark_input: str | None = None
    benchmark_config: str = "configs/benchmark.yaml"
    benchmark_archive: str = DEFAULT_PATHS["benchmark_archive"]
    benchmark_registry_output: str = DEFAULT_PATHS["benchmark_registry_output"]
    benchmark_normalized_output: str = DEFAULT_PATHS["benchmark_normalized_output"]
    benchmark_archive_summary_output: str = DEFAULT_PATHS["benchmark_archive_summary_output"]
    benchmark_history_report_output: str | None = None
    benchmark_symbols: list[str] | None = None
    single_benchmark_symbol: str | None = None
    performance_benchmark: str | None = None
    performance_summary_output: str = DEFAULT_PATHS["performance_summary_output"]
    performance_comparison_output: str = DEFAULT_PATHS["performance_comparison_output"]
    performance_kpi_output: str = DEFAULT_PATHS["performance_kpi_output"]
    performance_report_output: str | None = None
    multi_benchmark_comparison_output: str = DEFAULT_PATHS["multi_benchmark_comparison_output"]
    multi_benchmark_summary_output: str = DEFAULT_PATHS["multi_benchmark_summary_output"]
    multi_benchmark_kpi_output: str = DEFAULT_PATHS["multi_benchmark_kpi_output"]
    multi_benchmark_report_output: str | None = None
    ledger: str | None = None
    cost_tax_documents: list[str] | None = None
    cost_tax_archive: str = DEFAULT_PATHS["cost_tax_archive"]
    cost_tax_normalized_ledger_output: str = DEFAULT_PATHS["cost_tax_normalized_ledger_output"]
    cost_tax_summary_output: str = DEFAULT_PATHS["cost_tax_summary_output"]
    cost_tax_kpi_output: str = DEFAULT_PATHS["cost_tax_kpi_output"]
    cost_tax_archive_summary_output: str = DEFAULT_PATHS["cost_tax_archive_summary_output"]
    cost_tax_report_output: str | None = None
    dashboard_kpi_output: str = DEFAULT_PATHS["dashboard_kpi_output"]
    dashboard_sections_output: str = DEFAULT_PATHS["dashboard_sections_output"]
    dashboard_summary_output: str = DEFAULT_PATHS["dashboard_summary_output"]
    dashboard_report_output: str | None = None
    manifest_output: str = DEFAULT_PATHS["manifest_output"]
    artifacts_output: str = DEFAULT_PATHS["artifacts_output"]
    report_output: str | None = None

    def normalized(self) -> "PersonalRunOptions":
        self.benchmark_symbols = [str(symbol).strip().upper() for symbol in (self.benchmark_symbols or []) if str(symbol).strip()]
        self.cost_tax_documents = [str(path).strip() for path in (self.cost_tax_documents or []) if str(path).strip()]
        if self.fundamentals_coverage_report_output is None:
            self.fundamentals_coverage_report_output = default_dated_report_path("personal_fundamentals_coverage_report.md")
        if self.fundamentals_evidence_report_output is None:
            self.fundamentals_evidence_report_output = default_dated_report_path("personal_fundamentals_evidence_report.md")
        if self.fundamentals_overlay_report_output is None:
            self.fundamentals_overlay_report_output = default_dated_report_path("personal_fundamentals_overlay_report.md")
        if self.portfolio_history_report_output is None:
            self.portfolio_history_report_output = default_dated_report_path("portfolio_history_report.md")
        if self.benchmark_history_report_output is None:
            self.benchmark_history_report_output = default_dated_report_path("benchmark_history_report.md")
        if self.performance_report_output is None:
            self.performance_report_output = default_dated_report_path("performance_report.md")
        if self.multi_benchmark_report_output is None:
            self.multi_benchmark_report_output = default_dated_report_path("multi_benchmark_report.md")
        if self.cost_tax_report_output is None:
            self.cost_tax_report_output = default_dated_report_path("cost_tax_report.md")
        if self.dashboard_report_output is None:
            self.dashboard_report_output = default_dated_report_path("dashboard_report.md")
        if self.report_output is None:
            self.report_output = default_dated_report_path("personal_run_report.md")
        return self


def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def path_exists(path_value: str | None) -> bool:
    return bool(path_value) and resolve_repo_path(str(path_value)).exists()


def require_existing_path(path_value: str | None, label: str, stage_name: str) -> str:
    if not path_value:
        raise ValueError(f"stage {stage_name} requires {label}.")
    if not path_exists(path_value):
        raise ValueError(f"stage {stage_name} requires existing {label}: {path_value}")
    return str(path_value)


def output_exists(path_value: str) -> bool:
    return resolve_repo_path(path_value).exists()


def stage_result(
    stage_name: str,
    status: str,
    required_inputs: list[str],
    used_inputs: dict[str, str] | None = None,
    produced_outputs: dict[str, str] | None = None,
    warnings: list[str] | None = None,
    notes: str = "",
) -> StageResult:
    return StageResult(
        stage_name=stage_name,
        status=status,
        required_inputs=required_inputs,
        used_inputs=dict(sorted((used_inputs or {}).items())),
        produced_outputs=dict(sorted((produced_outputs or {}).items())),
        warnings=warnings or [],
        notes=notes,
    )


def validate_stage_selection(stages: list[str]) -> list[str]:
    if not stages:
        raise ValueError("at least one --stage is required; no implicit full run is assumed.")
    unknown = sorted({stage for stage in stages if stage not in STAGE_ORDER})
    if unknown:
        raise ValueError(f"unknown stage(s): {', '.join(unknown)}")
    return sorted(set(stages), key=STAGE_ORDER.index)


def input_snapshot(options: PersonalRunOptions) -> dict[str, Any]:
    return {
        "positions_raw_input": options.positions_raw_input or "",
        "cash_input": options.cash_input or "",
        "import_mode": options.import_mode,
        "source_name": options.source_name,
        "portfolio_date": options.portfolio_date or "",
        "positions_output": options.positions_output,
        "fundamentals_master": options.fundamentals_master,
        "research_priority_output": options.research_priority_output,
        "fundamentals_evidence_input": options.fundamentals_evidence_input,
        "fundamentals_overlay_input": options.fundamentals_overlay_input,
        "watchlist_input": options.watchlist_input or "",
        "benchmark_input": options.benchmark_input or "",
        "benchmark_config": options.benchmark_config,
        "benchmark_archive": options.benchmark_archive,
        "benchmark_registry": options.benchmark_registry_output,
        "benchmark_symbols": options.benchmark_symbols or [],
        "single_benchmark_symbol": options.single_benchmark_symbol or "",
        "performance_benchmark": options.performance_benchmark or options.benchmark_normalized_output,
        "ledger": options.ledger or "",
        "cost_tax_documents": options.cost_tax_documents or [],
    }


def run_import_stage(options: PersonalRunOptions) -> StageResult:
    stage = "import"
    raw_input = require_existing_path(options.positions_raw_input, "positions raw input", stage)
    used = {"positions_raw_input": raw_input, "import_mode": options.import_mode, "source_name": options.source_name}
    if options.import_mode == "tr_pdf":
        used["cash_input"] = options.cash_input or ""
        rows = load_trade_republic_pdf_rows(raw_input, options.cash_input, options.source_name or "trade_republic_official_docs")
    else:
        rows = read_csv_rows(raw_input)
    if not rows:
        raise ValueError(f"stage import raw portfolio input ({raw_input}) contains no rows.")
    snapshot = import_broker.build_positions_snapshot(rows, options.import_mode, options.source_name, options.portfolio_date)
    write_csv_rows(options.positions_output, import_broker.OUTPUT_FIELDS, snapshot)
    return stage_result(
        stage,
        SUCCESS,
        ["positions_raw_input"],
        used_inputs=used,
        produced_outputs={"positions_snapshot": options.positions_output},
        notes="Positions snapshot generated via import_broker.",
    )


def run_fundamentals_seed_stage(options: PersonalRunOptions) -> StageResult:
    stage = "fundamentals_seed"
    positions_path = require_existing_path(options.positions_output, "positions snapshot", stage)
    if path_exists(options.fundamentals_master) and not options.overwrite_fundamentals_master:
        raise ValueError(
            f"stage fundamentals_seed refuses to overwrite existing fundamentals master: {options.fundamentals_master}; "
            "pass --overwrite-fundamentals-master to replace it explicitly."
        )
    positions_rows = read_csv_rows(positions_path)
    require_columns(positions_rows, ["ticker", "isin", "company_name", "asset_type", "sleeve"], f"positions CSV ({positions_path})")
    seed_rows = build_master_seed_rows_from_positions(positions_rows)
    write_csv_rows(options.fundamentals_master, PERSONAL_MASTER_FIELDS, seed_rows)
    return stage_result(
        stage,
        SUCCESS,
        ["positions_output"],
        used_inputs={"positions_output": positions_path},
        produced_outputs={"fundamentals_master_seed": options.fundamentals_master},
        notes="Identity-only personal fundamentals master seed generated; KPI values were not invented.",
    )


def run_scoring_stage(options: PersonalRunOptions) -> StageResult:
    stage = "scoring"
    positions_path = require_existing_path(options.positions_output, "positions snapshot", stage)
    fundamentals_path = require_existing_path(options.fundamentals_master, "personal fundamentals master", stage)
    positions_rows = read_csv_rows(positions_path)
    fundamentals_rows = read_csv_rows(fundamentals_path)
    require_columns(positions_rows, ["ticker", "market_value_eur", "asset_type", "sleeve", "sector"], f"positions CSV ({positions_path})")
    require_columns(
        fundamentals_rows,
        ["ticker", "company_name", "sector", "country", "asset_type", "sleeve"],
        f"fundamentals CSV ({fundamentals_path})",
    )
    require_non_blank_fields(fundamentals_rows, ["ticker"], f"fundamentals CSV ({fundamentals_path})")
    results, _enriched_rows, audit_rows = scoring_engine.build_scores_with_audit(
        positions_rows,
        fundamentals_rows,
        fundamentals_source_name=f"fundamentals CSV ({fundamentals_path})",
        fundamentals_format="personal",
    )
    write_csv_rows(options.scores_output, scoring_engine.OUTPUT_FIELDS, results)
    write_csv_rows(options.score_audit_output, scoring_engine.SCORE_AUDIT_FIELDS, audit_rows)
    return stage_result(
        stage,
        SUCCESS,
        ["positions_output", "fundamentals_master"],
        used_inputs={"positions_output": positions_path, "fundamentals_master": fundamentals_path},
        produced_outputs={"company_scores": options.scores_output, "score_audit": options.score_audit_output},
        notes="Scores generated with fundamentals_format=personal; no sample fundamentals fallback used.",
    )


def run_coverage_stage(options: PersonalRunOptions) -> StageResult:
    stage = "coverage"
    positions_path = require_existing_path(options.positions_output, "positions snapshot", stage)
    fundamentals_path = require_existing_path(options.fundamentals_master, "personal fundamentals master", stage)
    scores_path = require_existing_path(options.scores_output, "personal company scores", stage)
    positions_rows = read_csv_rows(positions_path)
    fundamentals_rows = read_csv_rows(fundamentals_path)
    warnings = validate_personal_fundamentals_master(fundamentals_rows, f"personal fundamentals master ({fundamentals_path})")
    definitions = load_metric_definitions(options.metric_definitions)
    coverage_rows = build_fundamentals_coverage(positions_rows, fundamentals_rows, definitions)
    write_csv_rows(options.coverage_output, COVERAGE_OUTPUT_FIELDS, coverage_rows)
    research_priority_rows = build_research_priority_rows(positions_rows, coverage_rows)
    write_csv_rows(options.research_priority_output, RESEARCH_PRIORITY_OUTPUT_FIELDS, research_priority_rows)
    score_rows = read_csv_rows(scores_path)
    enriched_rows = build_personal_enriched_rows(coverage_rows, fundamentals_rows, score_rows)
    write_csv_rows(options.fundamentals_enriched_output, PERSONAL_ENRICHED_OUTPUT_FIELDS, enriched_rows)
    write_coverage_report(coverage_rows, options.fundamentals_coverage_report_output or "", fundamentals_path, warnings)
    return stage_result(
        stage,
        SUCCESS,
        ["positions_output", "fundamentals_master", "scores_output"],
        used_inputs={"positions_output": positions_path, "fundamentals_master": fundamentals_path, "scores_output": scores_path},
        produced_outputs={
            "fundamentals_coverage": options.coverage_output,
            "fundamentals_enriched": options.fundamentals_enriched_output,
            "fundamentals_coverage_report": options.fundamentals_coverage_report_output or "",
            "research_priority": options.research_priority_output,
        },
        warnings=warnings,
        notes="Personal fundamentals coverage, profile guardrails and research priority generated from the local master.",
    )


def run_fundamentals_evidence_stage(options: PersonalRunOptions) -> StageResult:
    stage = "fundamentals_evidence"
    fundamentals_path = require_existing_path(options.fundamentals_master, "personal fundamentals master", stage)
    evidence_path = require_existing_path(options.fundamentals_evidence_input, "personal fundamentals evidence input", stage)
    outputs = run_fundamentals_evidence_engine(
        fundamentals_master_path=fundamentals_path,
        evidence_input_path=evidence_path,
        metric_definitions_path=options.metric_definitions,
        registry_output=options.fundamentals_evidence_registry_output,
        backlog_output=options.fundamentals_research_backlog_output,
        summary_output=options.fundamentals_evidence_summary_output,
        report_output=options.fundamentals_evidence_report_output,
        template_output=options.fundamentals_evidence_template_output,
    )
    return stage_result(
        stage,
        SUCCESS,
        ["fundamentals_master", "fundamentals_evidence_input"],
        used_inputs={"fundamentals_master": fundamentals_path, "fundamentals_evidence_input": evidence_path},
        produced_outputs={role: str(path) for role, path in outputs.items()},
        notes="Personal fundamentals evidence registry and research backlog generated; master and scores were not modified.",
    )


def run_fundamentals_overlay_stage(options: PersonalRunOptions) -> StageResult:
    stage = "fundamentals_overlay"
    fundamentals_path = require_existing_path(options.fundamentals_master, "personal fundamentals master", stage)
    overlay_path = require_existing_path(options.fundamentals_overlay_input, "personal fundamentals overlay input", stage)
    outputs = run_fundamentals_overlay_engine(
        fundamentals_master_path=fundamentals_path,
        overlay_input_path=overlay_path,
        registry_output=options.fundamentals_overlay_registry_output,
        applied_master_output=options.fundamentals_applied_master_output,
        summary_output=options.fundamentals_overlay_summary_output,
        report_output=options.fundamentals_overlay_report_output,
        template_output=options.fundamentals_overlay_template_output,
    )
    return stage_result(
        stage,
        SUCCESS,
        ["fundamentals_master", "fundamentals_overlay_input"],
        used_inputs={"fundamentals_master": fundamentals_path, "fundamentals_overlay_input": overlay_path},
        produced_outputs={role: str(path) for role, path in outputs.items()},
        notes="Personal fundamentals overlay registry and applied master projection generated; original master and scores were not modified.",
    )


def run_watchlist_stage(options: PersonalRunOptions) -> StageResult:
    stage = "watchlist"
    watchlist_path = require_existing_path(options.watchlist_input, "watchlist input", stage)
    scores_path = require_existing_path(options.scores_output, "personal company scores", stage)
    watchlist_rows = read_csv_rows(watchlist_path)
    score_rows = read_csv_rows(scores_path)
    require_columns(watchlist_rows, ["ticker"], f"watchlist CSV ({watchlist_path})")
    require_columns(
        score_rows,
        ["ticker", "business_score", "valuation_score", "buy_score", "fair_value_estimate", "margin_of_safety_pct", "data_quality_flag"],
        f"scores CSV ({scores_path})",
    )
    ranked = watchlist_engine.build_watchlist_ranked(
        watchlist_rows,
        score_rows,
        score_source_name=f"scores CSV ({scores_path})",
        watchlist_source_name=f"watchlist CSV ({watchlist_path})",
    )
    write_csv_rows(options.watchlist_output, watchlist_engine.OUTPUT_FIELDS, ranked)
    watchlist_engine.build_watchlist_report(ranked, options.watchlist_report_output)
    return stage_result(
        stage,
        SUCCESS,
        ["watchlist_input", "scores_output"],
        used_inputs={"watchlist_input": watchlist_path, "scores_output": scores_path},
        produced_outputs={"watchlist_ranked": options.watchlist_output, "watchlist_report": options.watchlist_report_output},
        notes="Watchlist ranked from personal scores.",
    )


def run_monthly_stage(options: PersonalRunOptions) -> StageResult:
    stage = "monthly"
    positions_path = require_existing_path(options.positions_output, "positions snapshot", stage)
    scores_path = require_existing_path(options.scores_output, "personal company scores", stage)
    watchlist_path = require_existing_path(options.watchlist_output, "ranked watchlist", stage)
    coverage_path = require_existing_path(options.coverage_output, "personal fundamentals coverage", stage)
    positions_rows = read_csv_rows(positions_path)
    score_rows = read_csv_rows(scores_path)
    watchlist_rows = read_csv_rows(watchlist_path)
    coverage_rows = monthly_ranking_engine.read_coverage_rows(coverage_path)
    ranking, rebalance = monthly_ranking_engine.build_monthly_ranking(
        positions_rows,
        score_rows,
        watchlist_rows,
        score_source_name=f"scores CSV ({scores_path})",
        watchlist_source_name=f"watchlist CSV ({watchlist_path})",
        coverage_rows=coverage_rows,
        coverage_source_name=f"coverage CSV ({coverage_path})",
    )
    cleaned_ranking = [{key: row.get(key, "") for key in monthly_ranking_engine.OUTPUT_FIELDS} for row in ranking]
    write_csv_rows(options.monthly_ranking_output, monthly_ranking_engine.OUTPUT_FIELDS, cleaned_ranking)
    write_csv_rows(options.rebalance_output, monthly_ranking_engine.REBALANCE_FIELDS, rebalance)
    report_coverage_rows = read_report_coverage_rows(coverage_path)
    build_monthly_decision_report(positions_rows, score_rows, cleaned_ranking, options.monthly_report_output, coverage_rows=report_coverage_rows)
    return stage_result(
        stage,
        SUCCESS,
        ["positions_output", "scores_output", "watchlist_output", "coverage_output"],
        used_inputs={
            "positions_output": positions_path,
            "scores_output": scores_path,
            "watchlist_output": watchlist_path,
            "coverage_output": coverage_path,
        },
        produced_outputs={
            "monthly_buy_ranking": options.monthly_ranking_output,
            "rebalance_proposals": options.rebalance_output,
            "monthly_decision_report": options.monthly_report_output,
        },
        notes="Monthly ranking and decision report generated with fundamentals coverage guardrail.",
    )


def run_portfolio_review_stage(options: PersonalRunOptions) -> StageResult:
    stage = "portfolio_review"
    positions_path = require_existing_path(options.positions_output, "positions snapshot", stage)
    scores_path = require_existing_path(options.scores_output, "personal company scores", stage)
    coverage_path = require_existing_path(options.coverage_output, "personal fundamentals coverage", stage)
    positions_rows = read_csv_rows(positions_path)
    scores_rows = read_csv_rows(scores_path)
    coverage_rows = read_snapshot_coverage_rows(coverage_path)
    build_portfolio_snapshot_report(
        positions_rows,
        options.portfolio_review_output,
        scores_rows=scores_rows,
        holdings_output=options.holdings_output,
        coverage_rows=coverage_rows,
    )
    return stage_result(
        stage,
        SUCCESS,
        ["positions_output", "scores_output", "coverage_output"],
        used_inputs={"positions_output": positions_path, "scores_output": scores_path, "coverage_output": coverage_path},
        produced_outputs={"portfolio_review_report": options.portfolio_review_output, "holdings_action_table": options.holdings_output},
        notes="Portfolio review report and holdings action table generated with coverage guardrail.",
    )


def run_history_stage(options: PersonalRunOptions) -> StageResult:
    stage = "history"
    positions_path = require_existing_path(options.positions_output, "positions snapshot", stage)
    outputs = run_portfolio_history_engine(
        positions_path=positions_path,
        archive_path=options.portfolio_archive,
        archive_output=options.portfolio_archive,
        timeseries_output=options.portfolio_timeseries_output,
        summary_output=options.portfolio_history_summary_output,
        report_output=options.portfolio_history_report_output,
    )
    return stage_result(
        stage,
        SUCCESS,
        ["positions_output"],
        used_inputs={"positions_output": positions_path, "portfolio_archive": options.portfolio_archive},
        produced_outputs={role: str(path) for role, path in outputs.items()},
        notes="Portfolio snapshot archive and explicit timeseries generated.",
    )


def resolve_single_benchmark_symbol(options: PersonalRunOptions) -> str | None:
    if options.single_benchmark_symbol:
        return options.single_benchmark_symbol.strip().upper()
    symbols = options.benchmark_symbols or []
    if len(symbols) == 1:
        return symbols[0]
    if len(symbols) > 1:
        raise ValueError(
            "stage benchmark_archive needs --single-benchmark-symbol when multiple --benchmark-symbol values are supplied; "
            "the normalized performance output must be one explicit benchmark series."
        )
    return None


def run_benchmark_archive_stage(options: PersonalRunOptions) -> StageResult:
    stage = "benchmark_archive"
    if not options.benchmark_input and not path_exists(options.benchmark_archive):
        raise ValueError(f"stage benchmark_archive requires --benchmark-input or existing benchmark archive: {options.benchmark_archive}")
    if options.benchmark_input:
        require_existing_path(options.benchmark_input, "benchmark input", stage)
    require_existing_path(options.benchmark_config, "benchmark config", stage)
    selected_symbol = resolve_single_benchmark_symbol(options)
    outputs = run_benchmark_history_engine(
        benchmark_input=options.benchmark_input,
        benchmark_config_path=options.benchmark_config,
        archive_path=options.benchmark_archive,
        archive_output=options.benchmark_archive,
        normalized_output=options.benchmark_normalized_output,
        registry_output=options.benchmark_registry_output,
        archive_summary_output=options.benchmark_archive_summary_output,
        report_output=options.benchmark_history_report_output,
        benchmark_symbol=selected_symbol,
    )
    used = {"benchmark_config": options.benchmark_config, "benchmark_archive": options.benchmark_archive}
    if options.benchmark_input:
        used["benchmark_input"] = options.benchmark_input
    if selected_symbol:
        used["single_benchmark_symbol"] = selected_symbol
    return stage_result(
        stage,
        SUCCESS,
        ["benchmark_input_or_existing_archive", "benchmark_config"],
        used_inputs=used,
        produced_outputs={role: str(path) for role, path in outputs.items()},
        notes="Benchmark archive/registry generated; normalized output remains a single explicit benchmark series.",
    )


def run_performance_stage(options: PersonalRunOptions) -> StageResult:
    stage = "performance"
    positions_path = require_existing_path(options.positions_output, "positions snapshot", stage)
    timeseries_path = require_existing_path(options.portfolio_timeseries_output, "portfolio timeseries", stage)
    benchmark_path = require_existing_path(options.performance_benchmark or options.benchmark_normalized_output, "single benchmark timeseries", stage)
    require_existing_path(options.benchmark_config, "benchmark config", stage)
    outputs = run_performance_engine(
        positions_path=positions_path,
        benchmark_path=benchmark_path,
        benchmark_config_path=options.benchmark_config,
        portfolio_timeseries_path=timeseries_path,
        comparison_output=options.performance_comparison_output,
        kpi_output=options.performance_kpi_output,
        summary_output=options.performance_summary_output,
        normalized_benchmark_output=options.benchmark_normalized_output,
        portfolio_timeseries_output=options.portfolio_timeseries_output,
        report_output=options.performance_report_output or default_dated_report_path("performance_report.md"),
    )
    return stage_result(
        stage,
        SUCCESS,
        ["positions_output", "portfolio_timeseries_output", "performance_benchmark", "benchmark_config"],
        used_inputs={
            "positions_output": positions_path,
            "portfolio_timeseries_output": timeseries_path,
            "performance_benchmark": benchmark_path,
            "benchmark_config": options.benchmark_config,
        },
        produced_outputs={role: str(path) for role, path in outputs.items()},
        notes="Single-benchmark performance artifacts generated from explicit portfolio timeseries.",
    )


def run_multi_benchmark_stage(options: PersonalRunOptions) -> StageResult:
    stage = "multi_benchmark"
    positions_path = require_existing_path(options.positions_output, "positions snapshot", stage)
    timeseries_path = require_existing_path(options.portfolio_timeseries_output, "portfolio timeseries", stage)
    archive_path = require_existing_path(options.benchmark_archive, "benchmark archive", stage)
    registry_path = require_existing_path(options.benchmark_registry_output, "benchmark registry", stage)
    require_existing_path(options.benchmark_config, "benchmark config", stage)
    outputs = run_multi_benchmark_performance_engine(
        positions_path=positions_path,
        portfolio_timeseries_path=timeseries_path,
        benchmark_archive_path=archive_path,
        benchmark_registry_path=registry_path,
        benchmark_config_path=options.benchmark_config,
        benchmark_symbols=options.benchmark_symbols or [],
        comparison_output=options.multi_benchmark_comparison_output,
        summary_output=options.multi_benchmark_summary_output,
        kpi_output=options.multi_benchmark_kpi_output,
        report_output=options.multi_benchmark_report_output or default_dated_report_path("multi_benchmark_report.md"),
    )
    return stage_result(
        stage,
        SUCCESS,
        ["positions_output", "portfolio_timeseries_output", "benchmark_archive", "benchmark_registry_output"],
        used_inputs={
            "positions_output": positions_path,
            "portfolio_timeseries_output": timeseries_path,
            "benchmark_archive": archive_path,
            "benchmark_registry_output": registry_path,
        },
        produced_outputs={role: str(path) for role, path in outputs.items()},
        notes="Multi-benchmark comparison generated from archive and registry.",
    )


def run_cost_tax_stage(options: PersonalRunOptions) -> StageResult:
    stage = "cost_tax"
    if not options.ledger and not options.cost_tax_documents:
        raise ValueError("stage cost_tax requires --ledger and/or at least one --cost-tax-document.")
    used = {"cost_tax_archive": options.cost_tax_archive}
    if options.ledger:
        used["ledger"] = require_existing_path(options.ledger, "cost/tax ledger", stage)
    for index, document_path in enumerate(options.cost_tax_documents or [], start=1):
        used[f"cost_tax_document_{index}"] = require_existing_path(document_path, "cost/tax document", stage)
    outputs = run_cost_tax_archive_engine(
        ledger_path=options.ledger,
        document_inputs=options.cost_tax_documents,
        archive_path=options.cost_tax_archive,
        archive_output=options.cost_tax_archive,
        normalized_ledger_output=options.cost_tax_normalized_ledger_output,
        summary_output=options.cost_tax_summary_output,
        kpi_output=options.cost_tax_kpi_output,
        report_output=options.cost_tax_report_output or default_dated_report_path("cost_tax_report.md"),
        archive_summary_output=options.cost_tax_archive_summary_output,
    )
    return stage_result(
        stage,
        SUCCESS,
        ["ledger_or_cost_tax_document"],
        used_inputs=used,
        produced_outputs={role: str(path) for role, path in outputs.items()},
        notes="Cost/tax archive and downstream artifacts generated from explicit ledger/document evidence.",
    )


def run_dashboard_stage(options: PersonalRunOptions) -> StageResult:
    stage = "dashboard"
    require_existing_path(options.positions_output, "positions snapshot", stage)
    run_dashboard_engine(
        positions_path=options.positions_output,
        scores_path=options.scores_output,
        holdings_path=options.holdings_output,
        score_audit_path=options.score_audit_output,
        coverage_path=options.coverage_output,
        performance_kpis_path=options.performance_kpi_output,
        performance_summary_path=options.performance_summary_output,
        performance_comparison_path=options.performance_comparison_output,
        cost_tax_kpis_path=options.cost_tax_kpi_output,
        cost_tax_summary_path=options.cost_tax_summary_output,
        kpi_output=options.dashboard_kpi_output,
        sections_output=options.dashboard_sections_output,
        summary_output=options.dashboard_summary_output,
        report_output=options.dashboard_report_output or default_dated_report_path("dashboard_report.md"),
    )
    return stage_result(
        stage,
        SUCCESS,
        ["positions_output"],
        used_inputs={
            "positions_output": options.positions_output,
            "scores_output": options.scores_output,
            "holdings_output": options.holdings_output,
            "score_audit_output": options.score_audit_output,
            "coverage_output": options.coverage_output,
            "performance_kpi_output": options.performance_kpi_output,
            "performance_summary_output": options.performance_summary_output,
            "performance_comparison_output": options.performance_comparison_output,
            "cost_tax_kpi_output": options.cost_tax_kpi_output,
            "cost_tax_summary_output": options.cost_tax_summary_output,
        },
        produced_outputs={
            "dashboard_kpis": options.dashboard_kpi_output,
            "dashboard_sections": options.dashboard_sections_output,
            "dashboard_summary": options.dashboard_summary_output,
            "dashboard_report": options.dashboard_report_output or "",
        },
        notes="Dashboard consolidated from processed artifacts; missing optional sources remain visible in dashboard metrics.",
    )


STAGE_RUNNERS: dict[str, Callable[[PersonalRunOptions], StageResult]] = {
    "import": run_import_stage,
    "fundamentals_seed": run_fundamentals_seed_stage,
    "scoring": run_scoring_stage,
    "coverage": run_coverage_stage,
    "fundamentals_evidence": run_fundamentals_evidence_stage,
    "fundamentals_overlay": run_fundamentals_overlay_stage,
    "watchlist": run_watchlist_stage,
    "monthly": run_monthly_stage,
    "portfolio_review": run_portfolio_review_stage,
    "history": run_history_stage,
    "benchmark_archive": run_benchmark_archive_stage,
    "performance": run_performance_stage,
    "multi_benchmark": run_multi_benchmark_stage,
    "cost_tax": run_cost_tax_stage,
    "dashboard": run_dashboard_stage,
}


def artifact_rows_from_stage_results(stage_results: list[StageResult]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for stage in stage_results:
        for role, path_value in sorted(stage.produced_outputs.items()):
            if not path_value:
                continue
            rows.append(
                {
                    "artifact_role": role,
                    "artifact_path": path_value,
                    "stage_name": stage.stage_name,
                    "produced": str(stage.status == SUCCESS and output_exists(path_value)),
                    "notes": stage.notes,
                }
            )
    rows.sort(key=lambda row: (STAGE_ORDER.index(row["stage_name"]), row["artifact_role"], row["artifact_path"]))
    return rows


def read_first_row(path_value: str) -> dict[str, str]:
    if not path_exists(path_value):
        return {}
    rows = read_csv_rows(path_value)
    return rows[0] if rows else {}


def successful_stage_names(stage_results: list[StageResult]) -> set[str]:
    return {result.stage_name for result in stage_results if result.status == SUCCESS}


def collect_measurement_modes(options: PersonalRunOptions, stage_results: list[StageResult]) -> dict[str, str]:
    successful = successful_stage_names(stage_results)
    modes: dict[str, str] = {}
    performance = read_first_row(options.performance_summary_output) if "performance" in successful else {}
    if performance:
        modes["performance"] = performance.get("measurement_mode", "")
    multi = read_first_row(options.multi_benchmark_summary_output) if "multi_benchmark" in successful else {}
    if multi:
        modes["multi_benchmark"] = multi.get("measurement_mode", "")
    cost_tax = read_first_row(options.cost_tax_summary_output) if "cost_tax" in successful else {}
    if cost_tax:
        modes["cost_tax"] = cost_tax.get("ledger_measurement_mode", "")
    return modes


def collect_data_quality_flags(options: PersonalRunOptions, stage_results: list[StageResult]) -> dict[str, str]:
    successful = successful_stage_names(stage_results)
    flags: dict[str, str] = {}
    performance = read_first_row(options.performance_summary_output) if "performance" in successful else {}
    if performance:
        flags["performance"] = performance.get("data_quality_flag", "")
    multi = read_first_row(options.multi_benchmark_summary_output) if "multi_benchmark" in successful else {}
    if multi:
        flags["multi_benchmark"] = multi.get("data_quality_flag", "")
    cost_tax = read_first_row(options.cost_tax_summary_output) if "cost_tax" in successful else {}
    if cost_tax:
        flags["cost_tax"] = cost_tax.get("ledger_data_quality_flag", "")
    dashboard = read_first_row(options.dashboard_summary_output) if "dashboard" in successful else {}
    if dashboard:
        flags["dashboard"] = dashboard.get("dashboard_data_quality_flag", "")
    return flags


def build_manifest(
    options: PersonalRunOptions,
    selected_stages: list[str],
    executed_stage_order: list[str],
    stage_results: list[StageResult],
    run_started_at: str,
    run_finished_at: str,
    run_status: str,
    warnings: list[str],
    notes: str,
) -> dict[str, Any]:
    return {
        "run_started_at": run_started_at,
        "run_finished_at": run_finished_at,
        "run_status": run_status,
        "selected_stages": selected_stages,
        "executed_stage_order": executed_stage_order,
        "source_name": options.source_name,
        "input_mode": options.import_mode,
        "inputs": input_snapshot(options),
        "outputs": {
            "manifest_output": options.manifest_output,
            "artifacts_output": options.artifacts_output,
            "report_output": options.report_output or "",
        },
        "stage_results": [result.as_dict() for result in stage_results],
        "warnings": warnings,
        "measurement_modes": collect_measurement_modes(options, stage_results),
        "data_quality_flags": collect_data_quality_flags(options, stage_results),
        "notes": notes,
    }


def write_manifest(path_value: str, manifest: dict[str, Any]) -> Path:
    path = ensure_parent_dir(path_value)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path


def write_run_report(path_value: str, manifest: dict[str, Any], artifact_rows: list[dict[str, str]]) -> Path:
    lines = [
        "# Personal Run Report",
        "",
        "## Run Status",
        "",
        f"- Status: {manifest['run_status']}",
        f"- Started: {manifest['run_started_at']}",
        f"- Finished: {manifest['run_finished_at']}",
        f"- Source: {manifest['source_name']}",
        f"- Input Mode: {manifest['input_mode']}",
        "",
        "## Stages",
        "",
        "| Stage | Status | Notes |",
        "| --- | --- | --- |",
    ]
    for result in manifest["stage_results"]:
        lines.append(f"| {result['stage_name']} | {result['status']} | {result['notes']} |")
    lines.extend(["", "## Artifacts", ""])
    produced_rows = [row for row in artifact_rows if row["produced"] == "True"]
    if produced_rows:
        for row in produced_rows:
            lines.append(f"- `{row['stage_name']}` {row['artifact_role']}: `{row['artifact_path']}`")
    else:
        lines.append("- Keine Artefakte erzeugt.")
    lines.extend(["", "## Warnings", ""])
    if manifest["warnings"]:
        lines.extend(f"- {warning}" for warning in manifest["warnings"])
    else:
        lines.append("- Keine Run-Warnings.")
    lines.extend(
        [
            "",
            "## Methodische Grenzen",
            "",
            "- Der Orchestrator koordiniert bestehende Engines und fuehrt keine neue Scoring-, Performance-, Benchmark- oder Tax-Fachlogik ein.",
            "- Fehlende Inputs werden stage-spezifisch abgewiesen statt still ersetzt.",
        ]
    )
    path = ensure_parent_dir(path_value)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def not_requested_result(stage_name: str) -> StageResult:
    return stage_result(stage_name, NOT_REQUESTED, [], notes="Stage was not requested.")


def skipped_result(stage_name: str, failed_stage: str) -> StageResult:
    return stage_result(
        stage_name,
        SKIPPED,
        [],
        warnings=[f"Blocked by failed stage: {failed_stage}"],
        notes=f"Skipped because requested upstream stage {failed_stage} failed.",
    )


def finalize_run_outputs(
    options: PersonalRunOptions,
    selected_stages: list[str],
    executed_stage_order: list[str],
    stage_results: list[StageResult],
    run_started_at: str,
    run_status: str,
    warnings: list[str],
    notes: str,
) -> dict[str, Any]:
    run_finished_at = utc_now_text()
    artifact_rows = artifact_rows_from_stage_results(stage_results)
    write_csv_rows(options.artifacts_output, ARTIFACT_FIELDS, artifact_rows)
    manifest = build_manifest(
        options,
        selected_stages,
        executed_stage_order,
        stage_results,
        run_started_at,
        run_finished_at,
        run_status,
        warnings,
        notes,
    )
    write_manifest(options.manifest_output, manifest)
    write_run_report(options.report_output or "", manifest, artifact_rows)
    return manifest


def run_personal_run_engine(options: PersonalRunOptions) -> dict[str, Any]:
    options = options.normalized()
    selected_stages = validate_stage_selection(options.stages)
    run_started_at = utc_now_text()
    stage_results_by_name: dict[str, StageResult] = {}
    executed_stage_order: list[str] = []
    warnings: list[str] = []
    failed_stage = ""
    failed_error: Exception | None = None

    for stage_name in STAGE_ORDER:
        if stage_name not in selected_stages:
            stage_results_by_name[stage_name] = not_requested_result(stage_name)
            continue
        if failed_stage:
            stage_results_by_name[stage_name] = skipped_result(stage_name, failed_stage)
            continue
        try:
            executed_stage_order.append(stage_name)
            result = STAGE_RUNNERS[stage_name](options)
            stage_results_by_name[stage_name] = result
            warnings.extend(f"{stage_name}: {warning}" for warning in result.warnings)
        except Exception as exc:
            failed_stage = stage_name
            failed_error = exc
            warnings.append(f"{stage_name}: {exc}")
            stage_results_by_name[stage_name] = stage_result(
                stage_name,
                FAILED,
                [],
                warnings=[str(exc)],
                notes=f"Stage failed: {exc}",
            )

    stage_results = [stage_results_by_name[stage] for stage in STAGE_ORDER]
    run_status = FAILED if failed_stage else SUCCESS
    notes = "Personal run completed." if not failed_stage else f"Personal run failed at stage {failed_stage}: {failed_error}"
    manifest = finalize_run_outputs(
        options,
        selected_stages,
        executed_stage_order,
        stage_results,
        run_started_at,
        run_status,
        warnings,
        notes,
    )
    if failed_error is not None:
        raise RuntimeError(str(failed_error))
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run selected personal pipeline stages and write a reproducible run manifest.")
    parser.add_argument("--stage", action="append", default=[], choices=STAGE_ORDER, help="Stage to run; repeat for multiple stages.")
    parser.add_argument("--positions-raw-input", help="Raw personal positions input for import stage.")
    parser.add_argument("--cash-input", help="Optional cash input for document import stage.")
    parser.add_argument("--import-mode", choices=["sample", "real", "tr_pdf"], default="real", help="Import mode.")
    parser.add_argument("--source-name", default="personal_depot", help="Source label for imported rows and manifest.")
    parser.add_argument("--portfolio-date", help="Optional portfolio date override for import stage.")
    parser.add_argument("--positions-output", default=DEFAULT_PATHS["positions_output"], help="Personal positions snapshot path.")
    parser.add_argument("--fundamentals-master", default=DEFAULT_PATHS["fundamentals_master"], help="Personal fundamentals master path.")
    parser.add_argument("--overwrite-fundamentals-master", action="store_true", help="Allow fundamentals_seed to overwrite an existing master.")
    parser.add_argument("--metric-definitions", default=DEFAULT_METRIC_DEFINITIONS_PATH, help="Fundamentals KPI definitions config.")
    parser.add_argument("--scores-output", default=DEFAULT_PATHS["scores_output"], help="Personal company scores output.")
    parser.add_argument("--score-audit-output", default=DEFAULT_PATHS["score_audit_output"], help="Personal score audit output.")
    parser.add_argument("--coverage-output", default=DEFAULT_PATHS["coverage_output"], help="Personal fundamentals coverage output.")
    parser.add_argument("--fundamentals-enriched-output", default=DEFAULT_PATHS["fundamentals_enriched_output"], help="Personal enriched fundamentals output.")
    parser.add_argument("--research-priority-output", default=DEFAULT_PATHS["research_priority_output"], help="Personal fundamentals research priority output.")
    parser.add_argument("--fundamentals-coverage-report-output", help="Personal fundamentals coverage markdown report output.")
    parser.add_argument("--fundamentals-evidence-input", default=DEFAULT_PATHS["fundamentals_evidence_input"], help="Manual personal fundamentals evidence input.")
    parser.add_argument("--fundamentals-evidence-registry-output", default=DEFAULT_PATHS["fundamentals_evidence_registry_output"], help="Personal fundamentals evidence registry output.")
    parser.add_argument("--fundamentals-research-backlog-output", default=DEFAULT_PATHS["fundamentals_research_backlog_output"], help="Personal fundamentals research backlog output.")
    parser.add_argument("--fundamentals-evidence-summary-output", default=DEFAULT_PATHS["fundamentals_evidence_summary_output"], help="Personal fundamentals evidence summary output.")
    parser.add_argument("--fundamentals-evidence-template-output", default=DEFAULT_PATHS["fundamentals_evidence_template_output"], help="Personal fundamentals evidence template output.")
    parser.add_argument("--fundamentals-evidence-report-output", help="Personal fundamentals evidence markdown report output.")
    parser.add_argument("--fundamentals-overlay-input", default=DEFAULT_PATHS["fundamentals_overlay_input"], help="Manual personal fundamentals overlay input.")
    parser.add_argument("--fundamentals-overlay-registry-output", default=DEFAULT_PATHS["fundamentals_overlay_registry_output"], help="Personal fundamentals overlay registry output.")
    parser.add_argument("--fundamentals-applied-master-output", default=DEFAULT_PATHS["fundamentals_applied_master_output"], help="Applied personal fundamentals master output.")
    parser.add_argument("--fundamentals-overlay-summary-output", default=DEFAULT_PATHS["fundamentals_overlay_summary_output"], help="Personal fundamentals overlay summary output.")
    parser.add_argument("--fundamentals-overlay-template-output", default=DEFAULT_PATHS["fundamentals_overlay_template_output"], help="Personal fundamentals overlay template output.")
    parser.add_argument("--fundamentals-overlay-report-output", help="Personal fundamentals overlay markdown report output.")
    parser.add_argument("--watchlist-input", help="Watchlist CSV input.")
    parser.add_argument("--watchlist-output", default=DEFAULT_PATHS["watchlist_output"], help="Ranked personal watchlist output.")
    parser.add_argument("--watchlist-report-output", default=DEFAULT_PATHS["watchlist_report_output"], help="Watchlist markdown report output.")
    parser.add_argument("--monthly-ranking-output", default=DEFAULT_PATHS["monthly_ranking_output"], help="Personal monthly ranking output.")
    parser.add_argument("--rebalance-output", default=DEFAULT_PATHS["rebalance_output"], help="Personal rebalance proposals output.")
    parser.add_argument("--monthly-report-output", default=DEFAULT_PATHS["monthly_report_output"], help="Monthly decision report output.")
    parser.add_argument("--portfolio-review-output", default=DEFAULT_PATHS["portfolio_review_output"], help="Portfolio review markdown output.")
    parser.add_argument("--holdings-output", default=DEFAULT_PATHS["holdings_output"], help="Holdings action table output.")
    parser.add_argument("--portfolio-archive", default=DEFAULT_PATHS["portfolio_archive"], help="Portfolio snapshot archive path.")
    parser.add_argument("--portfolio-timeseries-output", default=DEFAULT_PATHS["portfolio_timeseries_output"], help="Portfolio timeseries output.")
    parser.add_argument("--portfolio-history-summary-output", default=DEFAULT_PATHS["portfolio_history_summary_output"], help="Portfolio history summary output.")
    parser.add_argument("--portfolio-history-report-output", help="Portfolio history markdown report output.")
    parser.add_argument("--benchmark-input", help="Local benchmark input CSV for benchmark_archive or performance stage.")
    parser.add_argument("--benchmark-config", default="configs/benchmark.yaml", help="Benchmark config path.")
    parser.add_argument("--benchmark-archive", default=DEFAULT_PATHS["benchmark_archive"], help="Benchmark archive path.")
    parser.add_argument("--benchmark-registry-output", default=DEFAULT_PATHS["benchmark_registry_output"], help="Benchmark registry path.")
    parser.add_argument("--benchmark-normalized-output", default=DEFAULT_PATHS["benchmark_normalized_output"], help="Single-symbol normalized benchmark output.")
    parser.add_argument("--benchmark-archive-summary-output", default=DEFAULT_PATHS["benchmark_archive_summary_output"], help="Benchmark archive summary output.")
    parser.add_argument("--benchmark-history-report-output", help="Benchmark history markdown report output.")
    parser.add_argument("--benchmark-symbol", action="append", default=[], help="Benchmark symbol for multi-benchmark selection; repeatable.")
    parser.add_argument("--single-benchmark-symbol", help="Explicit single benchmark symbol for benchmark_archive normalized output.")
    parser.add_argument("--performance-benchmark", help="Benchmark CSV used by performance stage; defaults to benchmark-normalized-output.")
    parser.add_argument("--performance-summary-output", default=DEFAULT_PATHS["performance_summary_output"], help="Performance summary output.")
    parser.add_argument("--performance-comparison-output", default=DEFAULT_PATHS["performance_comparison_output"], help="Performance comparison output.")
    parser.add_argument("--performance-kpi-output", default=DEFAULT_PATHS["performance_kpi_output"], help="Performance KPI output.")
    parser.add_argument("--performance-report-output", help="Performance markdown report output.")
    parser.add_argument("--multi-benchmark-comparison-output", default=DEFAULT_PATHS["multi_benchmark_comparison_output"], help="Multi-benchmark comparison output.")
    parser.add_argument("--multi-benchmark-summary-output", default=DEFAULT_PATHS["multi_benchmark_summary_output"], help="Multi-benchmark summary output.")
    parser.add_argument("--multi-benchmark-kpi-output", default=DEFAULT_PATHS["multi_benchmark_kpi_output"], help="Multi-benchmark KPI output.")
    parser.add_argument("--multi-benchmark-report-output", help="Multi-benchmark markdown report output.")
    parser.add_argument("--ledger", help="Manual cost/tax ledger CSV input.")
    parser.add_argument("--cost-tax-document", action="append", default=[], help="Supported cost/tax document input; repeatable.")
    parser.add_argument("--cost-tax-archive", default=DEFAULT_PATHS["cost_tax_archive"], help="Cost/tax ledger archive path.")
    parser.add_argument("--cost-tax-normalized-ledger-output", default=DEFAULT_PATHS["cost_tax_normalized_ledger_output"], help="Normalized cost/tax ledger output.")
    parser.add_argument("--cost-tax-summary-output", default=DEFAULT_PATHS["cost_tax_summary_output"], help="Cost/tax summary output.")
    parser.add_argument("--cost-tax-kpi-output", default=DEFAULT_PATHS["cost_tax_kpi_output"], help="Cost/tax KPI output.")
    parser.add_argument("--cost-tax-archive-summary-output", default=DEFAULT_PATHS["cost_tax_archive_summary_output"], help="Cost/tax archive summary output.")
    parser.add_argument("--cost-tax-report-output", help="Cost/tax markdown report output.")
    parser.add_argument("--dashboard-kpi-output", default=DEFAULT_PATHS["dashboard_kpi_output"], help="Dashboard KPI output.")
    parser.add_argument("--dashboard-sections-output", default=DEFAULT_PATHS["dashboard_sections_output"], help="Dashboard sections output.")
    parser.add_argument("--dashboard-summary-output", default=DEFAULT_PATHS["dashboard_summary_output"], help="Dashboard summary output.")
    parser.add_argument("--dashboard-report-output", help="Dashboard markdown report output.")
    parser.add_argument("--manifest-output", default=DEFAULT_PATHS["manifest_output"], help="Personal run manifest JSON output.")
    parser.add_argument("--artifacts-output", default=DEFAULT_PATHS["artifacts_output"], help="Personal run artifacts CSV output.")
    parser.add_argument("--report-output", help="Personal run markdown report output.")
    return parser.parse_args()


def options_from_args(args: argparse.Namespace) -> PersonalRunOptions:
    return PersonalRunOptions(
        stages=args.stage,
        positions_raw_input=args.positions_raw_input,
        cash_input=args.cash_input,
        import_mode=args.import_mode,
        source_name=args.source_name,
        portfolio_date=args.portfolio_date,
        positions_output=args.positions_output,
        fundamentals_master=args.fundamentals_master,
        overwrite_fundamentals_master=args.overwrite_fundamentals_master,
        metric_definitions=args.metric_definitions,
        scores_output=args.scores_output,
        score_audit_output=args.score_audit_output,
        coverage_output=args.coverage_output,
        fundamentals_enriched_output=args.fundamentals_enriched_output,
        research_priority_output=args.research_priority_output,
        fundamentals_coverage_report_output=args.fundamentals_coverage_report_output,
        fundamentals_evidence_input=args.fundamentals_evidence_input,
        fundamentals_evidence_registry_output=args.fundamentals_evidence_registry_output,
        fundamentals_research_backlog_output=args.fundamentals_research_backlog_output,
        fundamentals_evidence_summary_output=args.fundamentals_evidence_summary_output,
        fundamentals_evidence_template_output=args.fundamentals_evidence_template_output,
        fundamentals_evidence_report_output=args.fundamentals_evidence_report_output,
        fundamentals_overlay_input=args.fundamentals_overlay_input,
        fundamentals_overlay_registry_output=args.fundamentals_overlay_registry_output,
        fundamentals_applied_master_output=args.fundamentals_applied_master_output,
        fundamentals_overlay_summary_output=args.fundamentals_overlay_summary_output,
        fundamentals_overlay_template_output=args.fundamentals_overlay_template_output,
        fundamentals_overlay_report_output=args.fundamentals_overlay_report_output,
        watchlist_input=args.watchlist_input,
        watchlist_output=args.watchlist_output,
        watchlist_report_output=args.watchlist_report_output,
        monthly_ranking_output=args.monthly_ranking_output,
        rebalance_output=args.rebalance_output,
        monthly_report_output=args.monthly_report_output,
        portfolio_review_output=args.portfolio_review_output,
        holdings_output=args.holdings_output,
        portfolio_archive=args.portfolio_archive,
        portfolio_timeseries_output=args.portfolio_timeseries_output,
        portfolio_history_summary_output=args.portfolio_history_summary_output,
        portfolio_history_report_output=args.portfolio_history_report_output,
        benchmark_input=args.benchmark_input,
        benchmark_config=args.benchmark_config,
        benchmark_archive=args.benchmark_archive,
        benchmark_registry_output=args.benchmark_registry_output,
        benchmark_normalized_output=args.benchmark_normalized_output,
        benchmark_archive_summary_output=args.benchmark_archive_summary_output,
        benchmark_history_report_output=args.benchmark_history_report_output,
        benchmark_symbols=args.benchmark_symbol,
        single_benchmark_symbol=args.single_benchmark_symbol,
        performance_benchmark=args.performance_benchmark,
        performance_summary_output=args.performance_summary_output,
        performance_comparison_output=args.performance_comparison_output,
        performance_kpi_output=args.performance_kpi_output,
        performance_report_output=args.performance_report_output,
        multi_benchmark_comparison_output=args.multi_benchmark_comparison_output,
        multi_benchmark_summary_output=args.multi_benchmark_summary_output,
        multi_benchmark_kpi_output=args.multi_benchmark_kpi_output,
        multi_benchmark_report_output=args.multi_benchmark_report_output,
        ledger=args.ledger,
        cost_tax_documents=args.cost_tax_document,
        cost_tax_archive=args.cost_tax_archive,
        cost_tax_normalized_ledger_output=args.cost_tax_normalized_ledger_output,
        cost_tax_summary_output=args.cost_tax_summary_output,
        cost_tax_kpi_output=args.cost_tax_kpi_output,
        cost_tax_archive_summary_output=args.cost_tax_archive_summary_output,
        cost_tax_report_output=args.cost_tax_report_output,
        dashboard_kpi_output=args.dashboard_kpi_output,
        dashboard_sections_output=args.dashboard_sections_output,
        dashboard_summary_output=args.dashboard_summary_output,
        dashboard_report_output=args.dashboard_report_output,
        manifest_output=args.manifest_output,
        artifacts_output=args.artifacts_output,
        report_output=args.report_output,
    )


def main() -> None:
    args = parse_args()
    run_personal_run_engine(options_from_args(args))


if __name__ == "__main__":
    main()
