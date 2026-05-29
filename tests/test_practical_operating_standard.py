from __future__ import annotations

import unittest
from pathlib import Path


STANDARD_PATH = Path("docs/governance/CIOS_PRACTICAL_OPERATING_STANDARD.md")


def read_standard() -> str:
    return STANDARD_PATH.read_text(encoding="utf-8")


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


class PracticalOperatingStandardTests(unittest.TestCase):
    def test_standard_exists_and_required_sections_are_present(self) -> None:
        self.assertTrue(STANDARD_PATH.exists())
        text = read_standard()

        for heading in [
            "# CIOS Practical Operating Standard",
            "## Purpose",
            "## Core Rule",
            "## Source-Of-Truth Precedence",
            "## GitHub And Central Handoff Packet Usage",
            "## Normal Patch Lifecycle",
            "## Preflight Requirements",
            "## Targeted Validation",
            "## Handoff Regeneration Rules",
            "## External LLM Review Protocol",
            "## Operator Acceptance Protocol",
            "## Allowed Metadata-Only Head Offsets",
            "## Forbidden Parallel Handoffs",
            "## Required Final Report Structure",
            "## Minimum Validation Commands",
            "## Residual Risk Handling",
            "## Acceptance Threshold",
            "## Practical Default For Future CIOS Work",
            "## Final Non-Claims",
        ]:
            with self.subTest(heading=heading):
                self.assertIn(heading, text)

    def test_source_of_truth_precedence_and_handoff_boundary_are_explicit(self) -> None:
        text = read_standard()
        compact = normalized(text)

        for phrase in [
            "Committed Git repository state",
            "external_review_packet/HANDOFF_LATEST_CONTEXT.md",
            "external_review_packet/HANDOFF_LATEST.zip",
            "external_review_packet/HANDOFF_LATEST.sha256",
            "HANDOFF_VALIDATION.txt",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        for phrase in [
            "outputs/` only as local generated evidence",
            "forbidden parallel handoffs",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, compact)

    def test_push_and_remote_publication_status_fields_are_required(self) -> None:
        text = read_standard()

        for token in [
            "push_status",
            "PUSHED",
            "NOT_PUSHED",
            "NOT_CHECKED",
            "NOT_APPLICABLE",
            "remote_main_contains_head",
            "YES",
            "NO",
        ]:
            with self.subTest(token=token):
                self.assertIn(token, text)

        self.assertIn("Remote publication status must not be inferred from local commit state alone.", text)

    def test_external_review_finding_severities_are_canonicalized(self) -> None:
        text = read_standard()
        compact = normalized(text)

        for severity in ["BLOCKER", "MAJOR", "MINOR", "INFO"]:
            with self.subTest(severity=severity):
                self.assertIn(f"`{severity}`", text)

        self.assertIn("findings must use exactly these severities", compact)
        self.assertIn("alternative labels", compact)
        self.assertIn("mapped explicitly", compact)

    def test_missing_stale_unknown_data_visibility_invariant_exists(self) -> None:
        text = read_standard()
        compact = normalized(text)

        self.assertIn("Missing Stale Unknown Data Visibility Invariant", text)
        self.assertIn("missing, stale or unknown data must remain visible", compact)
        self.assertIn("must not be silently imputed", compact)
        self.assertIn("overwritten", compact)
        self.assertIn("suppressed", compact)
        self.assertIn("converted into accepted facts", compact)

        for area in [
            "data-contract work",
            "dashboard work",
            "report work",
            "evidence work",
            "valuation work",
            "portfolio work",
            "watchlist work",
            "ranking work",
            "decision-journal work",
        ]:
            with self.subTest(area=area):
                self.assertIn(area, compact)

    def test_final_non_claims_preserve_non_scope(self) -> None:
        compact = normalized(read_standard())

        for phrase in [
            "does not implement runtime enforcement",
            "does not claim",
            "production readiness",
            "product readiness",
            "investment readiness",
            "broker readiness",
            "provider/api readiness",
            "order execution capability",
            "buy/sell automation",
            "runtime enforcement",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, compact)


if __name__ == "__main__":
    unittest.main()
