from __future__ import annotations

import unittest
from pathlib import Path

from src.build_monthly_decision_report import build_monthly_decision_report
from src.build_portfolio_snapshot import build_portfolio_snapshot_report


class ReadmeAndReportTests(unittest.TestCase):
    def test_readme_uses_repo_portable_paths(self) -> None:
        readme = Path("README.md").read_text(encoding="utf-8")
        self.assertNotIn("C:\\Users\\", readme)
        self.assertNotIn("(/C:/Users/", readme)
        self.assertIn("reports/sample/portfolio_snapshot.md", readme)
        self.assertIn("data/raw/real_portfolio_example.csv", readme)
        self.assertIn("--mode real", readme)
        self.assertIn("data/processed/personal_positions_snapshot.csv", readme)
        self.assertIn("Private Rohdaten sollten nicht committed werden.", readme)

    def test_report_builders_generate_german_markdown(self) -> None:
        portfolio_output = Path("tests") / "_tmp_portfolio_snapshot.md"
        decision_output = Path("tests") / "_tmp_decision_report.md"
        try:
            build_portfolio_snapshot_report(
                positions_rows=[
                    {
                        "ticker": "EUR-CASH",
                        "company_name": "Cash",
                        "sleeve": "CASH",
                        "market_value_eur": "1000",
                        "weight_total_assets_pct": "100.0",
                        "asset_type": "CASH",
                        "sector": "Cash",
                    }
                ],
                output_path=str(portfolio_output),
                scores_rows=[],
            )
            build_monthly_decision_report(
                positions_rows=[],
                score_rows=[],
                ranking_rows=[],
                output_path=str(decision_output),
            )
            portfolio_report = portfolio_output.read_text(encoding="utf-8")
            decision_report = decision_output.read_text(encoding="utf-8")
            self.assertIn("# Portfolio-Ueberblick", portfolio_report)
            self.assertIn("## Regelpruefung", portfolio_report)
            self.assertIn("# Monatlicher Entscheidungsbericht", decision_report)
            self.assertIn("## Offene REVIEW-Faelle", decision_report)
        finally:
            if portfolio_output.exists():
                portfolio_output.unlink()
            if decision_output.exists():
                decision_output.unlink()


if __name__ == "__main__":
    unittest.main()
