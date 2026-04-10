from __future__ import annotations

import unittest

from src.import_broker import build_positions_snapshot
from src.portfolio_review import build_holdings_action_table
from src.scoring_engine import build_scores
from src.traderepublic_documents import parse_cash_statement_text, parse_depot_statement_text


class TradeRepublicDocumentTests(unittest.TestCase):
    def test_depot_statement_text_extracts_holdings_and_keeps_zero_value_rows(self) -> None:
        text = """
        DATUM 10.04.2026
        DEPOTAUSZUG
        zum 10.04.2026
        0,3453 Stk. Example Momentum ETF
        Registered Shares USD (Acc)o.N
        ISIN: IE00BP3QZ825
        Girosammelverwahrung
        87,22
        10.04.2026
        30,12
        0,000149 Stk. Legacy Restposition AG
        Registered Shares
        ISIN: US98138J5039
        Girosammelverwahrung
        0,00
        10.04.2026
        0,00
        ANZAHL POSITIONEN: 2 30,12 EUR
        """
        rows = parse_depot_statement_text(text)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["portfolio_date"], "2026-04-10")
        self.assertEqual(rows[0]["isin"], "IE00BP3QZ825")
        self.assertEqual(rows[0]["quantity"], "0,3453")
        self.assertEqual(rows[0]["current_price"], 87.22)
        self.assertEqual(rows[0]["market_value"], 30.12)
        self.assertEqual(rows[1]["isin"], "US98138J5039")
        self.assertEqual(rows[1]["market_value"], 0.0)
        self.assertIn("Kurswert ist 0", rows[1]["notes"])

    def test_cash_statement_text_extracts_end_balance(self) -> None:
        text = """
        DATUM 01 Juni 2020 - 09 Apr. 2026
        KONTOAUSZUG
        PRODUKT ANFANGSSALDO ZAHLUNGSEINGANG ZAHLUNGSAUSGANG ENDSALDO
        Cashkonto 0,00 € 40.041,42 € 32.516,79 € 7.524,63 €
        """
        row = parse_cash_statement_text(text)

        self.assertEqual(row["portfolio_date"], "2026-04-09")
        self.assertEqual(row["ticker"], "EUR-CASH")
        self.assertEqual(row["asset_type"], "CASH")
        self.assertEqual(row["market_value"], 7524.63)

    def test_pdf_import_rows_normalize_cash_and_review_legacy_position(self) -> None:
        depot_rows = parse_depot_statement_text(
            """
            DATUM 10.04.2026
            DEPOTAUSZUG
            0,000149 Stk. Legacy Restposition AG
            ISIN: US98138J5039
            0,00
            10.04.2026
            0,00
            """
        )
        cash_row = parse_cash_statement_text(
            """
            DATUM 01 Juni 2020 - 09 Apr. 2026
            Cashkonto 0,00 € 1.000,00 € 250,00 € 750,00 €
            """
        )
        snapshot = build_positions_snapshot([*depot_rows, cash_row], mode="tr_pdf", source_name="trade_republic_official_docs")

        legacy = next(row for row in snapshot if row["isin"] == "US98138J5039")
        cash = next(row for row in snapshot if row["asset_type"] == "CASH")
        self.assertEqual(legacy["quantity"], 0.000149)
        self.assertEqual(legacy["market_value_eur"], 0.0)
        self.assertEqual(legacy["data_quality_flag"], "MISSING_DATA")
        self.assertTrue(legacy["review_flag"])
        self.assertEqual(cash["ticker"], "EUR-CASH")
        self.assertEqual(cash["market_value_eur"], 750.0)
        self.assertEqual(cash["data_quality_flag"], "OK")

    def test_missing_cash_end_balance_is_flagged_for_review(self) -> None:
        cash_row = parse_cash_statement_text(
            """
            DATUM 01 Juni 2020 - 09 Apr. 2026
            Cashkonto ohne extrahierbaren Endsaldo
            """
        )
        snapshot = build_positions_snapshot([cash_row], mode="tr_pdf", source_name="trade_republic_official_docs")

        self.assertEqual(snapshot[0]["ticker"], "EUR-CASH")
        self.assertEqual(snapshot[0]["market_value_eur"], 0.0)
        self.assertEqual(snapshot[0]["data_quality_flag"], "MISSING_DATA")
        self.assertTrue(snapshot[0]["review_flag"])

    def test_scoring_matches_pdf_holdings_by_isin_without_guessing_ticker(self) -> None:
        positions = [
            {
                "ticker": "DE000A1TEST1",
                "isin": "DE000A1TEST1",
                "company_name": "Example Quality AG Registered Shares",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "sector": "Unknown",
                "country": "Germany",
                "market_value_eur": "100",
                "cost_basis_eur": "100",
                "price_eur": "100",
            }
        ]
        fundamentals = [
            {
                "ticker": "QTEST",
                "isin": "DE000A1TEST1",
                "company_name": "Example Quality AG",
                "sector": "Industrials",
                "country": "Germany",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "current_price_eur": "100",
                "quality_score": "90",
                "dividend_score": "70",
                "balance_sheet_score": "88",
                "growth_quality_score": "82",
                "capital_allocation_score": "85",
                "mandate_fit_score": "88",
                "pe_current": "14",
                "pe_hist": "16",
                "ev_ebit_current": "10",
                "ev_ebit_hist": "12",
                "fcf_yield_current_pct": "6",
                "fcf_yield_hist_pct": "5",
                "normalized_fcf_yield_pct": "6",
                "target_fcf_yield_pct": "5",
                "dividend_yield_current_pct": "2",
                "dividend_yield_hist_pct": "1.8",
                "expected_return_pct": "10",
                "drawdown_from_high_pct": "20",
                "has_hard_risk_flag": "false",
                "thesis_robustness": "ROBUST",
                "thesis_summary": "Anonymisierte Test-These.",
                "main_risks": "Anonymisierte Test-Risiken.",
                "data_quality_flag": "OK",
            }
        ]

        scores = build_scores(positions, fundamentals)
        row = next(score for score in scores if score["ticker"] == "QTEST")
        self.assertTrue(row["held_in_portfolio"])
        self.assertEqual(row["isin"], "DE000A1TEST1")
        self.assertEqual(row["data_quality_flag"], "OK")

    def test_holdings_action_table_uses_isin_matched_scores(self) -> None:
        positions = [
            {
                "ticker": "DE000A1TEST1",
                "isin": "DE000A1TEST1",
                "company_name": "Example Quality AG Registered Shares",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "market_value_eur": "100",
                "weight_total_assets_pct": "2.0",
                "review_flag": "false",
            }
        ]
        scores = [
            {
                "ticker": "QTEST",
                "isin": "DE000A1TEST1",
                "company_name": "Example Quality AG",
                "held_in_portfolio": "true",
                "current_weight_pct": "2.0",
                "business_score": "88",
                "valuation_score": "75",
                "buy_score": "80",
                "mandate_fit_score": "90",
                "classification": "HOLD",
                "data_quality_flag": "OK",
                "has_hard_risk_flag": "false",
            }
        ]

        table = build_holdings_action_table(positions, scores)
        self.assertEqual(table[0]["ticker"], "QTEST")
        self.assertEqual(table[0]["data_quality_flag"], "OK")
        self.assertNotEqual(table[0]["portfolio_action"], "EXIT_REVIEW")


if __name__ == "__main__":
    unittest.main()
