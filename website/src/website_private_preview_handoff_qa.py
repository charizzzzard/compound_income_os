from __future__ import annotations

import csv
import hashlib
import re
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.common import ensure_parent_dir, resolve_repo_path
from src.handoff_zip_export import is_forbidden_entry

ZIP_CONTENT_INDEX_OUTPUT = "data/processed/website_private_preview_handoff_zip_content_index.csv"
HANDOFF_QA_SUMMARY_OUTPUT = "data/processed/website_private_preview_handoff_qa_summary.csv"

WEBSITE_README = "website/compound-income-os-landing/README.md"
DEPLOYMENT_NOTES = "website/compound-income-os-landing/DEPLOYMENT_NOTES.md"
PUBLIC_SAMPLE_PAYLOAD = "website/compound-income-os-landing/public/demo/readiness_payload.sample.json"
STRATEGY_REVIEW = "reports/2026-04-26/strategy_review_fundamentals_trust_scoring.md"

REQUIRED_WEBSITE_ENTRIES = (
    "website/compound-income-os-landing/src/App.jsx",
    "website/compound-income-os-landing/src/siteConfig.js",
    WEBSITE_README,
    DEPLOYMENT_NOTES,
    PUBLIC_SAMPLE_PAYLOAD,
)

REQUIRED_SCREENSHOTS = (
    "website/compound-income-os-landing/review_screenshots/01_home_wayfinder.png",
    "website/compound-income-os-landing/review_screenshots/02_workflow_page.png",
    "website/compound-income-os-landing/review_screenshots/03_evidence_page.png",
    "website/compound-income-os-landing/review_screenshots/04_portfolio_page.png",
    "website/compound-income-os-landing/review_screenshots/05_dashboard_page.png",
    "website/compound-income-os-landing/review_screenshots/06_manifesto_page.png",
)

REQUIRED_QA_ARTIFACTS = (
    "data/processed/website_private_preview_route_matrix.csv",
    "data/processed/website_private_preview_cta_matrix.csv",
    "data/processed/website_private_preview_copy_guardrails.csv",
    "data/processed/website_private_preview_qa_summary.csv",
    "data/processed/website_static_build_package_qa.csv",
    "data/processed/website_static_build_package_summary.csv",
    "data/processed/website_private_preview_copy_freeze_matrix.csv",
    "data/processed/website_private_preview_copy_freeze_summary.csv",
    "data/processed/website_private_preview_handoff_index.csv",
    "data/processed/website_private_preview_release_summary.csv",
)

REQUIRED_REPORTS = (
    "reports/2026-04-27/website_private_preview_route_matrix_report.md",
    "reports/2026-04-27/website_static_build_package_report.md",
    "reports/2026-04-27/website_private_preview_copy_freeze_report.md",
    "reports/2026-04-27/website_private_preview_release_notes.md",
    STRATEGY_REVIEW,
)

FINAL_HANDOFF_QA_ARTIFACTS = (
    ZIP_CONTENT_INDEX_OUTPUT,
    HANDOFF_QA_SUMMARY_OUTPUT,
    "reports/2026-04-27/website_private_preview_handoff_qa_report.md",
)

REQUIRED_ENTRIES = REQUIRED_WEBSITE_ENTRIES + REQUIRED_SCREENSHOTS + REQUIRED_QA_ARTIFACTS + REQUIRED_REPORTS
EXPECTED_ENTRIES = REQUIRED_ENTRIES + FINAL_HANDOFF_QA_ARTIFACTS

INDEX_FIELDS = (
    "zip_path",
    "zip_sha256",
    "zip_entry",
    "entry_type",
    "expected",
    "allowed",
    "private_preview_safe",
    "forbidden_entry",
    "reason_codes",
)

SUMMARY_FIELDS = (
    "source_handoff_zip_path",
    "source_handoff_zip_sha256",
    "source_handoff_zip_file_count",
    "forbidden_entries_count",
    "required_entries_missing_count",
    "unexpected_entries_count",
    "screenshots_count",
    "all_main_screenshots_present",
    "release_notes_artifacts_present",
    "copy_freeze_artifacts_present",
    "static_build_qa_artifacts_present",
    "route_matrix_artifacts_present",
    "readiness_payload_present",
    "deployment_notes_present",
    "strategy_review_present",
    "dist_included",
    "deploy_artifacts_included",
    "node_modules_included",
    "env_files_included",
    "private_raw_files_included",
    "private_sec_identity_map_included",
    "private_values_leaked",
    "public_deploy_claim_detected",
    "decision_ready_claim_detected",
    "handoff_qa_status",
    "reason_codes",
)

TEXT_SUFFIXES = (".csv", ".json", ".md", ".txt", ".jsx", ".js", ".mjs")

PRIVATE_VALUE_PATTERNS = (
    r"personal_sec_identity_map\.csv",
    r"personal_sec_scope_review_filled\.csv",
    r"data/raw/private/",
    r"broker exports raw",
    r"private notes?:",
    r"\bsecret[_-]?key\b",
    r"\btoken\s*=",
)

PUBLIC_POSITIVE_PATTERNS = (
    r"\bpublic launch ready\b",
    r"\bpublic[- ]launch[- ]ready\b",
    r"\bready for public deployment\b",
)

DECISION_POSITIVE_PATTERNS = (
    r"\bdecision[- ]ready\b",
    r"\bdecision readiness[^.\n]{0,80}\b(PASS|READY)\b",
    r"\binvestment-ready\b",
    r"\bready to invest\b",
)

ALLOWED_PUBLIC_CONTEXTS = (
    "not public launch ready",
    "public launch remains blocked",
    "public launch still requires",
    "does not mean public-launch readiness",
    "not ready for public deployment",
    "not ready for public launch",
    "does not indicate public launch readiness",
    "does not imply public launch readiness",
    "no page implies decision readiness or public launch readiness",
    "no public deploy has been performed",
    "No public deployment is performed",
)

ALLOWED_DECISION_CONTEXTS = (
    "not decision-ready",
    "not decision ready",
    "no processed row is currently decision-ready",
    "watchlist ranking is not decision-ready",
    "decision readiness is blocked",
    "decision readiness currently blocked",
    "decision readiness blocked",
    "does not mean public-launch readiness or decision readiness",
    "handoff remains separate from decision readiness",
    "does not claim decision readiness",
    "decision-ready claim detected",
    "does not imply decision readiness",
    "no page implies decision readiness",
    "no page implies decision readiness or public launch readiness",
    "does not indicate decision readiness",
)


@dataclass(frozen=True)
class HandoffQaResult:
    index_path: Path
    summary_path: Path
    report_path: Path
    handoff_qa_status: str


def csv_bool(value: bool) -> str:
    return "True" if value else "False"


def yn(value: bool) -> str:
    return "yes" if value else "no"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normalize_entry_name(entry: str) -> str:
    return entry.replace("\\", "/").lstrip("/")


def entry_parts(entry: str) -> set[str]:
    return set(normalize_entry_name(entry).split("/"))


def has_path_segment(entry: str, segment: str) -> bool:
    return segment in entry_parts(entry)


def is_env_file(entry: str) -> bool:
    name = normalize_entry_name(entry).rsplit("/", 1)[-1]
    return name in {".env", ".env.local"} or (name.startswith(".env.") and name.endswith(".local"))


def is_private_raw_entry(entry: str) -> bool:
    name = normalize_entry_name(entry)
    return name.startswith("data/raw/private/") or name.startswith("data/raw/private_")


def is_private_sec_identity_map_entry(entry: str) -> bool:
    return normalize_entry_name(entry).rsplit("/", 1)[-1] == "personal_sec_identity_map.csv"


def is_handoff_forbidden_entry(entry: str) -> bool:
    name = normalize_entry_name(entry)
    return (
        is_forbidden_entry(name)
        or has_path_segment(name, "node_modules")
        or has_path_segment(name, "dist")
        or has_path_segment(name, "deploy_artifacts")
        or is_env_file(name)
        or is_private_raw_entry(name)
        or is_private_sec_identity_map_entry(name)
        or name == "personal_sec_scope_review_filled.csv"
    )


def entry_type(entry: str) -> str:
    name = normalize_entry_name(entry)
    if name.startswith("website/compound-income-os-landing/review_screenshots/") and name.endswith(".png"):
        return "SCREENSHOT"
    if name == PUBLIC_SAMPLE_PAYLOAD or name.startswith("website/compound-income-os-landing/public/demo/"):
        return "PAYLOAD"
    if name in {WEBSITE_README, DEPLOYMENT_NOTES}:
        return "WEBSITE_DOC"
    if name.startswith("website/compound-income-os-landing/src/"):
        return "WEBSITE_SOURCE"
    if name.startswith("data/processed/website_"):
        return "QA_ARTIFACT"
    if name.startswith("reports/"):
        return "REPORT"
    if name.startswith("tests/"):
        return "TEST"
    if name.startswith("src/"):
        return "SRC_MODULE"
    if name.startswith("configs/") or name.endswith((".toml", ".yaml", ".yml", ".json")):
        return "CONFIG"
    if name.startswith("ZIP_REPO_"):
        return "METADATA"
    return "OTHER"


def is_expected_entry(entry: str) -> bool:
    name = normalize_entry_name(entry)
    if name in EXPECTED_ENTRIES:
        return True
    if name in {"README.md", "AGENTS.md", "pyproject.toml", "requirements.txt"} or name.startswith("ZIP_REPO_"):
        return True
    if name.startswith(("src/", "tests/", "docs/", "configs/", "scripts/", "website/")):
        return True
    if name.startswith("data/processed/") and not is_handoff_forbidden_entry(name):
        return True
    return name.startswith("reports/") and not is_handoff_forbidden_entry(name)


def is_allowed_entry(entry: str) -> bool:
    return not is_handoff_forbidden_entry(entry) and is_expected_entry(entry)


def reason_codes_for_entry(entry: str, *, expected: bool, allowed: bool, forbidden: bool) -> str:
    reasons: list[str] = []
    if expected:
        reasons.append("EXPECTED_ENTRY")
    else:
        reasons.append("UNEXPECTED_ENTRY")
    if allowed:
        reasons.append("ALLOWED_ENTRY")
    if forbidden:
        reasons.append("FORBIDDEN_ENTRY")
    if not allowed and not forbidden:
        reasons.append("NOT_ALLOWLISTED")
    return "|".join(reasons)


def index_row(zip_path: str, zip_sha256: str, entry: str, *, expected: bool, allowed: bool, forbidden: bool) -> dict[str, str]:
    return {
        "zip_path": zip_path,
        "zip_sha256": zip_sha256,
        "zip_entry": entry,
        "entry_type": entry_type(entry),
        "expected": yn(expected),
        "allowed": yn(allowed),
        "private_preview_safe": yn(allowed and not forbidden),
        "forbidden_entry": yn(forbidden),
        "reason_codes": reason_codes_for_entry(entry, expected=expected, allowed=allowed, forbidden=forbidden),
    }


def strip_allowed_contexts(text: str, allowed_contexts: tuple[str, ...]) -> str:
    filtered = text.replace("*", "")
    for phrase in allowed_contexts:
        filtered = re.sub(re.escape(phrase), "", filtered, flags=re.IGNORECASE)
    return filtered


def count_patterns(patterns: tuple[str, ...], text: str) -> int:
    return sum(len(re.findall(pattern, text, flags=re.IGNORECASE)) for pattern in patterns)


def public_launch_claim_detected(text: str) -> bool:
    return count_patterns(PUBLIC_POSITIVE_PATTERNS, strip_allowed_contexts(text, ALLOWED_PUBLIC_CONTEXTS)) > 0


def decision_ready_claim_detected(text: str) -> bool:
    return count_patterns(DECISION_POSITIVE_PATTERNS, strip_allowed_contexts(text, ALLOWED_DECISION_CONTEXTS)) > 0


def private_values_leaked(text: str) -> bool:
    return count_patterns(PRIVATE_VALUE_PATTERNS, text) > 0


def text_entry_is_scannable(entry: str) -> bool:
    name = normalize_entry_name(entry)
    if not name.endswith(TEXT_SUFFIXES):
        return False
    if name.startswith("website/compound-income-os-landing/src/"):
        return True
    if name.startswith("website/compound-income-os-landing/public/demo/"):
        return True
    if name in {WEBSITE_README, DEPLOYMENT_NOTES}:
        return True
    if name.startswith("data/processed/website_"):
        return True
    return name.startswith("reports/2026-04-27/website_") or name == STRATEGY_REVIEW


def read_scannable_text(archive: zipfile.ZipFile) -> str:
    chunks: list[str] = []
    for name in sorted(archive.namelist()):
        if not text_entry_is_scannable(name):
            continue
        try:
            chunks.append(archive.read(name).decode("utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(chunks)


def write_csv(path_value: str, fields: tuple[str, ...], rows: list[dict[str, str]]) -> Path:
    path = ensure_parent_dir(path_value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def build_zip_content_index(zip_path: str | Path) -> tuple[list[dict[str, str]], dict[str, object]]:
    source_zip = resolve_repo_path(zip_path)
    source_zip_sha256 = sha256_file(source_zip)
    source_zip_label = source_zip.name
    with zipfile.ZipFile(source_zip, "r") as archive:
        entries = sorted(normalize_entry_name(name) for name in archive.namelist() if name and not name.endswith("/"))
        scannable_text = read_scannable_text(archive)
        archive.testzip()

    rows: list[dict[str, str]] = []
    entry_set = set(entries)
    for entry in entries:
        forbidden = is_handoff_forbidden_entry(entry)
        expected = is_expected_entry(entry)
        allowed = is_allowed_entry(entry)
        rows.append(index_row(source_zip_label, source_zip_sha256, entry, expected=expected, allowed=allowed, forbidden=forbidden))

    for required_entry in REQUIRED_ENTRIES:
        if required_entry in entry_set:
            continue
        rows.append(
            index_row(
                source_zip_label,
                source_zip_sha256,
                required_entry,
                expected=True,
                allowed=False,
                forbidden=False,
            )
            | {"private_preview_safe": "no", "reason_codes": "REQUIRED_ENTRY_MISSING"}
        )

    facts = {
        "zip_path": source_zip_label,
        "zip_sha256": source_zip_sha256,
        "entries": entries,
        "text": scannable_text,
    }
    return rows, facts


def all_present(entries: set[str], required: tuple[str, ...]) -> bool:
    return all(item in entries for item in required)


def build_summary(index_rows: list[dict[str, str]], facts: dict[str, object]) -> dict[str, str]:
    entries = set(facts["entries"])  # type: ignore[arg-type]
    text = str(facts["text"])
    forbidden_count = sum(1 for row in index_rows if row["forbidden_entry"] == "yes")
    required_missing = [entry for entry in REQUIRED_ENTRIES if entry not in entries]
    unexpected_count = sum(
        1
        for row in index_rows
        if row["expected"] == "no" and row["allowed"] == "no" and row["forbidden_entry"] == "no"
    )
    screenshots_count = sum(1 for entry in entries if entry in REQUIRED_SCREENSHOTS)
    public_claim = public_launch_claim_detected(text)
    decision_claim = decision_ready_claim_detected(text)
    private_leak = private_values_leaked(text)

    checks = {
        "dist_included": any(has_path_segment(entry, "dist") for entry in entries),
        "deploy_artifacts_included": any(has_path_segment(entry, "deploy_artifacts") for entry in entries),
        "node_modules_included": any(has_path_segment(entry, "node_modules") for entry in entries),
        "env_files_included": any(is_env_file(entry) for entry in entries),
        "private_raw_files_included": any(is_private_raw_entry(entry) for entry in entries),
        "private_sec_identity_map_included": any(is_private_sec_identity_map_entry(entry) for entry in entries),
        "private_values_leaked": private_leak,
        "public_deploy_claim_detected": public_claim,
        "decision_ready_claim_detected": decision_claim,
    }

    blockers = [name for name, value in checks.items() if value]
    status = "PASS"
    reasons = ["HANDOFF_QA_PASS"]
    if forbidden_count or required_missing or blockers:
        status = "BLOCKED"
        reasons = ["HANDOFF_QA_BLOCKED"]
        if forbidden_count:
            reasons.append("FORBIDDEN_ENTRIES_PRESENT")
        if required_missing:
            reasons.append("REQUIRED_ENTRIES_MISSING")
        reasons.extend(name.upper() for name in blockers)
    elif unexpected_count:
        status = "REVIEW"
        reasons = ["HANDOFF_QA_REVIEW", "UNEXPECTED_ENTRIES_PRESENT"]

    return {
        "source_handoff_zip_path": str(facts["zip_path"]),
        "source_handoff_zip_sha256": str(facts["zip_sha256"]),
        "source_handoff_zip_file_count": str(len(entries)),
        "forbidden_entries_count": str(forbidden_count),
        "required_entries_missing_count": str(len(required_missing)),
        "unexpected_entries_count": str(unexpected_count),
        "screenshots_count": str(screenshots_count),
        "all_main_screenshots_present": csv_bool(all_present(entries, REQUIRED_SCREENSHOTS)),
        "release_notes_artifacts_present": csv_bool(
            all_present(
                entries,
                (
                    "data/processed/website_private_preview_handoff_index.csv",
                    "data/processed/website_private_preview_release_summary.csv",
                    "reports/2026-04-27/website_private_preview_release_notes.md",
                ),
            )
        ),
        "copy_freeze_artifacts_present": csv_bool(
            all_present(
                entries,
                (
                    "data/processed/website_private_preview_copy_freeze_matrix.csv",
                    "data/processed/website_private_preview_copy_freeze_summary.csv",
                    "reports/2026-04-27/website_private_preview_copy_freeze_report.md",
                ),
            )
        ),
        "static_build_qa_artifacts_present": csv_bool(
            all_present(
                entries,
                (
                    "data/processed/website_static_build_package_qa.csv",
                    "data/processed/website_static_build_package_summary.csv",
                    "reports/2026-04-27/website_static_build_package_report.md",
                ),
            )
        ),
        "route_matrix_artifacts_present": csv_bool(
            all_present(
                entries,
                (
                    "data/processed/website_private_preview_route_matrix.csv",
                    "data/processed/website_private_preview_cta_matrix.csv",
                    "data/processed/website_private_preview_copy_guardrails.csv",
                    "data/processed/website_private_preview_qa_summary.csv",
                    "reports/2026-04-27/website_private_preview_route_matrix_report.md",
                ),
            )
        ),
        "readiness_payload_present": csv_bool(PUBLIC_SAMPLE_PAYLOAD in entries),
        "deployment_notes_present": csv_bool(DEPLOYMENT_NOTES in entries),
        "strategy_review_present": csv_bool(STRATEGY_REVIEW in entries),
        **{name: csv_bool(value) for name, value in checks.items()},
        "handoff_qa_status": status,
        "reason_codes": "|".join(reasons),
    }


def write_report(index_rows: list[dict[str, str]], summary: dict[str, str], *, report_date: date | None = None) -> Path:
    day = (report_date or date.today()).isoformat()
    path = ensure_parent_dir(f"reports/{day}/website_private_preview_handoff_qa_report.md")
    missing_required = [row["zip_entry"] for row in index_rows if row["reason_codes"] == "REQUIRED_ENTRY_MISSING"]
    forbidden_entries = [row["zip_entry"] for row in index_rows if row["forbidden_entry"] == "yes"]
    lines = [
        "# Website Private Preview Final Handoff QA",
        "",
        "## Executive Summary",
        "",
        f"- PRIVATE_PREVIEW_HANDOFF_QA: `{summary['handoff_qa_status']}`",
        "- Scope: existing private-preview handoff ZIP content, required artifacts, forbidden entries, and claim/privacy guardrails.",
        "- No website pages, product claims, screenshots, public deployment, or investment logic are added by this QA.",
        "",
        "## Source Handoff ZIP",
        "",
        "- This report indexes the pre-patch handoff ZIP that existed before the final QA patch.",
        f"- Source ZIP: `{summary['source_handoff_zip_path']}`",
        f"- Source ZIP SHA256: `{summary['source_handoff_zip_sha256']}`",
        f"- Source ZIP file count: `{summary['source_handoff_zip_file_count']}`",
        "",
        "## ZIP Content Summary",
        "",
        f"- Forbidden entries: `{summary['forbidden_entries_count']}`",
        f"- Required entries missing: `{summary['required_entries_missing_count']}`",
        f"- Unexpected entries: `{summary['unexpected_entries_count']}`",
        f"- Screenshots: `{summary['screenshots_count']}`",
        "",
        "## Required Entries Check",
        "",
        f"- Required website files present: `{csv_bool(not any(item in missing_required for item in REQUIRED_WEBSITE_ENTRIES))}`",
        f"- Required screenshots present: `{summary['all_main_screenshots_present']}`",
        f"- Required QA artifacts present: `{csv_bool(not any(item in missing_required for item in REQUIRED_QA_ARTIFACTS))}`",
        f"- Required reports present: `{csv_bool(not any(item in missing_required for item in REQUIRED_REPORTS))}`",
        "",
        "## Forbidden Entries Check",
        "",
        f"- `dist/` included: `{summary['dist_included']}`",
        f"- `deploy_artifacts/` included: `{summary['deploy_artifacts_included']}`",
        f"- `node_modules/` included: `{summary['node_modules_included']}`",
        f"- env files included: `{summary['env_files_included']}`",
        f"- private raw files included: `{summary['private_raw_files_included']}`",
        f"- private SEC identity map included: `{summary['private_sec_identity_map_included']}`",
        "",
        "## Screenshot Coverage",
        "",
        f"- All six main screenshots present: `{summary['all_main_screenshots_present']}`",
        "",
        "## QA Artifact Coverage",
        "",
        f"- Release notes artifacts present: `{summary['release_notes_artifacts_present']}`",
        f"- Copy freeze artifacts present: `{summary['copy_freeze_artifacts_present']}`",
        f"- Static build QA artifacts present: `{summary['static_build_qa_artifacts_present']}`",
        f"- Route matrix artifacts present: `{summary['route_matrix_artifacts_present']}`",
        "",
        "## Website / Payload Coverage",
        "",
        f"- Sanitized readiness payload present: `{summary['readiness_payload_present']}`",
        f"- Deployment notes present: `{summary['deployment_notes_present']}`",
        f"- Strategy review present: `{summary['strategy_review_present']}`",
        "",
        "## Claim / Privacy Scan",
        "",
        f"- Private values leaked: `{summary['private_values_leaked']}`",
        f"- Public deploy claim detected: `{summary['public_deploy_claim_detected']}`",
        f"- Decision-ready claim detected: `{summary['decision_ready_claim_detected']}`",
        "",
        "## Handoff QA Decision",
        "",
        f"`PRIVATE_PREVIEW_HANDOFF_QA = {summary['handoff_qa_status']}`",
        f"Reason codes: `{summary['reason_codes']}`",
        "",
        "## Post-Export Note",
        "",
        "A fresh handoff ZIP must be exported after this QA patch is committed. The fresh ZIP hash is intentionally not written back into committed artifacts.",
        "",
        "## Remaining Review Items",
        "",
        "- Public launch remains blocked until real CTA targets, imprint/privacy URLs, pricing/scope review, hosting route fallback validation, and final compliance review are complete.",
        "",
        "## Recommended Next Patch",
        "",
        "`PAUSE WEBSITE SCOPE / RETURN TO FUNDAMENTALS DATA CLOSURE`",
        "",
        "## Missing Required Entries",
        "",
        *(f"- `{entry}`" for entry in missing_required),
        "",
        "## Forbidden Entries",
        "",
        *(f"- `{entry}`" for entry in forbidden_entries),
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_website_private_preview_handoff_qa(
    zip_path: str | Path = "compound_income_os_HANDOFF_20260427-163623_1bb6a1a.zip",
    *,
    report_date: date | None = None,
) -> HandoffQaResult:
    index_rows, facts = build_zip_content_index(zip_path)
    summary = build_summary(index_rows, facts)
    index_path = write_csv(ZIP_CONTENT_INDEX_OUTPUT, INDEX_FIELDS, index_rows)
    summary_path = write_csv(HANDOFF_QA_SUMMARY_OUTPUT, SUMMARY_FIELDS, [summary])
    report_path = write_report(index_rows, summary, report_date=report_date)
    return HandoffQaResult(
        index_path=index_path,
        summary_path=summary_path,
        report_path=report_path,
        handoff_qa_status=summary["handoff_qa_status"],
    )


def main() -> None:
    result = run_website_private_preview_handoff_qa()
    print(f"zip_content_index={result.index_path}")
    print(f"handoff_qa_summary={result.summary_path}")
    print(f"report={result.report_path}")
    print(f"PRIVATE_PREVIEW_HANDOFF_QA={result.handoff_qa_status}")


if __name__ == "__main__":
    main()
