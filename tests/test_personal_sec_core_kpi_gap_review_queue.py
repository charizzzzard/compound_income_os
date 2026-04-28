from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_sec_core_kpi_gap_review_queue import QUEUE_FIELDS, SUMMARY_FIELDS, run_personal_sec_core_kpi_gap_review_queue


class PersonalSecCoreKpiGapReviewQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_gap_review_queue_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.impact = self.tmp / "impact.csv"
        self.summary = self.tmp / "impact_summary.csv"
        self.master = self.tmp / "applied_master.csv"
        self.queue = self.tmp / "processed" / "queue.csv"
        self.queue_summary = self.tmp / "processed" / "queue_summary.csv"
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

    def impact_row(self, **updates: str) -> dict[str, str]:
        row = {
            "ticker": "AAA",
            "isin": "US0000000001",
            "company_name": "Alpha Inc",
            "kpi_field": "gross_margin",
            "baseline_value": "",
            "evidence_applied_value": "",
            "value_changed": "False",
            "closure_status": "STILL_MISSING",
            "evidence_id": "",
            "evidence_confidence": "",
            "fiscal_year_end": "",
            "source_as_of_date": "",
            "source_forms": "",
            "stale_or_old_fiscal_year": "False",
            "stale_reason": "",
            "notes": "fixture",
        }
        row.update(updates)
        return row

    def write_inputs(self) -> None:
        self.write_csv(self.impact, list(self.impact_row().keys()), [self.impact_row()])
        self.write_csv(
            self.summary,
            ["no_score_change_confirmed", "no_network_confirmed", "raw_master_mutation_performed"],
            [{"no_score_change_confirmed": "True", "no_network_confirmed": "True", "raw_master_mutation_performed": "False"}],
        )
        self.write_csv(self.master, ["ticker", "isin", "company_name"], [{"ticker": "AAA", "isin": "US0000000001", "company_name": "Alpha Inc"}])

    def run_queue(self):
        return run_personal_sec_core_kpi_gap_review_queue(
            impact_input=self.impact,
            impact_summary_input=self.summary,
            evidence_applied_master=self.master,
            queue_output=self.queue,
            summary_output=self.queue_summary,
            report_output=self.report,
        )

    def test_selects_still_missing_rows_into_review_queue(self) -> None:
        result = self.run_queue()
        rows = self.read_csv(result.queue_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["closure_status"], "STILL_MISSING")

    def test_selects_stale_rows_into_review_queue(self) -> None:
        self.write_csv(
            self.impact,
            list(self.impact_row().keys()),
            [self.impact_row(closure_status="CLOSED_BY_SEC_DERIVED_KPI", evidence_applied_value="0.4", stale_or_old_fiscal_year="True", stale_reason="old")],
        )
        result = self.run_queue()
        rows = self.read_csv(result.queue_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["stale_or_old_fiscal_year"], "True")

    def test_classifies_stale_filled_values_as_stale_value_review(self) -> None:
        self.write_csv(
            self.impact,
            list(self.impact_row().keys()),
            [self.impact_row(closure_status="CLOSED_BY_SEC_DERIVED_KPI", evidence_applied_value="0.4", stale_or_old_fiscal_year="True", stale_reason="FY2018")],
        )
        rows = self.read_csv(self.run_queue().queue_path)
        self.assertEqual(rows[0]["review_bucket"], "STALE_VALUE_REVIEW")
        self.assertEqual(rows[0]["priority"], "HIGH")

    def test_classifies_missing_sec_sourceable_kpi_as_sec_refresh_candidate(self) -> None:
        rows = self.read_csv(self.run_queue().queue_path)
        self.assertEqual(rows[0]["review_bucket"], "SEC_REFRESH_CANDIDATE")

    def test_emits_deterministic_review_ids(self) -> None:
        self.write_csv(
            self.impact,
            list(self.impact_row().keys()),
            [
                self.impact_row(isin="US0000000002", kpi_field="revenue_cagr_5y"),
                self.impact_row(isin="US0000000001", kpi_field="gross_margin"),
            ],
        )
        rows = self.read_csv(self.run_queue().queue_path)
        self.assertEqual([row["review_id"] for row in rows], ["SEC_GAP_REVIEW_0001", "SEC_GAP_REVIEW_0002"])

    def test_writes_stable_csv_headers(self) -> None:
        result = self.run_queue()
        queue_rows = self.read_csv(result.queue_path)
        summary_rows = self.read_csv(result.summary_path)
        self.assertEqual(list(queue_rows[0].keys()), QUEUE_FIELDS)
        self.assertEqual(list(summary_rows[0].keys()), SUMMARY_FIELDS)

    def test_writes_summary_counts_correctly(self) -> None:
        self.write_csv(
            self.impact,
            list(self.impact_row().keys()),
            [
                self.impact_row(),
                self.impact_row(closure_status="CLOSED_BY_SEC_DERIVED_KPI", evidence_applied_value="0.4", stale_or_old_fiscal_year="True", stale_reason="old"),
            ],
        )
        summary = self.read_csv(self.run_queue().summary_path)[0]
        self.assertEqual(summary["total_review_rows"], "2")
        self.assertEqual(summary["still_missing_rows"], "1")
        self.assertEqual(summary["stale_value_rows"], "1")
        self.assertEqual(summary["sec_refresh_candidate_rows"], "1")
        self.assertEqual(summary["stale_value_review_rows"], "1")

    def test_no_score_monthly_watchlist_dashboard_artifacts_are_created(self) -> None:
        self.run_queue()
        names = {path.name for path in (self.tmp / "processed").iterdir()}
        self.assertNotIn("company_scores.csv", names)
        self.assertNotIn("monthly_buy_ranking.csv", names)
        self.assertNotIn("watchlist_ranked.csv", names)
        self.assertNotIn("dashboard_payload.json", names)

    def test_missing_required_input_fails_deterministically(self) -> None:
        self.impact.unlink()
        with self.assertRaisesRegex(RuntimeError, "MISSING_SEC_CORE_KPI_CLOSURE_IMPACT"):
            self.run_queue()


if __name__ == "__main__":
    unittest.main()
