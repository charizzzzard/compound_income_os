from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid


class ForwardValidationJobsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_forward_validation_jobs_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.journal = self.tmp / "decisions.csv"
        self.triggers = self.tmp / "missing-triggers.csv"
        self.resolutions = self.tmp / "missing-resolutions.csv"
        self.due = self.tmp / "due.csv"
        self.summary = self.tmp / "summary.json"
        self.report = self.tmp / "report.md"
        with self.journal.open("w", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=["decision_id"]).writeheader()
        self.powershell = shutil.which("powershell") or shutil.which("powershell.exe")

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def run_job(self, job: str) -> subprocess.CompletedProcess[str]:
        if not self.powershell:
            self.skipTest("PowerShell is not available")
        command = [
            self.powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/run_forward_validation_jobs.ps1",
            "-Job",
            job,
            "-AsOfDate",
            "2026-08-14",
            "-PythonExecutable",
            sys.executable,
            "-DecisionJournal",
            str(self.journal),
            "-TriggerLedger",
            str(self.triggers),
            "-ResolutionLedger",
            str(self.resolutions),
            "-DueOutput",
            str(self.due),
            "-SummaryOutput",
            str(self.summary),
            "-ReportOutput",
            str(self.report),
        ]
        return subprocess.run(command, check=False, capture_output=True, text=True)

    def test_weekly_job_is_idempotent_header_only_due_scan(self) -> None:
        first = self.run_job("weekly")
        self.assertEqual(first.returncode, 0, first.stderr)
        first_bytes = self.due.read_bytes()
        second = self.run_job("weekly")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first_bytes, self.due.read_bytes())
        with self.due.open("r", encoding="utf-8", newline="") as handle:
            self.assertEqual(list(csv.DictReader(handle)), [])
        self.assertFalse(self.resolutions.exists())

    def test_quarterly_job_is_idempotent_and_descriptive_only(self) -> None:
        first = self.run_job("quarterly")
        self.assertEqual(first.returncode, 0, first.stderr)
        first_summary = self.summary.read_bytes()
        first_report = self.report.read_bytes()
        second = self.run_job("quarterly")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first_summary, self.summary.read_bytes())
        self.assertEqual(first_report, self.report.read_bytes())
        result = json.loads(self.summary.read_text(encoding="utf-8"))
        self.assertEqual(result["operational_forward_validation_status"], "READY_FOR_FIRST_REAL_DECISION")
        self.assertFalse(result["confirmatory_registration_enabled"])
        self.assertFalse(self.resolutions.exists())

    def test_wrapper_does_not_register_scheduler_or_call_human_actions(self) -> None:
        source = Path("scripts/run_forward_validation_jobs.ps1").read_text(encoding="utf-8").lower()
        self.assertIn("scan-due", source)
        self.assertIn("personal_forward_validation", source)
        for forbidden in ["new-scheduledtask", "register-scheduledtask", " trigger_id", " confirm", " lock", " anchor"]:
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
