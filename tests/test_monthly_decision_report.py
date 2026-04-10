from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.build_monthly_decision_report import build_monthly_decision_report
from src.portfolio_rules import load_portfolio_rules


class MonthlyDecisionReportTests(unittest.TestCase):
    def test_report_uses_dynamic_monthly_cash_and_filters_review_noise(self) -> None:
        rules = load_portfolio_rules()
        rules["monthly_new_cash_eur"] = 321.0
        rules_path = Path("tests") / "_tmp_report_rules.yaml"
        output_path = Path("tests") / "_tmp_monthly_report.md"
        try:
            rules_path.write_text(json.dumps(rules), encoding="utf-8")
            build_monthly_decision_report(
                positions_rows=[],
                score_rows=[
                    {
                        "ticker": "WATCHOK",
                        "classification": "WATCHLIST",
                        "data_quality_flag": "OK",
                        "held_in_portfolio": "true",
                        "main_risks": "none",
                        "current_weight_pct": "1.0",
                    },
                    {
                        "ticker": "EXIT1",
                        "classification": "EXIT_REVIEW",
                        "data_quality_flag": "REVIEW",
                        "held_in_portfolio": "true",
                        "main_risks": "broken thesis",
                        "current_weight_pct": "2.0",
                    },
                ],
                ranking_rows=[
                    {
                        "rank": "1",
                        "ticker": "VWCE",
                        "target_action": "BUY",
                        "allocation_status": "SELECTED_THIS_MONTH",
                        "suggested_buy_amount_eur": "321.0",
                        "rationale": "test rationale",
                        "constraint_checks": "business_ok=YES",
                        "valuation_comment": "Attractive.",
                        "mandate_fit_comment": "Improves corridor.",
                    },
                    {
                        "rank": "2",
                        "ticker": "FUSD",
                        "target_action": "BUY",
                        "allocation_status": "ELIGIBLE_NOT_FUNDED",
                        "suggested_buy_amount_eur": "0.0",
                        "rationale": "fallback rationale",
                        "constraint_checks": "business_ok=YES",
                        "valuation_comment": "Attractive.",
                        "mandate_fit_comment": "Also good.",
                    }
                ],
                output_path=str(output_path),
                rules_path=str(rules_path),
            )
            report = output_path.read_text(encoding="utf-8")
            self.assertIn("# Monatlicher Entscheidungsbericht", report)
            self.assertIn("## Vorschlag fuer die naechsten 321.0 EUR", report)
            self.assertIn("Kaufbar, aber nicht finanziert", report)
            self.assertIn("`EXIT1`", report)
            self.assertNotIn("`WATCHOK`", report)
        finally:
            if rules_path.exists():
                rules_path.unlink()
            if output_path.exists():
                output_path.unlink()
