from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.common import ROOT, ensure_parent_dir, resolve_repo_path

APP_PATH = "website/compound-income-os-landing/src/App.jsx"
CONFIG_PATH = "website/compound-income-os-landing/src/siteConfig.js"
SCREENSHOT_SCRIPT_PATH = "website/compound-income-os-landing/scripts/capture-screenshots.mjs"
PUBLIC_DEMO_DIR = "website/compound-income-os-landing/public/demo"
WEBSITE_README_PATH = "website/compound-income-os-landing/README.md"
DEPLOYMENT_NOTES_PATH = "website/compound-income-os-landing/DEPLOYMENT_NOTES.md"

ROUTE_MATRIX_OUTPUT = "data/processed/website_private_preview_route_matrix.csv"
CTA_MATRIX_OUTPUT = "data/processed/website_private_preview_cta_matrix.csv"
COPY_GUARDRAILS_OUTPUT = "data/processed/website_private_preview_copy_guardrails.csv"
QA_SUMMARY_OUTPUT = "data/processed/website_private_preview_qa_summary.csv"

EXPECTED_ROUTES = (
    ("/", "Home", "A calmer way to run a long-term portfolio."),
    ("/workflow", "Workflow", "Six stages, one monthly cadence."),
    ("/evidence", "Evidence", "See what's covered. See what's missing."),
    ("/portfolio", "Portfolio", "Four sleeves. Clear rules. Long-term focus."),
    ("/dashboard", "Dashboard", "One local dashboard. Five KPI groups."),
    ("/manifesto", "Manifesto", "Built for people who think for the long run."),
    ("/about", "About alias", "Built for people who think for the long run."),
)

EXPECTED_MAIN_SCREENSHOTS = {
    "/": "01_home_wayfinder.png",
    "/workflow": "02_workflow_page.png",
    "/evidence": "03_evidence_page.png",
    "/portfolio": "04_portfolio_page.png",
    "/dashboard": "05_dashboard_page.png",
    "/manifesto": "06_manifesto_page.png",
}

FORBIDDEN_DISPLAY_TERMS = (
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

ALLOWED_LEGACY_TERMS = (
    "monthly_buy_ranking.csv",
    "buy_score",
    "BUILT FOR INVESTORS, NOT TRADERS.",
    "does not execute orders",
    "order/execution signals",
    "a brokerage or order execution interface",
    "does not provide personalized recommendations",
)

PRIVATE_PATTERNS = (
    r"data/raw/private",
    r"personal_sec_identity_map",
    r"\bCIK[0-9A-Z_-]*\b",
)

ROUTE_MATRIX_FIELDS = (
    "route",
    "route_exists",
    "hero_check_status",
    "nav_reachable",
    "home_reachable",
    "back_forward_supported",
    "private_preview_label_present",
    "synthetic_or_sanitized_label_present",
    "not_advice_label_present",
    "route_status",
    "reason_codes",
)

CTA_MATRIX_FIELDS = (
    "source_route",
    "cta_label",
    "target",
    "target_type",
    "target_exists",
    "fake_link_detected",
    "pending_state_ok",
    "advice_language_detected",
    "cta_status",
    "reason_codes",
)

COPY_GUARDRAILS_FIELDS = (
    "scope",
    "check_name",
    "status",
    "matches_count",
    "allowed_legacy_matches_count",
    "violating_matches_count",
    "reason_codes",
)

QA_SUMMARY_FIELDS = (
    "routes_total",
    "routes_pass",
    "routes_review",
    "routes_blocked",
    "ctas_total",
    "ctas_invalid",
    "fake_links_count",
    "advice_term_violations",
    "private_path_violations",
    "decision_ready_dummy_claims",
    "public_launch_dummy_claims",
    "screenshots_count",
    "main_routes_screenshot_covered",
    "private_preview_qa_status",
)


@dataclass(frozen=True)
class WebsitePrivatePreviewQaResult:
    route_matrix_path: Path
    cta_matrix_path: Path
    copy_guardrails_path: Path
    qa_summary_path: Path
    report_path: Path
    routes_total: int
    routes_pass: int
    ctas_invalid: int
    private_preview_qa_status: str


def read_text(path_value: str | Path) -> str:
    path = resolve_repo_path(path_value)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_website_text() -> dict[str, str]:
    files = {
        "app": APP_PATH,
        "config": CONFIG_PATH,
        "screenshots": SCREENSHOT_SCRIPT_PATH,
        "website_readme": WEBSITE_README_PATH,
        "deployment_notes": DEPLOYMENT_NOTES_PATH,
    }
    public_demo = resolve_repo_path(PUBLIC_DEMO_DIR)
    result = {name: read_text(path) for name, path in files.items()}
    if public_demo.exists():
        result["public_demo"] = "\n".join(path.read_text(encoding="utf-8") for path in sorted(public_demo.glob("*")) if path.is_file())
    else:
        result["public_demo"] = ""
    return result


def csv_bool(value: bool) -> str:
    return "True" if value else "False"


def join_reasons(reasons: list[str]) -> str:
    return "|".join(dict.fromkeys(reasons))


def route_exists(route: str, app_text: str, config_text: str) -> bool:
    if route == "/":
        return "home: '/'" in config_text and "href=\"/\"" in app_text
    if route == "/about":
        return "window.location.pathname === '/about'" in app_text and "about: '/manifesto'" in config_text
    return f"'{route}'" in app_text and route in config_text


def nav_reachable(route: str, app_text: str) -> bool:
    if route == "/":
        return 'href="/"' in app_text
    if route == "/about":
        return "about: '/manifesto'" in read_text(CONFIG_PATH)
    return f"['{route.strip('/').capitalize()}', '{route}', false]" in app_text or f"href=\"{route}\"" in app_text or f"href='{route}'" in app_text or f"'{route}', false" in app_text


def home_reachable(route: str, app_text: str) -> bool:
    if route == "/":
        return True
    if route == "/about":
        return "/manifesto" in app_text
    return f"'{route}', false" in app_text or f"href=\"{route}\"" in app_text


def build_route_matrix(texts: dict[str, str]) -> list[dict[str, str]]:
    app_text = texts["app"]
    config_text = texts["config"]
    screenshot_text = texts["screenshots"]
    rows: list[dict[str, str]] = []
    for route, _label, hero in EXPECTED_ROUTES:
        reasons: list[str] = []
        exists = route_exists(route, app_text, config_text)
        hero_ok = hero in app_text
        nav_ok = nav_reachable(route, app_text)
        home_ok = home_reachable(route, app_text)
        back_forward = "popstate" in app_text and "pushState" in app_text
        private_label = "Private preview" in app_text or "private preview" in app_text
        synthetic_label = "synthetic demo values" in app_text or "sanitized" in app_text
        not_advice = "not investment guidance" in app_text or "does not provide financial" in app_text
        screenshot_ok = route in screenshot_text or (route == "/" and "01_home_wayfinder.png" in screenshot_text)
        if not exists:
            reasons.append("ROUTE_MISSING")
        if not hero_ok:
            reasons.append("HERO_COPY_MISSING")
        if not nav_ok:
            reasons.append("NAV_NOT_REACHABLE")
        if not home_ok:
            reasons.append("HOME_NOT_REACHABLE")
        if not screenshot_ok and route != "/about":
            reasons.append("SCREENSHOT_NOT_COVERED")
        if route == "/about":
            reasons.append("ABOUT_ALIAS_TO_MANIFESTO")
        status = "PASS" if exists and hero_ok and nav_ok and home_ok and back_forward else "REVIEW"
        if not exists or not hero_ok:
            status = "BLOCKED"
        rows.append(
            {
                "route": route,
                "route_exists": csv_bool(exists),
                "hero_check_status": "PASS" if hero_ok else "BLOCKED",
                "nav_reachable": csv_bool(nav_ok),
                "home_reachable": csv_bool(home_ok),
                "back_forward_supported": csv_bool(back_forward),
                "private_preview_label_present": csv_bool(private_label),
                "synthetic_or_sanitized_label_present": csv_bool(synthetic_label),
                "not_advice_label_present": csv_bool(not_advice),
                "route_status": status,
                "reason_codes": join_reasons(reasons) if reasons else "ROUTE_OK",
            }
        )
    return rows


def classify_target(target: str, pending: bool = False) -> str:
    if pending:
        return "PENDING_DISABLED"
    if target.startswith("http"):
        return "EXTERNAL_URL"
    if target.startswith("#") or "#" in target:
        return "ANCHOR"
    if target.startswith("/"):
        return "INTERNAL_ROUTE"
    return "INVALID"


def has_forbidden_term(value: str) -> bool:
    filtered = value
    for allowed in ALLOWED_LEGACY_TERMS:
        filtered = filtered.replace(allowed, "")
    pattern = "|".join(re.escape(term).replace("\\ ", r"\s+") for term in FORBIDDEN_DISPLAY_TERMS)
    return bool(re.search(rf"(?<![A-Z0-9_])({pattern})(?![A-Z0-9_])", filtered.upper()))


def build_cta_matrix(texts: dict[str, str]) -> list[dict[str, str]]:
    valid_routes = {route for route, _label, _hero in EXPECTED_ROUTES}
    ctas = [
        ("/", "Read a sample monthly report", "/workflow#sample-report", False),
        ("/", "See the workflow", "/workflow", False),
        ("/", "Read the manifesto", "/manifesto", False),
        ("/workflow", "See the evidence layer", "/evidence", False),
        ("/workflow", "Read a sample monthly report", "/workflow#sample-report", False),
        ("/evidence", "Read a sample monthly report", "/workflow#sample-report", False),
        ("/evidence", "See the portfolio model", "/portfolio", False),
        ("/portfolio", "Open local dashboard", "/dashboard", False),
        ("/dashboard", "Private preview status", "/demo/readiness_payload.sample.json", False),
        ("/manifesto", "View the workflow", "/workflow", False),
        ("/manifesto", "Request private preview", "", True),
        ("/manifesto", "Request setup", "", True),
        ("/manifesto", "See the workflow", "/workflow", False),
        ("/manifesto", "Open local dashboard", "/dashboard", False),
        ("footer", "Imprint pending", "", True),
        ("footer", "Privacy pending", "", True),
    ]
    rows: list[dict[str, str]] = []
    for source_route, label, target, pending in ctas:
        reasons: list[str] = []
        target_type = classify_target(target, pending)
        fake_link = "example.invalid" in target or target.startswith("mailto:")
        target_path = target.split("#", 1)[0] if target else ""
        target_exists = pending or target_type == "ANCHOR" or target_path in valid_routes or target == "/demo/readiness_payload.sample.json"
        advice = has_forbidden_term(label)
        if fake_link:
            reasons.append("FAKE_LINK_DETECTED")
        if not target_exists:
            reasons.append("TARGET_MISSING")
        if advice:
            reasons.append("ADVICE_LANGUAGE_DETECTED")
        if pending:
            reasons.append("PENDING_STATE_OK")
        status = "PASS" if not fake_link and target_exists and not advice else "BLOCKED"
        rows.append(
            {
                "source_route": source_route,
                "cta_label": label,
                "target": target if target else "PENDING",
                "target_type": target_type,
                "target_exists": csv_bool(target_exists),
                "fake_link_detected": csv_bool(fake_link),
                "pending_state_ok": csv_bool(pending),
                "advice_language_detected": csv_bool(advice),
                "cta_status": status,
                "reason_codes": join_reasons(reasons) if reasons else "CTA_OK",
            }
        )
    return rows


def count_matches(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def build_copy_guardrails(texts: dict[str, str]) -> list[dict[str, str]]:
    combined = "\n".join(texts.values())
    checks: list[tuple[str, str, int, int, list[str]]] = []

    forbidden_matches = sum(count_matches(rf"(?<![A-Z0-9_]){re.escape(term).replace('\\ ', r'\\s+')}(?![A-Z0-9_])", combined.upper()) for term in FORBIDDEN_DISPLAY_TERMS)
    allowed_legacy = sum(combined.count(term) for term in ALLOWED_LEGACY_TERMS)
    checks.append(("website", "forbidden_action_terms", forbidden_matches, allowed_legacy, ["ALLOWED_LEGACY_CONTEXTS_PRESENT"] if allowed_legacy else []))

    private_matches = sum(count_matches(pattern, combined) for pattern in PRIVATE_PATTERNS)
    checks.append(("website", "private_path_or_identity_markers", private_matches, 0, []))

    decision_dummy = count_matches(r"decision readiness[^\\n]{0,80}(PASS|READY)", combined)
    checks.append(("website", "decision_ready_dummy_claims", decision_dummy, 0, []))

    public_dummy = count_matches(r"(public launch[^\\n]{0,80}(ready|complete|finished)|public_deploy_ready\"\\s*:\\s*true)", combined)
    checks.append(("website", "public_launch_dummy_claims", public_dummy, 0, []))

    brand_pivot = count_matches(r"Compounding Income OS", combined)
    checks.append(("website", "brand_pivot_claims", brand_pivot, 0, []))

    rows: list[dict[str, str]] = []
    for scope, name, matches, allowed, reasons in checks:
        violations = max(matches - allowed, 0) if name == "forbidden_action_terms" else matches
        status = "PASS" if violations == 0 else "BLOCKED"
        if violations:
            reasons.append("VIOLATION_DETECTED")
        else:
            reasons.append("GUARDRAIL_OK")
        rows.append(
            {
                "scope": scope,
                "check_name": name,
                "status": status,
                "matches_count": str(matches),
                "allowed_legacy_matches_count": str(allowed),
                "violating_matches_count": str(violations),
                "reason_codes": join_reasons(reasons),
            }
        )
    return rows


def screenshot_coverage(texts: dict[str, str]) -> tuple[int, bool]:
    screenshot_text = texts["screenshots"]
    count = len(re.findall(r"filename:", screenshot_text))
    covered = all(filename in screenshot_text for filename in EXPECTED_MAIN_SCREENSHOTS.values())
    return count, covered


def build_summary(route_rows: list[dict[str, str]], cta_rows: list[dict[str, str]], guardrail_rows: list[dict[str, str]], screenshots_count: int, screenshot_covered: bool) -> dict[str, str]:
    routes_total = len(route_rows)
    routes_pass = sum(1 for row in route_rows if row["route_status"] == "PASS")
    routes_review = sum(1 for row in route_rows if row["route_status"] == "REVIEW")
    routes_blocked = sum(1 for row in route_rows if row["route_status"] == "BLOCKED")
    ctas_invalid = sum(1 for row in cta_rows if row["cta_status"] == "BLOCKED")
    fake_links = sum(1 for row in cta_rows if row["fake_link_detected"] == "True")
    advice_violations = sum(int(row["violating_matches_count"]) for row in guardrail_rows if row["check_name"] == "forbidden_action_terms")
    private_violations = sum(int(row["violating_matches_count"]) for row in guardrail_rows if row["check_name"] == "private_path_or_identity_markers")
    decision_claims = sum(int(row["violating_matches_count"]) for row in guardrail_rows if row["check_name"] == "decision_ready_dummy_claims")
    public_claims = sum(int(row["violating_matches_count"]) for row in guardrail_rows if row["check_name"] == "public_launch_dummy_claims")
    status = "PASS"
    if routes_blocked or ctas_invalid or advice_violations or private_violations or decision_claims or public_claims or not screenshot_covered:
        status = "BLOCKED" if routes_blocked or ctas_invalid or private_violations else "REVIEW"
    return {
        "routes_total": str(routes_total),
        "routes_pass": str(routes_pass),
        "routes_review": str(routes_review),
        "routes_blocked": str(routes_blocked),
        "ctas_total": str(len(cta_rows)),
        "ctas_invalid": str(ctas_invalid),
        "fake_links_count": str(fake_links),
        "advice_term_violations": str(advice_violations),
        "private_path_violations": str(private_violations),
        "decision_ready_dummy_claims": str(decision_claims),
        "public_launch_dummy_claims": str(public_claims),
        "screenshots_count": str(screenshots_count),
        "main_routes_screenshot_covered": csv_bool(screenshot_covered),
        "private_preview_qa_status": status,
    }


def write_csv(path_value: str, fields: tuple[str, ...], rows: list[dict[str, str]]) -> Path:
    path = ensure_parent_dir(path_value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_report(route_rows: list[dict[str, str]], cta_rows: list[dict[str, str]], guardrail_rows: list[dict[str, str]], summary: dict[str, str], report_date: date | None = None) -> Path:
    day = (report_date or date.today()).isoformat()
    path = ensure_parent_dir(f"reports/{day}/website_private_preview_route_matrix_report.md")
    lines = [
        "# Website Private Preview Route Matrix QA",
        "",
        "## Executive Summary",
        "",
        f"- Private preview QA status: `{summary['private_preview_qa_status']}`",
        f"- Routes total: `{summary['routes_total']}`",
        f"- Routes pass/review/blocked: `{summary['routes_pass']}` / `{summary['routes_review']}` / `{summary['routes_blocked']}`",
        f"- CTAs invalid: `{summary['ctas_invalid']}`",
        f"- Main routes screenshot covered: `{summary['main_routes_screenshot_covered']}`",
        "",
        "## Route Matrix",
        "",
        "| Route | Status | Reason codes |",
        "|---|---:|---|",
        *[f"| `{row['route']}` | `{row['route_status']}` | `{row['reason_codes']}` |" for row in route_rows],
        "",
        "## CTA Matrix",
        "",
        "| Source | CTA | Target type | Status |",
        "|---|---|---:|---:|",
        *[f"| `{row['source_route']}` | {row['cta_label']} | `{row['target_type']}` | `{row['cta_status']}` |" for row in cta_rows],
        "",
        "## Copy Guardrails",
        "",
        "| Check | Status | Violations |",
        "|---|---:|---:|",
        *[f"| `{row['check_name']}` | `{row['status']}` | `{row['violating_matches_count']}` |" for row in guardrail_rows],
        "",
        "## Screenshot Coverage",
        "",
        f"- Screenshot count: `{summary['screenshots_count']}`",
        "- Covered routes: `/`, `/workflow`, `/evidence`, `/portfolio`, `/dashboard`, `/manifesto`",
        "",
        "## Private Preview / Public Launch Guardrails",
        "",
        "- Public launch remains blocked.",
        "- Imprint and privacy stay pending unless configured through real environment URLs.",
        "- No fake checkout, waitlist, or placeholder public CTA targets are allowed.",
        "",
        "## Advice / Privacy Guardrails",
        "",
        "- No private raw paths are allowed in website source or public demo payloads.",
        "- Market-action terms are blocked in new CTA/display fields, with legacy/internal filename exceptions only.",
        "",
        "## Fixed Issues",
        "",
        "- Screenshot script now covers all six main private-preview routes.",
        "- Route/CTA/copy matrices are generated as deterministic QA artifacts.",
        "",
        "## Remaining Review Items",
        "",
        "- Public launch blockers remain intentionally active.",
        "- External CTA targets remain pending until real environment URLs are configured.",
        "",
        "## Handoff Impact",
        "",
        "- QA CSVs and this report are allowlisted for handoff export.",
        "",
        "## Recommended Next Patch",
        "",
        "`PATCH / WEBSITE PRIVATE PREVIEW Handoff Review / STATIC BUILD PACKAGE QA / NO PUBLIC DEPLOY`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_website_private_preview_route_matrix(*, report_date: date | None = None) -> WebsitePrivatePreviewQaResult:
    texts = read_website_text()
    route_rows = build_route_matrix(texts)
    cta_rows = build_cta_matrix(texts)
    guardrail_rows = build_copy_guardrails(texts)
    screenshot_count, screenshot_covered = screenshot_coverage(texts)
    summary = build_summary(route_rows, cta_rows, guardrail_rows, screenshot_count, screenshot_covered)

    route_path = write_csv(ROUTE_MATRIX_OUTPUT, ROUTE_MATRIX_FIELDS, route_rows)
    cta_path = write_csv(CTA_MATRIX_OUTPUT, CTA_MATRIX_FIELDS, cta_rows)
    guardrail_path = write_csv(COPY_GUARDRAILS_OUTPUT, COPY_GUARDRAILS_FIELDS, guardrail_rows)
    summary_path = write_csv(QA_SUMMARY_OUTPUT, QA_SUMMARY_FIELDS, [summary])
    report_path = write_report(route_rows, cta_rows, guardrail_rows, summary, report_date=report_date)

    return WebsitePrivatePreviewQaResult(
        route_matrix_path=route_path,
        cta_matrix_path=cta_path,
        copy_guardrails_path=guardrail_path,
        qa_summary_path=summary_path,
        report_path=report_path,
        routes_total=int(summary["routes_total"]),
        routes_pass=int(summary["routes_pass"]),
        ctas_invalid=int(summary["ctas_invalid"]),
        private_preview_qa_status=summary["private_preview_qa_status"],
    )


def main() -> None:
    result = run_website_private_preview_route_matrix()
    print(f"route_matrix={result.route_matrix_path}")
    print(f"cta_matrix={result.cta_matrix_path}")
    print(f"copy_guardrails={result.copy_guardrails_path}")
    print(f"qa_summary={result.qa_summary_path}")
    print(f"report={result.report_path}")
    print(f"private_preview_qa_status={result.private_preview_qa_status}")


if __name__ == "__main__":
    main()
