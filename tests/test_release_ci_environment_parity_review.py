from __future__ import annotations

import csv
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from src.release_ci_environment_parity_review import (
    run_and_write,
    run_environment_parity_review,
)


class ReleaseCiEnvironmentParityReviewTests(unittest.TestCase):
    def _write_handoff_zip(self, root: Path, validation_text: str) -> None:
        packet = root / "external_review_packet"
        packet.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(packet / "HANDOFF_LATEST.zip", "w") as archive:
            archive.writestr("HANDOFF_VALIDATION.txt", validation_text)

    def _rows_text(self, root: Path) -> str:
        rows = run_environment_parity_review("2026-05-21", repo_root=root)
        return "\n".join(f"{row.check_id}|{row.severity}|{row.status}|{row.command}|{row.evidence}" for row in rows)

    def test_python_environment_is_reported_without_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = self._rows_text(root)
            self.assertIn("PYTHON_VERSION|INFO|AVAILABLE", text)
            self.assertIn("WORKING_DIRECTORY_CONTEXT|INFO|AVAILABLE", text)
            self.assertNotIn(str(root), text)

    def test_pytest_and_ruff_missing_are_not_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fake_find_spec(name: str) -> object | None:
                if name in {"pytest", "ruff"}:
                    return None
                return object()

            with patch("src.release_ci_environment_parity_review.importlib.util.find_spec", side_effect=fake_find_spec):
                text = self._rows_text(root)
            self.assertIn("TOOL_PYTEST|WARN|NOT_INSTALLED", text)
            self.assertIn("TOOL_RUFF|WARN|NOT_INSTALLED", text)
            self.assertIn("EXPECTED_PYTEST|WARN|SKIPPED_NOT_AVAILABLE", text)
            self.assertIn("EXPECTED_RUFF|WARN|SKIPPED_NOT_AVAILABLE", text)
            self.assertNotIn("TOOL_PYTEST|PASS|AVAILABLE", text)
            self.assertNotIn("TOOL_RUFF|PASS|AVAILABLE", text)

    def test_expected_commands_are_not_run_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fake_find_spec(name: str) -> object | None:
                return object()

            with patch("src.release_ci_environment_parity_review.importlib.util.find_spec", side_effect=fake_find_spec):
                text = self._rows_text(root)
            self.assertIn("EXPECTED_UNITTEST_PARITY_REVIEW|INFO|NOT_RUN", text)
            self.assertIn("EXPECTED_PARITY_CLI|INFO|NOT_RUN", text)
            self.assertIn("EXPECTED_PYTEST|INFO|NOT_RUN", text)

    def test_git_missing_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("src.release_ci_environment_parity_review.shutil.which", return_value=None):
                text = self._rows_text(root)
            self.assertIn("TOOL_GIT|FAIL|NOT_INSTALLED", text)
            self.assertIn("EXPECTED_GIT_DIFF_CHECK|WARN|SKIPPED_NOT_AVAILABLE", text)

    def test_recorded_handoff_commands_are_warn_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_handoff_zip(root, "commands_run:\n- command: unit\n  status: RECORDED\n")
            text = self._rows_text(root)
            self.assertIn("HANDOFF_VALIDATION_RECORDED|WARN|NOT_RUN", text)
            self.assertNotIn("HANDOFF_VALIDATION_RECORDED|PASS|AVAILABLE", text)

    def test_missing_handoff_zip_is_not_applicable_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = self._rows_text(root)
            self.assertIn("HANDOFF_VALIDATION_RECORDED|WARN|NOT_APPLICABLE", text)

    def test_csv_and_markdown_outputs_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_1 = run_and_write("2026-05-21", repo_root=root, csv_output=root / "out.csv", report_output=root / "out.md")
            csv_1 = (root / "out.csv").read_text(encoding="utf-8")
            md_1 = (root / "out.md").read_text(encoding="utf-8")
            result_2 = run_and_write("2026-05-21", repo_root=root, csv_output=root / "out.csv", report_output=root / "out.md")
            self.assertEqual(csv_1, (root / "out.csv").read_text(encoding="utf-8"))
            self.assertEqual(md_1, (root / "out.md").read_text(encoding="utf-8"))
            self.assertEqual(result_1["status_counts"], result_2["status_counts"])
            with (root / "out.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertGreater(len(rows), 0)
            self.assertIn("Release CI Environment Parity Review Report", md_1)

    def test_report_has_no_release_or_investment_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_and_write("2026-05-21", repo_root=root, csv_output=root / "out.csv", report_output=root / "out.md")
            report = (root / "out.md").read_text(encoding="utf-8").lower()
            self.assertIn("does not implement release acceptance", report)
            self.assertIn("investment logic", report)
            self.assertIn("product/production readiness", report)
            self.assertNotIn("ci-green", report.replace("do not claim ci-green", ""))

    def test_module_uses_no_network_or_process_imports(self) -> None:
        source = Path("src/release_ci_environment_parity_review.py").read_text(encoding="utf-8")
        for forbidden in ["requests", "urllib", "httpx", "socket", "subprocess"]:
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)


if __name__ == "__main__":
    unittest.main()
