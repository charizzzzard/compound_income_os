from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_kpi_tier_coverage import build_kpi_tier_rows, run_kpi_tier_coverage


class PersonalKpiTierCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_kpi_tier_coverage_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_csv(self, path: Path, rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_builds_tier_rows_from_coverage_scores_and_monthly_outputs(self) -> None:
        rows = build_kpi_tier_rows(
            coverage_rows=[
                {
                    "matched_ticker": "ADYEN",
                    "matched_isin": "NL0012969182",
                    "matched_company_name": "Adyen",
                    "company_type_profile": "STANDARD",
                    "core_quality_data_status": "OK",
                    "valuation_data_status": "MISSING",
                    "dividend_fcf_data_status": "OK",
                    "advanced_data_status": "PARTIAL",
                    "missing_core_quality_kpis": "",
                    "missing_valuation_kpis": "normalized_fcf_yield_pct",
                    "missing_dividend_fcf_kpis": "",
                    "missing_advanced_optional_kpis": "buyback_yield",
                }
            ],
            score_rows=[
                {
                    "ticker": "ADYEN",
                    "isin": "NL0012969182",
                    "core_quality_data_status": "OK",
                    "valuation_data_status": "MISSING",
                    "dividend_fcf_data_status": "OK",
                    "advanced_data_status": "PARTIAL",
                    "data_quality_flag": "REVIEW",
                }
            ],
            monthly_rows=[{"ticker": "ADYEN", "isin": "NL0012969182", "target_action": "WAIT"}],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticker"], "ADYEN")
        self.assertEqual(rows[0]["resulting_score_data_quality_flag"], "REVIEW")
        self.assertEqual(rows[0]["resulting_monthly_action"], "WAIT")
        self.assertEqual(rows[0]["recommended_next_action"], "WAIT_VALUATION")

    def test_recommends_profile_specific_next_actions(self) -> None:
        rows = build_kpi_tier_rows(
            coverage_rows=[
                {"ticker": "JPM", "isin": "US46625H1005", "company_type_profile": "FINANCIAL"},
                {"ticker": "XYZ", "isin": "US0000000001", "company_type_profile": "OTHER"},
                {
                    "ticker": "CORE",
                    "isin": "US0000000002",
                    "company_type_profile": "STANDARD",
                    "core_quality_data_status": "MISSING",
                },
            ],
            score_rows=[],
            monthly_rows=[],
        )

        actions = {row["ticker"]: row["recommended_next_action"] for row in rows}
        self.assertEqual(actions["JPM"], "add financial-company KPI profile or keep separate from STANDARD scoring")
        self.assertEqual(actions["XYZ"], "keep excluded unless explicit profile model exists")
        self.assertEqual(actions["CORE"], "REVIEW_CORE_DATA")

    def test_run_writes_stable_csv_and_report(self) -> None:
        coverage = self.tmp / "coverage.csv"
        scores = self.tmp / "scores.csv"
        monthly = self.tmp / "monthly.csv"
        output = self.tmp / "tier.csv"
        report = self.tmp / "tier.md"
        self.write_csv(
            coverage,
            [
                {
                    "ticker": "MSFT",
                    "isin": "US5949181045",
                    "holding_name": "Microsoft",
                    "company_type_profile": "STANDARD",
                    "core_quality_data_status": "OK",
                    "valuation_data_status": "OK",
                    "dividend_fcf_data_status": "OK",
                    "advanced_data_status": "OK",
                }
            ],
        )
        self.write_csv(scores, [{"ticker": "MSFT", "isin": "US5949181045", "data_quality_flag": "OK"}])
        self.write_csv(monthly, [{"ticker": "MSFT", "isin": "US5949181045", "target_action": "READY"}])

        output_path, report_path, rows = run_kpi_tier_coverage(
            coverage_input=str(coverage),
            scores_input=str(scores),
            monthly_input=str(monthly),
            output=str(output),
            report_output=str(report),
        )

        self.assertEqual(output_path, output.resolve())
        self.assertEqual(report_path, report.resolve())
        self.assertEqual(rows[0]["recommended_next_action"], "OK")
        written = self.read_csv(output)
        self.assertEqual(written[0]["resulting_monthly_action"], "READY")
        self.assertIn("Personal KPI Tier Coverage", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
