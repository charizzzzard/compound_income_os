from __future__ import annotations

import csv
import subprocess
import sys
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.external_sec_companyfacts_fetch import IDENTITY_MAP_FIELDS
from src.personal_sec_identity_export import build_identity_map_rows, run_personal_sec_identity_export
from src.personal_sec_scope_prepare import REVIEW_FIELDS


def review_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    cik: str = "789019",
    status: str = "REVIEWED_APPROVE",
    asset_type: str = "STOCK",
    country: str = "USA",
    enabled: str = "true",
    sec_entity_name: str = "MICROSOFT CORP",
    notes: str = "reviewed identity",
) -> dict[str, str]:
    row = {field: "" for field in REVIEW_FIELDS}
    row.update(
        {
            "master_row_number": "2",
            "original_ticker": "US5949181045",
            "original_isin": isin,
            "company_name": company_name,
            "original_country": "Unknown",
            "original_asset_type": "STOCK",
            "ticker_equals_isin_flag": "true",
            "ticker_looks_like_isin_flag": "true",
            "sec_scope_supported_now_flag": "false",
            "sec_scope_blocker_reason": "COUNTRY_UNKNOWN;TICKER_EQUALS_ISIN;TICKER_LOOKS_LIKE_ISIN",
            "candidate_for_us_stock_review_flag": "true",
            "reviewed_asset_type_scope": asset_type,
            "reviewed_country": country,
            "reviewed_canonical_ticker": ticker,
            "reviewed_cik": cik,
            "reviewed_enabled": enabled,
            "reviewed_sec_entity_name": sec_entity_name,
            "review_status": status,
            "review_notes": notes,
        }
    )
    return row


class PersonalSecIdentityExportTests(unittest.TestCase):
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

    def test_export_writes_only_complete_reviewed_enabled_us_stock_rows(self) -> None:
        review_path = self._path("_tmp_sec_identity_export_review.csv")
        output_path = self._path("_tmp_sec_identity_export_map.csv")
        self._write_csv(
            review_path,
            REVIEW_FIELDS,
            [
                review_row(),
                review_row(ticker="AAPL", isin="US0378331005", cik="", notes="missing cik"),
                review_row(ticker="V", isin="US92826C8394", cik="1403161", status="REVIEWED_REJECT"),
                review_row(ticker="ASML", isin="NL0010273215", cik="937966", country="NETHERLANDS"),
                review_row(ticker="DIS", isin="US2546871060", cik="1744489", enabled="false"),
            ],
        )

        result = run_personal_sec_identity_export(review_input=str(review_path), output=str(output_path))

        self.assertEqual(result["review_rows_total"], 5)
        self.assertEqual(result["exportable_identity_rows_total"], 1)
        rows = read_csv_rows(output_path)
        self.assertEqual(set(rows[0]), set(IDENTITY_MAP_FIELDS))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticker"], "MSFT")
        self.assertEqual(rows[0]["isin"], "US5949181045")
        self.assertEqual(rows[0]["cik"], "0000789019")
        self.assertEqual(rows[0]["enabled"], "True")

    def test_conflicting_duplicate_export_rows_fail_fast(self) -> None:
        rows = [
            review_row(notes="first reviewed identity"),
            review_row(company_name="Microsoft Corporation", notes="second reviewed identity"),
        ]

        with self.assertRaisesRegex(ValueError, "conflicting duplicate identity row"):
            build_identity_map_rows(rows)

    def test_identical_duplicate_export_rows_are_deduped_deterministically(self) -> None:
        rows = build_identity_map_rows([review_row(), review_row()])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticker"], "MSFT")
        self.assertEqual(rows[0]["cik"], "0000789019")

    def test_dry_run_does_not_write_private_identity_map(self) -> None:
        review_path = self._path("_tmp_sec_identity_export_dry_review.csv")
        output_path = self._path("_tmp_sec_identity_export_dry_map.csv")
        self._write_csv(review_path, REVIEW_FIELDS, [review_row()])

        result = run_personal_sec_identity_export(review_input=str(review_path), output=str(output_path), dry_run=True)

        self.assertEqual(result["exportable_identity_rows_total"], 1)
        self.assertFalse(output_path.exists())

    def test_cli_dry_run_smoke(self) -> None:
        review_path = self._path("_tmp_sec_identity_export_cli_review.csv")
        output_path = self._path("_tmp_sec_identity_export_cli_map.csv")
        self._write_csv(review_path, REVIEW_FIELDS, [review_row()])

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.personal_sec_identity_export",
                "--review-input",
                str(review_path),
                "--output",
                str(output_path),
                "--dry-run",
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(output_path.exists())


if __name__ == "__main__":
    unittest.main()
