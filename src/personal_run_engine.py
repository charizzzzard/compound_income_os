from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
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
from src.cost_tax_archive_engine import DEFAULT_CONFIG_PATH as DEFAULT_COST_TAX_CONFIG_PATH, run_cost_tax_archive_engine
from src.data_source_registry import (
    DEFAULT_CONFIG_PATH as DEFAULT_DATA_SOURCES_CONFIG_PATH,
    DEFAULT_RESOLVED_OUTPUT as DEFAULT_DATA_SOURCE_RESOLVED_OUTPUT,
    DEFAULT_STATUS_OUTPUT as DEFAULT_DATA_SOURCE_STATUS_OUTPUT,
    SourceRecord,
    build_status_rows as build_data_source_status_rows,
    load_personal_data_source_records,
    missing_required_source_keys,
    write_data_source_outputs,
)
from src.dashboard_engine import DEFAULT_CONFIG_PATH as DEFAULT_DASHBOARD_CONFIG_PATH, run_dashboard_engine
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
    DEFAULT_PROPOSED_UPDATES_OUTPUT,
    DEFAULT_REGISTRY_OUTPUT,
    DEFAULT_SUMMARY_OUTPUT as DEFAULT_EVIDENCE_SUMMARY_OUTPUT,
    run_fundamentals_evidence_engine,
)
from src.fundamentals_overlay_engine import (
    DEFAULT_APPLIED_MASTER_OUTPUT,
    DEFAULT_OVERLAY_INPUT_PATH,
    DEFAULT_OVERLAY_REGISTRY_OUTPUT,
    DEFAULT_OVERLAY_REVIEW_BACKLOG_OUTPUT,
    DEFAULT_SCHEMA_PATH as DEFAULT_OVERLAY_SCHEMA_PATH,
    DEFAULT_OVERLAY_SUMMARY_OUTPUT,
    DEFAULT_OVERLAY_TEMPLATE_PATH,
    run_fundamentals_overlay_engine,
)
from src.fundamentals_profile_engine import (
    DEFAULT_PROFILE_REGISTRY_OUTPUT,
    DEFAULT_PROFILE_REVIEW_BACKLOG_OUTPUT,
    DEFAULT_PROFILE_REVIEW_INPUT_PATH,
    DEFAULT_PROFILED_MASTER_OUTPUT,
    run_fundamentals_profile_engine,
)
from src.fundamentals_snapshot_ingestion import (
    DEFAULT_EVIDENCE_STAGING_OUTPUT as DEFAULT_SNAPSHOT_EVIDENCE_STAGING_OUTPUT,
    DEFAULT_NORMALIZED_OUTPUT as DEFAULT_SNAPSHOT_NORMALIZED_OUTPUT,
    DEFAULT_SNAPSHOT_INPUT_PATH,
    DEFAULT_SUMMARY_OUTPUT as DEFAULT_SNAPSHOT_SUMMARY_OUTPUT,
    DEFAULT_UNMATCHED_OUTPUT as DEFAULT_SNAPSHOT_UNMATCHED_OUTPUT,
    run_fundamentals_snapshot_ingestion,
)
from src.multi_benchmark_performance_engine import run_multi_benchmark_performance_engine
from src.performance_engine import run_performance_engine
from src.portfolio_history_engine import run_portfolio_history_engine
from src.portfolio_review import DEFAULT_RULES_PATH as DEFAULT_PORTFOLIO_REVIEW_RULES_PATH
from src.traderepublic_documents import load_trade_republic_pdf_rows

SUCCESS = "SUCCESS"
FAILED = "FAILED"
SKIPPED = "SKIPPED"
NOT_REQUESTED = "NOT_REQUESTED"

STAGE_ORDER = [
    "data_sources_validate",
    "import",
    "fundamentals_seed",
    "fundamentals_profile",
    "fundamentals_snapshot_ingest",
    "fundamentals_evidence",
    "fundamentals_overlay",
    "scoring",
    "coverage",
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
USED_INPUT_FIELDS = ["stage_name", "stage_status", "input_role", "input_path", "input_exists", "notes"]
RUN_ARTIFACT_STAGE = "personal_run"
USED_INPUT_METADATA_ROLES = {"fundamentals_source_mode", "import_mode", "source_name", "single_benchmark_symbol"}
FUNDAMENTALS_SOURCE_STAGES = {"fundamentals_overlay", "scoring", "coverage", "watchlist", "monthly", "portfolio_review"}


def default_dated_report_path(file_name: str) -> str:
    return f"reports/{date.today().isoformat()}/{file_name}"


DEFAULT_PATHS = {
    "data_sources_config": DEFAULT_DATA_SOURCES_CONFIG_PATH,
    "data_source_status_output": DEFAULT_DATA_SOURCE_STATUS_OUTPUT,
    "data_source_resolved_output": DEFAULT_DATA_SOURCE_RESOLVED_OUTPUT,
    "positions_output": "data/processed/personal_positions_snapshot.csv",
    "fundamentals_master": "data/raw/personal_fundamentals_master.csv",
    "scores_output": "data/processed/personal_company_scores.csv",
    "score_audit_output": "data/processed/personal_score_audit.csv",
    "coverage_output": "data/processed/personal_fundamentals_coverage.csv",
    "fundamentals_enriched_output": "data/processed/personal_fundamentals_enriched.csv",
    "research_priority_output": DEFAULT_RESEARCH_PRIORITY_OUTPUT,
    "profile_review_input": DEFAULT_PROFILE_REVIEW_INPUT_PATH,
    "profile_review_registry_output": DEFAULT_PROFILE_REGISTRY_OUTPUT,
    "profile_review_backlog_output": DEFAULT_PROFILE_REVIEW_BACKLOG_OUTPUT,
    "profiled_master_output": DEFAULT_PROFILED_MASTER_OUTPUT,
    "fundamentals_snapshot_input": DEFAULT_SNAPSHOT_INPUT_PATH,
    "fundamentals_snapshot_normalized_output": DEFAULT_SNAPSHOT_NORMALIZED_OUTPUT,
    "fundamentals_snapshot_unmatched_output": DEFAULT_SNAPSHOT_UNMATCHED_OUTPUT,
    "fundamentals_snapshot_evidence_staging_output": DEFAULT_SNAPSHOT_EVIDENCE_STAGING_OUTPUT,
    "fundamentals_snapshot_summary_output": DEFAULT_SNAPSHOT_SUMMARY_OUTPUT,
    "fundamentals_evidence_input": DEFAULT_EVIDENCE_INPUT_PATH,
    "fundamentals_evidence_registry_output": DEFAULT_REGISTRY_OUTPUT,
    "fundamentals_research_backlog_output": DEFAULT_BACKLOG_OUTPUT,
    "fundamentals_proposed_updates_output": DEFAULT_PROPOSED_UPDATES_OUTPUT,
    "fundamentals_evidence_summary_output": DEFAULT_EVIDENCE_SUMMARY_OUTPUT,
    "fundamentals_evidence_template_output": DEFAULT_EVIDENCE_TEMPLATE_PATH,
    "fundamentals_overlay_input": DEFAULT_OVERLAY_INPUT_PATH,
    "fundamentals_overlay_registry_output": DEFAULT_OVERLAY_REGISTRY_OUTPUT,
    "fundamentals_applied_master_output": DEFAULT_APPLIED_MASTER_OUTPUT,
    "fundamentals_overlay_summary_output": DEFAULT_OVERLAY_SUMMARY_OUTPUT,
    "fundamentals_overlay_review_backlog_output": DEFAULT_OVERLAY_REVIEW_BACKLOG_OUTPUT,
    "fundamentals_overlay_template_output": DEFAULT_OVERLAY_TEMPLATE_PATH,
    "watchlist_output": "data/processed/personal_watchlist_ranked.csv",
    "watchlist_report_output": default_dated_report_path("personal_watchlist_report.md"),
    "monthly_ranking_output": "data/processed/personal_monthly_buy_ranking.csv",
    "rebalance_output": "data/processed/personal_rebalance_proposals.csv",
    "monthly_report_output": default_dated_report_path("personal_monthly_decision_report.md"),
    "portfolio_review_output": default_dated_report_path("personal_portfolio_review.md"),
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
    "used_inputs_output": "data/processed/personal_run_used_inputs.csv",
}

DATA_SOURCE_OPTION_FIELDS = {
    "fundamentals_master": "fundamentals_master",
    "profile_review_input": "profile_review_input",
    "fundamentals_snapshot_input": "fundamentals_snapshot_input",
    "fundamentals_evidence_input": "fundamentals_evidence_input",
    "fundamentals_overlay_input": "fundamentals_overlay_input",
    "benchmark_input": "benchmark_input",
    "cost_tax_ledger_input": "ledger",
    "positions_raw_input": "positions_raw_input",
    "cash_input": "cash_input",
}

OPTION_FIELD_DEFAULTS = {
    "positions_raw_input": "",
    "cash_input": "",
    "fundamentals_master": DEFAULT_PATHS["fundamentals_master"],
    "profile_review_input": DEFAULT_PATHS["profile_review_input"],
    "fundamentals_snapshot_input": DEFAULT_PATHS["fundamentals_snapshot_input"],
    "fundamentals_evidence_input": DEFAULT_PATHS["fundamentals_evidence_input"],
    "fundamentals_overlay_input": DEFAULT_PATHS["fundamentals_overlay_input"],
    "benchmark_input": "",
    "ledger": "",
}


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
    data_sources_config: str = DEFAULT_PATHS["data_sources_config"]
    data_source_status_output: str = DEFAULT_PATHS["data_source_status_output"]
    data_source_resolved_output: str = DEFAULT_PATHS["data_source_resolved_output"]
    positions_raw_input: str | None = None
    cash_input: str | None = None
    import_mode: str = "real"
    source_name: str = "personal_depot"
    portfolio_date: str | None = None
    positions_output: str = DEFAULT_PATHS["positions_output"]
    fundamentals_master: str = DEFAULT_PATHS["fundamentals_master"]
    overwrite_fundamentals_master: bool = False
    use_profiled_master: bool = False
    use_applied_master: bool = False
    metric_definitions: str = DEFAULT_METRIC_DEFINITIONS_PATH
    scores_output: str = DEFAULT_PATHS["scores_output"]
    score_audit_output: str = DEFAULT_PATHS["score_audit_output"]
    coverage_output: str = DEFAULT_PATHS["coverage_output"]
    fundamentals_enriched_output: str = DEFAULT_PATHS["fundamentals_enriched_output"]
    research_priority_output: str = DEFAULT_PATHS["research_priority_output"]
    fundamentals_coverage_report_output: str | None = None
    profile_review_input: str = DEFAULT_PATHS["profile_review_input"]
    profile_review_registry_output: str = DEFAULT_PATHS["profile_review_registry_output"]
    profile_review_backlog_output: str = DEFAULT_PATHS["profile_review_backlog_output"]
    profiled_master_output: str = DEFAULT_PATHS["profiled_master_output"]
    fundamentals_snapshot_input: str = DEFAULT_PATHS["fundamentals_snapshot_input"]
    fundamentals_snapshot_normalized_output: str = DEFAULT_PATHS["fundamentals_snapshot_normalized_output"]
    fundamentals_snapshot_unmatched_output: str = DEFAULT_PATHS["fundamentals_snapshot_unmatched_output"]
    fundamentals_snapshot_evidence_staging_output: str = DEFAULT_PATHS["fundamentals_snapshot_evidence_staging_output"]
    fundamentals_snapshot_summary_output: str = DEFAULT_PATHS["fundamentals_snapshot_summary_output"]
    fundamentals_evidence_input: str = DEFAULT_PATHS["fundamentals_evidence_input"]
    fundamentals_evidence_registry_output: str = DEFAULT_PATHS["fundamentals_evidence_registry_output"]
    fundamentals_research_backlog_output: str = DEFAULT_PATHS["fundamentals_research_backlog_output"]
    fundamentals_proposed_updates_output: str = DEFAULT_PATHS["fundamentals_proposed_updates_output"]
    fundamentals_evidence_summary_output: str = DEFAULT_PATHS["fundamentals_evidence_summary_output"]
    fundamentals_evidence_template_output: str = DEFAULT_PATHS["fundamentals_evidence_template_output"]
    fundamentals_evidence_report_output: str | None = None
    fundamentals_overlay_input: str = DEFAULT_PATHS["fundamentals_overlay_input"]
    fundamentals_overlay_registry_output: str = DEFAULT_PATHS["fundamentals_overlay_registry_output"]
    fundamentals_applied_master_output: str = DEFAULT_PATHS["fundamentals_applied_master_output"]
    fundamentals_overlay_summary_output: str = DEFAULT_PATHS["fundamentals_overlay_summary_output"]
    fundamentals_overlay_review_backlog_output: str = DEFAULT_PATHS["fundamentals_overlay_review_backlog_output"]
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
    used_inputs_output: str = DEFAULT_PATHS["used_inputs_output"]
    report_output: str | None = None
    input_resolution_baseline: dict[str, str] = field(default_factory=dict)
    resolved_default_source_keys: set[str] = field(default_factory=set)
    resolved_default_input_fields: dict[str, str] = field(default_factory=dict)
    data_source_records: dict[str, SourceRecord] = field(default_factory=dict)
    data_source_status_rows: list[dict[str, str]] = field(default_factory=list)
    data_source_registry_loaded: bool = False

    def normalized(self) -> "PersonalRunOptions":
        if not self.input_resolution_baseline:
            self.input_resolution_baseline = {
                field_name: str(getattr(self, field_name, "") or "")
                for field_name in OPTION_FIELD_DEFAULTS
            }
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


def option_was_explicitly_set(options: PersonalRunOptions, field_name: str) -> bool:
    baseline = str(options.input_resolution_baseline.get(field_name, "") or "")
    default_value = str(OPTION_FIELD_DEFAULTS.get(field_name, "") or "")
    return baseline != default_value


def ensure_data_source_registry_loaded(options: PersonalRunOptions) -> None:
    if options.data_source_registry_loaded:
        return
    records = load_personal_data_source_records(options.data_sources_config)
    options.data_source_records = records
    options.data_source_status_rows = build_data_source_status_rows(records)
    for source_key, field_name in DATA_SOURCE_OPTION_FIELDS.items():
        record = records.get(source_key)
        if record is None or not record.enabled or record.status != "OK":
            continue
        if option_was_explicitly_set(options, field_name):
            continue
        setattr(options, field_name, record.configured_path)
        options.resolved_default_source_keys.add(source_key)
        options.resolved_default_input_fields[field_name] = source_key
    options.data_source_registry_loaded = True


def maybe_raise_required_registry_source(options: PersonalRunOptions, field_name: str, stage_name: str) -> None:
    if option_was_explicitly_set(options, field_name):
        return
    source_key = next((key for key, mapped_field in DATA_SOURCE_OPTION_FIELDS.items() if mapped_field == field_name), "")
    if not source_key:
        return
    ensure_data_source_registry_loaded(options)
    record = options.data_source_records.get(source_key)
    if record is None or not record.enabled or not record.required or record.status != "MISSING":
        return
    raise ValueError(
        f"stage {stage_name} requires configured data source '{source_key}' from {options.data_sources_config}: "
        f"{record.configured_path}"
    )


def append_registry_default_note(options: PersonalRunOptions, note: str, *field_names: str) -> str:
    source_keys = sorted(
        {
            options.resolved_default_input_fields.get(field_name, "")
            for field_name in field_names
            if options.resolved_default_input_fields.get(field_name, "")
        }
    )
    source_keys = [source_key for source_key in source_keys if source_key]
    if not source_keys:
        return note
    suffix = f"data_source_registry_defaults={','.join(source_keys)}"
    if not note:
        return f"{suffix}."
    return f"{note.rstrip('.')}; {suffix}."


def input_snapshot(options: PersonalRunOptions) -> dict[str, Any]:
    return {
        "data_sources_config": options.data_sources_config,
        "positions_raw_input": options.positions_raw_input or "",
        "cash_input": options.cash_input or "",
        "import_mode": options.import_mode,
        "source_name": options.source_name,
        "portfolio_date": options.portfolio_date or "",
        "positions_output": options.positions_output,
        "fundamentals_master": options.fundamentals_master,
        "use_profiled_master": options.use_profiled_master,
        "fundamentals_applied_master": options.fundamentals_applied_master_output,
        "use_applied_master": options.use_applied_master,
        "research_priority_output": options.research_priority_output,
        "profile_review_input": options.profile_review_input,
        "profile_review_registry_output": options.profile_review_registry_output,
        "profile_review_backlog_output": options.profile_review_backlog_output,
        "profiled_master_output": options.profiled_master_output,
        "fundamentals_snapshot_input": options.fundamentals_snapshot_input,
        "fundamentals_snapshot_normalized_output": options.fundamentals_snapshot_normalized_output,
        "fundamentals_snapshot_unmatched_output": options.fundamentals_snapshot_unmatched_output,
        "fundamentals_snapshot_evidence_staging_output": options.fundamentals_snapshot_evidence_staging_output,
        "fundamentals_snapshot_summary_output": options.fundamentals_snapshot_summary_output,
        "data_source_status_output": options.data_source_status_output,
        "data_source_resolved_output": options.data_source_resolved_output,
        "fundamentals_evidence_input": options.fundamentals_evidence_input,
        "fundamentals_proposed_updates_output": options.fundamentals_proposed_updates_output,
        "fundamentals_overlay_input": options.fundamentals_overlay_input,
        "fundamentals_overlay_review_backlog_output": options.fundamentals_overlay_review_backlog_output,
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
        "used_inputs_output": options.used_inputs_output,
    }


def resolve_fundamentals_source(
    options: PersonalRunOptions,
    stage_name: str,
    *,
    require_path_for_base: bool,
    allow_applied_master: bool = True,
) -> tuple[str | None, str, str | None]:
    if options.use_profiled_master and options.use_applied_master:
        raise ValueError("--use-profiled-master and --use-applied-master are mutually exclusive")
    if options.use_profiled_master:
        profiled_path = require_existing_path(
            options.profiled_master_output,
            "profiled personal fundamentals master (--use-profiled-master)",
            stage_name,
        )
        return profiled_path, "PROFILED", "profiled_master_output"
    if allow_applied_master and options.use_applied_master:
        applied_path = require_existing_path(
            options.fundamentals_applied_master_output,
            "applied personal fundamentals master (--use-applied-master)",
            stage_name,
        )
        return applied_path, "APPLIED", "fundamentals_applied_master_output"
    if require_path_for_base:
        maybe_raise_required_registry_source(options, "fundamentals_master", stage_name)
        base_path = require_existing_path(options.fundamentals_master, "personal fundamentals master", stage_name)
        return base_path, "BASE", "fundamentals_master"
    return None, "BASE", None


def run_data_sources_validate_stage(options: PersonalRunOptions) -> StageResult:
    stage = "data_sources_validate"
    ensure_data_source_registry_loaded(options)
    outputs = write_data_source_outputs(
        options.data_source_records,
        status_output=options.data_source_status_output,
        resolved_output=options.data_source_resolved_output,
        used_as_default_source_keys=options.resolved_default_source_keys,
    )
    missing_required = missing_required_source_keys(options.data_source_records)
    used_inputs = {"data_sources_config": options.data_sources_config}
    for source_key, record in options.data_source_records.items():
        used_inputs[f"source_{source_key}"] = record.configured_path
    if missing_required:
        missing_text = ", ".join(missing_required)
        raise ValueError(f"data source registry has missing required source(s): {missing_text}")
    return stage_result(
        stage,
        SUCCESS,
        ["data_sources_config"],
        used_inputs=used_inputs,
        produced_outputs={role: str(path) for role, path in outputs.items()},
        notes="Personal data source registry validated; status and resolved default-input outputs generated.",
    )


def run_import_stage(options: PersonalRunOptions) -> StageResult:
    stage = "import"
    maybe_raise_required_registry_source(options, "positions_raw_input", stage)
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


def run_fundamentals_profile_stage(options: PersonalRunOptions) -> StageResult:
    stage = "fundamentals_profile"
    maybe_raise_required_registry_source(options, "fundamentals_master", stage)
    maybe_raise_required_registry_source(options, "profile_review_input", stage)
    fundamentals_path = require_existing_path(options.fundamentals_master, "personal fundamentals master", stage)
    profile_review_path = require_existing_path(options.profile_review_input, "personal profile review input", stage)
    outputs = run_fundamentals_profile_engine(
        fundamentals_master_path=fundamentals_path,
        profile_review_input_path=profile_review_path,
        registry_output=options.profile_review_registry_output,
        backlog_output=options.profile_review_backlog_output,
        profiled_master_output=options.profiled_master_output,
        template_output=None,
    )
    return stage_result(
        stage,
        SUCCESS,
        ["fundamentals_master", "profile_review_input"],
        used_inputs={
            "fundamentals_master": fundamentals_path,
            "profile_review_input": profile_review_path,
        },
        produced_outputs={role: str(path) for role, path in outputs.items()},
        notes=append_registry_default_note(
            options,
            "Profile review registry, backlog and profiled master projection generated; raw master remained unchanged and downstream stages stayed on existing BASE/APPLIED semantics.",
            "fundamentals_master",
            "profile_review_input",
        ),
    )


def run_fundamentals_snapshot_ingest_stage(options: PersonalRunOptions) -> StageResult:
    stage = "fundamentals_snapshot_ingest"
    maybe_raise_required_registry_source(options, "fundamentals_master", stage)
    maybe_raise_required_registry_source(options, "fundamentals_snapshot_input", stage)
    fundamentals_path = require_existing_path(options.fundamentals_master, "personal fundamentals master", stage)
    snapshot_input_path = require_existing_path(options.fundamentals_snapshot_input, "local fundamentals snapshot input", stage)
    outputs = run_fundamentals_snapshot_ingestion(
        fundamentals_master_path=fundamentals_path,
        snapshot_input_path=snapshot_input_path,
        normalized_output=options.fundamentals_snapshot_normalized_output,
        unmatched_output=options.fundamentals_snapshot_unmatched_output,
        evidence_staging_output=options.fundamentals_snapshot_evidence_staging_output,
        summary_output=options.fundamentals_snapshot_summary_output,
        template_output=None,
    )
    return stage_result(
        stage,
        SUCCESS,
        ["fundamentals_master", "fundamentals_snapshot_input"],
        used_inputs={
            "fundamentals_master": fundamentals_path,
            "fundamentals_snapshot_input": snapshot_input_path,
        },
        produced_outputs={role: str(path) for role, path in outputs.items()},
        notes=append_registry_default_note(
            options,
            "Local fundamentals snapshot normalized, unmatched rows isolated and evidence-staging CSV generated; no raw master or evidence input was modified.",
            "fundamentals_master",
            "fundamentals_snapshot_input",
        ),
    )


def run_scoring_stage(options: PersonalRunOptions) -> StageResult:
    stage = "scoring"
    positions_path = require_existing_path(options.positions_output, "positions snapshot", stage)
    fundamentals_path, fundamentals_source_mode, fundamentals_required_input = resolve_fundamentals_source(options, stage, require_path_for_base=True)
    assert fundamentals_path is not None
    rules_path = scoring_engine.DEFAULT_RULES_PATH
    scoring_path = scoring_engine.DEFAULT_SCORING_PATH
    fundamentals_score_rules_path = scoring_engine.DEFAULT_FUNDAMENTALS_SCORE_RULES_PATH
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
        rules_path=rules_path,
        scoring_path=scoring_path,
        fundamentals_source_name=f"fundamentals CSV ({fundamentals_path})",
        fundamentals_format="personal",
        fundamentals_score_rules_path=fundamentals_score_rules_path,
    )
    write_csv_rows(options.scores_output, scoring_engine.OUTPUT_FIELDS, results)
    write_csv_rows(options.score_audit_output, scoring_engine.SCORE_AUDIT_FIELDS, audit_rows)
    return stage_result(
        stage,
        SUCCESS,
        ["positions_output", fundamentals_required_input or "fundamentals_master"],
        used_inputs={
            "positions_output": positions_path,
            "fundamentals_master": fundamentals_path,
            "portfolio_rules": rules_path,
            "scoring_config": scoring_path,
            "fundamentals_score_rules": fundamentals_score_rules_path,
            "fundamentals_source_mode": fundamentals_source_mode,
        },
        produced_outputs={"company_scores": options.scores_output, "score_audit": options.score_audit_output},
        notes=append_registry_default_note(
            options,
            f"Scores generated with fundamentals_format=personal; fundamentals_source_mode={fundamentals_source_mode}; no sample fundamentals fallback used.",
            "fundamentals_master",
        ),
    )


def run_coverage_stage(options: PersonalRunOptions) -> StageResult:
    stage = "coverage"
    positions_path = require_existing_path(options.positions_output, "positions snapshot", stage)
    fundamentals_path, fundamentals_source_mode, fundamentals_required_input = resolve_fundamentals_source(options, stage, require_path_for_base=True)
    assert fundamentals_path is not None
    scores_path = require_existing_path(options.scores_output, "personal company scores", stage)
    metric_definitions_path = options.metric_definitions
    positions_rows = read_csv_rows(positions_path)
    fundamentals_rows = read_csv_rows(fundamentals_path)
    warnings = validate_personal_fundamentals_master(fundamentals_rows, f"personal fundamentals master ({fundamentals_path})")
    definitions = load_metric_definitions(metric_definitions_path)
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
        ["positions_output", fundamentals_required_input or "fundamentals_master", "scores_output"],
        used_inputs={
            "positions_output": positions_path,
            "fundamentals_master": fundamentals_path,
            "metric_definitions": metric_definitions_path,
            "fundamentals_source_mode": fundamentals_source_mode,
            "scores_output": scores_path,
        },
        produced_outputs={
            "fundamentals_coverage": options.coverage_output,
            "fundamentals_enriched": options.fundamentals_enriched_output,
            "fundamentals_coverage_report": options.fundamentals_coverage_report_output or "",
            "research_priority": options.research_priority_output,
        },
        warnings=warnings,
        notes=append_registry_default_note(
            options,
            f"Personal fundamentals coverage, profile guardrails and research priority generated with fundamentals_source_mode={fundamentals_source_mode}.",
            "fundamentals_master",
        ),
    )


def run_fundamentals_evidence_stage(options: PersonalRunOptions) -> StageResult:
    stage = "fundamentals_evidence"
    maybe_raise_required_registry_source(options, "fundamentals_master", stage)
    maybe_raise_required_registry_source(options, "fundamentals_evidence_input", stage)
    fundamentals_path = require_existing_path(options.fundamentals_master, "personal fundamentals master", stage)
    evidence_path = require_existing_path(options.fundamentals_evidence_input, "personal fundamentals evidence input", stage)
    metric_definitions_path = options.metric_definitions
    outputs = run_fundamentals_evidence_engine(
        fundamentals_master_path=fundamentals_path,
        evidence_input_path=evidence_path,
        metric_definitions_path=metric_definitions_path,
        registry_output=options.fundamentals_evidence_registry_output,
        backlog_output=options.fundamentals_research_backlog_output,
        proposed_updates_output=options.fundamentals_proposed_updates_output,
        summary_output=options.fundamentals_evidence_summary_output,
        report_output=options.fundamentals_evidence_report_output,
        template_output=options.fundamentals_evidence_template_output,
    )
    return stage_result(
        stage,
        SUCCESS,
        ["fundamentals_master", "fundamentals_evidence_input"],
        used_inputs={
            "fundamentals_master": fundamentals_path,
            "fundamentals_evidence_input": evidence_path,
            "metric_definitions": metric_definitions_path,
        },
        produced_outputs={role: str(path) for role, path in outputs.items()},
        notes=append_registry_default_note(
            options,
            "Personal fundamentals evidence registry and research backlog generated; master and scores were not modified.",
            "fundamentals_master",
            "fundamentals_evidence_input",
        ),
    )


def run_fundamentals_overlay_stage(options: PersonalRunOptions) -> StageResult:
    stage = "fundamentals_overlay"
    fundamentals_path, fundamentals_source_mode, fundamentals_required_input = resolve_fundamentals_source(
        options,
        stage,
        require_path_for_base=True,
        allow_applied_master=False,
    )
    assert fundamentals_path is not None
    maybe_raise_required_registry_source(options, "fundamentals_overlay_input", stage)
    overlay_path = require_existing_path(options.fundamentals_overlay_input, "personal fundamentals overlay input", stage)
    schema_path = DEFAULT_OVERLAY_SCHEMA_PATH
    outputs = run_fundamentals_overlay_engine(
        fundamentals_master_path=fundamentals_path,
        overlay_input_path=overlay_path,
        schema_path=schema_path,
        registry_output=options.fundamentals_overlay_registry_output,
        applied_master_output=options.fundamentals_applied_master_output,
        summary_output=options.fundamentals_overlay_summary_output,
        review_backlog_output=options.fundamentals_overlay_review_backlog_output,
        report_output=options.fundamentals_overlay_report_output,
        template_output=options.fundamentals_overlay_template_output,
    )
    return stage_result(
        stage,
        SUCCESS,
        [fundamentals_required_input or "fundamentals_master", "fundamentals_overlay_input"],
        used_inputs={
            "fundamentals_master": fundamentals_path,
            "fundamentals_overlay_input": overlay_path,
            "fundamentals_schema": schema_path,
            "fundamentals_source_mode": fundamentals_source_mode,
        },
        produced_outputs={role: str(path) for role, path in outputs.items()},
        notes=append_registry_default_note(
            options,
            f"Personal fundamentals overlay registry and applied master projection generated from fundamentals_source_mode={fundamentals_source_mode}; original master and scores were not modified.",
            "fundamentals_master",
            "fundamentals_overlay_input",
        ),
    )


def run_watchlist_stage(options: PersonalRunOptions) -> StageResult:
    stage = "watchlist"
    fundamentals_path, fundamentals_source_mode, _fundamentals_required_input = resolve_fundamentals_source(options, stage, require_path_for_base=False)
    watchlist_path = require_existing_path(options.watchlist_input, "watchlist input", stage)
    scores_path = require_existing_path(options.scores_output, "personal company scores", stage)
    watchlist_config_path = watchlist_engine.DEFAULT_WATCHLIST_CONFIG
    rules_path = watchlist_engine.DEFAULT_RULES_PATH
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
        config_path=watchlist_config_path,
        rules_path=rules_path,
        score_source_name=f"scores CSV ({scores_path})",
        watchlist_source_name=f"watchlist CSV ({watchlist_path})",
    )
    write_csv_rows(options.watchlist_output, watchlist_engine.OUTPUT_FIELDS, ranked)
    watchlist_engine.build_watchlist_report(ranked, options.watchlist_report_output)
    used_inputs = {
        "watchlist_input": watchlist_path,
        "scores_output": scores_path,
        "watchlist_config": watchlist_config_path,
        "portfolio_rules": rules_path,
        "fundamentals_source_mode": fundamentals_source_mode,
    }
    if fundamentals_path:
        used_inputs["fundamentals_master"] = fundamentals_path
    return stage_result(
        stage,
        SUCCESS,
        ["watchlist_input", "scores_output"],
        used_inputs=used_inputs,
        produced_outputs={"watchlist_ranked": options.watchlist_output, "watchlist_report": options.watchlist_report_output},
        notes=append_registry_default_note(
            options,
            f"Watchlist ranked from personal scores; fundamentals_source_mode={fundamentals_source_mode}.",
            "fundamentals_master",
        ),
    )


def run_monthly_stage(options: PersonalRunOptions) -> StageResult:
    stage = "monthly"
    fundamentals_path, fundamentals_source_mode, _fundamentals_required_input = resolve_fundamentals_source(options, stage, require_path_for_base=False)
    positions_path = require_existing_path(options.positions_output, "positions snapshot", stage)
    scores_path = require_existing_path(options.scores_output, "personal company scores", stage)
    watchlist_path = require_existing_path(options.watchlist_output, "ranked watchlist", stage)
    coverage_path = require_existing_path(options.coverage_output, "personal fundamentals coverage", stage)
    rules_path = monthly_ranking_engine.DEFAULT_RULES_PATH
    positions_rows = read_csv_rows(positions_path)
    score_rows = read_csv_rows(scores_path)
    watchlist_rows = read_csv_rows(watchlist_path)
    coverage_rows = monthly_ranking_engine.read_coverage_rows(coverage_path)
    ranking, rebalance = monthly_ranking_engine.build_monthly_ranking(
        positions_rows,
        score_rows,
        watchlist_rows,
        rules_path=rules_path,
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
    used_inputs = {
        "positions_output": positions_path,
        "scores_output": scores_path,
        "watchlist_output": watchlist_path,
        "coverage_output": coverage_path,
        "portfolio_rules": rules_path,
        "fundamentals_source_mode": fundamentals_source_mode,
    }
    if fundamentals_path:
        used_inputs["fundamentals_master"] = fundamentals_path
    return stage_result(
        stage,
        SUCCESS,
        ["positions_output", "scores_output", "watchlist_output", "coverage_output"],
        used_inputs=used_inputs,
        produced_outputs={
            "monthly_buy_ranking": options.monthly_ranking_output,
            "rebalance_proposals": options.rebalance_output,
            "monthly_decision_report": options.monthly_report_output,
        },
        notes=append_registry_default_note(
            options,
            f"Monthly ranking and decision report generated with fundamentals coverage guardrail; fundamentals_source_mode={fundamentals_source_mode}.",
            "fundamentals_master",
        ),
    )


def run_portfolio_review_stage(options: PersonalRunOptions) -> StageResult:
    stage = "portfolio_review"
    fundamentals_path, fundamentals_source_mode, _fundamentals_required_input = resolve_fundamentals_source(options, stage, require_path_for_base=False)
    positions_path = require_existing_path(options.positions_output, "positions snapshot", stage)
    scores_path = require_existing_path(options.scores_output, "personal company scores", stage)
    coverage_path = require_existing_path(options.coverage_output, "personal fundamentals coverage", stage)
    rules_path = DEFAULT_PORTFOLIO_REVIEW_RULES_PATH
    positions_rows = read_csv_rows(positions_path)
    scores_rows = read_csv_rows(scores_path)
    coverage_rows = read_snapshot_coverage_rows(coverage_path)
    build_portfolio_snapshot_report(
        positions_rows,
        options.portfolio_review_output,
        scores_rows=scores_rows,
        rules_path=rules_path,
        holdings_output=options.holdings_output,
        coverage_rows=coverage_rows,
    )
    used_inputs = {
        "positions_output": positions_path,
        "scores_output": scores_path,
        "coverage_output": coverage_path,
        "portfolio_rules": rules_path,
        "fundamentals_source_mode": fundamentals_source_mode,
    }
    if fundamentals_path:
        used_inputs["fundamentals_master"] = fundamentals_path
    return stage_result(
        stage,
        SUCCESS,
        ["positions_output", "scores_output", "coverage_output"],
        used_inputs=used_inputs,
        produced_outputs={"portfolio_review_report": options.portfolio_review_output, "holdings_action_table": options.holdings_output},
        notes=append_registry_default_note(
            options,
            f"Portfolio review report and holdings action table generated with coverage guardrail; fundamentals_source_mode={fundamentals_source_mode}.",
            "fundamentals_master",
        ),
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
        maybe_raise_required_registry_source(options, "benchmark_input", stage)
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
        notes=append_registry_default_note(
            options,
            "Benchmark archive/registry generated; normalized output remains a single explicit benchmark series.",
            "benchmark_input",
        ),
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
            "benchmark_config": options.benchmark_config,
        },
        produced_outputs={role: str(path) for role, path in outputs.items()},
        notes="Multi-benchmark comparison generated from archive and registry.",
    )


def run_cost_tax_stage(options: PersonalRunOptions) -> StageResult:
    stage = "cost_tax"
    if not options.ledger and not options.cost_tax_documents:
        maybe_raise_required_registry_source(options, "ledger", stage)
        raise ValueError("stage cost_tax requires --ledger and/or at least one --cost-tax-document.")
    cost_tax_config_path = DEFAULT_COST_TAX_CONFIG_PATH
    used = {"cost_tax_archive": options.cost_tax_archive, "cost_tax_config": cost_tax_config_path}
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
        config_path=cost_tax_config_path,
    )
    return stage_result(
        stage,
        SUCCESS,
        ["ledger_or_cost_tax_document"],
        used_inputs=used,
        produced_outputs={role: str(path) for role, path in outputs.items()},
        notes=append_registry_default_note(
            options,
            "Cost/tax archive and downstream artifacts generated from explicit ledger/document evidence.",
            "ledger",
        ),
    )


def run_dashboard_stage(options: PersonalRunOptions) -> StageResult:
    stage = "dashboard"
    positions_path = require_existing_path(options.positions_output, "positions snapshot", stage)
    dashboard_config_path = DEFAULT_DASHBOARD_CONFIG_PATH
    run_dashboard_engine(
        positions_path=positions_path,
        scores_path=options.scores_output,
        holdings_path=options.holdings_output,
        score_audit_path=options.score_audit_output,
        coverage_path=options.coverage_output,
        performance_kpis_path=options.performance_kpi_output,
        performance_summary_path=options.performance_summary_output,
        performance_comparison_path=options.performance_comparison_output,
        cost_tax_kpis_path=options.cost_tax_kpi_output,
        cost_tax_summary_path=options.cost_tax_summary_output,
        config_path=dashboard_config_path,
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
            "positions_output": positions_path,
            "scores_output": options.scores_output,
            "holdings_output": options.holdings_output,
            "score_audit_output": options.score_audit_output,
            "coverage_output": options.coverage_output,
            "performance_kpi_output": options.performance_kpi_output,
            "performance_summary_output": options.performance_summary_output,
            "performance_comparison_output": options.performance_comparison_output,
            "cost_tax_kpi_output": options.cost_tax_kpi_output,
            "cost_tax_summary_output": options.cost_tax_summary_output,
            "dashboard_config": dashboard_config_path,
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
    "data_sources_validate": run_data_sources_validate_stage,
    "import": run_import_stage,
    "fundamentals_seed": run_fundamentals_seed_stage,
    "fundamentals_profile": run_fundamentals_profile_stage,
    "fundamentals_snapshot_ingest": run_fundamentals_snapshot_ingest_stage,
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
    rows.sort(key=lambda row: (stage_sort_index(row["stage_name"]), row["artifact_role"], row["artifact_path"]))
    return rows


def stage_sort_index(stage_name: str) -> int:
    return STAGE_ORDER.index(stage_name) if stage_name in STAGE_ORDER else len(STAGE_ORDER)


def used_input_notes(stage: StageResult) -> str:
    source_mode = stage.used_inputs.get("fundamentals_source_mode", "")
    if stage.stage_name in FUNDAMENTALS_SOURCE_STAGES and source_mode:
        return f"fundamentals_source_mode={source_mode}; {stage.notes}"
    return stage.notes


def used_input_rows_from_stage_results(stage_results: list[StageResult]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for stage in stage_results:
        if not stage.used_inputs:
            continue
        notes = used_input_notes(stage)
        for role, path_value in sorted(stage.used_inputs.items()):
            if role in USED_INPUT_METADATA_ROLES or not path_value:
                continue
            rows.append(
                {
                    "stage_name": stage.stage_name,
                    "stage_status": stage.status,
                    "input_role": role,
                    "input_path": path_value,
                    "input_exists": str(path_exists(path_value)),
                    "notes": notes,
                }
            )
    rows.sort(key=lambda row: (stage_sort_index(row["stage_name"]), row["input_role"], row["input_path"]))
    return rows


def run_level_artifact_rows(options: PersonalRunOptions) -> list[dict[str, str]]:
    return [
        {
            "artifact_role": "used_inputs_index",
            "artifact_path": options.used_inputs_output,
            "stage_name": RUN_ARTIFACT_STAGE,
            "produced": str(output_exists(options.used_inputs_output)),
            "notes": "Flat stage-level used-input lineage index generated from StageResult.used_inputs.",
        }
    ]


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
            "used_inputs_output": options.used_inputs_output,
            "data_source_status_output": options.data_source_status_output,
            "data_source_resolved_output": options.data_source_resolved_output,
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
    lines.extend(
        [
            "",
            "## Used Inputs",
            "",
            f"- Input-Lineage-Index: `{manifest['outputs'].get('used_inputs_output', '')}`",
        ]
    )
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
    used_input_rows = used_input_rows_from_stage_results(stage_results)
    write_csv_rows(options.used_inputs_output, USED_INPUT_FIELDS, used_input_rows)
    artifact_rows = artifact_rows_from_stage_results(stage_results)
    artifact_rows.extend(run_level_artifact_rows(options))
    artifact_rows.sort(key=lambda row: (stage_sort_index(row["stage_name"]), row["artifact_role"], row["artifact_path"]))
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
    parser.add_argument("--data-sources-config", default=DEFAULT_PATHS["data_sources_config"], help="Personal run data source registry config.")
    parser.add_argument("--data-source-status-output", default=DEFAULT_PATHS["data_source_status_output"], help="Personal run data source status CSV output.")
    parser.add_argument("--data-source-resolved-output", default=DEFAULT_PATHS["data_source_resolved_output"], help="Personal run resolved personal data source registry CSV output.")
    parser.add_argument("--positions-raw-input", help="Raw personal positions input for import stage.")
    parser.add_argument("--cash-input", help="Optional cash input for document import stage.")
    parser.add_argument("--import-mode", choices=["sample", "real", "tr_pdf"], default="real", help="Import mode.")
    parser.add_argument("--source-name", default="personal_depot", help="Source label for imported rows and manifest.")
    parser.add_argument("--portfolio-date", help="Optional portfolio date override for import stage.")
    parser.add_argument("--positions-output", default=DEFAULT_PATHS["positions_output"], help="Personal positions snapshot path.")
    parser.add_argument("--fundamentals-master", default=DEFAULT_PATHS["fundamentals_master"], help="Personal fundamentals master path.")
    parser.add_argument("--overwrite-fundamentals-master", action="store_true", help="Allow fundamentals_seed to overwrite an existing master.")
    parser.add_argument("--use-profiled-master", action="store_true", help="Use the explicit profiled Personal-Fundamentals master for eligible fundamentals-dependent stages.")
    parser.add_argument("--use-applied-master", action="store_true", help="Use the explicit applied Personal-Fundamentals master for downstream fundamentals-dependent stages.")
    parser.add_argument("--metric-definitions", default=DEFAULT_METRIC_DEFINITIONS_PATH, help="Fundamentals KPI definitions config.")
    parser.add_argument("--scores-output", default=DEFAULT_PATHS["scores_output"], help="Personal company scores output.")
    parser.add_argument("--score-audit-output", default=DEFAULT_PATHS["score_audit_output"], help="Personal score audit output.")
    parser.add_argument("--coverage-output", default=DEFAULT_PATHS["coverage_output"], help="Personal fundamentals coverage output.")
    parser.add_argument("--fundamentals-enriched-output", default=DEFAULT_PATHS["fundamentals_enriched_output"], help="Personal enriched fundamentals output.")
    parser.add_argument("--research-priority-output", default=DEFAULT_PATHS["research_priority_output"], help="Personal fundamentals research priority output.")
    parser.add_argument("--fundamentals-coverage-report-output", help="Personal fundamentals coverage markdown report output.")
    parser.add_argument("--profile-review-input", default=DEFAULT_PATHS["profile_review_input"], help="Manual personal profile review input.")
    parser.add_argument("--profile-review-registry-output", default=DEFAULT_PATHS["profile_review_registry_output"], help="Personal profile review registry output.")
    parser.add_argument("--profile-review-backlog-output", default=DEFAULT_PATHS["profile_review_backlog_output"], help="Personal profile review backlog output.")
    parser.add_argument("--profiled-master-output", default=DEFAULT_PATHS["profiled_master_output"], help="Projected personal profiled master output.")
    parser.add_argument("--fundamentals-snapshot-input", default=DEFAULT_PATHS["fundamentals_snapshot_input"], help="Local external fundamentals snapshot CSV input.")
    parser.add_argument("--fundamentals-snapshot-normalized-output", default=DEFAULT_PATHS["fundamentals_snapshot_normalized_output"], help="Normalized matched local fundamentals snapshot output.")
    parser.add_argument("--fundamentals-snapshot-unmatched-output", default=DEFAULT_PATHS["fundamentals_snapshot_unmatched_output"], help="Unmatched local fundamentals snapshot output.")
    parser.add_argument("--fundamentals-snapshot-evidence-staging-output", default=DEFAULT_PATHS["fundamentals_snapshot_evidence_staging_output"], help="Evidence-staging output from local fundamentals snapshot ingest.")
    parser.add_argument("--fundamentals-snapshot-summary-output", default=DEFAULT_PATHS["fundamentals_snapshot_summary_output"], help="Local fundamentals snapshot ingest summary output.")
    parser.add_argument("--fundamentals-evidence-input", default=DEFAULT_PATHS["fundamentals_evidence_input"], help="Manual personal fundamentals evidence input.")
    parser.add_argument("--fundamentals-evidence-registry-output", default=DEFAULT_PATHS["fundamentals_evidence_registry_output"], help="Personal fundamentals evidence registry output.")
    parser.add_argument("--fundamentals-research-backlog-output", default=DEFAULT_PATHS["fundamentals_research_backlog_output"], help="Personal fundamentals research backlog output.")
    parser.add_argument("--fundamentals-proposed-updates-output", default=DEFAULT_PATHS["fundamentals_proposed_updates_output"], help="Manual Personal-Master proposed updates output from evidence.")
    parser.add_argument("--fundamentals-evidence-summary-output", default=DEFAULT_PATHS["fundamentals_evidence_summary_output"], help="Personal fundamentals evidence summary output.")
    parser.add_argument("--fundamentals-evidence-template-output", default=DEFAULT_PATHS["fundamentals_evidence_template_output"], help="Personal fundamentals evidence template output.")
    parser.add_argument("--fundamentals-evidence-report-output", help="Personal fundamentals evidence markdown report output.")
    parser.add_argument("--fundamentals-overlay-input", default=DEFAULT_PATHS["fundamentals_overlay_input"], help="Manual personal fundamentals overlay input.")
    parser.add_argument("--fundamentals-overlay-registry-output", default=DEFAULT_PATHS["fundamentals_overlay_registry_output"], help="Personal fundamentals overlay registry output.")
    parser.add_argument("--fundamentals-applied-master-output", default=DEFAULT_PATHS["fundamentals_applied_master_output"], help="Applied personal fundamentals master output.")
    parser.add_argument("--fundamentals-overlay-summary-output", default=DEFAULT_PATHS["fundamentals_overlay_summary_output"], help="Personal fundamentals overlay summary output.")
    parser.add_argument("--fundamentals-overlay-review-backlog-output", default=DEFAULT_PATHS["fundamentals_overlay_review_backlog_output"], help="Personal fundamentals overlay review backlog output.")
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
    parser.add_argument("--used-inputs-output", default=DEFAULT_PATHS["used_inputs_output"], help="Flat personal run used-inputs lineage CSV output.")
    parser.add_argument("--report-output", help="Personal run markdown report output.")
    return parser.parse_args()


def options_from_args(args: argparse.Namespace) -> PersonalRunOptions:
    return PersonalRunOptions(
        stages=args.stage,
        data_sources_config=args.data_sources_config,
        data_source_status_output=args.data_source_status_output,
        data_source_resolved_output=args.data_source_resolved_output,
        positions_raw_input=args.positions_raw_input,
        cash_input=args.cash_input,
        import_mode=args.import_mode,
        source_name=args.source_name,
        portfolio_date=args.portfolio_date,
        positions_output=args.positions_output,
        fundamentals_master=args.fundamentals_master,
        overwrite_fundamentals_master=args.overwrite_fundamentals_master,
        use_profiled_master=args.use_profiled_master,
        use_applied_master=args.use_applied_master,
        metric_definitions=args.metric_definitions,
        scores_output=args.scores_output,
        score_audit_output=args.score_audit_output,
        coverage_output=args.coverage_output,
        fundamentals_enriched_output=args.fundamentals_enriched_output,
        research_priority_output=args.research_priority_output,
        fundamentals_coverage_report_output=args.fundamentals_coverage_report_output,
        profile_review_input=args.profile_review_input,
        profile_review_registry_output=args.profile_review_registry_output,
        profile_review_backlog_output=args.profile_review_backlog_output,
        profiled_master_output=args.profiled_master_output,
        fundamentals_snapshot_input=args.fundamentals_snapshot_input,
        fundamentals_snapshot_normalized_output=args.fundamentals_snapshot_normalized_output,
        fundamentals_snapshot_unmatched_output=args.fundamentals_snapshot_unmatched_output,
        fundamentals_snapshot_evidence_staging_output=args.fundamentals_snapshot_evidence_staging_output,
        fundamentals_snapshot_summary_output=args.fundamentals_snapshot_summary_output,
        fundamentals_evidence_input=args.fundamentals_evidence_input,
        fundamentals_evidence_registry_output=args.fundamentals_evidence_registry_output,
        fundamentals_research_backlog_output=args.fundamentals_research_backlog_output,
        fundamentals_proposed_updates_output=args.fundamentals_proposed_updates_output,
        fundamentals_evidence_summary_output=args.fundamentals_evidence_summary_output,
        fundamentals_evidence_template_output=args.fundamentals_evidence_template_output,
        fundamentals_evidence_report_output=args.fundamentals_evidence_report_output,
        fundamentals_overlay_input=args.fundamentals_overlay_input,
        fundamentals_overlay_registry_output=args.fundamentals_overlay_registry_output,
        fundamentals_applied_master_output=args.fundamentals_applied_master_output,
        fundamentals_overlay_summary_output=args.fundamentals_overlay_summary_output,
        fundamentals_overlay_review_backlog_output=args.fundamentals_overlay_review_backlog_output,
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
        used_inputs_output=args.used_inputs_output,
        report_output=args.report_output,
    )


def main() -> None:
    args = parse_args()
    run_personal_run_engine(options_from_args(args))


if __name__ == "__main__":
    main()
