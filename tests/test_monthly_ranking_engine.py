from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path
import json
from unittest.mock import patch

from src.common import read_csv_rows
from src.fundamentals_master import COVERAGE_OUTPUT_FIELDS
from src.monthly_ranking_engine import OUTPUT_FIELDS, build_monthly_ranking
from src.portfolio_rules import load_portfolio_rules


PRE_ROUTING_OUTPUT_FIELDS = [
    "rank",
    "ticker",
    "company_name",
    "current_weight",
    "target_action",
    "allocation_status",
    "suggested_buy_amount_eur",
    "rationale",
    "constraint_checks",
    "valuation_comment",
    "mandate_fit_comment",
]


class MonthlyRankingEngineTests(unittest.TestCase):
    def write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def eligible_holding_fixture(self) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
        positions = [
            {"ticker": "AAA", "company_name": "AAA", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "sector": "Tech", "market_value_eur": "200"},
            {"ticker": "BBB", "company_name": "BBB", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "sector": "Health", "market_value_eur": "200"},
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
            },
            {
                "ticker": "BBB",
                "company_name": "BBB",
                "sector": "Health",
                "sleeve": "SINGLE_STOCK",
                "held_in_portfolio": "true",
                "business_score": "84",
                "valuation_score": "70",
                "buy_score": "79",
                "margin_of_safety_pct": "10",
                "classification": "HOLD",
                "has_hard_risk_flag": "false",
                "data_quality_flag": "OK",
                "valuation_comment": "Attractive.",
                "mandate_fit_score": "90",
            },
        ]
        return positions, scores, []

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

    def test_output_fields_append_execution_mode_fields(self) -> None:
        self.assertEqual(OUTPUT_FIELDS[:-2], PRE_ROUTING_OUTPUT_FIELDS)
        self.assertEqual(OUTPUT_FIELDS[-2:], ["execution_mode", "execution_mode_reason"])

    def test_non_buy_rows_get_empty_execution_mode(self) -> None:
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
        watchlist = [{"ticker": "BAD", "company_name": "Bad Co", "sector": "Tech", "sleeve": "SINGLE_STOCK", "status": "REJECT"}]
        ranking, _ = build_monthly_ranking(positions, scores, watchlist)
        self.assertEqual(ranking[0]["execution_mode"], "")
        self.assertEqual(ranking[0]["execution_mode_reason"], "not_a_buy_candidate")

    def test_buy_row_gets_allowed_execution_mode(self) -> None:
        positions, scores, watchlist = self.eligible_holding_fixture()
        ranking, _ = build_monthly_ranking(positions, scores, watchlist)
        self.assertIn(
            ranking[0]["execution_mode"],
            {"SAVINGS_PLAN_EXISTING", "SAVINGS_PLAN_NEW", "SINGLE_ORDER", "NO_RECOMMENDATION"},
        )
        self.assertTrue(ranking[0]["execution_mode_reason"])

    def test_routing_thresholds_are_loaded_once_per_run(self) -> None:
        positions, scores, watchlist = self.eligible_holding_fixture()
        with patch("src.monthly_ranking_engine.load_routing_thresholds") as loader:
            loader.return_value = {
                "drawdown_opportunity_threshold": 70.0,
                "material_underweight_gap_pct": 1.0,
                "single_order_min_amount_eur": 200.0,
                "max_fee_ratio": 0.005,
                "max_wait_days_for_savings_plan": 14,
                "buy_gate_business_score": 60.0,
                "buy_gate_valuation_score": 60.0,
                "position_weight_cap": 0.10,
            }
            build_monthly_ranking(positions, scores, watchlist)
        loader.assert_called_once()

    def test_savings_plan_lookup_is_loaded_once_per_run(self) -> None:
        positions, scores, watchlist = self.eligible_holding_fixture()
        with patch("src.monthly_ranking_engine.load_savings_plan_lookup", return_value={}) as loader:
            build_monthly_ranking(positions, scores, watchlist)
        loader.assert_called_once()

    def test_no_routing_mode_for_non_buy_candidates(self) -> None:
        positions, scores, watchlist = self.eligible_holding_fixture()
        scores[0]["business_score"] = "40"
        scores[0]["valuation_score"] = "30"
        scores[0]["buy_score"] = "35"
        scores[1]["business_score"] = "40"
        scores[1]["valuation_score"] = "30"
        scores[1]["buy_score"] = "35"
        ranking, _ = build_monthly_ranking(positions, scores, watchlist)
        non_buy_rows = [row for row in ranking if str(row["target_action"]).upper() not in {"BUY", "TOP_UP"}]
        self.assertTrue(non_buy_rows)
        self.assertTrue(all(row["execution_mode"] == "" for row in non_buy_rows))

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

    def test_zero_eur_rows_are_marked_as_eligible_not_funded(self) -> None:
        positions = [
            {"ticker": "EUR-CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": "5000"},
        ]
        scores = [
            {
                "ticker": "AAA",
                "company_name": "Alpha",
                "sector": "Tech",
                "sleeve": "SINGLE_STOCK",
                "held_in_portfolio": "false",
                "business_score": "82",
                "valuation_score": "65",
                "buy_score": "76",
                "margin_of_safety_pct": "10",
                "classification": "BUY_CANDIDATE",
                "has_hard_risk_flag": "false",
                "data_quality_flag": "OK",
                "valuation_comment": "Attractive.",
                "mandate_fit_score": "90",
            },
            {
                "ticker": "BBB",
                "company_name": "Beta",
                "sector": "Tech",
                "sleeve": "SINGLE_STOCK",
                "held_in_portfolio": "false",
                "business_score": "81",
                "valuation_score": "64",
                "buy_score": "75",
                "margin_of_safety_pct": "9",
                "classification": "BUY_CANDIDATE",
                "has_hard_risk_flag": "false",
                "data_quality_flag": "OK",
                "valuation_comment": "Attractive.",
                "mandate_fit_score": "89",
            },
        ]
        watchlist = [
            {"ticker": "AAA", "company_name": "Alpha", "sector": "Tech", "sleeve": "SINGLE_STOCK", "status": "QUALITY_COMPOUNDER_CANDIDATE", "mandate_fit_comment": "Good fit."},
            {"ticker": "BBB", "company_name": "Beta", "sector": "Tech", "sleeve": "SINGLE_STOCK", "status": "QUALITY_COMPOUNDER_CANDIDATE", "mandate_fit_comment": "Good fit."},
        ]
        ranking, _ = build_monthly_ranking(positions, scores, watchlist)
        self.assertEqual(ranking[0]["allocation_status"], "SELECTED_THIS_MONTH")
        self.assertEqual(ranking[1]["allocation_status"], "ELIGIBLE_NOT_FUNDED")
        self.assertEqual(ranking[1]["suggested_buy_amount_eur"], 0.0)
        self.assertEqual(ranking[1]["target_action"], "BUY")
        self.assertIn("kaufbarkeit=KAUFBAR", ranking[0]["constraint_checks"])

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

    def test_coverage_review_and_no_match_block_existing_holdings_for_top_up(self) -> None:
        positions, scores, watchlist = self.eligible_holding_fixture()
        coverage = [
            {"ticker": "AAA", "match_status": "REVIEW", "match_method": "COMPANY_NAME", "missing_required_kpis": "", "needs_research_flag": "False"},
            {"ticker": "BBB", "match_status": "NO_MATCH", "match_method": "NO_MATCH", "missing_required_kpis": "", "needs_research_flag": "True"},
        ]
        ranking, _ = build_monthly_ranking(positions, scores, watchlist, coverage_rows=coverage)
        indexed = {row["ticker"]: row for row in ranking}
        self.assertEqual(indexed["AAA"]["target_action"], "DO_NOT_BUY")
        self.assertEqual(indexed["AAA"]["allocation_status"], "NOT_ELIGIBLE")
        self.assertEqual(indexed["AAA"]["suggested_buy_amount_eur"], 0.0)
        self.assertIn("fundamentals_coverage_guardrail=AKTIV", indexed["AAA"]["constraint_checks"])
        self.assertIn("status=REVIEW", indexed["AAA"]["constraint_checks"])
        self.assertEqual(indexed["BBB"]["target_action"], "DO_NOT_BUY")
        self.assertEqual(indexed["BBB"]["suggested_buy_amount_eur"], 0.0)
        self.assertIn("status=NO_MATCH", indexed["BBB"]["constraint_checks"])

    def test_coverage_research_flag_and_missing_required_block_existing_holding_for_top_up(self) -> None:
        positions, scores, watchlist = self.eligible_holding_fixture()
        coverage = [
            {"ticker": "AAA", "match_status": "COVERED", "match_method": "ISIN", "missing_required_kpis": "", "needs_research_flag": "True"},
            {"ticker": "BBB", "match_status": "COVERED", "match_method": "ISIN", "missing_required_kpis": "roic|fcf_margin", "needs_research_flag": "False"},
        ]
        ranking, _ = build_monthly_ranking(positions, scores, watchlist, coverage_rows=coverage)
        indexed = {row["ticker"]: row for row in ranking}
        self.assertEqual(indexed["AAA"]["target_action"], "DO_NOT_BUY")
        self.assertEqual(indexed["AAA"]["allocation_status"], "NOT_ELIGIBLE")
        self.assertEqual(indexed["AAA"]["suggested_buy_amount_eur"], 0.0)
        self.assertIn("needs_research=True", indexed["AAA"]["constraint_checks"])
        self.assertEqual(indexed["BBB"]["target_action"], "DO_NOT_BUY")
        self.assertEqual(indexed["BBB"]["allocation_status"], "NOT_ELIGIBLE")
        self.assertEqual(indexed["BBB"]["suggested_buy_amount_eur"], 0.0)
        self.assertIn("missing_required=roic|fcf_margin", indexed["BBB"]["constraint_checks"])

    def test_coverage_guardrail_does_not_block_external_watchlist_candidate(self) -> None:
        positions = [
            {"ticker": "EUR-CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": "5000"},
        ]
        scores = [
            {
                "ticker": "AAA",
                "company_name": "Alpha",
                "sector": "Tech",
                "sleeve": "SINGLE_STOCK",
                "held_in_portfolio": "false",
                "business_score": "85",
                "valuation_score": "70",
                "buy_score": "80",
                "margin_of_safety_pct": "10",
                "classification": "BUY_CANDIDATE",
                "has_hard_risk_flag": "false",
                "data_quality_flag": "OK",
                "valuation_comment": "Attractive.",
                "mandate_fit_score": "90",
            }
        ]
        watchlist = [{"ticker": "AAA", "company_name": "Alpha", "sector": "Tech", "sleeve": "SINGLE_STOCK", "status": "QUALITY_COMPOUNDER_CANDIDATE", "mandate_fit_comment": "Good fit."}]
        coverage = [{"ticker": "AAA", "match_status": "NO_MATCH", "match_method": "NO_MATCH", "missing_required_kpis": "", "needs_research_flag": "True"}]
        ranking, _ = build_monthly_ranking(positions, scores, watchlist, coverage_rows=coverage)
        self.assertEqual(ranking[0]["ticker"], "AAA")
        self.assertEqual(ranking[0]["target_action"], "BUY")
        self.assertEqual(ranking[0]["allocation_status"], "SELECTED_THIS_MONTH")
        self.assertNotIn("fundamentals_coverage_guardrail", ranking[0]["constraint_checks"])

    def test_header_only_coverage_file_is_accepted_and_leaves_ranking_unchanged(self) -> None:
        positions, scores, watchlist = self.eligible_holding_fixture()
        coverage_path = Path("tests") / "_tmp_monthly_header_only_coverage.csv"
        try:
            self.write_csv(coverage_path, COVERAGE_OUTPUT_FIELDS, [])
            baseline, _ = build_monthly_ranking(positions, scores, watchlist)
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.monthly_ranking_engine",
                    "--positions",
                    str(self.write_fixture_csv("positions", positions)),
                    "--scores",
                    str(self.write_fixture_csv("scores", scores)),
                    "--watchlist",
                    str(self.write_fixture_csv("watchlist", watchlist, fieldnames=["ticker"])),
                    "--coverage",
                    str(coverage_path),
                    "--output",
                    str(Path("tests") / "_tmp_monthly_header_only_ranking.csv"),
                    "--rebalance-output",
                    str(Path("tests") / "_tmp_monthly_header_only_rebalance.csv"),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output_rows = read_csv_rows(Path("tests") / "_tmp_monthly_header_only_ranking.csv")
            self.assertEqual(output_rows[0]["ticker"], baseline[0]["ticker"])
            self.assertEqual(output_rows[0]["target_action"], baseline[0]["target_action"])
        finally:
            for path in [
                coverage_path,
                Path("tests") / "_tmp_monthly_positions.csv",
                Path("tests") / "_tmp_monthly_scores.csv",
                Path("tests") / "_tmp_monthly_watchlist.csv",
                Path("tests") / "_tmp_monthly_header_only_ranking.csv",
                Path("tests") / "_tmp_monthly_header_only_rebalance.csv",
            ]:
                if path.exists():
                    path.unlink()

    def write_fixture_csv(self, kind: str, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> Path:
        path = Path("tests") / f"_tmp_monthly_{kind}.csv"
        if fieldnames is None:
            fieldnames = list(rows[0].keys()) if rows else ["ticker"]
        self.write_csv(path, fieldnames, rows)
        return path

    def test_incomplete_coverage_rows_are_rejected(self) -> None:
        positions, scores, watchlist = self.eligible_holding_fixture()
        bad_coverage = [{"ticker": "AAA", "match_status": "REVIEW", "needs_research_flag": "True"}]
        with self.assertRaisesRegex(ValueError, "coverage input missing required columns: .*match_method"):
            build_monthly_ranking(positions, scores, watchlist, coverage_rows=bad_coverage)

    def test_isin_matched_pdf_holding_is_ranked_as_top_up(self) -> None:
        positions = [
            {"ticker": "DE000A1TEST1", "isin": "DE000A1TEST1", "company_name": "Example AG", "asset_type": "STOCK", "sleeve": "SINGLE_STOCK", "sector": "Tech", "market_value_eur": "100"},
            {"ticker": "EUR-CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": "5000"},
        ]
        scores = [
            {
                "ticker": "QTEST",
                "isin": "DE000A1TEST1",
                "company_name": "Example AG",
                "sector": "Tech",
                "sleeve": "SINGLE_STOCK",
                "held_in_portfolio": "true",
                "business_score": "88",
                "valuation_score": "72",
                "buy_score": "80",
                "margin_of_safety_pct": "10",
                "classification": "HOLD",
                "has_hard_risk_flag": "false",
                "data_quality_flag": "OK",
                "valuation_comment": "Attraktiv.",
                "mandate_fit_score": "90",
            }
        ]
        ranking, _ = build_monthly_ranking(positions, scores, [])
        self.assertEqual(ranking[0]["ticker"], "QTEST")
        self.assertEqual(ranking[0]["target_action"], "TOP_UP")
        self.assertGreater(ranking[0]["current_weight"], 0.0)

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

    def test_duplicate_score_tickers_raise_clear_error_in_ranking(self) -> None:
        positions = [
            {"ticker": "EUR-CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": "5000"},
        ]
        scores = [{"ticker": "AAA"}, {"ticker": "aAa"}]
        with self.assertRaisesRegex(ValueError, "scores input contains duplicate tickers: AAA"):
            build_monthly_ranking(positions, scores, [])

    def test_blank_score_ticker_raises_clear_error_in_ranking(self) -> None:
        positions = [
            {"ticker": "EUR-CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": "5000"},
        ]
        scores = [{"ticker": "   ", "business_score": "80", "valuation_score": "65", "buy_score": "75", "classification": "BUY_CANDIDATE", "data_quality_flag": "OK"}]
        with self.assertRaisesRegex(ValueError, "scores input row 2 has blank required field\\(s\\): ticker"):
            build_monthly_ranking(positions, scores, [])

    def test_duplicate_watchlist_tickers_raise_clear_error_in_ranking(self) -> None:
        positions = [
            {"ticker": "EUR-CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": "5000"},
        ]
        scores = [
            {
                "ticker": "AAA",
                "business_score": "80",
                "valuation_score": "65",
                "buy_score": "75",
                "classification": "BUY_CANDIDATE",
                "data_quality_flag": "OK",
                "has_hard_risk_flag": "false",
            }
        ]
        watchlist = [{"ticker": "AAA"}, {"ticker": "aAa"}]
        with self.assertRaisesRegex(ValueError, "watchlist input contains duplicate tickers: AAA"):
            build_monthly_ranking(positions, scores, watchlist)

    def test_valuation_tier_gap_blocks_buy_candidate_as_wait_valuation(self) -> None:
        positions = [
            {"ticker": "EUR-CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": "5000"},
        ]
        scores = [
            {
                "ticker": "AAA",
                "company_name": "Alpha",
                "sector": "Tech",
                "sleeve": "SINGLE_STOCK",
                "held_in_portfolio": "false",
                "company_type_profile": "STANDARD",
                "business_score": "85",
                "valuation_score": "70",
                "buy_score": "80",
                "margin_of_safety_pct": "10",
                "classification": "BUY_CANDIDATE",
                "has_hard_risk_flag": "false",
                "data_quality_flag": "REVIEW",
                "core_quality_data_status": "OK",
                "valuation_data_status": "MISSING",
                "dividend_fcf_data_status": "OK",
                "valuation_comment": "Needs valuation.",
                "mandate_fit_score": "90",
            }
        ]
        watchlist = [{"ticker": "AAA", "company_name": "Alpha", "sector": "Tech", "sleeve": "SINGLE_STOCK", "status": "QUALITY_COMPOUNDER_CANDIDATE"}]
        ranking, _ = build_monthly_ranking(positions, scores, watchlist)
        aaa = next(row for row in ranking if row["ticker"] == "AAA")
        self.assertEqual(aaa["target_action"], "WAIT_VALUATION")
        self.assertEqual(aaa["suggested_buy_amount_eur"], 0.0)
        self.assertIn("valuation_data_status_MISSING", aaa["constraint_checks"])

    def test_dividend_fcf_gap_blocks_as_review_fcf_data(self) -> None:
        positions = [
            {"ticker": "EUR-CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": "5000"},
        ]
        scores = [
            {
                "ticker": "AAA",
                "company_name": "Alpha",
                "sector": "Tech",
                "sleeve": "SINGLE_STOCK",
                "held_in_portfolio": "false",
                "company_type_profile": "STANDARD",
                "business_score": "85",
                "valuation_score": "70",
                "buy_score": "80",
                "margin_of_safety_pct": "10",
                "classification": "BUY_CANDIDATE",
                "has_hard_risk_flag": "false",
                "data_quality_flag": "REVIEW",
                "core_quality_data_status": "OK",
                "valuation_data_status": "OK",
                "dividend_fcf_data_status": "MISSING",
                "valuation_comment": "Needs FCF.",
                "mandate_fit_score": "90",
            }
        ]
        watchlist = [{"ticker": "AAA", "company_name": "Alpha", "sector": "Tech", "sleeve": "SINGLE_STOCK", "status": "QUALITY_COMPOUNDER_CANDIDATE"}]
        ranking, _ = build_monthly_ranking(positions, scores, watchlist)
        aaa = next(row for row in ranking if row["ticker"] == "AAA")
        self.assertEqual(aaa["target_action"], "REVIEW_FCF_DATA")
        self.assertEqual(aaa["suggested_buy_amount_eur"], 0.0)

    def test_financial_profile_is_not_standard_core_blocked(self) -> None:
        positions = [
            {"ticker": "EUR-CASH", "company_name": "Cash", "asset_type": "CASH", "sleeve": "CASH", "sector": "Cash", "market_value_eur": "5000"},
        ]
        scores = [
            {
                "ticker": "BANK",
                "company_name": "Bank",
                "sector": "Financials",
                "sleeve": "SINGLE_STOCK",
                "held_in_portfolio": "false",
                "company_type_profile": "FINANCIAL",
                "business_score": "85",
                "valuation_score": "70",
                "buy_score": "80",
                "margin_of_safety_pct": "10",
                "classification": "BUY_CANDIDATE",
                "has_hard_risk_flag": "false",
                "data_quality_flag": "OK",
                "core_quality_data_status": "NOT_APPLICABLE",
                "valuation_data_status": "NOT_APPLICABLE",
                "dividend_fcf_data_status": "NOT_APPLICABLE",
                "valuation_comment": "Ok.",
                "mandate_fit_score": "90",
            }
        ]
        watchlist = [{"ticker": "BANK", "company_name": "Bank", "sector": "Financials", "sleeve": "SINGLE_STOCK", "status": "QUALITY_COMPOUNDER_CANDIDATE"}]
        ranking, _ = build_monthly_ranking(positions, scores, watchlist)
        self.assertNotEqual(ranking[0]["target_action"], "REVIEW_CORE_DATA")


if __name__ == "__main__":
    unittest.main()
