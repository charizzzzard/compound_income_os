from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from src import repo_docs_drift_check


class RepoDocsDriftCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_docs_drift_{uuid.uuid4().hex}"
        (self.tmp / "src").mkdir(parents=True)
        (self.tmp / "docs").mkdir(parents=True)
        (self.tmp / "website" / "compound-income-os-landing").mkdir(parents=True)
        (self.tmp / "src" / "documented_module.py").write_text("", encoding="utf-8")
        (self.tmp / "src" / "undocumented_module.py").write_text("", encoding="utf-8")
        (self.tmp / "src" / "handoff_zip_export.py").write_text("", encoding="utf-8")
        (self.tmp / "docs" / "MODULE_CONTRACTS.md").write_text("src.documented_module\n", encoding="utf-8")
        (self.tmp / "docs" / "HANDOFF_CONTRACT.md").write_text("handoff_zip_export\n", encoding="utf-8")
        (self.tmp / "website" / "compound-income-os-landing" / "README.md").write_text(
            "website/compound-income-os-landing/mockup\nwebsite/compound-income-os-landing/mockup/source_materials/claude_design_compound_income_os\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_reports_new_src_modules_not_mentioned_in_module_contracts(self) -> None:
        with patch.object(repo_docs_drift_check, "resolve_repo_path", side_effect=lambda value: self.tmp if str(value) == "." else self.tmp / value):
            result = repo_docs_drift_check.run_repo_docs_drift_check(output=self.tmp / "out.csv", report_output=self.tmp / "report.md")
        rows = self.read_csv(result.output_path)
        self.assertIn("src/undocumented_module.py", {row["path"] for row in rows})
        self.assertNotIn("src/documented_module.py", {row["path"] for row in rows})

    def test_no_website_mockup_finding_when_readme_mentions_paths(self) -> None:
        with patch.object(repo_docs_drift_check, "resolve_repo_path", side_effect=lambda value: self.tmp if str(value) == "." else self.tmp / value):
            result = repo_docs_drift_check.run_repo_docs_drift_check(output=self.tmp / "out.csv", report_output=self.tmp / "report.md")
        rows = self.read_csv(result.output_path)
        self.assertNotIn("WEBSITE_MOCKUP_FOLDER_NOT_MENTIONED", {row["finding_type"] for row in rows})


if __name__ == "__main__":
    unittest.main()
