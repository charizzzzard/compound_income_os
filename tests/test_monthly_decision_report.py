from __future__ import annotations

import csv
import json
import subprocess
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
            self.assertIn("- Monatlicher Cash-Zufluss: 321.0 EUR", report)
            self.assertIn("## Vorschlag fuer die naechsten 321.0 EUR", report)
            self.assertIn("Kaufbar, aber nicht finanziert", report)
            self.assertIn("`EXIT1`", report)
            self.assertNotIn("`WATCHOK`", report)
        finally:
            if rules_path.exists():
                rules_path.unlink()
            if output_path.exists():
                output_path.unlink()

    def test_cli_rejects_blank_ranking_ticker(self) -> None:
        positions_path = Path("tests") / "_tmp_report_positions.csv"
        scores_path = Path("tests") / "_tmp_report_scores.csv"
        ranking_path = Path("tests") / "_tmp_report_ranking.csv"
        output_path = Path("tests") / "_tmp_monthly_report_blank_ticker.md"
        try:
            with positions_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["ticker"])
                writer.writeheader()
                writer.writerow({"ticker": "AAPL"})
            with scores_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["ticker", "classification", "data_quality_flag", "held_in_portfolio", "main_risks"])
                writer.writeheader()
                writer.writerow({"ticker": "AAPL", "classification": "HOLD", "data_quality_flag": "OK", "held_in_portfolio": "true", "main_risks": ""})
            with ranking_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["rank", "ticker", "target_action", "suggested_buy_amount_eur", "rationale", "constraint_checks"])
                writer.writeheader()
                writer.writerow({"rank": "1", "ticker": "   ", "target_action": "BUY", "suggested_buy_amount_eur": "500", "rationale": "bad", "constraint_checks": "bad"})

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.build_monthly_decision_report",
                    "--positions",
                    str(positions_path),
                    "--scores",
                    str(scores_path),
                    "--ranking",
                    str(ranking_path),
                    "--output",
                    str(output_path),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ranking CSV", f"{result.stdout}\n{result.stderr}")
            self.assertIn("blank required field(s): ticker", f"{result.stdout}\n{result.stderr}")
            self.assertFalse(output_path.exists())
        finally:
            for path in [positions_path, scores_path, ranking_path, output_path]:
                if path.exists():
                    path.unlink()

    def test_report_renders_execution_mode_for_buy_candidate(self) -> None:
        rules = load_portfolio_rules()
        rules_path = Path("tests") / "_tmp_report_execution_rules.yaml"
        output_path = Path("tests") / "_tmp_monthly_report_execution.md"
        try:
            rules_path.write_text(json.dumps(rules), encoding="utf-8")
            build_monthly_decision_report(
                positions_rows=[],
                score_rows=[],
                ranking_rows=[
                    {
                        "rank": "1",
                        "ticker": "VWCE",
                        "target_action": "BUY",
                        "allocation_status": "SELECTED_THIS_MONTH",
                        "suggested_buy_amount_eur": "250.0",
                        "rationale": "test rationale",
                        "constraint_checks": "business_ok=YES",
                        "valuation_comment": "Attractive.",
                        "mandate_fit_comment": "Improves corridor.",
                        "execution_mode": "SAVINGS_PLAN_NEW",
                        "execution_mode_reason": "eligible_for_new_plan",
                    }
                ],
                output_path=str(output_path),
                rules_path=str(rules_path),
            )
            report = output_path.read_text(encoding="utf-8")
            self.assertIn("Empfohlene Ausfuehrung: SAVINGS_PLAN_NEW (eligible_for_new_plan)", report)
        finally:
            if rules_path.exists():
                rules_path.unlink()
            if output_path.exists():
                output_path.unlink()

    def test_report_does_not_render_execution_mode_for_non_buy_row(self) -> None:
        rules = load_portfolio_rules()
        rules_path = Path("tests") / "_tmp_report_non_buy_execution_rules.yaml"
        output_path = Path("tests") / "_tmp_monthly_report_non_buy_execution.md"
        try:
            rules_path.write_text(json.dumps(rules), encoding="utf-8")
            build_monthly_decision_report(
                positions_rows=[],
                score_rows=[],
                ranking_rows=[
                    {
                        "rank": "1",
                        "ticker": "HOLD_CASH",
                        "target_action": "HOLD_CASH",
                        "allocation_status": "SELECTED_THIS_MONTH",
                        "suggested_buy_amount_eur": "500.0",
                        "rationale": "hold cash",
                        "constraint_checks": "portfolio_rule=hold_cash_allowed",
                        "valuation_comment": "Cash.",
                        "mandate_fit_comment": "Allowed.",
                        "execution_mode": "SINGLE_ORDER",
                        "execution_mode_reason": "candidate_amount_above_min",
                    }
                ],
                output_path=str(output_path),
                rules_path=str(rules_path),
            )
            report = output_path.read_text(encoding="utf-8")
            self.assertNotIn("Empfohlene Ausfuehrung", report)
        finally:
            if rules_path.exists():
                rules_path.unlink()
            if output_path.exists():
                output_path.unlink()
