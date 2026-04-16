from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.fundamentals_master import CORE_KPI_FIELDS, PERSONAL_MASTER_FIELDS
from src.fundamentals_profile_engine import (
    PROFILE_REVIEW_BACKLOG_FIELDS,
    PROFILE_REVIEW_INPUT_FIELDS,
    PROFILE_REVIEW_REGISTRY_FIELDS,
    run_fundamentals_profile_engine,
    write_profile_review_template,
)


def master_row(
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    profile: str = "OTHER",
    asset_type: str = "STOCK",
    notes: str = "unit fixture",
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
            "asset_type": asset_type,
            "company_type_profile": profile,
            "source_name": "manual_master_fixture",
            "source_as_of_date": "2026-03-31",
            "fiscal_period": "FY",
            "fiscal_year": "2025",
            "report_date": "2026-03-31",
            "filing_date": "2026-04-01",
            "market_price_date": "2026-03-31",
            "calculation_version": "test",
            "data_quality_flag": "MISSING_DATA",
            "notes": notes,
            "sleeve": "SINGLE_STOCK",
            "current_price_eur": "100",
            "mandate_fit_score": "80",
        }
    )
    for kpi_name in CORE_KPI_FIELDS:
        row.setdefault(kpi_name, "")
    return row


def profile_review_row(
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    proposed_company_type_profile: str = "STANDARD",
    profile_reason: str = "operating company",
    review_status: str = "APPROVED",
    review_author: str = "analyst_a",
    review_as_of_date: str = "2026-04-16",
    source_name: str = "manual_profile_review",
    source_reference: str = "internal note 2026-04-16",
    notes: str = "fixture review",
) -> dict[str, str]:
    row = {field: "" for field in PROFILE_REVIEW_INPUT_FIELDS}
    row.update(
        {
            "ticker": ticker,
            "isin": isin,
            "company_name": company_name,
            "proposed_company_type_profile": proposed_company_type_profile,
            "profile_reason": profile_reason,
            "review_status": review_status,
            "review_author": review_author,
            "review_as_of_date": review_as_of_date,
            "source_name": source_name,
            "source_reference": source_reference,
            "notes": notes,
        }
    )
    return row


class FundamentalsProfileEngineTests(unittest.TestCase):
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
        master_rows: list[dict[str, str]],
        review_rows: list[dict[str, str]],
        prefix: str,
    ) -> tuple[Path, Path, Path, Path, Path, Path]:
        master_path = self._path(f"_tmp_profile_{prefix}_master.csv")
        review_path = self._path(f"_tmp_profile_{prefix}_input.csv")
        registry_path = self._path(f"_tmp_profile_{prefix}_registry.csv")
        backlog_path = self._path(f"_tmp_profile_{prefix}_backlog.csv")
        profiled_path = self._path(f"_tmp_profile_{prefix}_profiled.csv")
        template_path = self._path(f"_tmp_profile_{prefix}_template.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, master_rows)
        self._write_csv(review_path, PROFILE_REVIEW_INPUT_FIELDS, review_rows)
        run_fundamentals_profile_engine(
            fundamentals_master_path=str(master_path),
            profile_review_input_path=str(review_path),
            registry_output=str(registry_path),
            backlog_output=str(backlog_path),
            profiled_master_output=str(profiled_path),
            template_output=str(template_path),
        )
        return master_path, review_path, registry_path, backlog_path, profiled_path, template_path

    def test_valid_approved_review_projects_profiled_master_and_registry(self) -> None:
        _master_path, _review_path, registry_path, backlog_path, profiled_path, template_path = self._run_engine(
            [master_row()],
            [profile_review_row(proposed_company_type_profile="STANDARD", profile_reason="operating company")],
            "approved",
        )

        registry_rows = read_csv_rows(registry_path)
        backlog_rows = read_csv_rows(backlog_path)
        profiled_rows = read_csv_rows(profiled_path)
        self.assertEqual(len(registry_rows), 1)
        self.assertEqual(registry_rows[0]["projection_applied"], "True")
        self.assertEqual(registry_rows[0]["current_company_type_profile"], "OTHER")
        self.assertEqual(backlog_rows, [])
        self.assertEqual(profiled_rows[0]["company_type_profile"], "STANDARD")
        self.assertIn("profile_review_applied_profile=STANDARD", profiled_rows[0]["notes"])
        self.assertIn("profile_reason=operating company", profiled_rows[0]["notes"])
        with template_path.open("r", encoding="utf-8", newline="") as handle:
            self.assertEqual(next(csv.reader(handle)), PROFILE_REVIEW_INPUT_FIELDS)

    def test_other_profile_without_reason_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "proposed_company_type_profile=OTHER but blank profile_reason"):
            self._run_engine(
                [master_row()],
                [profile_review_row(proposed_company_type_profile="OTHER", profile_reason="")],
                "other_reason",
            )

    def test_conflicting_approved_rows_fail_fast_but_identical_duplicates_are_deduplicated(self) -> None:
        _master_path, _review_path, registry_path, _backlog_path, _profiled_path, _template_path = self._run_engine(
            [master_row()],
            [profile_review_row(), profile_review_row()],
            "dedupe",
        )
        self.assertEqual(len(read_csv_rows(registry_path)), 1)

        with self.assertRaisesRegex(ValueError, "conflicting APPROVED profile review rows"):
            self._run_engine(
                [master_row()],
                [
                    profile_review_row(proposed_company_type_profile="STANDARD", profile_reason="operating company"),
                    profile_review_row(
                        proposed_company_type_profile="FINANCIAL",
                        profile_reason="bank-like balance sheet",
                        review_author="analyst_b",
                        review_as_of_date="2026-04-17",
                        source_reference="internal note 2026-04-17",
                    ),
                ],
                "conflict",
            )

    def test_row_with_mismatched_ticker_and_isin_fails_fast(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires ticker and isin to match the same personal fundamentals master row"):
            self._run_engine(
                [master_row()],
                [profile_review_row(ticker="AAPL", isin="US5949181045", company_name="Microsoft Corp")],
                "ticker_isin_mismatch",
            )

    def test_pending_and_rejected_rows_stay_in_registry_and_backlog_without_projection(self) -> None:
        _master_path, _review_path, registry_path, backlog_path, profiled_path, _template_path = self._run_engine(
            [
                master_row(ticker="MSFT", isin="US5949181045", company_name="Microsoft Corp"),
                master_row(ticker="AAPL", isin="US0378331005", company_name="Apple Inc"),
            ],
            [
                profile_review_row(
                    ticker="MSFT",
                    isin="US5949181045",
                    company_name="Microsoft Corp",
                    proposed_company_type_profile="STANDARD",
                    review_status="PENDING",
                    profile_reason="pending review",
                ),
                profile_review_row(
                    ticker="AAPL",
                    isin="US0378331005",
                    company_name="Apple Inc",
                    proposed_company_type_profile="STANDARD",
                    review_status="REJECTED",
                    profile_reason="rejected review",
                    review_author="analyst_b",
                    source_reference="internal note 2026-04-18",
                ),
            ],
            "pending_rejected",
        )

        registry_rows = read_csv_rows(registry_path)
        backlog_rows = read_csv_rows(backlog_path)
        profiled_rows = {row["ticker"]: row for row in read_csv_rows(profiled_path)}
        self.assertEqual({row["review_status"] for row in registry_rows}, {"PENDING", "REJECTED"})
        self.assertEqual({row["ticker"] for row in backlog_rows}, {"MSFT", "AAPL"})
        self.assertEqual(profiled_rows["MSFT"]["company_type_profile"], "OTHER")
        self.assertEqual(profiled_rows["AAPL"]["company_type_profile"], "OTHER")
        self.assertNotIn("profile_review_applied_profile", profiled_rows["MSFT"]["notes"])
        self.assertNotIn("profile_review_applied_profile", profiled_rows["AAPL"]["notes"])

    def test_template_writer_matches_profile_review_contract(self) -> None:
        template_path = self._path("_tmp_profile_template_only.csv")

        write_profile_review_template(str(template_path))

        with template_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(reader.fieldnames, PROFILE_REVIEW_INPUT_FIELDS)
            self.assertEqual(list(reader), [])
        self.assertEqual(PROFILE_REVIEW_REGISTRY_FIELDS[0], "ticker")
        self.assertEqual(PROFILE_REVIEW_BACKLOG_FIELDS[0], "ticker")
