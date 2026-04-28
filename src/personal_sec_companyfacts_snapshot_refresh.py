from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.common import read_csv_rows, resolve_repo_path, write_csv_rows
from src.external_sec_companyfacts_fetch import canonical_cik
from src.personal_sec_derived_kpi_compose import clean_text

DEFAULT_APPROVAL_APPLIED = "data/raw/private/fundamentals/personal_sec_companyfacts_concept_approval_applied.csv"
DEFAULT_IDENTITY_MAP = "data/raw/private/fundamentals/personal_sec_identity_map.csv"
DEFAULT_USER_AGENT_FILE = "data/raw/private/fundamentals/sec_user_agent.local.txt"
DEFAULT_OUTPUT_ROOT = "data/raw/private/fundamentals/sec_companyfacts_snapshots"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_sec_companyfacts_snapshot_retention_summary.csv"
DEFAULT_REPORT_OUTPUT = "reports/2026-04-27/personal_sec_companyfacts_snapshot_retention_report.md"

SEC_COMPANYFACTS_URL_TEMPLATE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
CORE_SCOPE_ISINS = {
    "US02079K3059",
    "US22788C1053",
    "US8522341036",
    "US92826C8394",
}

MANIFEST_FIELDS = [
    "run_id",
    "fetched_at_utc",
    "holding_name",
    "ticker",
    "isin",
    "cik",
    "snapshot_path",
    "snapshot_exists",
    "snapshot_sha256",
    "fetch_status",
    "error_reason",
]

SUMMARY_FIELDS = [
    "run_id",
    "scope_holdings_count",
    "fetch_attempted_count",
    "fetch_success_count",
    "fetch_failed_count",
    "snapshots_written_count",
    "snapshots_private_root_category",
    "no_score_change_confirmed",
    "no_master_mutation_confirmed",
    "no_evidence_apply_confirmed",
    "no_imputation_confirmed",
]


@dataclass(frozen=True)
class SnapshotRefreshResult:
    run_id: str
    manifest_path: Path
    summary_path: Path
    report_path: Path
    summary: dict[str, str]
    network_performed: bool
    user_agent_present: bool


def read_user_agent(user_agent_file: str | Path = DEFAULT_USER_AGENT_FILE) -> tuple[str, bool]:
    path = resolve_repo_path(user_agent_file)
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        return http_header_safe_user_agent(value), bool(value)
    value = os.getenv("SEC_USER_AGENT", "").strip()
    return http_header_safe_user_agent(value), bool(value)


def http_header_safe_user_agent(value: str) -> str:
    return value.encode("latin-1", errors="ignore").decode("latin-1").strip()


def approved_scope_identities(
    approval_applied: str | Path = DEFAULT_APPROVAL_APPLIED,
    identity_map: str | Path = DEFAULT_IDENTITY_MAP,
) -> list[dict[str, str]]:
    approval_path = resolve_repo_path(approval_applied)
    identity_path = resolve_repo_path(identity_map)
    if not approval_path.exists():
        raise RuntimeError("MISSING_PRIVATE_APPROVAL_APPLIED")
    if not identity_path.exists():
        raise RuntimeError("MISSING_PRIVATE_SEC_IDENTITY_MAP")
    approved_isins = {
        clean_text(row.get("isin")).upper()
        for row in read_csv_rows(approval_path)
        if clean_text(row.get("approval_status")).upper() == "APPROVED" and clean_text(row.get("isin")).upper() in CORE_SCOPE_ISINS
    }
    identities: list[dict[str, str]] = []
    for row in read_csv_rows(identity_path):
        isin = clean_text(row.get("isin")).upper()
        enabled = clean_text(row.get("enabled")).lower() in {"1", "true", "yes", "y"}
        if isin not in approved_isins or not enabled:
            continue
        identities.append(
            {
                "holding_name": clean_text(row.get("company_name")),
                "ticker": clean_text(row.get("ticker")).upper(),
                "isin": isin,
                "cik": canonical_cik(row.get("cik")),
            }
        )
    return sorted(identities, key=lambda row: row["isin"])


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_")
    return cleaned[:48] or "holding"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def fetch_companyfacts_json(cik: str, user_agent: str) -> dict[str, Any]:
    request = Request(
        SEC_COMPANYFACTS_URL_TEMPLATE.format(cik=canonical_cik(cik)),
        headers={
            "User-Agent": user_agent,
            "Accept-Encoding": "identity",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8")
    loaded = json.loads(payload)
    if not isinstance(loaded, dict) or not isinstance(loaded.get("facts"), dict):
        raise ValueError("SEC CompanyFacts response did not match expected JSON object with facts")
    return loaded


def private_snapshot_path(run_dir: Path, identity: dict[str, str]) -> Path:
    cik = canonical_cik(identity.get("cik"))
    ticker = slug(identity.get("ticker") or identity.get("isin") or "holding")
    return run_dir / f"{cik}_{ticker}_companyfacts.json"


def manifest_row(
    *,
    run_id: str,
    fetched_at_utc: str,
    identity: dict[str, str],
    snapshot_path: Path | None,
    fetch_status: str,
    error_reason: str = "",
) -> dict[str, str]:
    exists = bool(snapshot_path and snapshot_path.exists())
    return {
        "run_id": run_id,
        "fetched_at_utc": fetched_at_utc,
        "holding_name": identity.get("holding_name", ""),
        "ticker": identity.get("ticker", ""),
        "isin": identity.get("isin", ""),
        "cik": identity.get("cik", ""),
        "snapshot_path": str(snapshot_path) if snapshot_path else "",
        "snapshot_exists": str(exists),
        "snapshot_sha256": sha256_file(snapshot_path) if exists and snapshot_path else "",
        "fetch_status": fetch_status,
        "error_reason": error_reason,
    }


def public_report(summary: dict[str, str], failures: list[dict[str, str]]) -> str:
    failure_lines = []
    for row in failures:
        failure_lines.append(f"- {row['isin']}: `{row['fetch_status']}`")
    if not failure_lines:
        failure_lines.append("- none")
    return "\n".join(
        [
            "# SEC CompanyFacts Snapshot Retention Report",
            "",
            "## Executive Summary",
            f"- run_id: `{summary['run_id']}`",
            f"- scope_holdings_count: `{summary['scope_holdings_count']}`",
            f"- fetch_attempted_count: `{summary['fetch_attempted_count']}`",
            f"- fetch_success_count: `{summary['fetch_success_count']}`",
            f"- fetch_failed_count: `{summary['fetch_failed_count']}`",
            f"- snapshots_written_count: `{summary['snapshots_written_count']}`",
            "",
            "## Scope",
            "Fetch-only retention for approved SEC Core KPI holdings. Raw JSON snapshots are private and excluded from public reports and handoffs.",
            "",
            "## Fetch/Retention Counts",
            f"- private snapshot root category: `{summary['snapshots_private_root_category']}`",
            "",
            "## Failures",
            *failure_lines,
            "",
            "## Guardrail Confirmation",
            "- no_score_change_confirmed=True",
            "- no_master_mutation_confirmed=True",
            "- no_evidence_apply_confirmed=True",
            "- no_imputation_confirmed=True",
            "- raw snapshot contents omitted",
            "",
            "## Next Steps",
            "Run approved fact export, fact-source audit, and derived KPI compose against the retained private snapshots.",
            "",
        ]
    )


def run_personal_sec_companyfacts_snapshot_refresh(
    *,
    approval_applied: str | Path = DEFAULT_APPROVAL_APPLIED,
    identity_map: str | Path = DEFAULT_IDENTITY_MAP,
    user_agent_file: str | Path = DEFAULT_USER_AGENT_FILE,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    summary_output: str | Path = DEFAULT_SUMMARY_OUTPUT,
    report_output: str | Path = DEFAULT_REPORT_OUTPUT,
    fetcher: Callable[[str, str], dict[str, Any]] | None = None,
    run_id: str | None = None,
) -> SnapshotRefreshResult:
    user_agent, user_agent_present = read_user_agent(user_agent_file)
    if not user_agent_present:
        raise RuntimeError("SEC_USER_AGENT_MISSING")
    identities = approved_scope_identities(approval_applied, identity_map)
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fetched_at_utc = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    run_dir = resolve_repo_path(output_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    fetch = fetcher or fetch_companyfacts_json

    manifest_rows: list[dict[str, str]] = []
    for identity in identities:
        if not identity.get("cik"):
            manifest_rows.append(
                manifest_row(
                    run_id=run_id,
                    fetched_at_utc=fetched_at_utc,
                    identity=identity,
                    snapshot_path=None,
                    fetch_status="IDENTITY_MISSING",
                    error_reason="missing cik",
                )
            )
            continue
        snapshot_path = private_snapshot_path(run_dir, identity)
        try:
            payload = fetch(identity["cik"], user_agent)
            snapshot_path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
            status = "FETCHED"
            error = ""
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            status = "FAILED_FETCH"
            error = type(exc).__name__
        manifest_rows.append(
            manifest_row(
                run_id=run_id,
                fetched_at_utc=fetched_at_utc,
                identity=identity,
                snapshot_path=snapshot_path,
                fetch_status=status,
                error_reason=error,
            )
        )

    manifest_path = write_csv_rows(run_dir / "snapshot_manifest.csv", MANIFEST_FIELDS, manifest_rows)
    successes = [row for row in manifest_rows if row["fetch_status"] == "FETCHED"]
    failures = [row for row in manifest_rows if row["fetch_status"] != "FETCHED"]
    summary = {
        "run_id": run_id,
        "scope_holdings_count": str(len(identities)),
        "fetch_attempted_count": str(sum(1 for row in manifest_rows if row["fetch_status"] != "IDENTITY_MISSING")),
        "fetch_success_count": str(len(successes)),
        "fetch_failed_count": str(len(failures)),
        "snapshots_written_count": str(sum(1 for row in successes if row["snapshot_exists"] == "True")),
        "snapshots_private_root_category": "<private_sec_companyfacts_snapshot_root>",
        "no_score_change_confirmed": "True",
        "no_master_mutation_confirmed": "True",
        "no_evidence_apply_confirmed": "True",
        "no_imputation_confirmed": "True",
    }
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, [summary])
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(public_report(summary, failures), encoding="utf-8")
    return SnapshotRefreshResult(
        run_id=run_id,
        manifest_path=manifest_path,
        summary_path=summary_path,
        report_path=report_path,
        summary=summary,
        network_performed=bool(manifest_rows),
        user_agent_present=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch and retain raw SEC CompanyFacts snapshots privately for approved Core KPI concepts.")
    parser.add_argument("--approval-applied", default=DEFAULT_APPROVAL_APPLIED)
    parser.add_argument("--identity-map", default=DEFAULT_IDENTITY_MAP)
    parser.add_argument("--user-agent-file", default=DEFAULT_USER_AGENT_FILE)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_companyfacts_snapshot_refresh(
        approval_applied=args.approval_applied,
        identity_map=args.identity_map,
        user_agent_file=args.user_agent_file,
        output_root=args.output_root,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    print(f"snapshot_manifest=<private_sec_companyfacts_snapshot_manifest>")
    print(f"retention_summary={result.summary_path}")
    print(f"retention_report={result.report_path}")
    print(f"run_id={result.run_id}")
    print(f"fetch_success_count={result.summary['fetch_success_count']}")
    print(f"snapshots_written_count={result.summary['snapshots_written_count']}")
    print("no_evidence_apply_confirmed=True")


if __name__ == "__main__":
    main()
