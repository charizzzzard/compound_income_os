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

from src.common import canonicalize_ticker, resolve_repo_path, safe_upper, write_csv_rows
from src.external_sec_companyfacts_fetch import SUPPORTED_ASSET_TYPES, SUPPORTED_COUNTRIES, canonical_cik, canonical_isin
from src.fundamentals_master import DEFAULT_PERSONAL_MASTER_PATH, validate_personal_fundamentals_master

DEFAULT_SEC_TICKER_REFERENCE_URL = "https://www.sec.gov/files/company_tickers.json"
DEFAULT_CANDIDATES_OUTPUT = "data/processed/external_sec_identity_candidates.csv"
DEFAULT_FAILURES_OUTPUT = "data/processed/external_sec_identity_failures.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/external_sec_identity_summary.csv"

SEC_IDENTITY_SOURCE_NAME = "sec_company_tickers"

CANDIDATE_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "cik",
    "sec_entity_name",
    "asset_type",
    "country",
    "enabled",
    "source_name",
    "source_reference",
    "source_as_of_date",
    "match_status",
    "notes",
]

FAILURE_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "asset_type",
    "country",
    "match_status",
    "failure_reason",
    "source_name",
    "source_reference",
    "source_as_of_date",
    "notes",
]

SUMMARY_FIELDS = [
    "master_rows_total",
    "sec_reference_rows_total",
    "candidate_rows_total",
    "failure_rows_total",
    "unsupported_rows_total",
    "ambiguous_rows_total",
    "notes",
]

CANDIDATE_EXACT = "CANDIDATE_EXACT"
SKIPPED_UNSUPPORTED = "SKIPPED_UNSUPPORTED"
FAILED_NO_SEC_MATCH = "FAILED_NO_SEC_MATCH"
FAILED_AMBIGUOUS = "FAILED_AMBIGUOUS"
FAILED_CONTRACT = "FAILED_CONTRACT"


def read_csv_rows_with_header(path_value: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def validate_as_of_date(value: str) -> str:
    text = str(value or "").strip()
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid --as-of-date {value!r}; expected YYYY-MM-DD") from exc
    return text


def fetch_sec_company_tickers(sec_user_agent: str, url: str = DEFAULT_SEC_TICKER_REFERENCE_URL) -> Any:
    request = Request(
        url,
        headers={
            "User-Agent": sec_user_agent,
            "Accept-Encoding": "identity",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_sec_reference_rows(raw_payload: Any) -> list[dict[str, str]]:
    if isinstance(raw_payload, dict):
        values = raw_payload.values()
    elif isinstance(raw_payload, list):
        values = raw_payload
    else:
        raise ValueError("SEC company tickers payload must be a JSON object or list")

    rows: list[dict[str, str]] = []
    for raw_row in values:
        if not isinstance(raw_row, dict):
            raise ValueError("SEC company tickers payload contains a non-object row")
        ticker = canonicalize_ticker(raw_row.get("ticker", ""))
        title = str(raw_row.get("title", "") or "").strip()
        cik = canonical_cik(raw_row.get("cik_str", raw_row.get("cik", "")))
        if not ticker or not title or not cik:
            raise ValueError("SEC company tickers payload row missing ticker, title or cik")
        rows.append({"ticker": ticker, "sec_entity_name": title, "cik": cik})
    rows.sort(key=lambda row: (row["ticker"], row["cik"], row["sec_entity_name"]))
    return rows


def sec_reference_index(sec_rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in sec_rows:
        grouped.setdefault(row["ticker"], []).append(row)
    return grouped


def master_sort_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        canonicalize_ticker(row.get("ticker", "")),
        canonical_isin(row.get("isin", "")),
        str(row.get("company_name", "") or "").strip(),
    )


def is_supported_master_row(row: dict[str, str]) -> bool:
    return safe_upper(row.get("asset_type", "")) in SUPPORTED_ASSET_TYPES and safe_upper(row.get("country", "")) in SUPPORTED_COUNTRIES


def candidate_row(
    master_row: dict[str, str],
    *,
    cik: str = "",
    sec_entity_name: str = "",
    match_status: str,
    as_of_date: str,
    notes: str,
    source_reference: str = DEFAULT_SEC_TICKER_REFERENCE_URL,
) -> dict[str, str]:
    return {
        "ticker": canonicalize_ticker(master_row.get("ticker", "")),
        "isin": canonical_isin(master_row.get("isin", "")),
        "company_name": str(master_row.get("company_name", "") or "").strip(),
        "cik": canonical_cik(cik),
        "sec_entity_name": str(sec_entity_name or "").strip(),
        "asset_type": safe_upper(master_row.get("asset_type", "")),
        "country": safe_upper(master_row.get("country", "")),
        "enabled": "false",
        "source_name": SEC_IDENTITY_SOURCE_NAME,
        "source_reference": source_reference,
        "source_as_of_date": as_of_date,
        "match_status": match_status,
        "notes": notes,
    }


def failure_row(master_row: dict[str, str], *, match_status: str, reason: str, as_of_date: str) -> dict[str, str]:
    return {
        "ticker": canonicalize_ticker(master_row.get("ticker", "")),
        "isin": canonical_isin(master_row.get("isin", "")),
        "company_name": str(master_row.get("company_name", "") or "").strip(),
        "asset_type": safe_upper(master_row.get("asset_type", "")),
        "country": safe_upper(master_row.get("country", "")),
        "match_status": match_status,
        "failure_reason": reason,
        "source_name": SEC_IDENTITY_SOURCE_NAME,
        "source_reference": DEFAULT_SEC_TICKER_REFERENCE_URL,
        "source_as_of_date": as_of_date,
        "notes": "SEC identity resolver never writes the private identity map; review candidates manually.",
    }


def build_identity_candidates(
    master_rows: list[dict[str, str]],
    sec_rows: list[dict[str, str]],
    *,
    as_of_date: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], Counter[str]]:
    sec_index = sec_reference_index(sec_rows)
    candidate_rows: list[dict[str, str]] = []
    failure_rows: list[dict[str, str]] = []
    counters: Counter[str] = Counter()

    for master_row in sorted(master_rows, key=master_sort_key):
        ticker = canonicalize_ticker(master_row.get("ticker", ""))
        asset_type = safe_upper(master_row.get("asset_type", ""))
        country = safe_upper(master_row.get("country", ""))
        if not is_supported_master_row(master_row):
            reason = f"SEC identity candidate resolver is US STOCK-only; asset_type={asset_type or '<blank>'}, country={country or '<blank>'}"
            row = candidate_row(master_row, match_status=SKIPPED_UNSUPPORTED, as_of_date=as_of_date, notes=reason)
            candidate_rows.append(row)
            failure_rows.append(failure_row(master_row, match_status=SKIPPED_UNSUPPORTED, reason=reason, as_of_date=as_of_date))
            counters["unsupported_rows_total"] += 1
            continue
        if not ticker:
            reason = "Personal-Master row has no ticker for exact SEC ticker match."
            candidate_rows.append(candidate_row(master_row, match_status=FAILED_CONTRACT, as_of_date=as_of_date, notes=reason))
            failure_rows.append(failure_row(master_row, match_status=FAILED_CONTRACT, reason=reason, as_of_date=as_of_date))
            continue

        matches = sec_index.get(ticker, [])
        if not matches:
            reason = f"No exact SEC ticker match for ticker={ticker}."
            candidate_rows.append(candidate_row(master_row, match_status=FAILED_NO_SEC_MATCH, as_of_date=as_of_date, notes=reason))
            failure_rows.append(failure_row(master_row, match_status=FAILED_NO_SEC_MATCH, reason=reason, as_of_date=as_of_date))
            continue
        if len(matches) > 1:
            reason = f"Ambiguous SEC ticker match for ticker={ticker}; matched CIKs={','.join(row['cik'] for row in matches)}."
            candidate_rows.append(candidate_row(master_row, match_status=FAILED_AMBIGUOUS, as_of_date=as_of_date, notes=reason))
            failure_rows.append(failure_row(master_row, match_status=FAILED_AMBIGUOUS, reason=reason, as_of_date=as_of_date))
            counters["ambiguous_rows_total"] += 1
            continue

        match = matches[0]
        candidate_rows.append(
            candidate_row(
                master_row,
                cik=match["cik"],
                sec_entity_name=match["sec_entity_name"],
                match_status=CANDIDATE_EXACT,
                as_of_date=as_of_date,
                notes="Exact ticker candidate from official SEC company_tickers reference; review before copying into private identity map.",
            )
        )

    return candidate_rows, failure_rows, counters


def build_summary_rows(
    *,
    master_rows_total: int,
    sec_reference_rows_total: int,
    candidate_rows_total: int,
    failure_rows_total: int,
    unsupported_rows_total: int,
    ambiguous_rows_total: int,
) -> list[dict[str, str]]:
    return [
        {
            "master_rows_total": str(master_rows_total),
            "sec_reference_rows_total": str(sec_reference_rows_total),
            "candidate_rows_total": str(candidate_rows_total),
            "failure_rows_total": str(failure_rows_total),
            "unsupported_rows_total": str(unsupported_rows_total),
            "ambiguous_rows_total": str(ambiguous_rows_total),
            "notes": "SEC identity candidates are staging only; private identity map was not modified.",
        }
    ]


def run_external_sec_identity_resolve(
    *,
    master_input: str = DEFAULT_PERSONAL_MASTER_PATH,
    candidates_output: str = DEFAULT_CANDIDATES_OUTPUT,
    failures_output: str = DEFAULT_FAILURES_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    as_of_date: str,
    allow_network: bool = False,
    sec_user_agent: str = "",
    fetcher: Callable[[str], Any] | None = None,
) -> dict[str, Path]:
    as_of_date = validate_as_of_date(as_of_date)
    if not allow_network:
        raise ValueError("SEC identity resolver requires explicit --allow-network before any external HTTP request")
    if not str(sec_user_agent or "").strip():
        raise ValueError("SEC identity resolver requires explicit --sec-user-agent before any external HTTP request")

    _fieldnames, raw_master_rows = read_csv_rows_with_header(master_input)
    master_rows = [row for row in raw_master_rows if any(str(value or "").strip() for value in row.values())]
    validate_personal_fundamentals_master(master_rows, f"personal fundamentals master ({master_input})")

    try:
        raw_sec_payload = fetcher(sec_user_agent) if fetcher else fetch_sec_company_tickers(sec_user_agent)
        sec_rows = normalize_sec_reference_rows(raw_sec_payload)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError, TypeError) as exc:
        reason = f"{type(exc).__name__}: {exc}"
        failure_rows = [
            {
                "ticker": "",
                "isin": "",
                "company_name": "",
                "asset_type": "",
                "country": "",
                "match_status": FAILED_CONTRACT,
                "failure_reason": reason,
                "source_name": SEC_IDENTITY_SOURCE_NAME,
                "source_reference": DEFAULT_SEC_TICKER_REFERENCE_URL,
                "source_as_of_date": as_of_date,
                "notes": "Official SEC ticker reference could not be loaded or parsed.",
            }
        ]
        write_csv_rows(candidates_output, CANDIDATE_FIELDS, [])
        write_csv_rows(failures_output, FAILURE_FIELDS, failure_rows)
        write_csv_rows(
            summary_output,
            SUMMARY_FIELDS,
            build_summary_rows(
                master_rows_total=len(master_rows),
                sec_reference_rows_total=0,
                candidate_rows_total=0,
                failure_rows_total=len(failure_rows),
                unsupported_rows_total=0,
                ambiguous_rows_total=0,
            ),
        )
        raise ValueError(f"SEC identity resolver failed to load official SEC ticker reference; see {failures_output}") from exc

    candidates, failures, counters = build_identity_candidates(master_rows, sec_rows, as_of_date=as_of_date)
    candidates.sort(key=lambda row: (master_sort_key(row), row["match_status"], row["cik"]))
    failures.sort(key=lambda row: (master_sort_key(row), row["match_status"], row["failure_reason"]))

    return {
        "identity_candidates": write_csv_rows(candidates_output, CANDIDATE_FIELDS, candidates),
        "identity_failures": write_csv_rows(failures_output, FAILURE_FIELDS, failures),
        "identity_summary": write_csv_rows(
            summary_output,
            SUMMARY_FIELDS,
            build_summary_rows(
                master_rows_total=len(master_rows),
                sec_reference_rows_total=len(sec_rows),
                candidate_rows_total=sum(1 for row in candidates if row["match_status"] == CANDIDATE_EXACT),
                failure_rows_total=len(failures),
                unsupported_rows_total=counters.get("unsupported_rows_total", 0),
                ambiguous_rows_total=counters.get("ambiguous_rows_total", 0),
            ),
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve official SEC identity candidates for the private SEC identity map.")
    parser.add_argument("--master-input", default=DEFAULT_PERSONAL_MASTER_PATH, help="Personal fundamentals master CSV.")
    parser.add_argument("--candidates-output", default=DEFAULT_CANDIDATES_OUTPUT, help="SEC identity candidates output.")
    parser.add_argument("--failures-output", default=DEFAULT_FAILURES_OUTPUT, help="SEC identity failures output.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT, help="SEC identity summary output.")
    parser.add_argument("--as-of-date", default=date.today().isoformat(), help="Source as-of date, YYYY-MM-DD.")
    parser.add_argument("--allow-network", action="store_true", help="Allow official SEC ticker-reference HTTP request.")
    parser.add_argument("--sec-user-agent", default="", help="Required SEC User-Agent, e.g. 'Name email@example.com'.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_external_sec_identity_resolve(
        master_input=args.master_input,
        candidates_output=args.candidates_output,
        failures_output=args.failures_output,
        summary_output=args.summary_output,
        as_of_date=args.as_of_date,
        allow_network=args.allow_network,
        sec_user_agent=args.sec_user_agent,
    )


if __name__ == "__main__":
    main()
