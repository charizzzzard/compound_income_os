from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "website" / "compound-income-os-landing" / "src" / "App.jsx"
CONFIG = ROOT / "website" / "compound-income-os-landing" / "src" / "siteConfig.js"
PUBLIC_DEMO = ROOT / "website" / "compound-income-os-landing" / "public" / "demo"


class WebsiteDashboardPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = APP.read_text(encoding="utf-8")
        self.config = CONFIG.read_text(encoding="utf-8")

    def test_dashboard_route_and_nav_exist(self) -> None:
        self.assertIn("['Dashboard', '/dashboard', false]", self.app)
        self.assertIn("window.location.pathname === '/dashboard'", self.app)
        self.assertRegex(self.app, r"route === '/dashboard'\s+\?\s+\(\s+<DashboardPage")
        self.assertIn("dashboard: '/dashboard'", self.config)

    def test_dashboard_hero_copy_exists(self) -> None:
        self.assertIn("// THE LOCAL DASHBOARD", self.app)
        self.assertIn("One local dashboard. Five KPI groups.", self.app)
        self.assertIn("decision readiness currently blocked", self.app)

    def test_five_kpi_groups_are_present(self) -> None:
        for label in (
            "Portfolio / Structure",
            "Score / Fundamentals",
            "Benchmark / Performance",
            "Cost / Tax",
            "Data Quality / Methodology",
        ):
            self.assertIn(label, self.app)

    def test_readiness_strip_preserves_blocked_review_statuses(self) -> None:
        self.assertIn("['Decision', 'BLOCKED', 'missing']", self.app)
        self.assertIn("['Dashboard', 'REVIEW', 'review']", self.app)
        self.assertIn("['Handoff', 'REVIEW', 'partial']", self.app)

    def test_scenario_guardrail_copy_exists(self) -> None:
        self.assertIn("Illustrative scenario - not a forecast", self.app)
        self.assertIn("Requires explicit local benchmark archive - not a prediction", self.app)
        self.assertIn("Requires explicit cost/tax ledger evidence", self.app)

    def test_no_private_raw_paths_in_website_sources_or_public_demo(self) -> None:
        text = self.app + "\n" + self.config
        for path in PUBLIC_DEMO.glob("*"):
            if path.is_file():
                text += "\n" + path.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"data/raw/private", "private raw path leaked into website/public demo")
        self.assertNotRegex(text, r"personal_sec_identity_map", "private SEC identity map leaked into website/public demo")
        self.assertNotRegex(text, r"\bCIK[0-9A-Z_-]*\b", "private SEC identity marker leaked into website/public demo")

    def test_dashboard_page_copy_avoids_restricted_action_terms(self) -> None:
        match = re.search(r"function DashboardPage\(\).*?function SloganBar", self.app, re.S)
        self.assertIsNotNone(match)
        dashboard_copy = match.group(0).upper()
        for term in ("BUY", "SELL", "STRONG_BUY", "STRONG_SELL", "TRADE", "EXECUTE", "ORDER", "DEPLOY CAPITAL", "ADD NOW"):
            self.assertNotRegex(dashboard_copy, rf"(?<![A-Z0-9_]){re.escape(term)}(?![A-Z0-9_])")


if __name__ == "__main__":
    unittest.main()
