from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_sec_kpi_extraction_gap_review import (
    MATRIX_FIELDS,
    SUMMARY_FIELDS,
    run_personal_sec_kpi_extraction_gap_review,
)


class PersonalSecKpiExtractionGapReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_kpi_gap_review_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.closure = self.tmp / "closure.csv"
        self.normalized = self.tmp / "normalized.csv"
        self.staging = self.tmp / "staging.csv"
        self.fetch_registry = self.tmp / "fetch_registry.csv"
        self.fetch_failures = self.tmp / "fetch_failures.csv"
        self.evidence = self.tmp / "evidence.csv"
        self.apply = self.tmp / "apply.csv"
        self.proposed = self.tmp / "proposed.csv"
        self.output_dir = self.tmp / "processed"
        self.report_dir = self.tmp / "reports"
        self.write_base_inputs()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def write_base_inputs(self) -> None:
        self.write_csv(
            self.closure,
            [
                "ticker",
                "isin",
                "company_name",
                "core_kpi_closure_status",
                "missing_core_kpis",
                "sec_scope_status",
                "reason_code",
            ],
            [
                {
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "company_name": "Alpha Inc",
                    "core_kpi_closure_status": "REVIEW",
                    "missing_core_kpis": "revenue_cagr_5y",
                    "sec_scope_status": "SEC_ELIGIBLE",
                    "reason_code": "CORE_KPI_MISSING;REVIEW_CORE_DATA",
                }
            ],
        )
        self.write_csv(
            self.normalized,
            [
                "ticker",
                "isin",
                "company_name",
                "source_name",
                "source_reference",
                "source_as_of_date",
                "fiscal_year",
                "currency",
                "revenue_cagr_5y",
                "gross_margin",
            ],
            [
                {
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "company_name": "Alpha Inc",
                    "source_name": "sec_companyfacts",
                    "source_reference": "SEC CompanyFacts CIK0000000001 FY2025",
                    "source_as_of_date": "2026-04-27",
                    "fiscal_year": "2025",
                    "currency": "USD",
                    "revenue_cagr_5y": "",
                    "gross_margin": "",
                }
            ],
        )
        self.write_csv(
            self.staging,
            [
                "ticker",
                "isin",
                "company_name",
                "kpi_name",
                "reported_value",
                "reported_unit",
                "source_name",
            ],
            [],
        )
        self.write_csv(
            self.fetch_registry,
            ["ticker", "isin", "company_name", "cik", "fetch_status", "source_name", "source_reference", "source_as_of_date", "notes"],
            [
                {
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "company_name": "Alpha Inc",
                    "cik": "0000000001",
                    "fetch_status": "FETCHED",
                    "source_name": "sec_companyfacts",
                    "source_reference": "SEC CompanyFacts CIK0000000001 FY2025",
                    "source_as_of_date": "2026-04-27",
                    "notes": "",
                }
            ],
        )
        self.write_csv(self.fetch_failures, ["ticker", "isin", "company_name", "cik", "failure_reason", "source_name", "notes"], [])
        self.write_csv(self.evidence, ["ticker", "isin", "company_name", "kpi_name", "evidence_present"], [])
        self.write_csv(self.apply, ["ticker", "isin", "company_name", "target_field", "apply_status"], [])
        self.write_csv(self.proposed, ["ticker", "isin", "company_name", "kpi_name", "reported_value"], [])

    def run_review(self, **overrides):
        kwargs = {
            "closure_queue": str(self.closure),
            "sec_normalized": str(self.normalized),
            "sec_staging": str(self.staging),
            "sec_fetch_registry": str(self.fetch_registry),
            "sec_fetch_failures": str(self.fetch_failures),
            "evidence_registry": str(self.evidence),
            "evidence_apply": str(self.apply),
            "proposed_updates": str(self.proposed),
            "output_dir": str(self.output_dir),
            "report_dir": str(self.report_dir),
        }
        kwargs.update(overrides)
        return run_personal_sec_kpi_extraction_gap_review(**kwargs)

    def test_missing_sec_normalized_artifact_writes_stable_no_normalized_gap(self) -> None:
        missing = self.tmp / "missing_normalized.csv"
        result = self.run_review(sec_normalized=str(missing))

        self.assertEqual(result.matrix_rows[0]["extraction_gap_type"], "NO_NORMALIZED_FACTS_FOR_HOLDING")
        self.assertEqual(result.summary_rows[0]["network_performed"], "False")
        self.assertTrue(result.report_output.exists())

    def test_candidate_sec_concepts_are_detected_for_revenue_cagr(self) -> None:
        result = self.run_review()
        concepts = {row["sec_concept"] for row in result.candidate_rows if row["kpi_field"] == "revenue_cagr_5y"}

        self.assertIn("Revenues", concepts)
        self.assertIn("RevenueFromContractWithCustomerExcludingAssessedTax", concepts)
        self.assertEqual(result.matrix_rows[0]["candidate_fact_count"], "5")

    def test_gross_margin_candidates_are_derived_logic_gap_without_calculation(self) -> None:
        self.write_csv(
            self.closure,
            ["ticker", "isin", "company_name", "core_kpi_closure_status", "missing_core_kpis", "sec_scope_status", "reason_code"],
            [
                {
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "company_name": "Alpha Inc",
                    "core_kpi_closure_status": "REVIEW",
                    "missing_core_kpis": "gross_margin",
                    "sec_scope_status": "SEC_ELIGIBLE",
                    "reason_code": "CORE_KPI_MISSING",
                }
            ],
        )
        result = self.run_review()
        concepts = {row["sec_concept"] for row in result.candidate_rows}

        self.assertIn("GrossProfit", concepts)
        self.assertIn("Revenues", concepts)
        self.assertEqual(result.matrix_rows[0]["extraction_gap_type"], "DERIVED_METRIC_LOGIC_MISSING")

    def test_normalized_value_without_evidence_is_candidate_found_not_mapped(self) -> None:
        self.write_csv(
            self.normalized,
            [
                "ticker",
                "isin",
                "company_name",
                "source_name",
                "source_reference",
                "source_as_of_date",
                "fiscal_year",
                "currency",
                "revenue_cagr_5y",
            ],
            [
                {
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "company_name": "Alpha Inc",
                    "source_name": "sec_companyfacts",
                    "source_reference": "SEC CompanyFacts CIK0000000001 FY2025",
                    "source_as_of_date": "2026-04-27",
                    "fiscal_year": "2025",
                    "currency": "USD",
                    "revenue_cagr_5y": "12.3",
                }
            ],
        )
        result = self.run_review()

        self.assertEqual(result.matrix_rows[0]["evidence_registry_match_status"], "NO_EVIDENCE")
        self.assertEqual(result.matrix_rows[0]["extraction_gap_type"], "CANDIDATE_FACTS_FOUND_NOT_MAPPED")

    def test_private_paths_and_user_agent_files_are_masked_in_report(self) -> None:
        private_normalized = self.tmp / "data" / "raw" / "private" / "fundamentals" / "sec_user_agent.local.txt"
        private_normalized.parent.mkdir(parents=True, exist_ok=True)
        private_normalized.write_text("not used as a CSV", encoding="utf-8")
        result = self.run_review(sec_normalized=str(private_normalized))
        text = result.report_output.read_text(encoding="utf-8")

        self.assertIn("<private_path>", text)
        self.assertNotIn("sec_user_agent.local.txt", text)
        self.assertNotIn("data/raw/private/fundamentals", text)

    def test_summary_has_stable_columns_and_no_network(self) -> None:
        result = self.run_review()
        summary_rows = self.read_csv(result.gap_summary_output)
        matrix_rows = self.read_csv(result.gap_matrix_output)

        self.assertEqual(list(summary_rows[0].keys()), SUMMARY_FIELDS)
        self.assertEqual(list(matrix_rows[0].keys()), MATRIX_FIELDS)
        self.assertEqual(summary_rows[0]["network_performed"], "False")

    def test_outputs_do_not_touch_score_monthly_or_website_files(self) -> None:
        result = self.run_review()
        output_paths = {
            result.gap_matrix_output.as_posix(),
            result.concept_candidates_output.as_posix(),
            result.gap_summary_output.as_posix(),
            result.report_output.as_posix(),
        }

        self.assertTrue(all("website" not in path for path in output_paths))
        self.assertTrue(all("monthly" not in path for path in output_paths))
        self.assertTrue(all("score" not in path for path in output_paths))


if __name__ == "__main__":
    unittest.main()
