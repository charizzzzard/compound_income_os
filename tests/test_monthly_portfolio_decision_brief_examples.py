from __future__ import annotations

import csv
import json
from pathlib import Path

EXAMPLE_DIR = Path("examples/monthly_portfolio_decision_brief")

EXPECTED_FILES = [
    "README.md",
    "monthly_portfolio_decision_brief_READY.example.json",
    "monthly_portfolio_decision_brief_READY.example.csv",
    "monthly_portfolio_decision_brief_READY.example.md",
    "monthly_portfolio_decision_brief_REVIEW.example.json",
    "monthly_portfolio_decision_brief_REVIEW.example.csv",
    "monthly_portfolio_decision_brief_REVIEW.example.md",
]

CSV_FIELDS = ["section", "item", "status", "value", "source_artifact", "notes"]

FORBIDDEN_PATTERNS = [
    "C:\\",
    "/Users/",
    "/home/",
    ".env",
    "API_KEY",
    "SECRET",
    "TOKEN",
    "BROKER",
    "IBKR",
    "Trade Republic",
    "Scalable",
    "Binance",
]

FORBIDDEN_CLAIMS = [
    "production ready",
    "investment ready",
    "executes orders",
    "live trading enabled",
    "automated buy",
    "automated sell",
]


def _read_example(name: str) -> str:
    return (EXAMPLE_DIR / name).read_text(encoding="utf-8")


def _json_example(status: str) -> dict[str, object]:
    return json.loads(_read_example(f"monthly_portfolio_decision_brief_{status}.example.json"))


def _csv_rows(status: str) -> list[dict[str, str]]:
    text = _read_example(f"monthly_portfolio_decision_brief_{status}.example.csv")
    return list(csv.DictReader(text.splitlines()))


def test_expected_example_files_exist() -> None:
    for name in EXPECTED_FILES:
        assert (EXAMPLE_DIR / name).is_file(), name


def test_json_examples_parse_and_are_marked_synthetic() -> None:
    for status in ("READY", "REVIEW"):
        payload = _json_example(status)

        assert payload["decision_brief_status"] == status
        assert payload["source_module"] == "src.monthly_portfolio_decision_brief"
        assert "Human Operator" in str(payload["operator_acceptance_boundary"])
        assert all(str(row["ticker"]).startswith("SYNTH_") for row in payload["ranking_summary"]["top_rows"])


def test_csv_examples_parse_with_core_columns_and_status() -> None:
    for status in ("READY", "REVIEW"):
        rows = _csv_rows(status)

        assert rows
        assert list(rows[0]) == CSV_FIELDS
        status_row = next(row for row in rows if row["item"] == "decision_brief_status")
        assert status_row["status"] == status
        assert status_row["value"] == status


def test_markdown_examples_contain_sanitized_disclaimer_and_status() -> None:
    for status in ("READY", "REVIEW"):
        text = _read_example(f"monthly_portfolio_decision_brief_{status}.example.md")

        assert "synthetic and sanitized reviewer-facing example" in text
        assert "not a generated\nreal portfolio output" in text
        assert f"decision_brief_status: `{status}`" in text
        assert "Human Operator remains final acceptance authority" in text


def test_ready_example_represents_ready_surface() -> None:
    payload = _json_example("READY")
    rows = _csv_rows("READY")
    markdown = _read_example("monthly_portfolio_decision_brief_READY.example.md")

    assert payload["decision_brief_status"] == "READY"
    assert payload["portfolio_decision_readiness"]["decision_brief_status"] == "READY"
    assert "decision_brief_status: `READY`" in markdown
    assert next(row for row in rows if row["item"] == "decision_brief_status")["value"] == "READY"


def test_review_example_preserves_optional_evidence_gaps() -> None:
    payload = _json_example("REVIEW")
    text = json.dumps(payload, sort_keys=True) + _read_example("monthly_portfolio_decision_brief_REVIEW.example.md")

    assert payload["decision_brief_status"] == "REVIEW"
    for state in ("MISSING", "STALE", "UNKNOWN", "REVIEW_REQUIRED", "NOT_AVAILABLE"):
        assert state in text
    assert payload["decision_quality_summary"]["process_confidence_not_investment_confidence"] is True


def test_examples_do_not_contain_forbidden_private_or_local_patterns() -> None:
    for path in sorted(EXAMPLE_DIR.iterdir()):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            assert pattern not in text, f"{path}: {pattern}"


def test_examples_do_not_claim_execution_or_readiness() -> None:
    for path in sorted(EXAMPLE_DIR.iterdir()):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").lower()
        for claim in FORBIDDEN_CLAIMS:
            assert claim not in text, f"{path}: {claim}"


def test_contract_points_to_sanitized_examples_without_changing_generated_boundary() -> None:
    text = Path("docs/contracts/MONTHLY_PORTFOLIO_DECISION_BRIEF_CONTRACT.md").read_text(encoding="utf-8")
    compact = " ".join(text.split())

    assert "examples/monthly_portfolio_decision_brief/" in text
    assert "reviewer-facing documentation artifacts only" in compact
    assert "data/processed/monthly_portfolio_decision_brief.json" in text
    assert "reports/<as_of_date>/monthly_portfolio_decision_brief.md" in text
