from __future__ import annotations

import csv
import shutil
import unittest
from pathlib import Path

from src.fundamentals_gap_diagnostics import build_gap_diagnostics_rows, run_fundamentals_gap_diagnostics
from src.fundamentals_master import CORE_KPI_FIELDS, COVERAGE_OUTPUT_FIELDS, PERSONAL_MASTER_FIELDS


def master_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    asset_type: str = "STOCK",
    country: str = "US",
    profile: str = "OTHER",
    data_quality_flag: str = "MISSING_DATA",
    notes: str = "",
    fill_all_kpis: bool = False,
    kpis_present: list[str] | None = None,
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
            "company_type_profile": profile,
            "source_name": "unit_fixture",
            "source_as_of_date": "2026-04-24",
            "fiscal_period": "FY",
            "fiscal_year": "2025",
            "report_date": "2026-04-24",
            "filing_date": "2026-04-24",
            "market_price_date": "2026-04-24",
            "calculation_version": "test",
            "data_quality_flag": data_quality_flag,
            "notes": notes,
            "sleeve": "SINGLE_STOCK",
            "current_price_eur": "100",
            "mandate_fit_score": "80",
        }
    )
    if fill_all_kpis:
        for field in CORE_KPI_FIELDS:
            row[field] = "1"
    for field in (kpis_present or []):
        row[field] = "1"
    return row


def coverage_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    asset_type: str = "STOCK",
    profile: str = "OTHER",
    data_quality_flag: str = "MISSING_DATA",
) -> dict[str, str]:
    row = {field: "" for field in COVERAGE_OUTPUT_FIELDS}
    row.update(
        {
            "holding_name": company_name,
            "ticker": ticker,
            "isin": isin,
            "asset_type": asset_type,
            "company_type_profile": profile,
            "match_status": "PARTIAL",
            "match_method": "ISIN",
            "matched_company_name": company_name,
            "matched_ticker": ticker,
            "matched_isin": isin,
            "match_conflict_flag": "False",
            "data_quality_flag": data_quality_flag,
            "derived_data_quality_flag": "",
            "derived_data_quality_reason": "",
            "core_kpis_present_count": "0",
            "required_kpis_expected": "0",
            "required_kpis_present": "0",
            "required_kpis_missing_count": "0",
            "missing_required_kpis": "",
            "not_applicable_kpis": "",
            "optional_missing_kpis": "",
            "profile_classification_warning_flag": "False",
            "profile_classification_warning_reason": "",
            "needs_research_flag": "True",
            "notes": "",
        }
    )
    return row


def fetch_row(*, ticker: str = "MSFT", isin: str = "US5949181045", company_name: str = "Microsoft Corp", status: str = "FETCHED") -> dict[str, str]:
    return {
        "ticker": ticker,
        "isin": isin,
        "company_name": company_name,
        "cik": "0000789019",
        "fetch_status": status,
        "source_name": "sec_companyfacts",
        "source_reference": "SEC CompanyFacts",
        "source_as_of_date": "2026-04-24",
        "notes": "",
    }


def proposed_update_row(*, ticker: str = "MSFT", isin: str = "US5949181045", company_name: str = "Microsoft Corp", kpi_name: str = "roic") -> dict[str, str]:
    return {
        "ticker": ticker,
        "isin": isin,
        "company_name": company_name,
        "company_type_profile": "OTHER",
        "kpi_name": kpi_name,
        "reported_value": "1",
        "reported_unit": "percent",
        "currency": "USD",
        "source_type": "SNAPSHOT_IMPORT",
        "source_name": "sec_companyfacts",
        "source_reference": "SEC CompanyFacts",
        "source_as_of_date": "2026-04-24",
        "fiscal_year": "2025",
        "verification_status": "UNVERIFIED",
        "data_quality_flag": "REVIEW",
        "proposal_reason": "fixture",
        "notes": "fixture",
    }


class FundamentalsGapDiagnosticsTests(unittest.TestCase):
    def _write_rows(self, path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _single_gap_type(
        self,
        master: dict[str, str],
        coverage: dict[str, str],
        *,
        fetch_rows: list[dict[str, str]] | None = None,
        proposed_rows: list[dict[str, str]] | None = None,
        profile_statuses: dict[tuple[str, str], str] | None = None,
        profile_review_input_status: str = "PROFILE_REVIEW_INPUT_EMPTY",
    ) -> str:
        rows = build_gap_diagnostics_rows(
            [master],
            [coverage],
            fetch_rows or [],
            proposed_rows or [],
            profile_statuses or {},
            profile_review_input_status,
        )
        self.assertEqual(len(rows), 1)
        return rows[0]["quality_gap_type"]

    def test_us_stock_with_sec_identity_and_profile_other_is_profile_review_missing(self) -> None:
        master = master_row(kpis_present=["roic"], notes="sec_identity_apply_cik=0000789019")
        coverage = coverage_row()

        gap_type = self._single_gap_type(
            master,
            coverage,
            fetch_rows=[fetch_row()],
            proposed_rows=[proposed_update_row(kpi_name="roic")],
        )

        self.assertEqual(gap_type, "PROFILE_REVIEW_MISSING")

    def test_us_stock_with_sec_values_but_stale_coverage_is_sec_evidence_available_not_downstream_ready(self) -> None:
        master = master_row(profile="STANDARD", fill_all_kpis=True, notes="profile_reason=operating company")
        coverage = coverage_row(profile="STANDARD", data_quality_flag="MISSING_DATA")

        gap_type = self._single_gap_type(
            master,
            coverage,
            fetch_rows=[fetch_row(status="FETCHED")],
            proposed_rows=[proposed_update_row(kpi_name="roic")],
            profile_statuses={("US5949181045", "MSFT"): "APPROVED"},
            profile_review_input_status="POPULATED",
        )

        self.assertEqual(gap_type, "SEC_EVIDENCE_AVAILABLE_NOT_DOWNSTREAM_READY")

    def test_etf_is_classified_as_non_company_fundamentals(self) -> None:
        master = master_row(ticker="VWCE", isin="IE00BK5BQT80", company_name="ETF Co", asset_type="ETF", country="Global", profile="OTHER")
        coverage = coverage_row(ticker="VWCE", isin="IE00BK5BQT80", company_name="ETF Co", asset_type="ETF", profile="OTHER")

        gap_type = self._single_gap_type(master, coverage)

        self.assertEqual(gap_type, "ETF_OR_NON_COMPANY_FUNDAMENTALS")

    def test_non_us_stock_without_sec_identity_is_outside_current_scope(self) -> None:
        master = master_row(ticker="ASML", isin="NL0010273215", company_name="ASML", country="NL", profile="OTHER")
        coverage = coverage_row(ticker="ASML", isin="NL0010273215", company_name="ASML", profile="OTHER")

        gap_type = self._single_gap_type(master, coverage)

        self.assertEqual(gap_type, "NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE")

    def test_standard_profile_with_some_but_not_all_required_kpis_is_sec_kpi_partial(self) -> None:
        master = master_row(profile="STANDARD", kpis_present=["roic", "revenue_cagr_5y"], notes="profile_reason=operating company")
        coverage = coverage_row(profile="STANDARD")

        gap_type = self._single_gap_type(
            master,
            coverage,
            fetch_rows=[fetch_row()],
            proposed_rows=[proposed_update_row(kpi_name="roic"), proposed_update_row(kpi_name="revenue_cagr_5y")],
            profile_statuses={("US5949181045", "MSFT"): "APPROVED"},
            profile_review_input_status="POPULATED",
        )

        self.assertEqual(gap_type, "SEC_KPI_PARTIAL")

    def test_standard_profile_with_all_required_kpis_is_covered(self) -> None:
        master = master_row(profile="STANDARD", fill_all_kpis=True, data_quality_flag="OK", notes="profile_reason=operating company")
        coverage = coverage_row(profile="STANDARD", data_quality_flag="OK")

        gap_type = self._single_gap_type(
            master,
            coverage,
            profile_statuses={("US5949181045", "MSFT"): "APPROVED"},
            profile_review_input_status="POPULATED",
        )

        self.assertEqual(gap_type, "COVERED")

    def test_sec_kpi_detection_uses_isin_bridge_when_master_ticker_is_canonicalized(self) -> None:
        master = master_row(ticker="GOOGL", isin="US02079K3059", company_name="Alphabet", kpis_present=["eps_cagr_5y"], notes="sec_identity_apply_cik=0001652044")
        coverage = coverage_row(ticker="GOOGL", isin="US02079K3059", company_name="Alphabet")

        rows = build_gap_diagnostics_rows(
            [master],
            [coverage],
            [fetch_row(ticker="US02079K3059", isin="US02079K3059", company_name="Alphabet")],
            [proposed_update_row(ticker="US02079K3059", isin="US02079K3059", company_name="Alphabet", kpi_name="eps_cagr_5y")],
            {},
            "PROFILE_REVIEW_INPUT_EMPTY",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sec_kpi_fields_present_count"], "1")
        self.assertEqual(rows[0]["sec_kpi_fields_present"], "eps_cagr_5y")

    def test_run_gap_diagnostics_accepts_legacy_coverage_header(self) -> None:
        master = master_row(kpis_present=["roic"], notes="sec_identity_apply_cik=0000789019")
        legacy_coverage = {
            "holding_name": "Microsoft Corp",
            "ticker": "MSFT",
            "isin": "US5949181045",
            "asset_type": "STOCK",
            "company_type_profile": "OTHER",
            "match_status": "PARTIAL",
            "match_method": "ISIN",
            "matched_company_name": "Microsoft Corp",
            "matched_ticker": "MSFT",
            "matched_isin": "US5949181045",
            "match_conflict_flag": "False",
            "data_quality_flag": "MISSING_DATA",
            "required_kpis_expected": "0",
            "required_kpis_present": "0",
            "missing_required_kpis": "",
            "not_applicable_kpis": "",
            "optional_missing_kpis": "",
            "profile_classification_warning_flag": "True",
            "profile_classification_warning_reason": "fixture",
            "needs_research_flag": "True",
            "notes": "",
        }
        fetch = fetch_row()
        proposed = proposed_update_row(kpi_name="roic")
        profile_review_header = [
            "ticker",
            "isin",
            "company_name",
            "proposed_company_type_profile",
            "profile_reason",
            "review_status",
            "review_author",
            "review_as_of_date",
            "source_name",
            "source_reference",
            "notes",
        ]

        tmp_path = Path("tests/_tmp_gap_diag_legacy")
        if tmp_path.exists():
            shutil.rmtree(tmp_path, ignore_errors=True)
        tmp_path.mkdir(parents=True, exist_ok=True)
        try:
            master_path = tmp_path / "master.csv"
            coverage_path = tmp_path / "coverage.csv"
            fetch_path = tmp_path / "fetch.csv"
            proposed_path = tmp_path / "proposed.csv"
            profile_review_path = tmp_path / "profile_review.csv"
            diagnostics_output = tmp_path / "diagnostics.csv"
            summary_output = tmp_path / "summary.csv"

            self._write_rows(master_path, PERSONAL_MASTER_FIELDS, [master])
            self._write_rows(coverage_path, list(legacy_coverage.keys()), [legacy_coverage])
            self._write_rows(fetch_path, list(fetch.keys()), [fetch])
            self._write_rows(proposed_path, list(proposed.keys()), [proposed])
            self._write_rows(profile_review_path, profile_review_header, [])

            outputs = run_fundamentals_gap_diagnostics(
                master_input=str(master_path),
                coverage_input=str(coverage_path),
                fetch_registry_input=str(fetch_path),
                proposed_updates_input=str(proposed_path),
                profile_review_input=str(profile_review_path),
                diagnostics_output=str(diagnostics_output),
                summary_output=str(summary_output),
            )

            self.assertEqual(outputs["gap_diagnostics"], diagnostics_output.resolve())
            self.assertEqual(outputs["gap_summary"], summary_output.resolve())
            with diagnostics_output.open("r", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["quality_gap_type"], "PROFILE_REVIEW_MISSING")
        finally:
            shutil.rmtree(tmp_path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
