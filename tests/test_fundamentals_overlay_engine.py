from __future__ import annotations

import csv
import subprocess
import unittest
from datetime import date
from pathlib import Path

from src.common import read_csv_rows
from src.fundamentals_master import CORE_KPI_FIELDS, PERSONAL_MASTER_FIELDS
from src.fundamentals_overlay_engine import (
    APPLIED_MASTER_FIELDS,
    OVERLAY_INPUT_FIELDS,
    OVERLAY_REVIEW_BACKLOG_FIELDS,
    build_overlay_registry,
    load_allowed_overlay_thesis_values,
    run_fundamentals_overlay_engine,
    write_overlay_template,
)


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
            "roic": "21.5",
            "normalized_fcf_yield_pct": "4.5",
        }
    )
    for kpi_name in CORE_KPI_FIELDS:
        row.setdefault(kpi_name, "")
    return row


def overlay_row(
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    overlay_as_of_date: str = "2026-04-10",
    overlay_author: str = "analyst_a",
    thesis: str = "ROBUST",
    hard_risk: str = "false",
    manual_override: str = "false",
    manual_reason: str = "",
    notes: str = "fixture overlay",
) -> dict[str, str]:
    row = {field: "" for field in OVERLAY_INPUT_FIELDS}
    row.update(
        {
            "ticker": ticker,
            "isin": isin,
            "company_name": company_name,
            "overlay_as_of_date": overlay_as_of_date,
            "overlay_source_name": "manual_overlay_review",
            "overlay_author": overlay_author,
            "overlay_thesis_robustness": thesis,
            "overlay_has_hard_risk_flag": hard_risk,
            "overlay_analyst_notes": "explicit unit overlay",
            "overlay_manual_override_flag": manual_override,
            "overlay_manual_override_reason": manual_reason,
            "verification_status": "VERIFIED",
            "notes": notes,
            "overlay_review_due_date": "2026-07-10",
            "overlay_priority": "MEDIUM",
            "source_reference": "internal note 2026-04-10",
        }
    )
    return row


class FundamentalsOverlayEngineTests(unittest.TestCase):
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
        overlay_rows: list[dict[str, str]],
        prefix: str,
        run_date: date = date(2026, 4, 14),
    ) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path]:
        master_path = self._path(f"_tmp_overlay_{prefix}_master.csv")
        overlay_path = self._path(f"_tmp_overlay_{prefix}_input.csv")
        registry_path = self._path(f"_tmp_overlay_{prefix}_registry.csv")
        applied_path = self._path(f"_tmp_overlay_{prefix}_applied.csv")
        summary_path = self._path(f"_tmp_overlay_{prefix}_summary.csv")
        review_backlog_path = self._path(f"_tmp_overlay_{prefix}_review_backlog.csv")
        report_path = self._path(f"_tmp_overlay_{prefix}_report.md")
        template_path = self._path(f"_tmp_overlay_{prefix}_template.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, master_rows)
        self._write_csv(overlay_path, OVERLAY_INPUT_FIELDS, overlay_rows)
        run_fundamentals_overlay_engine(
            fundamentals_master_path=str(master_path),
            overlay_input_path=str(overlay_path),
            registry_output=str(registry_path),
            applied_master_output=str(applied_path),
            summary_output=str(summary_path),
            review_backlog_output=str(review_backlog_path),
            report_output=str(report_path),
            template_output=str(template_path),
            run_date=run_date,
        )
        return master_path, overlay_path, registry_path, applied_path, summary_path, review_backlog_path, report_path, template_path

    def test_valid_overlay_input_generates_registry_applied_master_summary_and_report(self) -> None:
        _master_path, _overlay_path, registry_path, applied_path, summary_path, review_backlog_path, report_path, _template_path = self._run_engine(
            [master_row()],
            [overlay_row(hard_risk="true", manual_override="true", manual_reason="temporary override")],
            "valid",
        )

        registry_rows = read_csv_rows(registry_path)
        applied_rows = read_csv_rows(applied_path)
        summary_rows = {row["metric_name"]: row["metric_value"] for row in read_csv_rows(summary_path)}
        self.assertEqual(len(registry_rows), 1)
        self.assertEqual(registry_rows[0]["overlay_has_hard_risk_flag"], "True")
        self.assertEqual(registry_rows[0]["overlay_review_status"], "OK")
        self.assertEqual(read_csv_rows(review_backlog_path), [])
        self.assertEqual(applied_rows[0]["overlay_active_flag"], "True")
        self.assertEqual(applied_rows[0]["overlay_thesis_robustness"], "ROBUST")
        self.assertEqual(applied_rows[0]["overlay_manual_override_reason"], "temporary override")
        self.assertEqual(summary_rows["holdings_with_active_overlay"], "1")
        self.assertIn("Personal Fundamentals Overlay", report_path.read_text(encoding="utf-8"))

    def test_invalid_overlay_thesis_robustness_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid overlay_thesis_robustness"):
            self._run_engine([master_row()], [overlay_row(thesis="STRONG")], "bad_thesis")

    def test_missing_required_overlay_columns_are_rejected(self) -> None:
        master_path = self._path("_tmp_overlay_missing_columns_master.csv")
        overlay_path = self._path("_tmp_overlay_missing_columns_input.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])
        fieldnames = [field for field in OVERLAY_INPUT_FIELDS if field != "overlay_as_of_date"]
        invalid_row = {field: value for field, value in overlay_row().items() if field in fieldnames}
        self._write_csv(overlay_path, fieldnames, [invalid_row])

        with self.assertRaisesRegex(ValueError, "missing required columns: overlay_as_of_date"):
            run_fundamentals_overlay_engine(
                fundamentals_master_path=str(master_path),
                overlay_input_path=str(overlay_path),
                registry_output=str(self._path("_tmp_overlay_missing_columns_registry.csv")),
                applied_master_output=str(self._path("_tmp_overlay_missing_columns_applied.csv")),
                summary_output=str(self._path("_tmp_overlay_missing_columns_summary.csv")),
                report_output=str(self._path("_tmp_overlay_missing_columns_report.md")),
                template_output=str(self._path("_tmp_overlay_missing_columns_template.csv")),
            )

    def test_unknown_holding_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "no exact ticker/isin match"):
            self._run_engine([master_row()], [overlay_row(ticker="AAPL", isin="US0378331005", company_name="Apple Inc")], "unknown")

    def test_manual_override_without_reason_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "overlay_manual_override_flag=true"):
            self._run_engine([master_row()], [overlay_row(manual_override="true", manual_reason="")], "manual_reason")

    def test_applied_master_preserves_core_kpi_fields(self) -> None:
        _master_path, _overlay_path, _registry_path, applied_path, _summary_path, _review_backlog_path, _report_path, _template_path = self._run_engine(
            [master_row()],
            [overlay_row(thesis="FRAGILE")],
            "preserve_core",
        )

        applied = read_csv_rows(applied_path)[0]
        self.assertEqual(applied["roic"], "21.5")
        self.assertEqual(applied["normalized_fcf_yield_pct"], "4.5")
        self.assertEqual(applied["overlay_thesis_robustness"], "FRAGILE")

    def test_duplicate_identical_overlay_is_idempotent(self) -> None:
        _master_path, _overlay_path, registry_path, _applied_path, _summary_path, _review_backlog_path, _report_path, _template_path = self._run_engine(
            [master_row()],
            [overlay_row(), overlay_row()],
            "dedupe",
        )

        self.assertEqual(len(read_csv_rows(registry_path)), 1)

    def test_conflicting_overlay_duplicate_fails_fast(self) -> None:
        conflicting = overlay_row(notes="different notes for same overlay identity")

        with self.assertRaisesRegex(ValueError, "personal fundamentals overlay conflict"):
            self._run_engine([master_row()], [overlay_row(), conflicting], "conflict")

    def test_registry_and_applied_master_sorting_are_deterministic(self) -> None:
        _master_path, _overlay_path, registry_path, applied_path, _summary_path, _review_backlog_path, _report_path, _template_path = self._run_engine(
            [
                master_row(ticker="MSFT", isin="US5949181045", company_name="Microsoft Corp"),
                master_row(ticker="AAPL", isin="US0378331005", company_name="Apple Inc"),
            ],
            [
                overlay_row(ticker="MSFT", isin="US5949181045", company_name="Microsoft Corp"),
                overlay_row(ticker="AAPL", isin="US0378331005", company_name="Apple Inc"),
            ],
            "sorting",
        )

        self.assertEqual([row["ticker"] for row in read_csv_rows(registry_path)], ["AAPL", "MSFT"])
        self.assertEqual([row["ticker"] for row in read_csv_rows(applied_path)], ["AAPL", "MSFT"])

    def test_review_due_and_overdue_are_marked_and_backlogged(self) -> None:
        overdue = overlay_row(
            ticker="AAPL",
            isin="US0378331005",
            company_name="Apple Inc",
            overlay_as_of_date="2026-04-01",
            overlay_author="analyst_b",
            hard_risk="true",
            notes="overdue overlay",
        )
        overdue["overlay_review_due_date"] = "2026-04-13"
        overdue["overlay_priority"] = "HIGH"
        due = overlay_row(manual_override="true", manual_reason="temporary override", notes="due overlay")
        due["overlay_review_due_date"] = "2026-04-14"

        _master_path, _overlay_path, registry_path, _applied_path, summary_path, review_backlog_path, report_path, _template_path = self._run_engine(
            [
                master_row(ticker="MSFT", isin="US5949181045", company_name="Microsoft Corp"),
                master_row(ticker="AAPL", isin="US0378331005", company_name="Apple Inc"),
            ],
            [due, overdue],
            "review_due",
            run_date=date(2026, 4, 14),
        )

        registry_by_ticker = {row["ticker"]: row for row in read_csv_rows(registry_path)}
        summary_rows = {row["metric_name"]: row["metric_value"] for row in read_csv_rows(summary_path)}
        backlog_rows = read_csv_rows(review_backlog_path)
        self.assertEqual(registry_by_ticker["AAPL"]["overlay_review_status"], "OVERDUE")
        self.assertEqual(registry_by_ticker["MSFT"]["overlay_review_status"], "DUE")
        self.assertEqual(registry_by_ticker["AAPL"]["needs_overlay_review_flag"], "True")
        self.assertEqual(summary_rows["overlay_review_due_count"], "1")
        self.assertEqual(summary_rows["overlay_review_overdue_count"], "1")
        self.assertEqual([row["ticker"] for row in backlog_rows], ["AAPL", "MSFT"])
        self.assertEqual(backlog_rows[0]["overlay_review_status"], "OVERDUE")
        self.assertEqual(set(backlog_rows[0]), set(OVERLAY_REVIEW_BACKLOG_FIELDS))
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("Faellige Overlay-Reviews", report_text)
        self.assertIn("OVERDUE", report_text)

    def test_template_output_is_header_only_contract(self) -> None:
        template_path = self._path("_tmp_overlay_template_only.csv")

        write_overlay_template(str(template_path))

        with template_path.open(encoding="utf-8", newline="") as handle:
            header = next(csv.reader(handle))
            remaining = list(csv.reader(handle))
        self.assertEqual(header, OVERLAY_INPUT_FIELDS)
        self.assertEqual(remaining, [])

    def test_cli_smoke_builds_registry_applied_master_report_and_template(self) -> None:
        master_path = self._path("_tmp_overlay_cli_master.csv")
        overlay_path = self._path("_tmp_overlay_cli_input.csv")
        registry_path = self._path("_tmp_overlay_cli_registry.csv")
        applied_path = self._path("_tmp_overlay_cli_applied.csv")
        summary_path = self._path("_tmp_overlay_cli_summary.csv")
        review_backlog_path = self._path("_tmp_overlay_cli_review_backlog.csv")
        report_path = self._path("_tmp_overlay_cli_report.md")
        template_path = self._path("_tmp_overlay_cli_template.csv")
        self._write_csv(master_path, PERSONAL_MASTER_FIELDS, [master_row()])
        self._write_csv(overlay_path, OVERLAY_INPUT_FIELDS, [overlay_row()])

        result = subprocess.run(
            [
                "python",
                "-m",
                "src.fundamentals_overlay_engine",
                "--fundamentals-master",
                str(master_path),
                "--overlay-input",
                str(overlay_path),
                "--registry-output",
                str(registry_path),
                "--applied-master-output",
                str(applied_path),
                "--summary-output",
                str(summary_path),
                "--review-backlog-output",
                str(review_backlog_path),
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
        for path in [registry_path, applied_path, summary_path, review_backlog_path, report_path, template_path]:
            self.assertTrue(path.exists(), path)
        self.assertEqual(read_csv_rows(registry_path)[0]["overlay_thesis_robustness"], "ROBUST")
        self.assertEqual(read_csv_rows(applied_path)[0]["overlay_active_flag"], "True")

    def test_cli_template_only_does_not_require_master_or_overlay_input(self) -> None:
        template_path = self._path("_tmp_overlay_cli_template_only.csv")

        result = subprocess.run(
            [
                "python",
                "-m",
                "src.fundamentals_overlay_engine",
                "--template-only",
                "--template-output",
                str(template_path),
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        with template_path.open(encoding="utf-8", newline="") as handle:
            self.assertEqual(next(csv.reader(handle)), OVERLAY_INPUT_FIELDS)

    def test_direct_registry_uses_schema_allowed_values(self) -> None:
        allowed = load_allowed_overlay_thesis_values()

        registry = build_overlay_registry([overlay_row(thesis="review")], [master_row()], allowed)

        self.assertEqual(registry[0]["overlay_thesis_robustness"], "REVIEW")
        self.assertEqual(registry[0]["overlay_validation_status"], "VALID")


if __name__ == "__main__":
    unittest.main()
