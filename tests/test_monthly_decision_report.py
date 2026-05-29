from __future__ import annotations

import csv
import json
import subprocess
import unittest
from pathlib import Path

from src.build_monthly_decision_report import build_monthly_decision_report
from src.personal_decision_journal_validation import QUEUE_FIELDS, VALIDATION_FIELDS, read_decision_journal_surface
from src.portfolio_rules import load_portfolio_rules


class MonthlyDecisionReportTests(unittest.TestCase):
    def _write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def _minimal_ranking_row(self, ticker: str = "AAA") -> dict[str, str]:
        return {
            "rank": "1",
            "ticker": ticker,
            "target_action": "DO_NOT_BUY",
            "allocation_status": "NOT_ELIGIBLE",
            "suggested_buy_amount_eur": "0.0",
            "rationale": "synthetic",
            "constraint_checks": "missing_data=REVIEW",
            "valuation_comment": "REVIEW",
            "mandate_fit_comment": "Synthetic fixture.",
        }

    def _data_freshness_section(self, report: str) -> str:
        start = report.index("## Data Freshness")
        end = report.index("## Decision Quality")
        return report[start:end]

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
            self.assertIn("Reviewable candidate; not funded this month; not an order instruction", report)
            self.assertIn("Operator note: review evidence only", report)
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
            self.assertIn("Execution-mode evidence: SAVINGS_PLAN_NEW (eligible_for_new_plan)", report)
            self.assertIn("operator review required; no order is placed", report)
            self.assertNotIn("Empfohlene Ausfuehrung", report)
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

    def test_report_hardens_valuation_operator_wording_without_hiding_review_state(self) -> None:
        rules = load_portfolio_rules()
        rules_path = Path("tests") / "_tmp_report_wording_rules.yaml"
        output_path = Path("tests") / "_tmp_monthly_report_wording.md"
        try:
            rules_path.write_text(json.dumps(rules), encoding="utf-8")
            build_monthly_decision_report(
                positions_rows=[],
                score_rows=[
                    {
                        "ticker": "RISKY",
                        "classification": "WATCHLIST",
                        "data_quality_flag": "REVIEW",
                        "held_in_portfolio": "false",
                        "main_risks": "valuation input REVIEW",
                        "current_weight_pct": "0.0",
                    }
                ],
                ranking_rows=[
                    {
                        "rank": "1",
                        "ticker": "RISKY",
                        "target_action": "BUY",
                        "allocation_status": "SELECTED_THIS_MONTH",
                        "suggested_buy_amount_eur": "250.0",
                        "rationale": "test rationale",
                        "constraint_checks": "business_ok=YES",
                        "valuation_comment": "Die hybride Fair-Value-Sicht signalisiert Unterbewertung. REVIEW",
                        "mandate_fit_comment": "Improves corridor.",
                    }
                ],
                output_path=str(output_path),
                rules_path=str(rules_path),
            )
            report = output_path.read_text(encoding="utf-8")
            self.assertIn("Valuation evidence note", report)
            self.assertIn("Possible valuation discount based on current inputs", report)
            self.assertIn("heuristic fair-value evidence only", report)
            self.assertIn("REVIEW", report)
            self.assertIn("Human Operator remains final authority", report)
            self.assertNotIn("Unterbewertung", report)
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

    def test_report_renders_data_freshness_missing_as_not_available(self) -> None:
        output_path = Path("tests") / "_tmp_monthly_report_data_freshness_missing.md"
        try:
            build_monthly_decision_report([], [], [], str(output_path))
            report = output_path.read_text(encoding="utf-8")
            section = self._data_freshness_section(report)
            self.assertIn("## Data Freshness", section)
            self.assertIn("Data Freshness: `NOT_AVAILABLE`", section)
            self.assertIn("`NOT_AVAILABLE` ist kein `PASS`", section)
            self.assertIn("### Data Freshness Non-Scope", section)
            self.assertIn("freshness is process evidence", section)
            self.assertIn("no order execution", section)
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_report_renders_data_freshness_degraded_counts(self) -> None:
        output_path = Path("tests") / "_tmp_monthly_report_data_freshness_counts.md"
        summary = {
            "contract_version": "v1",
            "generated_at_utc": "2026-05-21T00:00:00Z",
            "overall_status": "REVIEW_REQUIRED",
            "review_required": True,
            "summary_counts": {
                "FRESH": 1,
                "STALE": 1,
                "MISSING": 1,
                "UNKNOWN": 1,
                "REVIEW_REQUIRED": 1,
                "NOT_APPLICABLE": 1,
            },
            "items": [],
        }
        try:
            build_monthly_decision_report([], [], [], str(output_path), data_freshness_summary=summary)
            section = self._data_freshness_section(output_path.read_text(encoding="utf-8"))
            self.assertIn("overall_status: `REVIEW_REQUIRED`", section)
            self.assertIn("review_required: `true`", section)
            for status in ("FRESH", "STALE", "MISSING", "UNKNOWN", "REVIEW_REQUIRED", "NOT_APPLICABLE"):
                self.assertIn(f"| `{status}` | 1 |", section)
            self.assertIn("degraded_state_indicators: `STALE;MISSING;UNKNOWN;REVIEW_REQUIRED`", section)
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_report_renders_data_freshness_reason_codes_or_item_reasons(self) -> None:
        output_path = Path("tests") / "_tmp_monthly_report_data_freshness_reasons.md"
        summary = {
            "overall_status": "REVIEW_REQUIRED",
            "review_required": True,
            "summary_counts": {"STALE": 1, "MISSING": 1, "UNKNOWN": 1},
            "items": [
                {"data_class": "portfolio_snapshot", "freshness_status": "STALE", "reason": "SOURCE_SNAPSHOT_TOO_OLD", "blocks_dashboard": True, "blocks_replay": True, "blocks_outcome_attribution": True},
                {"data_class": "decision_journal", "freshness_status": "MISSING", "reason": "ARTIFACT_MISSING", "blocks_dashboard": True, "blocks_replay": True, "blocks_outcome_attribution": False},
                {"data_class": "coverage_outputs", "freshness_status": "UNKNOWN", "reason": "NO_RELIABLE_DATE_SIGNAL", "blocks_dashboard": True, "blocks_replay": False, "blocks_outcome_attribution": False},
            ],
        }
        try:
            build_monthly_decision_report([], [], [], str(output_path), data_freshness_summary=summary)
            section = self._data_freshness_section(output_path.read_text(encoding="utf-8"))
            self.assertIn("SOURCE_SNAPSHOT_TOO_OLD=1", section)
            self.assertIn("ARTIFACT_MISSING=1", section)
            self.assertIn("NO_RELIABLE_DATE_SIGNAL=1", section)
            self.assertIn("portfolio_snapshot", section)
            self.assertIn("decision_journal", section)
            self.assertIn("coverage_outputs", section)
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_report_renders_data_freshness_blocker_counts(self) -> None:
        output_path = Path("tests") / "_tmp_monthly_report_data_freshness_blockers.md"
        summary = {
            "overall_status": "REVIEW_REQUIRED",
            "review_required": True,
            "summary_counts": {"STALE": 1, "MISSING": 1, "UNKNOWN": 1},
            "items": [
                {"data_class": "portfolio_snapshot", "freshness_status": "STALE", "reason": "THRESHOLD_EXCEEDED", "blocks_dashboard": True, "blocks_replay": True, "blocks_outcome_attribution": False},
                {"data_class": "review_queue", "freshness_status": "MISSING", "reason": "ARTIFACT_MISSING", "blocks_dashboard": False, "blocks_replay": True, "blocks_outcome_attribution": True},
                {"data_class": "coverage_outputs", "freshness_status": "UNKNOWN", "reason": "NO_DATE_SIGNAL", "blocks_dashboard": True, "blocks_replay": False, "blocks_outcome_attribution": True},
            ],
        }
        try:
            build_monthly_decision_report([], [], [], str(output_path), data_freshness_summary=summary)
            section = self._data_freshness_section(output_path.read_text(encoding="utf-8"))
            self.assertIn("blocks_dashboard_count: `2`", section)
            self.assertIn("blocks_replay_count: `2`", section)
            self.assertIn("blocks_outcome_attribution_count: `2`", section)
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_report_data_freshness_non_scope_blocks_investment_advice_wording(self) -> None:
        output_path = Path("tests") / "_tmp_monthly_report_data_freshness_non_scope.md"
        try:
            build_monthly_decision_report([], [], [], str(output_path))
            section = self._data_freshness_section(output_path.read_text(encoding="utf-8"))
            self.assertIn("freshness is process evidence, not an investment-confidence signal", section)
            self.assertIn("no order execution", section)
            self.assertIn("no purchase/sale instruction", section)
            self.assertIn("no score formula change", section)
            self.assertIn("no ranking formula change", section)
            self.assertIn("no valuation formula change", section)
            self.assertIn("no replay/backtesting/outcome-attribution approval", section)
            self.assertIn("no provider/API/broker integration", section)
            for unsafe in (
                "order execution approved",
                "buy instruction",
                "sell instruction",
                "investment confidence",
                "backtesting approved",
                "outcome attribution approved",
            ):
                self.assertNotIn(unsafe, section.lower())
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_cli_accepts_data_freshness_summary(self) -> None:
        positions_path = Path("tests") / "_tmp_report_freshness_positions.csv"
        scores_path = Path("tests") / "_tmp_report_freshness_scores.csv"
        ranking_path = Path("tests") / "_tmp_report_freshness_ranking.csv"
        freshness_path = Path("tests") / "_tmp_report_data_freshness_summary.json"
        output_path = Path("tests") / "_tmp_monthly_report_cli_freshness.md"
        try:
            self._write_csv(positions_path, ["ticker"], [{"ticker": "AAA"}])
            self._write_csv(
                scores_path,
                ["ticker", "classification", "data_quality_flag", "held_in_portfolio", "main_risks"],
                [{"ticker": "AAA", "classification": "WATCHLIST", "data_quality_flag": "REVIEW", "held_in_portfolio": "false", "main_risks": "missing"}],
            )
            self._write_csv(
                ranking_path,
                ["rank", "ticker", "target_action", "suggested_buy_amount_eur", "rationale", "constraint_checks", "valuation_comment", "mandate_fit_comment"],
                [
                    {
                        "rank": "1",
                        "ticker": "AAA",
                        "target_action": "DO_NOT_BUY",
                        "suggested_buy_amount_eur": "0",
                        "rationale": "blocked",
                        "constraint_checks": "missing_data=REVIEW",
                        "valuation_comment": "REVIEW",
                        "mandate_fit_comment": "Synthetic fixture.",
                    }
                ],
            )
            freshness_path.write_text(
                json.dumps(
                    {
                        "contract_version": "v1",
                        "generated_at_utc": "2026-05-21T00:00:00Z",
                        "overall_status": "STALE",
                        "review_required": True,
                        "summary_counts": {"STALE": 1},
                        "items": [
                            {"data_class": "portfolio_snapshot", "freshness_status": "STALE", "reason": "THRESHOLD_EXCEEDED", "blocks_dashboard": True, "blocks_replay": True, "blocks_outcome_attribution": True}
                        ],
                    }
                ),
                encoding="utf-8",
            )

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
                    "--data-freshness-summary",
                    str(freshness_path),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, f"{result.stdout}\n{result.stderr}")
            report = output_path.read_text(encoding="utf-8")
            self.assertIn("## Data Freshness", report)
            self.assertIn("Source artifact", report)
            self.assertIn("overall_status: `STALE`", report)
            self.assertIn("THRESHOLD_EXCEEDED", report)
        finally:
            for path in (positions_path, scores_path, ranking_path, freshness_path, output_path):
                if path.exists():
                    path.unlink()

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

    def test_monthly_report_renders_clean_decision_journal_validation_pass(self) -> None:
        output_path = Path("tests") / "_tmp_monthly_report_decision_journal_validation_pass.md"
        validation_path = Path("tests") / "_tmp_monthly_decision_journal_validation_pass.csv"
        queue_path = Path("tests") / "_tmp_monthly_decision_review_queue_pass.csv"
        try:
            self._write_csv(validation_path, VALIDATION_FIELDS, [])
            self._write_csv(queue_path, QUEUE_FIELDS, [])
            validation_rows, queue_rows = read_decision_journal_surface(str(validation_path), str(queue_path))
            build_monthly_decision_report(
                [],
                [],
                [],
                str(output_path),
                decision_journal_validation_rows=validation_rows,
                decision_review_queue_rows=queue_rows,
                decision_journal_validation_source_path=str(validation_path),
                decision_review_queue_source_path=str(queue_path),
            )
            report = output_path.read_text(encoding="utf-8")
            self.assertIn("validation_status: `PASS`", report)
            self.assertIn("validation_findings_count: `0`", report)
            self.assertIn("queue_items: `0`", report)
            self.assertNotIn("Decision Journal Validation: `NOT_AVAILABLE`", report)
        finally:
            for path in (output_path, validation_path, queue_path):
                if path.exists():
                    path.unlink()
