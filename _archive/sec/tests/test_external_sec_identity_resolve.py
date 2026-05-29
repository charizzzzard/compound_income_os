from __future__ import annotations

import csv
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

from src.common import read_csv_rows
from src.external_sec_identity_resolve import (
    CANDIDATE_FIELDS,
    SUMMARY_FIELDS,
    run_external_sec_identity_resolve,
)
from src.fundamentals_master import PERSONAL_MASTER_FIELDS


def master_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    asset_type: str = "STOCK",
    country: str = "USA",
) -> dict[str, str]:
    row = {field: "" for field in PERSONAL_MASTER_FIELDS}
    row.update(
        {
            "ticker": ticker,
            "isin": isin,
            "company_name": company_name,
            "currency": "USD",
            "sector": "Technology",
            "country": country,
            "asset_type": asset_type,
            "company_type_profile": "STANDARD",
            "source_name": "unit_master_fixture",
            "source_as_of_date": "2026-04-10",
            "fiscal_period": "FY",
            "fiscal_year": "2025",
            "market_price_date": "2026-04-10",
            "calculation_version": "test",
            "data_quality_flag": "MISSING_DATA",
            "notes": "unit fixture",
            "sleeve": "SINGLE_STOCK",
            "current_price_eur": "100",
            "mandate_fit_score": "80",
        }
    )
    return row


class ExternalSecIdentityResolveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_paths: list[Path] = []

    def tearDown(self) -> None:
        for path in reversed(self.temp_paths):
            if path.exists():
                path.unlink()

    def _path(self, name: str) -> Path:
        path = Path("tests") / name
        self.temp_paths.append(path)
        return path

    def _write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _run_resolve(
        self,
        *,
        master_rows: list[dict[str, str]],
        sec_payload: Any,
        prefix: str,
        allow_network: bool = True,
        sec_user_agent: str = "Unit Test unit@example.com",
    ) -> tuple[Path, Path, Path, Path]:
        master_path = self._path(f"_tmp_sec_identity_{prefix}_master.csv")
        candidates_path = self._path(f"_tmp_sec_identity_{prefix}_candidates.csv")
        failures_path = self._path(f"_tmp_sec_identity_{prefix}_failures.csv")
        summary_path = self._path(f"_tmp_sec_identity_{prefix}_summary.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, master_rows)
        run_external_sec_identity_resolve(
            master_input=str(master_path),
            candidates_output=str(candidates_path),
            failures_output=str(failures_path),
            summary_output=str(summary_path),
            as_of_date="2026-04-20",
            allow_network=allow_network,
            sec_user_agent=sec_user_agent,
            fetcher=lambda _user_agent: sec_payload,
        )
        return master_path, candidates_path, failures_path, summary_path

    def test_exact_ticker_match_generates_disabled_candidate_without_private_write(self) -> None:
        private_identity_path = Path("data/raw/private/fundamentals/personal_sec_identity_map.csv")
        existed_before = private_identity_path.exists()
        _master, candidates_path, failures_path, summary_path = self._run_resolve(
            master_rows=[master_row()],
            sec_payload={"0": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"}},
            prefix="success",
        )

        candidate_rows = read_csv_rows(candidates_path)
        self.assertEqual(set(candidate_rows[0]), set(CANDIDATE_FIELDS))
        self.assertEqual(candidate_rows[0]["ticker"], "MSFT")
        self.assertEqual(candidate_rows[0]["cik"], "0000789019")
        self.assertEqual(candidate_rows[0]["sec_entity_name"], "MICROSOFT CORP")
        self.assertEqual(candidate_rows[0]["enabled"], "false")
        self.assertEqual(candidate_rows[0]["match_status"], "CANDIDATE_EXACT")
        self.assertEqual(read_csv_rows(failures_path), [])
        self.assertEqual(set(read_csv_rows(summary_path)[0]), set(SUMMARY_FIELDS))
        self.assertEqual(read_csv_rows(summary_path)[0]["candidate_rows_total"], "1")
        self.assertEqual(private_identity_path.exists(), existed_before)

    def test_network_and_user_agent_are_explicitly_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "--allow-network"):
            self._run_resolve(
                master_rows=[master_row()],
                sec_payload=[],
                prefix="network_guard",
                allow_network=False,
            )
        with self.assertRaisesRegex(ValueError, "--sec-user-agent"):
            self._run_resolve(
                master_rows=[master_row()],
                sec_payload=[],
                prefix="ua_guard",
                sec_user_agent="",
            )

    def test_no_match_ambiguous_and_unsupported_are_visible_failures(self) -> None:
        _master, candidates_path, failures_path, summary_path = self._run_resolve(
            master_rows=[
                master_row(ticker="MSFT", isin="US5949181045", company_name="Microsoft Corp"),
                master_row(ticker="DUP", isin="US0000000001", company_name="Duplicate Corp"),
                master_row(ticker="ETF", isin="US0000000002", company_name="ETF Corp", asset_type="ETF", country="USA"),
                master_row(ticker="MISS", isin="US0000000003", company_name="Missing Corp"),
            ],
            sec_payload=[
                {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
                {"cik_str": 111111, "ticker": "DUP", "title": "DUP ONE"},
                {"cik_str": 222222, "ticker": "DUP", "title": "DUP TWO"},
            ],
            prefix="mixed",
        )

        statuses = {row["ticker"]: row["match_status"] for row in read_csv_rows(candidates_path)}
        self.assertEqual(statuses["MSFT"], "CANDIDATE_EXACT")
        self.assertEqual(statuses["DUP"], "FAILED_AMBIGUOUS")
        self.assertEqual(statuses["ETF"], "SKIPPED_UNSUPPORTED")
        self.assertEqual(statuses["MISS"], "FAILED_NO_SEC_MATCH")
        failure_statuses = {row["ticker"]: row["match_status"] for row in read_csv_rows(failures_path)}
        self.assertEqual(failure_statuses["DUP"], "FAILED_AMBIGUOUS")
        self.assertEqual(failure_statuses["ETF"], "SKIPPED_UNSUPPORTED")
        self.assertEqual(failure_statuses["MISS"], "FAILED_NO_SEC_MATCH")
        summary = read_csv_rows(summary_path)[0]
        self.assertEqual(summary["failure_rows_total"], "3")
        self.assertEqual(summary["unsupported_rows_total"], "1")
        self.assertEqual(summary["ambiguous_rows_total"], "1")

    def test_cli_without_allow_network_fails_before_download(self) -> None:
        master_path = self._path("_tmp_sec_identity_cli_master.csv")
        candidates_path = self._path("_tmp_sec_identity_cli_candidates.csv")
        failures_path = self._path("_tmp_sec_identity_cli_failures.csv")
        summary_path = self._path("_tmp_sec_identity_cli_summary.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.external_sec_identity_resolve",
                "--master-input",
                str(master_path),
                "--candidates-output",
                str(candidates_path),
                "--failures-output",
                str(failures_path),
                "--summary-output",
                str(summary_path),
                "--sec-user-agent",
                "Unit Test unit@example.com",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--allow-network", result.stderr)


if __name__ == "__main__":
    unittest.main()
