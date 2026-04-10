from __future__ import annotations

import unittest
from pathlib import Path
import json

from src.monthly_ranking_engine import build_monthly_ranking
from src.portfolio_rules import load_portfolio_rules


class MonthlyRankingEngineTests(unittest.TestCase):
    def test_hold_cash_logic_when_no_candidate_is_buyable(self) -> None:
        positions = [
            {"ticker": "EUR-CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": "2000"},
        ]
        scores = [
            {
                "ticker": "BAD",
                "company_name": "Bad Co",
                "sector": "Tech",
                "sleeve": "SINGLE_STOCK",
                "held_in_portfolio": "false",
                "business_score": "60",
                "valuation_score": "50",
                "buy_score": "61",
                "margin_of_safety_pct": "0",
                "classification": "REJECT",
                "has_hard_risk_flag": "true",
                "data_quality_flag": "OK",
                "valuation_comment": "Too weak.",
                "mandate_fit_score": "40",
            }
        ]
        watchlist = [
            {
                "ticker": "BAD",
                "company_name": "Bad Co",
                "sector": "Tech",
                "sleeve": "SINGLE_STOCK",
                "status": "REJECT",
                "mandate_fit_comment": "Weak fit.",
            }
        ]
        ranking, _ = build_monthly_ranking(positions, scores, watchlist)
        self.assertEqual(ranking[0]["ticker"], "HOLD_CASH")
        self.assertEqual(ranking[0]["target_action"], "HOLD_CASH")

    def test_monthly_cash_uses_configuration_value(self) -> None:
        rules = load_portfolio_rules()
        rules["monthly_new_cash_eur"] = 321.0
        path = Path("tests") / "_tmp_rules.yaml"
        try:
            path.write_text(json.dumps(rules), encoding="utf-8")
            positions = [
                {"ticker": "EUR-CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": "5000"},
            ]
            scores = [
                {
                    "ticker": "VWCE",
                    "company_name": "Core ETF",
                    "sector": "ETF",
                    "sleeve": "CORE_ETF",
                    "held_in_portfolio": "false",
                    "business_score": "80",
                    "valuation_score": "65",
                    "buy_score": "75",
                    "margin_of_safety_pct": "10",
                    "classification": "BUY_CANDIDATE",
                    "has_hard_risk_flag": "false",
                    "data_quality_flag": "OK",
                    "valuation_comment": "Attractive.",
                    "mandate_fit_score": "95",
                }
            ]
            watchlist = [
                {
                    "ticker": "VWCE",
                    "company_name": "Core ETF",
                    "sector": "ETF",
                    "sleeve": "CORE_ETF",
                    "status": "CORE_CANDIDATE",
                    "mandate_fit_comment": "Improves corridor.",
                }
            ]
            ranking, _ = build_monthly_ranking(positions, scores, watchlist, str(path))
            self.assertEqual(ranking[0]["suggested_buy_amount_eur"], 321.0)
        finally:
            if path.exists():
                path.unlink()

    def test_allowed_amount_caps_suggested_buy_amount_for_top_up(self) -> None:
        positions = [
            {"ticker": "AAA", "company_name": "AAA", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "sector": "Tech", "market_value_eur": "200"},
            {"ticker": "AAA", "company_name": "AAA", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "sector": "Tech", "market_value_eur": "140"},
            {"ticker": "EUR-CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": "5000"},
        ]
        scores = [
            {
                "ticker": "AAA",
                "company_name": "AAA",
                "sector": "Tech",
                "sleeve": "SINGLE_STOCK",
                "held_in_portfolio": "true",
                "business_score": "85",
                "valuation_score": "70",
                "buy_score": "80",
                "margin_of_safety_pct": "10",
                "classification": "HOLD",
                "has_hard_risk_flag": "false",
                "data_quality_flag": "OK",
                "valuation_comment": "Attractive.",
                "mandate_fit_score": "90",
            }
        ]
        ranking, _ = build_monthly_ranking(positions, scores, [])
        self.assertEqual(ranking[0]["target_action"], "TOP_UP")
        self.assertEqual(ranking[0]["suggested_buy_amount_eur"], 127.2)

    def test_hold_cash_respects_config_when_disabled(self) -> None:
        rules = load_portfolio_rules()
        rules["allow_hold_cash_if_no_opportunity"] = False
        path = Path("tests") / "_tmp_rules.yaml"
        try:
            path.write_text(json.dumps(rules), encoding="utf-8")
            positions = [
                {"ticker": "EUR-CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": "2000"},
            ]
            scores = [
                {
                    "ticker": "BAD",
                    "company_name": "Bad Co",
                    "sector": "Tech",
                    "sleeve": "SINGLE_STOCK",
                    "held_in_portfolio": "false",
                    "business_score": "50",
                    "valuation_score": "30",
                    "buy_score": "40",
                    "margin_of_safety_pct": "0",
                    "classification": "REJECT",
                    "has_hard_risk_flag": "true",
                    "data_quality_flag": "OK",
                    "valuation_comment": "Too weak.",
                    "mandate_fit_score": "40",
                }
            ]
            watchlist = [
                {
                    "ticker": "BAD",
                    "company_name": "Bad Co",
                    "sector": "Tech",
                    "sleeve": "SINGLE_STOCK",
                    "status": "REJECT",
                    "mandate_fit_comment": "Weak fit.",
                }
            ]
            ranking, _ = build_monthly_ranking(positions, scores, watchlist, str(path))
            self.assertFalse(any(row["ticker"] == "HOLD_CASH" for row in ranking))
            self.assertEqual(ranking[0]["target_action"], "DO_NOT_BUY")
            self.assertEqual(ranking[0]["suggested_buy_amount_eur"], 0.0)
        finally:
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
