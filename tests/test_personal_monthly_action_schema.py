from __future__ import annotations

import csv
import shutil
import unittest
from pathlib import Path

from src.personal_monthly_action_schema import (
    FORBIDDEN_MONTHLY_ACTION_VALUES,
    run_personal_monthly_action_schema,
)

ROOT = Path(__file__).resolve().parent.parent


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class PersonalMonthlyActionSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_monthly_action_schema"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.monthly = self.tmp / "monthly.csv"
        self.compatibility = self.tmp / "compatibility.csv"
        self.summary = self.tmp / "summary.csv"
        self.report = self.tmp / "report.md"

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def run_schema(self):
        return run_personal_monthly_action_schema(
            monthly_input=str(self.monthly),
            compatibility_output=str(self.compatibility),
            summary_output=str(self.summary),
            report_output=str(self.report),
        )

    def summary_value(self, metric: str) -> str:
        return {row["metric"]: row["value"] for row in read_csv(self.summary)}[metric]

    def test_existing_monthly_artifact_maps_to_neutral_monthly_action(self) -> None:
        write_csv(
            self.monthly,
            ["rank", "ticker", "company_name", "target_action", "allocation_status", "suggested_buy_amount_eur", "constraint_checks"],
            [
                {"rank": "1", "ticker": "AAA", "company_name": "Alpha", "target_action": "WAIT_VALUATION", "allocation_status": "NOT_ELIGIBLE", "suggested_buy_amount_eur": "0", "constraint_checks": "valuation_data_status_MISSING"},
                {"rank": "2", "ticker": "BBB", "company_name": "Beta", "target_action": "REVIEW_CORE_DATA", "allocation_status": "NOT_ELIGIBLE", "suggested_buy_amount_eur": "0", "constraint_checks": ""},
                {"rank": "3", "ticker": "CCC", "company_name": "Cash", "target_action": "HOLD_CASH", "allocation_status": "SELECTED_THIS_MONTH", "suggested_buy_amount_eur": "500", "constraint_checks": ""},
            ],
        )
        self.run_schema()

        rows = {row["ticker"]: row for row in read_csv(self.compatibility)}
        self.assertEqual(rows["AAA"]["monthly_action"], "WAIT_FOR_VALUATION")
        self.assertEqual(rows["BBB"]["monthly_action"], "REVIEW_DATA")
        self.assertEqual(rows["CCC"]["monthly_action"], "NO_ACTION")
        self.assertEqual(rows["AAA"]["legacy_target_action"], "WAIT_VALUATION")
        self.assertEqual(rows["AAA"]["legacy_allocation_status"], "NOT_ELIGIBLE")
        self.assertEqual(self.summary_value("monthly_schema_drift_resolved"), "True")

    def test_blocked_or_missing_data_maps_to_neutral_not_ready(self) -> None:
        write_csv(
            self.monthly,
            ["rank", "ticker", "company_name", "target_action", "allocation_status", "suggested_buy_amount_eur", "constraint_checks"],
            [{"rank": "1", "ticker": "AAA", "company_name": "Alpha", "target_action": "DO_NOT_BUY", "allocation_status": "NOT_ELIGIBLE", "suggested_buy_amount_eur": "0", "constraint_checks": "data_quality=MISSING_DATA"}],
        )
        self.run_schema()

        row = read_csv(self.compatibility)[0]
        self.assertEqual(row["monthly_action"], "NOT_READY")
        self.assertNotIn(row["monthly_action"], FORBIDDEN_MONTHLY_ACTION_VALUES)

    def test_missing_monthly_artifact_creates_empty_outputs_without_crash(self) -> None:
        self.run_schema()

        self.assertEqual(read_csv(self.compatibility), [])
        self.assertEqual(self.summary_value("monthly_rows_total"), "0")
        self.assertEqual(self.summary_value("monthly_schema_drift_resolved"), "False")
        self.assertEqual(self.summary_value("warnings_total"), "1")

    def test_new_monthly_action_values_do_not_use_advice_language(self) -> None:
        write_csv(
            self.monthly,
            ["rank", "ticker", "company_name", "target_action", "allocation_status", "suggested_buy_amount_eur", "constraint_checks"],
            [
                {"rank": "1", "ticker": "AAA", "company_name": "Alpha", "target_action": "BUY", "allocation_status": "SELECTED_THIS_MONTH", "suggested_buy_amount_eur": "100", "constraint_checks": ""},
                {"rank": "2", "ticker": "BBB", "company_name": "Beta", "target_action": "SELL", "allocation_status": "BLOCKED", "suggested_buy_amount_eur": "0", "constraint_checks": ""},
            ],
        )
        self.run_schema()

        for row in read_csv(self.compatibility):
            self.assertNotIn(row["monthly_action"], FORBIDDEN_MONTHLY_ACTION_VALUES)
        self.assertEqual(self.summary_value("forbidden_monthly_action_values_total"), "0")

    def test_report_documents_legacy_terms_without_private_path_dump(self) -> None:
        private_monthly = self.tmp / "data" / "raw" / "private" / "monthly.csv"
        write_csv(
            private_monthly,
            ["rank", "ticker", "company_name", "target_action", "allocation_status", "suggested_buy_amount_eur", "constraint_checks"],
            [{"rank": "1", "ticker": "AAA", "company_name": "Alpha", "target_action": "DO_NOT_BUY", "allocation_status": "NOT_ELIGIBLE", "suggested_buy_amount_eur": "0", "constraint_checks": ""}],
        )
        run_personal_monthly_action_schema(
            monthly_input=str(private_monthly),
            compatibility_output=str(self.compatibility),
            summary_output=str(self.summary),
            report_output=str(self.report),
        )

        report = self.report.read_text(encoding="utf-8")
        self.assertIn("legacy/internal", report)
        self.assertIn("<private_path>", report)
        self.assertNotIn("data/raw/private/monthly.csv", report)


if __name__ == "__main__":
    unittest.main()
