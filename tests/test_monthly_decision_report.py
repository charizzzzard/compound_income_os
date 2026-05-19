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

    def test_report_includes_portfolio_health_when_inputs_present(self) -> None:
        rules = load_portfolio_rules()
        rules_path = Path("tests") / "_tmp_report_health_rules.yaml"
        output_path = Path("tests") / "_tmp_monthly_report_health.md"
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
                    }
                ],
                output_path=str(output_path),
                rules_path=str(rules_path),
                cash_refill_rows=[
                    {
                        "status": "CASH_REFILL_REQUIRED",
                        "current_cash_eur": "100",
                        "min_cash_reserve_eur": "1500",
                        "current_cash_pct": "0.01",
                        "target_cash_min_pct": "0.05",
                        "trigger": "BOTH",
                        "data_quality_flag": "OK",
                    }
                ],
                rebalance_rows=[
                    {"bucket": "CORE_ETF", "current_pct": "0.40", "target_min_pct": "0.45", "target_max_pct": "0.60", "band_status": "UNDERWEIGHT", "recommended_action": "DEPLOY_NEW_CASH", "reason": "underweight_deploy_new_cash"},
                    {"bucket": "DIVIDEND_QUALITY_ETF", "current_pct": "0.15", "target_min_pct": "0.10", "target_max_pct": "0.25", "band_status": "WITHIN_BAND", "recommended_action": "HOLD", "reason": "within_band"},
                    {"bucket": "SINGLE_STOCK", "current_pct": "0.35", "target_min_pct": "0.20", "target_max_pct": "0.35", "band_status": "WITHIN_BAND", "recommended_action": "HOLD", "reason": "within_band"},
                    {"bucket": "CASH", "current_pct": "0.10", "target_min_pct": "0.05", "target_max_pct": "0.15", "band_status": "WITHIN_BAND", "recommended_action": "HOLD", "reason": "within_band"},
                ],
            )
            report = output_path.read_text(encoding="utf-8")
            self.assertIn("## Portfolio Health", report)
            self.assertIn("Status: `CASH_REFILL_REQUIRED`", report)
            self.assertIn("| CORE_ETF |", report)
            self.assertIn("| CASH |", report)
        finally:
            if rules_path.exists():
                rules_path.unlink()
            if output_path.exists():
                output_path.unlink()

    def test_report_renders_health_missing_as_not_available(self) -> None:
        rules = load_portfolio_rules()
        rules_path = Path("tests") / "_tmp_report_missing_health_rules.yaml"
        output_path = Path("tests") / "_tmp_monthly_report_missing_health.md"
        try:
            rules_path.write_text(json.dumps(rules), encoding="utf-8")
            build_monthly_decision_report([], [], [], str(output_path), str(rules_path))
            report = output_path.read_text(encoding="utf-8")
            self.assertIn("Cash-Refill Review: not available", report)
            self.assertIn("Rebalance Review: not available", report)
        finally:
            if rules_path.exists():
                rules_path.unlink()
            if output_path.exists():
                output_path.unlink()

    def test_portfolio_health_appears_before_buy_candidates(self) -> None:
        rules = load_portfolio_rules()
        rules_path = Path("tests") / "_tmp_report_health_order_rules.yaml"
        output_path = Path("tests") / "_tmp_monthly_report_health_order.md"
        try:
            rules_path.write_text(json.dumps(rules), encoding="utf-8")
            build_monthly_decision_report(
                positions_rows=[],
                score_rows=[],
                ranking_rows=[],
                output_path=str(output_path),
                rules_path=str(rules_path),
            )
            report = output_path.read_text(encoding="utf-8")
            self.assertLess(report.index("## Portfolio Health"), report.index("## Bestes Kauf-Ranking"))
        finally:
            if rules_path.exists():
                rules_path.unlink()
            if output_path.exists():
                output_path.unlink()

    def test_report_renders_decision_quality_state_surface(self) -> None:
        output_path = Path("tests") / "_tmp_monthly_report_decision_quality.md"
        try:
            build_monthly_decision_report(
                positions_rows=[],
                score_rows=[],
                ranking_rows=[],
                output_path=str(output_path),
                decision_quality_state={
                    "decision_confidence_level": "MEDIUM",
                    "review_required": False,
                    "evidence_coverage_status": "COVERED",
                    "evidence_coverage_pct": 1.0,
                    "data_quality_status": "COVERED",
                    "portfolio_health_status": "PASS",
                    "cash_refill_status": "PASS",
                    "rebalance_status": "PASS",
                    "missing_critical_fields": [],
                    "confidence_reason_codes": ["RANKING_STABILITY_NOT_EVALUATED", "SENSITIVITY_NOT_EVALUATED"],
                    "review_reason_codes": [],
                    "ranking_stability_status": "NOT_EVALUATED",
                    "sensitivity_status": "NOT_EVALUATED",
                    "scenario_status": "NOT_EVALUATED",
                    "tail_risk_status": "NOT_EVALUATED",
                    "scenario_robustness_score": "NOT_EVALUATED",
                },
                decision_quality_source_path="data/processed/decision_quality_state.json",
            )
            report = output_path.read_text(encoding="utf-8")
            self.assertIn("## Decision Quality", report)
            self.assertIn("decision_confidence_level", report)
            self.assertIn("review_required", report)
            self.assertIn("RANKING_STABILITY_NOT_EVALUATED", report)
            self.assertIn("phase_1_5_not_evaluated_fields", report)
            self.assertIn("Prozess-/Review-Confidence", report)
            self.assertIn("keine Erfolgswahrscheinlichkeit", report)
            self.assertIn("no broker/order/trading", report)
            self.assertIn("no simulation/backtesting", report)
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_report_renders_decision_quality_missing_as_not_available(self) -> None:
        output_path = Path("tests") / "_tmp_monthly_report_decision_quality_missing.md"
        try:
            build_monthly_decision_report([], [], [], str(output_path))
            report = output_path.read_text(encoding="utf-8")
            self.assertIn("## Decision Quality", report)
            self.assertIn("Decision Quality: `NOT_AVAILABLE`", report)
            self.assertIn("Stage ist nicht gelaufen", report)
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_report_renders_decision_journal_validation_surface(self) -> None:
        output_path = Path("tests") / "_tmp_monthly_report_decision_journal_validation.md"
        try:
            build_monthly_decision_report(
                [],
                [],
                [],
                str(output_path),
                decision_journal_validation_rows=[
                    {
                        "validation_id": "VAL_20260520_0001",
                        "as_of_date": "2026-05-20",
                        "validation_status": "REVIEW",
                        "decision_id": "DECISION_1",
                        "field_name": "review_date",
                        "reason_code": "REVIEW_DATE_MISSING",
                        "priority": "HIGH",
                        "source_artifact": "data/processed/personal_decision_state_capture.csv",
                        "message": "missing review date",
                    }
                ],
                decision_review_queue_rows=[
                    {
                        "queue_id": "QUEUE_20260520_0001",
                        "priority": "HIGH",
                        "reason_codes": "REVIEW_DATE_MISSING",
                    }
                ],
                decision_journal_validation_source_path="data/processed/decision_journal_validation.csv",
                decision_review_queue_source_path="data/processed/decision_review_queue.csv",
            )
            report = output_path.read_text(encoding="utf-8")
            self.assertIn("## Decision Journal Validation", report)
            self.assertIn("validation_status", report)
            self.assertIn("validation_findings_count", report)
            self.assertIn("validation_high_count", report)
            self.assertIn("queue_items", report)
            self.assertIn("queue_high_count", report)
            self.assertIn("Process/Review Confidence", report)
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_report_renders_decision_journal_validation_missing_as_not_available(self) -> None:
        output_path = Path("tests") / "_tmp_monthly_report_decision_journal_validation_missing.md"
        try:
            build_monthly_decision_report([], [], [], str(output_path))
            report = output_path.read_text(encoding="utf-8")
            self.assertIn("## Decision Journal Validation", report)
            self.assertIn("Decision Journal Validation: `NOT_AVAILABLE`", report)
        finally:
            if output_path.exists():
                output_path.unlink()
