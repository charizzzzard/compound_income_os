from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_sec_derived_kpi_fact_source_audit import (
    SUMMARY_FIELDS,
    run_personal_sec_derived_kpi_fact_source_audit,
)


class PersonalSecDerivedKpiFactSourceAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_fact_source_audit_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.approval = self.tmp / "approval.csv"
        self.unlock = self.tmp / "unlock.csv"
        self.output_dir = self.tmp / "processed"
        self.report_dir = self.tmp / "reports"
        self.write_base_private_inputs()

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

    def write_base_private_inputs(self) -> None:
        self.write_csv(
            self.approval,
            [
                "holding_name",
                "ticker",
                "isin",
                "kpi_field",
                "formula_recipe",
                "formula_role",
                "candidate_sec_concept",
                "approval_status",
            ],
            [
                {
                    "holding_name": "Alpha Inc",
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "kpi_field": "gross_margin",
                    "formula_recipe": "GROSS_MARGIN",
                    "formula_role": "gross_profit",
                    "candidate_sec_concept": "GrossProfit",
                    "approval_status": "APPROVED",
                }
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
                "fully_approved_after_human_decisions",
            ],
            [
                {
                    "holding_name": "Alpha Inc",
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "kpi_field": "gross_margin",
                    "formula_recipe": "GROSS_MARGIN",
                    "fully_approved_after_human_decisions": "True",
                }
            ],
        )

    def run_audit(self, artifacts: list[Path]):
        return run_personal_sec_derived_kpi_fact_source_audit(
            approval_applied=self.approval,
            unlock_matrix=self.unlock,
            output_dir=self.output_dir,
            report_dir=self.report_dir,
            artifact_paths=artifacts,
        )

    def test_concept_candidates_without_value_column_are_not_compose_usable(self) -> None:
        candidates = self.tmp / "personal_sec_kpi_extraction_concept_candidates.csv"
        self.write_csv(
            candidates,
            ["holding_name", "ticker", "isin", "kpi_field", "sec_concept", "unit", "fiscal_year", "fiscal_period", "form", "filed_date"],
            [{"holding_name": "Alpha Inc", "ticker": "AAA", "isin": "US0000000001", "kpi_field": "gross_margin", "sec_concept": "GrossProfit", "unit": "USD", "fiscal_year": "2025", "fiscal_period": "FY", "form": "10-K", "filed_date": "2026-01-01"}],
        )
        result = self.run_audit([candidates])
        inventory = self.read_csv(result.inventory_path)
        self.assertEqual(inventory[0]["candidate_for_derived_kpi_compose"], "False")
        self.assertEqual(result.summary["approved_roles_with_numeric_values"], "0")

    def test_normalized_facts_with_value_fy_10k_are_usable(self) -> None:
        facts = self.tmp / "personal_sec_companyfacts_normalized.csv"
        self.write_csv(
            facts,
            ["holding_name", "ticker", "isin", "sec_concept", "unit", "fiscal_year", "fiscal_period", "form", "filed_date", "value"],
            [{"holding_name": "Alpha Inc", "ticker": "AAA", "isin": "US0000000001", "sec_concept": "GrossProfit", "unit": "USD", "fiscal_year": "2025", "fiscal_period": "FY", "form": "10-K", "filed_date": "2026-01-01", "value": "40"}],
        )
        result = self.run_audit([facts])
        self.assertEqual(result.summary["approved_roles_with_numeric_values"], "1")
        self.assertEqual(result.summary["approved_roles_with_annual_10k_facts"], "1")
        self.assertEqual(result.summary["approved_roles_usable_for_compose"], "1")

    def test_summary_contains_stable_columns(self) -> None:
        facts = self.tmp / "facts.csv"
        self.write_csv(facts, ["isin", "sec_concept"], [{"isin": "US0000000001", "sec_concept": "GrossProfit"}])
        result = self.run_audit([facts])
        rows = self.read_csv(result.summary_path)
        self.assertEqual(list(rows[0].keys()), SUMMARY_FIELDS)
        self.assertEqual(rows[0]["no_network_confirmed"], "True")

    def test_private_paths_are_not_written_to_public_report(self) -> None:
        private_file = self.tmp / "data" / "raw" / "private" / "fundamentals" / "secret_companyfacts.csv"
        self.write_csv(private_file, ["isin", "sec_concept", "value"], [{"isin": "US0000000001", "sec_concept": "GrossProfit", "value": "40"}])
        result = self.run_audit([private_file])
        report = result.report_path.read_text(encoding="utf-8")
        self.assertNotIn("secret_companyfacts.csv", report)
        self.assertNotIn("data/raw/private", report)


if __name__ == "__main__":
    unittest.main()
