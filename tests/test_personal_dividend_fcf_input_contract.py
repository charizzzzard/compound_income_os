from __future__ import annotations

import csv
import shutil
import unittest
from pathlib import Path

from src.personal_dividend_fcf_input_contract import run_personal_dividend_fcf_input_contract

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


class PersonalDividendFcfInputContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_dividend_fcf_input_contract"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.kpi_tier = self.tmp / "kpi_tier.csv"
        self.scores = self.tmp / "scores.csv"
        self.registry = self.tmp / "registry.csv"
        self.applied = self.tmp / "applied.csv"
        self.sec_scope = self.tmp / "sec_scope.csv"
        self.sec_identity = self.tmp / "sec_identity.csv"
        self.metrics = self.tmp / "metrics.json"
        self.review_input = self.tmp / "review_input.csv"
        self.queue = self.tmp / "queue.csv"
        self.summary = self.tmp / "summary.csv"
        self.report = self.tmp / "report.md"
        self.metrics.write_text(
            '{"kpis":{"fcf_margin":{"kpi_tier":"DIVIDEND_FCF_REQUIRED"},"payout_ratio_fcf":{"kpi_tier":"DIVIDEND_FCF_REQUIRED"},"fcf_per_share_cagr_5y":{"kpi_tier":"DIVIDEND_FCF_REQUIRED"},"gross_margin":{"kpi_tier":"CORE_QUALITY_REQUIRED"}}}',
            encoding="utf-8",
        )
        write_csv(self.scores, ["ticker", "isin"], [{"ticker": "AAA", "isin": "US1"}])
        write_csv(self.registry, ["ticker", "isin", "kpi_name"], [])
        write_csv(self.applied, ["ticker", "isin", "fcf_margin", "payout_ratio_fcf", "fcf_per_share_cagr_5y"], [{"ticker": "AAA", "isin": "US1", "fcf_margin": "", "payout_ratio_fcf": "", "fcf_per_share_cagr_5y": ""}])
        write_csv(self.sec_scope, ["original_ticker", "original_isin", "reviewed_enabled", "reviewed_cik"], [])
        write_csv(self.sec_identity, ["isin", "current_ticker", "reviewed_cik"], [])

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def standard_gap(self) -> dict[str, str]:
        return {
            "ticker": "AAA",
            "isin": "US1",
            "company_name": "Alpha",
            "company_type_profile": "STANDARD",
            "dividend_fcf_data_status": "MISSING",
            "missing_dividend_fcf_kpis": "fcf_margin; fcf_per_share_cagr_5y; payout_ratio_fcf",
        }

    def write_kpi_rows(self, rows: list[dict[str, str]]) -> None:
        write_csv(
            self.kpi_tier,
            ["ticker", "isin", "company_name", "company_type_profile", "dividend_fcf_data_status", "missing_dividend_fcf_kpis"],
            rows,
        )

    def write_review_rows(self, rows: list[dict[str, str]]) -> None:
        write_csv(
            self.review_input,
            [
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
                "dividend_fcf_notes",
            ],
            rows,
        )

    def run_contract(self, **overrides):
        params = {
            "kpi_tier_input": str(self.kpi_tier),
            "scores_input": str(self.scores),
            "evidence_registry_input": str(self.registry),
            "evidence_applied_master_input": str(self.applied),
            "sec_scope_review_input": str(self.sec_scope),
            "sec_identity_apply_input": str(self.sec_identity),
            "metric_definitions_input": str(self.metrics),
            "review_input": str(self.review_input),
            "queue_output": str(self.queue),
            "summary_output": str(self.summary),
            "report_output": str(self.report),
        }
        params.update(overrides)
        return run_personal_dividend_fcf_input_contract(**params)

    def summary_value(self, metric: str) -> str:
        return {row["metric"]: row["value"] for row in read_csv(self.summary)}[metric]

    def queue_row(self) -> dict[str, str]:
        return read_csv(self.queue)[0]

    def test_standard_missing_dividend_fcf_kpis_are_queued(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.run_contract(review_input=str(self.tmp / "missing.csv"))
        row = self.queue_row()
        self.assertEqual(row["dividend_fcf_input_status"], "MISSING")
        self.assertIn("DIVIDEND_FCF_REQUIRED_MISSING", row["reason_code"])

    def test_non_standard_row_is_not_applicable(self) -> None:
        row = self.standard_gap()
        row["company_type_profile"] = "OTHER"
        self.write_kpi_rows([row])
        self.run_contract(review_input=str(self.tmp / "missing.csv"))
        self.assertEqual(read_csv(self.queue), [])
        self.assertEqual(self.summary_value("not_applicable_rows_count"), "1")
        self.assertIn("PROFILE_NOT_STANDARD", self.summary_value("reason_codes"))

    def test_missing_optional_review_input_is_not_a_crash(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.run_contract(review_input=str(self.tmp / "missing.csv"))
        self.assertEqual(self.summary_value("input_file_status"), "MISSING")
        self.assertEqual(self.summary_value("missing_rows_count"), "1")
        self.assertIn("INPUT_FILE_MISSING", self.summary_value("reason_codes"))

    def test_review_input_missing_value_remains_missing(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.write_review_rows([self.review_row(fcf_margin="", reference="source")])
        self.run_contract()
        self.assertEqual(self.queue_row()["dividend_fcf_input_status"], "MISSING")
        self.assertIn("DIVIDEND_FCF_REQUIRED_MISSING", self.queue_row()["reason_code"])

    def test_source_reference_missing_requires_review(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.write_review_rows([self.review_row(reference="")])
        self.run_contract()
        self.assertEqual(self.queue_row()["dividend_fcf_input_status"], "REVIEW")
        self.assertIn("DIVIDEND_FCF_SOURCE_REFERENCE_MISSING", self.queue_row()["reason_code"])

    def test_approved_review_input_is_ok(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.write_review_rows([self.review_row(reference="reviewed-source")])
        self.run_contract()
        self.assertEqual(self.queue_row()["dividend_fcf_input_status"], "OK")
        self.assertIn("DIVIDEND_FCF_APPROVED", self.queue_row()["reason_code"])

    def test_out_of_range_value_is_invalid(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.write_review_rows([self.review_row(fcf_margin="500", reference="source")])
        self.run_contract()
        self.assertEqual(self.queue_row()["dividend_fcf_input_status"], "INVALID")
        self.assertIn("DIVIDEND_FCF_VALUE_OUT_OF_RANGE", self.queue_row()["reason_code"])

    def test_evidence_registry_hint_requires_existing_evidence_review(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        write_csv(self.registry, ["ticker", "isin", "kpi_name"], [{"ticker": "AAA", "isin": "US1", "kpi_name": "fcf_margin"}])
        self.run_contract(review_input=str(self.tmp / "missing.csv"))
        self.assertEqual(self.queue_row()["recommended_closure_path"], "REVIEW_EXISTING_EVIDENCE")

    def test_sec_identity_structurally_present_is_sec_evidence_possible(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        write_csv(self.sec_identity, ["isin", "current_ticker", "reviewed_cik"], [{"isin": "US1", "current_ticker": "AAA", "reviewed_cik": "0000001"}])
        self.run_contract(review_input=str(self.tmp / "missing.csv"))
        self.assertEqual(self.queue_row()["recommended_closure_path"], "SEC_EVIDENCE_POSSIBLE")

    def test_missing_sec_identity_and_evidence_requires_manual_evidence(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.run_contract(review_input=str(self.tmp / "missing.csv"))
        self.assertEqual(self.queue_row()["recommended_closure_path"], "MANUAL_EVIDENCE_REQUIRED")

    def test_missing_values_are_not_imputed_or_reported(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.run_contract(review_input=str(self.tmp / "missing.csv"))
        row = self.queue_row()
        self.assertEqual(row["fcf_margin"], "")
        self.assertEqual(row["payout_ratio_fcf"], "")
        self.assertEqual(row["fcf_per_share_cagr_5y"], "")
        self.assertIn("NO_IMPUTATION", row["reason_code"])

    def test_report_does_not_dump_private_review_values(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        self.write_review_rows([self.review_row(fcf_margin="5.55", payout="44.4", cagr="3.33", reference="private-source", notes="secret note")])
        self.run_contract()
        text = self.report.read_text(encoding="utf-8")
        self.assertNotIn("5.55", text)
        self.assertNotIn("44.4", text)
        self.assertNotIn("secret note", text)

    def test_no_master_or_score_file_changes_are_performed(self) -> None:
        self.write_kpi_rows([self.standard_gap()])
        score_before = self.scores.read_text(encoding="utf-8")
        applied_before = self.applied.read_text(encoding="utf-8")
        self.run_contract(review_input=str(self.tmp / "missing.csv"))
        self.assertEqual(self.scores.read_text(encoding="utf-8"), score_before)
        self.assertEqual(self.applied.read_text(encoding="utf-8"), applied_before)
        self.assertEqual(self.summary_value("no_imputation_confirmed"), "True")

    def review_row(self, *, fcf_margin: str = "5", payout: str = "40", cagr: str = "3", reference: str = "source", notes: str = "private") -> dict[str, str]:
        return {
            "ticker": "AAA",
            "isin": "US1",
            "fcf_margin": fcf_margin,
            "payout_ratio_fcf": payout,
            "fcf_per_share_cagr_5y": cagr,
            "dividend_fcf_review_status": "APPROVED",
            "dividend_fcf_source_type": "MANUAL_REVIEW",
            "dividend_fcf_source_name": "review",
            "dividend_fcf_source_reference": reference,
            "dividend_fcf_source_as_of_date": "2026-04-26",
            "dividend_fcf_reviewed_by": "analyst",
            "dividend_fcf_reviewed_at": "2026-04-26",
            "dividend_fcf_notes": notes,
        }


if __name__ == "__main__":
    unittest.main()
