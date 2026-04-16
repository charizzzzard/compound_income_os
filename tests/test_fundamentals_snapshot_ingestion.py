from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.fundamentals_evidence_engine import EVIDENCE_INPUT_FIELDS
from src.fundamentals_master import PERSONAL_MASTER_FIELDS
from src.fundamentals_snapshot_ingestion import (
    NORMALIZED_FIELDS,
    SNAPSHOT_INPUT_FIELDS,
    SUMMARY_FIELDS,
    UNMATCHED_FIELDS,
    run_fundamentals_snapshot_ingestion,
    write_snapshot_template,
)


def master_row(
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
) -> dict[str, str]:
    row = {field: "" for field in PERSONAL_MASTER_FIELDS}
    row.update(
        {
            "ticker": ticker,
            "isin": isin,
            "company_name": company_name,
            "currency": "USD",
            "sector": "Technology",
            "country": "USA",
            "asset_type": "STOCK",
            "company_type_profile": "STANDARD",
            "source_name": "manual_master_fixture",
            "source_as_of_date": "2026-03-31",
            "fiscal_period": "FY",
            "fiscal_year": "2025",
            "report_date": "2026-03-31",
            "filing_date": "2026-04-01",
            "market_price_date": "2026-03-31",
            "calculation_version": "test",
            "data_quality_flag": "REVIEW",
            "notes": "unit fixture",
            "sleeve": "SINGLE_STOCK",
            "current_price_eur": "100",
            "mandate_fit_score": "80",
        }
    )
    return row


def snapshot_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    source_name: str = "vendor_snapshot",
    source_as_of_date: str = "2026-04-15",
    fiscal_year: str = "2025",
    currency: str = "USD",
    source_reference: str = "vendor_export_2026q1",
    market_price_date: str = "2026-04-15",
    roic: str = "25",
    fcf_margin: str = "31",
    notes: str = "unit snapshot row",
) -> dict[str, str]:
    row = {field: "" for field in SNAPSHOT_INPUT_FIELDS}
    row.update(
        {
            "ticker": ticker,
            "isin": isin,
            "company_name": company_name,
            "source_name": source_name,
            "source_as_of_date": source_as_of_date,
            "fiscal_year": fiscal_year,
            "currency": currency,
            "source_reference": source_reference,
            "market_price_date": market_price_date,
            "roic": roic,
            "fcf_margin": fcf_margin,
            "notes": notes,
        }
    )
    return row


class FundamentalsSnapshotIngestionTests(unittest.TestCase):
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

    def _run_engine(
        self,
        *,
        master_rows: list[dict[str, str]],
        snapshot_rows: list[dict[str, str]],
        prefix: str,
    ) -> tuple[Path, Path, Path, Path, Path, Path]:
        master_path = self._path(f"_tmp_snapshot_{prefix}_master.csv")
        snapshot_path = self._path(f"_tmp_snapshot_{prefix}_input.csv")
        normalized_path = self._path(f"_tmp_snapshot_{prefix}_normalized.csv")
        unmatched_path = self._path(f"_tmp_snapshot_{prefix}_unmatched.csv")
        evidence_staging_path = self._path(f"_tmp_snapshot_{prefix}_evidence_staging.csv")
        summary_path = self._path(f"_tmp_snapshot_{prefix}_summary.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, master_rows)
        self._write_csv(snapshot_path, SNAPSHOT_INPUT_FIELDS, snapshot_rows)
        run_fundamentals_snapshot_ingestion(
            fundamentals_master_path=str(master_path),
            snapshot_input_path=str(snapshot_path),
            normalized_output=str(normalized_path),
            unmatched_output=str(unmatched_path),
            evidence_staging_output=str(evidence_staging_path),
            summary_output=str(summary_path),
            template_output=None,
        )
        return master_path, snapshot_path, normalized_path, unmatched_path, evidence_staging_path, summary_path

    def test_valid_snapshot_generates_normalized_evidence_staging_and_summary(self) -> None:
        _master_path, _snapshot_path, normalized_path, unmatched_path, evidence_staging_path, summary_path = self._run_engine(
            master_rows=[master_row()],
            snapshot_rows=[snapshot_row()],
            prefix="valid",
        )

        normalized_rows = read_csv_rows(normalized_path)
        unmatched_rows = read_csv_rows(unmatched_path)
        evidence_rows = read_csv_rows(evidence_staging_path)
        summary_rows = read_csv_rows(summary_path)
        self.assertEqual(set(normalized_rows[0]), set(NORMALIZED_FIELDS))
        self.assertEqual(normalized_rows[0]["ticker"], "MSFT")
        self.assertEqual(normalized_rows[0]["isin"], "US5949181045")
        self.assertEqual(normalized_rows[0]["match_method"], "TICKER+ISIN")
        self.assertEqual(unmatched_rows, [])
        self.assertEqual(len(evidence_rows), 2)
        self.assertEqual(set(summary_rows[0]), set(SUMMARY_FIELDS))
        self.assertEqual(summary_rows[0]["snapshot_rows_total"], "1")
        self.assertEqual(summary_rows[0]["matched_rows"], "1")
        self.assertEqual(summary_rows[0]["unmatched_rows"], "0")
        self.assertEqual(summary_rows[0]["evidence_rows_generated"], "2")

    def test_unmatched_snapshot_rows_are_written_without_hard_failure(self) -> None:
        _master_path, _snapshot_path, normalized_path, unmatched_path, evidence_staging_path, summary_path = self._run_engine(
            master_rows=[master_row()],
            snapshot_rows=[snapshot_row(ticker="UNMATCHED", isin="US0000000001", company_name="Unknown Co")],
            prefix="unmatched",
        )

        normalized_rows = read_csv_rows(normalized_path)
        unmatched_rows = read_csv_rows(unmatched_path)
        evidence_rows = read_csv_rows(evidence_staging_path)
        summary_rows = read_csv_rows(summary_path)
        self.assertEqual(normalized_rows, [])
        self.assertEqual(set(unmatched_rows[0]), set(UNMATCHED_FIELDS))
        self.assertEqual(unmatched_rows[0]["ticker"], "UNMATCHED")
        self.assertIn("No exact ticker/isin match", unmatched_rows[0]["unmatched_reason"])
        self.assertEqual(evidence_rows, [])
        self.assertEqual(summary_rows[0]["matched_rows"], "0")
        self.assertEqual(summary_rows[0]["unmatched_rows"], "1")

    def test_conflicting_duplicate_snapshot_rows_fail_fast(self) -> None:
        with self.assertRaisesRegex(ValueError, "conflicting duplicate snapshot identity"):
            self._run_engine(
                master_rows=[master_row()],
                snapshot_rows=[
                    snapshot_row(roic="25"),
                    snapshot_row(roic="27"),
                ],
                prefix="conflict",
            )

    def test_conflicting_ticker_isin_match_fails_fast(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires ticker and isin to match the same personal fundamentals master row"):
            self._run_engine(
                master_rows=[master_row()],
                snapshot_rows=[snapshot_row(isin="US0000000001")],
                prefix="identity_conflict",
            )

    def test_evidence_staging_rows_follow_existing_evidence_contract(self) -> None:
        _master_path, _snapshot_path, _normalized_path, _unmatched_path, evidence_staging_path, _summary_path = self._run_engine(
            master_rows=[master_row()],
            snapshot_rows=[snapshot_row()],
            prefix="evidence_contract",
        )

        evidence_rows = read_csv_rows(evidence_staging_path)
        self.assertEqual(set(evidence_rows[0]), set(EVIDENCE_INPUT_FIELDS))
        self.assertEqual({row["kpi_name"] for row in evidence_rows}, {"roic", "fcf_margin"})
        self.assertTrue(all(row["source_type"] == "SNAPSHOT_IMPORT" for row in evidence_rows))
        self.assertTrue(all(row["verification_status"] == "UNVERIFIED" for row in evidence_rows))
        self.assertTrue(all(row["data_quality_flag"] == "REVIEW" for row in evidence_rows))
        self.assertTrue(all(row["reported_unit"] == "percent" for row in evidence_rows))

    def test_snapshot_template_writer_creates_header_only_template(self) -> None:
        template_path = self._path("_tmp_snapshot_template.csv")

        write_snapshot_template(str(template_path))

        self.assertTrue(template_path.exists())
        self.assertEqual(read_csv_rows(template_path), [])
        with template_path.open("r", encoding="utf-8") as handle:
            header = handle.readline().strip()
        self.assertEqual(header.split(","), SNAPSHOT_INPUT_FIELDS)


if __name__ == "__main__":
    unittest.main()
