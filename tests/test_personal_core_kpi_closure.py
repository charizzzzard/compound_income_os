from __future__ import annotations

import csv
import shutil
import unittest
from pathlib import Path

from src.personal_core_kpi_closure import run_personal_core_kpi_closure

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


class PersonalCoreKpiClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_core_kpi_closure"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.kpi_tier = self.tmp / "kpi_tier.csv"
        self.scores = self.tmp / "scores.csv"
        self.registry = self.tmp / "registry.csv"
        self.applied = self.tmp / "applied.csv"
        self.sec_scope = self.tmp / "sec_scope.csv"
        self.sec_identity = self.tmp / "sec_identity.csv"
        self.metrics = self.tmp / "metrics.json"
        self.queue = self.tmp / "queue.csv"
        self.summary = self.tmp / "summary.csv"
        self.report = self.tmp / "report.md"
        self.metrics.write_text(
            '{"kpis":{"revenue_cagr_5y":{"kpi_tier":"CORE_QUALITY_REQUIRED"},"gross_margin":{"kpi_tier":"CORE_QUALITY_REQUIRED"},"target_fcf_yield_pct":{"kpi_tier":"VALUATION_REQUIRED"}}}',
            encoding="utf-8",
        )
        write_csv(self.scores, ["ticker", "isin", "data_quality_flag"], [{"ticker": "AAA", "isin": "US1", "data_quality_flag": "REVIEW"}])
        write_csv(self.registry, ["ticker", "isin", "kpi_name"], [])
        write_csv(self.applied, ["ticker", "isin", "revenue_cagr_5y", "gross_margin"], [{"ticker": "AAA", "isin": "US1", "revenue_cagr_5y": "", "gross_margin": ""}])
        write_csv(self.sec_scope, ["original_ticker", "original_isin", "reviewed_enabled", "reviewed_cik"], [])
        write_csv(self.sec_identity, ["isin", "current_ticker", "reviewed_cik"], [])

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_kpi_rows(self, rows: list[dict[str, str]]) -> None:
        write_csv(
            self.kpi_tier,
            [
                "ticker",
                "isin",
                "company_name",
                "company_type_profile",
                "core_quality_data_status",
                "missing_core_quality_kpis",
                "resulting_monthly_action",
            ],
            rows,
        )

    def run_closure(self, **overrides):
        params = {
            "kpi_tier_input": str(self.kpi_tier),
            "scores_input": str(self.scores),
            "evidence_registry_input": str(self.registry),
            "evidence_applied_master_input": str(self.applied),
            "sec_scope_review_input": str(self.sec_scope),
            "sec_identity_apply_input": str(self.sec_identity),
            "metric_definitions_input": str(self.metrics),
            "queue_output": str(self.queue),
            "summary_output": str(self.summary),
            "report_output": str(self.report),
        }
        params.update(overrides)
        return run_personal_core_kpi_closure(**params)

    def standard_review_row(self) -> dict[str, str]:
        return {
            "ticker": "AAA",
            "isin": "US1",
            "company_name": "Alpha",
            "company_type_profile": "STANDARD",
            "core_quality_data_status": "MISSING",
            "missing_core_quality_kpis": "revenue_cagr_5y; gross_margin",
            "resulting_monthly_action": "REVIEW_CORE_DATA",
        }

    def summary_value(self, metric: str) -> str:
        return {row["metric"]: row["value"] for row in read_csv(self.summary)}[metric]

    def queue_row(self) -> dict[str, str]:
        return read_csv(self.queue)[0]

    def test_standard_review_core_data_row_is_queued(self) -> None:
        self.write_kpi_rows([self.standard_review_row()])
        self.run_closure()

        row = self.queue_row()
        self.assertEqual(row["core_kpi_closure_status"], "REVIEW")
        self.assertIn("REVIEW_CORE_DATA", row["reason_code"])
        self.assertIn("CORE_KPI_MISSING", row["reason_code"])
        self.assertEqual(self.summary_value("affected_standard_rows_count"), "1")

    def test_standard_row_with_sufficient_core_is_not_a_blocker_queue_row(self) -> None:
        ok_row = self.standard_review_row()
        ok_row["missing_core_quality_kpis"] = ""
        ok_row["resulting_monthly_action"] = "WAIT_VALUATION"
        self.write_kpi_rows([ok_row])
        self.run_closure()

        self.assertEqual(read_csv(self.queue), [])
        self.assertEqual(self.summary_value("queue_rows_count"), "0")

    def test_non_standard_row_is_not_applicable(self) -> None:
        row = self.standard_review_row()
        row["company_type_profile"] = "OTHER"
        self.write_kpi_rows([row])
        self.run_closure()

        self.assertEqual(read_csv(self.queue), [])
        self.assertEqual(self.summary_value("not_applicable_rows_count"), "1")
        self.assertIn("PROFILE_NOT_STANDARD", self.summary_value("reason_codes"))

    def test_evidence_registry_hint_requires_existing_evidence_review(self) -> None:
        self.write_kpi_rows([self.standard_review_row()])
        write_csv(self.registry, ["ticker", "isin", "kpi_name"], [{"ticker": "AAA", "isin": "US1", "kpi_name": "revenue_cagr_5y"}])
        self.run_closure()

        row = self.queue_row()
        self.assertEqual(row["recommended_closure_path"], "REVIEW_EXISTING_EVIDENCE")
        self.assertEqual(row["evidence_registry_status"], "PARTIAL_EVIDENCE")

    def test_sec_identity_structurally_present_is_sec_evidence_possible(self) -> None:
        self.write_kpi_rows([self.standard_review_row()])
        write_csv(self.sec_identity, ["isin", "current_ticker", "reviewed_cik"], [{"isin": "US1", "current_ticker": "AAA", "reviewed_cik": "0000001"}])
        self.run_closure()

        row = self.queue_row()
        self.assertEqual(row["sec_scope_status"], "SEC_ELIGIBLE")
        self.assertEqual(row["recommended_closure_path"], "SEC_EVIDENCE_POSSIBLE")

    def test_missing_sec_identity_and_evidence_requires_manual_evidence(self) -> None:
        self.write_kpi_rows([self.standard_review_row()])
        self.run_closure()

        row = self.queue_row()
        self.assertEqual(row["sec_scope_status"], "SEC_IDENTITY_MISSING")
        self.assertEqual(row["recommended_closure_path"], "MANUAL_EVIDENCE_REQUIRED")

    def test_missing_input_artifacts_create_empty_summary_without_crash(self) -> None:
        missing_path = self.tmp / "missing.csv"
        self.run_closure(kpi_tier_input=str(missing_path))

        self.assertEqual(read_csv(self.queue), [])
        self.assertEqual(self.summary_value("warnings_total"), "1")

    def test_report_does_not_dump_private_paths(self) -> None:
        self.write_kpi_rows([self.standard_review_row()])
        self.run_closure(evidence_registry_input="data/raw/private/fundamentals/evidence.csv")

        report = self.report.read_text(encoding="utf-8")
        self.assertIn("<private_path>", report)
        self.assertNotIn("data/raw/private/fundamentals/evidence.csv", report)

    def test_no_master_or_score_file_changes_are_performed(self) -> None:
        self.write_kpi_rows([self.standard_review_row()])
        score_before = self.scores.read_text(encoding="utf-8")
        applied_before = self.applied.read_text(encoding="utf-8")
        self.run_closure()

        self.assertEqual(self.scores.read_text(encoding="utf-8"), score_before)
        self.assertEqual(self.applied.read_text(encoding="utf-8"), applied_before)
        self.assertEqual(self.summary_value("no_value_changes_confirmed"), "True")


if __name__ == "__main__":
    unittest.main()
