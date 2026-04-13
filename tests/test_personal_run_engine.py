from __future__ import annotations

import csv
import json
import subprocess
import unittest
from pathlib import Path

from src.benchmark_history_engine import BENCHMARK_ARCHIVE_FIELDS, BENCHMARK_REGISTRY_FIELDS
from src.common import read_csv_rows
from src.personal_run_engine import PersonalRunOptions, run_personal_run_engine


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
        return PersonalRunOptions(
            stages=stages,
            positions_output=str(self._path(f"_tmp_{prefix}_positions.csv")),
            fundamentals_master=str(self._path(f"_tmp_{prefix}_personal_master.csv")),
            scores_output=str(self._path(f"_tmp_{prefix}_scores.csv")),
            score_audit_output=str(self._path(f"_tmp_{prefix}_score_audit.csv")),
            coverage_output=str(self._path(f"_tmp_{prefix}_coverage.csv")),
            fundamentals_enriched_output=str(self._path(f"_tmp_{prefix}_enriched.csv")),
            fundamentals_coverage_report_output=str(self._path(f"_tmp_{prefix}_coverage_report.md")),
            watchlist_output=str(self._path(f"_tmp_{prefix}_watchlist_ranked.csv")),
            watchlist_report_output=str(self._path(f"_tmp_{prefix}_watchlist_report.md")),
            monthly_ranking_output=str(self._path(f"_tmp_{prefix}_monthly_ranking.csv")),
            rebalance_output=str(self._path(f"_tmp_{prefix}_rebalance.csv")),
            monthly_report_output=str(self._path(f"_tmp_{prefix}_monthly_report.md")),
            portfolio_review_output=str(self._path(f"_tmp_{prefix}_portfolio_review.md")),
            holdings_output=str(self._path(f"_tmp_{prefix}_holdings.csv")),
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
            dashboard_report_output=str(self._path(f"_tmp_{prefix}_dashboard_report.md")),
            manifest_output=str(self._path(f"_tmp_{prefix}_manifest.json")),
            artifacts_output=str(self._path(f"_tmp_{prefix}_artifacts.csv")),
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
            ["import", "fundamentals_seed", "scoring", "coverage", "watchlist", "monthly", "portfolio_review"],
        )
        self.assertEqual({row["stage_name"] for row in artifact_rows if row["produced"] == "True"}, set(manifest_on_disk["executed_stage_order"]))
        self.assertTrue(Path(options.holdings_output).exists())
        self.assertIn("Personal Run Report", Path(options.report_output).read_text(encoding="utf-8"))
        statuses = {row["stage_name"]: row["status"] for row in manifest_on_disk["stage_results"]}
        self.assertEqual(statuses["cost_tax"], "NOT_REQUESTED")
        self.assertEqual(statuses["scoring"], "SUCCESS")

    def test_history_and_performance_run_uses_existing_single_benchmark_method(self) -> None:
        options = self._core_options("history_perf", ["import", "history", "performance"])
        options.performance_benchmark = "data/raw/sample_benchmark_timeseries.csv"

        manifest = run_personal_run_engine(options)

        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(manifest["measurement_modes"]["performance"], "SNAPSHOT_ONLY")
        self.assertTrue(Path(options.portfolio_timeseries_output).exists())
        self.assertTrue(Path(options.performance_kpi_output).exists())
        self.assertIn("performance", manifest["data_quality_flags"])

    def test_cost_tax_run_works_through_orchestrator(self) -> None:
        options = self._base_options("cost_tax", ["cost_tax"])
        options.ledger = "data/raw/sample_cost_tax_ledger.csv"

        manifest = run_personal_run_engine(options)

        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(manifest["measurement_modes"]["cost_tax"], "FULL_LEDGER")
        self.assertTrue(Path(options.cost_tax_kpi_output).exists())
        self.assertTrue(Path(options.cost_tax_archive).exists())

    def test_dashboard_run_works_when_core_upstream_artifacts_exist(self) -> None:
        options = self._core_options(
            "dashboard",
            ["import", "fundamentals_seed", "scoring", "coverage", "watchlist", "monthly", "portfolio_review", "dashboard"],
        )

        manifest = run_personal_run_engine(options)

        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertTrue(Path(options.dashboard_kpi_output).exists())
        self.assertIn("dashboard", manifest["data_quality_flags"])

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
        self.assertEqual(artifact_rows, [])

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
                "--report-output",
                str(options.report_output),
            ]
        )

        result = subprocess.run(command, cwd=Path.cwd(), capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(Path(options.manifest_output).read_text(encoding="utf-8"))
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertTrue(Path(options.artifacts_output).exists())
        self.assertTrue(Path(options.report_output).exists())


if __name__ == "__main__":
    unittest.main()
