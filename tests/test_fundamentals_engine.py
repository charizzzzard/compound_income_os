from __future__ import annotations

import csv
import json
import subprocess
import unittest
from pathlib import Path

from src.common import load_yaml_config
from src.fundamentals_engine import (
    build_score_audit_rows,
    detect_fundamentals_format,
    enrich_fundamentals_rows,
)
from src.scoring_engine import build_scores_with_audit


RAW_ROW = {
    "ticker": "RAWX",
    "isin": "US0000000001",
    "company_name": "Raw Quality Co",
    "currency": "EUR",
    "sector": "Technology",
    "country": "USA",
    "asset_type": "STOCK",
    "sleeve": "SINGLE_STOCK",
    "data_quality_flag": "OK",
    "current_price_eur": "100",
    "mandate_fit_score": "90",
    "revenue_cagr_5y": "10",
    "eps_cagr_5y": "12",
    "fcf_per_share_cagr_5y": "11",
    "roic": "20",
    "roce": "18",
    "gross_margin": "65",
    "operating_margin": "30",
    "fcf_margin": "22",
    "net_debt_to_ebitda": "1",
    "interest_coverage": "12",
    "dividend_yield_current_pct": "2",
    "dividend_yield_hist_pct": "1.8",
    "dividend_cagr_5y": "8",
    "dividend_streak_years": "10",
    "payout_ratio_eps": "45",
    "payout_ratio_fcf": "50",
    "share_count_cagr_5y": "-1",
    "buyback_yield": "2",
    "pe_current": "18",
    "pe_hist": "20",
    "ev_ebit_current": "14",
    "ev_ebit_hist": "16",
    "fcf_yield_current_pct": "5",
    "fcf_yield_hist_pct": "4",
    "normalized_fcf_yield_pct": "5.2",
    "target_fcf_yield_pct": "4.5",
    "drawdown_from_high_pct": "20",
    "expected_return_pct": "10",
    "thesis_robustness": "ROBUST",
    "has_hard_risk_flag": "false",
}


class FundamentalsEngineTests(unittest.TestCase):
    def test_raw_fundamentals_schema_is_detected_and_scores_are_deterministic(self) -> None:
        enriched, detected_format = enrich_fundamentals_rows([RAW_ROW], "auto")

        self.assertEqual(detected_format, "raw")
        self.assertEqual(enriched[0]["fundamentals_input_format"], "raw")
        self.assertEqual(enriched[0]["quality_score"], 74.96)
        self.assertEqual(enriched[0]["balance_sheet_score"], 76.61)
        self.assertEqual(enriched[0]["missing_kpi_count"], 0)
        self.assertIn("roic=20", enriched[0]["quality_score_inputs"])

    def test_missing_raw_kpis_degrade_data_quality_without_hallucination(self) -> None:
        sparse = {**RAW_ROW, "ticker": "MISS", "roic": "", "roce": "", "gross_margin": "", "interest_coverage": ""}
        enriched, _ = enrich_fundamentals_rows([sparse], "raw")

        self.assertEqual(enriched[0]["data_quality_flag"], "REVIEW")
        self.assertIn("roic", enriched[0]["missing_kpis"])
        self.assertIn("interest_coverage", enriched[0]["missing_kpis"])
        self.assertIn("MISSING", enriched[0]["quality_score_inputs"])

    def test_legacy_fundamentals_remain_supported(self) -> None:
        rows = [
            {
                "ticker": "LEG",
                "company_name": "Legacy Co",
                "sector": "Tech",
                "country": "USA",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "quality_score": "80",
                "dividend_score": "70",
                "balance_sheet_score": "75",
                "growth_quality_score": "65",
                "capital_allocation_score": "60",
                "pe_current": "18",
            }
        ]
        self.assertEqual(detect_fundamentals_format(rows, "auto"), "legacy")
        enriched, detected_format = enrich_fundamentals_rows(rows, "auto")
        self.assertEqual(detected_format, "legacy")
        self.assertEqual(enriched[0]["quality_score"], "80")
        self.assertEqual(enriched[0]["fundamentals_input_format"], "legacy")

    def test_auto_detection_prefers_raw_when_component_kpis_and_legacy_scores_are_mixed(self) -> None:
        mixed = {**RAW_ROW, "ticker": "rawmix", "quality_score": "1"}
        enriched, detected_format = enrich_fundamentals_rows([mixed], "auto")

        self.assertEqual(detected_format, "raw")
        self.assertEqual(enriched[0]["ticker"], "RAWMIX")
        self.assertEqual(enriched[0]["quality_score"], 74.96)
        self.assertNotEqual(enriched[0]["quality_score"], "1")

    def test_raw_schema_validation_rejects_missing_core_kpi_column(self) -> None:
        invalid = {**RAW_ROW, "roic_typo": RAW_ROW["roic"]}
        invalid.pop("roic")

        with self.assertRaisesRegex(ValueError, "missing required raw fundamentals columns: roic"):
            enrich_fundamentals_rows([invalid], "raw", source_name="test raw fundamentals")

    def test_fundamentals_blank_ticker_is_rejected(self) -> None:
        invalid = {**RAW_ROW, "ticker": "   ", "isin": "US0000000001"}

        with self.assertRaisesRegex(ValueError, "test raw fundamentals row 2 has blank required field\\(s\\): ticker"):
            enrich_fundamentals_rows([invalid], "raw", source_name="test raw fundamentals")

    def test_component_weight_validation_rejects_bad_sums(self) -> None:
        rules_path = Path("tests") / "_tmp_bad_fundamentals_score_rules.yaml"
        rules = load_yaml_config("configs/fundamentals_score_rules.yaml")
        rules["component_scores"]["quality_score"]["roic"] = 0.5
        try:
            rules_path.write_text(json.dumps(rules, indent=2), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "quality_score.*weights sum to 1.2"):
                enrich_fundamentals_rows([RAW_ROW], "raw", rules_path=str(rules_path))
        finally:
            if rules_path.exists():
                rules_path.unlink()

    def test_buy_score_contributions_are_auditable_and_consistent(self) -> None:
        positions = [
            {
                "ticker": "RAWX",
                "isin": "US0000000001",
                "company_name": "Raw Quality Co",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "sector": "Technology",
                "market_value_eur": "100",
                "cost_basis_eur": "90",
                "price_eur": "100",
            }
        ]
        scores, enriched, audit = build_scores_with_audit(positions, [RAW_ROW], fundamentals_format="raw")

        row = next(score for score in scores if score["ticker"] == "RAWX")
        contribution_sum = round(
            row["business_score_contribution"]
            + row["valuation_score_contribution"]
            + row["expected_return_score_contribution"]
            + row["drawdown_score_contribution"]
            + row["portfolio_fit_score_contribution"],
            2,
        )
        self.assertEqual(row["fundamentals_input_format"], "raw")
        self.assertAlmostEqual(contribution_sum, row["buy_score"], places=2)
        self.assertEqual(enriched[0]["fundamentals_input_format"], "raw")
        self.assertEqual(audit[0]["fundamentals_input_format"], "raw")
        self.assertIn("roic=20", audit[0]["quality_score_inputs"])
        self.assertGreater(row["pe_relative_ratio"], 0.0)

    def test_scoring_cli_writes_score_audit_csv(self) -> None:
        positions_path = Path("tests") / "_tmp_positions_raw.csv"
        fundamentals_path = Path("tests") / "_tmp_fundamentals_raw.csv"
        output_path = Path("tests") / "_tmp_scores_raw.csv"
        audit_path = Path("tests") / "_tmp_score_audit.csv"
        enriched_path = Path("tests") / "_tmp_fundamentals_enriched.csv"
        try:
            with positions_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["ticker", "isin", "company_name", "asset_type", "sleeve", "sector", "market_value_eur", "cost_basis_eur", "price_eur"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "ticker": "RAWX",
                        "isin": "US0000000001",
                        "company_name": "Raw Quality Co",
                        "asset_type": "STOCK",
                        "sleeve": "SINGLE_STOCK",
                        "sector": "Technology",
                        "market_value_eur": "100",
                        "cost_basis_eur": "90",
                        "price_eur": "100",
                    }
                )
            with fundamentals_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(RAW_ROW.keys()))
                writer.writeheader()
                writer.writerow(RAW_ROW)

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.scoring_engine",
                    "--positions",
                    str(positions_path),
                    "--fundamentals",
                    str(fundamentals_path),
                    "--fundamentals-format",
                    "raw",
                    "--output",
                    str(output_path),
                    "--audit-output",
                    str(audit_path),
                    "--enriched-output",
                    str(enriched_path),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with audit_path.open(encoding="utf-8") as handle:
                audit_rows = list(csv.DictReader(handle))
            self.assertEqual(audit_rows[0]["ticker"], "RAWX")
            self.assertEqual(audit_rows[0]["fundamentals_input_format"], "raw")
            self.assertIn("business_score_contribution", audit_rows[0])
            self.assertIn("roic", audit_rows[0])
            self.assertTrue(enriched_path.exists())
        finally:
            for path in [positions_path, fundamentals_path, output_path, audit_path, enriched_path]:
                if path.exists():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()
