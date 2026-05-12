from __future__ import annotations

import csv
import subprocess
import sys
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.fundamentals_master import PERSONAL_MASTER_FIELDS
from src.personal_sec_scope_prepare import (
    REVIEW_FIELDS,
    SUMMARY_FIELDS,
    build_audit_rows,
    run_personal_sec_scope_prepare,
)


def master_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    asset_type: str = "STOCK",
    country: str = "USA",
) -> dict[str, str]:
    row = {field: "" for field in PERSONAL_MASTER_FIELDS}
    row.update(
        {
            "ticker": ticker,
            "isin": isin,
            "company_name": company_name,
            "currency": "USD",
            "sector": "Technology",
            "country": country,
            "asset_type": asset_type,
            "company_type_profile": "STANDARD",
            "source_name": "unit_master_fixture",
            "source_as_of_date": "2026-04-10",
            "fiscal_period": "FY",
            "fiscal_year": "2025",
            "market_price_date": "2026-04-10",
            "calculation_version": "test",
            "data_quality_flag": "MISSING_DATA",
            "notes": "unit fixture",
            "sleeve": "SINGLE_STOCK",
            "current_price_eur": "100",
            "mandate_fit_score": "80",
        }
    )
    return row


class PersonalSecScopePrepareTests(unittest.TestCase):
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

    def test_master_ticker_equals_isin_and_unknown_country_are_blockers(self) -> None:
        rows = build_audit_rows(
            [
                master_row(
                    ticker="US5949181045",
                    isin="US5949181045",
                    country="Unknown",
                    company_name="Microsoft Corp",
                )
            ]
        )

        self.assertEqual(rows[0]["master_row_number"], "2")
        self.assertEqual(rows[0]["ticker_equals_isin_flag"], "true")
        self.assertEqual(rows[0]["ticker_looks_like_isin_flag"], "true")
        self.assertEqual(rows[0]["sec_scope_supported_now_flag"], "false")
        self.assertEqual(
            rows[0]["sec_scope_blocker_reason"],
            "COUNTRY_UNKNOWN;TICKER_EQUALS_ISIN;TICKER_LOOKS_LIKE_ISIN",
        )
        self.assertEqual(rows[0]["candidate_for_us_stock_review_flag"], "true")

    def test_supported_now_only_for_valid_us_stock_ticker(self) -> None:
        rows = build_audit_rows(
            [
                master_row(ticker="MSFT", isin="US5949181045", country="USA", asset_type="STOCK"),
                master_row(ticker="ASML", isin="NL0010273215", country="NETHERLANDS", asset_type="STOCK"),
                master_row(ticker="SPY", isin="US78462F1030", country="USA", asset_type="ETF"),
            ]
        )

        by_ticker = {row["original_ticker"]: row for row in rows}
        self.assertEqual(by_ticker["MSFT"]["sec_scope_supported_now_flag"], "true")
        self.assertEqual(by_ticker["ASML"]["sec_scope_supported_now_flag"], "false")
        self.assertIn("COUNTRY_UNSUPPORTED", by_ticker["ASML"]["sec_scope_blocker_reason"])
        self.assertEqual(by_ticker["SPY"]["sec_scope_supported_now_flag"], "false")
        self.assertIn("UNSUPPORTED_ASSET_TYPE", by_ticker["SPY"]["sec_scope_blocker_reason"])

    def test_prepare_writes_review_summary_and_blockers_without_master_mutation(self) -> None:
        master_path = self._path("_tmp_sec_scope_master.csv")
        review_path = self._path("_tmp_sec_scope_review.csv")
        summary_path = self._path("_tmp_sec_scope_summary.csv")
        blockers_path = self._path("_tmp_sec_scope_blockers.csv")
        private_identity_path = Path("data/raw/private/fundamentals/personal_sec_identity_map.csv")
        private_existed_before = private_identity_path.exists()
        self._write_csv(
            master_path,
            PERSONAL_MASTER_FIELDS,
            [
                master_row(ticker="US5949181045", isin="US5949181045", country="Unknown"),
                master_row(ticker="MSFT", isin="US5949181045", country="USA"),
            ],
        )
        before_bytes = master_path.read_bytes()

        run_personal_sec_scope_prepare(
            master_input=str(master_path),
            review_output=str(review_path),
            summary_output=str(summary_path),
            blockers_output=str(blockers_path),
        )

        self.assertEqual(master_path.read_bytes(), before_bytes)
        self.assertEqual(private_identity_path.exists(), private_existed_before)
        review_rows = read_csv_rows(review_path)
        self.assertEqual(set(review_rows[0]), set(REVIEW_FIELDS))
        self.assertEqual(review_rows[0]["review_status"], "BLANK")
        self.assertEqual(review_rows[0]["reviewed_canonical_ticker"], "")
        summary = read_csv_rows(summary_path)[0]
        self.assertEqual(set(summary), set(SUMMARY_FIELDS))
        self.assertEqual(summary["master_rows_total"], "2")
        self.assertEqual(summary["stock_rows_total"], "2")
        self.assertEqual(summary["sec_scope_supported_now_total"], "1")
        self.assertEqual(summary["ticker_equals_isin_total"], "1")
        self.assertEqual(summary["country_unknown_total"], "1")
        blockers = read_csv_rows(blockers_path)
        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0]["original_ticker"], "US5949181045")

    def test_summary_only_uses_reviewed_rows_without_overwriting_review(self) -> None:
        master_path = self._path("_tmp_sec_scope_summary_master.csv")
        review_path = self._path("_tmp_sec_scope_summary_review.csv")
        summary_path = self._path("_tmp_sec_scope_summary_only.csv")
        blockers_path = self._path("_tmp_sec_scope_summary_blockers.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])
        review_row = {field: "" for field in REVIEW_FIELDS}
        review_row.update(
            {
                "master_row_number": "2",
                "original_ticker": "MSFT",
                "original_isin": "US5949181045",
                "company_name": "Microsoft Corp",
                "original_country": "USA",
                "original_asset_type": "STOCK",
                "reviewed_asset_type_scope": "STOCK",
                "reviewed_country": "USA",
                "reviewed_canonical_ticker": "MSFT",
                "reviewed_cik": "789019",
                "reviewed_enabled": "true",
                "review_status": "REVIEWED_APPROVE",
            }
        )
        invalid_cik_row = dict(review_row)
        invalid_cik_row["master_row_number"] = "3"
        invalid_cik_row["reviewed_cik"] = "not-a-cik"
        self._write_csv(review_path, REVIEW_FIELDS, [review_row, invalid_cik_row])
        before_review = review_path.read_bytes()

        run_personal_sec_scope_prepare(
            master_input=str(master_path),
            review_output=str(self._path("_tmp_sec_scope_should_not_write.csv")),
            summary_output=str(summary_path),
            blockers_output=str(blockers_path),
            review_input=str(review_path),
            summary_only=True,
        )

        self.assertEqual(review_path.read_bytes(), before_review)
        summary = read_csv_rows(summary_path)[0]
        self.assertEqual(summary["reviewed_us_stock_scope_total"], "2")
        self.assertEqual(summary["reviewed_complete_sec_identity_total"], "1")
        self.assertEqual(summary["exportable_identity_rows_total"], "1")

    def test_cli_review_template_only_smoke(self) -> None:
        master_path = self._path("_tmp_sec_scope_cli_master.csv")
        review_path = self._path("_tmp_sec_scope_cli_review.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.personal_sec_scope_prepare",
                "--master-input",
                str(master_path),
                "--review-output",
                str(review_path),
                "--review-template-only",
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(read_csv_rows(review_path)[0]), set(REVIEW_FIELDS))


if __name__ == "__main__":
    unittest.main()
