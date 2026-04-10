from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path

from src.scoring_engine import build_fundamentals_index
from src.watchlist_engine import build_watchlist_ranked, score_index


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

    def test_duplicate_score_tickers_raise_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "scores input contains duplicate tickers: AAA"):
            score_index([{"ticker": "AAA"}, {"ticker": "AAA"}], "scores input")

    def test_duplicate_watchlist_tickers_raise_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "watchlist input contains duplicate tickers: AAA"):
            build_watchlist_ranked(
                [{"ticker": "AAA"}, {"ticker": "AAA"}],
                [{"ticker": "AAA", "business_score": "80", "valuation_score": "60", "buy_score": "75", "fair_value_estimate": "100", "margin_of_safety_pct": "10", "data_quality_flag": "OK"}],
                watchlist_source_name="watchlist input",
            )

    def test_duplicate_fundamental_tickers_raise_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "fundamentals input contains duplicate tickers: AAA"):
            build_fundamentals_index([{"ticker": "AAA"}, {"ticker": "AAA"}], "fundamentals input")

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
