from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_sec_concept_alias_approval_input import (
    APPROVAL_INPUT_FIELDS,
    SUMMARY_FIELDS,
    run_personal_sec_concept_alias_approval_input,
)


class PersonalSecConceptAliasApprovalInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_alias_approval_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.alias_review = self.tmp / "alias_review.csv"
        self.alias_summary = self.tmp / "alias_summary.csv"
        self.output = self.tmp / "processed" / "approval_input.csv"
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

    def alias_row(self, **updates: str) -> dict[str, str]:
        row = {
            "alias_review_id": "SEC_ALIAS_REVIEW_0001",
            "source_review_id": "SEC_GAP_REVIEW_0001",
            "ticker": "AAA",
            "isin": "US0000000001",
            "company_name": "Alpha Inc",
            "kpi_field": "gross_margin",
            "required_concept_role": "GROSS_PROFIT",
            "missing_required_concept": "gross_profit",
            "candidate_sec_concept": "GrossProfit",
            "candidate_label": "GrossProfit",
            "candidate_description": "Gross profit",
            "available_annual_periods": "",
            "first_available_fiscal_year": "",
            "last_available_fiscal_year": "",
            "available_period_count": "0",
            "alias_candidate_status": "APPROVE_CANDIDATE",
            "alias_risk_level": "LOW",
            "semantic_match_reason": "direct",
            "semantic_risk_reason": "low",
            "recommended_action": "approve after review",
            "source_artifact": "fixture.csv",
            "candidate_value_not_applied": "True",
            "apply_status": "REVIEW_ONLY",
            "notes": "",
        }
        row.update(updates)
        return row

    def write_base_inputs(self) -> None:
        rows = [
            self.alias_row(),
            self.alias_row(
                alias_review_id="SEC_ALIAS_REVIEW_0002",
                candidate_sec_concept="SalesRevenueNet",
                required_concept_role="REVENUE",
                missing_required_concept="revenue",
                alias_candidate_status="APPROVE_CANDIDATE",
                alias_risk_level="MEDIUM",
            ),
            self.alias_row(
                alias_review_id="SEC_ALIAS_REVIEW_0003",
                candidate_sec_concept="WeightedAverageNumberOfDilutedSharesOutstanding",
                required_concept_role="SHARE_COUNT",
                missing_required_concept="share_count_series",
                alias_candidate_status="REVIEW_REQUIRED",
                alias_risk_level="MEDIUM",
            ),
            self.alias_row(
                alias_review_id="SEC_ALIAS_REVIEW_0004",
                candidate_sec_concept="CostOfRevenue",
                alias_candidate_status="REJECT_CANDIDATE",
                alias_risk_level="HIGH",
            ),
        ]
        self.write_csv(self.alias_review, list(self.alias_row().keys()), rows)
        self.write_csv(
            self.alias_summary,
            ["no_aliases_applied_confirmed", "no_values_applied_confirmed", "no_score_change_confirmed", "no_network_confirmed", "raw_master_mutation_performed"],
            [
                {
                    "no_aliases_applied_confirmed": "True",
                    "no_values_applied_confirmed": "True",
                    "no_score_change_confirmed": "True",
                    "no_network_confirmed": "True",
                    "raw_master_mutation_performed": "False",
                }
            ],
        )

    def run_input(self):
        return run_personal_sec_concept_alias_approval_input(
            alias_review_table=self.alias_review,
            alias_review_summary=self.alias_summary,
            output=self.output,
            summary_output=self.summary,
            report_output=self.report,
        )

    def test_reads_approve_candidate_rows_from_alias_review_table(self) -> None:
        rows = self.read_csv(self.run_input().approval_input_path)
        self.assertIn("GrossProfit", {row["candidate_sec_concept"] for row in rows})

    def test_reads_review_required_rows_from_alias_review_table(self) -> None:
        rows = self.read_csv(self.run_input().approval_input_path)
        self.assertIn("WeightedAverageNumberOfDilutedSharesOutstanding", {row["candidate_sec_concept"] for row in rows})

    def test_excludes_reject_candidate_rows_from_approval_input_table(self) -> None:
        rows = self.read_csv(self.run_input().approval_input_path)
        self.assertNotIn("CostOfRevenue", {row["candidate_sec_concept"] for row in rows})

    def test_defaults_all_human_approval_status_values_to_pending_review(self) -> None:
        rows = self.read_csv(self.run_input().approval_input_path)
        self.assertEqual({row["human_approval_status"] for row in rows}, {"PENDING_REVIEW"})

    def test_sets_machine_suggested_approval_yes_for_approve_candidate(self) -> None:
        rows = self.read_csv(self.run_input().approval_input_path)
        gross = next(row for row in rows if row["candidate_sec_concept"] == "GrossProfit")
        self.assertEqual(gross["machine_suggested_approval"], "YES")

    def test_sets_machine_suggested_approval_no_for_review_required(self) -> None:
        rows = self.read_csv(self.run_input().approval_input_path)
        share = next(row for row in rows if row["alias_candidate_status"] == "REVIEW_REQUIRED")
        self.assertEqual(share["machine_suggested_approval"], "NO")

    def test_defaults_low_risk_approve_candidates_to_kpi_specific_scope(self) -> None:
        rows = self.read_csv(self.run_input().approval_input_path)
        gross = next(row for row in rows if row["candidate_sec_concept"] == "GrossProfit")
        self.assertEqual(gross["approval_scope"], "KPI_SPECIFIC")

    def test_defaults_medium_high_or_review_required_rows_to_do_not_use_scope(self) -> None:
        rows = self.read_csv(self.run_input().approval_input_path)
        non_default = [row for row in rows if row["candidate_sec_concept"] != "GrossProfit"]
        self.assertTrue(non_default)
        self.assertEqual({row["approval_scope"] for row in non_default}, {"DO_NOT_USE"})

    def test_emits_deterministic_approval_input_id_values(self) -> None:
        rows = self.read_csv(self.run_input().approval_input_path)
        self.assertEqual(rows[0]["approval_input_id"], "SEC_ALIAS_APPROVAL_INPUT_0001")
        self.assertEqual(rows[1]["approval_input_id"], "SEC_ALIAS_APPROVAL_INPUT_0002")

    def test_preserves_source_alias_review_id_and_source_review_id(self) -> None:
        rows = self.read_csv(self.run_input().approval_input_path)
        self.assertEqual(rows[0]["source_alias_review_id"], "SEC_ALIAS_REVIEW_0001")
        self.assertEqual(rows[0]["source_review_id"], "SEC_GAP_REVIEW_0001")

    def test_writes_stable_csv_headers(self) -> None:
        result = self.run_input()
        rows = self.read_csv(result.approval_input_path)
        summary = self.read_csv(result.summary_path)
        self.assertEqual(list(rows[0].keys()), APPROVAL_INPUT_FIELDS)
        self.assertEqual(list(summary[0].keys()), SUMMARY_FIELDS)

    def test_writes_summary_counts_correctly(self) -> None:
        summary = self.read_csv(self.run_input().summary_path)[0]
        self.assertEqual(summary["source_alias_review_rows"], "4")
        self.assertEqual(summary["total_approval_input_rows"], "3")
        self.assertEqual(summary["machine_suggested_approval_rows"], "2")
        self.assertEqual(summary["pending_review_rows"], "3")
        self.assertEqual(summary["kpi_specific_default_scope_rows"], "1")
        self.assertEqual(summary["do_not_use_default_scope_rows"], "2")
        self.assertEqual(summary["excluded_reject_candidate_rows"], "1")

    def test_confirms_no_aliases_are_applied(self) -> None:
        summary = self.read_csv(self.run_input().summary_path)[0]
        self.assertEqual(summary["no_aliases_applied_confirmed"], "True")

    def test_confirms_no_kpi_values_are_applied(self) -> None:
        rows = self.read_csv(self.run_input().approval_input_path)
        summary = self.read_csv(self.summary)[0]
        self.assertEqual({row["candidate_value_not_applied"] for row in rows}, {"True"})
        self.assertEqual(summary["no_values_applied_confirmed"], "True")

    def test_no_score_monthly_watchlist_dashboard_artifacts_created(self) -> None:
        self.run_input()
        names = {path.name for path in (self.tmp / "processed").iterdir()}
        self.assertNotIn("company_scores.csv", names)
        self.assertNotIn("monthly_buy_ranking.csv", names)
        self.assertNotIn("watchlist_ranked.csv", names)
        self.assertNotIn("dashboard_payload.json", names)

    def test_missing_required_input_fails_deterministically(self) -> None:
        self.alias_review.unlink()
        with self.assertRaisesRegex(RuntimeError, "MISSING_SEC_CONCEPT_ALIAS_REVIEW_TABLE"):
            self.run_input()


if __name__ == "__main__":
    unittest.main()
