from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.fundamentals_evidence_compose import (
    COMPOSE_CONFLICT_FIELDS,
    COMPOSE_SUMMARY_FIELDS,
    run_fundamentals_evidence_compose,
)
from src.fundamentals_evidence_engine import EVIDENCE_INPUT_FIELDS


def evidence_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    kpi_name: str = "roic",
    source_type: str = "ANNUAL_REPORT",
    source_name: str = "annual_report_2025",
    source_reference: str = "FY2025 annual report",
    source_as_of_date: str = "2026-03-31",
    fiscal_year: str = "2025",
    verification_status: str = "VERIFIED",
    data_quality_flag: str = "OK",
    reported_value: str = "25.0",
    notes: str = "fixture evidence",
) -> dict[str, str]:
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


class FundamentalsEvidenceComposeTests(unittest.TestCase):
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

    def test_valid_manual_and_promoted_evidence_are_composed(self) -> None:
        manual_path = self._path("_tmp_compose_manual.csv")
        promoted_path = self._path("_tmp_compose_promoted.csv")
        composed_path = self._path("_tmp_compose_output.csv")
        conflicts_path = self._path("_tmp_compose_conflicts.csv")
        summary_path = self._path("_tmp_compose_summary.csv")
        self._write_csv(manual_path, EVIDENCE_INPUT_FIELDS, [evidence_row(kpi_name="roic")])
        self._write_csv(
            promoted_path,
            EVIDENCE_INPUT_FIELDS,
            [
                evidence_row(
                    kpi_name="fcf_margin",
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

        outputs = run_fundamentals_evidence_compose(
            manual_evidence_input_path=str(manual_path),
            promoted_evidence_input_path=str(promoted_path),
            composed_output=str(composed_path),
            conflicts_output=str(conflicts_path),
            summary_output=str(summary_path),
        )

        with composed_path.open("r", encoding="utf-8-sig", newline="") as handle:
            self.assertEqual(csv.DictReader(handle).fieldnames, EVIDENCE_INPUT_FIELDS)
        composed_rows = read_csv_rows(composed_path)
        conflict_rows = read_csv_rows(conflicts_path)
        summary_rows = read_csv_rows(summary_path)
        self.assertEqual(set(outputs), {"evidence_composed", "evidence_compose_conflicts", "evidence_compose_summary"})
        self.assertEqual(len(composed_rows), 2)
        self.assertEqual(conflict_rows, [])
        self.assertEqual(set(summary_rows[0]), set(COMPOSE_SUMMARY_FIELDS))
        self.assertEqual(summary_rows[0]["manual_rows_total"], "1")
        self.assertEqual(summary_rows[0]["promoted_rows_total"], "1")
        self.assertEqual(summary_rows[0]["composed_rows_total"], "2")
        self.assertEqual(summary_rows[0]["identical_duplicates_removed"], "0")
        self.assertEqual(summary_rows[0]["conflict_rows_total"], "0")

    def test_identical_duplicates_are_deduplicated(self) -> None:
        manual_path = self._path("_tmp_compose_dedupe_manual.csv")
        promoted_path = self._path("_tmp_compose_dedupe_promoted.csv")
        composed_path = self._path("_tmp_compose_dedupe_output.csv")
        conflicts_path = self._path("_tmp_compose_dedupe_conflicts.csv")
        summary_path = self._path("_tmp_compose_dedupe_summary.csv")
        duplicate_row = evidence_row(
            source_type="SNAPSHOT_IMPORT",
            source_name="vendor_snapshot",
            source_reference="vendor_export_2026q1",
            source_as_of_date="2026-04-15",
            verification_status="UNVERIFIED",
            data_quality_flag="REVIEW",
        )
        self._write_csv(manual_path, EVIDENCE_INPUT_FIELDS, [duplicate_row, duplicate_row])
        self._write_csv(promoted_path, EVIDENCE_INPUT_FIELDS, [duplicate_row])

        run_fundamentals_evidence_compose(
            manual_evidence_input_path=str(manual_path),
            promoted_evidence_input_path=str(promoted_path),
            composed_output=str(composed_path),
            conflicts_output=str(conflicts_path),
            summary_output=str(summary_path),
        )

        composed_rows = read_csv_rows(composed_path)
        summary_rows = read_csv_rows(summary_path)
        self.assertEqual(len(composed_rows), 1)
        self.assertEqual(summary_rows[0]["identical_duplicates_removed"], "2")

    def test_conflicting_rows_are_written_to_conflicts_and_fail_fast(self) -> None:
        manual_path = self._path("_tmp_compose_conflict_manual.csv")
        promoted_path = self._path("_tmp_compose_conflict_promoted.csv")
        composed_path = self._path("_tmp_compose_conflict_output.csv")
        conflicts_path = self._path("_tmp_compose_conflict_conflicts.csv")
        summary_path = self._path("_tmp_compose_conflict_summary.csv")
        base_row = evidence_row(
            source_type="SNAPSHOT_IMPORT",
            source_name="vendor_snapshot",
            source_reference="vendor_export_2026q1",
            source_as_of_date="2026-04-15",
            verification_status="UNVERIFIED",
            data_quality_flag="REVIEW",
        )
        self._write_csv(manual_path, EVIDENCE_INPUT_FIELDS, [base_row])
        self._write_csv(promoted_path, EVIDENCE_INPUT_FIELDS, [{**base_row, "reported_value": "26.0"}])

        with self.assertRaisesRegex(ValueError, "compose found conflicting row"):
            run_fundamentals_evidence_compose(
                manual_evidence_input_path=str(manual_path),
                promoted_evidence_input_path=str(promoted_path),
                composed_output=str(composed_path),
                conflicts_output=str(conflicts_path),
                summary_output=str(summary_path),
            )

        composed_rows = read_csv_rows(composed_path)
        conflict_rows = read_csv_rows(conflicts_path)
        summary_rows = read_csv_rows(summary_path)
        with conflicts_path.open("r", encoding="utf-8-sig", newline="") as handle:
            self.assertEqual(csv.DictReader(handle).fieldnames, COMPOSE_CONFLICT_FIELDS)
        self.assertEqual(composed_rows, [])
        self.assertEqual(len(conflict_rows), 2)
        self.assertEqual(summary_rows[0]["composed_rows_total"], "0")
        self.assertEqual(summary_rows[0]["conflict_rows_total"], "2")

    def test_schema_drift_is_rejected(self) -> None:
        manual_path = self._path("_tmp_compose_schema_manual.csv")
        promoted_path = self._path("_tmp_compose_schema_promoted.csv")
        self._write_csv(manual_path, EVIDENCE_INPUT_FIELDS, [])
        invalid_fields = [field for field in EVIDENCE_INPUT_FIELDS if field != "currency"]
        self._write_csv(promoted_path, invalid_fields, [{field: evidence_row().get(field, "") for field in invalid_fields}])

        with self.assertRaisesRegex(ValueError, "does not match the evidence input contract"):
            run_fundamentals_evidence_compose(
                manual_evidence_input_path=str(manual_path),
                promoted_evidence_input_path=str(promoted_path),
                composed_output=str(self._path("_tmp_compose_schema_output.csv")),
                conflicts_output=str(self._path("_tmp_compose_schema_conflicts.csv")),
                summary_output=str(self._path("_tmp_compose_schema_summary.csv")),
            )


if __name__ == "__main__":
    unittest.main()
