from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from src.rebalance_review import (
    REBALANCE_BUCKETS,
    REBALANCE_REVIEW_FIELDS,
    build_rebalance_report,
    evaluate_rebalance,
    write_rebalance_csv,
)


class RebalanceReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / "_tmp_rebalance_review"
        self.tmp.mkdir(exist_ok=True)
        self.rules = {
            "target_core_etf_min": 0.45,
            "target_core_etf_max": 0.60,
            "target_dividend_quality_etf_min": 0.10,
            "target_dividend_quality_etf_max": 0.25,
            "target_single_stocks_min": 0.20,
            "target_single_stocks_max": 0.35,
            "target_cash_min": 0.05,
            "target_cash_max": 0.15,
            "monthly_new_cash_eur": 500.0,
        }
        self.thresholds = {
            "tolerance_band_multiplier": 2.0,
            "rebalance_action_thresholds": {
                "underweight_action_threshold_pct": 0.02,
                "overweight_trim_band_multiplier": 2.0,
            },
        }

    def tearDown(self) -> None:
        for path in sorted(self.tmp.glob("*"), reverse=True):
            path.unlink()
        if self.tmp.exists():
            self.tmp.rmdir()

    def rows(self, core: float, dividend: float, single: float, cash: float, extra: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
        base = [
            {"portfolio_date": "2026-05-01", "ticker": "CORE", "asset_type": "ETF", "sleeve": "CORE_ETF", "market_value_eur": str(core)},
            {"portfolio_date": "2026-05-01", "ticker": "DIV", "asset_type": "ETF", "sleeve": "DIVIDEND_QUALITY_ETF", "market_value_eur": str(dividend)},
            {"portfolio_date": "2026-05-01", "ticker": "STK", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": str(single)},
            {"portfolio_date": "2026-05-01", "ticker": "EUR-CASH", "asset_type": "CASH", "sleeve": "CASH", "market_value_eur": str(cash)},
        ]
        return base + list(extra or [])

    def by_bucket(self, rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
        return {row["bucket"]: row for row in rows}

    def test_all_buckets_within_band_hold(self) -> None:
        rows = evaluate_rebalance(self.rows(5000, 1500, 2500, 1000), self.rules, self.thresholds, 500.0)
        self.assertTrue(all(row["band_status"] == "WITHIN_BAND" for row in rows))
        self.assertTrue(all(row["recommended_action"] == "HOLD" for row in rows))

    def test_core_underweight_deploys_new_cash(self) -> None:
        result = self.by_bucket(evaluate_rebalance(self.rows(4100, 2000, 2900, 1000), self.rules, self.thresholds, 500.0))
        self.assertEqual(result["CORE_ETF"]["band_status"], "UNDERWEIGHT")
        self.assertEqual(result["CORE_ETF"]["recommended_action"], "DEPLOY_NEW_CASH")

    def test_core_extremely_underweight_deploys_new_cash_without_other_bucket_sale(self) -> None:
        result = evaluate_rebalance(self.rows(1000, 2500, 5500, 1000), self.rules, self.thresholds, 500.0)
        core = self.by_bucket(result)["CORE_ETF"]
        self.assertEqual(core["band_status"], "EXTREMELY_UNDERWEIGHT")
        self.assertEqual(core["recommended_action"], "DEPLOY_NEW_CASH")
        self.assertNotIn("SELL", {row["recommended_action"] for row in result})

    def test_single_stocks_overweight_is_hold_with_cash_first_reason(self) -> None:
        result = self.by_bucket(evaluate_rebalance(self.rows(4500, 1000, 4000, 500), self.rules, self.thresholds, 500.0))
        single = result["SINGLE_STOCK"]
        self.assertEqual(single["band_status"], "OVERWEIGHT")
        self.assertEqual(single["recommended_action"], "HOLD")
        self.assertIn("deploy_new_cash_first", single["reason"])

    def test_single_stocks_extremely_overweight_gets_qualitative_trim_marker(self) -> None:
        result = self.by_bucket(evaluate_rebalance(self.rows(1000, 1000, 7500, 500), self.rules, self.thresholds, 500.0))
        single = result["SINGLE_STOCK"]
        self.assertEqual(single["band_status"], "EXTREMELY_OVERWEIGHT")
        self.assertEqual(single["recommended_action"], "TRIM_FOR_REBALANCE_REVIEW")

    def test_trim_marker_has_no_tax_or_order_amount_fields(self) -> None:
        forbidden = {
            "realized_gain_eur",
            "estimated_kest_eur",
            "tax_optimal_trim_eur",
            "tax_estimate",
            "sell_amount_eur",
            "order_amount_eur",
        }
        self.assertTrue(forbidden.isdisjoint(REBALANCE_REVIEW_FIELDS))

    def test_estimated_months_to_correct_uses_ceiling(self) -> None:
        result = self.by_bucket(evaluate_rebalance(self.rows(4100, 2000, 2900, 1000), self.rules, self.thresholds, 300.0))
        self.assertEqual(result["CORE_ETF"]["estimated_months_to_correct_via_cashflow"], "2")

    def test_empty_positions_return_four_rows_with_positions_missing(self) -> None:
        rows = evaluate_rebalance([], self.rules, self.thresholds, 500.0)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["data_quality_flag"] == "POSITIONS_MISSING" for row in rows))

    def test_cash_bucket_always_present_without_cash_sleeve(self) -> None:
        rows = evaluate_rebalance(self.rows(5000, 1500, 2500, 0)[:-1], self.rules, self.thresholds, 500.0)
        self.assertIn("CASH", self.by_bucket(rows))

    def test_row_count_exactly_four(self) -> None:
        self.assertEqual(len(evaluate_rebalance(self.rows(5000, 1500, 2500, 1000), self.rules, self.thresholds, 500.0)), 4)

    def test_output_order_is_stable(self) -> None:
        rows = evaluate_rebalance(self.rows(5000, 1500, 2500, 1000), self.rules, self.thresholds, 500.0)
        self.assertEqual([row["bucket"] for row in rows], REBALANCE_BUCKETS)

    def test_drift_signs(self) -> None:
        result = self.by_bucket(evaluate_rebalance(self.rows(4100, 1500, 3900, 500), self.rules, self.thresholds, 500.0))
        self.assertLess(float(result["CORE_ETF"]["drift_pct"]), 0.0)
        self.assertGreater(float(result["SINGLE_STOCK"]["drift_pct"]), 0.0)
        self.assertEqual(result["DIVIDEND_QUALITY_ETF"]["drift_pct"], "0")

    def test_tolerance_multiplier_is_configurable(self) -> None:
        loose = evaluate_rebalance(self.rows(2000, 2500, 4500, 1000), self.rules, self.thresholds, 500.0)
        strict_thresholds = {**self.thresholds, "tolerance_band_multiplier": 1.5}
        strict = evaluate_rebalance(self.rows(2000, 2500, 4500, 1000), self.rules, strict_thresholds, 500.0)
        self.assertEqual(self.by_bucket(loose)["CORE_ETF"]["band_status"], "UNDERWEIGHT")
        self.assertEqual(self.by_bucket(strict)["CORE_ETF"]["band_status"], "EXTREMELY_UNDERWEIGHT")

    def test_csv_header_preserves_schema_order(self) -> None:
        output = self.tmp / "rebalance.csv"
        write_rebalance_csv(evaluate_rebalance(self.rows(5000, 1500, 2500, 1000), self.rules, self.thresholds, 500.0), output)
        self.assertEqual(output.read_text(encoding="utf-8").splitlines()[0].split(","), REBALANCE_REVIEW_FIELDS)

    def test_evaluate_rebalance_is_deterministic(self) -> None:
        first = evaluate_rebalance(self.rows(5000, 1500, 2500, 1000), self.rules, self.thresholds, 500.0)
        second = evaluate_rebalance(self.rows(5000, 1500, 2500, 1000), self.rules, self.thresholds, 500.0)
        self.assertEqual(first, second)

    def test_overweight_reason_contains_cash_first_marker(self) -> None:
        row = self.by_bucket(evaluate_rebalance(self.rows(4500, 1000, 4000, 500), self.rules, self.thresholds, 500.0))["SINGLE_STOCK"]
        self.assertIn("deploy_new_cash_first", row["reason"])

    def test_cli_help_exits_zero(self) -> None:
        result = subprocess.run(["python", "-m", "src.rebalance_review", "--help"], cwd=Path.cwd(), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("--positions", result.stdout)

    def test_review_sleeve_is_not_silently_included_in_single_stock(self) -> None:
        result = self.by_bucket(
            evaluate_rebalance(
                self.rows(5000, 1500, 2500, 1000, extra=[{"ticker": "REV", "asset_type": "OTHER", "sleeve": "REVIEW", "market_value_eur": "1000"}]),
                self.rules,
                self.thresholds,
                500.0,
            )
        )
        self.assertEqual(result["SINGLE_STOCK"]["current_eur"], "2500")
        self.assertEqual(result["SINGLE_STOCK"]["data_quality_flag"], "RULE_GAP")
        self.assertIn("review_sleeve_excluded", result["SINGLE_STOCK"]["reason"])

    def test_non_core_maps_to_single_stock(self) -> None:
        rows = self.rows(5000, 1500, 0, 1000, extra=[{"ticker": "NC", "asset_type": "OTHER", "sleeve": "NON_CORE", "market_value_eur": "2500"}])
        result = self.by_bucket(evaluate_rebalance(rows, self.rules, self.thresholds, 500.0))
        self.assertEqual(result["SINGLE_STOCK"]["current_eur"], "2500")

    def test_report_contains_empty_state_and_qualitative_marker(self) -> None:
        empty_output = self.tmp / "empty.md"
        build_rebalance_report(evaluate_rebalance([], self.rules, self.thresholds, 500.0), empty_output)
        self.assertIn("EMPTY_STATE", empty_output.read_text(encoding="utf-8"))
        trim_output = self.tmp / "trim.md"
        build_rebalance_report(evaluate_rebalance(self.rows(1000, 1000, 7500, 500), self.rules, self.thresholds, 500.0), trim_output)
        self.assertIn("Qualitative review marker only; no tax or order amount is calculated.", trim_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
