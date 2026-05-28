from __future__ import annotations

import csv
import shutil
import unittest
from pathlib import Path

import src.valuation_input_temporal_integrity_review as temporal
from src.valuation_input_temporal_integrity_review import run_valuation_input_temporal_integrity_review
from src.valuation_input_provenance_review import run_valuation_input_provenance_review

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "docs" / "contracts" / "VALUATION_INPUT_AS_OF_TEMPORAL_INTEGRITY_CONTRACT.md"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class ValuationInputTemporalIntegrityReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_valuation_input_temporal_integrity_review"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.queue = self.tmp / "queue.csv"
        self.review = self.tmp / "review.csv"
        self.provenance = self.tmp / "provenance.csv"
        self.evidence = self.tmp / "evidence.csv"
        self.output = self.tmp / "temporal_review.csv"
        self.summary = self.tmp / "temporal_summary.csv"
        self.report = self.tmp / "temporal_report.md"

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

    def build_provenance(self) -> None:
        run_valuation_input_provenance_review(
            as_of_date="2026-05-21",
            queue_input=str(self.queue),
            review_input=str(self.review),
            evidence_input=str(self.evidence),
            review_output=str(self.provenance),
            summary_output=str(self.tmp / "provenance_summary.csv"),
            report_output=str(self.tmp / "provenance_report.md"),
        )

    def run_temporal(self):
        return run_valuation_input_temporal_integrity_review(
            as_of_date="2026-05-21",
            queue_input=str(self.queue),
            review_input=str(self.review),
            provenance_input=str(self.provenance),
            evidence_input=str(self.evidence),
            review_output=str(self.output),
            summary_output=str(self.summary),
            report_output=str(self.report),
        )

    def first_row(self) -> dict[str, str]:
        return read_csv(self.output)[0]

    def summary_value(self, metric: str) -> str:
        return {row["metric"]: row["value"] for row in read_csv(self.summary)}[metric]

    def test_ok_row_where_source_review_and_run_dates_are_ordered(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row()])
        self.write_evidence()
        self.build_provenance()
        self.run_temporal()

        row = self.first_row()
        self.assertEqual(row["temporal_integrity_status"], "OK")
        self.assertIn("TEMPORAL_INTEGRITY_OK", row["reason_code"])
        self.assertEqual(row["source_after_run_as_of"], "False")
        self.assertEqual(row["review_after_run_as_of"], "False")
        self.assertEqual(row["review_before_source_as_of"], "False")

    def test_source_date_after_run_as_of_is_invalid(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row(valuation_source_as_of_date="2026-06-01")])
        self.run_temporal()

        row = self.first_row()
        self.assertEqual(row["temporal_integrity_status"], "INVALID")
        self.assertIn("VALUATION_SOURCE_DATE_AFTER_AS_OF", row["reason_code"])

    def test_reviewed_at_after_run_as_of_is_invalid(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row(valuation_reviewed_at="2026-06-01")])
        self.run_temporal()

        row = self.first_row()
        self.assertEqual(row["temporal_integrity_status"], "INVALID")
        self.assertIn("VALUATION_REVIEWED_AT_AFTER_AS_OF", row["reason_code"])

    def test_reviewed_at_before_source_date_is_inconsistent(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row(valuation_source_as_of_date="2026-01-15", valuation_reviewed_at="2026-01-14")])
        self.run_temporal()

        row = self.first_row()
        self.assertEqual(row["temporal_integrity_status"], "INCONSISTENT")
        self.assertIn("VALUATION_REVIEWED_AT_BEFORE_SOURCE_DATE", row["reason_code"])

    def test_missing_source_date_remains_visible(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row(valuation_source_as_of_date="")])
        self.run_temporal()

        row = self.first_row()
        self.assertEqual(row["temporal_integrity_status"], "MISSING")
        self.assertIn("VALUATION_SOURCE_DATE_MISSING", row["reason_code"])

    def test_missing_reviewed_at_remains_visible(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row(valuation_reviewed_at="")])
        self.run_temporal()

        row = self.first_row()
        self.assertEqual(row["temporal_integrity_status"], "MISSING")
        self.assertIn("VALUATION_REVIEWED_AT_MISSING", row["reason_code"])

    def test_invalid_date_strings_remain_visible(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row(valuation_source_as_of_date="bad-date", valuation_reviewed_at="also-bad")])
        self.run_temporal()

        row = self.first_row()
        self.assertEqual(row["temporal_integrity_status"], "INVALID")
        self.assertIn("VALUATION_SOURCE_DATE_INVALID", row["reason_code"])
        self.assertIn("VALUATION_REVIEWED_AT_INVALID", row["reason_code"])

    def test_non_standard_row_is_not_applicable(self) -> None:
        self.write_queue([self.queue_row(ticker="ETF", isin="US9999", company_type_profile="ETF")])
        self.run_temporal()

        row = self.first_row()
        self.assertEqual(row["temporal_integrity_status"], "NOT_APPLICABLE")
        self.assertIn("PROFILE_NOT_STANDARD", row["reason_code"])

    def test_missing_optional_private_input_does_not_crash_and_is_visible(self) -> None:
        self.write_queue([self.queue_row()])
        self.run_temporal()

        row = self.first_row()
        self.assertEqual(row["temporal_integrity_status"], "MISSING")
        self.assertIn("OPTIONAL_INPUT_MISSING", row["reason_code"])
        self.assertIn("NO_IMPUTATION", row["reason_code"])
        self.assertGreater(int(self.summary_value("warnings_total")), 0)

    def test_upstream_non_ok_status_is_not_upgraded_to_ok(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row()])
        write_csv(
            self.provenance,
            [
                "ticker",
                "isin",
                "valuation_input_provenance_status",
            ],
            [{"ticker": "AAA", "isin": "US0001", "valuation_input_provenance_status": "CONFLICT"}],
        )
        self.run_temporal()

        row = self.first_row()
        self.assertEqual(row["temporal_integrity_status"], "REVIEW")
        self.assertEqual(row["upstream_provenance_status"], "CONFLICT")
        self.assertIn("UPSTREAM_PROVENANCE_NOT_OK", row["reason_code"])

    def test_markdown_report_states_boundaries_and_sanitizes_paths(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row()])
        self.run_temporal()

        text = self.report.read_text(encoding="utf-8")
        self.assertIn("read-only governance evidence", text)
        self.assertIn("does not implement valuation automation", text)
        self.assertIn("investment readiness", text)
        self.assertNotIn(str(self.tmp), text)
        self.assertIn("<local_path>", text)

    def test_output_csv_schemas_are_stable(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_review([self.review_row()])
        self.run_temporal()

        with self.output.open("r", encoding="utf-8", newline="") as handle:
            self.assertEqual(csv.DictReader(handle).fieldnames, temporal.REVIEW_FIELDS)
        with self.summary.open("r", encoding="utf-8", newline="") as handle:
            self.assertEqual(csv.DictReader(handle).fieldnames, temporal.SUMMARY_FIELDS)

    def test_producer_uses_no_network_imports(self) -> None:
        source = Path(temporal.__file__).read_text(encoding="utf-8")

        for forbidden in ["requests", "urllib", "http.client", "socket", "smtplib", "ftplib"]:
            self.assertNotIn(forbidden, source)

    def test_contract_contains_required_boundary_language(self) -> None:
        text = CONTRACT_PATH.read_text(encoding="utf-8").lower()

        for phrase in [
            "as-of",
            "temporal integrity",
            "no imputation",
            "valuation automation",
            "investment readiness",
            "human operator",
        ]:
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
