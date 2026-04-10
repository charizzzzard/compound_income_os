from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.common import resolve_repo_path, to_float

ISIN_PATTERN = re.compile(r"\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b")
POSITION_START_PATTERN = re.compile(r"^([0-9][0-9.\s]*(?:,[0-9]+)?)\s+Stk\.\s+(.+)$")
DATE_PATTERN = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")
AMOUNT_PATTERN = re.compile(r"([0-9][0-9.\s]*,\d{2})\s*€?")

GERMAN_MONTHS = {
    "jan": "01",
    "januar": "01",
    "feb": "02",
    "februar": "02",
    "mär": "03",
    "maerz": "03",
    "mar": "03",
    "märz": "03",
    "apr": "04",
    "april": "04",
    "mai": "05",
    "jun": "06",
    "juni": "06",
    "jul": "07",
    "juli": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "okt": "10",
    "oktober": "10",
    "nov": "11",
    "november": "11",
    "dez": "12",
    "dezember": "12",
}


def extract_pdf_text(path_value: str | Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required for local text-based PDF extraction.") from exc

    path = resolve_repo_path(path_value)
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def normalize_pdf_lines(text: str) -> list[str]:
    return [line.strip().replace("\u00a0", " ") for line in text.splitlines() if line.strip()]


def parse_german_date(value: str) -> str:
    numeric = DATE_PATTERN.search(value)
    if numeric:
        day, month, year = numeric.groups()
        return f"{year}-{month}-{day}"

    text = value.replace(".", "").strip()
    match = re.search(r"\b(\d{1,2})\s+([A-Za-zÄÖÜäöüß]+)\s+(\d{4})\b", text)
    if not match:
        return ""
    day, month_name, year = match.groups()
    normalized_month = month_name.lower().replace("ä", "ae")
    month = GERMAN_MONTHS.get(normalized_month)
    if not month:
        return ""
    return f"{year}-{month}-{int(day):02d}"


def parse_depot_date(lines: list[str]) -> str:
    for line in lines:
        if "DEPOTAUSZUG" in line or line.startswith("zum ") or line.startswith("DATUM "):
            parsed = parse_german_date(line)
            if parsed:
                return parsed
    for line in lines:
        parsed = parse_german_date(line)
        if parsed:
            return parsed
    return ""


def is_position_start(line: str) -> bool:
    return bool(POSITION_START_PATTERN.match(line))


def is_amount_line(line: str) -> bool:
    return bool(re.fullmatch(r"[0-9][0-9.\s]*,\d{2}", line.strip()))


def infer_asset_type(raw_name: str) -> str:
    upper_name = raw_name.upper()
    if "ETF" in upper_name or "UCITS" in upper_name:
        return "ETF"
    return "STOCK"


def parse_depot_statement_text(text: str, source_name: str = "trade_republic_official_docs") -> list[dict[str, Any]]:
    lines = normalize_pdf_lines(text)
    portfolio_date = parse_depot_date(lines)
    rows: list[dict[str, Any]] = []
    index = 0

    while index < len(lines):
        start = POSITION_START_PATTERN.match(lines[index])
        if not start:
            index += 1
            continue

        quantity_text, first_name_line = start.groups()
        name_lines = [first_name_line.strip()]
        cursor = index + 1
        isin = ""
        while cursor < len(lines):
            line = lines[cursor]
            if line.startswith("ISIN:"):
                isin_match = ISIN_PATTERN.search(line)
                isin = isin_match.group(1) if isin_match else ""
                cursor += 1
                break
            if is_position_start(line) or line.startswith("ANZAHL POSITIONEN"):
                break
            name_lines.append(line)
            cursor += 1

        amount_values: list[float] = []
        while cursor < len(lines):
            line = lines[cursor]
            if is_position_start(line) or line.startswith("ANZAHL POSITIONEN"):
                break
            if is_amount_line(line):
                amount_values.append(to_float(line))
            cursor += 1

        raw_name = " ".join(name_lines)
        current_price = amount_values[0] if amount_values else 0.0
        market_value = amount_values[1] if len(amount_values) > 1 else 0.0
        review_reasons: list[str] = []
        if not isin:
            review_reasons.append("ISIN konnte nicht extrahiert werden")
        if len(amount_values) < 2:
            review_reasons.append("Kurs oder Kurswert konnte nicht vollstaendig extrahiert werden")
        if market_value == 0.0:
            review_reasons.append("Kurswert ist 0 oder fehlt; Position bleibt sichtbar")

        rows.append(
            {
                "portfolio_date": portfolio_date,
                "source_name": source_name,
                "source_type": "trade_republic_pdf",
                "raw_name": raw_name,
                "company_name": raw_name,
                "ticker": "",
                "isin": isin,
                "quantity": quantity_text,
                "current_price": current_price,
                "market_value": market_value,
                "currency": "EUR",
                "asset_type": infer_asset_type(raw_name),
                "position_type": "security",
                "sector": "Unknown",
                "country": "Unknown",
                "notes": "; ".join(review_reasons),
            }
        )
        index = max(cursor, index + 1)

    return rows


def parse_cash_statement_text(text: str, source_name: str = "trade_republic_official_docs") -> dict[str, Any]:
    lines = normalize_pdf_lines(text)
    portfolio_date = ""
    for line in lines:
        if line.startswith("DATUM "):
            parts = line.split("-", 1)
            portfolio_date = parse_german_date(parts[-1] if len(parts) > 1 else line)
            break

    for line in lines:
        if line.startswith("Cashkonto"):
            amounts = AMOUNT_PATTERN.findall(line)
            if not amounts:
                break
            cash_value = to_float(amounts[-1])
            return {
                "portfolio_date": portfolio_date,
                "source_name": source_name,
                "source_type": "trade_republic_pdf",
                "raw_name": "CASH",
                "company_name": "EUR-CASH",
                "ticker": "EUR-CASH",
                "isin": "",
                "quantity": cash_value,
                "current_price": 1.0,
                "avg_cost": 1.0,
                "market_value": cash_value,
                "currency": "EUR",
                "asset_type": "CASH",
                "position_type": "cash",
                "sector": "Cash",
                "country": "Eurozone",
                "sleeve": "CASH",
                "notes": "",
            }
    return {
        "portfolio_date": portfolio_date,
        "source_name": source_name,
        "source_type": "trade_republic_pdf",
        "raw_name": "CASH",
        "company_name": "EUR-CASH",
        "ticker": "EUR-CASH",
        "isin": "",
        "quantity": 0.0,
        "current_price": 1.0,
        "avg_cost": 1.0,
        "market_value": 0.0,
        "currency": "EUR",
        "asset_type": "CASH",
        "position_type": "cash",
        "sector": "Cash",
        "country": "Eurozone",
        "sleeve": "CASH",
        "notes": "Cash-Endsaldo konnte nicht extrahiert werden",
    }


def load_trade_republic_pdf_rows(
    depot_pdf: str | Path,
    cash_pdf: str | Path | None = None,
    source_name: str = "trade_republic_official_docs",
) -> list[dict[str, Any]]:
    rows = parse_depot_statement_text(extract_pdf_text(depot_pdf), source_name)
    if cash_pdf:
        rows.append(parse_cash_statement_text(extract_pdf_text(cash_pdf), source_name))
    return rows
