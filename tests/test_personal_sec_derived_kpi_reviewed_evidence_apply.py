from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.fundamentals_master import PERSONAL_MASTER_FIELDS
from src.personal_sec_derived_kpi_evidence_compose import REGISTRY_APPEND_FIELDS
from src.personal_sec_derived_kpi_reviewed_evidence_apply import (
    SUMMARY_FIELDS,
    run_personal_sec_derived_kpi_reviewed_evidence_apply,
)


class PersonalSecDerivedKpiReviewedEvidenceApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_reviewed_apply_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.proposals = self.tmp / "evidence_proposals.csv"
        self.registry_append = self.tmp / "registry_append.csv"
        self.master = self.tmp / "personal_fundamentals_master.csv"
        self.output_dir = self.tmp / "processed"
        self.report_dir = self.tmp / "reports"
        self.applied_master = self.output_dir / "applied_master.csv"
        self.write_master()
        self.write_proposals([self.proposal_row()])
        self.write_csv(self.registry_append, REGISTRY_APPEND_FIELDS, [])

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

    def master_row(self, isin: str = "US0000000001", ticker: str = "AAA", operating_margin: str = "") -> dict[str, str]:
        row = {field: "" for field in PERSONAL_MASTER_FIELDS}
        row.update(
            {
                "ticker": ticker,
                "isin": isin,
                "company_name": "Alpha Inc",
                "currency": "USD",
                "sector": "Technology",
                "country": "USA",
                "asset_type": "STOCK",
                "company_type_profile": "STANDARD",
                "source_name": "unit_test_master",
                "source_as_of_date": "2026-04-28",
                "fiscal_period": "FY",
                "fiscal_year": "2025",
                "report_date": "2026-04-28",
                "filing_date": "2026-04-28",
                "market_price_date": "2026-04-28",
                "calculation_version": "test",
                "data_quality_flag": "REVIEW",
                "notes": "unit fixture",
                "sleeve": "SINGLE_STOCK",
                "current_price_eur": "100",
                "mandate_fit_score": "80",
                "operating_margin": operating_margin,
            }
        )
        return row

    def write_master(self, rows: list[dict[str, str]] | None = None) -> None:
        self.write_csv(self.master, PERSONAL_MASTER_FIELDS, rows or [self.master_row()])

    def proposal_row(self, **updates: str) -> dict[str, str]:
        row = {
            "evidence_id": "SEC_DERIVED__US0000000001__operating_margin__FY2025",
            "holding_name": "Alpha Inc",
            "ticker": "AAA",
            "isin": "US0000000001",
            "kpi_field": "operating_margin",
            "proposed_value": "0.25",
            "proposed_value_unit": "ratio",
            "proposed_value_format": "decimal_ratio",
            "evidence_source_type": "SEC_COMPANYFACTS_DERIVED_KPI",
            "evidence_source_name": "SEC CompanyFacts",
            "evidence_source_artifact": "data/processed/personal_sec_companyfacts_approved_facts.csv",
            "source_sec_concepts": "OperatingIncomeLoss;RevenueFromContractWithCustomerExcludingAssessedTax",
            "source_units": "USD",
            "source_forms": "10-K",
            "source_filed_dates": "2026-02-01",
            "fiscal_year_start": "2025",
            "fiscal_year_end": "2025",
            "periods_used": "2025;2025",
            "calculation_method": "operating_income / revenue",
            "calculation_inputs_summary": "operating_income=25; revenue=100",
            "confidence": "HIGH",
            "evidence_status": "COMPOSED_PROPOSAL_ONLY",
            "apply_status": "NOT_APPLIED",
            "review_status": "READY_FOR_REVIEWED_EVIDENCE_APPLY",
            "no_imputation_confirmed": "True",
            "no_master_mutation_confirmed": "True",
            "notes": "",
        }
        row.update(updates)
        return row

    def write_proposals(self, rows: list[dict[str, str]]) -> None:
        self.write_csv(self.proposals, list(self.proposal_row().keys()), rows)

    def run_apply(self):
        return run_personal_sec_derived_kpi_reviewed_evidence_apply(
            evidence_proposals=self.proposals,
            registry_append=self.registry_append,
            fundamentals_master=self.master,
            output_dir=self.output_dir,
            report_dir=self.report_dir,
            evidence_applied_master=self.applied_master,
        )

    def test_no_eligible_proposals_fails_without_fake_values(self) -> None:
        self.write_proposals([self.proposal_row(confidence="LOW")])
        with self.assertRaisesRegex(RuntimeError, "NO_APPROVED_SEC_DERIVED_KPI_EVIDENCE_PROPOSALS"):
            self.run_apply()
        self.assertFalse((self.output_dir / "personal_sec_derived_kpi_reviewed_evidence_apply.csv").exists())

    def test_only_high_ready_not_applied_proposal_is_applied(self) -> None:
        self.write_proposals(
            [
                self.proposal_row(),
                self.proposal_row(evidence_id="low", confidence="LOW"),
                self.proposal_row(evidence_id="applied", apply_status="APPLIED"),
            ]
        )
        result = self.run_apply()
        apply_rows = self.read_csv(result.apply_path)
        skipped = self.read_csv(result.skipped_path)
        self.assertEqual(len(apply_rows), 1)
        self.assertEqual(len(skipped), 2)
        self.assertEqual(apply_rows[0]["apply_status"], "APPLIED_TO_EVIDENCE_MASTER_COPY")

    def test_review_required_low_or_already_applied_are_skipped(self) -> None:
        self.write_proposals(
            [
                self.proposal_row(),
                self.proposal_row(evidence_id="review", review_status="REVIEW_REQUIRED"),
                self.proposal_row(evidence_id="low", confidence="LOW"),
                self.proposal_row(evidence_id="done", apply_status="APPLIED"),
            ]
        )
        result = self.run_apply()
        self.assertEqual(len(self.read_csv(result.apply_path)), 1)
        self.assertEqual(len(self.read_csv(result.skipped_path)), 3)

    def test_strict_isin_match_is_used(self) -> None:
        self.write_master([self.master_row(isin="US0000000002", ticker="AAA")])
        result = self.run_apply()
        self.assertEqual(self.read_csv(result.apply_path), [])
        self.assertEqual(self.read_csv(result.skipped_path)[0]["skip_reason"], "IDENTITY_MATCH_FAILED")

    def test_existing_target_value_is_not_overwritten(self) -> None:
        self.write_master([self.master_row(operating_margin="0.99")])
        result = self.run_apply()
        self.assertEqual(self.read_csv(result.apply_path), [])
        skipped = self.read_csv(result.skipped_path)
        self.assertEqual(skipped[0]["skip_reason"], "TARGET_ALREADY_HAS_VALUE")
        applied_master = self.read_csv(result.evidence_applied_master_path)
        self.assertEqual(applied_master[0]["operating_margin"], "0.99")

    def test_evidence_applied_master_written_and_raw_master_unchanged(self) -> None:
        before = self.master.read_text(encoding="utf-8")
        result = self.run_apply()
        after = self.master.read_text(encoding="utf-8")
        self.assertEqual(before, after)
        applied_master = self.read_csv(result.evidence_applied_master_path)
        self.assertEqual(applied_master[0]["operating_margin"], "0.25")

    def test_summary_confirms_no_score_change(self) -> None:
        result = self.run_apply()
        summary = self.read_csv(result.summary_path)[0]
        self.assertEqual(list(summary.keys()), SUMMARY_FIELDS)
        self.assertEqual(summary["proposals_applied"], "1")
        self.assertEqual(summary["no_score_change_confirmed"], "True")
        self.assertEqual(summary["raw_master_mutation_performed"], "False")

    def test_private_paths_are_masked_in_reports_and_apply_rows(self) -> None:
        self.write_proposals([self.proposal_row(evidence_source_artifact="data/raw/private/fundamentals/sec_user_agent.local.txt")])
        result = self.run_apply()
        apply_rows = self.read_csv(result.apply_path)
        report = result.report_path.read_text(encoding="utf-8")
        self.assertEqual(apply_rows[0]["evidence_source_artifact"], "<private_artifact>")
        self.assertNotIn("data/raw/private", report)
        self.assertNotIn("sec_user_agent", report)

    def test_no_score_monthly_watchlist_dashboard_files_are_created(self) -> None:
        self.run_apply()
        names = {path.name for path in self.output_dir.iterdir()}
        self.assertNotIn("company_scores.csv", names)
        self.assertNotIn("watchlist_ranked.csv", names)
        self.assertNotIn("rebalance_proposals.csv", names)
        self.assertNotIn("dashboard_payload.json", names)


if __name__ == "__main__":
    unittest.main()
