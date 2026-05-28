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
        text = normalized(read(CONTRACT_PATH))

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

    def test_required_conservative_semantics_exist(self) -> None:
        text = normalized(read(CONTRACT_PATH))

        for phrase in [
            "human operator remains final authority",
            "missing/stale/conflicting/unknown/invalid data remains visible",
            "no silent imputation",
            "no silent overwrite",
            "outputs are evidence, not instructions",
        ]:
            self.assertIn(phrase, text)

    def test_future_method_families_are_candidates_not_implementations(self) -> None:
        text = normalized(read(CONTRACT_PATH))

        for phrase in [
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
            "investment ready",
            "production ready",
        ]:
            self.assertNotIn(overclaim, text)

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
                self.assertNotIn("investment ready", lowered)
                self.assertNotIn("production ready", lowered)


if __name__ == "__main__":
    unittest.main()
