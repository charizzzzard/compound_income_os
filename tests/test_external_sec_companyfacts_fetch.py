from __future__ import annotations

import csv
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

from src.common import read_csv_rows
from src.external_sec_companyfacts_fetch import (
    FAILURES_FIELDS,
    IDENTITY_MAP_FIELDS,
    REGISTRY_FIELDS,
    SUMMARY_FIELDS,
    run_external_sec_companyfacts_fetch,
    write_sec_identity_map_template,
)
from src.fundamentals_master import PERSONAL_MASTER_FIELDS
from src.fundamentals_snapshot_ingestion import SNAPSHOT_INPUT_FIELDS


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


def identity_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    cik: str = "789019",
    asset_type: str = "STOCK",
    country: str = "USA",
    enabled: str = "true",
) -> dict[str, str]:
    return {
        "ticker": ticker,
        "isin": isin,
        "company_name": company_name,
        "cik": cik,
        "sec_entity_name": company_name,
        "asset_type": asset_type,
        "country": country,
        "enabled": enabled,
        "notes": "unit identity",
    }


def sec_fact(concept: str, unit: str, values: dict[int, float]) -> tuple[str, dict[str, Any]]:
    return (
        concept,
        {
            "units": {
                unit: [
                    {
                        "fy": fiscal_year,
                        "fp": "FY",
                        "form": "10-K",
                        "filed": f"{fiscal_year + 1}-02-01",
                        "end": f"{fiscal_year}-12-31",
                        "accn": f"{fiscal_year}-fixture",
                        "val": value,
                    }
                    for fiscal_year, value in sorted(values.items())
                ]
            }
        },
    )


def companyfacts_fixture(*, include_optional: bool = True) -> dict[str, Any]:
    facts = dict(
        [
            sec_fact("RevenueFromContractWithCustomerExcludingAssessedTax", "USD", {2020: 1000, 2025: 2000}),
            sec_fact("GrossProfit", "USD", {2025: 800}),
            sec_fact("OperatingIncomeLoss", "USD", {2025: 500}),
        ]
    )
    if include_optional:
        facts.update(
            dict(
                [
                    sec_fact("EarningsPerShareDiluted", "USD/shares", {2020: 5, 2025: 10}),
                    sec_fact("InterestExpenseNonOperating", "USD", {2025: 25}),
                    sec_fact("WeightedAverageNumberOfDilutedSharesOutstanding", "shares", {2020: 100, 2025: 90}),
                ]
            )
        )
    return {"cik": 789019, "entityName": "MICROSOFT CORP", "facts": {"us-gaap": facts}}


class ExternalSecCompanyfactsFetchTests(unittest.TestCase):
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

    def _run_fetch(
        self,
        *,
        master_rows: list[dict[str, str]],
        identity_rows: list[dict[str, str]],
        fetcher,
        prefix: str,
        allow_network: bool = True,
        sec_user_agent: str = "Unit Test unit@example.com",
    ) -> tuple[Path, Path, Path, Path, Path, Path]:
        master_path = self._path(f"_tmp_sec_{prefix}_master.csv")
        identity_path = self._path(f"_tmp_sec_{prefix}_identity.csv")
        snapshot_path = self._path(f"_tmp_sec_{prefix}_snapshot.csv")
        registry_path = self._path(f"_tmp_sec_{prefix}_registry.csv")
        failures_path = self._path(f"_tmp_sec_{prefix}_failures.csv")
        summary_path = self._path(f"_tmp_sec_{prefix}_summary.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, master_rows)
        self._write_csv(identity_path, IDENTITY_MAP_FIELDS, identity_rows)
        run_external_sec_companyfacts_fetch(
            master_input=str(master_path),
            identity_map_input=str(identity_path),
            output=str(snapshot_path),
            registry_output=str(registry_path),
            failures_output=str(failures_path),
            summary_output=str(summary_path),
            as_of_date="2026-04-20",
            allow_network=allow_network,
            sec_user_agent=sec_user_agent,
            fetcher=fetcher,
        )
        return master_path, identity_path, snapshot_path, registry_path, failures_path, summary_path

    def test_successful_sec_fetch_writes_snapshot_registry_and_summary(self) -> None:
        calls: list[tuple[str, str]] = []

        def fetcher(cik: str, user_agent: str) -> dict[str, Any]:
            calls.append((cik, user_agent))
            return companyfacts_fixture()

        _master, _identity, snapshot_path, registry_path, failures_path, summary_path = self._run_fetch(
            master_rows=[master_row()],
            identity_rows=[identity_row()],
            fetcher=fetcher,
            prefix="success",
        )

        snapshot_rows = read_csv_rows(snapshot_path)
        registry_rows = read_csv_rows(registry_path)
        failure_rows = read_csv_rows(failures_path)
        summary_rows = read_csv_rows(summary_path)
        self.assertEqual(calls, [("0000789019", "Unit Test unit@example.com")])
        self.assertEqual(set(snapshot_rows[0]), set(SNAPSHOT_INPUT_FIELDS))
        self.assertEqual(snapshot_rows[0]["ticker"], "MSFT")
        self.assertEqual(snapshot_rows[0]["isin"], "US5949181045")
        self.assertEqual(snapshot_rows[0]["source_name"], "sec_companyfacts")
        self.assertEqual(snapshot_rows[0]["source_as_of_date"], "2026-04-20")
        self.assertEqual(snapshot_rows[0]["fiscal_year"], "2025")
        self.assertEqual(snapshot_rows[0]["currency"], "USD")
        self.assertEqual(snapshot_rows[0]["gross_margin"], "40")
        self.assertEqual(snapshot_rows[0]["operating_margin"], "25")
        self.assertEqual(snapshot_rows[0]["interest_coverage"], "20")
        self.assertNotEqual(snapshot_rows[0]["revenue_cagr_5y"], "")
        self.assertNotEqual(snapshot_rows[0]["eps_cagr_5y"], "")
        self.assertNotEqual(snapshot_rows[0]["share_count_cagr_5y"], "")
        self.assertEqual(registry_rows[0]["fetch_status"], "FETCHED")
        self.assertEqual(failure_rows, [])
        self.assertEqual(set(registry_rows[0]), set(REGISTRY_FIELDS))
        self.assertEqual(set(summary_rows[0]), set(SUMMARY_FIELDS))
        self.assertEqual(summary_rows[0]["snapshot_rows_written"], "1")

    def test_network_and_user_agent_are_explicitly_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "--allow-network"):
            self._run_fetch(
                master_rows=[master_row()],
                identity_rows=[identity_row()],
                fetcher=lambda _cik, _ua: companyfacts_fixture(),
                prefix="network_guard",
                allow_network=False,
            )
        with self.assertRaisesRegex(ValueError, "--sec-user-agent"):
            self._run_fetch(
                master_rows=[master_row()],
                identity_rows=[identity_row()],
                fetcher=lambda _cik, _ua: companyfacts_fixture(),
                prefix="ua_guard",
                sec_user_agent="",
            )

    def test_identity_map_must_match_master_without_fuzzy_company_name(self) -> None:
        def fetcher(_cik: str, _user_agent: str) -> dict[str, Any]:
            raise AssertionError("fetcher should not be called for identity mismatch")

        _master, _identity, snapshot_path, registry_path, failures_path, summary_path = self._run_fetch(
            master_rows=[master_row()],
            identity_rows=[identity_row(ticker="AAPL", isin="US5949181045", company_name="Microsoft Corp")],
            fetcher=fetcher,
            prefix="identity_mismatch",
        )

        self.assertEqual(read_csv_rows(snapshot_path), [])
        self.assertEqual(read_csv_rows(registry_path)[0]["fetch_status"], "SKIPPED_IDENTITY_MISSING")
        self.assertEqual(read_csv_rows(failures_path)[0]["failure_reason"], "SKIPPED_IDENTITY_MISSING")
        self.assertEqual(read_csv_rows(summary_path)[0]["failure_rows_total"], "1")

    def test_unsupported_non_us_or_non_stock_rows_are_visible_without_fetch(self) -> None:
        def fetcher(_cik: str, _user_agent: str) -> dict[str, Any]:
            raise AssertionError("fetcher should not be called for unsupported rows")

        _master, _identity, snapshot_path, registry_path, failures_path, summary_path = self._run_fetch(
            master_rows=[master_row(asset_type="ETF", country="Global")],
            identity_rows=[identity_row(asset_type="ETF", country="Global")],
            fetcher=fetcher,
            prefix="unsupported",
        )

        self.assertEqual(read_csv_rows(snapshot_path), [])
        self.assertEqual(read_csv_rows(registry_path)[0]["fetch_status"], "SKIPPED_UNSUPPORTED")
        self.assertEqual(read_csv_rows(failures_path)[0]["failure_reason"], "SKIPPED_UNSUPPORTED")
        self.assertEqual(read_csv_rows(summary_path)[0]["unsupported_rows_total"], "1")

    def test_missing_sec_concepts_leave_supported_snapshot_fields_blank(self) -> None:
        _master, _identity, snapshot_path, _registry, _failures, _summary = self._run_fetch(
            master_rows=[master_row()],
            identity_rows=[identity_row()],
            fetcher=lambda _cik, _ua: companyfacts_fixture(include_optional=False),
            prefix="missing_concepts",
        )

        snapshot_row = read_csv_rows(snapshot_path)[0]
        self.assertEqual(snapshot_row["eps_cagr_5y"], "")
        self.assertEqual(snapshot_row["interest_coverage"], "")
        self.assertEqual(snapshot_row["share_count_cagr_5y"], "")
        self.assertEqual(snapshot_row["fcf_margin"], "")
        self.assertEqual(snapshot_row["roic"], "")

    def test_outputs_are_deterministically_ordered_and_inputs_are_not_mutated(self) -> None:
        master_rows = [
            master_row(ticker="MSFT", isin="US5949181045", company_name="Microsoft Corp"),
            master_row(ticker="AAPL", isin="US0378331005", company_name="Apple Inc"),
        ]
        identity_rows = [
            identity_row(ticker="MSFT", isin="US5949181045", company_name="Microsoft Corp", cik="789019"),
            identity_row(ticker="AAPL", isin="US0378331005", company_name="Apple Inc", cik="320193"),
        ]

        master_path, identity_path, snapshot_path, registry_path, _failures, _summary = self._run_fetch(
            master_rows=master_rows,
            identity_rows=list(reversed(identity_rows)),
            fetcher=lambda _cik, _ua: companyfacts_fixture(),
            prefix="ordering",
        )

        self.assertEqual([row["ticker"] for row in read_csv_rows(snapshot_path)], ["AAPL", "MSFT"])
        self.assertEqual([row["ticker"] for row in read_csv_rows(registry_path)], ["AAPL", "MSFT"])
        self.assertEqual(read_csv_rows(master_path), master_rows)
        self.assertEqual(read_csv_rows(identity_path), list(reversed(identity_rows)))

    def test_identity_map_duplicates_are_idempotent_but_conflicts_fail_fast(self) -> None:
        calls: list[str] = []

        def fetcher(cik: str, _user_agent: str) -> dict[str, Any]:
            calls.append(cik)
            return companyfacts_fixture()

        _master, _identity, snapshot_path, registry_path, _failures, summary_path = self._run_fetch(
            master_rows=[master_row()],
            identity_rows=[identity_row(), identity_row()],
            fetcher=fetcher,
            prefix="dedupe",
        )

        self.assertEqual(calls, ["0000789019"])
        self.assertEqual(len(read_csv_rows(snapshot_path)), 1)
        self.assertEqual(len(read_csv_rows(registry_path)), 1)
        self.assertEqual(read_csv_rows(summary_path)[0]["identity_rows_total"], "1")

        with self.assertRaisesRegex(ValueError, "conflicting duplicate identity row"):
            self._run_fetch(
                master_rows=[master_row()],
                identity_rows=[identity_row(), identity_row(enabled="false")],
                fetcher=fetcher,
                prefix="duplicate_conflict",
            )

    def test_template_writer_matches_identity_map_contract(self) -> None:
        template_path = self._path("_tmp_sec_identity_template.csv")

        write_sec_identity_map_template(str(template_path))

        self.assertEqual(read_csv_rows(template_path), [])
        with template_path.open("r", encoding="utf-8") as handle:
            self.assertEqual(handle.readline().strip().split(","), IDENTITY_MAP_FIELDS)

    def test_cli_template_only_smoke_writes_identity_map_template(self) -> None:
        template_path = self._path("_tmp_sec_cli_identity_template.csv")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.external_sec_companyfacts_fetch",
                "--template-only",
                "--identity-map-template-output",
                str(template_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(read_csv_rows(template_path), [])
        with template_path.open("r", encoding="utf-8") as handle:
            self.assertEqual(handle.readline().strip().split(","), IDENTITY_MAP_FIELDS)


if __name__ == "__main__":
    unittest.main()
