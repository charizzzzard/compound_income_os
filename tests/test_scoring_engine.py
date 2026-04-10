from __future__ import annotations

import unittest

from src.scoring_engine import (
    build_fundamentals_isin_index,
    build_fundamentals_name_index,
    build_position_index,
    build_scores,
    classify_company,
    compute_business_score,
    compute_buy_score,
    evaluate_purchase_readiness,
    find_unique_name_match,
)
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
            },
            "buy_score_weights": {
                "business_score": 0.55,
                "valuation_score": 0.18,
                "expected_return_score": 0.1125,
                "drawdown_opportunity_score": 0.09,
                "portfolio_fit_score": 0.0675,
            },
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
        score = compute_buy_score(80.0, 70.0, 60.0, 50.0, 40.0, self.scoring_config)
        expected = 0.55 * 80.0 + 0.45 * (0.40 * 70.0 + 0.25 * 60.0 + 0.20 * 50.0 + 0.15 * 40.0)
        self.assertAlmostEqual(score, expected, places=2)

    def test_buy_score_uses_config_weights(self) -> None:
        config = {
            "buy_score_weights": {
                "business_score": 0.0,
                "valuation_score": 1.0,
                "expected_return_score": 0.0,
                "drawdown_opportunity_score": 0.0,
                "portfolio_fit_score": 0.0,
            }
        }
        score = compute_buy_score(80.0, 70.0, 60.0, 50.0, 40.0, config)
        self.assertEqual(score, 70.0)

    def test_buy_score_invalid_config_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "buy_score_weights missing keys"):
            compute_buy_score(80.0, 70.0, 60.0, 50.0, 40.0, {"buy_score_weights": {"business_score": 1.0}})

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
        self.assertIn("Fundamentaldaten", row["valuation_comment"])

    def test_canonical_position_mapping_aggregates_instead_of_overwriting(self) -> None:
        positions = [
            {
                "ticker": "AAPL",
                "isin": "US0378331005",
                "company_name": "Apple",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "sector": "Technology",
                "country": "USA",
                "quantity": "1",
                "market_value_eur": "100",
                "cost_basis_eur": "80",
                "price_eur": "100",
            },
            {
                "ticker": "US0378331005",
                "isin": "US0378331005",
                "company_name": "Apple Inc.",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "sector": "Technology",
                "country": "USA",
                "quantity": "2",
                "market_value_eur": "200",
                "cost_basis_eur": "180",
                "price_eur": "100",
            },
        ]
        fundamentals = [
            {
                "ticker": "AAPL",
                "isin": "US0378331005",
                "company_name": "Apple",
                "sector": "Technology",
                "country": "USA",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "current_price_eur": "100",
                "quality_score": "90",
                "dividend_score": "60",
                "balance_sheet_score": "90",
                "growth_quality_score": "80",
                "capital_allocation_score": "85",
                "mandate_fit_score": "90",
                "pe_current": "20",
                "pe_hist": "22",
                "ev_ebit_current": "16",
                "ev_ebit_hist": "18",
                "fcf_yield_current_pct": "5",
                "fcf_yield_hist_pct": "4",
                "normalized_fcf_yield_pct": "5",
                "target_fcf_yield_pct": "4",
                "dividend_yield_current_pct": "1",
                "dividend_yield_hist_pct": "1",
                "expected_return_pct": "10",
                "drawdown_from_high_pct": "15",
                "has_hard_risk_flag": "false",
                "thesis_robustness": "ROBUST",
                "data_quality_flag": "OK",
            }
        ]

        position_index = build_position_index(
            positions,
            build_fundamentals_isin_index(fundamentals),
            build_fundamentals_name_index(fundamentals),
        )
        self.assertEqual(position_index["AAPL"]["market_value_eur"], 300.0)
        self.assertEqual(position_index["AAPL"]["cost_basis_eur"], 260.0)
        self.assertEqual(position_index["AAPL"]["quantity"], 3.0)

        scores = build_scores(positions, fundamentals)
        apple = next(row for row in scores if row["ticker"] == "AAPL")
        self.assertTrue(apple["held_in_portfolio"])
        self.assertEqual(apple["position_market_value_eur"], 300.0)

    def test_name_fallback_does_not_match_ambiguous_fundamental_names(self) -> None:
        fundamentals = [
            {"ticker": "AAA", "company_name": "Example Duplicate", "sector": "Tech", "country": "USA", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK"},
            {"ticker": "BBB", "company_name": "Example Duplicate", "sector": "Tech", "country": "USA", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK"},
        ]
        position = {
            "ticker": "DE000A1MISS0",
            "isin": "DE000A1MISS0",
            "company_name": "Example Duplicate Registered Shares",
            "asset_type": "STOCK",
            "sleeve": "SINGLE_STOCK",
            "sector": "Unknown",
            "market_value_eur": "100",
        }
        name_index = build_fundamentals_name_index(fundamentals)

        self.assertIsNone(find_unique_name_match(position, name_index))
        position_index = build_position_index([position], {}, name_index)
        self.assertIn("DE000A1MISS0", position_index)
        self.assertNotIn("AAA", position_index)
        self.assertNotIn("BBB", position_index)

    def test_purchase_readiness_blocks_missing_data(self) -> None:
        readiness = evaluate_purchase_readiness(
            {
                "business_score": "90",
                "valuation_score": "80",
                "buy_score": "85",
                "classification": "BUY_CANDIDATE",
                "data_quality_flag": "MISSING_DATA",
                "has_hard_risk_flag": "false",
            },
            self.rules,
        )
        self.assertEqual(readiness["purchase_state"], "REVIEW")
        self.assertFalse(readiness["eligible_for_purchase"])


if __name__ == "__main__":
    unittest.main()
