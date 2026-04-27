from __future__ import annotations

import csv
import shutil
import unittest
import zipfile
from datetime import date
from pathlib import Path

from src.handoff_zip_export import HANDOFF_ARTIFACT_FILES, HANDOFF_ARTIFACT_GLOBS
from src.website_private_preview_handoff_qa import (
    EXPECTED_ENTRIES,
    HANDOFF_QA_SUMMARY_OUTPUT,
    REQUIRED_QA_ARTIFACTS,
    REQUIRED_SCREENSHOTS,
    REQUIRED_WEBSITE_ENTRIES,
    ZIP_CONTENT_INDEX_OUTPUT,
    build_summary,
    build_zip_content_index,
    decision_ready_claim_detected,
    is_handoff_forbidden_entry,
    public_launch_claim_detected,
    run_website_private_preview_handoff_qa,
)


ROOT = Path(__file__).resolve().parent.parent
REPORT = "reports/2026-04-27/website_private_preview_handoff_qa_report.md"


def read_csv(path_value: str) -> list[dict[str, str]]:
    with (ROOT / path_value).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class WebsitePrivatePreviewHandoffQaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = ROOT / "tests" / "_tmp_handoff_qa"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def make_zip(self, name: str, entries: dict[str, str] | None = None) -> Path:
        zip_path = self.temp_dir / name
        with zipfile.ZipFile(zip_path, "w") as archive:
            for entry in EXPECTED_ENTRIES:
                archive.writestr(entry, "not public launch ready\nnot decision-ready\nnot investment advice\n")
            for entry, content in (entries or {}).items():
                archive.writestr(entry, content)
        return zip_path

    def test_zip_content_index_artifact_is_generated(self) -> None:
        zip_path = self.make_zip("clean.zip")
        run_website_private_preview_handoff_qa(zip_path, report_date=date(2026, 4, 27))
        self.assertTrue((ROOT / ZIP_CONTENT_INDEX_OUTPUT).is_file())

    def test_handoff_qa_summary_artifact_is_generated(self) -> None:
        zip_path = self.make_zip("clean.zip")
        run_website_private_preview_handoff_qa(zip_path, report_date=date(2026, 4, 27))
        self.assertTrue((ROOT / HANDOFF_QA_SUMMARY_OUTPUT).is_file())

    def test_report_is_generated(self) -> None:
        zip_path = self.make_zip("clean.zip")
        run_website_private_preview_handoff_qa(zip_path, report_date=date(2026, 4, 27))
        self.assertTrue((ROOT / REPORT).is_file())

    def test_required_website_entries_are_checked(self) -> None:
        zip_path = self.make_zip("clean.zip")
        rows, _facts = build_zip_content_index(zip_path)
        entries = {row["zip_entry"] for row in rows if row["expected"] == "yes"}
        for entry in REQUIRED_WEBSITE_ENTRIES:
            self.assertIn(entry, entries)

    def test_required_screenshot_entries_are_checked(self) -> None:
        zip_path = self.make_zip("clean.zip")
        rows, _facts = build_zip_content_index(zip_path)
        entries = {row["zip_entry"] for row in rows if row["expected"] == "yes"}
        for entry in REQUIRED_SCREENSHOTS:
            self.assertIn(entry, entries)

    def test_required_qa_artifacts_are_checked(self) -> None:
        zip_path = self.make_zip("clean.zip")
        rows, _facts = build_zip_content_index(zip_path)
        entries = {row["zip_entry"] for row in rows if row["expected"] == "yes"}
        for entry in REQUIRED_QA_ARTIFACTS:
            self.assertIn(entry, entries)

    def test_forbidden_entries_are_detected_in_synthetic_zip_fixture(self) -> None:
        zip_path = self.make_zip("bad.zip", {"data/raw/private/secret.csv": "x"})
        rows, facts = build_zip_content_index(zip_path)
        summary = build_summary(rows, facts)
        self.assertGreater(int(summary["forbidden_entries_count"]), 0)
        self.assertEqual(summary["handoff_qa_status"], "BLOCKED")

    def test_build_and_env_directories_are_forbidden(self) -> None:
        for entry in (
            "website/compound-income-os-landing/dist/index.html",
            "website/compound-income-os-landing/deploy_artifacts/dist.zip",
            "website/compound-income-os-landing/node_modules/react/index.js",
            "website/compound-income-os-landing/.env",
            "website/compound-income-os-landing/.env.local",
        ):
            self.assertTrue(is_handoff_forbidden_entry(entry), entry)

    def test_private_raw_paths_and_private_sec_identity_map_are_forbidden(self) -> None:
        self.assertTrue(is_handoff_forbidden_entry("data/raw/private/holdings.csv"))
        self.assertTrue(is_handoff_forbidden_entry("personal_sec_identity_map.csv"))

    def test_summary_pass_for_clean_synthetic_zip_fixture(self) -> None:
        zip_path = self.make_zip("clean.zip")
        rows, facts = build_zip_content_index(zip_path)
        summary = build_summary(rows, facts)
        self.assertEqual(summary["handoff_qa_status"], "PASS")
        self.assertEqual(summary["forbidden_entries_count"], "0")

    def test_summary_blocked_for_forbidden_synthetic_zip_fixture(self) -> None:
        zip_path = self.make_zip("blocked.zip", {"website/compound-income-os-landing/.env": "SECRET=1"})
        rows, facts = build_zip_content_index(zip_path)
        summary = build_summary(rows, facts)
        self.assertEqual(summary["handoff_qa_status"], "BLOCKED")
        self.assertEqual(summary["env_files_included"], "True")

    def test_claim_scanner_allows_negative_compliance_language(self) -> None:
        self.assertFalse(public_launch_claim_detected("This is not public launch ready. Public launch remains blocked."))
        self.assertFalse(decision_ready_claim_detected("This is not decision-ready. Decision readiness is blocked."))

    def test_claim_scanner_blocks_positive_public_launch_or_decision_ready_claims(self) -> None:
        self.assertTrue(public_launch_claim_detected("This website is public launch ready."))
        self.assertTrue(decision_ready_claim_detected("This portfolio is decision ready and ready to invest."))

    def test_handoff_allowlist_includes_new_final_handoff_qa_artifacts(self) -> None:
        self.assertIn("data/processed/website_private_preview_handoff_zip_content_index.csv", HANDOFF_ARTIFACT_FILES)
        self.assertIn("data/processed/website_private_preview_handoff_qa_summary.csv", HANDOFF_ARTIFACT_FILES)
        self.assertIn("reports/*/website_private_preview_handoff_qa_report.md", HANDOFF_ARTIFACT_GLOBS)

    def test_current_source_zip_can_generate_pass_summary_when_present(self) -> None:
        source_zip = ROOT / "compound_income_os_HANDOFF_20260427-163623_1bb6a1a.zip"
        if not source_zip.exists():
            self.skipTest("pre-final handoff ZIP not present")
        run_website_private_preview_handoff_qa(source_zip, report_date=date(2026, 4, 27))
        summary = read_csv(HANDOFF_QA_SUMMARY_OUTPUT)[0]
        self.assertEqual(summary["source_handoff_zip_file_count"], "261")
        self.assertEqual(summary["forbidden_entries_count"], "0")


if __name__ == "__main__":
    unittest.main()
