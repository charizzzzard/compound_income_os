from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MATRIX_PATH = ROOT / "configs" / "test_reproduction_matrix.json"


class TestReproductionMatrixTests(unittest.TestCase):
    def load_matrix(self) -> dict:
        return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))

    def test_matrix_exists_and_defines_required_categories(self) -> None:
        matrix = self.load_matrix()

        self.assertEqual(matrix["schema_version"], 1)
        self.assertEqual(
            set(matrix["classification_values"]),
            {
                "ZIP_SAFE",
                "LOCAL_REPO_REQUIRED",
                "PRIVATE_INPUT_REQUIRED",
                "GIT_CONTEXT_REQUIRED",
                "TOOLING_OPTIONAL",
                "UNKNOWN",
            },
        )
        self.assertIn("EXECUTED_IN_CURRENT_REPO", matrix["execution_status_values"])
        self.assertIn("EXECUTED_IN_ZIP_CONTEXT", matrix["execution_status_values"])
        self.assertIn("RECORDED_FROM_PREVIOUS_RUN", matrix["execution_status_values"])

    def test_key_tests_are_classified_without_overclaim(self) -> None:
        matrix = self.load_matrix()
        by_command = {entry["command"]: entry for entry in matrix["tests"]}

        self.assertEqual(
            by_command["python -m unittest tests.test_zip_safe_operator_journey -v"]["classification"],
            "ZIP_SAFE",
        )
        self.assertEqual(
            by_command["python -m unittest tests.test_handoff_zip_export -v"]["classification"],
            "GIT_CONTEXT_REQUIRED",
        )
        self.assertEqual(
            by_command["python -m unittest tests.test_handoff_bundle -v"]["classification"],
            "GIT_CONTEXT_REQUIRED",
        )
        self.assertEqual(
            by_command["python -m unittest tests.test_personal_run_engine -v"]["classification"],
            "LOCAL_REPO_REQUIRED",
        )
        self.assertEqual(by_command["python -m pytest -q"]["classification"], "TOOLING_OPTIONAL")
        self.assertEqual(by_command["python -m ruff check ."]["classification"], "TOOLING_OPTIONAL")

    def test_zip_safe_entries_do_not_claim_private_or_release_readiness(self) -> None:
        matrix = self.load_matrix()
        text = json.dumps(matrix, sort_keys=True).lower()

        self.assertNotIn("production ready", text)
        self.assertNotIn("investment ready", text)
        self.assertNotIn("automatic release acceptance", text)
        self.assertIn("no private raw data", text)
        self.assertIn("not release acceptance", text)


if __name__ == "__main__":
    unittest.main()
