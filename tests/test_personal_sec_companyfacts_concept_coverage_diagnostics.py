from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_sec_companyfacts_concept_coverage_diagnostics import (
    DIAGNOSTIC_FIELDS,
    SUMMARY_FIELDS,
    run_personal_sec_companyfacts_concept_coverage_diagnostics,
)


class PersonalSecCompanyfactsConceptCoverageDiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_concept_coverage_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.period_review = self.tmp / "period_review.csv"
        self.period_summary = self.tmp / "period_summary.csv"
        self.gap_queue = self.tmp / "gap_queue.csv"
        self.approved_facts = self.tmp / "approved_facts.csv"
        self.concept_candidates = self.tmp / "concept_candidates.csv"
        self.output = self.tmp / "processed" / "diagnostics.csv"
        self.summary = self.tmp / "processed" / "summary.csv"
        self.report = self.tmp / "reports" / "report.md"
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
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def period_row(self, **updates: str) -> dict[str, str]:
        row = {
            "review_id": "SEC_GAP_REVIEW_0001",
            "ticker": "AAA",
            "isin": "US0000000001",
            "company_name": "Alpha Inc",
            "kpi_field": "gross_margin",
            "review_bucket": "SEC_REFRESH_CANDIDATE",
            "current_value": "",
            "stale_or_old_fiscal_year": "False",
            "stale_reason": "",
            "required_concepts": "gross_profit: GrossProfit | revenue: RevenueFromContractWithCustomerExcludingAssessedTax/Revenues",
            "available_concepts": "revenue: RevenueFromContractWithCustomerExcludingAssessedTax",
            "missing_concepts": "gross_profit",
            "selected_start_fiscal_year": "",
            "selected_end_fiscal_year": "",
            "selected_start_period": "",
            "selected_end_period": "",
            "selected_start_value": "",
            "selected_end_value": "",
            "candidate_value": "",
            "candidate_value_not_applied": "False",
            "period_selection_status": "MISSING_REQUIRED_CONCEPT",
            "confidence": "HIGH",
            "blocking_reason": "Missing annual facts for role.",
            "recommended_action": "Review mapping.",
            "source_artifact": "data/processed/personal_sec_companyfacts_approved_facts.csv",
            "notes": "fixture",
        }
        row.update(updates)
        return row

    def queue_row(self, **updates: str) -> dict[str, str]:
        row = {
            "review_id": "SEC_GAP_REVIEW_0001",
            "ticker": "AAA",
            "isin": "US0000000001",
            "company_name": "Alpha Inc",
            "kpi_field": "gross_margin",
        }
        row.update(updates)
        return row

    def fact(self, concept: str, year: str = "2025", *, isin: str = "US0000000001", kpi: str = "gross_margin") -> dict[str, str]:
        return {
            "holding_name": "Alpha Inc",
            "ticker": "AAA",
            "isin": isin,
            "kpi_field": kpi,
            "sec_concept": concept,
            "fiscal_year": year,
            "fiscal_period": "FY",
            "form": "10-K",
            "period_end": f"{year}-12-31",
            "annual_basis": "FY_10K",
        }

    def candidate(self, concept: str, *, isin: str = "US0000000001", kpi: str = "gross_margin") -> dict[str, str]:
        return {"isin": isin, "kpi_field": kpi, "sec_concept": concept}

    def write_base_inputs(self) -> None:
        self.write_csv(self.period_review, list(self.period_row().keys()), [self.period_row()])
        self.write_csv(
            self.period_summary,
            ["no_score_change_confirmed", "no_network_confirmed", "raw_master_mutation_performed"],
            [{"no_score_change_confirmed": "True", "no_network_confirmed": "True", "raw_master_mutation_performed": "False"}],
        )
        self.write_csv(self.gap_queue, list(self.queue_row().keys()), [self.queue_row()])
        self.write_csv(self.approved_facts, list(self.fact("RevenueFromContractWithCustomerExcludingAssessedTax").keys()), [self.fact("RevenueFromContractWithCustomerExcludingAssessedTax")])
        self.write_csv(self.concept_candidates, list(self.candidate("GrossProfit").keys()), [self.candidate("GrossProfit")])

    def run_diagnostics(self):
        return run_personal_sec_companyfacts_concept_coverage_diagnostics(
            period_review=self.period_review,
            period_review_summary=self.period_summary,
            gap_review_queue=self.gap_queue,
            approved_facts=self.approved_facts,
            concept_candidates=self.concept_candidates,
            output=self.output,
            summary_output=self.summary,
            report_output=self.report,
        )

    def test_reads_blocker_rows_from_period_selection_output(self) -> None:
        rows = self.read_csv(self.run_diagnostics().diagnostics_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["period_selection_status"], "MISSING_REQUIRED_CONCEPT")

    def test_true_sec_data_gap_when_no_related_concepts_exist(self) -> None:
        self.write_csv(self.approved_facts, list(self.fact("OtherConcept").keys()), [])
        self.write_csv(self.concept_candidates, list(self.candidate("OtherConcept").keys()), [])
        row = self.read_csv(self.run_diagnostics().diagnostics_path)[0]
        self.assertEqual(row["diagnostic_blocker_class"], "TRUE_SEC_DATA_GAP")

    def test_concept_alias_gap_when_related_available_concept_exists(self) -> None:
        row = self.read_csv(self.run_diagnostics().diagnostics_path)[0]
        self.assertEqual(row["diagnostic_blocker_class"], "CONCEPT_ALIAS_GAP")
        self.assertIn("GrossProfit", row["available_related_concepts"])

    def test_insufficient_cagr_history_classified_as_period_history_gap(self) -> None:
        self.write_csv(
            self.period_review,
            list(self.period_row().keys()),
            [self.period_row(kpi_field="revenue_cagr_5y", period_selection_status="INSUFFICIENT_PERIOD_HISTORY", missing_concepts="", required_concepts="revenue_series: Revenues")],
        )
        row = self.read_csv(self.run_diagnostics().diagnostics_path)[0]
        self.assertEqual(row["diagnostic_blocker_class"], "PERIOD_HISTORY_GAP")

    def test_ambiguous_rows_classified_as_period_ambiguity(self) -> None:
        self.write_csv(self.period_review, list(self.period_row().keys()), [self.period_row(period_selection_status="PERIOD_AMBIGUITY_REVIEW")])
        row = self.read_csv(self.run_diagnostics().diagnostics_path)[0]
        self.assertEqual(row["diagnostic_blocker_class"], "PERIOD_AMBIGUITY")

    def test_stale_no_refresh_rows_classified_as_stale_refresh_not_available(self) -> None:
        self.write_csv(
            self.period_review,
            list(self.period_row().keys()),
            [self.period_row(review_bucket="STALE_VALUE_REVIEW", period_selection_status="STALE_VALUE_NO_REFRESH_AVAILABLE", current_value="0.1", stale_or_old_fiscal_year="True")],
        )
        row = self.read_csv(self.run_diagnostics().diagnostics_path)[0]
        self.assertEqual(row["diagnostic_blocker_class"], "STALE_REFRESH_NOT_AVAILABLE")

    def test_preserves_review_id(self) -> None:
        row = self.read_csv(self.run_diagnostics().diagnostics_path)[0]
        self.assertEqual(row["review_id"], "SEC_GAP_REVIEW_0001")

    def test_writes_stable_csv_headers(self) -> None:
        result = self.run_diagnostics()
        rows = self.read_csv(result.diagnostics_path)
        summary = self.read_csv(result.summary_path)
        self.assertEqual(list(rows[0].keys()), DIAGNOSTIC_FIELDS)
        self.assertEqual(list(summary[0].keys()), SUMMARY_FIELDS)

    def test_writes_summary_counts_correctly(self) -> None:
        self.write_csv(
            self.period_review,
            list(self.period_row().keys()),
            [
                self.period_row(),
                self.period_row(review_id="SEC_GAP_REVIEW_0002", period_selection_status="INSUFFICIENT_PERIOD_HISTORY", kpi_field="revenue_cagr_5y"),
                self.period_row(review_id="SEC_GAP_REVIEW_0003", period_selection_status="STALE_VALUE_NO_REFRESH_AVAILABLE", review_bucket="STALE_VALUE_REVIEW"),
            ],
        )
        summary = self.read_csv(self.run_diagnostics().summary_path)[0]
        self.assertEqual(summary["total_diagnostic_rows"], "3")
        self.assertEqual(summary["concept_alias_gap_rows"], "1")
        self.assertEqual(summary["period_history_gap_rows"], "1")
        self.assertEqual(summary["stale_refresh_not_available_rows"], "1")
        self.assertEqual(summary["candidate_values_applied"], "0")

    def test_confirms_no_candidate_values_are_applied(self) -> None:
        row = self.read_csv(self.run_diagnostics().diagnostics_path)[0]
        summary = self.read_csv(self.run_diagnostics().summary_path)[0]
        self.assertEqual(row["candidate_value_not_applied"], "True")
        self.assertEqual(row["apply_status"], "DIAGNOSTIC_ONLY")
        self.assertEqual(summary["no_values_applied_confirmed"], "True")

    def test_no_score_monthly_watchlist_dashboard_artifacts_created(self) -> None:
        self.run_diagnostics()
        names = {path.name for path in (self.tmp / "processed").iterdir()}
        self.assertNotIn("company_scores.csv", names)
        self.assertNotIn("monthly_buy_ranking.csv", names)
        self.assertNotIn("watchlist_ranked.csv", names)
        self.assertNotIn("dashboard_payload.json", names)

    def test_missing_required_input_fails_deterministically(self) -> None:
        self.period_review.unlink()
        with self.assertRaisesRegex(RuntimeError, "MISSING_PERIOD_SELECTION_REVIEW"):
            self.run_diagnostics()


if __name__ == "__main__":
    unittest.main()
