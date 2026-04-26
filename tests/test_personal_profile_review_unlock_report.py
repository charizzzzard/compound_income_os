from __future__ import annotations

import csv
import shutil
import unittest
from pathlib import Path

from src.personal_profile_review_unlock_report import (
    HOLDING_FIELDS,
    SUMMARY_FIELDS,
    run_personal_profile_review_unlock_report,
)


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


class PersonalProfileReviewUnlockReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_profile_review_unlock_report"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)

        self.review = self.tmp / "review.csv"
        self.registry = self.tmp / "registry.csv"
        self.backlog = self.tmp / "backlog.csv"
        self.gap_summary = self.tmp / "gap_summary.csv"
        self.gap_diagnostics = self.tmp / "gap_diagnostics.csv"
        self.scores = self.tmp / "scores.csv"
        self.watchlist = self.tmp / "watchlist.csv"
        self.monthly = self.tmp / "monthly.csv"
        self.summary_output = self.tmp / "unlock_summary.csv"
        self.holdings_output = self.tmp / "unlock_holdings.csv"
        self.report_output = self.tmp / "unlock_report.md"

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_base_inputs(
        self,
        *,
        review_rows: list[dict[str, str]] | None = None,
        gap_rows: list[dict[str, str]] | None = None,
        monthly_rows: list[dict[str, str]] | None = None,
    ) -> None:
        write_csv(
            self.review,
            ["ticker", "isin", "company_name", "proposed_company_type_profile", "review_status"],
            review_rows
            or [
                {
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "company_name": "Alpha",
                    "proposed_company_type_profile": "STANDARD",
                    "review_status": "APPROVED",
                }
            ],
        )
        write_csv(
            self.registry,
            ["ticker", "isin", "company_name", "proposed_company_type_profile"],
            [{"ticker": "AAA", "isin": "US0000000001", "company_name": "Alpha", "proposed_company_type_profile": "STANDARD"}],
        )
        write_csv(
            self.backlog,
            ["ticker", "isin", "company_name", "backlog_reason"],
            [{"ticker": "BBB", "isin": "US0000000002", "company_name": "Beta", "backlog_reason": "manual review"}],
        )
        write_csv(
            self.gap_summary,
            ["summary_metric", "summary_value", "notes"],
            [{"summary_metric": "profile_review_input_status", "summary_value": "POPULATED", "notes": ""}],
        )
        write_csv(
            self.gap_diagnostics,
            [
                "ticker",
                "isin",
                "company_name",
                "asset_type",
                "company_type_profile",
                "current_data_quality_flag",
                "missing_required_kpis_under_current_profile",
                "profile_review_status",
                "quality_gap_type",
                "recommended_next_action",
            ],
            gap_rows
            or [
                {
                    "ticker": "AAA",
                    "isin": "US0000000001",
                    "company_name": "Alpha",
                    "asset_type": "STOCK",
                    "company_type_profile": "STANDARD",
                    "current_data_quality_flag": "OK",
                    "missing_required_kpis_under_current_profile": "",
                    "profile_review_status": "APPROVED",
                    "quality_gap_type": "COVERED",
                    "recommended_next_action": "",
                }
            ],
        )
        write_csv(
            self.scores,
            ["ticker", "isin", "company_name", "data_quality_flag"],
            [{"ticker": "AAA", "isin": "US0000000001", "company_name": "Alpha", "data_quality_flag": "OK"}],
        )
        write_csv(self.watchlist, ["ticker", "status"], [{"ticker": "AAA", "status": "SUCCESS"}])
        write_csv(
            self.monthly,
            ["rank", "ticker", "target_action"],
            monthly_rows or [{"rank": "1", "ticker": "AAA", "target_action": "BUY_CANDIDATE"}],
        )

    def run_report(self):
        return run_personal_profile_review_unlock_report(
            profile_review_input=str(self.review),
            profile_registry_input=str(self.registry),
            profile_backlog_input=str(self.backlog),
            gap_summary_input=str(self.gap_summary),
            gap_diagnostics_input=str(self.gap_diagnostics),
            scores_input=str(self.scores),
            watchlist_input=str(self.watchlist),
            monthly_input=str(self.monthly),
            summary_output=str(self.summary_output),
            holdings_output=str(self.holdings_output),
            report_output=str(self.report_output),
        )

    def summary_value(self, metric: str) -> str:
        rows = read_csv(self.summary_output)
        return {row["metric"]: row["value"] for row in rows}[metric]

    def test_counts_approved_profiles(self) -> None:
        self.write_base_inputs(
            review_rows=[
                {"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "proposed_company_type_profile": "STANDARD", "review_status": "APPROVED"},
                {"ticker": "BBB", "isin": "US2", "company_name": "Beta", "proposed_company_type_profile": "REIT", "review_status": "APPROVED"},
                {"ticker": "CCC", "isin": "US3", "company_name": "Gamma", "proposed_company_type_profile": "", "review_status": "REVIEW"},
            ]
        )
        self.run_report()

        self.assertEqual(self.summary_value("approved_profile_rows_total"), "2")
        self.assertEqual(self.summary_value("approved_profile__STANDARD"), "1")
        self.assertEqual(self.summary_value("approved_profile__REIT"), "1")
        self.assertEqual(self.summary_value("review_status__REVIEW"), "1")

    def test_marks_financial_and_other_separately(self) -> None:
        self.write_base_inputs(
            review_rows=[
                {"ticker": "FIN", "isin": "USF", "company_name": "Financial", "proposed_company_type_profile": "FINANCIAL", "review_status": "APPROVED"},
                {"ticker": "OTH", "isin": "USO", "company_name": "Other", "proposed_company_type_profile": "OTHER", "review_status": "APPROVED"},
            ],
            gap_rows=[
                {"ticker": "FIN", "isin": "USF", "company_name": "Financial", "asset_type": "STOCK", "company_type_profile": "FINANCIAL", "current_data_quality_flag": "REVIEW", "missing_required_kpis_under_current_profile": "", "profile_review_status": "APPROVED", "quality_gap_type": "COVERED", "recommended_next_action": ""},
                {"ticker": "OTH", "isin": "USO", "company_name": "Other", "asset_type": "STOCK", "company_type_profile": "OTHER", "current_data_quality_flag": "REVIEW", "missing_required_kpis_under_current_profile": "", "profile_review_status": "APPROVED", "quality_gap_type": "COVERED", "recommended_next_action": ""},
            ],
        )
        self.run_report()

        report = self.report_output.read_text(encoding="utf-8")
        self.assertIn("`FINANCIAL` = 1", report)
        self.assertIn("`OTHER` = 1", report)
        self.assertIn("financial-company KPI profile", report)
        self.assertIn("excluded from STANDARD scoring", report)

    def test_aggregates_gap_types(self) -> None:
        self.write_base_inputs(
            gap_rows=[
                {"ticker": "A", "isin": "US1", "company_name": "A", "asset_type": "STOCK", "company_type_profile": "", "current_data_quality_flag": "REVIEW", "missing_required_kpis_under_current_profile": "", "profile_review_status": "", "quality_gap_type": "PROFILE_REVIEW_MISSING", "recommended_next_action": ""},
                {"ticker": "B", "isin": "US2", "company_name": "B", "asset_type": "STOCK", "company_type_profile": "STANDARD", "current_data_quality_flag": "MISSING_DATA", "missing_required_kpis_under_current_profile": "revenue", "profile_review_status": "APPROVED", "quality_gap_type": "SEC_KPI_PARTIAL", "recommended_next_action": ""},
                {"ticker": "C", "isin": "US3", "company_name": "C", "asset_type": "STOCK", "company_type_profile": "", "current_data_quality_flag": "REVIEW", "missing_required_kpis_under_current_profile": "", "profile_review_status": "", "quality_gap_type": "NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE", "recommended_next_action": ""},
                {"ticker": "D", "isin": "US4", "company_name": "D", "asset_type": "ETF", "company_type_profile": "", "current_data_quality_flag": "REVIEW", "missing_required_kpis_under_current_profile": "", "profile_review_status": "", "quality_gap_type": "ETF_OR_NON_COMPANY_FUNDAMENTALS", "recommended_next_action": ""},
            ]
        )
        self.run_report()

        self.assertEqual(self.summary_value("quality_gap_type__PROFILE_REVIEW_MISSING"), "1")
        self.assertEqual(self.summary_value("remaining_blocker__MISSING_REQUIRED_KPI"), "1")
        self.assertEqual(self.summary_value("quality_gap_type__NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE"), "1")
        self.assertEqual(self.summary_value("quality_gap_type__ETF_OR_NON_COMPANY_FUNDAMENTALS"), "1")

    def test_aggregates_monthly_actions_when_file_exists(self) -> None:
        self.write_base_inputs(
            monthly_rows=[
                {"rank": "1", "ticker": "AAA", "target_action": "BUY_CANDIDATE"},
                {"rank": "2", "ticker": "BBB", "target_action": "HOLD_CASH"},
                {"rank": "3", "ticker": "CCC", "target_action": "DO_NOT_BUY"},
            ]
        )
        self.run_report()

        self.assertEqual(self.summary_value("monthly_action__BUY_CANDIDATE"), "1")
        self.assertEqual(self.summary_value("monthly_action__HOLD_CASH"), "1")
        self.assertEqual(self.summary_value("monthly_action__DO_NOT_BUY"), "1")

    def test_missing_optional_inputs_warn_without_crash(self) -> None:
        write_csv(
            self.review,
            ["ticker", "isin", "company_name", "proposed_company_type_profile", "review_status"],
            [{"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "proposed_company_type_profile": "STANDARD", "review_status": "APPROVED"}],
        )

        result = self.run_report()

        self.assertTrue(result.warnings)
        self.assertEqual(self.summary_value("gap_summary_status"), "MISSING")
        self.assertEqual(self.summary_value("monthly_ranking_status"), "MISSING")
        self.assertTrue(self.summary_output.exists())
        self.assertTrue(self.holdings_output.exists())
        self.assertTrue(self.report_output.exists())

    def test_output_holdings_are_deterministically_sorted(self) -> None:
        self.write_base_inputs(
            gap_rows=[
                {"ticker": "ZZZ", "isin": "US3", "company_name": "Zeta", "asset_type": "STOCK", "company_type_profile": "STANDARD", "current_data_quality_flag": "OK", "missing_required_kpis_under_current_profile": "", "profile_review_status": "APPROVED", "quality_gap_type": "COVERED", "recommended_next_action": ""},
                {"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "", "current_data_quality_flag": "REVIEW", "missing_required_kpis_under_current_profile": "", "profile_review_status": "", "quality_gap_type": "PROFILE_REVIEW_MISSING", "recommended_next_action": ""},
                {"ticker": "BBB", "isin": "US2", "company_name": "Beta", "asset_type": "ETF", "company_type_profile": "", "current_data_quality_flag": "REVIEW", "missing_required_kpis_under_current_profile": "", "profile_review_status": "", "quality_gap_type": "ETF_OR_NON_COMPANY_FUNDAMENTALS", "recommended_next_action": ""},
            ]
        )
        self.run_report()

        rows = read_csv(self.holdings_output)
        self.assertEqual(list(rows[0].keys()), HOLDING_FIELDS)
        self.assertEqual([row["ticker"] for row in rows], ["ZZZ", "BBB", "AAA"])

    def test_private_paths_are_not_written_to_report(self) -> None:
        self.write_base_inputs()
        private_missing_path = self.tmp / "data" / "raw" / "private" / "secret_map.csv"
        result = run_personal_profile_review_unlock_report(
            profile_review_input=str(self.review),
            profile_registry_input=str(private_missing_path),
            profile_backlog_input=str(self.backlog),
            gap_summary_input=str(self.gap_summary),
            gap_diagnostics_input=str(self.gap_diagnostics),
            scores_input=str(self.scores),
            watchlist_input=str(self.watchlist),
            monthly_input=str(self.monthly),
            summary_output=str(self.summary_output),
            holdings_output=str(self.holdings_output),
            report_output=str(self.report_output),
        )

        report = self.report_output.read_text(encoding="utf-8")
        self.assertIn("<private_path>", report)
        self.assertNotIn("data/raw/private", report.replace("\\", "/"))
        self.assertNotIn("secret_map", report)
        self.assertEqual(list(read_csv(self.summary_output)[0].keys()), SUMMARY_FIELDS)
        self.assertTrue(result.warnings)


if __name__ == "__main__":
    unittest.main()
