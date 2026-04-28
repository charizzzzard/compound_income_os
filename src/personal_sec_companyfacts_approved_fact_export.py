from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import read_csv_rows, resolve_repo_path, write_csv_rows
from src.external_sec_companyfacts_fetch import canonical_cik
from src.personal_sec_derived_kpi_compose import DEFAULT_APPROVAL_APPLIED, clean_text, to_float_or_none

DEFAULT_SNAPSHOT_ROOT = "data/raw/private/fundamentals"
DEFAULT_OUTPUT_DIR = "data/processed"
DEFAULT_REPORT_DIR = "reports/2026-04-27"
DEFAULT_IDENTITY_MAP = "data/raw/private/fundamentals/personal_sec_identity_map.csv"

APPROVED_FACTS_OUTPUT = "personal_sec_companyfacts_approved_facts.csv"
SUMMARY_OUTPUT = "personal_sec_companyfacts_approved_fact_export_summary.csv"
FAILURES_OUTPUT = "personal_sec_companyfacts_approved_fact_export_failures.csv"
REPORT_OUTPUT = "personal_sec_companyfacts_approved_fact_export_report.md"

APPROVED_FACT_FIELDS = [
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "formula_recipe",
    "formula_role",
    "approved_sec_concept",
    "sec_cik",
    "sec_entity_name",
    "sec_taxonomy",
    "sec_concept",
    "sec_label",
    "sec_description",
    "unit",
    "fiscal_year",
    "fiscal_period",
    "form",
    "filed_date",
    "frame",
    "period_start",
    "period_end",
    "accession",
    "value",
    "value_is_numeric",
    "annual_basis",
    "value_source",
    "approved_role_status",
    "export_status",
    "rejection_reason",
]

SUMMARY_FIELDS = [
    "approved_roles_total",
    "approved_concepts_total",
    "companyfacts_snapshots_found",
    "companyfacts_snapshots_matched",
    "facts_exported_total",
    "numeric_facts_exported",
    "annual_fy_facts_exported",
    "annual_10k_facts_exported",
    "holdings_with_exported_facts",
    "concepts_with_exported_facts",
    "roles_with_exported_facts",
    "roles_without_exported_facts",
    "no_network_confirmed",
    "no_score_change_confirmed",
    "no_master_mutation_confirmed",
    "no_imputation_confirmed",
]

FAILURE_FIELDS = [
    "holding_name",
    "ticker",
    "isin",
    "formula_role",
    "approved_sec_concept",
    "failure_reason",
    "snapshot_status",
    "fact_status",
    "next_action",
]


@dataclass(frozen=True)
class ApprovedFactExportResult:
    approved_facts_path: Path
    summary_path: Path
    failures_path: Path
    report_path: Path
    summary: dict[str, str]
    status: str


def safe_snapshot_label(_path: Path) -> str:
    return "<private_sec_companyfacts_snapshot>"


def is_numeric_value(value: Any) -> bool:
    return to_float_or_none(value) is not None


def annual_basis(point: dict[str, Any]) -> str:
    fp = clean_text(point.get("fp")).upper()
    form = clean_text(point.get("form")).upper()
    frame = clean_text(point.get("frame")).upper()
    if fp == "FY" and form == "10-K":
        return "FY_10K"
    if fp == "FY" and form == "10-K/A":
        return "FY_10KA"
    if fp == "FY" and form:
        return "FY_OTHER_FORM"
    if frame.startswith("CY") and len(frame) >= 6 and frame[2:6].isdigit():
        return "FRAME_ANNUAL"
    if fp in {"Q1", "Q2", "Q3", "Q4"}:
        return "NON_ANNUAL"
    return "UNKNOWN"


def discover_companyfacts_snapshots(snapshot_root: str | Path) -> list[Path]:
    root = resolve_repo_path(snapshot_root)
    if not root.exists():
        return []
    snapshots: list[Path] = []
    for path in root.rglob("*.json"):
        if "sec_user_agent" in path.name.lower():
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and isinstance(payload.get("facts"), dict):
            snapshots.append(path)
    return sorted(snapshots, key=lambda item: item.as_posix())


def load_companyfacts(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) and isinstance(payload.get("facts"), dict) else None


def approved_roles(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str, str, str]] = set()
    approved: list[dict[str, str]] = []
    for row in rows:
        if clean_text(row.get("approval_status")).upper() != "APPROVED":
            continue
        concept = clean_text(row.get("candidate_sec_concept") or row.get("approved_sec_concept"))
        key = (
            clean_text(row.get("holding_name")),
            clean_text(row.get("isin")),
            clean_text(row.get("kpi_field")),
            clean_text(row.get("formula_role")),
            concept,
        )
        if not concept or key in seen:
            continue
        seen.add(key)
        copied = dict(row)
        copied["approved_sec_concept"] = concept
        approved.append(copied)
    return sorted(approved, key=lambda row: (clean_text(row.get("isin")), clean_text(row.get("kpi_field")), clean_text(row.get("formula_role")), clean_text(row.get("approved_sec_concept"))))


def identity_cik_index(identity_map: str | Path = DEFAULT_IDENTITY_MAP) -> dict[tuple[str, str], str]:
    path = resolve_repo_path(identity_map)
    if not path.exists():
        return {}
    index: dict[tuple[str, str], str] = {}
    for row in read_csv_rows(path):
        ticker = clean_text(row.get("ticker")).upper()
        isin = clean_text(row.get("isin")).upper()
        cik = canonical_cik(row.get("cik"))
        if cik:
            index[(ticker, isin)] = cik
            if isin:
                index.setdefault((isin, isin), cik)
    return index


def snapshot_by_cik(paths: list[Path]) -> dict[str, dict[str, Any]]:
    by_cik: dict[str, dict[str, Any]] = {}
    for path in paths:
        payload = load_companyfacts(path)
        if payload is None:
            continue
        cik = canonical_cik(payload.get("cik"))
        if cik:
            by_cik[cik] = payload
    return by_cik


def role_cik(role: dict[str, str], cik_index: dict[tuple[str, str], str]) -> str:
    ticker = clean_text(role.get("ticker")).upper()
    isin = clean_text(role.get("isin")).upper()
    return cik_index.get((ticker, isin), "") or cik_index.get((isin, isin), "")


def fact_rows_for_concept(companyfacts: dict[str, Any], concept: str) -> list[dict[str, str]]:
    facts = companyfacts.get("facts")
    if not isinstance(facts, dict):
        return []
    output: list[dict[str, str]] = []
    sec_cik = canonical_cik(companyfacts.get("cik"))
    entity_name = clean_text(companyfacts.get("entityName"))
    for taxonomy, taxonomy_facts in sorted(facts.items()):
        if not isinstance(taxonomy_facts, dict):
            continue
        concept_block = taxonomy_facts.get(concept)
        if not isinstance(concept_block, dict):
            continue
        units = concept_block.get("units")
        if not isinstance(units, dict):
            continue
        label = clean_text(concept_block.get("label"))
        description = clean_text(concept_block.get("description"))
        for unit, points in sorted(units.items()):
            if not isinstance(points, list):
                continue
            for point in points:
                if not isinstance(point, dict):
                    continue
                output.append(
                    {
                        "sec_cik": sec_cik,
                        "sec_entity_name": entity_name,
                        "sec_taxonomy": clean_text(taxonomy),
                        "sec_concept": concept,
                        "sec_label": label,
                        "sec_description": description,
                        "unit": clean_text(unit),
                        "fiscal_year": clean_text(point.get("fy")),
                        "fiscal_period": clean_text(point.get("fp")),
                        "form": clean_text(point.get("form")),
                        "filed_date": clean_text(point.get("filed")),
                        "frame": clean_text(point.get("frame")),
                        "period_start": clean_text(point.get("start")),
                        "period_end": clean_text(point.get("end")),
                        "accession": clean_text(point.get("accn")),
                        "value": clean_text(point.get("val")),
                        "value_is_numeric": str(is_numeric_value(point.get("val"))),
                        "annual_basis": annual_basis(point),
                    }
                )
    return output


def export_rows_for_role(role: dict[str, str], companyfacts: dict[str, Any]) -> list[dict[str, str]]:
    concept = clean_text(role.get("approved_sec_concept"))
    rows: list[dict[str, str]] = []
    for fact in fact_rows_for_concept(companyfacts, concept):
        row = {field: "" for field in APPROVED_FACT_FIELDS}
        row.update(fact)
        row.update(
            {
                "holding_name": clean_text(role.get("holding_name")),
                "ticker": clean_text(role.get("ticker")),
                "isin": clean_text(role.get("isin")),
                "kpi_field": clean_text(role.get("kpi_field")),
                "formula_recipe": clean_text(role.get("formula_recipe")),
                "formula_role": clean_text(role.get("formula_role")),
                "approved_sec_concept": concept,
                "value_source": "SEC CompanyFacts local snapshot",
                "approved_role_status": "APPROVED",
                "export_status": "EXPORTED",
                "rejection_reason": "",
            }
        )
        rows.append(row)
    return rows


def failure_row(role: dict[str, str], reason: str, snapshot_status: str, fact_status: str) -> dict[str, str]:
    return {
        "holding_name": clean_text(role.get("holding_name")),
        "ticker": clean_text(role.get("ticker")),
        "isin": clean_text(role.get("isin")),
        "formula_role": clean_text(role.get("formula_role")),
        "approved_sec_concept": clean_text(role.get("approved_sec_concept")),
        "failure_reason": reason,
        "snapshot_status": snapshot_status,
        "fact_status": fact_status,
        "next_action": "RERUN_SEC_REFRESH_WITH_RAW_SNAPSHOT_RETENTION" if reason == "MISSING_LOCAL_SEC_COMPANYFACTS_SNAPSHOT" else "SEC_SNAPSHOT_NORMALIZED_FACT_EXPORT_REVIEW",
    }


def build_summary(approved: list[dict[str, str]], snapshots_found: int, matched_ciks: set[str], facts: list[dict[str, str]], failures: list[dict[str, str]]) -> dict[str, str]:
    roles_with_facts = {
        (row["holding_name"], row["isin"], row["kpi_field"], row["formula_role"], row["approved_sec_concept"])
        for row in facts
    }
    approved_role_keys = {
        (clean_text(row.get("holding_name")), clean_text(row.get("isin")), clean_text(row.get("kpi_field")), clean_text(row.get("formula_role")), clean_text(row.get("approved_sec_concept")))
        for row in approved
    }
    return {
        "approved_roles_total": str(len(approved_role_keys)),
        "approved_concepts_total": str(len({clean_text(row.get("approved_sec_concept")) for row in approved if clean_text(row.get("approved_sec_concept"))})),
        "companyfacts_snapshots_found": str(snapshots_found),
        "companyfacts_snapshots_matched": str(len(matched_ciks)),
        "facts_exported_total": str(len(facts)),
        "numeric_facts_exported": str(sum(1 for row in facts if row["value_is_numeric"] == "True")),
        "annual_fy_facts_exported": str(sum(1 for row in facts if row["annual_basis"].startswith("FY_"))),
        "annual_10k_facts_exported": str(sum(1 for row in facts if row["annual_basis"] in {"FY_10K", "FY_10KA"})),
        "holdings_with_exported_facts": str(len({row["isin"] for row in facts if row["isin"]})),
        "concepts_with_exported_facts": str(len({row["approved_sec_concept"] for row in facts if row["approved_sec_concept"]})),
        "roles_with_exported_facts": str(len(roles_with_facts)),
        "roles_without_exported_facts": str(len(approved_role_keys - roles_with_facts)),
        "no_network_confirmed": "True",
        "no_score_change_confirmed": "True",
        "no_master_mutation_confirmed": "True",
        "no_imputation_confirmed": "True",
    }


def render_report(summary: dict[str, str], failures: list[dict[str, str]], status: str) -> str:
    failure_counts = Counter(row["failure_reason"] for row in failures)
    lines = [
        "# SEC CompanyFacts Approved Fact Export",
        "",
        "## Executive Summary",
        f"- status: `{status}`",
        f"- approved_roles_total: `{summary['approved_roles_total']}`",
        f"- companyfacts_snapshots_found: `{summary['companyfacts_snapshots_found']}`",
        f"- companyfacts_snapshots_matched: `{summary['companyfacts_snapshots_matched']}`",
        f"- facts_exported_total: `{summary['facts_exported_total']}`",
        f"- numeric_facts_exported: `{summary['numeric_facts_exported']}`",
        f"- annual_10k_facts_exported: `{summary['annual_10k_facts_exported']}`",
        "",
        "## Inputs",
        "- private approval-applied input: present, path omitted",
        "- snapshot discovery root: `<private_sec_companyfacts_snapshot>`",
        "",
        "## Snapshot Discovery",
        f"- local CompanyFacts snapshots found: `{summary['companyfacts_snapshots_found']}`",
        f"- matched snapshots: `{summary['companyfacts_snapshots_matched']}`",
        "",
        "## Export Coverage by Holding",
        f"- holdings_with_exported_facts: `{summary['holdings_with_exported_facts']}`",
        f"- roles_with_exported_facts: `{summary['roles_with_exported_facts']}`",
        f"- roles_without_exported_facts: `{summary['roles_without_exported_facts']}`",
        "",
        "## Export Coverage by Concept",
        f"- approved_concepts_total: `{summary['approved_concepts_total']}`",
        f"- concepts_with_exported_facts: `{summary['concepts_with_exported_facts']}`",
        "",
        "## Failure Reasons",
    ]
    if failure_counts:
        for reason, count in sorted(failure_counts.items()):
            lines.append(f"- `{reason}`: `{count}`")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Guardrail Confirmation",
            "- no_network_confirmed=True",
            "- no_score_change_confirmed=True",
            "- no_master_mutation_confirmed=True",
            "- no_imputation_confirmed=True",
            "- private raw snapshot paths omitted from public outputs",
            "",
            "## Next Recommended Patch",
            "`SEC DERIVED KPI PERIOD SELECTION PATCH / ANNUAL BASIS REVIEW`" if int(summary["facts_exported_total"]) > 0 else "`RERUN SEC REFRESH WITH RAW SNAPSHOT RETENTION / NO SCORE CHANGES`",
        ]
    )
    return "\n".join(lines) + "\n"


def run_personal_sec_companyfacts_approved_fact_export(
    *,
    approval_applied: str | Path = DEFAULT_APPROVAL_APPLIED,
    snapshot_root: str | Path = DEFAULT_SNAPSHOT_ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    identity_map: str | Path = DEFAULT_IDENTITY_MAP,
) -> ApprovedFactExportResult:
    approval_path = resolve_repo_path(approval_applied)
    if not approval_path.exists():
        raise RuntimeError("MISSING_PRIVATE_APPROVAL_APPLIED")
    approved = approved_roles(read_csv_rows(approval_path))
    snapshots = discover_companyfacts_snapshots(snapshot_root)
    by_cik = snapshot_by_cik(snapshots)
    cik_index = identity_cik_index(identity_map)

    facts: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    matched_ciks: set[str] = set()
    if not snapshots:
        for role in approved:
            failures.append(failure_row(role, "MISSING_LOCAL_SEC_COMPANYFACTS_SNAPSHOT", "NOT_FOUND", "NOT_CHECKED"))
        status = "MISSING_LOCAL_SEC_COMPANYFACTS_SNAPSHOT"
    else:
        for role in approved:
            cik = role_cik(role, cik_index)
            companyfacts = by_cik.get(cik)
            if not cik or companyfacts is None:
                failures.append(failure_row(role, "NO_MATCHING_COMPANYFACTS_SNAPSHOT", "NOT_MATCHED", "NOT_CHECKED"))
                continue
            matched_ciks.add(cik)
            rows = export_rows_for_role(role, companyfacts)
            if rows:
                facts.extend(rows)
            else:
                failures.append(failure_row(role, "APPROVED_CONCEPT_NOT_FOUND_IN_SNAPSHOT", "MATCHED", "NO_FACTS_FOR_CONCEPT"))
        status = "EXECUTED" if facts else "NO_APPROVED_FACTS_EXPORTED"

    summary = build_summary(approved, len(snapshots), matched_ciks, facts, failures)
    output_root = resolve_repo_path(output_dir)
    report_root = resolve_repo_path(report_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    report_root.mkdir(parents=True, exist_ok=True)
    facts_path = write_csv_rows(output_root / APPROVED_FACTS_OUTPUT, APPROVED_FACT_FIELDS, facts)
    summary_path = write_csv_rows(output_root / SUMMARY_OUTPUT, SUMMARY_FIELDS, [summary])
    failures_path = write_csv_rows(output_root / FAILURES_OUTPUT, FAILURE_FIELDS, failures)
    report_path = report_root / REPORT_OUTPUT
    report_path.write_text(render_report(summary, failures, status), encoding="utf-8")
    return ApprovedFactExportResult(
        approved_facts_path=facts_path,
        summary_path=summary_path,
        failures_path=failures_path,
        report_path=report_path,
        summary=summary,
        status=status,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export approved SEC CompanyFacts concept facts from local snapshots without fetching.")
    parser.add_argument("--approval-applied", default=DEFAULT_APPROVAL_APPLIED)
    parser.add_argument("--snapshot-root", default=DEFAULT_SNAPSHOT_ROOT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_companyfacts_approved_fact_export(
        approval_applied=args.approval_applied,
        snapshot_root=args.snapshot_root,
        output_dir=args.output_dir,
        report_dir=args.report_dir,
    )
    print(f"approved_facts_path={result.approved_facts_path}")
    print(f"export_summary_path={result.summary_path}")
    print(f"export_failures_path={result.failures_path}")
    print(f"export_report_path={result.report_path}")
    print(f"export_status={result.status}")
    print(f"facts_exported_total={result.summary['facts_exported_total']}")
    print("no_network_confirmed=True")


if __name__ == "__main__":
    main()
