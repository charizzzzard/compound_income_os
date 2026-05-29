from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "docs" / "contracts" / "VALUATION_METHODOLOGY_BOUNDARY_CONTRACT.md"
CONTRACT_REF = "docs/contracts/VALUATION_METHODOLOGY_BOUNDARY_CONTRACT.md"


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


class ValuationMethodologyBoundaryContractTests(unittest.TestCase):
    def test_contract_file_exists(self) -> None:
        self.assertTrue(CONTRACT_PATH.exists())

    def test_required_sections_exist(self) -> None:
        text = read(CONTRACT_PATH)

        for section in [
            "## Purpose",
            "## Current State",
            "## Explicit Non-Scope",
            "## Future Methodology Preconditions",
            "## Allowed Future Method Families",
            "## Prohibited Claims",
            "## Required Operator Interpretation",
        ]:
            self.assertIn(section, text)

    def test_required_non_scope_phrases_exist(self) -> None:
        section = extract_section(read(CONTRACT_PATH), "## Explicit Non-Scope")
        text = normalized(section)

        for phrase in [
            "no dcf engine",
            "no valuation automation",
            "no scoring formula change",
            "no ranking change",
            "no analyst target price ingestion",
            "no provider/api integration",
            "no broker import",
            "no order execution",
            "no buy/sell automation",
            "no investment advice",
            "no production readiness",
            "no investment readiness",
        ]:
            self.assertIn(phrase, text)

    def test_purpose_preserves_operator_authority_and_governance_boundary(self) -> None:
        section = extract_section(read(CONTRACT_PATH), "## Purpose")
        text = normalized(section)

        for phrase in [
            "human operator remains final authority",
            "governance evidence only",
            "not a runtime gate",
            "not release acceptance",
            "not an investment decision",
        ]:
            self.assertIn(phrase, text)

    def test_future_methodology_preconditions_keep_degraded_data_visible(self) -> None:
        section = extract_section(read(CONTRACT_PATH), "## Future Methodology Preconditions")
        text = normalized(section)

        for phrase in [
            "stale, missing, conflict, unknown and invalid data handling",
            "no silent imputation",
            "no silent overwrite of accepted facts",
            "missing/stale/conflicting/unknown/invalid data remains visible",
            "no future methodology may silently upgrade degraded evidence to `ok`",
        ]:
            self.assertIn(phrase, text)

    def test_required_operator_interpretation_keeps_outputs_as_evidence(self) -> None:
        section = extract_section(read(CONTRACT_PATH), "## Required Operator Interpretation")
        text = normalized(section)

        for phrase in [
            "outputs are evidence, not instructions",
            "human operator remains final authority",
            "missing, stale, conflicting, unknown and invalid states",
            "no silent imputation",
            "no silent overwrite of accepted facts",
            "not truth and not acceptance",
        ]:
            self.assertIn(phrase, text)

    def test_future_method_families_are_candidates_not_implementations(self) -> None:
        section = extract_section(read(CONTRACT_PATH), "## Allowed Future Method Families")
        text = normalized(section)

        for phrase in [
            "future candidates only",
            "not implemented by this contract",
            "historical multiple comparison",
            "normalized owner earnings / fcf yield view",
            "dividend yield / dividend growth support view",
            "dcf as future methodology only after contract",
            "scenario/sensitivity view as future evidence only",
        ]:
            self.assertIn(phrase, text)

        for overclaim in [
            "dcf engine implemented",
            "valuation automation implemented",
            "provider/api integration implemented",
            "historical multiple comparison implemented",
            "normalized owner earnings implemented",
            "dividend growth implemented",
            "scenario/sensitivity implemented",
            "investment ready",
            "production ready",
        ]:
            self.assertNotIn(overclaim, text)

    def test_prohibited_claims_are_scoped_to_prohibited_claims_section(self) -> None:
        section = extract_section(read(CONTRACT_PATH), "## Prohibited Claims")
        text = normalized(section)

        for phrase in [
            "guaranteed undervaluation",
            "risk-free return",
            "automatic buy/sell",
            "order execution",
            "investment advice",
            "complete intrinsic value certainty",
            "production readiness",
            "investment readiness",
        ]:
            self.assertIn(phrase, text)

    def test_linked_docs_reference_contract_without_implying_implementation(self) -> None:
        linked_docs = [
            ROOT / "docs" / "MODULE_CONTRACTS.md",
            ROOT / "docs" / "contracts" / "VALUATION_ENGINE_BOUNDARY_CONTRACT.md",
            ROOT / "docs" / "contracts" / "VALUATION_SCORING_SEMANTIC_DECISION_QUALITY_CONTRACT.md",
            ROOT / "docs" / "architecture" / "CIOS_FEATURE_STATUS.yaml",
            ROOT / "docs" / "architecture" / "CURRENT_KNOWN_GAPS.md",
        ]

        for path in linked_docs:
            with self.subTest(path=str(path.relative_to(ROOT))):
                text = read(path)
                lowered = normalized(text)
                self.assertIn(CONTRACT_REF, text)
                self.assertNotIn("dcf engine implemented", lowered)
                self.assertNotIn("valuation automation implemented", lowered)
                self.assertNotIn("provider/api integration implemented", lowered)
                self.assertNotIn("investment ready", lowered)
                self.assertNotIn("production ready", lowered)


if __name__ == "__main__":
    unittest.main()
