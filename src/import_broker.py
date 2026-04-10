from __future__ import annotations

import argparse

from src.common import read_csv_rows, round2, write_csv_rows
from src.normalize_positions import normalize_positions
from src.portfolio_rules import compute_portfolio_value, compute_total_assets


OUTPUT_FIELDS = [
    "source_type",
    "ticker",
    "company_name",
    "asset_type",
    "sleeve",
    "sector",
    "country",
    "quantity",
    "price_eur",
    "market_value_eur",
    "cost_basis_eur",
    "unrealized_pnl_eur",
    "weight_portfolio_pct",
    "weight_total_assets_pct",
    "currency",
    "notes",
]


def build_positions_snapshot(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    normalized = normalize_positions(rows)
    total_assets = compute_total_assets(normalized) or 1.0
    portfolio_value = compute_portfolio_value(normalized) or 1.0
    snapshot: list[dict[str, object]] = []
    for row in normalized:
        market_value = float(row["market_value_eur"])
        is_cash = row["asset_type"] == "CASH"
        snapshot.append(
            {
                **row,
                "weight_portfolio_pct": 0.0 if is_cash else round2((market_value / portfolio_value) * 100.0),
                "weight_total_assets_pct": round2((market_value / total_assets) * 100.0),
            }
        )
    return snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize broker/manual CSV data into positions snapshot.")
    parser.add_argument("--input", required=True, help="Raw portfolio CSV path.")
    parser.add_argument("--output", required=True, help="Output snapshot CSV path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csv_rows(args.input)
    if not rows:
        raise ValueError(f"raw portfolio CSV ({args.input}) contains no rows.")
    snapshot = build_positions_snapshot(rows)
    write_csv_rows(args.output, OUTPUT_FIELDS, snapshot)


if __name__ == "__main__":
    main()
