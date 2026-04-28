from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_sec_companyfacts_snapshot_refresh import run_personal_sec_companyfacts_snapshot_refresh


class PersonalSecCompanyfactsSnapshotRefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_sec_snapshot_refresh_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.approval = self.tmp / "approval.csv"
        self.identity = self.tmp / "identity.csv"
        self.ua = self.tmp / "sec_user_agent.local.txt"
        self.output_root = self.tmp / "private_snapshots"
        self.summary = self.tmp / "processed" / "summary.csv"
        self.report = self.tmp / "reports" / "report.md"
        self.write_inputs()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def write_inputs(self) -> None:
        self.ua.write_text("Test User Agent contact@example.com", encoding="utf-8")
        self.write_csv(
            self.approval,
            ["holding_name", "ticker", "isin", "kpi_field", "formula_role", "candidate_sec_concept", "approval_status"],
            [
                {
                    "holding_name": "Alphabet",
                    "ticker": "GOOGL",
                    "isin": "US02079K3059",
                    "kpi_field": "gross_margin",
                    "formula_role": "gross_profit",
                    "candidate_sec_concept": "GrossProfit",
                    "approval_status": "APPROVED",
                }
            ],
        )
        self.write_csv(
            self.identity,
            ["ticker", "isin", "company_name", "cik", "sec_entity_name", "asset_type", "country", "enabled", "notes"],
            [
                {
                    "ticker": "GOOGL",
                    "isin": "US02079K3059",
                    "company_name": "Alphabet",
                    "cik": "1652044",
                    "sec_entity_name": "Alphabet Inc.",
                    "asset_type": "STOCK",
                    "country": "US",
                    "enabled": "True",
                    "notes": "",
                }
            ],
        )

    def run_refresh(self, fetcher):
        return run_personal_sec_companyfacts_snapshot_refresh(
            approval_applied=self.approval,
            identity_map=self.identity,
            user_agent_file=self.ua,
            output_root=self.output_root,
            summary_output=self.summary,
            report_output=self.report,
            fetcher=fetcher,
            run_id="test_run",
        )

    def test_user_agent_missing_blocks_without_network(self) -> None:
        self.ua.unlink()
        called = False

        def fetcher(_cik: str, _ua: str):
            nonlocal called
            called = True
            return {}

        with self.assertRaisesRegex(RuntimeError, "SEC_USER_AGENT_MISSING"):
            self.run_refresh(fetcher)
        self.assertFalse(called)
        self.assertFalse(self.summary.exists())

    def test_mocked_companyfacts_json_is_saved_privately_with_manifest_sha(self) -> None:
        def fetcher(cik: str, _ua: str):
            return {"cik": cik, "entityName": "Alphabet Inc.", "facts": {"us-gaap": {}}}

        result = self.run_refresh(fetcher)
        manifest = self.read_csv(result.manifest_path)
        self.assertEqual(manifest[0]["fetch_status"], "FETCHED")
        self.assertEqual(manifest[0]["snapshot_exists"], "True")
        self.assertTrue(manifest[0]["snapshot_sha256"])
        self.assertEqual(result.summary["snapshots_written_count"], "1")

    def test_public_report_masks_private_paths(self) -> None:
        def fetcher(cik: str, _ua: str):
            return {"cik": cik, "entityName": "Alphabet Inc.", "facts": {"us-gaap": {}}}

        result = self.run_refresh(fetcher)
        report = result.report_path.read_text(encoding="utf-8")
        self.assertIn("<private_sec_companyfacts_snapshot_root>", report)
        self.assertNotIn(str(self.output_root), report)
        self.assertNotIn("sec_user_agent", report)

    def test_user_agent_is_header_safe_without_printing_value(self) -> None:
        self.ua.write_text("Name with dash \u2013 contact@example.com", encoding="utf-8")
        seen = {}

        def fetcher(cik: str, ua: str):
            seen["ua"] = ua
            return {"cik": cik, "entityName": "Alphabet Inc.", "facts": {"us-gaap": {}}}

        result = self.run_refresh(fetcher)
        self.assertNotIn("\u2013", seen["ua"])
        report = result.report_path.read_text(encoding="utf-8")
        self.assertNotIn("contact@example.com", report)


if __name__ == "__main__":
    unittest.main()
