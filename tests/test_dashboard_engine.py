from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.dashboard_engine import NOT_AVAILABLE, PARTIAL, STALE_COST_TAX_SOURCE, STALE_PERFORMANCE_SOURCE, run_dashboard_engine


class DashboardEngineTests(unittest.TestCase):
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

    def _write_positions(self, path: Path) -> None:
        self._write_csv(
            path,
            [
                "portfolio_date",
                "source_name",
                "ticker",
                "asset_type",
                "sleeve",
                "market_value_eur",
                "weight_total_assets_pct",
                "data_quality_flag",
                "review_flag",
            ],
            [
                {
                    "portfolio_date": "2026-04-10",
                    "source_name": "unit_positions",
                    "ticker": "CORE",
                    "asset_type": "ETF",
                    "sleeve": "CORE_ETF",
                    "market_value_eur": "600",
                    "weight_total_assets_pct": "40",
                    "data_quality_flag": "OK",
                    "review_flag": "False",
                },
                {
                    "portfolio_date": "2026-04-10",
                    "source_name": "unit_positions",
                    "ticker": "QUAL",
                    "asset_type": "ETF",
                    "sleeve": "DIVIDEND_QUALITY_ETF",
                    "market_value_eur": "300",
                    "weight_total_assets_pct": "20",
                    "data_quality_flag": "OK",
                    "review_flag": "False",
                },
                {
                    "portfolio_date": "2026-04-10",
                    "source_name": "unit_positions",
                    "ticker": "MSFT",
                    "asset_type": "STOCK",
                    "sleeve": "SINGLE_STOCK",
                    "market_value_eur": "400",
                    "weight_total_assets_pct": "26.67",
                    "data_quality_flag": "OK",
                    "review_flag": "True",
                },
                {
                    "portfolio_date": "2026-04-10",
                    "source_name": "unit_positions",
                    "ticker": "CASH",
                    "asset_type": "CASH",
                    "sleeve": "CASH",
                    "market_value_eur": "200",
                    "weight_total_assets_pct": "13.33",
                    "data_quality_flag": "OK",
                    "review_flag": "False",
                },
            ],
        )

    def _write_scores(self, path: Path) -> None:
        self._write_csv(
            path,
            [
                "ticker",
                "held_in_portfolio",
                "position_market_value_eur",
                "current_weight_pct",
                "business_score",
                "valuation_score",
                "buy_score",
                "data_quality_flag",
            ],
            [
                {
                    "ticker": "CORE",
                    "held_in_portfolio": "True",
                    "position_market_value_eur": "600",
                    "current_weight_pct": "40",
                    "business_score": "80",
                    "valuation_score": "60",
                    "buy_score": "70",
                    "data_quality_flag": "OK",
                },
                {
                    "ticker": "QUAL",
                    "held_in_portfolio": "True",
                    "position_market_value_eur": "300",
                    "current_weight_pct": "20",
                    "business_score": "70",
                    "valuation_score": "50",
                    "buy_score": "60",
                    "data_quality_flag": "REVIEW",
                },
                {
                    "ticker": "WATCH",
                    "held_in_portfolio": "False",
                    "position_market_value_eur": "0",
                    "current_weight_pct": "0",
                    "business_score": "90",
                    "valuation_score": "80",
                    "buy_score": "85",
                    "data_quality_flag": "MISSING_DATA",
                },
            ],
        )

    def _write_score_audit(self, path: Path) -> None:
        self._write_csv(
            path,
            ["ticker", "data_quality_flag", "missing_kpi_count"],
            [
                {"ticker": "CORE", "data_quality_flag": "OK", "missing_kpi_count": "0"},
                {"ticker": "QUAL", "data_quality_flag": "REVIEW", "missing_kpi_count": "0"},
                {"ticker": "WATCH", "data_quality_flag": "MISSING_DATA", "missing_kpi_count": "2"},
            ],
        )

    def _write_holdings(self, path: Path) -> None:
        self._write_csv(
            path,
            ["ticker", "portfolio_action", "data_quality_flag", "review_flag"],
            [
                {"ticker": "CORE", "portfolio_action": "ADD", "data_quality_flag": "OK", "review_flag": "False"},
                {"ticker": "QUAL", "portfolio_action": "HOLD", "data_quality_flag": "OK", "review_flag": "False"},
                {"ticker": "MSFT", "portfolio_action": "REDUCE", "data_quality_flag": "OK", "review_flag": "True"},
                {"ticker": "EXIT", "portfolio_action": "EXIT_REVIEW", "data_quality_flag": "OK", "review_flag": "True"},
            ],
        )

    def _write_performance_kpis(self, path: Path, as_of_date: str = "2026-04-10") -> None:
        self._write_csv(
            path,
            ["metric_name", "metric_value", "metric_unit", "measurement_mode", "method_used", "time_window", "data_quality_flag", "notes"],
            [
                {
                    "metric_name": "current_cash_weight",
                    "metric_value": "13.33",
                    "metric_unit": "PCT",
                    "measurement_mode": "PARTIAL_HISTORY",
                    "method_used": "SIMPLE_PERIOD_RETURN",
                    "time_window": "",
                    "data_quality_flag": "OK",
                    "notes": "",
                },
                {
                    "metric_name": "current_equity_weight",
                    "metric_value": "86.67",
                    "metric_unit": "PCT",
                    "measurement_mode": "PARTIAL_HISTORY",
                    "method_used": "SIMPLE_PERIOD_RETURN",
                    "time_window": "",
                    "data_quality_flag": "OK",
                    "notes": "",
                },
                {
                    "metric_name": "portfolio_as_of_date",
                    "metric_value": as_of_date,
                    "metric_unit": "DATE",
                    "measurement_mode": "PARTIAL_HISTORY",
                    "method_used": "SIMPLE_PERIOD_RETURN",
                    "time_window": "",
                    "data_quality_flag": "OK",
                    "notes": "",
                },
                {
                    "metric_name": "rolling_return_1m",
                    "metric_value": "INSUFFICIENT_HISTORY",
                    "metric_unit": "PCT",
                    "measurement_mode": "PARTIAL_HISTORY",
                    "method_used": "SIMPLE_PERIOD_RETURN",
                    "time_window": "1m",
                    "data_quality_flag": "OK",
                    "notes": "Not enough history.",
                },
            ],
        )

    def _write_performance_summary(self, path: Path, as_of_date: str = "2026-04-10") -> None:
        self._write_csv(
            path,
            [
                "as_of_date",
                "benchmark_reference_end_date",
                "benchmark_staleness_days",
                "measurement_mode",
                "method_used",
                "benchmark_name",
                "benchmark_symbol",
                "benchmark_return_basis_used",
                "portfolio_value_eur",
                "cash_value_eur",
                "portfolio_nav_eur",
                "invested_assets_eur",
                "current_cash_weight",
                "current_equity_weight",
                "portfolio_timeseries_points",
                "net_cash_flow_assumption",
                "data_quality_flag",
                "notes",
            ],
            [
                {
                    "as_of_date": as_of_date,
                    "benchmark_reference_end_date": as_of_date,
                    "benchmark_staleness_days": "0",
                    "measurement_mode": "PARTIAL_HISTORY",
                    "method_used": "SIMPLE_PERIOD_RETURN",
                    "benchmark_name": "Unit Benchmark",
                    "benchmark_symbol": "UB",
                    "benchmark_return_basis_used": "total_return_index",
                    "portfolio_value_eur": "1300",
                    "cash_value_eur": "200",
                    "portfolio_nav_eur": "1500",
                    "invested_assets_eur": "1300",
                    "current_cash_weight": "13.33",
                    "current_equity_weight": "86.67",
                    "portfolio_timeseries_points": "3",
                    "net_cash_flow_assumption": "UNKNOWN_OR_ZERO_ASSUMED",
                    "data_quality_flag": "OK",
                    "notes": "Unit performance summary.",
                }
            ],
        )

    def _write_performance_comparison(self, path: Path, as_of_date: str = "2026-04-10") -> None:
        self._write_csv(
            path,
            [
                "period_start",
                "period_end",
                "as_of_date",
                "benchmark_reference_end_date",
                "benchmark_staleness_days",
                "portfolio_nav_start_eur",
                "portfolio_nav_end_eur",
                "benchmark_reference_start",
                "benchmark_reference_end",
                "portfolio_return_period",
                "benchmark_return_period",
                "active_return",
                "measurement_mode",
                "method_used",
                "benchmark_name",
                "benchmark_return_basis_used",
                "net_cash_flow_assumption",
                "data_quality_flag",
                "notes",
            ],
            [
                {
                    "period_start": "2026-01-31",
                    "period_end": as_of_date,
                    "as_of_date": as_of_date,
                    "benchmark_reference_end_date": as_of_date,
                    "benchmark_staleness_days": "0",
                    "portfolio_nav_start_eur": "1400",
                    "portfolio_nav_end_eur": "1500",
                    "benchmark_reference_start": "100",
                    "benchmark_reference_end": "104",
                    "portfolio_return_period": "7.14",
                    "benchmark_return_period": "4.0",
                    "active_return": "3.14",
                    "measurement_mode": "PARTIAL_HISTORY",
                    "method_used": "SIMPLE_PERIOD_RETURN",
                    "benchmark_name": "Unit Benchmark",
                    "benchmark_return_basis_used": "total_return_index",
                    "net_cash_flow_assumption": "UNKNOWN_OR_ZERO_ASSUMED",
                    "data_quality_flag": "OK",
                    "notes": "Unit performance comparison.",
                }
            ],
        )

    def _write_cost_tax_kpis(self, path: Path, total_fees: str = "9.0", period_start: str = "2026-01-01", period_end: str = "2026-04-10") -> None:
        period = f"{period_start}..{period_end}"
        self._write_csv(
            path,
            ["metric_name", "metric_value", "metric_unit", "measurement_mode", "period", "data_quality_flag", "notes"],
            [
                {"metric_name": "ledger_measurement_mode", "metric_value": "FULL_LEDGER", "metric_unit": "TEXT", "measurement_mode": "FULL_LEDGER", "period": period, "data_quality_flag": "OK", "notes": ""},
                {"metric_name": "ledger_data_quality_flag", "metric_value": "OK", "metric_unit": "TEXT", "measurement_mode": "FULL_LEDGER", "period": period, "data_quality_flag": "OK", "notes": ""},
                {"metric_name": "period_start", "metric_value": period_start, "metric_unit": "DATE", "measurement_mode": "FULL_LEDGER", "period": period, "data_quality_flag": "OK", "notes": ""},
                {"metric_name": "period_end", "metric_value": period_end, "metric_unit": "DATE", "measurement_mode": "FULL_LEDGER", "period": period, "data_quality_flag": "OK", "notes": ""},
                {"metric_name": "total_fees", "metric_value": total_fees, "metric_unit": "EUR", "measurement_mode": "FULL_LEDGER", "period": period, "data_quality_flag": "OK", "notes": ""},
                {"metric_name": "total_taxes", "metric_value": "5.0", "metric_unit": "EUR", "measurement_mode": "FULL_LEDGER", "period": period, "data_quality_flag": "OK", "notes": ""},
                {"metric_name": "total_withholding_taxes", "metric_value": "1.0", "metric_unit": "EUR", "measurement_mode": "FULL_LEDGER", "period": period, "data_quality_flag": "OK", "notes": ""},
                {"metric_name": "total_dividends_gross", "metric_value": "20.0", "metric_unit": "EUR", "measurement_mode": "FULL_LEDGER", "period": period, "data_quality_flag": "OK", "notes": ""},
                {"metric_name": "total_dividends_net", "metric_value": "14.0", "metric_unit": "EUR", "measurement_mode": "FULL_LEDGER", "period": period, "data_quality_flag": "OK", "notes": ""},
                {"metric_name": "total_realized_pnl_before_tax", "metric_value": "10.0", "metric_unit": "EUR", "measurement_mode": "FULL_LEDGER", "period": period, "data_quality_flag": "OK", "notes": ""},
                {"metric_name": "total_realized_pnl_after_tax_estimate_or_partial", "metric_value": "7.0", "metric_unit": "EUR", "measurement_mode": "FULL_LEDGER", "period": period, "data_quality_flag": "OK", "notes": ""},
                {"metric_name": "gross_to_net_dividend_gap", "metric_value": "6.0", "metric_unit": "EUR", "measurement_mode": "FULL_LEDGER", "period": period, "data_quality_flag": "OK", "notes": ""},
                {"metric_name": "fee_drag_estimate", "metric_value": NOT_AVAILABLE, "metric_unit": "TEXT", "measurement_mode": "FULL_LEDGER", "period": period, "data_quality_flag": "OK", "notes": "No period link."},
                {"metric_name": "realized_tax_drag", "metric_value": "3.0", "metric_unit": "EUR", "measurement_mode": "FULL_LEDGER", "period": period, "data_quality_flag": "OK", "notes": ""},
            ],
        )

    def _write_cost_tax_summary(self, path: Path, total_fees: str = "2.0", period_start: str = "2026-01-01", period_end: str = "2026-04-10") -> None:
        self._write_csv(
            path,
            [
                "period_start",
                "period_end",
                "total_fees",
                "total_taxes",
                "total_withholding_taxes",
                "total_dividends_gross",
                "total_dividends_net",
                "total_interest_received",
                "total_realized_proceeds",
                "total_realized_cost_basis",
                "total_realized_pnl_before_tax",
                "total_realized_pnl_after_tax",
                "ledger_measurement_mode",
                "ledger_data_quality_flag",
                "notes",
            ],
            [
                {
                    "period_start": period_start,
                    "period_end": period_end,
                    "total_fees": total_fees,
                    "total_taxes": "4.0",
                    "total_withholding_taxes": "1.0",
                    "total_dividends_gross": "18.0",
                    "total_dividends_net": "13.0",
                    "total_interest_received": "0.0",
                    "total_realized_proceeds": "0.0",
                    "total_realized_cost_basis": "0.0",
                    "total_realized_pnl_before_tax": "9.0",
                    "total_realized_pnl_after_tax": "6.0",
                    "ledger_measurement_mode": "FULL_LEDGER",
                    "ledger_data_quality_flag": "OK",
                    "notes": "Unit cost/tax summary.",
                }
            ],
        )

    def _build_full_source_set(self, performance_as_of_date: str = "2026-04-10", cost_tax_period_end: str = "2026-04-10") -> dict[str, str]:
        paths = {
            "positions": str(self._path("_tmp_dashboard_positions.csv")),
            "scores": str(self._path("_tmp_dashboard_scores.csv")),
            "holdings": str(self._path("_tmp_dashboard_holdings.csv")),
            "score_audit": str(self._path("_tmp_dashboard_score_audit.csv")),
            "performance_kpis": str(self._path("_tmp_dashboard_performance_kpis.csv")),
            "performance_summary": str(self._path("_tmp_dashboard_performance_summary.csv")),
            "performance_comparison": str(self._path("_tmp_dashboard_performance_comparison.csv")),
            "cost_tax_kpis": str(self._path("_tmp_dashboard_cost_tax_kpis.csv")),
            "cost_tax_summary": str(self._path("_tmp_dashboard_cost_tax_summary.csv")),
        }
        self._write_positions(Path(paths["positions"]))
        self._write_scores(Path(paths["scores"]))
        self._write_holdings(Path(paths["holdings"]))
        self._write_score_audit(Path(paths["score_audit"]))
        self._write_performance_kpis(Path(paths["performance_kpis"]), as_of_date=performance_as_of_date)
        self._write_performance_summary(Path(paths["performance_summary"]), as_of_date=performance_as_of_date)
        self._write_performance_comparison(Path(paths["performance_comparison"]), as_of_date=performance_as_of_date)
        self._write_cost_tax_kpis(Path(paths["cost_tax_kpis"]), period_end=cost_tax_period_end)
        self._write_cost_tax_summary(Path(paths["cost_tax_summary"]), period_end=cost_tax_period_end)
        return paths

    def test_kpi_consolidation_from_multiple_csv_sources(self) -> None:
        paths = self._build_full_source_set()
        result = run_dashboard_engine(
            positions_path=paths["positions"],
            scores_path=paths["scores"],
            holdings_path=paths["holdings"],
            score_audit_path=paths["score_audit"],
            performance_kpis_path=paths["performance_kpis"],
            performance_summary_path=paths["performance_summary"],
            performance_comparison_path=paths["performance_comparison"],
            cost_tax_kpis_path=paths["cost_tax_kpis"],
            cost_tax_summary_path=paths["cost_tax_summary"],
            kpi_output=str(self._path("_tmp_dashboard_kpis.csv")),
            sections_output=str(self._path("_tmp_dashboard_sections.csv")),
            summary_output=str(self._path("_tmp_dashboard_summary.csv")),
            report_output=str(self._path("_tmp_dashboard_report.md")),
        )
        metric_index = {row["metric_name"]: row for row in result["metric_rows"]}
        self.assertEqual(metric_index["total_assets"]["metric_value"], "1500.0")
        self.assertEqual(metric_index["active_return"]["metric_value"], "3.14")
        self.assertEqual(metric_index["total_fees"]["metric_value"], "9.0")
        self.assertEqual(metric_index["non_core_weight"]["metric_value"], "0.0")
        self.assertEqual(metric_index["non_core_weight"]["availability_status"], "AVAILABLE")

    def test_missing_sources_are_marked_not_available(self) -> None:
        positions_path = self._path("_tmp_dashboard_positions_only.csv")
        self._write_positions(positions_path)
        result = run_dashboard_engine(
            positions_path=str(positions_path),
            scores_path=str(self._path("_missing_scores.csv")),
            holdings_path=str(self._path("_missing_holdings.csv")),
            score_audit_path=str(self._path("_missing_score_audit.csv")),
            performance_kpis_path=str(self._path("_missing_perf_kpis.csv")),
            performance_summary_path=str(self._path("_missing_perf_summary.csv")),
            performance_comparison_path=str(self._path("_missing_perf_comp.csv")),
            cost_tax_kpis_path=str(self._path("_missing_cost_kpis.csv")),
            cost_tax_summary_path=str(self._path("_missing_cost_summary.csv")),
            kpi_output=str(self._path("_tmp_dashboard_missing_kpis.csv")),
            sections_output=str(self._path("_tmp_dashboard_missing_sections.csv")),
            summary_output=str(self._path("_tmp_dashboard_missing_summary.csv")),
            report_output=str(self._path("_tmp_dashboard_missing_report.md")),
        )
        metric_index = {row["metric_name"]: row for row in result["metric_rows"]}
        self.assertEqual(metric_index["weighted_buy_score"]["metric_value"], NOT_AVAILABLE)
        self.assertEqual(result["group_statuses"]["Kosten / Steuern"], NOT_AVAILABLE)

    def test_mixed_sources_produce_partial_block(self) -> None:
        paths = self._build_full_source_set()
        result = run_dashboard_engine(
            positions_path=paths["positions"],
            scores_path=paths["scores"],
            holdings_path=paths["holdings"],
            score_audit_path=paths["score_audit"],
            performance_kpis_path=paths["performance_kpis"],
            performance_summary_path=paths["performance_summary"],
            performance_comparison_path=paths["performance_comparison"],
            cost_tax_kpis_path=paths["cost_tax_kpis"],
            cost_tax_summary_path=paths["cost_tax_summary"],
            kpi_output=str(self._path("_tmp_dashboard_partial_kpis.csv")),
            sections_output=str(self._path("_tmp_dashboard_partial_sections.csv")),
            summary_output=str(self._path("_tmp_dashboard_partial_summary.csv")),
            report_output=str(self._path("_tmp_dashboard_partial_report.md")),
        )
        self.assertEqual(result["group_statuses"]["Benchmark / Performance"], PARTIAL)
        self.assertEqual(result["group_statuses"]["Kosten / Steuern"], PARTIAL)

    def test_source_priority_prefers_kpi_file_over_summary(self) -> None:
        paths = self._build_full_source_set()
        result = run_dashboard_engine(
            positions_path=paths["positions"],
            scores_path=paths["scores"],
            holdings_path=paths["holdings"],
            score_audit_path=paths["score_audit"],
            performance_kpis_path=paths["performance_kpis"],
            performance_summary_path=paths["performance_summary"],
            performance_comparison_path=paths["performance_comparison"],
            cost_tax_kpis_path=paths["cost_tax_kpis"],
            cost_tax_summary_path=paths["cost_tax_summary"],
            kpi_output=str(self._path("_tmp_dashboard_priority_kpis.csv")),
            sections_output=str(self._path("_tmp_dashboard_priority_sections.csv")),
            summary_output=str(self._path("_tmp_dashboard_priority_summary.csv")),
            report_output=str(self._path("_tmp_dashboard_priority_report.md")),
        )
        metric_index = {row["metric_name"]: row for row in result["metric_rows"]}
        self.assertEqual(metric_index["total_fees"]["metric_value"], "9.0")
        self.assertEqual(metric_index["total_fees"]["source_file"], paths["cost_tax_kpis"])

    def test_weighted_score_kpis_are_derived_from_company_scores(self) -> None:
        paths = self._build_full_source_set()
        result = run_dashboard_engine(
            positions_path=paths["positions"],
            scores_path=paths["scores"],
            holdings_path=paths["holdings"],
            score_audit_path=paths["score_audit"],
            performance_kpis_path=paths["performance_kpis"],
            performance_summary_path=paths["performance_summary"],
            performance_comparison_path=paths["performance_comparison"],
            cost_tax_kpis_path=paths["cost_tax_kpis"],
            cost_tax_summary_path=paths["cost_tax_summary"],
            kpi_output=str(self._path("_tmp_dashboard_weighted_kpis.csv")),
            sections_output=str(self._path("_tmp_dashboard_weighted_sections.csv")),
            summary_output=str(self._path("_tmp_dashboard_weighted_summary.csv")),
            report_output=str(self._path("_tmp_dashboard_weighted_report.md")),
        )
        metric_index = {row["metric_name"]: row for row in result["metric_rows"]}
        self.assertEqual(metric_index["weighted_business_score"]["metric_value"], "76.67")
        self.assertEqual(metric_index["weighted_valuation_score"]["metric_value"], "56.67")
        self.assertEqual(metric_index["weighted_buy_score"]["metric_value"], "66.67")

    def test_action_counts_are_derived_from_holdings_table(self) -> None:
        paths = self._build_full_source_set()
        result = run_dashboard_engine(
            positions_path=paths["positions"],
            scores_path=paths["scores"],
            holdings_path=paths["holdings"],
            score_audit_path=paths["score_audit"],
            performance_kpis_path=paths["performance_kpis"],
            performance_summary_path=paths["performance_summary"],
            performance_comparison_path=paths["performance_comparison"],
            cost_tax_kpis_path=paths["cost_tax_kpis"],
            cost_tax_summary_path=paths["cost_tax_summary"],
            kpi_output=str(self._path("_tmp_dashboard_actions_kpis.csv")),
            sections_output=str(self._path("_tmp_dashboard_actions_sections.csv")),
            summary_output=str(self._path("_tmp_dashboard_actions_summary.csv")),
            report_output=str(self._path("_tmp_dashboard_actions_report.md")),
        )
        metric_index = {row["metric_name"]: row for row in result["metric_rows"]}
        self.assertEqual(metric_index["add_count"]["metric_value"], "1")
        self.assertEqual(metric_index["reduce_count"]["metric_value"], "1")
        self.assertEqual(metric_index["exit_review_count"]["metric_value"], "1")

    def test_measurement_modes_are_carried_through(self) -> None:
        paths = self._build_full_source_set()
        result = run_dashboard_engine(
            positions_path=paths["positions"],
            scores_path=paths["scores"],
            holdings_path=paths["holdings"],
            score_audit_path=paths["score_audit"],
            performance_kpis_path=paths["performance_kpis"],
            performance_summary_path=paths["performance_summary"],
            performance_comparison_path=paths["performance_comparison"],
            cost_tax_kpis_path=paths["cost_tax_kpis"],
            cost_tax_summary_path=paths["cost_tax_summary"],
            kpi_output=str(self._path("_tmp_dashboard_modes_kpis.csv")),
            sections_output=str(self._path("_tmp_dashboard_modes_sections.csv")),
            summary_output=str(self._path("_tmp_dashboard_modes_summary.csv")),
            report_output=str(self._path("_tmp_dashboard_modes_report.md")),
        )
        summary_row = result["summary_row"]
        self.assertEqual(summary_row["portfolio_measurement_mode"], "SNAPSHOT_ONLY")
        self.assertEqual(summary_row["performance_measurement_mode"], "PARTIAL_HISTORY")
        self.assertEqual(summary_row["ledger_measurement_mode"], "FULL_LEDGER")

    def test_stale_performance_source_date_is_flagged(self) -> None:
        paths = self._build_full_source_set(performance_as_of_date="2026-01-31")
        report_output = self._path("_tmp_dashboard_stale_performance_report.md")
        result = run_dashboard_engine(
            positions_path=paths["positions"],
            scores_path=paths["scores"],
            holdings_path=paths["holdings"],
            score_audit_path=paths["score_audit"],
            performance_kpis_path=paths["performance_kpis"],
            performance_summary_path=paths["performance_summary"],
            performance_comparison_path=paths["performance_comparison"],
            cost_tax_kpis_path=paths["cost_tax_kpis"],
            cost_tax_summary_path=paths["cost_tax_summary"],
            kpi_output=str(self._path("_tmp_dashboard_stale_performance_kpis.csv")),
            sections_output=str(self._path("_tmp_dashboard_stale_performance_sections.csv")),
            summary_output=str(self._path("_tmp_dashboard_stale_performance_summary.csv")),
            report_output=str(report_output),
        )
        summary_row = result["summary_row"]
        metric_index = {row["metric_name"]: row for row in result["metric_rows"]}
        self.assertEqual(summary_row["performance_source_date"], "2026-01-31")
        self.assertIn(STALE_PERFORMANCE_SOURCE, summary_row["cross_source_data_quality_flag"])
        self.assertIn(STALE_PERFORMANCE_SOURCE, metric_index["cross_source_data_quality_flag"]["metric_value"])
        self.assertIn(STALE_PERFORMANCE_SOURCE, report_output.read_text(encoding="utf-8"))

    def test_fresh_performance_source_date_has_no_stale_flag(self) -> None:
        paths = self._build_full_source_set(performance_as_of_date="2026-04-09", cost_tax_period_end="2026-04-09")
        result = run_dashboard_engine(
            positions_path=paths["positions"],
            scores_path=paths["scores"],
            holdings_path=paths["holdings"],
            score_audit_path=paths["score_audit"],
            performance_kpis_path=paths["performance_kpis"],
            performance_summary_path=paths["performance_summary"],
            performance_comparison_path=paths["performance_comparison"],
            cost_tax_kpis_path=paths["cost_tax_kpis"],
            cost_tax_summary_path=paths["cost_tax_summary"],
            kpi_output=str(self._path("_tmp_dashboard_fresh_dates_kpis.csv")),
            sections_output=str(self._path("_tmp_dashboard_fresh_dates_sections.csv")),
            summary_output=str(self._path("_tmp_dashboard_fresh_dates_summary.csv")),
            report_output=str(self._path("_tmp_dashboard_fresh_dates_report.md")),
        )
        summary_row = result["summary_row"]
        self.assertEqual(summary_row["performance_source_date"], "2026-04-09")
        self.assertEqual(summary_row["cost_tax_source_date"], "2026-04-09")
        self.assertEqual(summary_row["cross_source_data_quality_flag"], "OK")

    def test_stale_cost_tax_source_date_is_flagged(self) -> None:
        paths = self._build_full_source_set(cost_tax_period_end="2026-01-31")
        result = run_dashboard_engine(
            positions_path=paths["positions"],
            scores_path=paths["scores"],
            holdings_path=paths["holdings"],
            score_audit_path=paths["score_audit"],
            performance_kpis_path=paths["performance_kpis"],
            performance_summary_path=paths["performance_summary"],
            performance_comparison_path=paths["performance_comparison"],
            cost_tax_kpis_path=paths["cost_tax_kpis"],
            cost_tax_summary_path=paths["cost_tax_summary"],
            kpi_output=str(self._path("_tmp_dashboard_stale_cost_tax_kpis.csv")),
            sections_output=str(self._path("_tmp_dashboard_stale_cost_tax_sections.csv")),
            summary_output=str(self._path("_tmp_dashboard_stale_cost_tax_summary.csv")),
            report_output=str(self._path("_tmp_dashboard_stale_cost_tax_report.md")),
        )
        summary_row = result["summary_row"]
        self.assertEqual(summary_row["cost_tax_source_date"], "2026-01-31")
        self.assertIn(STALE_COST_TAX_SOURCE, summary_row["cross_source_data_quality_flag"])

    def test_duplicate_kpi_metric_name_is_rejected(self) -> None:
        paths = self._build_full_source_set()
        self._write_csv(
            Path(paths["performance_kpis"]),
            ["metric_name", "metric_value", "metric_unit", "measurement_mode", "method_used", "time_window", "data_quality_flag", "notes"],
            [
                {"metric_name": "current_cash_weight", "metric_value": "10", "metric_unit": "PCT", "measurement_mode": "SNAPSHOT_ONLY", "method_used": "SNAPSHOT_COMPARISON", "time_window": "", "data_quality_flag": "OK", "notes": ""},
                {"metric_name": "current_cash_weight", "metric_value": "11", "metric_unit": "PCT", "measurement_mode": "SNAPSHOT_ONLY", "method_used": "SNAPSHOT_COMPARISON", "time_window": "", "data_quality_flag": "OK", "notes": ""},
            ],
        )
        with self.assertRaisesRegex(ValueError, "duplicate metric_name values: current_cash_weight"):
            run_dashboard_engine(
                positions_path=paths["positions"],
                scores_path=paths["scores"],
                holdings_path=paths["holdings"],
                score_audit_path=paths["score_audit"],
                performance_kpis_path=paths["performance_kpis"],
                performance_summary_path=paths["performance_summary"],
                performance_comparison_path=paths["performance_comparison"],
                cost_tax_kpis_path=paths["cost_tax_kpis"],
                cost_tax_summary_path=paths["cost_tax_summary"],
            )

    def test_blank_kpi_metric_name_is_rejected(self) -> None:
        paths = self._build_full_source_set()
        self._write_csv(
            Path(paths["cost_tax_kpis"]),
            ["metric_name", "metric_value", "metric_unit", "measurement_mode", "period", "data_quality_flag", "notes"],
            [
                {"metric_name": "   ", "metric_value": "FULL_LEDGER", "metric_unit": "TEXT", "measurement_mode": "FULL_LEDGER", "period": "2026-01-01..2026-04-10", "data_quality_flag": "OK", "notes": ""},
            ],
        )
        with self.assertRaisesRegex(ValueError, "blank required field\\(s\\): metric_name"):
            run_dashboard_engine(
                positions_path=paths["positions"],
                scores_path=paths["scores"],
                holdings_path=paths["holdings"],
                score_audit_path=paths["score_audit"],
                performance_kpis_path=paths["performance_kpis"],
                performance_summary_path=paths["performance_summary"],
                performance_comparison_path=paths["performance_comparison"],
                cost_tax_kpis_path=paths["cost_tax_kpis"],
                cost_tax_summary_path=paths["cost_tax_summary"],
            )

    def test_dashboard_artifacts_are_generated(self) -> None:
        paths = self._build_full_source_set()
        kpi_output = self._path("_tmp_dashboard_cli_kpis.csv")
        sections_output = self._path("_tmp_dashboard_cli_sections.csv")
        summary_output = self._path("_tmp_dashboard_cli_summary.csv")
        report_output = self._path("_tmp_dashboard_cli_report.md")
        subprocess.run(
            [
                "python",
                "-m",
                "src.dashboard_engine",
                "--positions",
                paths["positions"],
                "--scores",
                paths["scores"],
                "--holdings",
                paths["holdings"],
                "--score-audit",
                paths["score_audit"],
                "--performance-kpis",
                paths["performance_kpis"],
                "--performance-summary",
                paths["performance_summary"],
                "--performance-comparison",
                paths["performance_comparison"],
                "--cost-tax-kpis",
                paths["cost_tax_kpis"],
                "--cost-tax-summary",
                paths["cost_tax_summary"],
                "--kpi-output",
                str(kpi_output),
                "--sections-output",
                str(sections_output),
                "--summary-output",
                str(summary_output),
                "--report-output",
                str(report_output),
            ],
            check=True,
        )
        self.assertTrue(kpi_output.exists())
        self.assertTrue(sections_output.exists())
        self.assertTrue(summary_output.exists())
        self.assertTrue(report_output.exists())
        self.assertTrue(read_csv_rows(kpi_output))
        self.assertEqual(read_csv_rows(summary_output)[0]["snapshot_date"], "2026-04-10")
        self.assertIn("# KPI-Dashboard", report_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
