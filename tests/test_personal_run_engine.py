from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from src import monthly_ranking_engine, portfolio_review, scoring_engine, watchlist_engine
from src.benchmark_history_engine import BENCHMARK_ARCHIVE_FIELDS, BENCHMARK_REGISTRY_FIELDS
from src.common import read_csv_rows
from src.cost_tax_archive_engine import DEFAULT_CONFIG_PATH as DEFAULT_COST_TAX_CONFIG_PATH
from src.data_source_registry import RESOLVED_FIELDS, STATUS_FIELDS
from src.dashboard_engine import DEFAULT_CONFIG_PATH as DEFAULT_DASHBOARD_CONFIG_PATH
from src.fundamentals_evidence_apply import APPLY_SUMMARY_FIELDS
from src.fundamentals_evidence_engine import EVIDENCE_INPUT_FIELDS, PROPOSED_UPDATES_FIELDS
from src.fundamentals_master import DEFAULT_METRIC_DEFINITIONS_PATH, PERSONAL_MASTER_FIELDS
from src.fundamentals_overlay_engine import DEFAULT_SCHEMA_PATH as DEFAULT_OVERLAY_SCHEMA_PATH, OVERLAY_INPUT_FIELDS
from src.fundamentals_profile_engine import PROFILE_REVIEW_INPUT_FIELDS
from src.fundamentals_snapshot_ingestion import SNAPSHOT_INPUT_FIELDS, SUMMARY_FIELDS
from src.fundamentals_snapshot_review import SNAPSHOT_REVIEW_INPUT_FIELDS, SNAPSHOT_REVIEW_SUMMARY_FIELDS
from src.personal_run_engine import DEFAULT_PATHS, STAGE_ORDER, STAGE_RUNNERS, SUCCESS, USED_INPUT_FIELDS, PersonalRunOptions, options_from_args, parse_args, run_personal_run_engine, stage_result
from src.savings_plan_registry import REGISTRY_FIELDS


class PersonalRunEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_paths: list[Path] = []

    def tearDown(self) -> None:
        for path in reversed(self.temp_paths):
            if path.exists():
                path.unlink()

    def _path(self, name: str) -> Path:
        path = Path("tests") / name
        self.temp_paths.append(path)
        return path

    def _write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _write_raw_positions(self, path: Path, portfolio_date: str = "2026-04-10") -> None:
        self._write_csv(
            path,
            [
                "portfolio_date",
                "source_type",
                "ticker",
                "company_name",
                "asset_type",
                "sleeve",
                "sector",
                "country",
                "quantity",
                "price_eur",
                "market_value_eur",
                "cost_basis_eur",
                "currency",
                "notes",
            ],
            [
                {
                    "portfolio_date": portfolio_date,
                    "source_type": "manual_csv",
                    "ticker": "MSFT",
                    "company_name": "Microsoft",
                    "asset_type": "STOCK",
                    "sleeve": "SINGLE_STOCK",
                    "sector": "Technology",
                    "country": "USA",
                    "quantity": "2",
                    "price_eur": "500",
                    "market_value_eur": "1000",
                    "cost_basis_eur": "800",
                    "currency": "EUR",
                    "notes": "unit test holding",
                },
                {
                    "portfolio_date": portfolio_date,
                    "source_type": "manual_csv",
                    "ticker": "EUR-CASH",
                    "company_name": "Cash",
                    "asset_type": "CASH",
                    "sleeve": "CASH",
                    "sector": "Cash",
                    "country": "Eurozone",
                    "quantity": "100",
                    "price_eur": "1",
                    "market_value_eur": "100",
                    "cost_basis_eur": "100",
                    "currency": "EUR",
                    "notes": "unit test cash",
                },
            ],
        )

    def _write_watchlist(self, path: Path) -> None:
        self._write_csv(
            path,
            ["ticker", "company_name", "sector", "country", "asset_type", "sleeve", "mandate_fit", "thesis_summary", "main_risks"],
            [
                {
                    "ticker": "MSFT",
                    "company_name": "Microsoft",
                    "sector": "Technology",
                    "country": "USA",
                    "asset_type": "STOCK",
                    "sleeve": "SINGLE_STOCK",
                    "mandate_fit": "90",
                    "thesis_summary": "unit test watchlist candidate",
                    "main_risks": "unit test risk",
                }
            ],
        )

    def _write_personal_master_rows(self, path: Path, rows: list[dict[str, object]]) -> None:
        self._write_csv(path, PERSONAL_MASTER_FIELDS, rows)

    def _write_empty_evidence(self, path: Path) -> None:
        self._write_csv(path, EVIDENCE_INPUT_FIELDS, [])

    def _write_evidence_rows(self, path: Path, rows: list[dict[str, object]]) -> None:
        self._write_csv(path, EVIDENCE_INPUT_FIELDS, rows)

    def _write_proposed_updates_rows(self, path: Path, rows: list[dict[str, object]]) -> None:
        self._write_csv(path, PROPOSED_UPDATES_FIELDS, rows)

    def _write_empty_overlay(self, path: Path) -> None:
        self._write_csv(path, OVERLAY_INPUT_FIELDS, [])

    def _write_snapshot_rows(self, path: Path, rows: list[dict[str, object]]) -> None:
        self._write_csv(path, SNAPSHOT_INPUT_FIELDS, rows)

    def _write_profile_review_rows(self, path: Path, rows: list[dict[str, object]]) -> None:
        self._write_csv(path, PROFILE_REVIEW_INPUT_FIELDS, rows)

    def _write_snapshot_review_rows(self, path: Path, rows: list[dict[str, object]]) -> None:
        self._write_csv(path, SNAPSHOT_REVIEW_INPUT_FIELDS, rows)

    def _write_data_sources_config(self, path: Path, sources: dict[str, dict[str, object]]) -> None:
        path.write_text(json.dumps({"sources": sources}, indent=2) + "\n", encoding="utf-8")

    def _profile_review_row(
        self,
        *,
        ticker: str = "MSFT",
        isin: str = "US5949181045",
        company_name: str = "Microsoft",
        proposed_company_type_profile: str = "STANDARD",
        profile_reason: str = "manual profile review",
        review_status: str = "APPROVED",
        review_author: str = "qa_user",
        review_as_of_date: str = "2026-04-16",
        source_name: str = "manual_profile_review",
        source_reference: str = "internal note",
        notes: str = "unit profile review",
    ) -> dict[str, object]:
        row = {field: "" for field in PROFILE_REVIEW_INPUT_FIELDS}
        row.update(
            {
                "ticker": ticker,
                "isin": isin,
                "company_name": company_name,
                "proposed_company_type_profile": proposed_company_type_profile,
                "profile_reason": profile_reason,
                "review_status": review_status,
                "review_author": review_author,
                "review_as_of_date": review_as_of_date,
                "source_name": source_name,
                "source_reference": source_reference,
                "notes": notes,
            }
        )
        return row

    def _personal_master_row(
        self,
        *,
        ticker: str = "MSFT",
        isin: str = "",
        company_name: str = "Microsoft",
        asset_type: str = "STOCK",
    ) -> dict[str, object]:
        row = {field: "" for field in PERSONAL_MASTER_FIELDS}
        row.update(
            {
                "ticker": ticker,
                "isin": isin,
                "company_name": company_name,
                "currency": "USD",
                "sector": "Technology",
                "country": "USA",
                "asset_type": asset_type,
                "company_type_profile": "OTHER",
                "source_name": "unit_master_fixture",
                "source_as_of_date": "2026-04-10",
                "fiscal_year": "2025",
                "market_price_date": "2026-04-10",
                "calculation_version": "test",
                "data_quality_flag": "MISSING_DATA",
                "notes": "unit master fixture",
                "sleeve": "SINGLE_STOCK" if asset_type != "CASH" else "CASH",
                "current_price_eur": "100",
                "mandate_fit_score": "80",
            }
        )
        return row

    def _evidence_row(
        self,
        *,
        ticker: str = "MSFT",
        isin: str = "",
        company_name: str = "Microsoft",
        kpi_name: str = "roic",
        source_type: str = "ANNUAL_REPORT",
        source_name: str = "annual_report_2025",
        source_reference: str = "FY2025 annual report",
        source_as_of_date: str = "2026-03-31",
        fiscal_year: str = "2025",
        verification_status: str = "VERIFIED",
        data_quality_flag: str = "OK",
        reported_value: str = "25.0",
        notes: str = "unit evidence row",
    ) -> dict[str, object]:
        row = {field: "" for field in EVIDENCE_INPUT_FIELDS}
        row.update(
            {
                "ticker": ticker,
                "isin": isin,
                "company_name": company_name,
                "kpi_name": kpi_name,
                "source_type": source_type,
                "source_name": source_name,
                "source_reference": source_reference,
                "source_as_of_date": source_as_of_date,
                "fiscal_year": fiscal_year,
                "verification_status": verification_status,
                "data_quality_flag": data_quality_flag,
                "notes": notes,
                "source_section": "unit section",
                "source_page": "1",
                "reported_value": reported_value,
                "reported_unit": "percent",
                "currency": "USD",
            }
        )
        return row

    def _snapshot_row(
        self,
        *,
        ticker: str = "MSFT",
        isin: str = "",
        company_name: str = "Microsoft",
        source_name: str = "vendor_snapshot",
        source_as_of_date: str = "2026-04-15",
        fiscal_year: str = "2025",
        currency: str = "USD",
        source_reference: str = "vendor_export_2026q1",
        market_price_date: str = "2026-04-15",
        roic: str = "25",
        fcf_margin: str = "30",
        notes: str = "unit snapshot row",
    ) -> dict[str, object]:
        row = {field: "" for field in SNAPSHOT_INPUT_FIELDS}
        row.update(
            {
                "ticker": ticker,
                "isin": isin,
                "company_name": company_name,
                "source_name": source_name,
                "source_as_of_date": source_as_of_date,
                "fiscal_year": fiscal_year,
                "currency": currency,
                "source_reference": source_reference,
                "market_price_date": market_price_date,
                "roic": roic,
                "fcf_margin": fcf_margin,
                "notes": notes,
            }
        )
        return row

    def _snapshot_review_row(
        self,
        *,
        ticker: str = "MSFT",
        isin: str = "",
        company_name: str = "Microsoft",
        kpi_name: str = "roic",
        source_name: str = "vendor_snapshot",
        source_reference: str = "vendor_export_2026q1",
        source_as_of_date: str = "2026-04-15",
        fiscal_year: str = "2025",
        review_decision: str = "APPROVE",
        review_reason: str = "manual snapshot review",
        review_author: str = "qa_user",
        review_as_of_date: str = "2026-04-17",
        notes: str = "unit snapshot review",
    ) -> dict[str, object]:
        row = {field: "" for field in SNAPSHOT_REVIEW_INPUT_FIELDS}
        row.update(
            {
                "ticker": ticker,
                "isin": isin,
                "company_name": company_name,
                "kpi_name": kpi_name,
                "source_name": source_name,
                "source_reference": source_reference,
                "source_as_of_date": source_as_of_date,
                "fiscal_year": fiscal_year,
                "review_decision": review_decision,
                "review_reason": review_reason,
                "review_author": review_author,
                "review_as_of_date": review_as_of_date,
                "notes": notes,
            }
        )
        return row

    def _proposed_update_row(
        self,
        *,
        ticker: str = "MSFT",
        isin: str = "",
        company_name: str = "Microsoft",
        kpi_name: str = "roic",
        reported_value: str = "25.0",
        source_type: str = "ANNUAL_REPORT",
        source_name: str = "annual_report_2025",
        source_reference: str = "FY2025 annual report",
        source_as_of_date: str = "2026-03-31",
        fiscal_year: str = "2025",
        verification_status: str = "VERIFIED",
        data_quality_flag: str = "OK",
        notes: str = "unit proposed update",
    ) -> dict[str, object]:
        row = {field: "" for field in PROPOSED_UPDATES_FIELDS}
        row.update(
            {
                "ticker": ticker,
                "isin": isin,
                "company_name": company_name,
                "company_type_profile": "OTHER",
                "kpi_name": kpi_name,
                "reported_value": reported_value,
                "reported_unit": "percent",
                "currency": "USD",
                "source_type": source_type,
                "source_name": source_name,
                "source_reference": source_reference,
                "source_as_of_date": source_as_of_date,
                "fiscal_year": fiscal_year,
                "verification_status": verification_status,
                "data_quality_flag": data_quality_flag,
                "proposal_reason": "validated evidence for apply test",
                "notes": notes,
            }
        )
        return row

    def _archive_row(self, symbol: str, point_date: str, value: str, name: str | None = None) -> dict[str, str]:
        row = {field: "" for field in BENCHMARK_ARCHIVE_FIELDS}
        row.update(
            {
                "date": point_date,
                "benchmark_name": name or f"{symbol} Benchmark",
                "benchmark_symbol": symbol,
                "currency": "EUR",
                "close": value,
                "adjusted_close": value,
                "total_return_index": value,
                "benchmark_return_basis_used": "total_return_index",
                "benchmark_reference_value": value,
                "data_quality_flag": "OK",
                "notes": "unit benchmark archive row",
                "source_name": "unit_source",
            }
        )
        return row

    def _registry_row(self, symbol: str, first_date: str, last_date: str, points_count: str, name: str | None = None) -> dict[str, str]:
        return {
            "benchmark_name": name or f"{symbol} Benchmark",
            "benchmark_symbol": symbol,
            "currency": "EUR",
            "first_date": first_date,
            "last_date": last_date,
            "points_count": points_count,
            "benchmark_return_basis_used": "total_return_index",
            "source_name": "unit_source",
            "data_quality_flag": "OK",
            "notes": "",
        }

    def _write_benchmark_archive_and_registry(self, archive_path: Path, registry_path: Path) -> None:
        self._write_csv(
            archive_path,
            BENCHMARK_ARCHIVE_FIELDS,
            [
                self._archive_row("WORLD", "2026-01-31", "100"),
                self._archive_row("EUROPE", "2026-01-31", "100"),
                self._archive_row("EUROPE", "2026-04-10", "105"),
                self._archive_row("WORLD", "2026-04-10", "110"),
            ],
        )
        self._write_csv(
            registry_path,
            BENCHMARK_REGISTRY_FIELDS,
            [
                self._registry_row("WORLD", "2026-01-31", "2026-04-10", "2"),
                self._registry_row("EUROPE", "2026-01-31", "2026-04-10", "2"),
            ],
        )

    def _base_options(self, prefix: str, stages: list[str]) -> PersonalRunOptions:
        data_sources_config = self._path(f"_tmp_{prefix}_data_sources.yaml")
        self._write_data_sources_config(data_sources_config, {})
        return PersonalRunOptions(
            stages=stages,
            data_sources_config=str(data_sources_config),
            data_source_status_output=str(self._path(f"_tmp_{prefix}_data_source_status.csv")),
            data_source_resolved_output=str(self._path(f"_tmp_{prefix}_data_source_resolved.csv")),
            positions_output=str(self._path(f"_tmp_{prefix}_positions.csv")),
            savings_plan_input=str(self._path(f"_tmp_{prefix}_savings_plan_registry.csv")),
            savings_plan_summary_output=str(self._path(f"_tmp_{prefix}_savings_plan_summary.csv")),
            savings_plan_report_output=str(self._path(f"_tmp_{prefix}_savings_plan_report.md")),
            fundamentals_master=str(self._path(f"_tmp_{prefix}_personal_master.csv")),
            scores_output=str(self._path(f"_tmp_{prefix}_scores.csv")),
            score_audit_output=str(self._path(f"_tmp_{prefix}_score_audit.csv")),
            coverage_output=str(self._path(f"_tmp_{prefix}_coverage.csv")),
            fundamentals_enriched_output=str(self._path(f"_tmp_{prefix}_enriched.csv")),
            research_priority_output=str(self._path(f"_tmp_{prefix}_research_priority.csv")),
            fundamentals_coverage_report_output=str(self._path(f"_tmp_{prefix}_coverage_report.md")),
            profile_review_input=str(self._path(f"_tmp_{prefix}_profile_review.csv")),
            profile_review_registry_output=str(self._path(f"_tmp_{prefix}_profile_registry.csv")),
            profile_review_backlog_output=str(self._path(f"_tmp_{prefix}_profile_backlog.csv")),
            profiled_master_output=str(self._path(f"_tmp_{prefix}_profiled_master.csv")),
            fundamentals_snapshot_input=str(self._path(f"_tmp_{prefix}_fundamentals_snapshot.csv")),
            fundamentals_snapshot_normalized_output=str(self._path(f"_tmp_{prefix}_fundamentals_snapshot_normalized.csv")),
            fundamentals_snapshot_unmatched_output=str(self._path(f"_tmp_{prefix}_fundamentals_snapshot_unmatched.csv")),
            fundamentals_snapshot_evidence_staging_output=str(self._path(f"_tmp_{prefix}_fundamentals_snapshot_evidence_staging.csv")),
            fundamentals_snapshot_summary_output=str(self._path(f"_tmp_{prefix}_fundamentals_snapshot_summary.csv")),
            fundamentals_snapshot_review_input=str(self._path(f"_tmp_{prefix}_fundamentals_snapshot_review.csv")),
            fundamentals_snapshot_review_registry_output=str(self._path(f"_tmp_{prefix}_fundamentals_snapshot_review_registry.csv")),
            fundamentals_snapshot_evidence_promoted_input=str(self._path(f"_tmp_{prefix}_fundamentals_snapshot_evidence_promoted.csv")),
            fundamentals_snapshot_evidence_promoted_output=str(self._path(f"_tmp_{prefix}_fundamentals_snapshot_evidence_promoted.csv")),
            fundamentals_snapshot_review_backlog_output=str(self._path(f"_tmp_{prefix}_fundamentals_snapshot_review_backlog.csv")),
            fundamentals_snapshot_review_summary_output=str(self._path(f"_tmp_{prefix}_fundamentals_snapshot_review_summary.csv")),
            fundamentals_evidence_input=str(self._path(f"_tmp_{prefix}_evidence_input.csv")),
            fundamentals_evidence_composed_output=str(self._path(f"_tmp_{prefix}_evidence_composed.csv")),
            fundamentals_evidence_compose_conflicts_output=str(self._path(f"_tmp_{prefix}_evidence_compose_conflicts.csv")),
            fundamentals_evidence_compose_summary_output=str(self._path(f"_tmp_{prefix}_evidence_compose_summary.csv")),
            fundamentals_evidence_registry_output=str(self._path(f"_tmp_{prefix}_evidence_registry.csv")),
            fundamentals_research_backlog_output=str(self._path(f"_tmp_{prefix}_research_backlog.csv")),
            fundamentals_proposed_updates_output=str(self._path(f"_tmp_{prefix}_proposed_updates.csv")),
            fundamentals_evidence_summary_output=str(self._path(f"_tmp_{prefix}_evidence_summary.csv")),
            fundamentals_evidence_template_output=str(self._path(f"_tmp_{prefix}_evidence_template.csv")),
            fundamentals_evidence_apply_registry_output=str(self._path(f"_tmp_{prefix}_evidence_apply_registry.csv")),
            fundamentals_evidence_applied_master_output=str(self._path(f"_tmp_{prefix}_evidence_applied_master.csv")),
            fundamentals_evidence_apply_summary_output=str(self._path(f"_tmp_{prefix}_evidence_apply_summary.csv")),
            fundamentals_evidence_report_output=str(self._path(f"_tmp_{prefix}_evidence_report.md")),
            fundamentals_overlay_input=str(self._path(f"_tmp_{prefix}_overlay_input.csv")),
            fundamentals_overlay_registry_output=str(self._path(f"_tmp_{prefix}_overlay_registry.csv")),
            fundamentals_applied_master_output=str(self._path(f"_tmp_{prefix}_applied_master.csv")),
            fundamentals_overlay_summary_output=str(self._path(f"_tmp_{prefix}_overlay_summary.csv")),
            fundamentals_overlay_review_backlog_output=str(self._path(f"_tmp_{prefix}_overlay_review_backlog.csv")),
            fundamentals_overlay_template_output=str(self._path(f"_tmp_{prefix}_overlay_template.csv")),
            fundamentals_overlay_report_output=str(self._path(f"_tmp_{prefix}_overlay_report.md")),
            watchlist_output=str(self._path(f"_tmp_{prefix}_watchlist_ranked.csv")),
            watchlist_report_output=str(self._path(f"_tmp_{prefix}_watchlist_report.md")),
            monthly_ranking_output=str(self._path(f"_tmp_{prefix}_monthly_ranking.csv")),
            rebalance_output=str(self._path(f"_tmp_{prefix}_rebalance.csv")),
            monthly_report_output=str(self._path(f"_tmp_{prefix}_monthly_report.md")),
            portfolio_review_output=str(self._path(f"_tmp_{prefix}_portfolio_review.md")),
            holdings_output=str(self._path(f"_tmp_{prefix}_holdings.csv")),
            portfolio_health_thresholds_input=DEFAULT_PATHS["portfolio_health_thresholds_input"],
            cash_refill_csv_output=str(self._path(f"_tmp_{prefix}_cash_refill_review.csv")),
            cash_refill_report_output=str(self._path(f"_tmp_{prefix}_cash_refill_review.md")),
            rebalance_review_csv_output=str(self._path(f"_tmp_{prefix}_rebalance_review.csv")),
            rebalance_review_report_output=str(self._path(f"_tmp_{prefix}_rebalance_review.md")),
            personal_input_closure_report=str(self._path(f"_tmp_{prefix}_personal_input_closure_report.csv")),
            personal_decision_state_capture=str(self._path(f"_tmp_{prefix}_personal_decision_state_capture.csv")),
            decision_quality_csv_output=str(self._path(f"_tmp_{prefix}_decision_quality_state.csv")),
            decision_quality_json_output=str(self._path(f"_tmp_{prefix}_decision_quality_state.json")),
            decision_quality_report_output=str(self._path(f"_tmp_{prefix}_decision_quality_report.md")),
            portfolio_archive=str(self._path(f"_tmp_{prefix}_portfolio_archive.csv")),
            portfolio_timeseries_output=str(self._path(f"_tmp_{prefix}_portfolio_timeseries.csv")),
            portfolio_history_summary_output=str(self._path(f"_tmp_{prefix}_portfolio_history_summary.csv")),
            portfolio_history_report_output=str(self._path(f"_tmp_{prefix}_portfolio_history_report.md")),
            benchmark_archive=str(self._path(f"_tmp_{prefix}_benchmark_archive.csv")),
            benchmark_registry_output=str(self._path(f"_tmp_{prefix}_benchmark_registry.csv")),
            benchmark_normalized_output=str(self._path(f"_tmp_{prefix}_benchmark_normalized.csv")),
            benchmark_archive_summary_output=str(self._path(f"_tmp_{prefix}_benchmark_archive_summary.csv")),
            benchmark_history_report_output=str(self._path(f"_tmp_{prefix}_benchmark_history_report.md")),
            performance_summary_output=str(self._path(f"_tmp_{prefix}_performance_summary.csv")),
            performance_comparison_output=str(self._path(f"_tmp_{prefix}_performance_comparison.csv")),
            performance_kpi_output=str(self._path(f"_tmp_{prefix}_performance_kpis.csv")),
            performance_report_output=str(self._path(f"_tmp_{prefix}_performance_report.md")),
            multi_benchmark_comparison_output=str(self._path(f"_tmp_{prefix}_multi_comparison.csv")),
            multi_benchmark_summary_output=str(self._path(f"_tmp_{prefix}_multi_summary.csv")),
            multi_benchmark_kpi_output=str(self._path(f"_tmp_{prefix}_multi_kpis.csv")),
            multi_benchmark_report_output=str(self._path(f"_tmp_{prefix}_multi_report.md")),
            cost_tax_archive=str(self._path(f"_tmp_{prefix}_cost_tax_archive.csv")),
            cost_tax_normalized_ledger_output=str(self._path(f"_tmp_{prefix}_cost_tax_normalized.csv")),
            cost_tax_summary_output=str(self._path(f"_tmp_{prefix}_cost_tax_summary.csv")),
            cost_tax_kpi_output=str(self._path(f"_tmp_{prefix}_cost_tax_kpis.csv")),
            cost_tax_archive_summary_output=str(self._path(f"_tmp_{prefix}_cost_tax_archive_summary.csv")),
            cost_tax_report_output=str(self._path(f"_tmp_{prefix}_cost_tax_report.md")),
            dashboard_kpi_output=str(self._path(f"_tmp_{prefix}_dashboard_kpis.csv")),
            dashboard_sections_output=str(self._path(f"_tmp_{prefix}_dashboard_sections.csv")),
            dashboard_summary_output=str(self._path(f"_tmp_{prefix}_dashboard_summary.csv")),
            dashboard_universe_output=str(self._path(f"_tmp_{prefix}_dashboard_universe.csv")),
            dashboard_report_output=str(self._path(f"_tmp_{prefix}_dashboard_report.md")),
            manifest_output=str(self._path(f"_tmp_{prefix}_manifest.json")),
            artifacts_output=str(self._path(f"_tmp_{prefix}_artifacts.csv")),
            used_inputs_output=str(self._path(f"_tmp_{prefix}_used_inputs.csv")),
            report_output=str(self._path(f"_tmp_{prefix}_run_report.md")),
        )

    def _core_options(self, prefix: str, stages: list[str]) -> PersonalRunOptions:
        raw_positions = self._path(f"_tmp_{prefix}_raw_positions.csv")
        watchlist = self._path(f"_tmp_{prefix}_watchlist.csv")
        self._write_raw_positions(raw_positions)
        self._write_watchlist(watchlist)
        options = self._base_options(prefix, stages)
        options.positions_raw_input = str(raw_positions)
        options.watchlist_input = str(watchlist)
        options.import_mode = "real"
        options.source_name = f"{prefix}_source"
        return options

    def _write_decision_quality_inputs(self, options: PersonalRunOptions) -> None:
        self._write_csv(
            Path(options.personal_input_closure_report),
            [
                "input_area",
                "artifact_path",
                "status",
                "blocker_severity",
                "missing_or_review_items_count",
                "sample_or_synthetic_flag",
                "reason_codes",
                "required_operator_action",
                "downstream_impact",
                "next_recommended_step",
            ],
            [
                {
                    "input_area": area,
                    "artifact_path": f"tests/{area.lower()}_input.csv",
                    "status": "READY",
                    "blocker_severity": "NONE",
                    "missing_or_review_items_count": "0",
                    "sample_or_synthetic_flag": "false",
                    "reason_codes": "",
                    "required_operator_action": "",
                    "downstream_impact": "",
                    "next_recommended_step": "",
                }
                for area in ["WATCHLIST", "VALUATION", "DIVIDEND_FCF", "KPI_PROVENANCE"]
            ],
        )

    def _write_minimal_decision_quality_review_inputs(self, options: PersonalRunOptions) -> None:
        self._write_decision_quality_inputs(options)
        self._write_csv(
            Path(options.cash_refill_csv_output),
            ["review_date", "status", "trigger", "data_quality_flag"],
            [{"review_date": "2026-05-19", "status": "CASH_REFILL_NOT_REQUIRED", "trigger": "NONE", "data_quality_flag": "OK"}],
        )
        self._write_csv(
            Path(options.rebalance_review_csv_output),
            ["review_date", "bucket", "band_status", "recommended_action", "data_quality_flag"],
            [{"review_date": "2026-05-19", "bucket": "CASH", "band_status": "WITHIN_BAND", "recommended_action": "HOLD", "data_quality_flag": "OK"}],
        )
        self._write_csv(
            Path(options.personal_decision_state_capture),
            [
                "decision_id",
                "decision_date",
                "decision_scope",
                "proposed_action",
                "human_decision",
                "decision_status",
                "reasoning_3_sentences",
                "dominant_uncertainty",
                "benchmark_alternative",
            ],
            [
                {
                    "decision_id": "DECISION_20260519_0001",
                    "decision_date": "2026-05-19",
                    "decision_scope": "MONTHLY_REVIEW",
                    "proposed_action": "NO_ACTION",
                    "human_decision": "NO_ACTION",
                    "decision_status": "CLOSED",
                    "reasoning_3_sentences": "Reviewed. No action. Continue.",
                    "dominant_uncertainty": "UNKNOWN",
                    "benchmark_alternative": "CASH",
                }
            ],
        )

    def _used_inputs_for_stage(self, rows: list[dict[str, str]], stage_name: str) -> dict[str, dict[str, str]]:
        return {row["input_role"]: row for row in rows if row["stage_name"] == stage_name}

    def test_savings_plan_stage_order_runner_and_existing_order(self) -> None:
        self.assertEqual(STAGE_ORDER[STAGE_ORDER.index("import") + 1], "savings_plan")
        self.assertEqual(STAGE_ORDER[STAGE_ORDER.index("savings_plan") + 1], "fundamentals_seed")
        self.assertIn("savings_plan", STAGE_RUNNERS)
        self.assertEqual(
            [stage for stage in STAGE_ORDER if stage != "savings_plan"],
            [
                "data_sources_validate",
                "import",
                "fundamentals_seed",
                "fundamentals_profile",
                "fundamentals_snapshot_ingest",
                "fundamentals_snapshot_review",
                "fundamentals_evidence_compose",
                "fundamentals_evidence",
                "fundamentals_evidence_apply",
                "fundamentals_overlay",
                "scoring",
                "coverage",
                "watchlist",
                "portfolio_review",
                "cash_refill_review",
                "rebalance_review",
                "monthly",
                "decision_quality",
                "history",
                "benchmark_archive",
                "performance",
                "multi_benchmark",
                "cost_tax",
                "dashboard",
            ],
        )

    def test_targeted_savings_plan_stage_succeeds_with_header_only_input(self) -> None:
        options = self._base_options("savings_plan_stage", ["savings_plan"])
        self._write_csv(Path(options.savings_plan_input), REGISTRY_FIELDS, [])

        manifest = run_personal_run_engine(options)

        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(manifest["executed_stage_order"], ["savings_plan"])
        savings_plan_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "savings_plan")
        self.assertEqual(savings_plan_result["status"], "SUCCESS")
        self.assertTrue(Path(options.savings_plan_summary_output).exists())
        self.assertTrue(Path(options.savings_plan_report_output).exists())
        artifact_rows = read_csv_rows(options.artifacts_output)
        produced_roles = {row["artifact_role"] for row in artifact_rows if row["stage_name"] == "savings_plan" and row["produced"] == "True"}
        self.assertEqual(produced_roles, {"savings_plan_report", "savings_plan_summary"})

    def test_portfolio_health_stages_order_and_runners(self) -> None:
        self.assertEqual(STAGE_ORDER[STAGE_ORDER.index("portfolio_review") + 1], "cash_refill_review")
        self.assertEqual(STAGE_ORDER[STAGE_ORDER.index("cash_refill_review") + 1], "rebalance_review")
        self.assertEqual(STAGE_ORDER[STAGE_ORDER.index("rebalance_review") + 1], "monthly")
        self.assertEqual(STAGE_ORDER[STAGE_ORDER.index("monthly") + 1], "decision_quality")
        self.assertIn("cash_refill_review", STAGE_RUNNERS)
        self.assertIn("rebalance_review", STAGE_RUNNERS)
        self.assertIn("decision_quality", STAGE_RUNNERS)

    def test_targeted_cash_refill_review_stage_writes_outputs(self) -> None:
        options = self._base_options("cash_refill_stage", ["cash_refill_review"])
        self._write_csv(Path(options.positions_output), ["ticker", "asset_type", "sleeve", "market_value_eur"], [])

        manifest = run_personal_run_engine(options)

        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(manifest["executed_stage_order"], ["cash_refill_review"])
        result = next(row for row in manifest["stage_results"] if row["stage_name"] == "cash_refill_review")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertTrue(Path(options.cash_refill_csv_output).exists())
        self.assertTrue(Path(options.cash_refill_report_output).exists())
        artifact_rows = read_csv_rows(options.artifacts_output)
        produced_roles = {row["artifact_role"] for row in artifact_rows if row["stage_name"] == "cash_refill_review" and row["produced"] == "True"}
        self.assertEqual(produced_roles, {"cash_refill_review", "cash_refill_review_report"})

    def test_targeted_rebalance_review_stage_writes_outputs(self) -> None:
        options = self._base_options("rebalance_review_stage", ["rebalance_review"])
        self._write_csv(Path(options.positions_output), ["ticker", "asset_type", "sleeve", "market_value_eur"], [])

        manifest = run_personal_run_engine(options)

        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(manifest["executed_stage_order"], ["rebalance_review"])
        result = next(row for row in manifest["stage_results"] if row["stage_name"] == "rebalance_review")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertTrue(Path(options.rebalance_review_csv_output).exists())
        self.assertTrue(Path(options.rebalance_review_report_output).exists())
        artifact_rows = read_csv_rows(options.artifacts_output)
        produced_roles = {row["artifact_role"] for row in artifact_rows if row["stage_name"] == "rebalance_review" and row["produced"] == "True"}
        self.assertEqual(produced_roles, {"rebalance_review", "rebalance_review_report"})

    def test_core_personal_run_writes_manifest_artifacts_and_reports(self) -> None:
        options = self._core_options(
            "core",
            ["import", "fundamentals_seed", "scoring", "coverage", "watchlist", "monthly", "portfolio_review"],
        )

        manifest = run_personal_run_engine(options)

        manifest_on_disk = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        artifact_rows = read_csv_rows(options.artifacts_output)
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(manifest_on_disk["run_status"], "SUCCESS")
        self.assertEqual(
            manifest_on_disk["executed_stage_order"],
            ["import", "fundamentals_seed", "scoring", "coverage", "watchlist", "portfolio_review", "monthly"],
        )
        self.assertEqual({row["stage_name"] for row in artifact_rows if row["produced"] == "True"}, {*set(manifest_on_disk["executed_stage_order"]), "personal_run"})
        self.assertTrue(Path(options.holdings_output).exists())
        self.assertTrue(Path(options.research_priority_output).exists())
        self.assertTrue(Path(options.used_inputs_output).exists())
        self.assertIn("Personal Run Report", Path(options.report_output).read_text(encoding="utf-8"))
        self.assertIn("Input-Lineage-Index", Path(options.report_output).read_text(encoding="utf-8"))
        statuses = {row["stage_name"]: row["status"] for row in manifest_on_disk["stage_results"]}
        self.assertEqual(statuses["cost_tax"], "NOT_REQUESTED")
        self.assertEqual(statuses["scoring"], "SUCCESS")
        scoring_result = next(row for row in manifest_on_disk["stage_results"] if row["stage_name"] == "scoring")
        self.assertEqual(scoring_result["used_inputs"]["fundamentals_source_mode"], "BASE")
        used_input_rows = read_csv_rows(options.used_inputs_output)
        self.assertEqual(set(used_input_rows[0]), set(USED_INPUT_FIELDS))
        scoring_master_inputs = [row for row in used_input_rows if row["stage_name"] == "scoring" and row["input_role"] == "fundamentals_master"]
        self.assertEqual(scoring_master_inputs[0]["input_path"], options.fundamentals_master)
        self.assertEqual(scoring_master_inputs[0]["input_exists"], "True")
        self.assertIn("fundamentals_source_mode=BASE", scoring_master_inputs[0]["notes"])
        self.assertIn(
            "used_inputs_index",
            {row["artifact_role"] for row in artifact_rows if row["stage_name"] == "personal_run" and row["produced"] == "True"},
        )

    def test_fundamentals_evidence_stage_updates_manifest_and_artifacts(self) -> None:
        options = self._core_options("evidence_stage", ["import", "fundamentals_seed", "fundamentals_evidence"])
        self._write_empty_evidence(Path(options.fundamentals_evidence_input))

        manifest = run_personal_run_engine(options)

        artifact_rows = read_csv_rows(options.artifacts_output)
        statuses = {row["stage_name"]: row["status"] for row in manifest["stage_results"]}
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(statuses["fundamentals_evidence"], "SUCCESS")
        self.assertTrue(Path(options.fundamentals_evidence_registry_output).exists())
        self.assertTrue(Path(options.fundamentals_research_backlog_output).exists())
        self.assertTrue(Path(options.fundamentals_proposed_updates_output).exists())
        self.assertIn("fundamentals_evidence", {row["stage_name"] for row in artifact_rows if row["produced"] == "True"})
        evidence_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "fundamentals_evidence")
        self.assertEqual(evidence_inputs["metric_definitions"]["input_path"], DEFAULT_METRIC_DEFINITIONS_PATH)
        self.assertEqual(evidence_inputs["metric_definitions"]["input_exists"], "True")

    def test_fundamentals_evidence_apply_stage_writes_registry_summary_and_evidence_applied_master(self) -> None:
        options = self._core_options(
            "evidence_apply_stage",
            ["import", "fundamentals_seed", "fundamentals_evidence", "fundamentals_evidence_apply"],
        )
        self._write_evidence_rows(Path(options.fundamentals_evidence_input), [self._evidence_row(kpi_name="roic", reported_value="25.0")])

        manifest = run_personal_run_engine(options)

        registry_rows = read_csv_rows(options.fundamentals_evidence_apply_registry_output)
        summary_rows = read_csv_rows(options.fundamentals_evidence_apply_summary_output)
        applied_master_rows = read_csv_rows(options.fundamentals_evidence_applied_master_output)
        apply_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "fundamentals_evidence_apply")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(registry_rows[0]["apply_status"], "APPLIED")
        self.assertEqual(registry_rows[0]["target_field"], "roic")
        self.assertEqual(set(summary_rows[0]), set(APPLY_SUMMARY_FIELDS))
        self.assertEqual(summary_rows[0]["applied_rows_total"], "1")
        self.assertEqual(summary_rows[0]["applied_fields_total"], "1")
        self.assertEqual(applied_master_rows[0]["roic"], "25.0")
        self.assertEqual(apply_inputs["fundamentals_master"]["input_path"], options.fundamentals_master)
        self.assertEqual(
            apply_inputs["fundamentals_proposed_updates_output"]["input_path"],
            options.fundamentals_proposed_updates_output,
        )

    def test_use_evidence_applied_master_switch_routes_scoring_and_coverage_explicitly(self) -> None:
        options = self._core_options(
            "evidence_applied_switch",
            ["import", "fundamentals_seed", "fundamentals_evidence", "fundamentals_evidence_apply", "scoring", "coverage"],
        )
        options.use_evidence_applied_master = True
        self._write_evidence_rows(Path(options.fundamentals_evidence_input), [self._evidence_row(kpi_name="roic", reported_value="25.0")])

        manifest = run_personal_run_engine(options)

        applied_master_rows = read_csv_rows(options.fundamentals_evidence_applied_master_output)
        used_input_rows = read_csv_rows(options.used_inputs_output)
        scoring_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "scoring")
        coverage_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "coverage")
        scoring_inputs = self._used_inputs_for_stage(used_input_rows, "scoring")
        coverage_inputs = self._used_inputs_for_stage(used_input_rows, "coverage")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertTrue(manifest["inputs"]["use_evidence_applied_master"])
        self.assertEqual(applied_master_rows[0]["roic"], "25.0")
        self.assertEqual(scoring_result["used_inputs"]["fundamentals_source_mode"], "EVIDENCE_APPLIED")
        self.assertEqual(coverage_result["used_inputs"]["fundamentals_source_mode"], "EVIDENCE_APPLIED")
        self.assertEqual(scoring_result["used_inputs"]["fundamentals_master"], options.fundamentals_evidence_applied_master_output)
        self.assertEqual(coverage_result["used_inputs"]["fundamentals_master"], options.fundamentals_evidence_applied_master_output)
        self.assertIn("fundamentals_source_mode=EVIDENCE_APPLIED", scoring_inputs["fundamentals_master"]["notes"])
        self.assertIn("fundamentals_source_mode=EVIDENCE_APPLIED", coverage_inputs["fundamentals_master"]["notes"])

    def test_fundamentals_overlay_stage_updates_manifest_and_artifacts(self) -> None:
        options = self._core_options("overlay_stage", ["import", "fundamentals_seed", "fundamentals_overlay"])
        self._write_empty_overlay(Path(options.fundamentals_overlay_input))

        manifest = run_personal_run_engine(options)

        artifact_rows = read_csv_rows(options.artifacts_output)
        statuses = {row["stage_name"]: row["status"] for row in manifest["stage_results"]}
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(statuses["fundamentals_overlay"], "SUCCESS")
        self.assertTrue(Path(options.fundamentals_overlay_registry_output).exists())
        self.assertTrue(Path(options.fundamentals_applied_master_output).exists())
        self.assertTrue(Path(options.fundamentals_overlay_review_backlog_output).exists())
        self.assertIn("fundamentals_overlay", {row["stage_name"] for row in artifact_rows if row["produced"] == "True"})
        overlay_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "fundamentals_overlay")
        self.assertEqual(overlay_inputs["fundamentals_schema"]["input_path"], DEFAULT_OVERLAY_SCHEMA_PATH)
        self.assertEqual(overlay_inputs["fundamentals_schema"]["input_exists"], "True")

    def test_fundamentals_profile_stage_writes_registry_backlog_and_profiled_master(self) -> None:
        options = self._core_options("profile_stage", ["import", "fundamentals_seed", "fundamentals_profile"])
        self._write_profile_review_rows(
            Path(options.profile_review_input),
            [self._profile_review_row(isin="", proposed_company_type_profile="STANDARD", profile_reason="operating company")],
        )

        manifest = run_personal_run_engine(options)

        artifact_rows = read_csv_rows(options.artifacts_output)
        statuses = {row["stage_name"]: row["status"] for row in manifest["stage_results"]}
        registry_rows = read_csv_rows(options.profile_review_registry_output)
        profiled_rows = read_csv_rows(options.profiled_master_output)
        profile_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "fundamentals_profile")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(statuses["fundamentals_profile"], "SUCCESS")
        self.assertTrue(Path(options.profile_review_registry_output).exists())
        self.assertTrue(Path(options.profile_review_backlog_output).exists())
        self.assertTrue(Path(options.profiled_master_output).exists())
        self.assertIn("fundamentals_profile", {row["stage_name"] for row in artifact_rows if row["produced"] == "True"})
        self.assertEqual(registry_rows[0]["projection_applied"], "True")
        self.assertEqual(profiled_rows[0]["company_type_profile"], "STANDARD")
        self.assertEqual(profile_inputs["fundamentals_master"]["input_path"], options.fundamentals_master)
        self.assertEqual(profile_inputs["profile_review_input"]["input_path"], options.profile_review_input)
        self.assertEqual(profile_inputs["profile_review_input"]["input_exists"], "True")

    def test_fundamentals_profile_stage_does_not_switch_downstream_master_implicitly(self) -> None:
        options = self._core_options("profile_no_switch", ["import", "fundamentals_seed", "fundamentals_profile", "scoring"])
        self._write_profile_review_rows(
            Path(options.profile_review_input),
            [self._profile_review_row(isin="", proposed_company_type_profile="STANDARD", profile_reason="operating company")],
        )

        manifest = run_personal_run_engine(options)

        scoring_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "scoring")
        scoring_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "scoring")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(scoring_result["used_inputs"]["fundamentals_source_mode"], "BASE")
        self.assertEqual(scoring_result["used_inputs"]["fundamentals_master"], options.fundamentals_master)
        self.assertNotEqual(scoring_result["used_inputs"]["fundamentals_master"], options.profiled_master_output)
        self.assertEqual(scoring_inputs["fundamentals_master"]["input_path"], options.fundamentals_master)
        self.assertIn("fundamentals_source_mode=BASE", scoring_inputs["fundamentals_master"]["notes"])

    def test_fundamentals_snapshot_ingest_stage_writes_normalized_unmatched_evidence_staging_and_summary(self) -> None:
        options = self._core_options("snapshot_stage", ["import", "fundamentals_seed", "fundamentals_snapshot_ingest"])
        self._write_snapshot_rows(
            Path(options.fundamentals_snapshot_input),
            [
                self._snapshot_row(),
                self._snapshot_row(ticker="UNMATCHED", company_name="Unknown Co", roic="12", fcf_margin="9"),
            ],
        )

        manifest = run_personal_run_engine(options)

        normalized_rows = read_csv_rows(options.fundamentals_snapshot_normalized_output)
        unmatched_rows = read_csv_rows(options.fundamentals_snapshot_unmatched_output)
        evidence_rows = read_csv_rows(options.fundamentals_snapshot_evidence_staging_output)
        summary_rows = read_csv_rows(options.fundamentals_snapshot_summary_output)
        snapshot_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "fundamentals_snapshot_ingest")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(len(normalized_rows), 1)
        self.assertEqual(normalized_rows[0]["ticker"], "MSFT")
        self.assertEqual(normalized_rows[0]["match_method"], "TICKER")
        self.assertEqual(len(unmatched_rows), 1)
        self.assertEqual(unmatched_rows[0]["ticker"], "UNMATCHED")
        self.assertEqual(len(evidence_rows), 2)
        self.assertEqual(set(summary_rows[0]), set(SUMMARY_FIELDS))
        self.assertEqual(summary_rows[0]["matched_rows"], "1")
        self.assertEqual(summary_rows[0]["unmatched_rows"], "1")
        self.assertEqual(summary_rows[0]["evidence_rows_generated"], "2")
        self.assertEqual(snapshot_inputs["fundamentals_snapshot_input"]["input_path"], options.fundamentals_snapshot_input)
        self.assertEqual(snapshot_inputs["fundamentals_snapshot_input"]["input_exists"], "True")

    def test_fundamentals_snapshot_ingest_uses_registry_default_input_when_no_cli_override_exists(self) -> None:
        options = self._core_options("snapshot_registry_default", ["import", "fundamentals_seed", "fundamentals_snapshot_ingest"])
        registry_snapshot = self._path("_tmp_snapshot_registry_default_input.csv")
        self._write_snapshot_rows(Path(registry_snapshot), [self._snapshot_row()])
        options.fundamentals_snapshot_input = DEFAULT_PATHS["fundamentals_snapshot_input"]
        self._write_data_sources_config(
            Path(options.data_sources_config),
            {
                "fundamentals_snapshot_input": {
                    "enabled": True,
                    "path": str(registry_snapshot),
                    "required": True,
                    "kind": "file",
                    "description": "registry snapshot input should win over repo default",
                }
            },
        )

        manifest = run_personal_run_engine(options)

        snapshot_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "fundamentals_snapshot_ingest")
        snapshot_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "fundamentals_snapshot_ingest")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(snapshot_result["used_inputs"]["fundamentals_snapshot_input"], str(registry_snapshot))
        self.assertEqual(snapshot_inputs["fundamentals_snapshot_input"]["input_path"], str(registry_snapshot))
        self.assertIn("data_source_registry_defaults=fundamentals_snapshot_input", snapshot_inputs["fundamentals_snapshot_input"]["notes"])

    def test_fundamentals_snapshot_review_stage_writes_registry_promoted_backlog_and_summary(self) -> None:
        options = self._core_options(
            "snapshot_review_stage",
            ["import", "fundamentals_seed", "fundamentals_snapshot_ingest", "fundamentals_snapshot_review"],
        )
        self._write_snapshot_rows(Path(options.fundamentals_snapshot_input), [self._snapshot_row()])
        self._write_snapshot_review_rows(
            Path(options.fundamentals_snapshot_review_input),
            [
                self._snapshot_review_row(kpi_name="roic", review_decision="APPROVE"),
                self._snapshot_review_row(kpi_name="fcf_margin", review_decision="PENDING", review_reason="awaiting second check"),
            ],
        )

        manifest = run_personal_run_engine(options)

        registry_rows = read_csv_rows(options.fundamentals_snapshot_review_registry_output)
        promoted_rows = read_csv_rows(options.fundamentals_snapshot_evidence_promoted_output)
        backlog_rows = read_csv_rows(options.fundamentals_snapshot_review_backlog_output)
        summary_rows = read_csv_rows(options.fundamentals_snapshot_review_summary_output)
        review_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "fundamentals_snapshot_review")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(len(registry_rows), 2)
        self.assertEqual({row["promotion_status"] for row in registry_rows}, {"PROMOTED", "PENDING"})
        self.assertEqual(len(promoted_rows), 1)
        self.assertEqual(promoted_rows[0]["kpi_name"], "roic")
        self.assertIn("snapshot_review_decision=APPROVE", promoted_rows[0]["notes"])
        self.assertEqual(len(backlog_rows), 1)
        self.assertEqual(backlog_rows[0]["backlog_status"], "PENDING")
        self.assertEqual(set(summary_rows[0]), set(SNAPSHOT_REVIEW_SUMMARY_FIELDS))
        self.assertEqual(summary_rows[0]["approved_rows"], "1")
        self.assertEqual(summary_rows[0]["pending_rows"], "1")
        self.assertEqual(summary_rows[0]["promoted_rows"], "1")
        self.assertEqual(review_inputs["fundamentals_snapshot_evidence_staging_output"]["input_path"], options.fundamentals_snapshot_evidence_staging_output)
        self.assertEqual(review_inputs["fundamentals_snapshot_review_input"]["input_path"], options.fundamentals_snapshot_review_input)
        self.assertEqual(review_inputs["fundamentals_snapshot_review_input"]["input_exists"], "True")

    def test_fundamentals_snapshot_review_uses_registry_default_input_when_no_cli_override_exists(self) -> None:
        options = self._core_options(
            "snapshot_review_registry_default",
            ["import", "fundamentals_seed", "fundamentals_snapshot_ingest", "fundamentals_snapshot_review"],
        )
        registry_review = self._path("_tmp_snapshot_review_registry_default_input.csv")
        self._write_snapshot_rows(Path(options.fundamentals_snapshot_input), [self._snapshot_row()])
        self._write_snapshot_review_rows(
            Path(registry_review),
            [self._snapshot_review_row(kpi_name="roic", review_decision="APPROVE")],
        )
        options.fundamentals_snapshot_review_input = DEFAULT_PATHS["fundamentals_snapshot_review_input"]
        self._write_data_sources_config(
            Path(options.data_sources_config),
            {
                "fundamentals_snapshot_review_input": {
                    "enabled": True,
                    "path": str(registry_review),
                    "required": True,
                    "kind": "file",
                    "description": "registry snapshot review input should win over repo default",
                }
            },
        )

        manifest = run_personal_run_engine(options)

        review_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "fundamentals_snapshot_review")
        review_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "fundamentals_snapshot_review")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(review_result["used_inputs"]["fundamentals_snapshot_review_input"], str(registry_review))
        self.assertEqual(review_inputs["fundamentals_snapshot_review_input"]["input_path"], str(registry_review))
        self.assertIn(
            "data_source_registry_defaults=fundamentals_snapshot_review_input",
            review_inputs["fundamentals_snapshot_review_input"]["notes"],
        )

    def test_fundamentals_evidence_compose_stage_writes_composed_conflicts_and_summary(self) -> None:
        options = self._core_options(
            "evidence_compose_stage",
            [
                "import",
                "fundamentals_seed",
                "fundamentals_snapshot_ingest",
                "fundamentals_snapshot_review",
                "fundamentals_evidence_compose",
            ],
        )
        self._write_evidence_rows(
            Path(options.fundamentals_evidence_input),
            [self._evidence_row(kpi_name="dividend_yield_current_pct", reported_value="0.8")],
        )
        self._write_snapshot_rows(Path(options.fundamentals_snapshot_input), [self._snapshot_row(isin="")])
        self._write_snapshot_review_rows(
            Path(options.fundamentals_snapshot_review_input),
            [self._snapshot_review_row(isin="", kpi_name="roic", review_decision="APPROVE")],
        )

        manifest = run_personal_run_engine(options)

        composed_rows = read_csv_rows(options.fundamentals_evidence_composed_output)
        conflict_rows = read_csv_rows(options.fundamentals_evidence_compose_conflicts_output)
        summary_rows = read_csv_rows(options.fundamentals_evidence_compose_summary_output)
        compose_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "fundamentals_evidence_compose")
        compose_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "fundamentals_evidence_compose")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(len(composed_rows), 2)
        self.assertEqual(conflict_rows, [])
        self.assertEqual(summary_rows[0]["manual_rows_total"], "1")
        self.assertEqual(summary_rows[0]["promoted_rows_total"], "1")
        self.assertEqual(summary_rows[0]["composed_rows_total"], "2")
        self.assertEqual(compose_result["used_inputs"]["fundamentals_evidence_input"], options.fundamentals_evidence_input)
        self.assertEqual(
            compose_result["used_inputs"]["fundamentals_snapshot_evidence_promoted_input"],
            options.fundamentals_snapshot_evidence_promoted_output,
        )
        self.assertEqual(compose_inputs["fundamentals_evidence_input"]["input_path"], options.fundamentals_evidence_input)
        self.assertEqual(
            compose_inputs["fundamentals_snapshot_evidence_promoted_input"]["input_path"],
            options.fundamentals_snapshot_evidence_promoted_output,
        )

    def test_fundamentals_evidence_compose_uses_registry_default_promoted_input_when_no_cli_override_exists(self) -> None:
        options = self._core_options("evidence_compose_registry_default", ["import", "fundamentals_seed", "fundamentals_evidence_compose"])
        registry_promoted = self._path("_tmp_evidence_compose_registry_promoted.csv")
        self._write_empty_evidence(Path(options.fundamentals_evidence_input))
        self._write_evidence_rows(
            Path(registry_promoted),
            [
                self._evidence_row(
                    source_type="SNAPSHOT_IMPORT",
                    source_name="vendor_snapshot",
                    source_reference="vendor_export_2026q1",
                    source_as_of_date="2026-04-15",
                    verification_status="UNVERIFIED",
                    data_quality_flag="REVIEW",
                    notes="registry promoted evidence",
                )
            ],
        )
        options.fundamentals_snapshot_evidence_promoted_input = DEFAULT_PATHS["fundamentals_snapshot_evidence_promoted_input"]
        self._write_data_sources_config(
            Path(options.data_sources_config),
            {
                "fundamentals_snapshot_evidence_promoted_input": {
                    "enabled": True,
                    "path": str(registry_promoted),
                    "required": True,
                    "kind": "file",
                    "description": "registry promoted evidence input for compose stage",
                }
            },
        )

        manifest = run_personal_run_engine(options)

        compose_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "fundamentals_evidence_compose")
        compose_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "fundamentals_evidence_compose")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(
            compose_result["used_inputs"]["fundamentals_snapshot_evidence_promoted_input"],
            str(registry_promoted),
        )
        self.assertEqual(compose_inputs["fundamentals_snapshot_evidence_promoted_input"]["input_path"], str(registry_promoted))
        self.assertIn(
            "data_source_registry_defaults=fundamentals_snapshot_evidence_promoted_input",
            compose_inputs["fundamentals_snapshot_evidence_promoted_input"]["notes"],
        )

    def test_use_composed_evidence_switch_routes_fundamentals_evidence_explicitly(self) -> None:
        options = self._core_options(
            "use_composed_evidence",
            ["import", "fundamentals_seed", "fundamentals_evidence_compose", "fundamentals_evidence"],
        )
        options.use_composed_evidence = True
        self._write_empty_evidence(Path(options.fundamentals_evidence_input))
        self._write_evidence_rows(
            Path(options.fundamentals_snapshot_evidence_promoted_input),
            [
                self._evidence_row(
                    source_type="SNAPSHOT_IMPORT",
                    source_name="vendor_snapshot",
                    source_reference="vendor_export_2026q1",
                    source_as_of_date="2026-04-15",
                    verification_status="UNVERIFIED",
                    data_quality_flag="REVIEW",
                    notes="promoted snapshot evidence",
                )
            ],
        )

        manifest = run_personal_run_engine(options)

        evidence_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "fundamentals_evidence")
        evidence_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "fundamentals_evidence")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(evidence_result["used_inputs"]["fundamentals_evidence_input"], options.fundamentals_evidence_composed_output)
        self.assertEqual(evidence_result["used_inputs"]["evidence_input_mode"], "COMPOSED")
        self.assertEqual(evidence_inputs["fundamentals_evidence_input"]["input_path"], options.fundamentals_evidence_composed_output)
        self.assertIn("evidence_input_mode=COMPOSED", evidence_inputs["fundamentals_evidence_input"]["notes"])

    def test_use_composed_evidence_and_explicit_different_evidence_input_are_mutually_exclusive(self) -> None:
        options = self._core_options("use_composed_evidence_conflict", ["import", "fundamentals_seed", "fundamentals_evidence"])
        options.use_composed_evidence = True
        self._write_empty_evidence(Path(options.fundamentals_evidence_input))
        self._write_evidence_rows(
            Path(options.fundamentals_evidence_composed_output),
            [
                self._evidence_row(
                    source_type="SNAPSHOT_IMPORT",
                    source_name="vendor_snapshot",
                    source_reference="vendor_export_2026q1",
                    source_as_of_date="2026-04-15",
                    verification_status="UNVERIFIED",
                    data_quality_flag="REVIEW",
                )
            ],
        )

        with self.assertRaisesRegex(RuntimeError, "--use-composed-evidence and an explicit --fundamentals-evidence-input are mutually exclusive"):
            run_personal_run_engine(options)

        manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        self.assertEqual(manifest["run_status"], "FAILED")
        evidence_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "fundamentals_evidence")
        self.assertEqual(evidence_result["status"], "FAILED")

    def test_use_profiled_master_switch_routes_scoring_and_coverage_explicitly(self) -> None:
        options = self._core_options("profiled_switch", ["import", "fundamentals_seed", "fundamentals_profile", "scoring", "coverage"])
        options.use_profiled_master = True
        self._write_profile_review_rows(
            Path(options.profile_review_input),
            [self._profile_review_row(isin="", proposed_company_type_profile="STANDARD", profile_reason="operating company")],
        )

        manifest = run_personal_run_engine(options)

        scoring_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "scoring")
        coverage_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "coverage")
        coverage_rows = read_csv_rows(options.coverage_output)
        used_input_rows = read_csv_rows(options.used_inputs_output)
        scoring_inputs = self._used_inputs_for_stage(used_input_rows, "scoring")
        coverage_inputs = self._used_inputs_for_stage(used_input_rows, "coverage")
        profiled_lineage_rows = [
            row
            for row in used_input_rows
            if row["stage_name"] in {"scoring", "coverage"} and row["input_role"] == "fundamentals_master"
        ]
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertTrue(manifest["inputs"]["use_profiled_master"])
        self.assertEqual(scoring_result["used_inputs"]["fundamentals_source_mode"], "PROFILED")
        self.assertEqual(coverage_result["used_inputs"]["fundamentals_source_mode"], "PROFILED")
        self.assertEqual(scoring_result["used_inputs"]["fundamentals_master"], options.profiled_master_output)
        self.assertEqual(coverage_result["used_inputs"]["fundamentals_master"], options.profiled_master_output)
        self.assertEqual({row["input_path"] for row in profiled_lineage_rows}, {options.profiled_master_output})
        self.assertTrue(all("fundamentals_source_mode=PROFILED" in row["notes"] for row in profiled_lineage_rows))
        self.assertEqual(scoring_inputs["scoring_config"]["input_path"], scoring_engine.DEFAULT_SCORING_PATH)
        self.assertEqual(coverage_inputs["metric_definitions"]["input_path"], DEFAULT_METRIC_DEFINITIONS_PATH)
        self.assertEqual(coverage_rows[0]["company_type_profile"], "STANDARD")

    def test_profile_stage_can_build_profiled_master_from_explicit_evidence_identity_master(self) -> None:
        options = self._core_options("profiled_explicit_master", ["import", "fundamentals_profile", "scoring", "coverage"])
        options.use_profiled_master = True
        explicit_master = self._path("_tmp_profiled_explicit_master_input.csv")
        options.fundamentals_master = str(explicit_master)
        explicit_row = self._personal_master_row(ticker="MSFT", isin="US5949181045", company_name="Microsoft")
        explicit_row["ticker"] = "MSFT"
        explicit_row["country"] = "US"
        explicit_row["notes"] = "sec_identity_apply_ticker=MSFT; sec_identity_apply_country=US"
        self._write_personal_master_rows(explicit_master, [explicit_row])
        self._write_profile_review_rows(
            Path(options.profile_review_input),
            [self._profile_review_row(ticker="MSFT", isin="US5949181045", company_name="Microsoft", proposed_company_type_profile="STANDARD", profile_reason="operating company")],
        )

        manifest = run_personal_run_engine(options)

        profile_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "fundamentals_profile")
        scoring_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "scoring")
        coverage_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "coverage")
        used_input_rows = read_csv_rows(options.used_inputs_output)
        profile_inputs = self._used_inputs_for_stage(used_input_rows, "fundamentals_profile")
        scoring_inputs = self._used_inputs_for_stage(used_input_rows, "scoring")
        coverage_inputs = self._used_inputs_for_stage(used_input_rows, "coverage")
        profiled_rows = read_csv_rows(options.profiled_master_output)

        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(profile_result["used_inputs"]["fundamentals_master"], str(explicit_master))
        self.assertEqual(profile_inputs["fundamentals_master"]["input_path"], str(explicit_master))
        self.assertEqual(profiled_rows[0]["company_type_profile"], "STANDARD")
        self.assertEqual(scoring_result["used_inputs"]["fundamentals_master"], options.profiled_master_output)
        self.assertEqual(coverage_result["used_inputs"]["fundamentals_master"], options.profiled_master_output)
        self.assertEqual(scoring_inputs["fundamentals_master"]["input_path"], options.profiled_master_output)
        self.assertEqual(coverage_inputs["fundamentals_master"]["input_path"], options.profiled_master_output)
        self.assertIn("fundamentals_source_mode=PROFILED", scoring_inputs["fundamentals_master"]["notes"])
        self.assertIn("fundamentals_source_mode=PROFILED", coverage_inputs["fundamentals_master"]["notes"])

    def test_use_profiled_master_routes_overlay_input_without_switching_to_applied(self) -> None:
        options = self._core_options("profiled_overlay", ["import", "fundamentals_seed", "fundamentals_profile", "fundamentals_overlay"])
        options.use_profiled_master = True
        self._write_profile_review_rows(
            Path(options.profile_review_input),
            [self._profile_review_row(isin="", proposed_company_type_profile="STANDARD", profile_reason="operating company")],
        )
        self._write_empty_overlay(Path(options.fundamentals_overlay_input))

        manifest = run_personal_run_engine(options)

        overlay_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "fundamentals_overlay")
        overlay_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "fundamentals_overlay")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(overlay_result["used_inputs"]["fundamentals_source_mode"], "PROFILED")
        self.assertEqual(overlay_result["used_inputs"]["fundamentals_master"], options.profiled_master_output)
        self.assertEqual(overlay_inputs["fundamentals_master"]["input_path"], options.profiled_master_output)
        self.assertIn("fundamentals_source_mode=PROFILED", overlay_inputs["fundamentals_master"]["notes"])
        self.assertTrue(Path(options.fundamentals_applied_master_output).exists())

    def test_use_profiled_master_and_use_applied_master_are_mutually_exclusive(self) -> None:
        options = self._core_options("profiled_applied_conflict", ["import", "fundamentals_seed", "scoring"])
        options.use_profiled_master = True
        options.use_applied_master = True

        with self.assertRaisesRegex(RuntimeError, "--use-profiled-master and --use-applied-master are mutually exclusive"):
            run_personal_run_engine(options)

        manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        statuses = {row["stage_name"]: row["status"] for row in manifest["stage_results"]}
        self.assertEqual(manifest["run_status"], "FAILED")
        self.assertEqual(statuses["scoring"], "FAILED")
        self.assertIn("--use-profiled-master and --use-applied-master are mutually exclusive", manifest["warnings"][0])

    def test_use_evidence_applied_master_is_mutually_exclusive_with_profiled_and_applied(self) -> None:
        conflict_specs = [
            ("evidence_applied_profiled_conflict", "--use-profiled-master and --use-evidence-applied-master are mutually exclusive", {"use_profiled_master": True}),
            ("evidence_applied_applied_conflict", "--use-applied-master and --use-evidence-applied-master are mutually exclusive", {"use_applied_master": True}),
        ]

        for prefix, message, updates in conflict_specs:
            options = self._core_options(prefix, ["import", "fundamentals_seed", "scoring"])
            options.use_evidence_applied_master = True
            for field_name, value in updates.items():
                setattr(options, field_name, value)

            with self.subTest(prefix=prefix):
                with self.assertRaisesRegex(RuntimeError, message):
                    run_personal_run_engine(options)

                manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
                statuses = {row["stage_name"]: row["status"] for row in manifest["stage_results"]}
                self.assertEqual(manifest["run_status"], "FAILED")
                self.assertEqual(statuses["scoring"], "FAILED")
                self.assertIn(message, manifest["warnings"][0])

    def test_use_profiled_master_without_projection_fails_fast(self) -> None:
        options = self._core_options("profiled_missing", ["import", "fundamentals_seed", "scoring"])
        options.use_profiled_master = True

        with self.assertRaisesRegex(RuntimeError, "profiled personal fundamentals master"):
            run_personal_run_engine(options)

        manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        statuses = {row["stage_name"]: row["status"] for row in manifest["stage_results"]}
        self.assertEqual(manifest["run_status"], "FAILED")
        self.assertEqual(statuses["scoring"], "FAILED")
        self.assertIn("profiled personal fundamentals master", manifest["warnings"][0])

    def test_use_applied_master_switch_routes_scoring_explicitly(self) -> None:
        options = self._core_options("applied_switch", ["import", "fundamentals_seed", "fundamentals_overlay", "scoring", "coverage"])
        options.use_applied_master = True
        self._write_empty_overlay(Path(options.fundamentals_overlay_input))

        manifest = run_personal_run_engine(options)

        scoring_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "scoring")
        coverage_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "coverage")
        artifact_roles = {row["artifact_role"] for row in read_csv_rows(options.artifacts_output) if row["produced"] == "True"}
        used_input_rows = read_csv_rows(options.used_inputs_output)
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertTrue(manifest["inputs"]["use_applied_master"])
        self.assertEqual(scoring_result["used_inputs"]["fundamentals_source_mode"], "APPLIED")
        self.assertEqual(coverage_result["used_inputs"]["fundamentals_source_mode"], "APPLIED")
        self.assertEqual(scoring_result["used_inputs"]["fundamentals_master"], options.fundamentals_applied_master_output)
        self.assertEqual(coverage_result["used_inputs"]["fundamentals_master"], options.fundamentals_applied_master_output)
        overlay_inputs = self._used_inputs_for_stage(used_input_rows, "fundamentals_overlay")
        scoring_inputs = self._used_inputs_for_stage(used_input_rows, "scoring")
        coverage_inputs = self._used_inputs_for_stage(used_input_rows, "coverage")
        applied_lineage_rows = [
            row
            for row in used_input_rows
            if row["stage_name"] in {"scoring", "coverage"} and row["input_role"] == "fundamentals_master"
        ]
        self.assertEqual({row["input_path"] for row in applied_lineage_rows}, {options.fundamentals_applied_master_output})
        self.assertTrue(all("fundamentals_source_mode=APPLIED" in row["notes"] for row in applied_lineage_rows))
        self.assertEqual(overlay_inputs["fundamentals_schema"]["input_path"], DEFAULT_OVERLAY_SCHEMA_PATH)
        self.assertEqual(scoring_inputs["scoring_config"]["input_path"], scoring_engine.DEFAULT_SCORING_PATH)
        self.assertEqual(coverage_inputs["metric_definitions"]["input_path"], DEFAULT_METRIC_DEFINITIONS_PATH)
        self.assertIn("fundamentals_source_mode=APPLIED", scoring_inputs["fundamentals_master"]["notes"])
        self.assertIn("fundamentals_source_mode=APPLIED", coverage_inputs["fundamentals_master"]["notes"])
        self.assertIn("applied_master", artifact_roles)

    def test_use_applied_master_without_projection_fails_fast(self) -> None:
        options = self._core_options("applied_missing", ["import", "fundamentals_seed", "scoring"])
        options.use_applied_master = True

        with self.assertRaisesRegex(RuntimeError, "applied personal fundamentals master"):
            run_personal_run_engine(options)

        manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        statuses = {row["stage_name"]: row["status"] for row in manifest["stage_results"]}
        self.assertEqual(manifest["run_status"], "FAILED")
        self.assertEqual(statuses["scoring"], "FAILED")
        self.assertIn("applied personal fundamentals master", manifest["warnings"][0])

    def test_use_evidence_applied_master_without_projection_fails_fast(self) -> None:
        options = self._core_options("evidence_applied_missing", ["import", "fundamentals_seed", "scoring"])
        options.use_evidence_applied_master = True

        with self.assertRaisesRegex(RuntimeError, "evidence-applied personal fundamentals master"):
            run_personal_run_engine(options)

        manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        statuses = {row["stage_name"]: row["status"] for row in manifest["stage_results"]}
        self.assertEqual(manifest["run_status"], "FAILED")
        self.assertEqual(statuses["scoring"], "FAILED")
        self.assertIn("evidence-applied personal fundamentals master", manifest["warnings"][0])

    def test_personal_report_defaults_are_dated_not_sample_paths(self) -> None:
        options = PersonalRunOptions(stages=["import"])
        expected_prefix = f"reports/{date.today().isoformat()}/"

        self.assertEqual(options.watchlist_report_output, f"{expected_prefix}personal_watchlist_report.md")
        self.assertEqual(options.monthly_report_output, f"{expected_prefix}personal_monthly_decision_report.md")
        self.assertEqual(options.portfolio_review_output, f"{expected_prefix}personal_portfolio_review.md")
        self.assertNotIn("reports/sample", options.watchlist_report_output)
        self.assertNotIn("reports/sample", options.monthly_report_output)
        self.assertNotIn("reports/sample", options.portfolio_review_output)

    def test_cli_default_report_paths_for_downstream_stages_are_dated(self) -> None:
        with patch.object(
            sys,
            "argv",
            [
                "personal_run_engine",
                "--stage",
                "coverage",
                "--stage",
                "watchlist",
                "--stage",
                "monthly",
                "--stage",
                "portfolio_review",
            ],
        ):
            options = options_from_args(parse_args())
        expected_prefix = f"reports/{date.today().isoformat()}/"
        self.assertEqual(options.watchlist_report_output, f"{expected_prefix}personal_watchlist_report.md")
        self.assertEqual(options.monthly_report_output, f"{expected_prefix}personal_monthly_decision_report.md")
        self.assertEqual(options.portfolio_review_output, f"{expected_prefix}personal_portfolio_review.md")
        self.assertNotIn("reports/sample", options.watchlist_report_output)
        self.assertNotIn("reports/sample", options.monthly_report_output)
        self.assertNotIn("reports/sample", options.portfolio_review_output)

    def test_data_sources_validate_stage_writes_status_and_resolved_outputs(self) -> None:
        options = self._base_options("data_sources_validate", ["data_sources_validate"])
        options.fundamentals_master = DEFAULT_PATHS["fundamentals_master"]
        options.profile_review_input = DEFAULT_PATHS["profile_review_input"]
        configured_master = self._path("_tmp_data_sources_validate_master.csv")
        configured_review = self._path("_tmp_data_sources_validate_profile_review.csv")
        configured_master.write_text("ticker,company_name\nMSFT,Microsoft\n", encoding="utf-8")
        self._write_profile_review_rows(Path(configured_review), [])
        self._write_data_sources_config(
            Path(options.data_sources_config),
            {
                "fundamentals_master": {
                    "enabled": True,
                    "path": str(configured_master),
                    "required": True,
                    "kind": "file",
                    "description": "configured personal fundamentals master",
                },
                "profile_review_input": {
                    "enabled": True,
                    "path": str(configured_review),
                    "required": False,
                    "kind": "file",
                    "description": "configured profile review input",
                },
            },
        )

        manifest = run_personal_run_engine(options)

        status_rows = read_csv_rows(options.data_source_status_output)
        resolved_rows = read_csv_rows(options.data_source_resolved_output)
        used_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "data_sources_validate")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(set(status_rows[0]), set(STATUS_FIELDS))
        self.assertEqual(set(resolved_rows[0]), set(RESOLVED_FIELDS))
        self.assertEqual(used_inputs["data_sources_config"]["input_path"], options.data_sources_config)
        self.assertEqual(used_inputs["source_fundamentals_master"]["input_path"], str(configured_master))
        self.assertEqual(
            {row["source_key"] for row in resolved_rows if row["used_as_default_input"] == "True"},
            {"fundamentals_master", "profile_review_input"},
        )

    def test_required_missing_data_source_fails_fast_with_source_key(self) -> None:
        options = self._base_options("data_sources_missing", ["data_sources_validate"])
        missing_master = self._path("_tmp_data_sources_missing_master.csv")
        self._write_data_sources_config(
            Path(options.data_sources_config),
            {
                "fundamentals_master": {
                    "enabled": True,
                    "path": str(missing_master),
                    "required": True,
                    "kind": "file",
                    "description": "missing configured personal fundamentals master",
                }
            },
        )

        with self.assertRaisesRegex(RuntimeError, "fundamentals_master"):
            run_personal_run_engine(options)

        manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        self.assertEqual(manifest["run_status"], "FAILED")
        self.assertIn("fundamentals_master", manifest["warnings"][0])

    def test_explicit_cli_fundamentals_master_wins_against_registry_default(self) -> None:
        options = self._core_options("registry_cli_priority", ["import", "fundamentals_seed", "scoring"])
        registry_master = self._path("_tmp_registry_cli_priority_master.csv")
        registry_master.write_text(Path("data/raw/personal_fundamentals_master.csv").read_text(encoding="utf-8"), encoding="utf-8")
        self._write_data_sources_config(
            Path(options.data_sources_config),
            {
                "fundamentals_master": {
                    "enabled": True,
                    "path": str(registry_master),
                    "required": True,
                    "kind": "file",
                    "description": "registry master should lose to explicit CLI path",
                }
            },
        )

        manifest = run_personal_run_engine(options)

        scoring_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "scoring")
        scoring_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "scoring")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(scoring_result["used_inputs"]["fundamentals_master"], options.fundamentals_master)
        self.assertEqual(scoring_inputs["fundamentals_master"]["input_path"], options.fundamentals_master)
        self.assertNotEqual(scoring_inputs["fundamentals_master"]["input_path"], str(registry_master))
        self.assertNotIn("data_source_registry_defaults=fundamentals_master", scoring_inputs["fundamentals_master"]["notes"])

    def test_registry_default_fundamentals_master_overrides_repo_default_when_no_cli_override_exists(self) -> None:
        options = self._core_options("registry_default_priority", ["import", "scoring"])
        registry_master = self._path("_tmp_registry_default_priority_master.csv")
        registry_master.write_text(Path("data/raw/personal_fundamentals_master.csv").read_text(encoding="utf-8"), encoding="utf-8")
        options.fundamentals_master = "data/raw/personal_fundamentals_master.csv"
        self._write_data_sources_config(
            Path(options.data_sources_config),
            {
                "fundamentals_master": {
                    "enabled": True,
                    "path": str(registry_master),
                    "required": True,
                    "kind": "file",
                    "description": "registry master should win over repo default",
                }
            },
        )

        manifest = run_personal_run_engine(options)

        scoring_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "scoring")
        scoring_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "scoring")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(scoring_result["used_inputs"]["fundamentals_master"], str(registry_master))
        self.assertEqual(scoring_inputs["fundamentals_master"]["input_path"], str(registry_master))
        self.assertIn("data_source_registry_defaults=fundamentals_master", scoring_inputs["fundamentals_master"]["notes"])

    def test_registry_default_watchlist_input_is_used_when_no_cli_override_exists(self) -> None:
        options = self._core_options(
            "watchlist_registry_default",
            ["import", "fundamentals_seed", "scoring", "watchlist"],
        )
        registry_watchlist = self._path("_tmp_watchlist_registry_default_input.csv")
        self._write_watchlist(registry_watchlist)
        options.watchlist_input = None
        self._write_data_sources_config(
            Path(options.data_sources_config),
            {
                "watchlist_input": {
                    "enabled": True,
                    "path": str(registry_watchlist),
                    "required": False,
                    "kind": "file",
                    "description": "registry watchlist should win when no explicit CLI path exists",
                }
            },
        )

        manifest = run_personal_run_engine(options)

        watchlist_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "watchlist")
        watchlist_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "watchlist")
        status_rows = {row["source_key"]: row for row in read_csv_rows(options.data_source_status_output)}
        resolved_rows = {row["source_key"]: row for row in read_csv_rows(options.data_source_resolved_output)}
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(watchlist_result["used_inputs"]["watchlist_input"], str(registry_watchlist))
        self.assertEqual(watchlist_inputs["watchlist_input"]["input_path"], str(registry_watchlist))
        self.assertIn("data_source_registry_defaults=watchlist_input", watchlist_inputs["watchlist_input"]["notes"])
        self.assertEqual(status_rows["watchlist_input"]["status"], "OK")
        self.assertEqual(resolved_rows["watchlist_input"]["used_as_default_input"], "True")

    def test_explicit_cli_watchlist_input_wins_against_registry_default(self) -> None:
        options = self._core_options("watchlist_registry_cli_priority", ["import", "fundamentals_seed", "scoring", "watchlist"])
        explicit_watchlist = str(options.watchlist_input)
        registry_watchlist = self._path("_tmp_watchlist_registry_cli_priority_input.csv")
        self._write_watchlist(registry_watchlist)
        self._write_data_sources_config(
            Path(options.data_sources_config),
            {
                "watchlist_input": {
                    "enabled": True,
                    "path": str(registry_watchlist),
                    "required": False,
                    "kind": "file",
                    "description": "registry watchlist should lose to explicit CLI path",
                }
            },
        )

        manifest = run_personal_run_engine(options)

        watchlist_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "watchlist")
        watchlist_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "watchlist")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(watchlist_result["used_inputs"]["watchlist_input"], explicit_watchlist)
        self.assertEqual(watchlist_inputs["watchlist_input"]["input_path"], explicit_watchlist)
        self.assertNotIn("data_source_registry_defaults=watchlist_input", watchlist_inputs["watchlist_input"]["notes"])

    def test_cli_explicit_fundamentals_master_override_wins_against_registry_end_to_end(self) -> None:
        options = self._core_options("cli_registry_priority_e2e", ["data_sources_validate", "import", "scoring", "coverage"])
        explicit_master = self._path("_tmp_cli_registry_priority_explicit_master.csv")
        registry_master = self._path("_tmp_cli_registry_priority_registry_master.csv")
        self._write_personal_master_rows(Path(explicit_master), [self._personal_master_row()])
        self._write_personal_master_rows(Path(registry_master), [self._personal_master_row(company_name="Registry Microsoft")])
        self._write_data_sources_config(
            Path(options.data_sources_config),
            {
                "fundamentals_master": {
                    "enabled": True,
                    "path": str(registry_master),
                    "required": True,
                    "kind": "file",
                    "description": "registry master should lose to explicit CLI override in real CLI path",
                }
            },
        )
        command = [
            "python",
            "-m",
            "src.personal_run_engine",
            "--stage",
            "data_sources_validate",
            "--stage",
            "import",
            "--stage",
            "scoring",
            "--stage",
            "coverage",
            "--data-sources-config",
            options.data_sources_config,
            "--data-source-status-output",
            options.data_source_status_output,
            "--data-source-resolved-output",
            options.data_source_resolved_output,
            "--positions-raw-input",
            str(options.positions_raw_input),
            "--positions-output",
            options.positions_output,
            "--fundamentals-master",
            str(explicit_master),
            "--scores-output",
            options.scores_output,
            "--score-audit-output",
            options.score_audit_output,
            "--coverage-output",
            options.coverage_output,
            "--fundamentals-enriched-output",
            options.fundamentals_enriched_output,
            "--research-priority-output",
            options.research_priority_output,
            "--fundamentals-coverage-report-output",
            str(options.fundamentals_coverage_report_output),
            "--manifest-output",
            options.manifest_output,
            "--artifacts-output",
            options.artifacts_output,
            "--used-inputs-output",
            options.used_inputs_output,
            "--report-output",
            str(options.report_output),
        ]

        result = subprocess.run(command, cwd=Path.cwd(), capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        scoring_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "scoring")
        coverage_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "coverage")
        used_inputs = read_csv_rows(options.used_inputs_output)
        scoring_inputs = self._used_inputs_for_stage(used_inputs, "scoring")
        coverage_inputs = self._used_inputs_for_stage(used_inputs, "coverage")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(scoring_result["used_inputs"]["fundamentals_master"], str(explicit_master))
        self.assertEqual(coverage_result["used_inputs"]["fundamentals_master"], str(explicit_master))
        self.assertEqual(scoring_inputs["fundamentals_master"]["input_path"], str(explicit_master))
        self.assertEqual(coverage_inputs["fundamentals_master"]["input_path"], str(explicit_master))
        self.assertNotIn("data_source_registry_defaults=fundamentals_master", scoring_inputs["fundamentals_master"]["notes"])
        self.assertNotIn("data_source_registry_defaults=fundamentals_master", coverage_inputs["fundamentals_master"]["notes"])

    def test_cli_explicit_snapshot_input_override_wins_against_registry_end_to_end(self) -> None:
        options = self._core_options(
            "cli_snapshot_registry_priority_e2e",
            ["data_sources_validate", "import", "fundamentals_seed", "fundamentals_snapshot_ingest"],
        )
        explicit_snapshot = self._path("_tmp_cli_snapshot_priority_explicit.csv")
        registry_snapshot = self._path("_tmp_cli_snapshot_priority_registry.csv")
        self._write_snapshot_rows(
            Path(explicit_snapshot),
            [self._snapshot_row(source_reference="explicit_snapshot_reference", notes="explicit snapshot")],
        )
        self._write_snapshot_rows(
            Path(registry_snapshot),
            [self._snapshot_row(source_reference="registry_snapshot_reference", notes="registry snapshot")],
        )
        self._write_data_sources_config(
            Path(options.data_sources_config),
            {
                "fundamentals_snapshot_input": {
                    "enabled": True,
                    "path": str(registry_snapshot),
                    "required": True,
                    "kind": "file",
                    "description": "registry snapshot input should lose to explicit CLI override in real CLI path",
                }
            },
        )
        command = [
            "python",
            "-m",
            "src.personal_run_engine",
            "--stage",
            "data_sources_validate",
            "--stage",
            "import",
            "--stage",
            "fundamentals_seed",
            "--stage",
            "fundamentals_snapshot_ingest",
            "--data-sources-config",
            options.data_sources_config,
            "--data-source-status-output",
            options.data_source_status_output,
            "--data-source-resolved-output",
            options.data_source_resolved_output,
            "--positions-raw-input",
            str(options.positions_raw_input),
            "--positions-output",
            options.positions_output,
            "--fundamentals-master",
            options.fundamentals_master,
            "--fundamentals-snapshot-input",
            str(explicit_snapshot),
            "--fundamentals-snapshot-normalized-output",
            options.fundamentals_snapshot_normalized_output,
            "--fundamentals-snapshot-unmatched-output",
            options.fundamentals_snapshot_unmatched_output,
            "--fundamentals-snapshot-evidence-staging-output",
            options.fundamentals_snapshot_evidence_staging_output,
            "--fundamentals-snapshot-summary-output",
            options.fundamentals_snapshot_summary_output,
            "--manifest-output",
            options.manifest_output,
            "--artifacts-output",
            options.artifacts_output,
            "--used-inputs-output",
            options.used_inputs_output,
            "--report-output",
            str(options.report_output),
        ]

        result = subprocess.run(command, cwd=Path.cwd(), capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        snapshot_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "fundamentals_snapshot_ingest")
        used_inputs = read_csv_rows(options.used_inputs_output)
        snapshot_inputs = self._used_inputs_for_stage(used_inputs, "fundamentals_snapshot_ingest")
        normalized_rows = read_csv_rows(options.fundamentals_snapshot_normalized_output)
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(snapshot_result["used_inputs"]["fundamentals_snapshot_input"], str(explicit_snapshot))
        self.assertEqual(snapshot_inputs["fundamentals_snapshot_input"]["input_path"], str(explicit_snapshot))
        self.assertNotIn(
            "data_source_registry_defaults=fundamentals_snapshot_input",
            snapshot_inputs["fundamentals_snapshot_input"]["notes"],
        )
        self.assertEqual(normalized_rows[0]["source_reference"], "explicit_snapshot_reference")

    def test_cli_explicit_snapshot_review_input_override_wins_against_registry_end_to_end(self) -> None:
        options = self._core_options(
            "cli_snapshot_review_registry_priority_e2e",
            ["data_sources_validate", "import", "fundamentals_seed", "fundamentals_snapshot_ingest", "fundamentals_snapshot_review"],
        )
        explicit_review = self._path("_tmp_cli_snapshot_review_priority_explicit.csv")
        registry_review = self._path("_tmp_cli_snapshot_review_priority_registry.csv")
        self._write_snapshot_rows(Path(options.fundamentals_snapshot_input), [self._snapshot_row()])
        self._write_snapshot_review_rows(
            Path(explicit_review),
            [self._snapshot_review_row(kpi_name="roic", review_decision="APPROVE", review_reason="explicit cli review")],
        )
        self._write_snapshot_review_rows(
            Path(registry_review),
            [self._snapshot_review_row(kpi_name="fcf_margin", review_decision="APPROVE", review_reason="registry review should lose")],
        )
        self._write_data_sources_config(
            Path(options.data_sources_config),
            {
                "fundamentals_snapshot_review_input": {
                    "enabled": True,
                    "path": str(registry_review),
                    "required": True,
                    "kind": "file",
                    "description": "registry snapshot review input should lose to explicit CLI override in real CLI path",
                }
            },
        )
        command = [
            "python",
            "-m",
            "src.personal_run_engine",
            "--stage",
            "data_sources_validate",
            "--stage",
            "import",
            "--stage",
            "fundamentals_seed",
            "--stage",
            "fundamentals_snapshot_ingest",
            "--stage",
            "fundamentals_snapshot_review",
            "--data-sources-config",
            options.data_sources_config,
            "--data-source-status-output",
            options.data_source_status_output,
            "--data-source-resolved-output",
            options.data_source_resolved_output,
            "--positions-raw-input",
            str(options.positions_raw_input),
            "--positions-output",
            options.positions_output,
            "--fundamentals-master",
            options.fundamentals_master,
            "--fundamentals-snapshot-input",
            options.fundamentals_snapshot_input,
            "--fundamentals-snapshot-normalized-output",
            options.fundamentals_snapshot_normalized_output,
            "--fundamentals-snapshot-unmatched-output",
            options.fundamentals_snapshot_unmatched_output,
            "--fundamentals-snapshot-evidence-staging-output",
            options.fundamentals_snapshot_evidence_staging_output,
            "--fundamentals-snapshot-summary-output",
            options.fundamentals_snapshot_summary_output,
            "--fundamentals-snapshot-review-input",
            str(explicit_review),
            "--fundamentals-snapshot-review-registry-output",
            options.fundamentals_snapshot_review_registry_output,
            "--fundamentals-snapshot-evidence-promoted-output",
            options.fundamentals_snapshot_evidence_promoted_output,
            "--fundamentals-snapshot-review-backlog-output",
            options.fundamentals_snapshot_review_backlog_output,
            "--fundamentals-snapshot-review-summary-output",
            options.fundamentals_snapshot_review_summary_output,
            "--manifest-output",
            options.manifest_output,
            "--artifacts-output",
            options.artifacts_output,
            "--used-inputs-output",
            options.used_inputs_output,
            "--report-output",
            str(options.report_output),
        ]

        result = subprocess.run(command, cwd=Path.cwd(), capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        review_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "fundamentals_snapshot_review")
        review_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "fundamentals_snapshot_review")
        promoted_rows = read_csv_rows(options.fundamentals_snapshot_evidence_promoted_output)
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(review_result["used_inputs"]["fundamentals_snapshot_review_input"], str(explicit_review))
        self.assertEqual(review_inputs["fundamentals_snapshot_review_input"]["input_path"], str(explicit_review))
        self.assertNotIn(
            "data_source_registry_defaults=fundamentals_snapshot_review_input",
            review_inputs["fundamentals_snapshot_review_input"]["notes"],
        )
        self.assertEqual([row["kpi_name"] for row in promoted_rows], ["roic"])

    def test_used_inputs_capture_stage_config_files_for_core_pipeline(self) -> None:
        options = self._core_options(
            "core_lineage_depth",
            ["import", "fundamentals_seed", "scoring", "coverage", "watchlist", "monthly", "portfolio_review"],
        )

        manifest = run_personal_run_engine(options)

        used_input_rows = read_csv_rows(options.used_inputs_output)
        scoring_inputs = self._used_inputs_for_stage(used_input_rows, "scoring")
        coverage_inputs = self._used_inputs_for_stage(used_input_rows, "coverage")
        watchlist_inputs = self._used_inputs_for_stage(used_input_rows, "watchlist")
        monthly_inputs = self._used_inputs_for_stage(used_input_rows, "monthly")
        review_inputs = self._used_inputs_for_stage(used_input_rows, "portfolio_review")
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(scoring_inputs["portfolio_rules"]["input_path"], scoring_engine.DEFAULT_RULES_PATH)
        self.assertEqual(scoring_inputs["scoring_config"]["input_path"], scoring_engine.DEFAULT_SCORING_PATH)
        self.assertEqual(scoring_inputs["fundamentals_score_rules"]["input_path"], scoring_engine.DEFAULT_FUNDAMENTALS_SCORE_RULES_PATH)
        self.assertEqual(coverage_inputs["metric_definitions"]["input_path"], DEFAULT_METRIC_DEFINITIONS_PATH)
        self.assertEqual(watchlist_inputs["watchlist_config"]["input_path"], watchlist_engine.DEFAULT_WATCHLIST_CONFIG)
        self.assertEqual(watchlist_inputs["portfolio_rules"]["input_path"], watchlist_engine.DEFAULT_RULES_PATH)
        self.assertEqual(monthly_inputs["portfolio_rules"]["input_path"], monthly_ranking_engine.DEFAULT_RULES_PATH)
        self.assertEqual(review_inputs["portfolio_rules"]["input_path"], portfolio_review.DEFAULT_RULES_PATH)
        self.assertTrue(all(row["input_exists"] == "True" for row in [
            scoring_inputs["portfolio_rules"],
            scoring_inputs["scoring_config"],
            scoring_inputs["fundamentals_score_rules"],
            coverage_inputs["metric_definitions"],
            watchlist_inputs["watchlist_config"],
            watchlist_inputs["portfolio_rules"],
            monthly_inputs["portfolio_rules"],
            review_inputs["portfolio_rules"],
        ]))

    def test_decision_quality_stage_generates_outputs_and_lineage(self) -> None:
        options = self._core_options(
            "decision_quality_e2e",
            ["import", "fundamentals_seed", "scoring", "coverage", "watchlist", "cash_refill_review", "rebalance_review", "monthly", "decision_quality"],
        )
        options.portfolio_date = "2026-05-19"
        self._write_decision_quality_inputs(options)

        manifest = run_personal_run_engine(options)

        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertTrue(Path(options.decision_quality_csv_output).exists())
        self.assertTrue(Path(options.decision_quality_json_output).exists())
        self.assertTrue(Path(options.decision_quality_report_output or "").exists())
        self.assertLess(manifest["executed_stage_order"].index("monthly"), manifest["executed_stage_order"].index("decision_quality"))
        decision_quality_result = next(row for row in manifest["stage_results"] if row["stage_name"] == "decision_quality")
        self.assertEqual(decision_quality_result["status"], "SUCCESS")
        artifact_rows = read_csv_rows(options.artifacts_output)
        produced_roles = {row["artifact_role"] for row in artifact_rows if row["stage_name"] == "decision_quality" and row["produced"] == "True"}
        self.assertEqual(produced_roles, {"decision_quality_report", "decision_quality_state_csv", "decision_quality_state_json"})
        used_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "decision_quality")
        self.assertIn("personal_run_manifest", used_inputs)
        self.assertIn("personal_run_used_inputs", used_inputs)
        self.assertIn("monthly_ranking_output", used_inputs)
        self.assertIn("score_audit_output", used_inputs)
        state = json.loads(Path(options.decision_quality_json_output).read_text(encoding="utf-8"))
        self.assertEqual(state["decision_confidence_level"], "MEDIUM")
        self.assertIs(state["review_required"], False)
        run_report = Path(options.report_output or "").read_text(encoding="utf-8")
        self.assertIn("## Decision Quality", run_report)
        self.assertIn("decision_confidence_level", run_report)
        self.assertIn("review_required", run_report)
        self.assertIn("ranking_stability_status", run_report)
        self.assertIn("sensitivity_status", run_report)
        self.assertIn("scenario_status", run_report)
        self.assertIn("tail_risk_status", run_report)
        self.assertIn("Prozess-/Review-Confidence", run_report)
        self.assertIn("no broker/order/trading", run_report)
        self.assertIn("no simulation/backtesting", run_report)

    def test_run_report_renders_decision_quality_not_available_when_stage_missing(self) -> None:
        options = self._core_options("decision_quality_run_report_missing", ["import"])

        manifest = run_personal_run_engine(options)

        self.assertEqual(manifest["run_status"], "SUCCESS")
        run_report = Path(options.report_output or "").read_text(encoding="utf-8")
        self.assertIn("## Decision Quality", run_report)
        self.assertIn("Decision Quality: `NOT_AVAILABLE`", run_report)

    def test_decision_quality_reports_review_when_monthly_stage_lacks_ranking_output(self) -> None:
        options = self._core_options("decision_quality_missing_monthly", ["monthly", "decision_quality"])
        options.portfolio_date = "2026-05-19"
        self._write_minimal_decision_quality_review_inputs(options)
        original_monthly = STAGE_RUNNERS["monthly"]

        def fake_monthly_stage(fake_options: PersonalRunOptions):
            return stage_result(
                "monthly",
                SUCCESS,
                [],
                produced_outputs={"monthly_buy_ranking": fake_options.monthly_ranking_output},
                notes="Synthetic test stage intentionally did not write monthly ranking output.",
            )

        STAGE_RUNNERS["monthly"] = fake_monthly_stage
        try:
            manifest = run_personal_run_engine(options)
        finally:
            STAGE_RUNNERS["monthly"] = original_monthly

        self.assertEqual(manifest["run_status"], "SUCCESS")
        state = json.loads(Path(options.decision_quality_json_output).read_text(encoding="utf-8"))
        self.assertEqual(state["decision_confidence_level"], "REVIEW")
        self.assertIs(state["review_required"], True)
        self.assertIn("monthly_ranking_output", state["missing_critical_fields"])

    def test_decision_quality_reports_review_when_scoring_stage_lacks_score_audit(self) -> None:
        options = self._core_options("decision_quality_missing_score", ["scoring", "decision_quality"])
        options.portfolio_date = "2026-05-19"
        self._write_minimal_decision_quality_review_inputs(options)
        original_scoring = STAGE_RUNNERS["scoring"]

        def fake_scoring_stage(fake_options: PersonalRunOptions):
            return stage_result(
                "scoring",
                SUCCESS,
                [],
                produced_outputs={"score_audit": fake_options.score_audit_output},
                notes="Synthetic test stage intentionally did not write score audit output.",
            )

        STAGE_RUNNERS["scoring"] = fake_scoring_stage
        try:
            manifest = run_personal_run_engine(options)
        finally:
            STAGE_RUNNERS["scoring"] = original_scoring

        self.assertEqual(manifest["run_status"], "SUCCESS")
        state = json.loads(Path(options.decision_quality_json_output).read_text(encoding="utf-8"))
        self.assertEqual(state["decision_confidence_level"], "REVIEW")
        self.assertIs(state["review_required"], True)
        self.assertIn("score_audit_output", state["missing_critical_fields"])

    def test_decision_quality_default_report_path_uses_as_of_date(self) -> None:
        options = self._base_options("decision_quality_default_report", ["decision_quality"])
        options.portfolio_date = "2026-05-19"
        options.decision_quality_report_output = None
        self._write_minimal_decision_quality_review_inputs(options)

        manifest = run_personal_run_engine(options)
        report_path = Path("reports/2026-05-19/decision_quality_report.md")

        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertTrue(report_path.exists())
        report_path.unlink()
        try:
            report_path.parent.rmdir()
        except OSError:
            pass

    def test_decision_quality_output_has_no_forbidden_fields(self) -> None:
        options = self._core_options(
            "decision_quality_forbidden_fields",
            ["import", "fundamentals_seed", "scoring", "coverage", "watchlist", "cash_refill_review", "rebalance_review", "monthly", "decision_quality"],
        )
        self._write_decision_quality_inputs(options)

        run_personal_run_engine(options)

        state = json.loads(Path(options.decision_quality_json_output).read_text(encoding="utf-8"))
        forbidden = {"broker", "order_id", "execution_id", "filled_price", "tax_lot", "simulation", "backtest"}
        self.assertTrue(forbidden.isdisjoint(state.keys()))

    def test_history_and_performance_run_uses_existing_single_benchmark_method(self) -> None:
        options = self._core_options("history_perf", ["import", "history", "performance"])
        options.performance_benchmark = "data/raw/sample_benchmark_timeseries.csv"

        manifest = run_personal_run_engine(options)

        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(manifest["measurement_modes"]["performance"], "SNAPSHOT_ONLY")
        self.assertTrue(Path(options.portfolio_timeseries_output).exists())
        self.assertTrue(Path(options.performance_kpi_output).exists())
        self.assertIn("performance", manifest["data_quality_flags"])
        performance_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "performance")
        self.assertEqual(performance_inputs["benchmark_config"]["input_path"], options.benchmark_config)
        self.assertEqual(performance_inputs["benchmark_config"]["input_exists"], "True")

    def test_cost_tax_run_works_through_orchestrator(self) -> None:
        options = self._base_options("cost_tax", ["cost_tax"])
        options.ledger = "data/raw/sample_cost_tax_ledger.csv"

        manifest = run_personal_run_engine(options)

        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(manifest["measurement_modes"]["cost_tax"], "FULL_LEDGER")
        self.assertTrue(Path(options.cost_tax_kpi_output).exists())
        self.assertTrue(Path(options.cost_tax_archive).exists())
        cost_tax_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "cost_tax")
        self.assertEqual(cost_tax_inputs["cost_tax_config"]["input_path"], DEFAULT_COST_TAX_CONFIG_PATH)
        self.assertEqual(cost_tax_inputs["cost_tax_config"]["input_exists"], "True")

    def test_dashboard_run_works_when_core_upstream_artifacts_exist(self) -> None:
        options = self._core_options(
            "dashboard",
            ["import", "fundamentals_seed", "scoring", "coverage", "watchlist", "monthly", "portfolio_review", "dashboard"],
        )

        manifest = run_personal_run_engine(options)

        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertTrue(Path(options.dashboard_kpi_output).exists())
        self.assertTrue(Path(options.dashboard_universe_output).exists())
        self.assertIn("dashboard", manifest["data_quality_flags"])
        dashboard_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "dashboard")
        self.assertEqual(dashboard_inputs["dashboard_config"]["input_path"], DEFAULT_DASHBOARD_CONFIG_PATH)
        self.assertEqual(dashboard_inputs["dashboard_config"]["input_exists"], "True")

    def test_missing_input_failure_writes_manifest_and_skips_downstream(self) -> None:
        options = self._base_options("failure", ["scoring", "coverage"])

        with self.assertRaisesRegex(RuntimeError, "stage scoring requires existing positions snapshot"):
            run_personal_run_engine(options)

        manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        artifact_rows = read_csv_rows(options.artifacts_output)
        statuses = {row["stage_name"]: row["status"] for row in manifest["stage_results"]}
        self.assertEqual(manifest["run_status"], "FAILED")
        self.assertEqual(statuses["scoring"], "FAILED")
        self.assertEqual(statuses["coverage"], "SKIPPED")
        self.assertEqual([row["artifact_role"] for row in artifact_rows], ["used_inputs_index"])
        self.assertEqual(read_csv_rows(options.used_inputs_output), [])

    def test_multi_benchmark_stage_keeps_deterministic_symbol_order(self) -> None:
        options = self._core_options("multi", ["import", "history", "multi_benchmark"])
        archive_path = Path(options.benchmark_archive)
        registry_path = Path(options.benchmark_registry_output)
        self._write_benchmark_archive_and_registry(archive_path, registry_path)
        options.benchmark_symbols = ["WORLD", "EUROPE"]

        manifest = run_personal_run_engine(options)

        comparison_rows = read_csv_rows(options.multi_benchmark_comparison_output)
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual([row["benchmark_symbol"] for row in comparison_rows], ["EUROPE", "WORLD"])
        multi_inputs = self._used_inputs_for_stage(read_csv_rows(options.used_inputs_output), "multi_benchmark")
        self.assertEqual(multi_inputs["benchmark_config"]["input_path"], options.benchmark_config)
        self.assertEqual(multi_inputs["benchmark_config"]["input_exists"], "True")

    def test_cli_mutually_exclusive_profiled_and_applied_flags_fail_fast(self) -> None:
        options = self._core_options("cli_profiled_applied_conflict", ["import", "fundamentals_seed", "scoring"])
        command = [
            "python",
            "-m",
            "src.personal_run_engine",
        ]
        for stage in options.stages:
            command.extend(["--stage", stage])
        command.extend(
            [
                "--positions-raw-input",
                str(options.positions_raw_input),
                "--positions-output",
                options.positions_output,
                "--fundamentals-master",
                options.fundamentals_master,
                "--scores-output",
                options.scores_output,
                "--score-audit-output",
                options.score_audit_output,
                "--manifest-output",
                options.manifest_output,
                "--artifacts-output",
                options.artifacts_output,
                "--used-inputs-output",
                options.used_inputs_output,
                "--report-output",
                str(options.report_output),
                "--use-profiled-master",
                "--use-applied-master",
            ]
        )

        result = subprocess.run(command, cwd=Path.cwd(), capture_output=True, text=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--use-profiled-master and --use-applied-master are mutually exclusive", result.stderr)
        manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        self.assertEqual(manifest["run_status"], "FAILED")

    def test_cli_composed_evidence_and_explicit_different_evidence_input_fail_fast(self) -> None:
        options = self._core_options("cli_composed_evidence_conflict", ["import", "fundamentals_seed", "fundamentals_evidence"])
        explicit_evidence_input = self._path("_tmp_cli_composed_evidence_conflict_explicit_evidence.csv")
        self._write_empty_evidence(explicit_evidence_input)
        self._write_empty_evidence(Path(options.fundamentals_evidence_composed_output))
        command = [
            "python",
            "-m",
            "src.personal_run_engine",
        ]
        for stage in options.stages:
            command.extend(["--stage", stage])
        command.extend(
            [
                "--positions-raw-input",
                str(options.positions_raw_input),
                "--positions-output",
                options.positions_output,
                "--fundamentals-master",
                options.fundamentals_master,
                "--fundamentals-evidence-input",
                str(explicit_evidence_input),
                "--fundamentals-evidence-composed-output",
                options.fundamentals_evidence_composed_output,
                "--fundamentals-evidence-registry-output",
                options.fundamentals_evidence_registry_output,
                "--fundamentals-research-backlog-output",
                options.fundamentals_research_backlog_output,
                "--fundamentals-proposed-updates-output",
                options.fundamentals_proposed_updates_output,
                "--fundamentals-evidence-summary-output",
                options.fundamentals_evidence_summary_output,
                "--fundamentals-evidence-template-output",
                options.fundamentals_evidence_template_output,
                "--manifest-output",
                options.manifest_output,
                "--artifacts-output",
                options.artifacts_output,
                "--used-inputs-output",
                options.used_inputs_output,
                "--report-output",
                str(options.report_output),
                "--use-composed-evidence",
            ]
        )

        result = subprocess.run(command, cwd=Path.cwd(), capture_output=True, text=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--use-composed-evidence and an explicit --fundamentals-evidence-input are mutually exclusive", result.stderr)
        manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        self.assertEqual(manifest["run_status"], "FAILED")

    def test_cli_smoke_core_run_generates_manifest_artifacts_and_report(self) -> None:
        options = self._core_options(
            "cli",
            ["import", "fundamentals_seed", "scoring", "coverage", "watchlist", "monthly", "portfolio_review"],
        )
        command = [
            "python",
            "-m",
            "src.personal_run_engine",
        ]
        for stage in options.stages:
            command.extend(["--stage", stage])
        command.extend(
            [
                "--positions-raw-input",
                str(options.positions_raw_input),
                "--watchlist-input",
                str(options.watchlist_input),
                "--positions-output",
                options.positions_output,
                "--fundamentals-master",
                options.fundamentals_master,
                "--scores-output",
                options.scores_output,
                "--score-audit-output",
                options.score_audit_output,
                "--coverage-output",
                options.coverage_output,
                "--fundamentals-enriched-output",
                options.fundamentals_enriched_output,
                "--research-priority-output",
                options.research_priority_output,
                "--fundamentals-coverage-report-output",
                str(options.fundamentals_coverage_report_output),
                "--watchlist-output",
                options.watchlist_output,
                "--watchlist-report-output",
                options.watchlist_report_output,
                "--monthly-ranking-output",
                options.monthly_ranking_output,
                "--rebalance-output",
                options.rebalance_output,
                "--monthly-report-output",
                options.monthly_report_output,
                "--portfolio-review-output",
                options.portfolio_review_output,
                "--holdings-output",
                options.holdings_output,
                "--manifest-output",
                options.manifest_output,
                "--artifacts-output",
                options.artifacts_output,
                "--used-inputs-output",
                options.used_inputs_output,
                "--report-output",
                str(options.report_output),
            ]
        )

        result = subprocess.run(command, cwd=Path.cwd(), capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertTrue(Path(options.artifacts_output).exists())
        self.assertTrue(Path(options.used_inputs_output).exists())
        self.assertTrue(Path(options.research_priority_output).exists())
        self.assertTrue(Path(options.report_output).exists())


if __name__ == "__main__":
    unittest.main()
