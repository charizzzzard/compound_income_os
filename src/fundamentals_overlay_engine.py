from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, ensure_parent_dir, load_yaml_config, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows
from src.fundamentals_master import (
    DEFAULT_PERSONAL_MASTER_PATH,
    OVERLAY_FIELDS,
    PERSONAL_MASTER_FIELDS,
    validate_personal_fundamentals_master,
)

DEFAULT_SCHEMA_PATH = "configs/fundamentals_schema.yaml"
DEFAULT_OVERLAY_INPUT_PATH = "data/raw/personal_fundamentals_overlay.csv"
DEFAULT_OVERLAY_TEMPLATE_PATH = "data/raw/personal_fundamentals_overlay_template.csv"
DEFAULT_OVERLAY_REGISTRY_OUTPUT = "data/processed/personal_fundamentals_overlay_registry.csv"
DEFAULT_APPLIED_MASTER_OUTPUT = "data/processed/personal_fundamentals_master_applied.csv"
DEFAULT_OVERLAY_SUMMARY_OUTPUT = "data/processed/personal_fundamentals_overlay_summary.csv"
DEFAULT_OVERLAY_REVIEW_BACKLOG_OUTPUT = "data/processed/personal_fundamentals_overlay_review_backlog.csv"

VALID_VERIFICATION_STATUSES = {"VERIFIED", "REVIEW", "UNVERIFIED"}
VALID_OVERLAY_PRIORITIES = {"HIGH", "MEDIUM", "LOW"}
OVERLAY_REVIEW_DUE_SOON_DAYS = 30
TRUE_VALUES = {"TRUE", "1", "YES", "Y"}
FALSE_VALUES = {"FALSE", "0", "NO", "N"}

OVERLAY_REQUIRED_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "overlay_as_of_date",
    "overlay_source_name",
    "overlay_author",
    "overlay_thesis_robustness",
    "overlay_has_hard_risk_flag",
    "overlay_analyst_notes",
    "overlay_manual_override_flag",
    "overlay_manual_override_reason",
    "verification_status",
    "notes",
]

OVERLAY_OPTIONAL_FIELDS = [
    "overlay_review_due_date",
    "overlay_priority",
    "source_reference",
]

OVERLAY_INPUT_FIELDS = [*OVERLAY_REQUIRED_FIELDS, *OVERLAY_OPTIONAL_FIELDS]

OVERLAY_IDENTITY_FIELDS = [
    "ticker",
    "isin",
    "overlay_as_of_date",
    "overlay_author",
]

OVERLAY_REGISTRY_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "overlay_as_of_date",
    "overlay_author",
    "overlay_source_name",
    "source_reference",
    "overlay_thesis_robustness",
    "overlay_has_hard_risk_flag",
    "overlay_analyst_notes",
    "overlay_manual_override_flag",
    "overlay_manual_override_reason",
    "overlay_review_due_date",
    "overlay_review_status",
    "needs_overlay_review_flag",
    "overlay_priority",
    "verification_status",
    "overlay_validation_status",
    "overlay_active_flag",
    "overlay_identity",
    "notes",
]

APPLIED_MASTER_EXTRA_FIELDS = [
    "overlay_active_flag",
    "overlay_applied_as_of_date",
]

APPLIED_MASTER_FIELDS = [*PERSONAL_MASTER_FIELDS, *APPLIED_MASTER_EXTRA_FIELDS]
OVERLAY_REVIEW_BACKLOG_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "overlay_as_of_date",
    "overlay_review_due_date",
    "overlay_review_status",
    "overlay_author",
    "overlay_source_name",
    "overlay_has_hard_risk_flag",
    "overlay_manual_override_flag",
    "overlay_priority",
    "needs_overlay_review_flag",
    "notes",
]
OVERLAY_SUMMARY_FIELDS = ["metric_name", "metric_value", "notes"]


def default_overlay_report_path() -> str:
    return f"reports/{date.today().isoformat()}/personal_fundamentals_overlay_report.md"


def read_csv_rows_with_header(path_value: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def require_header_columns(fieldnames: list[str], required_columns: list[str], source_name: str) -> None:
    available = set(fieldnames)
    missing = [field for field in required_columns if field not in available]
    if missing:
        raise ValueError(f"{source_name} missing required columns: {', '.join(sorted(missing))}")


def require_nonblank_value(row: dict[str, str], field: str, source_name: str, row_number: int) -> str:
    text = str(row.get(field, "") or "").strip()
    if not text:
        raise ValueError(f"{source_name} row {row_number} has blank required field(s): {field}")
    return text


def parse_iso_date_text(value: Any, field: str, source_name: str, row_number: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{source_name} row {row_number} has blank required field(s): {field}")
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{source_name} row {row_number} has invalid {field}: {text!r}; expected YYYY-MM-DD") from exc
    return text


def parse_optional_iso_date_text(value: Any, field: str, source_name: str, row_number: int) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return parse_iso_date_text(text, field, source_name, row_number)


def compute_overlay_review_status(due_date_text: str, run_date: date) -> str:
    if not due_date_text:
        return "NOT_SET"
    due_date = date.fromisoformat(due_date_text)
    if due_date < run_date:
        return "OVERDUE"
    if due_date <= run_date + timedelta(days=OVERLAY_REVIEW_DUE_SOON_DAYS):
        return "DUE"
    return "OK"


def parse_bool_text(value: Any, field: str, source_name: str, row_number: int) -> str:
    text = safe_upper(value)
    if text in TRUE_VALUES:
        return "True"
    if text in FALSE_VALUES:
        return "False"
    raise ValueError(
        f"{source_name} row {row_number} has invalid {field}: {value!r}; "
        "allowed boolean values: TRUE/FALSE, YES/NO, 1/0"
    )


def load_allowed_overlay_thesis_values(schema_path: str = DEFAULT_SCHEMA_PATH) -> set[str]:
    schema = load_yaml_config(schema_path)
    values = schema.get("overlay_fields", {}).get("overlay_thesis_robustness", {}).get("allowed", [])
    allowed = {safe_upper(value) for value in values}
    if not allowed:
        raise ValueError(f"fundamentals schema ({schema_path}) missing overlay_thesis_robustness allowed values")
    return allowed


def overlay_identity(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "") or "").strip() for field in OVERLAY_IDENTITY_FIELDS)


def overlay_identity_text(identity: tuple[str, ...]) -> str:
    return ", ".join(f"{field}={value or '<blank>'}" for field, value in zip(OVERLAY_IDENTITY_FIELDS, identity, strict=True))


def registry_content_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "") or "").strip() for field in OVERLAY_REGISTRY_FIELDS)


def master_identifier_key(row: dict[str, str]) -> tuple[str, str]:
    return canonicalize_ticker(row.get("ticker", "")), str(row.get("isin", "") or "").strip().upper()


def validate_master_identifier_uniqueness(master_rows: list[dict[str, str]]) -> None:
    for field, normalizer in [
        ("ticker", lambda row: canonicalize_ticker(row.get("ticker", ""))),
        ("isin", lambda row: str(row.get("isin", "") or "").strip().upper()),
    ]:
        counts = Counter(normalizer(row) for row in master_rows if normalizer(row))
        duplicates = sorted(value for value, count in counts.items() if count > 1)
        if duplicates:
            raise ValueError(f"personal fundamentals master has duplicate {field} value(s); overlay matching would be ambiguous: {', '.join(duplicates)}")


def build_master_identifier_index(master_rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    validate_master_identifier_uniqueness(master_rows)
    index: dict[str, dict[str, dict[str, str]]] = {"ticker": {}, "isin": {}}
    for row in master_rows:
        ticker, isin = master_identifier_key(row)
        if ticker:
            index["ticker"][ticker] = row
        if isin:
            index["isin"][isin] = row
    return index


def match_overlay_to_master(
    row: dict[str, str],
    master_index: dict[str, dict[str, dict[str, str]]],
    source_name: str,
    row_number: int,
) -> dict[str, str]:
    ticker = canonicalize_ticker(row.get("ticker", ""))
    isin = str(row.get("isin", "") or "").strip().upper()
    if not ticker and not isin:
        raise ValueError(f"{source_name} row {row_number} requires ticker or isin for exact Personal-Master matching")

    ticker_match = master_index["ticker"].get(ticker) if ticker else None
    isin_match = master_index["isin"].get(isin) if isin else None
    if ticker_match is not None and isin_match is not None and id(ticker_match) != id(isin_match):
        raise ValueError(f"{source_name} row {row_number} has conflicting ticker/isin matches in personal fundamentals master: ticker={ticker}, isin={isin}")

    matched = isin_match or ticker_match
    if matched is None:
        raise ValueError(f"{source_name} row {row_number} has no exact ticker/isin match in personal fundamentals master: ticker={ticker or '<blank>'}, isin={isin or '<blank>'}")

    matched_ticker, matched_isin = master_identifier_key(matched)
    if ticker and matched_ticker and ticker != matched_ticker:
        raise ValueError(f"{source_name} row {row_number} ticker={ticker} conflicts with matched master ticker={matched_ticker}")
    if isin and matched_isin and isin != matched_isin:
        raise ValueError(f"{source_name} row {row_number} isin={isin} conflicts with matched master isin={matched_isin}")
    return matched


def canonical_overlay_registry_row(
    row: dict[str, str],
    master_row: dict[str, str],
    allowed_thesis_values: set[str],
    source_name: str,
    row_number: int,
    run_date: date,
) -> dict[str, str]:
    overlay_as_of_date = parse_iso_date_text(row.get("overlay_as_of_date", ""), "overlay_as_of_date", source_name, row_number)
    overlay_author = require_nonblank_value(row, "overlay_author", source_name, row_number)
    overlay_source_name = require_nonblank_value(row, "overlay_source_name", source_name, row_number)
    thesis = safe_upper(require_nonblank_value(row, "overlay_thesis_robustness", source_name, row_number))
    if thesis not in allowed_thesis_values:
        raise ValueError(
            f"{source_name} row {row_number} has invalid overlay_thesis_robustness: {row.get('overlay_thesis_robustness')!r}; "
            f"allowed: {', '.join(sorted(allowed_thesis_values))}"
        )
    hard_risk = parse_bool_text(row.get("overlay_has_hard_risk_flag", ""), "overlay_has_hard_risk_flag", source_name, row_number)
    manual_override = parse_bool_text(row.get("overlay_manual_override_flag", ""), "overlay_manual_override_flag", source_name, row_number)
    manual_reason = str(row.get("overlay_manual_override_reason", "") or "").strip()
    if manual_override == "True" and not manual_reason:
        raise ValueError(f"{source_name} row {row_number} has overlay_manual_override_flag=true but blank overlay_manual_override_reason")

    verification_status = safe_upper(require_nonblank_value(row, "verification_status", source_name, row_number))
    if verification_status not in VALID_VERIFICATION_STATUSES:
        raise ValueError(
            f"{source_name} row {row_number} has invalid verification_status: {row.get('verification_status')!r}; "
            f"allowed: {', '.join(sorted(VALID_VERIFICATION_STATUSES))}"
        )

    overlay_priority = safe_upper(row.get("overlay_priority", ""))
    if overlay_priority and overlay_priority not in VALID_OVERLAY_PRIORITIES:
        raise ValueError(
            f"{source_name} row {row_number} has invalid overlay_priority: {row.get('overlay_priority')!r}; "
            f"allowed: {', '.join(sorted(VALID_OVERLAY_PRIORITIES))}"
        )

    ticker, isin = master_identifier_key(master_row)
    overlay_review_due_date = parse_optional_iso_date_text(row.get("overlay_review_due_date", ""), "overlay_review_due_date", source_name, row_number)
    overlay_review_status = compute_overlay_review_status(overlay_review_due_date, run_date)
    registry_row = {
        "ticker": ticker,
        "isin": isin,
        "company_name": str(master_row.get("company_name", "") or "").strip(),
        "overlay_as_of_date": overlay_as_of_date,
        "overlay_author": overlay_author,
        "overlay_source_name": overlay_source_name,
        "source_reference": str(row.get("source_reference", "") or "").strip(),
        "overlay_thesis_robustness": thesis,
        "overlay_has_hard_risk_flag": hard_risk,
        "overlay_analyst_notes": str(row.get("overlay_analyst_notes", "") or "").strip(),
        "overlay_manual_override_flag": manual_override,
        "overlay_manual_override_reason": manual_reason,
        "overlay_review_due_date": overlay_review_due_date,
        "overlay_review_status": overlay_review_status,
        "needs_overlay_review_flag": str(overlay_review_status in {"DUE", "OVERDUE"}),
        "overlay_priority": overlay_priority,
        "verification_status": verification_status,
        "overlay_validation_status": "VALID",
        "overlay_active_flag": "True",
        "overlay_identity": "",
        "notes": str(row.get("notes", "") or "").strip(),
    }
    registry_row["overlay_identity"] = overlay_identity_text(overlay_identity(registry_row))
    return registry_row


def registry_sort_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        canonicalize_ticker(row.get("ticker", "")),
        str(row.get("isin", "") or "").strip().upper(),
        str(row.get("overlay_as_of_date", "") or "").strip(),
        str(row.get("overlay_author", "") or "").strip(),
        str(row.get("overlay_source_name", "") or "").strip(),
        str(row.get("source_reference", "") or "").strip(),
    )


def build_overlay_registry(
    overlay_rows: list[dict[str, str]],
    master_rows: list[dict[str, str]],
    allowed_thesis_values: set[str],
    source_name: str = "personal fundamentals overlay",
    run_date: date | None = None,
) -> list[dict[str, str]]:
    effective_run_date = run_date or date.today()
    master_index = build_master_identifier_index(master_rows)
    indexed: dict[tuple[str, ...], dict[str, str]] = {}
    for row_number, row in enumerate(overlay_rows, start=2):
        master_row = match_overlay_to_master(row, master_index, source_name, row_number)
        registry_row = canonical_overlay_registry_row(row, master_row, allowed_thesis_values, source_name, row_number, effective_run_date)
        identity = overlay_identity(registry_row)
        existing = indexed.get(identity)
        if existing is None:
            indexed[identity] = registry_row
            continue
        if registry_content_key(existing) != registry_content_key(registry_row):
            raise ValueError(f"personal fundamentals overlay conflict for identity {overlay_identity_text(identity)}")
    return sorted(indexed.values(), key=registry_sort_key)


def applied_master_sort_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        canonicalize_ticker(row.get("ticker", "")),
        str(row.get("isin", "") or "").strip().upper(),
        str(row.get("company_name", "") or "").strip(),
    )


def choose_active_overlays(registry_rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    by_holding: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in registry_rows:
        key = canonicalize_ticker(row.get("ticker", "")), str(row.get("isin", "") or "").strip().upper()
        by_holding.setdefault(key, []).append(row)

    selected: dict[tuple[str, str], dict[str, str]] = {}
    for key, rows in by_holding.items():
        latest_date = max(str(row.get("overlay_as_of_date", "") or "").strip() for row in rows)
        latest_rows = [row for row in rows if str(row.get("overlay_as_of_date", "") or "").strip() == latest_date]
        if len(latest_rows) > 1:
            identity_text = f"ticker={key[0] or '<blank>'}, isin={key[1] or '<blank>'}, overlay_as_of_date={latest_date}"
            raise ValueError(f"multiple active personal fundamentals overlays for {identity_text}; latest-date tie requires manual cleanup")
        selected[key] = latest_rows[0]
    return selected


def overlay_review_priority_sort_value(priority: str) -> int:
    return {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "": 3}.get(priority, 4)


def overlay_review_status_sort_value(status: str) -> int:
    return {"OVERDUE": 0, "DUE": 1, "NOT_SET": 2, "OK": 3}.get(status, 4)


def overlay_review_backlog_sort_key(row: dict[str, str]) -> tuple[int, int, int, str, str, str]:
    hard_or_override = row.get("overlay_has_hard_risk_flag") == "True" or row.get("overlay_manual_override_flag") == "True"
    return (
        overlay_review_status_sort_value(str(row.get("overlay_review_status", ""))),
        0 if hard_or_override else 1,
        overlay_review_priority_sort_value(str(row.get("overlay_priority", ""))),
        canonicalize_ticker(row.get("ticker", "")),
        str(row.get("isin", "") or "").strip().upper(),
        str(row.get("overlay_as_of_date", "") or "").strip(),
    )


def build_overlay_review_backlog(registry_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    backlog_rows = [
        {field: str(row.get(field, "") or "") for field in OVERLAY_REVIEW_BACKLOG_FIELDS}
        for row in registry_rows
        if row.get("needs_overlay_review_flag") == "True"
    ]
    return sorted(backlog_rows, key=overlay_review_backlog_sort_key)


def build_applied_master_rows(master_rows: list[dict[str, str]], registry_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    active_overlays = choose_active_overlays(registry_rows)
    applied_rows: list[dict[str, str]] = []
    for master_row in master_rows:
        row = {field: master_row.get(field, "") for field in PERSONAL_MASTER_FIELDS}
        row.update({"overlay_active_flag": "False", "overlay_applied_as_of_date": ""})
        key = master_identifier_key(master_row)
        overlay = active_overlays.get(key)
        if overlay:
            for field in OVERLAY_FIELDS:
                row[field] = overlay.get(field, "")
            row["overlay_active_flag"] = "True"
            row["overlay_applied_as_of_date"] = overlay.get("overlay_as_of_date", "")
        applied_rows.append(row)
    return sorted(applied_rows, key=applied_master_sort_key)


def build_summary_rows(master_rows: list[dict[str, str]], registry_rows: list[dict[str, str]], applied_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    hard_risk_count = sum(1 for row in registry_rows if row.get("overlay_has_hard_risk_flag") == "True")
    manual_override_count = sum(1 for row in registry_rows if row.get("overlay_manual_override_flag") == "True")
    active_holdings = sum(1 for row in applied_rows if row.get("overlay_active_flag") == "True")
    review_status_counts = Counter(row.get("overlay_review_status", "NOT_SET") for row in registry_rows)
    needs_review_count = sum(1 for row in registry_rows if row.get("needs_overlay_review_flag") == "True")
    hard_risk_or_manual_needs_review_count = sum(
        1
        for row in registry_rows
        if row.get("needs_overlay_review_flag") == "True"
        and (row.get("overlay_has_hard_risk_flag") == "True" or row.get("overlay_manual_override_flag") == "True")
    )
    rows = [
        ("holdings_checked", len(master_rows), "Personal-Master rows evaluated for overlay projection."),
        ("overlay_registry_rows", len(registry_rows), "Validated explicit overlay rows after deterministic dedupe."),
        ("holdings_with_active_overlay", active_holdings, "Holdings with an active latest-date overlay applied in the projection."),
        ("hard_risk_overlay_count", hard_risk_count, "Validated overlay rows with overlay_has_hard_risk_flag=True."),
        ("manual_override_count", manual_override_count, "Validated overlay rows with overlay_manual_override_flag=True."),
        ("overlay_review_due_count", review_status_counts.get("DUE", 0), "Overlay rows with review due within the conservative due window."),
        ("overlay_review_overdue_count", review_status_counts.get("OVERDUE", 0), "Overlay rows with review due date before the run date."),
        ("overlay_review_not_set_count", review_status_counts.get("NOT_SET", 0), "Overlay rows without overlay_review_due_date."),
        ("overlay_review_needed_count", needs_review_count, "Overlay rows with DUE or OVERDUE review status."),
        ("hard_risk_or_manual_override_review_needed_count", hard_risk_or_manual_needs_review_count, "DUE/OVERDUE overlay rows with hard-risk or manual-override flags."),
        ("rejected_overlay_rows", 0, "Successful runs reject invalid overlays fail-fast before outputs are written."),
    ]
    return [{"metric_name": name, "metric_value": str(value), "notes": notes} for name, value, notes in rows]


def write_overlay_report(
    output_path: str,
    master_rows: list[dict[str, str]],
    registry_rows: list[dict[str, str]],
    applied_rows: list[dict[str, str]],
    fundamentals_master_path: str,
    overlay_input_path: str,
    review_backlog_rows: list[dict[str, str]] | None = None,
) -> Path:
    summary_rows = build_summary_rows(master_rows, registry_rows, applied_rows)
    summary = {row["metric_name"]: row["metric_value"] for row in summary_rows}
    active_rows = [row for row in applied_rows if row.get("overlay_active_flag") == "True"]
    review_backlog_rows = review_backlog_rows if review_backlog_rows is not None else build_overlay_review_backlog(registry_rows)
    lines = [
        "# Personal Fundamentals Overlay",
        "",
        "## Input",
        "",
        f"- Fundamentals master: `{fundamentals_master_path}`",
        f"- Overlay input: `{overlay_input_path}`",
        "- Der originale Personal-Master wurde nicht veraendert.",
        "- Es wurden keine Core-KPIs veraendert und keine Score-Logik angepasst.",
        "",
        "## Summary",
        "",
        f"- Holdings geprueft: {summary.get('holdings_checked', '0')}",
        f"- Registry-Overlay-Zeilen: {summary.get('overlay_registry_rows', '0')}",
        f"- Holdings mit aktiven Overlays: {summary.get('holdings_with_active_overlay', '0')}",
        f"- Hard-Risk-Overlays: {summary.get('hard_risk_overlay_count', '0')}",
        f"- Manual-Override-Faelle: {summary.get('manual_override_count', '0')}",
        f"- Faellige Overlay-Reviews: {summary.get('overlay_review_due_count', '0')}",
        f"- Ueberfaellige Overlay-Reviews: {summary.get('overlay_review_overdue_count', '0')}",
        f"- Overlay-Reviews ohne Due-Date: {summary.get('overlay_review_not_set_count', '0')}",
        f"- Abgewiesene Overlay-Zeilen: {summary.get('rejected_overlay_rows', '0')}",
        "- Faellige oder ueberfaellige Overlays werden markiert, aber nicht automatisch deaktiviert.",
        "",
        "## Aktive Overlays",
        "",
    ]
    if active_rows:
        for row in active_rows:
            ticker = row.get("ticker") or row.get("isin") or row.get("company_name")
            lines.append(
                f"- `{ticker}` {row.get('company_name', '')}: "
                f"thesis={row.get('overlay_thesis_robustness') or 'none'} "
                f"hard_risk={row.get('overlay_has_hard_risk_flag')} "
                f"manual_override={row.get('overlay_manual_override_flag')} "
                f"as_of={row.get('overlay_applied_as_of_date') or 'none'}"
            )
    else:
        lines.append("- Keine aktiven Analyst-Overlays.")

    lines.extend(["", "## Faellige Overlay-Reviews", ""])
    if review_backlog_rows:
        for row in review_backlog_rows:
            ticker = row.get("ticker") or row.get("isin") or row.get("company_name")
            lines.append(
                f"- `{ticker}` status={row.get('overlay_review_status')} due={row.get('overlay_review_due_date') or 'none'} "
                f"hard_risk={row.get('overlay_has_hard_risk_flag')} manual_override={row.get('overlay_manual_override_flag')} "
                f"priority={row.get('overlay_priority') or 'none'}"
            )
    else:
        lines.append("- Keine faelligen oder ueberfaelligen Overlay-Reviews.")

    path = ensure_parent_dir(output_path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_overlay_template(output_path: str) -> Path:
    return write_csv_rows(output_path, OVERLAY_INPUT_FIELDS, [])


def load_validated_inputs(
    fundamentals_master_path: str,
    overlay_input_path: str,
    schema_path: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], set[str]]:
    master_rows = read_csv_rows(fundamentals_master_path)
    validate_personal_fundamentals_master(master_rows, f"personal fundamentals master ({fundamentals_master_path})")
    fieldnames, overlay_rows = read_csv_rows_with_header(overlay_input_path)
    require_header_columns(fieldnames, OVERLAY_REQUIRED_FIELDS, f"personal fundamentals overlay ({overlay_input_path})")
    allowed_thesis_values = load_allowed_overlay_thesis_values(schema_path)
    return master_rows, overlay_rows, allowed_thesis_values


def run_fundamentals_overlay_engine(
    fundamentals_master_path: str,
    overlay_input_path: str,
    schema_path: str = DEFAULT_SCHEMA_PATH,
    registry_output: str = DEFAULT_OVERLAY_REGISTRY_OUTPUT,
    applied_master_output: str = DEFAULT_APPLIED_MASTER_OUTPUT,
    summary_output: str | None = DEFAULT_OVERLAY_SUMMARY_OUTPUT,
    review_backlog_output: str | None = DEFAULT_OVERLAY_REVIEW_BACKLOG_OUTPUT,
    report_output: str | None = None,
    template_output: str | None = DEFAULT_OVERLAY_TEMPLATE_PATH,
    run_date: date | None = None,
) -> dict[str, Path]:
    master_rows, overlay_rows, allowed_thesis_values = load_validated_inputs(fundamentals_master_path, overlay_input_path, schema_path)
    registry_rows = build_overlay_registry(
        overlay_rows,
        master_rows,
        allowed_thesis_values,
        source_name=f"personal fundamentals overlay ({overlay_input_path})",
        run_date=run_date,
    )
    applied_rows = build_applied_master_rows(master_rows, registry_rows)
    review_backlog_rows = build_overlay_review_backlog(registry_rows)
    validate_personal_fundamentals_master(applied_rows, f"personal fundamentals applied master ({applied_master_output})")

    outputs: dict[str, Path] = {}
    outputs["overlay_registry"] = write_csv_rows(registry_output, OVERLAY_REGISTRY_FIELDS, registry_rows)
    outputs["applied_master"] = write_csv_rows(applied_master_output, APPLIED_MASTER_FIELDS, applied_rows)
    if summary_output:
        outputs["overlay_summary"] = write_csv_rows(summary_output, OVERLAY_SUMMARY_FIELDS, build_summary_rows(master_rows, registry_rows, applied_rows))
    if review_backlog_output:
        outputs["overlay_review_backlog"] = write_csv_rows(review_backlog_output, OVERLAY_REVIEW_BACKLOG_FIELDS, review_backlog_rows)
    if report_output:
        outputs["overlay_report"] = write_overlay_report(report_output, master_rows, registry_rows, applied_rows, fundamentals_master_path, overlay_input_path, review_backlog_rows)
    if template_output:
        outputs["overlay_template"] = write_overlay_template(template_output)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Personal-Fundamentals analyst overlay registry and applied master projection.")
    parser.add_argument("--fundamentals-master", default=DEFAULT_PERSONAL_MASTER_PATH, help="Personal fundamentals master CSV.")
    parser.add_argument("--overlay-input", default=DEFAULT_OVERLAY_INPUT_PATH, help="Manual personal fundamentals overlay CSV.")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA_PATH, help="Fundamentals schema config.")
    parser.add_argument("--registry-output", default=DEFAULT_OVERLAY_REGISTRY_OUTPUT, help="Normalized overlay registry output.")
    parser.add_argument("--applied-master-output", default=DEFAULT_APPLIED_MASTER_OUTPUT, help="Applied personal fundamentals master output.")
    parser.add_argument("--summary-output", default=DEFAULT_OVERLAY_SUMMARY_OUTPUT, help="Overlay summary output.")
    parser.add_argument("--review-backlog-output", default=DEFAULT_OVERLAY_REVIEW_BACKLOG_OUTPUT, help="Overlay review backlog output.")
    parser.add_argument("--report-output", default=default_overlay_report_path(), help="Overlay markdown report output.")
    parser.add_argument("--template-output", default=DEFAULT_OVERLAY_TEMPLATE_PATH, help="Overlay input template output.")
    parser.add_argument("--template-only", action="store_true", help="Only write the overlay template; do not require master or overlay input.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.template_only:
        write_overlay_template(args.template_output)
        return
    run_fundamentals_overlay_engine(
        fundamentals_master_path=args.fundamentals_master,
        overlay_input_path=args.overlay_input,
        schema_path=args.schema,
        registry_output=args.registry_output,
        applied_master_output=args.applied_master_output,
        summary_output=args.summary_output,
        review_backlog_output=args.review_backlog_output,
        report_output=args.report_output,
        template_output=args.template_output,
    )


if __name__ == "__main__":
    main()
