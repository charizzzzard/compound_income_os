from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid

from src.canonical_record import GENESIS_PREVIOUS_RECORD_HASH, HASH_SCHEMA_VERSION
from src.forward_validation_audit import (
    ANCHOR_FIELDS,
    TRIGGER_LEDGER_NAME,
    append_ledger_anchor,
    load_anchor_index,
    verify_forward_validation_ledgers,
)
from src.personal_decision_trigger_capture import lock_trigger_proposals, write_trigger_proposals


class ForwardValidationAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_forward_validation_audit_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.journal = self.tmp / "decisions.csv"
        self.proposals = self.tmp / "proposals.json"
        self.triggers = self.tmp / "triggers.csv"
        self.resolutions = self.tmp / "resolutions.csv"
        self.anchors = self.tmp / "ledger_anchors.jsonl"
        with self.journal.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["decision_id", "decision_date"])
            writer.writeheader()
            writer.writerow({"decision_id": "DECISION_20260814_0001", "decision_date": "2026-08-14"})

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    @staticmethod
    def proposal(trigger_id: str, *, supersedes: str = "", created_at: str = "2026-08-14T10:00:00Z") -> dict[str, object]:
        return {
            "trigger_id": trigger_id,
            "decision_id": "DECISION_20260814_0001",
            "claim": f"Forward claim {trigger_id}",
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
            "expected_resolution_date": "2026-11-15",
            "resolution_deadline": "2026-12-15",
            "policy_version": "FORWARD_VALIDATION_V1",
            "created_at": created_at,
            "source_paths": "reports/research.md",
            "supersedes_trigger_id": supersedes,
        }

    def create_trigger_ledger(self) -> None:
        write_trigger_proposals(
            [self.proposal("TRIGGER_001"), self.proposal("TRIGGER_002")],
            decision_journal=str(self.journal),
            output=str(self.proposals),
        )
        lock_trigger_proposals(
            decision_id="DECISION_20260814_0001",
            trigger_ids=["TRIGGER_001", "TRIGGER_002"],
            locked_at="2026-08-14T12:00:00Z",
            proposal_path=str(self.proposals),
            decision_journal=str(self.journal),
            ledger=str(self.triggers),
        )

    def append_trigger_anchor(self) -> tuple[bool, dict[str, object]]:
        return append_ledger_anchor(
            ledger_name=TRIGGER_LEDGER_NAME,
            anchor_date="2026-08-14",
            created_at="2026-08-14T18:00:00Z",
            git_head="a" * 40,
            trigger_ledger=str(self.triggers),
            resolution_ledger=str(self.resolutions),
            anchor_index=str(self.anchors),
        )

    def test_empty_ledgers_verify_without_inventing_rows(self) -> None:
        result = verify_forward_validation_ledgers(
            trigger_ledger=str(self.triggers),
            resolution_ledger=str(self.resolutions),
            anchor_index=str(self.anchors),
        )
        self.assertEqual(result["verification_status"], "PASS")
        self.assertEqual(result["tamper_evidence"], "TAMPER_EVIDENT_NOT_TAMPER_PROOF")
        self.assertEqual(result["ledgers"][TRIGGER_LEDGER_NAME]["row_count"], 0)
        self.assertEqual(result["ledgers"][TRIGGER_LEDGER_NAME]["head_hash"], GENESIS_PREVIOUS_RECORD_HASH)
        self.assertEqual(result["ledgers"][TRIGGER_LEDGER_NAME]["anchor_status"], "UNANCHORED")

    def test_same_ledger_head_anchor_is_idempotent_and_content_free(self) -> None:
        appended, first = self.append_trigger_anchor()
        first_bytes = self.anchors.read_bytes()
        appended_again, second = append_ledger_anchor(
            ledger_name=TRIGGER_LEDGER_NAME,
            anchor_date="2026-08-15",
            created_at="2026-08-15T18:00:00Z",
            git_head="b" * 40,
            trigger_ledger=str(self.triggers),
            resolution_ledger=str(self.resolutions),
            anchor_index=str(self.anchors),
        )
        self.assertTrue(appended)
        self.assertFalse(appended_again)
        self.assertEqual(first, second)
        self.assertEqual(first_bytes, self.anchors.read_bytes())
        rows = load_anchor_index(str(self.anchors))
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0]), ANCHOR_FIELDS)
        self.assertEqual(rows[0]["hash_schema_version"], HASH_SCHEMA_VERSION)
        serialized = json.dumps(rows[0]).lower()
        self.assertNotIn("decision_id", serialized)
        self.assertNotIn("claim", serialized)

    def test_anchor_path_cannot_use_git_ignored_processed_directory(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be stored under git-ignored data/processed"):
            append_ledger_anchor(
                ledger_name=TRIGGER_LEDGER_NAME,
                anchor_date="2026-08-14",
                created_at="2026-08-14T18:00:00Z",
                git_head="a" * 40,
                trigger_ledger=str(self.triggers),
                resolution_ledger=str(self.resolutions),
                anchor_index="data/processed/ledger_anchors.jsonl",
            )

    def test_hash_tampering_fails_verification(self) -> None:
        self.create_trigger_ledger()
        self.append_trigger_anchor()
        with self.triggers.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
            fields = list(rows[0])
        rows[0]["probability_holds"] = "0.71"
        with self.triggers.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, "record_hash mismatch"):
            verify_forward_validation_ledgers(
                trigger_ledger=str(self.triggers),
                resolution_ledger=str(self.resolutions),
                anchor_index=str(self.anchors),
            )

    def test_valid_append_after_anchor_is_reported_as_ledger_advanced(self) -> None:
        self.create_trigger_ledger()
        self.append_trigger_anchor()
        write_trigger_proposals(
            [self.proposal("TRIGGER_003", supersedes="TRIGGER_001", created_at="2026-08-15T10:00:00Z")],
            decision_journal=str(self.journal),
            output=str(self.proposals),
        )
        lock_trigger_proposals(
            decision_id="DECISION_20260814_0001",
            trigger_ids=["TRIGGER_003"],
            locked_at="2026-08-15T12:00:00Z",
            proposal_path=str(self.proposals),
            decision_journal=str(self.journal),
            ledger=str(self.triggers),
        )
        result = verify_forward_validation_ledgers(
            trigger_ledger=str(self.triggers),
            resolution_ledger=str(self.resolutions),
            anchor_index=str(self.anchors),
        )
        self.assertEqual(
            result["ledgers"][TRIGGER_LEDGER_NAME]["anchor_status"],
            "LEDGER_ADVANCED_SINCE_ANCHOR",
        )

    def test_anchor_index_rejects_personal_or_unknown_fields(self) -> None:
        row = {
            "anchor_date": "2026-08-14",
            "ledger_name": TRIGGER_LEDGER_NAME,
            "row_count": 0,
            "head_hash": GENESIS_PREVIOUS_RECORD_HASH,
            "hash_schema_version": HASH_SCHEMA_VERSION,
            "git_head": "a" * 40,
            "created_at": "2026-08-14T18:00:00Z",
            "decision_id": "MUST_NOT_BE_STORED",
        }
        self.anchors.write_text(json.dumps(row) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "field mismatch"):
            load_anchor_index(str(self.anchors))

    def test_cli_verification_is_read_only_and_no_signed_tag_is_created(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.forward_validation_audit",
                "verify",
                "--trigger-ledger",
                str(self.triggers),
                "--resolution-ledger",
                str(self.resolutions),
                "--anchor-index",
                str(self.anchors),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["verification_status"], "PASS")
        source = Path("src/forward_validation_audit.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("git tag", source)
        self.assertNotIn("gpg", source)


if __name__ == "__main__":
    unittest.main()
