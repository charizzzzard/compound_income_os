from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from src.common import canonicalize_ticker, ensure_parent_dir, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows
from src.fundamentals_master import (
    CORE_KPI_FIELDS,
    DEFAULT_METRIC_DEFINITIONS_PATH,
    VALID_DATA_QUALITY_FLAGS,
    compute_kpi_coverage,
    kpi_applicability,
    load_metric_definitions,
    validate_personal_fundamentals_master,
)

DEFAULT_PERSONAL_MASTER_PATH = "data/raw/personal_fundamentals_master.csv"
DEFAULT_EVIDENCE_INPUT_PATH = "data/raw/personal_fundamentals_evidence.csv"
DEFAULT_EVIDENCE_TEMPLATE_PATH = "data/raw/personal_fundamentals_evidence_template.csv"
DEFAULT_REGISTRY_OUTPUT = "data/processed/personal_fundamentals_evidence_registry.csv"
DEFAULT_BACKLOG_OUTPUT = "data/processed/personal_fundamentals_research_backlog.csv"
DEFAULT_PROPOSED_UPDATES_OUTPUT = "data/processed/personal_fundamentals_proposed_updates.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_fundamentals_evidence_summary.csv"

VALID_VERIFICATION_STATUSES = {"VERIFIED", "REVIEW", "UNVERIFIED"}
STRONG_VERIFICATION_STATUS = "VERIFIED"

EVIDENCE_REQUIRED_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "kpi_name",
    "source_type",
    "source_name",
    "source_reference",
    "source_as_of_date",
    "fiscal_year",
    "verification_status",
    "data_quality_flag",
    "notes",
]

EVIDENCE_OPTIONAL_FIELDS = [
    "source_section",
    "source_page",
    "reported_value",
    "reported_unit",
    "currency",
]

EVIDENCE_INPUT_FIELDS = [*EVIDENCE_REQUIRED_FIELDS, *EVIDENCE_OPTIONAL_FIELDS]

EVIDENCE_IDENTITY_FIELDS = [
    "ticker",
    "isin",
    "kpi_name",
    "source_type",
    "source_name",
    "source_reference",
    "source_as_of_date",
    "fiscal_year",
]

EVIDENCE_REGISTRY_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "kpi_name",
    "applicability",
    "source_type",
    "source_name",
    "source_reference",
    "source_section",
    "source_page",
    "source_as_of_date",
    "fiscal_year",
    "verification_status",
    "data_quality_flag",
    "evidence_present",
    "reported_value",
    "reported_unit",
    "currency",
    "evidence_identity",
    "notes",
]

RESEARCH_BACKLOG_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "required_kpis_expected",
    "required_kpis_with_evidence",
    "missing_required_evidence_kpis",
    "weak_verification_kpis",
    "optional_missing_evidence_kpis",
    "needs_research_flag",
    "research_priority",
    "notes",
]

PROPOSED_UPDATES_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "kpi_name",
    "reported_value",
    "reported_unit",
    "currency",
    "source_type",
    "source_name",
    "source_reference",
    "source_as_of_date",
    "fiscal_year",
    "verification_status",
    "data_quality_flag",
    "proposal_reason",
    "notes",
]

EVIDENCE_SUMMARY_FIELDS = ["metric_name", "metric_value", "notes"]


def default_evidence_report_path() -> str:
    return f"reports/{date.today().isoformat()}/personal_fundamentals_evidence_report.md"


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


def parse_iso_date_text(value: Any, field: str, source_name: str, row_number: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{source_name} row {row_number} has blank required field(s): {field}")
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{source_name} row {row_number} has invalid {field}: {text!r}; expected YYYY-MM-DD") from exc
    return text


def validate_optional_fiscal_year(value: Any, source_name: str, row_number: int) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        int(text)
    except ValueError as exc:
        raise ValueError(f"{source_name} row {row_number} has invalid fiscal_year: {text!r}") from exc
    return text


def require_nonblank_value(row: dict[str, str], field: str, source_name: str, row_number: int) -> str:
    text = str(row.get(field, "") or "").strip()
    if not text:
        raise ValueError(f"{source_name} row {row_number} has blank required field(s): {field}")
    return text


def evidence_identity(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "") or "").strip() for field in EVIDENCE_IDENTITY_FIELDS)


def evidence_identity_text(identity: tuple[str, ...]) -> str:
    return ", ".join(f"{field}={value or '<blank>'}" for field, value in zip(EVIDENCE_IDENTITY_FIELDS, identity, strict=True))


def registry_content_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "") or "").strip() for field in EVIDENCE_REGISTRY_FIELDS)


def registry_sort_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        canonicalize_ticker(row.get("ticker", "")),
        str(row.get("isin", "") or "").strip().upper(),
        str(row.get("kpi_name", "") or "").strip(),
        str(row.get("source_as_of_date", "") or "").strip(),
        str(row.get("source_name", "") or "").strip(),
        str(row.get("source_reference", "") or "").strip(),
    )


def backlog_priority_sort_value(priority: str) -> int:
    return {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "NONE": 3}.get(priority, 4)


def backlog_sort_key(row: dict[str, str]) -> tuple[int, str, str]:
    return (
        backlog_priority_sort_value(str(row.get("research_priority", ""))),
        canonicalize_ticker(row.get("ticker", "")),
        str(row.get("isin", "") or "").strip().upper(),
    )


def proposed_update_sort_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        canonicalize_ticker(row.get("ticker", "")),
        str(row.get("isin", "") or "").strip().upper(),
        str(row.get("kpi_name", "") or "").strip(),
        str(row.get("source_as_of_date", "") or "").strip(),
        str(row.get("source_name", "") or "").strip(),
        str(row.get("source_reference", "") or "").strip(),
    )


def canonical_list(values: list[str]) -> str:
    return "; ".join(sorted({value for value in values if value}))


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
            raise ValueError(f"personal fundamentals master has duplicate {field} value(s); evidence matching would be ambiguous: {', '.join(duplicates)}")


def build_master_identifier_index(master_rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    validate_master_identifier_uniqueness(master_rows)
    index: dict[str, dict[str, dict[str, str]]] = {"ticker": {}, "isin": {}}
    for row in master_rows:
        ticker = canonicalize_ticker(row.get("ticker", ""))
        isin = str(row.get("isin", "") or "").strip().upper()
        if ticker:
            index["ticker"][ticker] = row
        if isin:
            index["isin"][isin] = row
    return index


def match_evidence_to_master(
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


def allowed_kpi_names(metric_definitions: dict[str, Any]) -> set[str]:
    return {kpi for kpi in CORE_KPI_FIELDS if kpi in metric_definitions}


def canonical_evidence_registry_row(
    row: dict[str, str],
    master_row: dict[str, str],
    metric_definitions: dict[str, Any],
    source_name: str,
    row_number: int,
) -> dict[str, str]:
    kpi_name = require_nonblank_value(row, "kpi_name", source_name, row_number)
    if kpi_name not in allowed_kpi_names(metric_definitions):
        raise ValueError(f"{source_name} row {row_number} has unknown kpi_name: {kpi_name!r}")

    verification_status = safe_upper(require_nonblank_value(row, "verification_status", source_name, row_number))
    if verification_status not in VALID_VERIFICATION_STATUSES:
        raise ValueError(
            f"{source_name} row {row_number} has invalid verification_status: {row.get('verification_status')!r}; "
            f"allowed: {', '.join(sorted(VALID_VERIFICATION_STATUSES))}"
        )
    data_quality_flag = safe_upper(require_nonblank_value(row, "data_quality_flag", source_name, row_number))
    if data_quality_flag not in VALID_DATA_QUALITY_FLAGS:
        raise ValueError(
            f"{source_name} row {row_number} has invalid data_quality_flag: {row.get('data_quality_flag')!r}; "
            f"allowed: {', '.join(sorted(VALID_DATA_QUALITY_FLAGS))}"
        )

    profile = safe_upper(master_row.get("company_type_profile")) or "OTHER"
    source_as_of_date = parse_iso_date_text(row.get("source_as_of_date", ""), "source_as_of_date", source_name, row_number)
    fiscal_year = validate_optional_fiscal_year(row.get("fiscal_year", ""), source_name, row_number)
    source_type = safe_upper(require_nonblank_value(row, "source_type", source_name, row_number))
    source_name_value = require_nonblank_value(row, "source_name", source_name, row_number)
    source_reference = require_nonblank_value(row, "source_reference", source_name, row_number)
    ticker, isin = master_identifier_key(master_row)

    registry_row = {
        "ticker": ticker,
        "isin": isin,
        "company_name": str(master_row.get("company_name", "") or "").strip(),
        "company_type_profile": profile,
        "kpi_name": kpi_name,
        "applicability": kpi_applicability(metric_definitions[kpi_name], profile),
        "source_type": source_type,
        "source_name": source_name_value,
        "source_reference": source_reference,
        "source_section": str(row.get("source_section", "") or "").strip(),
        "source_page": str(row.get("source_page", "") or "").strip(),
        "source_as_of_date": source_as_of_date,
        "fiscal_year": fiscal_year,
        "verification_status": verification_status,
        "data_quality_flag": data_quality_flag,
        "evidence_present": "True",
        "reported_value": str(row.get("reported_value", "") or "").strip(),
        "reported_unit": str(row.get("reported_unit", "") or "").strip(),
        "currency": str(row.get("currency", "") or "").strip().upper(),
        "evidence_identity": "",
        "notes": str(row.get("notes", "") or "").strip(),
    }
    registry_row["evidence_identity"] = evidence_identity_text(evidence_identity(registry_row))
    return registry_row


def build_evidence_registry(
    evidence_rows: list[dict[str, str]],
    master_rows: list[dict[str, str]],
    metric_definitions: dict[str, Any],
    source_name: str = "personal fundamentals evidence",
) -> list[dict[str, str]]:
    master_index = build_master_identifier_index(master_rows)
    indexed: dict[tuple[str, ...], dict[str, str]] = {}
    for row_number, row in enumerate(evidence_rows, start=2):
        master_row = match_evidence_to_master(row, master_index, source_name, row_number)
        registry_row = canonical_evidence_registry_row(row, master_row, metric_definitions, source_name, row_number)
        identity = evidence_identity(registry_row)
        existing = indexed.get(identity)
        if existing is None:
            indexed[identity] = registry_row
            continue
        if registry_content_key(existing) != registry_content_key(registry_row):
            raise ValueError(f"personal fundamentals evidence conflict for identity {evidence_identity_text(identity)}")
    return sorted(indexed.values(), key=registry_sort_key)


def required_kpis_for_profile(profile: str, metric_definitions: dict[str, Any]) -> list[str]:
    return [
        kpi
        for kpi in CORE_KPI_FIELDS
        if kpi_applicability(metric_definitions[kpi], profile) == "REQUIRED"
    ]


def optional_kpis_for_profile(profile: str, metric_definitions: dict[str, Any]) -> list[str]:
    return [
        kpi
        for kpi in CORE_KPI_FIELDS
        if kpi_applicability(metric_definitions[kpi], profile) == "OPTIONAL"
    ]


def has_strong_evidence(rows: list[dict[str, str]]) -> bool:
    return any(
        safe_upper(row.get("verification_status")) == STRONG_VERIFICATION_STATUS
        and safe_upper(row.get("data_quality_flag")) == "OK"
        for row in rows
    )


def build_research_backlog(
    master_rows: list[dict[str, str]],
    registry_rows: list[dict[str, str]],
    metric_definitions: dict[str, Any],
) -> list[dict[str, str]]:
    evidence_by_holding_kpi: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in registry_rows:
        ticker = canonicalize_ticker(row.get("ticker", ""))
        isin = str(row.get("isin", "") or "").strip().upper()
        kpi_name = str(row.get("kpi_name", "") or "").strip()
        evidence_by_holding_kpi.setdefault((ticker, isin, kpi_name), []).append(row)

    backlog_rows: list[dict[str, str]] = []
    for master_row in master_rows:
        if safe_upper(master_row.get("asset_type")) == "CASH":
            continue
        ticker, isin = master_identifier_key(master_row)
        profile = safe_upper(master_row.get("company_type_profile")) or "OTHER"
        kpi_coverage = compute_kpi_coverage(master_row, profile, metric_definitions)
        required_kpis = list(kpi_coverage["required"])
        optional_kpis = optional_kpis_for_profile(profile, metric_definitions)

        required_with_evidence: list[str] = []
        missing_required: list[str] = []
        weak_required: list[str] = []
        optional_missing: list[str] = []

        for kpi_name in required_kpis:
            rows = evidence_by_holding_kpi.get((ticker, isin, kpi_name), [])
            if not rows:
                missing_required.append(kpi_name)
                continue
            required_with_evidence.append(kpi_name)
            if not has_strong_evidence(rows):
                weak_required.append(kpi_name)

        for kpi_name in optional_kpis:
            if not evidence_by_holding_kpi.get((ticker, isin, kpi_name), []):
                optional_missing.append(kpi_name)

        if missing_required:
            priority = "HIGH"
            notes = "Missing required KPI evidence."
        elif weak_required:
            priority = "MEDIUM"
            notes = "Required KPI evidence exists but verification or data quality is weak."
        elif optional_missing:
            priority = "LOW"
            notes = "Required KPI evidence is complete; optional KPI evidence remains open."
        else:
            priority = "NONE"
            notes = "Required and optional KPI evidence complete for applicable profile."

        backlog_rows.append(
            {
                "ticker": ticker,
                "isin": isin,
                "company_name": str(master_row.get("company_name", "") or "").strip(),
                "company_type_profile": profile,
                "required_kpis_expected": str(len(required_kpis)),
                "required_kpis_with_evidence": str(len(required_with_evidence)),
                "missing_required_evidence_kpis": canonical_list(missing_required),
                "weak_verification_kpis": canonical_list(weak_required),
                "optional_missing_evidence_kpis": canonical_list(optional_missing),
                "needs_research_flag": str(priority != "NONE"),
                "research_priority": priority,
                "notes": notes,
            }
        )
    return sorted(backlog_rows, key=backlog_sort_key)


def build_proposed_update_rows(registry_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in registry_rows:
        reported_value = str(row.get("reported_value", "") or "").strip()
        if not reported_value:
            continue
        rows.append(
            {
                "ticker": row.get("ticker", ""),
                "isin": row.get("isin", ""),
                "company_name": row.get("company_name", ""),
                "company_type_profile": row.get("company_type_profile", ""),
                "kpi_name": row.get("kpi_name", ""),
                "reported_value": reported_value,
                "reported_unit": row.get("reported_unit", ""),
                "currency": row.get("currency", ""),
                "source_type": row.get("source_type", ""),
                "source_name": row.get("source_name", ""),
                "source_reference": row.get("source_reference", ""),
                "source_as_of_date": row.get("source_as_of_date", ""),
                "fiscal_year": row.get("fiscal_year", ""),
                "verification_status": row.get("verification_status", ""),
                "data_quality_flag": row.get("data_quality_flag", ""),
                "proposal_reason": "Validated explicit evidence has reported_value; manual Personal-Master review required.",
                "notes": row.get("notes", ""),
            }
        )
    return sorted(rows, key=proposed_update_sort_key)


def build_summary_rows(registry_rows: list[dict[str, str]], backlog_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    priority_counts = Counter(row.get("research_priority", "NONE") for row in backlog_rows)
    required_gap_count = sum(1 for row in backlog_rows if str(row.get("missing_required_evidence_kpis", "")).strip())
    weak_count = sum(1 for row in backlog_rows if str(row.get("weak_verification_kpis", "")).strip())
    required_complete = sum(
        1
        for row in backlog_rows
        if not str(row.get("missing_required_evidence_kpis", "")).strip()
        and not str(row.get("weak_verification_kpis", "")).strip()
    )
    rows = [
        ("holdings_checked", len(backlog_rows), "Non-cash Personal-Master holdings evaluated."),
        ("evidence_registry_rows", len(registry_rows), "Normalized explicit evidence rows."),
        ("holdings_with_required_evidence_complete", required_complete, "Required KPI evidence present and strongly verified."),
        ("holdings_with_required_evidence_gaps", required_gap_count, "At least one required KPI has no evidence row."),
        ("holdings_with_weak_required_evidence", weak_count, "At least one required KPI has weak verification or data quality."),
    ]
    for priority in ["HIGH", "MEDIUM", "LOW", "NONE"]:
        rows.append((f"research_priority_{priority.lower()}_count", priority_counts.get(priority, 0), f"Backlog rows with priority {priority}."))
    return [{"metric_name": name, "metric_value": str(value), "notes": notes} for name, value, notes in rows]


def missing_required_kpi_frequency(backlog_rows: list[dict[str, str]]) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for row in backlog_rows:
        for kpi_name in str(row.get("missing_required_evidence_kpis", "")).split(";"):
            cleaned = kpi_name.strip()
            if cleaned:
                counter[cleaned] += 1
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def write_evidence_report(
    output_path: str,
    registry_rows: list[dict[str, str]],
    backlog_rows: list[dict[str, str]],
    fundamentals_master_path: str,
    evidence_input_path: str,
) -> Path:
    summary_rows = build_summary_rows(registry_rows, backlog_rows)
    summary = {row["metric_name"]: row["metric_value"] for row in summary_rows}
    open_backlog = [row for row in backlog_rows if row.get("needs_research_flag") == "True"]
    lines = [
        "# Personal Fundamentals Evidence",
        "",
        "## Input",
        "",
        f"- Fundamentals master: `{fundamentals_master_path}`",
        f"- Evidence input: `{evidence_input_path}`",
        "- Es wurden keine Evidence-Werte in den Personal-Master zurueckgeschrieben.",
        "- Es wurden keine KPI-Werte erfunden und keine externen Quellen abgefragt.",
        "",
        "## Summary",
        "",
        f"- Holdings geprueft: {summary.get('holdings_checked', '0')}",
        f"- Registry-Evidence-Zeilen: {summary.get('evidence_registry_rows', '0')}",
        f"- Vollstaendige Required-Evidence: {summary.get('holdings_with_required_evidence_complete', '0')}",
        f"- Required-Evidence-Gaps: {summary.get('holdings_with_required_evidence_gaps', '0')}",
        f"- Schwache Required-Evidence: {summary.get('holdings_with_weak_required_evidence', '0')}",
        "",
        "## Research Backlog",
        "",
    ]
    if open_backlog:
        for row in open_backlog[:25]:
            ticker = row.get("ticker") or row.get("isin") or row.get("company_name")
            lines.append(
                f"- `{ticker}` priority={row.get('research_priority')} "
                f"missing_required={row.get('missing_required_evidence_kpis') or 'none'} "
                f"weak={row.get('weak_verification_kpis') or 'none'}"
            )
    else:
        lines.append("- Keine offenen Fundamentals-Evidence-Luecken.")

    lines.extend(["", "## Haeufigste Fehlende Required-KPIs", ""])
    frequencies = missing_required_kpi_frequency(backlog_rows)
    if frequencies:
        for kpi_name, count in frequencies:
            lines.append(f"- `{kpi_name}`: {count}")
    else:
        lines.append("- Keine fehlenden Required-KPI-Evidence-Luecken.")

    path = ensure_parent_dir(output_path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_evidence_template(output_path: str) -> Path:
    return write_csv_rows(output_path, EVIDENCE_INPUT_FIELDS, [])


def load_validated_inputs(
    fundamentals_master_path: str,
    evidence_input_path: str,
    metric_definitions_path: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    master_rows = read_csv_rows(fundamentals_master_path)
    validate_personal_fundamentals_master(master_rows, f"personal fundamentals master ({fundamentals_master_path})")
    definitions = load_metric_definitions(metric_definitions_path)
    fieldnames, evidence_rows = read_csv_rows_with_header(evidence_input_path)
    require_header_columns(fieldnames, EVIDENCE_REQUIRED_FIELDS, f"personal fundamentals evidence ({evidence_input_path})")
    return master_rows, evidence_rows, definitions


def run_fundamentals_evidence_engine(
    fundamentals_master_path: str,
    evidence_input_path: str,
    metric_definitions_path: str = DEFAULT_METRIC_DEFINITIONS_PATH,
    registry_output: str = DEFAULT_REGISTRY_OUTPUT,
    backlog_output: str = DEFAULT_BACKLOG_OUTPUT,
    proposed_updates_output: str | None = DEFAULT_PROPOSED_UPDATES_OUTPUT,
    summary_output: str | None = DEFAULT_SUMMARY_OUTPUT,
    report_output: str | None = None,
    template_output: str | None = DEFAULT_EVIDENCE_TEMPLATE_PATH,
) -> dict[str, Path]:
    master_rows, evidence_rows, definitions = load_validated_inputs(fundamentals_master_path, evidence_input_path, metric_definitions_path)
    registry_rows = build_evidence_registry(
        evidence_rows,
        master_rows,
        definitions,
        source_name=f"personal fundamentals evidence ({evidence_input_path})",
    )
    backlog_rows = build_research_backlog(master_rows, registry_rows, definitions)
    proposed_update_rows = build_proposed_update_rows(registry_rows)

    outputs: dict[str, Path] = {}
    outputs["evidence_registry"] = write_csv_rows(registry_output, EVIDENCE_REGISTRY_FIELDS, registry_rows)
    outputs["research_backlog"] = write_csv_rows(backlog_output, RESEARCH_BACKLOG_FIELDS, backlog_rows)
    if proposed_updates_output:
        outputs["proposed_updates"] = write_csv_rows(proposed_updates_output, PROPOSED_UPDATES_FIELDS, proposed_update_rows)
    if summary_output:
        outputs["evidence_summary"] = write_csv_rows(summary_output, EVIDENCE_SUMMARY_FIELDS, build_summary_rows(registry_rows, backlog_rows))
    if report_output:
        outputs["evidence_report"] = write_evidence_report(report_output, registry_rows, backlog_rows, fundamentals_master_path, evidence_input_path)
    if template_output:
        outputs["evidence_template"] = write_evidence_template(template_output)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Personal-Fundamentals evidence registry and research backlog.")
    parser.add_argument("--fundamentals-master", default=DEFAULT_PERSONAL_MASTER_PATH, help="Personal fundamentals master CSV.")
    parser.add_argument("--evidence-input", default=DEFAULT_EVIDENCE_INPUT_PATH, help="Manual personal fundamentals evidence CSV.")
    parser.add_argument("--metric-definitions", default=DEFAULT_METRIC_DEFINITIONS_PATH, help="Fundamentals metric definitions config.")
    parser.add_argument("--registry-output", default=DEFAULT_REGISTRY_OUTPUT, help="Normalized evidence registry output.")
    parser.add_argument("--backlog-output", default=DEFAULT_BACKLOG_OUTPUT, help="Research backlog output.")
    parser.add_argument("--proposed-updates-output", default=DEFAULT_PROPOSED_UPDATES_OUTPUT, help="Manual Personal-Master proposed updates output.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT, help="Evidence summary output.")
    parser.add_argument("--report-output", default=default_evidence_report_path(), help="Evidence markdown report output.")
    parser.add_argument("--template-output", default=DEFAULT_EVIDENCE_TEMPLATE_PATH, help="Evidence input template output.")
    parser.add_argument("--template-only", action="store_true", help="Only write the evidence template; do not require master or evidence input.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.template_only:
        write_evidence_template(args.template_output)
        return
    run_fundamentals_evidence_engine(
        fundamentals_master_path=args.fundamentals_master,
        evidence_input_path=args.evidence_input,
        metric_definitions_path=args.metric_definitions,
        registry_output=args.registry_output,
        backlog_output=args.backlog_output,
        proposed_updates_output=args.proposed_updates_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
        template_output=args.template_output,
    )


if __name__ == "__main__":
    main()
