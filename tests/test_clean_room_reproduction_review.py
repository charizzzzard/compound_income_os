from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.clean_room_reproduction_review import (
    NON_SCOPE_PHRASES,
    REQUIRED_ZIP_FILES,
    run_and_write,
    run_clean_room_reproduction_review,
)
from src.external_review_cross_patch_regression import REQUIRED_GATE_FIELDS


TEST_GATES = [
    ("CROSS_PATCH_REGRESSION_REVIEW", "P0"),
    ("CLEAN_ROOM_REPRODUCTION_REVIEW", "P0"),
    ("RUNTIME_ENFORCEMENT_BOUNDARY_REVIEW", "P0"),
    ("BROKER_IMPORT_STAGING_READINESS_REVIEW", "P0"),
    ("PORTFOLIO_EVENT_LEDGER_RUNTIME_READINESS_REVIEW", "P0"),
    ("ADVERSARIAL_INPUT_AND_FAILURE_MODE_REVIEW", "P0"),
    ("RELEASE_CI_ENVIRONMENT_PARITY_REVIEW", "P1"),
]


class CleanRoomReproductionReviewTests(unittest.TestCase):
    def _write(self, root: Path, relative_path: str, text: str) -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _source_of_truth_text(self) -> str:
        return "\n".join(
            [
                "Bei Konflikten gilt diese Reihenfolge:",
                "1. `external_review_packet/00_READ_ME_FIRST.md`",
                "2. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`",
                "3. `external_review_packet/HANDOFF_LATEST.zip`",
                "4. `external_review_packet/HANDOFF_LATEST.sha256`",
                "5. historische Reports nur als Kontext",
            ]
        )

    def _non_scope_text(self) -> str:
        return "\n".join(
            [
                "keine Investmentlogik",
                "kein produktiver Portfolio Event Ledger",
                "keine Event-Ledger-Runtime",
                "kein Broker Import",
                "kein Broker Parser",
                "kein Provider Adapter",
                "keine API-Anbindung",
                "kein Scraping oder Web-Crawling",
                "keine Corporate Actions Engine",
                "keine FX Engine",
                "kein Replay, Backtesting oder Simulation",
                "keine Outcome Attribution",
                "kein Dashboard",
                "keine Valuation Automation",
                "keine Buy/Sell Recommendation Aenderungen",
                "keine Steuerberechnung",
                "keine Legal-/Commercial-Freigabe",
                "keine Order Execution",
                "keine Runtime-LLM-Agentenlogik",
                "keine Runtime-Enforcement-Engine",
                "keine vollautomatische Release-Akzeptanz",
            ]
        )

    def _registry(self) -> str:
        gates = []
        for gate_id, priority in TEST_GATES:
            gates.append(
                {
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
            )
        for gate in gates:
            self.assertEqual(set(REQUIRED_GATE_FIELDS) - set(gate), set())
        return json.dumps({"schema_version": 1, "gates": gates}, indent=2)

    def _sequence(self) -> str:
        gate_lines = "\n".join(f"- `{gate_id}`" for gate_id, _priority in TEST_GATES)
        return f"# Gate Sequence\n\n{gate_lines}\n"

    def _external_context(self, head: str = "abc123") -> str:
        return "\n".join(
            [
                self._source_of_truth_text(),
                f"current_handoff_head: {head}",
                "python -m pytest -q",
                "No module named pytest",
                "python -m ruff check .",
                "No module named ruff",
                "No full test suite is claimed",
                "python -m src.external_review_cross_patch_regression --as-of-date 2026-05-21",
                "result: status: WARN, findings: 999, FAIL: 0, WARN: 999, PASS: 0",
                self._non_scope_text(),
            ]
        )

    def _make_cross_patch_inputs(self, root: Path) -> None:
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
        (root / "src").mkdir(exist_ok=True)
        (root / "tests").mkdir(exist_ok=True)
        self._write(root, "src/external_review_cross_patch_regression.py", "placeholder\n")
        self._write(root, "tests/test_external_review_cross_patch_regression.py", "placeholder\n")

    def _make_packet(self, root: Path, *, include_zip: bool = True, sha_mismatch: bool = False, include_external_metadata: bool = True) -> None:
        packet = root / "external_review_packet"
        packet.mkdir(parents=True, exist_ok=True)
        context = self._external_context()
        if include_external_metadata:
            self._write(root, "external_review_packet/00_READ_ME_FIRST.md", context)
            self._write(root, "external_review_packet/HANDOFF_LATEST_CONTEXT.md", context)
        if not include_zip:
            self._write(root, "external_review_packet/HANDOFF_LATEST.sha256", "0" * 64 + "  HANDOFF_LATEST.zip\n")
            return
        zip_path = packet / "HANDOFF_LATEST.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("HANDOFF_CONTEXT.md", "# Handoff\n\n- head: `abc123`\n")
            archive.writestr("HANDOFF_VALIDATION.txt", "commands_run:\n- command: unit\n  status: RECORDED\n")
            for required in REQUIRED_ZIP_FILES:
                archive.writestr(required, "placeholder\n")
        digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        if sha_mismatch:
            digest = "0" * 64
        self._write(root, "external_review_packet/HANDOFF_LATEST.sha256", f"{digest}  HANDOFF_LATEST.zip\n")

    def _make_fixture(self, root: Path, **packet_options: object) -> None:
        self._make_cross_patch_inputs(root)
        self._make_packet(root, **packet_options)

    def _findings_text(self, root: Path) -> str:
        findings = run_clean_room_reproduction_review("2026-05-21", repo_root=root)
        return "\n".join(f"{finding.check_id}|{finding.status}|{finding.evidence}|{finding.finding}" for finding in findings)

    def test_complete_fixture_runs_without_crash_and_flags_recorded_baseline_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root)
            text = self._findings_text(root)
            self.assertIn("PACKET_METADATA_PRESENT|PASS", text)
            self.assertIn("SHA256_MATCH|PASS", text)
            self.assertIn("ZIP_TESTZIP|PASS", text)
            self.assertIn("VALIDATION_RECORDED_COMMANDS|WARN", text)
            self.assertIn("CROSS_PATCH_REPRODUCTION_BASELINE|WARN", text)

    def test_missing_zip_is_not_available_without_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root, include_zip=False)
            text = self._findings_text(root)
            self.assertIn("ZIP_NOT_AVAILABLE", text)
            self.assertIn("ZIP_REQUIRED_FILES|NOT_AVAILABLE", text)

    def test_sha_mismatch_is_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root, sha_mismatch=True)
            text = self._findings_text(root)
            self.assertIn("SHA256_MATCH|FAIL", text)

    def test_recorded_is_not_passed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root)
            text = self._findings_text(root)
            self.assertIn("VALIDATION_RECORDED_COMMANDS|WARN", text)
            self.assertNotIn("VALIDATION_RECORDED_COMMANDS|PASS", text)

    def test_release_acceptance_non_scope_accepts_negative_variants(self) -> None:
        variants = [
            "keine automatische Release-Akzeptanz",
            "keine vollautomatische Release-Akzeptanz",
            "no release acceptance",
            "no full release acceptance",
            "no automated release acceptance",
        ]
        release_variants = NON_SCOPE_PHRASES["Full release acceptance"]

        for variant in variants:
            with self.subTest(variant=variant):
                self.assertIn(variant, release_variants)

    def test_missing_external_metadata_produces_zip_only_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root, include_external_metadata=False)
            text = self._findings_text(root)
            self.assertIn("EXTERNAL_CONTEXT_PRESENT|MISSING", text)
            self.assertIn("ZIP_ONLY_VS_FULL_PACKET|WARN", text)

    def test_required_zip_files_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root)
            text = self._findings_text(root)
            self.assertIn("ZIP_REQUIRED_FILES|PASS", text)

    def test_required_zip_files_include_clean_room_self_protection(self) -> None:
        self.assertIn("src/clean_room_reproduction_review.py", REQUIRED_ZIP_FILES)
        self.assertIn("tests/test_clean_room_reproduction_review.py", REQUIRED_ZIP_FILES)

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
            self.assertEqual(result_1["counts"], result_2["counts"])
            with (root / "out.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertGreater(len(rows), 0)
            self.assertIn("Clean-Room Reproduction Review Report", first_md)

    def test_producer_uses_no_network_imports(self) -> None:
        source = Path("src/clean_room_reproduction_review.py").read_text(encoding="utf-8")
        for forbidden in ["requests", "urllib", "httpx", "socket", "subprocess"]:
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)

    def test_report_has_no_runtime_or_investment_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_fixture(root)
            run_and_write("2026-05-21", repo_root=root, csv_output=root / "out.csv", report_output=root / "out.md")
            report = (root / "out.md").read_text(encoding="utf-8")
            self.assertIn("does not implement release acceptance", report)
            self.assertIn("investment logic", report)
            self.assertIn("broker import", report)
            for label in NON_SCOPE_PHRASES:
                self.assertNotIn(f"implements {label}", report.lower())


if __name__ == "__main__":
    unittest.main()
