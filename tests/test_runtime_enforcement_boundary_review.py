from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.runtime_enforcement_boundary_review import (
    RELEVANT_TEXT_FILES,
    run_and_write,
    run_runtime_enforcement_boundary_review,
)


class RuntimeEnforcementBoundaryReviewTests(unittest.TestCase):
    def _write(self, root: Path, relative_path: str, text: str) -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _registry(self) -> str:
        return json.dumps(
            {
                "schema_version": 1,
                "gates": [
                    {
                        "gate_id": "RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW",
                        "gate_name": "Runtime Enforcement Boundary Review",
                        "priority": "P0",
                        "purpose": "Review whether documentation-only, template-only and runtime-enforced boundaries are clearly separated.",
                        "trigger_condition": "Before runtime stage integration, production workflow claims or dashboard readiness claims.",
                        "required_inputs": ["contracts", "validators", "stage DAG", "runtime code", "tests"],
                        "required_outputs": ["enforcement boundary map", "documentation-only risk findings"],
                        "acceptance_criteria": [
                            "template validation is not described as runtime validation",
                            "runtime claims have code and tests",
                            "documentation-only controls remain labeled",
                        ],
                        "non_scope": ["runtime implementation", "feature readiness approval"],
                        "blocks_features": [
                            "runtime_stage_integration",
                            "production_workflow_claims",
                            "dashboard_readiness_claims",
                        ],
                        "evidence_required": ["boundary map", "claim-to-evidence trace"],
                        "operator_acceptance_required": True,
                    }
                ],
            },
            indent=2,
        )

    def _sequence(self, include_broker_staging_gate: bool = True) -> str:
        broker_gate = "- `RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW`\n" if include_broker_staging_gate else ""
        return (
            "# External Review Gate Sequence\n\n"
            "## Before Portfolio Event Ledger Runtime\n\n"
            "- `PORTFOLIO_EVENT_LEDGER_RUNTIME_READINESS_REVIEW`\n"
            "- `RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW`\n\n"
            "## Before Broker Import Staging\n\n"
            "- `BROKER_IMPORT_STAGING_READINESS_REVIEW`\n"
            f"{broker_gate}\n"
            "## Before Dashboard Expansion\n\n"
            "- `DASHBOARD_MISINTERPRETATION_REVIEW`\n"
            "- `RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW`\n"
        )

    def _base_text(self) -> str:
        return "\n".join(
            [
                "This is governance documentation only and does not implement runtime enforcement.",
                "No release acceptance is granted.",
                "No automated release acceptance is granted.",
                "No runtime LLM agents are introduced.",
                "No broker import or order execution is introduced.",
                "No product readiness, production readiness or investment readiness is implied.",
                "Human Operator remains final acceptance authority.",
                "Template validation, review and reporting are distinct from runtime enforcement.",
            ]
        )

    def _module_contracts(self) -> str:
        return "\n".join(
            [
                "| module | notes |",
                "| `src.release_ci_environment_parity_review` | read-only governance review; keine Runtime-Enforcement-Engine |",
                "| `src.clean_room_reproduction_review` | read-only packet reproduction; keine Runtime-Enforcement-Engine |",
                "| `src.external_review_cross_patch_regression` | read-only governance regression; keine Runtime-Enforcement-Engine |",
                "| `src.handoff_bundle` | handoff packaging; keine Runtime-Enforcement-Engine |",
                "| `src.portfolio_event_ledger_validation` | template validation only; keine Runtime-Enforcement-Engine |",
                "| `src.data_source_registry_validation` | template validation only; keine Runtime-Enforcement-Engine |",
            ]
        )

    def _fixture(self, root: Path, *, include_broker_staging_gate: bool = True) -> None:
        for relative_path in RELEVANT_TEXT_FILES:
            if relative_path == "docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml":
                self._write(root, relative_path, self._registry())
            elif relative_path == "docs/governance/EXTERNAL_REVIEW_GATE_SEQUENCE.md":
                self._write(root, relative_path, self._sequence(include_broker_staging_gate=include_broker_staging_gate))
            elif relative_path == "docs/MODULE_CONTRACTS.md":
                self._write(root, relative_path, self._module_contracts())
            else:
                self._write(root, relative_path, self._base_text())
        self._write(root, "src/runtime_enforcement_boundary_review.py", Path("src/runtime_enforcement_boundary_review.py").read_text(encoding="utf-8"))

    def _findings_text(self, root: Path) -> str:
        findings = run_runtime_enforcement_boundary_review("2026-05-21", repo_root=root)
        return "\n".join(f"{finding.check_id}|{finding.severity}|{finding.status}|{finding.evidence}" for finding in findings)

    def test_complete_fixture_returns_deterministic_pass_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)

            first = [finding.row() for finding in run_runtime_enforcement_boundary_review("2026-05-21", repo_root=root)]
            second = [finding.row() for finding in run_runtime_enforcement_boundary_review("2026-05-21", repo_root=root)]

            self.assertEqual(first, second)
            text = "\n".join(f"{row['check_id']}|{row['severity']}|{row['status']}" for row in first)
            self.assertIn("RUNTIME_ENFORCEMENT_NON_SCOPE_PRESENT|PASS|PASS", text)
            self.assertIn("REVIEW_GATE_REGISTRY_ALIGNMENT|PASS|PASS", text)
            self.assertIn("REVIEW_GATE_SEQUENCE_ALIGNMENT|PASS|PASS", text)

    def test_required_non_scope_language_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            text = self._findings_text(root)

            self.assertIn("RUNTIME_ENFORCEMENT_NON_SCOPE_PRESENT|PASS|PASS", text)

    def test_risky_overclaim_language_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            self._write(root, "README.md", "runtime_enforced: true\n")
            text = self._findings_text(root)

            self.assertIn("RUNTIME_LANGUAGE_OVERCLAIM_SCAN|WARN|WARN", text)

    def test_registry_alignment_check_fails_when_gate_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            self._write(root, "docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml", json.dumps({"gates": []}))
            text = self._findings_text(root)

            self.assertIn("REVIEW_GATE_REGISTRY_ALIGNMENT|FAIL|FAIL", text)

    def test_gate_sequence_alignment_warns_when_missing_before_broker_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root, include_broker_staging_gate=False)
            text = self._findings_text(root)

            self.assertIn("REVIEW_GATE_SEQUENCE_ALIGNMENT|WARN|WARN", text)
            self.assertIn("Before Broker Import Staging", text)

    def test_missing_files_are_not_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            (root / "docs/architecture/CIOS_FEATURE_STATUS.yaml").unlink()
            text = self._findings_text(root)

            self.assertIn("NOT_AVAILABLE", text)

    def test_report_generation_includes_non_scope_and_human_operator_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            result = run_and_write(
                "2026-05-21",
                repo_root=root,
                csv_output=root / "out.csv",
                report_output=root / "out.md",
            )
            report = (root / "out.md").read_text(encoding="utf-8")

            self.assertEqual(result["status"], "OK")
            self.assertIn("not runtime enforcement", report)
            self.assertIn("Human Operator remains the final acceptance authority", report)
            self.assertIn("documentation, validation, review and reporting", report)

    def test_producer_does_not_require_network_or_private_files(self) -> None:
        source = Path("src/runtime_enforcement_boundary_review.py").read_text(encoding="utf-8")

        for forbidden in ["requests", "urllib", "httpx", "socket", "subprocess"]:
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)
        self.assertNotIn("data/raw/private", source)
        self.assertNotIn("C:\\Users\\", source)


if __name__ == "__main__":
    unittest.main()
