from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_sec_companyfacts_period_selection_review import REVIEW_FIELDS, SUMMARY_FIELDS, run_personal_sec_companyfacts_period_selection_review


class PersonalSecCompanyfactsPeriodSelectionReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_period_selection_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.queue = self.tmp / "queue.csv"
        self.queue_summary = self.tmp / "queue_summary.csv"
        self.master = self.tmp / "applied_master.csv"
        self.facts = self.tmp / "approved_facts.csv"
        self.output = self.tmp / "processed" / "review.csv"
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

    def queue_row(self, **updates: str) -> dict[str, str]:
        row = {
            "review_id": "SEC_GAP_REVIEW_0001",
            "ticker": "AAA",
            "isin": "US0000000001",
            "company_name": "Alpha Inc",
            "kpi_field": "gross_margin",
            "current_value": "",
            "baseline_value": "",
            "evidence_applied_value": "",
            "closure_status": "STILL_MISSING",
            "stale_or_old_fiscal_year": "False",
            "stale_reason": "",
            "fiscal_year_end": "",
            "source_as_of_date": "",
            "source_forms": "",
            "review_bucket": "SEC_REFRESH_CANDIDATE",
            "priority": "HIGH",
            "recommended_action": "review",
            "evidence_id": "",
            "evidence_confidence": "",
            "notes": "",
        }
        row.update(updates)
        return row

    def fact(self, concept: str, value: str, year: str = "2025", *, isin: str = "US0000000001", filed: str = "2026-01-01") -> dict[str, str]:
        return {
            "holding_name": "Alpha Inc",
            "ticker": "AAA",
            "isin": isin,
            "kpi_field": "gross_margin",
            "formula_recipe": "",
            "formula_role": "",
            "approved_sec_concept": concept,
            "sec_cik": "0000001",
            "sec_entity_name": "Alpha Inc",
            "sec_taxonomy": "us-gaap",
            "sec_concept": concept,
            "sec_label": concept,
            "sec_description": "",
            "unit": "USD",
            "fiscal_year": year,
            "fiscal_period": "FY",
            "form": "10-K",
            "filed_date": filed,
            "frame": f"CY{year}",
            "period_start": f"{year}-01-01",
            "period_end": f"{year}-12-31",
            "accession": f"accn-{year}",
            "value": value,
            "value_is_numeric": "True",
            "annual_basis": "FY_10K",
            "value_source": "fixture",
            "approved_role_status": "APPROVED",
            "export_status": "EXPORTED",
            "rejection_reason": "",
        }

    def write_base_inputs(self) -> None:
        self.write_csv(self.queue, list(self.queue_row().keys()), [self.queue_row()])
        self.write_csv(
            self.queue_summary,
            ["no_score_change_confirmed", "no_network_confirmed", "raw_master_mutation_performed"],
            [{"no_score_change_confirmed": "True", "no_network_confirmed": "True", "raw_master_mutation_performed": "False"}],
        )
        self.write_csv(self.master, ["ticker", "isin", "company_name"], [{"ticker": "AAA", "isin": "US0000000001", "company_name": "Alpha Inc"}])
        self.write_csv(
            self.facts,
            list(self.fact("GrossProfit", "40").keys()),
            [self.fact("GrossProfit", "40"), self.fact("RevenueFromContractWithCustomerExcludingAssessedTax", "100")],
        )

    def run_review(self):
        return run_personal_sec_companyfacts_period_selection_review(
            review_queue=self.queue,
            review_queue_summary=self.queue_summary,
            evidence_applied_master=self.master,
            approved_facts=self.facts,
            output=self.output,
            summary_output=self.summary,
            report_output=self.report,
        )

    def test_reads_sec_refresh_candidate_rows_from_queue(self) -> None:
        rows = self.read_csv(self.run_review().review_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["review_bucket"], "SEC_REFRESH_CANDIDATE")

    def test_reads_stale_value_review_rows_from_queue(self) -> None:
        self.write_csv(
            self.queue,
            list(self.queue_row().keys()),
            [self.queue_row(review_bucket="STALE_VALUE_REVIEW", closure_status="CLOSED_BY_SEC_DERIVED_KPI", current_value="0.2", stale_or_old_fiscal_year="True", fiscal_year_end="2020")],
        )
        rows = self.read_csv(self.run_review().review_path)
        self.assertEqual(rows[0]["review_bucket"], "STALE_VALUE_REVIEW")

    def test_maps_gross_margin_to_revenue_and_gross_profit_requirements(self) -> None:
        row = self.read_csv(self.run_review().review_path)[0]
        self.assertIn("gross_profit: GrossProfit", row["required_concepts"])
        self.assertIn("revenue:", row["required_concepts"])

    def test_maps_operating_margin_to_revenue_and_operating_income_requirements(self) -> None:
        self.write_csv(self.queue, list(self.queue_row().keys()), [self.queue_row(kpi_field="operating_margin")])
        self.write_csv(
            self.facts,
            list(self.fact("OperatingIncomeLoss", "25").keys()),
            [self.fact("OperatingIncomeLoss", "25"), self.fact("RevenueFromContractWithCustomerExcludingAssessedTax", "100")],
        )
        row = self.read_csv(self.run_review().review_path)[0]
        self.assertIn("operating_income: OperatingIncomeLoss", row["required_concepts"])
        self.assertIn("revenue:", row["required_concepts"])

    def test_maps_revenue_cagr_to_start_end_revenue_requirements(self) -> None:
        self.write_csv(self.queue, list(self.queue_row().keys()), [self.queue_row(kpi_field="revenue_cagr_5y")])
        self.write_csv(
            self.facts,
            list(self.fact("RevenueFromContractWithCustomerExcludingAssessedTax", "100").keys()),
            [
                self.fact("RevenueFromContractWithCustomerExcludingAssessedTax", "100", "2020"),
                self.fact("RevenueFromContractWithCustomerExcludingAssessedTax", "200", "2025"),
            ],
        )
        row = self.read_csv(self.run_review().review_path)[0]
        self.assertIn("revenue_series", row["required_concepts"])
        self.assertEqual(row["selected_start_fiscal_year"], "2020")
        self.assertEqual(row["selected_end_fiscal_year"], "2025")

    def test_maps_share_count_cagr_to_start_end_share_count_requirements(self) -> None:
        self.write_csv(self.queue, list(self.queue_row().keys()), [self.queue_row(kpi_field="share_count_cagr_5y")])
        self.write_csv(
            self.facts,
            list(self.fact("WeightedAverageNumberOfDilutedSharesOutstanding", "100", "2020").keys()),
            [
                self.fact("WeightedAverageNumberOfDilutedSharesOutstanding", "100", "2020"),
                self.fact("WeightedAverageNumberOfDilutedSharesOutstanding", "120", "2025"),
            ],
        )
        row = self.read_csv(self.run_review().review_path)[0]
        self.assertIn("share_count_series", row["required_concepts"])
        self.assertEqual(row["selected_start_fiscal_year"], "2020")
        self.assertEqual(row["selected_end_fiscal_year"], "2025")

    def test_ready_for_derived_kpi_review_when_required_periods_available(self) -> None:
        row = self.read_csv(self.run_review().review_path)[0]
        self.assertEqual(row["period_selection_status"], "READY_FOR_DERIVED_KPI_REVIEW")
        self.assertEqual(row["candidate_value_not_applied"], "True")

    def test_missing_required_concept_when_concept_missing(self) -> None:
        self.write_csv(self.facts, list(self.fact("RevenueFromContractWithCustomerExcludingAssessedTax", "100").keys()), [self.fact("RevenueFromContractWithCustomerExcludingAssessedTax", "100")])
        row = self.read_csv(self.run_review().review_path)[0]
        self.assertEqual(row["period_selection_status"], "MISSING_REQUIRED_CONCEPT")
        self.assertIn("gross_profit", row["missing_concepts"])

    def test_insufficient_period_history_for_cagr(self) -> None:
        self.write_csv(self.queue, list(self.queue_row().keys()), [self.queue_row(kpi_field="revenue_cagr_5y")])
        self.write_csv(
            self.facts,
            list(self.fact("RevenueFromContractWithCustomerExcludingAssessedTax", "100").keys()),
            [
                self.fact("RevenueFromContractWithCustomerExcludingAssessedTax", "100", "2024"),
                self.fact("RevenueFromContractWithCustomerExcludingAssessedTax", "110", "2025"),
            ],
        )
        row = self.read_csv(self.run_review().review_path)[0]
        self.assertEqual(row["period_selection_status"], "INSUFFICIENT_PERIOD_HISTORY")

    def test_local_sec_snapshot_missing_when_no_local_evidence_exists(self) -> None:
        self.facts.unlink()
        row = self.read_csv(self.run_review().review_path)[0]
        self.assertEqual(row["period_selection_status"], "LOCAL_SEC_SNAPSHOT_MISSING")

    def test_stale_value_refresh_candidate_with_newer_period_evidence(self) -> None:
        self.write_csv(
            self.queue,
            list(self.queue_row().keys()),
            [self.queue_row(review_bucket="STALE_VALUE_REVIEW", closure_status="CLOSED_BY_SEC_DERIVED_KPI", current_value="0.2", stale_or_old_fiscal_year="True", fiscal_year_end="2020")],
        )
        row = self.read_csv(self.run_review().review_path)[0]
        self.assertEqual(row["period_selection_status"], "STALE_VALUE_REFRESH_CANDIDATE")

    def test_candidate_values_are_not_applied(self) -> None:
        row = self.read_csv(self.run_review().review_path)[0]
        summary = self.read_csv(self.run_review().summary_path)[0]
        self.assertTrue(row["candidate_value"])
        self.assertEqual(row["candidate_value_not_applied"], "True")
        self.assertEqual(summary["candidate_values_applied"], "0")
        self.assertEqual(summary["no_values_applied_confirmed"], "True")

    def test_writes_stable_csv_headers(self) -> None:
        result = self.run_review()
        rows = self.read_csv(result.review_path)
        summary = self.read_csv(result.summary_path)
        self.assertEqual(list(rows[0].keys()), REVIEW_FIELDS)
        self.assertEqual(list(summary[0].keys()), SUMMARY_FIELDS)

    def test_writes_summary_counts_correctly(self) -> None:
        self.write_csv(
            self.queue,
            list(self.queue_row().keys()),
            [
                self.queue_row(),
                self.queue_row(review_id="SEC_GAP_REVIEW_0002", review_bucket="STALE_VALUE_REVIEW", closure_status="CLOSED_BY_SEC_DERIVED_KPI", current_value="0.2", stale_or_old_fiscal_year="True", fiscal_year_end="2020"),
            ],
        )
        summary = self.read_csv(self.run_review().summary_path)[0]
        self.assertEqual(summary["total_review_rows"], "2")
        self.assertEqual(summary["sec_refresh_candidate_rows"], "1")
        self.assertEqual(summary["stale_value_review_rows"], "1")

    def test_no_score_monthly_watchlist_dashboard_artifacts_created(self) -> None:
        self.run_review()
        names = {path.name for path in (self.tmp / "processed").iterdir()}
        self.assertNotIn("company_scores.csv", names)
        self.assertNotIn("monthly_buy_ranking.csv", names)
        self.assertNotIn("watchlist_ranked.csv", names)
        self.assertNotIn("dashboard_payload.json", names)

    def test_missing_required_input_fails_deterministically(self) -> None:
        self.queue.unlink()
        with self.assertRaisesRegex(RuntimeError, "MISSING_SEC_CORE_KPI_GAP_REVIEW_QUEUE"):
            self.run_review()


if __name__ == "__main__":
    unittest.main()
