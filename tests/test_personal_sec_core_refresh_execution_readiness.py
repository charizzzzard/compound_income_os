from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.handoff_zip_export import HANDOFF_ARTIFACT_FILES, HANDOFF_ARTIFACT_GLOBS
from src.personal_sec_core_refresh_execution_readiness import run_personal_sec_core_refresh_execution_readiness


class PersonalSecCoreRefreshExecutionReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_execution_readiness_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.plan = self.tmp / "plan.csv"
        self.preflight_summary = self.tmp / "preflight_summary.csv"
        self.identity_map = self.tmp / "identity_map.csv"
        self.readiness = self.tmp / "readiness.csv"
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

    def write_plan(self) -> None:
        self.write_csv(
            self.plan,
            [
                "ticker",
                "isin",
                "company_name",
                "company_type_profile",
                "missing_core_kpis",
                "missing_core_kpi_count",
                "sec_identity_status",
                "sec_refresh_plan_status",
                "mapping_review_required",
            ],
            [
                {
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "company_name": "Alpha Inc",
                    "company_type_profile": "STANDARD",
                    "missing_core_kpis": "revenue_cagr_5y",
                    "missing_core_kpi_count": "1",
                    "sec_identity_status": "APPROVED_IDENTITY",
                    "sec_refresh_plan_status": "READY_FOR_EXPLICIT_SEC_REFRESH",
                    "mapping_review_required": "no",
                }
            ],
        )

    def write_preflight_summary(self, *, present: str = "True", valid: str = "True") -> None:
        self.write_csv(
            self.preflight_summary,
            ["identity_map_present", "identity_schema_valid"],
            [{"identity_map_present": present, "identity_schema_valid": valid}],
        )

    def write_identity_map(self, valid: bool = True) -> None:
        fields = ["ticker", "isin", "company_name", "cik", "sec_entity_name", "asset_type", "country", "enabled", "notes"]
        row = {
            "ticker": "AAA",
            "isin": "US0000000001",
            "company_name": "Alpha Inc",
            "cik": "0000000001",
            "sec_entity_name": "Alpha Private Entity",
            "asset_type": "STOCK",
            "country": "US",
            "enabled": "True",
            "notes": "private note",
        }
        if not valid:
            fields = ["ticker", "isin"]
            row = {"ticker": "AAA", "isin": "US0000000001"}
        self.write_csv(
            self.identity_map,
            fields,
            [row],
        )

    def run_readiness(self, *, user_agent: str = ""):
        return run_personal_sec_core_refresh_execution_readiness(
            plan_input=str(self.plan),
            preflight_summary_input=str(self.preflight_summary),
            identity_map_input=str(self.identity_map),
            readiness_output=str(self.readiness),
            summary_output=str(self.summary),
            report_output=str(self.report),
            sec_user_agent=user_agent,
        )

    def test_ready_plan_missing_user_agent_blocks_without_network_or_value_changes(self) -> None:
        self.write_plan()
        self.write_identity_map()
        result = self.run_readiness()
        summary = result.summary_rows[0]

        self.assertEqual(summary["execution_status"], "BLOCKED_NOT_EXECUTED")
        self.assertEqual(summary["missing_user_agent_count"], "1")
        self.assertEqual(summary["network_performed"], "False")
        self.assertEqual(summary["evidence_apply_performed"], "False")

    def test_ready_plan_with_user_agent_is_ready_for_explicit_run_without_execution(self) -> None:
        self.write_plan()
        self.write_identity_map()
        result = self.run_readiness(user_agent="Max Contact max@example.com")
        summary = result.summary_rows[0]

        self.assertEqual(summary["execution_status"], "READY_FOR_EXPLICIT_RUN")
        self.assertEqual(summary["ready_count"], "1")
        self.assertEqual(summary["network_performed"], "False")

    def test_private_paths_are_masked_in_public_report(self) -> None:
        self.write_plan()
        self.write_identity_map()
        private_path = self.tmp / "data" / "raw" / "private" / "fundamentals" / "personal_sec_identity_map.csv"
        result = run_personal_sec_core_refresh_execution_readiness(
            plan_input=str(self.plan),
            preflight_summary_input=str(self.preflight_summary),
            identity_map_input=str(private_path),
            readiness_output=str(self.readiness),
            summary_output=str(self.summary),
            report_output=str(self.report),
        )
        text = self.report.read_text(encoding="utf-8")

        self.assertIn("<private_path>", text)
        self.assertNotIn("data/raw/private/fundamentals/personal_sec_identity_map.csv", text)
        self.assertEqual(result.summary_rows[0]["execution_status"], "BLOCKED_NOT_EXECUTED")

    def test_invalid_identity_map_blocks_deterministically(self) -> None:
        self.write_plan()
        self.write_identity_map(valid=False)
        result = self.run_readiness(user_agent="Max Contact max@example.com")
        summary = result.summary_rows[0]

        self.assertEqual(summary["identity_map_status"], "INVALID_SCHEMA")
        self.assertEqual(summary["execution_status"], "BLOCKED_NOT_EXECUTED")

    def test_missing_identity_map_blocks_deterministically(self) -> None:
        self.write_plan()
        self.write_preflight_summary(present="False", valid="False")
        result = self.run_readiness(user_agent="Max Contact max@example.com")
        summary = result.summary_rows[0]

        self.assertEqual(summary["identity_map_status"], "MISSING")
        self.assertEqual(summary["execution_status"], "BLOCKED_NOT_EXECUTED")

    def test_handoff_allowlist_contains_execution_readiness_artifacts(self) -> None:
        self.assertIn("data/processed/personal_sec_core_refresh_execution_readiness.csv", HANDOFF_ARTIFACT_FILES)
        self.assertIn("data/processed/personal_sec_core_refresh_execution_readiness_summary.csv", HANDOFF_ARTIFACT_FILES)
        self.assertIn("reports/*/personal_sec_core_refresh_execution_readiness_report.md", HANDOFF_ARTIFACT_GLOBS)


if __name__ == "__main__":
    unittest.main()
