from __future__ import annotations

import unittest

from src.scoring_engine import build_scores, classify_company, compute_business_score, compute_buy_score
from src.portfolio_rules import load_portfolio_rules
from src.valuation_engine import compute_valuation_metrics


class ScoringEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = load_portfolio_rules()
        self.scoring_config = {
            "business_score_weights": {
                "quality_score": 0.30,
                "dividend_score": 0.20,
                "balance_sheet_score": 0.20,
                "growth_quality_score": 0.15,
                "capital_allocation_score": 0.15,
            }
        }

    def test_business_score_formula(self) -> None:
        row = {
            "quality_score": 90,
            "dividend_score": 80,
            "balance_sheet_score": 70,
            "growth_quality_score": 60,
            "capital_allocation_score": 50,
        }
        score = compute_business_score(row, self.scoring_config)
        expected = 0.30 * 90 + 0.20 * 80 + 0.20 * 70 + 0.15 * 60 + 0.15 * 50
        self.assertAlmostEqual(score, expected, places=2)

    def test_buy_score_formula(self) -> None:
        score = compute_buy_score(80.0, 70.0, 60.0, 50.0, 40.0)
        expected = 0.55 * 80.0 + 0.45 * (0.40 * 70.0 + 0.25 * 60.0 + 0.20 * 50.0 + 0.15 * 40.0)
        self.assertAlmostEqual(score, expected, places=2)

    def test_fair_value_score_formula(self) -> None:
        metrics = compute_valuation_metrics(
            {
                "current_price_eur": 100,
                "pe_current": 10,
                "pe_hist": 15,
                "ev_ebit_current": 12,
                "ev_ebit_hist": 15,
                "fcf_yield_current_pct": 6,
                "fcf_yield_hist_pct": 4,
                "normalized_fcf_yield_pct": 6,
                "target_fcf_yield_pct": 4,
                "dividend_yield_current_pct": 3,
                "dividend_yield_hist_pct": 2,
                "data_quality_flag": "OK",
            }
        )
        self.assertAlmostEqual(metrics["historical_multiple_score"], 93.33, places=2)
        self.assertAlmostEqual(metrics["fair_value_score"], 97.33, places=2)

    def test_classification_thresholds(self) -> None:
        candidate = classify_company(80.0, 65.0, 75.0, False, 0.0, False, "ROBUST", "OK", self.rules)
        self.assertEqual(candidate, "BUY_CANDIDATE")
        rejected = classify_company(60.0, 65.0, 70.0, False, 0.0, False, "ROBUST", "OK", self.rules)
        self.assertEqual(rejected, "REJECT")

    def test_held_positions_do_not_end_as_reject(self) -> None:
        classification = classify_company(50.0, 35.0, 40.0, True, 2.0, False, "ROBUST", "OK", self.rules)
        self.assertEqual(classification, "EXIT_REVIEW")

    def test_missing_fundamentals_for_holding_stays_in_score_universe(self) -> None:
        positions = [
            {
                "ticker": "ONLYPOS",
                "company_name": "Only Position",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "sector": "Tech",
                "country": "USA",
                "market_value_eur": "100",
                "cost_basis_eur": "90",
                "price_eur": "100",
            }
        ]
        results = build_scores(positions, [])
        self.assertEqual(len(results), 1)
        row = results[0]
        self.assertEqual(row["ticker"], "ONLYPOS")
        self.assertTrue(row["held_in_portfolio"])
        self.assertEqual(row["data_quality_flag"], "MISSING_DATA")
        self.assertEqual(row["classification"], "EXIT_REVIEW")
        self.assertIn("Missing fundamentals", row["valuation_comment"])


if __name__ == "__main__":
    unittest.main()
