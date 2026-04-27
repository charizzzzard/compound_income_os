from __future__ import annotations

import csv
import shutil
import unittest
from pathlib import Path

from src.personal_private_input_apply_candidates import run_personal_private_input_apply_candidates

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


class PersonalPrivateInputApplyCandidatesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_private_input_apply_candidates"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.validation = self.tmp / "validation.csv"
        self.review_summary = self.tmp / "review_summary.csv"
        self.valuation_private = self.tmp / "valuation_private.csv"
        self.dividend_private = self.tmp / "dividend_private.csv"
        self.private_candidates = self.tmp / "private" / "personal_private_input_apply_candidates.csv"
        self.sanitized = self.tmp / "sanitized.csv"
        self.summary = self.tmp / "summary.csv"
        self.report = self.tmp / "report.md"
        self.master = self.tmp / "master.csv"
        self.score = self.tmp / "score.csv"
        self.evidence = self.tmp / "evidence.csv"
        self.master.write_text("ticker,value\nAAA,1\n", encoding="utf-8")
        self.score.write_text("ticker,score\nAAA,50\n", encoding="utf-8")
        self.evidence.write_text("ticker,kpi\nAAA,x\n", encoding="utf-8")
        self.write_base_validation()

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def validation_fields(self) -> list[str]:
        return [
            "review_domain",
            "ticker",
            "isin",
            "company_name",
            "company_type_profile",
            "required_kpis",
            "missing_kpi_count",
            "present_kpi_count",
            "approved_kpi_count",
            "invalid_kpi_count",
            "private_input_file_status",
            "row_validation_status",
            "apply_eligibility_status",
            "source_metadata_complete",
            "reason_codes",
        ]

    def valuation_private_fields(self) -> list[str]:
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
        ]

    def dividend_private_fields(self) -> list[str]:
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
            "dividend_fcf_reviewed_by",
            "dividend_fcf_reviewed_at",
        ]

    def write_base_validation(self) -> None:
        write_csv(
            self.validation,
            self.validation_fields(),
            [
                self.validation_row("VALUATION", status="MISSING", eligibility="NOT_AVAILABLE", reasons="INPUT_FILE_MISSING;VALUATION_REQUIRED_MISSING"),
                self.validation_row("DIVIDEND_FCF", status="MISSING", eligibility="NOT_AVAILABLE", reasons="INPUT_FILE_MISSING;DIVIDEND_FCF_REQUIRED_MISSING"),
            ],
        )
        write_csv(
            self.review_summary,
            [
                "review_domain",
                "input_file_status",
                "queue_rows_count",
                "input_rows_count",
                "approved_rows_count",
                "review_rows_count",
                "missing_rows_count",
                "invalid_rows_count",
                "eligible_for_approved_apply_count",
                "no_imputation_confirmed",
                "private_values_sanitized",
                "reason_codes",
            ],
            [
                self.summary_row("VALUATION", input_status="MISSING", approved="0", eligible="0", reasons="INPUT_FILE_MISSING;VALUATION_REQUIRED_MISSING"),
                self.summary_row("DIVIDEND_FCF", input_status="MISSING", approved="0", eligible="0", reasons="INPUT_FILE_MISSING;DIVIDEND_FCF_REQUIRED_MISSING"),
            ],
        )

    def validation_row(self, domain: str, *, status: str = "APPROVED", eligibility: str = "ELIGIBLE_FOR_APPROVED_APPLY", reasons: str = "") -> dict[str, str]:
        if domain == "VALUATION":
            kpis = "normalized_fcf_yield_pct;target_fcf_yield_pct"
            approved_count = "2" if status == "APPROVED" else "0"
        else:
            kpis = "fcf_margin;payout_ratio_fcf;fcf_per_share_cagr_5y"
            approved_count = "3" if status == "APPROVED" else "0"
        return {
            "review_domain": domain,
            "ticker": "AAA",
            "isin": "US1",
            "company_name": "Alpha",
            "company_type_profile": "STANDARD",
            "required_kpis": kpis,
            "missing_kpi_count": "0" if status == "APPROVED" else "2",
            "present_kpi_count": approved_count,
            "approved_kpi_count": approved_count,
            "invalid_kpi_count": "0",
            "private_input_file_status": "PRESENT" if status == "APPROVED" else "MISSING",
            "row_validation_status": status,
            "apply_eligibility_status": eligibility,
            "source_metadata_complete": "yes" if status == "APPROVED" else "no",
            "reason_codes": reasons or (f"{domain}_APPROVED" if domain == "VALUATION" else "DIVIDEND_FCF_APPROVED"),
        }

    def summary_row(self, domain: str, *, input_status: str = "PRESENT", approved: str = "1", eligible: str = "1", reasons: str = "") -> dict[str, str]:
        return {
            "review_domain": domain,
            "input_file_status": input_status,
            "queue_rows_count": "1",
            "input_rows_count": "1" if input_status == "PRESENT" else "0",
            "approved_rows_count": approved,
            "review_rows_count": "0",
            "missing_rows_count": "0" if approved != "0" else "1",
            "invalid_rows_count": "0",
            "eligible_for_approved_apply_count": eligible,
            "no_imputation_confirmed": "True",
            "private_values_sanitized": "True",
            "reason_codes": reasons,
        }

    def valuation_private_row(self, **overrides: str) -> dict[str, str]:
        row = {
            "ticker": "AAA",
            "isin": "US1",
            "normalized_fcf_yield_pct": "5.55",
            "target_fcf_yield_pct": "6.66",
            "valuation_review_status": "APPROVED",
            "valuation_source_type": "MANUAL_REVIEW",
            "valuation_source_name": "model",
            "valuation_source_reference": "private ref",
            "valuation_source_as_of_date": "2026-04-27",
            "valuation_reviewed_by": "reviewer",
            "valuation_reviewed_at": "2026-04-27",
        }
        row.update(overrides)
        return row

    def dividend_private_row(self, **overrides: str) -> dict[str, str]:
        row = {
            "ticker": "AAA",
            "isin": "US1",
            "fcf_margin": "11.11",
            "payout_ratio_fcf": "22.22",
            "fcf_per_share_cagr_5y": "3.33",
            "dividend_fcf_review_status": "APPROVED",
            "dividend_fcf_source_type": "MANUAL_REVIEW",
            "dividend_fcf_source_name": "model",
            "dividend_fcf_source_reference": "private ref",
            "dividend_fcf_source_as_of_date": "2026-04-27",
            "dividend_fcf_reviewed_by": "reviewer",
            "dividend_fcf_reviewed_at": "2026-04-27",
        }
        row.update(overrides)
        return row

    def run_candidates(self, **overrides):
        params = {
            "review_validation_input": str(self.validation),
            "review_summary_input": str(self.review_summary),
            "valuation_private_input": str(self.valuation_private),
            "dividend_fcf_private_input": str(self.dividend_private),
            "private_candidate_output": str(self.private_candidates),
            "sanitized_output": str(self.sanitized),
            "summary_output": str(self.summary),
            "report_output": str(self.report),
        }
        params.update(overrides)
        return run_personal_private_input_apply_candidates(**params)

    def test_no_private_inputs_creates_zero_candidates(self) -> None:
        self.run_candidates()
        summary = {row["review_domain"]: row for row in read_csv(self.summary)}
        self.assertEqual(summary["VALUATION"]["candidate_rows_count"], "0")
        self.assertIn("NO_APPROVED_INPUTS", summary["VALUATION"]["reason_codes"])
        self.assertFalse(self.private_candidates.exists())

    def test_approved_valuation_creates_sanitized_and_private_candidate(self) -> None:
        write_csv(self.validation, self.validation_fields(), [self.validation_row("VALUATION")])
        write_csv(self.review_summary, list(self.summary_row("VALUATION").keys()), [self.summary_row("VALUATION", reasons="VALUATION_APPROVED")])
        write_csv(self.valuation_private, self.valuation_private_fields(), [self.valuation_private_row()])
        self.run_candidates()
        sanitized = read_csv(self.sanitized)[0]
        self.assertEqual(sanitized["apply_candidate_status"], "READY_FOR_PRIVATE_APPLY_REVIEW")
        self.assertEqual(sanitized["would_update_fields"], "normalized_fcf_yield_pct;target_fcf_yield_pct")
        self.assertTrue(self.private_candidates.exists())
        self.assertNotIn("5.55", self.sanitized.read_text(encoding="utf-8"))
        self.assertIn("5.55", self.private_candidates.read_text(encoding="utf-8"))

    def test_approved_dividend_fcf_creates_expected_candidate_fields(self) -> None:
        write_csv(self.validation, self.validation_fields(), [self.validation_row("DIVIDEND_FCF")])
        write_csv(self.review_summary, list(self.summary_row("DIVIDEND_FCF").keys()), [self.summary_row("DIVIDEND_FCF", reasons="DIVIDEND_FCF_APPROVED")])
        write_csv(self.dividend_private, self.dividend_private_fields(), [self.dividend_private_row()])
        self.run_candidates()
        summary = {row["review_domain"]: row for row in read_csv(self.summary)}["DIVIDEND_FCF"]
        self.assertEqual(summary["candidate_rows_count"], "1")
        self.assertEqual(summary["candidate_fields_count"], "3")
        self.assertNotIn("11.11", self.sanitized.read_text(encoding="utf-8"))

    def test_review_missing_or_invalid_rows_are_not_candidates(self) -> None:
        write_csv(self.validation, self.validation_fields(), [self.validation_row("VALUATION", status="REVIEW", eligibility="NOT_ELIGIBLE", reasons="VALUATION_REVIEW_PENDING")])
        write_csv(self.valuation_private, self.valuation_private_fields(), [self.valuation_private_row()])
        self.run_candidates()
        row = read_csv(self.sanitized)[0]
        self.assertEqual(row["apply_candidate_status"], "NOT_READY")
        self.assertEqual(row["candidate_kpi_count"], "0")
        self.assertFalse(self.private_candidates.exists())

    def test_missing_source_metadata_is_not_candidate(self) -> None:
        write_csv(self.validation, self.validation_fields(), [self.validation_row("VALUATION", reasons="VALUATION_SOURCE_REFERENCE_MISSING")])
        write_csv(self.review_summary, list(self.summary_row("VALUATION").keys()), [self.summary_row("VALUATION", reasons="VALUATION_SOURCE_REFERENCE_MISSING")])
        write_csv(self.valuation_private, self.valuation_private_fields(), [self.valuation_private_row(valuation_source_reference="")])
        self.run_candidates()
        row = read_csv(self.sanitized)[0]
        self.assertEqual(row["apply_candidate_status"], "NOT_READY")
        self.assertIn("SOURCE_METADATA_MISSING", row["reason_codes"])

    def test_duplicate_identity_is_invalid(self) -> None:
        write_csv(self.validation, self.validation_fields(), [self.validation_row("VALUATION")])
        write_csv(self.review_summary, list(self.summary_row("VALUATION").keys()), [self.summary_row("VALUATION", reasons="VALUATION_APPROVED")])
        write_csv(self.valuation_private, self.valuation_private_fields(), [self.valuation_private_row(), self.valuation_private_row(normalized_fcf_yield_pct="7")])
        self.run_candidates()
        row = read_csv(self.sanitized)[0]
        self.assertEqual(row["apply_candidate_status"], "INVALID")
        self.assertIn("DUPLICATE_IDENTITY", row["reason_codes"])

    def test_public_report_is_sanitized(self) -> None:
        write_csv(self.validation, self.validation_fields(), [self.validation_row("VALUATION"), self.validation_row("DIVIDEND_FCF")])
        write_csv(self.review_summary, list(self.summary_row("VALUATION").keys()), [self.summary_row("VALUATION"), self.summary_row("DIVIDEND_FCF")])
        write_csv(self.valuation_private, self.valuation_private_fields(), [self.valuation_private_row()])
        write_csv(self.dividend_private, self.dividend_private_fields(), [self.dividend_private_row()])
        self.run_candidates()
        report_text = self.report.read_text(encoding="utf-8")
        for secret in ("5.55", "6.66", "11.11", "22.22", "3.33"):
            self.assertNotIn(secret, report_text)

    def test_no_master_score_or_evidence_files_are_changed(self) -> None:
        master_before = self.master.read_text(encoding="utf-8")
        score_before = self.score.read_text(encoding="utf-8")
        evidence_before = self.evidence.read_text(encoding="utf-8")
        write_csv(self.validation, self.validation_fields(), [self.validation_row("VALUATION")])
        write_csv(self.review_summary, list(self.summary_row("VALUATION").keys()), [self.summary_row("VALUATION")])
        write_csv(self.valuation_private, self.valuation_private_fields(), [self.valuation_private_row()])
        self.run_candidates()
        self.assertEqual(self.master.read_text(encoding="utf-8"), master_before)
        self.assertEqual(self.score.read_text(encoding="utf-8"), score_before)
        self.assertEqual(self.evidence.read_text(encoding="utf-8"), evidence_before)


if __name__ == "__main__":
    unittest.main()
