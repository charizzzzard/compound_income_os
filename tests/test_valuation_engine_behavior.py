from __future__ import annotations

import unittest
from pathlib import Path

from src.valuation_engine import compute_valuation_metrics, fair_value_from_ratio, relative_score, safe_ratio

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "docs" / "contracts" / "VALUATION_ENGINE_BOUNDARY_CONTRACT.md"


def complete_row() -> dict[str, str]:
    return {
        "current_price_eur": "100",
        "pe_current": "20",
        "pe_hist": "15",
        "ev_ebit_current": "12",
        "ev_ebit_hist": "10",
        "fcf_yield_current_pct": "5",
        "fcf_yield_hist_pct": "4",
        "normalized_fcf_yield_pct": "6",
        "target_fcf_yield_pct": "5",
        "dividend_yield_current_pct": "3",
        "dividend_yield_hist_pct": "2.5",
        "data_quality_flag": "OK",
    }


class ValuationEngineBehaviorTests(unittest.TestCase):
    def test_relative_score_invalid_inputs_return_fallback_and_not_ok(self) -> None:
        score, ok = relative_score(0.0, 10.0, True)

        self.assertEqual(score, 35.0)
        self.assertFalse(ok)

    def test_relative_score_lower_and_higher_is_better_behave_as_expected(self) -> None:
        lower_score, lower_ok = relative_score(10.0, 5.0, False)
        higher_score, higher_ok = relative_score(10.0, 5.0, True)

        self.assertEqual(lower_score, 20.0)
        self.assertTrue(lower_ok)
        self.assertEqual(higher_score, 100.0)
        self.assertTrue(higher_ok)

    def test_relative_score_extreme_values_are_clamped(self) -> None:
        high_score, high_ok = relative_score(1000.0, 1.0, True)
        low_score, low_ok = relative_score(1000.0, 1.0, False)

        self.assertEqual(high_score, 100.0)
        self.assertTrue(high_ok)
        self.assertEqual(low_score, 0.0)
        self.assertTrue(low_ok)

    def test_fair_value_from_ratio_valid_and_invalid_inputs(self) -> None:
        value, ok = fair_value_from_ratio(100.0, 15.0, 20.0)
        invalid_value, invalid_ok = fair_value_from_ratio(0.0, 15.0, 20.0)

        self.assertEqual(value, 75.0)
        self.assertTrue(ok)
        self.assertIsNone(invalid_value)
        self.assertFalse(invalid_ok)
        self.assertEqual(fair_value_from_ratio(100.0, 0.0, 20.0), (None, False))
        self.assertEqual(fair_value_from_ratio(100.0, 15.0, 0.0), (None, False))

    def test_safe_ratio_valid_and_invalid_inputs(self) -> None:
        self.assertEqual(safe_ratio(3.0, 2.0), 1.5)
        self.assertEqual(safe_ratio(0.0, 2.0), 0.0)
        self.assertEqual(safe_ratio(2.0, 0.0), 0.0)

    def test_compute_valuation_metrics_complete_synthetic_row(self) -> None:
        metrics = compute_valuation_metrics(complete_row())

        self.assertEqual(metrics["historical_multiple_score"], 55.56)
        self.assertEqual(metrics["normalized_fcf_score"], 76.0)
        self.assertEqual(metrics["dividend_yield_relative_score"], 76.0)
        self.assertEqual(metrics["fair_value_score"], 67.82)
        self.assertEqual(metrics["fair_value_estimate"], 109.78)
        self.assertEqual(metrics["margin_of_safety_pct"], 9.78)
        self.assertEqual(metrics["data_quality_flag"], "OK")
        self.assertIn("nahe am geschaetzten Fair Value", metrics["valuation_comment"])
        self.assertEqual(metrics["pe_relative_ratio"], 0.75)
        self.assertEqual(metrics["ev_ebit_relative_ratio"], 0.83)
        self.assertEqual(metrics["fcf_yield_relative_ratio"], 1.25)
        self.assertEqual(metrics["normalized_fcf_gap"], 1.0)
        self.assertEqual(metrics["dividend_yield_relative_ratio"], 1.2)

    def test_compute_valuation_metrics_missing_data_is_conservative_and_visible(self) -> None:
        metrics = compute_valuation_metrics({"current_price_eur": "100"})

        self.assertEqual(metrics["fair_value_score"], 35.0)
        self.assertEqual(metrics["fair_value_estimate"], 100.0)
        self.assertEqual(metrics["margin_of_safety_pct"], 0.0)
        self.assertEqual(metrics["data_quality_flag"], "MISSING_DATA")
        self.assertIn("Bewertungsinputs fehlen", metrics["valuation_comment"])
        self.assertIn("konservativ", metrics["valuation_comment"])
        self.assertEqual(metrics["pe_relative_ratio"], 0.0)
        self.assertEqual(metrics["ev_ebit_relative_ratio"], 0.0)
        self.assertEqual(metrics["fcf_yield_relative_ratio"], 0.0)
        self.assertEqual(metrics["normalized_fcf_gap"], 0.0)
        self.assertEqual(metrics["dividend_yield_relative_ratio"], 0.0)

    def test_compute_valuation_metrics_partial_missing_data_degrades_to_review(self) -> None:
        row = complete_row()
        row["normalized_fcf_yield_pct"] = ""

        metrics = compute_valuation_metrics(row)

        self.assertEqual(metrics["normalized_fcf_score"], 35.0)
        self.assertEqual(metrics["data_quality_flag"], "REVIEW")

    def test_compute_valuation_metrics_preserves_review_and_missing_data_semantics(self) -> None:
        review_row = complete_row()
        review_row["data_quality_flag"] = "REVIEW"
        review_row["normalized_fcf_yield_pct"] = ""
        missing_row = complete_row()
        missing_row["data_quality_flag"] = "REVIEW"
        for field in ("pe_current", "pe_hist", "ev_ebit_current"):
            missing_row[field] = ""

        self.assertEqual(compute_valuation_metrics(review_row)["data_quality_flag"], "REVIEW")
        self.assertEqual(compute_valuation_metrics(missing_row)["data_quality_flag"], "MISSING_DATA")

    def test_compute_valuation_metrics_preserves_conflict_stale_unknown_and_blocked_flags(self) -> None:
        for flag in ("CONFLICT", "STALE", "UNKNOWN", "BLOCKED", "INVALID"):
            with self.subTest(flag=flag):
                row = complete_row()
                row["data_quality_flag"] = flag
                metrics = compute_valuation_metrics(row)
                self.assertEqual(metrics["data_quality_flag"], flag)
                self.assertIn("Bewertungsinputs pruefen", metrics["valuation_comment"])
                self.assertIn("konservativ", metrics["valuation_comment"])

    def test_malformed_numeric_inputs_do_not_create_confident_ok_state(self) -> None:
        malformed_values = ["", "N/A", "--", "not-a-number"]
        for value in malformed_values:
            with self.subTest(value=value):
                row = complete_row()
                row["pe_current"] = value
                metrics = compute_valuation_metrics(row)
                self.assertNotEqual(metrics["data_quality_flag"], "OK")
                self.assertIn(metrics["data_quality_flag"], {"REVIEW", "MISSING_DATA"})
                self.assertIn("konservativ", metrics["valuation_comment"])

    def test_invalid_current_price_with_complete_inputs_is_review_not_ok(self) -> None:
        for price in ("0", "-100", "not-a-number"):
            with self.subTest(price=price):
                row = complete_row()
                row["current_price_eur"] = price
                metrics = compute_valuation_metrics(row)
                self.assertEqual(metrics["margin_of_safety_pct"], 0.0)
                self.assertNotEqual(metrics["data_quality_flag"], "OK")
                self.assertIn("konservativ", metrics["valuation_comment"])

    def test_invalid_or_zero_current_price_does_not_crash_and_keeps_expected_keys(self) -> None:
        expected_keys = {
            "historical_multiple_score",
            "normalized_fcf_score",
            "dividend_yield_relative_score",
            "fair_value_score",
            "fair_value_estimate",
            "margin_of_safety_pct",
            "valuation_comment",
            "data_quality_flag",
            "pe_relative_ratio",
            "ev_ebit_relative_ratio",
            "fcf_yield_relative_ratio",
            "normalized_fcf_gap",
            "dividend_yield_relative_ratio",
        }

        for price in ("0", "-1", "not-a-number"):
            with self.subTest(price=price):
                metrics = compute_valuation_metrics({"current_price_eur": price})
                self.assertEqual(set(metrics), expected_keys)
                self.assertEqual(metrics["margin_of_safety_pct"], 0.0)
                self.assertNotEqual(metrics["data_quality_flag"], "OK")

    def test_boundary_contract_contains_required_non_claims(self) -> None:
        text = CONTRACT_PATH.read_text(encoding="utf-8").lower()

        for phrase in [
            "no investment advice",
            "no order execution",
            "no valuation automation",
            "missing",
            "stale",
            "unknown",
            "fallback",
            "not silent",
            "human operator",
        ]:
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
