from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_sec_approved_concept_alias_map import MAP_FIELDS, SUMMARY_FIELDS, run_personal_sec_approved_concept_alias_map


class PersonalSecApprovedConceptAliasMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_approved_alias_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.private_approval = self.tmp / "private" / "approval_filled.csv"
        self.processed_approval = self.tmp / "processed_approval.csv"
        self.approval_input = self.tmp / "approval_input.csv"
        self.output = self.tmp / "processed" / "map.csv"
        self.summary = self.tmp / "processed" / "summary.csv"
        self.invalid = self.tmp / "processed" / "invalid.csv"
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

    def approval_row(self, **updates: str) -> dict[str, str]:
        row = {
            "approval_input_id": "SEC_ALIAS_APPROVAL_INPUT_0001",
            "source_alias_review_id": "SEC_ALIAS_REVIEW_0001",
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
            "machine_suggested_approval": "YES",
            "human_approval_status": "APPROVED",
            "approval_scope": "GLOBAL_CONCEPT_ROLE",
            "approval_rationale": "Direct semantic alias.",
            "reviewer_notes": "",
            "reviewer_name": "reviewer",
            "review_date": "2026-04-28",
            "semantic_match_reason": "direct",
            "semantic_risk_reason": "low",
            "recommended_action": "approve",
            "source_artifact": "fixture.csv",
            "candidate_value_not_applied": "True",
            "apply_status": "HUMAN_REVIEW_FILLED_NO_VALUE_APPLY",
            "notes": "",
        }
        row.update(updates)
        return row

    def write_base_inputs(self) -> None:
        rows = [
            self.approval_row(),
            self.approval_row(
                approval_input_id="SEC_ALIAS_APPROVAL_INPUT_0002",
                candidate_sec_concept="RevenueFromContractWithCustomerExcludingAssessedTax",
                required_concept_role="REVENUE",
                missing_required_concept="revenue",
                human_approval_status="REJECTED",
            ),
            self.approval_row(
                approval_input_id="SEC_ALIAS_APPROVAL_INPUT_0003",
                candidate_sec_concept="SalesRevenueNet",
                required_concept_role="REVENUE",
                missing_required_concept="revenue",
                human_approval_status="NEEDS_MORE_EVIDENCE",
            ),
        ]
        self.write_csv(self.private_approval, list(self.approval_row().keys()), rows)

    def run_map(self):
        return run_personal_sec_approved_concept_alias_map(
            private_approval=self.private_approval,
            processed_approval=self.processed_approval,
            approval_input=self.approval_input,
            output=self.output,
            summary_output=self.summary,
            invalid_output=self.invalid,
            report_output=self.report,
        )

    def test_only_human_approved_rows_enter_alias_map(self) -> None:
        rows = self.read_csv(self.run_map().map_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["approved_sec_concept"], "GrossProfit")

    def test_machine_suggestion_is_not_treated_as_approval(self) -> None:
        self.write_csv(self.private_approval, list(self.approval_row().keys()), [self.approval_row(human_approval_status="PENDING_REVIEW", machine_suggested_approval="YES")])
        rows = self.read_csv(self.run_map().map_path)
        self.assertEqual(rows, [])

    def test_active_for_period_selection_is_false(self) -> None:
        rows = self.read_csv(self.run_map().map_path)
        self.assertEqual({row["active_for_period_selection"] for row in rows}, {"False"})

    def test_invalid_high_risk_approval_is_reported(self) -> None:
        self.write_csv(self.private_approval, list(self.approval_row().keys()), [self.approval_row(alias_risk_level="HIGH", approval_scope="GLOBAL_CONCEPT_ROLE")])
        result = self.run_map()
        invalid = self.read_csv(result.invalid_path)
        self.assertEqual(result.summary["invalid_approved_rows"], "1")
        self.assertIn("HIGH_RISK_APPROVAL_REQUIRES_HOLDING_SCOPE_AND_RATIONALE", invalid[0]["invalid_reason"])

    def test_do_not_use_scope_is_invalid(self) -> None:
        self.write_csv(self.private_approval, list(self.approval_row().keys()), [self.approval_row(approval_scope="DO_NOT_USE")])
        invalid = self.read_csv(self.run_map().invalid_path)
        self.assertIn("APPROVAL_SCOPE_DO_NOT_USE", invalid[0]["invalid_reason"])

    def test_missing_rationale_is_invalid(self) -> None:
        self.write_csv(self.private_approval, list(self.approval_row().keys()), [self.approval_row(approval_rationale="")])
        invalid = self.read_csv(self.run_map().invalid_path)
        self.assertIn("MISSING_APPROVAL_RATIONALE", invalid[0]["invalid_reason"])

    def test_unknown_role_is_invalid(self) -> None:
        self.write_csv(self.private_approval, list(self.approval_row().keys()), [self.approval_row(required_concept_role="UNKNOWN")])
        invalid = self.read_csv(self.run_map().invalid_path)
        self.assertIn("UNKNOWN_REQUIRED_CONCEPT_ROLE", invalid[0]["invalid_reason"])

    def test_writes_stable_headers(self) -> None:
        result = self.run_map()
        rows = self.read_csv(result.map_path)
        summary = self.read_csv(result.summary_path)
        self.assertEqual(list(rows[0].keys()), MAP_FIELDS)
        self.assertEqual(list(summary[0].keys()), SUMMARY_FIELDS)

    def test_summary_counts_statuses(self) -> None:
        summary = self.read_csv(self.run_map().summary_path)[0]
        self.assertEqual(summary["approval_input_rows"], "3")
        self.assertEqual(summary["approved_alias_rows"], "1")
        self.assertEqual(summary["rejected_rows"], "1")
        self.assertEqual(summary["needs_more_evidence_rows"], "1")
        self.assertEqual(summary["active_for_period_selection_rows"], "0")

    def test_missing_input_fails_deterministically(self) -> None:
        self.private_approval.unlink()
        with self.assertRaisesRegex(RuntimeError, "MISSING_FILLED_ALIAS_APPROVAL_INPUT"):
            self.run_map()


if __name__ == "__main__":
    unittest.main()
