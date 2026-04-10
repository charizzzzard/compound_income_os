from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path

from src.build_portfolio_snapshot import build_portfolio_snapshot_report
from src.import_broker import build_positions_snapshot
from src.normalize_positions import normalize_position_row
from src.portfolio_review import build_holdings_action_table


class RealPortfolioOnboardingTests(unittest.TestCase):
    def test_real_alias_mapping_and_cash_detection_work(self) -> None:
        rows = [
            {
                "portfolio_date": "2026-04-10",
                "source_name": "manual_real_depot",
                "instrument": "Vanguard FTSE All-World UCITS ETF",
                "symbol": "VWCE",
                "isin": "IE00BK5BQT80",
                "shares": "3",
                "current_value": "360",
                "purchase_price": "110",
                "current_price": "120",
                "currency": "EUR",
                "category": "ETF",
                "sector": "ETF",
                "country": "Global",
            },
            {
                "portfolio_date": "2026-04-10",
                "source_name": "manual_real_depot",
                "position_type": "cash",
                "cash": "2500",
                "currency": "EUR",
            },
        ]
        snapshot = build_positions_snapshot(rows, mode="real", source_name="manual_real_depot")
        vwce = next(row for row in snapshot if row["ticker"] == "VWCE")
        cash = next(row for row in snapshot if row["asset_type"] == "CASH")
        self.assertEqual(vwce["portfolio_date"], "2026-04-10")
        self.assertEqual(vwce["source_name"], "manual_real_depot")
        self.assertEqual(vwce["current_price"], 120.0)
        self.assertEqual(vwce["avg_cost"], 110.0)
        self.assertEqual(vwce["market_value_eur"], 360.0)
        self.assertEqual(vwce["sleeve"], "CORE_ETF")
        self.assertEqual(cash["ticker"], "EUR-CASH")
        self.assertEqual(cash["market_value_eur"], 2500.0)
        self.assertEqual(cash["mandate_fit"], "CASH_RESERVE")

    def test_unknown_real_row_is_flagged_for_review(self) -> None:
        normalized = normalize_position_row(
            {
                "instrument": "Legacy Spin-Off Certificate",
                "isin": "XS1234567890",
                "shares": "1",
                "current_value": "75",
                "purchase_price": "200",
                "current_price": "75",
                "currency": "EUR",
                "category": "certificate",
                "position_type": "other",
            },
            mode="real",
            source_name="manual_real_depot",
        )
        assert normalized is not None
        self.assertEqual(normalized["ticker"], "XS1234567890")
        self.assertEqual(normalized["asset_type"], "OTHER")
        self.assertEqual(normalized["sleeve"], "NON_CORE")
        self.assertTrue(normalized["review_flag"])
        self.assertIn(normalized["data_quality_flag"], {"REVIEW", "MISSING_DATA"})

    def test_portfolio_action_rules_cover_core_outcomes(self) -> None:
        positions_rows = [
            {"ticker": "ADDX", "company_name": "Add Co", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "200", "weight_total_assets_pct": "2.0", "review_flag": "false"},
            {"ticker": "HOLDX", "company_name": "Hold Co", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "740", "weight_total_assets_pct": "7.4", "review_flag": "false"},
            {"ticker": "WATCHX", "company_name": "Watch Co", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "250", "weight_total_assets_pct": "2.5", "review_flag": "false"},
            {"ticker": "REDX", "company_name": "Reduce Co", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "1000", "weight_total_assets_pct": "10.0", "review_flag": "false"},
            {"ticker": "EXITX", "company_name": "Exit Co", "asset_type": "OTHER", "sleeve": "NON_CORE", "market_value_eur": "80", "weight_total_assets_pct": "0.8", "review_flag": "true"},
        ]
        score_rows = [
            {"ticker": "ADDX", "company_name": "Add Co", "held_in_portfolio": "true", "current_weight_pct": "2.0", "business_score": "84", "valuation_score": "70", "buy_score": "78", "mandate_fit_score": "88", "classification": "HOLD", "data_quality_flag": "OK", "has_hard_risk_flag": "false"},
            {"ticker": "HOLDX", "company_name": "Hold Co", "held_in_portfolio": "true", "current_weight_pct": "7.4", "business_score": "85", "valuation_score": "68", "buy_score": "77", "mandate_fit_score": "90", "classification": "HOLD", "data_quality_flag": "OK", "has_hard_risk_flag": "false"},
            {"ticker": "WATCHX", "company_name": "Watch Co", "held_in_portfolio": "true", "current_weight_pct": "2.5", "business_score": "82", "valuation_score": "55", "buy_score": "70", "mandate_fit_score": "78", "classification": "HOLD", "data_quality_flag": "OK", "has_hard_risk_flag": "false"},
            {"ticker": "REDX", "company_name": "Reduce Co", "held_in_portfolio": "true", "current_weight_pct": "10.0", "business_score": "88", "valuation_score": "65", "buy_score": "76", "mandate_fit_score": "90", "classification": "REDUCE", "data_quality_flag": "OK", "has_hard_risk_flag": "false"},
            {"ticker": "EXITX", "company_name": "Exit Co", "held_in_portfolio": "true", "current_weight_pct": "0.8", "business_score": "20", "valuation_score": "20", "buy_score": "20", "mandate_fit_score": "10", "classification": "EXIT_REVIEW", "data_quality_flag": "MISSING_DATA", "has_hard_risk_flag": "true"},
        ]
        table = build_holdings_action_table(positions_rows, score_rows)
        actions = {row["ticker"]: row["portfolio_action"] for row in table}
        self.assertEqual(actions["ADDX"], "ADD")
        self.assertEqual(actions["HOLDX"], "HOLD")
        self.assertEqual(actions["WATCHX"], "WATCH")
        self.assertEqual(actions["REDX"], "REDUCE")
        self.assertEqual(actions["EXITX"], "EXIT_REVIEW")

    def test_portfolio_review_rejects_duplicate_score_tickers(self) -> None:
        positions_rows = [
            {"ticker": "AAPL", "company_name": "Apple", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "100", "weight_total_assets_pct": "10.0", "review_flag": "false"},
        ]
        score_rows = [
            {"ticker": "AAPL", "company_name": "Apple", "held_in_portfolio": "true", "current_weight_pct": "10.0", "business_score": "80", "valuation_score": "70", "buy_score": "75", "classification": "HOLD", "data_quality_flag": "OK"},
            {"ticker": "aapl", "company_name": "Apple duplicate", "held_in_portfolio": "true", "current_weight_pct": "10.0", "business_score": "10", "valuation_score": "10", "buy_score": "10", "classification": "EXIT_REVIEW", "data_quality_flag": "MISSING_DATA"},
        ]
        with self.assertRaisesRegex(ValueError, "holdings action scores input contains duplicate tickers: AAPL"):
            build_holdings_action_table(positions_rows, score_rows)

    def test_portfolio_review_rejects_blank_score_ticker(self) -> None:
        positions_rows = [
            {"ticker": "AAPL", "company_name": "Apple", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "100", "weight_total_assets_pct": "10.0", "review_flag": "false"},
        ]
        score_rows = [
            {"ticker": "   ", "company_name": "Blank", "held_in_portfolio": "true", "current_weight_pct": "10.0", "business_score": "80", "valuation_score": "70", "buy_score": "75", "classification": "HOLD", "data_quality_flag": "OK"},
        ]
        with self.assertRaisesRegex(ValueError, "holdings action scores input row 2 has blank required field\\(s\\): ticker"):
            build_holdings_action_table(positions_rows, score_rows)

    def test_exit_review_priority_over_reduce_for_hard_review_case(self) -> None:
        positions_rows = [
            {"ticker": "RISKX", "company_name": "Risk Co", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "1500", "weight_total_assets_pct": "15.0", "review_flag": "false"},
        ]
        score_rows = [
            {"ticker": "RISKX", "company_name": "Risk Co", "held_in_portfolio": "true", "current_weight_pct": "15.0", "business_score": "20", "valuation_score": "20", "buy_score": "20", "mandate_fit_score": "10", "classification": "EXIT_REVIEW", "data_quality_flag": "MISSING_DATA", "has_hard_risk_flag": "true"},
        ]
        table = build_holdings_action_table(positions_rows, score_rows)
        self.assertEqual(table[0]["portfolio_action"], "EXIT_REVIEW")

    def test_normal_overweight_case_remains_reduce(self) -> None:
        positions_rows = [
            {"ticker": "REDX", "company_name": "Reduce Co", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "1000", "weight_total_assets_pct": "10.0", "review_flag": "false"},
        ]
        score_rows = [
            {"ticker": "REDX", "company_name": "Reduce Co", "held_in_portfolio": "true", "current_weight_pct": "10.0", "business_score": "88", "valuation_score": "65", "buy_score": "76", "mandate_fit_score": "90", "classification": "HOLD", "data_quality_flag": "OK", "has_hard_risk_flag": "false"},
        ]
        table = build_holdings_action_table(positions_rows, score_rows)
        self.assertEqual(table[0]["portfolio_action"], "REDUCE")

    def test_real_review_report_and_action_csv_are_generated(self) -> None:
        positions_rows = [
            {"ticker": "VWCE", "company_name": "Core ETF", "asset_type": "ETF", "sleeve": "CORE_ETF", "market_value_eur": "360", "weight_total_assets_pct": "12.0", "review_flag": "false"},
            {"ticker": "WKHS", "company_name": "Workhorse", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "89.65", "weight_total_assets_pct": "3.0", "review_flag": "true"},
            {"ticker": "EUR-CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "market_value_eur": "2500", "weight_total_assets_pct": "85.0", "review_flag": "false"},
        ]
        score_rows = [
            {"ticker": "VWCE", "company_name": "Core ETF", "held_in_portfolio": "true", "current_weight_pct": "12.0", "business_score": "78", "valuation_score": "67", "buy_score": "74", "mandate_fit_score": "95", "classification": "HOLD", "data_quality_flag": "OK", "has_hard_risk_flag": "false"},
            {"ticker": "WKHS", "company_name": "Workhorse", "held_in_portfolio": "true", "current_weight_pct": "3.0", "business_score": "5", "valuation_score": "35", "buy_score": "19", "mandate_fit_score": "5", "classification": "EXIT_REVIEW", "data_quality_flag": "MISSING_DATA", "has_hard_risk_flag": "true"},
            {"ticker": "EUR-CASH", "company_name": "Cash", "held_in_portfolio": "true", "current_weight_pct": "85.0", "business_score": "0", "valuation_score": "0", "buy_score": "0", "mandate_fit_score": "0", "classification": "HOLD", "data_quality_flag": "OK", "has_hard_risk_flag": "false"},
        ]
        report_path = Path("tests") / "_tmp_real_portfolio_review.md"
        holdings_path = Path("tests") / "_tmp_holdings_action_table.csv"
        try:
            build_portfolio_snapshot_report(
                positions_rows=positions_rows,
                output_path=str(report_path),
                scores_rows=score_rows,
                holdings_output=str(holdings_path),
            )
            report_text = report_path.read_text(encoding="utf-8")
            holdings_text = holdings_path.read_text(encoding="utf-8")
            self.assertIn("## Operatives Bestandsrating", report_text)
            self.assertIn("ACTION=EXIT_REVIEW", report_text)
            self.assertIn("portfolio_action", holdings_text)
            self.assertIn("EXIT_REVIEW", holdings_text)
        finally:
            if report_path.exists():
                report_path.unlink()
            if holdings_path.exists():
                holdings_path.unlink()

    def test_portfolio_snapshot_cli_rejects_duplicate_score_tickers(self) -> None:
        positions_path = Path("tests") / "_tmp_snapshot_positions.csv"
        scores_path = Path("tests") / "_tmp_snapshot_scores.csv"
        output_path = Path("tests") / "_tmp_snapshot_report.md"
        try:
            with positions_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["ticker", "company_name", "sleeve", "market_value_eur", "weight_total_assets_pct", "asset_type", "sector"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "ticker": "AAPL",
                        "company_name": "Apple",
                        "sleeve": "SINGLE_STOCK",
                        "market_value_eur": "100",
                        "weight_total_assets_pct": "10.0",
                        "asset_type": "STOCK",
                        "sector": "Technology",
                    }
                )
            with scores_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["ticker"])
                writer.writeheader()
                writer.writerow({"ticker": "AAPL"})
                writer.writerow({"ticker": "aapl"})

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.build_portfolio_snapshot",
                    "--positions",
                    str(positions_path),
                    "--scores",
                    str(scores_path),
                    "--output",
                    str(output_path),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("scores CSV", f"{result.stdout}\n{result.stderr}")
            self.assertIn("duplicate tickers: AAPL", f"{result.stdout}\n{result.stderr}")
            self.assertFalse(output_path.exists())
        finally:
            for path in [positions_path, scores_path, output_path]:
                if path.exists():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()
