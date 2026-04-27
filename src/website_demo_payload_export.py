from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import ensure_parent_dir, resolve_repo_path

DEFAULT_SOURCE_PAYLOAD = "data/processed/dashboard_readiness_payload.json"
DEFAULT_SAMPLE_OUTPUT = "website/compound-income-os-landing/public/demo/readiness_payload.sample.json"
DEFAULT_README_OUTPUT = "website/compound-income-os-landing/public/demo/README.md"

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
ALLOWED_INTERNAL_TERMS = ("monthly_buy_ranking.csv", "buy_score")
PRIVATE_PATTERNS = (
    r"data/raw/private",
    r"personal_sec_identity_map",
    r"\bCIK[0-9A-Z_-]*\b",
)

WAVE_TWO_EVIDENCE_PAYLOAD: dict[str, Any] = {
    "evidence_page": {
        "route": "/evidence",
        "page": "M3 Evidence & Data Quality",
        "product_mockup": "P3 Evidence Workspace",
        "private_preview_only": True,
        "public_deploy_ready": False,
        "synthetic_demo_values": True,
    },
    "coverage_tiers": [
        {"holding": "MSFT", "profile": "STANDARD", "core": "OK", "valuation": "PARTIAL", "dividend_fcf": "COVERED", "advanced": "PARTIAL", "monthly_action": "WAIT_VALUATION"},
        {"holding": "V", "profile": "STANDARD", "core": "COVERED", "valuation": "OK", "dividend_fcf": "COVERED", "advanced": "OK", "monthly_action": "READY"},
        {"holding": "JNJ", "profile": "STANDARD", "core": "OK", "valuation": "REVIEW", "dividend_fcf": "PARTIAL", "advanced": "PARTIAL", "monthly_action": "REVIEW_CORE_DATA"},
        {"holding": "KO", "profile": "DIVIDEND_QUALITY", "core": "COVERED", "valuation": "PARTIAL", "dividend_fcf": "COVERED", "advanced": "NOT_APPLICABLE", "monthly_action": "HOLD"},
        {"holding": "LIN", "profile": "QUALITY_COMPOUNDER", "core": "OK", "valuation": "MISSING_DATA", "dividend_fcf": "PARTIAL", "advanced": "INSUFFICIENT_HISTORY", "monthly_action": "NOT_READY"},
    ],
    "sec_pipeline_stages": [
        "Scope Prepare",
        "Identity Resolve",
        "Identity Export",
        "CompanyFacts Fetch",
        "Snapshot Ingest",
        "Snapshot Review",
        "Evidence Apply",
    ],
    "evidence_workspace": {
        "run_id": "DEMO-20260427-EVIDENCE",
        "source": "SEC CompanyFacts snapshot",
        "apply_mode": "reviewed only",
        "contains_real_values": False,
        "network_performed": False,
    },
    "status_labels": [
        "COVERED",
        "OK",
        "PARTIAL",
        "REVIEW",
        "NO_MATCH",
        "MISSING_DATA",
        "INSUFFICIENT_INPUTS",
        "INSUFFICIENT_HISTORY",
        "NOT_APPLICABLE",
    ],
    "master_layers": [
        "Base Master",
        "Profiled Master",
        "Evidence-Applied Master",
    ],
}

WAVE_TWO_B_DASHBOARD_PAYLOAD: dict[str, Any] = {
    "dashboard_page": {
        "route": "/dashboard",
        "page": "M5 The Local Dashboard",
        "private_preview_only": True,
        "public_deploy_ready": False,
        "decision_readiness_claimed": False,
        "synthetic_demo_values": True,
    },
    "readiness_strip": {
        "demo": "BLOCKED",
        "decision": "BLOCKED",
        "dashboard": "REVIEW",
        "handoff": "REVIEW",
        "active_blockers": 11,
        "p0_blockers": 6,
        "p1_reviews": 4,
        "next_actions": 5,
    },
    "kpi_groups": [
        "Portfolio / Structure",
        "Score / Fundamentals",
        "Benchmark / Performance",
        "Cost / Tax",
        "Data Quality / Methodology",
    ],
    "scenario_sections": [
        "Dividend Snowball Analysis",
        "Reinvest Comparison",
        "Cashflow Calendar",
        "Multi-Benchmark Context",
        "Cost / Tax Ledger",
    ],
    "guardrails": {
        "no_public_deploy": True,
        "no_private_values": True,
        "no_network": True,
        "not_a_prediction": True,
    },
}

WAVE_THREE_PORTFOLIO_PAYLOAD: dict[str, Any] = {
    "portfolio_page": {
        "route": "/portfolio",
        "page": "M4 Portfolio Model",
        "product_mockup": "P4 Holdings & Sleeves Workspace",
        "private_preview_only": True,
        "public_deploy_ready": False,
        "decision_readiness_claimed": False,
        "synthetic_demo_values": True,
        "not_personal_allocation_guidance": True,
    },
    "sleeves": [
        {"name": "Core ETF", "example_band": "45-60%", "status": "illustrative rule band"},
        {"name": "Dividend Quality ETF", "example_band": "10-25%", "status": "illustrative rule band"},
        {"name": "Single Stock", "example_band": "20-35%", "status": "review required"},
        {"name": "Cash", "example_band": "5-15%", "status": "rule-based reserve"},
    ],
    "portfolio_workspace": {
        "title": "Holdings & Sleeves Workspace",
        "contains_real_allocations": False,
        "contains_private_values": False,
        "risk_rules": [
            "Max single position",
            "Max top-10 weight",
            "Max sector exposure",
            "Minimum cash reserve",
        ],
    },
    "readiness_connection": {
        "decision": "BLOCKED",
        "valuation_inputs": "missing",
        "dividend_fcf_inputs": "missing",
        "core_kpi_review": "open",
        "provenance": "incomplete",
        "watchlist": "sample input active",
    },
    "guardrails": {
        "no_public_deploy": True,
        "no_private_values": True,
        "no_network": True,
        "no_execution_signal": True,
    },
}


@dataclass(frozen=True)
class WebsiteDemoPayloadExportResult:
    sample_output: Path
    readme_output: Path
    decision_status: str
    contains_private_data: bool
    contains_investment_advice: bool


def load_payload(path_value: str | Path) -> dict[str, Any]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Dashboard readiness payload must be a JSON object: {path}")
    return payload


def contains_private_marker(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in PRIVATE_PATTERNS)


def contains_forbidden_display_term(text: str) -> bool:
    filtered = text
    for allowed in ALLOWED_INTERNAL_TERMS:
        filtered = filtered.replace(allowed, "")
    patterns = [re.escape(term).replace("\\ ", r"\s+") for term in FORBIDDEN_DISPLAY_TERMS]
    return bool(re.search(r"(?<![A-Z0-9_])(" + "|".join(patterns) + r")(?![A-Z0-9_])", filtered.upper()))


def assert_payload_safe(payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    if contains_private_marker(encoded):
        raise ValueError("Refusing to export website demo payload: private marker detected.")
    if contains_forbidden_display_term(encoded):
        raise ValueError("Refusing to export website demo payload: restricted market-action wording detected.")
    if payload.get("metadata", {}).get("private_data_included") is True:
        raise ValueError("Refusing to export website demo payload: source metadata reports private data.")
    if payload.get("metadata", {}).get("dummy_claims_included") is True:
        raise ValueError("Refusing to export website demo payload: source metadata reports dummy claims.")
    if payload.get("readiness", {}).get("decision", {}).get("status") == "PASS":
        raise ValueError("Refusing to export website demo payload: decision readiness PASS is not expected for private preview.")


def build_sample_payload(source_payload: dict[str, Any], *, generated_from: str) -> dict[str, Any]:
    return {
        "sample_metadata": {
            "sample_type": "private_preview_readiness_payload",
            "generated_from": generated_from,
            "public_deploy_ready": False,
            "contains_private_data": False,
            "contains_real_portfolio_values": False,
            "contains_investment_advice": False,
            "synthetic_or_sanitized": True,
            "intended_use": "private preview / local demo handoff only",
        },
        "payload": source_payload,
        "website_mockup_wave_two": WAVE_TWO_EVIDENCE_PAYLOAD,
        "website_mockup_wave_two_b": WAVE_TWO_B_DASHBOARD_PAYLOAD,
        "website_mockup_wave_three": WAVE_THREE_PORTFOLIO_PAYLOAD,
    }


def write_sample(path_value: str | Path, sample_payload: dict[str, Any]) -> Path:
    path = ensure_parent_dir(path_value)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(sample_payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def write_readme(path_value: str | Path) -> Path:
    path = ensure_parent_dir(path_value)
    path.write_text(
        "\n".join(
            [
                "# Private Preview Readiness Payload",
                "",
                "This directory contains a static, sanitized readiness sample payload for private demos:",
                "",
                "- `readiness_payload.sample.json`",
                "",
                "The file is derived from local processed readiness artifacts and is intended for private preview/handoff review only.",
                "",
                "It must not contain private raw files, broker exports, private SEC identity maps, private input values, investment advice, or order/execution signals.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def run_website_demo_payload_export(
    *,
    source_payload: str = DEFAULT_SOURCE_PAYLOAD,
    sample_output: str = DEFAULT_SAMPLE_OUTPUT,
    readme_output: str = DEFAULT_README_OUTPUT,
) -> WebsiteDemoPayloadExportResult:
    payload = load_payload(source_payload)
    assert_payload_safe(payload)
    sample_payload = build_sample_payload(payload, generated_from=source_payload)
    sample_text = json.dumps(sample_payload, sort_keys=True)
    if contains_private_marker(sample_text) or contains_forbidden_display_term(sample_text):
        raise ValueError("Refusing to export website demo payload: sample payload failed sanitization.")
    sample_path = write_sample(sample_output, sample_payload)
    readme_path = write_readme(readme_output)
    return WebsiteDemoPayloadExportResult(
        sample_output=sample_path,
        readme_output=readme_path,
        decision_status=str(payload.get("readiness", {}).get("decision", {}).get("status", "NOT_AVAILABLE")),
        contains_private_data=False,
        contains_investment_advice=False,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a sanitized website demo readiness payload.")
    parser.add_argument("--source-payload", default=DEFAULT_SOURCE_PAYLOAD)
    parser.add_argument("--sample-output", default=DEFAULT_SAMPLE_OUTPUT)
    parser.add_argument("--readme-output", default=DEFAULT_README_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_website_demo_payload_export(
        source_payload=args.source_payload,
        sample_output=args.sample_output,
        readme_output=args.readme_output,
    )
    print(f"sample_output={result.sample_output}")
    print(f"readme_output={result.readme_output}")
    print(f"decision_readiness={result.decision_status}")


if __name__ == "__main__":
    main()
