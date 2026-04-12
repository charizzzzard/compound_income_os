from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path

from src.fundamentals_master import (
    CORE_KPI_FIELDS,
    PERSONAL_MASTER_FIELDS,
    build_fundamentals_coverage,
    load_metric_definitions,
    validate_personal_fundamentals_master,
    validate_metric_definitions,
)
from src.common import load_yaml_config
from src.scoring_engine import resolve_fundamentals_cli_format, resolve_fundamentals_cli_path


def position_row(
    ticker: str = "RAW",
    isin: str = "US0000000001",
    company_name: str = "Raw Quality Co",
    asset_type: str = "STOCK",
) -> dict[str, str]:
    return {
        "ticker": ticker,
        "isin": isin,
        "company_name": company_name,
        "asset_type": asset_type,
        "sleeve": "SINGLE_STOCK",
        "market_value_eur": "100",
        "cost_basis_eur": "90",
        "price_eur": "100",
    }


def master_row(
    ticker: str = "RAW",
    isin: str = "US0000000001",
    company_name: str = "Raw Quality Co",
    profile: str = "STANDARD",
    data_quality_flag: str = "OK",
    fill_kpis: bool = True,
) -> dict[str, str]:
    row = {field: "" for field in PERSONAL_MASTER_FIELDS}
    row.update(
        {
            "ticker": ticker,
            "isin": isin,
            "company_name": company_name,
            "currency": "USD",
            "sector": "Technology",
            "country": "USA",
            "asset_type": "STOCK",
            "company_type_profile": profile,
            "source_name": "manual_fixture",
            "source_as_of_date": "2026-01-31",
            "fiscal_period": "FY",
            "fiscal_year": "2025",
            "report_date": "2026-01-31",
            "filing_date": "2026-02-15",
            "market_price_date": "2026-01-31",
            "calculation_version": "test",
            "data_quality_flag": data_quality_flag,
            "notes": "fixture",
            "sleeve": "SINGLE_STOCK",
            "current_price_eur": "100",
            "mandate_fit_score": "80",
        }
    )
    if fill_kpis:
        for field in CORE_KPI_FIELDS:
            row[field] = "1"
        row["interest_coverage"] = "5"
        row["target_fcf_yield_pct"] = "4"
    return row


class FundamentalsMasterTests(unittest.TestCase):
    def test_personal_master_contract_matches_code_template_and_schema(self) -> None:
        schema = load_yaml_config("configs/fundamentals_schema.yaml")
        with Path("data/raw/personal_fundamentals_master_template.csv").open(encoding="utf-8", newline="") as handle:
            template_fields = next(csv.reader(handle))

        self.assertEqual(PERSONAL_MASTER_FIELDS, template_fields)
        self.assertEqual(PERSONAL_MASTER_FIELDS, schema["personal_master_required_columns"])

    def test_metric_definitions_cover_all_core_kpis(self) -> None:
        definitions = load_metric_definitions()

        self.assertEqual(set(CORE_KPI_FIELDS), set(definitions))

    def test_metric_definitions_missing_core_kpi_fails_fast(self) -> None:
        definitions = load_metric_definitions()
        definitions.pop("expected_return_pct")

        with self.assertRaisesRegex(ValueError, "missing KPI definition\\(s\\): expected_return_pct"):
            validate_metric_definitions(definitions)

    def test_isin_match_has_priority_and_is_auditable(self) -> None:
        coverage = build_fundamentals_coverage(
            [position_row(ticker="WRONG", isin="US0000000001")],
            [master_row(ticker="RAW", isin="US0000000001")],
        )

        self.assertEqual(coverage[0]["match_method"], "ISIN")
        self.assertEqual(coverage[0]["matched_ticker"], "RAW")
        self.assertEqual(coverage[0]["match_status"], "COVERED")

    def test_ticker_match_works_when_isin_is_missing(self) -> None:
        coverage = build_fundamentals_coverage(
            [position_row(ticker="RAW", isin="")],
            [master_row(ticker="RAW", isin="")],
        )

        self.assertEqual(coverage[0]["match_method"], "TICKER")
        self.assertEqual(coverage[0]["match_status"], "COVERED")

    def test_company_name_match_is_exact_after_normalization_only(self) -> None:
        exact = build_fundamentals_coverage(
            [position_row(ticker="UNKNOWN", isin="", company_name="Raw Quality Co")],
            [master_row(ticker="RAW", isin="", company_name="Raw Quality Co")],
        )
        partial = build_fundamentals_coverage(
            [position_row(ticker="UNKNOWN", isin="", company_name="Raw Quality Co Registered Shares")],
            [master_row(ticker="RAW", isin="", company_name="Raw Quality Co")],
        )

        self.assertEqual(exact[0]["match_method"], "COMPANY_NAME")
        self.assertEqual(partial[0]["match_status"], "NO_MATCH")

    def test_ambiguous_match_becomes_review_instead_of_guessing(self) -> None:
        coverage = build_fundamentals_coverage(
            [position_row(ticker="DUP", isin="US0000000002", company_name="Duplicate Co")],
            [
                master_row(ticker="DUP", isin="US0000000002", company_name="Duplicate Co A"),
                master_row(ticker="DUP", isin="US0000000003", company_name="Duplicate Co B"),
            ],
        )

        self.assertEqual(coverage[0]["match_status"], "REVIEW")
        self.assertTrue(coverage[0]["match_conflict_flag"])
        self.assertEqual(coverage[0]["needs_research_flag"], True)

    def test_no_match_is_research_gap(self) -> None:
        coverage = build_fundamentals_coverage(
            [position_row(ticker="MISS", isin="US0000000004", company_name="Missing Co")],
            [master_row(ticker="RAW", isin="US0000000001")],
        )

        self.assertEqual(coverage[0]["match_status"], "NO_MATCH")
        self.assertEqual(coverage[0]["match_method"], "NO_MATCH")
        self.assertTrue(coverage[0]["needs_research_flag"])

    def test_other_profile_kpis_are_not_marked_as_required_missing(self) -> None:
        coverage = build_fundamentals_coverage(
            [position_row(ticker="ETF", isin="US0000000005", company_name="ETF Co", asset_type="ETF")],
            [master_row(ticker="ETF", isin="US0000000005", company_name="ETF Co", profile="OTHER", data_quality_flag="MISSING_DATA", fill_kpis=False)],
        )

        self.assertEqual(coverage[0]["match_status"], "PARTIAL")
        self.assertEqual(coverage[0]["missing_required_kpis"], "")
        self.assertIn("roic", coverage[0]["not_applicable_kpis"])

    def test_validation_rejects_missing_required_master_columns(self) -> None:
        invalid = master_row()
        invalid.pop("company_type_profile")

        with self.assertRaisesRegex(ValueError, "missing required columns: company_type_profile"):
            validate_personal_fundamentals_master([invalid], "fixture master")

    def test_personal_master_is_preferred_for_personal_scoring_cli_defaults(self) -> None:
        self.assertEqual(
            resolve_fundamentals_cli_format("auto", "data/raw/personal_fundamentals_master.csv"),
            "personal",
        )
        try:
            resolved_path = resolve_fundamentals_cli_path("data/processed/personal_positions_snapshot.csv", None)
        except ValueError as exc:
            self.assertIn("no sample fundamentals fallback", str(exc))
        else:
            self.assertEqual(resolved_path, "data/raw/personal_fundamentals_master.csv")

    def test_fundamentals_master_cli_writes_coverage_artifacts(self) -> None:
        positions_path = Path("tests") / "_tmp_personal_positions.csv"
        fundamentals_path = Path("tests") / "_tmp_personal_master.csv"
        coverage_path = Path("tests") / "_tmp_personal_coverage.csv"
        enriched_path = Path("tests") / "_tmp_personal_enriched.csv"
        report_path = Path("tests") / "_tmp_personal_coverage.md"
        try:
            with positions_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(position_row().keys()))
                writer.writeheader()
                writer.writerow(position_row())
            with fundamentals_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=PERSONAL_MASTER_FIELDS)
                writer.writeheader()
                writer.writerow(master_row())

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.fundamentals_master",
                    "--positions",
                    str(positions_path),
                    "--fundamentals",
                    str(fundamentals_path),
                    "--coverage-output",
                    str(coverage_path),
                    "--enriched-output",
                    str(enriched_path),
                    "--report-output",
                    str(report_path),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(coverage_path.exists())
            self.assertTrue(enriched_path.exists())
            self.assertTrue(report_path.exists())
            with coverage_path.open(encoding="utf-8") as handle:
                coverage_rows = list(csv.DictReader(handle))
            self.assertEqual(coverage_rows[0]["match_method"], "ISIN")
        finally:
            for path in [positions_path, fundamentals_path, coverage_path, enriched_path, report_path]:
                if path.exists():
                    path.unlink()

    def test_personal_master_cli_end_to_end_smoke_uses_personal_input(self) -> None:
        positions_path = Path("tests") / "_tmp_personal_cli_smoke_positions.csv"
        master_path = Path("tests") / "_tmp_personal_cli_smoke_master.csv"
        scores_path = Path("tests") / "_tmp_personal_cli_smoke_scores.csv"
        audit_path = Path("tests") / "_tmp_personal_cli_smoke_audit.csv"
        coverage_path = Path("tests") / "_tmp_personal_cli_smoke_coverage.csv"
        enriched_path = Path("tests") / "_tmp_personal_cli_smoke_enriched.csv"
        report_path = Path("tests") / "_tmp_personal_cli_smoke_report.md"
        paths = [
            positions_path,
            master_path,
            scores_path,
            audit_path,
            coverage_path,
            enriched_path,
            report_path,
        ]
        smoke_position = position_row(ticker="SMK", isin="US0000000001", company_name="Smoke Compounder AG")
        smoke_position.update({"sector": "Industrials", "country": "USA", "currency": "USD"})

        try:
            with positions_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(smoke_position.keys()))
                writer.writeheader()
                writer.writerow(smoke_position)

            seed_result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.fundamentals_master",
                    "--positions",
                    str(positions_path),
                    "--init-master-output",
                    str(master_path),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )

            self.assertEqual(seed_result.returncode, 0, seed_result.stderr)
            self.assertTrue(master_path.exists())
            with master_path.open(encoding="utf-8") as handle:
                seed_rows = list(csv.DictReader(handle))
            self.assertEqual(len(seed_rows), 1)
            self.assertEqual(seed_rows[0]["ticker"], "SMK")

            enriched_master_row = master_row(
                ticker=seed_rows[0]["ticker"],
                isin=seed_rows[0]["isin"],
                company_name=seed_rows[0]["company_name"],
            )
            enriched_master_row.update(
                {
                    "sector": seed_rows[0]["sector"] or "Industrials",
                    "country": seed_rows[0]["country"] or "USA",
                    "asset_type": seed_rows[0]["asset_type"],
                    "sleeve": seed_rows[0]["sleeve"],
                    "current_price_eur": seed_rows[0]["current_price_eur"] or "100",
                    "source_name": "cli_smoke_personal_master",
                    "notes": "CLI smoke fixture enriched from seed master.",
                }
            )
            with master_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=PERSONAL_MASTER_FIELDS)
                writer.writeheader()
                writer.writerow(enriched_master_row)

            scoring_result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.scoring_engine",
                    "--positions",
                    str(positions_path),
                    "--fundamentals",
                    str(master_path),
                    "--fundamentals-format",
                    "personal",
                    "--output",
                    str(scores_path),
                    "--audit-output",
                    str(audit_path),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )

            self.assertEqual(scoring_result.returncode, 0, scoring_result.stderr)
            self.assertTrue(scores_path.exists())
            self.assertTrue(audit_path.exists())
            with audit_path.open(encoding="utf-8") as handle:
                audit_rows = list(csv.DictReader(handle))
            self.assertEqual(audit_rows[0]["fundamentals_input_format"], "personal")
            self.assertEqual(audit_rows[0]["source_name"], "cli_smoke_personal_master")
            self.assertNotIn("sample", audit_rows[0]["source_name"].lower())

            coverage_result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.fundamentals_master",
                    "--positions",
                    str(positions_path),
                    "--fundamentals",
                    str(master_path),
                    "--scores",
                    str(scores_path),
                    "--coverage-output",
                    str(coverage_path),
                    "--enriched-output",
                    str(enriched_path),
                    "--report-output",
                    str(report_path),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )

            self.assertEqual(coverage_result.returncode, 0, coverage_result.stderr)
            self.assertTrue(coverage_path.exists())
            self.assertTrue(enriched_path.exists())
            self.assertTrue(report_path.exists())

            with coverage_path.open(encoding="utf-8") as handle:
                coverage_rows = list(csv.DictReader(handle))
            self.assertEqual(coverage_rows[0]["match_status"], "COVERED")
            self.assertEqual(coverage_rows[0]["match_method"], "ISIN")
            for field in [
                "match_status",
                "match_method",
                "missing_required_kpis",
                "not_applicable_kpis",
                "needs_research_flag",
            ]:
                self.assertIn(field, coverage_rows[0])
            self.assertEqual(coverage_rows[0]["missing_required_kpis"], "")
            self.assertEqual(coverage_rows[0]["needs_research_flag"], "False")

            with enriched_path.open(encoding="utf-8") as handle:
                enriched_rows = list(csv.DictReader(handle))
            self.assertEqual(len(enriched_rows), 1)
            self.assertEqual(enriched_rows[0]["matched_ticker"], "SMK")
            self.assertEqual(enriched_rows[0]["fundamentals_input_format"], "personal")

            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("# Personal Fundamentals Coverage", report_text)
            self.assertIn("## Summary Counts", report_text)
            self.assertIn("## COVERED", report_text)
            self.assertIn("## Research-Luecken", report_text)
            self.assertIn("Fehlende Fundamentaldaten wurden nicht aufgefuellt und nicht geraten.", report_text)
        finally:
            for path in paths:
                if path.exists():
                    path.unlink()

    def test_scoring_cli_rejects_personal_master_missing_company_type_profile(self) -> None:
        fundamentals_path = Path("tests") / "_tmp_personal_missing_profile.csv"
        output_path = Path("tests") / "_tmp_personal_missing_profile_scores.csv"
        fields = [field for field in PERSONAL_MASTER_FIELDS if field != "company_type_profile"]
        row = master_row()
        row.pop("company_type_profile")
        try:
            with fundamentals_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(row)

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.scoring_engine",
                    "--positions",
                    "data/raw/sample_portfolio.csv",
                    "--fundamentals",
                    str(fundamentals_path),
                    "--fundamentals-format",
                    "personal",
                    "--output",
                    str(output_path),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required personal fundamentals columns: company_type_profile", result.stderr)
            self.assertFalse(output_path.exists())
        finally:
            for path in [fundamentals_path, output_path]:
                if path.exists():
                    path.unlink()

    def test_scoring_cli_rejects_personal_master_invalid_company_type_profile(self) -> None:
        fundamentals_path = Path("tests") / "_tmp_personal_invalid_profile.csv"
        output_path = Path("tests") / "_tmp_personal_invalid_profile_scores.csv"
        try:
            with fundamentals_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=PERSONAL_MASTER_FIELDS)
                writer.writeheader()
                writer.writerow(master_row(ticker="GOOGL", isin="US02079K3059", company_name="Alphabet A", profile="BANK"))

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.scoring_engine",
                    "--positions",
                    "data/raw/sample_portfolio.csv",
                    "--fundamentals",
                    str(fundamentals_path),
                    "--fundamentals-format",
                    "personal",
                    "--output",
                    str(output_path),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid company_type_profile", result.stderr)
            self.assertFalse(output_path.exists())
        finally:
            for path in [fundamentals_path, output_path]:
                if path.exists():
                    path.unlink()

    def test_scoring_cli_accepts_valid_personal_master(self) -> None:
        fundamentals_path = Path("tests") / "_tmp_valid_personal_master.csv"
        output_path = Path("tests") / "_tmp_valid_personal_scores.csv"
        try:
            with fundamentals_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=PERSONAL_MASTER_FIELDS)
                writer.writeheader()
                writer.writerow(master_row(ticker="GOOGL", isin="US02079K3059", company_name="Alphabet A"))

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.scoring_engine",
                    "--positions",
                    "data/raw/sample_portfolio.csv",
                    "--fundamentals",
                    str(fundamentals_path),
                    "--fundamentals-format",
                    "personal",
                    "--output",
                    str(output_path),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output_path.exists())
            with output_path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertTrue(any(row["ticker"] == "GOOGL" and row["fundamentals_input_format"] == "personal" for row in rows))
        finally:
            for path in [fundamentals_path, output_path]:
                if path.exists():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()
