from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "docs" / "contracts" / "VALUATION_METHODOLOGY_PROPOSAL_TEMPLATE.md"
FEATURE_STATUS_PATH = ROOT / "docs" / "architecture" / "CIOS_FEATURE_STATUS.yaml"
TEMPLATE_REF = "docs/contracts/VALUATION_METHODOLOGY_PROPOSAL_TEMPLATE.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


class ValuationMethodologyProposalTemplateTests(unittest.TestCase):
    def test_template_file_exists(self) -> None:
        self.assertTrue(TEMPLATE_PATH.exists())

    def test_required_sections_exist(self) -> None:
        text = read(TEMPLATE_PATH)

        for section in [
            "## Purpose",
            "## Methodology Identity",
            "## Scope Boundary",
            "## Required Input Data",
            "## Calculation Semantics",
            "## Review Gates",
            "## Output Semantics",
            "## Traceability",
            "## Explicit Non-Scope",
            "## Proposal Acceptance Boundary",
        ]:
            self.assertIn(section, text)

    def test_required_identity_fields_exist(self) -> None:
        text = normalized(read(TEMPLATE_PATH))

        for field in [
            "methodology_id",
            "methodology_name",
            "methodology_family",
            "proposal_status",
            "owner_role",
            "reviewer_role",
            "contract_reference",
            "related_boundary_contract",
            "version",
            "decision_record_reference",
        ]:
            self.assertIn(field, text)

    def test_required_non_scope_phrases_exist(self) -> None:
        text = normalized(read(TEMPLATE_PATH))

        for phrase in [
            "this template does not implement",
            "dcf engine",
            "valuation automation",
            "scoring integration",
            "ranking integration",
            "provider/api integration",
            "investment advice",
            "buy/sell automation",
            "product readiness",
            "production readiness",
            "investment readiness",
        ]:
            self.assertIn(phrase, text)

    def test_proposal_only_and_not_runtime_enforced_language_exists(self) -> None:
        text = normalized(read(TEMPLATE_PATH))

        for phrase in [
            "proposal-only governance evidence",
            "proposal acceptance does not imply runtime enforcement",
            'calculation_status: "proposed_only"',
            'runtime_status: "not_runtime_enforced"',
            'formula_implementation_status: "not_implemented"',
        ]:
            self.assertIn(phrase, text)

    def test_proposal_acceptance_boundary_requires_future_runtime_prerequisites(self) -> None:
        text = normalized(read(TEMPLATE_PATH))

        self.assertIn("completing this template can only create review evidence", text)
        self.assertIn("it cannot promote a methodology to runtime use", text)

        for phrase in [
            "separate accepted methodology contract",
            "implementation patch",
            "tests",
            "evidence artifacts",
            "rollback/correction path",
            "operator-facing wording boundary",
            "explicit human operator acceptance",
        ]:
            self.assertIn(phrase, text)

    def test_degraded_data_handling_is_explicit(self) -> None:
        text = normalized(read(TEMPLATE_PATH))

        for phrase in [
            "missing, stale, unknown, conflicting or blocked data",
            "must remain visible",
            "no silent imputation",
            "no silent overwrite",
            "insufficient_data",
            "blocked",
        ]:
            self.assertIn(phrase, text)

    def test_template_does_not_imply_implementation_or_readiness(self) -> None:
        text = normalized(read(TEMPLATE_PATH))

        forbidden_overclaims = [
            "dcf engine is implemented",
            "implemented dcf engine",
            "valuation automation is implemented",
            "scoring integration is implemented",
            "ranking integration is implemented",
            "buy/sell automation is implemented",
            "investment advice is provided",
            "product ready",
            "production ready",
            "investment ready",
            "runtime enforced",
        ]

        for phrase in forbidden_overclaims:
            self.assertNotIn(phrase, text)

    def test_feature_status_marks_template_as_governance_only(self) -> None:
        text = read(FEATURE_STATUS_PATH)
        lowered = normalized(text)

        self.assertIn(TEMPLATE_REF, text)
        self.assertIn("tests/test_valuation_methodology_proposal_template.py", text)
        self.assertIn("proposal/governance-only", lowered)

        for overclaim in [
            "dcf engine implemented",
            "valuation automation implemented",
            "scoring integration implemented",
            "ranking integration implemented",
            "investment ready",
            "production ready",
        ]:
            self.assertNotIn(overclaim, lowered)


if __name__ == "__main__":
    unittest.main()
