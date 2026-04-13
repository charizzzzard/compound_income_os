from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.performance_engine import PARTIAL_HISTORY, SIMPLE_PERIOD_RETURN, run_performance_engine
from src.portfolio_history_engine import ARCHIVE_FIELDS, PORTFOLIO_TIMESERIES_FIELDS, run_portfolio_history_engine


class PortfolioHistoryEngineTests(unittest.TestCase):
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

    def _write_positions_snapshot(
        self,
        path: Path,
        portfolio_date: str,
        stock_value: str = "1000",
        cash_value: str = "200",
    ) -> None:
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
                    "source_name": "unit_positions",
                    "ticker": "MSFT",
                    "company_name": "Microsoft",
                    "asset_type": "STOCK",
                    "sleeve": "SINGLE_STOCK",
                    "market_value_eur": stock_value,
                    "weight_total_assets_pct": "83.33",
                },
                {
                    "portfolio_date": portfolio_date,
                    "source_name": "unit_positions",
                    "ticker": "EUR-CASH",
                    "company_name": "Cash",
                    "asset_type": "CASH",
                    "sleeve": "CASH",
                    "market_value_eur": cash_value,
                    "weight_total_assets_pct": "16.67",
                },
            ],
        )

    def _write_benchmark_csv(self, path: Path) -> None:
        self._write_csv(
            path,
            ["date", "benchmark_name", "benchmark_symbol", "currency", "close", "adjusted_close", "total_return_index", "dividend", "source_name"],
            [
                {
                    "date": "2026-01-31",
                    "benchmark_name": "Unit Benchmark",
                    "benchmark_symbol": "UTB",
                    "currency": "EUR",
                    "close": "100",
                    "adjusted_close": "100",
                    "total_return_index": "100",
                    "dividend": "0",
                    "source_name": "unit_fixture",
                },
                {
                    "date": "2026-02-28",
                    "benchmark_name": "Unit Benchmark",
                    "benchmark_symbol": "UTB",
                    "currency": "EUR",
                    "close": "110",
                    "adjusted_close": "110",
                    "total_return_index": "110",
                    "dividend": "0",
                    "source_name": "unit_fixture",
                },
            ],
        )

    def _write_benchmark_config(self, path: Path) -> None:
        path.write_text(
            """{
  "benchmark_name": "Unit Benchmark",
  "benchmark_symbol": "UTB",
  "benchmark_currency": "EUR",
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
}""",
            encoding="utf-8",
        )

    def test_first_snapshot_creates_archive_and_timeseries(self) -> None:
        positions_path = self._path("_tmp_history_positions_first.csv")
        archive_path = self._path("_tmp_portfolio_snapshot_archive_first.csv")
        timeseries_path = self._path("_tmp_portfolio_timeseries_first.csv")

        self._write_positions_snapshot(positions_path, "2026-01-31", stock_value="1000", cash_value="200")

        outputs = run_portfolio_history_engine(
            positions_path=str(positions_path),
            archive_path=str(archive_path),
            archive_output=str(archive_path),
            timeseries_output=str(timeseries_path),
        )

        self.assertTrue(outputs["archive_output"].exists())
        self.assertTrue(outputs["timeseries_output"].exists())
        archive_rows = read_csv_rows(archive_path)
        timeseries_rows = read_csv_rows(timeseries_path)
        self.assertEqual(len(archive_rows), 1)
        self.assertEqual(archive_rows[0]["as_of_date"], "2026-01-31")
        self.assertEqual(archive_rows[0]["portfolio_value_eur"], "1000.0")
        self.assertEqual(archive_rows[0]["cash_value_eur"], "200.0")
        self.assertEqual(archive_rows[0]["portfolio_nav_eur"], "1200.0")
        self.assertEqual(archive_rows[0]["history_source_type"], "positions_snapshot")
        self.assertEqual(timeseries_rows[0]["date"], "2026-01-31")
        self.assertEqual(timeseries_rows[0]["net_external_cash_flow_eur"], "")

    def test_second_snapshot_extends_archive_without_invented_points(self) -> None:
        first_positions = self._path("_tmp_history_positions_first_extend.csv")
        second_positions = self._path("_tmp_history_positions_second_extend.csv")
        archive_path = self._path("_tmp_portfolio_snapshot_archive_extend.csv")
        timeseries_path = self._path("_tmp_portfolio_timeseries_extend.csv")

        self._write_positions_snapshot(first_positions, "2026-01-31", stock_value="1000", cash_value="200")
        self._write_positions_snapshot(second_positions, "2026-02-28", stock_value="1100", cash_value="250")

        run_portfolio_history_engine(str(first_positions), archive_path=str(archive_path), archive_output=str(archive_path), timeseries_output=str(timeseries_path))
        run_portfolio_history_engine(str(second_positions), archive_path=str(archive_path), archive_output=str(archive_path), timeseries_output=str(timeseries_path))

        archive_rows = read_csv_rows(archive_path)
        timeseries_rows = read_csv_rows(timeseries_path)
        self.assertEqual([row["as_of_date"] for row in archive_rows], ["2026-01-31", "2026-02-28"])
        self.assertEqual([row["date"] for row in timeseries_rows], ["2026-01-31", "2026-02-28"])
        self.assertTrue(all(row["net_external_cash_flow_eur"] == "" for row in timeseries_rows))

    def test_duplicate_date_conflict_is_rejected(self) -> None:
        positions_path = self._path("_tmp_history_positions_duplicate.csv")
        archive_path = self._path("_tmp_portfolio_snapshot_archive_duplicate.csv")
        timeseries_path = self._path("_tmp_portfolio_timeseries_duplicate.csv")

        self._write_positions_snapshot(positions_path, "2026-01-31", stock_value="1000", cash_value="200")
        self._write_csv(
            archive_path,
            ARCHIVE_FIELDS,
            [
                {
                    "as_of_date": "2026-01-31",
                    "portfolio_nav_eur": "999",
                    "portfolio_value_eur": "800",
                    "cash_value_eur": "199",
                    "source_name": "manual_archive",
                    "history_source_type": "positions_snapshot",
                    "notes": "conflict",
                }
            ],
        )

        with self.assertRaisesRegex(ValueError, "conflicting point for as_of_date=2026-01-31"):
            run_portfolio_history_engine(str(positions_path), archive_path=str(archive_path), archive_output=str(archive_path), timeseries_output=str(timeseries_path))

    def test_identical_duplicate_date_is_idempotent(self) -> None:
        positions_path = self._path("_tmp_history_positions_idempotent.csv")
        archive_path = self._path("_tmp_portfolio_snapshot_archive_idempotent.csv")
        timeseries_path = self._path("_tmp_portfolio_timeseries_idempotent.csv")

        self._write_positions_snapshot(positions_path, "2026-01-31", stock_value="1000", cash_value="200")

        run_portfolio_history_engine(str(positions_path), archive_path=str(archive_path), archive_output=str(archive_path), timeseries_output=str(timeseries_path))
        run_portfolio_history_engine(str(positions_path), archive_path=str(archive_path), archive_output=str(archive_path), timeseries_output=str(timeseries_path))

        self.assertEqual(len(read_csv_rows(archive_path)), 1)
        self.assertEqual(len(read_csv_rows(timeseries_path)), 1)

    def test_missing_required_snapshot_columns_fail_fast(self) -> None:
        positions_path = self._path("_tmp_history_positions_missing_columns.csv")
        archive_path = self._path("_tmp_portfolio_snapshot_archive_missing_columns.csv")
        timeseries_path = self._path("_tmp_portfolio_timeseries_missing_columns.csv")

        self._write_csv(
            positions_path,
            ["portfolio_date", "ticker", "asset_type", "sleeve", "market_value_eur"],
            [{"portfolio_date": "2026-01-31", "ticker": "MSFT", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "1000"}],
        )

        with self.assertRaisesRegex(ValueError, "source_name"):
            run_portfolio_history_engine(str(positions_path), archive_path=str(archive_path), archive_output=str(archive_path), timeseries_output=str(timeseries_path))

    def test_generated_timeseries_is_compatible_with_performance_engine(self) -> None:
        first_positions = self._path("_tmp_history_positions_perf_first.csv")
        latest_positions = self._path("_tmp_history_positions_perf_latest.csv")
        archive_path = self._path("_tmp_portfolio_snapshot_archive_perf.csv")
        timeseries_path = self._path("_tmp_portfolio_timeseries_perf.csv")
        benchmark_path = self._path("_tmp_history_benchmark.csv")
        config_path = self._path("_tmp_history_benchmark_config.yaml")
        comparison_path = self._path("_tmp_history_performance_comparison.csv")
        kpi_path = self._path("_tmp_history_performance_kpis.csv")
        summary_path = self._path("_tmp_history_performance_summary.csv")
        normalized_benchmark_path = self._path("_tmp_history_benchmark_normalized.csv")
        performance_timeseries_path = self._path("_tmp_history_performance_timeseries_out.csv")
        report_path = self._path("_tmp_history_performance_report.md")

        self._write_positions_snapshot(first_positions, "2026-01-31", stock_value="1000", cash_value="200")
        self._write_positions_snapshot(latest_positions, "2026-02-28", stock_value="1100", cash_value="250")
        self._write_benchmark_csv(benchmark_path)
        self._write_benchmark_config(config_path)

        run_portfolio_history_engine(str(first_positions), archive_path=str(archive_path), archive_output=str(archive_path), timeseries_output=str(timeseries_path))
        run_portfolio_history_engine(str(latest_positions), archive_path=str(archive_path), archive_output=str(archive_path), timeseries_output=str(timeseries_path))
        run_performance_engine(
            positions_path=str(latest_positions),
            benchmark_path=str(benchmark_path),
            benchmark_config_path=str(config_path),
            portfolio_timeseries_path=str(timeseries_path),
            comparison_output=str(comparison_path),
            kpi_output=str(kpi_path),
            summary_output=str(summary_path),
            normalized_benchmark_output=str(normalized_benchmark_path),
            portfolio_timeseries_output=str(performance_timeseries_path),
            report_output=str(report_path),
        )

        summary_row = read_csv_rows(summary_path)[0]
        comparison_row = read_csv_rows(comparison_path)[0]
        self.assertEqual(summary_row["portfolio_timeseries_points"], "2")
        self.assertEqual(summary_row["measurement_mode"], PARTIAL_HISTORY)
        self.assertEqual(comparison_row["method_used"], SIMPLE_PERIOD_RETURN)

    def test_cli_smoke_generates_archive_timeseries_summary_and_report(self) -> None:
        positions_path = self._path("_tmp_history_positions_cli.csv")
        archive_path = self._path("_tmp_portfolio_snapshot_archive_cli.csv")
        timeseries_path = self._path("_tmp_portfolio_timeseries_cli.csv")
        summary_path = self._path("_tmp_portfolio_history_summary_cli.csv")
        report_path = self._path("_tmp_portfolio_history_report_cli.md")

        self._write_positions_snapshot(positions_path, "2026-01-31", stock_value="1000", cash_value="200")

        result = subprocess.run(
            [
                "python",
                "-m",
                "src.portfolio_history_engine",
                "--positions",
                str(positions_path),
                "--archive",
                str(archive_path),
                "--archive-output",
                str(archive_path),
                "--timeseries-output",
                str(timeseries_path),
                "--summary-output",
                str(summary_path),
                "--report-output",
                str(report_path),
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, msg=f"{result.stdout}\n{result.stderr}")
        self.assertEqual(list(read_csv_rows(archive_path)[0].keys()), ARCHIVE_FIELDS)
        self.assertEqual(list(read_csv_rows(timeseries_path)[0].keys()), PORTFOLIO_TIMESERIES_FIELDS)
        self.assertEqual(read_csv_rows(summary_path)[0]["measurement_readiness"], "SNAPSHOT_ONLY")
        self.assertIn("# Portfolio History Report", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
