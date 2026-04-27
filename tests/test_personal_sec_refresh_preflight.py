from __future__ import annotations

import csv
import inspect
import shutil
import unittest
import uuid
from pathlib import Path

from src import personal_sec_refresh_preflight as preflight_module
from src.personal_sec_refresh_preflight import run_personal_sec_refresh_preflight


class PersonalSecRefreshPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_preflight_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.plan = self.tmp / "plan.csv"
        self.plan_summary = self.tmp / "plan_summary.csv"
        self.identity_map = self.tmp / "identity_map.csv"
        self.fetch_module = self.tmp / "fetch_module.py"
        self.refresh_cli = self.tmp / "refresh_cli.py"
        self.preflight = self.tmp / "preflight.csv"
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

    def write_plan(self, rows: list[dict[str, str]]) -> None:
        self.write_csv(
            self.plan,
            [
                "ticker",
                "isin",
                "company_name",
                "company_type_profile",
                "missing_core_kpis",
                "sec_identity_status",
                "sec_refresh_plan_status",
            ],
            rows,
        )
        self.write_csv(
            self.plan_summary,
            [
                "affected_rows_count",
                "ready_for_explicit_sec_refresh_count",
                "identity_missing_count",
                "identity_review_count",
                "mapping_review_required_count",
                "not_ready_count",
                "network_performed",
                "value_fetch_performed",
                "evidence_apply_performed",
                "master_mutation_performed",
                "score_mutation_performed",
                "reason_codes",
            ],
            [
                {
                    "affected_rows_count": str(len(rows)),
                    "ready_for_explicit_sec_refresh_count": str(len(rows)),
                    "identity_missing_count": "0",
                    "identity_review_count": "0",
                    "mapping_review_required_count": "0",
                    "not_ready_count": "0",
                    "network_performed": "False",
                    "value_fetch_performed": "False",
                    "evidence_apply_performed": "False",
                    "master_mutation_performed": "False",
                    "score_mutation_performed": "False",
                    "reason_codes": "READY_FOR_EXPLICIT_SEC_REFRESH",
                }
            ],
        )

    def plan_row(self, **overrides: str) -> dict[str, str]:
        row = {
            "ticker": "AAA",
            "isin": "US0000000001",
            "company_name": "Alpha Inc",
            "company_type_profile": "STANDARD",
            "missing_core_kpis": "revenue_cagr_5y; gross_margin",
            "sec_identity_status": "APPROVED_IDENTITY",
            "sec_refresh_plan_status": "READY_FOR_EXPLICIT_SEC_REFRESH",
        }
        row.update(overrides)
        return row

    def write_identity_map(self, valid: bool = True) -> None:
        fields = ["ticker", "isin", "company_name", "cik", "sec_entity_name", "asset_type", "country", "enabled", "notes"]
        if not valid:
            fields = ["ticker", "isin"]
        self.write_csv(
            self.identity_map,
            fields,
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
                    "notes": "private note",
                }
            ],
        )

    def write_modules(self, *, fetch: bool = True, refresh: bool = True) -> None:
        if fetch:
            self.fetch_module.write_text(
                "import argparse\n\ndef main():\n    parser = argparse.ArgumentParser()\n    parser.add_argument('--allow-network', action='store_true')\n    parser.add_argument('--sec-user-agent', default='')\n",
                encoding="utf-8",
            )
        if refresh:
            self.refresh_cli.write_text(
                "import argparse\n\ndef main():\n    parser = argparse.ArgumentParser()\n    parser.add_argument('--allow-network', action='store_true')\n    parser.add_argument('--sec-user-agent', default='')\n",
                encoding="utf-8",
            )

    def run_preflight(self, *, user_agent: str = ""):
        return run_personal_sec_refresh_preflight(
            sec_plan_input=str(self.plan),
            sec_plan_summary_input=str(self.plan_summary),
            sec_identity_map_input=str(self.identity_map),
            fetch_module_path=str(self.fetch_module),
            refresh_cli_module_path=str(self.refresh_cli),
            sec_user_agent=user_agent,
            preflight_output=str(self.preflight),
            summary_output=str(self.summary),
            report_output=str(self.report),
        )

    def test_ready_plan_identity_and_user_agent_is_ready_without_network_or_fetch(self) -> None:
        self.write_plan([self.plan_row()])
        self.write_identity_map()
        self.write_modules()

        result = self.run_preflight(user_agent="Test Contact test@example.com")
        row = result.preflight_rows[0]
        summary = result.summary_rows[0]

        self.assertEqual(row["preflight_status"], "READY_FOR_EXPLICIT_NETWORK_RUN")
        self.assertEqual(summary["ready_for_explicit_network_run_count"], "1")
        self.assertEqual(summary["network_performed"], "False")
        self.assertEqual(summary["fetch_performed"], "False")

    def test_identity_map_missing_blocks_or_requires_review(self) -> None:
        self.write_plan([self.plan_row()])
        self.write_modules()

        result = self.run_preflight(user_agent="Test Contact test@example.com")
        row = result.preflight_rows[0]

        self.assertIn(row["preflight_status"], {"BLOCKED", "REVIEW_REQUIRED"})
        self.assertIn("SEC_IDENTITY_MAP_MISSING", row["reason_codes"])

    def test_user_agent_missing_requires_review(self) -> None:
        self.write_plan([self.plan_row()])
        self.write_identity_map()
        self.write_modules()

        result = self.run_preflight()
        row = result.preflight_rows[0]

        self.assertEqual(row["preflight_status"], "REVIEW_REQUIRED")
        self.assertIn("SEC_USER_AGENT_MISSING", row["reason_codes"])

    def test_sec_plan_missing_writes_not_available_summary_without_crash(self) -> None:
        self.write_identity_map()
        self.write_modules()

        result = self.run_preflight(user_agent="Test Contact test@example.com")
        summary = result.summary_rows[0]

        self.assertEqual(result.preflight_rows, [])
        self.assertEqual(summary["plan_rows_count"], "0")
        self.assertEqual(summary["network_performed"], "False")
        self.assertIn("SEC_REFRESH_PLAN_MISSING", summary["reason_codes"])

    def test_fetch_module_missing_does_not_invent_command(self) -> None:
        self.write_plan([self.plan_row()])
        self.write_identity_map()
        self.write_modules(fetch=False, refresh=True)

        result = self.run_preflight(user_agent="Test Contact test@example.com")
        summary = result.summary_rows[0]
        row = result.preflight_rows[0]

        self.assertIn(summary["future_refresh_command_status"], {"MISSING", "REVIEW"})
        self.assertEqual(row["fetch_module_status"], "MISSING")
        self.assertIn("FETCH_MODULE_MISSING", row["reason_codes"])

    def test_no_network_client_is_imported_or_called(self) -> None:
        source = inspect.getsource(preflight_module)

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
        self.write_plan([self.plan_row()])
        self.write_identity_map()
        self.write_modules()

        self.run_preflight(user_agent="Test Contact test@example.com")

        after = {path: path.read_text(encoding="utf-8") for path in (master, evidence, score)}
        self.assertEqual(before, after)

    def test_report_does_not_dump_private_identity_details(self) -> None:
        self.write_plan([self.plan_row()])
        self.write_identity_map()
        self.write_modules()

        self.run_preflight(user_agent="Test Contact test@example.com")
        text = self.report.read_text(encoding="utf-8")

        self.assertNotIn("0000000001", text)
        self.assertNotIn("private note", text)


if __name__ == "__main__":
    unittest.main()
