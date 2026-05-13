from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path

from src.cash_refill_review import (
    CASH_REFILL_FIELDS,
    build_cash_refill_report,
    evaluate_cash_refill,
    load_health_thresholds,
    write_cash_refill_csv,
)


class CashRefillReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / "_tmp_cash_refill_review"
        self.tmp.mkdir(exist_ok=True)
        self.rules = {
            "min_cash_reserve_eur": 1500.0,
            "target_cash_min": 0.05,
        }
        self.thresholds = {"cash_refill_margin_pct": 0.01, "rebalance_action_thresholds": {}, "tolerance_band_multiplier": 2.0, "months_to_floor_warning_threshold": 3}

    def tearDown(self) -> None:
        for path in sorted(self.tmp.glob("*"), reverse=True):
            path.unlink()
        if self.tmp.exists():
            self.tmp.rmdir()

    def rows(self, cash: float, core: float = 20000.0, stock: float = 8000.0) -> list[dict[str, str]]:
        return [
            {"portfolio_date": "2026-05-01", "ticker": "CORE", "asset_type": "ETF", "sleeve": "CORE_ETF", "market_value_eur": str(core)},
            {"portfolio_date": "2026-05-01", "ticker": "STK", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": str(stock)},
            {"portfolio_date": "2026-05-01", "ticker": "EUR-CASH", "asset_type": "CASH", "sleeve": "CASH", "market_value_eur": str(cash)},
        ]

    def test_cash_above_reserve_and_floor_not_required(self) -> None:
        record = evaluate_cash_refill(self.rows(cash=3000.0), self.rules, self.thresholds)
        self.assertEqual(record["status"], "CASH_REFILL_NOT_REQUIRED")
        self.assertEqual(record["trigger"], "NONE")

    def test_cash_below_min_reserve_only_required(self) -> None:
        rules = {**self.rules, "min_cash_reserve_eur": 5000.0, "target_cash_min": 0.01}
        record = evaluate_cash_refill(self.rows(cash=3000.0), rules, self.thresholds)
        self.assertEqual(record["status"], "CASH_REFILL_REQUIRED")
        self.assertEqual(record["trigger"], "BELOW_MIN_RESERVE")

    def test_cash_below_bucket_floor_only_required(self) -> None:
        rules = {**self.rules, "min_cash_reserve_eur": 500.0, "target_cash_min": 0.10}
        record = evaluate_cash_refill(self.rows(cash=2000.0), rules, self.thresholds)
        self.assertEqual(record["status"], "CASH_REFILL_REQUIRED")
        self.assertEqual(record["trigger"], "BELOW_BUCKET_FLOOR")

    def test_cash_below_both_required(self) -> None:
        record = evaluate_cash_refill(self.rows(cash=100.0), self.rules, self.thresholds)
        self.assertEqual(record["status"], "CASH_REFILL_REQUIRED")
        self.assertEqual(record["trigger"], "BOTH")

    def test_cash_near_threshold_is_marginal(self) -> None:
        record = evaluate_cash_refill(self.rows(cash=1600.0, core=20000.0, stock=8000.0), self.rules, self.thresholds)
        self.assertEqual(record["status"], "CASH_REFILL_MARGINAL")
        self.assertEqual(record["trigger"], "NEAR_THRESHOLD")

    def test_no_cash_sleeve_is_visible_data_quality(self) -> None:
        rows = [{"ticker": "AAA", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "1000"}]
        record = evaluate_cash_refill(rows, self.rules, self.thresholds)
        self.assertEqual(record["current_cash_eur"], "0")
        self.assertEqual(record["data_quality_flag"], "CASH_SLEEVE_NOT_FOUND")

    def test_empty_positions_are_visible(self) -> None:
        record = evaluate_cash_refill([], self.rules, self.thresholds)
        self.assertEqual(record["data_quality_flag"], "POSITIONS_MISSING")

    def test_months_to_floor_semantics_do_not_use_inflow_as_burn_rate(self) -> None:
        required = evaluate_cash_refill(self.rows(cash=100.0), self.rules, self.thresholds)
        ok = evaluate_cash_refill(self.rows(cash=3000.0), self.rules, self.thresholds)
        self.assertEqual(required["months_to_floor_at_monthly_inflow"], "0")
        self.assertEqual(ok["months_to_floor_at_monthly_inflow"], "")
        self.assertIn("NO_BURN_RATE_AVAILABLE", ok["reason"])

    def test_reason_contains_no_cash_refill_action_antipatterns(self) -> None:
        record = evaluate_cash_refill(self.rows(cash=100.0), self.rules, self.thresholds)
        lowered = record["reason"].lower()
        for term in ("sell", "trim", "exit", "verkaufen", "reduzieren", "abbauen"):
            self.assertNotIn(term, lowered)

    def test_csv_header_preserves_schema_order(self) -> None:
        output = self.tmp / "cash.csv"
        write_cash_refill_csv(evaluate_cash_refill(self.rows(cash=3000.0), self.rules, self.thresholds), output)
        self.assertEqual(output.read_text(encoding="utf-8").splitlines()[0].split(","), CASH_REFILL_FIELDS)

    def test_markdown_report_contains_status_and_empty_state(self) -> None:
        output = self.tmp / "cash.md"
        build_cash_refill_report(evaluate_cash_refill([], self.rules, self.thresholds), output)
        text = output.read_text(encoding="utf-8")
        self.assertIn("Status: `CASH_REFILL_REQUIRED`", text)
        self.assertIn("EMPTY_STATE", text)

    def test_cli_help_exits_zero(self) -> None:
        result = subprocess.run(["python", "-m", "src.cash_refill_review", "--help"], cwd=Path.cwd(), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("--positions", result.stdout)

    def test_evaluate_cash_refill_is_deterministic(self) -> None:
        first = evaluate_cash_refill(self.rows(cash=3000.0), self.rules, self.thresholds)
        second = evaluate_cash_refill(self.rows(cash=3000.0), self.rules, self.thresholds)
        self.assertEqual(first, second)

    def test_no_cash_sleeve_still_writes_csv_and_report(self) -> None:
        rows = [{"ticker": "AAA", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "market_value_eur": "1000"}]
        record = evaluate_cash_refill(rows, self.rules, self.thresholds)
        csv_output = write_cash_refill_csv(record, self.tmp / "no_cash.csv")
        report_output = build_cash_refill_report(record, self.tmp / "no_cash.md")
        self.assertTrue(csv_output.exists())
        self.assertTrue(report_output.exists())

    def test_threshold_loader_accepts_config(self) -> None:
        thresholds = load_health_thresholds()
        self.assertEqual(thresholds["tolerance_band_multiplier"], 2.0)


if __name__ == "__main__":
    unittest.main()
