from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

from src.personal_decision_state_capture import ENUMS, FIELDS, append_decision_capture, run_decision_state_capture


EXPECTED_ENUMS = {
    "decision_scope": {"ASSET", "HOLDING_REVIEW", "PORTFOLIO", "CASH", "MONTHLY_REVIEW", "WATCHLIST", "UNKNOWN"},
    "proposed_action": {
        "ADD_REVIEW",
        "HOLD_REVIEW",
        "TRIM_REVIEW",
        "EXIT_REVIEW",
        "WAIT_FOR_EVIDENCE",
        "WAIT_FOR_PRICE",
        "WAIT_FOR_REVIEW",
        "RESEARCH_MORE",
        "REJECT_CANDIDATE",
        "NO_ACTION",
        "SKIP_MONTH",
        "CASH_DEPLOYMENT",
        "UNKNOWN",
    },
    "human_decision": {"PENDING_REVIEW", "APPROVED_FOR_MANUAL_ACTION", "REJECTED", "DEFERRED", "NO_ACTION", "NOT_REVIEWED"},
    "decision_status": {"OPEN", "BLOCKED", "REVIEW_SCHEDULED", "CLOSED", "NOT_AVAILABLE", "INVALID", "INSUFFICIENT_EVIDENCE", "SUPERSEDED"},
    "dominant_uncertainty": {
        "MISSING_DATA",
        "VALUATION",
        "PORTFOLIO_FIT",
        "CASH_CONTEXT",
        "TAX_CONTEXT",
        "EVIDENCE_QUALITY",
        "BEHAVIOURAL_RISK",
        "UNKNOWN",
    },
    "benchmark_alternative": {
        "CASH",
        "CORE_ETF",
        "DIVIDEND_GROWTH_ETF",
        "QUALITY_ETF",
        "EXISTING_HOLDING",
        "WATCHLIST_CANDIDATE",
        "WATCHLIST_TOP_CANDIDATE",
        "NO_ACTION",
        "UNKNOWN",
    },
    "accounting_basis": {"SNAPSHOT_ONLY", "PARTIAL_LEDGER", "RECONCILED_LEDGER", "UNKNOWN"},
    "cash_context": {"AVAILABLE_CASH", "RESERVED_CASH", "TAX_RESERVE", "NO_CASH", "UNKNOWN"},
    "operator_state": {"NORMAL", "MARKET_STRESS", "DRAWDOWN_STRESS", "EUPHORIA", "TIME_CONSTRAINED", "UNCERTAIN", "NOT_RECORDED"},
    "decision_pressure": {"NORMAL", "TIME_CONSTRAINED", "MARKET_STRESS", "UNKNOWN"},
}


class PersonalDecisionStateCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_decision_capture_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_csv(self, path: Path, rows: list[dict[str, str]]) -> None:
        fieldnames = list(dict.fromkeys(field for row in rows for field in row))
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

    def append_capture(self, output: Path, report: Path, **overrides: str):
        values = {
            "decision_date": "2026-05-18",
            "decision_scope": "ASSET",
            "ticker": "MSFT",
            "asset_name": "Microsoft Corp.",
            "proposed_action": "WAIT_FOR_PRICE",
            "human_decision": "DEFERRED",
            "decision_status": "REVIEW_SCHEDULED",
            "reasoning_3_sentences": (
                "The candidate remains high quality. The current valuation does not justify adding this month. "
                "Review again after updated valuation and cash context are available."
            ),
            "dominant_uncertainty": "VALUATION",
            "benchmark_alternative": "CASH",
            "review_date": "2026-06-18",
            "run_id": "2026-05-18-monthly",
            "primary_report_path": "reports/2026-05-18/personal_monthly_decision_report.md",
            "manifest_path": "data/processed/personal_run_manifest.json",
            "source_snapshot_date": "2026-05-18",
        }
        values.update(overrides)
        return append_decision_capture(output=str(output), report=str(report), **values)

    def documented_enums(self) -> dict[str, set[str]]:
        contract = Path("docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md").read_text(encoding="utf-8")
        documented: dict[str, set[str]] = {}
        for field in EXPECTED_ENUMS:
            match = re.search(rf"### `{re.escape(field)}`\n\n(?P<body>.*?)(?:\n## |\n### |\Z)", contract, re.S)
            self.assertIsNotNone(match, field)
            documented[field] = set(re.findall(r"^- `([^`]+)`", match.group("body"), re.M))
        return documented

    def test_documented_enums_match_producer_source_of_truth(self) -> None:
        self.assertEqual(ENUMS, EXPECTED_ENUMS)
        self.assertEqual(self.documented_enums(), EXPECTED_ENUMS)

    def test_contract_documented_enum_values_are_accepted(self) -> None:
        rows: list[dict[str, str]] = []
        for field, values in EXPECTED_ENUMS.items():
            for value in sorted(values):
                row = self.base_row()
                row[field] = value
                rows.append(row)
        input_path = self.tmp / "input.csv"
        self.write_csv(input_path, rows)

        result = run_decision_state_capture(input_path=str(input_path), output=str(self.tmp / "out.csv"), report=str(self.tmp / "report.md"), report_date="2026-04-29")

        self.assertEqual(result.invalid_rows, [])

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

    def test_cli_help_works(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "src.personal_decision_state_capture", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("capture", result.stdout)
        self.assertIn("does not execute trades", result.stdout)

    def test_capture_cli_appends_one_decision(self) -> None:
        output = self.tmp / "capture.csv"
        report = self.tmp / "capture.md"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.personal_decision_state_capture",
                "capture",
                "--decision-date",
                "2026-05-18",
                "--decision-scope",
                "ASSET",
                "--ticker",
                "MSFT",
                "--asset-name",
                "Microsoft Corp.",
                "--proposed-action",
                "WAIT_FOR_PRICE",
                "--human-decision",
                "DEFERRED",
                "--decision-status",
                "REVIEW_SCHEDULED",
                "--reasoning-3-sentences",
                "The candidate remains high quality. The current valuation does not justify adding this month. Review again after updated valuation and cash context are available.",
                "--dominant-uncertainty",
                "VALUATION",
                "--benchmark-alternative",
                "CASH",
                "--review-date",
                "2026-06-18",
                "--run-id",
                "2026-05-18-monthly",
                "--primary-report-path",
                "reports/2026-05-18/personal_monthly_decision_report.md",
                "--manifest-path",
                "data/processed/personal_run_manifest.json",
                "--source-snapshot-date",
                "2026-05-18",
                "--output",
                str(output),
                "--report",
                str(report),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("appended_decision_id=DECISION_20260518_0001", result.stdout)
        rows = self.read_csv(output)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["decision_id"], "DECISION_20260518_0001")
        self.assertEqual(rows[0]["proposed_action"], "WAIT_FOR_PRICE")
        self.assertIn("not order execution", report.read_text(encoding="utf-8"))

    def test_second_capture_appends_without_changing_existing_row(self) -> None:
        output = self.tmp / "capture.csv"
        report = self.tmp / "capture.md"
        self.append_capture(output, report)
        first_rows = self.read_csv(output)

        self.append_capture(output, report, ticker="AAPL", asset_name="Apple Inc.", proposed_action="NO_ACTION", human_decision="NO_ACTION", decision_status="CLOSED", review_date="")
        rows = self.read_csv(output)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], first_rows[0])
        self.assertEqual(rows[0]["decision_id"], "DECISION_20260518_0001")
        self.assertEqual(rows[1]["decision_id"], "DECISION_20260518_0002")
        self.assertEqual(rows[1]["ticker"], "AAPL")

    def test_duplicate_decision_id_fails_cleanly(self) -> None:
        output = self.tmp / "capture.csv"
        report = self.tmp / "capture.md"
        self.append_capture(output, report, decision_id="DECISION_20260518_0099")

        with self.assertRaisesRegex(ValueError, "duplicate decision_id"):
            self.append_capture(output, report, decision_id="DECISION_20260518_0099", ticker="AAPL")

    def test_capture_rejects_invalid_contract_enums(self) -> None:
        cases = [
            ("proposed_action", "TOP_UP"),
            ("human_decision", "WAIT"),
            ("dominant_uncertainty", "VALUATION_NOT_ATTRACTIVE"),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                output = self.tmp / f"{field}.csv"
                report = self.tmp / f"{field}.md"
                with self.assertRaisesRegex(ValueError, "INVALID_ENUM"):
                    self.append_capture(output, report, **{field: value})

    def test_capture_rejects_missing_required_fields(self) -> None:
        for field in [
            "reasoning_3_sentences",
            "proposed_action",
            "human_decision",
            "decision_status",
            "dominant_uncertainty",
            "benchmark_alternative",
        ]:
            with self.subTest(field=field):
                output = self.tmp / f"{field}.csv"
                report = self.tmp / f"{field}.md"
                with self.assertRaisesRegex(ValueError, f"MISSING_REQUIRED:{field}"):
                    self.append_capture(output, report, **{field: ""})

    def test_capture_preserves_conditional_review_date_rule(self) -> None:
        for action in ("HOLD_REVIEW", "WAIT_FOR_EVIDENCE", "WAIT_FOR_PRICE", "WAIT_FOR_REVIEW", "RESEARCH_MORE"):
            with self.subTest(action=action):
                output = self.tmp / f"{action}.csv"
                report = self.tmp / f"{action}.md"
                with self.assertRaisesRegex(ValueError, "MISSING_CONDITIONAL:review_date"):
                    self.append_capture(output, report, proposed_action=action, decision_status="OPEN", review_date="")
        with self.assertRaisesRegex(ValueError, "MISSING_CONDITIONAL:review_date"):
            self.append_capture(self.tmp / "status.csv", self.tmp / "status.md", proposed_action="NO_ACTION", decision_status="REVIEW_SCHEDULED", review_date="")

    def test_capture_rejects_absolute_local_stored_paths(self) -> None:
        absolute_path = str(Path.home() / "private_manifest.json")

        with self.assertRaisesRegex(ValueError, "repo-relative path"):
            self.append_capture(self.tmp / "capture.csv", self.tmp / "capture.md", manifest_path=absolute_path)

    def test_capture_rejects_private_raw_source_paths(self) -> None:
        with self.assertRaisesRegex(ValueError, "private raw"):
            self.append_capture(self.tmp / "capture.csv", self.tmp / "capture.md", source_paths="data/raw/private/traderepublic/Kontoauszug.pdf")

    def test_validate_journal_cli_fails_on_duplicate_decision_id(self) -> None:
        input_path = self.tmp / "dupe.csv"
        output_path = self.tmp / "dupe_out.csv"
        report_path = self.tmp / "dupe.md"
        row = self.base_row()
        row["decision_id"] = "DECISION_20260518_0001"
        self.write_csv(input_path, [row, row])

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.personal_decision_state_capture",
                "validate-journal",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
                "--report",
                str(report_path),
                "--report-date",
                "2026-05-18",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DUPLICATE_DECISION_ID", result.stderr + result.stdout)

    def test_no_broker_order_or_tax_fields_are_generated(self) -> None:
        output = self.tmp / "capture.csv"
        report = self.tmp / "capture.md"
        self.append_capture(output, report)

        with output.open("r", encoding="utf-8") as handle:
            header = handle.readline().strip().split(",")
        forbidden = {"order_id", "broker", "execution_id", "linked_transaction_id", "filled_price", "tax_lot", "realized_gain"}
        self.assertTrue(forbidden.isdisjoint(header))

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

    def test_hold_review_requires_review_date(self) -> None:
        row = self.base_row()
        row["proposed_action"] = "HOLD_REVIEW"
        row["decision_status"] = "OPEN"
        row["review_date"] = ""
        input_path = self.tmp / "input.csv"
        self.write_csv(input_path, [row])

        result = run_decision_state_capture(input_path=str(input_path), output=str(self.tmp / "out.csv"), report=str(self.tmp / "report.md"), report_date="2026-04-29")

        self.assertIn("MISSING_CONDITIONAL:review_date", result.invalid_rows[0]["validation_reasons"])

    def test_wait_actions_require_review_date(self) -> None:
        for action in ("WAIT_FOR_EVIDENCE", "WAIT_FOR_PRICE", "WAIT_FOR_REVIEW"):
            with self.subTest(action=action):
                row = self.base_row()
                row["proposed_action"] = action
                row["decision_status"] = "OPEN"
                row["review_date"] = ""
                input_path = self.tmp / f"{action}.csv"
                self.write_csv(input_path, [row])

                result = run_decision_state_capture(input_path=str(input_path), output=str(self.tmp / f"{action}_out.csv"), report=str(self.tmp / f"{action}.md"), report_date="2026-04-29")

                self.assertIn("MISSING_CONDITIONAL:review_date", result.invalid_rows[0]["validation_reasons"])

    def test_review_scheduled_status_requires_review_date(self) -> None:
        row = self.base_row()
        row["proposed_action"] = "NO_ACTION"
        row["decision_status"] = "REVIEW_SCHEDULED"
        row["review_date"] = ""
        input_path = self.tmp / "input.csv"
        self.write_csv(input_path, [row])

        result = run_decision_state_capture(input_path=str(input_path), output=str(self.tmp / "out.csv"), report=str(self.tmp / "report.md"), report_date="2026-04-29")

        self.assertIn("MISSING_CONDITIONAL:review_date", result.invalid_rows[0]["validation_reasons"])

    def test_missing_input_path_is_surfaced_in_report(self) -> None:
        missing_input = self.tmp / "missing.csv"
        report = self.tmp / "report.md"

        result = run_decision_state_capture(input_path=str(missing_input), output=str(self.tmp / "out.csv"), report=str(report), report_date="2026-04-29")

        self.assertEqual(result.rows, [])
        self.assertEqual(result.input_status, "MISSING_INPUT_PATH")
        self.assertIn("input_status: MISSING_INPUT_PATH", report.read_text(encoding="utf-8"))

    def test_unresolved_auto_system_references_are_surfaced(self) -> None:
        input_path = self.tmp / "input.csv"
        row = self.base_row()
        row["ticker"] = ""
        row["asset_name"] = ""
        self.write_csv(input_path, [row])

        result = run_decision_state_capture(input_path=str(input_path), output=str(self.tmp / "out.csv"), report=str(self.tmp / "report.md"), report_date="2026-04-29")

        written = self.read_csv(self.tmp / "out.csv")
        self.assertEqual(written[0]["run_id"], "MISSING_REFERENCE")
        self.assertEqual(written[0]["asset_id"], "UNKNOWN")
        self.assertTrue(result.missing_replay_references)
        self.assertTrue(result.unresolved_auto_system_fields)
        self.assertIn("asset_id", result.unresolved_auto_system_fields[0]["unresolved_auto_system_fields"])
        self.assertIn("ticker", result.unresolved_auto_system_fields[0]["unresolved_auto_system_fields"])
        self.assertIn("asset_name", result.unresolved_auto_system_fields[0]["unresolved_auto_system_fields"])
        self.assertIn("asset_type", result.unresolved_auto_system_fields[0]["unresolved_auto_system_fields"])
        self.assertIn("Missing Replay References", (self.tmp / "report.md").read_text(encoding="utf-8"))
        self.assertIn("Unresolved Auto/System Fields", (self.tmp / "report.md").read_text(encoding="utf-8"))

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
