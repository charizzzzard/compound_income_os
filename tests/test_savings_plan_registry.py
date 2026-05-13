from __future__ import annotations

import csv
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from src.savings_plan_registry import (
    REGISTRY_FIELDS,
    SUMMARY_FIELDS,
    load_savings_plan_registry,
    run_savings_plan_registry,
    summarize_savings_plan_registry,
    validate_savings_plan_registry,
    write_summary_csv,
)


class SavingsPlanRegistryTests(unittest.TestCase):
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

    def _row(self, ticker: str = "msft", active: str = "TRUE") -> dict[str, str]:
        return {
            "ticker": ticker,
            "isin": "US5949181045",
            "broker": "TRADE_REPUBLIC",
            "instrument_name": "Microsoft",
            "monthly_amount_eur": "25",
            "frequency": "MONTHLY",
            "execution_day_of_month": "2",
            "active": active,
            "started_at": "2026-01-01",
            "last_modified": "2026-05-01",
            "notes": "",
        }

    def test_happy_path_three_active_plans_load_and_summarize(self) -> None:
        path = self._path("_tmp_savings_plan_registry.csv")
        self._write_csv(path, REGISTRY_FIELDS, [self._row("msft"), self._row("aapl"), self._row("nvda")])

        loaded = load_savings_plan_registry(path)
        rows, warnings = validate_savings_plan_registry(loaded, str(path))
        summary = summarize_savings_plan_registry(rows, warnings)

        self.assertEqual([row["ticker"] for row in rows], ["MSFT", "AAPL", "NVDA"])
        self.assertEqual(summary["row_count"], "3")
        self.assertEqual(summary["active_count"], "3")
        self.assertEqual(summary["total_monthly_eur"], "75.00")
        self.assertEqual(summary["next_execution_day"], "2")
        self.assertEqual(summary["data_quality_flag"], "OK")

    def test_unknown_column_rejected(self) -> None:
        path = self._path("_tmp_savings_plan_unknown.csv")
        self._write_csv(path, [*REGISTRY_FIELDS, "extra"], [])

        with self.assertRaisesRegex(ValueError, "unknown columns: extra"):
            load_savings_plan_registry(path)

    def test_missing_required_column_raises_clear_error(self) -> None:
        path = self._path("_tmp_savings_plan_missing.csv")
        fields = [field for field in REGISTRY_FIELDS if field != "ticker"]
        self._write_csv(path, fields, [])

        with self.assertRaisesRegex(ValueError, "missing required columns: ticker"):
            load_savings_plan_registry(path)

    def test_frequency_enum_violation_raises(self) -> None:
        row = self._row()
        row["frequency"] = "WEEKLY"

        with self.assertRaisesRegex(ValueError, "frequency has invalid enum value: WEEKLY"):
            validate_savings_plan_registry([row])

    def test_negative_monthly_amount_raises(self) -> None:
        row = self._row()
        row["monthly_amount_eur"] = "-1"

        with self.assertRaisesRegex(ValueError, "monthly_amount_eur must be non-negative"):
            validate_savings_plan_registry([row])

    def test_invalid_optional_isin_warns_but_does_not_reject(self) -> None:
        row = self._row()
        row["isin"] = "INVALID"

        rows, warnings = validate_savings_plan_registry([row])

        self.assertEqual(rows[0]["ticker"], "MSFT")
        self.assertEqual(warnings, ["INVALID_ISIN:MSFT"])
        self.assertEqual(summarize_savings_plan_registry(rows, warnings)["data_quality_flag"], "WARNINGS_PRESENT")

    def test_header_only_registry_valid(self) -> None:
        path = self._path("_tmp_savings_plan_empty.csv")
        self._write_csv(path, REGISTRY_FIELDS, [])

        result = run_savings_plan_registry(
            input_path=str(path),
            summary_output=str(self._path("_tmp_savings_plan_empty_summary.csv")),
            report_output=str(self._path("_tmp_savings_plan_empty_report.md")),
        )

        self.assertEqual(result["summary"]["row_count"], "0")
        self.assertEqual(result["summary"]["active_count"], "0")
        self.assertEqual(result["summary"]["data_quality_flag"], "EMPTY_REGISTRY")
        self.assertIn("EMPTY_STATE", result["report_path"].read_text(encoding="utf-8"))

    def test_atomic_write_preserves_old_file_on_replace_error(self) -> None:
        path = self._path("_tmp_savings_plan_atomic_summary.csv")
        path.write_text("old\n", encoding="utf-8")

        with patch("src.savings_plan_registry.os.replace", side_effect=OSError("replace failed")):
            with self.assertRaises(OSError):
                write_summary_csv({field: "" for field in SUMMARY_FIELDS}, path)

        self.assertEqual(path.read_text(encoding="utf-8"), "old\n")

    def test_duplicate_ticker_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate tickers: MSFT"):
            validate_savings_plan_registry([self._row("MSFT"), self._row("msft")])

    def test_cli_help_exits_zero(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "src.savings_plan_registry", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0)
        self.assertIn("--summary-output", completed.stdout)

    def test_schema_order_preserved_in_written_summary_csv(self) -> None:
        path = self._path("_tmp_savings_plan_summary_order.csv")
        write_summary_csv({field: field for field in SUMMARY_FIELDS}, path)

        header = path.read_text(encoding="utf-8").splitlines()[0].split(",")

        self.assertEqual(header, SUMMARY_FIELDS)


if __name__ == "__main__":
    unittest.main()
