from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path

from src.benchmark_history_engine import BENCHMARK_ARCHIVE_FIELDS, BENCHMARK_REGISTRY_FIELDS
from src.common import read_csv_rows
from src.multi_benchmark_performance_engine import run_multi_benchmark_performance_engine
from src.performance_engine import PORTFOLIO_TIMESERIES_FIELDS


class MultiBenchmarkPerformanceEngineTests(unittest.TestCase):
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

    def _write_positions_snapshot(self, path: Path) -> None:
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
                    "portfolio_date": "2026-03-31",
                    "source_name": "unit_positions",
                    "ticker": "MSFT",
                    "company_name": "Microsoft",
                    "asset_type": "STOCK",
                    "sleeve": "SINGLE_STOCK",
                    "market_value_eur": "1200",
                    "weight_total_assets_pct": "100.0",
                }
            ],
        )

    def _write_portfolio_timeseries(self, path: Path) -> None:
        self._write_csv(
            path,
            PORTFOLIO_TIMESERIES_FIELDS,
            [
                {
                    "date": "2026-01-31",
                    "portfolio_nav_eur": "1000",
                    "portfolio_value_eur": "1000",
                    "cash_value_eur": "0",
                    "net_external_cash_flow_eur": "",
                    "source_name": "unit_nav",
                    "notes": "explicit period start",
                }
            ],
        )

    def _archive_row(
        self,
        benchmark_symbol: str,
        point_date: str,
        value: str,
        benchmark_name: str | None = None,
        data_quality_flag: str = "OK",
        return_basis: str = "total_return_index",
    ) -> dict[str, str]:
        name = benchmark_name or f"{benchmark_symbol} Benchmark"
        row = {field: "" for field in BENCHMARK_ARCHIVE_FIELDS}
        row.update(
            {
                "date": point_date,
                "benchmark_name": name,
                "benchmark_symbol": benchmark_symbol,
                "currency": "EUR",
                "close": value,
                "adjusted_close": value,
                "total_return_index": value if return_basis == "total_return_index" else "",
                "benchmark_return_basis_used": return_basis,
                "benchmark_reference_value": value,
                "data_quality_flag": data_quality_flag,
                "notes": "unit benchmark archive row",
                "source_name": "unit_source",
            }
        )
        return row

    def _registry_row(
        self,
        benchmark_symbol: str,
        first_date: str,
        last_date: str,
        points_count: str,
        benchmark_name: str | None = None,
        data_quality_flag: str = "OK",
        return_basis: str = "total_return_index",
    ) -> dict[str, str]:
        name = benchmark_name or f"{benchmark_symbol} Benchmark"
        return {
            "benchmark_name": name,
            "benchmark_symbol": benchmark_symbol,
            "currency": "EUR",
            "first_date": first_date,
            "last_date": last_date,
            "points_count": points_count,
            "benchmark_return_basis_used": return_basis,
            "source_name": "unit_source",
            "data_quality_flag": data_quality_flag,
            "notes": "",
        }

    def _write_archive_and_registry(
        self,
        archive_path: Path,
        registry_path: Path,
        archive_rows: list[dict[str, str]] | None = None,
        registry_rows: list[dict[str, str]] | None = None,
    ) -> None:
        rows = archive_rows or [
            self._archive_row("WORLD", "2026-01-31", "100"),
            self._archive_row("WORLD", "2026-03-31", "110"),
            self._archive_row("EUROPE", "2026-01-31", "100"),
            self._archive_row("EUROPE", "2026-03-31", "105"),
        ]
        registry = registry_rows or [
            self._registry_row("WORLD", "2026-01-31", "2026-03-31", "2"),
            self._registry_row("EUROPE", "2026-01-31", "2026-03-31", "2"),
        ]
        self._write_csv(archive_path, BENCHMARK_ARCHIVE_FIELDS, rows)
        self._write_csv(registry_path, BENCHMARK_REGISTRY_FIELDS, registry)

    def _run_engine(
        self,
        benchmark_symbols: list[str] | None = None,
        archive_rows: list[dict[str, str]] | None = None,
        registry_rows: list[dict[str, str]] | None = None,
    ) -> tuple[Path, Path, Path, Path]:
        positions_path = self._path("_tmp_multi_benchmark_positions.csv")
        portfolio_timeseries_path = self._path("_tmp_multi_benchmark_portfolio_timeseries.csv")
        archive_path = self._path("_tmp_multi_benchmark_archive.csv")
        registry_path = self._path("_tmp_multi_benchmark_registry.csv")
        comparison_output = self._path("_tmp_multi_benchmark_comparison.csv")
        summary_output = self._path("_tmp_multi_benchmark_summary.csv")
        kpi_output = self._path("_tmp_multi_benchmark_kpis.csv")
        report_output = self._path("_tmp_multi_benchmark_report.md")
        self._write_positions_snapshot(positions_path)
        self._write_portfolio_timeseries(portfolio_timeseries_path)
        self._write_archive_and_registry(archive_path, registry_path, archive_rows, registry_rows)

        run_multi_benchmark_performance_engine(
            positions_path=str(positions_path),
            portfolio_timeseries_path=str(portfolio_timeseries_path),
            benchmark_archive_path=str(archive_path),
            benchmark_registry_path=str(registry_path),
            comparison_output=str(comparison_output),
            summary_output=str(summary_output),
            kpi_output=str(kpi_output),
            report_output=str(report_output),
            benchmark_symbols=benchmark_symbols,
        )
        return comparison_output, summary_output, kpi_output, report_output

    def test_two_benchmark_symbols_are_compared_against_same_portfolio_timeseries(self) -> None:
        comparison_output, summary_output, kpi_output, report_output = self._run_engine(["WORLD", "EUROPE"])

        comparison_rows = read_csv_rows(comparison_output)
        summary_row = read_csv_rows(summary_output)[0]
        kpi_rows = read_csv_rows(kpi_output)
        report_text = report_output.read_text(encoding="utf-8")

        self.assertEqual([row["benchmark_symbol"] for row in comparison_rows], ["EUROPE", "WORLD"])
        self.assertEqual({row["portfolio_return_period"] for row in comparison_rows}, {"20.0"})
        europe = next(row for row in comparison_rows if row["benchmark_symbol"] == "EUROPE")
        world = next(row for row in comparison_rows if row["benchmark_symbol"] == "WORLD")
        self.assertEqual(europe["benchmark_return_period"], "5.0")
        self.assertEqual(europe["relative_performance_pct"], "15.0")
        self.assertEqual(world["benchmark_return_period"], "10.0")
        self.assertEqual(world["relative_performance_pct"], "10.0")
        self.assertEqual(summary_row["benchmarks_evaluated"], "2")
        self.assertEqual(summary_row["benchmarks_restricted"], "0")
        self.assertEqual(summary_row["best_relative_benchmark_symbol"], "EUROPE")
        self.assertEqual(summary_row["weakest_relative_benchmark_symbol"], "WORLD")
        self.assertIn("# Multi-Benchmark Performance Report", report_text)
        self.assertIn("EUROPE", {row["benchmark_symbol"] for row in kpi_rows})
        self.assertIn("WORLD", {row["benchmark_symbol"] for row in kpi_rows})
        self.assertIn("relative_performance_pct", {row["metric_name"] for row in kpi_rows})

    def test_stale_approx_and_insufficient_history_benchmarks_are_marked(self) -> None:
        archive_rows = [
            self._archive_row("STALE", "2026-01-31", "100"),
            self._archive_row("STALE", "2026-03-15", "104"),
            self._archive_row("PRICE", "2026-01-31", "100", data_quality_flag="APPROX_PRICE_ONLY_BENCHMARK", return_basis="close"),
            self._archive_row("PRICE", "2026-03-31", "108", data_quality_flag="APPROX_PRICE_ONLY_BENCHMARK", return_basis="close"),
            self._archive_row("LATE", "2026-03-31", "120"),
        ]
        registry_rows = [
            self._registry_row("STALE", "2026-01-31", "2026-03-15", "2"),
            self._registry_row("PRICE", "2026-01-31", "2026-03-31", "2", data_quality_flag="APPROX_PRICE_ONLY_BENCHMARK", return_basis="close"),
            self._registry_row("LATE", "2026-03-31", "2026-03-31", "1"),
        ]

        comparison_output, summary_output, _kpi_output, report_output = self._run_engine(
            ["STALE", "PRICE", "LATE"],
            archive_rows=archive_rows,
            registry_rows=registry_rows,
        )

        comparison_rows = {row["benchmark_symbol"]: row for row in read_csv_rows(comparison_output)}
        summary_row = read_csv_rows(summary_output)[0]
        report_text = report_output.read_text(encoding="utf-8")

        self.assertIn("STALE_BENCHMARK", comparison_rows["STALE"]["data_quality_flag"])
        self.assertEqual(comparison_rows["STALE"]["benchmark_staleness_days"], "16")
        self.assertIn("APPROX_PRICE_ONLY_BENCHMARK", comparison_rows["PRICE"]["data_quality_flag"])
        self.assertIn("INSUFFICIENT_HISTORY", comparison_rows["LATE"]["data_quality_flag"])
        self.assertEqual(comparison_rows["LATE"]["relative_performance_pct"], "NOT_AVAILABLE")
        self.assertEqual(summary_row["benchmarks_restricted"], "3")
        self.assertIn("`LATE`: INSUFFICIENT_HISTORY", report_text)

    def test_multi_symbol_archive_requires_explicit_selection(self) -> None:
        with self.assertRaisesRegex(ValueError, "multiple symbols .* pass --benchmark-symbol"):
            self._run_engine()

    def test_missing_selected_symbol_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "benchmark archive contains no rows for benchmark_symbol=MISSING"):
            self._run_engine(["WORLD", "MISSING"])

    def test_duplicate_selected_symbol_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate --benchmark-symbol"):
            self._run_engine(["WORLD", "WORLD"])

    def test_single_available_symbol_can_be_used_without_explicit_selection(self) -> None:
        archive_rows = [
            self._archive_row("WORLD", "2026-01-31", "100"),
            self._archive_row("WORLD", "2026-03-31", "110"),
        ]
        registry_rows = [self._registry_row("WORLD", "2026-01-31", "2026-03-31", "2")]

        comparison_output, summary_output, _kpi_output, _report_output = self._run_engine(
            archive_rows=archive_rows,
            registry_rows=registry_rows,
        )

        self.assertEqual(read_csv_rows(comparison_output)[0]["benchmark_symbol"], "WORLD")
        self.assertEqual(read_csv_rows(summary_output)[0]["benchmarks_requested"], "1")

    def test_registry_missing_selected_symbol_is_rejected(self) -> None:
        archive_rows = [
            self._archive_row("WORLD", "2026-01-31", "100"),
            self._archive_row("WORLD", "2026-03-31", "110"),
            self._archive_row("EUROPE", "2026-01-31", "100"),
            self._archive_row("EUROPE", "2026-03-31", "105"),
        ]
        registry_rows = [self._registry_row("WORLD", "2026-01-31", "2026-03-31", "2")]

        with self.assertRaisesRegex(ValueError, "benchmark registry contains no row for benchmark_symbol=EUROPE"):
            self._run_engine(["EUROPE"], archive_rows=archive_rows, registry_rows=registry_rows)

    def test_cli_smoke_generates_multi_benchmark_artifacts(self) -> None:
        positions_path = self._path("_tmp_multi_benchmark_cli_positions.csv")
        portfolio_timeseries_path = self._path("_tmp_multi_benchmark_cli_portfolio_timeseries.csv")
        archive_path = self._path("_tmp_multi_benchmark_cli_archive.csv")
        registry_path = self._path("_tmp_multi_benchmark_cli_registry.csv")
        comparison_output = self._path("_tmp_multi_benchmark_cli_comparison.csv")
        summary_output = self._path("_tmp_multi_benchmark_cli_summary.csv")
        kpi_output = self._path("_tmp_multi_benchmark_cli_kpis.csv")
        report_output = self._path("_tmp_multi_benchmark_cli_report.md")
        self._write_positions_snapshot(positions_path)
        self._write_portfolio_timeseries(portfolio_timeseries_path)
        self._write_archive_and_registry(archive_path, registry_path)

        result = subprocess.run(
            [
                "python",
                "-m",
                "src.multi_benchmark_performance_engine",
                "--positions",
                str(positions_path),
                "--portfolio-timeseries",
                str(portfolio_timeseries_path),
                "--benchmark-archive",
                str(archive_path),
                "--benchmark-registry",
                str(registry_path),
                "--benchmark-symbol",
                "WORLD",
                "--benchmark-symbol",
                "EUROPE",
                "--comparison-output",
                str(comparison_output),
                "--summary-output",
                str(summary_output),
                "--kpi-output",
                str(kpi_output),
                "--report-output",
                str(report_output),
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row["benchmark_symbol"] for row in read_csv_rows(comparison_output)], ["EUROPE", "WORLD"])
        self.assertEqual(len(read_csv_rows(kpi_output)), 8)
        self.assertIn("# Multi-Benchmark Performance Report", report_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
