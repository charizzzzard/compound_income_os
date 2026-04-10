from __future__ import annotations

from typing import Any

from src.common import round2, safe_upper, to_float
from src.portfolio_rules import classify_sleeve


FIELD_ALIASES = {
    "source_type": ["source_type", "source", "broker_source"],
    "ticker": ["ticker", "symbol", "isin"],
    "company_name": ["company_name", "name", "security_name"],
    "asset_type": ["asset_type", "security_type"],
    "sleeve": ["sleeve", "bucket"],
    "sector": ["sector"],
    "country": ["country"],
    "quantity": ["quantity", "shares", "units"],
    "price_eur": ["price_eur", "price", "last_price_eur"],
    "market_value_eur": ["market_value_eur", "market_value", "position_value_eur"],
    "cost_basis_eur": ["cost_basis_eur", "cost_basis", "book_value_eur"],
    "currency": ["currency", "ccy"],
    "notes": ["notes", "comment"],
}


def pick_value(row: dict[str, Any], aliases: list[str], default: str = "") -> str:
    for alias in aliases:
        if alias in row and str(row.get(alias, "")).strip():
            return str(row.get(alias)).strip()
    return default


def normalize_asset_type(value: str, ticker: str, company_name: str) -> str:
    asset_type = safe_upper(value)
    if asset_type:
        return asset_type
    if ticker.endswith("CASH") or "cash" in company_name.lower():
        return "CASH"
    if "etf" in company_name.lower():
        return "ETF"
    return "STOCK"


def normalize_position_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        field: pick_value(row, aliases)
        for field, aliases in FIELD_ALIASES.items()
    }
    ticker = normalized["ticker"] or "UNKNOWN"
    company_name = normalized["company_name"] or ticker
    asset_type = normalize_asset_type(normalized["asset_type"], ticker, company_name)
    quantity = to_float(normalized["quantity"], 0.0)
    price_eur = to_float(normalized["price_eur"], 0.0)
    market_value_eur = to_float(normalized["market_value_eur"], 0.0)
    if market_value_eur == 0.0 and quantity and price_eur:
        market_value_eur = quantity * price_eur
    cost_basis_eur = to_float(normalized["cost_basis_eur"], market_value_eur)
    sleeve = normalized["sleeve"] or classify_sleeve(
        {
            "asset_type": asset_type,
            "company_name": company_name,
        }
    )
    unrealized_pnl_eur = market_value_eur - cost_basis_eur
    return {
        "source_type": normalized["source_type"] or "manual_csv",
        "ticker": ticker,
        "company_name": company_name,
        "asset_type": asset_type,
        "sleeve": sleeve,
        "sector": normalized["sector"] or ("Cash" if asset_type == "CASH" else "Unknown"),
        "country": normalized["country"] or "Unknown",
        "quantity": round2(quantity),
        "price_eur": round2(price_eur),
        "market_value_eur": round2(market_value_eur),
        "cost_basis_eur": round2(cost_basis_eur),
        "unrealized_pnl_eur": round2(unrealized_pnl_eur),
        "currency": normalized["currency"] or "EUR",
        "notes": normalized["notes"],
    }


def normalize_positions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_rows = [normalize_position_row(row) for row in rows]
    normalized_rows.sort(key=lambda row: (row["sleeve"] == "CASH", -row["market_value_eur"], row["ticker"]))
    return normalized_rows
