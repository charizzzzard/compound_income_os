from __future__ import annotations

import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.external_review_cross_patch_regression import (
    NON_SCOPE_PHRASES,
    run_and_write,
    run_cross_patch_regression,
)


ALL_TEST_GATES = [
    ("CROSS_PATCH_REGRESSION_REVIEW", "P0"),
    ("CLEAN_ROOM_REPRODUCTION_REVIEW", "P0"),
    ("RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW", "P0"),
    ("BROKER_IMPORT_STAGING_READINESS_REVIEW", "P0"),
    ("PORTFOLIO_EVENT_LEDGER_RUNTIME_READINESS_REVIEW", "P0"),
    ("ADVERSARIAL_INPUT_AND_FAILURE_MODE_REVIEW", "P0"),
    ("RELEASE_CI_ENVIRONMENT_PARITY_REVIEW", "P1"),
]


class ExternalReviewCrossPatchRegressionTests(unittest.TestCase):
    def _write(self, root: Path, relative_path: str, text: str) -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _registry(self, gates: list[tuple[str, str]] | None = None, omit_field: str | None = None) -> str:
        entries = []
        for gate_id, priority in gates or ALL_TEST_GATES:
            entry = {
                "gate_id": gate_id,
                "priority": priority,
                "purpose": f"Purpose for {gate_id}",
                "trigger_condition": "Before relevant feature class.",
                "required_inputs": ["input"],
                "required_outputs": ["output"],
                "acceptance_criteria": ["criterion"],
                "non_scope": ["feature implementation"],
                "blocks_features": ["feature"],
                "evidence_required": ["evidence"],
                "operator_acceptance_required": True,
            }
            if omit_field:
                entry.pop(omit_field, None)
            entries.append(entry)
        return json.dumps({"schema_version": 1, "gates": entries}, indent=2)

    def _sequence(self, gates: list[str] | None = None, extra: str = "") -> str:
        gate_text = "\n".join(f"- `{gate_id}`" for gate_id in (gates or [gate_id for gate_id, _ in ALL_TEST_GATES]))
        return f"# Sequence\n\nRequired gates:\n\n{gate_text}\n{extra}\n"

    def _source_of_truth_text(self) -> str:
        return "\n".join(
            [
                "external_review_packet/00_READ_ME_FIRST.md",
                "external_review_packet/HANDOFF_LATEST_CONTEXT.md",
                "external_review_packet/HANDOFF_LATEST.zip",
                "external_review_packet/HANDOFF_LATEST.sha256",
                "historische Reports nur als Kontext",
            ]
        )

    def _non_scope_text(self) -> str:
        return "\n".join(NON_SCOPE_PHRASES)

    def _make_fixture(self, root: Path, include_zip: bool = True) -> None:
        self._write(root, "docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml", self._registry())
        self._write(root, "docs/governance/EXTERNAL_REVIEW_GATE_SEQUENCE.md", self._sequence())
        self._write(root, "docs/governance/EXTERNAL_REVIEW_COVERAGE_STANDARD.md", self._source_of_truth_text() + "\n" + self._non_scope_text())
        self._write(root, "docs/architecture/CIOS_FEATURE_STATUS.yaml", "capability_id: external_review_coverage_standard\nlimitations:\n- not fully automated\n")
        self._write(root, "docs/architecture/CURRENT_KNOWN_GAPS.md", "# gaps\n\n| gap_id | title | severity | current_status | impact |\n| --- | --- | --- | --- | --- |\n| GAP-P0-100 | Cross-patch regression gate | P0 | documented_gap | CROSS_PATCH_REGRESSION_REVIEW |\n")
        for path in [
            "docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md",
            "docs/architecture/CIOS_MATURITY_MODEL.yaml",
            "docs/MODULE_CONTRACTS.md",
            "docs/CONTEXT_AND_ROADMAP.md",
            "README.md",
        ]:
            self._write(root, path, "placeholder\n")
        context = "\n".join(
            [
                self._source_of_truth_text(),
                "python -m pytest -q",
                "No module named pytest",
                "python -m ruff check .",
                "No module named ruff",
                "No full test suite is claimed",
                self._non_scope_text(),
            ]
        )
        self._write(root, "external_review_packet/00_READ_ME_FIRST.md", context)
        self._write(root, "external_review_packet/HANDOFF_LATEST_CONTEXT.md", context)
        self._write(root, "external_review_packet/HANDOFF_LATEST.sha256", "0" * 64 + "  HANDOFF_LATEST.zip\n")
        if include_zip:
            zip_path = root / "external_review_packet/HANDOFF_LATEST.zip"
            zip_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("HANDOFF_VALIDATION.txt", "commands_run:\n- command: unit\n  status: RECORDED\n")

    def _findings_text(self, root: Path) -> str:
        findings = run_cross_patch_regression("2026-05-21", repo_root=root)
        return "\n".join(f"{row.check_id}|{row.status}|{row.evidence}|{row.finding}" for row in findings)

    def test_complete_gate_registry_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root)
            text = self._findings_text(root)
            self.assertIn("GATE_REGISTRY_REQUIRED_FIELDS|PASS", text)
            self.assertNotIn("Gate entry misses a required field", text)

    def test_missing_registry_required_field_produces_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root)
            self._write(root, "docs/governance/EXTERNAL_REVIEW_GATE_REGISTRY.yaml", self._registry(omit_field="purpose"))
            text = self._findings_text(root)
            self.assertIn("GATE_REGISTRY_REQUIRED_FIELDS|FAIL", text)
            self.assertIn("missing purpose", text)

    def test_sequence_gate_missing_from_registry_is_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root)
            self._write(root, "docs/governance/EXTERNAL_REVIEW_GATE_SEQUENCE.md", self._sequence(extra="- `UNKNOWN_GATE_REVIEW`\n"))
            text = self._findings_text(root)
            self.assertIn("GATE_SEQUENCE_UNKNOWN_GATE|FAIL|UNKNOWN_GATE_REVIEW", text)

    def test_p0_registry_gate_missing_from_sequence_is_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root)
            sequence_gates = [gate_id for gate_id, _ in ALL_TEST_GATES if gate_id != "CROSS_PATCH_REGRESSION_REVIEW"]
            self._write(root, "docs/governance/EXTERNAL_REVIEW_GATE_SEQUENCE.md", self._sequence(sequence_gates))
            text = self._findings_text(root)
            self.assertIn("GATE_SEQUENCE_P0_COVERAGE|WARN|CROSS_PATCH_REGRESSION_REVIEW", text)

    def test_release_ci_gate_not_sequenced_is_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root)
            sequence_gates = [gate_id for gate_id, _ in ALL_TEST_GATES if gate_id != "RELEASE_CI_ENVIRONMENT_PARITY_REVIEW"]
            self._write(root, "docs/governance/EXTERNAL_REVIEW_GATE_SEQUENCE.md", self._sequence(sequence_gates))
            text = self._findings_text(root)
            self.assertIn("GATE_SEQUENCE_RELEASE_CI_PARITY|WARN|RELEASE_CI_ENVIRONMENT_PARITY_REVIEW", text)

    def test_pytest_ruff_failure_is_not_full_suite_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root)
            text = self._findings_text(root)
            self.assertIn("VALIDATION_REALITY_PYTEST|PASS", text)
            self.assertIn("VALIDATION_REALITY_RUFF|PASS", text)

    def test_recorded_is_not_interpreted_as_passed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root)
            text = self._findings_text(root)
            self.assertIn("VALIDATION_REALITY_RECORDED_COMMANDS|WARN", text)
            self.assertNotIn("VALIDATION_REALITY_RECORDED_COMMANDS|PASS", text)

    def test_ambiguous_addressed_by_this_patch_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root)
            self._write(root, "docs/architecture/CURRENT_KNOWN_GAPS.md", "# gaps\n\n| gap_id | title | severity | current_status | impact |\n| --- | --- | --- | --- | --- |\n| GAP-P0-001 | Clean-room gate | P0 | addressed_by_this_patch | clean-room review gate |\n")
            text = self._findings_text(root)
            self.assertIn("KNOWN_GAPS_AMBIGUOUS_PATCH_REFERENCE|WARN", text)

    def test_non_scope_boundaries_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root)
            self._write(root, "docs/governance/EXTERNAL_REVIEW_COVERAGE_STANDARD.md", self._source_of_truth_text())
            self._write(root, "docs/architecture/CIOS_FEATURE_STATUS.yaml", "capability_id: external_review_coverage_standard\n")
            self._write(root, "docs/architecture/CURRENT_KNOWN_GAPS.md", "# gaps\n")
            self._write(root, "external_review_packet/00_READ_ME_FIRST.md", self._source_of_truth_text())
            self._write(root, "external_review_packet/HANDOFF_LATEST_CONTEXT.md", self._source_of_truth_text())
            text = self._findings_text(root)
            self.assertIn("NON_SCOPE_PRESERVATION|WARN", text)

    def test_missing_zip_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root, include_zip=False)
            text = self._findings_text(root)
            self.assertIn("ZIP_NOT_AVAILABLE", text)
            self.assertIn("NOT_AVAILABLE", text)

    def test_csv_and_markdown_outputs_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root)
            result_1 = run_and_write("2026-05-21", repo_root=root, csv_output=root / "out.csv", report_output=root / "out.md")
            first_csv = (root / "out.csv").read_text(encoding="utf-8")
            first_md = (root / "out.md").read_text(encoding="utf-8")
            result_2 = run_and_write("2026-05-21", repo_root=root, csv_output=root / "out.csv", report_output=root / "out.md")
            self.assertEqual(first_csv, (root / "out.csv").read_text(encoding="utf-8"))
            self.assertEqual(first_md, (root / "out.md").read_text(encoding="utf-8"))
            with (root / "out.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertGreater(len(rows), 0)
            self.assertEqual(result_1["counts"], result_2["counts"])
            self.assertIn("External Review Cross-Patch Regression Report", first_md)


if __name__ == "__main__":
    unittest.main()
