from __future__ import annotations

import csv
import shutil
import unittest
from pathlib import Path

from src.personal_watchlist_input_gate import run_personal_watchlist_input_gate

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


class PersonalWatchlistInputGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_watchlist_input_gate"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.used_inputs = self.tmp / "used_inputs.csv"
        self.watchlist = self.tmp / "watchlist.csv"
        self.gate = self.tmp / "gate.csv"
        self.summary = self.tmp / "summary.csv"
        self.report = self.tmp / "report.md"

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_used_inputs(self, path_value: str, *, exists: str = "True", notes: str = "") -> None:
        write_csv(
            self.used_inputs,
            ["stage_name", "stage_status", "input_role", "input_path", "input_exists", "notes"],
            [{"stage_name": "watchlist", "stage_status": "SUCCESS", "input_role": "watchlist_input", "input_path": path_value, "input_exists": exists, "notes": notes}],
        )

    def write_watchlist(self, rows: list[dict[str, str]]) -> None:
        write_csv(self.watchlist, ["ticker", "status", "data_quality_flag"], rows)

    def run_gate(self):
        return run_personal_watchlist_input_gate(
            used_inputs_input=str(self.used_inputs),
            watchlist_input=str(self.watchlist),
            gate_output=str(self.gate),
            summary_output=str(self.summary),
            report_output=str(self.report),
        )

    def summary_value(self, metric: str) -> str:
        return {row["metric"]: row["value"] for row in read_csv(self.summary)}[metric]

    def gate_row(self) -> dict[str, str]:
        return read_csv(self.gate)[0]

    def test_sample_watchlist_input_is_demo_only_and_blocked(self) -> None:
        self.write_used_inputs("data/raw/sample_watchlist.csv")
        self.write_watchlist([{"ticker": "AAA", "status": "REVIEW", "data_quality_flag": "MISSING_DATA"}])
        self.run_gate()

        row = self.gate_row()
        self.assertEqual(row["watchlist_input_status"], "SAMPLE_DEMO_ONLY")
        self.assertEqual(row["watchlist_readiness_status"], "BLOCKED")
        self.assertIn("WATCHLIST_SAMPLE_INPUT", row["reason_codes"])
        self.assertEqual(self.summary_value("watchlist_sample_input_active"), "True")

    def test_all_review_or_missing_rows_are_flagged(self) -> None:
        self.write_used_inputs("data/raw/personal_watchlist_reviewed.csv", notes="reviewed=true")
        self.write_watchlist(
            [
                {"ticker": "AAA", "status": "REVIEW", "data_quality_flag": "MISSING_DATA"},
                {"ticker": "BBB", "status": "REVIEW", "data_quality_flag": "MISSING_DATA"},
            ]
        )
        self.run_gate()

        row = self.gate_row()
        self.assertEqual(row["watchlist_data_status"], "MISSING_DATA")
        self.assertIn("WATCHLIST_REVIEW_OR_MISSING_DATA", row["reason_codes"])

    def test_missing_watchlist_artifact_creates_not_available_without_crash(self) -> None:
        self.write_used_inputs("data/raw/personal_watchlist_reviewed.csv", notes="reviewed=true")
        self.run_gate()

        row = self.gate_row()
        self.assertEqual(row["watchlist_input_status"], "NOT_AVAILABLE")
        self.assertEqual(row["watchlist_readiness_status"], "NOT_AVAILABLE")
        self.assertIn("WATCHLIST_ARTIFACT_MISSING", row["reason_codes"])
        self.assertEqual(self.summary_value("warnings_total"), "1")

    def test_personal_watchlist_without_review_marker_is_review(self) -> None:
        self.write_used_inputs("data/raw/personal_watchlist.csv")
        self.write_watchlist([{"ticker": "AAA", "status": "OK", "data_quality_flag": "OK"}])
        self.run_gate()

        row = self.gate_row()
        self.assertEqual(row["watchlist_input_status"], "PERSONAL_UNREVIEWED")
        self.assertEqual(row["watchlist_readiness_status"], "REVIEW")
        self.assertIn("WATCHLIST_PERSONAL_UNREVIEWED", row["reason_codes"])

    def test_personal_reviewed_watchlist_with_ok_rows_passes(self) -> None:
        self.write_used_inputs("data/raw/personal_watchlist_reviewed.csv", notes="reviewed=true")
        self.write_watchlist([{"ticker": "AAA", "status": "OK", "data_quality_flag": "OK"}])
        self.run_gate()

        row = self.gate_row()
        self.assertEqual(row["watchlist_input_status"], "PERSONAL_REVIEWED")
        self.assertEqual(row["watchlist_data_status"], "OK")
        self.assertEqual(row["watchlist_readiness_status"], "PASS")

    def test_private_paths_are_sanitized_in_report(self) -> None:
        private_used_inputs = self.tmp / "data" / "raw" / "private" / "used_inputs.csv"
        private_watchlist = self.tmp / "data" / "raw" / "private" / "watchlist.csv"
        write_csv(
            private_used_inputs,
            ["stage_name", "stage_status", "input_role", "input_path", "input_exists", "notes"],
            [{"stage_name": "watchlist", "stage_status": "SUCCESS", "input_role": "watchlist_input", "input_path": "data/raw/private/watchlist.csv", "input_exists": "True", "notes": ""}],
        )
        write_csv(private_watchlist, ["ticker", "status", "data_quality_flag"], [{"ticker": "AAA", "status": "OK", "data_quality_flag": "OK"}])
        run_personal_watchlist_input_gate(
            used_inputs_input=str(private_used_inputs),
            watchlist_input=str(private_watchlist),
            gate_output=str(self.gate),
            summary_output=str(self.summary),
            report_output=str(self.report),
        )

        report = self.report.read_text(encoding="utf-8")
        self.assertIn("<private_path>", report)
        self.assertNotIn("data/raw/private/watchlist.csv", report)


if __name__ == "__main__":
    unittest.main()
