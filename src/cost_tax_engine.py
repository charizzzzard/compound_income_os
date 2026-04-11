from __future__ import annotations

import argparse
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, load_yaml_config, read_csv_rows, require_columns, require_non_blank_fields, round2, to_float, write_csv_rows
from src.traderepublic_documents import extract_pdf_text, normalize_pdf_lines, parse_german_date

DOCUMENT_SUMMARY_ONLY = "DOCUMENT_SUMMARY_ONLY"
PARTIAL_LEDGER = "PARTIAL_LEDGER"
FULL_LEDGER = "FULL_LEDGER"

EVENT = "EVENT"
DOCUMENT_SUMMARY = "DOCUMENT_SUMMARY"
PERIOD_SUMMARY = "PERIOD_SUMMARY"

VERIFIED = "VERIFIED"
PARTIAL = "PARTIAL"
UNVERIFIED = "UNVERIFIED"
REVIEW = "REVIEW"

OK_FLAG = "OK"
NOT_AVAILABLE = "NOT_AVAILABLE"
INSUFFICIENT_DOCUMENTATION = "INSUFFICIENT_DOCUMENTATION"

DEFAULT_CONFIG_PATH = "configs/cost_tax_ledger.yaml"
DEFAULT_NORMALIZED_LEDGER_OUTPUT = "data/processed/cost_tax_ledger_normalized.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/cost_tax_summary.csv"
DEFAULT_KPI_OUTPUT = "data/processed/cost_tax_kpis.csv"
DEFAULT_REPORT_OUTPUT = "reports/sample/cost_tax_report.md"

NORMALIZED_LEDGER_FIELDS = [
    "event_date",
    "broker",
    "document_type",
    "record_granularity",
    "event_type",
    "instrument_name",
    "ticker",
    "isin",
    "currency",
    "gross_amount",
    "net_amount",
    "fee_amount",
    "tax_amount",
    "withholding_tax_amount",
    "quantity",
    "price_per_unit",
    "reference_id",
    "source_name",
    "verification_status",
    "data_quality_flag",
    "notes",
    "event_group_id",
    "document_period_start",
    "document_period_end",
    "realized_proceeds_amount",
    "realized_cost_basis_amount",
    "realized_pnl_before_tax",
    "realized_pnl_after_tax_estimate_or_partial",
    "tax_jurisdiction",
]

SUMMARY_FIELDS = [
    "period_start",
    "period_end",
    "total_fees",
    "total_taxes",
    "total_withholding_taxes",
    "total_dividends_gross",
    "total_dividends_net",
    "total_interest_received",
    "total_realized_proceeds",
    "total_realized_cost_basis",
    "total_realized_pnl_before_tax",
    "total_realized_pnl_after_tax",
    "ledger_measurement_mode",
    "ledger_data_quality_flag",
    "notes",
]

KPI_FIELDS = [
    "metric_name",
    "metric_value",
    "metric_unit",
    "measurement_mode",
    "period",
    "data_quality_flag",
    "notes",
]

AMOUNT_PATTERN = re.compile(r"([0-9][0-9.\s]*,\d{2})")
PERIOD_PATTERN = re.compile(r"(\d{2}\.\d{2}\.\d{4})\s*-\s*(\d{2}\.\d{2}\.\d{4})")
YEAR_PATTERN = re.compile(r"(?:kalenderjahr|jahr)\s*(20\d{2})", re.IGNORECASE)
REFERENCE_ID_PATTERN = re.compile(r"(JSB[0-9A-Z.-]+|\d{7,}|\d{4,}-\d{4,})")


def parse_iso_date(value: Any, field_name: str) -> date:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"Missing required date field: {field_name}")
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Invalid date '{text}' in field {field_name}; expected YYYY-MM-DD") from exc


def format_optional_number(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return str(round2(to_float(text)))


def has_value(row: dict[str, Any], field_name: str) -> bool:
    return str(row.get(field_name, "")).strip() != ""


def combine_quality_flags(*values: str) -> str:
    flags: list[str] = []
    for value in values:
        for flag in str(value or "").split("|"):
            cleaned = flag.strip()
            if cleaned and cleaned not in flags:
                flags.append(cleaned)
    non_ok_flags = [flag for flag in flags if flag != OK_FLAG]
    if non_ok_flags:
        return "|".join(non_ok_flags)
    return OK_FLAG


def uppercase_or_blank(value: Any) -> str:
    return str(value or "").strip().upper()


def normalize_search_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def infer_reference_id(row: dict[str, str], index: int) -> str:
    explicit_reference = str(row.get("reference_id", "")).strip()
    if explicit_reference:
        return explicit_reference
    source_name = str(row.get("source_name", "")).strip() or "ledger"
    event_date = str(row.get("event_date", "")).strip() or "unknown-date"
    event_type = uppercase_or_blank(row.get("event_type")) or "UNKNOWN"
    return f"{source_name}:{event_date}:{event_type}:{index:04d}"


def normalize_manual_ledger_rows(rows: list[dict[str, str]], config: dict[str, Any], source_name: str) -> list[dict[str, str]]:
    require_columns(rows, config["required_columns"], f"cost/tax ledger ({source_name})")
    require_non_blank_fields(rows, config["required_non_blank_fields"], f"cost/tax ledger ({source_name})")
    allowed_granularity = set(config["allowed_record_granularity"])
    allowed_verification = set(config["allowed_verification_status"])
    allowed_event_types = set(config["allowed_event_types"])

    normalized_rows: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=1):
        event_date = parse_iso_date(row.get("event_date"), "event_date").isoformat()
        record_granularity = uppercase_or_blank(row.get("record_granularity"))
        verification_status = uppercase_or_blank(row.get("verification_status"))
        event_type = uppercase_or_blank(row.get("event_type"))
        if record_granularity not in allowed_granularity:
            raise ValueError(f"cost/tax ledger ({source_name}) row {index + 1} has invalid record_granularity: {record_granularity}")
        if verification_status not in allowed_verification:
            raise ValueError(f"cost/tax ledger ({source_name}) row {index + 1} has invalid verification_status: {verification_status}")
        if event_type not in allowed_event_types:
            raise ValueError(f"cost/tax ledger ({source_name}) row {index + 1} has invalid event_type: {event_type}")

        period_start = str(row.get("document_period_start", "")).strip()
        if period_start:
            period_start = parse_iso_date(period_start, "document_period_start").isoformat()
        period_end = str(row.get("document_period_end", "")).strip()
        if period_end:
            period_end = parse_iso_date(period_end, "document_period_end").isoformat()

        normalized_row = {
            "event_date": event_date,
            "broker": uppercase_or_blank(row.get("broker")) or uppercase_or_blank(config.get("default_broker", "")),
            "document_type": uppercase_or_blank(row.get("document_type")),
            "record_granularity": record_granularity,
            "event_type": event_type,
            "instrument_name": str(row.get("instrument_name", "")).strip(),
            "ticker": uppercase_or_blank(row.get("ticker")),
            "isin": uppercase_or_blank(row.get("isin")),
            "currency": uppercase_or_blank(row.get("currency")) or uppercase_or_blank(config.get("default_currency", "EUR")),
            "gross_amount": format_optional_number(row.get("gross_amount")),
            "net_amount": format_optional_number(row.get("net_amount")),
            "fee_amount": format_optional_number(row.get("fee_amount")),
            "tax_amount": format_optional_number(row.get("tax_amount")),
            "withholding_tax_amount": format_optional_number(row.get("withholding_tax_amount")),
            "quantity": format_optional_number(row.get("quantity")),
            "price_per_unit": format_optional_number(row.get("price_per_unit")),
            "reference_id": infer_reference_id(row, index),
            "source_name": str(row.get("source_name", "")).strip() or source_name,
            "verification_status": verification_status,
            "data_quality_flag": uppercase_or_blank(row.get("data_quality_flag")) or OK_FLAG,
            "notes": str(row.get("notes", "")).strip(),
            "event_group_id": str(row.get("event_group_id", "")).strip(),
            "document_period_start": period_start,
            "document_period_end": period_end,
            "realized_proceeds_amount": format_optional_number(row.get("realized_proceeds_amount")),
            "realized_cost_basis_amount": format_optional_number(row.get("realized_cost_basis_amount")),
            "realized_pnl_before_tax": format_optional_number(row.get("realized_pnl_before_tax")),
            "realized_pnl_after_tax_estimate_or_partial": format_optional_number(row.get("realized_pnl_after_tax_estimate_or_partial")),
            "tax_jurisdiction": uppercase_or_blank(row.get("tax_jurisdiction")),
        }
        normalized_rows.append(normalized_row)
    return sorted(normalized_rows, key=lambda current: (current["event_date"], current["reference_id"]))


def extract_amount_near_label(lines: list[str], label: str) -> str:
    label_lower = normalize_search_text(label)
    for index, line in enumerate(lines):
        if label_lower in normalize_search_text(line):
            for candidate in lines[index:index + 4]:
                match = AMOUNT_PATTERN.search(candidate)
                if match:
                    return format_optional_number(match.group(1))
    return ""


def extract_period_bounds_from_text(lines: list[str]) -> tuple[str, str]:
    for line in lines:
        match = PERIOD_PATTERN.search(line)
        if match:
            start_text, end_text = match.groups()
            start = parse_german_date(start_text)
            end = parse_german_date(end_text)
            if start and end:
                return start, end
    text_blob = " ".join(lines)
    year_match = YEAR_PATTERN.search(text_blob)
    if year_match:
        year = year_match.group(1)
        return f"{year}-01-01", f"{year}-12-31"
    return "", ""


def extract_reference_id(lines: list[str], fallback_name: str) -> str:
    for line in lines:
        match = REFERENCE_ID_PATTERN.search(line)
        if match:
            return match.group(1)
    return fallback_name


def parse_trade_republic_tax_document_text(
    text: str,
    source_name: str,
    document_name: str,
) -> list[dict[str, str]]:
    lines = normalize_pdf_lines(text)
    period_start, period_end = extract_period_bounds_from_text(lines)
    capital_income = extract_amount_near_label(lines, "Hoehe der Kapitalertraege")
    capital_gains_tax = extract_amount_near_label(lines, "Kapitalertragsteuer")
    solidarity = extract_amount_near_label(lines, "Solidaritaetszuschlag")
    church_tax = extract_amount_near_label(lines, "Kirchensteuer")
    foreign_tax = extract_amount_near_label(lines, "auslaendischen Steuer")
    realized_stock_gain = extract_amount_near_label(lines, "Gewinn aus Aktienveraeusserungen")

    tax_components = [value for value in [capital_gains_tax, solidarity, church_tax] if value]
    tax_amount = str(round2(sum(to_float(value) for value in tax_components))) if tax_components else ""
    verification_status = VERIFIED if capital_income and period_end else PARTIAL
    data_quality_flag = OK_FLAG if capital_income and period_end else REVIEW
    notes: list[str] = [
        "Aggregated yearly tax certificate imported as DOCUMENT_SUMMARY.",
        "Current parser is limited to explicit summary totals from Trade Republic tax certificates.",
    ]
    if not capital_income:
        notes.append("Kapitalertraege konnten nicht belastbar extrahiert werden.")
    if not tax_components:
        notes.append("Keine expliziten Steuerkomponenten extrahiert; tax_amount bleibt leer.")
    reference_id = extract_reference_id(lines, document_name)
    event_date = period_end or period_start
    if not event_date:
        raise ValueError(f"Unsupported Trade Republic tax document without extractable period: {document_name}")

    return [
        {
            "event_date": event_date,
            "broker": "TRADE_REPUBLIC",
            "document_type": "TRADE_REPUBLIC_YEARLY_TAX_CERTIFICATE",
            "record_granularity": DOCUMENT_SUMMARY,
            "event_type": "DOCUMENT_SUMMARY",
            "instrument_name": "",
            "ticker": "",
            "isin": "",
            "currency": "EUR",
            "gross_amount": capital_income,
            "net_amount": "",
            "fee_amount": "",
            "tax_amount": tax_amount,
            "withholding_tax_amount": foreign_tax,
            "quantity": "",
            "price_per_unit": "",
            "reference_id": reference_id,
            "source_name": source_name,
            "verification_status": verification_status,
            "data_quality_flag": data_quality_flag,
            "notes": " ".join(notes),
            "event_group_id": "",
            "document_period_start": period_start,
            "document_period_end": period_end,
            "realized_proceeds_amount": "",
            "realized_cost_basis_amount": "",
            "realized_pnl_before_tax": realized_stock_gain,
            "realized_pnl_after_tax_estimate_or_partial": "",
            "tax_jurisdiction": "DE",
        }
    ]


def load_document_rows(document_paths: list[str], source_name: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path_value in document_paths:
        file_name = Path(path_value).name
        lowered = file_name.lower()
        if "steuerbericht" in lowered or "steuerreport" in lowered:
            rows.extend(parse_trade_republic_tax_document_text(extract_pdf_text(path_value), source_name, file_name))
            continue
        raise ValueError(f"Unsupported document input for cost/tax engine: {path_value}")
    return rows


def determine_measurement_mode(rows: list[dict[str, str]], requested_mode: str) -> str:
    if not rows:
        raise ValueError("cost/tax ledger contains no rows after normalization.")
    has_event_rows = any(row["record_granularity"] == EVENT for row in rows)
    summary_only = all(row["record_granularity"] in {DOCUMENT_SUMMARY, PERIOD_SUMMARY} for row in rows)
    all_event_verified = all(
        row["record_granularity"] == EVENT
        and row["verification_status"] == VERIFIED
        and row["data_quality_flag"] == OK_FLAG
        for row in rows
    )
    detected = DOCUMENT_SUMMARY_ONLY if summary_only else FULL_LEDGER if all_event_verified else PARTIAL_LEDGER
    if requested_mode == "auto":
        return detected
    requested_map = {
        "summary": DOCUMENT_SUMMARY_ONLY,
        "partial": PARTIAL_LEDGER,
        "full": FULL_LEDGER,
    }
    requested = requested_map[requested_mode]
    if requested == DOCUMENT_SUMMARY_ONLY and not summary_only:
        raise ValueError("measurement mode 'summary' requires only DOCUMENT_SUMMARY/PERIOD_SUMMARY rows.")
    if requested == FULL_LEDGER and detected != FULL_LEDGER:
        raise ValueError("measurement mode 'full' requires only VERIFIED EVENT rows with OK data quality.")
    if requested == PARTIAL_LEDGER and not has_event_rows:
        raise ValueError("measurement mode 'partial' requires at least one EVENT row.")
    return requested


def metric_period(rows: list[dict[str, str]]) -> tuple[str, str]:
    period_starts: list[date] = []
    period_ends: list[date] = []
    for row in rows:
        start_text = row["document_period_start"] or row["event_date"]
        end_text = row["document_period_end"] or row["event_date"]
        period_starts.append(parse_iso_date(start_text, "period_start"))
        period_ends.append(parse_iso_date(end_text, "period_end"))
    return min(period_starts).isoformat(), max(period_ends).isoformat()


def select_rows(rows: list[dict[str, str]], event_types: set[str]) -> list[dict[str, str]]:
    return [row for row in rows if row["event_type"] in event_types]


def sum_explicit_field(rows: list[dict[str, str]], field_name: str) -> float | None:
    values = [to_float(row[field_name]) for row in rows if has_value(row, field_name)]
    if not values:
        return None
    return round2(sum(values))


def compute_dividends_net(dividend_rows: list[dict[str, str]]) -> float | None:
    if not dividend_rows:
        return None
    derived_values: list[float] = []
    for row in dividend_rows:
        if has_value(row, "net_amount"):
            derived_values.append(to_float(row["net_amount"]))
            continue
        if has_value(row, "gross_amount") and has_value(row, "tax_amount") and has_value(row, "withholding_tax_amount"):
            derived_values.append(round2(to_float(row["gross_amount"]) - to_float(row["tax_amount"]) - to_float(row["withholding_tax_amount"])))
            continue
        return None
    return round2(sum(derived_values))


def detect_realized_evidence(rows: list[dict[str, str]]) -> bool:
    return any(
        has_value(row, "realized_proceeds_amount")
        or has_value(row, "realized_cost_basis_amount")
        or has_value(row, "realized_pnl_before_tax")
        or has_value(row, "realized_pnl_after_tax_estimate_or_partial")
        for row in rows
    )


def build_summary_values(rows: list[dict[str, str]], measurement_mode: str) -> tuple[dict[str, str], list[dict[str, str]]]:
    period_start, period_end = metric_period(rows)
    ledger_data_quality_flag = combine_quality_flags(*(row["data_quality_flag"] for row in rows))
    notes = [
        "Manual CSV ledger is the primary Phase 2C input path.",
        "Trade Republic document support remains limited to position snapshot, cash end balance, and optional yearly tax summary extraction.",
        "`avg_cost`, `cost_basis_eur` and `unrealized_pnl_eur` from the positions snapshot are not treated as a tax event ledger.",
    ]

    dividend_rows = select_rows(rows, {"DIVIDEND"})
    interest_rows = select_rows(rows, {"INTEREST"})
    trade_rows = select_rows(rows, {"BUY", "SELL"})

    total_fees_value = sum_explicit_field(rows, "fee_amount")
    total_taxes_value = sum_explicit_field(rows, "tax_amount")
    total_withholding_value = sum_explicit_field(rows, "withholding_tax_amount")
    total_dividends_gross_value = sum_explicit_field(dividend_rows, "gross_amount")
    total_dividends_net_value = compute_dividends_net(dividend_rows)
    total_interest_value = sum_explicit_field(interest_rows, "net_amount")
    if total_interest_value is None:
        total_interest_value = sum_explicit_field(interest_rows, "gross_amount")

    if total_fees_value is None and measurement_mode == FULL_LEDGER and not trade_rows:
        total_fees_value = 0.0
    if total_taxes_value is None and measurement_mode == FULL_LEDGER:
        total_taxes_value = 0.0
    if total_withholding_value is None and measurement_mode == FULL_LEDGER:
        total_withholding_value = 0.0
    if total_dividends_gross_value is None and measurement_mode == FULL_LEDGER and not dividend_rows:
        total_dividends_gross_value = 0.0
    if total_dividends_net_value is None and measurement_mode == FULL_LEDGER and not dividend_rows:
        total_dividends_net_value = 0.0
    if total_interest_value is None and measurement_mode == FULL_LEDGER and not interest_rows:
        total_interest_value = 0.0

    realized_evidence = detect_realized_evidence(rows)
    total_realized_proceeds_value = sum_explicit_field(rows, "realized_proceeds_amount") if realized_evidence else None
    total_realized_cost_basis_value = sum_explicit_field(rows, "realized_cost_basis_amount") if realized_evidence else None
    total_realized_pnl_before_tax_value = sum_explicit_field(rows, "realized_pnl_before_tax") if realized_evidence else None
    if realized_evidence and total_realized_pnl_before_tax_value is None and total_realized_proceeds_value is not None and total_realized_cost_basis_value is not None:
        total_realized_pnl_before_tax_value = round2(total_realized_proceeds_value - total_realized_cost_basis_value)
    total_realized_pnl_after_tax_value = sum_explicit_field(rows, "realized_pnl_after_tax_estimate_or_partial") if realized_evidence else None

    trade_rows_with_explicit_fees = [row for row in trade_rows if has_value(row, "fee_amount")]
    average_fee_per_trade_value = None
    if trade_rows and len(trade_rows_with_explicit_fees) == len(trade_rows) and total_fees_value is not None:
        average_fee_per_trade_value = round2(total_fees_value / len(trade_rows))

    dividend_tax_rate_effective_value = None
    gross_to_net_dividend_gap_value = None
    if total_dividends_gross_value is not None and total_dividends_gross_value > 0.0 and total_dividends_net_value is not None:
        total_dividend_taxes = 0.0
        for row in dividend_rows:
            total_dividend_taxes += to_float(row.get("tax_amount"))
            total_dividend_taxes += to_float(row.get("withholding_tax_amount"))
        gross_to_net_dividend_gap_value = round2(total_dividends_gross_value - total_dividends_net_value)
        dividend_tax_rate_effective_value = round2((total_dividend_taxes / total_dividends_gross_value) * 100.0)

    realized_tax_drag_value = None
    if total_realized_pnl_before_tax_value is not None and total_realized_pnl_after_tax_value is not None:
        realized_tax_drag_value = round2(total_realized_pnl_before_tax_value - total_realized_pnl_after_tax_value)

    summary_row = {
        "period_start": period_start,
        "period_end": period_end,
        "total_fees": str(total_fees_value) if total_fees_value is not None else NOT_AVAILABLE,
        "total_taxes": str(total_taxes_value) if total_taxes_value is not None else NOT_AVAILABLE,
        "total_withholding_taxes": str(total_withholding_value) if total_withholding_value is not None else NOT_AVAILABLE,
        "total_dividends_gross": str(total_dividends_gross_value) if total_dividends_gross_value is not None else NOT_AVAILABLE,
        "total_dividends_net": str(total_dividends_net_value) if total_dividends_net_value is not None else NOT_AVAILABLE,
        "total_interest_received": str(total_interest_value) if total_interest_value is not None else NOT_AVAILABLE,
        "total_realized_proceeds": str(total_realized_proceeds_value) if total_realized_proceeds_value is not None else INSUFFICIENT_DOCUMENTATION,
        "total_realized_cost_basis": str(total_realized_cost_basis_value) if total_realized_cost_basis_value is not None else INSUFFICIENT_DOCUMENTATION,
        "total_realized_pnl_before_tax": str(total_realized_pnl_before_tax_value) if total_realized_pnl_before_tax_value is not None else INSUFFICIENT_DOCUMENTATION,
        "total_realized_pnl_after_tax": str(total_realized_pnl_after_tax_value) if total_realized_pnl_after_tax_value is not None else INSUFFICIENT_DOCUMENTATION,
        "ledger_measurement_mode": measurement_mode,
        "ledger_data_quality_flag": ledger_data_quality_flag,
        "notes": " ".join(notes),
    }

    derived_kpis = [
        ("ledger_measurement_mode", measurement_mode, "TEXT", OK_FLAG, "Detected cost/tax measurement mode."),
        ("ledger_data_quality_flag", ledger_data_quality_flag, "TEXT", ledger_data_quality_flag, "Combined ledger data quality flag."),
        ("period_start", period_start, "DATE", ledger_data_quality_flag, "Earliest covered date across ledger rows."),
        ("period_end", period_end, "DATE", ledger_data_quality_flag, "Latest covered date across ledger rows."),
        ("total_fees", summary_row["total_fees"], "EUR", ledger_data_quality_flag, "Aggregated explicit fee_amount values."),
        ("total_taxes", summary_row["total_taxes"], "EUR", ledger_data_quality_flag, "Aggregated explicit tax_amount values."),
        ("total_withholding_taxes", summary_row["total_withholding_taxes"], "EUR", ledger_data_quality_flag, "Aggregated explicit withholding_tax_amount values."),
        ("total_dividends_gross", summary_row["total_dividends_gross"], "EUR", ledger_data_quality_flag, "Aggregated explicit dividend gross amounts."),
        ("total_dividends_net", summary_row["total_dividends_net"], "EUR", ledger_data_quality_flag, "Dividend net amounts, derived from gross - taxes - withholding taxes when net_amount is not explicit."),
        ("total_interest_received", summary_row["total_interest_received"], "EUR", ledger_data_quality_flag, "Interest receipts from explicit INTEREST rows."),
        ("total_realized_proceeds", summary_row["total_realized_proceeds"], "EUR", ledger_data_quality_flag, "Available only with explicit realized evidence."),
        ("total_realized_cost_basis", summary_row["total_realized_cost_basis"], "EUR", ledger_data_quality_flag, "Available only with explicit realized evidence."),
        ("total_realized_pnl_before_tax", summary_row["total_realized_pnl_before_tax"], "EUR", ledger_data_quality_flag, "Available only with explicit realized evidence."),
        ("total_realized_pnl_after_tax_estimate_or_partial", summary_row["total_realized_pnl_after_tax"], "EUR", ledger_data_quality_flag, "Available only with explicit after-tax realized fields."),
        ("average_fee_per_trade", str(average_fee_per_trade_value) if average_fee_per_trade_value is not None else NOT_AVAILABLE, "EUR", ledger_data_quality_flag, "Requires explicit fee_amount on all BUY/SELL rows used in the covered period."),
        ("dividend_tax_rate_effective", str(dividend_tax_rate_effective_value) if dividend_tax_rate_effective_value is not None else NOT_AVAILABLE, "PCT", ledger_data_quality_flag, "Requires explicit dividend gross and explicit/derivable tax components."),
        ("gross_to_net_dividend_gap", str(gross_to_net_dividend_gap_value) if gross_to_net_dividend_gap_value is not None else NOT_AVAILABLE, "EUR", ledger_data_quality_flag, "Difference between gross and net dividends when net dividends are explicit or derivable."),
        ("realized_tax_drag", str(realized_tax_drag_value) if realized_tax_drag_value is not None else NOT_AVAILABLE, "EUR", ledger_data_quality_flag, "Requires explicit realized pnl before tax and explicit realized pnl after tax."),
        ("fee_drag_estimate", NOT_AVAILABLE, "EUR", ledger_data_quality_flag, "Phase 2C does not estimate fee drag relative to performance without a synchronized period-level return base."),
        ("net_performance_after_costs", NOT_AVAILABLE, "PCT", ledger_data_quality_flag, "Phase 2C does not infer net performance from ledger totals without an aligned performance period."),
        ("net_performance_after_costs_and_taxes", NOT_AVAILABLE, "PCT", ledger_data_quality_flag, "Phase 2C does not infer after-tax performance without aligned performance and cashflow periods."),
    ]

    kpi_rows = [
        {
            "metric_name": name,
            "metric_value": value,
            "metric_unit": unit,
            "measurement_mode": measurement_mode,
            "period": f"{period_start}..{period_end}",
            "data_quality_flag": flag,
            "notes": notes_text,
        }
        for name, value, unit, flag, notes_text in derived_kpis
    ]
    return summary_row, kpi_rows


def build_report_text(summary_row: dict[str, str], kpi_rows: list[dict[str, str]], rows: list[dict[str, str]]) -> str:
    record_counts = {
        EVENT: sum(1 for row in rows if row["record_granularity"] == EVENT),
        DOCUMENT_SUMMARY: sum(1 for row in rows if row["record_granularity"] == DOCUMENT_SUMMARY),
        PERIOD_SUMMARY: sum(1 for row in rows if row["record_granularity"] == PERIOD_SUMMARY),
    }
    lines = [
        "# Cost and Tax Report",
        "",
        "## Datenlage",
        "",
        f"- Measurement Mode: {summary_row['ledger_measurement_mode']}",
        f"- Period: {summary_row['period_start']} bis {summary_row['period_end']}",
        f"- Data Quality Flag: {summary_row['ledger_data_quality_flag']}",
        f"- EVENT rows: {record_counts[EVENT]}",
        f"- DOCUMENT_SUMMARY rows: {record_counts[DOCUMENT_SUMMARY]}",
        f"- PERIOD_SUMMARY rows: {record_counts[PERIOD_SUMMARY]}",
        "",
        "## Aggregierte Sicht",
        "",
        f"- Total Fees: {summary_row['total_fees']}",
        f"- Total Taxes: {summary_row['total_taxes']}",
        f"- Total Withholding Taxes: {summary_row['total_withholding_taxes']}",
        f"- Total Dividends Gross: {summary_row['total_dividends_gross']}",
        f"- Total Dividends Net: {summary_row['total_dividends_net']}",
        f"- Total Interest Received: {summary_row['total_interest_received']}",
        f"- Total Realized PnL Before Tax: {summary_row['total_realized_pnl_before_tax']}",
        f"- Total Realized PnL After Tax: {summary_row['total_realized_pnl_after_tax']}",
        "",
        "## Methodik und Grenzen",
        "",
        "- Phase 2C trennt strikt zwischen `EVENT`, `DOCUMENT_SUMMARY` und `PERIOD_SUMMARY`.",
        "- `verification_status` trennt belastbare, partielle und ungepruefte Datensaetze explizit.",
        "- Der bestehende Trade-Republic-PDF-Pfad fuer `Depotauszug.pdf` und `Kontoauszug.pdf` erzeugt kein vollstaendiges Transaktions- oder Steuer-Ledger.",
        "- `avg_cost`, `cost_basis_eur` und `unrealized_pnl_eur` aus dem Positions-Snapshot werden nicht als Ersatz fuer ein steuerliches Event-Ledger verwendet.",
        "- Realized PnL wird nur ausgewiesen, wenn explizite realized-Felder im Ledger oder im dokumentierten Summary vorliegen.",
        "- Netto-/After-Tax-Performance wird ohne sauber verknuepfte Perioden zu Phase 2B nicht berechnet.",
        "",
        "## KPI Detail",
        "",
        "| metric_name | metric_value | metric_unit | data_quality_flag | notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in kpi_rows:
        lines.append(f"| {row['metric_name']} | {row['metric_value']} | {row['metric_unit']} | {row['data_quality_flag']} | {row['notes']} |")
    return "\n".join(lines) + "\n"


def run_cost_tax_engine(
    ledger_path: str | None,
    normalized_ledger_output: str,
    summary_output: str,
    kpi_output: str,
    report_output: str,
    config_path: str = DEFAULT_CONFIG_PATH,
    document_inputs: list[str] | None = None,
    measurement_mode: str = "auto",
) -> dict[str, Path]:
    config = load_yaml_config(config_path)
    ledger_rows = read_csv_rows(ledger_path) if ledger_path else []
    normalized_rows = normalize_manual_ledger_rows(ledger_rows, config, ledger_path or "manual_cost_tax_ledger") if ledger_rows else []
    if document_inputs:
        normalized_rows.extend(load_document_rows(document_inputs, "document_summary_input"))
    if not normalized_rows:
        raise ValueError("cost/tax engine requires --ledger and/or --document-input with at least one parseable row.")
    normalized_rows = sorted(normalized_rows, key=lambda current: (current["event_date"], current["reference_id"]))

    detected_measurement_mode = determine_measurement_mode(normalized_rows, measurement_mode)
    summary_row, kpi_rows = build_summary_values(normalized_rows, detected_measurement_mode)

    outputs = {
        "normalized_ledger_output": write_csv_rows(normalized_ledger_output, NORMALIZED_LEDGER_FIELDS, normalized_rows),
        "summary_output": write_csv_rows(summary_output, SUMMARY_FIELDS, [summary_row]),
        "kpi_output": write_csv_rows(kpi_output, KPI_FIELDS, kpi_rows),
    }
    report_path = ensure_parent_dir(report_output)
    report_path.write_text(build_report_text(summary_row, kpi_rows, normalized_rows), encoding="utf-8")
    outputs["report_output"] = report_path
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic cost and tax ledger artifacts.")
    parser.add_argument("--ledger", help="Manual cost/tax ledger CSV input.")
    parser.add_argument("--document-input", action="append", default=[], help="Optional supported document input, e.g. Trade Republic yearly tax report PDF.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Cost/tax ledger config path.")
    parser.add_argument("--measurement-mode", choices=["auto", "summary", "partial", "full"], default="auto", help="Measurement mode override.")
    parser.add_argument("--normalized-ledger-output", default=DEFAULT_NORMALIZED_LEDGER_OUTPUT, help="Normalized ledger CSV output.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT, help="Summary CSV output.")
    parser.add_argument("--kpi-output", default=DEFAULT_KPI_OUTPUT, help="KPI CSV output.")
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT, help="Markdown report output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_cost_tax_engine(
        ledger_path=args.ledger,
        normalized_ledger_output=args.normalized_ledger_output,
        summary_output=args.summary_output,
        kpi_output=args.kpi_output,
        report_output=args.report_output,
        config_path=args.config,
        document_inputs=args.document_input,
        measurement_mode=args.measurement_mode,
    )


if __name__ == "__main__":
    main()
