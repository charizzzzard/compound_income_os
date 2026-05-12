from __future__ import annotations

import csv
import unittest
from datetime import date
from pathlib import Path

from src.handoff_zip_export import HANDOFF_ARTIFACT_FILES, HANDOFF_ARTIFACT_GLOBS
from website.src.website_private_preview_copy_freeze import (
    COPY_FREEZE_MATRIX_OUTPUT,
    COPY_FREEZE_SUMMARY_OUTPUT,
    action_term_matches,
    private_matches,
    public_claim_matches,
    readiness_claim_matches,
    run_website_private_preview_copy_freeze,
)


ROOT = Path(__file__).resolve().parents[2]


def read_csv(path_value: str) -> list[dict[str, str]]:
    with (ROOT / path_value).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class WebsitePrivatePreviewCopyFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_website_private_preview_copy_freeze(report_date=date(2026, 4, 27), include_dist=False)
        cls.matrix = read_csv(COPY_FREEZE_MATRIX_OUTPUT)
        cls.summary = read_csv(COPY_FREEZE_SUMMARY_OUTPUT)[0]

    def row(self, check_name: str) -> dict[str, str]:
        return next(row for row in self.matrix if row["check_name"] == check_name)

    def test_copy_freeze_artifacts_are_generated(self) -> None:
        self.assertTrue((ROOT / COPY_FREEZE_MATRIX_OUTPUT).is_file())
        self.assertTrue((ROOT / COPY_FREEZE_SUMMARY_OUTPUT).is_file())
        self.assertTrue((ROOT / "reports" / "2026-04-27" / "website_private_preview_copy_freeze_report.md").is_file())

    def test_brand_consistency_passes_for_visible_copy(self) -> None:
        self.assertEqual(self.row("brand_consistency")["status"], "PASS")
        self.assertEqual(self.row("brand_consistency")["violating_matches_count"], "0")

    def test_compounding_filename_is_allowed_as_spec_input(self) -> None:
        self.assertTrue((ROOT / "Compounding_Income_OS_Mockup_Master_Plan_v4.md").exists())
        self.assertEqual(self.row("brand_consistency")["status"], "PASS")

    def test_decision_ready_positive_claims_are_blocked(self) -> None:
        _total, _allowed, violations = readiness_claim_matches("This product is decision ready and ready to invest.")
        self.assertGreater(violations, 0)

    def test_negative_decision_ready_statements_are_allowed(self) -> None:
        _total, _allowed, violations = readiness_claim_matches("This is not decision-ready. Decision readiness is blocked.")
        self.assertEqual(violations, 0)

    def test_public_launch_positive_claims_are_blocked(self) -> None:
        _total, _allowed, violations = public_claim_matches("This website is public launch ready.")
        self.assertGreater(violations, 0)

    def test_negative_public_launch_statements_are_allowed(self) -> None:
        _total, _allowed, violations = public_claim_matches("Public launch remains blocked and does not mean public launch readiness.")
        self.assertEqual(violations, 0)

    def test_advice_action_terms_are_blocked(self) -> None:
        _total, _allowed, violations = action_term_matches("Buy now and deploy capital.")
        self.assertGreater(violations, 0)

    def test_negative_compliance_action_language_is_allowed(self) -> None:
        _total, _allowed, violations = action_term_matches("The product does not execute orders and is not a brokerage or order execution interface.")
        self.assertEqual(violations, 0)

    def test_fake_links_are_blocked_in_current_matrix(self) -> None:
        self.assertEqual(self.row("cta_safety")["status"], "PASS")
        self.assertEqual(self.row("cta_safety")["violating_matches_count"], "0")

    def test_private_raw_and_sec_identity_markers_are_blocked(self) -> None:
        self.assertGreater(private_matches("data/raw/private/personal_sec_identity_map.csv CIK0001"), 0)
        self.assertEqual(self.row("privacy_data_leakage")["status"], "PASS")

    def test_all_six_screenshot_main_routes_are_covered(self) -> None:
        row = self.row("screenshot_coverage")
        self.assertEqual(row["status"], "PASS")
        self.assertEqual(row["matches_count"], "6")

    def test_summary_is_not_blocked_for_current_clean_state(self) -> None:
        self.assertIn(self.summary["copy_freeze_status"], {"PASS", "REVIEW"})
        self.assertNotEqual(self.summary["copy_freeze_status"], "BLOCKED")
        self.assertEqual(self.summary["public_deploy_performed"], "False")
        self.assertEqual(self.summary["private_data_leak_detected"], "False")
        self.assertEqual(self.summary["dummy_claims_detected"], "False")

    def test_handoff_allowlist_contains_copy_freeze_artifacts(self) -> None:
        self.assertIn("data/processed/website_private_preview_copy_freeze_matrix.csv", HANDOFF_ARTIFACT_FILES)
        self.assertIn("data/processed/website_private_preview_copy_freeze_summary.csv", HANDOFF_ARTIFACT_FILES)
        self.assertIn("reports/*/website_private_preview_copy_freeze_report.md", HANDOFF_ARTIFACT_GLOBS)


if __name__ == "__main__":
    unittest.main()
