from __future__ import annotations

import unittest

from src.import_broker import build_positions_snapshot
from src.normalize_positions import normalize_position_row
from src.portfolio_rules import aggregate_positions_by_ticker


class ImportNormalizationTests(unittest.TestCase):
    def test_normalize_position_computes_market_value(self) -> None:
        row = {
            "source": "manual_csv",
            "symbol": "TEST",
            "name": "Test Co",
            "security_type": "stock",
            "shares": "2",
            "price": "25",
            "book_value_eur": "40",
        }
        normalized = normalize_position_row(row)
        self.assertEqual(normalized["ticker"], "TEST")
        self.assertEqual(normalized["asset_type"], "STOCK")
        self.assertEqual(normalized["market_value_eur"], 50.0)
        self.assertEqual(normalized["unrealized_pnl_eur"], 10.0)

    def test_build_positions_snapshot_weight_sum_is_consistent(self) -> None:
        rows = [
            {
                "source_type": "manual_csv",
                "ticker": "AAA",
                "company_name": "AAA",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "sector": "Tech",
                "country": "USA",
                "quantity": "1",
                "price_eur": "60",
                "market_value_eur": "60",
                "cost_basis_eur": "50",
                "currency": "EUR",
                "notes": "",
            },
            {
                "source_type": "manual_csv",
                "ticker": "BBB",
                "company_name": "BBB ETF",
                "asset_type": "ETF",
                "sleeve": "CORE_ETF",
                "sector": "ETF",
                "country": "Global",
                "quantity": "1",
                "price_eur": "40",
                "market_value_eur": "40",
                "cost_basis_eur": "35",
                "currency": "EUR",
                "notes": "",
            },
        ]
        snapshot = build_positions_snapshot(rows)
        total_weight = sum(item["weight_total_assets_pct"] for item in snapshot)
        self.assertAlmostEqual(total_weight, 100.0, places=2)

    def test_unknown_positions_get_stable_distinct_fallback_keys(self) -> None:
        rows = [
            {
                "source": "manual_csv",
                "name": "Legacy Position Alpha",
                "security_type": "stock",
                "shares": "1",
                "current_value": "10",
            },
            {
                "source": "manual_csv",
                "name": "Legacy Position Beta",
                "security_type": "stock",
                "shares": "2",
                "current_value": "20",
            },
        ]

        snapshot = build_positions_snapshot(rows, mode="real", source_name="manual_real_depot")
        tickers = {row["ticker"] for row in snapshot}
        aggregated = aggregate_positions_by_ticker(snapshot)

        self.assertEqual(len(snapshot), 2)
        self.assertEqual(len(tickers), 2)
        self.assertTrue(all(str(ticker).startswith("UNKNOWN::") for ticker in tickers))
        self.assertEqual(len(aggregated), 2)
        self.assertEqual(sum(row["market_value_eur"] for row in aggregated), 30.0)

        second_snapshot = build_positions_snapshot(rows, mode="real", source_name="manual_real_depot")
        self.assertEqual([row["ticker"] for row in snapshot], [row["ticker"] for row in second_snapshot])


if __name__ == "__main__":
    unittest.main()
