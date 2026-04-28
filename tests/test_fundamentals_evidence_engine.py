from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.fundamentals_evidence_engine import (
    EVIDENCE_INPUT_FIELDS,
    PROPOSED_UPDATES_FIELDS,
    RESEARCH_BACKLOG_FIELDS,
    build_evidence_registry,
    required_kpis_for_profile,
    run_fundamentals_evidence_engine,
    write_evidence_template,
)
from src.fundamentals_master import CORE_KPI_FIELDS, PERSONAL_MASTER_FIELDS, load_metric_definitions


def master_row(
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    profile: str = "STANDARD",
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
            "source_name": "manual_master_fixture",
            "source_as_of_date": "2026-03-31",
            "fiscal_period": "FY",
            "fiscal_year": "2025",
            "report_date": "2026-03-31",
            "filing_date": "2026-04-01",
            "market_price_date": "2026-03-31",
            "calculation_version": "test",
            "data_quality_flag": "REVIEW",
            "notes": "unit fixture",
            "sleeve": "SINGLE_STOCK",
            "current_price_eur": "100",
            "mandate_fit_score": "80",
        }
    )
    for kpi_name in CORE_KPI_FIELDS:
        row[kpi_name] = ""
    return row


def evidence_row(
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    kpi_name: str = "roic",
    verification_status: str = "VERIFIED",
    data_quality_flag: str = "OK",
    reported_value: str = "25.0",
    notes: str = "fixture evidence",
) -> dict[str, str]:
    row = {field: "" for field in EVIDENCE_INPUT_FIELDS}
    row.update(
        {
            "ticker": ticker,
            "isin": isin,
            "company_name": company_name,
            "kpi_name": kpi_name,
            "source_type": "annual_report",
            "source_name": "annual_report_2025",
            "source_reference": "FY2025 annual report",
            "source_as_of_date": "2026-03-31",
            "fiscal_year": "2025",
            "verification_status": verification_status,
            "data_quality_flag": data_quality_flag,
            "notes": notes,
            "source_section": "financial statements",
            "source_page": "42",
            "reported_value": reported_value,
            "reported_unit": "percent",
            "currency": "USD",
        }
    )
    return row


class FundamentalsEvidenceEngineTests(unittest.TestCase):
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

    def _run_engine(
        self,
        master_rows: list[dict[str, str]],
        evidence_rows: list[dict[str, str]],
        prefix: str,
    ) -> tuple[Path, Path, Path, Path, Path, Path, Path]:
        master_path = self._path(f"_tmp_evidence_{prefix}_master.csv")
        evidence_path = self._path(f"_tmp_evidence_{prefix}_input.csv")
        registry_path = self._path(f"_tmp_evidence_{prefix}_registry.csv")
        backlog_path = self._path(f"_tmp_evidence_{prefix}_backlog.csv")
        proposed_path = self._path(f"_tmp_evidence_{prefix}_proposed_updates.csv")
        summary_path = self._path(f"_tmp_evidence_{prefix}_summary.csv")
        report_path = self._path(f"_tmp_evidence_{prefix}_report.md")
        template_path = self._path(f"_tmp_evidence_{prefix}_template.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, master_rows)
        self._write_csv(evidence_path, EVIDENCE_INPUT_FIELDS, evidence_rows)
        run_fundamentals_evidence_engine(
            fundamentals_master_path=str(master_path),
            evidence_input_path=str(evidence_path),
            registry_output=str(registry_path),
            backlog_output=str(backlog_path),
            proposed_updates_output=str(proposed_path),
            summary_output=str(summary_path),
            report_output=str(report_path),
            template_output=str(template_path),
        )
        return master_path, evidence_path, registry_path, backlog_path, proposed_path, summary_path, report_path

    def test_valid_evidence_input_generates_registry_backlog_summary_and_report(self) -> None:
        definitions = load_metric_definitions()
        required = required_kpis_for_profile("STANDARD", definitions)
        evidence_rows = [evidence_row(kpi_name=kpi_name, reported_value=str(index)) for index, kpi_name in enumerate(required, start=1)]

        _master_path, _evidence_path, registry_path, backlog_path, proposed_path, summary_path, report_path = self._run_engine(
            [master_row()],
            evidence_rows,
            "valid",
        )

        registry_rows = read_csv_rows(registry_path)
        backlog_rows = read_csv_rows(backlog_path)
        proposed_rows = read_csv_rows(proposed_path)
        summary_rows = {row["metric_name"]: row["metric_value"] for row in read_csv_rows(summary_path)}
        self.assertEqual(len(registry_rows), len(required))
        self.assertEqual(len(proposed_rows), len(required))
        self.assertEqual(proposed_rows[0]["proposal_reason"], "Validated explicit evidence has reported_value; manual Personal-Master review required.")
        self.assertEqual(backlog_rows[0]["required_kpis_expected"], str(len(required)))
        self.assertEqual(backlog_rows[0]["required_kpis_with_evidence"], str(len(required)))
        self.assertEqual(backlog_rows[0]["missing_required_evidence_kpis"], "")
        self.assertEqual(backlog_rows[0]["weak_verification_kpis"], "")
        self.assertEqual(summary_rows["holdings_with_required_evidence_complete"], "1")
        self.assertIn("Personal Fundamentals Evidence", report_path.read_text(encoding="utf-8"))

    def test_unknown_kpi_name_is_rejected(self) -> None:
        master = [master_row()]
        definitions = load_metric_definitions()

        with self.assertRaisesRegex(ValueError, "unknown kpi_name"):
            build_evidence_registry([evidence_row(kpi_name="not_a_kpi")], master, definitions)

    def test_missing_required_evidence_columns_are_rejected(self) -> None:
        master_path = self._path("_tmp_evidence_missing_columns_master.csv")
        evidence_path = self._path("_tmp_evidence_missing_columns_input.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])
        fieldnames = [field for field in EVIDENCE_INPUT_FIELDS if field != "kpi_name"]
        invalid_row = {field: value for field, value in evidence_row().items() if field in fieldnames}
        self._write_csv(evidence_path, fieldnames, [invalid_row])

        with self.assertRaisesRegex(ValueError, "missing required columns: kpi_name"):
            run_fundamentals_evidence_engine(
                fundamentals_master_path=str(master_path),
                evidence_input_path=str(evidence_path),
                registry_output=str(self._path("_tmp_evidence_missing_columns_registry.csv")),
                backlog_output=str(self._path("_tmp_evidence_missing_columns_backlog.csv")),
                summary_output=str(self._path("_tmp_evidence_missing_columns_summary.csv")),
                report_output=str(self._path("_tmp_evidence_missing_columns_report.md")),
                template_output=str(self._path("_tmp_evidence_missing_columns_template.csv")),
            )

    def test_required_kpi_expectations_follow_company_type_profile(self) -> None:
        _master_path, _evidence_path, _registry_path, backlog_path, _proposed_path, _summary_path, _report_path = self._run_engine(
            [
                master_row(ticker="STD", isin="US0000000001", company_name="Standard Co", profile="STANDARD"),
                master_row(ticker="FIN", isin="US0000000002", company_name="Financial Co", profile="FINANCIAL"),
            ],
            [],
            "profiles",
        )

        rows_by_ticker = {row["ticker"]: row for row in read_csv_rows(backlog_path)}
        self.assertGreater(int(rows_by_ticker["STD"]["required_kpis_expected"]), 0)
        self.assertEqual(rows_by_ticker["STD"]["research_priority"], "HIGH")
        self.assertEqual(rows_by_ticker["FIN"]["required_kpis_expected"], "0")
        self.assertNotEqual(rows_by_ticker["FIN"]["research_priority"], "HIGH")

    def test_holding_without_required_evidence_is_research_gap(self) -> None:
        _master_path, _evidence_path, _registry_path, backlog_path, _proposed_path, _summary_path, _report_path = self._run_engine(
            [master_row()],
            [],
            "missing",
        )

        row = read_csv_rows(backlog_path)[0]
        self.assertEqual(row["research_priority"], "HIGH")
        self.assertEqual(row["needs_research_flag"], "True")
        self.assertIn("revenue_cagr_5y", row["missing_required_evidence_kpis"])

    def test_weak_verification_is_visible_without_hiding_required_evidence(self) -> None:
        definitions = load_metric_definitions()
        required = required_kpis_for_profile("STANDARD", definitions)
        evidence_rows = []
        weak_required_kpi = required[0]
        for kpi_name in required:
            if kpi_name == weak_required_kpi:
                evidence_rows.append(evidence_row(kpi_name=kpi_name, verification_status="REVIEW", data_quality_flag="REVIEW"))
            else:
                evidence_rows.append(evidence_row(kpi_name=kpi_name))

        _master_path, _evidence_path, _registry_path, backlog_path, _proposed_path, _summary_path, _report_path = self._run_engine(
            [master_row()],
            evidence_rows,
            "weak",
        )

        row = read_csv_rows(backlog_path)[0]
        self.assertEqual(row["missing_required_evidence_kpis"], "")
        self.assertEqual(row["research_priority"], "MEDIUM")
        self.assertIn(weak_required_kpi, row["weak_verification_kpis"])

    def test_template_output_is_header_only_contract(self) -> None:
        template_path = self._path("_tmp_evidence_template_only.csv")

        write_evidence_template(str(template_path))

        with template_path.open(encoding="utf-8", newline="") as handle:
            header = next(csv.reader(handle))
            remaining = list(csv.reader(handle))
        self.assertEqual(header, EVIDENCE_INPUT_FIELDS)
        self.assertEqual(remaining, [])

    def test_proposed_updates_skip_blank_reported_values(self) -> None:
        _master_path, _evidence_path, _registry_path, _backlog_path, proposed_path, _summary_path, _report_path = self._run_engine(
            [master_row()],
            [evidence_row(reported_value="")],
            "blank_proposal",
        )

        with proposed_path.open(encoding="utf-8", newline="") as handle:
            header = next(csv.reader(handle))
            remaining = list(csv.reader(handle))
        self.assertEqual(header, PROPOSED_UPDATES_FIELDS)
        self.assertEqual(remaining, [])

    def test_duplicate_identical_evidence_is_idempotent(self) -> None:
        _master_path, _evidence_path, registry_path, _backlog_path, _proposed_path, _summary_path, _report_path = self._run_engine(
            [master_row()],
            [evidence_row(), evidence_row()],
            "dedupe",
        )

        self.assertEqual(len(read_csv_rows(registry_path)), 1)

    def test_conflict_on_same_evidence_identity_fails_fast(self) -> None:
        conflicting = evidence_row(reported_value="26.0")
        conflicting["notes"] = "different value for same evidence identity"

        with self.assertRaisesRegex(ValueError, "personal fundamentals evidence conflict"):
            self._run_engine([master_row()], [evidence_row(), conflicting], "conflict")

    def test_registry_and_backlog_sorting_are_deterministic(self) -> None:
        evidence_rows = [
            evidence_row(ticker="MSFT", isin="US5949181045", kpi_name="roic"),
            evidence_row(ticker="AAPL", isin="US0378331005", company_name="Apple Inc", kpi_name="roic"),
        ]

        _master_path, _evidence_path, registry_path, backlog_path, _proposed_path, _summary_path, _report_path = self._run_engine(
            [
                master_row(ticker="MSFT", isin="US5949181045", company_name="Microsoft Corp"),
                master_row(ticker="AAPL", isin="US0378331005", company_name="Apple Inc"),
            ],
            list(reversed(evidence_rows)),
            "sorting",
        )

        self.assertEqual([row["ticker"] for row in read_csv_rows(registry_path)], ["AAPL", "MSFT"])
        self.assertEqual([row["ticker"] for row in read_csv_rows(backlog_path)], ["AAPL", "MSFT"])

    def test_cli_smoke_builds_registry_backlog_summary_report_and_template(self) -> None:
        master_path = self._path("_tmp_evidence_cli_master.csv")
        evidence_path = self._path("_tmp_evidence_cli_input.csv")
        registry_path = self._path("_tmp_evidence_cli_registry.csv")
        backlog_path = self._path("_tmp_evidence_cli_backlog.csv")
        proposed_path = self._path("_tmp_evidence_cli_proposed_updates.csv")
        summary_path = self._path("_tmp_evidence_cli_summary.csv")
        report_path = self._path("_tmp_evidence_cli_report.md")
        template_path = self._path("_tmp_evidence_cli_template.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])
        self._write_csv(evidence_path, EVIDENCE_INPUT_FIELDS, [evidence_row()])

        result = subprocess.run(
            [
                "python",
                "-m",
                "src.fundamentals_evidence_engine",
                "--fundamentals-master",
                str(master_path),
                "--evidence-input",
                str(evidence_path),
                "--registry-output",
                str(registry_path),
                "--backlog-output",
                str(backlog_path),
                "--proposed-updates-output",
                str(proposed_path),
                "--summary-output",
                str(summary_path),
                "--report-output",
                str(report_path),
                "--template-output",
                str(template_path),
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        for path in [registry_path, backlog_path, proposed_path, summary_path, report_path, template_path]:
            self.assertTrue(path.exists(), path)
        self.assertEqual(read_csv_rows(registry_path)[0]["kpi_name"], "roic")
        self.assertEqual(read_csv_rows(proposed_path)[0]["reported_value"], "25.0")


if __name__ == "__main__":
    unittest.main()
