from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_sec_concept_alias_review_table import (
    ALIAS_REVIEW_FIELDS,
    SUMMARY_FIELDS,
    classify_alias_candidate,
    run_personal_sec_concept_alias_review_table,
)


class PersonalSecConceptAliasReviewTableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_alias_review_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.diagnostics = self.tmp / "diagnostics.csv"
        self.diagnostics_summary = self.tmp / "diagnostics_summary.csv"
        self.period_review = self.tmp / "period_review.csv"
        self.gap_queue = self.tmp / "gap_queue.csv"
        self.approved_facts = self.tmp / "approved_facts.csv"
        self.concept_candidates = self.tmp / "concept_candidates.csv"
        self.output = self.tmp / "processed" / "alias_review.csv"
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

    def diagnostic_row(self, **updates: str) -> dict[str, str]:
        row = {
            "review_id": "SEC_GAP_REVIEW_0001",
            "ticker": "AAA",
            "isin": "US0000000001",
            "company_name": "Alpha Inc",
            "kpi_field": "gross_margin",
            "period_selection_status": "MISSING_REQUIRED_CONCEPT",
            "review_bucket": "SEC_REFRESH_CANDIDATE",
            "required_concepts": "gross_profit: GrossProfit | revenue: RevenueFromContractWithCustomerExcludingAssessedTax/Revenues/SalesRevenueNet",
            "missing_concepts": "gross_profit",
            "available_related_concepts": "GrossProfit; RevenueFromContractWithCustomerExcludingAssessedTax",
            "available_concepts_count": "2",
            "available_annual_periods": "",
            "minimum_required_period_span": "0",
            "actual_available_period_span": "0",
            "diagnostic_blocker_class": "CONCEPT_ALIAS_GAP",
            "likely_fix_type": "SEC_CONCEPT_ALIAS_OR_ROLE_MAPPING_REVIEW",
            "recommended_action": "review aliases",
            "source_artifact": "data/processed/personal_sec_companyfacts_approved_facts.csv",
            "candidate_value_not_applied": "True",
            "apply_status": "DIAGNOSTIC_ONLY",
            "notes": "",
        }
        row.update(updates)
        return row

    def fact(self, concept: str, year: str = "2025", *, kpi: str = "gross_margin") -> dict[str, str]:
        return {
            "holding_name": "Alpha Inc",
            "ticker": "AAA",
            "isin": "US0000000001",
            "kpi_field": kpi,
            "sec_concept": concept,
            "sec_label": concept,
            "sec_description": f"{concept} description",
            "fiscal_year": year,
            "fiscal_period": "FY",
            "form": "10-K",
            "period_end": f"{year}-12-31",
            "annual_basis": "FY_10K",
        }

    def candidate(self, concept: str, *, kpi: str = "gross_margin") -> dict[str, str]:
        return {
            "isin": "US0000000001",
            "kpi_field": kpi,
            "sec_concept": concept,
            "sec_label_or_description": concept,
            "source_artifact": "data/processed/personal_sec_kpi_extraction_concept_candidates.csv",
        }

    def write_base_inputs(self) -> None:
        diagnostics_rows = [
            self.diagnostic_row(),
            self.diagnostic_row(
                review_id="SEC_GAP_REVIEW_9999",
                diagnostic_blocker_class="PERIOD_HISTORY_GAP",
                kpi_field="revenue_cagr_5y",
                missing_concepts="",
            ),
        ]
        self.write_csv(self.diagnostics, list(self.diagnostic_row().keys()), diagnostics_rows)
        self.write_csv(
            self.diagnostics_summary,
            ["no_score_change_confirmed", "no_network_confirmed", "raw_master_mutation_performed"],
            [{"no_score_change_confirmed": "True", "no_network_confirmed": "True", "raw_master_mutation_performed": "False"}],
        )
        self.write_csv(self.period_review, ["review_id", "period_selection_status"], [{"review_id": "SEC_GAP_REVIEW_0001", "period_selection_status": "MISSING_REQUIRED_CONCEPT"}])
        self.write_csv(self.gap_queue, ["review_id", "ticker", "isin", "kpi_field"], [{"review_id": "SEC_GAP_REVIEW_0001", "ticker": "AAA", "isin": "US0000000001", "kpi_field": "gross_margin"}])
        self.write_csv(self.approved_facts, list(self.fact("GrossProfit").keys()), [self.fact("GrossProfit", "2024"), self.fact("GrossProfit", "2025")])
        self.write_csv(
            self.concept_candidates,
            list(self.candidate("GrossProfit").keys()),
            [
                self.candidate("GrossProfit"),
                self.candidate("CostOfRevenue"),
                self.candidate("RevenueFromContractWithCustomerExcludingAssessedTax"),
            ],
        )

    def run_review(self):
        return run_personal_sec_concept_alias_review_table(
            diagnostics=self.diagnostics,
            diagnostics_summary=self.diagnostics_summary,
            period_review=self.period_review,
            gap_review_queue=self.gap_queue,
            approved_facts=self.approved_facts,
            concept_candidates=self.concept_candidates,
            output=self.output,
            summary_output=self.summary,
            report_output=self.report,
        )

    def test_reads_only_concept_alias_gap_rows_from_diagnostics(self) -> None:
        result = self.run_review()
        source_ids = {row["source_review_id"] for row in result.rows}
        self.assertEqual(source_ids, {"SEC_GAP_REVIEW_0001"})

    def test_emits_alias_candidates_when_related_concepts_are_available(self) -> None:
        rows = self.read_csv(self.run_review().table_path)
        self.assertTrue(rows)
        self.assertIn("GrossProfit", {row["candidate_sec_concept"] for row in rows})

    def test_classifies_direct_revenue_aliases_conservatively(self) -> None:
        status, risk, *_ = classify_alias_candidate("REVENUE", "RevenueFromContractWithCustomerExcludingAssessedTax", True)
        self.assertEqual(status, "APPROVE_CANDIDATE")
        self.assertEqual(risk, "LOW")
        status, risk, *_ = classify_alias_candidate("REVENUE", "SalesRevenueNet", True)
        self.assertEqual(status, "APPROVE_CANDIDATE")
        self.assertEqual(risk, "MEDIUM")

    def test_classifies_gross_profit_as_low_risk_for_gross_profit_role(self) -> None:
        status, risk, *_ = classify_alias_candidate("GROSS_PROFIT", "GrossProfit", True)
        self.assertEqual(status, "APPROVE_CANDIDATE")
        self.assertEqual(risk, "LOW")

    def test_classifies_operating_income_loss_as_low_risk_for_operating_income_role(self) -> None:
        status, risk, *_ = classify_alias_candidate("OPERATING_INCOME", "OperatingIncomeLoss", True)
        self.assertEqual(status, "APPROVE_CANDIDATE")
        self.assertEqual(risk, "LOW")

    def test_treats_broad_income_concepts_as_review_required_or_high_risk(self) -> None:
        status, risk, *_ = classify_alias_candidate("OPERATING_INCOME", "NetIncomeLoss", True)
        self.assertEqual(status, "REVIEW_REQUIRED")
        self.assertEqual(risk, "HIGH")

    def test_treats_share_count_aliases_conservatively(self) -> None:
        status, risk, *_ = classify_alias_candidate("SHARE_COUNT", "WeightedAverageNumberOfDilutedSharesOutstanding", True)
        self.assertEqual(status, "REVIEW_REQUIRED")
        self.assertEqual(risk, "MEDIUM")

    def test_emits_deterministic_alias_review_id_values(self) -> None:
        rows = self.read_csv(self.run_review().table_path)
        self.assertEqual(rows[0]["alias_review_id"], "SEC_ALIAS_REVIEW_0001")

    def test_preserves_source_review_id(self) -> None:
        rows = self.read_csv(self.run_review().table_path)
        self.assertEqual(rows[0]["source_review_id"], "SEC_GAP_REVIEW_0001")

    def test_writes_stable_csv_headers(self) -> None:
        result = self.run_review()
        rows = self.read_csv(result.table_path)
        summary = self.read_csv(result.summary_path)
        self.assertEqual(list(rows[0].keys()), ALIAS_REVIEW_FIELDS)
        self.assertEqual(list(summary[0].keys()), SUMMARY_FIELDS)

    def test_writes_summary_counts_correctly(self) -> None:
        summary = self.read_csv(self.run_review().summary_path)[0]
        self.assertEqual(summary["source_concept_alias_gap_rows"], "1")
        self.assertEqual(summary["total_alias_review_rows"], "2")
        self.assertEqual(summary["approve_candidate_rows"], "1")
        self.assertEqual(summary["reject_candidate_rows"], "1")
        self.assertEqual(summary["rows_potentially_ready_for_alias_approval"], "1")

    def test_confirms_no_aliases_are_applied(self) -> None:
        summary = self.read_csv(self.run_review().summary_path)[0]
        rows = self.read_csv(self.output)
        self.assertEqual(summary["no_aliases_applied_confirmed"], "True")
        self.assertEqual({row["apply_status"] for row in rows}, {"REVIEW_ONLY"})

    def test_confirms_no_kpi_values_are_applied(self) -> None:
        summary = self.read_csv(self.run_review().summary_path)[0]
        rows = self.read_csv(self.output)
        self.assertEqual(summary["no_values_applied_confirmed"], "True")
        self.assertEqual({row["candidate_value_not_applied"] for row in rows}, {"True"})

    def test_no_score_monthly_watchlist_dashboard_artifacts_created(self) -> None:
        self.run_review()
        names = {path.name for path in (self.tmp / "processed").iterdir()}
        self.assertNotIn("company_scores.csv", names)
        self.assertNotIn("monthly_buy_ranking.csv", names)
        self.assertNotIn("watchlist_ranked.csv", names)
        self.assertNotIn("dashboard_payload.json", names)

    def test_missing_required_input_fails_deterministically(self) -> None:
        self.diagnostics.unlink()
        with self.assertRaisesRegex(RuntimeError, "MISSING_CONCEPT_COVERAGE_DIAGNOSTICS"):
            self.run_review()


if __name__ == "__main__":
    unittest.main()
