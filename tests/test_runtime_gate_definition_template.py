from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


TEMPLATE_PATH = Path("docs/contracts/RUNTIME_GATE_DEFINITION_TEMPLATE.md")
BOUNDARY_CONTRACT_PATH = Path("docs/contracts/RUNTIME_GATE_BOUNDARY_CONTRACT.md")
REQUIRED_TOP_LEVEL_KEYS = [
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
]
REQUIRED_NESTED_KEYS = [
    "missing",
    "stale",
    "unknown",
    "failed",
    "not_applicable",
    "PASS",
    "WARN",
    "FAIL",
    "NOT_AVAILABLE",
    "allowed",
    "operator_record_required",
    "cannot_override",
]
REQUIRED_CHILDREN_BY_PARENT = {
    "failure_modes": [
        "missing",
        "stale",
        "unknown",
        "failed",
        "not_applicable",
    ],
    "severity_semantics": [
        "PASS",
        "WARN",
        "FAIL",
        "NOT_AVAILABLE",
    ],
    "override_policy": [
        "allowed",
        "operator_record_required",
        "cannot_override",
    ],
}


class RuntimeGateDefinitionTemplateTests(unittest.TestCase):
    def _read(self, path: str | Path) -> str:
        return Path(path).read_text(encoding="utf-8")

    def _extract_template_yaml_block(self, text: str) -> str:
        match = re.search(r"(?ms)^## Template\s*^```yaml\s*\n(?P<yaml>.*?)^```$", text)
        self.assertIsNotNone(match, "Template document must contain a fenced yaml block under ## Template")
        return match.group("yaml")

    def _assert_required_yaml_like_keys_present(self, yaml_block: str) -> None:
        for key in REQUIRED_TOP_LEVEL_KEYS:
            self.assertRegex(yaml_block, rf"(?m)^{re.escape(key)}:\s*", key)
        for key in REQUIRED_NESTED_KEYS:
            self.assertRegex(yaml_block, rf"(?m)^\s+{re.escape(key)}:\s*", key)
        self._assert_required_parent_child_keys_present(yaml_block)

    def _extract_parent_section(self, yaml_block: str, parent: str) -> str:
        lines = yaml_block.splitlines()
        start_index = next(
            (
                index
                for index, line in enumerate(lines)
                if re.match(rf"^{re.escape(parent)}:\s*$", line)
            ),
            None,
        )
        self.assertIsNotNone(start_index, f"Missing parent section: {parent}")

        section_lines: list[str] = []
        for line in lines[start_index + 1 :]:
            if line and not line.startswith(" "):
                break
            section_lines.append(line)
        return "\n".join(section_lines)

    def _assert_required_parent_child_keys_present(self, yaml_block: str) -> None:
        for parent, child_keys in REQUIRED_CHILDREN_BY_PARENT.items():
            section = self._extract_parent_section(yaml_block, parent)
            for child_key in child_keys:
                self.assertRegex(
                    section,
                    rf"(?m)^\s+{re.escape(child_key)}:\s*",
                    f"{child_key} must be nested under {parent}",
                )

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

    def test_required_fields_are_present_in_fenced_yaml_template_block(self) -> None:
        yaml_block = self._extract_template_yaml_block(self._read(TEMPLATE_PATH))

        self._assert_required_yaml_like_keys_present(yaml_block)

    def test_required_field_check_uses_yaml_block_not_document_text(self) -> None:
        text = self._read(TEMPLATE_PATH)
        yaml_block = self._extract_template_yaml_block(text)
        mutated_block = "\n".join(
            line for line in yaml_block.splitlines() if not line.startswith("gate_id:")
        )

        self.assertIn("gate_id", text)
        with self.assertRaises(AssertionError):
            self._assert_required_yaml_like_keys_present(mutated_block)

    def test_nested_key_misplacement_is_rejected(self) -> None:
        yaml_block = self._extract_template_yaml_block(self._read(TEMPLATE_PATH))
        misplaced_block = yaml_block.replace("  PASS: \"\"\n", "")
        misplaced_block = misplaced_block.replace("  missing: \"\"\n", "  missing: \"\"\n  PASS: \"\"\n")

        with self.assertRaises(AssertionError):
            self._assert_required_parent_child_keys_present(misplaced_block)

    def test_wrong_parent_child_presence_does_not_satisfy_correct_parent(self) -> None:
        yaml_block = self._extract_template_yaml_block(self._read(TEMPLATE_PATH))
        misplaced_block = yaml_block.replace("  NOT_AVAILABLE: \"\"\n", "")
        misplaced_block = misplaced_block.replace("  unknown: \"\"\n", "  unknown: \"\"\n  NOT_AVAILABLE: \"\"\n")

        self.assertRegex(misplaced_block, r"failure_modes:\n(?:  .+\n)*  NOT_AVAILABLE:")
        with self.assertRaises(AssertionError):
            self._assert_required_parent_child_keys_present(misplaced_block)

    def test_parent_section_missing_required_child_is_rejected(self) -> None:
        yaml_block = self._extract_template_yaml_block(self._read(TEMPLATE_PATH))
        missing_child_block = yaml_block.replace("  not_applicable: \"\"\n", "")

        with self.assertRaises(AssertionError):
            self._assert_required_parent_child_keys_present(missing_child_block)

    def test_template_contains_allowed_classifications(self) -> None:
        text = self._read(TEMPLATE_PATH)

        for classification in [
            "documentation_only",
            "review_evidence",
            "runtime_relevant_candidate",
            "future_runtime_enforced",
        ]:
            self.assertIn(classification, text)

    def test_template_contains_classification_crosswalk(self) -> None:
        text = self._read(TEMPLATE_PATH)

        for phrase in [
            "Classification Crosswalk",
            "future_runtime_enforced",
            "proposal-only",
            "not the same as actual `runtime_enforced`",
            "docs/contracts/RUNTIME_GATE_BOUNDARY_CONTRACT.md",
            "explicit Human Operator acceptance",
            "cannot promote any current producer to runtime enforcement",
        ]:
            self.assertIn(phrase, text)

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
