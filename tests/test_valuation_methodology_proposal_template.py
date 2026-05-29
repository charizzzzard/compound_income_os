from __future__ import annotations

import re
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
        line = lines[index].strip()
        if line.startswith("## ") and not line.startswith("### "):
            end_index = index
            break
    return "\n".join(lines[start_index:end_index])


def extract_fenced_yaml_blocks(section_text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    in_yaml_block = False

    for line in section_text.splitlines():
        stripped = line.strip()
        if not in_yaml_block and stripped == "```yaml":
            in_yaml_block = True
            current = []
            continue
        if in_yaml_block and stripped == "```":
            blocks.append("\n".join(current))
            in_yaml_block = False
            current = []
            continue
        if in_yaml_block:
            current.append(line)

    return blocks


def assert_yaml_key_present(testcase: unittest.TestCase, yaml_block: str, key: str) -> None:
    testcase.assertRegex(yaml_block, rf"(?m)^{re.escape(key)}:\s*")


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

    def test_methodology_identity_yaml_block_has_required_fields(self) -> None:
        section = extract_section(read(TEMPLATE_PATH), "## Methodology Identity")
        blocks = extract_fenced_yaml_blocks(section)
        self.assertTrue(blocks, "Methodology Identity must contain a fenced yaml block")
        yaml_block = blocks[0]

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
            assert_yaml_key_present(self, yaml_block, field)

        for exact_line in [
            'proposal_status: "PROPOSED_ONLY"',
            'contract_reference: "docs/contracts/VALUATION_METHODOLOGY_PROPOSAL_TEMPLATE.md"',
            'related_boundary_contract: "docs/contracts/VALUATION_METHODOLOGY_BOUNDARY_CONTRACT.md"',
        ]:
            self.assertIn(exact_line, yaml_block)

    def test_required_non_scope_phrases_exist(self) -> None:
        section = extract_section(read(TEMPLATE_PATH), "## Explicit Non-Scope")
        text = normalized(section)

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
        ]:
            self.assertIn(phrase, text)

    def test_calculation_semantics_yaml_block_has_exact_proposal_only_markers(self) -> None:
        section = extract_section(read(TEMPLATE_PATH), "## Calculation Semantics")
        blocks = extract_fenced_yaml_blocks(section)
        self.assertTrue(blocks, "Calculation Semantics must contain a fenced yaml block")
        yaml_block = blocks[0]

        for exact_line in [
            'calculation_status: "PROPOSED_ONLY"',
            'runtime_status: "NOT_RUNTIME_ENFORCED"',
            'formula_implementation_status: "NOT_IMPLEMENTED"',
        ]:
            self.assertIn(exact_line, yaml_block)

    def test_proposal_acceptance_boundary_requires_future_runtime_prerequisites(self) -> None:
        section = extract_section(read(TEMPLATE_PATH), "## Proposal Acceptance Boundary")
        text = normalized(section)

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
