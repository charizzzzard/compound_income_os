from __future__ import annotations

import csv
import json
import shutil
import unittest
import uuid
from pathlib import Path

from src.dashboard_readiness_payload import FORBIDDEN_DISPLAY_TERMS, run_dashboard_readiness_payload


class DashboardReadinessPayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_dashboard_payload_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.panel = self.tmp / "dashboard_readiness_panel.csv"
        self.blockers = self.tmp / "dashboard_readiness_blockers.csv"
        self.actions = self.tmp / "dashboard_readiness_next_actions.csv"
        self.payload = self.tmp / "dashboard_readiness_payload.json"
        self.report = self.tmp / "dashboard_readiness_payload_report.md"

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def write_inputs(self) -> None:
        self.write_csv(
            self.panel,
            [
                "panel_section",
                "metric_name",
                "metric_value",
                "status",
                "severity",
                "source_artifact",
                "reason_codes",
                "display_label",
                "display_hint",
                "safe_cta",
            ],
            [
                {"panel_section": "READINESS_OVERVIEW", "metric_name": "demo_readiness", "metric_value": "BLOCKED", "status": "BLOCKED", "severity": "P0_BLOCKER", "source_artifact": "data/processed/personal_readiness_status_summary.csv", "reason_codes": "WATCHLIST_SAMPLE_INPUT", "display_label": "Demo readiness", "display_hint": "Demo readiness is blocked.", "safe_cta": "Review handoff package"},
                {"panel_section": "READINESS_OVERVIEW", "metric_name": "decision_readiness", "metric_value": "BLOCKED", "status": "BLOCKED", "severity": "P0_BLOCKER", "source_artifact": "data/processed/personal_readiness_status_summary.csv", "reason_codes": "MISSING_VALUATION_REQUIRED", "display_label": "Decision readiness", "display_hint": "Decision readiness is blocked.", "safe_cta": "Open readiness report"},
                {"panel_section": "READINESS_OVERVIEW", "metric_name": "dashboard_readiness", "metric_value": "REVIEW", "status": "REVIEW", "severity": "P1_REVIEW", "source_artifact": "data/processed/personal_readiness_status_summary.csv", "reason_codes": "WATCHLIST_REVIEW_OR_MISSING_DATA", "display_label": "Dashboard readiness", "display_hint": "Dashboard readiness is under review.", "safe_cta": "Open readiness report"},
                {"panel_section": "READINESS_OVERVIEW", "metric_name": "handoff_readiness", "metric_value": "REVIEW", "status": "REVIEW", "severity": "P1_REVIEW", "source_artifact": "data/processed/personal_readiness_status_summary.csv", "reason_codes": "MISSING_METADATA", "display_label": "Handoff readiness", "display_hint": "Handoff readiness is under review.", "safe_cta": "Review handoff package"},
                {"panel_section": "SEC_PREFLIGHT", "metric_name": "sec_preflight_status", "metric_value": "USER_AGENT_MISSING", "status": "REVIEW", "severity": "P1_REVIEW", "source_artifact": "data/processed/personal_sec_refresh_preflight_summary.csv", "reason_codes": "SEC_USER_AGENT_MISSING;NO_NETWORK_PERFORMED", "display_label": "SEC preflight", "display_hint": "SEC refresh remains gated; no network or fetch was performed.", "safe_cta": "Prepare explicit SEC refresh"},
                {"panel_section": "PRIVATE_INPUTS", "metric_name": "valuation_candidate_rows", "metric_value": "0", "status": "BLOCKED", "severity": "P0_BLOCKER", "source_artifact": "data/processed/personal_private_input_apply_candidates_summary.csv", "reason_codes": "INPUT_FILE_MISSING;NO_APPROVED_INPUTS", "display_label": "Valuation candidates", "display_hint": "Approved candidates: 0.", "safe_cta": "Review private valuation inputs"},
            ],
        )
        self.write_csv(
            self.blockers,
            [
                "blocker_code",
                "blocker_status",
                "blocker_severity",
                "readiness_scope",
                "display_title",
                "display_description",
                "source_artifact",
                "safe_next_action",
                "dashboard_priority",
                "show_on_dashboard",
            ],
            [
                {"blocker_code": "MISSING_VALUATION_REQUIRED", "blocker_status": "ACTIVE", "blocker_severity": "P0_BLOCKER", "readiness_scope": "DECISION", "display_title": "Valuation inputs missing", "display_description": "Active blocker for decision scope.", "source_artifact": "data/processed/personal_valuation_input_contract_summary.csv", "safe_next_action": "Review private valuation inputs", "dashboard_priority": "10", "show_on_dashboard": "yes"},
                {"blocker_code": "MONTHLY_SCHEMA_DRIFT", "blocker_status": "RESOLVED", "blocker_severity": "INFO", "readiness_scope": "DASHBOARD", "display_title": "Monthly schema drift resolved", "display_description": "Resolved blocker.", "source_artifact": "data/processed/personal_monthly_action_compatibility_summary.csv", "safe_next_action": "Open readiness report", "dashboard_priority": "80", "show_on_dashboard": "yes"},
            ],
        )
        self.write_csv(
            self.actions,
            [
                "priority",
                "action_title",
                "action_description",
                "blocker_code",
                "requires_private_input",
                "requires_external_api",
                "requires_value_change",
                "safe_next_patch",
                "source_artifact",
                "dashboard_cta_label",
            ],
            [
                {"priority": "P0_BLOCKER", "action_title": "Review private valuation inputs", "action_description": "Fill reviewed private valuation input or keep readiness blocked.", "blocker_code": "MISSING_VALUATION_REQUIRED", "requires_private_input": "yes", "requires_external_api": "no", "requires_value_change": "yes_reviewed_input_only", "safe_next_patch": "VALUATION REVIEW INPUT APPLY / APPROVED ONLY / NO IMPUTATION", "source_artifact": "data/processed/personal_valuation_input_contract_summary.csv", "dashboard_cta_label": "Review private valuation inputs"}
            ],
        )

    def run_payload(self, *, missing: bool = False):
        if not missing:
            self.write_inputs()
        return run_dashboard_readiness_payload(
            panel_input=str(self.panel),
            blockers_input=str(self.blockers),
            next_actions_input=str(self.actions),
            payload_output=str(self.payload),
            report_output=str(self.report),
            server_integration="done",
        )

    def test_valid_artifacts_create_payload(self) -> None:
        result = self.run_payload()

        self.assertEqual(result.payload["metadata"]["schema_version"], "1")
        self.assertEqual(result.payload["summary"]["active_blockers_count"], 1)
        self.assertEqual(result.payload["summary"]["next_actions_count"], 1)
        self.assertTrue(result.payload["sections"]["readiness_overview"])

    def test_readiness_scopes_are_separate(self) -> None:
        result = self.run_payload()
        readiness = result.payload["readiness"]

        self.assertEqual(readiness["demo"]["status"], "BLOCKED")
        self.assertEqual(readiness["decision"]["status"], "BLOCKED")
        self.assertEqual(readiness["dashboard"]["status"], "REVIEW")
        self.assertEqual(readiness["handoff"]["status"], "REVIEW")

    def test_missing_inputs_are_not_available_without_crash(self) -> None:
        result = self.run_payload(missing=True)

        self.assertEqual(result.payload["readiness"]["decision"]["status"], "NOT_AVAILABLE")
        self.assertTrue(result.warnings)
        self.assertTrue(self.payload.exists())

    def test_advice_language_guardrail_sanitizes_cta_terms(self) -> None:
        self.write_inputs()
        with self.actions.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        rows[0]["dashboard_cta_label"] = "Buy"
        self.write_csv(self.actions, list(rows[0].keys()), rows)

        result = run_dashboard_readiness_payload(
            panel_input=str(self.panel),
            blockers_input=str(self.blockers),
            next_actions_input=str(self.actions),
            payload_output=str(self.payload),
            report_output=str(self.report),
        )

        self.assertEqual(result.payload["sections"]["next_actions"][0]["cta_label"], "Open readiness report")

    def test_private_data_is_sanitized_from_payload_and_report(self) -> None:
        self.write_inputs()
        with self.panel.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        rows[0]["display_hint"] = "private note CIK0000123456 value 123.45 data/raw/private/file.csv"
        self.write_csv(self.panel, list(rows[0].keys()), rows)

        result = self.run_payload(missing=True)
        text = json.dumps(result.payload, sort_keys=True) + self.report.read_text(encoding="utf-8")
        self.assertNotIn("data/raw/private", text)
        self.assertNotIn("CIK0000123456", text)
        self.assertNotIn("123.45", text)

    def test_no_dummy_decision_ready_claim(self) -> None:
        result = self.run_payload()
        encoded = json.dumps(result.payload, sort_keys=True).lower()

        self.assertEqual(result.payload["readiness"]["decision"]["status"], "BLOCKED")
        self.assertNotIn('"decision_ready": true', encoded)
        self.assertFalse(result.payload["metadata"]["dummy_claims_included"])

    def test_sec_preflight_and_private_input_sections_are_present(self) -> None:
        result = self.run_payload()

        self.assertEqual(result.payload["sections"]["sec_preflight"][0]["value"], "USER_AGENT_MISSING")
        self.assertEqual(result.payload["sections"]["private_inputs"][0]["value"], "0")
        self.assertTrue(result.payload["guardrails"]["no_network"])

    def test_payload_display_fields_have_no_forbidden_terms(self) -> None:
        result = self.run_payload()
        encoded_sections = json.dumps(result.payload["sections"], sort_keys=True).upper()

        for term in FORBIDDEN_DISPLAY_TERMS:
            self.assertNotIn(term, encoded_sections)

    def test_outputs_are_written(self) -> None:
        self.run_payload()

        payload = json.loads(self.payload.read_text(encoding="utf-8"))
        self.assertEqual(payload["metadata"]["private_data_included"], False)
        self.assertIn("# Dashboard Readiness Payload", self.report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
