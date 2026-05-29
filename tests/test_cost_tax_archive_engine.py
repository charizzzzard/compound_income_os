from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from src.common import read_csv_rows
from src.cost_tax_archive_engine import run_cost_tax_archive_engine
from src.cost_tax_engine import DOCUMENT_SUMMARY_ONLY, FULL_LEDGER, NORMALIZED_LEDGER_FIELDS, PARTIAL_LEDGER


class CostTaxArchiveEngineTests(unittest.TestCase):
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

    def _ledger_row(
        self,
        reference_id: str,
        event_date: str = "2026-04-10",
        event_type: str = "BUY",
        ticker: str = "AAPL",
        isin: str = "US0378331005",
        gross_amount: str = "100.00",
        net_amount: str = "-101.00",
        fee_amount: str = "1.00",
        tax_amount: str = "",
        withholding_tax_amount: str = "",
        record_granularity: str = "EVENT",
        verification_status: str = "VERIFIED",
        data_quality_flag: str = "OK",
    ) -> dict[str, str]:
        row = {field: "" for field in NORMALIZED_LEDGER_FIELDS}
        row.update(
            {
                "event_date": event_date,
                "broker": "TRADE_REPUBLIC",
                "document_type": "MANUAL_LEDGER",
                "record_granularity": record_granularity,
                "event_type": event_type,
                "instrument_name": f"{ticker} Holding",
                "ticker": ticker,
                "isin": isin,
                "currency": "EUR",
                "gross_amount": gross_amount,
                "net_amount": net_amount,
                "fee_amount": fee_amount,
                "tax_amount": tax_amount,
                "withholding_tax_amount": withholding_tax_amount,
                "quantity": "1",
                "price_per_unit": "100.00",
                "reference_id": reference_id,
                "source_name": "manual_ledger_fixture",
                "verification_status": verification_status,
                "data_quality_flag": data_quality_flag,
                "notes": "unit fixture",
            }
        )
        return row

    def _document_summary_row(
        self,
        reference_id: str,
        period_start: str,
        period_end: str,
        gross_amount: str = "50.00",
        tax_amount: str = "10.00",
    ) -> dict[str, str]:
        row = {field: "" for field in NORMALIZED_LEDGER_FIELDS}
        row.update(
            {
                "event_date": period_end,
                "broker": "TRADE_REPUBLIC",
                "document_type": "TRADE_REPUBLIC_YEARLY_TAX_CERTIFICATE",
                "record_granularity": "DOCUMENT_SUMMARY",
                "event_type": "DOCUMENT_SUMMARY",
                "currency": "EUR",
                "gross_amount": gross_amount,
                "tax_amount": tax_amount,
                "reference_id": reference_id,
                "source_name": "document_summary_input",
                "verification_status": "VERIFIED",
                "data_quality_flag": "OK",
                "notes": "document summary fixture",
                "document_period_start": period_start,
                "document_period_end": period_end,
                "tax_jurisdiction": "DE",
            }
        )
        return row

    def _write_ledger(self, path: Path, rows: list[dict[str, str]]) -> None:
        self._write_csv(path, NORMALIZED_LEDGER_FIELDS, rows)

    def test_first_run_creates_archive_and_downstream_artifacts(self) -> None:
        ledger_path = self._path("_tmp_cost_tax_archive_first_ledger.csv")
        archive_path = self._path("_tmp_cost_tax_archive_first_archive.csv")
        normalized_output = self._path("_tmp_cost_tax_archive_first_normalized.csv")
        summary_output = self._path("_tmp_cost_tax_archive_first_summary.csv")
        kpi_output = self._path("_tmp_cost_tax_archive_first_kpis.csv")
        report_output = self._path("_tmp_cost_tax_archive_first_report.md")
        archive_summary_output = self._path("_tmp_cost_tax_archive_first_archive_summary.csv")
        self._write_ledger(ledger_path, [self._ledger_row("TRX-001")])

        run_cost_tax_archive_engine(
            ledger_path=str(ledger_path),
            archive_path=str(archive_path),
            archive_output=str(archive_path),
            normalized_ledger_output=str(normalized_output),
            summary_output=str(summary_output),
            kpi_output=str(kpi_output),
            report_output=str(report_output),
            archive_summary_output=str(archive_summary_output),
        )

        self.assertEqual(len(read_csv_rows(archive_path)), 1)
        self.assertEqual(len(read_csv_rows(normalized_output)), 1)
        self.assertEqual(read_csv_rows(summary_output)[0]["ledger_measurement_mode"], FULL_LEDGER)
        archive_summary = read_csv_rows(archive_summary_output)[0]
        self.assertEqual(archive_summary["archive_rows"], "1")
        self.assertEqual(archive_summary["new_rows_added"], "1")
        self.assertEqual(archive_summary["duplicate_rows_skipped"], "0")
        self.assertIn("# Cost and Tax Report", report_output.read_text(encoding="utf-8"))

    def test_second_run_extends_existing_archive(self) -> None:
        first_ledger = self._path("_tmp_cost_tax_archive_extend_first.csv")
        second_ledger = self._path("_tmp_cost_tax_archive_extend_second.csv")
        archive_path = self._path("_tmp_cost_tax_archive_extend_archive.csv")
        self._write_ledger(first_ledger, [self._ledger_row("TRX-001", event_date="2026-04-10")])
        self._write_ledger(second_ledger, [self._ledger_row("TRX-002", event_date="2026-04-11", ticker="MSFT", isin="US5949181045")])

        run_cost_tax_archive_engine(
            ledger_path=str(first_ledger),
            archive_path=str(archive_path),
            archive_output=str(archive_path),
            normalized_ledger_output=str(self._path("_tmp_cost_tax_archive_extend_first_normalized.csv")),
            summary_output=str(self._path("_tmp_cost_tax_archive_extend_first_summary.csv")),
            kpi_output=str(self._path("_tmp_cost_tax_archive_extend_first_kpis.csv")),
            report_output=str(self._path("_tmp_cost_tax_archive_extend_first_report.md")),
        )
        run_cost_tax_archive_engine(
            ledger_path=str(second_ledger),
            archive_path=str(archive_path),
            archive_output=str(archive_path),
            normalized_ledger_output=str(self._path("_tmp_cost_tax_archive_extend_second_normalized.csv")),
            summary_output=str(self._path("_tmp_cost_tax_archive_extend_second_summary.csv")),
            kpi_output=str(self._path("_tmp_cost_tax_archive_extend_second_kpis.csv")),
            report_output=str(self._path("_tmp_cost_tax_archive_extend_second_report.md")),
        )

        archive_rows = read_csv_rows(archive_path)
        self.assertEqual([row["reference_id"] for row in archive_rows], ["TRX-001", "TRX-002"])

    def test_identical_repetition_is_idempotent(self) -> None:
        ledger_path = self._path("_tmp_cost_tax_archive_idempotent_ledger.csv")
        archive_path = self._path("_tmp_cost_tax_archive_idempotent_archive.csv")
        archive_summary_output = self._path("_tmp_cost_tax_archive_idempotent_archive_summary.csv")
        self._write_ledger(ledger_path, [self._ledger_row("TRX-001")])

        for index in range(2):
            run_cost_tax_archive_engine(
                ledger_path=str(ledger_path),
                archive_path=str(archive_path),
                archive_output=str(archive_path),
                normalized_ledger_output=str(self._path(f"_tmp_cost_tax_archive_idempotent_normalized_{index}.csv")),
                summary_output=str(self._path(f"_tmp_cost_tax_archive_idempotent_summary_{index}.csv")),
                kpi_output=str(self._path(f"_tmp_cost_tax_archive_idempotent_kpis_{index}.csv")),
                report_output=str(self._path(f"_tmp_cost_tax_archive_idempotent_report_{index}.md")),
                archive_summary_output=str(archive_summary_output),
            )

        self.assertEqual(len(read_csv_rows(archive_path)), 1)
        archive_summary = read_csv_rows(archive_summary_output)[0]
        self.assertEqual(archive_summary["new_rows_added"], "0")
        self.assertEqual(archive_summary["duplicate_rows_skipped"], "1")

    def test_conflict_on_same_identity_with_different_values_fails_fast(self) -> None:
        first_ledger = self._path("_tmp_cost_tax_archive_conflict_first.csv")
        conflict_ledger = self._path("_tmp_cost_tax_archive_conflict_second.csv")
        archive_path = self._path("_tmp_cost_tax_archive_conflict_archive.csv")
        self._write_ledger(first_ledger, [self._ledger_row("TRX-001", fee_amount="1.00")])
        self._write_ledger(conflict_ledger, [self._ledger_row("TRX-001", fee_amount="2.00")])
        run_cost_tax_archive_engine(
            ledger_path=str(first_ledger),
            archive_path=str(archive_path),
            archive_output=str(archive_path),
            normalized_ledger_output=str(self._path("_tmp_cost_tax_archive_conflict_normalized.csv")),
            summary_output=str(self._path("_tmp_cost_tax_archive_conflict_summary.csv")),
            kpi_output=str(self._path("_tmp_cost_tax_archive_conflict_kpis.csv")),
            report_output=str(self._path("_tmp_cost_tax_archive_conflict_report.md")),
        )

        with self.assertRaisesRegex(ValueError, "reference_id=TRX-001"):
            run_cost_tax_archive_engine(
                ledger_path=str(conflict_ledger),
                archive_path=str(archive_path),
                archive_output=str(archive_path),
                normalized_ledger_output=str(self._path("_tmp_cost_tax_archive_conflict_second_normalized.csv")),
                summary_output=str(self._path("_tmp_cost_tax_archive_conflict_second_summary.csv")),
                kpi_output=str(self._path("_tmp_cost_tax_archive_conflict_second_kpis.csv")),
                report_output=str(self._path("_tmp_cost_tax_archive_conflict_second_report.md")),
            )

    def test_multiple_document_inputs_are_processed_in_deterministic_order(self) -> None:
        archive_path = self._path("_tmp_cost_tax_archive_docs_archive.csv")
        summary_output = self._path("_tmp_cost_tax_archive_docs_summary.csv")
        document_inputs = [
            str(self._path("_tmp_Z_Steuerbericht_2025.pdf")),
            str(self._path("_tmp_A_Steuerbericht_2024.pdf")),
        ]
        with patch("src.cost_tax_archive_engine.load_document_rows") as mocked_loader:
            mocked_loader.return_value = [
                self._document_summary_row("DOC-2024", "2024-01-01", "2024-12-31"),
                self._document_summary_row("DOC-2025", "2025-01-01", "2025-12-31"),
            ]
            run_cost_tax_archive_engine(
                document_inputs=document_inputs,
                archive_path=str(archive_path),
                archive_output=str(archive_path),
                normalized_ledger_output=str(self._path("_tmp_cost_tax_archive_docs_normalized.csv")),
                summary_output=str(summary_output),
                kpi_output=str(self._path("_tmp_cost_tax_archive_docs_kpis.csv")),
                report_output=str(self._path("_tmp_cost_tax_archive_docs_report.md")),
            )

        mocked_loader.assert_called_once_with(sorted(document_inputs), "document_summary_input")
        self.assertEqual(len(read_csv_rows(archive_path)), 2)
        self.assertEqual(read_csv_rows(summary_output)[0]["ledger_measurement_mode"], DOCUMENT_SUMMARY_ONLY)

    def test_archive_only_run_regenerates_summary_kpis_and_report(self) -> None:
        archive_path = self._path("_tmp_cost_tax_archive_only_input.csv")
        summary_output = self._path("_tmp_cost_tax_archive_only_summary.csv")
        kpi_output = self._path("_tmp_cost_tax_archive_only_kpis.csv")
        report_output = self._path("_tmp_cost_tax_archive_only_report.md")
        self._write_csv(archive_path, NORMALIZED_LEDGER_FIELDS, [self._ledger_row("TRX-001")])

        run_cost_tax_archive_engine(
            archive_path=str(archive_path),
            archive_output=str(self._path("_tmp_cost_tax_archive_only_output.csv")),
            normalized_ledger_output=str(self._path("_tmp_cost_tax_archive_only_normalized.csv")),
            summary_output=str(summary_output),
            kpi_output=str(kpi_output),
            report_output=str(report_output),
        )

        self.assertEqual(read_csv_rows(summary_output)[0]["ledger_measurement_mode"], FULL_LEDGER)
        self.assertTrue(read_csv_rows(kpi_output))
        self.assertIn("## Datenlage", report_output.read_text(encoding="utf-8"))

    def test_mixed_event_and_document_rows_produce_partial_ledger_mode(self) -> None:
        ledger_path = self._path("_tmp_cost_tax_archive_partial_ledger.csv")
        archive_path = self._path("_tmp_cost_tax_archive_partial_archive.csv")
        summary_output = self._path("_tmp_cost_tax_archive_partial_summary.csv")
        self._write_ledger(ledger_path, [self._ledger_row("TRX-001")])

        with patch("src.cost_tax_archive_engine.load_document_rows") as mocked_loader:
            mocked_loader.return_value = [self._document_summary_row("DOC-2024", "2024-01-01", "2024-12-31")]
            run_cost_tax_archive_engine(
                ledger_path=str(ledger_path),
                document_inputs=[str(self._path("_tmp_partial_Steuerbericht_2024.pdf"))],
                archive_path=str(archive_path),
                archive_output=str(archive_path),
                normalized_ledger_output=str(self._path("_tmp_cost_tax_archive_partial_normalized.csv")),
                summary_output=str(summary_output),
                kpi_output=str(self._path("_tmp_cost_tax_archive_partial_kpis.csv")),
                report_output=str(self._path("_tmp_cost_tax_archive_partial_report.md")),
            )

        self.assertEqual(read_csv_rows(summary_output)[0]["ledger_measurement_mode"], PARTIAL_LEDGER)

    def test_incomplete_archive_header_is_rejected(self) -> None:
        archive_path = self._path("_tmp_cost_tax_archive_bad_header.csv")
        self._write_csv(archive_path, ["event_date", "reference_id"], [{"event_date": "2026-04-10", "reference_id": "TRX-001"}])

        with self.assertRaisesRegex(ValueError, "cost/tax ledger archive .* missing required columns: .*broker"):
            run_cost_tax_archive_engine(
                archive_path=str(archive_path),
                archive_output=str(self._path("_tmp_cost_tax_archive_bad_header_output.csv")),
                normalized_ledger_output=str(self._path("_tmp_cost_tax_archive_bad_header_normalized.csv")),
                summary_output=str(self._path("_tmp_cost_tax_archive_bad_header_summary.csv")),
                kpi_output=str(self._path("_tmp_cost_tax_archive_bad_header_kpis.csv")),
                report_output=str(self._path("_tmp_cost_tax_archive_bad_header_report.md")),
            )

    def test_cli_smoke_builds_archive_to_report_chain(self) -> None:
        ledger_path = self._path("_tmp_cost_tax_archive_cli_ledger.csv")
        archive_path = self._path("_tmp_cost_tax_archive_cli_archive.csv")
        normalized_output = self._path("_tmp_cost_tax_archive_cli_normalized.csv")
        summary_output = self._path("_tmp_cost_tax_archive_cli_summary.csv")
        kpi_output = self._path("_tmp_cost_tax_archive_cli_kpis.csv")
        report_output = self._path("_tmp_cost_tax_archive_cli_report.md")
        archive_summary_output = self._path("_tmp_cost_tax_archive_cli_archive_summary.csv")
        self._write_ledger(ledger_path, [self._ledger_row("TRX-001")])

        result = subprocess.run(
            [
                "python",
                "-m",
                "src.cost_tax_archive_engine",
                "--ledger",
                str(ledger_path),
                "--archive",
                str(archive_path),
                "--archive-output",
                str(archive_path),
                "--normalized-ledger-output",
                str(normalized_output),
                "--summary-output",
                str(summary_output),
                "--kpi-output",
                str(kpi_output),
                "--report-output",
                str(report_output),
                "--archive-summary-output",
                str(archive_summary_output),
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(read_csv_rows(archive_path)), 1)
        self.assertEqual(len(read_csv_rows(normalized_output)), 1)
        self.assertEqual(read_csv_rows(summary_output)[0]["ledger_measurement_mode"], FULL_LEDGER)
        self.assertTrue(read_csv_rows(kpi_output))
        self.assertEqual(read_csv_rows(archive_summary_output)[0]["archive_rows"], "1")
        self.assertIn("# Cost and Tax Report", report_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
