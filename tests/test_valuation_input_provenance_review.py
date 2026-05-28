from __future__ import annotations

import csv
import shutil
import unittest
from pathlib import Path

import src.valuation_input_provenance_review as provenance
from src.valuation_input_provenance_review import run_valuation_input_provenance_review

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "docs" / "contracts" / "VALUATION_INPUT_PROVENANCE_AND_CONFLICT_CONTRACT.md"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class ValuationInputProvenanceReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_valuation_input_provenance_review"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.queue = self.tmp / "queue.csv"
        self.review = self.tmp / "review.csv"
        self.evidence = self.tmp / "evidence.csv"
        self.review_output = self.tmp / "review_output.csv"
        self.summary_output = self.tmp / "summary_output.csv"
        self.report_output = self.tmp / "report.md"

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    @property
    def queue_fields(self) -> list[str]:
        return [
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
        ]

    @property
    def review_fields(self) -> list[str]:
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
            "valuation_reviewed_by",
            "valuation_reviewed_at",
            "valuation_notes",
        ]

    def queue_row(self, **overrides: str) -> dict[str, str]:
        row = {
            "ticker": "AAA",
            "isin": "US0001",
            "company_name": "Alpha",
            "company_type_profile": "STANDARD",
            "missing_valuation_kpis": "normalized_fcf_yield_pct; target_fcf_yield_pct",
            "normalized_fcf_yield_pct": "",
            "target_fcf_yield_pct": "",
            "valuation_review_status": "",
            "valuation_source_type": "",
            "valuation_source_name": "",
            "valuation_source_reference": "",
            "valuation_source_as_of_date": "",
            "valuation_reviewed_by": "",
            "valuation_reviewed_at": "",
            "valuation_notes": "",
            "valuation_input_status": "MISSING",
            "reason_code": "VALUATION_REQUIRED_MISSING",
            "recommended_next_action": "",
        }
        row.update(overrides)
        return row

    def review_row(self, **overrides: str) -> dict[str, str]:
        row = {
            "ticker": "AAA",
            "isin": "US0001",
            "normalized_fcf_yield_pct": "6",
            "target_fcf_yield_pct": "5",
            "valuation_review_status": "APPROVED",
            "valuation_source_type": "MANUAL_REVIEW",
            "valuation_source_name": "synthetic review",
            "valuation_source_reference": "synthetic-source",
            "valuation_source_as_of_date": "2026-01-15",
            "valuation_reviewed_by": "synthetic-operator",
            "valuation_reviewed_at": "2026-01-16",
            "valuation_notes": "synthetic fixture",
        }
        row.update(overrides)
        return row

    def write_queue(self, rows: list[dict[str, str]]) -> None:
        write_csv(self.queue, self.queue_fields, rows)

    def write_review(self, rows: list[dict[str, str]]) -> None:
        write_csv(self.review, self.review_fields, rows)

    def write_evidence(self) -> None:
        write_csv(self.evidence, ["ticker", "isin"], [{"ticker": "AAA", "isin": "US0001"}])

    def run_review(self, *, max_age: int = 365):
        return run_valuation_input_provenance_review(
            as_of_date="2026-05-21",
            max_source_age_days=max_age,
            queue_input=str(self.queue),
            review_input=str(self.review),
            evidence_input=str(self.evidence),
            review_output=str(self.review_output),
            summary_output=str(self.summary_output),
            report_output=str(self.report_output),
        )

    def first_output_row(self) -> dict[str, str]:
        return read_csv(self.review_output)[0]

    def summary_value(self, metric: str) -> str:
        return {row["metric"]: row["value"] for row in read_csv(self.summary_output)}[metric]

    def test_missing_optional_reviewed_input_does_not_crash_and_remains_visible(self) -> None:
        self.write_queue([self.queue_row()])
        result = self.run_review()

        row = self.first_output_row()
        self.assertEqual(row["valuation_input_provenance_status"], "MISSING")
        self.assertIn("VALUATION_REQUIRED_MISSING", row["reason_code"])
        self.assertIn("NO_IMPUTATION", row["reason_code"])
        self.assertEqual(self.summary_value("optional_evidence_input_status"), "MISSING")
        self.assertTrue(result.warnings)

    def test_approved_complete_row_becomes_ok(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row()])
        self.write_evidence()
        self.run_review()

        row = self.first_output_row()
        self.assertEqual(row["valuation_input_provenance_status"], "OK")
        self.assertEqual(row["valuation_conflict_status"], "OK")
        self.assertIn("VALUATION_PROVENANCE_OK", row["reason_code"])
        self.assertEqual(self.summary_value("ok_rows_count"), "1")

    def test_approved_row_with_missing_source_reference_requires_review(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row(valuation_source_reference="")])
        self.run_review()

        row = self.first_output_row()
        self.assertEqual(row["valuation_input_provenance_status"], "REVIEW")
        self.assertIn("VALUATION_SOURCE_REFERENCE_MISSING", row["reason_code"])

    def test_invalid_source_date_is_invalid_with_reason(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row(valuation_source_as_of_date="bad-date")])
        self.run_review()

        row = self.first_output_row()
        self.assertEqual(row["valuation_input_provenance_status"], "INVALID")
        self.assertIn("VALUATION_SOURCE_DATE_INVALID", row["reason_code"])

    def test_stale_source_date_is_visible(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row(valuation_source_as_of_date="2024-01-01")])
        self.run_review(max_age=30)

        row = self.first_output_row()
        self.assertEqual(row["valuation_input_provenance_status"], "STALE")
        self.assertIn("VALUATION_SOURCE_STALE", row["reason_code"])

    def test_duplicate_identity_becomes_conflict(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row(), self.review_row(valuation_notes="duplicate")])
        self.run_review()

        row = self.first_output_row()
        self.assertEqual(row["valuation_input_provenance_status"], "CONFLICT")
        self.assertEqual(row["valuation_conflict_status"], "CONFLICT")
        self.assertIn("DUPLICATE_VALUATION_IDENTITY", row["reason_code"])

    def test_conflicting_values_and_metadata_are_conflict(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review(
            [
                self.review_row(),
                self.review_row(
                    normalized_fcf_yield_pct="7",
                    valuation_source_reference="different-source",
                    valuation_source_as_of_date="2026-01-20",
                ),
            ]
        )
        self.run_review()

        row = self.first_output_row()
        self.assertEqual(row["valuation_input_provenance_status"], "CONFLICT")
        self.assertIn("CONFLICTING_VALUATION_VALUES", row["reason_code"])
        self.assertIn("CONFLICTING_SOURCE_METADATA", row["reason_code"])

    def test_out_of_range_value_is_invalid(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row(normalized_fcf_yield_pct="500")])
        self.run_review()

        row = self.first_output_row()
        self.assertEqual(row["valuation_input_provenance_status"], "INVALID")
        self.assertIn("VALUATION_VALUE_OUT_OF_RANGE", row["reason_code"])

    def test_missing_values_remain_missing_and_no_imputation(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row(normalized_fcf_yield_pct="")])
        self.run_review()

        row = self.first_output_row()
        self.assertEqual(row["valuation_input_provenance_status"], "MISSING")
        self.assertEqual(row["normalized_fcf_yield_pct"], "")
        self.assertIn("NO_IMPUTATION", row["reason_code"])

    def test_non_standard_rows_are_not_applicable(self) -> None:
        self.write_queue([self.queue_row(ticker="ETF", isin="US9999", company_type_profile="ETF")])
        self.run_review()

        row = self.first_output_row()
        self.assertEqual(row["valuation_input_provenance_status"], "NOT_APPLICABLE")
        self.assertIn("PROFILE_NOT_STANDARD", row["reason_code"])
        self.assertEqual(self.summary_value("not_applicable_rows_count"), "1")

    def test_output_csv_schemas_are_stable(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row()])
        self.run_review()

        with self.review_output.open("r", encoding="utf-8", newline="") as handle:
            self.assertEqual(csv.DictReader(handle).fieldnames, provenance.REVIEW_FIELDS)
        with self.summary_output.open("r", encoding="utf-8", newline="") as handle:
            self.assertEqual(csv.DictReader(handle).fieldnames, provenance.SUMMARY_FIELDS)

    def test_markdown_report_states_boundaries_and_sanitizes_paths(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row()])
        self.run_review()

        text = self.report_output.read_text(encoding="utf-8")
        self.assertIn("read-only governance evidence", text)
        self.assertIn("does not implement valuation automation", text)
        self.assertIn("investment readiness", text)
        self.assertNotIn(str(self.tmp), text)
        self.assertIn("<local_path>", text)

    def test_contract_contains_required_boundary_language(self) -> None:
        text = CONTRACT_PATH.read_text(encoding="utf-8").lower()

        for phrase in [
            "provenance",
            "conflict",
            "freshness",
            "no imputation",
            "valuation automation",
            "investment readiness",
            "human operator",
        ]:
            self.assertIn(phrase, text)

    def test_producer_uses_no_network_imports(self) -> None:
        source = Path(provenance.__file__).read_text(encoding="utf-8")

        for forbidden in ["requests", "urllib", "http.client", "socket", "smtplib", "ftplib"]:
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
