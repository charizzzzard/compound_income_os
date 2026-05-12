from __future__ import annotations

import csv
import json
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_sec_companyfacts_approved_fact_export import run_personal_sec_companyfacts_approved_fact_export
from src.personal_sec_derived_kpi_compose import run_personal_sec_derived_kpi_compose
from src.personal_sec_derived_kpi_fact_source_audit import run_personal_sec_derived_kpi_fact_source_audit


class PersonalSecCompanyfactsApprovedFactExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_approved_fact_export_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.approval = self.tmp / "approval.csv"
        self.identity = self.tmp / "identity.csv"
        self.snapshot_root = self.tmp / "private_snapshots"
        self.output_dir = self.tmp / "processed"
        self.report_dir = self.tmp / "reports"
        self.unlock = self.tmp / "unlock.csv"
        self.gap = self.tmp / "gap.csv"
        self.candidates = self.tmp / "candidates.csv"
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
            "holding_name": "Alpha Inc",
            "ticker": "AAA",
            "isin": "US0000000001",
            "kpi_field": kpi,
            "formula_recipe": kpi.upper(),
            "formula_role": role,
            "candidate_sec_concept": concept,
            "approval_status": status,
        }

    def write_base_inputs(self) -> None:
        self.write_csv(
            self.approval,
            ["holding_name", "ticker", "isin", "kpi_field", "formula_recipe", "formula_role", "candidate_sec_concept", "approval_status"],
            [
                self.approval_row("gross_margin", "gross_profit", "GrossProfit"),
                self.approval_row("gross_margin", "revenue", "RevenueFromContractWithCustomerExcludingAssessedTax"),
                self.approval_row("gross_margin", "revenue", "Revenues", "REVIEW_REQUIRED"),
                self.approval_row("gross_margin", "revenue", "SalesRevenueNet", "REJECTED"),
            ],
        )
        self.write_csv(
            self.identity,
            ["ticker", "isin", "company_name", "cik", "sec_entity_name", "asset_type", "country", "enabled", "notes"],
            [{"ticker": "AAA", "isin": "US0000000001", "company_name": "Alpha Inc", "cik": "1234", "sec_entity_name": "Alpha Inc", "asset_type": "STOCK", "country": "US", "enabled": "True", "notes": ""}],
        )
        self.write_csv(
            self.unlock,
            ["holding_name", "ticker", "isin", "kpi_field", "formula_recipe", "fully_approved_after_human_decisions"],
            [{"holding_name": "Alpha Inc", "ticker": "AAA", "isin": "US0000000001", "kpi_field": "gross_margin", "formula_recipe": "GROSS_MARGIN", "fully_approved_after_human_decisions": "True"}],
        )
        self.write_csv(self.gap, ["holding_name", "ticker", "isin", "kpi_field"], [{"holding_name": "Alpha Inc", "ticker": "AAA", "isin": "US0000000001", "kpi_field": "gross_margin"}])
        self.write_csv(self.candidates, ["holding_name", "ticker", "isin", "kpi_field"], [{"holding_name": "Alpha Inc", "ticker": "AAA", "isin": "US0000000001", "kpi_field": "gross_margin"}])

    def write_companyfacts(self) -> Path:
        path = self.snapshot_root / "CIK0000001234.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cik": "1234",
            "entityName": "Alpha Inc",
            "facts": {
                "us-gaap": {
                    "GrossProfit": {
                        "label": "Gross Profit",
                        "description": "Gross profit",
                        "units": {"USD": [{"val": 40, "fy": 2025, "fp": "FY", "form": "10-K", "filed": "2026-01-01", "frame": "CY2025", "start": "2025-01-01", "end": "2025-12-31", "accn": "abc"}]},
                    },
                    "RevenueFromContractWithCustomerExcludingAssessedTax": {
                        "label": "Revenue",
                        "description": "Revenue",
                        "units": {"USD": [{"val": 100, "fy": 2025, "fp": "FY", "form": "10-K", "filed": "2026-01-01", "frame": "CY2025", "start": "2025-01-01", "end": "2025-12-31", "accn": "abc"}]},
                    },
                    "Revenues": {
                        "label": "Revenues",
                        "description": "Rejected by approval status",
                        "units": {"USD": [{"val": 101, "fy": 2025, "fp": "FY", "form": "10-K", "filed": "2026-01-01"}]},
                    },
                }
            },
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def run_export(self):
        return run_personal_sec_companyfacts_approved_fact_export(
            approval_applied=self.approval,
            snapshot_root=self.snapshot_root,
            output_dir=self.output_dir,
            report_dir=self.report_dir,
            identity_map=self.identity,
        )

    def test_missing_local_sec_snapshot_reports_missing_without_fake_values(self) -> None:
        result = self.run_export()
        self.assertEqual(result.status, "MISSING_LOCAL_SEC_COMPANYFACTS_SNAPSHOT")
        self.assertEqual(self.read_csv(result.approved_facts_path), [])
        self.assertEqual(result.summary["facts_exported_total"], "0")

    def test_companyfacts_json_exports_approved_revenues_usd_facts(self) -> None:
        self.write_companyfacts()
        result = self.run_export()
        rows = self.read_csv(result.approved_facts_path)
        concepts = {row["sec_concept"] for row in rows}
        self.assertIn("GrossProfit", concepts)
        self.assertIn("RevenueFromContractWithCustomerExcludingAssessedTax", concepts)
        self.assertNotIn("Revenues", concepts)
        self.assertTrue(all(row["value_source"] == "SEC CompanyFacts local snapshot" for row in rows))

    def test_numeric_value_and_annual_basis_are_classified(self) -> None:
        self.write_companyfacts()
        result = self.run_export()
        rows = self.read_csv(result.approved_facts_path)
        self.assertTrue(all(row["value_is_numeric"] == "True" for row in rows))
        self.assertTrue(all(row["annual_basis"] == "FY_10K" for row in rows))
        self.assertEqual(result.summary["numeric_facts_exported"], "2")
        self.assertEqual(result.summary["annual_10k_facts_exported"], "2")

    def test_private_raw_paths_are_masked_in_public_report(self) -> None:
        self.write_companyfacts()
        result = self.run_export()
        report = result.report_path.read_text(encoding="utf-8")
        self.assertNotIn("CIK0000001234.json", report)
        self.assertNotIn(str(self.snapshot_root), report)
        self.assertIn("<private_sec_companyfacts_snapshot>", report)

    def test_fact_source_audit_recognizes_approved_facts_as_usable(self) -> None:
        self.write_companyfacts()
        result = self.run_export()
        audit = run_personal_sec_derived_kpi_fact_source_audit(
            approval_applied=self.approval,
            unlock_matrix=self.unlock,
            output_dir=self.output_dir,
            report_dir=self.report_dir,
            artifact_paths=[result.approved_facts_path],
        )
        self.assertEqual(audit.summary["approved_roles_with_numeric_values"], "2")
        self.assertEqual(audit.summary["approved_roles_usable_for_compose"], "2")

    def test_compose_can_calculate_from_approved_facts_csv(self) -> None:
        self.write_companyfacts()
        result = self.run_export()
        compose = run_personal_sec_derived_kpi_compose(
            approval_applied=self.approval,
            unlock_matrix=self.unlock,
            concept_candidates=self.candidates,
            sec_facts=result.approved_facts_path,
            gap_matrix=self.gap,
            output_dir=self.output_dir,
            report_dir=self.report_dir,
        )
        proposals = self.read_csv(compose.proposals_path)
        self.assertEqual(float(proposals[0]["derived_value"]), 0.4)
        self.assertEqual(compose.summary["proposals_ready_for_evidence_compose"], "1")


if __name__ == "__main__":
    unittest.main()
