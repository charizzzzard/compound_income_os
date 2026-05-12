from __future__ import annotations

import csv
import inspect
import shutil
import unittest
import uuid
from pathlib import Path

from src import personal_sec_core_kpi_refresh_plan as plan_module
from src.personal_sec_core_kpi_refresh_plan import run_personal_sec_core_kpi_refresh_plan


class PersonalSecCoreKpiRefreshPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_core_plan_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.queue = self.tmp / "queue.csv"
        self.scope = self.tmp / "scope.csv"
        self.identity_map = self.tmp / "identity_map.csv"
        self.identity_apply = self.tmp / "identity_apply.csv"
        self.plan = self.tmp / "plan.csv"
        self.summary = self.tmp / "summary.csv"
        self.report = self.tmp / "report.md"

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

    def queue_row(self, **overrides: str) -> dict[str, str]:
        row = {
            "ticker": "AAA",
            "isin": "US0000000001",
            "company_name": "Alpha Inc",
            "company_type_profile": "STANDARD",
            "missing_core_kpis": "revenue_cagr_5y; gross_margin",
            "missing_core_kpi_count": "2",
            "core_kpi_closure_status": "REVIEW",
            "reason_code": "CORE_KPI_MISSING;REVIEW_CORE_DATA;SEC_IDENTITY_AVAILABLE;NO_VALUE_CHANGES",
        }
        row.update(overrides)
        return row

    def write_queue(self, rows: list[dict[str, str]]) -> None:
        self.write_csv(
            self.queue,
            [
                "ticker",
                "isin",
                "company_name",
                "company_type_profile",
                "missing_core_kpis",
                "missing_core_kpi_count",
                "core_kpi_closure_status",
                "reason_code",
            ],
            rows,
        )

    def write_identity_map(self, rows: list[dict[str, str]]) -> None:
        self.write_csv(
            self.identity_map,
            ["ticker", "isin", "company_name", "cik", "sec_entity_name", "asset_type", "country", "enabled", "notes"],
            rows,
        )

    def run_plan(self):
        return run_personal_sec_core_kpi_refresh_plan(
            core_closure_queue_input=str(self.queue),
            sec_scope_review_input=str(self.scope),
            sec_identity_map_input=str(self.identity_map),
            sec_identity_apply_input=str(self.identity_apply),
            plan_output=str(self.plan),
            summary_output=str(self.summary),
            report_output=str(self.report),
        )

    def test_ready_identity_creates_explicit_refresh_plan_without_network_or_fetch(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_identity_map(
            [
                {
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "company_name": "Alpha Inc",
                    "cik": "0000000001",
                    "sec_entity_name": "Alpha Inc",
                    "asset_type": "STOCK",
                    "country": "US",
                    "enabled": "True",
                    "notes": "",
                }
            ]
        )

        result = self.run_plan()
        rows = result.plan_rows
        summary = result.summary_rows[0]

        self.assertEqual(rows[0]["sec_identity_status"], "APPROVED_IDENTITY")
        self.assertEqual(rows[0]["sec_refresh_plan_status"], "READY_FOR_EXPLICIT_SEC_REFRESH")
        self.assertEqual(summary["network_performed"], "False")
        self.assertEqual(summary["value_fetch_performed"], "False")
        self.assertEqual(rows[0]["evidence_apply_performed"], "False")

    def test_missing_identity_requires_identity_review(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_identity_map([])

        result = self.run_plan()
        row = result.plan_rows[0]

        self.assertEqual(row["sec_refresh_plan_status"], "REVIEW_IDENTITY")
        self.assertIn("SEC_IDENTITY_MISSING", row["reason_codes"])

    def test_missing_mapping_requires_mapping_review(self) -> None:
        self.write_queue([self.queue_row(missing_core_kpis="unknown_core_kpi")])
        self.write_identity_map(
            [
                {
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "company_name": "Alpha Inc",
                    "cik": "0000000001",
                    "sec_entity_name": "Alpha Inc",
                    "asset_type": "STOCK",
                    "country": "US",
                    "enabled": "True",
                    "notes": "",
                }
            ]
        )

        result = self.run_plan()
        row = result.plan_rows[0]

        self.assertEqual(row["mapping_review_required"], "yes")
        self.assertEqual(row["sec_refresh_plan_status"], "MAPPING_REVIEW_REQUIRED")
        self.assertIn("SEC_FACT_MAPPING_MISSING", row["reason_codes"])

    def test_non_standard_profile_not_applicable(self) -> None:
        self.write_queue([self.queue_row(company_type_profile="ETF")])
        self.write_identity_map([])

        result = self.run_plan()
        row = result.plan_rows[0]

        self.assertEqual(row["sec_refresh_plan_status"], "NOT_APPLICABLE")
        self.assertEqual(row["sec_identity_status"], "NOT_SEC_ELIGIBLE")
        self.assertIn("PROFILE_NOT_STANDARD", row["reason_codes"])

    def test_missing_core_closure_queue_writes_empty_summary_without_crash(self) -> None:
        self.write_identity_map([])

        result = self.run_plan()
        summary = result.summary_rows[0]

        self.assertEqual(result.plan_rows, [])
        self.assertEqual(summary["affected_rows_count"], "0")
        self.assertEqual(summary["network_performed"], "False")
        self.assertTrue(self.plan.exists())

    def test_no_network_client_is_imported_or_called(self) -> None:
        source = inspect.getsource(plan_module)

        self.assertNotIn("requests", source)
        self.assertNotIn("urlopen", source)
        self.assertNotIn("urllib", source)

    def test_no_master_evidence_or_score_files_are_written(self) -> None:
        master = self.tmp / "personal_fundamentals_master.csv"
        evidence = self.tmp / "personal_fundamentals_evidence_registry.csv"
        score = self.tmp / "personal_score_audit.csv"
        for path in (master, evidence, score):
            path.write_text("sentinel\n", encoding="utf-8")
        before = {path: path.read_text(encoding="utf-8") for path in (master, evidence, score)}
        self.write_queue([self.queue_row()])
        self.write_identity_map([])

        self.run_plan()

        after = {path: path.read_text(encoding="utf-8") for path in (master, evidence, score)}
        self.assertEqual(before, after)

    def test_report_does_not_dump_private_identity_details(self) -> None:
        self.write_queue([self.queue_row()])
        self.write_identity_map(
            [
                {
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "company_name": "Alpha Inc",
                    "cik": "1234567890",
                    "sec_entity_name": "Private SEC Entity",
                    "asset_type": "STOCK",
                    "country": "US",
                    "enabled": "True",
                    "notes": "private identity note",
                }
            ]
        )

        self.run_plan()
        text = self.report.read_text(encoding="utf-8")

        self.assertNotIn("1234567890", text)
        self.assertNotIn("Private SEC Entity", text)
        self.assertNotIn("private identity note", text)


if __name__ == "__main__":
    unittest.main()
