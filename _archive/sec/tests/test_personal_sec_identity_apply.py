from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.external_sec_companyfacts_fetch import IDENTITY_MAP_FIELDS
from src.fundamentals_master import PERSONAL_MASTER_FIELDS
from src.personal_run_engine import PersonalRunOptions, run_personal_run_engine
from src.personal_sec_identity_apply import (
    IDENTITY_APPLY_CHANGE_FIELDS,
    IDENTITY_APPLY_SUMMARY_FIELDS,
    run_personal_sec_identity_apply,
)
from src.personal_sec_scope_prepare import REVIEW_FIELDS


def master_row(
    *,
    ticker: str = "US5949181045",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    country: str = "Unknown",
    asset_type: str = "STOCK",
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
            "company_type_profile": "OTHER",
            "source_name": "unit_master_fixture",
            "source_as_of_date": "2026-04-20",
            "market_price_date": "2026-04-20",
            "calculation_version": "test",
            "data_quality_flag": "MISSING_DATA",
            "notes": "identity seed",
            "sleeve": "SINGLE_STOCK",
            "current_price_eur": "100",
            "mandate_fit_score": "80",
            "revenue_cagr_5y": "12.5",
        }
    )
    return row


def review_row(
    *,
    reviewed_ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    cik: str = "0000789019",
    review_status: str = "REVIEWED_APPROVE",
    asset_type: str = "STOCK",
    country: str = "US",
    enabled: str = "true",
) -> dict[str, str]:
    row = {field: "" for field in REVIEW_FIELDS}
    row.update(
        {
            "master_row_number": "2",
            "original_ticker": isin,
            "original_isin": isin,
            "company_name": company_name,
            "original_country": "UNKNOWN",
            "original_asset_type": asset_type,
            "ticker_equals_isin_flag": "true",
            "ticker_looks_like_isin_flag": "true",
            "sec_scope_supported_now_flag": "false",
            "sec_scope_blocker_reason": "COUNTRY_UNKNOWN;TICKER_EQUALS_ISIN;TICKER_LOOKS_LIKE_ISIN",
            "candidate_for_us_stock_review_flag": "true",
            "reviewed_asset_type_scope": asset_type,
            "reviewed_country": country,
            "reviewed_canonical_ticker": reviewed_ticker,
            "reviewed_cik": cik,
            "reviewed_enabled": enabled,
            "reviewed_sec_entity_name": "MICROSOFT CORP",
            "review_status": review_status,
            "review_notes": "reviewed SEC identity",
        }
    )
    return row


def identity_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    cik: str = "0000789019",
    sec_entity_name: str = "MICROSOFT CORP",
    asset_type: str = "STOCK",
    country: str = "US",
    enabled: str = "True",
) -> dict[str, str]:
    return {
        "ticker": ticker,
        "isin": isin,
        "company_name": company_name,
        "cik": cik,
        "sec_entity_name": sec_entity_name,
        "asset_type": asset_type,
        "country": country,
        "enabled": enabled,
        "notes": "reviewed identity map row",
    }


class PersonalSecIdentityApplyTests(unittest.TestCase):
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

    def _raw_positions_row(self) -> list[dict[str, object]]:
        return [
            {
                "portfolio_date": "2026-04-20",
                "source_type": "manual_csv",
                "ticker": "US5949181045",
                "isin": "US5949181045",
                "company_name": "Microsoft Corp",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "sector": "Technology",
                "country": "Unknown",
                "quantity": "2",
                "price_eur": "500",
                "market_value_eur": "1000",
                "cost_basis_eur": "800",
                "currency": "EUR",
                "notes": "unit test position",
            },
            {
                "portfolio_date": "2026-04-20",
                "source_type": "manual_csv",
                "ticker": "EUR-CASH",
                "isin": "",
                "company_name": "Cash",
                "asset_type": "CASH",
                "sleeve": "CASH",
                "sector": "Cash",
                "country": "Eurozone",
                "quantity": "100",
                "price_eur": "1",
                "market_value_eur": "100",
                "cost_basis_eur": "100",
                "currency": "EUR",
                "notes": "unit test cash",
            },
        ]

    def _watchlist_row(self) -> list[dict[str, object]]:
        return [
            {
                "ticker": "MSFT",
                "company_name": "Microsoft Corp",
                "sector": "Technology",
                "country": "USA",
                "asset_type": "STOCK",
                "sleeve": "SINGLE_STOCK",
                "mandate_fit": "90",
                "thesis_summary": "unit watchlist",
                "main_risks": "unit risk",
            }
        ]

    def test_projects_reviewed_us_stock_identity_by_exact_isin(self) -> None:
        master_path = self._path("_tmp_sec_identity_apply_master.csv")
        review_path = self._path("_tmp_sec_identity_apply_review.csv")
        identity_map_path = self._path("_tmp_sec_identity_apply_map.csv")
        changes_path = self._path("_tmp_sec_identity_apply_changes.csv")
        applied_path = self._path("_tmp_sec_identity_apply_output.csv")
        summary_path = self._path("_tmp_sec_identity_apply_summary.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row(ticker="AAPL", country="Unknown")])
        self._write_csv(review_path, REVIEW_FIELDS, [review_row(reviewed_ticker="MSFT")])
        self._write_csv(identity_map_path, IDENTITY_MAP_FIELDS, [identity_row(ticker="MSFT")])

        outputs = run_personal_sec_identity_apply(
            evidence_applied_master_input=str(master_path),
            review_input=str(review_path),
            identity_map_input=str(identity_map_path),
            changes_output=str(changes_path),
            identity_applied_master_output=str(applied_path),
            summary_output=str(summary_path),
        )

        self.assertTrue(outputs["identity_applied_master"].exists())
        applied_rows = read_csv_rows(applied_path)
        change_rows = read_csv_rows(changes_path)
        summary_rows = read_csv_rows(summary_path)
        self.assertEqual(applied_rows[0]["ticker"], "MSFT")
        self.assertEqual(applied_rows[0]["country"], "US")
        self.assertEqual(applied_rows[0]["asset_type"], "STOCK")
        self.assertIn("sec_identity_apply_ticker=MSFT", applied_rows[0]["notes"])
        self.assertEqual(change_rows[0]["projection_status"], "APPLIED")
        self.assertEqual(change_rows[0]["changed_fields"], "ticker;country;notes")
        self.assertEqual(set(change_rows[0]), set(IDENTITY_APPLY_CHANGE_FIELDS))
        self.assertEqual(summary_rows[0]["applied_rows_total"], "1")
        self.assertEqual(summary_rows[0]["ticker_projected_total"], "1")
        self.assertEqual(summary_rows[0]["country_projected_total"], "1")
        self.assertEqual(set(summary_rows[0]), set(IDENTITY_APPLY_SUMMARY_FIELDS))

    def test_non_approved_non_us_and_non_stock_rows_are_not_projected(self) -> None:
        master_path = self._path("_tmp_sec_identity_apply_skip_master.csv")
        review_path = self._path("_tmp_sec_identity_apply_skip_review.csv")
        identity_map_path = self._path("_tmp_sec_identity_apply_skip_map.csv")
        changes_path = self._path("_tmp_sec_identity_apply_skip_changes.csv")
        applied_path = self._path("_tmp_sec_identity_apply_skip_output.csv")
        summary_path = self._path("_tmp_sec_identity_apply_skip_summary.csv")
        original_master = master_row()
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [original_master])
        self._write_csv(
            review_path,
            REVIEW_FIELDS,
            [
                review_row(review_status="REVIEWED_REJECT"),
                review_row(country="NETHERLANDS"),
                review_row(asset_type="ADR"),
            ],
        )
        self._write_csv(identity_map_path, IDENTITY_MAP_FIELDS, [identity_row()])

        run_personal_sec_identity_apply(
            evidence_applied_master_input=str(master_path),
            review_input=str(review_path),
            identity_map_input=str(identity_map_path),
            changes_output=str(changes_path),
            identity_applied_master_output=str(applied_path),
            summary_output=str(summary_path),
        )

        self.assertEqual(read_csv_rows(applied_path)[0]["ticker"], original_master["ticker"])
        self.assertEqual(read_csv_rows(changes_path), [])
        summary_row = read_csv_rows(summary_path)[0]
        self.assertEqual(summary_row["review_rows_total"], "3")
        self.assertEqual(summary_row["exportable_review_rows_total"], "0")
        self.assertEqual(summary_row["applied_rows_total"], "0")

    def test_missing_identity_map_row_is_reported_without_projection(self) -> None:
        master_path = self._path("_tmp_sec_identity_apply_missing_map_master.csv")
        review_path = self._path("_tmp_sec_identity_apply_missing_map_review.csv")
        identity_map_path = self._path("_tmp_sec_identity_apply_missing_map.csv")
        changes_path = self._path("_tmp_sec_identity_apply_missing_map_changes.csv")
        applied_path = self._path("_tmp_sec_identity_apply_missing_map_output.csv")
        summary_path = self._path("_tmp_sec_identity_apply_missing_map_summary.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])
        self._write_csv(review_path, REVIEW_FIELDS, [review_row()])
        self._write_csv(identity_map_path, IDENTITY_MAP_FIELDS, [])

        run_personal_sec_identity_apply(
            evidence_applied_master_input=str(master_path),
            review_input=str(review_path),
            identity_map_input=str(identity_map_path),
            changes_output=str(changes_path),
            identity_applied_master_output=str(applied_path),
            summary_output=str(summary_path),
        )

        self.assertEqual(read_csv_rows(applied_path)[0]["ticker"], "US5949181045")
        self.assertEqual(read_csv_rows(changes_path)[0]["projection_status"], "SKIPPED_NO_IDENTITY_MAP")
        self.assertEqual(read_csv_rows(summary_path)[0]["skipped_no_identity_map_total"], "1")

    def test_conflicting_review_and_identity_map_fail_fast(self) -> None:
        master_path = self._path("_tmp_sec_identity_apply_conflict_master.csv")
        review_path = self._path("_tmp_sec_identity_apply_conflict_review.csv")
        identity_map_path = self._path("_tmp_sec_identity_apply_conflict_map.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])
        self._write_csv(review_path, REVIEW_FIELDS, [review_row(reviewed_ticker="MSFT")])
        self._write_csv(identity_map_path, IDENTITY_MAP_FIELDS, [identity_row(ticker="AAPL")])

        with self.assertRaisesRegex(ValueError, "disagree"):
            run_personal_sec_identity_apply(
                evidence_applied_master_input=str(master_path),
                review_input=str(review_path),
                identity_map_input=str(identity_map_path),
                changes_output=str(self._path("_tmp_sec_identity_apply_conflict_changes.csv")),
                identity_applied_master_output=str(self._path("_tmp_sec_identity_apply_conflict_output.csv")),
                summary_output=str(self._path("_tmp_sec_identity_apply_conflict_summary.csv")),
            )

    def test_input_files_are_not_mutated(self) -> None:
        master_path = self._path("_tmp_sec_identity_apply_immutable_master.csv")
        review_path = self._path("_tmp_sec_identity_apply_immutable_review.csv")
        identity_map_path = self._path("_tmp_sec_identity_apply_immutable_map.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])
        self._write_csv(review_path, REVIEW_FIELDS, [review_row()])
        self._write_csv(identity_map_path, IDENTITY_MAP_FIELDS, [identity_row()])
        before_master = master_path.read_bytes()
        before_review = review_path.read_bytes()
        before_identity = identity_map_path.read_bytes()

        run_personal_sec_identity_apply(
            evidence_applied_master_input=str(master_path),
            review_input=str(review_path),
            identity_map_input=str(identity_map_path),
            changes_output=str(self._path("_tmp_sec_identity_apply_immutable_changes.csv")),
            identity_applied_master_output=str(self._path("_tmp_sec_identity_apply_immutable_output.csv")),
            summary_output=str(self._path("_tmp_sec_identity_apply_immutable_summary.csv")),
        )

        self.assertEqual(master_path.read_bytes(), before_master)
        self.assertEqual(review_path.read_bytes(), before_review)
        self.assertEqual(identity_map_path.read_bytes(), before_identity)

    def test_downstream_can_use_identity_applied_master_explicitly(self) -> None:
        master_path = self._path("_tmp_sec_identity_apply_downstream_master.csv")
        review_path = self._path("_tmp_sec_identity_apply_downstream_review.csv")
        identity_map_path = self._path("_tmp_sec_identity_apply_downstream_map.csv")
        identity_applied_path = self._path("_tmp_sec_identity_apply_downstream_output.csv")
        changes_path = self._path("_tmp_sec_identity_apply_downstream_changes.csv")
        summary_path = self._path("_tmp_sec_identity_apply_downstream_summary.csv")
        raw_positions_path = self._path("_tmp_sec_identity_apply_positions.csv")
        positions_output = self._path("_tmp_sec_identity_apply_positions_snapshot.csv")
        watchlist_input = self._path("_tmp_sec_identity_apply_watchlist.csv")
        scores_output = self._path("_tmp_sec_identity_apply_scores.csv")
        score_audit_output = self._path("_tmp_sec_identity_apply_audit.csv")
        coverage_output = self._path("_tmp_sec_identity_apply_coverage.csv")
        enriched_output = self._path("_tmp_sec_identity_apply_enriched.csv")
        research_output = self._path("_tmp_sec_identity_apply_research.csv")
        coverage_report = self._path("_tmp_sec_identity_apply_coverage.md")
        manifest_output = self._path("_tmp_sec_identity_apply_manifest.json")
        artifacts_output = self._path("_tmp_sec_identity_apply_artifacts.csv")
        used_inputs_output = self._path("_tmp_sec_identity_apply_used_inputs.csv")
        report_output = self._path("_tmp_sec_identity_apply_report.md")

        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])
        self._write_csv(review_path, REVIEW_FIELDS, [review_row()])
        self._write_csv(identity_map_path, IDENTITY_MAP_FIELDS, [identity_row()])
        self._write_csv(
            raw_positions_path,
            [
                "portfolio_date",
                "source_type",
                "ticker",
                "isin",
                "company_name",
                "asset_type",
                "sleeve",
                "sector",
                "country",
                "quantity",
                "price_eur",
                "market_value_eur",
                "cost_basis_eur",
                "currency",
                "notes",
            ],
            self._raw_positions_row(),
        )
        self._write_csv(
            watchlist_input,
            ["ticker", "company_name", "sector", "country", "asset_type", "sleeve", "mandate_fit", "thesis_summary", "main_risks"],
            self._watchlist_row(),
        )

        run_personal_sec_identity_apply(
            evidence_applied_master_input=str(master_path),
            review_input=str(review_path),
            identity_map_input=str(identity_map_path),
            changes_output=str(changes_path),
            identity_applied_master_output=str(identity_applied_path),
            summary_output=str(summary_path),
        )

        manifest = run_personal_run_engine(
            PersonalRunOptions(
                stages=["import", "scoring", "coverage"],
                positions_raw_input=str(raw_positions_path),
                positions_output=str(positions_output),
                import_mode="real",
                source_name="sec_identity_apply_test",
                fundamentals_master=str(master_path),
                fundamentals_evidence_applied_master_output=str(identity_applied_path),
                use_evidence_applied_master=True,
                watchlist_input=str(watchlist_input),
                scores_output=str(scores_output),
                score_audit_output=str(score_audit_output),
                coverage_output=str(coverage_output),
                fundamentals_enriched_output=str(enriched_output),
                research_priority_output=str(research_output),
                fundamentals_coverage_report_output=str(coverage_report),
                manifest_output=str(manifest_output),
                artifacts_output=str(artifacts_output),
                used_inputs_output=str(used_inputs_output),
                report_output=str(report_output),
            ).normalized()
        )

        score_rows = read_csv_rows(scores_output)
        coverage_rows = read_csv_rows(coverage_output)
        used_inputs_rows = read_csv_rows(used_inputs_output)
        manifest_on_disk = json.loads(manifest_output.read_text(encoding="utf-8"))
        self.assertEqual(manifest["run_status"], "SUCCESS")
        self.assertEqual(manifest_on_disk["run_status"], "SUCCESS")
        self.assertEqual(score_rows[0]["ticker"], "MSFT")
        self.assertEqual(score_rows[0]["country"], "US")
        self.assertEqual(coverage_rows[0]["matched_ticker"], "MSFT")
        scoring_master_input = next(
            row for row in used_inputs_rows if row["stage_name"] == "scoring" and row["input_role"] == "fundamentals_master"
        )
        self.assertEqual(scoring_master_input["input_path"], str(identity_applied_path))
        self.assertIn("fundamentals_source_mode=EVIDENCE_APPLIED", scoring_master_input["notes"])


if __name__ == "__main__":
    unittest.main()
