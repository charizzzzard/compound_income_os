from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.handoff_zip_export import HANDOFF_ARTIFACT_FILES, HANDOFF_ARTIFACT_GLOBS
from src.website_private_preview_route_matrix import (
    COPY_GUARDRAILS_OUTPUT,
    CTA_MATRIX_OUTPUT,
    QA_SUMMARY_OUTPUT,
    ROUTE_MATRIX_OUTPUT,
    run_website_private_preview_route_matrix,
)


ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_SCRIPT = ROOT / "website" / "compound-income-os-landing" / "scripts" / "capture-screenshots.mjs"
PUBLIC_DEMO = ROOT / "website" / "compound-income-os-landing" / "public" / "demo"


def read_csv(path_value: str) -> list[dict[str, str]]:
    with (ROOT / path_value).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class WebsitePrivatePreviewRouteMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_website_private_preview_route_matrix()
        cls.routes = read_csv(ROUTE_MATRIX_OUTPUT)
        cls.ctas = read_csv(CTA_MATRIX_OUTPUT)
        cls.guardrails = read_csv(COPY_GUARDRAILS_OUTPUT)
        cls.summary = read_csv(QA_SUMMARY_OUTPUT)[0]

    def test_all_expected_routes_are_in_route_matrix(self) -> None:
        routes = {row["route"] for row in self.routes}
        self.assertEqual({"/", "/workflow", "/evidence", "/portfolio", "/dashboard", "/manifesto", "/about"}, routes)

    def test_routes_are_available_and_not_blocked(self) -> None:
        for row in self.routes:
            self.assertNotEqual(row["route_status"], "NOT_AVAILABLE")
            self.assertNotEqual(row["route_status"], "BLOCKED")
            self.assertEqual(row["route_exists"], "True")

    def test_header_nav_and_about_alias_are_consistent(self) -> None:
        about = next(row for row in self.routes if row["route"] == "/about")
        self.assertEqual(about["route_exists"], "True")
        self.assertIn("ABOUT_ALIAS_TO_MANIFESTO", about["reason_codes"])
        for route in ("/workflow", "/evidence", "/portfolio", "/dashboard", "/manifesto"):
            row = next(item for item in self.routes if item["route"] == route)
            self.assertEqual(row["nav_reachable"], "True")

    def test_cta_matrix_has_no_fake_or_invalid_links(self) -> None:
        self.assertTrue(self.ctas)
        for row in self.ctas:
            self.assertNotIn("example.invalid", row["target"])
            self.assertFalse(row["target"].startswith("mailto:"))
            self.assertEqual(row["fake_link_detected"], "False")
            self.assertEqual(row["advice_language_detected"], "False")
            self.assertEqual(row["cta_status"], "PASS")

    def test_imprint_and_privacy_are_pending_not_fake_links(self) -> None:
        pending = {row["cta_label"]: row for row in self.ctas if row["source_route"] == "footer"}
        self.assertEqual(pending["Imprint pending"]["target_type"], "PENDING_DISABLED")
        self.assertEqual(pending["Privacy pending"]["target_type"], "PENDING_DISABLED")
        self.assertEqual(pending["Imprint pending"]["pending_state_ok"], "True")
        self.assertEqual(pending["Privacy pending"]["pending_state_ok"], "True")

    def test_copy_guardrails_have_no_violations(self) -> None:
        for row in self.guardrails:
            self.assertEqual(row["status"], "PASS", row)
            self.assertEqual(row["violating_matches_count"], "0", row)
        self.assertEqual(self.summary["decision_ready_dummy_claims"], "0")
        self.assertEqual(self.summary["public_launch_dummy_claims"], "0")
        self.assertEqual(self.summary["private_path_violations"], "0")
        self.assertEqual(self.summary["advice_term_violations"], "0")

    def test_public_demo_has_no_private_markers(self) -> None:
        text = ""
        for path in PUBLIC_DEMO.glob("*"):
            if path.is_file():
                text += path.read_text(encoding="utf-8") + "\n"
        self.assertNotIn("data/raw/private", text)
        self.assertNotIn("personal_sec_identity_map", text)

    def test_screenshot_matrix_covers_all_main_routes(self) -> None:
        script = SCREENSHOT_SCRIPT.read_text(encoding="utf-8")
        for filename in (
            "01_home_wayfinder.png",
            "02_workflow_page.png",
            "03_evidence_page.png",
            "04_portfolio_page.png",
            "05_dashboard_page.png",
            "06_manifesto_page.png",
        ):
            self.assertIn(filename, script)
        self.assertEqual(self.summary["screenshots_count"], "6")
        self.assertEqual(self.summary["main_routes_screenshot_covered"], "True")

    def test_handoff_allowlist_contains_qa_artifacts(self) -> None:
        for path in (ROUTE_MATRIX_OUTPUT, CTA_MATRIX_OUTPUT, COPY_GUARDRAILS_OUTPUT, QA_SUMMARY_OUTPUT):
            self.assertIn(path, HANDOFF_ARTIFACT_FILES)
        self.assertIn("reports/*/website_private_preview_route_matrix_report.md", HANDOFF_ARTIFACT_GLOBS)


if __name__ == "__main__":
    unittest.main()
