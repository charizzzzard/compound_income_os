from __future__ import annotations

import hashlib
import re
from typing import Any

from src.common import canonicalize_ticker, round2, safe_upper, to_float
from src.portfolio_rules import classify_sleeve

FIELD_ALIASES = {
    "portfolio_date": ["portfolio_date", "date", "as_of", "valuation_date"],
    "source_name": ["source_name", "source", "broker_source", "account_name", "depot_name"],
    "source_type": ["source_type", "source", "broker_source"],
    "raw_name": ["raw_name", "name", "instrument", "security_name"],
    "company_name": ["company_name", "name", "instrument", "security_name"],
    "ticker": ["ticker", "symbol", "instrument_ticker"],
    "isin": ["isin", "security_isin", "instrument_isin"],
    "asset_type": ["asset_type", "security_type", "category", "position_type", "instrument_type"],
    "position_type": ["position_type", "category", "security_type", "asset_type"],
    "sleeve": ["sleeve", "bucket"],
    "sector": ["sector", "gics_sector"],
    "country": ["country", "domicile"],
    "quantity": ["quantity", "shares", "units"],
    "current_price": ["current_price", "current_price_eur", "price_eur", "price", "last_price_eur", "current_price_local"],
    "avg_cost": ["avg_cost", "avg_price", "purchase_price", "average_price"],
    "market_value": ["market_value", "current_value", "market_value_eur", "position_value_eur", "value"],
    "cost_basis_total": ["cost_basis_eur", "cost_basis", "book_value_eur", "book_value", "purchase_value"],
    "cash": ["cash", "cash_balance", "available_cash"],
    "currency": ["currency", "ccy"],
    "notes": ["notes", "comment", "memo"],
}


def pick_value(row: dict[str, Any], aliases: list[str], default: str = "") -> str:
    for alias in aliases:
        if alias in row and str(row.get(alias, "")).strip():
            return str(row.get(alias)).strip()
    return default


def normalize_ticker(value: str) -> str:
    return canonicalize_ticker(value)


def normalize_key_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "blank"


def build_unknown_position_key(row: dict[str, Any], source_name: str, raw_name: str, company_name: str) -> str:
    raw_parts = [
        f"{key}={str(value).strip()}"
        for key, value in sorted(row.items())
        if str(value or "").strip()
    ]
    material = "|".join(raw_parts) or "|".join([source_name, raw_name, company_name])
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
    label = normalize_key_text(company_name or raw_name)
    return f"UNKNOWN::{label}::{digest}"


def normalize_asset_type(raw_asset_type: str, raw_position_type: str, company_name: str, ticker: str, cash_value: float) -> str:
    combined = " ".join(
        part for part in [safe_upper(raw_asset_type), safe_upper(raw_position_type), company_name.upper(), ticker.upper()]
        if part
    )
    if cash_value > 0.0 or "CASH" in combined or "LIQUID" in combined:
        return "CASH"
    if "ETF" in combined or "UCITS" in combined or "INDEX FUND" in combined:
        return "ETF"
    if "ADR" in combined:
        return "ADR"
    if any(token in combined for token in ["STOCK", "SHARE", "EQUITY", "AKTIE"]):
        return "STOCK"
    if any(token in combined for token in ["OPTION", "WARRANT", "CERTIFICATE", "DERIVATIVE", "CRYPTO", "BOND", "NOTE", "ETN"]):
        return "OTHER"
    if ticker:
        return "STOCK"
    return "OTHER"


def derive_sleeve(asset_type: str, explicit_sleeve: str, company_name: str, raw_type_text: str) -> str:
    if explicit_sleeve:
        return classify_sleeve({"sleeve": explicit_sleeve, "asset_type": asset_type, "company_name": company_name})
    if asset_type == "OTHER":
        if any(token in raw_type_text for token in ["CERTIFICATE", "WARRANT", "OPTION", "CRYPTO", "THEMATIC"]):
            return "NON_CORE"
        return "REVIEW"
    return classify_sleeve({"asset_type": asset_type, "company_name": company_name})


def derive_mandate_fit(sleeve: str, review_flag: bool) -> str:
    if review_flag:
        return "REVIEW"
    if sleeve == "CORE_ETF":
        return "CORE"
    if sleeve == "DIVIDEND_QUALITY_ETF":
        return "DG_QUALITY"
    if sleeve == "SINGLE_STOCK":
        return "MANDATE_CANDIDATE"
    if sleeve == "CASH":
        return "CASH_RESERVE"
    if sleeve == "NON_CORE":
        return "NON_CORE"
    return "REVIEW"


def build_review_state(
    ticker_found: bool,
    asset_type: str,
    sleeve: str,
    market_value_eur: float,
    notes: str,
) -> tuple[str, bool, str]:
    reasons: list[str] = []
    extraction_issue = "konnte nicht extrahiert" in notes.lower()
    if extraction_issue:
        reasons.append(notes)
    if not ticker_found and asset_type != "CASH":
        reasons.append("Ticker fehlt, ISIN oder Platzhalter wurde verwendet")
    if asset_type == "OTHER":
        reasons.append("Asset-Typ nicht sauber dem Mandat zuordenbar")
    if sleeve in {"NON_CORE", "REVIEW"}:
        reasons.append("Position liegt ausserhalb des Kernmandats oder erfordert Review")
    if market_value_eur <= 0.0 and asset_type != "CASH":
        reasons.append("Marktwert fehlt oder ist nicht plausibel")

    review_text = "; ".join(reasons)
    if notes and review_text and notes not in reasons:
        review_text = f"{notes}; {review_text}"
    elif notes:
        review_text = notes

    if any(
        reason.startswith("Ticker fehlt")
        or reason.startswith("Marktwert fehlt")
        or "konnte nicht extrahiert" in reason.lower()
        for reason in reasons
    ):
        return "MISSING_DATA", bool(reasons), review_text
    return ("REVIEW" if reasons else "OK"), bool(reasons), review_text


def is_effectively_empty(row: dict[str, Any]) -> bool:
    meaningful_fields = ["ticker", "symbol", "isin", "name", "instrument", "security_name", "market_value", "current_value", "cash"]
    return not any(str(row.get(field, "")).strip() for field in meaningful_fields)


def normalize_position_row(
    row: dict[str, Any],
    mode: str = "sample",
    source_name: str | None = None,
    portfolio_date: str | None = None,
) -> dict[str, Any] | None:
    if is_effectively_empty(row):
        return None

    normalized = {field: pick_value(row, aliases) for field, aliases in FIELD_ALIASES.items()}
    normalized_portfolio_date = portfolio_date if portfolio_date is not None else normalized["portfolio_date"]
    normalized_source_name = source_name or normalized["source_name"] or normalized["source_type"] or ("manual_csv" if mode == "sample" else "real_manual_csv")
    raw_name = normalized["raw_name"] or normalized["company_name"]
    isin = str(normalized["isin"]).strip().upper()
    input_ticker = normalize_ticker(normalized["ticker"])
    ticker_found = bool(input_ticker)
    ticker = input_ticker or isin
    company_name = normalized["company_name"] or raw_name or ticker
    quantity = to_float(normalized["quantity"], 0.0)
    current_price = to_float(normalized["current_price"], 0.0)
    avg_cost = to_float(normalized["avg_cost"], 0.0)
    cash_value = to_float(normalized["cash"], 0.0)
    market_value_eur = to_float(normalized["market_value"], 0.0)
    if market_value_eur == 0.0 and cash_value > 0.0:
        market_value_eur = cash_value

    asset_type = normalize_asset_type(
        normalized["asset_type"],
        normalized["position_type"],
        company_name,
        ticker,
        cash_value,
    )

    if asset_type == "CASH":
        ticker = ticker or f"{(normalized['currency'] or 'EUR').upper()}-CASH"
        quantity = quantity or market_value_eur
        current_price = current_price or 1.0
        avg_cost = avg_cost or 1.0
    else:
        ticker = ticker or build_unknown_position_key(row, normalized_source_name, raw_name, company_name)
        if market_value_eur == 0.0 and quantity > 0.0 and current_price > 0.0:
            market_value_eur = quantity * current_price
        if current_price == 0.0 and quantity > 0.0 and market_value_eur > 0.0:
            current_price = market_value_eur / quantity

    cost_basis_eur = to_float(normalized["cost_basis_total"], 0.0)
    if cost_basis_eur == 0.0 and avg_cost > 0.0 and quantity > 0.0:
        cost_basis_eur = avg_cost * quantity
    if avg_cost == 0.0 and cost_basis_eur > 0.0 and quantity > 0.0:
        avg_cost = cost_basis_eur / quantity
    if cost_basis_eur == 0.0:
        cost_basis_eur = market_value_eur
    if avg_cost == 0.0 and quantity > 0.0:
        avg_cost = cost_basis_eur / quantity

    raw_type_text = " ".join([safe_upper(normalized["asset_type"]), safe_upper(normalized["position_type"]), company_name.upper()]).strip()
    sleeve = derive_sleeve(asset_type, normalized["sleeve"], company_name, raw_type_text)
    data_quality_flag, review_flag, review_reason = build_review_state(
        ticker_found or bool(isin),
        asset_type,
        sleeve,
        market_value_eur,
        normalized["notes"],
    )
    mandate_fit = derive_mandate_fit(sleeve, review_flag)
    unrealized_pnl_eur = market_value_eur - cost_basis_eur
    currency = normalized["currency"] or "EUR"

    return {
        "portfolio_date": normalized_portfolio_date,
        "source_name": normalized_source_name,
        "source_type": normalized["source_type"] or normalized_source_name,
        "raw_name": raw_name or company_name,
        "company_name": company_name,
        "ticker": ticker,
        "isin": isin,
        "asset_type": asset_type,
        "position_type": normalized["position_type"] or asset_type,
        "sleeve": sleeve,
        "quantity": round(quantity, 6),
        "current_price": round2(current_price),
        "avg_cost": round2(avg_cost),
        "market_value": round2(market_value_eur),
        "currency": currency,
        "sector": normalized["sector"] or ("Cash" if asset_type == "CASH" else "Unknown"),
        "country": normalized["country"] or ("Eurozone" if asset_type == "CASH" else "Unknown"),
        "mandate_fit": mandate_fit,
        "data_quality_flag": data_quality_flag,
        "review_flag": review_flag,
        "review_reason": review_reason,
        "price_eur": round2(current_price),
        "market_value_eur": round2(market_value_eur),
        "cost_basis_eur": round2(cost_basis_eur),
        "unrealized_pnl_eur": round2(unrealized_pnl_eur),
        "notes": review_reason,
    }


def normalize_positions(
    rows: list[dict[str, Any]],
    mode: str = "sample",
    source_name: str | None = None,
    portfolio_date: str | None = None,
) -> list[dict[str, Any]]:
    normalized_rows = [
        normalized
        for row in rows
        if (normalized := normalize_position_row(row, mode, source_name, portfolio_date)) is not None
    ]
    normalized_rows.sort(key=lambda row: (row["sleeve"] == "CASH", -row["market_value_eur"], row["ticker"]))
    return normalized_rows
