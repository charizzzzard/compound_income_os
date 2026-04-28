from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from datetime import date
from pathlib import Path

from src.fundamentals_master import PERSONAL_MASTER_FIELDS
from src.personal_sec_core_kpi_closure_impact_rerun import IMPACT_FIELDS, SUMMARY_FIELDS, run_personal_sec_core_kpi_closure_impact_rerun
from src.personal_sec_derived_kpi_reviewed_evidence_apply import APPLY_FIELDS, SUMMARY_FIELDS as APPLY_SUMMARY_FIELDS


class PersonalSecCoreKpiClosureImpactRerunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_core_closure_impact_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.baseline = self.tmp / "baseline_master.csv"
        self.applied = self.tmp / "applied_master.csv"
        self.apply_summary = self.tmp / "apply_summary.csv"
        self.apply_detail = self.tmp / "apply_detail.csv"
        self.proposals = self.tmp / "proposals.csv"
        self.registry = self.tmp / "registry_append.csv"
        self.queue = self.tmp / "closure_queue.csv"
        self.impact = self.tmp / "processed" / "impact.csv"
        self.summary = self.tmp / "processed" / "summary.csv"
        self.report = self.tmp / "reports" / "report.md"
        self.write_inputs()

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

    def master_row(self, *, operating_margin: str = "", gross_margin: str = "", revenue: str = "") -> dict[str, str]:
        row = {field: "" for field in PERSONAL_MASTER_FIELDS}
        row.update(
            {
                "ticker": "AAA",
                "isin": "US0000000001",
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
                "gross_margin": gross_margin,
                "revenue_cagr_5y": revenue,
            }
        )
        return row

    def apply_row(self, *, kpi: str = "operating_margin", evidence_id: str = "SEC_DERIVED__US0000000001__operating_margin__FY2025", old: str = "", new: str = "0.25") -> dict[str, str]:
        row = {field: "" for field in APPLY_FIELDS}
        row.update(
            {
                "evidence_id": evidence_id,
                "holding_name": "Alpha Inc",
                "ticker": "AAA",
                "isin": "US0000000001",
                "kpi_field": kpi,
                "old_value": old,
                "new_value": new,
                "proposed_value": new,
                "value_unit": "ratio",
                "apply_status": "APPLIED_TO_EVIDENCE_MASTER_COPY",
                "evidence_source_type": "SEC_COMPANYFACTS_DERIVED_KPI",
                "evidence_source_artifact": "data/processed/facts.csv",
                "confidence": "HIGH",
                "no_imputation_confirmed": "True",
                "master_mutation_performed": "False",
                "raw_master_mutation_performed": "False",
                "score_mutation_performed": "False",
            }
        )
        return row

    def proposal_row(self, *, evidence_id: str = "SEC_DERIVED__US0000000001__operating_margin__FY2025", fiscal_year: str = "2025") -> dict[str, str]:
        return {
            "evidence_id": evidence_id,
            "fiscal_year_end": fiscal_year,
            "source_filed_dates": "2026-02-01",
            "source_forms": "10-K",
        }

    def write_inputs(self) -> None:
        self.write_csv(self.baseline, PERSONAL_MASTER_FIELDS, [self.master_row()])
        self.write_csv(self.applied, PERSONAL_MASTER_FIELDS, [self.master_row(operating_margin="0.25")])
        self.write_csv(
            self.apply_summary,
            APPLY_SUMMARY_FIELDS,
            [
                {
                    "evidence_proposals_input": "1",
                    "proposals_eligible_for_apply": "1",
                    "proposals_applied": "1",
                    "proposals_skipped": "0",
                    "holdings_updated": "1",
                    "kpi_fields_updated": "1",
                    "raw_master_mutation_performed": "False",
                    "evidence_applied_master_written": "True",
                    "score_mutation_performed": "False",
                    "no_score_change_confirmed": "True",
                    "no_imputation_confirmed": "True",
                    "no_network_confirmed": "True",
                }
            ],
        )
        self.write_csv(self.apply_detail, APPLY_FIELDS, [self.apply_row()])
        self.write_csv(self.proposals, ["evidence_id", "fiscal_year_end", "source_filed_dates", "source_forms"], [self.proposal_row()])
        self.write_csv(self.registry, ["evidence_id"], [])
        self.write_csv(
            self.queue,
            ["ticker", "isin", "company_name", "missing_core_kpis"],
            [{"ticker": "AAA", "isin": "US0000000001", "company_name": "Alpha Inc", "missing_core_kpis": "operating_margin"}],
        )

    def run_impact(self):
        return run_personal_sec_core_kpi_closure_impact_rerun(
            baseline_master=self.baseline,
            evidence_applied_master=self.applied,
            apply_summary=self.apply_summary,
            apply_detail=self.apply_detail,
            evidence_proposals=self.proposals,
            registry_append=self.registry,
            closure_queue=self.queue,
            impact_output=self.impact,
            summary_output=self.summary,
            report_output=self.report,
            as_of_date=date(2026, 4, 28),
        )

    def test_detects_kpi_closure_from_blank_to_evidence_value(self) -> None:
        result = self.run_impact()
        rows = self.read_csv(result.impact_path)
        self.assertEqual(rows[0]["closure_status"], "CLOSED_BY_SEC_DERIVED_KPI")
        self.assertEqual(rows[0]["baseline_value"], "")
        self.assertEqual(rows[0]["evidence_applied_value"], "0.25")
        self.assertEqual(result.summary["closed_kpi_count"], "1")

    def test_does_not_treat_unchanged_existing_values_as_new_closure(self) -> None:
        self.write_csv(self.baseline, PERSONAL_MASTER_FIELDS, [self.master_row(operating_margin="0.25")])
        self.write_csv(self.applied, PERSONAL_MASTER_FIELDS, [self.master_row(operating_margin="0.25")])
        result = self.run_impact()
        row = self.read_csv(result.impact_path)[0]
        self.assertEqual(row["closure_status"], "UNCHANGED_EXISTING")
        self.assertEqual(result.summary["closed_kpi_count"], "0")

    def test_emits_stale_flag_for_old_fiscal_years(self) -> None:
        self.write_csv(self.proposals, ["evidence_id", "fiscal_year_end", "source_filed_dates", "source_forms"], [self.proposal_row(fiscal_year="2018")])
        result = self.run_impact()
        row = self.read_csv(result.impact_path)[0]
        self.assertEqual(row["stale_or_old_fiscal_year"], "True")
        self.assertIn("2018", row["stale_reason"])

    def test_summary_contains_raw_master_hash_before_after(self) -> None:
        result = self.run_impact()
        summary = self.read_csv(result.summary_path)[0]
        self.assertEqual(list(summary.keys()), SUMMARY_FIELDS)
        self.assertTrue(summary["raw_master_sha256_before"])
        self.assertEqual(summary["raw_master_sha256_before"], summary["raw_master_sha256_after"])

    def test_confirms_raw_master_not_mutated(self) -> None:
        result = self.run_impact()
        self.assertEqual(result.summary["raw_master_mutation_performed"], "False")

    def test_no_score_monthly_watchlist_dashboard_files_are_created(self) -> None:
        self.run_impact()
        names = {path.name for path in (self.tmp / "processed").iterdir()}
        self.assertNotIn("company_scores.csv", names)
        self.assertNotIn("monthly_buy_ranking.csv", names)
        self.assertNotIn("watchlist_ranked.csv", names)
        self.assertNotIn("dashboard_payload.json", names)

    def test_missing_required_inputs_fail_deterministically(self) -> None:
        self.applied.unlink()
        with self.assertRaisesRegex(RuntimeError, "MISSING_EVIDENCE_APPLIED_MASTER"):
            self.run_impact()

    def test_csv_headers_are_stable(self) -> None:
        result = self.run_impact()
        impact_rows = self.read_csv(result.impact_path)
        summary_rows = self.read_csv(result.summary_path)
        self.assertEqual(list(impact_rows[0].keys()), IMPACT_FIELDS)
        self.assertEqual(list(summary_rows[0].keys()), SUMMARY_FIELDS)


if __name__ == "__main__":
    unittest.main()
