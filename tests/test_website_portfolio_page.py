from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "website" / "compound-income-os-landing" / "src" / "App.jsx"
CONFIG = ROOT / "website" / "compound-income-os-landing" / "src" / "siteConfig.js"
SCREENSHOT_SCRIPT = ROOT / "website" / "compound-income-os-landing" / "scripts" / "capture-screenshots.mjs"
PUBLIC_DEMO = ROOT / "website" / "compound-income-os-landing" / "public" / "demo"
HANDOFF_EXPORT = ROOT / "src" / "handoff_zip_export.py"


class WebsitePortfolioPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = APP.read_text(encoding="utf-8")
        self.config = CONFIG.read_text(encoding="utf-8")
        self.screenshot_script = SCREENSHOT_SCRIPT.read_text(encoding="utf-8")

    def portfolio_section(self) -> str:
        match = re.search(r"function PortfolioPage\(\{ navigate \}\).*?function DashboardPage", self.app, re.S)
        self.assertIsNotNone(match)
        return match.group(0)

    def test_portfolio_route_and_nav_exist(self) -> None:
        self.assertIn("['Portfolio', '/portfolio', false]", self.app)
        self.assertIn("window.location.pathname === '/portfolio'", self.app)
        self.assertIn("route === '/portfolio' ? (", self.app)
        self.assertIn("portfolio: '/portfolio'", self.config)

    def test_portfolio_hero_copy_exists(self) -> None:
        section = self.portfolio_section()
        self.assertIn("// PORTFOLIO MODEL", section)
        self.assertIn("Four sleeves. Clear rules. Long-term focus.", section)
        self.assertIn("Private preview - synthetic demo values - not portfolio allocation guidance", section)

    def test_four_sleeves_are_present(self) -> None:
        for label in ("Core ETF", "Dividend Quality ETF", "Single Stock", "Cash"):
            self.assertIn(label, self.app)

    def test_holdings_sleeves_workspace_is_present(self) -> None:
        section = self.portfolio_section()
        self.assertIn("Holdings & Sleeves Workspace", section)
        self.assertIn("current band", section)
        self.assertIn("rule band", section)
        self.assertIn("review flag", section)

    def test_rule_and_concentration_section_is_present(self) -> None:
        section = self.portfolio_section()
        self.assertIn("Rules before opinions.", section)
        self.assertIn("Max single position", self.app)
        self.assertIn("Max top-10 weight", self.app)
        self.assertIn("Minimum cash reserve", self.app)

    def test_holding_status_model_is_present(self) -> None:
        section = self.portfolio_section()
        self.assertIn("A status model for long-term operators.", section)
        for label in ("Core candidate", "Quality compounder", "Dividend growth", "Too expensive", "Review", "Reject"):
            self.assertIn(label, self.app)

    def test_readiness_box_preserves_blocked_state(self) -> None:
        section = self.portfolio_section()
        self.assertIn("Why this portfolio view is not decision-ready yet.", section)
        self.assertIn("['Decision readiness', 'BLOCKED', 'missing']", self.app)
        self.assertIn("['Valuation inputs', 'missing', 'missing']", self.app)
        self.assertIn("['Dividend / FCF inputs', 'missing', 'missing']", self.app)

    def test_portfolio_page_copy_avoids_restricted_action_terms(self) -> None:
        portfolio_copy = self.portfolio_section().upper()
        for term in ("BUY", "SELL", "STRONG_BUY", "STRONG_SELL", "TRADE", "EXECUTE", "ORDER", "RECOMMENDATION", "DEPLOY CAPITAL", "ADD NOW"):
            self.assertNotRegex(portfolio_copy, rf"(?<![A-Z0-9_]){re.escape(term)}(?![A-Z0-9_])")

    def test_no_private_raw_paths_in_website_sources_or_public_demo(self) -> None:
        text = self.app + "\n" + self.config
        for path in PUBLIC_DEMO.glob("*"):
            if path.is_file():
                text += "\n" + path.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"data/raw/private", "private raw path leaked into website/public demo")
        self.assertNotRegex(text, r"personal_sec_identity_map", "private SEC identity map leaked into website/public demo")
        self.assertNotRegex(text, r"\bCIK[0-9A-Z_-]*\b", "private SEC identity marker leaked into website/public demo")

    def test_screenshot_and_handoff_paths_cover_portfolio(self) -> None:
        self.assertIn("/portfolio", self.screenshot_script)
        self.assertIn("04_portfolio_page.png", self.screenshot_script)
        handoff_export = HANDOFF_EXPORT.read_text(encoding="utf-8")
        self.assertIn('"website"', handoff_export)
        self.assertIn("INCLUDED_DIRS", handoff_export)


if __name__ == "__main__":
    unittest.main()
