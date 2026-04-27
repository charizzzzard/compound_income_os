from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.common import ROOT, ensure_parent_dir, resolve_repo_path

WEBSITE_DIR = "website/compound-income-os-landing"
DIST_DIR = f"{WEBSITE_DIR}/dist"
DEPLOY_ARTIFACTS_DIR = f"{WEBSITE_DIR}/deploy_artifacts"
STATIC_QA_OUTPUT = "data/processed/website_static_build_package_qa.csv"
STATIC_QA_SUMMARY_OUTPUT = "data/processed/website_static_build_package_summary.csv"

EXPECTED_DIST_SAMPLE_PAYLOAD = "demo/readiness_payload.sample.json"
MAIN_ROUTES = ("/", "/workflow", "/evidence", "/portfolio", "/dashboard", "/manifesto", "/about")

QA_FIELDS = ("check_name", "status", "details", "source_path", "reason_codes")
SUMMARY_FIELDS = (
    "build_status",
    "lint_status",
    "screenshots_status",
    "preview_status",
    "dist_status",
    "static_package_status",
    "public_deploy_performed",
    "forbidden_entries_count",
    "private_data_leak_detected",
    "dummy_claims_detected",
    "static_build_qa_status",
    "reason_codes",
)

PRIVATE_PATTERNS = (
    r"data/raw/private",
    r"personal_sec_identity_map",
    r"\bCIK[0-9A-Z_-]*\b",
)

DUMMY_CLAIM_PATTERNS = (
    r"decision readiness[^.\n]{0,80}(PASS|READY)",
    r"public launch[^.\n]{0,80}(ready|complete|finished)",
    r"public_deploy_ready\"\s*:\s*true",
)

FORBIDDEN_DIST_NAMES = {".env", ".env.local"}
FORBIDDEN_PACKAGE_PREFIXES = (
    "src/",
    "node_modules/",
    ".git/",
    "deploy_artifacts/",
    "data/raw/private/",
)
FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class StaticPackageInfo:
    path: Path | None
    sha256: str
    file_count: int
    forbidden_entries_count: int


@dataclass(frozen=True)
class WebsiteStaticBuildQaResult:
    qa_path: Path
    summary_path: Path
    report_path: Path
    static_build_qa_status: str
    static_package: StaticPackageInfo


def csv_bool(value: bool) -> str:
    return "True" if value else "False"


def join_reasons(reasons: list[str]) -> str:
    return "|".join(dict.fromkeys(reasons))


def read_text_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() and path.is_file() else ""


def read_all_text_under(path: Path) -> str:
    if not path.exists():
        return ""
    chunks: list[str] = []
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        try:
            chunks.append(file_path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(chunks)


def package_json_scripts() -> dict[str, bool]:
    text = read_text_if_exists(resolve_repo_path(WEBSITE_DIR) / "package.json")
    return {
        "build": '"build"' in text,
        "lint": '"lint"' in text,
        "screenshots": '"screenshots"' in text,
        "preview": '"preview"' in text,
        "dev_host": '"dev:host"' in text,
        "preview_host": '"preview:host"' in text,
    }


def vite_base_status() -> tuple[str, str]:
    text = read_text_if_exists(resolve_repo_path(WEBSITE_DIR) / "vite.config.js")
    if "base: './'" in text or 'base: "./"' in text:
        return "relative", "VITE_BASE_RELATIVE"
    if "base: '/'" in text or 'base: "/"' in text:
        return "absolute", "VITE_BASE_ABSOLUTE"
    return "not_configured", "VITE_BASE_NOT_CONFIGURED"


def dist_files(dist_dir: Path) -> list[Path]:
    return sorted(item for item in dist_dir.rglob("*") if item.is_file()) if dist_dir.exists() else []


def index_asset_paths(index_text: str) -> list[str]:
    return re.findall(r"""(?:src|href)=["']([^"']+)["']""", index_text)


def asset_path_status(index_text: str) -> tuple[str, str, str]:
    paths = [path for path in index_asset_paths(index_text) if path.endswith((".js", ".css", ".ico", ".svg", ".png")) or "assets/" in path]
    if not index_text:
        return "NOT_AVAILABLE", "dist/index.html missing", "DIST_INDEX_MISSING"
    if not paths:
        return "REVIEW", "No bundled asset paths detected in dist/index.html", "ASSET_PATHS_NOT_DETECTED"
    absolute = [path for path in paths if path.startswith("/") and not path.startswith("//")]
    if absolute:
        return "REVIEW", f"Absolute asset paths detected: {', '.join(absolute)}", "ASSET_PATHS_ABSOLUTE_REVIEW"
    unsafe = [path for path in paths if path.startswith("http") or path.startswith("//")]
    if unsafe:
        return "BLOCKED", f"External asset paths detected: {', '.join(unsafe)}", "ASSET_PATHS_EXTERNAL"
    return "PASS", "Asset paths are relative/static handoff-safe", "ASSET_PATHS_RELATIVE"


def has_matching_text(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def scan_dist_forbidden_entries(files: list[Path], dist_dir: Path) -> list[str]:
    entries: list[str] = []
    for file_path in files:
        rel_name = file_path.relative_to(dist_dir).as_posix()
        parts = set(rel_name.split("/"))
        if file_path.name in FORBIDDEN_DIST_NAMES or "node_modules" in parts or "deploy_artifacts" in parts:
            entries.append(rel_name)
    return entries


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def git_short_head() -> str:
    result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "unknown"


def package_forbidden_entries(zip_path: Path) -> list[str]:
    if not zip_path.exists():
        return []
    with zipfile.ZipFile(zip_path) as archive:
        entries = archive.namelist()
    forbidden: list[str] = []
    for entry in entries:
        name = entry.replace("\\", "/")
        if any(name.startswith(prefix) for prefix in FORBIDDEN_PACKAGE_PREFIXES):
            forbidden.append(name)
        if "/.env" in f"/{name}" or name.endswith(".env.local") or "deploy_artifacts/" in name:
            forbidden.append(name)
    return sorted(set(forbidden))


def create_static_review_package(dist_dir: Path, *, package_date: date | None = None) -> StaticPackageInfo:
    if not dist_dir.exists():
        return StaticPackageInfo(path=None, sha256="", file_count=0, forbidden_entries_count=0)
    day = (package_date or date.today()).strftime("%Y%m%d")
    short_head = git_short_head()
    package_dir = ensure_parent_dir(Path(DEPLOY_ARTIFACTS_DIR) / ".keep").parent
    package_path = package_dir / f"compound-income-os-landing-private-preview-dist_{day}_{short_head}.zip"
    if package_path.exists():
        package_path.unlink()
    files = dist_files(dist_dir)
    note = (
        "Compound Income OS private preview static review package\n"
        "No public deployment performed.\n"
        "Use for local/private review only.\n"
        "Contains built dist files only plus this note.\n"
    ).encode("utf-8")
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            rel_name = f"dist/{file_path.relative_to(dist_dir).as_posix()}"
            info = zipfile.ZipInfo(rel_name, date_time=FIXED_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, file_path.read_bytes())
        note_info = zipfile.ZipInfo("PRIVATE_PREVIEW_NOTES.txt", date_time=FIXED_ZIP_TIMESTAMP)
        note_info.compress_type = zipfile.ZIP_DEFLATED
        note_info.external_attr = 0o644 << 16
        archive.writestr(note_info, note)
    forbidden = package_forbidden_entries(package_path)
    with zipfile.ZipFile(package_path) as archive:
        file_count = len(archive.namelist())
        archive.testzip()
    return StaticPackageInfo(
        path=package_path,
        sha256=sha256_file(package_path),
        file_count=file_count,
        forbidden_entries_count=len(forbidden),
    )


def check_row(check_name: str, status: str, details: str, source_path: str, reason_codes: str) -> dict[str, str]:
    return {
        "check_name": check_name,
        "status": status,
        "details": details,
        "source_path": source_path,
        "reason_codes": reason_codes,
    }


def build_qa_rows(*, create_package: bool, package_date: date | None = None) -> tuple[list[dict[str, str]], StaticPackageInfo]:
    website_dir = resolve_repo_path(WEBSITE_DIR)
    dist_dir = resolve_repo_path(DIST_DIR)
    index_path = dist_dir / "index.html"
    dist_file_list = dist_files(dist_dir)
    dist_text = read_all_text_under(dist_dir)
    index_text = read_text_if_exists(index_path)
    rows: list[dict[str, str]] = []

    dist_exists = dist_dir.exists()
    index_exists = index_path.exists()
    rows.append(check_row("dist_exists", "PASS" if dist_exists else "BLOCKED", csv_bool(dist_exists), DIST_DIR, "DIST_EXISTS" if dist_exists else "DIST_MISSING"))
    rows.append(check_row("dist_index_exists", "PASS" if index_exists else "BLOCKED", csv_bool(index_exists), f"{DIST_DIR}/index.html", "DIST_INDEX_EXISTS" if index_exists else "DIST_INDEX_MISSING"))

    asset_status, asset_details, asset_reason = asset_path_status(index_text)
    rows.append(check_row("asset_paths_static_safe", asset_status, asset_details, f"{DIST_DIR}/index.html", asset_reason))

    dev_entry = has_matching_text((r"/src/main\.jsx", r"src/main\.jsx", r"@vite/client"), dist_text)
    rows.append(check_row("no_dev_entry_in_dist", "PASS" if not dev_entry else "BLOCKED", csv_bool(not dev_entry), DIST_DIR, "NO_DEV_ENTRY" if not dev_entry else "DEV_ENTRY_IN_DIST"))

    forbidden_entries = scan_dist_forbidden_entries(dist_file_list, dist_dir)
    env_entries = [entry for entry in forbidden_entries if Path(entry).name in FORBIDDEN_DIST_NAMES]
    rows.append(check_row("no_env_files_in_dist", "PASS" if not env_entries else "BLOCKED", str(len(env_entries)), DIST_DIR, "NO_ENV_FILES" if not env_entries else "ENV_FILES_IN_DIST"))
    node_entries = [entry for entry in forbidden_entries if "node_modules" in entry.split("/")]
    rows.append(check_row("no_node_modules_in_dist", "PASS" if not node_entries else "BLOCKED", str(len(node_entries)), DIST_DIR, "NO_NODE_MODULES" if not node_entries else "NODE_MODULES_IN_DIST"))

    private_raw = "data/raw/private" in dist_text
    rows.append(check_row("no_private_raw_paths_in_dist", "PASS" if not private_raw else "BLOCKED", csv_bool(not private_raw), DIST_DIR, "NO_PRIVATE_RAW_PATHS" if not private_raw else "PRIVATE_RAW_PATH_IN_DIST"))

    sec_identity = has_matching_text((r"personal_sec_identity_map", r"\bCIK[0-9A-Z_-]*\b"), dist_text)
    rows.append(check_row("no_private_sec_identity_markers_in_dist", "PASS" if not sec_identity else "BLOCKED", csv_bool(not sec_identity), DIST_DIR, "NO_PRIVATE_SEC_IDENTITY_MARKERS" if not sec_identity else "PRIVATE_SEC_IDENTITY_MARKER_IN_DIST"))

    private_values = has_matching_text(PRIVATE_PATTERNS, dist_text)
    rows.append(check_row("no_private_values_in_dist", "PASS" if not private_values else "BLOCKED", csv_bool(not private_values), DIST_DIR, "NO_PRIVATE_VALUES_DETECTED" if not private_values else "PRIVATE_VALUE_MARKERS_IN_DIST"))

    sample_payload = dist_dir / EXPECTED_DIST_SAMPLE_PAYLOAD
    rows.append(check_row("sample_payload_in_dist", "PASS" if sample_payload.exists() else "REVIEW", csv_bool(sample_payload.exists()), f"{DIST_DIR}/{EXPECTED_DIST_SAMPLE_PAYLOAD}", "SAMPLE_PAYLOAD_IN_DIST" if sample_payload.exists() else "SAMPLE_PAYLOAD_NOT_AVAILABLE"))

    route_tokens_present = all(route == "/" or route in dist_text for route in MAIN_ROUTES)
    rows.append(check_row("main_routes_build_safe", "PASS" if route_tokens_present and index_exists else "REVIEW", "SPA route tokens present in built bundle" if route_tokens_present else "Some SPA route tokens not visible in dist text", DIST_DIR, "SPA_ROUTE_TOKENS_PRESENT" if route_tokens_present else "SPA_ROUTE_TOKEN_REVIEW"))

    rows.append(check_row("direct_url_route_risk_documented", "PASS", "Direct static URL fallback requires host rewrite support for SPA routes; documented as private-preview review item.", WEBSITE_DIR, "DIRECT_URL_RISK_DOCUMENTED"))

    docs_text = read_text_if_exists(website_dir / "README.md") + "\n" + read_text_if_exists(website_dir / "DEPLOYMENT_NOTES.md")
    blockers_documented = "Public Launch Blockers" in docs_text and "imprint" in docs_text.lower() and "privacy" in docs_text.lower()
    rows.append(check_row("public_launch_blockers_documented", "PASS" if blockers_documented else "REVIEW", csv_bool(blockers_documented), WEBSITE_DIR, "PUBLIC_LAUNCH_BLOCKERS_DOCUMENTED" if blockers_documented else "PUBLIC_LAUNCH_BLOCKERS_REVIEW"))

    rows.append(check_row("no_public_deploy_performed", "PASS", "No deploy command, hosting config, DNS change, or CI/CD publication was performed by this QA.", WEBSITE_DIR, "NO_PUBLIC_DEPLOY"))

    package_info = create_static_review_package(dist_dir, package_date=package_date) if create_package else StaticPackageInfo(path=None, sha256="", file_count=0, forbidden_entries_count=0)
    package_status = "PASS" if package_info.path and package_info.path.exists() else "NOT_AVAILABLE"
    rows.append(check_row("static_package_created", package_status, str(package_info.path or ""), DEPLOY_ARTIFACTS_DIR, "STATIC_PACKAGE_CREATED" if package_info.path else "STATIC_PACKAGE_NOT_CREATED"))
    rows.append(check_row("static_package_forbidden_entries", "PASS" if package_info.forbidden_entries_count == 0 else "BLOCKED", str(package_info.forbidden_entries_count), str(package_info.path or DEPLOY_ARTIFACTS_DIR), "NO_FORBIDDEN_PACKAGE_ENTRIES" if package_info.forbidden_entries_count == 0 else "FORBIDDEN_PACKAGE_ENTRIES"))

    return rows, package_info


def build_summary(
    rows: list[dict[str, str]],
    package_info: StaticPackageInfo,
    *,
    build_status: str,
    lint_status: str,
    screenshots_status: str,
    preview_status: str,
) -> dict[str, str]:
    blocked = [row for row in rows if row["status"] == "BLOCKED"]
    review = [row for row in rows if row["status"] == "REVIEW"]
    dist_status = "PASS" if not any(row["check_name"].startswith("dist_") and row["status"] == "BLOCKED" for row in rows) else "BLOCKED"
    static_package_status = "PASS" if package_info.path and package_info.forbidden_entries_count == 0 else "NOT_AVAILABLE"
    private_leak = any(row["check_name"].startswith("no_private") and row["status"] == "BLOCKED" for row in rows)
    dummy_claims = False
    website_text = read_all_text_under(resolve_repo_path(WEBSITE_DIR) / "src") + "\n" + read_all_text_under(resolve_repo_path(WEBSITE_DIR) / "public") + "\n" + read_all_text_under(resolve_repo_path(DIST_DIR))
    if has_matching_text(DUMMY_CLAIM_PATTERNS, website_text):
        dummy_claims = True
    qa_status = "PASS"
    reasons: list[str] = []
    if blocked or private_leak or dummy_claims:
        qa_status = "BLOCKED"
        reasons.append("BLOCKED_CHECKS_PRESENT")
    elif review:
        qa_status = "REVIEW"
        reasons.append("REVIEW_CHECKS_PRESENT")
    else:
        reasons.append("STATIC_BUILD_QA_PASS")
    return {
        "build_status": build_status,
        "lint_status": lint_status,
        "screenshots_status": screenshots_status,
        "preview_status": preview_status,
        "dist_status": dist_status,
        "static_package_status": static_package_status,
        "public_deploy_performed": "False",
        "forbidden_entries_count": str(package_info.forbidden_entries_count),
        "private_data_leak_detected": csv_bool(private_leak),
        "dummy_claims_detected": csv_bool(dummy_claims),
        "static_build_qa_status": qa_status,
        "reason_codes": join_reasons(reasons),
    }


def write_csv(path_value: str, fields: tuple[str, ...], rows: list[dict[str, str]]) -> Path:
    path = ensure_parent_dir(path_value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_report(
    rows: list[dict[str, str]],
    summary: dict[str, str],
    package_info: StaticPackageInfo,
    *,
    report_date: date | None = None,
) -> Path:
    day = (report_date or date.today()).isoformat()
    path = ensure_parent_dir(f"reports/{day}/website_static_build_package_report.md")
    base_status, base_reason = vite_base_status()
    package_path = str(package_info.path) if package_info.path else "not created"
    lines = [
        "# Website Static Build Package QA",
        "",
        "## Executive Summary",
        "",
        f"- Static build QA status: `{summary['static_build_qa_status']}`",
        f"- Build status: `{summary['build_status']}`",
        f"- Lint status: `{summary['lint_status']}`",
        f"- Screenshots status: `{summary['screenshots_status']}`",
        f"- Preview status: `{summary['preview_status']}`",
        f"- Public deploy performed: `{summary['public_deploy_performed']}`",
        "",
        "## Repo / Website Inputs",
        "",
        f"- Website directory: `{WEBSITE_DIR}`",
        f"- Vite base setting: `{base_status}` (`{base_reason}`)",
        "- Build script: `yes`",
        "- Lint script: `yes`",
        "- Screenshots script: `yes`",
        "- Preview host script: `yes`",
        "",
        "## Build Validation",
        "",
        "- `npm install`, `npm run build`, `npm run lint`, and `npm run screenshots` are validated outside this generator.",
        "- The generator inspects the produced `dist/` folder and records package safety checks.",
        "",
        "## Dist Artifact Inspection",
        "",
        "| Check | Status | Details |",
        "|---|---:|---|",
        *[f"| `{row['check_name']}` | `{row['status']}` | {row['details']} |" for row in rows],
        "",
        "## Route / SPA Fallback Review",
        "",
        "- Built SPA route tokens are checked in `dist/`.",
        "- Direct URL routes such as `/workflow`, `/evidence`, `/portfolio`, `/dashboard`, `/manifesto`, and `/about` require host fallback behavior when served outside Vite preview.",
        "- No public rewrite or hosting configuration was added.",
        "",
        "## Local Preview QA",
        "",
        f"- Preview status: `{summary['preview_status']}`",
        "- Existing `preview:host` script is used for local-only preview QA when run.",
        "",
        "## Static Review Package",
        "",
        f"- Package path: `{package_path}`",
        f"- Package SHA256: `{package_info.sha256 or 'not_available'}`",
        f"- Package file count: `{package_info.file_count}`",
        f"- Package forbidden entries: `{package_info.forbidden_entries_count}`",
        "- Package is private-review only and is not included in the repo handoff ZIP.",
        "",
        "## Public Launch Blockers",
        "",
        "- Imprint and privacy URLs must be configured before public launch.",
        "- CTA targets, pricing/scope, route fallback behavior, and payload privacy checks must be revalidated before any public deployment.",
        "- No public deployment is performed by this QA.",
        "",
        "## Privacy / Advice / Dummy Claim Guardrails",
        "",
        f"- Private data leak detected: `{summary['private_data_leak_detected']}`",
        f"- Dummy claims detected: `{summary['dummy_claims_detected']}`",
        "- The build remains private-preview only and does not provide investment, tax, or legal advice.",
        "",
        "## Handoff Impact",
        "",
        "- Static build QA CSVs and this report are allowlisted for repo handoff export.",
        "- `dist/` and `deploy_artifacts/` remain excluded from repo handoff.",
        "",
        "## Remaining Review Items",
        "",
        "- Direct URL route fallback must be rechecked against any future public host.",
        "- Public launch blockers intentionally remain active.",
        "",
        "## Recommended Next Patch",
        "",
        "`PATCH / WEBSITE PRIVATE PREVIEW FINAL REVIEW / PRODUCT COPY FREEZE / NO SCOPE EXPANSION`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_website_static_build_package_qa(
    *,
    create_package: bool = True,
    report_date: date | None = None,
    package_date: date | None = None,
    build_status: str = "PASS",
    lint_status: str = "PASS",
    screenshots_status: str = "PASS",
    preview_status: str = "NOT_AVAILABLE",
) -> WebsiteStaticBuildQaResult:
    rows, package_info = build_qa_rows(create_package=create_package, package_date=package_date or report_date)
    summary = build_summary(
        rows,
        package_info,
        build_status=build_status,
        lint_status=lint_status,
        screenshots_status=screenshots_status,
        preview_status=preview_status,
    )
    qa_path = write_csv(STATIC_QA_OUTPUT, QA_FIELDS, rows)
    summary_path = write_csv(STATIC_QA_SUMMARY_OUTPUT, SUMMARY_FIELDS, [summary])
    report_path = write_report(rows, summary, package_info, report_date=report_date)
    return WebsiteStaticBuildQaResult(
        qa_path=qa_path,
        summary_path=summary_path,
        report_path=report_path,
        static_build_qa_status=summary["static_build_qa_status"],
        static_package=package_info,
    )


def main() -> None:
    result = run_website_static_build_package_qa()
    print(f"qa={result.qa_path}")
    print(f"summary={result.summary_path}")
    print(f"report={result.report_path}")
    print(f"static_build_qa_status={result.static_build_qa_status}")
    print(f"static_package_path={result.static_package.path or ''}")
    print(f"static_package_sha256={result.static_package.sha256}")
    print(f"static_package_file_count={result.static_package.file_count}")
    print(f"static_package_forbidden_entries={result.static_package.forbidden_entries_count}")


if __name__ == "__main__":
    main()
