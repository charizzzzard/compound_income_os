from __future__ import annotations

import unittest
from pathlib import Path


STANDARD_PATH = Path("docs/governance/CIOS_CODEX_OPERATIONALIZATION_STANDARD.md")


def read_standard() -> str:
    return STANDARD_PATH.read_text(encoding="utf-8")


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


class CodexOperationalizationStandardTests(unittest.TestCase):
    def test_standard_exists(self) -> None:
        self.assertTrue(STANDARD_PATH.exists())

    def test_required_headings_exist(self) -> None:
        text = read_standard()

        for heading in [
            "# CIOS Codex Operationalization Standard",
            "## Purpose",
            "## Source Of Truth Hierarchy",
            "## Required Head Taxonomy",
            "## Allowed Head Offset Cases",
            "## Disallowed Ambiguity",
            "## Handoff Reconciliation Gates",
            "## Codex Operating Requirements",
            "## External LLM Review Requirements",
            "## Operator Decision Capture",
            "## Failure Mode Reporting",
            "## Explicit Non-Scope",
        ]:
            with self.subTest(heading=heading):
                self.assertIn(heading, text)

    def test_source_of_truth_hierarchy_mentions_repo_and_external_packet(self) -> None:
        text = read_standard()

        for phrase in [
            "committed GitHub repository",
            "external_review_packet/HANDOFF_LATEST_CONTEXT.md",
            "external_review_packet/HANDOFF_LATEST.zip",
            "external_review_packet/HANDOFF_LATEST.sha256",
            "HANDOFF_CONTEXT.md",
            "outputs/",
            "local generated evidence",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_required_head_taxonomy_exists(self) -> None:
        text = read_standard()

        for head_name in [
            "repo_current_head",
            "implementation_head",
            "preflight_head",
            "handoff_export_head",
            "handoff_metadata_commit_head",
            "central_handoff_zip_head",
            "current_handoff_head",
            "remote_main_head",
            "accepted_review_head",
        ]:
            with self.subTest(head_name=head_name):
                self.assertIn(head_name, text)

    def test_allowed_head_offsets_and_disallowed_ambiguity_are_explicit(self) -> None:
        compact = normalized(read_standard())

        for phrase in [
            "metadata-only commits after implementation",
            "handoff metadata sync commits",
            "central packet publication commits",
            "report-only ignored outputs",
            "claim github head equals handoff head without checking both",
            "treat ignored outputs as committed repo truth",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, compact)

    def test_recorded_validation_is_not_execution_proof(self) -> None:
        compact = normalized(read_standard())

        self.assertIn("recorded validation as executed validation", compact)
        self.assertIn("recor ded_validation".replace(" ", ""), compact)
        self.assertIn("unless independently executed", compact)

    def test_external_llms_and_codex_cannot_accept_releases(self) -> None:
        compact = normalized(read_standard())

        self.assertIn("codex must not self-certify final acceptance", compact)
        self.assertIn("external reviewers cannot accept releases", compact)
        self.assertIn("human operator", compact)
        self.assertIn("final acceptance authority", compact)

    def test_handoff_reconciliation_invariants_exist(self) -> None:
        text = read_standard()
        compact = normalized(text)

        for phrase in [
            "zipfile.testzip()",
            "nested_zip_count",
            "forbidden_count",
            "local path leak",
            "file_count",
            "post-assembly delta",
            "POST_MANIFEST_INCLUDED_EVIDENCE",
            "PRE_FLIGHT_REPO_REMOTE/*",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertIn("the packet fails reconciliation", compact)

    def test_ignored_outputs_are_not_authoritative_without_acceptance(self) -> None:
        compact = normalized(read_standard())

        self.assertIn("ignored outputs are not authoritative repo truth", compact)
        self.assertIn("unless explicitly accepted", compact)
        self.assertIn("committed", compact)
        self.assertIn("summarized", compact)

    def test_operator_decision_states_are_defined(self) -> None:
        text = read_standard()

        for state in [
            "ACCEPT_BASELINE_AS_WORKING_INPUT",
            "ACCEPT_WITH_FINDINGS",
            "RUN_NEXT_PATCH",
            "PAUSE_FOR_MANUAL_REVIEW",
            "REJECT_OR_REWORK",
            "ACCEPT_RELEASE_SCOPE_ONLY",
        ]:
            with self.subTest(state=state):
                self.assertIn(state, text)

    def test_no_runtime_or_investment_readiness_claims_are_introduced(self) -> None:
        compact = normalized(read_standard())

        for phrase in [
            "does not implement runtime enforcement",
            "does not implement or approve",
            "investment logic changes",
            "scoring changes",
            "ranking changes",
            "valuation changes",
            "broker import changes",
            "provider/api integration",
            "order execution",
            "buy/sell automation",
            "production readiness",
            "product readiness",
            "investment readiness",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, compact)


if __name__ == "__main__":
    unittest.main()
