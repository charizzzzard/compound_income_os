from __future__ import annotations

import unittest
from pathlib import Path

from src.build_portfolio_snapshot import build_portfolio_snapshot_report
from src.common import read_csv_rows
from src.portfolio_review import build_holdings_action_table


def base_positions() -> list[dict[str, str]]:
    return [
        {"ticker": "ADDX", "company_name": "Add Co", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "200", "weight_total_assets_pct": "2.0", "review_flag": "false"},
        {"ticker": "HOLDX", "company_name": "Hold Co", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "740", "weight_total_assets_pct": "7.4", "review_flag": "false"},
        {"ticker": "KPIX", "company_name": "KPI Gap Co", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "210", "weight_total_assets_pct": "2.1", "review_flag": "false"},
        {"ticker": "MISSX", "company_name": "No Match Co", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "220", "weight_total_assets_pct": "2.2", "review_flag": "false"},
        {"ticker": "REDX", "company_name": "Reduce Co", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "1000", "weight_total_assets_pct": "10.0", "review_flag": "false"},
    ]


def base_scores() -> list[dict[str, str]]:
    return [
        {"ticker": "ADDX", "company_name": "Add Co", "held_in_portfolio": "true", "current_weight_pct": "2.0", "business_score": "84", "valuation_score": "70", "buy_score": "78", "mandate_fit_score": "88", "classification": "HOLD", "data_quality_flag": "OK", "has_hard_risk_flag": "false"},
        {"ticker": "HOLDX", "company_name": "Hold Co", "held_in_portfolio": "true", "current_weight_pct": "7.4", "business_score": "85", "valuation_score": "68", "buy_score": "77", "mandate_fit_score": "90", "classification": "HOLD", "data_quality_flag": "OK", "has_hard_risk_flag": "false"},
        {"ticker": "KPIX", "company_name": "KPI Gap Co", "held_in_portfolio": "true", "current_weight_pct": "2.1", "business_score": "84", "valuation_score": "70", "buy_score": "78", "mandate_fit_score": "88", "classification": "HOLD", "data_quality_flag": "OK", "has_hard_risk_flag": "false"},
        {"ticker": "MISSX", "company_name": "No Match Co", "held_in_portfolio": "true", "current_weight_pct": "2.2", "business_score": "84", "valuation_score": "70", "buy_score": "78", "mandate_fit_score": "88", "classification": "HOLD", "data_quality_flag": "OK", "has_hard_risk_flag": "false"},
        {"ticker": "REDX", "company_name": "Reduce Co", "held_in_portfolio": "true", "current_weight_pct": "10.0", "business_score": "88", "valuation_score": "65", "buy_score": "76", "mandate_fit_score": "90", "classification": "HOLD", "data_quality_flag": "OK", "has_hard_risk_flag": "false"},
    ]


def coverage_rows() -> list[dict[str, str]]:
    return [
        {"ticker": "ADDX", "match_status": "PARTIAL", "match_method": "TICKER", "missing_required_kpis": "", "needs_research_flag": "True"},
        {"ticker": "HOLDX", "match_status": "REVIEW", "match_method": "COMPANY_NAME", "missing_required_kpis": "", "needs_research_flag": "False"},
        {"ticker": "KPIX", "match_status": "COVERED", "match_method": "ISIN", "missing_required_kpis": "roic|fcf_margin", "needs_research_flag": "False"},
        {"ticker": "MISSX", "match_status": "NO_MATCH", "match_method": "NO_MATCH", "missing_required_kpis": "", "needs_research_flag": "True"},
        {"ticker": "REDX", "match_status": "COVERED", "match_method": "ISIN", "missing_required_kpis": "normalized_fcf_yield_pct", "needs_research_flag": "False"},
    ]


class PortfolioReviewCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_paths: list[Path] = []

    def tearDown(self) -> None:
        for path in self.temp_paths:
            if path.exists():
                path.unlink()

    def _path(self, name: str) -> Path:
        path = Path("tests") / name
        self.temp_paths.append(path)
        return path

    def test_without_coverage_existing_actions_stay_unchanged(self) -> None:
        rows = build_holdings_action_table(base_positions(), base_scores())
        actions = {row["ticker"]: row["portfolio_action"] for row in rows}
        self.assertEqual(actions["ADDX"], "ADD")
        self.assertEqual(actions["HOLDX"], "HOLD")
        self.assertEqual(actions["REDX"], "REDUCE")

    def test_coverage_guardrail_changes_only_existing_actions_conservatively(self) -> None:
        rows = build_holdings_action_table(base_positions(), base_scores(), coverage_rows=coverage_rows())
        indexed = {row["ticker"]: row for row in rows}

        self.assertEqual(indexed["ADDX"]["portfolio_action"], "WATCH")
        self.assertIn("Fundamentals-Coverage-Guardrail", indexed["ADDX"]["portfolio_action_reason"])
        self.assertTrue(indexed["ADDX"]["review_flag"])

        self.assertEqual(indexed["HOLDX"]["portfolio_action"], "EXIT_REVIEW")
        self.assertIn("status=REVIEW", indexed["HOLDX"]["portfolio_action_reason"])

        self.assertEqual(indexed["KPIX"]["portfolio_action"], "WATCH")
        self.assertIn("missing_required=roic|fcf_margin", indexed["KPIX"]["portfolio_action_reason"])

        self.assertEqual(indexed["MISSX"]["portfolio_action"], "EXIT_REVIEW")
        self.assertIn("status=NO_MATCH", indexed["MISSX"]["portfolio_action_reason"])

        self.assertEqual(indexed["REDX"]["portfolio_action"], "REDUCE")
        self.assertIn("missing_required=normalized_fcf_yield_pct", indexed["REDX"]["portfolio_action_reason"])
        self.assertTrue(indexed["REDX"]["review_flag"])

    def test_incomplete_coverage_rows_are_rejected(self) -> None:
        bad_coverage = [{"ticker": "ADDX", "match_status": "PARTIAL", "needs_research_flag": "True"}]
        with self.assertRaisesRegex(ValueError, "holdings action coverage input missing required columns: .*match_method"):
            build_holdings_action_table(base_positions(), base_scores(), coverage_rows=bad_coverage)

    def test_portfolio_snapshot_action_output_uses_coverage_guardrail(self) -> None:
        report_path = self._path("_tmp_portfolio_review_coverage_guardrail.md")
        holdings_path = self._path("_tmp_holdings_action_coverage_guardrail.csv")
        build_portfolio_snapshot_report(
            positions_rows=base_positions()[:1],
            output_path=str(report_path),
            scores_rows=base_scores()[:1],
            holdings_output=str(holdings_path),
            coverage_rows=coverage_rows()[:1],
        )
        rows = read_csv_rows(holdings_path)
        self.assertEqual(rows[0]["portfolio_action"], "WATCH")
        self.assertEqual(rows[0]["review_flag"], "True")
        self.assertIn("Fundamentals-Coverage-Guardrail", rows[0]["portfolio_action_reason"])


if __name__ == "__main__":
    unittest.main()
