from __future__ import annotations

import csv
import shutil
import unittest
from pathlib import Path

from src.personal_private_input_review import run_personal_private_input_review

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


class PersonalPrivateInputReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_private_input_review"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.valuation_queue = self.tmp / "valuation_queue.csv"
        self.dividend_queue = self.tmp / "dividend_queue.csv"
        self.valuation_input = self.tmp / "valuation_private.csv"
        self.dividend_input = self.tmp / "dividend_private.csv"
        self.validation = self.tmp / "validation.csv"
        self.summary = self.tmp / "summary.csv"
        self.report = self.tmp / "report.md"
        self.master = self.tmp / "master.csv"
        self.score = self.tmp / "score.csv"
        self.evidence = self.tmp / "evidence.csv"
        self.master.write_text("ticker,value\nAAA,1\n", encoding="utf-8")
        self.score.write_text("ticker,score\nAAA,50\n", encoding="utf-8")
        self.evidence.write_text("ticker,kpi\nAAA,x\n", encoding="utf-8")
        self.write_queues()

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_queues(self) -> None:
        write_csv(
            self.valuation_queue,
            [
                "ticker",
                "isin",
                "company_name",
                "company_type_profile",
                "missing_valuation_kpis",
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
                "valuation_input_status",
                "reason_code",
                "recommended_next_action",
            ],
            [
                {
                    "ticker": "AAA",
                    "isin": "US1",
                    "company_name": "Alpha",
                    "company_type_profile": "STANDARD",
                    "missing_valuation_kpis": "normalized_fcf_yield_pct; target_fcf_yield_pct",
                }
            ],
        )
        write_csv(
            self.dividend_queue,
            [
                "ticker",
                "isin",
                "company_name",
                "company_type_profile",
                "missing_dividend_fcf_kpis",
                "fcf_margin",
                "payout_ratio_fcf",
                "fcf_per_share_cagr_5y",
            ],
            [
                {
                    "ticker": "AAA",
                    "isin": "US1",
                    "company_name": "Alpha",
                    "company_type_profile": "STANDARD",
                    "missing_dividend_fcf_kpis": "fcf_margin; payout_ratio_fcf; fcf_per_share_cagr_5y",
                }
            ],
        )

    def valuation_fields(self) -> list[str]:
        return [
            "ticker",
            "isin",
            "normalized_fcf_yield_pct",
            "target_fcf_yield_pct",
            "valuation_review_status",
            "valuation_source_type",
            "valuation_source_name",
            "valuation_source_reference",
            "valuation_source_as_of_date",
        ]

    def dividend_fields(self) -> list[str]:
        return [
            "ticker",
            "isin",
            "fcf_margin",
            "payout_ratio_fcf",
            "fcf_per_share_cagr_5y",
            "dividend_fcf_review_status",
            "dividend_fcf_source_type",
            "dividend_fcf_source_name",
            "dividend_fcf_source_reference",
            "dividend_fcf_source_as_of_date",
        ]

    def valuation_row(self, **overrides: str) -> dict[str, str]:
        row = {
            "ticker": "AAA",
            "isin": "US1",
            "normalized_fcf_yield_pct": "5.55",
            "target_fcf_yield_pct": "6.66",
            "valuation_review_status": "APPROVED",
            "valuation_source_type": "MANUAL_REVIEW",
            "valuation_source_name": "private model",
            "valuation_source_reference": "private ref",
            "valuation_source_as_of_date": "2026-04-27",
        }
        row.update(overrides)
        return row

    def dividend_row(self, **overrides: str) -> dict[str, str]:
        row = {
            "ticker": "AAA",
            "isin": "US1",
            "fcf_margin": "11.11",
            "payout_ratio_fcf": "22.22",
            "fcf_per_share_cagr_5y": "3.33",
            "dividend_fcf_review_status": "APPROVED",
            "dividend_fcf_source_type": "MANUAL_REVIEW",
            "dividend_fcf_source_name": "private model",
            "dividend_fcf_source_reference": "private ref",
            "dividend_fcf_source_as_of_date": "2026-04-27",
        }
        row.update(overrides)
        return row

    def run_review(self, **overrides):
        params = {
            "valuation_queue_input": str(self.valuation_queue),
            "dividend_fcf_queue_input": str(self.dividend_queue),
            "valuation_private_input": str(self.valuation_input),
            "dividend_fcf_private_input": str(self.dividend_input),
            "validation_output": str(self.validation),
            "summary_output": str(self.summary),
            "report_output": str(self.report),
        }
        params.update(overrides)
        return run_personal_private_input_review(**params)

    def rows_for_domain(self, domain: str) -> list[dict[str, str]]:
        return [row for row in read_csv(self.validation) if row["review_domain"] == domain]

    def summary_for_domain(self, domain: str) -> dict[str, str]:
        return {row["review_domain"]: row for row in read_csv(self.summary)}[domain]

    def test_missing_private_inputs_are_controlled_missing_without_crash(self) -> None:
        self.run_review()
        valuation = self.summary_for_domain("VALUATION")
        dividend = self.summary_for_domain("DIVIDEND_FCF")
        self.assertEqual(valuation["input_file_status"], "MISSING")
        self.assertEqual(dividend["input_file_status"], "MISSING")
        self.assertIn("INPUT_FILE_MISSING", valuation["reason_codes"])
        self.assertEqual(valuation["no_imputation_confirmed"], "True")

    def test_valuation_approved_with_complete_source_metadata_is_eligible(self) -> None:
        write_csv(self.valuation_input, self.valuation_fields(), [self.valuation_row()])
        self.run_review()
        row = self.rows_for_domain("VALUATION")[0]
        self.assertEqual(row["row_validation_status"], "APPROVED")
        self.assertEqual(row["apply_eligibility_status"], "ELIGIBLE_FOR_APPROVED_APPLY")
        self.assertIn("VALUATION_APPROVED", row["reason_codes"])

    def test_valuation_approved_without_source_reference_is_review(self) -> None:
        write_csv(self.valuation_input, self.valuation_fields(), [self.valuation_row(valuation_source_reference="")])
        self.run_review()
        row = self.rows_for_domain("VALUATION")[0]
        self.assertEqual(row["row_validation_status"], "REVIEW")
        self.assertIn("VALUATION_SOURCE_REFERENCE_MISSING", row["reason_codes"])

    def test_dividend_fcf_approved_with_complete_source_metadata_is_eligible(self) -> None:
        write_csv(self.dividend_input, self.dividend_fields(), [self.dividend_row()])
        self.run_review()
        row = self.rows_for_domain("DIVIDEND_FCF")[0]
        self.assertEqual(row["row_validation_status"], "APPROVED")
        self.assertEqual(row["apply_eligibility_status"], "ELIGIBLE_FOR_APPROVED_APPLY")
        self.assertIn("DIVIDEND_FCF_APPROVED", row["reason_codes"])

    def test_dividend_fcf_out_of_range_is_invalid(self) -> None:
        write_csv(self.dividend_input, self.dividend_fields(), [self.dividend_row(fcf_margin="500")])
        self.run_review()
        row = self.rows_for_domain("DIVIDEND_FCF")[0]
        self.assertEqual(row["row_validation_status"], "INVALID")
        self.assertIn("DIVIDEND_FCF_VALUE_OUT_OF_RANGE", row["reason_codes"])

    def test_duplicate_identity_is_invalid(self) -> None:
        write_csv(self.valuation_input, self.valuation_fields(), [self.valuation_row(), self.valuation_row(normalized_fcf_yield_pct="7")])
        self.run_review()
        row = self.rows_for_domain("VALUATION")[0]
        self.assertEqual(row["row_validation_status"], "INVALID")
        self.assertIn("DUPLICATE_IDENTITY", row["reason_codes"])

    def test_unknown_identity_is_missing_and_not_silently_matched(self) -> None:
        write_csv(self.valuation_input, self.valuation_fields(), [self.valuation_row(isin="US2", ticker="BBB")])
        self.run_review()
        row = self.rows_for_domain("VALUATION")[0]
        self.assertEqual(row["row_validation_status"], "MISSING")
        self.assertIn("IDENTITY_NOT_FOUND", row["reason_codes"])

    def test_private_numeric_values_are_sanitized_from_outputs_and_report(self) -> None:
        write_csv(self.valuation_input, self.valuation_fields(), [self.valuation_row()])
        write_csv(self.dividend_input, self.dividend_fields(), [self.dividend_row()])
        self.run_review()
        validation_text = self.validation.read_text(encoding="utf-8")
        report_text = self.report.read_text(encoding="utf-8")
        for secret in ("5.55", "6.66", "11.11", "22.22", "3.33"):
            self.assertNotIn(secret, validation_text)
            self.assertNotIn(secret, report_text)
        self.assertEqual(self.summary_for_domain("VALUATION")["private_values_sanitized"], "True")

    def test_no_master_score_or_evidence_files_are_changed(self) -> None:
        master_before = self.master.read_text(encoding="utf-8")
        score_before = self.score.read_text(encoding="utf-8")
        evidence_before = self.evidence.read_text(encoding="utf-8")
        write_csv(self.valuation_input, self.valuation_fields(), [self.valuation_row()])
        write_csv(self.dividend_input, self.dividend_fields(), [self.dividend_row()])
        self.run_review()
        self.assertEqual(self.master.read_text(encoding="utf-8"), master_before)
        self.assertEqual(self.score.read_text(encoding="utf-8"), score_before)
        self.assertEqual(self.evidence.read_text(encoding="utf-8"), evidence_before)


if __name__ == "__main__":
    unittest.main()
