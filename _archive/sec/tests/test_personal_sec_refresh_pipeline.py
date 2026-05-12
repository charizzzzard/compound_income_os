from __future__ import annotations

import csv
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from src.common import read_csv_rows
from src.external_sec_companyfacts_fetch import IDENTITY_MAP_FIELDS
from src.fundamentals_evidence_engine import EVIDENCE_INPUT_FIELDS
from src.fundamentals_master import PERSONAL_MASTER_FIELDS
from src.fundamentals_snapshot_review import SNAPSHOT_REVIEW_INPUT_FIELDS
from src.personal_sec_refresh_pipeline import (
    AUTO_SAFE_KPI_ALLOWLIST,
    prepare_resolved_review_input,
    run_personal_sec_refresh_pipeline,
)


def master_row() -> dict[str, str]:
    row = {field: "" for field in PERSONAL_MASTER_FIELDS}
    row.update(
        {
            "ticker": "MSFT",
            "isin": "US5949181045",
            "company_name": "Microsoft Corp",
            "currency": "USD",
            "sector": "Technology",
            "country": "USA",
            "asset_type": "STOCK",
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


def identity_row(*, ticker: str = "MSFT", isin: str = "US5949181045") -> dict[str, str]:
    return {
        "ticker": ticker,
        "isin": isin,
        "company_name": "Microsoft Corp",
        "cik": "789019",
        "sec_entity_name": "MICROSOFT CORP",
        "asset_type": "STOCK",
        "country": "USA",
        "enabled": "true",
        "notes": "reviewed identity",
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


def companyfacts_fixture() -> dict[str, Any]:
    facts = dict(
        [
            sec_fact("RevenueFromContractWithCustomerExcludingAssessedTax", "USD", {2020: 1000, 2025: 2000}),
            sec_fact("GrossProfit", "USD", {2025: 800}),
            sec_fact("OperatingIncomeLoss", "USD", {2025: 500}),
            sec_fact("EarningsPerShareDiluted", "USD/shares", {2020: 5, 2025: 10}),
            sec_fact("InterestExpenseNonOperating", "USD", {2025: 25}),
            sec_fact("WeightedAverageNumberOfDilutedSharesOutstanding", "shares", {2020: 100, 2025: 90}),
        ]
    )
    return {"cik": 789019, "entityName": "MICROSOFT CORP", "facts": {"us-gaap": facts}}


def staging_row(
    *,
    kpi_name: str,
    reported_value: str = "10",
    ticker: str = "MSFT",
    isin: str = "US5949181045",
) -> dict[str, str]:
    row = {field: "" for field in EVIDENCE_INPUT_FIELDS}
    row.update(
        {
            "ticker": ticker,
            "isin": isin,
            "company_name": "Microsoft Corp",
            "kpi_name": kpi_name,
            "source_type": "SNAPSHOT_IMPORT",
            "source_name": "sec_companyfacts",
            "source_reference": "SEC CompanyFacts CIK0000789019",
            "source_as_of_date": "2026-04-20",
            "fiscal_year": "2025",
            "verification_status": "UNVERIFIED",
            "data_quality_flag": "REVIEW",
            "reported_value": reported_value,
            "reported_unit": "%",
            "currency": "USD",
            "notes": "unit staging",
        }
    )
    return row


class PersonalSecRefreshPipelineTests(unittest.TestCase):
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

    def _pipeline_paths(self, prefix: str) -> dict[str, Path]:
        names = [
            "master",
            "identity",
            "snapshot",
            "sec_registry",
            "sec_failures",
            "sec_summary",
            "normalized",
            "unmatched",
            "staging",
            "snapshot_summary",
            "manual_review",
            "auto_review",
            "resolved_review",
            "review_registry",
            "promoted",
            "review_backlog",
            "review_summary",
            "manual_evidence",
            "composed",
            "compose_conflicts",
            "compose_summary",
            "evidence_registry",
            "evidence_backlog",
            "proposed",
            "evidence_summary",
            "apply_registry",
            "evidence_applied_master",
            "apply_summary",
            "refresh_summary",
        ]
        return {name: self._path(f"_tmp_sec_refresh_{prefix}_{name}.csv") for name in names}

    def _run_pipeline(
        self,
        *,
        prefix: str,
        run_downstream: bool = False,
        watchlist_input: str | None = None,
    ) -> dict[str, Path]:
        paths = self._pipeline_paths(prefix)
        self._write_csv(paths["master"], PERSONAL_MASTER_FIELDS, [master_row()])
        self._write_csv(paths["identity"], IDENTITY_MAP_FIELDS, [identity_row()])
        self._write_csv(paths["manual_review"], SNAPSHOT_REVIEW_INPUT_FIELDS, [])
        self._write_csv(paths["manual_evidence"], EVIDENCE_INPUT_FIELDS, [])
        run_personal_sec_refresh_pipeline(
            master_input=str(paths["master"]),
            identity_map_input=str(paths["identity"]),
            snapshot_output=str(paths["snapshot"]),
            sec_fetch_registry_output=str(paths["sec_registry"]),
            sec_fetch_failures_output=str(paths["sec_failures"]),
            sec_fetch_summary_output=str(paths["sec_summary"]),
            snapshot_normalized_output=str(paths["normalized"]),
            snapshot_unmatched_output=str(paths["unmatched"]),
            snapshot_evidence_staging_output=str(paths["staging"]),
            snapshot_summary_output=str(paths["snapshot_summary"]),
            snapshot_review_registry_output=str(paths["review_registry"]),
            snapshot_evidence_promoted_output=str(paths["promoted"]),
            snapshot_review_backlog_output=str(paths["review_backlog"]),
            snapshot_review_summary_output=str(paths["review_summary"]),
            manual_evidence_input=str(paths["manual_evidence"]),
            evidence_composed_output=str(paths["composed"]),
            evidence_compose_conflicts_output=str(paths["compose_conflicts"]),
            evidence_compose_summary_output=str(paths["compose_summary"]),
            evidence_registry_output=str(paths["evidence_registry"]),
            evidence_backlog_output=str(paths["evidence_backlog"]),
            evidence_proposed_updates_output=str(paths["proposed"]),
            evidence_summary_output=str(paths["evidence_summary"]),
            evidence_apply_registry_output=str(paths["apply_registry"]),
            evidence_applied_master_output=str(paths["evidence_applied_master"]),
            evidence_apply_summary_output=str(paths["apply_summary"]),
            manual_review_input=str(paths["manual_review"]),
            auto_review_output=str(paths["auto_review"]),
            resolved_review_output=str(paths["resolved_review"]),
            refresh_summary_output=str(paths["refresh_summary"]),
            as_of_date="2026-04-20",
            allow_network=True,
            sec_user_agent="Unit Test unit@example.com",
            companyfacts_fetcher=lambda _cik, _ua: companyfacts_fixture(),
            run_downstream=run_downstream,
            downstream_stages=["scoring"] if run_downstream else None,
            watchlist_input=watchlist_input,
        )
        return paths

    def test_refresh_pipeline_runs_existing_steps_in_order_and_applies_evidence(self) -> None:
        paths = self._run_pipeline(prefix="happy")

        step_names = [row["step_name"] for row in read_csv_rows(paths["refresh_summary"])]
        step_order = list(dict.fromkeys(step_names))
        self.assertEqual(
            step_order,
            [
                "sec_companyfacts_fetch",
                "fundamentals_snapshot_ingest",
                "snapshot_review_resolve",
                "fundamentals_snapshot_review",
                "fundamentals_evidence_compose",
                "fundamentals_evidence",
                "fundamentals_evidence_apply",
            ],
        )
        auto_rows = read_csv_rows(paths["auto_review"])
        self.assertTrue(auto_rows)
        self.assertTrue(all(row["kpi_name"] in AUTO_SAFE_KPI_ALLOWLIST for row in auto_rows if row["review_decision"] == "APPROVE"))
        self.assertEqual({row["review_decision"] for row in auto_rows}, {"APPROVE"})
        applied_master = read_csv_rows(paths["evidence_applied_master"])[0]
        self.assertNotEqual(applied_master["revenue_cagr_5y"], "")
        self.assertNotEqual(applied_master["gross_margin"], "")

    def test_refresh_pipeline_does_not_rewrite_raw_evidence_template(self) -> None:
        template_path = Path("data/raw/personal_fundamentals_evidence_template.csv")
        before_bytes = template_path.read_bytes()

        self._run_pipeline(prefix="template_guard")

        self.assertEqual(template_path.read_bytes(), before_bytes)

    def test_refresh_pipeline_requires_network_and_user_agent_before_fetch(self) -> None:
        with self.assertRaisesRegex(ValueError, "--allow-network"):
            run_personal_sec_refresh_pipeline(as_of_date="2026-04-20")
        with self.assertRaisesRegex(ValueError, "--sec-user-agent"):
            run_personal_sec_refresh_pipeline(as_of_date="2026-04-20", allow_network=True)

    def test_auto_safe_promotes_only_allowlist_and_keeps_other_rows_pending(self) -> None:
        staging_path = self._path("_tmp_sec_refresh_policy_staging.csv")
        manual_path = self._path("_tmp_sec_refresh_policy_manual.csv")
        auto_path = self._path("_tmp_sec_refresh_policy_auto.csv")
        resolved_path = self._path("_tmp_sec_refresh_policy_resolved.csv")
        self._write_csv(staging_path, EVIDENCE_INPUT_FIELDS, [staging_row(kpi_name="gross_margin"), staging_row(kpi_name="roic")])
        self._write_csv(manual_path, SNAPSHOT_REVIEW_INPUT_FIELDS, [])

        prepare_resolved_review_input(
            policy="auto_safe",
            staging_input=str(staging_path),
            manual_review_input=str(manual_path),
            enabled_identity_rows=[identity_row()],
            auto_review_output=str(auto_path),
            resolved_review_output=str(resolved_path),
            review_as_of_date="2026-04-20",
        )

        decisions = {row["kpi_name"]: row["review_decision"] for row in read_csv_rows(resolved_path)}
        self.assertEqual(decisions["gross_margin"], "APPROVE")
        self.assertEqual(decisions["roic"], "PENDING")

    def test_manual_review_wins_over_auto_safe_and_raw_review_is_not_overwritten(self) -> None:
        staging_path = self._path("_tmp_sec_refresh_manual_win_staging.csv")
        manual_path = self._path("_tmp_sec_refresh_manual_win_manual.csv")
        auto_path = self._path("_tmp_sec_refresh_manual_win_auto.csv")
        resolved_path = self._path("_tmp_sec_refresh_manual_win_resolved.csv")
        self._write_csv(staging_path, EVIDENCE_INPUT_FIELDS, [staging_row(kpi_name="gross_margin")])
        manual_row = {
            field: staging_row(kpi_name="gross_margin").get(field, "")
            for field in SNAPSHOT_REVIEW_INPUT_FIELDS
        }
        manual_row.update(
            {
                "review_decision": "REJECT",
                "review_reason": "manual rejection wins",
                "review_author": "human",
                "review_as_of_date": "2026-04-20",
                "notes": "do not overwrite",
            }
        )
        self._write_csv(manual_path, SNAPSHOT_REVIEW_INPUT_FIELDS, [manual_row])
        before_bytes = manual_path.read_bytes()

        prepare_resolved_review_input(
            policy="auto_safe",
            staging_input=str(staging_path),
            manual_review_input=str(manual_path),
            enabled_identity_rows=[identity_row()],
            auto_review_output=str(auto_path),
            resolved_review_output=str(resolved_path),
            review_as_of_date="2026-04-20",
        )

        self.assertEqual(manual_path.read_bytes(), before_bytes)
        self.assertEqual(read_csv_rows(auto_path)[0]["review_decision"], "APPROVE")
        self.assertEqual(read_csv_rows(resolved_path)[0]["review_decision"], "REJECT")
        self.assertEqual(read_csv_rows(resolved_path)[0]["review_author"], "human")

    def test_auto_safe_can_bridge_dirty_staging_ticker_that_still_equals_isin(self) -> None:
        staging_path = self._path("_tmp_sec_refresh_dirty_ticker_staging.csv")
        manual_path = self._path("_tmp_sec_refresh_dirty_ticker_manual.csv")
        auto_path = self._path("_tmp_sec_refresh_dirty_ticker_auto.csv")
        resolved_path = self._path("_tmp_sec_refresh_dirty_ticker_resolved.csv")
        self._write_csv(
            staging_path,
            EVIDENCE_INPUT_FIELDS,
            [staging_row(kpi_name="gross_margin", ticker="US5949181045", isin="US5949181045")],
        )
        self._write_csv(manual_path, SNAPSHOT_REVIEW_INPUT_FIELDS, [])

        prepare_resolved_review_input(
            policy="auto_safe",
            staging_input=str(staging_path),
            manual_review_input=str(manual_path),
            enabled_identity_rows=[identity_row(ticker="MSFT", isin="US5949181045")],
            auto_review_output=str(auto_path),
            resolved_review_output=str(resolved_path),
            review_as_of_date="2026-04-20",
        )

        self.assertEqual(read_csv_rows(auto_path)[0]["review_decision"], "APPROVE")
        self.assertEqual(read_csv_rows(resolved_path)[0]["review_decision"], "APPROVE")

    def test_private_identity_map_is_required_and_not_replaced_by_candidates(self) -> None:
        master_path = self._path("_tmp_sec_refresh_missing_identity_master.csv")
        missing_identity_path = self._path("_tmp_sec_refresh_missing_identity_private.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])

        with self.assertRaisesRegex(ValueError, "reviewed private SEC identity map"):
            run_personal_sec_refresh_pipeline(
                master_input=str(master_path),
                identity_map_input=str(missing_identity_path),
                as_of_date="2026-04-20",
                allow_network=True,
                sec_user_agent="Unit Test unit@example.com",
                companyfacts_fetcher=lambda _cik, _ua: companyfacts_fixture(),
            )

    def test_downstream_run_starts_only_after_apply_and_uses_evidence_applied_master(self) -> None:
        captured = {}

        def fake_personal_run(options):
            captured["stages"] = options.stages
            captured["use_evidence_applied_master"] = options.use_evidence_applied_master
            captured["evidence_applied_master"] = options.fundamentals_evidence_applied_master_output
            captured["watchlist_input"] = options.watchlist_input
            return {"run_status": "SUCCESS"}

        with patch("src.personal_sec_refresh_pipeline.run_personal_run_engine", side_effect=fake_personal_run):
            paths = self._run_pipeline(
                prefix="downstream",
                run_downstream=True,
                watchlist_input="data/raw/sample_watchlist.csv",
            )

        self.assertEqual(captured["stages"], ["scoring"])
        self.assertTrue(captured["use_evidence_applied_master"])
        self.assertEqual(captured["evidence_applied_master"], str(paths["evidence_applied_master"]))
        self.assertEqual(captured["watchlist_input"], "data/raw/sample_watchlist.csv")
        self.assertTrue(paths["apply_summary"].exists())


if __name__ == "__main__":
    unittest.main()
