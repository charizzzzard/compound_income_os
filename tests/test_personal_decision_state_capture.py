from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

from src.personal_decision_state_capture import FIELDS, run_decision_state_capture


class PersonalDecisionStateCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_decision_capture_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_csv(self, path: Path, rows: list[dict[str, str]]) -> None:
        fieldnames = list(rows[0])
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def base_row(self) -> dict[str, str]:
        return {
            "decision_scope": "ASSET",
            "proposed_action": "WAIT_FOR_EVIDENCE",
            "human_decision": "DEFERRED",
            "decision_status": "REVIEW_SCHEDULED",
            "reasoning_3_sentences": "Evidence is incomplete. Waiting preserves discipline. Review when data is available.",
            "dominant_uncertainty": "MISSING_DATA",
            "benchmark_alternative": "CASH",
            "review_date": "2026-05-15",
            "ticker": "MSFT",
            "asset_name": "Microsoft",
        }

    def test_empty_template_csv_has_stable_headers_and_report(self) -> None:
        output = self.tmp / "nested" / "capture.csv"
        report = self.tmp / "reports" / "capture.md"
        result = run_decision_state_capture(output=str(output), report=str(report), report_date="2026-04-29")

        self.assertEqual(result.rows, [])
        self.assertTrue(output.exists())
        self.assertTrue(report.exists())
        with output.open("r", encoding="utf-8") as handle:
            self.assertEqual(handle.readline().strip().split(","), FIELDS)
        self.assertIn("capture_status: EMPTY_STATE", report.read_text(encoding="utf-8"))

    def test_loads_existing_csv_and_defaults_benchmark_reference(self) -> None:
        input_path = self.tmp / "input.csv"
        output = self.tmp / "output.csv"
        report = self.tmp / "report.md"
        self.write_csv(input_path, [self.base_row()])

        result = run_decision_state_capture(
            input_path=str(input_path),
            output=str(output),
            report=str(report),
            run_id="RUN-1",
            manifest_path="data/processed/personal_run_manifest.json",
            primary_report_path="reports/2026-04-29/personal_monthly_decision_report.md",
            source_snapshot_date="2026-04-29",
            report_date="2026-04-29",
        )

        written = self.read_csv(output)
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(written[0]["benchmark_ref_or_label"], "CASH")
        self.assertEqual(written[0]["accounting_basis"], "SNAPSHOT_ONLY")
        self.assertEqual(written[0]["operator_state"], "NOT_RECORDED")
        self.assertEqual(written[0]["decision_pressure"], "UNKNOWN")
        self.assertEqual(written[0]["cash_context"], "UNKNOWN")

    def test_enum_validation_marks_invalid_rows(self) -> None:
        row = self.base_row()
        row["decision_scope"] = "BAD_SCOPE"
        input_path = self.tmp / "input.csv"
        self.write_csv(input_path, [row])

        result = run_decision_state_capture(input_path=str(input_path), output=str(self.tmp / "out.csv"), report=str(self.tmp / "report.md"), report_date="2026-04-29")

        self.assertEqual(len(result.invalid_rows), 1)
        self.assertIn("INVALID_ENUM:decision_scope=BAD_SCOPE", result.invalid_rows[0]["validation_reasons"])

    def test_missing_required_manual_fields_are_reported(self) -> None:
        row = self.base_row()
        row["reasoning_3_sentences"] = ""
        input_path = self.tmp / "input.csv"
        self.write_csv(input_path, [row])

        result = run_decision_state_capture(input_path=str(input_path), output=str(self.tmp / "out.csv"), report=str(self.tmp / "report.md"), report_date="2026-04-29")

        self.assertIn("MISSING_REQUIRED:reasoning_3_sentences", result.invalid_rows[0]["validation_reasons"])

    def test_conditional_review_date_rule(self) -> None:
        row = self.base_row()
        row["proposed_action"] = "RESEARCH_MORE"
        row["decision_status"] = "OPEN"
        row["review_date"] = ""
        input_path = self.tmp / "input.csv"
        self.write_csv(input_path, [row])

        result = run_decision_state_capture(input_path=str(input_path), output=str(self.tmp / "out.csv"), report=str(self.tmp / "report.md"), report_date="2026-04-29")

        self.assertIn("MISSING_CONDITIONAL:review_date", result.invalid_rows[0]["validation_reasons"])

    def test_unresolved_auto_system_references_are_surfaced(self) -> None:
        input_path = self.tmp / "input.csv"
        self.write_csv(input_path, [self.base_row()])

        result = run_decision_state_capture(input_path=str(input_path), output=str(self.tmp / "out.csv"), report=str(self.tmp / "report.md"), report_date="2026-04-29")

        written = self.read_csv(self.tmp / "out.csv")
        self.assertEqual(written[0]["run_id"], "MISSING_REFERENCE")
        self.assertEqual(written[0]["asset_id"], "UNKNOWN")
        self.assertTrue(result.missing_replay_references)
        self.assertIn("Missing Replay References", (self.tmp / "report.md").read_text(encoding="utf-8"))

    def test_report_contains_required_sections_and_v1_exclusions(self) -> None:
        input_path = self.tmp / "input.csv"
        self.write_csv(input_path, [self.base_row()])

        run_decision_state_capture(input_path=str(input_path), output=str(self.tmp / "out.csv"), report=str(self.tmp / "report.md"), report_date="2026-06-01")
        report_text = (self.tmp / "report.md").read_text(encoding="utf-8")

        for section in [
            "Summary",
            "Row Counts",
            "Open Decisions",
            "Blocked Decisions",
            "No-Action Entries",
            "Wait / Review Scheduled Entries",
            "Overdue Review Items",
            "Missing Replay References",
            "Invalid Rows",
            "V1 Exclusions",
            "Input / Output Paths",
        ]:
            self.assertIn(f"## {section}", report_text)
        self.assertIn("not order execution", report_text)
        self.assertIn("no benchmark return calculation", report_text)
        self.assertIn("no simulation", report_text)
        self.assertNotIn("Buy now", report_text)
        self.assertNotIn("Sell now", report_text)

    def test_deterministic_output_column_order(self) -> None:
        input_path = self.tmp / "input.csv"
        self.write_csv(input_path, [self.base_row()])
        output = self.tmp / "out.csv"

        run_decision_state_capture(input_path=str(input_path), output=str(output), report=str(self.tmp / "report.md"), report_date="2026-04-29")

        with output.open("r", encoding="utf-8") as handle:
            self.assertEqual(handle.readline().strip().split(","), FIELDS)


if __name__ == "__main__":
    unittest.main()
