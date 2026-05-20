from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

from src.dashboard_operator_summary import (
    build_dashboard_operator_summary,
    run_dashboard_operator_summary,
)
from src.personal_decision_journal_validation import QUEUE_FIELDS, VALIDATION_FIELDS


class DashboardOperatorSummaryTests(unittest.TestCase):
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

    def _write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _write_manifest(self, path: Path, *, selected_stages: list[str] | None = None) -> None:
        path.write_text(
            json.dumps(
                {
                    "as_of_date": "2026-05-19",
                    "run_id": "unit-run",
                    "selected_stages": selected_stages or [],
                    "source_commit_sha": "abc123",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_decision_quality(self, path: Path, *, review_required: bool, confidence_level: str = "MEDIUM") -> None:
        payload = {
            "as_of_date": "2026-05-19",
            "decision_confidence_level": confidence_level,
            "review_reason_codes": ["EVIDENCE_MISSING"] if review_required else [],
            "review_required": review_required,
            "run_id": "unit-run",
            "source_commit_sha": "abc123",
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _write_data_freshness_summary(
        self,
        path: Path,
        *,
        overall_status: str,
        review_required: bool,
        counts: dict[str, int],
        item_reason: str = "WITHIN_THRESHOLD",
    ) -> None:
        payload = {
            "contract_version": "v1-test",
            "generated_at_utc": "2026-05-19T00:00:00Z",
            "items": [
                {
                    "age_days": 0,
                    "as_of_date": "2026-05-19",
                    "blocks_dashboard": item_reason != "WITHIN_THRESHOLD",
                    "blocks_outcome_attribution": True,
                    "blocks_replay": True,
                    "data_class": "unit_class",
                    "evidence_source": "field:as_of_date",
                    "freshness_status": overall_status,
                    "invalid_date_count": 0,
                    "max_as_of_date": "2026-05-19",
                    "min_as_of_date": "2026-05-19",
                    "missing_date_count": 0,
                    "reason": item_reason,
                    "record_count": 1,
                    "review_required": review_required,
                    "source_path": "tests/unit.csv",
                    "threshold_days": 7,
                    "valid_date_count": 1,
                }
            ],
            "overall_status": overall_status,
            "review_required": review_required,
            "summary_counts": {
                "FRESH": counts.get("FRESH", 0),
                "MISSING": counts.get("MISSING", 0),
                "NOT_APPLICABLE": counts.get("NOT_APPLICABLE", 0),
                "REVIEW_REQUIRED": counts.get("REVIEW_REQUIRED", 0),
                "STALE": counts.get("STALE", 0),
                "UNKNOWN": counts.get("UNKNOWN", 0),
            },
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _base_inputs(self, prefix: str) -> dict[str, str]:
        validation = self._path(f"_tmp_{prefix}_validation.csv")
        queue = self._path(f"_tmp_{prefix}_queue.csv")
        manifest = self._path(f"_tmp_{prefix}_manifest.json")
        output = self._path(f"_tmp_{prefix}_summary.json")
        self._write_csv(validation, VALIDATION_FIELDS, [])
        self._write_csv(queue, QUEUE_FIELDS, [])
        self._write_manifest(manifest)
        return {
            "decision_journal_validation": str(validation),
            "decision_review_queue": str(queue),
            "run_manifest": str(manifest),
            "out_json": str(output),
            "decision_quality_state": str(self._path(f"_tmp_{prefix}_decision_quality.json")),
            "data_freshness_summary": str(self._path(f"_tmp_{prefix}_data_freshness.json")),
            "run_artifacts": str(self._path(f"_tmp_{prefix}_artifacts.csv")),
            "run_used_inputs": str(self._path(f"_tmp_{prefix}_used_inputs.csv")),
        }

    def test_all_inputs_missing_is_not_available_and_not_pass(self) -> None:
        summary = build_dashboard_operator_summary(
            decision_journal_validation="tests/_tmp_missing_validation.csv",
            decision_review_queue="tests/_tmp_missing_queue.csv",
            run_manifest="tests/_tmp_missing_manifest.json",
        )

        self.assertEqual(summary["surface_status"], "NOT_AVAILABLE")
        self.assertNotEqual(summary["surface_status"], "PASS")
        self.assertTrue(summary["missing_required_artifacts"])
        self.assertTrue(summary["operator_attention_required"])

    def test_header_only_validation_and_queue_are_clean_pass(self) -> None:
        paths = self._base_inputs("header_pass")

        result = run_dashboard_operator_summary(**paths)

        self.assertEqual(result.summary["surface_status"], "PASS")
        self.assertEqual(result.summary["validation_findings_count"], 0)
        self.assertEqual(result.summary["queue_items"], 0)
        self.assertFalse(result.summary["operator_attention_required"])
        self.assertEqual(result.summary["operator_attention_level"], "NONE")

    def test_decision_quality_review_required_prevents_pass(self) -> None:
        paths = self._base_inputs("dq_review_required")
        self._write_decision_quality(Path(paths["decision_quality_state"]), review_required=True, confidence_level="REVIEW")

        result = run_dashboard_operator_summary(**paths)

        self.assertEqual(result.summary["surface_status"], "REVIEW")
        self.assertEqual(result.summary["decision_quality_status"], "REVIEW")
        self.assertIs(result.summary["decision_quality_review_required"], True)
        self.assertGreaterEqual(result.summary["decision_quality_review_required_count"], 1)
        self.assertTrue(result.summary["operator_attention_required"])
        self.assertIn(result.summary["operator_attention_level"], {"MEDIUM", "HIGH", "BLOCKER"})
        self.assertIn("DECISION_QUALITY_REVIEW_REQUIRED", result.summary["operator_attention_reasons"])
        self.assertNotEqual(result.summary["surface_status"], "PASS")

    def test_header_only_clean_with_decision_quality_not_required_remains_pass(self) -> None:
        paths = self._base_inputs("dq_pass")
        self._write_decision_quality(Path(paths["decision_quality_state"]), review_required=False)

        result = run_dashboard_operator_summary(**paths)

        self.assertEqual(result.summary["surface_status"], "PASS")
        self.assertEqual(result.summary["decision_quality_status"], "PASS")
        self.assertIs(result.summary["decision_quality_review_required"], False)
        self.assertFalse(result.summary["operator_attention_required"])
        self.assertEqual(result.summary["operator_attention_level"], "NONE")
        self.assertNotIn("DECISION_QUALITY_REVIEW_REQUIRED", result.summary["operator_attention_reasons"])

    def test_data_freshness_review_required_prevents_pass(self) -> None:
        paths = self._base_inputs("freshness_review")
        self._write_decision_quality(Path(paths["decision_quality_state"]), review_required=False)
        self._write_data_freshness_summary(
            Path(paths["data_freshness_summary"]),
            overall_status="STALE",
            review_required=True,
            counts={"STALE": 1},
            item_reason="THRESHOLD_EXCEEDED",
        )

        result = run_dashboard_operator_summary(**paths)

        self.assertEqual(result.summary["surface_status"], "REVIEW")
        self.assertEqual(result.summary["data_freshness_status"], "STALE")
        self.assertIs(result.summary["data_freshness_review_required"], True)
        self.assertEqual(result.summary["data_freshness_stale_count"], 1)
        self.assertEqual(result.summary["data_freshness_blocking_dashboard_count"], 1)
        self.assertTrue(result.summary["operator_attention_required"])
        self.assertIn("DATA_FRESHNESS_REVIEW_REQUIRED", result.summary["operator_attention_reasons"])
        self.assertIn("THRESHOLD_EXCEEDED", result.summary["data_freshness_top_reason_codes"])

    def test_expected_missing_data_freshness_summary_is_partial_not_pass(self) -> None:
        paths = self._base_inputs("freshness_expected_missing")
        self._write_manifest(Path(paths["run_manifest"]), selected_stages=["data_freshness", "dashboard_operator_summary"])
        self._write_decision_quality(Path(paths["decision_quality_state"]), review_required=False)

        result = run_dashboard_operator_summary(**paths)

        self.assertEqual(result.summary["surface_status"], "PARTIAL")
        self.assertEqual(result.summary["artifact_status"], "PARTIAL")
        self.assertIn(paths["data_freshness_summary"].replace("\\", "/"), result.summary["missing_required_artifacts"])
        self.assertTrue(result.summary["operator_attention_required"])

    def test_one_required_artifact_missing_is_partial(self) -> None:
        paths = self._base_inputs("partial")
        Path(paths["decision_review_queue"]).unlink()

        result = run_dashboard_operator_summary(**paths)

        self.assertEqual(result.summary["surface_status"], "PARTIAL")
        self.assertEqual(result.summary["artifact_status"], "PARTIAL")
        self.assertTrue(result.summary["missing_required_artifacts"])
        self.assertNotEqual(result.summary["surface_status"], "PASS")

    def test_duplicate_decision_id_finding_is_blocker(self) -> None:
        paths = self._base_inputs("duplicate")
        self._write_csv(
            Path(paths["decision_journal_validation"]),
            VALIDATION_FIELDS,
            [
                {
                    "validation_id": "VAL-1",
                    "as_of_date": "2026-05-19",
                    "validation_status": "REVIEW",
                    "decision_id": "DECISION_1",
                    "field_name": "decision_id",
                    "reason_code": "DECISION_ID_DUPLICATE",
                    "priority": "BLOCKER",
                    "source_artifact": "tests/journal.csv",
                    "message": "duplicate",
                }
            ],
        )

        result = run_dashboard_operator_summary(**paths)

        self.assertEqual(result.summary["surface_status"], "REVIEW")
        self.assertEqual(result.summary["operator_attention_level"], "BLOCKER")
        self.assertGreater(result.summary["duplicate_decision_id_count"], 0)

    def test_queue_high_sets_high_attention(self) -> None:
        paths = self._base_inputs("queue_high")
        self._write_csv(
            Path(paths["decision_review_queue"]),
            QUEUE_FIELDS,
            [
                {
                    "queue_id": "QUEUE-1",
                    "as_of_date": "2026-05-19",
                    "decision_id": "DECISION_1",
                    "decision_date": "2026-05-01",
                    "symbol": "MSFT",
                    "action": "WAIT_FOR_PRICE",
                    "priority": "HIGH",
                    "queue_status": "OPEN",
                    "reason_codes": "REVIEW_DATE_DUE",
                    "review_due_date": "2026-05-19",
                    "days_overdue": "0",
                    "process_confidence_level": "MEDIUM",
                    "decision_quality_status": "PASS",
                    "source_commit_sha": "abc123",
                    "run_id": "unit-run",
                    "source_artifact": "tests/journal.csv",
                    "recommended_operator_action": "Review due decision.",
                }
            ],
        )

        result = run_dashboard_operator_summary(**paths)

        self.assertEqual(result.summary["surface_status"], "REVIEW")
        self.assertEqual(result.summary["operator_attention_level"], "HIGH")
        self.assertTrue(result.summary["operator_attention_required"])

    def test_stale_only_sets_medium_without_investment_risk_text(self) -> None:
        paths = self._base_inputs("stale")
        self._write_csv(
            Path(paths["decision_review_queue"]),
            QUEUE_FIELDS,
            [
                {
                    "queue_id": "QUEUE-1",
                    "as_of_date": "2026-05-19",
                    "decision_id": "",
                    "decision_date": "",
                    "symbol": "",
                    "action": "",
                    "priority": "MEDIUM",
                    "queue_status": "OPEN",
                    "reason_codes": "DECISION_QUALITY_STALE",
                    "review_due_date": "",
                    "days_overdue": "",
                    "process_confidence_level": "MEDIUM",
                    "decision_quality_status": "STALE",
                    "source_commit_sha": "abc123",
                    "run_id": "unit-run",
                    "source_artifact": "tests/decision_quality.json",
                    "recommended_operator_action": "Refresh process state.",
                }
            ],
        )

        result = run_dashboard_operator_summary(**paths)
        text = json.dumps(result.summary, sort_keys=True).lower()

        self.assertEqual(result.summary["operator_attention_level"], "MEDIUM")
        self.assertGreater(result.summary["stale_state_count"], 0)
        for forbidden in ("order signal", "trade signal", "expected return", "alpha", "outperform", "investment confidence"):
            self.assertNotIn(forbidden, text)

    def test_lineage_mismatch_sets_at_least_medium(self) -> None:
        paths = self._base_inputs("lineage")
        self._write_csv(
            Path(paths["decision_review_queue"]),
            QUEUE_FIELDS,
            [
                {
                    "queue_id": "QUEUE-1",
                    "as_of_date": "2026-05-19",
                    "decision_id": "DECISION_1",
                    "decision_date": "2026-05-19",
                    "symbol": "MSFT",
                    "action": "WAIT_FOR_PRICE",
                    "priority": "MEDIUM",
                    "queue_status": "OPEN",
                    "reason_codes": "DECISION_QUALITY_LINEAGE_MISMATCH",
                    "review_due_date": "",
                    "days_overdue": "",
                    "process_confidence_level": "MEDIUM",
                    "decision_quality_status": "REVIEW",
                    "source_commit_sha": "def456",
                    "run_id": "unit-run",
                    "source_artifact": "tests/decision_quality.json",
                    "recommended_operator_action": "Review lineage mismatch.",
                }
            ],
        )

        result = run_dashboard_operator_summary(**paths)

        self.assertGreater(result.summary["lineage_mismatch_count"], 0)
        self.assertIn(result.summary["operator_attention_level"], {"MEDIUM", "HIGH", "BLOCKER"})

    def test_top_reason_codes_are_deterministic(self) -> None:
        paths = self._base_inputs("top_reasons")
        self._write_csv(
            Path(paths["decision_review_queue"]),
            QUEUE_FIELDS,
            [
                {field: "" for field in QUEUE_FIELDS}
                | {"queue_id": "1", "priority": "HIGH", "reason_codes": "B_REASON;A_REASON"},
                {field: "" for field in QUEUE_FIELDS}
                | {"queue_id": "2", "priority": "HIGH", "reason_codes": "A_REASON"},
                {field: "" for field in QUEUE_FIELDS}
                | {"queue_id": "3", "priority": "HIGH", "reason_codes": "C_REASON"},
            ],
        )

        result = run_dashboard_operator_summary(**paths)

        self.assertEqual(result.summary["top_reason_codes"], ["A_REASON", "B_REASON", "C_REASON"])

    def test_source_artifacts_are_structured_and_paths_are_sanitized(self) -> None:
        summary = build_dashboard_operator_summary(
            decision_journal_validation=r"C:\Users\Max\private.csv",
            decision_review_queue=r"\\server\share\queue.csv",
            run_manifest="../outside.json",
        )

        artifacts = summary["source_artifacts"]
        self.assertTrue(all({"path", "required", "status", "row_count", "sha256", "reason"}.issubset(artifact) for artifact in artifacts))
        text = json.dumps(summary, sort_keys=True)
        self.assertNotIn(r"C:\Users\Max", text)
        self.assertNotIn(r"\\server\share", text)
        self.assertNotIn("../outside", text)

    def test_repo_internal_absolute_paths_are_stored_relative(self) -> None:
        paths = self._base_inputs("absolute_inside_repo")
        summary = build_dashboard_operator_summary(
            decision_journal_validation=str(Path(paths["decision_journal_validation"]).resolve()),
            decision_review_queue=str(Path(paths["decision_review_queue"]).resolve()),
            run_manifest=str(Path(paths["run_manifest"]).resolve()),
            decision_quality_state=paths["decision_quality_state"],
            run_artifacts=paths["run_artifacts"],
            run_used_inputs=paths["run_used_inputs"],
        )

        artifact_paths = [artifact["path"] for artifact in summary["source_artifacts"]]
        self.assertIn(Path(paths["decision_journal_validation"]).as_posix(), artifact_paths)
        self.assertIn(Path(paths["decision_review_queue"]).as_posix(), artifact_paths)
        self.assertNotIn("EXTERNAL_PATH_REDACTED:decision_journal_validation", artifact_paths)

    def test_json_serialization_is_deterministic_and_native(self) -> None:
        paths = self._base_inputs("json")

        result = run_dashboard_operator_summary(**paths)
        raw = Path(paths["out_json"]).read_text(encoding="utf-8")
        parsed = json.loads(raw)

        self.assertTrue(raw.startswith("{\n"))
        self.assertIn('  "operator_attention_required": false', raw)
        self.assertIs(parsed["operator_attention_required"], False)
        self.assertIsInstance(parsed["top_reason_codes"], list)
        self.assertEqual(result.summary, parsed)

    def test_cli_writes_output_to_temp_path(self) -> None:
        paths = self._base_inputs("cli")
        command = [
            sys.executable,
            "-m",
            "src.dashboard_operator_summary",
            "--decision-journal-validation",
            paths["decision_journal_validation"],
            "--decision-review-queue",
            paths["decision_review_queue"],
            "--run-manifest",
            paths["run_manifest"],
            "--out-json",
            paths["out_json"],
        ]

        completed = subprocess.run(command, text=True, capture_output=True, check=False)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(Path(paths["out_json"]).exists())


if __name__ == "__main__":
    unittest.main()
