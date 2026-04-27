from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.handoff_zip_export import HANDOFF_ARTIFACT_FILES, HANDOFF_ARTIFACT_GLOBS
from src.personal_sec_core_refresh_impact import HOLDING_FIELDS, SUMMARY_FIELDS, run_personal_sec_core_refresh_impact


class PersonalSecCoreRefreshImpactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_refresh_impact_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.execution = self.tmp / "execution.csv"
        self.plan = self.tmp / "plan.csv"
        self.core = self.tmp / "core.csv"
        self.coverage = self.tmp / "coverage.csv"
        self.readiness = self.tmp / "readiness.csv"
        self.blockers = self.tmp / "blockers.csv"
        self.monthly = self.tmp / "monthly.csv"
        self.delta_summary = self.tmp / "delta_summary.csv"
        self.private_apply = self.tmp / "private_apply.csv"
        self.summary = self.tmp / "summary.csv"
        self.holdings = self.tmp / "holdings.csv"
        self.report = self.tmp / "report.md"
        self.write_base_inputs()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def write_metric_file(self, path: Path, rows: dict[str, str]) -> None:
        self.write_csv(path, ["metric", "value", "notes"], [{"metric": key, "value": value, "notes": ""} for key, value in rows.items()])

    def write_base_inputs(self) -> None:
        self.write_csv(
            self.execution,
            [
                "execution_status",
                "network_performed",
                "master_mutation_performed",
                "score_formula_mutation_performed",
            ],
            [
                {
                    "execution_status": "BLOCKED_NOT_EXECUTED",
                    "network_performed": "False",
                    "master_mutation_performed": "False",
                    "score_formula_mutation_performed": "False",
                }
            ],
        )
        self.write_csv(
            self.plan,
            ["ticker", "isin", "company_name", "missing_core_kpi_count"],
            [{"ticker": "AAA", "isin": "US0000000001", "company_name": "Alpha Inc", "missing_core_kpi_count": "2"}],
        )
        self.write_metric_file(self.core, {"review_rows_count": "1"})
        self.write_csv(
            self.coverage,
            [
                "ticker",
                "isin",
                "resulting_score_data_quality_flag",
                "resulting_monthly_action",
                "missing_core_quality_kpis",
            ],
            [
                {
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "resulting_score_data_quality_flag": "MISSING_DATA",
                    "resulting_monthly_action": "REVIEW_CORE_DATA",
                    "missing_core_quality_kpis": "revenue_cagr_5y; gross_margin",
                }
            ],
        )
        self.write_csv(
            self.readiness,
            ["readiness_scope", "readiness_status", "active_p0_blockers"],
            [{"readiness_scope": "DECISION", "readiness_status": "BLOCKED", "active_p0_blockers": "REVIEW_CORE_DATA"}],
        )
        self.write_csv(
            self.blockers,
            ["readiness_scope", "blocker_code", "blocker_status", "severity"],
            [{"readiness_scope": "DECISION", "blocker_code": "REVIEW_CORE_DATA", "blocker_status": "ACTIVE", "severity": "P0"}],
        )
        self.write_csv(self.monthly, ["ticker", "target_action"], [{"ticker": "AAA", "target_action": "REVIEW_CORE_DATA"}])
        self.write_metric_file(self.delta_summary, {"evidence_registry_rows_added": "0", "evidence_apply_rows_added": "0"})
        self.write_csv(
            self.private_apply,
            ["review_domain", "not_ready_rows_count"],
            [{"review_domain": "VALUATION", "not_ready_rows_count": "1"}],
        )

    def run_impact(self):
        return run_personal_sec_core_refresh_impact(
            execution_summary_input=str(self.execution),
            plan_input=str(self.plan),
            core_closure_summary_input=str(self.core),
            kpi_tier_coverage_input=str(self.coverage),
            readiness_summary_input=str(self.readiness),
            readiness_blockers_input=str(self.blockers),
            monthly_input=str(self.monthly),
            evidence_delta_summary_input=str(self.delta_summary),
            private_apply_summary_input=str(self.private_apply),
            impact_summary_output=str(self.summary),
            impact_holdings_output=str(self.holdings),
            report_output=str(self.report),
        )

    def test_blocked_run_writes_no_value_change_impact(self) -> None:
        result = self.run_impact()
        summary = result.summary_rows[0]
        holding = result.holding_rows[0]

        self.assertEqual(summary["execution_status"], "BLOCKED_NOT_EXECUTED")
        self.assertEqual(summary["no_value_changes_confirmed"], "True")
        self.assertEqual(summary["missing_core_kpi_count_before"], summary["missing_core_kpi_count_after"])
        self.assertEqual(holding["score_data_quality_flag_before"], holding["score_data_quality_flag_after"])

    def test_summary_and_holdings_have_stable_columns_without_value_changes(self) -> None:
        self.run_impact()
        summary_rows = self.read_csv(self.summary)
        holding_rows = self.read_csv(self.holdings)

        self.assertEqual(list(summary_rows[0].keys()), SUMMARY_FIELDS)
        self.assertEqual(list(holding_rows[0].keys()), HOLDING_FIELDS)

    def test_no_imputation_keeps_missing_values_missing_without_evidence(self) -> None:
        result = self.run_impact()
        summary = result.summary_rows[0]
        holding = result.holding_rows[0]

        self.assertEqual(summary["no_imputation_confirmed"], "True")
        self.assertEqual(holding["missing_core_kpi_count_before"], "2")
        self.assertEqual(holding["missing_core_kpi_count_after"], "2")

    def test_handoff_allowlist_contains_impact_artifacts(self) -> None:
        self.assertIn("data/processed/personal_sec_core_refresh_impact_summary.csv", HANDOFF_ARTIFACT_FILES)
        self.assertIn("data/processed/personal_sec_core_refresh_impact_holdings.csv", HANDOFF_ARTIFACT_FILES)
        self.assertIn("reports/*/personal_sec_core_refresh_impact_report.md", HANDOFF_ARTIFACT_GLOBS)


if __name__ == "__main__":
    unittest.main()
