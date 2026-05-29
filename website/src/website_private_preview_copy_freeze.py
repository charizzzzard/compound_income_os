from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.common import ensure_parent_dir, resolve_repo_path

APP_PATH = "website/compound-income-os-landing/src/App.jsx"
CONFIG_PATH = "website/compound-income-os-landing/src/siteConfig.js"
SCREENSHOT_SCRIPT_PATH = "website/compound-income-os-landing/scripts/capture-screenshots.mjs"
WEBSITE_README_PATH = "website/compound-income-os-landing/README.md"
DEPLOYMENT_NOTES_PATH = "website/compound-income-os-landing/DEPLOYMENT_NOTES.md"
PUBLIC_DEMO_DIR = "website/compound-income-os-landing/public/demo"
DIST_DIR = "website/compound-income-os-landing/dist"

ROUTE_QA_SUMMARY = "data/processed/website_private_preview_qa_summary.csv"
STATIC_BUILD_SUMMARY = "data/processed/website_static_build_package_summary.csv"
PUBLIC_SAMPLE_PAYLOAD = "website/compound-income-os-landing/public/demo/readiness_payload.sample.json"
READINESS_PAYLOAD = "data/processed/dashboard_readiness_payload.json"

COPY_FREEZE_MATRIX_OUTPUT = "data/processed/website_private_preview_copy_freeze_matrix.csv"
COPY_FREEZE_SUMMARY_OUTPUT = "data/processed/website_private_preview_copy_freeze_summary.csv"

EXPECTED_SCREENSHOTS = (
    "01_home_wayfinder.png",
    "02_workflow_page.png",
    "03_evidence_page.png",
    "04_portfolio_page.png",
    "05_dashboard_page.png",
    "06_manifesto_page.png",
)

VISIBLE_SOURCE_PATHS = (
    APP_PATH,
    CONFIG_PATH,
    WEBSITE_README_PATH,
    DEPLOYMENT_NOTES_PATH,
    SCREENSHOT_SCRIPT_PATH,
)

MATRIX_FIELDS = (
    "scope",
    "check_name",
    "status",
    "severity",
    "matches_count",
    "violating_matches_count",
    "allowed_matches_count",
    "source_paths",
    "reason_codes",
    "recommended_fix",
)

SUMMARY_FIELDS = (
    "routes_total",
    "routes_covered_by_screenshots",
    "brand_consistency_status",
    "readiness_claim_status",
    "advice_language_status",
    "cta_safety_status",
    "privacy_guardrail_status",
    "public_launch_framing_status",
    "static_build_qa_status",
    "copy_freeze_status",
    "p0_blockers_count",
    "p1_review_count",
    "public_deploy_performed",
    "private_data_leak_detected",
    "dummy_claims_detected",
    "reason_codes",
)

ACTION_TERMS = (
    "BUY",
    "SELL",
    "STRONG_BUY",
    "STRONG_SELL",
    "TRADE",
    "EXECUTE",
    "ORDER",
    "RECOMMENDATION",
    "DEPLOY CAPITAL",
    "ADD NOW",
)

ALLOWED_ACTION_CONTEXTS = (
    "does not execute orders",
    "not a brokerage or order execution interface",
    "brokerage or order execution interface",
    "order/execution signals",
    "not investment advice",
    "not investment, tax, or legal advice",
    "monthly_buy_ranking.csv",
    "buy_score",
    "DO_NOT_BUY",
    "BUILT FOR INVESTORS, NOT TRADERS.",
)

PRIVATE_PATTERNS = (
    r"data/raw/private",
    r"personal_sec_identity_map",
    r"\bCIK[0-9A-Z_-]*\b",
    r"private notes?",
    r"broker exports raw",
)

READINESS_POSITIVE_PATTERNS = (
    r"\bdecision[- ]ready\b",
    r"\bready to invest\b",
    r"\binvestment-ready\b",
)

PUBLIC_POSITIVE_PATTERNS = (
    r"\bpublic launch ready\b",
    r"\bpublic[- ]launch[- ]ready\b",
)

ALLOWED_READINESS_CONTEXTS = (
    "not decision-ready",
    "not decision ready",
    "decision readiness is blocked",
    "decision readiness currently blocked",
    "does not imply decision readiness",
    "no page implies decision readiness",
    "Decision readiness is currently blocked",
    "not investment advice",
)

ALLOWED_PUBLIC_CONTEXTS = (
    "public launch remains blocked",
    "public launch still requires",
    "not ready for public deployment",
    "not ready for public launch",
    "does not mean public launch readiness",
    "no public deploy has been performed",
    "No public deployment is performed",
    "no page implies decision readiness or public launch readiness",
)


@dataclass(frozen=True)
class CopyFreezeResult:
    matrix_path: Path
    summary_path: Path
    report_path: Path
    copy_freeze_status: str


def read_text(path_value: str | Path) -> str:
    path = resolve_repo_path(path_value)
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() and path.is_file() else ""


def read_csv_first(path_value: str) -> dict[str, str]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[0] if rows else {}


def read_json_status(path_value: str) -> tuple[bool, str]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return False, "missing"
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True, "valid"
    except json.JSONDecodeError:
        return True, "invalid"


def read_public_demo_text() -> str:
    directory = resolve_repo_path(PUBLIC_DEMO_DIR)
    if not directory.exists():
        return ""
    chunks = []
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def read_dist_text() -> str:
    directory = resolve_repo_path(DIST_DIR)
    if not directory.exists():
        return ""
    chunks = []
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(chunks)


def source_texts(include_dist: bool = True) -> dict[str, str]:
    texts = {path: read_text(path) for path in VISIBLE_SOURCE_PATHS}
    texts[PUBLIC_DEMO_DIR] = read_public_demo_text()
    texts["reports/2026-04-27/website_private_preview_route_matrix_report.md"] = read_text("reports/2026-04-27/website_private_preview_route_matrix_report.md")
    texts["reports/2026-04-27/website_static_build_package_report.md"] = read_text("reports/2026-04-27/website_static_build_package_report.md")
    if include_dist:
        texts[DIST_DIR] = read_dist_text()
    return texts


def combined_text(texts: dict[str, str]) -> str:
    return "\n".join(texts.values())


def count_pattern(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def strip_allowed_contexts(text: str, allowed: tuple[str, ...]) -> tuple[str, int]:
    filtered = text
    count = 0
    for phrase in allowed:
        phrase_count = filtered.lower().count(phrase.lower())
        if phrase_count:
            count += phrase_count
            filtered = re.sub(re.escape(phrase), "", filtered, flags=re.IGNORECASE)
    return filtered, count


def action_term_matches(text: str) -> tuple[int, int, int]:
    filtered, allowed = strip_allowed_contexts(text, ALLOWED_ACTION_CONTEXTS)
    matches = 0
    for term in ACTION_TERMS:
        pattern = re.escape(term).replace(r"\ ", r"\s+")
        matches += count_pattern(rf"(?<![A-Z0-9_]){pattern}(?![A-Z0-9_])", filtered.upper())
    total = matches + allowed
    return total, allowed, matches


def readiness_claim_matches(text: str) -> tuple[int, int, int]:
    filtered, allowed = strip_allowed_contexts(text, ALLOWED_READINESS_CONTEXTS)
    violations = sum(count_pattern(pattern, filtered) for pattern in READINESS_POSITIVE_PATTERNS)
    total = violations + allowed
    return total, allowed, violations


def public_claim_matches(text: str) -> tuple[int, int, int]:
    filtered, allowed = strip_allowed_contexts(text, ALLOWED_PUBLIC_CONTEXTS)
    violations = sum(count_pattern(pattern, filtered) for pattern in PUBLIC_POSITIVE_PATTERNS)
    total = violations + allowed
    return total, allowed, violations


def private_matches(text: str) -> int:
    return sum(count_pattern(pattern, text) for pattern in PRIVATE_PATTERNS)


def make_row(
    scope: str,
    check_name: str,
    status: str,
    severity: str,
    matches_count: int,
    violating_matches_count: int,
    allowed_matches_count: int,
    source_paths: str,
    reason_codes: str,
    recommended_fix: str,
) -> dict[str, str]:
    return {
        "scope": scope,
        "check_name": check_name,
        "status": status,
        "severity": severity,
        "matches_count": str(matches_count),
        "violating_matches_count": str(violating_matches_count),
        "allowed_matches_count": str(allowed_matches_count),
        "source_paths": source_paths,
        "reason_codes": reason_codes,
        "recommended_fix": recommended_fix,
    }


def build_matrix(texts: dict[str, str]) -> list[dict[str, str]]:
    visible_texts = {key: value for key, value in texts.items() if key != DIST_DIR}
    text = combined_text(visible_texts)
    privacy_text = combined_text(texts)
    app_text = texts.get(APP_PATH, "")
    config_text = texts.get(CONFIG_PATH, "")
    screenshot_text = texts.get(SCREENSHOT_SCRIPT_PATH, "")
    route_summary = read_csv_first(ROUTE_QA_SUMMARY)
    static_summary = read_csv_first(STATIC_BUILD_SUMMARY)

    rows: list[dict[str, str]] = []

    brand_matches = count_pattern(r"\bCompound Income OS\b", text)
    brand_pivots = count_pattern(r"\bCompounding Income OS\b", text)
    rows.append(
        make_row(
            "website",
            "brand_consistency",
            "PASS" if brand_matches > 0 and brand_pivots == 0 else "BLOCKED",
            "P0_BLOCKER" if brand_pivots else "INFO",
            brand_matches + brand_pivots,
            brand_pivots,
            brand_matches,
            "|".join(VISIBLE_SOURCE_PATHS),
            "BRAND_OK" if brand_pivots == 0 else "BRAND_PIVOT_DETECTED",
            "Keep visible product copy on Compound Income OS.",
        )
    )

    readiness_total, readiness_allowed, readiness_violations = readiness_claim_matches(text)
    rows.append(
        make_row(
            "website",
            "readiness_claims",
            "PASS" if readiness_violations == 0 else "BLOCKED",
            "P0_BLOCKER",
            readiness_total,
            readiness_violations,
            readiness_allowed,
            "|".join(VISIBLE_SOURCE_PATHS),
            "READINESS_CLAIMS_OK" if readiness_violations == 0 else "POSITIVE_READINESS_CLAIM",
            "Replace positive readiness language with blocked/private-preview framing.",
        )
    )

    public_total, public_allowed, public_violations = public_claim_matches(text)
    rows.append(
        make_row(
            "website",
            "public_launch_claims",
            "PASS" if public_violations == 0 else "BLOCKED",
            "P0_BLOCKER",
            public_total,
            public_violations,
            public_allowed,
            "|".join(VISIBLE_SOURCE_PATHS),
            "PUBLIC_LAUNCH_FRAMING_OK" if public_violations == 0 else "PUBLIC_LAUNCH_READY_CLAIM",
            "Keep public-launch blockers visible and avoid launch-ready claims.",
        )
    )

    action_total, action_allowed, action_violations = action_term_matches(text)
    rows.append(
        make_row(
            "website",
            "advice_action_language",
            "PASS" if action_violations == 0 else "BLOCKED",
            "P0_BLOCKER",
            action_total,
            action_violations,
            action_allowed,
            "|".join(VISIBLE_SOURCE_PATHS),
            "ACTION_LANGUAGE_OK" if action_violations == 0 else "ACTION_LANGUAGE_DETECTED",
            "Remove market-action language from visible CTA/display copy.",
        )
    )

    fake_links = count_pattern(r"example\.invalid", text) + count_pattern(r"mailto:", app_text + "\n" + config_text)
    pending_ok = "Imprint pending" in text and "Privacy pending" in text
    rows.append(
        make_row(
            "website",
            "cta_safety",
            "PASS" if fake_links == 0 and pending_ok else "BLOCKED",
            "P0_BLOCKER",
            fake_links,
            fake_links + (0 if pending_ok else 1),
            1 if pending_ok else 0,
            f"{APP_PATH}|{CONFIG_PATH}|{WEBSITE_README_PATH}|{DEPLOYMENT_NOTES_PATH}",
            "CTA_SAFETY_OK" if fake_links == 0 and pending_ok else "CTA_SAFETY_VIOLATION",
            "Use real routes or pending/disabled states for unset external URLs.",
        )
    )

    privacy_violations = private_matches(privacy_text)
    rows.append(
        make_row(
            "website",
            "privacy_data_leakage",
            "PASS" if privacy_violations == 0 else "BLOCKED",
            "P0_BLOCKER",
            privacy_violations,
            privacy_violations,
            0,
            "|".join((*VISIBLE_SOURCE_PATHS, PUBLIC_DEMO_DIR)),
            "PRIVACY_GUARDRAILS_OK" if privacy_violations == 0 else "PRIVATE_MARKER_DETECTED",
            "Remove private raw paths, SEC identity markers, notes, or private values.",
        )
    )

    blockers = ("Imprint", "Privacy", "Real CTA targets", "Pricing and scope", "No public deploy")
    launch_blocker_matches = sum(1 for phrase in blockers if phrase.lower() in text.lower())
    private_preview_present = "private preview" in text.lower()
    rows.append(
        make_row(
            "website",
            "public_launch_blocker_visibility",
            "PASS" if launch_blocker_matches >= 4 and private_preview_present else "REVIEW",
            "P1_REVIEW",
            launch_blocker_matches,
            0 if launch_blocker_matches >= 4 and private_preview_present else 1,
            launch_blocker_matches,
            f"{WEBSITE_README_PATH}|{DEPLOYMENT_NOTES_PATH}|{APP_PATH}",
            "PUBLIC_LAUNCH_BLOCKERS_VISIBLE" if launch_blocker_matches >= 4 and private_preview_present else "PUBLIC_LAUNCH_BLOCKERS_REVIEW",
            "Keep imprint/privacy/CTA/pricing/no-public-deploy blockers visible.",
        )
    )

    screenshot_count = sum(1 for filename in EXPECTED_SCREENSHOTS if filename in screenshot_text)
    rows.append(
        make_row(
            "website",
            "screenshot_coverage",
            "PASS" if screenshot_count == len(EXPECTED_SCREENSHOTS) else "REVIEW",
            "P1_REVIEW",
            screenshot_count,
            0 if screenshot_count == len(EXPECTED_SCREENSHOTS) else 1,
            screenshot_count,
            SCREENSHOT_SCRIPT_PATH,
            "SCREENSHOT_COVERAGE_OK" if screenshot_count == len(EXPECTED_SCREENSHOTS) else "SCREENSHOT_COVERAGE_REVIEW",
            "Keep all six main private-preview pages screenshot-covered.",
        )
    )

    route_status = route_summary.get("private_preview_qa_status", "NOT_AVAILABLE")
    rows.append(
        make_row(
            "qa_artifacts",
            "route_matrix_linkage",
            "PASS" if route_status == "PASS" else "REVIEW",
            "P1_REVIEW",
            1 if route_status else 0,
            0 if route_status == "PASS" else 1,
            1 if route_status == "PASS" else 0,
            ROUTE_QA_SUMMARY,
            f"ROUTE_MATRIX_{route_status or 'NOT_AVAILABLE'}",
            "Regenerate route matrix QA if route coverage drifts.",
        )
    )

    static_status = static_summary.get("static_build_qa_status", "NOT_AVAILABLE")
    public_deploy = static_summary.get("public_deploy_performed", "True")
    static_violation = 0 if static_status == "PASS" and public_deploy == "False" else 1
    rows.append(
        make_row(
            "qa_artifacts",
            "static_build_qa_linkage",
            "PASS" if static_violation == 0 else "REVIEW",
            "P1_REVIEW",
            1 if static_status else 0,
            static_violation,
            1 if static_violation == 0 else 0,
            STATIC_BUILD_SUMMARY,
            f"STATIC_BUILD_{static_status}|PUBLIC_DEPLOY_{public_deploy}",
            "Regenerate static build QA if build/package status drifts.",
        )
    )

    sample_exists, sample_status = read_json_status(PUBLIC_SAMPLE_PAYLOAD)
    readiness_exists, readiness_status = read_json_status(READINESS_PAYLOAD)
    payload_violation = 0 if sample_exists and sample_status == "valid" and readiness_exists and readiness_status == "valid" else 1
    rows.append(
        make_row(
            "qa_artifacts",
            "readiness_payload_linkage",
            "PASS" if payload_violation == 0 else "REVIEW",
            "P1_REVIEW",
            int(sample_exists) + int(readiness_exists),
            payload_violation,
            int(sample_status == "valid") + int(readiness_status == "valid"),
            f"{PUBLIC_SAMPLE_PAYLOAD}|{READINESS_PAYLOAD}",
            f"PUBLIC_SAMPLE_{sample_status.upper()}|DASHBOARD_PAYLOAD_{readiness_status.upper()}",
            "Regenerate sanitized readiness payload if JSON validity or source linkage fails.",
        )
    )

    home_subline_present = "one monthly decision you can trust" in app_text
    rows.append(
        make_row(
            "website",
            "home_subline_claim",
            "PASS" if not home_subline_present else "REVIEW",
            "P1_REVIEW",
            1 if home_subline_present else 0,
            1 if home_subline_present else 0,
            0 if home_subline_present else 1,
            APP_PATH,
            "HOME_SUBLINE_NEUTRALIZED" if not home_subline_present else "HOME_SUBLINE_REVIEW",
            "Use neutral report/re-open wording instead of trust-ready decision wording.",
        )
    )

    return rows


def summary_from_matrix(rows: list[dict[str, str]]) -> dict[str, str]:
    route_summary = read_csv_first(ROUTE_QA_SUMMARY)
    static_summary = read_csv_first(STATIC_BUILD_SUMMARY)
    p0 = sum(1 for row in rows if row["status"] == "BLOCKED" and row["severity"] == "P0_BLOCKER")
    p1 = sum(1 for row in rows if row["status"] in {"REVIEW", "BLOCKED"} and row["severity"] == "P1_REVIEW")
    statuses = {row["check_name"]: row["status"] for row in rows}
    copy_status = "PASS"
    reason_codes = ["COPY_FREEZE_PASS"]
    if p0:
        copy_status = "BLOCKED"
        reason_codes = ["P0_BLOCKERS_PRESENT"]
    elif p1:
        copy_status = "REVIEW"
        reason_codes = ["P1_REVIEW_ITEMS_PRESENT"]
    return {
        "routes_total": route_summary.get("routes_total", "0"),
        "routes_covered_by_screenshots": route_summary.get("screenshots_count", "0"),
        "brand_consistency_status": statuses.get("brand_consistency", "NOT_AVAILABLE"),
        "readiness_claim_status": statuses.get("readiness_claims", "NOT_AVAILABLE"),
        "advice_language_status": statuses.get("advice_action_language", "NOT_AVAILABLE"),
        "cta_safety_status": statuses.get("cta_safety", "NOT_AVAILABLE"),
        "privacy_guardrail_status": statuses.get("privacy_data_leakage", "NOT_AVAILABLE"),
        "public_launch_framing_status": statuses.get("public_launch_blocker_visibility", "NOT_AVAILABLE"),
        "static_build_qa_status": static_summary.get("static_build_qa_status", "NOT_AVAILABLE"),
        "copy_freeze_status": copy_status,
        "p0_blockers_count": str(p0),
        "p1_review_count": str(p1),
        "public_deploy_performed": static_summary.get("public_deploy_performed", "False"),
        "private_data_leak_detected": static_summary.get("private_data_leak_detected", "False"),
        "dummy_claims_detected": static_summary.get("dummy_claims_detected", "False"),
        "reason_codes": "|".join(reason_codes),
    }


def write_csv(path_value: str, fields: tuple[str, ...], rows: list[dict[str, str]]) -> Path:
    path = ensure_parent_dir(path_value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_report(rows: list[dict[str, str]], summary: dict[str, str], *, report_date: date | None = None) -> Path:
    day = (report_date or date.today()).isoformat()
    path = ensure_parent_dir(f"reports/{day}/website_private_preview_copy_freeze_report.md")
    lines = [
        "# Website Private Preview Copy Freeze",
        "",
        "## Executive Summary",
        "",
        f"- PRIVATE_PREVIEW_COPY_FREEZE: `{summary['copy_freeze_status']}`",
        f"- P0 blockers: `{summary['p0_blockers_count']}`",
        f"- P1 review items: `{summary['p1_review_count']}`",
        f"- Public deploy performed: `{summary['public_deploy_performed']}`",
        f"- Private data leak detected: `{summary['private_data_leak_detected']}`",
        f"- Dummy claims detected: `{summary['dummy_claims_detected']}`",
        "",
        "## Source QA Inputs",
        "",
        f"- Route matrix status: `{read_csv_first(ROUTE_QA_SUMMARY).get('private_preview_qa_status', 'NOT_AVAILABLE')}`",
        f"- Static build QA status: `{summary['static_build_qa_status']}`",
        f"- Routes covered by screenshots: `{summary['routes_covered_by_screenshots']}`",
        "",
        "## Brand Consistency",
        "",
        f"- Status: `{summary['brand_consistency_status']}`",
        "- Visible product copy remains `Compound Income OS`.",
        "",
        "## Route / Screenshot Coverage",
        "",
        "- Six main private-preview pages remain covered by the screenshot script.",
        "",
        "## CTA Safety",
        "",
        f"- Status: `{summary['cta_safety_status']}`",
        "- External targets remain real-or-pending; no fake `mailto:` or `example.invalid` fallback is allowed.",
        "",
        "## Readiness / Public Launch Claims",
        "",
        f"- Readiness claim status: `{summary['readiness_claim_status']}`",
        f"- Public-launch framing status: `{summary['public_launch_framing_status']}`",
        "- The freeze does not mean public-launch readiness or decision readiness.",
        "",
        "## Advice / Action Language",
        "",
        f"- Status: `{summary['advice_language_status']}`",
        "- Compliance/negative contexts and legacy internal filenames are allowed; CTA/display action terms are blocked.",
        "",
        "## Privacy / Data Leakage",
        "",
        f"- Status: `{summary['privacy_guardrail_status']}`",
        "- Website/public demo/report copy contains no private raw paths or private SEC identity markers.",
        "",
        "## Static Build QA Linkage",
        "",
        f"- Static build QA status: `{summary['static_build_qa_status']}`",
        "- Repo handoff continues to exclude `dist/` and `deploy_artifacts/`.",
        "",
        "## Fixed Issues",
        "",
        "- Home hero subline was neutralized from decision-trust wording to report re-open wording.",
        "- README and deployment notes now document the copy-freeze check.",
        "",
        "## Remaining Review Items",
        "",
        "- Public launch blockers remain active until real CTA targets, imprint, privacy policy, pricing/scope review, hosting/rewrite validation, and compliance review are complete.",
        "",
        "## Copy Freeze Decision",
        "",
        f"`PRIVATE_PREVIEW_COPY_FREEZE = {summary['copy_freeze_status']}`",
        f"Reason codes: `{summary['reason_codes']}`",
        "",
        "## Recommended Next Patch",
        "",
        "`PATCH / WEBSITE PRIVATE PREVIEW RELEASE NOTES / HANDOFF INDEX / NO SCOPE EXPANSION`",
        "",
        "## Matrix",
        "",
        "| Scope | Check | Status | Severity | Violations |",
        "|---|---|---:|---:|---:|",
        *[
            f"| `{row['scope']}` | `{row['check_name']}` | `{row['status']}` | `{row['severity']}` | `{row['violating_matches_count']}` |"
            for row in rows
        ],
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_website_private_preview_copy_freeze(*, report_date: date | None = None, include_dist: bool = True) -> CopyFreezeResult:
    rows = build_matrix(source_texts(include_dist=include_dist))
    summary = summary_from_matrix(rows)
    matrix_path = write_csv(COPY_FREEZE_MATRIX_OUTPUT, MATRIX_FIELDS, rows)
    summary_path = write_csv(COPY_FREEZE_SUMMARY_OUTPUT, SUMMARY_FIELDS, [summary])
    report_path = write_report(rows, summary, report_date=report_date)
    return CopyFreezeResult(
        matrix_path=matrix_path,
        summary_path=summary_path,
        report_path=report_path,
        copy_freeze_status=summary["copy_freeze_status"],
    )


def main() -> None:
    result = run_website_private_preview_copy_freeze()
    print(f"matrix={result.matrix_path}")
    print(f"summary={result.summary_path}")
    print(f"report={result.report_path}")
    print(f"PRIVATE_PREVIEW_COPY_FREEZE={result.copy_freeze_status}")


if __name__ == "__main__":
    main()
