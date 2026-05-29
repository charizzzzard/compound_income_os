from __future__ import annotations

import json
import unittest
from pathlib import Path


CONTRACT_PATH = Path("docs/contracts/RUNTIME_GATE_BOUNDARY_CONTRACT.md")


class RuntimeGateBoundaryContractTests(unittest.TestCase):
    def _read(self, path: str | Path) -> str:
        return Path(path).read_text(encoding="utf-8")

    def test_contract_exists_and_contains_core_classifications(self) -> None:
        self.assertTrue(CONTRACT_PATH.exists())
        text = self._read(CONTRACT_PATH)

        for token in [
            "documentation_only",
            "review_evidence",
            "runtime_relevant_candidate",
            "runtime_enforced",
            "release_acceptance",
            "production_ready",
            "investment_ready",
        ]:
            self.assertIn(token, text)

    def test_contract_contains_hard_invariants(self) -> None:
        text = self._read(CONTRACT_PATH)

        for phrase in [
            "No gate may auto-accept a release",
            "Human Operator remains final acceptance authority",
            "No silent imputation",
            "No silent overwrite of accepted facts",
        ]:
            self.assertIn(phrase, text)

    def test_runtime_enforcement_boundary_review_is_not_runtime_enforced(self) -> None:
        text = self._read(CONTRACT_PATH)
        row = next(
            line
            for line in text.splitlines()
            if line.startswith("| RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW |")
        )

        self.assertIn("| review_evidence |", row)
        self.assertIn("| yes | yes | no |", row)
        self.assertIn("not runtime_enforced", row)
        self.assertNotIn("| runtime_enforced |", row)
        self.assertNotIn("release_acceptance", row)

    def test_governance_documents_reference_contract(self) -> None:
        expected_path = "docs/contracts/RUNTIME_GATE_BOUNDARY_CONTRACT.md"
        for path in [
            "docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml",
            "docs/governance/EXTERNAL_REVIEW_GATE_SEQUENCE.md",
            "docs/governance/EXTERNAL_REVIEW_COVERAGE_STANDARD.md",
            "docs/architecture/CIOS_FEATURE_STATUS.yaml",
            "docs/architecture/CURRENT_KNOWN_GAPS.md",
            "docs/MODULE_CONTRACTS.md",
            "docs/CONTEXT_AND_ROADMAP.md",
            "README.md",
        ]:
            self.assertIn(expected_path, self._read(path), path)

    def test_gate_registry_remains_machine_readable_and_non_runtime(self) -> None:
        data = json.loads(self._read("docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml"))
        gate = next(
            item
            for item in data["gates"]
            if item["gate_id"] == "RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW"
        )

        self.assertIn("docs/contracts/RUNTIME_GATE_BOUNDARY_CONTRACT.md", gate["evidence_required"])
        self.assertIn("runtime implementation", gate["non_scope"])
        self.assertIn("feature readiness approval", gate["non_scope"])
        self.assertNotIn("runtime_enforced", json.dumps(gate).lower())
        self.assertTrue(gate["operator_acceptance_required"])

    def test_no_unnegated_readiness_overclaim_in_review_surfaces(self) -> None:
        risky = [
            "production ready",
            "investment ready",
            "automatically accepts releases",
        ]
        negation_markers = (
            "no ",
            "not ",
            "does not",
            "must not",
            "keine",
            "kein",
            "nicht",
            "non-scope",
            "without",
        )
        for path in [
            CONTRACT_PATH,
            Path("README.md"),
            Path("docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md"),
            Path("docs/architecture/CIOS_FEATURE_STATUS.yaml"),
        ]:
            for line_no, line in enumerate(self._read(path).splitlines(), start=1):
                lowered = line.lower()
                if not any(term in lowered for term in risky):
                    continue
                if any(marker in lowered for marker in negation_markers):
                    continue
                self.fail(f"Unnegated readiness overclaim in {path}:{line_no}: {line}")

    def test_future_runtime_sensitive_areas_are_prerequisites_not_implemented(self) -> None:
        text = self._read(CONTRACT_PATH)

        for area in [
            "Broker Import Staging",
            "Portfolio Event Ledger Runtime",
            "Dashboard Expansion",
            "Replay / Backtesting",
            "Outcome Attribution",
            "Valuation Automation",
        ]:
            self.assertIn(area, text)

        for phrase in [
            "No broker import exists from this contract",
            "No productive Event Ledger exists from this contract",
            "No dashboard expansion exists from this contract",
            "No replay or backtesting exists from this contract",
            "No outcome attribution exists from this contract",
            "No valuation automation exists from this contract",
        ]:
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
