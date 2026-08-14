from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid

from src.canonical_record import (
    GENESIS_PREVIOUS_RECORD_HASH,
    HASH_SCHEMA_VERSION,
    build_hashed_record,
    calculate_record_hash,
    canonical_record_bytes,
    verify_hash_chain,
)
from src.personal_decision_trigger_capture import (
    DECIMAL_FIELDS,
    FIELDS,
    active_trigger_rows,
    load_trigger_ledger,
    lock_trigger_proposals,
    normalize_trigger_proposal,
    write_trigger_proposals,
)


class PersonalDecisionTriggerCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_trigger_capture_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.journal = self.tmp / "decisions.csv"
        self.proposals = self.tmp / "proposals.json"
        self.ledger = self.tmp / "triggers.csv"
        with self.journal.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["decision_id", "decision_date"])
            writer.writeheader()
            writer.writerow({"decision_id": "DECISION_20260814_0001", "decision_date": "2026-08-14"})

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def proposal(self, trigger_id: str, **overrides: object) -> dict[str, object]:
        row: dict[str, object] = {
            "trigger_id": trigger_id,
            "decision_id": "DECISION_20260814_0001",
            "claim": "Reported organic revenue growth will be at least five percent.",
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
            "tolerance": "0.0010",
            "ambiguity_rule": "UNRESOLVABLE_DEFINITION_IF_ISSUER_DEFINITION_CHANGES",
            "operator": ">=",
            "threshold": "0.0500",
            "unit": "ratio",
            "probability_holds": "0.70",
            "expected_resolution_date": "2026-11-15",
            "resolution_deadline": "2026-12-15",
            "policy_version": "FORWARD_VALIDATION_V1",
            "created_at": "2026-08-14T10:00:00Z",
            "source_paths": "reports/2026-08-14/research.md",
            "supersedes_trigger_id": "",
        }
        row.update(overrides)
        return row

    def prepare_proposals(self, rows: list[dict[str, object]]) -> None:
        write_trigger_proposals(
            rows,
            decision_journal=str(self.journal),
            output=str(self.proposals),
        )

    def lock(self, trigger_ids: list[str], **overrides: str):
        values = {
            "decision_id": "DECISION_20260814_0001",
            "trigger_ids": trigger_ids,
            "locked_at": "2026-08-14T12:00:00Z",
            "proposal_path": str(self.proposals),
            "decision_journal": str(self.journal),
            "ledger": str(self.ledger),
        }
        values.update(overrides)
        return lock_trigger_proposals(**values)

    def test_proposal_artifact_is_replaceable_non_canonical_and_deterministic(self) -> None:
        rows = [self.proposal("TRIGGER_002"), self.proposal("TRIGGER_001")]
        self.prepare_proposals(rows)
        first = self.proposals.read_bytes()
        artifact = json.loads(first)
        self.assertEqual(artifact["artifact_status"], "NON_CANONICAL_REPLACEABLE_PROPOSAL")
        self.assertEqual([row["trigger_id"] for row in artifact["proposals"]], ["TRIGGER_001", "TRIGGER_002"])

        self.prepare_proposals(list(reversed(rows)))
        self.assertEqual(first, self.proposals.read_bytes())

    def test_decision_id_must_exist(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not exist"):
            self.prepare_proposals([self.proposal("TRIGGER_001", decision_id="DECISION_MISSING")])

    def test_human_lock_requires_two_to_five_triggers_and_preserves_existing_rows(self) -> None:
        self.prepare_proposals([self.proposal("TRIGGER_001"), self.proposal("TRIGGER_002")])
        appended = self.lock(["TRIGGER_001", "TRIGGER_002"])
        first_bytes = self.ledger.read_bytes()

        self.assertEqual(len(appended), 2)
        rows = load_trigger_ledger(str(self.ledger))
        self.assertEqual(len(active_trigger_rows(rows, "DECISION_20260814_0001")), 2)
        self.assertEqual(rows[0]["previous_record_hash"], GENESIS_PREVIOUS_RECORD_HASH)
        self.assertEqual(rows[1]["previous_record_hash"], rows[0]["record_hash"])
        self.assertEqual(verify_hash_chain(rows, decimal_fields=DECIMAL_FIELDS), rows[-1]["record_hash"])

        with self.assertRaisesRegex(ValueError, "duplicate trigger_id"):
            self.lock(["TRIGGER_001"])
        self.assertEqual(first_bytes, self.ledger.read_bytes())

    def test_one_trigger_initial_lock_fails_without_writing(self) -> None:
        self.prepare_proposals([self.proposal("TRIGGER_001")])
        with self.assertRaisesRegex(ValueError, "2-5 active triggers"):
            self.lock(["TRIGGER_001"])
        self.assertFalse(self.ledger.exists())

    def test_more_than_five_active_triggers_fail(self) -> None:
        proposals = [self.proposal(f"TRIGGER_{index:03d}") for index in range(1, 7)]
        self.prepare_proposals(proposals)
        with self.assertRaisesRegex(ValueError, "2-5 active triggers"):
            self.lock([row["trigger_id"] for row in proposals])
        self.assertFalse(self.ledger.exists())

    def test_superseding_record_retains_history_without_increasing_active_count(self) -> None:
        initial = [self.proposal("TRIGGER_001"), self.proposal("TRIGGER_002")]
        self.prepare_proposals(initial)
        self.lock(["TRIGGER_001", "TRIGGER_002"])
        before = load_trigger_ledger(str(self.ledger))

        correction = self.proposal(
            "TRIGGER_003",
            supersedes_trigger_id="TRIGGER_001",
            claim="Corrected locked metric definition remains a forward claim.",
        )
        self.prepare_proposals([correction])
        self.lock(["TRIGGER_003"])
        after = load_trigger_ledger(str(self.ledger))

        self.assertEqual(after[:2], before)
        self.assertEqual(len(after), 3)
        self.assertEqual(len(active_trigger_rows(after, "DECISION_20260814_0001")), 2)
        self.assertEqual(after[-1]["supersedes_trigger_id"], "TRIGGER_001")

    def test_invalid_probability_operator_flags_and_dates_fail(self) -> None:
        invalid_cases = [
            ("probability_holds", "1.01", "between 0 and 1"),
            ("probability_holds", -0.1, "decimal string"),
            ("operator", "~=", "operator must be"),
            ("falsifiable", False, "falsifiable must be true"),
            ("tautological", True, "tautological must be false"),
            ("expected_resolution_date", "2026-08-14", "after created_at"),
            ("resolution_deadline", "2026-10-01", "on or after"),
        ]
        for field, value, message in invalid_cases:
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(ValueError, message):
                    self.prepare_proposals([self.proposal("TRIGGER_001", **{field: value})])

    def test_resolution_date_must_be_after_human_lock(self) -> None:
        self.prepare_proposals(
            [
                self.proposal("TRIGGER_001", expected_resolution_date="2026-08-15", resolution_deadline="2026-08-15"),
                self.proposal("TRIGGER_002"),
            ]
        )
        with self.assertRaisesRegex(ValueError, "after locked_at"):
            self.lock(["TRIGGER_001", "TRIGGER_002"], locked_at="2026-08-15T08:00:00Z")
        self.assertFalse(self.ledger.exists())

    def test_hash_is_order_line_ending_utf8_and_decimal_stable(self) -> None:
        base = {
            "trigger_id": "TRIGGER_HASH",
            "claim": "Umlaut ä\r\nnext line",
            "threshold": "0.0500",
            "tolerance": "0.0010",
            "probability_holds": "0.700",
            "hash_schema_version": HASH_SCHEMA_VERSION,
            "previous_record_hash": GENESIS_PREVIOUS_RECORD_HASH,
        }
        reordered = {
            "previous_record_hash": GENESIS_PREVIOUS_RECORD_HASH,
            "hash_schema_version": HASH_SCHEMA_VERSION,
            "probability_holds": "0.7",
            "tolerance": "0.001",
            "threshold": "0.05",
            "claim": "Umlaut ä\nnext line",
            "trigger_id": "TRIGGER_HASH",
        }
        self.assertEqual(
            calculate_record_hash(base, decimal_fields=DECIMAL_FIELDS),
            calculate_record_hash(reordered, decimal_fields=DECIMAL_FIELDS),
        )
        self.assertIn(b"\\u00e4", canonical_record_bytes(base, decimal_fields=DECIMAL_FIELDS))

    def test_hash_is_stable_across_csv_roundtrip_and_schema_is_explicit(self) -> None:
        record = build_hashed_record(
            {
                "trigger_id": "TRIGGER_HASH",
                "threshold": "0.0500",
                "tolerance": "0.0010",
                "probability_holds": "0.700",
            },
            previous_record_hash=GENESIS_PREVIOUS_RECORD_HASH,
            decimal_fields=DECIMAL_FIELDS,
        )
        csv_path = self.tmp / "roundtrip.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(record), lineterminator="\n")
            writer.writeheader()
            writer.writerow(record)
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            loaded = next(csv.DictReader(handle))
        self.assertEqual(loaded["hash_schema_version"], HASH_SCHEMA_VERSION)
        self.assertEqual(calculate_record_hash(loaded, decimal_fields=DECIMAL_FIELDS), record["record_hash"])

    def test_no_broker_order_fields_or_runtime_llm_dependency(self) -> None:
        forbidden = {"broker", "order_id", "execution_id", "filled_price", "transaction_id"}
        self.assertTrue(forbidden.isdisjoint(FIELDS))
        source = Path("src/personal_decision_trigger_capture.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("openai", source)
        self.assertNotIn("anthropic", source)

    def test_cli_help_describes_human_boundary(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "src.personal_decision_trigger_capture", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("human-lock", completed.stdout)
        self.assertIn("No LLM", completed.stdout)


if __name__ == "__main__":
    unittest.main()
