from __future__ import annotations

import csv
import json
import subprocess
import unittest
from datetime import date
from pathlib import Path

from src.savings_plan_routing import (
    ROUTING_FIELDS,
    evaluate_execution_mode,
    load_routing_thresholds,
    load_savings_plan_lookup,
    route_candidates,
    write_routing_csv,
)


class SavingsPlanRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / "_tmp_savings_plan_routing"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.thresholds = {
            "drawdown_opportunity_threshold": 70.0,
            "material_underweight_gap_pct": 1.0,
            "single_order_min_amount_eur": 200.0,
            "max_fee_ratio": 0.005,
            "max_wait_days_for_savings_plan": 14,
            "buy_gate_business_score": 60.0,
            "buy_gate_valuation_score": 60.0,
            "position_weight_cap": 0.10,
        }

    def tearDown(self) -> None:
        for path in sorted(self.tmp.glob("*")):
            path.unlink()
        if self.tmp.exists():
            self.tmp.rmdir()

    def write_json_yaml(self, name: str, payload: dict[str, object]) -> Path:
        path = self.tmp / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def write_registry(self, rows: list[dict[str, str]]) -> Path:
        path = self.tmp / "registry.csv"
        fieldnames = [
            "ticker",
            "isin",
            "broker",
            "instrument_name",
            "monthly_amount_eur",
            "frequency",
            "execution_day_of_month",
            "active",
            "started_at",
            "last_modified",
            "notes",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def plan(self, active: str = "TRUE", execution_day: str = "2") -> dict[str, str]:
        return {
            "ticker": "MSFT",
            "isin": "",
            "broker": "TRADE_REPUBLIC",
            "instrument_name": "Microsoft",
            "monthly_amount_eur": "50",
            "frequency": "MONTHLY",
            "execution_day_of_month": execution_day,
            "active": active,
            "started_at": "2026-01-01",
            "last_modified": "2026-05-01",
            "notes": "",
        }

    def buy_candidate(self, ticker: str = "MSFT") -> dict[str, str]:
        return {"ticker": ticker, "target_action": "BUY", "savings_plan_eligible": "TRUE"}

    def test_existing_plan_when_active_plan_exists_without_single_order_trigger(self) -> None:
        mode, reason = evaluate_execution_mode({"ticker": "MSFT", "target_action": "BUY"}, {"MSFT": {"savings_plan_active": "TRUE", "execution_day_of_month": "2", "frequency": "MONTHLY"}}, self.thresholds)
        self.assertEqual((mode, reason), ("SAVINGS_PLAN_EXISTING", "eligible_for_existing_plan"))

    def test_new_plan_when_explicitly_eligible_without_active_plan(self) -> None:
        mode, reason = evaluate_execution_mode(self.buy_candidate("AAPL"), {}, self.thresholds)
        self.assertEqual((mode, reason), ("SAVINGS_PLAN_NEW", "eligible_for_new_plan"))

    def test_no_recommendation_when_no_plan_and_eligibility_unknown(self) -> None:
        mode, reason = evaluate_execution_mode({"ticker": "AAPL", "target_action": "BUY"}, {}, self.thresholds)
        self.assertEqual(mode, "NO_RECOMMENDATION")
        self.assertEqual(reason, "missing_inputs")

    def test_single_order_condition_a_explicit_not_eligible(self) -> None:
        mode, reason = evaluate_execution_mode({"ticker": "AAPL", "savings_plan_eligible": "false"}, {}, self.thresholds)
        self.assertEqual((mode, reason), ("SINGLE_ORDER", "savings_plan_not_eligible"))

    def test_single_order_condition_b_all_gates_pass(self) -> None:
        candidate = {
            "ticker": "AAPL",
            "drawdown_opportunity_score": "75",
            "valuation_score": "65",
            "business_score": "70",
            "bucket_underweight_gap": "2.0",
            "position_weight_after_buy": "0.08",
        }
        self.assertEqual(evaluate_execution_mode(candidate, {}, self.thresholds), ("SINGLE_ORDER", "drawdown_opportunity_gate_passed"))

    def test_drawdown_alone_does_not_trigger_single_order_when_scores_below_gate(self) -> None:
        candidate = {
            "ticker": "AAPL",
            "drawdown_opportunity_score": "90",
            "valuation_score": "55",
            "business_score": "55",
            "bucket_underweight_gap": "2.0",
            "position_weight_after_buy": "0.08",
            "savings_plan_eligible": "TRUE",
        }
        self.assertEqual(evaluate_execution_mode(candidate, {}, self.thresholds)[0], "SAVINGS_PLAN_NEW")

    def test_drawdown_does_not_trigger_single_order_when_portfolio_fit_missing(self) -> None:
        candidate = {
            "ticker": "AAPL",
            "drawdown_opportunity_score": "90",
            "valuation_score": "70",
            "business_score": "70",
            "savings_plan_eligible": "TRUE",
        }
        self.assertEqual(evaluate_execution_mode(candidate, {}, self.thresholds)[0], "SAVINGS_PLAN_NEW")

    def test_single_order_condition_c_large_amount_low_fee(self) -> None:
        candidate = {"ticker": "AAPL", "candidate_amount_eur": "250", "order_fee_ratio": "0.001"}
        self.assertEqual(evaluate_execution_mode(candidate, {}, self.thresholds), ("SINGLE_ORDER", "candidate_amount_above_min"))

    def test_condition_c_fails_when_fee_ratio_missing(self) -> None:
        candidate = {"ticker": "AAPL", "candidate_amount_eur": "250", "savings_plan_eligible": "TRUE"}
        self.assertEqual(evaluate_execution_mode(candidate, {}, self.thresholds)[0], "SAVINGS_PLAN_NEW")

    def test_single_order_condition_d_direct_wait_days(self) -> None:
        candidate = {"ticker": "MSFT", "next_savings_plan_execution_days": "30"}
        self.assertEqual(evaluate_execution_mode(candidate, {}, self.thresholds), ("SINGLE_ORDER", "next_execution_too_far"))

    def test_single_order_condition_d_derived_from_active_plan_and_run_date(self) -> None:
        lookup = {"MSFT": {"savings_plan_active": "TRUE", "execution_day_of_month": "28", "frequency": "MONTHLY"}}
        self.assertEqual(evaluate_execution_mode({"ticker": "MSFT"}, lookup, self.thresholds, date(2026, 5, 10)), ("SINGLE_ORDER", "next_execution_too_far"))

    def test_no_recommendation_when_required_inputs_missing(self) -> None:
        mode, reason = evaluate_execution_mode({"ticker": "AAPL", "drawdown_opportunity_score": "80"}, {}, self.thresholds)
        self.assertEqual((mode, reason), ("NO_RECOMMENDATION", "missing_inputs"))

    def test_threshold_loading_succeeds_with_valid_config(self) -> None:
        path = self.write_json_yaml("thresholds.yaml", {"schema_version": 1, "thresholds": self.thresholds})
        loaded = load_routing_thresholds(path)
        self.assertEqual(loaded["single_order_min_amount_eur"], 200.0)

    def test_threshold_loading_raises_on_missing_key(self) -> None:
        bad = dict(self.thresholds)
        bad.pop("max_fee_ratio")
        path = self.write_json_yaml("bad_missing.yaml", {"schema_version": 1, "thresholds": bad})
        with self.assertRaisesRegex(ValueError, "max_fee_ratio"):
            load_routing_thresholds(path)

    def test_threshold_loading_raises_on_out_of_range_value(self) -> None:
        bad = dict(self.thresholds)
        bad["position_weight_cap"] = 2
        path = self.write_json_yaml("bad_range.yaml", {"schema_version": 1, "thresholds": bad})
        with self.assertRaisesRegex(ValueError, "position_weight_cap"):
            load_routing_thresholds(path)

    def test_evaluate_execution_mode_is_pure_for_same_inputs(self) -> None:
        candidate = {"ticker": "AAPL", "savings_plan_eligible": "TRUE"}
        first = evaluate_execution_mode(candidate, {}, self.thresholds)
        second = evaluate_execution_mode(candidate, {}, self.thresholds)
        self.assertEqual(first, second)
        self.assertEqual(candidate, {"ticker": "AAPL", "savings_plan_eligible": "TRUE"})

    def test_execution_mode_reason_is_always_non_empty(self) -> None:
        rows = route_candidates([{"ticker": "AAPL", "target_action": "BUY"}, {"ticker": "MSFT", "target_action": "DO_NOT_BUY"}], {}, self.thresholds, {"BUY"})
        self.assertTrue(all(row["execution_mode_reason"] for row in rows))

    def test_aggregate_summary_is_not_used_for_per_ticker_lookup(self) -> None:
        summary_path = self.tmp / "savings_plan_registry_summary.csv"
        summary_path.write_text("row_count,active_count,inactive_count,total_monthly_eur,next_execution_day,warning_count,drift_warnings,data_quality_flag\n1,1,0,50.00,2,0,,OK\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            load_savings_plan_lookup(summary_path)

    def test_load_savings_plan_lookup_uses_registry_rows(self) -> None:
        path = self.write_registry([self.plan(active="FALSE")])
        lookup = load_savings_plan_lookup(path)
        self.assertEqual(lookup["MSFT"]["savings_plan_active"], "FALSE")
        self.assertEqual(lookup["MSFT"]["execution_day_of_month"], "2")

    def test_routing_csv_header_order_is_stable(self) -> None:
        output = self.tmp / "routing.csv"
        write_routing_csv([{"ticker": "AAPL", "execution_mode": "SAVINGS_PLAN_NEW", "execution_mode_reason": "eligible_for_new_plan"}], output)
        self.assertEqual(output.read_text(encoding="utf-8").splitlines()[0], ",".join(ROUTING_FIELDS))

    def test_cli_help_exits_zero(self) -> None:
        result = subprocess.run(["python", "-m", "src.savings_plan_routing", "--help"], cwd=Path.cwd(), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--registry-input", result.stdout)


if __name__ == "__main__":
    unittest.main()
