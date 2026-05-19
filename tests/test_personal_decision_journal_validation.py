from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from src.personal_decision_journal_validation import QUEUE_FIELDS, VALIDATION_FIELDS, run_decision_journal_validation
from src.personal_decision_state_capture import FIELDS

ROOT = Path(__file__).resolve().parent.parent


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class DecisionJournalValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_decision_journal_validation"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.journal = self.tmp / "personal_decision_state_capture.csv"
        self.decision_quality_json = self.tmp / "decision_quality_state.json"
        self.decision_quality_csv = self.tmp / "decision_quality_state.csv"
        self.run_manifest = self.tmp / "personal_run_manifest.json"
        self.run_used_inputs = self.tmp / "personal_run_used_inputs.csv"
        self.validation_output = self.tmp / "decision_journal_validation.csv"
        self.queue_output = self.tmp / "decision_review_queue.csv"
        self.report = self.tmp / "decision_journal_validation_report.md"
        self.primary_report = self.tmp / "personal_monthly_decision_report.md"
        self.primary_report.write_text("# report\n", encoding="utf-8")
        self.run_manifest.write_text(
            json.dumps(
                {
                    "run_id": "2026-05-20-monthly",
                    "as_of_date": "2026-05-20",
                    "source_commit_sha": "abc123",
                    "executed_stage_order": ["decision_quality"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        write_csv(self.run_used_inputs, ["artifact_path", "status"], [{"artifact_path": self.journal.as_posix(), "status": "USED"}])
        self.write_decision_quality(review_required=False, as_of_date="2026-05-20", source_commit_sha="abc123", confidence="MEDIUM")
        self.write_journal([self.base_row()])

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def base_row(self, **overrides: str) -> dict[str, str]:
        row = {field: "" for field in FIELDS}
        row.update(
            {
                "decision_id": "DECISION_20260518_0001",
                "decision_date": "2026-05-18",
                "decision_scope": "ASSET",
                "asset_id": "MSFT",
                "ticker": "MSFT",
                "asset_name": "Microsoft Corp.",
                "asset_type": "STOCK",
                "proposed_action": "WAIT_FOR_PRICE",
                "human_decision": "DEFERRED",
                "decision_status": "REVIEW_SCHEDULED",
                "reasoning_3_sentences": "The candidate remains high quality. Valuation is not attractive enough. Review after updated valuation and cash context.",
                "dominant_uncertainty": "VALUATION",
                "benchmark_alternative": "CASH",
                "benchmark_ref_or_label": "CASH",
                "review_date": "2026-05-20",
                "created_at": "2026-05-18T00:00:00",
                "run_id": "2026-05-20-monthly",
                "manifest_path": self.run_manifest.relative_to(ROOT).as_posix(),
                "primary_report_path": self.primary_report.relative_to(ROOT).as_posix(),
                "source_snapshot_date": "2026-05-20",
                "accounting_basis": "SNAPSHOT_ONLY",
                "policy_ref": "docs/architecture/COMPOUND_INCOME_OS_SYSTEM_DEFINITION.md",
                "operator_state": "NORMAL",
                "decision_pressure": "NORMAL",
                "cash_context": "AVAILABLE_CASH",
            }
        )
        row.update(overrides)
        return row

    def write_journal(self, rows: list[dict[str, str]]) -> None:
        write_csv(self.journal, FIELDS, rows)

    def write_decision_quality(
        self,
        *,
        review_required: bool,
        as_of_date: str,
        source_commit_sha: str,
        confidence: str,
    ) -> None:
        state = {
            "run_id": "2026-05-20-monthly",
            "as_of_date": as_of_date,
            "generated_at": "2026-05-20T12:00:00Z",
            "source_commit_sha": source_commit_sha,
            "contract_version": "v1-design",
            "decision_confidence_level": confidence,
            "review_required": review_required,
            "review_reason_codes": ["EVIDENCE_MISSING"] if review_required else [],
        }
        self.decision_quality_json.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def run_validation(self, **overrides):
        params = {
            "journal": str(self.journal),
            "decision_quality_csv": str(self.decision_quality_csv),
            "decision_quality_json": str(self.decision_quality_json),
            "run_manifest": str(self.run_manifest),
            "run_used_inputs": str(self.run_used_inputs),
            "validation_output": str(self.validation_output),
            "queue_output": str(self.queue_output),
            "report": str(self.report),
            "as_of_date": "2026-05-20",
        }
        params.update(overrides)
        return run_decision_journal_validation(**params)

    def test_missing_journal_creates_review_queue(self) -> None:
        self.journal.unlink()
        result = self.run_validation()
        self.assertEqual(result.summary["validation_status"], "REVIEW")
        self.assertIn("DECISION_JOURNAL_MISSING", result.validation_rows[0]["reason_code"])
        self.assertEqual(result.queue_rows[0]["priority"], "BLOCKER")

    def test_empty_journal_is_review_not_ok(self) -> None:
        self.write_journal([])
        result = self.run_validation()
        self.assertEqual(result.summary["validation_status"], "REVIEW")
        self.assertIn("DECISION_JOURNAL_EMPTY", {row["reason_code"] for row in result.validation_rows})
        self.assertIn("DECISION_JOURNAL_EMPTY", result.queue_rows[0]["reason_codes"])

    def test_missing_required_field_is_visible(self) -> None:
        self.write_journal([self.base_row(proposed_action="")])
        result = self.run_validation()
        self.assertIn("DECISION_FIELD_MISSING", {row["reason_code"] for row in result.validation_rows})
        self.assertIn("proposed_action", {row["field_name"] for row in result.validation_rows})

    def test_review_date_due_creates_high_queue_item(self) -> None:
        result = self.run_validation()
        due_items = [row for row in result.queue_rows if "REVIEW_DATE_DUE" in row["reason_codes"]]
        self.assertEqual(due_items[0]["priority"], "HIGH")
        self.assertEqual(due_items[0]["days_overdue"], "0")

    def test_missing_review_date_for_active_decision_creates_queue_item(self) -> None:
        self.write_journal([self.base_row(review_date="", proposed_action="WAIT_FOR_REVIEW", decision_status="OPEN")])
        result = self.run_validation()
        self.assertTrue(any("REVIEW_DATE_MISSING" in row["reason_codes"] for row in result.queue_rows))

    def test_decision_quality_missing_is_not_available_without_crash(self) -> None:
        self.decision_quality_json.unlink()
        result = self.run_validation()
        self.assertEqual(result.summary["decision_quality_status"], "NOT_AVAILABLE")
        self.assertTrue(self.validation_output.exists())
        self.assertTrue(self.queue_output.exists())

    def test_decision_quality_review_required_creates_queue_item(self) -> None:
        self.write_decision_quality(review_required=True, as_of_date="2026-05-20", source_commit_sha="abc123", confidence="REVIEW")
        result = self.run_validation()
        self.assertTrue(any("DECISION_QUALITY_REVIEW_REQUIRED" in row["reason_codes"] for row in result.queue_rows))

    def test_stale_decision_quality_creates_queue_item(self) -> None:
        self.write_decision_quality(review_required=False, as_of_date="2026-05-18", source_commit_sha="abc123", confidence="MEDIUM")
        result = self.run_validation()
        self.assertTrue(any("DECISION_QUALITY_STALE" in row["reason_codes"] for row in result.queue_rows))

    def test_source_commit_mismatch_creates_queue_item(self) -> None:
        self.write_decision_quality(review_required=False, as_of_date="2026-05-20", source_commit_sha="different", confidence="MEDIUM")
        result = self.run_validation()
        self.assertTrue(any("DECISION_QUALITY_LINEAGE_MISMATCH" in row["reason_codes"] for row in result.queue_rows))

    def test_report_uses_process_confidence_wording_and_non_scope(self) -> None:
        self.run_validation()
        text = self.report.read_text(encoding="utf-8")
        self.assertIn("Process/Review Confidence", text)
        self.assertIn("not investment confidence", text)
        self.assertIn("no broker/order/trading", text)
        self.assertIn("no simulation/backtesting", text)

    def test_csv_serialization_and_no_private_raw_paths(self) -> None:
        private_journal = "data/raw/private/decision.csv"
        result = self.run_validation(journal=private_journal)
        validation_text = self.validation_output.read_text(encoding="utf-8")
        queue_text = self.queue_output.read_text(encoding="utf-8")
        self.assertEqual(read_csv(self.validation_output)[0].keys(), set(VALIDATION_FIELDS))
        self.assertEqual(read_csv(self.queue_output)[0].keys(), set(QUEUE_FIELDS))
        self.assertIn("EXTERNAL_PATH_REDACTED:decision_journal", validation_text + queue_text)
        self.assertNotIn(private_journal, validation_text + queue_text)
        self.assertIn("DECISION_JOURNAL_MISSING", result.queue_rows[0]["reason_codes"])

    def test_cli_writes_outputs_to_temp_paths(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.personal_decision_journal_validation",
                "--journal",
                str(self.journal),
                "--decision-quality-json",
                str(self.decision_quality_json),
                "--run-manifest",
                str(self.run_manifest),
                "--run-used-inputs",
                str(self.run_used_inputs),
                "--validation-output",
                str(self.validation_output),
                "--queue-output",
                str(self.queue_output),
                "--report",
                str(self.report),
                "--as-of-date",
                "2026-05-20",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(self.validation_output.exists())
        self.assertTrue(self.queue_output.exists())
        self.assertTrue(self.report.exists())


if __name__ == "__main__":
    unittest.main()
