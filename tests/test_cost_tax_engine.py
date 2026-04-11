from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path

from src.common import load_yaml_config, read_csv_rows
from src.cost_tax_engine import (
    DOCUMENT_SUMMARY_ONLY,
    FULL_LEDGER,
    INSUFFICIENT_DOCUMENTATION,
    PARTIAL_LEDGER,
    determine_measurement_mode,
    normalize_manual_ledger_rows,
    parse_trade_republic_tax_document_text,
    run_cost_tax_engine,
)


class CostTaxEngineTests(unittest.TestCase):
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

    def _base_fields(self) -> list[str]:
        return [
            "event_date",
            "broker",
            "document_type",
            "record_granularity",
            "event_type",
            "instrument_name",
            "ticker",
            "isin",
            "currency",
            "gross_amount",
            "net_amount",
            "fee_amount",
            "tax_amount",
            "withholding_tax_amount",
            "quantity",
            "price_per_unit",
            "reference_id",
            "source_name",
            "verification_status",
            "data_quality_flag",
            "notes",
            "event_group_id",
            "document_period_start",
            "document_period_end",
            "realized_proceeds_amount",
            "realized_cost_basis_amount",
            "realized_pnl_before_tax",
            "realized_pnl_after_tax_estimate_or_partial",
            "tax_jurisdiction",
        ]

    def _write_document_summary_ledger(self, path: Path) -> None:
        self._write_csv(
            path,
            self._base_fields(),
            [
                {
                    "event_date": "2026-12-31",
                    "broker": "TRADE_REPUBLIC",
                    "document_type": "TRADE_REPUBLIC_YEARLY_TAX_CERTIFICATE",
                    "record_granularity": "DOCUMENT_SUMMARY",
                    "event_type": "DOCUMENT_SUMMARY",
                    "instrument_name": "",
                    "ticker": "",
                    "isin": "",
                    "currency": "EUR",
                    "gross_amount": "120.00",
                    "net_amount": "",
                    "fee_amount": "",
                    "tax_amount": "0.00",
                    "withholding_tax_amount": "",
                    "quantity": "",
                    "price_per_unit": "",
                    "reference_id": "DOC-2026",
                    "source_name": "document_summary_fixture",
                    "verification_status": "VERIFIED",
                    "data_quality_flag": "OK",
                    "notes": "Aggregated yearly tax summary",
                    "event_group_id": "",
                    "document_period_start": "2026-01-01",
                    "document_period_end": "2026-12-31",
                    "realized_proceeds_amount": "",
                    "realized_cost_basis_amount": "",
                    "realized_pnl_before_tax": "20.00",
                    "realized_pnl_after_tax_estimate_or_partial": "",
                    "tax_jurisdiction": "DE",
                }
            ],
        )

    def _write_partial_ledger(self, path: Path) -> None:
        self._write_csv(
            path,
            self._base_fields(),
            [
                {
                    "event_date": "2026-01-15",
                    "broker": "TRADE_REPUBLIC",
                    "document_type": "TRADE_CONFIRMATION",
                    "record_granularity": "EVENT",
                    "event_type": "BUY",
                    "instrument_name": "ETF",
                    "ticker": "VWCE",
                    "isin": "IE00BK5BQT80",
                    "currency": "EUR",
                    "gross_amount": "1100.00",
                    "net_amount": "",
                    "fee_amount": "1.00",
                    "tax_amount": "",
                    "withholding_tax_amount": "",
                    "quantity": "10",
                    "price_per_unit": "110.00",
                    "reference_id": "TRX-001",
                    "source_name": "partial_ledger_fixture",
                    "verification_status": "VERIFIED",
                    "data_quality_flag": "OK",
                    "notes": "",
                    "event_group_id": "TRX-001",
                    "document_period_start": "",
                    "document_period_end": "",
                    "realized_proceeds_amount": "",
                    "realized_cost_basis_amount": "",
                    "realized_pnl_before_tax": "",
                    "realized_pnl_after_tax_estimate_or_partial": "",
                    "tax_jurisdiction": "",
                },
                {
                    "event_date": "2026-12-31",
                    "broker": "TRADE_REPUBLIC",
                    "document_type": "TRADE_REPUBLIC_YEARLY_TAX_CERTIFICATE",
                    "record_granularity": "DOCUMENT_SUMMARY",
                    "event_type": "DOCUMENT_SUMMARY",
                    "instrument_name": "",
                    "ticker": "",
                    "isin": "",
                    "currency": "EUR",
                    "gross_amount": "120.00",
                    "net_amount": "",
                    "fee_amount": "",
                    "tax_amount": "0.00",
                    "withholding_tax_amount": "",
                    "quantity": "",
                    "price_per_unit": "",
                    "reference_id": "DOC-2026",
                    "source_name": "partial_ledger_fixture",
                    "verification_status": "PARTIAL",
                    "data_quality_flag": "OK",
                    "notes": "Mixed event and document summary coverage",
                    "event_group_id": "",
                    "document_period_start": "2026-01-01",
                    "document_period_end": "2026-12-31",
                    "realized_proceeds_amount": "",
                    "realized_cost_basis_amount": "",
                    "realized_pnl_before_tax": "",
                    "realized_pnl_after_tax_estimate_or_partial": "",
                    "tax_jurisdiction": "DE",
                },
            ],
        )

    def test_ledger_csv_normalization(self) -> None:
        config = load_yaml_config("configs/cost_tax_ledger.yaml")
        rows = read_csv_rows("data/raw/sample_cost_tax_ledger.csv")
        normalized = normalize_manual_ledger_rows(rows, config, "data/raw/sample_cost_tax_ledger.csv")
        self.assertEqual(len(normalized), 4)
        self.assertEqual(normalized[0]["record_granularity"], "EVENT")
        self.assertEqual(normalized[0]["verification_status"], "VERIFIED")
        self.assertEqual(normalized[3]["realized_pnl_before_tax"], "70.0")

    def test_missing_required_columns_are_rejected(self) -> None:
        config = load_yaml_config("configs/cost_tax_ledger.yaml")
        path = self._path("_tmp_incomplete_cost_tax_ledger.csv")
        self._write_csv(path, ["event_date", "broker"], [{"event_date": "2026-01-01", "broker": "TR"}])
        rows = read_csv_rows(path)
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            normalize_manual_ledger_rows(rows, config, str(path))

    def test_document_summary_only_mode_is_detected(self) -> None:
        config = load_yaml_config("configs/cost_tax_ledger.yaml")
        path = self._path("_tmp_document_summary_ledger.csv")
        self._write_document_summary_ledger(path)
        normalized = normalize_manual_ledger_rows(read_csv_rows(path), config, str(path))
        self.assertEqual(determine_measurement_mode(normalized, "auto"), DOCUMENT_SUMMARY_ONLY)

    def test_partial_ledger_mode_is_detected(self) -> None:
        config = load_yaml_config("configs/cost_tax_ledger.yaml")
        path = self._path("_tmp_partial_ledger.csv")
        self._write_partial_ledger(path)
        normalized = normalize_manual_ledger_rows(read_csv_rows(path), config, str(path))
        self.assertEqual(determine_measurement_mode(normalized, "auto"), PARTIAL_LEDGER)

    def test_full_ledger_mode_is_detected(self) -> None:
        config = load_yaml_config("configs/cost_tax_ledger.yaml")
        normalized = normalize_manual_ledger_rows(read_csv_rows("data/raw/sample_cost_tax_ledger.csv"), config, "data/raw/sample_cost_tax_ledger.csv")
        self.assertEqual(determine_measurement_mode(normalized, "auto"), FULL_LEDGER)

    def test_fee_tax_and_dividend_aggregation(self) -> None:
        summary_path = self._path("_tmp_cost_tax_summary.csv")
        kpi_path = self._path("_tmp_cost_tax_kpis.csv")
        report_path = self._path("_tmp_cost_tax_report.md")

        run_cost_tax_engine(
            ledger_path="data/raw/sample_cost_tax_ledger.csv",
            normalized_ledger_output=str(self._path("_tmp_cost_tax_ledger_normalized.csv")),
            summary_output=str(summary_path),
            kpi_output=str(kpi_path),
            report_output=str(report_path),
        )

        summary_row = read_csv_rows(summary_path)[0]
        self.assertEqual(summary_row["total_fees"], "2.5")
        self.assertEqual(summary_row["total_taxes"], "15.0")
        self.assertEqual(summary_row["total_withholding_taxes"], "2.0")
        self.assertEqual(summary_row["total_dividends_gross"], "30.0")
        self.assertEqual(summary_row["total_interest_received"], "4.5")

    def test_total_dividends_net_is_derived_from_explicit_tax_fields(self) -> None:
        summary_path = self._path("_tmp_cost_tax_summary_dividends.csv")
        run_cost_tax_engine(
            ledger_path="data/raw/sample_cost_tax_ledger.csv",
            normalized_ledger_output=str(self._path("_tmp_cost_tax_ledger_dividends.csv")),
            summary_output=str(summary_path),
            kpi_output=str(self._path("_tmp_cost_tax_kpis_dividends.csv")),
            report_output=str(self._path("_tmp_cost_tax_report_dividends.md")),
        )
        summary_row = read_csv_rows(summary_path)[0]
        self.assertEqual(summary_row["total_dividends_net"], "23.0")

    def test_realized_pnl_stays_insufficient_without_explicit_evidence(self) -> None:
        path = self._path("_tmp_cost_tax_no_realized.csv")
        rows = read_csv_rows("data/raw/sample_cost_tax_ledger.csv")
        for row in rows:
            row["realized_proceeds_amount"] = ""
            row["realized_cost_basis_amount"] = ""
            row["realized_pnl_before_tax"] = ""
            row["realized_pnl_after_tax_estimate_or_partial"] = ""
        self._write_csv(path, self._base_fields(), rows)
        summary_path = self._path("_tmp_cost_tax_summary_no_realized.csv")

        run_cost_tax_engine(
            ledger_path=str(path),
            normalized_ledger_output=str(self._path("_tmp_cost_tax_ledger_no_realized.csv")),
            summary_output=str(summary_path),
            kpi_output=str(self._path("_tmp_cost_tax_kpis_no_realized.csv")),
            report_output=str(self._path("_tmp_cost_tax_report_no_realized.md")),
        )

        summary_row = read_csv_rows(summary_path)[0]
        self.assertEqual(summary_row["total_realized_pnl_before_tax"], INSUFFICIENT_DOCUMENTATION)
        self.assertEqual(summary_row["total_realized_pnl_after_tax"], INSUFFICIENT_DOCUMENTATION)

    def test_explicit_realized_fields_are_aggregated(self) -> None:
        summary_path = self._path("_tmp_cost_tax_summary_realized.csv")
        run_cost_tax_engine(
            ledger_path="data/raw/sample_cost_tax_ledger.csv",
            normalized_ledger_output=str(self._path("_tmp_cost_tax_ledger_realized.csv")),
            summary_output=str(summary_path),
            kpi_output=str(self._path("_tmp_cost_tax_kpis_realized.csv")),
            report_output=str(self._path("_tmp_cost_tax_report_realized.md")),
        )
        summary_row = read_csv_rows(summary_path)[0]
        self.assertEqual(summary_row["total_realized_proceeds"], "520.0")
        self.assertEqual(summary_row["total_realized_cost_basis"], "450.0")
        self.assertEqual(summary_row["total_realized_pnl_before_tax"], "70.0")
        self.assertEqual(summary_row["total_realized_pnl_after_tax"], "60.0")

    def test_artifacts_are_generated(self) -> None:
        normalized_path = self._path("_tmp_cost_tax_ledger_out.csv")
        summary_path = self._path("_tmp_cost_tax_summary_out.csv")
        kpi_path = self._path("_tmp_cost_tax_kpis_out.csv")
        report_path = self._path("_tmp_cost_tax_report_out.md")

        outputs = run_cost_tax_engine(
            ledger_path="data/raw/sample_cost_tax_ledger.csv",
            normalized_ledger_output=str(normalized_path),
            summary_output=str(summary_path),
            kpi_output=str(kpi_path),
            report_output=str(report_path),
        )

        self.assertTrue(outputs["normalized_ledger_output"].exists())
        self.assertTrue(outputs["summary_output"].exists())
        self.assertTrue(outputs["kpi_output"].exists())
        self.assertTrue(outputs["report_output"].exists())

    def test_trade_republic_tax_document_text_is_parsed_as_document_summary(self) -> None:
        rows = parse_trade_republic_tax_document_text(
            """
            Jahressteuerbescheinigung fuer das Jahr 2024
            werden fuer das Kalenderjahr 2024 folgende Angaben bescheinigt:
            Hoehe der Kapitalertraege
            258,21 EUR
            Kapitalertragsteuer
            0,00 EUR
            Solidaritaetszuschlag
            0,00 EUR
            Summe der anrechenbaren noch nicht angerechneten auslaendischen Steuer
            7,12 EUR
            davon: Gewinn aus Aktienveraeusserungen
            2,83 EUR
            """,
            source_name="document_summary_input",
            document_name="Steuerbericht 2024.pdf",
        )
        self.assertEqual(rows[0]["record_granularity"], "DOCUMENT_SUMMARY")
        self.assertEqual(rows[0]["event_type"], "DOCUMENT_SUMMARY")
        self.assertEqual(rows[0]["gross_amount"], "258.21")
        self.assertEqual(rows[0]["realized_pnl_before_tax"], "2.83")

    def test_cli_run_generates_outputs(self) -> None:
        normalized_path = self._path("_tmp_cost_tax_cli_ledger.csv")
        summary_path = self._path("_tmp_cost_tax_cli_summary.csv")
        kpi_path = self._path("_tmp_cost_tax_cli_kpis.csv")
        report_path = self._path("_tmp_cost_tax_cli_report.md")

        result = subprocess.run(
            [
                "python",
                "-m",
                "src.cost_tax_engine",
                "--ledger",
                "data/raw/sample_cost_tax_ledger.csv",
                "--normalized-ledger-output",
                str(normalized_path),
                "--summary-output",
                str(summary_path),
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
        self.assertTrue(normalized_path.exists())
        self.assertTrue(summary_path.exists())
        self.assertTrue(kpi_path.exists())
        self.assertTrue(report_path.exists())


if __name__ == "__main__":
    unittest.main()
