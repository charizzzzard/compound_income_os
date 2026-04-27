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


class WebsiteManifestoPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = APP.read_text(encoding="utf-8")
        self.config = CONFIG.read_text(encoding="utf-8")
        self.screenshot_script = SCREENSHOT_SCRIPT.read_text(encoding="utf-8")

    def manifesto_section(self) -> str:
        match = re.search(r"function ManifestoPage\(\{ navigate \}\).*?function DashboardPage", self.app, re.S)
        self.assertIsNotNone(match)
        return match.group(0)

    def test_manifesto_route_and_about_alias_exist(self) -> None:
        self.assertIn("['Manifesto', '/manifesto', false]", self.app)
        self.assertIn("window.location.pathname === '/manifesto' || window.location.pathname === '/about'", self.app)
        self.assertIn("route === '/manifesto' ? (", self.app)
        self.assertIn("manifesto: '/manifesto'", self.config)
        self.assertIn("about: '/manifesto'", self.config)

    def test_manifesto_hero_copy_exists(self) -> None:
        section = self.manifesto_section()
        self.assertIn("// OUR PROMISE", section)
        self.assertIn("Built for people who think for the long run.", section)
        self.assertIn("Private preview - research and decision-support only - not investment guidance", section)

    def test_manifesto_principles_are_present(self) -> None:
        for label in (
            "Local-first",
            "Evidence-only",
            "Process over impulse",
            "Decisions, not brokerage actions",
            "Privacy by default",
            "Reproducible by design",
        ):
            self.assertIn(label, self.app)

    def test_built_for_and_not_built_for_sections_are_present(self) -> None:
        section = self.manifesto_section()
        self.assertIn("Built for independent operators.", section)
        self.assertIn("Not built for", section)
        self.assertIn("Dividend-growth investors", self.app)
        self.assertIn("Quality-compounder investors", self.app)
        self.assertIn("brokerage connectivity", self.app)

    def test_access_section_has_three_cards(self) -> None:
        section = self.manifesto_section()
        self.assertIn("Open-source core. Optional help around the workflow.", section)
        self.assertIn("Open-Source Core", self.app)
        self.assertIn("Pro Modules", self.app)
        self.assertIn("Setup Service", self.app)
        self.assertIn("Pricing TBD - Private preview", self.app)
        self.assertIn("Pricing on request - Private preview", self.app)

    def test_public_launch_blockers_are_present(self) -> None:
        section = self.manifesto_section()
        self.assertIn("Still private preview.", section)
        for label in ("Imprint", "Privacy Policy", "Real CTA targets", "Pricing and scope", "Readiness state"):
            self.assertIn(label, self.app)

    def test_manifesto_page_copy_avoids_restricted_action_terms(self) -> None:
        manifesto_copy = self.manifesto_section().upper()
        for term in ("BUY", "SELL", "STRONG_BUY", "STRONG_SELL", "TRADE", "EXECUTE", "ORDER", "RECOMMENDATION", "DEPLOY CAPITAL", "ADD NOW"):
            self.assertNotRegex(manifesto_copy, rf"(?<![A-Z0-9_]){re.escape(term)}(?![A-Z0-9_])")

    def test_no_private_raw_paths_in_website_sources_or_public_demo(self) -> None:
        text = self.app + "\n" + self.config
        for path in PUBLIC_DEMO.glob("*"):
            if path.is_file():
                text += "\n" + path.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"data/raw/private", "private raw path leaked into website/public demo")
        self.assertNotRegex(text, r"personal_sec_identity_map", "private SEC identity map leaked into website/public demo")
        self.assertNotRegex(text, r"\bCIK[0-9A-Z_-]*\b", "private SEC identity marker leaked into website/public demo")

    def test_screenshot_and_handoff_paths_cover_manifesto(self) -> None:
        self.assertIn("/manifesto", self.screenshot_script)
        self.assertIn("06_manifesto_page.png", self.screenshot_script)
        handoff_export = HANDOFF_EXPORT.read_text(encoding="utf-8")
        self.assertIn('"website"', handoff_export)
        self.assertIn("INCLUDED_DIRS", handoff_export)


if __name__ == "__main__":
    unittest.main()
