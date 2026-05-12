from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_sec_derived_kpi_compose import SUMMARY_FIELDS, run_personal_sec_derived_kpi_compose


class PersonalSecDerivedKpiComposeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_derived_compose_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.approval = self.tmp / "approval.csv"
        self.unlock = self.tmp / "unlock.csv"
        self.candidates = self.tmp / "candidates.csv"
        self.gap = self.tmp / "gap.csv"
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

    def approval_row(self, kpi: str, role: str, concept: str, status: str = "APPROVED") -> dict[str, str]:
        return {
            "review_id": f"AAA__{kpi}__{role}__{concept}",
            "holding_name": "Alpha Inc",
            "ticker": "AAA",
            "isin": "US0000000001",
            "kpi_field": kpi,
            "formula_recipe": kpi.upper(),
            "formula_role": role,
            "candidate_sec_concept": concept,
            "candidate_unit": "USD",
            "candidate_years_available": "6",
            "candidate_latest_fiscal_year": "2025",
            "recommended_approval": "",
            "approval_status": status,
            "approval_reason": "approved for test",
            "reviewer_notes": "",
        }

    def unlock_row(self, kpi: str, roles: str) -> dict[str, str]:
        return {
            "holding_name": "Alpha Inc",
            "ticker": "AAA",
            "isin": "US0000000001",
            "kpi_field": kpi,
            "formula_recipe": kpi.upper(),
            "required_roles": roles,
            "approved_roles": roles,
            "review_required_roles": "",
            "rejected_roles": "",
            "fully_approved_after_human_decisions": "True",
            "remaining_decisions_to_unlock": "",
            "next_action": "READY_FOR_DERIVED_KPI_COMPOSE",
        }

    def candidate(self, kpi: str, concept: str, value: str, year: str = "2025", unit: str = "USD", filed: str = "2026-01-01") -> dict[str, str]:
        return {
            "holding_name": "Alpha Inc",
            "ticker": "AAA",
            "isin": "US0000000001",
            "kpi_field": kpi,
            "sec_taxonomy": "us-gaap",
            "sec_concept": concept,
            "sec_label_or_description": concept,
            "unit": unit,
            "fiscal_year": year,
            "fiscal_period": "FY",
            "form": "10-K",
            "filed_date": filed,
            "frame": "",
            "value": value,
            "value_present": "True",
            "value_is_numeric": "True",
            "candidate_role": "",
            "usable_for_metric": "False",
            "rejection_reason": "",
            "source_artifact": "unit_candidates.csv",
        }

    def write_base_inputs(self) -> None:
        self.write_csv(
            self.approval,
            [
                "review_id",
                "holding_name",
                "ticker",
                "isin",
                "kpi_field",
                "formula_recipe",
                "formula_role",
                "candidate_sec_concept",
                "candidate_unit",
                "candidate_years_available",
                "candidate_latest_fiscal_year",
                "recommended_approval",
                "approval_status",
                "approval_reason",
                "reviewer_notes",
            ],
            [
                self.approval_row("gross_margin", "gross_profit", "GrossProfit"),
                self.approval_row("gross_margin", "revenue", "RevenueFromContractWithCustomerExcludingAssessedTax"),
            ],
        )
        self.write_csv(
            self.unlock,
            [
                "holding_name",
                "ticker",
                "isin",
                "kpi_field",
                "formula_recipe",
                "required_roles",
                "approved_roles",
                "review_required_roles",
                "rejected_roles",
                "fully_approved_after_human_decisions",
                "remaining_decisions_to_unlock",
                "next_action",
            ],
            [self.unlock_row("gross_margin", "gross_profit;revenue")],
        )
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
                "value",
                "value_present",
                "value_is_numeric",
                "candidate_role",
                "usable_for_metric",
                "rejection_reason",
                "source_artifact",
            ],
            [
                self.candidate("gross_margin", "GrossProfit", "40"),
                self.candidate("gross_margin", "RevenueFromContractWithCustomerExcludingAssessedTax", "100"),
            ],
        )
        self.write_csv(
            self.gap,
            ["holding_name", "ticker", "isin", "kpi_field"],
            [{"holding_name": "Alpha Inc", "ticker": "AAA", "isin": "US0000000001", "kpi_field": "gross_margin"}],
        )

    def run_compose(self, sec_facts: Path | None = None):
        return run_personal_sec_derived_kpi_compose(
            approval_applied=self.approval,
            unlock_matrix=self.unlock,
            concept_candidates=self.candidates,
            sec_facts=sec_facts,
            gap_matrix=self.gap,
            output_dir=self.output_dir,
            report_dir=self.report_dir,
        )

    def test_missing_private_approval_file_fails_without_fake_outputs(self) -> None:
        self.approval.unlink()
        with self.assertRaisesRegex(RuntimeError, "MISSING_PRIVATE_APPROVAL_APPLIED"):
            self.run_compose()
        self.assertFalse((self.output_dir / "personal_sec_derived_kpi_proposals.csv").exists())

    def test_gross_margin_computes_only_with_approved_roles(self) -> None:
        result = self.run_compose()
        rows = self.read_csv(result.proposals_path)
        self.assertEqual(rows[0]["kpi_field"], "gross_margin")
        self.assertEqual(float(rows[0]["derived_value"]), 0.4)
        self.assertEqual(rows[0]["proposal_status"], "READY_FOR_EVIDENCE_COMPOSE")

    def test_operating_margin_computes_operating_income_over_revenue(self) -> None:
        self.write_csv(self.approval, list(self.read_csv(self.approval)[0].keys()), [
            self.approval_row("operating_margin", "operating_income", "OperatingIncomeLoss"),
            self.approval_row("operating_margin", "revenue", "RevenueFromContractWithCustomerExcludingAssessedTax"),
        ])
        self.write_csv(self.unlock, list(self.read_csv(self.unlock)[0].keys()), [self.unlock_row("operating_margin", "operating_income;revenue")])
        self.write_csv(self.candidates, list(self.read_csv(self.candidates)[0].keys()), [
            self.candidate("operating_margin", "OperatingIncomeLoss", "25"),
            self.candidate("operating_margin", "RevenueFromContractWithCustomerExcludingAssessedTax", "100"),
        ])
        result = self.run_compose()
        rows = self.read_csv(result.proposals_path)
        self.assertEqual(rows[0]["kpi_field"], "operating_margin")
        self.assertEqual(float(rows[0]["derived_value"]), 0.25)

    def test_revenue_cagr_requires_positive_endpoints_and_sufficient_history(self) -> None:
        self.write_csv(self.approval, list(self.read_csv(self.approval)[0].keys()), [self.approval_row("revenue_cagr_5y", "revenue_series", "RevenueFromContractWithCustomerExcludingAssessedTax")])
        self.write_csv(self.unlock, list(self.read_csv(self.unlock)[0].keys()), [self.unlock_row("revenue_cagr_5y", "revenue_series")])
        self.write_csv(self.candidates, list(self.read_csv(self.candidates)[0].keys()), [
            self.candidate("revenue_cagr_5y", "RevenueFromContractWithCustomerExcludingAssessedTax", "100", "2020"),
            self.candidate("revenue_cagr_5y", "RevenueFromContractWithCustomerExcludingAssessedTax", "161.051", "2025"),
        ])
        result = self.run_compose()
        rows = self.read_csv(result.proposals_path)
        self.assertAlmostEqual(float(rows[0]["derived_value"]), 0.1, places=4)

    def test_eps_cagr_rejects_non_positive_endpoint(self) -> None:
        self.write_csv(self.approval, list(self.read_csv(self.approval)[0].keys()), [self.approval_row("eps_cagr_5y", "eps_series", "EarningsPerShareDiluted")])
        self.write_csv(self.unlock, list(self.read_csv(self.unlock)[0].keys()), [self.unlock_row("eps_cagr_5y", "eps_series")])
        self.write_csv(self.candidates, list(self.read_csv(self.candidates)[0].keys()), [
            self.candidate("eps_cagr_5y", "EarningsPerShareDiluted", "-1", "2020", "USD/shares"),
            self.candidate("eps_cagr_5y", "EarningsPerShareDiluted", "2", "2025", "USD/shares"),
        ])
        result = self.run_compose()
        rows = self.read_csv(result.rejections_path)
        self.assertEqual(rows[0]["rejection_reason"], "EPS_CAGR_NON_POSITIVE_ENDPOINT")

    def test_share_count_cagr_does_not_mix_different_concepts(self) -> None:
        self.write_csv(self.approval, list(self.read_csv(self.approval)[0].keys()), [
            self.approval_row("share_count_cagr_5y", "share_count_series", "WeightedAverageNumberOfDilutedSharesOutstanding"),
            self.approval_row("share_count_cagr_5y", "share_count_series", "EntityCommonStockSharesOutstanding"),
        ])
        self.write_csv(self.unlock, list(self.read_csv(self.unlock)[0].keys()), [self.unlock_row("share_count_cagr_5y", "share_count_series")])
        self.write_csv(self.candidates, list(self.read_csv(self.candidates)[0].keys()), [
            self.candidate("share_count_cagr_5y", "WeightedAverageNumberOfDilutedSharesOutstanding", "100", "2020", "shares"),
            self.candidate("share_count_cagr_5y", "WeightedAverageNumberOfDilutedSharesOutstanding", "90", "2025", "shares"),
        ])
        result = self.run_compose()
        rows = self.read_csv(result.rejections_path)
        self.assertEqual(rows[0]["rejection_reason"], "MISSING_OR_AMBIGUOUS_APPROVED_ROLE")

    def test_non_approved_concepts_are_ignored(self) -> None:
        rows = self.read_csv(self.approval)
        rows.append(self.approval_row("gross_margin", "revenue", "Revenues", status="REVIEW_REQUIRED"))
        self.write_csv(self.approval, list(rows[0].keys()), rows)
        result = self.run_compose()
        inputs = self.read_csv(result.proposal_inputs_path)
        self.assertNotIn("Revenues", {row["sec_concept"] for row in inputs})

    def test_unit_conflict_creates_rejection(self) -> None:
        rows = self.read_csv(self.candidates)
        rows[1]["unit"] = "EUR"
        self.write_csv(self.candidates, list(rows[0].keys()), rows)
        result = self.run_compose()
        rows = self.read_csv(result.rejections_path)
        self.assertEqual(rows[0]["rejection_reason"], "UNIT_CONFLICT")

    def test_duplicate_annual_facts_dedupe_by_latest_filed_date(self) -> None:
        rows = self.read_csv(self.candidates)
        rows.append(self.candidate("gross_margin", "RevenueFromContractWithCustomerExcludingAssessedTax", "80", "2025", "USD", "2025-01-01"))
        rows.append(self.candidate("gross_margin", "RevenueFromContractWithCustomerExcludingAssessedTax", "100", "2025", "USD", "2026-01-01"))
        self.write_csv(self.candidates, list(rows[0].keys()), rows)
        result = self.run_compose()
        rows = self.read_csv(result.proposals_path)
        self.assertEqual(float(rows[0]["derived_value"]), 0.4)

    def test_companyfacts_comparatives_use_period_end_year_for_dedupe(self) -> None:
        rows = self.read_csv(self.candidates)
        rows[0]["fiscal_year"] = "2025"
        rows[0]["frame"] = "CY2024"
        rows[0]["period_end"] = "2024-12-31"
        rows[1]["fiscal_year"] = "2025"
        rows[1]["frame"] = "CY2024"
        rows[1]["period_end"] = "2024-12-31"
        self.write_csv(self.candidates, list(rows[0].keys()), rows)
        result = self.run_compose()
        proposals = self.read_csv(result.proposals_path)
        self.assertEqual(proposals[0]["periods_used"], "2024;2024")

    def test_summary_has_stable_columns_and_no_network(self) -> None:
        result = self.run_compose()
        rows = self.read_csv(result.summary_path)
        self.assertEqual(list(rows[0].keys()), SUMMARY_FIELDS)
        self.assertEqual(rows[0]["no_network_confirmed"], "True")

    def test_compose_with_sec_facts_computes_gross_margin_from_normalized_facts(self) -> None:
        facts = self.tmp / "normalized_facts.csv"
        self.write_csv(
            facts,
            ["holding_name", "ticker", "isin", "sec_concept", "unit", "fiscal_year", "fiscal_period", "form", "filed_date", "value"],
            [
                {"holding_name": "Alpha Inc", "ticker": "AAA", "isin": "US0000000001", "sec_concept": "GrossProfit", "unit": "USD", "fiscal_year": "2025", "fiscal_period": "FY", "form": "10-K", "filed_date": "2026-01-01", "value": "45"},
                {"holding_name": "Alpha Inc", "ticker": "AAA", "isin": "US0000000001", "sec_concept": "RevenueFromContractWithCustomerExcludingAssessedTax", "unit": "USD", "fiscal_year": "2025", "fiscal_period": "FY", "form": "10-K", "filed_date": "2026-01-01", "value": "100"},
            ],
        )
        result = self.run_compose(sec_facts=facts)
        rows = self.read_csv(result.proposals_path)
        summary = self.read_csv(result.summary_path)[0]
        self.assertEqual(float(rows[0]["derived_value"]), 0.45)
        self.assertEqual(summary["fact_source_mode"], "NORMALIZED_FACTS")
        self.assertEqual(summary["annual_10k_fact_count"], "2")

    def test_candidate_metadata_fallback_does_not_create_fake_values(self) -> None:
        rows = self.read_csv(self.candidates)
        for row in rows:
            row.pop("value", None)
            row["value_present"] = "False"
            row["value_is_numeric"] = "False"
        self.write_csv(self.candidates, [key for key in rows[0].keys()], rows)
        result = self.run_compose()
        self.assertEqual(self.read_csv(result.proposals_path), [])
        rejections = self.read_csv(result.rejections_path)
        self.assertEqual(rejections[0]["rejection_reason"], "INVALID_OR_MISSING_ANNUAL_FACTS")

    def test_missing_value_column_rejects_instead_of_creating_value(self) -> None:
        facts = self.tmp / "normalized_facts_without_value.csv"
        self.write_csv(
            facts,
            ["holding_name", "ticker", "isin", "sec_concept", "unit", "fiscal_year", "fiscal_period", "form", "filed_date"],
            [{"holding_name": "Alpha Inc", "ticker": "AAA", "isin": "US0000000001", "sec_concept": "GrossProfit", "unit": "USD", "fiscal_year": "2025", "fiscal_period": "FY", "form": "10-K", "filed_date": "2026-01-01"}],
        )
        result = self.run_compose(sec_facts=facts)
        self.assertEqual(self.read_csv(result.proposals_path), [])
        rejections = self.read_csv(result.rejections_path)
        self.assertEqual(rejections[0]["rejection_reason"], "INVALID_OR_MISSING_ANNUAL_FACTS")

    def test_fy_frame_without_form_is_not_ready_for_evidence_compose(self) -> None:
        facts = self.tmp / "frame_only_facts.csv"
        self.write_csv(
            facts,
            ["holding_name", "ticker", "isin", "sec_concept", "unit", "fiscal_year", "fiscal_period", "form", "filed_date", "frame", "value"],
            [
                {"holding_name": "Alpha Inc", "ticker": "AAA", "isin": "US0000000001", "sec_concept": "GrossProfit", "unit": "USD", "fiscal_year": "2025", "fiscal_period": "FY", "form": "", "filed_date": "2026-01-01", "frame": "CY2025", "value": "40"},
                {"holding_name": "Alpha Inc", "ticker": "AAA", "isin": "US0000000001", "sec_concept": "RevenueFromContractWithCustomerExcludingAssessedTax", "unit": "USD", "fiscal_year": "2025", "fiscal_period": "FY", "form": "", "filed_date": "2026-01-01", "frame": "CY2025", "value": "100"},
            ],
        )
        result = self.run_compose(sec_facts=facts)
        self.assertEqual(self.read_csv(result.proposals_path), [])
        rejections = self.read_csv(result.rejections_path)
        self.assertEqual(rejections[0]["invalid_periods"], "NO_ANNUAL_10K_FACTS;NO_ANNUAL_10K_FACTS")


if __name__ == "__main__":
    unittest.main()
