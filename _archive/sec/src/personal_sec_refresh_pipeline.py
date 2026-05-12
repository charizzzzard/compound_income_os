from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Callable

from src.common import read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows
from src.external_sec_companyfacts_fetch import (
    DEFAULT_SEC_FETCH_FAILURES_OUTPUT,
    DEFAULT_SEC_FETCH_REGISTRY_OUTPUT,
    DEFAULT_SEC_FETCH_SUMMARY_OUTPUT,
    DEFAULT_SEC_IDENTITY_MAP_INPUT,
    IDENTITY_MAP_FIELDS,
    SEC_SOURCE_NAME,
    SUPPORTED_ASSET_TYPES,
    SUPPORTED_COUNTRIES,
    canonical_isin,
    parse_enabled,
    read_csv_rows_with_header as read_fetch_csv_rows_with_header,
    require_header_columns,
    run_external_sec_companyfacts_fetch,
    validate_identity_map_rows,
)
from src.external_sec_identity_resolve import (
    DEFAULT_CANDIDATES_OUTPUT as DEFAULT_SEC_IDENTITY_CANDIDATES_OUTPUT,
    DEFAULT_FAILURES_OUTPUT as DEFAULT_SEC_IDENTITY_FAILURES_OUTPUT,
    DEFAULT_SUMMARY_OUTPUT as DEFAULT_SEC_IDENTITY_SUMMARY_OUTPUT,
    run_external_sec_identity_resolve,
)
from src.fundamentals_evidence_apply import (
    DEFAULT_APPLY_REGISTRY_OUTPUT,
    DEFAULT_APPLY_SUMMARY_OUTPUT,
    DEFAULT_EVIDENCE_APPLIED_MASTER_OUTPUT,
    run_fundamentals_evidence_apply,
)
from src.fundamentals_evidence_compose import (
    DEFAULT_COMPOSED_OUTPUT,
    DEFAULT_CONFLICTS_OUTPUT,
    DEFAULT_SUMMARY_OUTPUT as DEFAULT_COMPOSE_SUMMARY_OUTPUT,
    run_fundamentals_evidence_compose,
)
from src.fundamentals_evidence_engine import (
    DEFAULT_BACKLOG_OUTPUT,
    DEFAULT_EVIDENCE_INPUT_PATH,
    DEFAULT_PROPOSED_UPDATES_OUTPUT,
    DEFAULT_REGISTRY_OUTPUT as DEFAULT_EVIDENCE_REGISTRY_OUTPUT,
    DEFAULT_SUMMARY_OUTPUT as DEFAULT_EVIDENCE_SUMMARY_OUTPUT,
    EVIDENCE_INPUT_FIELDS,
    run_fundamentals_evidence_engine,
)
from src.fundamentals_master import DEFAULT_METRIC_DEFINITIONS_PATH, DEFAULT_PERSONAL_MASTER_PATH
from src.fundamentals_snapshot_ingestion import (
    DEFAULT_EVIDENCE_STAGING_OUTPUT,
    DEFAULT_NORMALIZED_OUTPUT,
    DEFAULT_SNAPSHOT_INPUT_PATH,
    DEFAULT_SUMMARY_OUTPUT as DEFAULT_SNAPSHOT_SUMMARY_OUTPUT,
    DEFAULT_UNMATCHED_OUTPUT,
    run_fundamentals_snapshot_ingestion,
)
from src.fundamentals_snapshot_review import (
    DEFAULT_PROMOTED_EVIDENCE_OUTPUT,
    DEFAULT_REVIEW_BACKLOG_OUTPUT,
    DEFAULT_REVIEW_INPUT_PATH,
    DEFAULT_REVIEW_REGISTRY_OUTPUT,
    DEFAULT_REVIEW_SUMMARY_OUTPUT,
    SNAPSHOT_REVIEW_INPUT_FIELDS,
    STAGING_MATCH_FIELDS,
    canonical_review_row,
    canonical_staging_row,
    is_blank_row,
    row_signature,
    run_fundamentals_snapshot_review,
    sort_identity_key,
)
from src.personal_run_engine import PersonalRunOptions, run_personal_run_engine

DEFAULT_AUTO_REVIEW_OUTPUT = "data/processed/personal_fundamentals_snapshot_review_auto.csv"
DEFAULT_RESOLVED_REVIEW_OUTPUT = "data/processed/personal_fundamentals_snapshot_review_resolved.csv"
DEFAULT_REFRESH_SUMMARY_OUTPUT = "data/processed/personal_sec_refresh_summary.csv"

REVIEW_POLICY_MANUAL_ONLY = "manual_only"
REVIEW_POLICY_AUTO_SAFE = "auto_safe"
REVIEW_POLICY_REVIEWED_INPUT_ONLY = "reviewed_input_only"
VALID_REVIEW_POLICIES = {
    REVIEW_POLICY_MANUAL_ONLY,
    REVIEW_POLICY_AUTO_SAFE,
    REVIEW_POLICY_REVIEWED_INPUT_ONLY,
}

AUTO_SAFE_KPI_ALLOWLIST = {
    "revenue_cagr_5y",
    "eps_cagr_5y",
    "gross_margin",
    "operating_margin",
    "interest_coverage",
    "share_count_cagr_5y",
}

REFRESH_SUMMARY_FIELDS = ["step_name", "status", "artifact_path", "notes"]


def read_csv_rows_with_header(path_value: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def path_exists(path_value: str | Path) -> bool:
    return resolve_repo_path(path_value).exists()


def validate_private_identity_map(identity_map_input: str) -> list[dict[str, str]]:
    if not path_exists(identity_map_input):
        raise ValueError(
            f"SEC refresh requires reviewed private SEC identity map: {identity_map_input}. "
            "Run identity candidate staging first, then manually review/copy rows into the private identity map."
        )
    fieldnames, raw_rows = read_fetch_csv_rows_with_header(identity_map_input)
    require_header_columns(fieldnames, IDENTITY_MAP_FIELDS, f"SEC identity map ({identity_map_input})")
    identity_rows = validate_identity_map_rows(raw_rows, f"SEC identity map ({identity_map_input})")
    enabled_rows = [row for row in identity_rows if parse_enabled(row.get("enabled", ""))]
    if not enabled_rows:
        raise ValueError(
            f"SEC refresh requires at least one enabled row in reviewed private SEC identity map: {identity_map_input}. "
            "Candidate staging output is not used automatically."
        )
    return enabled_rows


def enabled_identity_key(row: dict[str, str]) -> tuple[str, str]:
    return (str(row.get("ticker", "") or "").strip().upper(), canonical_isin(row.get("isin", "")))


def supported_enabled_identity_index(identity_rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    index: dict[tuple[str, str], dict[str, str]] = {}
    for row in identity_rows:
        if not row.get("cik"):
            continue
        if safe_upper(row.get("asset_type", "")) not in SUPPORTED_ASSET_TYPES:
            continue
        if safe_upper(row.get("country", "")) not in SUPPORTED_COUNTRIES:
            continue
        ticker, isin = enabled_identity_key(row)
        index[(ticker, isin)] = row
        if isin:
            # Bridge staging rows that still carry the dirty Personal-Master
            # ticker placeholder equal to the ISIN from the scope-prepare step.
            index.setdefault((isin, isin), row)
    return index


def load_staging_rows(staging_input: str) -> list[dict[str, str]]:
    fieldnames, raw_rows = read_csv_rows_with_header(staging_input)
    require_header_columns(fieldnames, EVIDENCE_INPUT_FIELDS, f"snapshot evidence staging ({staging_input})")
    return [
        canonical_staging_row(row, f"snapshot evidence staging ({staging_input})", row_number)
        for row_number, row in enumerate(raw_rows, start=2)
        if not is_blank_row(row)
    ]


def load_review_rows(review_input: str) -> list[dict[str, str]]:
    if not path_exists(review_input):
        return []
    fieldnames, raw_rows = read_csv_rows_with_header(review_input)
    require_header_columns(fieldnames, SNAPSHOT_REVIEW_INPUT_FIELDS, f"snapshot review input ({review_input})")
    return [
        canonical_review_row(row, f"snapshot review input ({review_input})", row_number)
        for row_number, row in enumerate(raw_rows, start=2)
        if not is_blank_row(row)
    ]


def build_review_row_from_staging(
    staging_row: dict[str, str],
    *,
    review_decision: str,
    review_reason: str,
    review_author: str,
    review_as_of_date: str,
    notes: str,
) -> dict[str, str]:
    return {
        "ticker": staging_row["ticker"],
        "isin": staging_row["isin"],
        "company_name": staging_row["company_name"],
        "kpi_name": staging_row["kpi_name"],
        "source_name": staging_row["source_name"],
        "source_reference": staging_row["source_reference"],
        "source_as_of_date": staging_row["source_as_of_date"],
        "fiscal_year": staging_row["fiscal_year"],
        "review_decision": review_decision,
        "review_reason": review_reason,
        "review_author": review_author,
        "review_as_of_date": review_as_of_date,
        "notes": notes,
    }


def auto_safe_decision(
    staging_row: dict[str, str],
    *,
    supported_identity_index: dict[tuple[str, str], dict[str, str]],
) -> tuple[str, str]:
    kpi_name = str(staging_row.get("kpi_name", "") or "").strip()
    reported_value = str(staging_row.get("reported_value", "") or "").strip()
    source_name = str(staging_row.get("source_name", "") or "").strip()
    ticker = str(staging_row.get("ticker", "") or "").strip().upper()
    isin = canonical_isin(staging_row.get("isin", ""))
    if source_name != SEC_SOURCE_NAME:
        return "PENDING", "auto_safe only approves staging rows from SEC CompanyFacts source."
    if kpi_name not in AUTO_SAFE_KPI_ALLOWLIST:
        return "PENDING", "KPI is outside the conservative SEC auto_safe allowlist."
    if not reported_value:
        return "PENDING", "reported_value is blank."
    if (ticker, isin) not in supported_identity_index:
        return "PENDING", "No enabled supported private SEC identity-map row matched this staging identity."
    return "APPROVE", "auto_safe approved SEC allowlist KPI with non-blank reported_value and reviewed private CIK identity."


def build_auto_review_rows(
    staging_rows: list[dict[str, str]],
    *,
    enabled_identity_rows: list[dict[str, str]],
    review_author: str,
    review_as_of_date: str,
) -> list[dict[str, str]]:
    supported_index = supported_enabled_identity_index(enabled_identity_rows)
    rows: list[dict[str, str]] = []
    for staging_row in sorted(staging_rows, key=sort_identity_key):
        decision, reason = auto_safe_decision(staging_row, supported_identity_index=supported_index)
        rows.append(
            build_review_row_from_staging(
                staging_row,
                review_decision=decision,
                review_reason=reason,
                review_author=review_author,
                review_as_of_date=review_as_of_date,
                notes="auto_safe generated processed review row; raw manual review input was not modified.",
            )
        )
    return rows


def merge_manual_and_auto_reviews(
    *,
    manual_rows: list[dict[str, str]],
    auto_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    merged: dict[tuple[str, ...], dict[str, str]] = {}
    for row in auto_rows:
        merged[row_signature(row, STAGING_MATCH_FIELDS)] = row
    for row in manual_rows:
        merged[row_signature(row, STAGING_MATCH_FIELDS)] = row
    return sorted(merged.values(), key=sort_identity_key)


def prepare_resolved_review_input(
    *,
    policy: str,
    staging_input: str,
    manual_review_input: str,
    enabled_identity_rows: list[dict[str, str]],
    auto_review_output: str = DEFAULT_AUTO_REVIEW_OUTPUT,
    resolved_review_output: str = DEFAULT_RESOLVED_REVIEW_OUTPUT,
    review_author: str = "sec_auto_safe",
    review_as_of_date: str,
) -> dict[str, Path]:
    if policy not in VALID_REVIEW_POLICIES:
        raise ValueError(f"unknown review policy: {policy}; allowed: {', '.join(sorted(VALID_REVIEW_POLICIES))}")
    staging_rows = load_staging_rows(staging_input)
    manual_rows = load_review_rows(manual_review_input)

    if policy == REVIEW_POLICY_AUTO_SAFE:
        auto_rows = build_auto_review_rows(
            staging_rows,
            enabled_identity_rows=enabled_identity_rows,
            review_author=review_author,
            review_as_of_date=review_as_of_date,
        )
        resolved_rows = merge_manual_and_auto_reviews(manual_rows=manual_rows, auto_rows=auto_rows)
        auto_output = write_csv_rows(auto_review_output, SNAPSHOT_REVIEW_INPUT_FIELDS, auto_rows)
    else:
        if not path_exists(manual_review_input):
            raise ValueError(f"review policy {policy} requires existing manual review input: {manual_review_input}")
        auto_output = write_csv_rows(auto_review_output, SNAPSHOT_REVIEW_INPUT_FIELDS, [])
        resolved_rows = sorted(manual_rows, key=sort_identity_key)

    resolved_output = write_csv_rows(resolved_review_output, SNAPSHOT_REVIEW_INPUT_FIELDS, resolved_rows)
    return {"auto_review": auto_output, "resolved_review": resolved_output}


def review_decision_counts(review_input: str) -> Counter[str]:
    return Counter(row.get("review_decision", "") for row in load_review_rows(review_input))


def append_summary_rows(step_rows: list[dict[str, str]], step_name: str, outputs: dict[str, Path], notes: str = "") -> None:
    for role, path_value in sorted(outputs.items()):
        step_rows.append(
            {
                "step_name": step_name,
                "status": "SUCCESS",
                "artifact_path": str(path_value),
                "notes": notes,
            }
        )


def run_personal_sec_refresh_pipeline(
    *,
    master_input: str = DEFAULT_PERSONAL_MASTER_PATH,
    identity_map_input: str = DEFAULT_SEC_IDENTITY_MAP_INPUT,
    snapshot_output: str = DEFAULT_SNAPSHOT_INPUT_PATH,
    sec_fetch_registry_output: str = DEFAULT_SEC_FETCH_REGISTRY_OUTPUT,
    sec_fetch_failures_output: str = DEFAULT_SEC_FETCH_FAILURES_OUTPUT,
    sec_fetch_summary_output: str = DEFAULT_SEC_FETCH_SUMMARY_OUTPUT,
    snapshot_normalized_output: str = DEFAULT_NORMALIZED_OUTPUT,
    snapshot_unmatched_output: str = DEFAULT_UNMATCHED_OUTPUT,
    snapshot_evidence_staging_output: str = DEFAULT_EVIDENCE_STAGING_OUTPUT,
    snapshot_summary_output: str = DEFAULT_SNAPSHOT_SUMMARY_OUTPUT,
    snapshot_review_registry_output: str = DEFAULT_REVIEW_REGISTRY_OUTPUT,
    snapshot_evidence_promoted_output: str = DEFAULT_PROMOTED_EVIDENCE_OUTPUT,
    snapshot_review_backlog_output: str = DEFAULT_REVIEW_BACKLOG_OUTPUT,
    snapshot_review_summary_output: str = DEFAULT_REVIEW_SUMMARY_OUTPUT,
    manual_evidence_input: str = DEFAULT_EVIDENCE_INPUT_PATH,
    evidence_composed_output: str = DEFAULT_COMPOSED_OUTPUT,
    evidence_compose_conflicts_output: str = DEFAULT_CONFLICTS_OUTPUT,
    evidence_compose_summary_output: str = DEFAULT_COMPOSE_SUMMARY_OUTPUT,
    evidence_registry_output: str = DEFAULT_EVIDENCE_REGISTRY_OUTPUT,
    evidence_backlog_output: str = DEFAULT_BACKLOG_OUTPUT,
    evidence_proposed_updates_output: str = DEFAULT_PROPOSED_UPDATES_OUTPUT,
    evidence_summary_output: str = DEFAULT_EVIDENCE_SUMMARY_OUTPUT,
    evidence_apply_registry_output: str = DEFAULT_APPLY_REGISTRY_OUTPUT,
    evidence_applied_master_output: str = DEFAULT_EVIDENCE_APPLIED_MASTER_OUTPUT,
    evidence_apply_summary_output: str = DEFAULT_APPLY_SUMMARY_OUTPUT,
    as_of_date: str,
    allow_network: bool = False,
    sec_user_agent: str = "",
    identity_preflight: bool = False,
    review_policy: str = REVIEW_POLICY_AUTO_SAFE,
    manual_review_input: str = DEFAULT_REVIEW_INPUT_PATH,
    auto_review_output: str = DEFAULT_AUTO_REVIEW_OUTPUT,
    resolved_review_output: str = DEFAULT_RESOLVED_REVIEW_OUTPUT,
    refresh_summary_output: str = DEFAULT_REFRESH_SUMMARY_OUTPUT,
    run_downstream: bool = False,
    downstream_stages: list[str] | None = None,
    watchlist_input: str | None = None,
    companyfacts_fetcher: Callable[[str, str], dict[str, object]] | None = None,
    identity_fetcher: Callable[[str], object] | None = None,
) -> dict[str, Path]:
    if not allow_network:
        raise ValueError("SEC refresh pipeline requires explicit --allow-network for SEC network steps")
    if not str(sec_user_agent or "").strip():
        raise ValueError("SEC refresh pipeline requires explicit --sec-user-agent for SEC network steps")

    enabled_identity_rows = validate_private_identity_map(identity_map_input)
    step_rows: list[dict[str, str]] = []
    outputs: dict[str, Path] = {}

    if identity_preflight:
        identity_outputs = run_external_sec_identity_resolve(
            master_input=master_input,
            candidates_output=DEFAULT_SEC_IDENTITY_CANDIDATES_OUTPUT,
            failures_output=DEFAULT_SEC_IDENTITY_FAILURES_OUTPUT,
            summary_output=DEFAULT_SEC_IDENTITY_SUMMARY_OUTPUT,
            as_of_date=as_of_date,
            allow_network=allow_network,
            sec_user_agent=sec_user_agent,
            fetcher=identity_fetcher,
        )
        outputs.update(identity_outputs)
        append_summary_rows(step_rows, "identity_preflight", identity_outputs, "Candidate staging only; private identity map was not modified.")

    fetch_outputs = run_external_sec_companyfacts_fetch(
        master_input=master_input,
        identity_map_input=identity_map_input,
        output=snapshot_output,
        registry_output=sec_fetch_registry_output,
        failures_output=sec_fetch_failures_output,
        summary_output=sec_fetch_summary_output,
        as_of_date=as_of_date,
        allow_network=allow_network,
        sec_user_agent=sec_user_agent,
        fetcher=companyfacts_fetcher,
    )
    outputs.update(fetch_outputs)
    append_summary_rows(step_rows, "sec_companyfacts_fetch", fetch_outputs)

    ingest_outputs = run_fundamentals_snapshot_ingestion(
        fundamentals_master_path=master_input,
        snapshot_input_path=snapshot_output,
        normalized_output=snapshot_normalized_output,
        unmatched_output=snapshot_unmatched_output,
        evidence_staging_output=snapshot_evidence_staging_output,
        summary_output=snapshot_summary_output,
        template_output=None,
    )
    outputs.update(ingest_outputs)
    append_summary_rows(step_rows, "fundamentals_snapshot_ingest", ingest_outputs)

    review_outputs = prepare_resolved_review_input(
        policy=review_policy,
        staging_input=snapshot_evidence_staging_output,
        manual_review_input=manual_review_input,
        enabled_identity_rows=enabled_identity_rows,
        auto_review_output=auto_review_output,
        resolved_review_output=resolved_review_output,
        review_as_of_date=as_of_date,
    )
    outputs.update(review_outputs)
    append_summary_rows(step_rows, "snapshot_review_resolve", review_outputs, f"review_policy={review_policy}; manual decisions take precedence.")

    if review_policy == REVIEW_POLICY_MANUAL_ONLY and run_downstream and review_decision_counts(resolved_review_output).get("APPROVE", 0) == 0:
        raise ValueError("review_policy=manual_only produced no APPROVE rows; downstream evidence-applied run was not started.")

    snapshot_review_outputs = run_fundamentals_snapshot_review(
        staging_input_path=snapshot_evidence_staging_output,
        review_input_path=resolved_review_output,
        registry_output=snapshot_review_registry_output,
        promoted_output=snapshot_evidence_promoted_output,
        backlog_output=snapshot_review_backlog_output,
        summary_output=snapshot_review_summary_output,
        template_output=None,
    )
    outputs.update(snapshot_review_outputs)
    append_summary_rows(step_rows, "fundamentals_snapshot_review", snapshot_review_outputs)

    compose_outputs = run_fundamentals_evidence_compose(
        manual_evidence_input_path=manual_evidence_input,
        promoted_evidence_input_path=snapshot_evidence_promoted_output,
        composed_output=evidence_composed_output,
        conflicts_output=evidence_compose_conflicts_output,
        summary_output=evidence_compose_summary_output,
    )
    outputs.update(compose_outputs)
    append_summary_rows(step_rows, "fundamentals_evidence_compose", compose_outputs)

    evidence_outputs = run_fundamentals_evidence_engine(
        fundamentals_master_path=master_input,
        evidence_input_path=evidence_composed_output,
        metric_definitions_path=DEFAULT_METRIC_DEFINITIONS_PATH,
        registry_output=evidence_registry_output,
        backlog_output=evidence_backlog_output,
        proposed_updates_output=evidence_proposed_updates_output,
        summary_output=evidence_summary_output,
        report_output=None,
        template_output=None,
    )
    outputs.update(evidence_outputs)
    append_summary_rows(step_rows, "fundamentals_evidence", evidence_outputs, "Evidence input mode is COMPOSED.")

    apply_outputs = run_fundamentals_evidence_apply(
        fundamentals_master_path=master_input,
        proposed_updates_input_path=evidence_proposed_updates_output,
        registry_output=evidence_apply_registry_output,
        evidence_applied_master_output=evidence_applied_master_output,
        summary_output=evidence_apply_summary_output,
    )
    outputs.update(apply_outputs)
    append_summary_rows(step_rows, "fundamentals_evidence_apply", apply_outputs)

    if run_downstream:
        stages = downstream_stages or ["scoring", "coverage", "watchlist", "monthly", "portfolio_review"]
        run_personal_run_engine(
            PersonalRunOptions(
                stages=stages,
                fundamentals_master=master_input,
                fundamentals_evidence_applied_master_output=evidence_applied_master_output,
                use_evidence_applied_master=True,
                watchlist_input=watchlist_input,
            ).normalized()
        )
        step_rows.append(
            {
                "step_name": "personal_run_downstream",
                "status": "SUCCESS",
                "artifact_path": "",
                "notes": f"Started downstream personal run with --use-evidence-applied-master; stages={','.join(stages)}.",
            }
        )

    summary_path = write_csv_rows(refresh_summary_output, REFRESH_SUMMARY_FIELDS, step_rows)
    outputs["refresh_summary"] = summary_path
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run explicit SEC refresh through snapshot/review/evidence/apply artifacts.")
    parser.add_argument("--master-input", default=DEFAULT_PERSONAL_MASTER_PATH, help="Personal fundamentals master CSV.")
    parser.add_argument("--identity-map-input", default=DEFAULT_SEC_IDENTITY_MAP_INPUT, help="Reviewed private SEC identity map CSV.")
    parser.add_argument("--snapshot-output", default=DEFAULT_SNAPSHOT_INPUT_PATH, help="Local SEC fundamentals snapshot output.")
    parser.add_argument("--sec-fetch-registry-output", default=DEFAULT_SEC_FETCH_REGISTRY_OUTPUT, help="SEC fetch registry output.")
    parser.add_argument("--sec-fetch-failures-output", default=DEFAULT_SEC_FETCH_FAILURES_OUTPUT, help="SEC fetch failures output.")
    parser.add_argument("--sec-fetch-summary-output", default=DEFAULT_SEC_FETCH_SUMMARY_OUTPUT, help="SEC fetch summary output.")
    parser.add_argument("--snapshot-normalized-output", default=DEFAULT_NORMALIZED_OUTPUT, help="Snapshot normalized output.")
    parser.add_argument("--snapshot-unmatched-output", default=DEFAULT_UNMATCHED_OUTPUT, help="Snapshot unmatched output.")
    parser.add_argument("--snapshot-evidence-staging-output", default=DEFAULT_EVIDENCE_STAGING_OUTPUT, help="Snapshot evidence staging output.")
    parser.add_argument("--snapshot-summary-output", default=DEFAULT_SNAPSHOT_SUMMARY_OUTPUT, help="Snapshot ingest summary output.")
    parser.add_argument("--snapshot-review-registry-output", default=DEFAULT_REVIEW_REGISTRY_OUTPUT, help="Snapshot review registry output.")
    parser.add_argument("--snapshot-evidence-promoted-output", default=DEFAULT_PROMOTED_EVIDENCE_OUTPUT, help="Promoted snapshot evidence output.")
    parser.add_argument("--snapshot-review-backlog-output", default=DEFAULT_REVIEW_BACKLOG_OUTPUT, help="Snapshot review backlog output.")
    parser.add_argument("--snapshot-review-summary-output", default=DEFAULT_REVIEW_SUMMARY_OUTPUT, help="Snapshot review summary output.")
    parser.add_argument("--manual-evidence-input", default=DEFAULT_EVIDENCE_INPUT_PATH, help="Manual raw evidence input for compose.")
    parser.add_argument("--evidence-composed-output", default=DEFAULT_COMPOSED_OUTPUT, help="Composed evidence output.")
    parser.add_argument("--evidence-compose-conflicts-output", default=DEFAULT_CONFLICTS_OUTPUT, help="Evidence compose conflicts output.")
    parser.add_argument("--evidence-compose-summary-output", default=DEFAULT_COMPOSE_SUMMARY_OUTPUT, help="Evidence compose summary output.")
    parser.add_argument("--evidence-registry-output", default=DEFAULT_EVIDENCE_REGISTRY_OUTPUT, help="Evidence registry output.")
    parser.add_argument("--evidence-backlog-output", default=DEFAULT_BACKLOG_OUTPUT, help="Evidence backlog output.")
    parser.add_argument("--evidence-proposed-updates-output", default=DEFAULT_PROPOSED_UPDATES_OUTPUT, help="Evidence proposed updates output.")
    parser.add_argument("--evidence-summary-output", default=DEFAULT_EVIDENCE_SUMMARY_OUTPUT, help="Evidence summary output.")
    parser.add_argument("--evidence-apply-registry-output", default=DEFAULT_APPLY_REGISTRY_OUTPUT, help="Evidence apply registry output.")
    parser.add_argument("--evidence-applied-master-output", default=DEFAULT_EVIDENCE_APPLIED_MASTER_OUTPUT, help="Evidence-applied master output.")
    parser.add_argument("--evidence-apply-summary-output", default=DEFAULT_APPLY_SUMMARY_OUTPUT, help="Evidence apply summary output.")
    parser.add_argument("--as-of-date", default=date.today().isoformat(), help="Run as-of date, YYYY-MM-DD.")
    parser.add_argument("--allow-network", action="store_true", help="Allow explicit SEC network steps.")
    parser.add_argument("--sec-user-agent", default="", help="Required SEC User-Agent.")
    parser.add_argument("--identity-preflight", action="store_true", help="Also stage official SEC identity candidates before refresh.")
    parser.add_argument(
        "--review-policy",
        choices=sorted(VALID_REVIEW_POLICIES),
        default=REVIEW_POLICY_AUTO_SAFE,
        help="Snapshot review resolution policy.",
    )
    parser.add_argument("--manual-review-input", default=DEFAULT_REVIEW_INPUT_PATH, help="Manual snapshot review input; never overwritten.")
    parser.add_argument("--auto-review-output", default=DEFAULT_AUTO_REVIEW_OUTPUT, help="Processed auto-review output.")
    parser.add_argument("--resolved-review-output", default=DEFAULT_RESOLVED_REVIEW_OUTPUT, help="Processed resolved review input.")
    parser.add_argument("--refresh-summary-output", default=DEFAULT_REFRESH_SUMMARY_OUTPUT, help="SEC refresh summary output.")
    parser.add_argument("--run-downstream", action="store_true", help="Run downstream personal stages with --use-evidence-applied-master after apply.")
    parser.add_argument("--downstream-stage", action="append", default=[], help="Downstream personal stage to run; repeatable.")
    parser.add_argument("--watchlist-input", help="Watchlist CSV input for downstream watchlist/monthly stages.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_personal_sec_refresh_pipeline(
        master_input=args.master_input,
        identity_map_input=args.identity_map_input,
        snapshot_output=args.snapshot_output,
        sec_fetch_registry_output=args.sec_fetch_registry_output,
        sec_fetch_failures_output=args.sec_fetch_failures_output,
        sec_fetch_summary_output=args.sec_fetch_summary_output,
        snapshot_normalized_output=args.snapshot_normalized_output,
        snapshot_unmatched_output=args.snapshot_unmatched_output,
        snapshot_evidence_staging_output=args.snapshot_evidence_staging_output,
        snapshot_summary_output=args.snapshot_summary_output,
        snapshot_review_registry_output=args.snapshot_review_registry_output,
        snapshot_evidence_promoted_output=args.snapshot_evidence_promoted_output,
        snapshot_review_backlog_output=args.snapshot_review_backlog_output,
        snapshot_review_summary_output=args.snapshot_review_summary_output,
        manual_evidence_input=args.manual_evidence_input,
        evidence_composed_output=args.evidence_composed_output,
        evidence_compose_conflicts_output=args.evidence_compose_conflicts_output,
        evidence_compose_summary_output=args.evidence_compose_summary_output,
        evidence_registry_output=args.evidence_registry_output,
        evidence_backlog_output=args.evidence_backlog_output,
        evidence_proposed_updates_output=args.evidence_proposed_updates_output,
        evidence_summary_output=args.evidence_summary_output,
        evidence_apply_registry_output=args.evidence_apply_registry_output,
        evidence_applied_master_output=args.evidence_applied_master_output,
        evidence_apply_summary_output=args.evidence_apply_summary_output,
        as_of_date=args.as_of_date,
        allow_network=args.allow_network,
        sec_user_agent=args.sec_user_agent,
        identity_preflight=args.identity_preflight,
        review_policy=args.review_policy,
        manual_review_input=args.manual_review_input,
        auto_review_output=args.auto_review_output,
        resolved_review_output=args.resolved_review_output,
        refresh_summary_output=args.refresh_summary_output,
        run_downstream=args.run_downstream,
        downstream_stages=args.downstream_stage,
        watchlist_input=args.watchlist_input,
    )


if __name__ == "__main__":
    main()
