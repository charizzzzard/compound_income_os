from __future__ import annotations

import csv
import json
import shutil
import unittest
from pathlib import Path

from src.personal_readiness_status import run_personal_readiness_status

ROOT = Path(__file__).resolve().parent.parent


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class PersonalReadinessStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_readiness_status"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.reconciliation_summary = self.tmp / "reconciliation_summary.csv"
        self.reconciliation_checks = self.tmp / "reconciliation_checks.csv"
        self.freshness = self.tmp / "freshness.csv"
        self.watchlist = self.tmp / "watchlist.csv"
        self.monthly = self.tmp / "monthly.csv"
        self.score_provenance = self.tmp / "score_provenance.csv"
        self.kpi_provenance = self.tmp / "kpi_provenance.csv"
        self.valuation = self.tmp / "valuation.csv"
        self.core = self.tmp / "core.csv"
        self.dividend_fcf = self.tmp / "dividend_fcf.csv"
        self.used_inputs = self.tmp / "used_inputs.csv"
        self.manifest = self.tmp / "manifest.json"
        self.deployment_notes = self.tmp / "DEPLOYMENT_NOTES.md"
        self.env_example = self.tmp / ".env.example"
        self.summary = self.tmp / "summary.csv"
        self.blockers = self.tmp / "blockers.csv"
        self.next_actions = self.tmp / "next_actions.csv"
        self.report = self.tmp / "report.md"
        self.write_base_inputs()

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_metric_file(self, path: Path, rows: dict[str, str]) -> None:
        write_csv(path, ["metric", "value", "notes"], [{"metric": key, "value": value, "notes": ""} for key, value in rows.items()])

    def write_base_inputs(self) -> None:
        self.write_metric_file(
            self.reconciliation_summary,
            {
                "demo_readiness_status": "BLOCKED",
                "decision_readiness_status": "BLOCKED",
                "artifact_drift_active": "False",
                "monthly_schema_drift_resolved": "True",
                "standard_missing_valuation_required_rows_total": "1",
                "standard_missing_dividend_fcf_required_rows_total": "1",
                "standard_review_core_data_rows_total": "1",
            },
        )
        write_csv(
            self.reconciliation_checks,
            ["check_id", "category", "status", "reason_codes", "observed_value", "expected_value", "evidence", "recommended_next_action"],
            [],
        )
        self.write_metric_file(
            self.freshness,
            {
                "artifact_drift_active": "False",
                "freshness_reason_codes": "MISSING_METADATA;STALE_DERIVED_ARTIFACT",
            },
        )
        self.write_metric_file(
            self.watchlist,
            {
                "watchlist_input_status": "SAMPLE_DEMO_ONLY",
                "watchlist_data_status": "MISSING_DATA",
                "watchlist_readiness_status": "BLOCKED",
                "watchlist_reason_codes": "WATCHLIST_REVIEW_OR_MISSING_DATA;WATCHLIST_SAMPLE_INPUT",
                "watchlist_input_path": "data/raw/sample_watchlist.csv",
            },
        )
        self.write_metric_file(
            self.monthly,
            {
                "monthly_schema_drift_resolved": "True",
                "forbidden_monthly_action_values_total": "0",
            },
        )
        self.write_metric_file(
            self.score_provenance,
            {
                "provenance_incomplete_flag": "True",
                "holdings_with_incomplete_provenance_total": "1",
            },
        )
        self.write_metric_file(self.kpi_provenance, {"audit_rows_total": "1"})
        self.write_metric_file(
            self.valuation,
            {
                "affected_standard_rows_count": "1",
                "approved_rows_count": "0",
                "reason_codes": "VALUATION_REQUIRED_MISSING;INPUT_FILE_MISSING;NO_IMPUTATION",
            },
        )
        self.write_metric_file(
            self.core,
            {
                "affected_standard_rows_count": "1",
                "reason_codes": "REVIEW_CORE_DATA;CORE_KPI_MISSING;NO_VALUE_CHANGES",
                "sec_evidence_possible_count": "1",
            },
        )
        self.write_metric_file(
            self.dividend_fcf,
            {
                "affected_standard_rows_count": "1",
                "approved_rows_count": "0",
                "reason_codes": "DIVIDEND_FCF_REQUIRED_MISSING;INPUT_FILE_MISSING;NO_IMPUTATION",
            },
        )
        write_csv(self.used_inputs, ["stage_name", "input_role", "input_path"], [])
        self.manifest.write_text(json.dumps({"stages": []}), encoding="utf-8")
        self.deployment_notes.write_text("Private preview. Not ready for public deployment.", encoding="utf-8")
        self.env_example.write_text(
            "\n".join(
                [
                    "VITE_SAMPLE_REPORT_URL=",
                    "VITE_EARLY_ACCESS_URL=",
                    "VITE_SETUP_SERVICE_URL=",
                    "VITE_GITHUB_URL=",
                    "VITE_PRIVACY_URL=",
                    "VITE_IMPRINT_URL=",
                ]
            ),
            encoding="utf-8",
        )

    def run_status(self, **overrides):
        params = {
            "reconciliation_summary_input": str(self.reconciliation_summary),
            "reconciliation_checks_input": str(self.reconciliation_checks),
            "artifact_freshness_summary_input": str(self.freshness),
            "watchlist_gate_summary_input": str(self.watchlist),
            "monthly_action_summary_input": str(self.monthly),
            "score_audit_provenance_summary_input": str(self.score_provenance),
            "kpi_provenance_summary_input": str(self.kpi_provenance),
            "valuation_contract_summary_input": str(self.valuation),
            "core_kpi_closure_summary_input": str(self.core),
            "dividend_fcf_contract_summary_input": str(self.dividend_fcf),
            "used_inputs_input": str(self.used_inputs),
            "manifest_input": str(self.manifest),
            "deployment_notes_input": str(self.deployment_notes),
            "env_example_input": str(self.env_example),
            "summary_output": str(self.summary),
            "blockers_output": str(self.blockers),
            "next_actions_output": str(self.next_actions),
            "report_output": str(self.report),
        }
        params.update(overrides)
        return run_personal_readiness_status(**params)

    def summary_status(self, scope: str) -> str:
        return {row["readiness_scope"]: row["readiness_status"] for row in read_csv(self.summary)}[scope]

    def blocker_rows(self, code: str) -> list[dict[str, str]]:
        return [row for row in read_csv(self.blockers) if row["blocker_code"] == code]

    def test_active_contract_core_provenance_and_watchlist_block_decision(self) -> None:
        self.run_status()
        self.assertEqual(self.summary_status("DECISION"), "BLOCKED")
        active_codes = {row["blocker_code"] for row in read_csv(self.blockers) if row["blocker_status"] == "ACTIVE"}
        self.assertIn("MISSING_VALUATION_REQUIRED", active_codes)
        self.assertIn("MISSING_DIVIDEND_FCF_REQUIRED", active_codes)
        self.assertIn("REVIEW_CORE_DATA", active_codes)
        self.assertIn("PROVENANCE_INCOMPLETE", active_codes)
        self.assertIn("WATCHLIST_SAMPLE_INPUT", active_codes)

    def test_monthly_schema_resolved_is_not_active(self) -> None:
        self.run_status()
        rows = self.blocker_rows("MONTHLY_SCHEMA_DRIFT")
        self.assertEqual(rows[0]["blocker_status"], "RESOLVED")
        self.assertEqual(rows[0]["reason_codes"], "MONTHLY_SCHEMA_DRIFT_RESOLVED")

    def test_artifact_drift_resolved_but_metadata_review_remains(self) -> None:
        self.run_status()
        self.assertEqual(self.blocker_rows("ARTIFACT_DRIFT")[0]["blocker_status"], "RESOLVED")
        self.assertEqual(self.blocker_rows("MISSING_METADATA")[0]["blocker_status"], "ACTIVE")
        self.assertEqual(self.blocker_rows("STALE_ARTIFACT")[0]["blocker_status"], "ACTIVE")

    def test_sample_watchlist_blocks_demo_and_decision(self) -> None:
        self.run_status()
        self.assertEqual(self.summary_status("DEMO"), "BLOCKED")
        self.assertEqual(self.summary_status("DECISION"), "BLOCKED")
        rows = self.blocker_rows("WATCHLIST_SAMPLE_INPUT")
        self.assertTrue(any(row["readiness_scope"] == "DEMO" and row["blocker_status"] == "ACTIVE" for row in rows))

    def test_handoff_scope_is_review_without_forbidden_zip_claims(self) -> None:
        self.write_metric_file(self.freshness, {"artifact_drift_active": "False", "freshness_reason_codes": ""})
        self.run_status()
        self.assertIn(self.summary_status("HANDOFF"), {"PASS", "REVIEW"})
        text = self.report.read_text(encoding="utf-8")
        self.assertNotIn("forbidden entries count", text.lower())

    def test_missing_summary_artifacts_are_not_available_without_crash(self) -> None:
        missing = self.tmp / "missing.csv"
        self.run_status(
            reconciliation_summary_input=str(missing),
            reconciliation_checks_input=str(missing),
            watchlist_gate_summary_input=str(missing),
            monthly_action_summary_input=str(missing),
            score_audit_provenance_summary_input=str(missing),
            valuation_contract_summary_input=str(missing),
            core_kpi_closure_summary_input=str(missing),
            dividend_fcf_contract_summary_input=str(missing),
        )
        self.assertEqual(self.summary_status("DEMO"), "NOT_AVAILABLE")
        self.assertEqual(self.summary_status("DECISION"), "NOT_AVAILABLE")
        self.assertEqual(self.summary_status("DASHBOARD"), "NOT_AVAILABLE")

    def test_next_actions_do_not_use_advice_or_order_language(self) -> None:
        self.run_status()
        text = "\n".join(",".join(row.values()) for row in read_csv(self.next_actions)).upper()
        for term in ("BUY", "SELL", "STRONG_BUY", "STRONG_SELL", "RECOMMEND", "TRADE_SIGNAL", "ORDER", "EXECUTE"):
            self.assertNotIn(term, text)

    def test_report_sanitizes_private_paths(self) -> None:
        self.write_metric_file(
            self.watchlist,
            {
                "watchlist_input_status": "SAMPLE_DEMO_ONLY",
                "watchlist_data_status": "MISSING_DATA",
                "watchlist_readiness_status": "BLOCKED",
                "watchlist_reason_codes": "WATCHLIST_SAMPLE_INPUT",
                "watchlist_input_path": "data/raw/private/secret_watchlist.csv",
            },
        )
        self.run_status()
        text = self.report.read_text(encoding="utf-8")
        self.assertNotIn("data/raw/private/secret_watchlist.csv", text)
        self.assertIn("<private_path>", self.blocker_rows("WATCHLIST_SAMPLE_INPUT")[0]["observed_value"])


if __name__ == "__main__":
    unittest.main()
