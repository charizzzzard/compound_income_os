from __future__ import annotations

import csv
import json
import shutil
import unittest
from pathlib import Path

from src.personal_artifact_reconciliation import run_personal_artifact_reconciliation


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


class PersonalArtifactReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_artifact_reconciliation"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.scores = self.tmp / "scores.csv"
        self.score_audit = self.tmp / "score_audit.csv"
        self.kpi_tier = self.tmp / "kpi_tier.csv"
        self.missing_summary = self.tmp / "missing_summary.csv"
        self.missing_holdings = self.tmp / "missing_holdings.csv"
        self.delta_summary = self.tmp / "delta_summary.csv"
        self.delta_holdings = self.tmp / "delta_holdings.csv"
        self.monthly = self.tmp / "monthly.csv"
        self.monthly_action_summary = self.tmp / "monthly_action_summary.csv"
        self.watchlist = self.tmp / "watchlist.csv"
        self.used_inputs = self.tmp / "used_inputs.csv"
        self.manifest = self.tmp / "manifest.json"
        self.summary_output = self.tmp / "summary.csv"
        self.checks_output = self.tmp / "checks.csv"
        self.report_output = self.tmp / "report.md"

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_base_inputs(self, *, delta_review_count: str = "0", watchlist_path: str = "data/raw/sample_watchlist.csv") -> None:
        write_csv(
            self.scores,
            ["ticker", "isin", "data_quality_flag"],
            [
                {"ticker": "AAA", "isin": "US1", "data_quality_flag": "REVIEW"},
                {"ticker": "BBB", "isin": "US2", "data_quality_flag": "MISSING_DATA"},
            ],
        )
        write_csv(self.score_audit, ["ticker", "isin", "metric"], [{"ticker": "AAA", "isin": "US1", "metric": "quality_score"}])
        write_csv(
            self.kpi_tier,
            [
                "ticker",
                "isin",
                "company_name",
                "company_type_profile",
                "core_quality_data_status",
                "valuation_data_status",
                "dividend_fcf_data_status",
                "advanced_data_status",
                "resulting_monthly_action",
            ],
            [
                {
                    "ticker": "AAA",
                    "isin": "US1",
                    "company_name": "Alpha",
                    "company_type_profile": "STANDARD",
                    "core_quality_data_status": "PARTIAL",
                    "valuation_data_status": "MISSING",
                    "dividend_fcf_data_status": "MISSING",
                    "advanced_data_status": "MISSING",
                    "resulting_monthly_action": "REVIEW_CORE_DATA",
                }
            ],
        )
        write_csv(self.missing_summary, ["metric", "value", "notes"], [{"metric": "missing_required_kpi_total", "value": "1", "notes": ""}])
        write_csv(self.missing_holdings, ["ticker", "isin", "likely_blocker"], [{"ticker": "AAA", "isin": "US1", "likely_blocker": "SEC_KPI_MISSING"}])
        write_csv(
            self.delta_summary,
            ["metric", "value", "notes"],
            [
                {"metric": "score_data_quality__OK", "value": "0", "notes": ""},
                {"metric": "score_data_quality__REVIEW", "value": delta_review_count, "notes": ""},
                {"metric": "score_data_quality__MISSING_DATA", "value": "2", "notes": ""},
                {"metric": "score_data_quality__BLOCKED", "value": "0", "notes": ""},
                {"metric": "current_missing_required_kpi_total", "value": "1", "notes": ""},
            ],
        )
        write_csv(self.delta_holdings, ["ticker", "isin", "current_likely_blocker"], [{"ticker": "AAA", "isin": "US1", "current_likely_blocker": "still_missing_after_evidence"}])
        write_csv(
            self.monthly,
            ["rank", "ticker", "target_action", "allocation_status"],
            [{"rank": "1", "ticker": "AAA", "target_action": "DO_NOT_BUY", "allocation_status": "BLOCKED"}],
        )
        write_csv(
            self.watchlist,
            ["ticker", "status", "data_quality_flag"],
            [{"ticker": "AAA", "status": "REVIEW", "data_quality_flag": "MISSING_DATA"}],
        )
        write_csv(
            self.used_inputs,
            ["stage_name", "stage_status", "input_role", "input_path", "input_exists", "notes"],
            [
                {
                    "stage_name": "scoring",
                    "stage_status": "SUCCESS",
                    "input_role": "fundamentals_master",
                    "input_path": "data/processed/personal_fundamentals_master_evidence_applied.csv",
                    "input_exists": "True",
                    "notes": "fundamentals_source_mode=EVIDENCE_APPLIED",
                },
                {
                    "stage_name": "watchlist",
                    "stage_status": "SUCCESS",
                    "input_role": "watchlist_input",
                    "input_path": watchlist_path,
                    "input_exists": "True",
                    "notes": "fundamentals_source_mode=EVIDENCE_APPLIED",
                },
            ],
        )
        self.manifest.write_text(json.dumps({"inputs": {"use_evidence_applied_master": True}}), encoding="utf-8")

    def run_reconciliation(self):
        return run_personal_artifact_reconciliation(
            scores_input=str(self.scores),
            score_audit_input=str(self.score_audit),
            kpi_tier_input=str(self.kpi_tier),
            missing_kpi_summary_input=str(self.missing_summary),
            missing_kpi_holdings_input=str(self.missing_holdings),
            evidence_delta_summary_input=str(self.delta_summary),
            evidence_delta_holdings_input=str(self.delta_holdings),
            monthly_input=str(self.monthly),
            monthly_action_summary_input=str(self.monthly_action_summary),
            watchlist_input=str(self.watchlist),
            used_inputs_input=str(self.used_inputs),
            manifest_input=str(self.manifest),
            summary_output=str(self.summary_output),
            checks_output=str(self.checks_output),
            report_output=str(self.report_output),
        )

    def summary_value(self, metric: str) -> str:
        return {row["metric"]: row["value"] for row in read_csv(self.summary_output)}[metric]

    def check_row(self, check_id: str) -> dict[str, str]:
        return {row["check_id"]: row for row in read_csv(self.checks_output)}[check_id]

    def test_detects_score_delta_counter_drift(self) -> None:
        self.write_base_inputs(delta_review_count="0")
        self.run_reconciliation()

        row = self.check_row("score_vs_delta_data_quality")
        self.assertEqual(row["status"], "BLOCKED")
        self.assertIn("ARTIFACT_DRIFT", row["reason_codes"])
        self.assertEqual(self.summary_value("demo_readiness_status"), "BLOCKED")

    def test_detects_monthly_schema_drift_without_migration(self) -> None:
        self.write_base_inputs(delta_review_count="1")
        self.run_reconciliation()

        row = self.check_row("monthly_schema_contract")
        self.assertEqual(row["status"], "REVIEW")
        self.assertIn("MONTHLY_SCHEMA_DRIFT", row["reason_codes"])
        self.assertEqual(self.summary_value("monthly_has_target_action"), "True")
        self.assertEqual(self.summary_value("monthly_has_allocation_status"), "True")
        self.assertEqual(self.summary_value("monthly_has_monthly_action"), "False")

    def test_monthly_schema_drift_resolves_with_neutral_compatibility_summary(self) -> None:
        self.write_base_inputs(delta_review_count="1")
        write_csv(
            self.monthly_action_summary,
            ["metric", "value", "notes"],
            [
                {"metric": "monthly_action_compatibility_available", "value": "True", "notes": ""},
                {"metric": "monthly_schema_drift_resolved", "value": "True", "notes": ""},
                {"metric": "forbidden_monthly_action_values_total", "value": "0", "notes": ""},
                {"metric": "monthly_action__NOT_READY", "value": "1", "notes": ""},
            ],
        )
        self.run_reconciliation()

        row = self.check_row("monthly_schema_contract")
        self.assertEqual(row["status"], "PASS")
        self.assertNotIn("MONTHLY_SCHEMA_DRIFT", row["reason_codes"])
        self.assertEqual(self.summary_value("monthly_schema_drift_resolved"), "True")
        self.assertEqual(self.summary_value("monthly_action__NOT_READY"), "1")

    def test_sample_watchlist_blocks_readiness(self) -> None:
        self.write_base_inputs(delta_review_count="1")
        self.run_reconciliation()

        row = self.check_row("watchlist_demo_decision_readiness")
        self.assertEqual(row["status"], "BLOCKED")
        self.assertIn("WATCHLIST_SAMPLE_INPUT", row["reason_codes"])
        self.assertEqual(self.summary_value("decision_readiness_status"), "BLOCKED")

    def test_report_is_deterministic_and_sanitized(self) -> None:
        self.write_base_inputs(delta_review_count="1", watchlist_path="data/raw/private/fundamentals/watchlist.csv")
        self.run_reconciliation()

        report = self.report_output.read_text(encoding="utf-8")
        self.assertIn("<private_path>", report)
        self.assertNotIn("data/raw/private/fundamentals/watchlist.csv", report)
        self.assertEqual([row["check_id"] for row in read_csv(self.checks_output)], sorted(row["check_id"] for row in read_csv(self.checks_output)))


if __name__ == "__main__":
    unittest.main()
