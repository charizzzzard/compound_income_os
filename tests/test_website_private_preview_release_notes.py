from __future__ import annotations

import csv
import re
import unittest
from datetime import date
from pathlib import Path

from src.handoff_zip_export import HANDOFF_ARTIFACT_FILES, HANDOFF_ARTIFACT_GLOBS
from src.website_private_preview_release_notes import (
    HANDOFF_INDEX_OUTPUT,
    RELEASE_SUMMARY_OUTPUT,
    run_website_private_preview_release_notes,
)


ROOT = Path(__file__).resolve().parent.parent
REPORT = "reports/2026-04-27/website_private_preview_release_notes.md"


def read_csv(path_value: str) -> list[dict[str, str]]:
    with (ROOT / path_value).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class WebsitePrivatePreviewReleaseNotesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_website_private_preview_release_notes(report_date=date(2026, 4, 27))
        cls.index_rows = read_csv(HANDOFF_INDEX_OUTPUT)
        cls.summary = read_csv(RELEASE_SUMMARY_OUTPUT)[0]
        cls.report = (ROOT / REPORT).read_text(encoding="utf-8")

    def names_for_type(self, item_type: str) -> set[str]:
        return {row["item_name"] for row in self.index_rows if row["item_type"] == item_type}

    def test_handoff_index_artifact_is_generated(self) -> None:
        self.assertTrue((ROOT / HANDOFF_INDEX_OUTPUT).is_file())

    def test_release_summary_artifact_is_generated(self) -> None:
        self.assertTrue((ROOT / RELEASE_SUMMARY_OUTPUT).is_file())

    def test_release_notes_report_is_generated(self) -> None:
        self.assertTrue((ROOT / REPORT).is_file())

    def test_all_main_pages_are_present_in_handoff_index(self) -> None:
        pages = self.names_for_type("PAGE")
        for page in ("Home", "Workflow", "Evidence", "Portfolio", "Dashboard", "Manifesto", "About alias"):
            self.assertIn(page, pages)
        self.assertEqual(self.summary["pages_total"], "7")

    def test_all_six_screenshots_are_present_in_handoff_index(self) -> None:
        screenshots = self.names_for_type("SCREENSHOT")
        for screenshot in (
            "Home screenshot",
            "Workflow screenshot",
            "Evidence screenshot",
            "Portfolio screenshot",
            "Dashboard screenshot",
            "Manifesto screenshot",
        ):
            self.assertIn(screenshot, screenshots)
        self.assertEqual(self.summary["screenshots_count"], "6")

    def test_route_matrix_qa_artifacts_are_present_in_handoff_index(self) -> None:
        names = self.names_for_type("QA_ARTIFACT")
        self.assertIn("Route Matrix CSV", names)
        self.assertIn("CTA Matrix CSV", names)
        self.assertIn("Copy Guardrails CSV", names)
        self.assertIn("Route Matrix Report", names)

    def test_static_build_qa_artifacts_are_present_in_handoff_index(self) -> None:
        names = self.names_for_type("BUILD_QA")
        self.assertIn("Static Build QA CSV", names)
        self.assertIn("Static Build Summary CSV", names)
        self.assertIn("Static Build Report", names)

    def test_copy_freeze_artifacts_are_present_in_handoff_index(self) -> None:
        names = self.names_for_type("QA_ARTIFACT")
        self.assertIn("Copy Freeze Matrix CSV", names)
        self.assertIn("Copy Freeze Summary CSV", names)
        self.assertIn("Copy Freeze Report", names)

    def test_summary_keeps_public_deploy_disabled(self) -> None:
        self.assertEqual(self.summary["public_deploy_performed"], "False")
        self.assertIn(self.summary["handoff_release_status"], {"PASS", "REVIEW"})

    def test_summary_reports_no_private_data_leak(self) -> None:
        self.assertEqual(self.summary["private_data_leak_detected"], "False")

    def test_summary_reports_no_dummy_claims(self) -> None:
        self.assertEqual(self.summary["dummy_claims_detected"], "False")

    def test_release_notes_contain_public_launch_blockers(self) -> None:
        for blocker in ("real CTA targets", "imprint URL", "privacy policy URL", "pricing and scope review"):
            self.assertIn(blocker, self.report)

    def test_release_notes_do_not_claim_public_launch_readiness(self) -> None:
        self.assertNotRegex(self.report, re.compile(r"public launch[^.\n]{0,80}(ready|complete|finished)", re.I))
        self.assertIn("Not a public launch.", self.report)

    def test_release_notes_do_not_claim_decision_readiness(self) -> None:
        self.assertNotRegex(self.report, re.compile(r"decision readiness[^.\n]{0,80}(PASS|READY)", re.I))
        self.assertIn("Confirm readiness is not claimed as PASS.", self.report)

    def test_handoff_allowlist_includes_release_notes_artifacts(self) -> None:
        self.assertIn("data/processed/website_private_preview_handoff_index.csv", HANDOFF_ARTIFACT_FILES)
        self.assertIn("data/processed/website_private_preview_release_summary.csv", HANDOFF_ARTIFACT_FILES)
        self.assertIn("reports/*/website_private_preview_release_notes.md", HANDOFF_ARTIFACT_GLOBS)


if __name__ == "__main__":
    unittest.main()
