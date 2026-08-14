from __future__ import annotations

import csv
import inspect
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid

from src.canonical_record import GENESIS_PREVIOUS_RECORD_HASH, verify_hash_chain
from src.personal_decision_trigger_capture import lock_trigger_proposals, write_trigger_proposals
from src.personal_trigger_resolution import (
    FINAL_RESOLUTION_STATUSES,
    append_trigger_resolution,
    build_due_review_rows,
    load_resolution_ledger,
    scan_due_triggers,
)


class PersonalTriggerResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_trigger_resolution_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.journal = self.tmp / "decisions.csv"
        self.proposals = self.tmp / "proposals.json"
        self.triggers = self.tmp / "triggers.csv"
        self.resolutions = self.tmp / "resolutions.csv"
        self.due = self.tmp / "due.csv"
        with self.journal.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["decision_id", "decision_date"])
            writer.writeheader()
            writer.writerow({"decision_id": "DECISION_20260814_0001", "decision_date": "2026-08-14"})
        rows = [
            self.proposal("TRIGGER_001", "2026-11-15", "2026-12-15"),
            self.proposal("TRIGGER_002", "2026-12-20", "2026-12-31"),
        ]
        write_trigger_proposals(rows, decision_journal=str(self.journal), output=str(self.proposals))
        lock_trigger_proposals(
            decision_id="DECISION_20260814_0001",
            trigger_ids=["TRIGGER_001", "TRIGGER_002"],
            locked_at="2026-08-14T12:00:00Z",
            proposal_path=str(self.proposals),
            decision_journal=str(self.journal),
            ledger=str(self.triggers),
        )

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    @staticmethod
    def proposal(trigger_id: str, expected: str, deadline: str) -> dict[str, object]:
        return {
            "trigger_id": trigger_id,
            "decision_id": "DECISION_20260814_0001",
            "claim": f"Forward metric claim {trigger_id}",
            "claim_type": "FUNDAMENTAL_METRIC",
            "material": True,
            "decision_relevant": True,
            "future_facing": True,
            "falsifiable": True,
            "deterministically_resolvable": True,
            "tautological": False,
            "already_known": False,
            "purely_narrative_without_resolution_rule": False,
            "metric_name": "organic_revenue_growth_yoy",
            "metric_definition_version": "1",
            "source_document_type": "annual_report",
            "source_section": "Financial Review",
            "line_item": "Organic revenue growth (%)",
            "fallback_computation": "NOT_APPLICABLE",
            "tolerance": "0.001",
            "ambiguity_rule": "UNRESOLVABLE_DEFINITION_IF_ISSUER_DEFINITION_CHANGES",
            "operator": ">=",
            "threshold": "0.05",
            "unit": "ratio",
            "probability_holds": "0.70",
            "expected_resolution_date": expected,
            "resolution_deadline": deadline,
            "policy_version": "FORWARD_VALIDATION_V1",
            "created_at": "2026-08-14T10:00:00Z",
            "source_paths": "reports/2026-08-14/research.md",
            "supersedes_trigger_id": "",
        }

    def confirm(self, trigger_id: str = "TRIGGER_001", **overrides: str) -> dict[str, str]:
        values = {
            "trigger_id": trigger_id,
            "resolution_status": "RESOLVED_TRUE",
            "resolved_value": "0.061",
            "resolution_date": "2026-12-16",
            "resolution_source": "issuer_annual_report",
            "resolution_evidence_path": "evidence/issuer/annual-report.pdf",
            "resolution_reason": "Locked line item met the threshold including tolerance.",
            "created_at": "2026-12-16T12:00:00Z",
            "trigger_ledger": str(self.triggers),
            "resolution_ledger": str(self.resolutions),
        }
        values.update(overrides)
        return append_trigger_resolution(**values)

    def test_human_confirmation_appends_hash_chained_resolution(self) -> None:
        row = self.confirm()
        loaded = load_resolution_ledger(str(self.resolutions))
        self.assertEqual(row, loaded[0])
        self.assertEqual(row["previous_record_hash"], GENESIS_PREVIOUS_RECORD_HASH)
        self.assertEqual(verify_hash_chain(loaded), row["record_hash"])

    def test_resolution_before_trigger_lock_fails_without_writing(self) -> None:
        with self.assertRaisesRegex(ValueError, "before trigger locked_at"):
            self.confirm(
                resolution_date="2026-08-13",
                created_at="2026-08-13T12:00:00Z",
            )
        self.assertFalse(self.resolutions.exists())

    def test_duplicate_resolution_fails_and_preserves_ledger(self) -> None:
        self.confirm()
        before = self.resolutions.read_bytes()
        with self.assertRaisesRegex(ValueError, "duplicate trigger resolution"):
            self.confirm(resolution_status="RESOLVED_FALSE", resolved_value="0.02")
        self.assertEqual(before, self.resolutions.read_bytes())

    def test_overdue_is_derived_and_cannot_be_final(self) -> None:
        self.assertNotIn("OVERDUE", FINAL_RESOLUTION_STATUSES)
        with self.assertRaisesRegex(ValueError, "OVERDUE is derived"):
            self.confirm(resolution_status="OVERDUE")
        self.assertFalse(self.resolutions.exists())

    def test_unresolvable_states_require_not_applicable_value(self) -> None:
        row = self.confirm(
            resolution_status="UNRESOLVABLE_DEFINITION",
            resolved_value="NOT_APPLICABLE",
            resolution_evidence_path="NOT_APPLICABLE",
            resolution_reason="Issuer changed the locked metric definition.",
        )
        self.assertEqual(row["resolution_status"], "UNRESOLVABLE_DEFINITION")
        with self.assertRaisesRegex(ValueError, "resolved_value=NOT_APPLICABLE"):
            self.confirm(
                trigger_id="TRIGGER_002",
                resolution_status="UNRESOLVABLE_CORPORATE",
                resolved_value="0",
            )

    def test_due_scan_distinguishes_due_and_overdue_without_resolving(self) -> None:
        scan_due_triggers(
            as_of_date="2026-12-20",
            trigger_ledger=str(self.triggers),
            resolution_ledger=str(self.resolutions),
            output=str(self.due),
        )
        with self.due.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([row["trigger_id"] for row in rows], ["TRIGGER_001", "TRIGGER_002"])
        self.assertEqual(rows[0]["review_status"], "OVERDUE")
        self.assertEqual(rows[0]["days_overdue"], "5")
        self.assertEqual(rows[1]["review_status"], "DUE")
        self.assertFalse(self.resolutions.exists())

    def test_resolved_trigger_is_removed_from_due_queue(self) -> None:
        self.confirm()
        scan_due_triggers(
            as_of_date="2027-01-01",
            trigger_ledger=str(self.triggers),
            resolution_ledger=str(self.resolutions),
            output=str(self.due),
        )
        with self.due.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([row["trigger_id"] for row in rows], ["TRIGGER_002"])

    def test_same_due_scan_inputs_produce_identical_output(self) -> None:
        kwargs = {
            "as_of_date": "2026-12-20",
            "trigger_ledger": str(self.triggers),
            "resolution_ledger": str(self.resolutions),
            "output": str(self.due),
        }
        scan_due_triggers(**kwargs)
        first = self.due.read_bytes()
        scan_due_triggers(**kwargs)
        self.assertEqual(first, self.due.read_bytes())

    def test_due_scan_without_any_locked_trigger_writes_empty_header_only_queue(self) -> None:
        missing_triggers = self.tmp / "not-created-triggers.csv"
        scan_due_triggers(
            as_of_date="2026-08-14",
            trigger_ledger=str(missing_triggers),
            resolution_ledger=str(self.resolutions),
            output=str(self.due),
        )
        with self.due.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(rows, [])
        self.assertIn("review_status", self.due.read_text(encoding="utf-8"))

    def test_sold_position_cannot_censor_open_trigger(self) -> None:
        parameters = inspect.signature(build_due_review_rows).parameters
        self.assertNotIn("positions", parameters)
        scan_due_triggers(
            as_of_date="2027-01-01",
            trigger_ledger=str(self.triggers),
            resolution_ledger=str(self.resolutions),
            output=str(self.due),
        )
        self.assertIn("TRIGGER_001", self.due.read_text(encoding="utf-8"))
        self.assertIn("TRIGGER_002", self.due.read_text(encoding="utf-8"))

    def test_binary_resolution_requires_repo_relative_non_private_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "require a resolution_evidence_path"):
            self.confirm(resolution_evidence_path="NOT_APPLICABLE")
        with self.assertRaisesRegex(ValueError, "private raw or broker"):
            self.confirm(resolution_evidence_path="data/raw/private/report.pdf")
        self.assertFalse(self.resolutions.exists())

    def test_cli_help_preserves_human_confirmation_boundary_and_no_llm_dependency(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "src.personal_trigger_resolution", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("human-confirmed", completed.stdout)
        source = Path("src/personal_trigger_resolution.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("openai", source)
        self.assertNotIn("anthropic", source)
        self.assertNotIn("broker", source)


if __name__ == "__main__":
    unittest.main()
