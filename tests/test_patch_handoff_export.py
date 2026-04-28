from __future__ import annotations

import shutil
import unittest
import zipfile
from pathlib import Path

from src.patch_handoff_export import export_patch_handoff_zip, is_forbidden_patch_handoff_entry


ROOT = Path(__file__).resolve().parent.parent


class PatchHandoffExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "patch_handoff_export_fixture"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.include_file = self.tmp / "artifact.txt"
        self.include_file.write_text("artifact\n", encoding="utf-8")

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def test_patch_handoff_wrapper_uses_unified_contract(self) -> None:
        result = export_patch_handoff_zip(
            patch_id="unit_patch",
            include_paths=[self.include_file],
            output_dir=self.tmp,
            summary="unit summary",
            validation="unit validation",
        )

        with zipfile.ZipFile(result.zip_path, "r") as archive:
            names = set(archive.namelist())
            context_text = archive.read("HANDOFF_CONTEXT.md").decode("utf-8")
            report_text = archive.read("HANDOFF_REPORT.md").decode("utf-8")

        self.assertIn("tests/patch_handoff_export_fixture/artifact.txt", names)
        self.assertIn("HANDOFF_CONTEXT.md", names)
        self.assertIn("HANDOFF_REPORT.md", names)
        self.assertIn("HANDOFF_MANIFEST.csv", names)
        self.assertNotIn("PATCH_HANDOFF_CONTEXT.md", names)
        self.assertIn("profile: `patch`", context_text)
        self.assertIn("unit validation", report_text)

    def test_private_raw_paths_are_rejected_by_wrapper(self) -> None:
        private_path = ROOT / "data" / "raw" / "private" / "fundamentals" / "secret.csv"

        with self.assertRaises(ValueError):
            export_patch_handoff_zip(patch_id="bad", include_paths=[private_path], output_dir=self.tmp)

    def test_forbidden_entry_rules_block_secrets_and_nested_zips(self) -> None:
        self.assertTrue(is_forbidden_patch_handoff_entry("data/raw/private/fundamentals/sec_user_agent.local.txt"))
        self.assertTrue(is_forbidden_patch_handoff_entry(".env"))
        self.assertTrue(is_forbidden_patch_handoff_entry("old.zip"))
        self.assertTrue(is_forbidden_patch_handoff_entry("website/compound-income-os-landing/dist/index.html"))
        self.assertFalse(is_forbidden_patch_handoff_entry("data/processed/personal_review.csv"))
        self.assertFalse(is_forbidden_patch_handoff_entry("reports/2026-04-27/personal_review.md"))


if __name__ == "__main__":
    unittest.main()
