from __future__ import annotations

import unittest

from src.portfolio_rules import (
    aggregate_positions_by_ticker,
    allocation_summary,
    compute_position_weights,
    compute_top10_weights,
    find_rule_violations,
    load_portfolio_rules,
)


class PortfolioRulesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = load_portfolio_rules()
        self.rows = [
            {"ticker": "CORE", "company_name": "Core ETF", "asset_type": "ETF", "sleeve": "CORE_ETF", "sector": "ETF", "market_value_eur": 200.0},
            {"ticker": "STK1", "company_name": "Stock 1", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "sector": "Tech", "market_value_eur": 500.0},
            {"ticker": "STK2", "company_name": "Stock 2", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "sector": "Tech", "market_value_eur": 200.0},
            {"ticker": "CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": 100.0},
        ]

    def test_allocation_summary_detects_corridor_misalignment(self) -> None:
        summary = allocation_summary(self.rows)
        self.assertAlmostEqual(summary["core_etf_weight"], 0.2, places=2)
        self.assertAlmostEqual(summary["single_stocks_weight"], 0.7, places=2)
        violations = find_rule_violations(self.rows, self.rules)
        self.assertTrue(any("Core ETF unter Zielkorridor" in item for item in violations))
        self.assertTrue(any("Single Stocks ueber Zielkorridor" in item for item in violations))

    def test_max_single_position_rule_is_detected(self) -> None:
        weights = compute_position_weights(self.rows)
        self.assertGreater(weights["STK1"], self.rules["max_single_position_weight"])
        violations = find_rule_violations(self.rows, self.rules)
        self.assertTrue(any("STK1 ueberschreitet maximale Einzelpositionsgroesse" in item for item in violations))
        self.assertFalse(any("CASH ueberschreitet maximale Einzelpositionsgroesse" in item for item in violations))

    def test_duplicate_tickers_are_aggregated_for_rule_checks(self) -> None:
        rows = [
            {"ticker": "DUP", "company_name": "Dup", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "sector": "Tech", "market_value_eur": 300.0, "cost_basis_eur": 250.0},
            {"ticker": "DUP", "company_name": "Dup", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "sector": "Tech", "market_value_eur": 200.0, "cost_basis_eur": 150.0},
            {"ticker": "CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": 500.0},
        ]
        aggregated = aggregate_positions_by_ticker(rows)
        dup_row = next(row for row in aggregated if row["ticker"] == "DUP")
        self.assertEqual(dup_row["market_value_eur"], 500.0)
        self.assertEqual(dup_row["cost_basis_eur"], 400.0)
        weights = compute_position_weights(rows)
        self.assertAlmostEqual(weights["DUP"], 0.5, places=2)
        violations = find_rule_violations(rows, self.rules)
        self.assertTrue(any("DUP ueberschreitet maximale Einzelpositionsgroesse" in item for item in violations))

    def test_top10_weight_reports_total_and_invested_views(self) -> None:
        rows = [
            {"ticker": "AAA", "company_name": "AAA", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "sector": "Tech", "market_value_eur": 100.0},
            {"ticker": "BBB", "company_name": "BBB", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "sector": "Health", "market_value_eur": 100.0},
            {"ticker": "CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": 300.0},
        ]
        metrics = compute_top10_weights(rows)
        self.assertAlmostEqual(metrics["top10_weight_total_assets"], 0.4, places=2)
        self.assertAlmostEqual(metrics["top10_weight_invested_assets"], 1.0, places=2)


if __name__ == "__main__":
    unittest.main()
