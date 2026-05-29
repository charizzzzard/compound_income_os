from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "docs" / "contracts" / "DASHBOARD_FRESHNESS_SURFACE_CONTRACT.md"
DATA_FRESHNESS_CONTRACT = ROOT / "docs" / "contracts" / "DATA_FRESHNESS_STALENESS_CONTRACT.md"
DASHBOARD_SURFACE_CONTRACT = ROOT / "docs" / "contracts" / "DASHBOARD_OPERATOR_SURFACE_CONTRACT.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


def extract_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start_index: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start_index = index
            break
    if start_index is None:
        raise AssertionError(f"Missing section: {heading}")
    end_index = len(lines)
    for index in range(start_index + 1, len(lines)):
        if lines[index].startswith("## "):
            end_index = index
            break
    return "\n".join(lines[start_index:end_index])


class DashboardFreshnessSurfaceContractTests(unittest.TestCase):
    def test_dashboard_freshness_surface_contract_exists(self) -> None:
        self.assertTrue(CONTRACT_PATH.exists())

    def test_required_sections_exist(self) -> None:
        text = read(CONTRACT_PATH)

        for section in [
            "# Dashboard Freshness Surface Contract",
            "## Purpose",
            "## Contract Position",
            "## Operator Surface Scope",
            "## Required Freshness Surface Fields",
            "## Allowed Freshness States",
            "## Surface Status Mapping",
            "## Artifact Visibility",
            "## No Silent Normalization",
            "## Acceptance Criteria For Future Operator Surface Hardening",
            "## Explicit Non-Scope",
            "## Human Operator Authority",
        ]:
            with self.subTest(section=section):
                self.assertIn(section, text)

    def test_contract_references_parent_contracts(self) -> None:
        text = read(CONTRACT_PATH)

        self.assertIn("DATA_FRESHNESS_STALENESS_CONTRACT.md", text)
        self.assertIn("DASHBOARD_OPERATOR_SURFACE_CONTRACT.md", text)
        self.assertIn("does not replace either parent contract", normalized(text))

    def test_required_freshness_states_are_defined(self) -> None:
        text = read(CONTRACT_PATH)

        for state in [
            "FRESH",
            "STALE",
            "MISSING",
            "UNKNOWN",
            "REVIEW_REQUIRED",
            "NOT_APPLICABLE",
            "NOT_AVAILABLE",
            "PARTIAL",
        ]:
            with self.subTest(state=state):
                self.assertIn(f"`{state}`", text)

    def test_no_silent_normalization_language_exists(self) -> None:
        text = read(CONTRACT_PATH)
        compact = normalized(text)

        self.assertIn("must never be silently normalized to `pass`", compact)
        self.assertIn("do not convert `stale`/`missing`/`unknown`/`review_required`/`partial`/`not_available` to `pass`", compact)
        self.assertIn("do not convert `stale`/`missing`/`unknown`/`review_required`/`partial`/`not_available` to `ok`", compact)
        self.assertIn("do not impute freshness counts", compact)
        self.assertIn("do not overwrite accepted facts silently", compact)

    def test_required_surface_fields_are_defined(self) -> None:
        text = read(CONTRACT_PATH)

        for field in [
            "data_freshness_status",
            "data_freshness_review_required",
            "data_freshness_artifact_status",
            "data_freshness_artifact_reason",
            "data_freshness_expected",
            "data_freshness_fresh_count",
            "data_freshness_stale_count",
            "data_freshness_missing_count",
            "data_freshness_unknown_count",
            "data_freshness_review_required_count",
            "data_freshness_not_applicable_count",
            "data_freshness_source_artifact",
            "operator_attention_required",
            "operator_attention_reasons",
        ]:
            with self.subTest(field=field):
                self.assertIn(field, text)

    def test_future_hardening_acceptance_criteria_exist(self) -> None:
        text = read(CONTRACT_PATH)
        compact = normalized(text)

        self.assertIn("dashboard_freshness_operator_surface_hardening", compact)
        for phrase in [
            "tests for `fresh`",
            "tests for `stale`",
            "tests for `missing`",
            "tests for `unknown`",
            "tests for `review_required`",
            "tests for `not_applicable`",
            "tests for `not_available`",
            "tests for `partial` / missing expected artifact",
            "tests proving no silent `pass` normalization",
            "tests proving `operator_attention_reasons` remain stable",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, compact)

    def test_future_hardening_requires_missing_unreadable_not_selected_distinguishability(self) -> None:
        section = normalized(
            extract_section(
                read(CONTRACT_PATH),
                "## Acceptance Criteria For Future Operator Surface Hardening",
            )
        )

        for phrase in [
            "missing",
            "unreadable",
            "not-selected",
            "distinguishable",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)

    def test_explicit_non_scope_exists(self) -> None:
        text = normalized(read(CONTRACT_PATH))

        for phrase in [
            "dashboard ui server",
            "web app implementation",
            "broker integration",
            "order execution",
            "buy/sell automation",
            "investment advice",
            "valuation automation",
            "dcf engine",
            "provider/api integration",
            "scraping/crawling",
            "replay/backtesting/simulation",
            "outcome attribution",
            "score/ranking/portfolio-rule changes",
            "runtime enforcement",
            "production/product/investment readiness claims",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_human_operator_authority_exists(self) -> None:
        text = normalized(read(CONTRACT_PATH))

        self.assertIn("the human operator remains final acceptance authority", text)
        self.assertIn("visibility and reviewability only", text)
        self.assertIn("does not authorize investment action", text)

    def test_parent_contracts_cross_reference_dashboard_freshness_surface_contract(self) -> None:
        for path in [DATA_FRESHNESS_CONTRACT, DASHBOARD_SURFACE_CONTRACT]:
            with self.subTest(path=path):
                self.assertIn("DASHBOARD_FRESHNESS_SURFACE_CONTRACT.md", read(path))


if __name__ == "__main__":
    unittest.main()
