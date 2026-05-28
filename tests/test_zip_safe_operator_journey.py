from __future__ import annotations

import csv
import json
import shutil
import unittest
from pathlib import Path

from src.dashboard_operator_summary import run_dashboard_operator_summary
from src.data_freshness import run_data_freshness
from src.personal_decision_journal_validation import QUEUE_FIELDS, VALIDATION_FIELDS


ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / "tests" / "_tmp_zip_safe_operator_journey"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


class ZipSafeOperatorJourneyTests(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree(TMP, ignore_errors=True)
        TMP.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(TMP, ignore_errors=True)

    def test_synthetic_operator_journey_surfaces_missing_stale_and_unknown_state(self) -> None:
        stale_csv = TMP / "synthetic_stale_source.csv"
        unknown_csv = TMP / "synthetic_unknown_source.csv"
        missing_csv = TMP / "synthetic_missing_source.csv"
        freshness_config = TMP / "data_freshness_config.json"
        freshness_json = TMP / "data_freshness_summary.json"
        freshness_report = TMP / "data_freshness_summary.md"
        validation_csv = TMP / "decision_journal_validation.csv"
        queue_csv = TMP / "decision_review_queue.csv"
        manifest_json = TMP / "personal_run_manifest.json"
        decision_quality_json = TMP / "decision_quality_state.json"
        operator_summary_json = TMP / "review_queue_summary.json"

        stale_csv.write_text("as_of_date,value\n2026-04-01,1\n", encoding="utf-8")
        unknown_csv.write_text("symbol,value\nSYNTHETIC,1\n", encoding="utf-8")
        freshness_config.write_text(
            json.dumps(
                {
                    "contract_version": "zip-safe-smoke-v1",
                    "items": [
                        {
                            "blocks_dashboard": True,
                            "blocks_outcome_attribution": True,
                            "blocks_replay": True,
                            "data_class": "synthetic_stale",
                            "freshness_date_fields": ["as_of_date"],
                            "missing_behavior": "MISSING",
                            "required": True,
                            "review_on_missing": True,
                            "review_on_stale": True,
                            "review_on_unknown": True,
                            "source_path": stale_csv.relative_to(ROOT).as_posix(),
                            "threshold_days": 7,
                            "unknown_behavior": "UNKNOWN",
                        },
                        {
                            "blocks_dashboard": True,
                            "blocks_outcome_attribution": True,
                            "blocks_replay": True,
                            "data_class": "synthetic_unknown",
                            "freshness_date_fields": ["as_of_date"],
                            "missing_behavior": "MISSING",
                            "required": True,
                            "review_on_missing": True,
                            "review_on_stale": True,
                            "review_on_unknown": True,
                            "source_path": unknown_csv.relative_to(ROOT).as_posix(),
                            "threshold_days": 7,
                            "unknown_behavior": "UNKNOWN",
                        },
                        {
                            "blocks_dashboard": True,
                            "blocks_outcome_attribution": True,
                            "blocks_replay": True,
                            "data_class": "synthetic_missing",
                            "freshness_date_fields": ["as_of_date"],
                            "missing_behavior": "MISSING",
                            "required": True,
                            "review_on_missing": True,
                            "review_on_stale": True,
                            "review_on_unknown": True,
                            "source_path": missing_csv.relative_to(ROOT).as_posix(),
                            "threshold_days": 7,
                            "unknown_behavior": "UNKNOWN",
                        },
                    ],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        write_csv(validation_csv, VALIDATION_FIELDS, [])
        write_csv(queue_csv, QUEUE_FIELDS, [])
        manifest_json.write_text(
            json.dumps(
                {
                    "as_of_date": "2026-05-21",
                    "run_id": "zip-safe-smoke",
                    "selected_stages": ["data_freshness", "dashboard_operator_summary"],
                    "source_commit_sha": "zip-safe-synthetic",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        decision_quality_json.write_text(
            json.dumps(
                {
                    "as_of_date": "2026-05-21",
                    "decision_confidence_level": "REVIEW",
                    "review_required": False,
                    "run_id": "zip-safe-smoke",
                    "source_commit_sha": "zip-safe-synthetic",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        freshness_result = run_data_freshness(
            config_path=freshness_config,
            as_of_date="2026-05-21",
            out_json=freshness_json,
            report=freshness_report,
            generated_at_utc="2026-05-21T00:00:00Z",
        )
        operator_result = run_dashboard_operator_summary(
            decision_quality_state=str(decision_quality_json.relative_to(ROOT)),
            decision_journal_validation=str(validation_csv.relative_to(ROOT)),
            decision_review_queue=str(queue_csv.relative_to(ROOT)),
            data_freshness_summary=str(freshness_json.relative_to(ROOT)),
            run_manifest=str(manifest_json.relative_to(ROOT)),
            out_json=str(operator_summary_json.relative_to(ROOT)),
            as_of_date="2026-05-21",
        )

        self.assertTrue(freshness_result.json_output.exists())
        self.assertTrue(freshness_result.report_output.exists())
        self.assertTrue(operator_result.json_output.exists())
        self.assertEqual(freshness_result.summary["summary_counts"]["STALE"], 1)
        self.assertEqual(freshness_result.summary["summary_counts"]["UNKNOWN"], 1)
        self.assertEqual(freshness_result.summary["summary_counts"]["MISSING"], 1)
        self.assertTrue(freshness_result.summary["review_required"])
        self.assertEqual(operator_result.summary["surface_status"], "REVIEW")
        self.assertEqual(operator_result.summary["data_freshness_stale_count"], 1)
        self.assertEqual(operator_result.summary["data_freshness_unknown_count"], 1)
        self.assertEqual(operator_result.summary["data_freshness_missing_count"], 1)
        self.assertTrue(operator_result.summary["operator_attention_required"])
        self.assertIn("DATA_FRESHNESS_REVIEW_REQUIRED", operator_result.summary["operator_attention_reasons"])

        combined = "\n".join(
            [
                freshness_json.read_text(encoding="utf-8"),
                freshness_report.read_text(encoding="utf-8"),
                operator_summary_json.read_text(encoding="utf-8"),
            ]
        )
        self.assertIn("ARTIFACT_MISSING", combined)
        self.assertIn("NO_DATE_SIGNAL", combined)
        self.assertIn("THRESHOLD_EXCEEDED", combined)
        self.assertNotIn(str(ROOT), combined)
        for forbidden in (
            "buy signal",
            "sell signal",
            "order execution",
            "production ready",
            "investment ready",
            "broker write",
        ):
            self.assertNotIn(forbidden, combined.lower())


if __name__ == "__main__":
    unittest.main()
