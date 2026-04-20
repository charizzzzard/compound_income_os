from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.external_sec_companyfacts_fetch import IDENTITY_MAP_FIELDS
from src.fundamentals_master import PERSONAL_MASTER_FIELDS
from src.fundamentals_profile_engine import PROFILE_REVIEW_INPUT_FIELDS
from src.personal_sec_profile_seed import PROFILE_SEED_SUMMARY_FIELDS, run_personal_sec_profile_seed
from src.personal_sec_scope_prepare import REVIEW_FIELDS


def master_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    country: str = "US",
    asset_type: str = "STOCK",
    company_type_profile: str = "OTHER",
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
            "company_type_profile": company_type_profile,
            "source_name": "unit_master_fixture",
            "source_as_of_date": "2026-04-20",
            "market_price_date": "2026-04-20",
            "calculation_version": "test",
            "data_quality_flag": "MISSING_DATA",
            "notes": "identity-applied fixture",
            "sleeve": "SINGLE_STOCK",
            "current_price_eur": "100",
            "mandate_fit_score": "80",
        }
    )
    return row


def review_row(
    *,
    reviewed_ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    cik: str = "0000789019",
    review_status: str = "REVIEWED_APPROVE",
    asset_type: str = "STOCK",
    country: str = "US",
    enabled: str = "true",
) -> dict[str, str]:
    row = {field: "" for field in REVIEW_FIELDS}
    row.update(
        {
            "master_row_number": "2",
            "original_ticker": isin,
            "original_isin": isin,
            "company_name": company_name,
            "original_country": "UNKNOWN",
            "original_asset_type": asset_type,
            "ticker_equals_isin_flag": "true",
            "ticker_looks_like_isin_flag": "true",
            "sec_scope_supported_now_flag": "false",
            "sec_scope_blocker_reason": "COUNTRY_UNKNOWN;TICKER_EQUALS_ISIN;TICKER_LOOKS_LIKE_ISIN",
            "candidate_for_us_stock_review_flag": "true",
            "reviewed_asset_type_scope": asset_type,
            "reviewed_country": country,
            "reviewed_canonical_ticker": reviewed_ticker,
            "reviewed_cik": cik,
            "reviewed_enabled": enabled,
            "reviewed_sec_entity_name": "MICROSOFT CORP",
            "review_status": review_status,
            "review_notes": "reviewed SEC identity",
        }
    )
    return row


def identity_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    cik: str = "0000789019",
    sec_entity_name: str = "MICROSOFT CORP",
    asset_type: str = "STOCK",
    country: str = "US",
    enabled: str = "True",
) -> dict[str, str]:
    return {
        "ticker": ticker,
        "isin": isin,
        "company_name": company_name,
        "cik": cik,
        "sec_entity_name": sec_entity_name,
        "asset_type": asset_type,
        "country": country,
        "enabled": enabled,
        "notes": "reviewed identity map row",
    }


class PersonalSecProfileSeedTests(unittest.TestCase):
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

    def test_builds_manual_seed_for_reviewed_approved_us_stock_rows(self) -> None:
        master_path = self._path("_tmp_sec_profile_seed_master.csv")
        review_path = self._path("_tmp_sec_profile_seed_review.csv")
        identity_map_path = self._path("_tmp_sec_profile_seed_map.csv")
        seed_path = self._path("_tmp_sec_profile_seed_output.csv")
        summary_path = self._path("_tmp_sec_profile_seed_summary.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])
        self._write_csv(review_path, REVIEW_FIELDS, [review_row()])
        self._write_csv(identity_map_path, IDENTITY_MAP_FIELDS, [identity_row()])

        outputs = run_personal_sec_profile_seed(
            identity_applied_master_input=str(master_path),
            review_input=str(review_path),
            identity_map_input=str(identity_map_path),
            seed_output=str(seed_path),
            summary_output=str(summary_path),
        )

        self.assertTrue(outputs["profile_review_seed"].exists())
        seed_rows = read_csv_rows(seed_path)
        summary_rows = read_csv_rows(summary_path)
        self.assertEqual(len(seed_rows), 1)
        self.assertEqual(set(seed_rows[0]), set(PROFILE_REVIEW_INPUT_FIELDS))
        self.assertEqual(seed_rows[0]["ticker"], "MSFT")
        self.assertEqual(seed_rows[0]["isin"], "US5949181045")
        self.assertEqual(seed_rows[0]["company_name"], "Microsoft Corp")
        self.assertEqual(seed_rows[0]["proposed_company_type_profile"], "")
        self.assertEqual(seed_rows[0]["review_status"], "")
        self.assertEqual(seed_rows[0]["source_name"], "")
        self.assertIn("company_type_profile must be reviewed manually", seed_rows[0]["notes"].lower())
        self.assertIn("current_company_type_profile=OTHER", seed_rows[0]["notes"])
        self.assertEqual(summary_rows[0]["seeded_rows_total"], "1")
        self.assertEqual(set(summary_rows[0]), set(PROFILE_SEED_SUMMARY_FIELDS))

    def test_non_approved_non_us_and_non_stock_rows_are_not_seeded(self) -> None:
        master_path = self._path("_tmp_sec_profile_seed_skip_master.csv")
        review_path = self._path("_tmp_sec_profile_seed_skip_review.csv")
        identity_map_path = self._path("_tmp_sec_profile_seed_skip_map.csv")
        seed_path = self._path("_tmp_sec_profile_seed_skip_output.csv")
        summary_path = self._path("_tmp_sec_profile_seed_skip_summary.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])
        self._write_csv(
            review_path,
            REVIEW_FIELDS,
            [
                review_row(review_status="REVIEWED_REJECT"),
                review_row(country="NETHERLANDS"),
                review_row(asset_type="ADR"),
            ],
        )
        self._write_csv(identity_map_path, IDENTITY_MAP_FIELDS, [identity_row()])

        run_personal_sec_profile_seed(
            identity_applied_master_input=str(master_path),
            review_input=str(review_path),
            identity_map_input=str(identity_map_path),
            seed_output=str(seed_path),
            summary_output=str(summary_path),
        )

        self.assertEqual(read_csv_rows(seed_path), [])
        summary_row = read_csv_rows(summary_path)[0]
        self.assertEqual(summary_row["review_rows_total"], "3")
        self.assertEqual(summary_row["exportable_review_rows_total"], "0")
        self.assertEqual(summary_row["seeded_rows_total"], "0")

    def test_master_conflict_fails_fast(self) -> None:
        master_path = self._path("_tmp_sec_profile_seed_conflict_master.csv")
        review_path = self._path("_tmp_sec_profile_seed_conflict_review.csv")
        identity_map_path = self._path("_tmp_sec_profile_seed_conflict_map.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row(ticker="US5949181045", country="Unknown")])
        self._write_csv(review_path, REVIEW_FIELDS, [review_row(reviewed_ticker="MSFT")])
        self._write_csv(identity_map_path, IDENTITY_MAP_FIELDS, [identity_row(ticker="MSFT", country="US")])

        with self.assertRaisesRegex(ValueError, "identity-applied master disagrees"):
            run_personal_sec_profile_seed(
                identity_applied_master_input=str(master_path),
                review_input=str(review_path),
                identity_map_input=str(identity_map_path),
                seed_output=str(self._path("_tmp_sec_profile_seed_conflict_output.csv")),
                summary_output=str(self._path("_tmp_sec_profile_seed_conflict_summary.csv")),
            )

    def test_input_files_are_not_mutated(self) -> None:
        master_path = self._path("_tmp_sec_profile_seed_immutable_master.csv")
        review_path = self._path("_tmp_sec_profile_seed_immutable_review.csv")
        identity_map_path = self._path("_tmp_sec_profile_seed_immutable_map.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])
        self._write_csv(review_path, REVIEW_FIELDS, [review_row()])
        self._write_csv(identity_map_path, IDENTITY_MAP_FIELDS, [identity_row()])
        before_master = master_path.read_bytes()
        before_review = review_path.read_bytes()
        before_identity = identity_map_path.read_bytes()

        run_personal_sec_profile_seed(
            identity_applied_master_input=str(master_path),
            review_input=str(review_path),
            identity_map_input=str(identity_map_path),
            seed_output=str(self._path("_tmp_sec_profile_seed_immutable_output.csv")),
            summary_output=str(self._path("_tmp_sec_profile_seed_immutable_summary.csv")),
        )

        self.assertEqual(master_path.read_bytes(), before_master)
        self.assertEqual(review_path.read_bytes(), before_review)
        self.assertEqual(identity_map_path.read_bytes(), before_identity)
