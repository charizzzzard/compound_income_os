from __future__ import annotations

import json
import unittest
from pathlib import Path


TEMPLATE_PATH = Path("docs/contracts/RUNTIME_GATE_DEFINITION_TEMPLATE.md")
BOUNDARY_CONTRACT_PATH = Path("docs/contracts/RUNTIME_GATE_BOUNDARY_CONTRACT.md")


class RuntimeGateDefinitionTemplateTests(unittest.TestCase):
    def _read(self, path: str | Path) -> str:
        return Path(path).read_text(encoding="utf-8")

    def test_template_exists_and_contains_required_fields(self) -> None:
        self.assertTrue(TEMPLATE_PATH.exists())
        text = self._read(TEMPLATE_PATH)

        for field in [
            "gate_id",
            "gate_name",
            "gate_classification",
            "owner_surface",
            "trigger_condition",
            "runtime_surface_impacted",
            "input_artifacts",
            "output_artifacts",
            "failure_modes",
            "severity_semantics",
            "blocking_behavior",
            "override_policy",
            "rollback_or_correction_path",
            "evidence_required",
            "tests_required",
            "operator_acceptance_required",
            "release_acceptance_semantics",
            "non_scope",
            "promotion_prerequisites",
            "demotion_or_retraction_conditions",
        ]:
            self.assertIn(field, text)

    def test_template_contains_allowed_classifications(self) -> None:
        text = self._read(TEMPLATE_PATH)

        for classification in [
            "documentation_only",
            "review_evidence",
            "runtime_relevant_candidate",
            "future_runtime_enforced",
        ]:
            self.assertIn(classification, text)

    def test_template_contains_hard_non_overclaim_language(self) -> None:
        text = self._read(TEMPLATE_PATH)
        lowered = text.lower()

        for phrase in [
            "no automatic release acceptance",
            "no product readiness",
            "no production readiness",
            "no investment readiness",
            "does not make a gate runtime_enforced",
            "human operator acceptance",
            "missing, stale, unknown, failed and not-applicable data must remain visible",
            "no buy/sell recommendation changes",
            "no investment advice",
        ]:
            self.assertIn(phrase, lowered)

    def test_boundary_contract_and_module_contracts_reference_template(self) -> None:
        expected_path = "docs/contracts/RUNTIME_GATE_DEFINITION_TEMPLATE.md"

        for path in [
            BOUNDARY_CONTRACT_PATH,
            Path("docs/governance/EXTERNAL_REVIEW_COVERAGE_STANDARD.md"),
            Path("docs/MODULE_CONTRACTS.md"),
            Path("docs/CONTEXT_AND_ROADMAP.md"),
            Path("README.md"),
        ]:
            self.assertIn(expected_path, self._read(path), str(path))

    def test_system_map_references_boundary_contract_with_repo_relative_path(self) -> None:
        text = self._read("docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md")

        self.assertIn("docs/contracts/RUNTIME_GATE_BOUNDARY_CONTRACT.md", text)
        self.assertIn("docs/contracts/RUNTIME_GATE_DEFINITION_TEMPLATE.md", text)

    def test_no_current_gate_is_promoted_to_runtime_enforced(self) -> None:
        registry_text = self._read("docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml")
        registry = json.loads(registry_text)

        self.assertIn("gates", registry)
        for gate in registry["gates"]:
            dumped = json.dumps(gate).lower()
            self.assertNotIn('"gate_classification": "runtime_enforced"', dumped)
            self.assertNotIn('"current_classification": "runtime_enforced"', dumped)
            self.assertNotIn('"runtime_enforced"', dumped)

    def test_registry_remains_machine_readable(self) -> None:
        data = json.loads(self._read("docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml"))

        self.assertIsInstance(data.get("gates"), list)
        self.assertTrue(
            any(gate["gate_id"] == "RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW" for gate in data["gates"])
        )

    def test_automatic_release_acceptance_is_only_negated(self) -> None:
        negation_markers = (
            "no automatic release acceptance",
            "rejects automatic release acceptance",
            "cannot automatically accept",
            "may_auto_accept_release: false",
            "does not grant",
            "must state that the gate cannot automatically accept",
        )

        for line_no, line in enumerate(self._read(TEMPLATE_PATH).splitlines(), start=1):
            lowered = line.lower()
            if "automatic release acceptance" not in lowered:
                continue
            if any(marker in lowered for marker in negation_markers):
                continue
            self.fail(f"Unnegated automatic release acceptance phrase at line {line_no}: {line}")


if __name__ == "__main__":
    unittest.main()
