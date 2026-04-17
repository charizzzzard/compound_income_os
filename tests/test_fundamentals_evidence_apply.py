from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.fundamentals_evidence_apply import APPLY_SUMMARY_FIELDS, run_fundamentals_evidence_apply
from src.fundamentals_evidence_engine import PROPOSED_UPDATES_FIELDS
from src.fundamentals_master import PERSONAL_MASTER_FIELDS


class FundamentalsEvidenceApplyTests(unittest.TestCase):
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

    def _master_row(
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
                "sleeve": "SINGLE_STOCK",
                "current_price_eur": "100",
                "mandate_fit_score": "80",
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
        source_reference: str = "FY2025 annual report",
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
                "source_type": "ANNUAL_REPORT",
                "source_name": "annual_report_2025",
                "source_reference": source_reference,
                "source_as_of_date": "2026-03-31",
                "fiscal_year": "2025",
                "verification_status": "VERIFIED",
                "data_quality_flag": "OK",
                "proposal_reason": "validated evidence for apply test",
                "notes": "unit proposed update",
            }
        )
        return row

    def test_run_fundamentals_evidence_apply_projects_supported_fields_and_preserves_master_schema(self) -> None:
        master_path = self._path("_tmp_evidence_apply_master.csv")
        proposed_updates_path = self._path("_tmp_evidence_apply_proposed_updates.csv")
        registry_output = self._path("_tmp_evidence_apply_registry.csv")
        applied_master_output = self._path("_tmp_evidence_apply_master_applied.csv")
        summary_output = self._path("_tmp_evidence_apply_summary.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [self._master_row()])
        self._write_csv(proposed_updates_path, PROPOSED_UPDATES_FIELDS, [self._proposed_update_row()])

        outputs = run_fundamentals_evidence_apply(
            fundamentals_master_path=str(master_path),
            proposed_updates_input_path=str(proposed_updates_path),
            registry_output=str(registry_output),
            evidence_applied_master_output=str(applied_master_output),
            summary_output=str(summary_output),
        )

        registry_rows = read_csv_rows(outputs["evidence_apply_registry"])
        applied_master_rows = read_csv_rows(outputs["evidence_applied_master"])
        summary_rows = read_csv_rows(outputs["evidence_apply_summary"])
        self.assertEqual(registry_rows[0]["apply_status"], "APPLIED")
        self.assertEqual(registry_rows[0]["target_field"], "roic")
        self.assertEqual(applied_master_rows[0]["roic"], "25.0")
        self.assertEqual(set(applied_master_rows[0]), set(PERSONAL_MASTER_FIELDS))
        self.assertEqual(set(summary_rows[0]), set(APPLY_SUMMARY_FIELDS))
        self.assertEqual(summary_rows[0]["applied_rows_total"], "1")
        self.assertEqual(summary_rows[0]["applied_fields_total"], "1")

    def test_run_fundamentals_evidence_apply_skips_unsupported_fields(self) -> None:
        master_path = self._path("_tmp_evidence_apply_unsupported_master.csv")
        proposed_updates_path = self._path("_tmp_evidence_apply_unsupported_proposed_updates.csv")
        registry_output = self._path("_tmp_evidence_apply_unsupported_registry.csv")
        applied_master_output = self._path("_tmp_evidence_apply_unsupported_master_applied.csv")
        summary_output = self._path("_tmp_evidence_apply_unsupported_summary.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [self._master_row()])
        self._write_csv(
            proposed_updates_path,
            PROPOSED_UPDATES_FIELDS,
            [self._proposed_update_row(kpi_name="company_type_profile", reported_value="STANDARD")],
        )

        run_fundamentals_evidence_apply(
            fundamentals_master_path=str(master_path),
            proposed_updates_input_path=str(proposed_updates_path),
            registry_output=str(registry_output),
            evidence_applied_master_output=str(applied_master_output),
            summary_output=str(summary_output),
        )

        registry_rows = read_csv_rows(registry_output)
        applied_master_rows = read_csv_rows(applied_master_output)
        summary_rows = read_csv_rows(summary_output)
        self.assertEqual(registry_rows[0]["apply_status"], "SKIPPED_UNSUPPORTED_FIELD")
        self.assertEqual(applied_master_rows[0]["company_type_profile"], "OTHER")
        self.assertEqual(summary_rows[0]["skipped_unsupported_fields_total"], "1")

    def test_run_fundamentals_evidence_apply_skips_rows_without_master_match(self) -> None:
        master_path = self._path("_tmp_evidence_apply_nomatch_master.csv")
        proposed_updates_path = self._path("_tmp_evidence_apply_nomatch_proposed_updates.csv")
        registry_output = self._path("_tmp_evidence_apply_nomatch_registry.csv")
        applied_master_output = self._path("_tmp_evidence_apply_nomatch_master_applied.csv")
        summary_output = self._path("_tmp_evidence_apply_nomatch_summary.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [self._master_row()])
        self._write_csv(
            proposed_updates_path,
            PROPOSED_UPDATES_FIELDS,
            [self._proposed_update_row(ticker="AAPL", company_name="Apple", reported_value="33.0")],
        )

        run_fundamentals_evidence_apply(
            fundamentals_master_path=str(master_path),
            proposed_updates_input_path=str(proposed_updates_path),
            registry_output=str(registry_output),
            evidence_applied_master_output=str(applied_master_output),
            summary_output=str(summary_output),
        )

        registry_rows = read_csv_rows(registry_output)
        applied_master_rows = read_csv_rows(applied_master_output)
        summary_rows = read_csv_rows(summary_output)
        self.assertEqual(registry_rows[0]["apply_status"], "SKIPPED_NO_MATCH")
        self.assertEqual(applied_master_rows[0]["roic"], "")
        self.assertEqual(summary_rows[0]["skipped_no_match_total"], "1")

    def test_run_fundamentals_evidence_apply_rejects_conflicting_values_for_same_entity_and_field(self) -> None:
        master_path = self._path("_tmp_evidence_apply_conflict_master.csv")
        proposed_updates_path = self._path("_tmp_evidence_apply_conflict_proposed_updates.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [self._master_row()])
        self._write_csv(
            proposed_updates_path,
            PROPOSED_UPDATES_FIELDS,
            [
                self._proposed_update_row(reported_value="25.0"),
                self._proposed_update_row(reported_value="30.0", source_reference="alternate source"),
            ],
        )

        with self.assertRaisesRegex(ValueError, "conflicts for entity=MSFT target_field=roic"):
            run_fundamentals_evidence_apply(
                fundamentals_master_path=str(master_path),
                proposed_updates_input_path=str(proposed_updates_path),
                registry_output=str(self._path("_tmp_evidence_apply_conflict_registry.csv")),
                evidence_applied_master_output=str(self._path("_tmp_evidence_apply_conflict_master_applied.csv")),
                summary_output=str(self._path("_tmp_evidence_apply_conflict_summary.csv")),
            )

    def test_run_fundamentals_evidence_apply_deduplicates_identical_entity_field_values(self) -> None:
        master_path = self._path("_tmp_evidence_apply_duplicate_master.csv")
        proposed_updates_path = self._path("_tmp_evidence_apply_duplicate_proposed_updates.csv")
        registry_output = self._path("_tmp_evidence_apply_duplicate_registry.csv")
        applied_master_output = self._path("_tmp_evidence_apply_duplicate_master_applied.csv")
        summary_output = self._path("_tmp_evidence_apply_duplicate_summary.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [self._master_row()])
        self._write_csv(
            proposed_updates_path,
            PROPOSED_UPDATES_FIELDS,
            [
                self._proposed_update_row(reported_value="25.0"),
                self._proposed_update_row(reported_value="25", source_reference="duplicate source"),
            ],
        )

        run_fundamentals_evidence_apply(
            fundamentals_master_path=str(master_path),
            proposed_updates_input_path=str(proposed_updates_path),
            registry_output=str(registry_output),
            evidence_applied_master_output=str(applied_master_output),
            summary_output=str(summary_output),
        )

        registry_rows = read_csv_rows(registry_output)
        summary_rows = read_csv_rows(summary_output)
        self.assertEqual([row["apply_status"] for row in registry_rows], ["APPLIED", "DUPLICATE_IDENTICAL"])
        self.assertEqual(summary_rows[0]["applied_rows_total"], "1")
        self.assertEqual(summary_rows[0]["duplicate_identical_total"], "1")


if __name__ == "__main__":
    unittest.main()
