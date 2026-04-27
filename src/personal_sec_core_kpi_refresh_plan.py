from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, safe_upper, write_csv_rows

DEFAULT_CORE_CLOSURE_QUEUE_INPUT = "data/processed/personal_core_kpi_closure_queue.csv"
DEFAULT_SEC_SCOPE_REVIEW_INPUT = "data/processed/personal_sec_scope_review.csv"
DEFAULT_SEC_IDENTITY_MAP_INPUT = "data/raw/private/fundamentals/personal_sec_identity_map.csv"
DEFAULT_SEC_IDENTITY_APPLY_INPUT = "data/processed/personal_sec_identity_apply_changes.csv"
DEFAULT_PLAN_OUTPUT = "data/processed/personal_sec_core_kpi_refresh_plan.csv"
DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_sec_core_kpi_refresh_plan_summary.csv"
DEFAULT_REPORT_OUTPUT = f"reports/{date.today().isoformat()}/personal_sec_core_kpi_refresh_plan_report.md"

CORE_KPI_FACT_MAPPING = {
    "revenue_cagr_5y": "RevenueFromContractWithCustomerExcludingAssessedTax; Revenues; SalesRevenueNet",
    "eps_cagr_5y": "EarningsPerShareDiluted",
    "gross_margin": "GrossProfit; RevenueFromContractWithCustomerExcludingAssessedTax; Revenues; SalesRevenueNet",
    "operating_margin": "OperatingIncomeLoss; RevenueFromContractWithCustomerExcludingAssessedTax; Revenues; SalesRevenueNet",
    "share_count_cagr_5y": "WeightedAverageNumberOfDilutedSharesOutstanding",
}

PLAN_FIELDS = [
    "ticker",
    "isin",
    "company_name",
    "company_type_profile",
    "missing_core_kpis",
    "missing_core_kpi_count",
    "core_kpi_closure_status",
    "core_kpi_closure_reason_codes",
    "candidate_sec_fact_tags",
    "sec_identity_status",
    "sec_refresh_plan_status",
    "network_required",
    "allow_network_required_for_future_refresh",
    "sec_user_agent_required",
    "kpi_to_sec_fact_mapping_status",
    "mapping_review_required",
    "value_fetch_performed",
    "evidence_apply_performed",
    "master_mutation_performed",
    "score_mutation_performed",
    "reason_codes",
]

SUMMARY_FIELDS = [
    "affected_rows_count",
    "ready_for_explicit_sec_refresh_count",
    "identity_missing_count",
    "identity_review_count",
    "mapping_review_required_count",
    "not_ready_count",
    "network_performed",
    "value_fetch_performed",
    "evidence_apply_performed",
    "master_mutation_performed",
    "score_mutation_performed",
    "reason_codes",
]


@dataclass(frozen=True)
class SecCoreKpiRefreshPlanResult:
    plan_output: Path
    summary_output: Path
    report_output: Path
    plan_rows: list[dict[str, str]]
    summary_rows: list[dict[str, str]]
    warnings: tuple[str, ...]


def safe_display_path(path_value: str) -> str:
    normalized = str(path_value).replace("\\", "/")
    if "data/raw/private" in normalized:
        return "<private_path>"
    return path_value


def optional_csv_rows(path_value: str, label: str) -> tuple[list[dict[str, str]], bool, list[str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return [], False, [f"missing_input={label}:{safe_display_path(path_value)}"]
    return read_csv_rows(path), True, []


def bool_text(value: bool) -> str:
    return "True" if value else "False"


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def joined(values: set[str] | list[str] | tuple[str, ...]) -> str:
    return ";".join(sorted(value for value in values if value))


def split_list(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").replace(",", ";").split(";") if item.strip()]


def identity_keys(row: dict[str, str]) -> tuple[tuple[str, str], ...]:
    isin = str(row.get("isin", "") or row.get("original_isin", "") or "").strip().upper()
    ticker = str(
        row.get("ticker", "")
        or row.get("original_ticker", "")
        or row.get("current_ticker", "")
        or row.get("reviewed_canonical_ticker", "")
        or ""
    ).strip().upper()
    keys: list[tuple[str, str]] = []
    if isin:
        keys.append(("isin", isin))
    if ticker and not isin:
        keys.append(("ticker", ticker))
    return tuple(keys)


def row_enabled(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def row_approved(value: Any) -> bool:
    return safe_upper(value) in {"APPROVED", "REVIEWED_APPROVE", "APPROVE", "APPROVED_IDENTITY"}


def has_cik(row: dict[str, str]) -> bool:
    return bool(str(row.get("cik", "") or row.get("reviewed_cik", "") or "").strip())


def build_approved_identity_keys(
    *,
    scope_rows: list[dict[str, str]],
    identity_map_rows: list[dict[str, str]],
    identity_apply_rows: list[dict[str, str]],
) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for row in scope_rows:
        if row_enabled(row.get("reviewed_enabled", "")) and has_cik(row) and row_approved(row.get("review_status", "")):
            keys.update(identity_keys(row))
    for row in identity_map_rows:
        if row_enabled(row.get("enabled", "")) and has_cik(row):
            keys.update(identity_keys(row))
    for row in identity_apply_rows:
        if has_cik(row) and safe_upper(row.get("projection_status", "")) not in {"REJECTED", "INVALID"}:
            keys.update(identity_keys(row))
    return keys


def classify_identity_status(row: dict[str, str], approved_keys: set[tuple[str, str]], identity_artifacts_present: bool) -> tuple[str, set[str]]:
    keys = identity_keys(row)
    if keys and any(key in approved_keys for key in keys):
        return "APPROVED_IDENTITY", {"SEC_IDENTITY_AVAILABLE"}
    if not identity_artifacts_present:
        return "UNKNOWN", {"SEC_IDENTITY_REVIEW_REQUIRED"}
    return "IDENTITY_MISSING", {"SEC_IDENTITY_MISSING"}


def mapping_for_kpis(kpis: list[str]) -> tuple[str, str, bool, set[str]]:
    if not kpis:
        return "", "NOT_APPLICABLE", False, set()
    mapped = [kpi for kpi in kpis if kpi in CORE_KPI_FACT_MAPPING]
    missing = [kpi for kpi in kpis if kpi not in CORE_KPI_FACT_MAPPING]
    facts = sorted({fact for kpi in mapped for fact in split_list(CORE_KPI_FACT_MAPPING[kpi])})
    if not mapped:
        return "", "UNKNOWN", True, {"SEC_FACT_MAPPING_MISSING", "SEC_FACT_MAPPING_REVIEW_REQUIRED"}
    if missing:
        return "; ".join(facts), "PARTIAL", True, {"SEC_FACT_MAPPING_MISSING", "SEC_FACT_MAPPING_REVIEW_REQUIRED"}
    return "; ".join(facts), "MAPPED", False, set()


def plan_status_for(*, profile: str, identity_status: str, mapping_status: str, mapping_review_required: bool) -> str:
    if safe_upper(profile) != "STANDARD":
        return "NOT_APPLICABLE"
    if identity_status == "IDENTITY_MISSING":
        return "REVIEW_IDENTITY"
    if identity_status in {"IDENTITY_REVIEW", "UNKNOWN"}:
        return "REVIEW_IDENTITY"
    if mapping_review_required or mapping_status in {"UNKNOWN", "REVIEW", "PARTIAL"}:
        return "MAPPING_REVIEW_REQUIRED"
    if identity_status == "APPROVED_IDENTITY" and mapping_status == "MAPPED":
        return "READY_FOR_EXPLICIT_SEC_REFRESH"
    return "NOT_READY"


def build_plan(
    *,
    closure_rows: list[dict[str, str]],
    scope_rows: list[dict[str, str]],
    identity_map_rows: list[dict[str, str]],
    identity_apply_rows: list[dict[str, str]],
    identity_artifacts_present: bool,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    approved_keys = build_approved_identity_keys(
        scope_rows=scope_rows,
        identity_map_rows=identity_map_rows,
        identity_apply_rows=identity_apply_rows,
    )
    plan_rows: list[dict[str, str]] = []
    for row in sorted(closure_rows, key=lambda item: (str(item.get("isin", "")), str(item.get("ticker", "")))):
        profile = row.get("company_type_profile", "")
        missing_kpis = split_list(row.get("missing_core_kpis", ""))
        reasons = {
            "NO_NETWORK_BY_DEFAULT",
            "SEC_USER_AGENT_REQUIRED_FOR_FUTURE_REFRESH",
            "ALLOW_NETWORK_REQUIRED_FOR_FUTURE_REFRESH",
            "NO_VALUE_FETCH",
            "NO_EVIDENCE_APPLY",
            "NO_MASTER_MUTATION",
            "NO_SCORE_MUTATION",
        }
        if safe_upper(profile) != "STANDARD":
            reasons.add("PROFILE_NOT_STANDARD")
            identity_status = "NOT_SEC_ELIGIBLE"
            identity_reasons: set[str] = set()
        else:
            reasons.add("CORE_KPI_MISSING")
            identity_status, identity_reasons = classify_identity_status(row, approved_keys, identity_artifacts_present)
        candidate_facts, mapping_status, mapping_review_required, mapping_reasons = mapping_for_kpis(missing_kpis)
        reasons.update(identity_reasons)
        reasons.update(mapping_reasons)
        status = plan_status_for(
            profile=profile,
            identity_status=identity_status,
            mapping_status=mapping_status,
            mapping_review_required=mapping_review_required,
        )
        if status == "READY_FOR_EXPLICIT_SEC_REFRESH":
            reasons.add("READY_FOR_EXPLICIT_SEC_REFRESH")
        plan_rows.append(
            {
                "ticker": row.get("ticker", ""),
                "isin": row.get("isin", ""),
                "company_name": row.get("company_name", ""),
                "company_type_profile": profile,
                "missing_core_kpis": "; ".join(missing_kpis),
                "missing_core_kpi_count": str(len(missing_kpis)),
                "core_kpi_closure_status": row.get("core_kpi_closure_status", ""),
                "core_kpi_closure_reason_codes": row.get("reason_code", ""),
                "candidate_sec_fact_tags": candidate_facts,
                "sec_identity_status": identity_status,
                "sec_refresh_plan_status": status,
                "network_required": "False",
                "allow_network_required_for_future_refresh": "yes" if status == "READY_FOR_EXPLICIT_SEC_REFRESH" else "no",
                "sec_user_agent_required": "yes" if status == "READY_FOR_EXPLICIT_SEC_REFRESH" else "no",
                "kpi_to_sec_fact_mapping_status": mapping_status,
                "mapping_review_required": yes_no(mapping_review_required),
                "value_fetch_performed": "False",
                "evidence_apply_performed": "False",
                "master_mutation_performed": "False",
                "score_mutation_performed": "False",
                "reason_codes": joined(reasons),
            }
        )

    status_counts = Counter(row["sec_refresh_plan_status"] for row in plan_rows)
    identity_counts = Counter(row["sec_identity_status"] for row in plan_rows)
    mapping_review_count = sum(1 for row in plan_rows if row["mapping_review_required"] == "yes")
    reason_union: set[str] = set()
    for row in plan_rows:
        reason_union.update(split_list(row.get("reason_codes", "")))
    if not plan_rows:
        reason_union.add("CORE_KPI_MISSING")
    summary_rows = [
        {
            "affected_rows_count": str(len(plan_rows)),
            "ready_for_explicit_sec_refresh_count": str(status_counts.get("READY_FOR_EXPLICIT_SEC_REFRESH", 0)),
            "identity_missing_count": str(identity_counts.get("IDENTITY_MISSING", 0)),
            "identity_review_count": str(identity_counts.get("IDENTITY_REVIEW", 0) + identity_counts.get("UNKNOWN", 0)),
            "mapping_review_required_count": str(mapping_review_count),
            "not_ready_count": str(len(plan_rows) - status_counts.get("READY_FOR_EXPLICIT_SEC_REFRESH", 0)),
            "network_performed": "False",
            "value_fetch_performed": "False",
            "evidence_apply_performed": "False",
            "master_mutation_performed": "False",
            "score_mutation_performed": "False",
            "reason_codes": joined(reason_union),
        }
    ]
    return plan_rows, summary_rows


def render_report(
    *,
    plan_rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
    input_paths: dict[str, str],
    warnings: tuple[str, ...],
) -> str:
    summary = summary_rows[0] if summary_rows else {}
    reason_counts = Counter(reason for row in plan_rows for reason in split_list(row.get("reason_codes", "")))
    lines = [
        "# Personal SEC Core KPI Refresh Plan Report",
        "",
        "## 1. Executive Summary",
        f"- Affected rows: `{summary.get('affected_rows_count', '0')}`",
        f"- Ready for explicit SEC refresh: `{summary.get('ready_for_explicit_sec_refresh_count', '0')}`",
        f"- Mapping review required: `{summary.get('mapping_review_required_count', '0')}`",
        f"- Network performed: `{summary.get('network_performed', 'False')}`",
        f"- Value fetch performed: `{summary.get('value_fetch_performed', 'False')}`",
        "",
        "## 2. Input Artifacts",
    ]
    for label, path_value in sorted(input_paths.items()):
        lines.append(f"- `{label}`: `{safe_display_path(path_value)}`")
    lines.extend(
        [
            "",
            "## 3. Core KPI Gaps in Scope",
            "| ticker | isin | company_name | missing_core_kpis |",
            "| --- | --- | --- | --- |",
        ]
    )
    if plan_rows:
        for row in plan_rows:
            lines.append(f"| {row['ticker']} | {row['isin']} | {row['company_name']} | {row['missing_core_kpis']} |")
    else:
        lines.append("| none |  |  |  |")
    lines.extend(
        [
            "",
            "## 4. SEC Identity Readiness",
            "| ticker | sec_identity_status | sec_refresh_plan_status |",
            "| --- | --- | --- |",
        ]
    )
    for row in plan_rows:
        lines.append(f"| {row['ticker']} | `{row['sec_identity_status']}` | `{row['sec_refresh_plan_status']}` |")
    lines.extend(
        [
            "",
            "## 5. KPI-to-SEC Mapping Readiness",
            "| ticker | mapping_status | mapping_review_required | candidate_fact_tags |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in plan_rows:
        lines.append(
            f"| {row['ticker']} | `{row['kpi_to_sec_fact_mapping_status']}` | `{row['mapping_review_required']}` | `{row['candidate_sec_fact_tags']}` |"
        )
    lines.extend(
        [
            "",
            "## 6. Refresh Plan",
            "- Rows marked `READY_FOR_EXPLICIT_SEC_REFRESH` have approved identities and mapped KPI fact candidates.",
            "- Rows marked `MAPPING_REVIEW_REQUIRED` need mapping review before any explicit SEC refresh.",
            "- This report is a plan only and does not fetch or apply values.",
            "",
            "## 7. Network Guardrail",
            "- `network_performed=False`.",
            "- No `--allow-network` path was executed.",
            "- No SEC CompanyFacts HTTP request was made.",
            "",
            "## 8. No-Value-Change Guardrail",
            "- `value_fetch_performed=False`.",
            "- `evidence_apply_performed=False`.",
            "- `master_mutation_performed=False`.",
            "- `score_mutation_performed=False`.",
            "",
            "## 9. Future Explicit Refresh Requirements",
            "- Approved SEC identities must be present.",
            "- A SEC user agent is required.",
            "- A future refresh must use an explicit network gate.",
            "- Evidence review/apply must remain a separate step.",
            "",
            "## 10. Readiness Impact",
            "- `REVIEW_CORE_DATA` is not resolved by this plan.",
            "- Plan-ready status is visible in `personal_sec_core_kpi_refresh_plan_summary.csv`.",
            "",
            "## 11. Remaining Blockers",
            "- `MISSING_VALUATION_REQUIRED`",
            "- `MISSING_DIVIDEND_FCF_REQUIRED`",
            "- `PROVENANCE_INCOMPLETE`",
            "- `REVIEW_CORE_DATA`",
            "- `WATCHLIST_SAMPLE_INPUT`",
            "- `WATCHLIST_REVIEW_OR_MISSING_DATA`",
            "",
            "## 12. Recommended Next Patch",
            "`PATCH / SEC REFRESH COMMAND PREFLIGHT / EXPLICIT NETWORK GATES / NO FETCH BY DEFAULT`",
            "",
            "## Reason Code Counts",
        ]
    )
    for reason, count in sorted(reason_counts.items()):
        lines.append(f"- `{reason}`: {count}")
    if warnings:
        lines.extend(["", "## Warnings"])
        for warning in warnings:
            lines.append(f"- `{warning}`")
    lines.append("")
    return "\n".join(lines)


def run_personal_sec_core_kpi_refresh_plan(
    *,
    core_closure_queue_input: str = DEFAULT_CORE_CLOSURE_QUEUE_INPUT,
    sec_scope_review_input: str = DEFAULT_SEC_SCOPE_REVIEW_INPUT,
    sec_identity_map_input: str = DEFAULT_SEC_IDENTITY_MAP_INPUT,
    sec_identity_apply_input: str = DEFAULT_SEC_IDENTITY_APPLY_INPUT,
    plan_output: str = DEFAULT_PLAN_OUTPUT,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str = DEFAULT_REPORT_OUTPUT,
) -> SecCoreKpiRefreshPlanResult:
    warnings: list[str] = []
    closure_rows, closure_present, closure_warnings = optional_csv_rows(core_closure_queue_input, "core_closure_queue")
    scope_rows, scope_present, scope_warnings = optional_csv_rows(sec_scope_review_input, "sec_scope_review")
    identity_map_rows, identity_map_present, identity_map_warnings = optional_csv_rows(sec_identity_map_input, "sec_identity_map")
    identity_apply_rows, identity_apply_present, identity_apply_warnings = optional_csv_rows(sec_identity_apply_input, "sec_identity_apply")
    warnings.extend(closure_warnings)
    warnings.extend(scope_warnings)
    warnings.extend(identity_map_warnings)
    warnings.extend(identity_apply_warnings)
    if not closure_present:
        closure_rows = []
    identity_artifacts_present = scope_present or identity_map_present or identity_apply_present
    plan_rows, summary_rows = build_plan(
        closure_rows=closure_rows,
        scope_rows=scope_rows,
        identity_map_rows=identity_map_rows,
        identity_apply_rows=identity_apply_rows,
        identity_artifacts_present=identity_artifacts_present,
    )
    plan_path = write_csv_rows(plan_output, PLAN_FIELDS, plan_rows)
    summary_path = write_csv_rows(summary_output, SUMMARY_FIELDS, summary_rows)
    report_path = resolve_repo_path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    input_paths = {
        "core_closure_queue": core_closure_queue_input,
        "sec_scope_review": sec_scope_review_input,
        "sec_identity_map": sec_identity_map_input,
        "sec_identity_apply": sec_identity_apply_input,
        "plan_output": plan_output,
        "summary_output": summary_output,
    }
    report_path.write_text(
        render_report(
            plan_rows=plan_rows,
            summary_rows=summary_rows,
            input_paths=input_paths,
            warnings=tuple(warnings),
        ),
        encoding="utf-8",
    )
    return SecCoreKpiRefreshPlanResult(
        plan_output=plan_path,
        summary_output=summary_path,
        report_output=report_path,
        plan_rows=plan_rows,
        summary_rows=summary_rows,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a no-network SEC core KPI refresh plan.")
    parser.add_argument("--core-closure-queue-input", default=DEFAULT_CORE_CLOSURE_QUEUE_INPUT)
    parser.add_argument("--sec-scope-review-input", default=DEFAULT_SEC_SCOPE_REVIEW_INPUT)
    parser.add_argument("--sec-identity-map-input", default=DEFAULT_SEC_IDENTITY_MAP_INPUT)
    parser.add_argument("--sec-identity-apply-input", default=DEFAULT_SEC_IDENTITY_APPLY_INPUT)
    parser.add_argument("--plan-output", default=DEFAULT_PLAN_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_core_kpi_refresh_plan(
        core_closure_queue_input=args.core_closure_queue_input,
        sec_scope_review_input=args.sec_scope_review_input,
        sec_identity_map_input=args.sec_identity_map_input,
        sec_identity_apply_input=args.sec_identity_apply_input,
        plan_output=args.plan_output,
        summary_output=args.summary_output,
        report_output=args.report_output,
    )
    summary = result.summary_rows[0] if result.summary_rows else {}
    print(f"plan_output={result.plan_output}")
    print(f"summary_output={result.summary_output}")
    print(f"report_output={result.report_output}")
    print(f"affected_rows_count={summary.get('affected_rows_count', '0')}")
    print(f"ready_for_explicit_sec_refresh_count={summary.get('ready_for_explicit_sec_refresh_count', '0')}")
    print(f"network_performed={summary.get('network_performed', 'False')}")
    print(f"warnings_total={len(result.warnings)}")


if __name__ == "__main__":
    main()
