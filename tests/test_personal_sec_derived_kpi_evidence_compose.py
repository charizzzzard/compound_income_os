from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_sec_derived_kpi_evidence_compose import (
    REGISTRY_APPEND_FIELDS,
    SUMMARY_FIELDS,
    run_personal_sec_derived_kpi_evidence_compose,
)


class PersonalSecDerivedKpiEvidenceComposeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_derived_evidence_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.proposals = self.tmp / "proposals.csv"
        self.inputs = self.tmp / "proposal_inputs.csv"
        self.output_dir = self.tmp / "processed"
        self.report_dir = self.tmp / "reports"
        self.write_proposals([self.ready_row()])
        self.write_csv(self.inputs, ["holding_name", "ticker", "isin", "kpi_field"], [{"holding_name": "Alpha Inc", "ticker": "AAA", "isin": "US0000000001", "kpi_field": "operating_margin"}])

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

    def ready_row(self, **updates: str) -> dict[str, str]:
        row = {
            "holding_name": "Alpha Inc",
            "ticker": "AAA",
            "isin": "US0000000001",
            "kpi_field": "operating_margin",
            "formula_recipe": "OPERATING_MARGIN",
            "derived_value": "0.3210977721",
            "derived_value_unit": "ratio",
            "derived_value_format": "decimal_ratio",
            "fiscal_year_start": "2024",
            "fiscal_year_end": "2024",
            "periods_used": "2024;2024",
            "source_sec_concepts": "OperatingIncomeLoss;RevenueFromContractWithCustomerExcludingAssessedTax",
            "source_units": "USD",
            "source_forms": "10-K",
            "source_filed_dates": "2025-02-05;2026-02-05",
            "calculation_method": "operating_income / revenue",
            "calculation_inputs_summary": "operating_income=112390000000.0; revenue=350018000000.0",
            "approval_source_status": "APPROVED_COMPANYFACTS_CONCEPTS_ONLY",
            "evidence_status": "PROPOSAL_ONLY_NOT_APPLIED",
            "proposal_status": "READY_FOR_EVIDENCE_COMPOSE",
            "rejection_reason": "",
            "review_required": "False",
            "no_imputation_confirmed": "True",
            "source_artifact": "data/processed/personal_sec_companyfacts_approved_facts.csv",
        }
        row.update(updates)
        return row

    def write_proposals(self, rows: list[dict[str, str]]) -> None:
        self.write_csv(self.proposals, list(self.ready_row().keys()), rows)

    def run_compose(self):
        return run_personal_sec_derived_kpi_evidence_compose(
            proposals=self.proposals,
            proposal_inputs=self.inputs,
            output_dir=self.output_dir,
            report_dir=self.report_dir,
        )

    def test_no_ready_proposals_fails_without_fake_evidence(self) -> None:
        self.write_proposals([self.ready_row(proposal_status="REJECTED", review_required="True")])
        with self.assertRaisesRegex(RuntimeError, "NO_READY_SEC_DERIVED_KPI_PROPOSALS"):
            self.run_compose()
        self.assertFalse((self.output_dir / "personal_sec_derived_kpi_evidence_proposals.csv").exists())

    def test_only_ready_for_evidence_compose_is_transferred(self) -> None:
        self.write_proposals(
            [
                self.ready_row(),
                self.ready_row(isin="US0000000002", proposal_status="REJECTED", review_required="True"),
                self.ready_row(isin="US0000000003", evidence_status="ALREADY_APPLIED"),
            ]
        )
        result = self.run_compose()
        proposals = self.read_csv(result.evidence_proposals_path)
        skipped = self.read_csv(result.skipped_path)
        self.assertEqual(len(proposals), 1)
        self.assertEqual(len(skipped), 2)
        self.assertEqual(proposals[0]["apply_status"], "NOT_APPLIED")

    def test_evidence_proposal_copies_derived_value_exactly_without_recalculation(self) -> None:
        result = self.run_compose()
        proposals = self.read_csv(result.evidence_proposals_path)
        self.assertEqual(proposals[0]["proposed_value"], "0.3210977721")
        self.assertEqual(proposals[0]["calculation_inputs_summary"], "operating_income=112390000000.0; revenue=350018000000.0")

    def test_sec_lineage_columns_are_filled(self) -> None:
        result = self.run_compose()
        proposals = self.read_csv(result.evidence_proposals_path)
        self.assertEqual(proposals[0]["source_sec_concepts"], "OperatingIncomeLoss;RevenueFromContractWithCustomerExcludingAssessedTax")
        self.assertEqual(proposals[0]["source_units"], "USD")
        self.assertEqual(proposals[0]["source_forms"], "10-K")
        self.assertEqual(proposals[0]["evidence_source_type"], "SEC_COMPANYFACTS_DERIVED_KPI")

    def test_registry_append_created_without_mutating_existing_registry(self) -> None:
        existing_registry = self.tmp / "existing_registry.csv"
        existing_registry.write_text("sentinel\n", encoding="utf-8")
        result = self.run_compose()
        registry = self.read_csv(result.registry_append_path)
        self.assertEqual(existing_registry.read_text(encoding="utf-8"), "sentinel\n")
        self.assertEqual(list(registry[0].keys()), REGISTRY_APPEND_FIELDS)
        self.assertEqual(registry[0]["reported_value"], "0.3210977721")
        self.assertEqual(registry[0]["apply_status"], "NOT_APPLIED")

    def test_confidence_high_for_10k_sources_with_no_imputation(self) -> None:
        result = self.run_compose()
        proposals = self.read_csv(result.evidence_proposals_path)
        self.assertEqual(proposals[0]["confidence"], "HIGH")
        self.assertEqual(proposals[0]["review_status"], "READY_FOR_REVIEWED_EVIDENCE_APPLY")

    def test_private_paths_are_masked_in_outputs_and_report(self) -> None:
        self.write_proposals([self.ready_row(source_artifact="data/raw/private/fundamentals/sec_user_agent.local.txt")])
        result = self.run_compose()
        proposals = self.read_csv(result.evidence_proposals_path)
        report = result.report_path.read_text(encoding="utf-8")
        self.assertEqual(proposals[0]["evidence_source_artifact"], "<private_artifact>")
        self.assertNotIn("data/raw/private", report)
        self.assertNotIn("sec_user_agent", report)

    def test_summary_has_stable_columns_and_guardrails(self) -> None:
        result = self.run_compose()
        summary = self.read_csv(result.summary_path)
        self.assertEqual(list(summary[0].keys()), SUMMARY_FIELDS)
        self.assertEqual(summary[0]["ready_proposals_input"], "1")
        self.assertEqual(summary[0]["evidence_proposals_created"], "1")
        self.assertEqual(summary[0]["no_network_confirmed"], "True")
        self.assertEqual(summary[0]["no_score_change_confirmed"], "True")
        self.assertEqual(summary[0]["no_master_mutation_confirmed"], "True")

    def test_invalid_ready_row_is_rejected_not_applied(self) -> None:
        self.write_proposals([self.ready_row(derived_value="not-a-number")])
        result = self.run_compose()
        self.assertEqual(self.read_csv(result.evidence_proposals_path), [])
        skipped = self.read_csv(result.skipped_path)
        self.assertEqual(skipped[0]["skip_reason"], "NON_NUMERIC_DERIVED_VALUE")
        summary = self.read_csv(result.summary_path)[0]
        self.assertEqual(summary["proposals_rejected"], "1")


if __name__ == "__main__":
    unittest.main()
