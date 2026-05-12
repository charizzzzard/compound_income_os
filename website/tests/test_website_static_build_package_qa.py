from __future__ import annotations

import csv
import re
import unittest
import zipfile
from datetime import date
from pathlib import Path

from src.handoff_zip_export import HANDOFF_ARTIFACT_FILES, HANDOFF_ARTIFACT_GLOBS, is_forbidden_entry
from website.src.website_static_build_package_qa import (
    STATIC_QA_OUTPUT,
    STATIC_QA_SUMMARY_OUTPUT,
    run_website_static_build_package_qa,
)


ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "website" / "compound-income-os-landing" / "dist"


def read_csv(path_value: str) -> list[dict[str, str]]:
    with (ROOT / path_value).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class WebsiteStaticBuildPackageQaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_website_static_build_package_qa(
            report_date=date(2026, 4, 27),
            package_date=date(2026, 4, 27),
            preview_status="PASS",
        )
        cls.rows = read_csv(STATIC_QA_OUTPUT)
        cls.summary = read_csv(STATIC_QA_SUMMARY_OUTPUT)[0]

    def row(self, check_name: str) -> dict[str, str]:
        return next(row for row in self.rows if row["check_name"] == check_name)

    def test_static_build_qa_artifacts_exist(self) -> None:
        self.assertTrue((ROOT / STATIC_QA_OUTPUT).is_file())
        self.assertTrue((ROOT / STATIC_QA_SUMMARY_OUTPUT).is_file())
        self.assertTrue((ROOT / "reports" / "2026-04-27" / "website_static_build_package_report.md").is_file())

    def test_summary_keeps_public_deploy_disabled(self) -> None:
        self.assertEqual(self.summary["public_deploy_performed"], "False")
        self.assertIn(self.summary["static_build_qa_status"], {"PASS", "REVIEW"})
        self.assertEqual(self.summary["private_data_leak_detected"], "False")
        self.assertEqual(self.summary["dummy_claims_detected"], "False")

    def test_dist_inspection_blocks_forbidden_entries(self) -> None:
        for check_name in (
            "no_env_files_in_dist",
            "no_node_modules_in_dist",
            "no_private_raw_paths_in_dist",
            "no_private_sec_identity_markers_in_dist",
            "no_private_values_in_dist",
        ):
            self.assertEqual(self.row(check_name)["status"], "PASS", self.row(check_name))

    def test_asset_path_check_is_deterministic(self) -> None:
        row = self.row("asset_paths_static_safe")
        self.assertIn(row["status"], {"PASS", "REVIEW", "NOT_AVAILABLE"})
        if (DIST / "index.html").exists():
            self.assertNotEqual(row["status"], "NOT_AVAILABLE")

    def test_sample_payload_is_present_or_explicitly_reported(self) -> None:
        row = self.row("sample_payload_in_dist")
        self.assertIn(row["status"], {"PASS", "REVIEW", "NOT_AVAILABLE"})
        self.assertIn("SAMPLE_PAYLOAD", row["reason_codes"])

    def test_static_package_contains_only_allowed_review_files(self) -> None:
        package_path = self.result.static_package.path
        self.assertIsNotNone(package_path)
        self.assertTrue(package_path.is_file())
        with zipfile.ZipFile(package_path) as archive:
            names = archive.namelist()
        self.assertTrue(names)
        self.assertTrue(all(name.startswith("dist/") or name == "PRIVATE_PREVIEW_NOTES.txt" for name in names))
        for name in names:
            self.assertFalse(name.startswith("src/"), name)
            self.assertNotIn("node_modules/", name)
            self.assertNotIn("deploy_artifacts/", name)
            self.assertNotRegex(name, r"(^|/)\.env(\.|$)")
            self.assertNotIn("data/raw/private", name)
        self.assertEqual(self.result.static_package.forbidden_entries_count, 0)

    def test_report_has_no_public_or_decision_ready_dummy_claim(self) -> None:
        report = (ROOT / "reports" / "2026-04-27" / "website_static_build_package_report.md").read_text(encoding="utf-8")
        self.assertNotRegex(report, re.compile(r"public launch[^.\n]{0,80}(ready|complete|finished)", re.I))
        self.assertNotRegex(report, re.compile(r"decision readiness[^.\n]{0,80}(PASS|READY)", re.I))
        self.assertIn("No public deployment is performed by this QA.", report)

    def test_handoff_allowlist_includes_qa_artifacts_but_excludes_dist_and_deploy_artifacts(self) -> None:
        self.assertIn("data/processed/website_static_build_package_qa.csv", HANDOFF_ARTIFACT_FILES)
        self.assertIn("data/processed/website_static_build_package_summary.csv", HANDOFF_ARTIFACT_FILES)
        self.assertIn("reports/*/website_static_build_package_report.md", HANDOFF_ARTIFACT_GLOBS)
        self.assertTrue(is_forbidden_entry("website/compound-income-os-landing/dist/index.html"))
        self.assertTrue(is_forbidden_entry("website/compound-income-os-landing/deploy_artifacts/review.zip"))


if __name__ == "__main__":
    unittest.main()
