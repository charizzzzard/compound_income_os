from __future__ import annotations

import json
import unittest
from pathlib import Path

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
from src.common import load_yaml_config
from src.fundamentals_master import PERSONAL_MASTER_FIELDS
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

    def personal_row(self, ticker: str, values: dict[str, str]) -> dict[str, str]:
        row = {field: "" for field in PERSONAL_MASTER_FIELDS}
        row.update(
            {
                "ticker": ticker,
                "isin": "US0000000001",
                "company_name": f"{ticker} Corp",
                "currency": "USD",
                "sector": "Technology",
                "country": "US",
                "asset_type": "STOCK",
                "company_type_profile": "STANDARD",
                "source_name": "unit_test",
                "source_as_of_date": "2026-04-26",
                "data_quality_flag": "OK",
                "sleeve": "SINGLE_STOCK",
                "current_price_eur": "100",
                "mandate_fit_score": "90",
                "thesis_robustness": "ROBUST",
                "has_hard_risk_flag": "false",
                "drawdown_from_high_pct": "10",
                "expected_return_pct": "8",
            }
        )
        row.update(values)
        return row

    def score_single_personal_row(self, values: dict[str, str]) -> dict[str, object]:
        positions = [
            {
                "ticker": "AAA",
                "isin": "US0000000001",
                "company_name": "AAA Corp",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "sector": "Technology",
                "country": "US",
                "market_value_eur": "100",
            }
        ]
        scores = build_scores(positions, [self.personal_row("AAA", values)], fundamentals_format="personal")
        return next(row for row in scores if row["ticker"] == "AAA")

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

    def test_business_score_weights_must_sum_to_one(self) -> None:
        config = {
            **self.scoring_config,
            "business_score_weights": {
                "quality_score": 0.50,
                "dividend_score": 0.20,
                "balance_sheet_score": 0.20,
                "growth_quality_score": 0.15,
                "capital_allocation_score": 0.15,
            },
        }
        with self.assertRaisesRegex(ValueError, "business_score_weights must sum to 1.0, got 1.2"):
            compute_business_score({"quality_score": 90}, config)

    def test_fair_value_weights_must_sum_to_one(self) -> None:
        config_path = Path("tests") / "_tmp_bad_scoring_weights.yaml"
        config = load_yaml_config("configs/scoring_weights.yaml")
        config["fair_value_weights"]["historical_multiple_score"] = 0.60
        try:
            config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fair_value_weights must sum to 1.0, got 1.2"):
                compute_valuation_metrics({"current_price_eur": 100}, str(config_path))
        finally:
            if config_path.exists():
                config_path.unlink()

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

    def test_blank_fundamentals_ticker_is_rejected_before_missing_data_fallback(self) -> None:
        positions = [
            {
                "ticker": "AAPL",
                "isin": "US0378331005",
                "company_name": "Apple",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "sector": "Technology",
                "market_value_eur": "100",
            }
        ]
        fundamentals = [
            {
                "ticker": " ",
                "isin": "US0378331005",
                "company_name": "Apple",
                "sector": "Technology",
                "country": "USA",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "quality_score": "90",
                "dividend_score": "60",
                "balance_sheet_score": "90",
                "growth_quality_score": "80",
                "capital_allocation_score": "85",
            }
        ]

        with self.assertRaisesRegex(ValueError, "fundamentals input row 2 has blank required field\\(s\\): ticker"):
            build_scores(positions, fundamentals)

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

    def test_ticker_case_normalization_matches_position_and_fundamentals(self) -> None:
        positions = [
            {
                "ticker": "AAPL",
                "company_name": "Apple",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "sector": "Technology",
                "country": "USA",
                "market_value_eur": "100",
            }
        ]
        fundamentals = [
            {
                "ticker": "aapl",
                "company_name": "Apple",
                "sector": "Technology",
                "country": "USA",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "quality_score": "90",
                "dividend_score": "60",
                "balance_sheet_score": "90",
                "growth_quality_score": "80",
                "capital_allocation_score": "85",
                "mandate_fit_score": "90",
                "data_quality_flag": "OK",
            }
        ]

        scores = build_scores(positions, fundamentals)

        self.assertEqual([row["ticker"] for row in scores], ["AAPL"])
        self.assertTrue(scores[0]["held_in_portfolio"])
        self.assertEqual(scores[0]["fundamentals_input_format"], "legacy")

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

    def test_purchase_readiness_keeps_degraded_data_quality_states_under_review(self) -> None:
        for flag in ("MISSING_DATA", "REVIEW", "STALE", "CONFLICT", "UNKNOWN", "BLOCKED", "INVALID"):
            with self.subTest(flag=flag):
                readiness = evaluate_purchase_readiness(
                    {
                        "business_score": "95",
                        "valuation_score": "90",
                        "buy_score": "92",
                        "classification": "BUY_CANDIDATE",
                        "data_quality_flag": flag,
                        "has_hard_risk_flag": "false",
                    },
                    self.rules,
                )
                self.assertEqual(readiness["purchase_state"], "REVIEW")
                self.assertFalse(readiness["eligible_for_purchase"])

    def test_core_quality_complete_missing_valuation_is_review_not_missing_data(self) -> None:
        row = self.score_single_personal_row(
            {
                "revenue_cagr_5y": "8",
                "eps_cagr_5y": "7",
                "gross_margin": "50",
                "operating_margin": "25",
                "share_count_cagr_5y": "-1",
                "fcf_margin": "20",
                "payout_ratio_fcf": "50",
                "fcf_per_share_cagr_5y": "6",
            }
        )
        self.assertEqual(row["core_quality_data_status"], "OK")
        self.assertEqual(row["valuation_data_status"], "MISSING")
        self.assertEqual(row["data_quality_flag"], "REVIEW")
        self.assertNotEqual(row["classification"], "BUY_CANDIDATE")

    def test_zero_core_quality_kpis_remains_missing_data(self) -> None:
        row = self.score_single_personal_row(
            {
                "normalized_fcf_yield_pct": "5",
                "target_fcf_yield_pct": "4",
                "fcf_margin": "20",
                "payout_ratio_fcf": "50",
                "fcf_per_share_cagr_5y": "6",
            }
        )
        self.assertEqual(row["core_quality_data_status"], "MISSING")
        self.assertEqual(row["data_quality_flag"], "MISSING_DATA")

    def test_three_of_five_core_quality_kpis_is_partial_review(self) -> None:
        row = self.score_single_personal_row(
            {
                "revenue_cagr_5y": "8",
                "eps_cagr_5y": "7",
                "gross_margin": "50",
                "normalized_fcf_yield_pct": "5",
                "target_fcf_yield_pct": "4",
                "fcf_margin": "20",
                "payout_ratio_fcf": "50",
                "fcf_per_share_cagr_5y": "6",
            }
        )
        self.assertEqual(row["core_quality_data_status"], "PARTIAL")
        self.assertEqual(row["data_quality_flag"], "REVIEW")

    def test_missing_advanced_optional_kpis_do_not_block_core_score(self) -> None:
        row = self.score_single_personal_row(
            {
                "revenue_cagr_5y": "8",
                "eps_cagr_5y": "7",
                "gross_margin": "50",
                "operating_margin": "25",
                "share_count_cagr_5y": "-1",
                "normalized_fcf_yield_pct": "5",
                "target_fcf_yield_pct": "4",
                "fcf_margin": "20",
                "payout_ratio_fcf": "50",
                "fcf_per_share_cagr_5y": "6",
                "pe_current": "20",
                "pe_hist": "22",
                "ev_ebit_current": "15",
                "ev_ebit_hist": "16",
            }
        )
        self.assertEqual(row["advanced_data_status"], "MISSING")
        self.assertEqual(row["data_quality_flag"], "OK")


if __name__ == "__main__":
    unittest.main()
