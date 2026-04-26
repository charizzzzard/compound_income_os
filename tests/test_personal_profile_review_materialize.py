from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.fundamentals_master import PERSONAL_MASTER_FIELDS
from src.fundamentals_profile_engine import PROFILE_REVIEW_INPUT_FIELDS, run_fundamentals_profile_engine
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


def master_row(
    *,
    ticker: str = "US0378331005",
    isin: str = "US0378331005",
    company_name: str = "Apple Inc. Registered Shares o.N.",
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
            "country": "US",
            "asset_type": "STOCK",
            "company_type_profile": company_type_profile,
            "source_name": "unit_master_fixture",
            "source_as_of_date": "2026-04-26",
            "fiscal_period": "FY",
            "fiscal_year": "2025",
            "report_date": "2026-04-26",
            "filing_date": "2026-04-26",
            "market_price_date": "2026-04-26",
            "calculation_version": "test",
            "data_quality_flag": "MISSING_DATA",
            "notes": "unit master fixture",
            "sleeve": "SINGLE_STOCK",
            "current_price_eur": "100",
            "mandate_fit_score": "80",
        }
    )
    return row


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

    def _missing_master_path(self, name: str = "missing_master.csv") -> Path:
        return self._path(name)

    def test_seed_is_materialized_as_review_rows(self) -> None:
        seed_path = self._path("seed.csv")
        output_path = self._path("review.csv")
        self._write_csv(seed_path, PROFILE_REVIEW_INPUT_FIELDS, [seed_row()])

        result = run_personal_profile_review_materialize(
            seed_input=str(seed_path),
            fundamentals_master_input=str(self._missing_master_path()),
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
                fundamentals_master_input=str(self._missing_master_path()),
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
            fundamentals_master_input=str(self._missing_master_path()),
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
                fundamentals_master_input=str(self._missing_master_path()),
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
                fundamentals_master_input=str(self._missing_master_path()),
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
            fundamentals_master_input=str(self._missing_master_path()),
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
            fundamentals_master_input=str(self._missing_master_path()),
            output=str(output_path),
            exact_map_input="",
        )

        rows = read_csv_rows(output_path)
        self.assertEqual([row["ticker"] for row in rows], ["AAPL", "BRK-B", "MSFT"])

    def test_seed_identifier_is_rewritten_from_exact_master_isin(self) -> None:
        seed_path = self._path("master_bridge_seed.csv")
        master_path = self._path("master_bridge_master.csv")
        output_path = self._path("master_bridge_review.csv")
        self._write_csv(seed_path, PROFILE_REVIEW_INPUT_FIELDS, [seed_row(ticker="AAPL", isin="US0378331005")])
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])

        result = run_personal_profile_review_materialize(
            seed_input=str(seed_path),
            fundamentals_master_input=str(master_path),
            output=str(output_path),
            exact_map_input="",
        )

        rows = read_csv_rows(output_path)
        self.assertEqual(result.master_rows_total, 1)
        self.assertEqual(result.master_identity_matched_rows_total, 1)
        self.assertEqual(result.master_identity_missing_rows_total, 0)
        self.assertEqual(rows[0]["ticker"], "US0378331005")
        self.assertEqual(rows[0]["isin"], "US0378331005")
        self.assertEqual(rows[0]["company_name"], "Apple Inc. Registered Shares o.N.")
        self.assertIn("sec_identity_ticker=AAPL", rows[0]["notes"])

    def test_isin_only_exact_map_applies_after_master_identifier_rewrite(self) -> None:
        seed_path = self._path("isin_map_seed.csv")
        master_path = self._path("isin_map_master.csv")
        map_path = self._path("isin_map.csv")
        output_path = self._path("isin_map_review.csv")
        self._write_csv(seed_path, PROFILE_REVIEW_INPUT_FIELDS, [seed_row(ticker="AAPL", isin="US0378331005")])
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])
        self._write_csv(map_path, EXACT_MAP_FIELDS, [exact_map_row(ticker="", isin="US0378331005", notes="mapped by isin")])

        result = run_personal_profile_review_materialize(
            seed_input=str(seed_path),
            fundamentals_master_input=str(master_path),
            output=str(output_path),
            exact_map_input=str(map_path),
        )

        rows = read_csv_rows(output_path)
        self.assertEqual(result.mapped_rows_total, 1)
        self.assertEqual(rows[0]["ticker"], "US0378331005")
        self.assertEqual(rows[0]["proposed_company_type_profile"], "STANDARD")
        self.assertEqual(rows[0]["review_status"], "APPROVED")
        self.assertIn("sec_identity_ticker=AAPL", rows[0]["notes"])

    def test_duplicate_master_isin_fails_fast(self) -> None:
        seed_path = self._path("duplicate_master_seed.csv")
        master_path = self._path("duplicate_master.csv")
        output_path = self._path("duplicate_master_review.csv")
        self._write_csv(seed_path, PROFILE_REVIEW_INPUT_FIELDS, [seed_row(ticker="AAPL", isin="US0378331005")])
        self._write_csv(
            master_path,
            PERSONAL_MASTER_FIELDS,
            [
                master_row(ticker="US0378331005", isin="US0378331005"),
                master_row(ticker="AAPL-DUP", isin="US0378331005"),
            ],
        )

        with self.assertRaisesRegex(ValueError, "duplicate isin"):
            run_personal_profile_review_materialize(
                seed_input=str(seed_path),
                fundamentals_master_input=str(master_path),
                output=str(output_path),
                exact_map_input="",
            )

    def test_missing_master_identity_warns_without_blocking(self) -> None:
        seed_path = self._path("missing_identity_seed.csv")
        master_path = self._path("missing_identity_master.csv")
        output_path = self._path("missing_identity_review.csv")
        self._write_csv(seed_path, PROFILE_REVIEW_INPUT_FIELDS, [seed_row(ticker="AAPL", isin="US0378331005")])
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row(ticker="MSFT", isin="US5949181045", company_name="Microsoft")])

        result = run_personal_profile_review_materialize(
            seed_input=str(seed_path),
            fundamentals_master_input=str(master_path),
            output=str(output_path),
            exact_map_input="",
        )

        rows = read_csv_rows(output_path)
        self.assertEqual(result.master_identity_matched_rows_total, 0)
        self.assertEqual(result.master_identity_missing_rows_total, 1)
        self.assertIn("master_identity_missing_for_isin=US0378331005", result.warnings)
        self.assertEqual(rows[0]["ticker"], "AAPL")
        self.assertEqual(rows[0]["isin"], "US0378331005")

    def test_generated_review_is_accepted_by_profile_engine_with_master_isin_ticker(self) -> None:
        seed_path = self._path("profile_engine_seed.csv")
        master_path = self._path("profile_engine_master.csv")
        map_path = self._path("profile_engine_map.csv")
        review_path = self._path("profile_engine_review.csv")
        registry_path = self._path("profile_engine_registry.csv")
        backlog_path = self._path("profile_engine_backlog.csv")
        profiled_path = self._path("profile_engine_profiled.csv")
        template_path = self._path("profile_engine_template.csv")
        self._write_csv(seed_path, PROFILE_REVIEW_INPUT_FIELDS, [seed_row(ticker="AAPL", isin="US0378331005")])
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])
        self._write_csv(map_path, EXACT_MAP_FIELDS, [exact_map_row(ticker="", isin="US0378331005", profile_reason="operating company")])

        run_personal_profile_review_materialize(
            seed_input=str(seed_path),
            fundamentals_master_input=str(master_path),
            output=str(review_path),
            exact_map_input=str(map_path),
        )
        run_fundamentals_profile_engine(
            fundamentals_master_path=str(master_path),
            profile_review_input_path=str(review_path),
            registry_output=str(registry_path),
            backlog_output=str(backlog_path),
            profiled_master_output=str(profiled_path),
            template_output=str(template_path),
        )

        registry_rows = read_csv_rows(registry_path)
        profiled_rows = read_csv_rows(profiled_path)
        self.assertEqual(registry_rows[0]["ticker"], "US0378331005")
        self.assertEqual(registry_rows[0]["projection_applied"], "True")
        self.assertEqual(profiled_rows[0]["company_type_profile"], "STANDARD")


if __name__ == "__main__":
    unittest.main()
