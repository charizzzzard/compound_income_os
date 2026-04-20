from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.common import canonicalize_ticker, read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows
from src.fundamentals_master import DEFAULT_PERSONAL_MASTER_PATH, validate_personal_fundamentals_master
from src.fundamentals_snapshot_ingestion import DEFAULT_SNAPSHOT_INPUT_PATH, SNAPSHOT_INPUT_FIELDS

DEFAULT_SEC_IDENTITY_MAP_INPUT = "data/raw/private/fundamentals/personal_sec_identity_map.csv"
DEFAULT_SEC_IDENTITY_MAP_TEMPLATE = "data/raw/personal_sec_identity_map_template.csv"
DEFAULT_SEC_FETCH_REGISTRY_OUTPUT = "data/processed/external_sec_fetch_registry.csv"
DEFAULT_SEC_FETCH_FAILURES_OUTPUT = "data/processed/external_sec_fetch_failures.csv"
DEFAULT_SEC_FETCH_SUMMARY_OUTPUT = "data/processed/external_sec_fetch_summary.csv"

SEC_SOURCE_NAME = "sec_companyfacts"
SEC_COMPANYFACTS_URL_TEMPLATE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

IDENTITY_MAP_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "cik",
    "sec_entity_name",
    "asset_type",
    "country",
    "enabled",
    "notes",
]

REGISTRY_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "cik",
    "fetch_status",
    "source_name",
    "source_reference",
    "source_as_of_date",
    "notes",
]

FAILURES_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "cik",
    "failure_reason",
    "source_name",
    "notes",
]

SUMMARY_FIELDS = [
    "master_rows_total",
    "identity_rows_total",
    "sec_candidates_total",
    "fetched_rows_total",
    "snapshot_rows_written",
    "failure_rows_total",
    "unsupported_rows_total",
    "notes",
]

FETCHED = "FETCHED"
SKIPPED_UNSUPPORTED = "SKIPPED_UNSUPPORTED"
SKIPPED_IDENTITY_MISSING = "SKIPPED_IDENTITY_MISSING"
FAILED_HTTP = "FAILED_HTTP"
FAILED_PARSE = "FAILED_PARSE"
FAILED_AMBIGUOUS = "FAILED_AMBIGUOUS"
FAILED_CONTRACT = "FAILED_CONTRACT"

SUPPORTED_COUNTRIES = {"US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"}
SUPPORTED_ASSET_TYPES = {"STOCK"}

CONCEPT_REVENUE = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
]
CONCEPT_EPS_DILUTED = ["EarningsPerShareDiluted"]
CONCEPT_GROSS_PROFIT = ["GrossProfit"]
CONCEPT_OPERATING_INCOME = ["OperatingIncomeLoss"]
CONCEPT_INTEREST_EXPENSE = ["InterestExpenseNonOperating"]
CONCEPT_DILUTED_SHARES = ["WeightedAverageNumberOfDilutedSharesOutstanding"]


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


def canonical_isin(value: Any) -> str:
    return str(value or "").strip().upper()


def canonical_cik(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    digits = "".join(char for char in text if char.isdigit())
    if not digits:
        return ""
    return digits.zfill(10)


def parse_enabled(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def sort_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        canonicalize_ticker(row.get("ticker", "")),
        canonical_isin(row.get("isin", "")),
        str(row.get("company_name", "") or "").strip(),
    )


def registry_row(
    identity: dict[str, str],
    *,
    fetch_status: str,
    source_reference: str = "",
    source_as_of_date: str = "",
    notes: str = "",
) -> dict[str, str]:
    return {
        "ticker": canonicalize_ticker(identity.get("ticker", "")),
        "isin": canonical_isin(identity.get("isin", "")),
        "company_name": str(identity.get("company_name", "") or "").strip(),
        "cik": canonical_cik(identity.get("cik", "")),
        "fetch_status": fetch_status,
        "source_name": SEC_SOURCE_NAME,
        "source_reference": source_reference,
        "source_as_of_date": source_as_of_date,
        "notes": notes,
    }


def failure_row(identity: dict[str, str], reason: str, notes: str = "") -> dict[str, str]:
    return {
        "ticker": canonicalize_ticker(identity.get("ticker", "")),
        "isin": canonical_isin(identity.get("isin", "")),
        "company_name": str(identity.get("company_name", "") or "").strip(),
        "cik": canonical_cik(identity.get("cik", "")),
        "failure_reason": reason,
        "source_name": SEC_SOURCE_NAME,
        "notes": notes,
    }


def master_identifier_key(row: dict[str, str]) -> tuple[str, str]:
    return canonicalize_ticker(row.get("ticker", "")), canonical_isin(row.get("isin", ""))


def build_master_identifier_index(master_rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    index: dict[str, dict[str, dict[str, str]]] = {"ticker": {}, "isin": {}}
    for field, normalizer in [
        ("ticker", lambda row: canonicalize_ticker(row.get("ticker", ""))),
        ("isin", lambda row: canonical_isin(row.get("isin", ""))),
    ]:
        counts = Counter(normalizer(row) for row in master_rows if normalizer(row))
        duplicates = sorted(value for value, count in counts.items() if count > 1)
        if duplicates:
            raise ValueError(f"personal fundamentals master has duplicate {field} value(s): {', '.join(duplicates)}")
    for row in master_rows:
        ticker, isin = master_identifier_key(row)
        if ticker:
            index["ticker"][ticker] = row
        if isin:
            index["isin"][isin] = row
    return index


def match_identity_to_master(
    identity: dict[str, str],
    master_index: dict[str, dict[str, dict[str, str]]],
) -> tuple[dict[str, str] | None, str]:
    ticker = canonicalize_ticker(identity.get("ticker", ""))
    isin = canonical_isin(identity.get("isin", ""))
    if not ticker and not isin:
        return None, "identity map row requires ticker or isin for exact Personal-Master matching"
    ticker_match = master_index["ticker"].get(ticker) if ticker else None
    isin_match = master_index["isin"].get(isin) if isin else None
    if ticker and isin:
        # Allow the reviewed identity-map ticker to bridge a dirty master row whose
        # ticker field still mirrors the ISIN placeholder from the scope-review prep step.
        if ticker_match is None and isin_match is not None:
            master_ticker = canonicalize_ticker(isin_match.get("ticker", ""))
            if not master_ticker or master_ticker == isin:
                return isin_match, ""
        if ticker_match is None or isin_match is None:
            return None, f"ticker/isin did not both match the Personal-Master: ticker={ticker}, isin={isin}"
        if id(ticker_match) != id(isin_match):
            return None, f"ticker/isin matched different Personal-Master rows: ticker={ticker}, isin={isin}"
        return ticker_match, ""
    matched = isin_match or ticker_match
    if matched is None:
        return None, f"no exact ticker/isin match in Personal-Master: ticker={ticker or '<blank>'}, isin={isin or '<blank>'}"
    return matched, ""


def canonical_identity_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "ticker": canonicalize_ticker(row.get("ticker", "")),
        "isin": canonical_isin(row.get("isin", "")),
        "company_name": str(row.get("company_name", "") or "").strip(),
        "cik": canonical_cik(row.get("cik", "")),
        "sec_entity_name": str(row.get("sec_entity_name", "") or "").strip(),
        "asset_type": safe_upper(row.get("asset_type", "")),
        "country": safe_upper(row.get("country", "")),
        "enabled": str(parse_enabled(row.get("enabled", ""))),
        "notes": str(row.get("notes", "") or "").strip(),
    }


def validate_identity_map_rows(raw_rows: list[dict[str, str]], source_name: str) -> list[dict[str, str]]:
    rows = [canonical_identity_row(row) for row in raw_rows if any(str(value or "").strip() for value in row.values())]
    seen: dict[tuple[str, str, str], tuple[str, ...]] = {}
    deduped: list[dict[str, str]] = []
    for row in rows:
        identity = (row["ticker"], row["isin"], row["cik"])
        content = tuple(row.get(field, "") for field in IDENTITY_MAP_FIELDS)
        existing = seen.get(identity)
        if existing is None:
            seen[identity] = content
            deduped.append(row)
            continue
        if existing != content:
            raise ValueError(
                f"{source_name} has conflicting duplicate identity row: ticker={row['ticker'] or '<blank>'}, "
                f"isin={row['isin'] or '<blank>'}, cik={row['cik'] or '<blank>'}"
            )
    return sorted(deduped, key=sort_key)


def sec_companyfacts_url(cik: str) -> str:
    return SEC_COMPANYFACTS_URL_TEMPLATE.format(cik=canonical_cik(cik))


def fetch_companyfacts(cik: str, sec_user_agent: str) -> dict[str, Any]:
    request = Request(
        sec_companyfacts_url(cik),
        headers={
            "User-Agent": sec_user_agent,
            "Accept-Encoding": "identity",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8")
    loaded = json.loads(payload)
    if not isinstance(loaded, dict):
        raise ValueError("SEC CompanyFacts response was not a JSON object")
    return loaded


def fact_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def annual_series(companyfacts: dict[str, Any], concepts: list[str], preferred_units: list[str]) -> dict[int, dict[str, Any]]:
    facts = companyfacts.get("facts")
    if not isinstance(facts, dict):
        return {}
    us_gaap = facts.get("us-gaap")
    if not isinstance(us_gaap, dict):
        return {}
    for concept in concepts:
        concept_block = us_gaap.get(concept)
        if not isinstance(concept_block, dict):
            continue
        units = concept_block.get("units")
        if not isinstance(units, dict):
            continue
        for unit in preferred_units:
            raw_points = units.get(unit)
            if not isinstance(raw_points, list):
                continue
            by_year: dict[int, dict[str, Any]] = {}
            for point in raw_points:
                if not isinstance(point, dict):
                    continue
                if str(point.get("fp", "")).upper() != "FY":
                    continue
                if str(point.get("form", "")).upper() not in {"10-K", "10-K/A"}:
                    continue
                try:
                    fiscal_year = int(point.get("fy"))
                except (TypeError, ValueError):
                    continue
                value = fact_number(point.get("val"))
                if value is None:
                    continue
                candidate = {
                    "fy": fiscal_year,
                    "value": value,
                    "filed": str(point.get("filed", "") or ""),
                    "end": str(point.get("end", "") or ""),
                    "accn": str(point.get("accn", "") or ""),
                    "concept": concept,
                    "unit": unit,
                }
                existing = by_year.get(fiscal_year)
                if existing is None or (candidate["filed"], candidate["accn"]) >= (existing["filed"], existing["accn"]):
                    by_year[fiscal_year] = candidate
            if by_year:
                return by_year
    return {}


def pct(value: float) -> str:
    return format(value, ".6g")


def latest_value(series: dict[int, dict[str, Any]], year: int) -> float | None:
    point = series.get(year)
    return float(point["value"]) if point else None


def ratio_pct(numerator: float | None, denominator: float | None) -> str:
    if numerator is None or denominator is None or denominator == 0:
        return ""
    return pct((numerator / denominator) * 100.0)


def cagr_pct(series: dict[int, dict[str, Any]], latest_year: int, years: int = 5) -> str:
    start = latest_value(series, latest_year - years)
    end = latest_value(series, latest_year)
    if start is None or end is None or start <= 0 or end <= 0:
        return ""
    return pct(((end / start) ** (1.0 / years) - 1.0) * 100.0)


def detect_currency(*series_items: dict[int, dict[str, Any]]) -> str:
    for series in series_items:
        for point in series.values():
            unit = str(point.get("unit", "") or "").upper()
            if unit == "USD" or unit.startswith("USD/"):
                return "USD"
    return ""


def source_reference(cik: str, latest_year: int, *series_items: dict[int, dict[str, Any]]) -> str:
    accessions = sorted(
        {
            str(series[latest_year].get("accn", "") or "")
            for series in series_items
            if latest_year in series and str(series[latest_year].get("accn", "") or "")
        }
    )
    suffix = f"; accession(s)={';'.join(accessions)}" if accessions else ""
    return f"SEC CompanyFacts CIK{canonical_cik(cik)} FY{latest_year}{suffix}"


def build_snapshot_row_from_companyfacts(
    *,
    master_row: dict[str, str],
    identity: dict[str, str],
    companyfacts: dict[str, Any],
    as_of_date: str,
) -> tuple[dict[str, str] | None, str]:
    revenue = annual_series(companyfacts, CONCEPT_REVENUE, ["USD"])
    eps = annual_series(companyfacts, CONCEPT_EPS_DILUTED, ["USD/shares"])
    gross_profit = annual_series(companyfacts, CONCEPT_GROSS_PROFIT, ["USD"])
    operating_income = annual_series(companyfacts, CONCEPT_OPERATING_INCOME, ["USD"])
    interest_expense = annual_series(companyfacts, CONCEPT_INTEREST_EXPENSE, ["USD"])
    diluted_shares = annual_series(companyfacts, CONCEPT_DILUTED_SHARES, ["shares"])

    years = sorted(set().union(revenue, eps, gross_profit, operating_income, interest_expense, diluted_shares))
    if not years:
        return None, "SEC CompanyFacts response contained no supported annual us-gaap fact series"
    latest_year = max(years)
    currency = detect_currency(revenue, eps, gross_profit, operating_income, interest_expense)
    if not currency:
        return None, "SEC CompanyFacts response did not expose a supported USD-denominated annual fact"

    revenue_latest = latest_value(revenue, latest_year)
    operating_income_latest = latest_value(operating_income, latest_year)
    interest_expense_latest = latest_value(interest_expense, latest_year)
    interest_coverage = ""
    if operating_income_latest is not None and interest_expense_latest is not None and interest_expense_latest > 0:
        interest_coverage = pct(operating_income_latest / interest_expense_latest)

    row = {field: "" for field in SNAPSHOT_INPUT_FIELDS}
    row.update(
        {
            "ticker": canonicalize_ticker(master_row.get("ticker", "")),
            "isin": canonical_isin(master_row.get("isin", "")),
            "company_name": str(master_row.get("company_name", "") or "").strip(),
            "source_name": SEC_SOURCE_NAME,
            "source_as_of_date": as_of_date,
            "fiscal_year": str(latest_year),
            "currency": currency,
            "source_reference": source_reference(
                identity["cik"],
                latest_year,
                revenue,
                eps,
                gross_profit,
                operating_income,
                interest_expense,
                diluted_shares,
            ),
            "notes": "Read-only SEC CompanyFacts snapshot; unsupported or insufficient KPI fields left blank.",
            "revenue_cagr_5y": cagr_pct(revenue, latest_year),
            "eps_cagr_5y": cagr_pct(eps, latest_year),
            "gross_margin": ratio_pct(latest_value(gross_profit, latest_year), revenue_latest),
            "operating_margin": ratio_pct(operating_income_latest, revenue_latest),
            "interest_coverage": interest_coverage,
            "share_count_cagr_5y": cagr_pct(diluted_shares, latest_year),
        }
    )
    return row, ""


def validate_as_of_date(as_of_date: str) -> str:
    text = str(as_of_date or "").strip()
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid --as-of-date: {as_of_date!r}; expected YYYY-MM-DD") from exc
    return text


def build_summary_rows(
    *,
    master_rows_total: int,
    identity_rows_total: int,
    sec_candidates_total: int,
    fetched_rows_total: int,
    snapshot_rows_written: int,
    failure_rows_total: int,
    unsupported_rows_total: int,
) -> list[dict[str, str]]:
    return [
        {
            "master_rows_total": str(master_rows_total),
            "identity_rows_total": str(identity_rows_total),
            "sec_candidates_total": str(sec_candidates_total),
            "fetched_rows_total": str(fetched_rows_total),
            "snapshot_rows_written": str(snapshot_rows_written),
            "failure_rows_total": str(failure_rows_total),
            "unsupported_rows_total": str(unsupported_rows_total),
            "notes": "SEC CompanyFacts fetch writes only a local fundamentals snapshot for the existing snapshot/review/evidence path; no raw master or raw evidence input was modified.",
        }
    ]


def write_sec_identity_map_template(path_value: str = DEFAULT_SEC_IDENTITY_MAP_TEMPLATE) -> Path:
    return write_csv_rows(path_value, IDENTITY_MAP_FIELDS, [])


def run_external_sec_companyfacts_fetch(
    *,
    master_input: str = DEFAULT_PERSONAL_MASTER_PATH,
    identity_map_input: str = DEFAULT_SEC_IDENTITY_MAP_INPUT,
    output: str = DEFAULT_SNAPSHOT_INPUT_PATH,
    registry_output: str = DEFAULT_SEC_FETCH_REGISTRY_OUTPUT,
    failures_output: str = DEFAULT_SEC_FETCH_FAILURES_OUTPUT,
    summary_output: str = DEFAULT_SEC_FETCH_SUMMARY_OUTPUT,
    as_of_date: str,
    allow_network: bool = False,
    sec_user_agent: str = "",
    fetcher: Callable[[str, str], dict[str, Any]] | None = None,
) -> dict[str, Path]:
    as_of_date = validate_as_of_date(as_of_date)
    master_rows = read_csv_rows(master_input)
    validate_personal_fundamentals_master(master_rows, f"personal fundamentals master ({master_input})")
    identity_fieldnames, raw_identity_rows = read_csv_rows_with_header(identity_map_input)
    require_header_columns(identity_fieldnames, IDENTITY_MAP_FIELDS, f"SEC identity map ({identity_map_input})")
    identity_rows = validate_identity_map_rows(raw_identity_rows, f"SEC identity map ({identity_map_input})")
    enabled_rows = [row for row in identity_rows if parse_enabled(row.get("enabled", ""))]
    if enabled_rows and not allow_network:
        raise ValueError("SEC CompanyFacts fetch requires explicit --allow-network before any external HTTP request")
    if enabled_rows and not str(sec_user_agent or "").strip():
        raise ValueError("SEC CompanyFacts fetch requires explicit --sec-user-agent before any external HTTP request")

    fetch = fetcher or fetch_companyfacts
    master_index = build_master_identifier_index(master_rows)
    registry_rows: list[dict[str, str]] = []
    failure_rows: list[dict[str, str]] = []
    snapshot_rows: list[dict[str, str]] = []
    sec_candidates_total = 0
    fetched_rows_total = 0
    unsupported_rows_total = 0

    for identity in enabled_rows:
        matched_master, match_error = match_identity_to_master(identity, master_index)
        if matched_master is None:
            registry_rows.append(registry_row(identity, fetch_status=SKIPPED_IDENTITY_MISSING, notes=match_error))
            failure_rows.append(failure_row(identity, SKIPPED_IDENTITY_MISSING, match_error))
            continue
        if not identity["cik"]:
            reason = "enabled SEC identity row requires non-blank cik"
            registry_rows.append(registry_row(identity, fetch_status=SKIPPED_IDENTITY_MISSING, notes=reason))
            failure_rows.append(failure_row(identity, SKIPPED_IDENTITY_MISSING, reason))
            continue
        asset_type = identity["asset_type"] or safe_upper(matched_master.get("asset_type", ""))
        country = identity["country"] or safe_upper(matched_master.get("country", ""))
        if asset_type not in SUPPORTED_ASSET_TYPES or country not in SUPPORTED_COUNTRIES:
            unsupported_rows_total += 1
            reason = f"SEC fetch is US STOCK-only in this patch; asset_type={asset_type or '<blank>'}, country={country or '<blank>'}"
            registry_rows.append(registry_row(identity, fetch_status=SKIPPED_UNSUPPORTED, notes=reason))
            failure_rows.append(failure_row(identity, SKIPPED_UNSUPPORTED, reason))
            continue

        sec_candidates_total += 1
        try:
            companyfacts = fetch(identity["cik"], sec_user_agent)
        except (HTTPError, URLError, TimeoutError) as exc:
            reason = f"{type(exc).__name__}: {exc}"
            registry_rows.append(registry_row(identity, fetch_status=FAILED_HTTP, notes=reason))
            failure_rows.append(failure_row(identity, FAILED_HTTP, reason))
            continue
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            reason = f"{type(exc).__name__}: {exc}"
            registry_rows.append(registry_row(identity, fetch_status=FAILED_PARSE, notes=reason))
            failure_rows.append(failure_row(identity, FAILED_PARSE, reason))
            continue

        snapshot_row, parse_failure = build_snapshot_row_from_companyfacts(
            master_row=matched_master,
            identity=identity,
            companyfacts=companyfacts,
            as_of_date=as_of_date,
        )
        if snapshot_row is None:
            registry_rows.append(registry_row(identity, fetch_status=FAILED_PARSE, notes=parse_failure))
            failure_rows.append(failure_row(identity, FAILED_PARSE, parse_failure))
            continue
        fetched_rows_total += 1
        snapshot_rows.append(snapshot_row)
        registry_rows.append(
            registry_row(
                identity,
                fetch_status=FETCHED,
                source_reference=snapshot_row["source_reference"],
                source_as_of_date=as_of_date,
                notes="SEC CompanyFacts fetched and emitted as local snapshot row.",
            )
        )

    registry_rows.sort(key=sort_key)
    failure_rows.sort(key=sort_key)
    snapshot_rows.sort(key=sort_key)
    outputs = {
        "snapshot": write_csv_rows(output, SNAPSHOT_INPUT_FIELDS, snapshot_rows),
        "registry": write_csv_rows(registry_output, REGISTRY_FIELDS, registry_rows),
        "failures": write_csv_rows(failures_output, FAILURES_FIELDS, failure_rows),
        "summary": write_csv_rows(
            summary_output,
            SUMMARY_FIELDS,
            build_summary_rows(
                master_rows_total=len(master_rows),
                identity_rows_total=len(identity_rows),
                sec_candidates_total=sec_candidates_total,
                fetched_rows_total=fetched_rows_total,
                snapshot_rows_written=len(snapshot_rows),
                failure_rows_total=len(failure_rows),
                unsupported_rows_total=unsupported_rows_total,
            ),
        ),
    }
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch SEC CompanyFacts into a local personal fundamentals snapshot CSV.")
    parser.add_argument("--master-input", default=DEFAULT_PERSONAL_MASTER_PATH, help="Personal fundamentals master CSV.")
    parser.add_argument("--identity-map-input", default=DEFAULT_SEC_IDENTITY_MAP_INPUT, help="Explicit local SEC identity map CSV.")
    parser.add_argument("--output", default=DEFAULT_SNAPSHOT_INPUT_PATH, help="Local fundamentals snapshot CSV output.")
    parser.add_argument("--registry-output", default=DEFAULT_SEC_FETCH_REGISTRY_OUTPUT, help="SEC fetch registry output.")
    parser.add_argument("--failures-output", default=DEFAULT_SEC_FETCH_FAILURES_OUTPUT, help="SEC fetch failures output.")
    parser.add_argument("--summary-output", default=DEFAULT_SEC_FETCH_SUMMARY_OUTPUT, help="SEC fetch summary output.")
    parser.add_argument("--identity-map-template-output", default=DEFAULT_SEC_IDENTITY_MAP_TEMPLATE, help="SEC identity map template output.")
    parser.add_argument("--as-of-date", default=date.today().isoformat(), help="Snapshot source_as_of_date to write, YYYY-MM-DD.")
    parser.add_argument("--allow-network", action="store_true", help="Allow real external SEC HTTP requests.")
    parser.add_argument("--sec-user-agent", default="", help="Required SEC User-Agent for real fetches, e.g. 'Name email@example.com'.")
    parser.add_argument("--template-only", action="store_true", help="Only write the SEC identity-map template; do not fetch.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.template_only:
        write_sec_identity_map_template(args.identity_map_template_output)
        return
    run_external_sec_companyfacts_fetch(
        master_input=args.master_input,
        identity_map_input=args.identity_map_input,
        output=args.output,
        registry_output=args.registry_output,
        failures_output=args.failures_output,
        summary_output=args.summary_output,
        as_of_date=args.as_of_date,
        allow_network=args.allow_network,
        sec_user_agent=args.sec_user_agent,
    )


if __name__ == "__main__":
    main()
