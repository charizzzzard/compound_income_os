from __future__ import annotations

import csv
import shutil
import unittest
from pathlib import Path

from src.personal_valuation_input_contract import run_personal_valuation_input_contract

ROOT = Path(__file__).resolve().parent.parent


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class PersonalValuationInputContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_valuation_input_contract"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.kpi_tier = self.tmp / "kpi_tier.csv"
        self.scores = self.tmp / "scores.csv"
        self.master = self.tmp / "master.csv"
        self.review_input = self.tmp / "review_input.csv"
        self.queue = self.tmp / "queue.csv"
        self.summary = self.tmp / "summary.csv"
        self.report = self.tmp / "report.md"
        write_csv(self.scores, ["ticker", "isin"], [{"ticker": "AAA", "isin": "US1"}])
        write_csv(self.master, ["ticker", "isin"], [{"ticker": "AAA", "isin": "US1"}])

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_kpi_rows(self, rows: list[dict[str, str]]) -> None:
        write_csv(
            self.kpi_tier,
            [
                "ticker",
                "isin",
                "company_name",
                "company_type_profile",
                "valuation_data_status",
                "missing_valuation_kpis",
            ],
            rows,
        )

    def write_review_rows(self, rows: list[dict[str, str]]) -> None:
        write_csv(
            self.review_input,
            [
                "ticker",
                "isin",
                "normalized_fcf_yield_pct",
                "target_fcf_yield_pct",
                "valuation_review_status",
                "valuation_source_type",
                "valuation_source_name",
                "valuation_source_reference",
                "valuation_source_as_of_date",
                "valuation_reviewed_by",
                "valuation_reviewed_at",
                "valuation_notes",
            ],
            rows,
        )

    def run_contract(self, *, review_input: str | None = None):
        return run_personal_valuation_input_contract(
            kpi_tier_input=str(self.kpi_tier),
            scores_input=str(self.scores),
            evidence_applied_master_input=str(self.master),
            review_input=str(self.review_input if review_input is None else review_input),
            queue_output=str(self.queue),
            summary_output=str(self.summary),
            report_output=str(self.report),
        )

    def summary_value(self, metric: str) -> str:
        return {row["metric"]: row["value"] for row in read_csv(self.summary)}[metric]

    def queue_row(self) -> dict[str, str]:
        return read_csv(self.queue)[0]

    def standard_gap(self) -> dict[str, str]:
        return {
            "ticker": "AAA",
            "isin": "US1",
            "company_name": "Alpha",
            "company_type_profile": "STANDARD",
            "valuation_data_status": "MISSING",
            "missing_valuation_kpis": "normalized_fcf_yield_pct; target_fcf_yield_pct",
        }

    def test_standard_missing_valuation_kpis_are_queued(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.run_contract(review_input=str(self.tmp / "missing_review.csv"))

        row = self.queue_row()
        self.assertEqual(row["ticker"], "AAA")
        self.assertEqual(row["valuation_input_status"], "MISSING")
        self.assertIn("VALUATION_REQUIRED_MISSING", row["reason_code"])
        self.assertEqual(self.summary_value("affected_standard_rows_count"), "1")

    def test_non_standard_row_is_not_applicable(self) -> None:
        self.write_kpi_rows(
            [
                {
                    "ticker": "ETF",
                    "isin": "US2",
                    "company_name": "Fund",
                    "company_type_profile": "OTHER",
                    "valuation_data_status": "NOT_APPLICABLE",
                    "missing_valuation_kpis": "",
                }
            ]
        )
        self.run_contract(review_input=str(self.tmp / "missing_review.csv"))

        self.assertEqual(read_csv(self.queue), [])
        self.assertEqual(self.summary_value("not_applicable_rows_count"), "1")
        self.assertIn("PROFILE_NOT_STANDARD", self.summary_value("reason_codes"))

    def test_missing_optional_review_input_is_not_a_crash(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.run_contract(review_input=str(self.tmp / "missing_review.csv"))

        self.assertEqual(self.summary_value("input_file_status"), "MISSING")
        self.assertEqual(self.summary_value("missing_rows_count"), "1")
        self.assertIn("INPUT_FILE_MISSING", self.summary_value("reason_codes"))

    def test_review_input_missing_value_remains_missing(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.write_review_rows(
            [
                {
                    "ticker": "AAA",
                    "isin": "US1",
                    "normalized_fcf_yield_pct": "",
                    "target_fcf_yield_pct": "4",
                    "valuation_review_status": "APPROVED",
                    "valuation_source_type": "MANUAL_REVIEW",
                    "valuation_source_name": "review",
                    "valuation_source_reference": "source",
                    "valuation_source_as_of_date": "2026-04-26",
                    "valuation_reviewed_by": "analyst",
                    "valuation_reviewed_at": "2026-04-26",
                    "valuation_notes": "private",
                }
            ]
        )
        self.run_contract()

        self.assertEqual(self.queue_row()["valuation_input_status"], "MISSING")
        self.assertIn("VALUATION_REQUIRED_MISSING", self.queue_row()["reason_code"])

    def test_source_reference_missing_requires_review(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.write_review_rows(
            [
                {
                    "ticker": "AAA",
                    "isin": "US1",
                    "normalized_fcf_yield_pct": "5",
                    "target_fcf_yield_pct": "4",
                    "valuation_review_status": "APPROVED",
                    "valuation_source_type": "MANUAL_REVIEW",
                    "valuation_source_name": "review",
                    "valuation_source_reference": "",
                    "valuation_source_as_of_date": "2026-04-26",
                    "valuation_reviewed_by": "analyst",
                    "valuation_reviewed_at": "2026-04-26",
                    "valuation_notes": "private",
                }
            ]
        )
        self.run_contract()

        self.assertEqual(self.queue_row()["valuation_input_status"], "REVIEW")
        self.assertIn("VALUATION_SOURCE_REFERENCE_MISSING", self.queue_row()["reason_code"])

    def test_approved_review_input_is_ok(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.write_review_rows(
            [
                {
                    "ticker": "AAA",
                    "isin": "US1",
                    "normalized_fcf_yield_pct": "5",
                    "target_fcf_yield_pct": "4",
                    "valuation_review_status": "APPROVED",
                    "valuation_source_type": "MANUAL_REVIEW",
                    "valuation_source_name": "review",
                    "valuation_source_reference": "manual-reviewed-note",
                    "valuation_source_as_of_date": "2026-04-26",
                    "valuation_reviewed_by": "analyst",
                    "valuation_reviewed_at": "2026-04-26",
                    "valuation_notes": "private value text",
                }
            ]
        )
        self.run_contract()

        self.assertEqual(self.queue_row()["valuation_input_status"], "OK")
        self.assertIn("VALUATION_APPROVED", self.queue_row()["reason_code"])
        self.assertEqual(self.summary_value("approved_rows_count"), "1")

    def test_out_of_range_value_is_invalid(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.write_review_rows(
            [
                {
                    "ticker": "AAA",
                    "isin": "US1",
                    "normalized_fcf_yield_pct": "500",
                    "target_fcf_yield_pct": "4",
                    "valuation_review_status": "APPROVED",
                    "valuation_source_type": "MANUAL_REVIEW",
                    "valuation_source_name": "review",
                    "valuation_source_reference": "source",
                    "valuation_source_as_of_date": "2026-04-26",
                    "valuation_reviewed_by": "analyst",
                    "valuation_reviewed_at": "2026-04-26",
                    "valuation_notes": "private",
                }
            ]
        )
        self.run_contract()

        self.assertEqual(self.queue_row()["valuation_input_status"], "INVALID")
        self.assertIn("VALUATION_VALUE_OUT_OF_RANGE", self.queue_row()["reason_code"])

    def test_missing_values_are_not_imputed_or_reported(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.run_contract(review_input=str(self.tmp / "missing_review.csv"))

        row = self.queue_row()
        self.assertEqual(row["normalized_fcf_yield_pct"], "")
        self.assertEqual(row["target_fcf_yield_pct"], "")
        self.assertIn("NO_IMPUTATION", row["reason_code"])
        self.assertEqual(self.summary_value("no_imputation_confirmed"), "True")

    def test_private_review_values_are_not_dumped_in_report(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.write_review_rows(
            [
                {
                    "ticker": "AAA",
                    "isin": "US1",
                    "normalized_fcf_yield_pct": "5.55",
                    "target_fcf_yield_pct": "4.44",
                    "valuation_review_status": "APPROVED",
                    "valuation_source_type": "MANUAL_REVIEW",
                    "valuation_source_name": "private-model",
                    "valuation_source_reference": "private-source",
                    "valuation_source_as_of_date": "2026-04-26",
                    "valuation_reviewed_by": "private-person",
                    "valuation_reviewed_at": "2026-04-26",
                    "valuation_notes": "secret valuation note",
                }
            ]
        )
        self.run_contract()

        report_text = self.report.read_text(encoding="utf-8")
        self.assertNotIn("5.55", report_text)
        self.assertNotIn("4.44", report_text)
        self.assertNotIn("secret valuation note", report_text)


if __name__ == "__main__":
    unittest.main()
