from __future__ import annotations

import csv
import json
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.common import ROOT, ensure_parent_dir, resolve_repo_path

HANDOFF_INDEX_OUTPUT = "data/processed/website_private_preview_handoff_index.csv"
RELEASE_SUMMARY_OUTPUT = "data/processed/website_private_preview_release_summary.csv"

ROUTE_QA_SUMMARY = "data/processed/website_private_preview_qa_summary.csv"
STATIC_BUILD_SUMMARY = "data/processed/website_static_build_package_summary.csv"
COPY_FREEZE_SUMMARY = "data/processed/website_private_preview_copy_freeze_summary.csv"

PUBLIC_SAMPLE_PAYLOAD = "website/compound-income-os-landing/public/demo/readiness_payload.sample.json"
READINESS_PAYLOAD = "data/processed/dashboard_readiness_payload.json"
READINESS_PANEL = "data/processed/dashboard_readiness_panel.csv"

WEBSITE_README = "website/compound-income-os-landing/README.md"
DEPLOYMENT_NOTES = "website/compound-income-os-landing/DEPLOYMENT_NOTES.md"
STRATEGY_REVIEW = "reports/2026-04-26/strategy_review_fundamentals_trust_scoring.md"

ROUTE_MATRIX_REPORT = "reports/2026-04-27/website_private_preview_route_matrix_report.md"
STATIC_BUILD_REPORT = "reports/2026-04-27/website_static_build_package_report.md"
COPY_FREEZE_REPORT = "reports/2026-04-27/website_private_preview_copy_freeze_report.md"

PAGES = (
    ("Home", "/", "A calmer way to run a long-term portfolio."),
    ("Workflow", "/workflow", "Six stages, one monthly cadence."),
    ("Evidence", "/evidence", "See what's covered. See what's missing."),
    ("Portfolio", "/portfolio", "Four sleeves. Clear rules. Long-term focus."),
    ("Dashboard", "/dashboard", "One local dashboard. Five KPI groups."),
    ("Manifesto", "/manifesto", "Built for people who think for the long run."),
    ("About alias", "/about", "Alias to Manifesto."),
)

SCREENSHOTS = (
    ("Home screenshot", "website/compound-income-os-landing/review_screenshots/01_home_wayfinder.png"),
    ("Workflow screenshot", "website/compound-income-os-landing/review_screenshots/02_workflow_page.png"),
    ("Evidence screenshot", "website/compound-income-os-landing/review_screenshots/03_evidence_page.png"),
    ("Portfolio screenshot", "website/compound-income-os-landing/review_screenshots/04_portfolio_page.png"),
    ("Dashboard screenshot", "website/compound-income-os-landing/review_screenshots/05_dashboard_page.png"),
    ("Manifesto screenshot", "website/compound-income-os-landing/review_screenshots/06_manifesto_page.png"),
)

QA_ARTIFACTS = (
    ("Route Matrix CSV", "data/processed/website_private_preview_route_matrix.csv"),
    ("CTA Matrix CSV", "data/processed/website_private_preview_cta_matrix.csv"),
    ("Copy Guardrails CSV", "data/processed/website_private_preview_copy_guardrails.csv"),
    ("Route QA Summary CSV", "data/processed/website_private_preview_qa_summary.csv"),
    ("Static Build QA CSV", "data/processed/website_static_build_package_qa.csv"),
    ("Static Build Summary CSV", "data/processed/website_static_build_package_summary.csv"),
    ("Copy Freeze Matrix CSV", "data/processed/website_private_preview_copy_freeze_matrix.csv"),
    ("Copy Freeze Summary CSV", "data/processed/website_private_preview_copy_freeze_summary.csv"),
    ("Route Matrix Report", ROUTE_MATRIX_REPORT),
    ("Static Build Report", STATIC_BUILD_REPORT),
    ("Copy Freeze Report", COPY_FREEZE_REPORT),
)

PAYLOADS = (
    ("Sanitized readiness sample payload", PUBLIC_SAMPLE_PAYLOAD),
    ("Dashboard readiness payload", READINESS_PAYLOAD),
    ("Dashboard readiness panel", READINESS_PANEL),
)

DOCS = (
    ("Website README", WEBSITE_README),
    ("Deployment Notes", DEPLOYMENT_NOTES),
    ("Strategy Review Report", STRATEGY_REVIEW),
)

GUARDRAILS = (
    ("No public deploy performed", "Public deployment remains blocked.", "PUBLIC_DEPLOY_FALSE"),
    ("No private data leak detected", "QA summaries report no private data leakage.", "NO_PRIVATE_DATA_LEAK"),
    ("No dummy claims detected", "QA summaries report no readiness or launch dummy claims.", "NO_DUMMY_CLAIMS"),
    ("No fake links detected", "CTA matrix reports no fake links.", "NO_FAKE_LINKS"),
    ("No forbidden action terms detected", "Copy guardrails report no CTA/display action-language violations.", "NO_ACTION_LANGUAGE"),
)

INDEX_FIELDS = (
    "item_type",
    "item_name",
    "path",
    "status",
    "included_in_handoff_expected",
    "private_preview_safe",
    "contains_private_data",
    "contains_synthetic_or_sanitized_data",
    "notes",
    "reason_codes",
)

SUMMARY_FIELDS = (
    "release_scope",
    "source_head",
    "pages_total",
    "pages_pass",
    "screenshots_count",
    "route_matrix_status",
    "static_build_qa_status",
    "copy_freeze_status",
    "public_deploy_performed",
    "private_data_leak_detected",
    "dummy_claims_detected",
    "fake_links_detected",
    "forbidden_advice_terms_detected",
    "handoff_release_status",
    "remaining_public_launch_blockers",
    "reason_codes",
)

PUBLIC_LAUNCH_BLOCKERS = (
    "real CTA targets",
    "imprint URL",
    "privacy policy URL",
    "pricing and scope review",
    "hosting and route-fallback validation",
    "final compliance review",
)


@dataclass(frozen=True)
class ReleaseNotesResult:
    handoff_index_path: Path
    release_summary_path: Path
    report_path: Path
    handoff_release_status: str


def csv_bool(value: bool) -> str:
    return "True" if value else "False"


def yn(value: bool) -> str:
    return "yes" if value else "no"


def read_csv_rows(path_value: str) -> list[dict[str, str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_csv_first(path_value: str) -> dict[str, str]:
    rows = read_csv_rows(path_value)
    return rows[0] if rows else {}


def json_is_valid(path_value: str) -> bool:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return False
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return True


def path_exists(path_value: str) -> bool:
    return resolve_repo_path(path_value).exists()


def git_short_head() -> str:
    result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "unknown"


def write_csv(path_value: str, fields: tuple[str, ...], rows: list[dict[str, str]]) -> Path:
    path = ensure_parent_dir(path_value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def index_row(
    item_type: str,
    item_name: str,
    path: str,
    status: str,
    included: bool,
    safe: bool,
    private_data: bool,
    synthetic_or_sanitized: bool,
    notes: str,
    reason_codes: str,
) -> dict[str, str]:
    return {
        "item_type": item_type,
        "item_name": item_name,
        "path": path,
        "status": status,
        "included_in_handoff_expected": yn(included),
        "private_preview_safe": yn(safe),
        "contains_private_data": yn(private_data),
        "contains_synthetic_or_sanitized_data": yn(synthetic_or_sanitized),
        "notes": notes,
        "reason_codes": reason_codes,
    }


def build_handoff_index() -> list[dict[str, str]]:
    route_rows = read_csv_rows("data/processed/website_private_preview_route_matrix.csv")
    route_status_by_path = {row.get("route", ""): row.get("route_status", "NOT_AVAILABLE") for row in route_rows}
    rows: list[dict[str, str]] = []

    for name, route, notes in PAGES:
        status = route_status_by_path.get(route, "NOT_AVAILABLE")
        rows.append(
            index_row(
                "PAGE",
                name,
                route,
                status,
                True,
                status in {"PASS", "REVIEW"},
                False,
                True,
                notes,
                "PAGE_INDEXED" if status != "NOT_AVAILABLE" else "PAGE_ROUTE_NOT_AVAILABLE",
            )
        )

    for name, path in SCREENSHOTS:
        exists = path_exists(path)
        rows.append(
            index_row(
                "SCREENSHOT",
                name,
                path,
                "PASS" if exists else "NOT_AVAILABLE",
                True,
                exists,
                False,
                True,
                "Main private-preview page screenshot.",
                "SCREENSHOT_INCLUDED" if exists else "SCREENSHOT_MISSING",
            )
        )

    for name, path in QA_ARTIFACTS:
        exists = path_exists(path)
        item_type = "BUILD_QA" if "static_build" in path else "QA_ARTIFACT"
        rows.append(
            index_row(
                item_type,
                name,
                path,
                "PASS" if exists else "NOT_AVAILABLE",
                True,
                exists,
                False,
                False,
                "Generated QA evidence artifact.",
                "QA_ARTIFACT_INCLUDED" if exists else "QA_ARTIFACT_MISSING",
            )
        )

    for name, path in PAYLOADS:
        exists = path_exists(path)
        valid = json_is_valid(path) if path.endswith(".json") else exists
        rows.append(
            index_row(
                "PAYLOAD",
                name,
                path,
                "PASS" if valid else "NOT_AVAILABLE",
                True,
                valid,
                False,
                True,
                "Sanitized or processed readiness evidence for private preview review.",
                "PAYLOAD_VALID" if valid else "PAYLOAD_NOT_AVAILABLE",
            )
        )

    for name, path in DOCS:
        exists = path_exists(path)
        rows.append(
            index_row(
                "DOC",
                name,
                path,
                "PASS" if exists else "NOT_AVAILABLE",
                True,
                exists,
                False,
                False,
                "Reviewer-facing documentation or accepted strategy evidence.",
                "DOC_INCLUDED" if exists else "DOC_MISSING",
            )
        )

    route_summary = read_csv_first(ROUTE_QA_SUMMARY)
    static_summary = read_csv_first(STATIC_BUILD_SUMMARY)
    copy_summary = read_csv_first(COPY_FREEZE_SUMMARY)
    guardrail_values = {
        "PUBLIC_DEPLOY_FALSE": static_summary.get("public_deploy_performed", "True") == "False",
        "NO_PRIVATE_DATA_LEAK": copy_summary.get("private_data_leak_detected", "True") == "False",
        "NO_DUMMY_CLAIMS": copy_summary.get("dummy_claims_detected", "True") == "False",
        "NO_FAKE_LINKS": route_summary.get("fake_links_count", "1") == "0",
        "NO_ACTION_LANGUAGE": route_summary.get("advice_term_violations", "1") == "0",
    }
    for name, notes, code in GUARDRAILS:
        passed = guardrail_values.get(code, False)
        rows.append(
            index_row(
                "GUARDRAIL",
                name,
                "data/processed",
                "PASS" if passed else "BLOCKED",
                True,
                passed,
                False,
                False,
                notes,
                code if passed else f"{code}_FAILED",
            )
        )

    return rows


def build_release_summary(index_rows: list[dict[str, str]]) -> dict[str, str]:
    route_summary = read_csv_first(ROUTE_QA_SUMMARY)
    static_summary = read_csv_first(STATIC_BUILD_SUMMARY)
    copy_summary = read_csv_first(COPY_FREEZE_SUMMARY)

    pages = [row for row in index_rows if row["item_type"] == "PAGE"]
    screenshots = [row for row in index_rows if row["item_type"] == "SCREENSHOT" and row["status"] == "PASS"]
    blocked = [row for row in index_rows if row["status"] == "BLOCKED"]
    missing_required = [
        row
        for row in index_rows
        if row["included_in_handoff_expected"] == "yes" and row["status"] == "NOT_AVAILABLE"
    ]
    private_data = any(row["contains_private_data"] == "yes" for row in index_rows)

    route_status = route_summary.get("private_preview_qa_status", "NOT_AVAILABLE")
    static_status = static_summary.get("static_build_qa_status", "NOT_AVAILABLE")
    copy_status = copy_summary.get("copy_freeze_status", "NOT_AVAILABLE")
    public_deploy = static_summary.get("public_deploy_performed", "True")
    fake_links = route_summary.get("fake_links_count", "1") != "0"
    action_terms = route_summary.get("advice_term_violations", "1") != "0"
    dummy_claims = copy_summary.get("dummy_claims_detected", "True") != "False"
    private_leak = copy_summary.get("private_data_leak_detected", "True") != "False" or private_data

    release_status = "PASS"
    reason_codes = ["HANDOFF_RELEASE_PASS"]
    if blocked or private_leak or dummy_claims or fake_links or action_terms or public_deploy != "False":
        release_status = "BLOCKED"
        reason_codes = ["HANDOFF_RELEASE_BLOCKED"]
    elif missing_required or route_status != "PASS" or static_status != "PASS" or copy_status != "PASS":
        release_status = "REVIEW"
        reason_codes = ["HANDOFF_RELEASE_REVIEW"]

    return {
        "release_scope": "PRIVATE_PREVIEW_WEBSITE",
        "source_head": git_short_head(),
        "pages_total": str(len(pages)),
        "pages_pass": str(sum(1 for row in pages if row["status"] == "PASS")),
        "screenshots_count": str(len(screenshots)),
        "route_matrix_status": route_status,
        "static_build_qa_status": static_status,
        "copy_freeze_status": copy_status,
        "public_deploy_performed": public_deploy,
        "private_data_leak_detected": csv_bool(private_leak),
        "dummy_claims_detected": csv_bool(dummy_claims),
        "fake_links_detected": csv_bool(fake_links),
        "forbidden_advice_terms_detected": csv_bool(action_terms),
        "handoff_release_status": release_status,
        "remaining_public_launch_blockers": "; ".join(PUBLIC_LAUNCH_BLOCKERS),
        "reason_codes": "|".join(reason_codes),
    }


def write_report(index_rows: list[dict[str, str]], summary: dict[str, str], *, report_date: date | None = None) -> Path:
    day = (report_date or date.today()).isoformat()
    path = ensure_parent_dir(f"reports/{day}/website_private_preview_release_notes.md")
    pages = [row for row in index_rows if row["item_type"] == "PAGE"]
    screenshots = [row for row in index_rows if row["item_type"] == "SCREENSHOT"]
    qa_rows = [row for row in index_rows if row["item_type"] in {"QA_ARTIFACT", "BUILD_QA"}]
    payloads = [row for row in index_rows if row["item_type"] == "PAYLOAD"]
    docs = [row for row in index_rows if row["item_type"] == "DOC"]

    lines = [
        "# Website Private Preview Release Notes",
        "",
        "## Executive Summary",
        "",
        f"- Release scope: `{summary['release_scope']}`",
        f"- Source head: `{summary['source_head']}`",
        f"- Handoff release status: `{summary['handoff_release_status']}`",
        f"- Pages indexed: `{summary['pages_pass']}` / `{summary['pages_total']}`",
        f"- Screenshots indexed: `{summary['screenshots_count']}`",
        f"- Public deploy performed: `{summary['public_deploy_performed']}`",
        f"- Private data leak detected: `{summary['private_data_leak_detected']}`",
        f"- Dummy claims detected: `{summary['dummy_claims_detected']}`",
        "",
        "## Current Private Preview Scope",
        "",
        "- This handoff covers the private-preview website and its generated QA evidence.",
        "- It does not add pages, sections, product claims, public deployment, pricing, or external services.",
        "- The website remains a private review surface backed by sanitized or synthetic demo data.",
        "",
        "## Pages Included",
        "",
        "| Page | Route | Status | Notes |",
        "|---|---|---:|---|",
        *[f"| {row['item_name']} | `{row['path']}` | `{row['status']}` | {row['notes']} |" for row in pages],
        "",
        "## Screenshots Included",
        "",
        "| Screenshot | Path | Status |",
        "|---|---|---:|",
        *[f"| {row['item_name']} | `{row['path']}` | `{row['status']}` |" for row in screenshots],
        "",
        "## QA Evidence",
        "",
        "| Artifact | Path | Status |",
        "|---|---|---:|",
        *[f"| {row['item_name']} | `{row['path']}` | `{row['status']}` |" for row in qa_rows],
        "",
        "## Static Build / Package QA",
        "",
        f"- Static build QA status: `{summary['static_build_qa_status']}`",
        "- `dist/` and `deploy_artifacts/` remain outside the repo handoff ZIP.",
        "- Static review package outputs, if present locally, are private-review only.",
        "",
        "## Copy Freeze Result",
        "",
        f"- Copy freeze status: `{summary['copy_freeze_status']}`",
        f"- Fake links detected: `{summary['fake_links_detected']}`",
        f"- Forbidden action terms detected: `{summary['forbidden_advice_terms_detected']}`",
        "",
        "## Readiness Payload",
        "",
        "| Payload | Path | Status |",
        "|---|---|---:|",
        *[f"| {row['item_name']} | `{row['path']}` | `{row['status']}` |" for row in payloads],
        "",
        "## Public Launch Blockers",
        "",
        *[f"- {item}" for item in PUBLIC_LAUNCH_BLOCKERS],
        "",
        "## What This Is Not",
        "",
        "- Not a public launch.",
        "- Not a launched pricing page.",
        "- Not a brokerage interface.",
        "- Not investment, tax, or legal advice.",
        "- Not a claim that readiness has passed.",
        "",
        "## Reviewer Checklist",
        "",
        "- Open Home screenshot.",
        "- Open Workflow screenshot.",
        "- Open Evidence screenshot.",
        "- Open Portfolio screenshot.",
        "- Open Dashboard screenshot.",
        "- Open Manifesto screenshot.",
        "- Review route matrix summary.",
        "- Review static build QA summary.",
        "- Review copy freeze summary.",
        "- Confirm public launch blockers.",
        "- Confirm no private raw files in handoff.",
        "- Confirm no dist or deploy artifacts in repo handoff.",
        "- Confirm readiness is not claimed as PASS.",
        "",
        "## Handoff ZIP Expectations",
        "",
        "- Include release notes artifacts, QA artifacts, screenshots, readiness artifacts, deployment notes, and strategy review evidence.",
        "- Exclude `dist/`, `deploy_artifacts/`, environment files, secrets, private raw data, and local ZIPs.",
        "",
        "## Remaining Review Items",
        "",
        f"- {summary['remaining_public_launch_blockers']}",
        "",
        "## Documentation Indexed",
        "",
        "| Document | Path | Status |",
        "|---|---|---:|",
        *[f"| {row['item_name']} | `{row['path']}` | `{row['status']}` |" for row in docs],
        "",
        "## Recommended Next Patch",
        "",
        "`PATCH / WEBSITE PRIVATE PREVIEW FINAL HANDOFF QA / ZIP CONTENT INDEX / NO SCOPE EXPANSION`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_website_private_preview_release_notes(*, report_date: date | None = None) -> ReleaseNotesResult:
    index_rows = build_handoff_index()
    summary = build_release_summary(index_rows)
    handoff_index_path = write_csv(HANDOFF_INDEX_OUTPUT, INDEX_FIELDS, index_rows)
    release_summary_path = write_csv(RELEASE_SUMMARY_OUTPUT, SUMMARY_FIELDS, [summary])
    report_path = write_report(index_rows, summary, report_date=report_date)
    return ReleaseNotesResult(
        handoff_index_path=handoff_index_path,
        release_summary_path=release_summary_path,
        report_path=report_path,
        handoff_release_status=summary["handoff_release_status"],
    )


def main() -> None:
    result = run_website_private_preview_release_notes()
    print(f"handoff_index={result.handoff_index_path}")
    print(f"release_summary={result.release_summary_path}")
    print(f"report={result.report_path}")
    print(f"handoff_release_status={result.handoff_release_status}")


if __name__ == "__main__":
    main()
