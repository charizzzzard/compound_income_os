from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path

from src.common import load_yaml_config, read_csv_rows
from src.performance_engine import (
    INSUFFICIENT_HISTORY,
    NOT_AVAILABLE,
    PARTIAL_HISTORY,
    SIMPLE_PERIOD_RETURN,
    SNAPSHOT_COMPARISON,
    SNAPSHOT_ONLY,
    normalize_benchmark_timeseries,
    run_performance_engine,
)


class PerformanceEngineTests(unittest.TestCase):
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

    def _write_json_yaml(self, path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")

    def _build_positions_snapshot(self, path: Path, portfolio_date: str = "2026-04-10") -> None:
        self._write_csv(
            path,
            [
                "portfolio_date",
                "source_name",
                "ticker",
                "company_name",
                "asset_type",
                "sleeve",
                "market_value_eur",
                "weight_total_assets_pct",
            ],
            [
                {
                    "portfolio_date": portfolio_date,
                    "source_name": "unit_test_positions",
                    "ticker": "VWCE",
                    "company_name": "All World ETF",
                    "asset_type": "ETF",
                    "sleeve": "CORE_ETF",
                    "market_value_eur": "1200",
                    "weight_total_assets_pct": "60.0",
                },
                {
                    "portfolio_date": portfolio_date,
                    "source_name": "unit_test_positions",
                    "ticker": "MSFT",
                    "company_name": "Microsoft",
                    "asset_type": "STOCK",
                    "sleeve": "SINGLE_STOCK",
                    "market_value_eur": "500",
                    "weight_total_assets_pct": "25.0",
                },
                {
                    "portfolio_date": portfolio_date,
                    "source_name": "unit_test_positions",
                    "ticker": "EUR-CASH",
                    "company_name": "Cash",
                    "asset_type": "CASH",
                    "sleeve": "CASH",
                    "market_value_eur": "300",
                    "weight_total_assets_pct": "15.0",
                },
            ],
        )

    def _build_benchmark_csv(
        self,
        path: Path,
        rows: list[dict[str, object]] | None = None,
        include_adjusted: bool = True,
        include_total_return: bool = True,
    ) -> None:
        fieldnames = ["date", "benchmark_name", "benchmark_symbol", "currency", "close"]
        if include_adjusted:
            fieldnames.append("adjusted_close")
        if include_total_return:
            fieldnames.append("total_return_index")
        fieldnames.extend(["dividend", "source_name"])
        default_rows = rows or [
            {
                "date": "2026-01-31",
                "benchmark_name": "Unit Test Benchmark",
                "benchmark_symbol": "UTB",
                "currency": "EUR",
                "close": "100",
                "adjusted_close": "101",
                "total_return_index": "102",
                "dividend": "0.2",
                "source_name": "unit_fixture",
            },
            {
                "date": "2026-04-10",
                "benchmark_name": "Unit Test Benchmark",
                "benchmark_symbol": "UTB",
                "currency": "EUR",
                "close": "105",
                "adjusted_close": "106",
                "total_return_index": "108",
                "dividend": "0.4",
                "source_name": "unit_fixture",
            },
        ]
        normalized_rows: list[dict[str, object]] = []
        for row in default_rows:
            current = dict(row)
            if not include_adjusted:
                current.pop("adjusted_close", None)
            if not include_total_return:
                current.pop("total_return_index", None)
            normalized_rows.append(current)
        self._write_csv(path, fieldnames, normalized_rows)

    def _build_benchmark_config(self, path: Path, benchmark_currency: str = "EUR") -> None:
        self._write_json_yaml(
            path,
            """{
  "benchmark_name": "Unit Test Benchmark",
  "benchmark_symbol": "UTB",
  "benchmark_currency": "%s",
  "portfolio_reference_currency": "EUR",
  "frequency": "monthly",
  "date_column": "date",
  "close_column": "close",
  "adjusted_close_column": "adjusted_close",
  "total_return_index_column": "total_return_index",
  "source_name": "unit_fixture",
  "return_basis_priority": ["total_return_index", "adjusted_close", "close"],
  "data_quality_policy": {
    "price_only_flag": "APPROX_PRICE_ONLY_BENCHMARK",
    "currency_mismatch_flag": "CURRENCY_MISMATCH",
    "duplicate_date_policy": "raise_error",
    "missing_required_field_policy": "raise_error"
  }
}"""
            % benchmark_currency,
        )

    def _build_portfolio_timeseries(self, path: Path) -> None:
        self._write_csv(
            path,
            ["date", "portfolio_nav_eur", "portfolio_value_eur", "cash_value_eur", "source_name", "notes"],
            [
                {
                    "date": "2026-01-31",
                    "portfolio_nav_eur": "1500",
                    "portfolio_value_eur": "1200",
                    "cash_value_eur": "300",
                    "source_name": "manual_nav",
                    "notes": "period start",
                },
                {
                    "date": "2026-03-31",
                    "portfolio_nav_eur": "1600",
                    "portfolio_value_eur": "1280",
                    "cash_value_eur": "320",
                    "source_name": "manual_nav",
                    "notes": "intermediate point",
                },
            ],
        )

    def _build_future_portfolio_timeseries(self, path: Path) -> None:
        self._write_csv(
            path,
            ["date", "portfolio_nav_eur", "portfolio_value_eur", "cash_value_eur", "source_name", "notes"],
            [
                {
                    "date": "2026-01-31",
                    "portfolio_nav_eur": "1500",
                    "portfolio_value_eur": "1200",
                    "cash_value_eur": "300",
                    "source_name": "manual_nav",
                    "notes": "period start",
                },
                {
                    "date": "2026-05-01",
                    "portfolio_nav_eur": "1650",
                    "portfolio_value_eur": "1330",
                    "cash_value_eur": "320",
                    "source_name": "manual_nav",
                    "notes": "invalid future point",
                },
            ],
        )

    def test_benchmark_normalization_uses_priority_basis(self) -> None:
        config = load_yaml_config("configs/benchmark.yaml")
        rows = read_csv_rows("data/raw/sample_benchmark_timeseries.csv")
        normalized = normalize_benchmark_timeseries(rows, config)
        self.assertEqual(len(normalized), 4)
        self.assertEqual(normalized[0]["benchmark_return_basis_used"], "total_return_index")
        self.assertEqual(normalized[0]["benchmark_reference_value"], "100.0")

    def test_duplicate_dates_in_benchmark_are_rejected(self) -> None:
        config_path = self._path("_tmp_benchmark_config.yaml")
        benchmark_path = self._path("_tmp_duplicate_benchmark.csv")
        self._build_benchmark_config(config_path)
        self._build_benchmark_csv(
            benchmark_path,
            rows=[
                {
                    "date": "2026-01-31",
                    "benchmark_name": "Unit Test Benchmark",
                    "benchmark_symbol": "UTB",
                    "currency": "EUR",
                    "close": "100",
                    "adjusted_close": "101",
                    "total_return_index": "102",
                    "dividend": "0.1",
                    "source_name": "unit_fixture",
                },
                {
                    "date": "2026-01-31",
                    "benchmark_name": "Unit Test Benchmark",
                    "benchmark_symbol": "UTB",
                    "currency": "EUR",
                    "close": "101",
                    "adjusted_close": "102",
                    "total_return_index": "103",
                    "dividend": "0.1",
                    "source_name": "unit_fixture",
                },
            ],
        )
        rows = read_csv_rows(benchmark_path)
        config = load_yaml_config(config_path)
        with self.assertRaisesRegex(ValueError, "duplicate date: 2026-01-31"):
            normalize_benchmark_timeseries(rows, config)

    def test_snapshot_only_mode(self) -> None:
        positions_path = self._path("_tmp_positions_snapshot.csv")
        benchmark_path = self._path("_tmp_benchmark.csv")
        config_path = self._path("_tmp_benchmark_config.yaml")
        comparison_path = self._path("_tmp_performance_comparison.csv")
        kpi_path = self._path("_tmp_performance_kpis.csv")
        summary_path = self._path("_tmp_performance_summary.csv")
        normalized_benchmark_path = self._path("_tmp_benchmark_normalized.csv")
        portfolio_timeseries_path = self._path("_tmp_portfolio_timeseries_out.csv")
        report_path = self._path("_tmp_performance_report.md")

        self._build_positions_snapshot(positions_path)
        self._build_benchmark_csv(benchmark_path)
        self._build_benchmark_config(config_path)

        run_performance_engine(
            positions_path=str(positions_path),
            benchmark_path=str(benchmark_path),
            benchmark_config_path=str(config_path),
            comparison_output=str(comparison_path),
            kpi_output=str(kpi_path),
            summary_output=str(summary_path),
            normalized_benchmark_output=str(normalized_benchmark_path),
            portfolio_timeseries_output=str(portfolio_timeseries_path),
            report_output=str(report_path),
        )

        comparison_rows = read_csv_rows(comparison_path)
        summary_rows = read_csv_rows(summary_path)
        kpi_rows = read_csv_rows(kpi_path)
        self.assertEqual(summary_rows[0]["measurement_mode"], SNAPSHOT_ONLY)
        self.assertEqual(summary_rows[0]["method_used"], SNAPSHOT_COMPARISON)
        self.assertEqual(comparison_rows[0]["portfolio_return_period"], NOT_AVAILABLE)
        self.assertEqual(comparison_rows[0]["active_return"], NOT_AVAILABLE)
        rolling_1m = next(row for row in kpi_rows if row["metric_name"] == "rolling_return_1m")
        self.assertEqual(rolling_1m["metric_value"], INSUFFICIENT_HISTORY)

    def test_simple_period_comparison_with_explicit_timeseries(self) -> None:
        positions_path = self._path("_tmp_positions_snapshot_period.csv")
        benchmark_path = self._path("_tmp_benchmark_period.csv")
        config_path = self._path("_tmp_benchmark_config_period.yaml")
        portfolio_timeseries_path = self._path("_tmp_portfolio_timeseries.csv")
        comparison_path = self._path("_tmp_performance_comparison_period.csv")
        kpi_path = self._path("_tmp_performance_kpis_period.csv")
        report_path = self._path("_tmp_performance_report_period.md")

        self._build_positions_snapshot(positions_path)
        self._build_benchmark_csv(benchmark_path)
        self._build_benchmark_config(config_path)
        self._build_portfolio_timeseries(portfolio_timeseries_path)

        run_performance_engine(
            positions_path=str(positions_path),
            benchmark_path=str(benchmark_path),
            benchmark_config_path=str(config_path),
            portfolio_timeseries_path=str(portfolio_timeseries_path),
            comparison_output=str(comparison_path),
            kpi_output=str(kpi_path),
            report_output=str(report_path),
        )

        comparison_rows = read_csv_rows(comparison_path)
        self.assertEqual(comparison_rows[0]["measurement_mode"], PARTIAL_HISTORY)
        self.assertEqual(comparison_rows[0]["method_used"], SIMPLE_PERIOD_RETURN)
        self.assertEqual(comparison_rows[0]["period_start"], "2026-01-31")
        self.assertEqual(comparison_rows[0]["period_end"], "2026-04-10")

    def test_future_portfolio_timeseries_date_is_rejected(self) -> None:
        positions_path = self._path("_tmp_positions_snapshot_future_ts.csv")
        benchmark_path = self._path("_tmp_benchmark_future_ts.csv")
        config_path = self._path("_tmp_benchmark_config_future_ts.yaml")
        portfolio_timeseries_path = self._path("_tmp_portfolio_timeseries_future.csv")
        comparison_path = self._path("_tmp_performance_comparison_future_ts.csv")
        kpi_path = self._path("_tmp_performance_kpis_future_ts.csv")
        report_path = self._path("_tmp_performance_report_future_ts.md")

        self._build_positions_snapshot(positions_path, portfolio_date="2026-04-10")
        self._build_benchmark_csv(benchmark_path)
        self._build_benchmark_config(config_path)
        self._build_future_portfolio_timeseries(portfolio_timeseries_path)

        with self.assertRaisesRegex(
            ValueError,
            "snapshot_as_of_date=2026-04-10, latest_portfolio_timeseries_date=2026-05-01",
        ):
            run_performance_engine(
                positions_path=str(positions_path),
                benchmark_path=str(benchmark_path),
                benchmark_config_path=str(config_path),
                portfolio_timeseries_path=str(portfolio_timeseries_path),
                comparison_output=str(comparison_path),
                kpi_output=str(kpi_path),
                report_output=str(report_path),
            )

    def test_valid_portfolio_timeseries_date_keeps_snapshot_as_of_date(self) -> None:
        positions_path = self._path("_tmp_positions_snapshot_valid_ts.csv")
        benchmark_path = self._path("_tmp_benchmark_valid_ts.csv")
        config_path = self._path("_tmp_benchmark_config_valid_ts.yaml")
        portfolio_timeseries_path = self._path("_tmp_portfolio_timeseries_valid.csv")
        comparison_path = self._path("_tmp_performance_comparison_valid_ts.csv")
        summary_path = self._path("_tmp_performance_summary_valid_ts.csv")
        kpi_path = self._path("_tmp_performance_kpis_valid_ts.csv")
        report_path = self._path("_tmp_performance_report_valid_ts.md")

        self._build_positions_snapshot(positions_path, portfolio_date="2026-04-10")
        self._build_benchmark_csv(benchmark_path)
        self._build_benchmark_config(config_path)
        self._build_portfolio_timeseries(portfolio_timeseries_path)

        run_performance_engine(
            positions_path=str(positions_path),
            benchmark_path=str(benchmark_path),
            benchmark_config_path=str(config_path),
            portfolio_timeseries_path=str(portfolio_timeseries_path),
            comparison_output=str(comparison_path),
            kpi_output=str(kpi_path),
            summary_output=str(summary_path),
            report_output=str(report_path),
        )

        summary_row = read_csv_rows(summary_path)[0]
        self.assertEqual(summary_row["as_of_date"], "2026-04-10")

    def test_active_return_is_calculated(self) -> None:
        positions_path = self._path("_tmp_positions_snapshot_active.csv")
        benchmark_path = self._path("_tmp_benchmark_active.csv")
        config_path = self._path("_tmp_benchmark_config_active.yaml")
        portfolio_timeseries_path = self._path("_tmp_portfolio_timeseries_active.csv")
        comparison_path = self._path("_tmp_performance_comparison_active.csv")
        kpi_path = self._path("_tmp_performance_kpis_active.csv")
        report_path = self._path("_tmp_performance_report_active.md")

        self._build_positions_snapshot(positions_path)
        self._build_benchmark_csv(
            benchmark_path,
            rows=[
                {
                    "date": "2026-01-31",
                    "benchmark_name": "Unit Test Benchmark",
                    "benchmark_symbol": "UTB",
                    "currency": "EUR",
                    "close": "100",
                    "adjusted_close": "100",
                    "total_return_index": "100",
                    "dividend": "0.0",
                    "source_name": "unit_fixture",
                },
                {
                    "date": "2026-04-10",
                    "benchmark_name": "Unit Test Benchmark",
                    "benchmark_symbol": "UTB",
                    "currency": "EUR",
                    "close": "108",
                    "adjusted_close": "108",
                    "total_return_index": "108",
                    "dividend": "0.0",
                    "source_name": "unit_fixture",
                },
            ],
        )
        self._build_benchmark_config(config_path)
        self._build_portfolio_timeseries(portfolio_timeseries_path)

        run_performance_engine(
            positions_path=str(positions_path),
            benchmark_path=str(benchmark_path),
            benchmark_config_path=str(config_path),
            portfolio_timeseries_path=str(portfolio_timeseries_path),
            comparison_output=str(comparison_path),
            kpi_output=str(kpi_path),
            report_output=str(report_path),
        )

        comparison_row = read_csv_rows(comparison_path)[0]
        self.assertEqual(comparison_row["portfolio_return_period"], "33.33")
        self.assertEqual(comparison_row["benchmark_return_period"], "8.0")
        self.assertEqual(comparison_row["active_return"], "25.33")

    def test_missing_history_leaves_fields_unavailable(self) -> None:
        positions_path = self._path("_tmp_positions_snapshot_missing_history.csv")
        benchmark_path = self._path("_tmp_benchmark_missing_history.csv")
        config_path = self._path("_tmp_benchmark_config_missing_history.yaml")
        comparison_path = self._path("_tmp_performance_comparison_missing_history.csv")
        kpi_path = self._path("_tmp_performance_kpis_missing_history.csv")
        report_path = self._path("_tmp_performance_report_missing_history.md")

        self._build_positions_snapshot(positions_path)
        self._build_benchmark_csv(benchmark_path)
        self._build_benchmark_config(config_path)

        run_performance_engine(
            positions_path=str(positions_path),
            benchmark_path=str(benchmark_path),
            benchmark_config_path=str(config_path),
            comparison_output=str(comparison_path),
            kpi_output=str(kpi_path),
            report_output=str(report_path),
        )

        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("Kein belastbarer Renditevergleich moeglich", report_text)
        self.assertIn("TIME_WEIGHTED_RETURN", report_text)

    def test_price_only_benchmark_sets_quality_flag(self) -> None:
        config_path = self._path("_tmp_benchmark_config_price_only.yaml")
        benchmark_path = self._path("_tmp_benchmark_price_only.csv")
        self._build_benchmark_config(config_path)
        self._build_benchmark_csv(benchmark_path, include_adjusted=False, include_total_return=False)
        rows = read_csv_rows(benchmark_path)
        config = load_yaml_config(config_path)
        normalized = normalize_benchmark_timeseries(rows, config)
        self.assertEqual(normalized[0]["benchmark_return_basis_used"], "close")
        self.assertIn("APPROX_PRICE_ONLY_BENCHMARK", normalized[0]["data_quality_flag"])

    def test_missing_global_benchmark_basis_in_later_row_is_rejected(self) -> None:
        config_path = self._path("_tmp_benchmark_config_missing_basis.yaml")
        benchmark_path = self._path("_tmp_benchmark_missing_basis.csv")
        self._build_benchmark_config(config_path)
        self._build_benchmark_csv(
            benchmark_path,
            rows=[
                {
                    "date": "2026-01-31",
                    "benchmark_name": "Unit Test Benchmark",
                    "benchmark_symbol": "UTB",
                    "currency": "EUR",
                    "close": "100",
                    "adjusted_close": "101",
                    "total_return_index": "102",
                    "dividend": "0.0",
                    "source_name": "unit_fixture",
                },
                {
                    "date": "2026-04-10",
                    "benchmark_name": "Unit Test Benchmark",
                    "benchmark_symbol": "UTB",
                    "currency": "EUR",
                    "close": "105",
                    "adjusted_close": "106",
                    "total_return_index": "",
                    "dividend": "0.0",
                    "source_name": "unit_fixture",
                },
            ],
        )
        rows = read_csv_rows(benchmark_path)
        config = load_yaml_config(config_path)
        with self.assertRaisesRegex(
            ValueError,
            "missing globally selected basis 'total_return_index' for date 2026-04-10",
        ):
            normalize_benchmark_timeseries(rows, config)

    def test_valid_global_benchmark_basis_in_all_rows_still_normalizes(self) -> None:
        config_path = self._path("_tmp_benchmark_config_valid_basis.yaml")
        benchmark_path = self._path("_tmp_benchmark_valid_basis.csv")
        self._build_benchmark_config(config_path)
        self._build_benchmark_csv(benchmark_path)
        rows = read_csv_rows(benchmark_path)
        config = load_yaml_config(config_path)
        normalized = normalize_benchmark_timeseries(rows, config)
        self.assertEqual(len(normalized), 2)
        self.assertEqual(normalized[-1]["benchmark_reference_value"], "108.0")

    def test_currency_mismatch_sets_quality_flag(self) -> None:
        config_path = self._path("_tmp_benchmark_config_currency.yaml")
        benchmark_path = self._path("_tmp_benchmark_currency.csv")
        self._build_benchmark_config(config_path, benchmark_currency="EUR")
        self._build_benchmark_csv(
            benchmark_path,
            rows=[
                {
                    "date": "2026-01-31",
                    "benchmark_name": "Unit Test Benchmark",
                    "benchmark_symbol": "UTB",
                    "currency": "USD",
                    "close": "100",
                    "adjusted_close": "101",
                    "total_return_index": "102",
                    "dividend": "0.0",
                    "source_name": "unit_fixture",
                }
            ],
        )
        rows = read_csv_rows(benchmark_path)
        config = load_yaml_config(config_path)
        normalized = normalize_benchmark_timeseries(rows, config)
        self.assertIn("CURRENCY_MISMATCH", normalized[0]["data_quality_flag"])

    def test_performance_artifacts_are_generated(self) -> None:
        positions_path = self._path("_tmp_positions_snapshot_artifacts.csv")
        benchmark_path = self._path("_tmp_benchmark_artifacts.csv")
        config_path = self._path("_tmp_benchmark_config_artifacts.yaml")
        comparison_path = self._path("_tmp_performance_comparison_artifacts.csv")
        kpi_path = self._path("_tmp_performance_kpis_artifacts.csv")
        summary_path = self._path("_tmp_performance_summary_artifacts.csv")
        normalized_benchmark_path = self._path("_tmp_benchmark_normalized_artifacts.csv")
        portfolio_timeseries_path = self._path("_tmp_portfolio_timeseries_artifacts.csv")
        report_path = self._path("_tmp_performance_report_artifacts.md")

        self._build_positions_snapshot(positions_path)
        self._build_benchmark_csv(benchmark_path)
        self._build_benchmark_config(config_path)

        outputs = run_performance_engine(
            positions_path=str(positions_path),
            benchmark_path=str(benchmark_path),
            benchmark_config_path=str(config_path),
            comparison_output=str(comparison_path),
            kpi_output=str(kpi_path),
            summary_output=str(summary_path),
            normalized_benchmark_output=str(normalized_benchmark_path),
            portfolio_timeseries_output=str(portfolio_timeseries_path),
            report_output=str(report_path),
        )

        self.assertTrue(outputs["normalized_benchmark_output"].exists())
        self.assertTrue(outputs["summary_output"].exists())
        self.assertTrue(outputs["comparison_output"].exists())
        self.assertTrue(outputs["kpi_output"].exists())
        self.assertTrue(outputs["report_output"].exists())

    def test_cli_run_generates_outputs(self) -> None:
        positions_path = self._path("_tmp_positions_snapshot_cli.csv")
        benchmark_path = self._path("_tmp_benchmark_cli.csv")
        config_path = self._path("_tmp_benchmark_config_cli.yaml")
        comparison_path = self._path("_tmp_performance_comparison_cli.csv")
        kpi_path = self._path("_tmp_performance_kpis_cli.csv")
        report_path = self._path("_tmp_performance_report_cli.md")

        self._build_positions_snapshot(positions_path)
        self._build_benchmark_csv(benchmark_path)
        self._build_benchmark_config(config_path)

        result = subprocess.run(
            [
                "python",
                "-m",
                "src.performance_engine",
                "--positions",
                str(positions_path),
                "--benchmark",
                str(benchmark_path),
                "--benchmark-config",
                str(config_path),
                "--comparison-output",
                str(comparison_path),
                "--kpi-output",
                str(kpi_path),
                "--report-output",
                str(report_path),
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, msg=f"{result.stdout}\n{result.stderr}")
        self.assertTrue(comparison_path.exists())
        self.assertTrue(kpi_path.exists())
        self.assertTrue(report_path.exists())


if __name__ == "__main__":
    unittest.main()
