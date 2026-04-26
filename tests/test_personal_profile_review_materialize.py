from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.fundamentals_profile_engine import PROFILE_REVIEW_INPUT_FIELDS
from src.personal_profile_review_materialize import EXACT_MAP_FIELDS, run_personal_profile_review_materialize


def seed_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    notes: str = "SEC identity seed; company_type_profile must be reviewed manually.",
) -> dict[str, str]:
    row = {field: "" for field in PROFILE_REVIEW_INPUT_FIELDS}
    row.update(
        {
            "ticker": ticker,
            "isin": isin,
            "company_name": company_name,
            "notes": notes,
        }
    )
    return row


def exact_map_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_type_profile: str = "STANDARD",
    profile_reason: str = "operating company",
    review_status: str = "APPROVED",
    review_author: str = "analyst_a",
    review_as_of_date: str = "2026-04-26",
    source_name: str = "manual_review",
    source_reference: str = "internal profile memo",
    notes: str = "reviewed exact map row",
) -> dict[str, str]:
    return {
        "ticker": ticker,
        "isin": isin,
        "company_type_profile": company_type_profile,
        "profile_reason": profile_reason,
        "review_status": review_status,
        "review_author": review_author,
        "review_as_of_date": review_as_of_date,
        "source_name": source_name,
        "source_reference": source_reference,
        "notes": notes,
    }


class PersonalProfileReviewMaterializeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_paths: list[Path] = []

    def tearDown(self) -> None:
        for path in reversed(self.temp_paths):
            if path.exists():
                path.unlink()

    def _path(self, name: str) -> Path:
        path = Path("tests") / f"_tmp_profile_review_materialize_{name}"
        self.temp_paths.append(path)
        return path

    def _write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_seed_is_materialized_as_review_rows(self) -> None:
        seed_path = self._path("seed.csv")
        output_path = self._path("review.csv")
        self._write_csv(seed_path, PROFILE_REVIEW_INPUT_FIELDS, [seed_row()])

        result = run_personal_profile_review_materialize(
            seed_input=str(seed_path),
            output=str(output_path),
            exact_map_input="",
        )

        rows = read_csv_rows(output_path)
        self.assertEqual(result.seed_rows_total, 1)
        self.assertEqual(result.review_rows_total, 1)
        self.assertEqual(result.approved_rows_total, 0)
        self.assertEqual(rows[0]["ticker"], "MSFT")
        self.assertEqual(rows[0]["isin"], "US5949181045")
        self.assertEqual(rows[0]["proposed_company_type_profile"], "")
        self.assertEqual(rows[0]["review_status"], "REVIEW")
        self.assertEqual(rows[0]["review_author"], "")
        self.assertEqual(rows[0]["source_name"], "")

    def test_existing_output_blocks_without_overwrite(self) -> None:
        seed_path = self._path("seed.csv")
        output_path = self._path("review.csv")
        self._write_csv(seed_path, PROFILE_REVIEW_INPUT_FIELDS, [seed_row()])
        self._write_csv(output_path, PROFILE_REVIEW_INPUT_FIELDS, [])

        with self.assertRaisesRegex(ValueError, "output already exists"):
            run_personal_profile_review_materialize(
                seed_input=str(seed_path),
                output=str(output_path),
                exact_map_input="",
            )

    def test_exact_map_fills_only_matching_ticker_isin(self) -> None:
        seed_path = self._path("seed.csv")
        map_path = self._path("map.csv")
        output_path = self._path("review.csv")
        self._write_csv(
            seed_path,
            PROFILE_REVIEW_INPUT_FIELDS,
            [
                seed_row(ticker="MSFT", isin="US5949181045", company_name="Microsoft Corp"),
                seed_row(ticker="AAPL", isin="US0378331005", company_name="Apple Inc"),
            ],
        )
        self._write_csv(
            map_path,
            EXACT_MAP_FIELDS,
            [
                exact_map_row(ticker="MSFT", isin="US5949181045"),
                exact_map_row(ticker="NVDA", isin="US67066G1040"),
            ],
        )

        result = run_personal_profile_review_materialize(
            seed_input=str(seed_path),
            output=str(output_path),
            exact_map_input=str(map_path),
        )

        rows = {row["ticker"]: row for row in read_csv_rows(output_path)}
        self.assertEqual(result.mapped_rows_total, 1)
        self.assertEqual(rows["MSFT"]["proposed_company_type_profile"], "STANDARD")
        self.assertEqual(rows["MSFT"]["review_status"], "APPROVED")
        self.assertEqual(rows["AAPL"]["proposed_company_type_profile"], "")
        self.assertEqual(rows["AAPL"]["review_status"], "REVIEW")
        self.assertIn("exact_map_unmatched_rows=3", result.warnings)

    def test_approved_other_without_reason_fails_fast(self) -> None:
        seed_path = self._path("seed.csv")
        map_path = self._path("map.csv")
        output_path = self._path("review.csv")
        self._write_csv(seed_path, PROFILE_REVIEW_INPUT_FIELDS, [seed_row()])
        self._write_csv(
            map_path,
            EXACT_MAP_FIELDS,
            [exact_map_row(company_type_profile="OTHER", profile_reason="")],
        )

        with self.assertRaisesRegex(ValueError, "company_type_profile=OTHER but blank profile_reason"):
            run_personal_profile_review_materialize(
                seed_input=str(seed_path),
                output=str(output_path),
                exact_map_input=str(map_path),
            )

    def test_approved_without_review_metadata_fails_fast(self) -> None:
        seed_path = self._path("seed.csv")
        map_path = self._path("map.csv")
        output_path = self._path("review.csv")
        self._write_csv(seed_path, PROFILE_REVIEW_INPUT_FIELDS, [seed_row()])
        self._write_csv(
            map_path,
            EXACT_MAP_FIELDS,
            [exact_map_row(review_author="", review_as_of_date="", source_name="", source_reference="")],
        )

        with self.assertRaisesRegex(ValueError, "review_status=APPROVED but missing required review metadata"):
            run_personal_profile_review_materialize(
                seed_input=str(seed_path),
                output=str(output_path),
                exact_map_input=str(map_path),
            )

    def test_dry_run_does_not_write_output_or_report(self) -> None:
        seed_path = self._path("seed.csv")
        output_path = self._path("review.csv")
        report_path = self._path("report.md")
        self._write_csv(seed_path, PROFILE_REVIEW_INPUT_FIELDS, [seed_row()])

        result = run_personal_profile_review_materialize(
            seed_input=str(seed_path),
            output=str(output_path),
            exact_map_input="",
            dry_run=True,
            report_output=str(report_path),
        )

        self.assertEqual(result.review_rows_total, 1)
        self.assertFalse(output_path.exists())
        self.assertFalse(report_path.exists())

    def test_output_sorting_is_deterministic(self) -> None:
        seed_path = self._path("seed.csv")
        output_path = self._path("review.csv")
        self._write_csv(
            seed_path,
            PROFILE_REVIEW_INPUT_FIELDS,
            [
                seed_row(ticker="MSFT", isin="US5949181045", company_name="Microsoft Corp"),
                seed_row(ticker="AAPL", isin="US0378331005", company_name="Apple Inc"),
                seed_row(ticker="BRK-B", isin="US0846707026", company_name="Berkshire Hathaway Inc"),
            ],
        )

        run_personal_profile_review_materialize(
            seed_input=str(seed_path),
            output=str(output_path),
            exact_map_input="",
        )

        rows = read_csv_rows(output_path)
        self.assertEqual([row["ticker"] for row in rows], ["AAPL", "BRK-B", "MSFT"])


if __name__ == "__main__":
    unittest.main()
