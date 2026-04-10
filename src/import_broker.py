from __future__ import annotations

import argparse

from src.common import read_csv_rows, round2, to_float, write_csv_rows
from src.normalize_positions import normalize_positions
from src.portfolio_rules import compute_portfolio_value, compute_total_assets
from src.traderepublic_documents import load_trade_republic_pdf_rows


OUTPUT_FIELDS = [
    "portfolio_date",
    "source_name",
    "source_type",
    "raw_name",
    "isin",
    "ticker",
    "company_name",
    "asset_type",
    "position_type",
    "sleeve",
    "sector",
    "country",
    "quantity",
    "current_price",
    "avg_cost",
    "market_value",
    "price_eur",
    "market_value_eur",
    "cost_basis_eur",
    "unrealized_pnl_eur",
    "mandate_fit",
    "data_quality_flag",
    "review_flag",
    "review_reason",
    "weight_portfolio_pct",
    "weight_total_assets_pct",
    "currency",
    "notes",
]


def build_positions_snapshot(
    rows: list[dict[str, str]],
    mode: str = "sample",
    source_name: str | None = None,
    portfolio_date: str | None = None,
) -> list[dict[str, object]]:
    normalized = normalize_positions(rows, mode, source_name, portfolio_date)
    total_assets = compute_total_assets(normalized) or 1.0
    portfolio_value = compute_portfolio_value(normalized) or 1.0
    snapshot: list[dict[str, object]] = []
    for row in normalized:
        market_value = to_float(row.get("market_value_eur"))
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
    parser.add_argument("--cash-input", help="Optional cash statement input for document-based imports.")
    parser.add_argument("--output", required=True, help="Output snapshot CSV path.")
    parser.add_argument("--mode", choices=["sample", "real", "tr_pdf"], default="sample", help="Input mode for fixture, real CSV, or Trade Republic PDF files.")
    parser.add_argument("--source-name", help="Optional source label written into the normalized snapshot.")
    parser.add_argument("--portfolio-date", help="Optional portfolio date written into the normalized snapshot.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "tr_pdf":
        rows = load_trade_republic_pdf_rows(
            args.input,
            args.cash_input,
            args.source_name or "trade_republic_official_docs",
        )
    else:
        rows = read_csv_rows(args.input)
    if not rows:
        raise ValueError(f"raw portfolio CSV ({args.input}) contains no rows.")
    snapshot = build_positions_snapshot(rows, args.mode, args.source_name, args.portfolio_date)
    write_csv_rows(args.output, OUTPUT_FIELDS, snapshot)


if __name__ == "__main__":
    main()
