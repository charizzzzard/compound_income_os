from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path

from src.benchmark_history_engine import BENCHMARK_ARCHIVE_FIELDS, run_benchmark_history_engine
from src.common import read_csv_rows
from src.performance_engine import BENCHMARK_NORMALIZED_FIELDS, run_performance_engine


class BenchmarkHistoryEngineTests(unittest.TestCase):
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

    def _write_config(
        self,
        path: Path,
        benchmark_name: str = "Unit Benchmark",
        benchmark_symbol: str = "UTB",
        source_name: str = "unit_source",
    ) -> None:
        path.write_text(
            """{
  "benchmark_name": "%s",
  "benchmark_symbol": "%s",
  "benchmark_currency": "EUR",
  "portfolio_reference_currency": "EUR",
  "frequency": "monthly",
  "date_column": "date",
  "close_column": "close",
  "adjusted_close_column": "adjusted_close",
  "total_return_index_column": "total_return_index",
  "source_name": "%s",
  "return_basis_priority": ["total_return_index", "adjusted_close", "close"],
  "data_quality_policy": {
    "price_only_flag": "APPROX_PRICE_ONLY_BENCHMARK",
    "currency_mismatch_flag": "CURRENCY_MISMATCH",
    "duplicate_date_policy": "raise_error",
    "missing_required_field_policy": "raise_error"
  }
}"""
            % (benchmark_name, benchmark_symbol, source_name),
            encoding="utf-8",
        )

    def _benchmark_row(
        self,
        point_date: str,
        value: str,
        benchmark_name: str = "Unit Benchmark",
        benchmark_symbol: str = "UTB",
        source_name: str = "unit_source",
        notes: str | None = None,
    ) -> dict[str, object]:
        row = {
            "date": point_date,
            "benchmark_name": benchmark_name,
            "benchmark_symbol": benchmark_symbol,
            "currency": "EUR",
            "close": value,
            "adjusted_close": value,
            "total_return_index": value,
            "dividend": "0.0",
            "source_name": source_name,
        }
        if notes is not None:
            row["notes"] = notes
        return row

    def _write_benchmark(self, path: Path, rows: list[dict[str, object]]) -> None:
        fieldnames = [
            "date",
            "benchmark_name",
            "benchmark_symbol",
            "currency",
            "close",
            "adjusted_close",
            "total_return_index",
            "dividend",
            "source_name",
            "notes",
        ]
        self._write_csv(path, fieldnames, rows)

    def _run_archive(
        self,
        benchmark_input: Path | None,
        config_path: Path,
        archive_path: Path,
        normalized_output: Path | None = None,
        registry_output: Path | None = None,
        archive_summary_output: Path | None = None,
        report_output: Path | None = None,
        benchmark_symbol: str | None = None,
    ) -> None:
        run_benchmark_history_engine(
            benchmark_input=str(benchmark_input) if benchmark_input else None,
            benchmark_config_path=str(config_path),
            archive_path=str(archive_path),
            archive_output=str(archive_path),
            normalized_output=str(normalized_output or self._path("_tmp_benchmark_history_normalized.csv")),
            registry_output=str(registry_output or self._path("_tmp_benchmark_history_registry.csv")),
            archive_summary_output=str(archive_summary_output) if archive_summary_output else None,
            report_output=str(report_output) if report_output else None,
            benchmark_symbol=benchmark_symbol,
        )

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
                    "portfolio_date": "2026-02-28",
                    "source_name": "unit_positions",
                    "ticker": "MSFT",
                    "company_name": "Microsoft",
                    "asset_type": "STOCK",
                    "sleeve": "SINGLE_STOCK",
                    "market_value_eur": "1000",
                    "weight_total_assets_pct": "100.0",
                }
            ],
        )

    def test_first_run_creates_archive_registry_and_normalized_output(self) -> None:
        benchmark_path = self._path("_tmp_benchmark_history_first_input.csv")
        config_path = self._path("_tmp_benchmark_history_first_config.yaml")
        archive_path = self._path("_tmp_benchmark_history_first_archive.csv")
        normalized_output = self._path("_tmp_benchmark_history_first_normalized.csv")
        registry_output = self._path("_tmp_benchmark_history_first_registry.csv")
        archive_summary_output = self._path("_tmp_benchmark_history_first_summary.csv")
        report_output = self._path("_tmp_benchmark_history_first_report.md")
        self._write_config(config_path)
        self._write_benchmark(
            benchmark_path,
            [self._benchmark_row("2026-01-31", "100"), self._benchmark_row("2026-02-28", "105")],
        )

        self._run_archive(
            benchmark_path,
            config_path,
            archive_path,
            normalized_output,
            registry_output,
            archive_summary_output,
            report_output,
        )

        archive_rows = read_csv_rows(archive_path)
        registry_rows = read_csv_rows(registry_output)
        normalized_rows = read_csv_rows(normalized_output)
        self.assertEqual(len(archive_rows), 2)
        self.assertEqual(len(registry_rows), 1)
        self.assertEqual(len(normalized_rows), 2)
        self.assertEqual(list(normalized_rows[0].keys()), BENCHMARK_NORMALIZED_FIELDS)
        self.assertEqual(registry_rows[0]["benchmark_symbol"], "UTB")
        self.assertEqual(registry_rows[0]["first_date"], "2026-01-31")
        self.assertEqual(registry_rows[0]["last_date"], "2026-02-28")
        self.assertEqual(registry_rows[0]["points_count"], "2")
        self.assertEqual(read_csv_rows(archive_summary_output)[0]["new_rows_added"], "2")
        self.assertIn("# Benchmark History Report", report_output.read_text(encoding="utf-8"))

    def test_identical_repetition_is_idempotent(self) -> None:
        benchmark_path = self._path("_tmp_benchmark_history_idempotent_input.csv")
        config_path = self._path("_tmp_benchmark_history_idempotent_config.yaml")
        archive_path = self._path("_tmp_benchmark_history_idempotent_archive.csv")
        archive_summary_output = self._path("_tmp_benchmark_history_idempotent_summary.csv")
        self._write_config(config_path)
        self._write_benchmark(
            benchmark_path,
            [self._benchmark_row("2026-01-31", "100"), self._benchmark_row("2026-02-28", "105")],
        )

        for _ in range(2):
            self._run_archive(
                benchmark_path,
                config_path,
                archive_path,
                archive_summary_output=archive_summary_output,
            )

        self.assertEqual(len(read_csv_rows(archive_path)), 2)
        summary_row = read_csv_rows(archive_summary_output)[0]
        self.assertEqual(summary_row["new_rows_added"], "0")
        self.assertEqual(summary_row["duplicate_rows_skipped"], "2")

    def test_second_run_with_new_date_extends_archive(self) -> None:
        first_input = self._path("_tmp_benchmark_history_extend_first.csv")
        second_input = self._path("_tmp_benchmark_history_extend_second.csv")
        config_path = self._path("_tmp_benchmark_history_extend_config.yaml")
        archive_path = self._path("_tmp_benchmark_history_extend_archive.csv")
        registry_output = self._path("_tmp_benchmark_history_extend_registry.csv")
        self._write_config(config_path)
        self._write_benchmark(first_input, [self._benchmark_row("2026-01-31", "100")])
        self._write_benchmark(second_input, [self._benchmark_row("2026-02-28", "105")])

        self._run_archive(first_input, config_path, archive_path, registry_output=registry_output)
        self._run_archive(second_input, config_path, archive_path, registry_output=registry_output)

        archive_rows = read_csv_rows(archive_path)
        registry_row = read_csv_rows(registry_output)[0]
        self.assertEqual([row["date"] for row in archive_rows], ["2026-01-31", "2026-02-28"])
        self.assertEqual(registry_row["points_count"], "2")
        self.assertEqual(registry_row["last_date"], "2026-02-28")

    def test_conflict_on_same_symbol_and_date_fails_fast(self) -> None:
        first_input = self._path("_tmp_benchmark_history_conflict_first.csv")
        conflict_input = self._path("_tmp_benchmark_history_conflict_second.csv")
        config_path = self._path("_tmp_benchmark_history_conflict_config.yaml")
        archive_path = self._path("_tmp_benchmark_history_conflict_archive.csv")
        self._write_config(config_path)
        self._write_benchmark(first_input, [self._benchmark_row("2026-01-31", "100")])
        self._write_benchmark(conflict_input, [self._benchmark_row("2026-01-31", "101")])

        self._run_archive(first_input, config_path, archive_path)
        with self.assertRaisesRegex(ValueError, "benchmark_symbol=UTB, date=2026-01-31"):
            self._run_archive(conflict_input, config_path, archive_path)

    def test_multiple_symbols_can_coexist_and_registry_aggregates_each_symbol(self) -> None:
        first_input = self._path("_tmp_benchmark_history_multi_first.csv")
        second_input = self._path("_tmp_benchmark_history_multi_second.csv")
        first_config = self._path("_tmp_benchmark_history_multi_first_config.yaml")
        second_config = self._path("_tmp_benchmark_history_multi_second_config.yaml")
        archive_path = self._path("_tmp_benchmark_history_multi_archive.csv")
        normalized_output = self._path("_tmp_benchmark_history_multi_normalized.csv")
        registry_output = self._path("_tmp_benchmark_history_multi_registry.csv")
        self._write_config(first_config, benchmark_name="Unit Benchmark", benchmark_symbol="UTB", source_name="unit_source")
        self._write_config(second_config, benchmark_name="Alt Benchmark", benchmark_symbol="ALT", source_name="alt_source")
        self._write_benchmark(first_input, [self._benchmark_row("2026-01-31", "100", benchmark_symbol="UTB")])
        self._write_benchmark(second_input, [self._benchmark_row("2026-01-31", "200", benchmark_name="Alt Benchmark", benchmark_symbol="ALT", source_name="alt_source")])

        self._run_archive(first_input, first_config, archive_path, registry_output=registry_output)
        self._run_archive(second_input, second_config, archive_path, normalized_output=normalized_output, registry_output=registry_output, benchmark_symbol="ALT")

        archive_rows = read_csv_rows(archive_path)
        registry_rows = read_csv_rows(registry_output)
        normalized_rows = read_csv_rows(normalized_output)
        self.assertEqual([row["benchmark_symbol"] for row in archive_rows], ["ALT", "UTB"])
        self.assertEqual([row["benchmark_symbol"] for row in registry_rows], ["ALT", "UTB"])
        self.assertEqual({row["points_count"] for row in registry_rows}, {"1"})
        self.assertEqual({row["benchmark_symbol"] for row in normalized_rows}, {"ALT"})

    def test_multi_symbol_archive_requires_explicit_normalized_output_selection(self) -> None:
        archive_path = self._path("_tmp_benchmark_history_multi_select_archive.csv")
        config_path = self._path("_tmp_benchmark_history_multi_select_config.yaml")
        self._write_config(config_path)
        self._write_csv(
            archive_path,
            BENCHMARK_ARCHIVE_FIELDS,
            [
                {**self._archive_row("UTB", "2026-01-31", "100"), "source_name": "unit_source"},
                {**self._archive_row("ALT", "2026-01-31", "200", benchmark_name="Alt Benchmark"), "source_name": "alt_source"},
            ],
        )

        with self.assertRaisesRegex(ValueError, "contains multiple symbols .* pass --benchmark-symbol"):
            self._run_archive(None, config_path, archive_path)

    def test_normalized_output_is_compatible_with_performance_engine(self) -> None:
        benchmark_path = self._path("_tmp_benchmark_history_perf_input.csv")
        config_path = self._path("_tmp_benchmark_history_perf_config.yaml")
        archive_path = self._path("_tmp_benchmark_history_perf_archive.csv")
        normalized_output = self._path("_tmp_benchmark_history_perf_normalized.csv")
        positions_path = self._path("_tmp_benchmark_history_perf_positions.csv")
        portfolio_timeseries_path = self._path("_tmp_benchmark_history_perf_portfolio_timeseries.csv")
        comparison_output = self._path("_tmp_benchmark_history_perf_comparison.csv")
        kpi_output = self._path("_tmp_benchmark_history_perf_kpis.csv")
        report_output = self._path("_tmp_benchmark_history_perf_report.md")
        self._write_config(config_path)
        self._write_benchmark(
            benchmark_path,
            [self._benchmark_row("2026-01-31", "100"), self._benchmark_row("2026-02-28", "105")],
        )
        self._write_positions_snapshot(positions_path)
        self._write_csv(
            portfolio_timeseries_path,
            ["date", "portfolio_nav_eur", "portfolio_value_eur", "cash_value_eur", "source_name", "notes"],
            [
                {
                    "date": "2026-01-31",
                    "portfolio_nav_eur": "1000",
                    "portfolio_value_eur": "1000",
                    "cash_value_eur": "0",
                    "source_name": "unit_nav",
                    "notes": "explicit period start",
                }
            ],
        )

        self._run_archive(benchmark_path, config_path, archive_path, normalized_output=normalized_output)
        run_performance_engine(
            positions_path=str(positions_path),
            benchmark_path=str(normalized_output),
            benchmark_config_path=str(config_path),
            portfolio_timeseries_path=str(portfolio_timeseries_path),
            comparison_output=str(comparison_output),
            kpi_output=str(kpi_output),
            report_output=str(report_output),
        )

        self.assertEqual(read_csv_rows(comparison_output)[0]["benchmark_return_period"], "5.0")
        self.assertIn("# Performance Report", report_output.read_text(encoding="utf-8"))

    def test_missing_required_input_column_is_rejected(self) -> None:
        benchmark_path = self._path("_tmp_benchmark_history_missing_input.csv")
        config_path = self._path("_tmp_benchmark_history_missing_input_config.yaml")
        archive_path = self._path("_tmp_benchmark_history_missing_input_archive.csv")
        self._write_config(config_path)
        self._write_csv(benchmark_path, ["date", "benchmark_symbol"], [{"date": "2026-01-31", "benchmark_symbol": "UTB"}])

        with self.assertRaisesRegex(ValueError, "benchmark timeseries missing required columns: close"):
            self._run_archive(benchmark_path, config_path, archive_path)

    def test_missing_required_config_symbol_is_rejected(self) -> None:
        benchmark_path = self._path("_tmp_benchmark_history_missing_config.csv")
        config_path = self._path("_tmp_benchmark_history_missing_config.yaml")
        archive_path = self._path("_tmp_benchmark_history_missing_config_archive.csv")
        config_path.write_text(
            """{
  "benchmark_name": "Unit Benchmark",
  "benchmark_currency": "EUR",
  "date_column": "date",
  "close_column": "close",
  "adjusted_close_column": "adjusted_close",
  "total_return_index_column": "total_return_index",
  "source_name": "unit_source",
  "return_basis_priority": ["total_return_index", "adjusted_close", "close"],
  "data_quality_policy": {
    "price_only_flag": "APPROX_PRICE_ONLY_BENCHMARK",
    "currency_mismatch_flag": "CURRENCY_MISMATCH"
  }
}""",
            encoding="utf-8",
        )
        self._write_benchmark(
            benchmark_path,
            [
                {
                    "date": "2026-01-31",
                    "benchmark_name": "",
                    "benchmark_symbol": "",
                    "currency": "EUR",
                    "close": "100",
                    "adjusted_close": "100",
                    "total_return_index": "100",
                    "dividend": "0.0",
                    "source_name": "unit_source",
                    "notes": "",
                }
            ],
        )

        with self.assertRaisesRegex(ValueError, "blank required field\\(s\\): benchmark_symbol"):
            self._run_archive(benchmark_path, config_path, archive_path)

    def test_symbol_metadata_drift_is_rejected(self) -> None:
        first_input = self._path("_tmp_benchmark_history_metadata_first.csv")
        second_input = self._path("_tmp_benchmark_history_metadata_second.csv")
        first_config = self._path("_tmp_benchmark_history_metadata_first_config.yaml")
        second_config = self._path("_tmp_benchmark_history_metadata_second_config.yaml")
        archive_path = self._path("_tmp_benchmark_history_metadata_archive.csv")
        self._write_config(first_config, benchmark_name="Unit Benchmark", benchmark_symbol="UTB")
        self._write_config(second_config, benchmark_name="Renamed Benchmark", benchmark_symbol="UTB")
        self._write_benchmark(first_input, [self._benchmark_row("2026-01-31", "100", benchmark_name="Unit Benchmark")])
        self._write_benchmark(second_input, [self._benchmark_row("2026-02-28", "105", benchmark_name="Renamed Benchmark")])

        self._run_archive(first_input, first_config, archive_path)
        with self.assertRaisesRegex(ValueError, "conflicting benchmark_name for benchmark_symbol=UTB"):
            self._run_archive(second_input, second_config, archive_path)

    def test_multiple_source_names_are_visible_in_registry_notes(self) -> None:
        first_input = self._path("_tmp_benchmark_history_sources_first.csv")
        second_input = self._path("_tmp_benchmark_history_sources_second.csv")
        first_config = self._path("_tmp_benchmark_history_sources_first_config.yaml")
        second_config = self._path("_tmp_benchmark_history_sources_second_config.yaml")
        archive_path = self._path("_tmp_benchmark_history_sources_archive.csv")
        registry_output = self._path("_tmp_benchmark_history_sources_registry.csv")
        self._write_config(first_config, benchmark_symbol="UTB", source_name="provider_a")
        self._write_config(second_config, benchmark_symbol="UTB", source_name="provider_b")
        self._write_benchmark(first_input, [self._benchmark_row("2026-01-31", "100", source_name="provider_a")])
        self._write_benchmark(second_input, [self._benchmark_row("2026-02-28", "105", source_name="provider_b")])

        self._run_archive(first_input, first_config, archive_path, registry_output=registry_output)
        self._run_archive(second_input, second_config, archive_path, registry_output=registry_output)

        registry_row = read_csv_rows(registry_output)[0]
        self.assertEqual(registry_row["source_name"], "MULTIPLE_SOURCES")
        self.assertIn("provider_a", registry_row["notes"])
        self.assertIn("provider_b", registry_row["notes"])

    def test_cli_smoke_builds_archive_registry_and_normalized_output(self) -> None:
        benchmark_path = self._path("_tmp_benchmark_history_cli_input.csv")
        config_path = self._path("_tmp_benchmark_history_cli_config.yaml")
        archive_path = self._path("_tmp_benchmark_history_cli_archive.csv")
        normalized_output = self._path("_tmp_benchmark_history_cli_normalized.csv")
        registry_output = self._path("_tmp_benchmark_history_cli_registry.csv")
        archive_summary_output = self._path("_tmp_benchmark_history_cli_summary.csv")
        report_output = self._path("_tmp_benchmark_history_cli_report.md")
        self._write_config(config_path)
        self._write_benchmark(benchmark_path, [self._benchmark_row("2026-01-31", "100")])

        result = subprocess.run(
            [
                "python",
                "-m",
                "src.benchmark_history_engine",
                "--benchmark-input",
                str(benchmark_path),
                "--benchmark-config",
                str(config_path),
                "--archive",
                str(archive_path),
                "--archive-output",
                str(archive_path),
                "--normalized-output",
                str(normalized_output),
                "--registry-output",
                str(registry_output),
                "--archive-summary-output",
                str(archive_summary_output),
                "--report-output",
                str(report_output),
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(read_csv_rows(archive_path)), 1)
        self.assertEqual(len(read_csv_rows(registry_output)), 1)
        self.assertEqual(list(read_csv_rows(normalized_output)[0].keys()), BENCHMARK_NORMALIZED_FIELDS)
        self.assertEqual(read_csv_rows(archive_summary_output)[0]["selected_benchmark_symbol"], "UTB")
        self.assertIn("# Benchmark History Report", report_output.read_text(encoding="utf-8"))

    def _archive_row(
        self,
        benchmark_symbol: str,
        point_date: str,
        value: str,
        benchmark_name: str = "Unit Benchmark",
    ) -> dict[str, str]:
        row = {field: "" for field in BENCHMARK_ARCHIVE_FIELDS}
        row.update(
            {
                "date": point_date,
                "benchmark_name": benchmark_name,
                "benchmark_symbol": benchmark_symbol,
                "currency": "EUR",
                "close": value,
                "adjusted_close": value,
                "total_return_index": value,
                "benchmark_return_basis_used": "total_return_index",
                "benchmark_reference_value": value,
                "data_quality_flag": "OK",
                "notes": "",
                "source_name": "unit_source",
            }
        )
        return row


if __name__ == "__main__":
    unittest.main()
