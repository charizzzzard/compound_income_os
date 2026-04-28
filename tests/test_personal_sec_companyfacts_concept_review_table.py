from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_sec_companyfacts_concept_review_table import (
    SUMMARY_FIELDS,
    run_personal_sec_companyfacts_concept_review_table,
)


class PersonalSecCompanyfactsConceptReviewTableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_concept_review_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.gap = self.tmp / "gap.csv"
        self.candidates = self.tmp / "candidates.csv"
        self.output_dir = self.tmp / "processed"
        self.private_dir = self.tmp / "data" / "raw" / "private" / "fundamentals"
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

    def write_gap(self, kpi: str) -> None:
        self.write_csv(
            self.gap,
            [
                "holding_name",
                "ticker",
                "isin",
                "kpi_field",
                "companyfacts_fetch_status",
                "candidate_fact_count",
                "extraction_gap_type",
            ],
            [
                {
                    "holding_name": "Alpha Inc",
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "kpi_field": kpi,
                    "companyfacts_fetch_status": "FETCHED",
                    "candidate_fact_count": "1",
                    "extraction_gap_type": "DERIVED_METRIC_LOGIC_MISSING",
                }
            ],
        )

    def candidate(self, kpi: str, concept: str, unit: str = "USD") -> dict[str, str]:
        return {
            "holding_name": "Alpha Inc",
            "ticker": "AAA",
            "isin": "US0000000001",
            "kpi_field": kpi,
            "sec_taxonomy": "us-gaap",
            "sec_concept": concept,
            "sec_label_or_description": concept,
            "unit": unit,
            "fiscal_year": "2025",
            "fiscal_period": "FY",
            "form": "10-K",
            "filed_date": "2026-04-27",
            "frame": "",
            "value_present": "True",
            "value_is_numeric": "True",
            "candidate_role": "",
            "usable_for_metric": "False",
            "rejection_reason": "",
            "source_artifact": "data/processed/personal_sec_kpi_extraction_concept_candidates.csv",
        }

    def write_candidates(self, rows: list[dict[str, str]]) -> None:
        self.write_csv(
            self.candidates,
            [
                "holding_name",
                "ticker",
                "isin",
                "kpi_field",
                "sec_taxonomy",
                "sec_concept",
                "sec_label_or_description",
                "unit",
                "fiscal_year",
                "fiscal_period",
                "form",
                "filed_date",
                "frame",
                "value_present",
                "value_is_numeric",
                "candidate_role",
                "usable_for_metric",
                "rejection_reason",
                "source_artifact",
            ],
            rows,
        )

    def write_base_inputs(self) -> None:
        self.write_gap("revenue_cagr_5y")
        self.write_candidates([self.candidate("revenue_cagr_5y", "Revenues")])

    def run_review(self, **overrides):
        kwargs = {
            "gap_matrix": str(self.gap),
            "concept_candidates": str(self.candidates),
            "output_dir": str(self.output_dir),
            "private_template_dir": str(self.private_dir),
            "report_dir": str(self.report_dir),
        }
        kwargs.update(overrides)
        return run_personal_sec_companyfacts_concept_review_table(**kwargs)

    def test_missing_input_files_fail_with_missing_gap_review_inputs(self) -> None:
        missing = self.tmp / "missing.csv"

        with self.assertRaises(FileNotFoundError) as context:
            self.run_review(gap_matrix=str(missing))

        self.assertIn("MISSING_GAP_REVIEW_INPUTS", str(context.exception))
        self.assertFalse((self.output_dir / "personal_sec_companyfacts_concept_review_table.csv").exists())

    def test_revenue_candidates_map_to_revenue_series(self) -> None:
        result = self.run_review()

        self.assertEqual(result.review_rows[0]["formula_role"], "revenue_series")
        self.assertEqual(result.review_rows[0]["formula_recipe"], "REVENUE_CAGR_5Y")

    def test_gross_margin_creates_gross_profit_and_revenue_roles(self) -> None:
        self.write_gap("gross_margin")
        self.write_candidates(
            [
                self.candidate("gross_margin", "GrossProfit"),
                self.candidate("gross_margin", "RevenueFromContractWithCustomerExcludingAssessedTax"),
            ]
        )
        result = self.run_review()
        roles = {row["formula_role"] for row in result.review_rows}

        self.assertIn("gross_profit", roles)
        self.assertIn("revenue", roles)

    def test_operating_margin_creates_operating_income_and_revenue_roles(self) -> None:
        self.write_gap("operating_margin")
        self.write_candidates(
            [
                self.candidate("operating_margin", "OperatingIncomeLoss"),
                self.candidate("operating_margin", "Revenues"),
            ]
        )
        result = self.run_review()
        roles = {row["formula_role"] for row in result.review_rows}

        self.assertIn("operating_income", roles)
        self.assertIn("revenue", roles)

    def test_eps_cagr_prefers_diluted_but_remains_reviewable(self) -> None:
        self.write_gap("eps_cagr_5y")
        self.write_candidates(
            [
                self.candidate("eps_cagr_5y", "EarningsPerShareBasic", "USD/shares"),
                self.candidate("eps_cagr_5y", "EarningsPerShareDiluted", "USD/shares"),
            ]
        )
        result = self.run_review()
        by_concept = {row["candidate_sec_concept"]: row for row in result.review_rows}

        self.assertEqual(by_concept["EarningsPerShareDiluted"]["concept_confidence"], "HIGH")
        self.assertEqual(by_concept["EarningsPerShareBasic"]["recommended_approval"], "REVIEW_REQUIRED")
        self.assertEqual(by_concept["EarningsPerShareDiluted"]["approval_status"], "PENDING_REVIEW")

    def test_share_count_does_not_auto_mix_period_end_and_weighted_average(self) -> None:
        self.write_gap("share_count_cagr_5y")
        self.write_candidates(
            [
                self.candidate("share_count_cagr_5y", "EntityCommonStockSharesOutstanding", "shares"),
                self.candidate("share_count_cagr_5y", "WeightedAverageNumberOfDilutedSharesOutstanding", "shares"),
            ]
        )
        result = self.run_review()

        self.assertTrue(all(row["role_status"] == "AMBIGUOUS" for row in result.review_rows))
        self.assertTrue(all(row["auto_apply_after_approval"] == "False" for row in result.review_rows))

    def test_private_approval_template_is_created_but_not_mirrored_in_report(self) -> None:
        result = self.run_review()
        text = result.report_output.read_text(encoding="utf-8")

        self.assertTrue(result.private_approval_template_output.exists())
        self.assertIn("<private_path>", text)
        self.assertNotIn("personal_sec_companyfacts_concept_approval_template.csv", text)

    def test_summary_has_stable_columns_and_guardrails(self) -> None:
        result = self.run_review()
        summary = self.read_csv(result.review_summary_output)[0]

        self.assertEqual(list(summary.keys()), SUMMARY_FIELDS)
        self.assertEqual(summary["no_network_confirmed"], "True")
        self.assertEqual(summary["no_value_apply_confirmed"], "True")
        self.assertEqual(summary["no_score_change_confirmed"], "True")
        self.assertEqual(summary["no_imputation_confirmed"], "True")


if __name__ == "__main__":
    unittest.main()
