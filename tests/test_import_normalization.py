from __future__ import annotations

import unittest

from src.import_broker import build_positions_snapshot
from src.normalize_positions import normalize_position_row


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


if __name__ == "__main__":
    unittest.main()
