from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path

from src.monthly_ranking_engine import build_monthly_ranking
from src.savings_plan_registry import REGISTRY_FIELDS
from src.scoring_engine import build_fundamentals_index
from src.watchlist_engine import build_watchlist_ranked, build_watchlist_report, score_index


class WatchlistEngineTests(unittest.TestCase):
    def test_build_watchlist_ranked_parses_robust_numeric_formats(self) -> None:
        watchlist_rows = [
            {
                "ticker": "AAA",
                "company_name": "Alpha",
                "sector": "Technology",
                "country": "USA",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "mandate_fit": "90",
                "thesis_summary": "Quality compounder",
                "main_risks": "valuation",
            }
        ]
        score_rows = [
            {
                "ticker": "AAA",
                "company_name": "Alpha",
                "sector": "Technology",
                "country": "USA",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "business_score": "80,5",
                "valuation_score": "65,2",
                "buy_score": "74,1",
                "fair_value_estimate": "1.234,56",
                "margin_of_safety_pct": "12,5",
                "valuation_comment": "Attraktiv bewertet.",
                "mandate_fit_score": "90,0",
                "classification": "BUY_CANDIDATE",
                "data_quality_flag": "OK",
            }
        ]
        ranked = build_watchlist_ranked(watchlist_rows, score_rows)
        self.assertEqual(ranked[0]["status"], "QUALITY_COMPOUNDER_CANDIDATE")
        self.assertEqual(ranked[0]["business_score"], 80.5)
        self.assertEqual(ranked[0]["fair_value_estimate"], 1234.56)
        self.assertEqual(ranked[0]["margin_of_safety_pct"], 12.5)
        self.assertEqual(ranked[0]["mandate_fit"], "Hoch (90.0/100)")
        self.assertIn("Mandats-Fit", ranked[0]["mandate_fit_comment"])

    def test_watchlist_and_monthly_ranking_block_missing_data_consistently(self) -> None:
        watchlist_rows = [
            {
                "ticker": "AAA",
                "company_name": "Alpha",
                "sector": "Technology",
                "country": "USA",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "mandate_fit": "90",
                "thesis_summary": "Qualitativ stark",
                "main_risks": "Daten fehlen",
            }
        ]
        score_rows = [
            {
                "ticker": "AAA",
                "company_name": "Alpha",
                "sector": "Technology",
                "country": "USA",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "business_score": "82",
                "valuation_score": "68",
                "buy_score": "76",
                "fair_value_estimate": "120",
                "margin_of_safety_pct": "10",
                "valuation_comment": "Bewertungsinputs fehlen; Fair Value bleibt konservativ angesetzt.",
                "mandate_fit_score": "90",
                "classification": "BUY_CANDIDATE",
                "data_quality_flag": "MISSING_DATA",
                "has_hard_risk_flag": "false",
                "held_in_portfolio": "false",
            }
        ]
        ranked = build_watchlist_ranked(watchlist_rows, score_rows)
        self.assertEqual(ranked[0]["status"], "REVIEW")

        registry_path = Path("tests") / "_tmp_watchlist_savings_plan_registry.csv"
        try:
            with registry_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=REGISTRY_FIELDS, lineterminator="\n")
                writer.writeheader()

            ranking, _ = build_monthly_ranking(
                positions_rows=[
                    {
                        "ticker": "EUR-CASH",
                        "company_name": "Cash",
                        "asset_type": "CASH",
                        "sleeve": "CASH",
                        "sector": "Cash",
                        "market_value_eur": "5000",
                    }
                ],
                score_rows=score_rows,
                watchlist_rows=ranked,
                savings_plan_registry_path=str(registry_path),
            )
            aaa_row = next(row for row in ranking if row["ticker"] == "AAA")
            self.assertEqual(aaa_row["target_action"], "DO_NOT_BUY")
            self.assertEqual(aaa_row["allocation_status"], "NOT_ELIGIBLE")
        finally:
            if registry_path.exists():
                registry_path.unlink()

    def test_duplicate_score_tickers_raise_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "scores input contains duplicate tickers: AAA"):
            score_index([{"ticker": "AAA"}, {"ticker": "AAA"}], "scores input")

    def test_watchlist_lookup_uses_case_insensitive_ticker_identity(self) -> None:
        ranked = build_watchlist_ranked(
            [{"ticker": "aapl", "company_name": "Apple"}],
            [
                {
                    "ticker": "AAPL",
                    "company_name": "Apple",
                    "business_score": "80",
                    "valuation_score": "65",
                    "buy_score": "75",
                    "fair_value_estimate": "100",
                    "margin_of_safety_pct": "10",
                    "classification": "BUY_CANDIDATE",
                    "data_quality_flag": "OK",
                    "has_hard_risk_flag": "false",
                }
            ],
        )

        self.assertEqual(ranked[0]["ticker"], "AAPL")
        self.assertNotEqual(ranked[0]["status"], "REVIEW")
        self.assertNotEqual(ranked[0]["data_quality_flag"], "MISSING_DATA")

    def test_watchlist_report_hardens_valuation_wording_and_preserves_review_state(self) -> None:
        output_path = Path("tests") / "_tmp_watchlist_wording_report.md"
        try:
            build_watchlist_report(
                [
                    {
                        "ticker": "AAA",
                        "status": "QUALITY_COMPOUNDER_CANDIDATE",
                        "buy_score": 75.0,
                        "valuation_score": 68.0,
                        "margin_of_safety_pct": 12.5,
                        "mandate_fit": "Hoch (90.0/100)",
                        "valuation_comment": "Die hybride Fair-Value-Sicht signalisiert Unterbewertung. REVIEW",
                        "mandate_fit_comment": "Mandats-Fit 90.0/100.",
                        "data_quality_flag": "REVIEW",
                        "main_risks": "valuation input REVIEW",
                    }
                ],
                str(output_path),
            )
            report = output_path.read_text(encoding="utf-8")
            self.assertIn("Operator note: review evidence only", report)
            self.assertIn("Valuation evidence note", report)
            self.assertIn("Possible valuation discount based on current inputs", report)
            self.assertIn("Indicative margin-of-safety field; not certainty: 12.5%", report)
            self.assertIn("REVIEW", report)
            self.assertNotIn("Unterbewertung", report)
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_blank_watchlist_ticker_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "watchlist input row 2 has blank required field\\(s\\): ticker"):
            build_watchlist_ranked(
                [{"ticker": "   ", "company_name": "Blank"}],
                [
                    {
                        "ticker": "AAA",
                        "business_score": "80",
                        "valuation_score": "65",
                        "buy_score": "75",
                        "fair_value_estimate": "100",
                        "margin_of_safety_pct": "10",
                        "data_quality_flag": "OK",
                    }
                ],
                watchlist_source_name="watchlist input",
            )

    def test_duplicate_watchlist_tickers_raise_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "watchlist input contains duplicate tickers: AAA"):
            build_watchlist_ranked(
                [{"ticker": "AAA"}, {"ticker": "AAA"}],
                [{"ticker": "AAA", "business_score": "80", "valuation_score": "60", "buy_score": "75", "fair_value_estimate": "100", "margin_of_safety_pct": "10", "data_quality_flag": "OK"}],
                watchlist_source_name="watchlist input",
            )

    def test_duplicate_fundamental_tickers_raise_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "fundamentals input contains duplicate tickers: AAA"):
            build_fundamentals_index([{"ticker": "AAA"}, {"ticker": "aAa"}], "fundamentals input")

    def test_watchlist_cli_validates_required_columns(self) -> None:
        watchlist_path = Path("tests") / "_tmp_watchlist_missing_ticker.csv"
        scores_path = Path("tests") / "_tmp_watchlist_scores.csv"
        output_path = Path("tests") / "_tmp_watchlist_output.csv"
        try:
            with watchlist_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["company_name"])
                writer.writeheader()
                writer.writerow({"company_name": "Alpha"})

            with scores_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "ticker",
                        "business_score",
                        "valuation_score",
                        "buy_score",
                        "fair_value_estimate",
                        "margin_of_safety_pct",
                        "data_quality_flag",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "ticker": "AAA",
                        "business_score": "80",
                        "valuation_score": "60",
                        "buy_score": "75",
                        "fair_value_estimate": "100",
                        "margin_of_safety_pct": "10",
                        "data_quality_flag": "OK",
                    }
                )

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.watchlist_engine",
                    "--input",
                    str(watchlist_path),
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
            combined_output = f"{result.stdout}\n{result.stderr}"
            self.assertIn("watchlist CSV", combined_output)
            self.assertIn("missing required columns: ticker", combined_output)
        finally:
            for path in [watchlist_path, scores_path, output_path]:
                if path.exists():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()
