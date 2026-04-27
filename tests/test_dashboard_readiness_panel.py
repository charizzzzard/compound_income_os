from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.common import read_csv_rows
from src.dashboard_readiness_panel import FORBIDDEN_DISPLAY_TERMS, run_dashboard_readiness_panel


class DashboardReadinessPanelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_dashboard_readiness_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.readiness = self.tmp / "readiness.csv"
        self.blockers = self.tmp / "blockers.csv"
        self.actions = self.tmp / "actions.csv"
        self.sec_preflight = self.tmp / "sec_preflight.csv"
        self.sec_plan = self.tmp / "sec_plan.csv"
        self.private_review = self.tmp / "private_review.csv"
        self.private_candidates = self.tmp / "private_candidates.csv"
        self.watchlist = self.tmp / "watchlist.csv"
        self.panel = self.tmp / "panel.csv"
        self.dashboard_blockers = self.tmp / "dashboard_blockers.csv"
        self.dashboard_actions = self.tmp / "dashboard_actions.csv"
        self.report = self.tmp / "report.md"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def write_inputs(self) -> None:
        self.write_csv(
            self.readiness,
            [
                "readiness_scope",
                "readiness_status",
                "active_p0_blockers",
                "active_p1_reviews",
                "active_p2_backlog",
                "resolved_blockers",
                "deferred_blockers",
                "primary_reason_codes",
                "evidence",
                "recommended_next_action",
            ],
            [
                {"readiness_scope": "DEMO", "readiness_status": "BLOCKED", "active_p0_blockers": "WATCHLIST_SAMPLE_INPUT", "active_p1_reviews": "", "active_p2_backlog": "", "resolved_blockers": "", "deferred_blockers": "", "primary_reason_codes": "WATCHLIST_SAMPLE_INPUT", "evidence": "personal_readiness_blockers.csv", "recommended_next_action": "Review blockers."},
                {"readiness_scope": "DECISION", "readiness_status": "BLOCKED", "active_p0_blockers": "MISSING_VALUATION_REQUIRED;REVIEW_CORE_DATA", "active_p1_reviews": "WATCHLIST_REVIEW_OR_MISSING_DATA", "active_p2_backlog": "", "resolved_blockers": "", "deferred_blockers": "", "primary_reason_codes": "MISSING_VALUATION_REQUIRED;REVIEW_CORE_DATA", "evidence": "personal_readiness_blockers.csv", "recommended_next_action": "Review blockers."},
                {"readiness_scope": "DASHBOARD", "readiness_status": "REVIEW", "active_p0_blockers": "", "active_p1_reviews": "WATCHLIST_REVIEW_OR_MISSING_DATA", "active_p2_backlog": "", "resolved_blockers": "MONTHLY_SCHEMA_DRIFT", "deferred_blockers": "", "primary_reason_codes": "WATCHLIST_REVIEW_OR_MISSING_DATA", "evidence": "personal_readiness_blockers.csv", "recommended_next_action": "Review dashboard evidence."},
                {"readiness_scope": "HANDOFF", "readiness_status": "REVIEW", "active_p0_blockers": "", "active_p1_reviews": "MISSING_METADATA", "active_p2_backlog": "", "resolved_blockers": "ARTIFACT_DRIFT", "deferred_blockers": "NO_IMPRINT_PRIVACY", "primary_reason_codes": "MISSING_METADATA", "evidence": "personal_readiness_blockers.csv", "recommended_next_action": "Review handoff evidence."},
            ],
        )
        self.write_csv(
            self.blockers,
            [
                "blocker_code",
                "blocker_status",
                "blocker_severity",
                "readiness_scope",
                "reason_codes",
                "source_artifact",
                "observed_value",
                "recommended_next_action",
                "requires_private_input",
                "requires_value_change",
                "requires_external_api",
            ],
            [
                {"blocker_code": "MISSING_VALUATION_REQUIRED", "blocker_status": "ACTIVE", "blocker_severity": "P0_BLOCKER", "readiness_scope": "DECISION", "reason_codes": "VALUATION_REQUIRED_MISSING", "source_artifact": "data/processed/personal_valuation_input_contract_summary.csv", "observed_value": "", "recommended_next_action": "Fill reviewed private valuation input or keep readiness blocked.", "requires_private_input": "yes", "requires_value_change": "yes_reviewed_input_only", "requires_external_api": "no"},
                {"blocker_code": "WATCHLIST_REVIEW_OR_MISSING_DATA", "blocker_status": "ACTIVE", "blocker_severity": "P1_REVIEW", "readiness_scope": "DECISION", "reason_codes": "WATCHLIST_REVIEW_OR_MISSING_DATA", "source_artifact": "data/processed/personal_watchlist_input_gate_summary.csv", "observed_value": "", "recommended_next_action": "Review watchlist status.", "requires_private_input": "yes", "requires_value_change": "yes_reviewed_input_only", "requires_external_api": "no"},
                {"blocker_code": "MONTHLY_SCHEMA_DRIFT", "blocker_status": "RESOLVED", "blocker_severity": "INFO", "readiness_scope": "DASHBOARD", "reason_codes": "MONTHLY_SCHEMA_DRIFT_RESOLVED", "source_artifact": "data/processed/personal_monthly_action_compatibility_summary.csv", "observed_value": "", "recommended_next_action": "Inspect resolved blocker.", "requires_private_input": "no", "requires_value_change": "no", "requires_external_api": "no"},
            ],
        )
        self.write_csv(
            self.actions,
            [
                "priority",
                "blocker_code",
                "readiness_scope",
                "recommended_next_action",
                "input_artifact",
                "output_artifact",
                "requires_private_input",
                "requires_value_change",
                "requires_external_api",
                "safe_next_patch",
                "reason",
            ],
            [
                {"priority": "P0_BLOCKER", "blocker_code": "MISSING_VALUATION_REQUIRED", "readiness_scope": "DECISION", "recommended_next_action": "Fill reviewed private valuation input or keep readiness blocked.", "input_artifact": "<private_path>", "output_artifact": "data/processed/personal_valuation_input_contract_summary.csv", "requires_private_input": "yes", "requires_value_change": "yes_reviewed_input_only", "requires_external_api": "no", "safe_next_patch": "VALUATION REVIEW INPUT APPLY / APPROVED ONLY / NO IMPUTATION", "reason": "INPUT_FILE_MISSING"},
                {"priority": "P0_BLOCKER", "blocker_code": "REVIEW_CORE_DATA", "readiness_scope": "DECISION", "recommended_next_action": "Review core KPI closure queue through SEC or manual evidence.", "input_artifact": "data/processed/personal_core_kpi_closure_summary.csv", "output_artifact": "data/processed/personal_core_kpi_closure_summary.csv", "requires_private_input": "maybe", "requires_value_change": "yes_reviewed_input_only", "requires_external_api": "no", "safe_next_patch": "CORE KPI REVIEW INPUT APPLY / APPROVED ONLY / NO IMPUTATION", "reason": "CORE_KPI_MISSING"},
            ],
        )
        self.write_csv(
            self.sec_preflight,
            [
                "plan_rows_count",
                "ready_for_explicit_network_run_count",
                "review_required_count",
                "blocked_count",
                "identity_map_present",
                "identity_schema_valid",
                "sec_user_agent_present",
                "network_gate_required_for_future_refresh",
                "network_performed",
                "fetch_performed",
                "raw_sec_snapshot_written",
                "evidence_apply_performed",
                "master_mutation_performed",
                "score_mutation_performed",
                "future_refresh_command_status",
                "reason_codes",
            ],
            [{"plan_rows_count": "4", "ready_for_explicit_network_run_count": "0", "review_required_count": "4", "blocked_count": "0", "identity_map_present": "True", "identity_schema_valid": "True", "sec_user_agent_present": "False", "network_gate_required_for_future_refresh": "True", "network_performed": "False", "fetch_performed": "False", "raw_sec_snapshot_written": "False", "evidence_apply_performed": "False", "master_mutation_performed": "False", "score_mutation_performed": "False", "future_refresh_command_status": "AVAILABLE", "reason_codes": "SEC_USER_AGENT_MISSING;NO_NETWORK_PERFORMED"}],
        )
        self.write_csv(
            self.sec_plan,
            ["affected_rows_count", "ready_for_explicit_sec_refresh_count", "identity_missing_count", "identity_review_count", "mapping_review_required_count", "not_ready_count", "network_performed", "value_fetch_performed", "evidence_apply_performed", "master_mutation_performed", "score_mutation_performed", "reason_codes"],
            [{"affected_rows_count": "4", "ready_for_explicit_sec_refresh_count": "4", "identity_missing_count": "0", "identity_review_count": "0", "mapping_review_required_count": "0", "not_ready_count": "0", "network_performed": "False", "value_fetch_performed": "False", "evidence_apply_performed": "False", "master_mutation_performed": "False", "score_mutation_performed": "False", "reason_codes": "READY_FOR_EXPLICIT_SEC_REFRESH"}],
        )
        self.write_csv(
            self.private_review,
            ["review_domain", "input_file_status", "queue_rows_count", "input_rows_count", "approved_rows_count", "review_rows_count", "missing_rows_count", "invalid_rows_count", "eligible_for_approved_apply_count", "no_imputation_confirmed", "private_values_sanitized", "reason_codes"],
            [
                {"review_domain": "VALUATION", "input_file_status": "MISSING", "queue_rows_count": "10", "input_rows_count": "0", "approved_rows_count": "0", "review_rows_count": "0", "missing_rows_count": "10", "invalid_rows_count": "0", "eligible_for_approved_apply_count": "0", "no_imputation_confirmed": "True", "private_values_sanitized": "True", "reason_codes": "INPUT_FILE_MISSING"},
                {"review_domain": "DIVIDEND_FCF", "input_file_status": "MISSING", "queue_rows_count": "10", "input_rows_count": "0", "approved_rows_count": "0", "review_rows_count": "0", "missing_rows_count": "10", "invalid_rows_count": "0", "eligible_for_approved_apply_count": "0", "no_imputation_confirmed": "True", "private_values_sanitized": "True", "reason_codes": "INPUT_FILE_MISSING"},
            ],
        )
        self.write_csv(
            self.private_candidates,
            ["review_domain", "input_file_status", "review_rows_count", "approved_rows_count", "candidate_rows_count", "candidate_fields_count", "not_ready_rows_count", "invalid_rows_count", "private_candidate_file_created", "private_values_in_public_outputs", "master_mutation_performed", "score_mutation_performed", "no_imputation_confirmed", "reason_codes"],
            [
                {"review_domain": "VALUATION", "input_file_status": "MISSING", "review_rows_count": "10", "approved_rows_count": "0", "candidate_rows_count": "0", "candidate_fields_count": "0", "not_ready_rows_count": "10", "invalid_rows_count": "0", "private_candidate_file_created": "False", "private_values_in_public_outputs": "False", "master_mutation_performed": "False", "score_mutation_performed": "False", "no_imputation_confirmed": "True", "reason_codes": "NO_APPROVED_INPUTS"},
                {"review_domain": "DIVIDEND_FCF", "input_file_status": "MISSING", "review_rows_count": "10", "approved_rows_count": "0", "candidate_rows_count": "0", "candidate_fields_count": "0", "not_ready_rows_count": "10", "invalid_rows_count": "0", "private_candidate_file_created": "False", "private_values_in_public_outputs": "False", "master_mutation_performed": "False", "score_mutation_performed": "False", "no_imputation_confirmed": "True", "reason_codes": "NO_APPROVED_INPUTS"},
            ],
        )
        self.write_csv(
            self.watchlist,
            ["metric", "value", "notes"],
            [
                {"metric": "watchlist_input_status", "value": "SAMPLE_DEMO_ONLY", "notes": ""},
                {"metric": "watchlist_data_status", "value": "MISSING_DATA", "notes": ""},
                {"metric": "watchlist_readiness_status", "value": "BLOCKED", "notes": ""},
                {"metric": "watchlist_reason_codes", "value": "WATCHLIST_SAMPLE_INPUT;WATCHLIST_REVIEW_OR_MISSING_DATA", "notes": ""},
            ],
        )

    def run_panel(self, *, missing: bool = False):
        if not missing:
            self.write_inputs()
        return run_dashboard_readiness_panel(
            readiness_summary_input=str(self.readiness),
            readiness_blockers_input=str(self.blockers),
            readiness_next_actions_input=str(self.actions),
            sec_preflight_summary_input=str(self.sec_preflight),
            sec_plan_summary_input=str(self.sec_plan),
            private_input_review_summary_input=str(self.private_review),
            private_apply_candidates_summary_input=str(self.private_candidates),
            watchlist_gate_summary_input=str(self.watchlist),
            panel_output=str(self.panel),
            blockers_output=str(self.dashboard_blockers),
            next_actions_output=str(self.dashboard_actions),
            report_output=str(self.report),
        )

    def test_readiness_overview_preserves_blocked_and_review_statuses(self) -> None:
        result = self.run_panel()
        panel = {row["metric_name"]: row for row in result.panel_rows}

        self.assertEqual(panel["demo_readiness"]["metric_value"], "BLOCKED")
        self.assertEqual(panel["decision_readiness"]["metric_value"], "BLOCKED")
        self.assertEqual(panel["dashboard_readiness"]["metric_value"], "REVIEW")
        self.assertEqual(panel["handoff_readiness"]["metric_value"], "REVIEW")

    def test_p0_blockers_are_shown_on_dashboard(self) -> None:
        result = self.run_panel()
        p0 = [row for row in result.blocker_rows if row["blocker_severity"] == "P0_BLOCKER"]

        self.assertTrue(p0)
        self.assertTrue(all(row["show_on_dashboard"] == "yes" for row in p0))

    def test_resolved_monthly_schema_is_not_active_p0(self) -> None:
        result = self.run_panel()
        rows = [row for row in result.blocker_rows if row["blocker_code"] == "MONTHLY_SCHEMA_DRIFT"]

        self.assertEqual(rows[0]["blocker_status"], "RESOLVED")
        self.assertNotEqual(rows[0]["blocker_severity"], "P0_BLOCKER")

    def test_sec_preflight_user_agent_missing_is_review_without_network_claim(self) -> None:
        result = self.run_panel()
        panel = {row["metric_name"]: row for row in result.panel_rows}

        self.assertEqual(panel["sec_preflight_status"]["status"], "REVIEW")
        self.assertEqual(panel["sec_preflight_status"]["metric_value"], "USER_AGENT_MISSING")
        self.assertNotIn("fetch completed", self.report.read_text(encoding="utf-8").lower())

    def test_private_inputs_zero_candidates_create_safe_cta(self) -> None:
        result = self.run_panel()
        actions = {row["blocker_code"]: row for row in result.next_action_rows}
        panel = {row["metric_name"]: row for row in result.panel_rows}

        self.assertEqual(panel["valuation_candidate_rows"]["metric_value"], "0")
        self.assertEqual(actions["MISSING_VALUATION_REQUIRED"]["dashboard_cta_label"], "Review private valuation inputs")

    def test_missing_inputs_are_not_available_without_crash(self) -> None:
        result = self.run_panel(missing=True)
        panel = {row["metric_name"]: row for row in result.panel_rows}

        self.assertEqual(panel["demo_readiness"]["metric_value"], "NOT_AVAILABLE")
        self.assertTrue(result.warnings)
        self.assertTrue(self.panel.exists())

    def test_advice_language_guardrail_for_display_fields(self) -> None:
        result = self.run_panel()
        rows = result.panel_rows + result.blocker_rows + result.next_action_rows
        display_fields = ("display_label", "display_hint", "safe_cta", "display_title", "display_description", "safe_next_action", "action_title", "action_description", "dashboard_cta_label")

        for row in rows:
            text = " ".join(str(row.get(field, "")) for field in display_fields).upper()
            for term in FORBIDDEN_DISPLAY_TERMS:
                self.assertNotIn(term, text)

    def test_report_sanitizes_private_data(self) -> None:
        result = self.run_panel()
        text = self.report.read_text(encoding="utf-8")

        self.assertNotIn("data/raw/private", text)
        self.assertNotIn("CIK000", text)
        self.assertNotIn("1234567890", text)
        self.assertTrue(result.panel_rows)

    def test_outputs_are_written(self) -> None:
        self.run_panel()

        self.assertTrue(read_csv_rows(self.panel))
        self.assertTrue(read_csv_rows(self.dashboard_blockers))
        self.assertTrue(read_csv_rows(self.dashboard_actions))
        self.assertIn("# Dashboard Readiness Panel", self.report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
