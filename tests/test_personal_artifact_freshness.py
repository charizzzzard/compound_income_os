from __future__ import annotations

import csv
import json
import shutil
import unittest
from pathlib import Path

from src.personal_artifact_freshness import run_personal_artifact_freshness

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


class PersonalArtifactFreshnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_artifact_freshness"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.scores = self.tmp / "scores.csv"
        self.delta_summary = self.tmp / "delta_summary.csv"
        self.delta_holdings = self.tmp / "delta_holdings.csv"
        self.kpi_tier = self.tmp / "kpi_tier.csv"
        self.missing_summary = self.tmp / "missing_summary.csv"
        self.used_inputs = self.tmp / "used_inputs.csv"
        self.manifest = self.tmp / "manifest.json"
        self.checks = self.tmp / "checks.csv"
        self.summary = self.tmp / "summary.csv"
        self.report = self.tmp / "report.md"

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_base_inputs(
        self,
        *,
        score_flags: list[str] | None = None,
        delta_counts: dict[str, int] | None = None,
        delta_metadata: dict[str, str] | None = None,
        manifest_metadata: dict[str, str] | None = None,
    ) -> None:
        flags = score_flags or ["REVIEW", "MISSING_DATA"]
        write_csv(
            self.scores,
            ["ticker", "isin", "data_quality_flag"],
            [{"ticker": f"T{i}", "isin": f"US{i}", "data_quality_flag": flag} for i, flag in enumerate(flags, start=1)],
        )
        counts = delta_counts or {
            "OK": 0,
            "REVIEW": flags.count("REVIEW"),
            "MISSING_DATA": flags.count("MISSING_DATA"),
            "BLOCKED": flags.count("BLOCKED"),
        }
        metadata = delta_metadata or {}
        rows = [{"metric": f"score_data_quality__{key}", "value": str(counts.get(key, 0)), "notes": ""} for key in ("OK", "REVIEW", "MISSING_DATA", "BLOCKED")]
        rows.extend({"metric": key, "value": value, "notes": ""} for key, value in metadata.items())
        write_csv(self.delta_summary, ["metric", "value", "notes"], rows)
        write_csv(self.delta_holdings, ["ticker", "data_quality_flag"], [{"ticker": "T1", "data_quality_flag": flags[0]}])
        write_csv(self.kpi_tier, ["ticker", "resulting_monthly_action"], [{"ticker": "T1", "resulting_monthly_action": "REVIEW_CORE_DATA"}])
        write_csv(self.missing_summary, ["metric", "value", "notes"], [{"metric": "missing_required_kpi_total", "value": "1", "notes": ""}])
        write_csv(self.used_inputs, ["stage_name", "input_role", "input_path", "notes"], [{"stage_name": "scoring", "input_role": "fundamentals_master", "input_path": "data/processed/master.csv", "notes": "fundamentals_source_mode=EVIDENCE_APPLIED"}])
        manifest = {"run_id": "run-1", "run_finished_at": "2026-04-26T12:00:00+00:00"}
        if manifest_metadata:
            manifest.update(manifest_metadata)
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")

    def run_freshness(self, *, deferred: set[str] | None = None):
        return run_personal_artifact_freshness(
            scores_input=str(self.scores),
            evidence_delta_summary_input=str(self.delta_summary),
            evidence_delta_holdings_input=str(self.delta_holdings),
            kpi_tier_input=str(self.kpi_tier),
            missing_kpi_summary_input=str(self.missing_summary),
            run_used_inputs_input=str(self.used_inputs),
            run_manifest_input=str(self.manifest),
            checks_output=str(self.checks),
            summary_output=str(self.summary),
            report_output=str(self.report),
            deferred_artifact_labels=deferred,
        )

    def check_row(self, check_id: str) -> dict[str, str]:
        return {row["check_id"]: row for row in read_csv(self.checks)}[check_id]

    def summary_value(self, metric: str) -> str:
        return {row["metric"]: row["value"] for row in read_csv(self.summary)}[metric]

    def test_matching_counters_and_metadata_are_fresh_pass(self) -> None:
        self.write_base_inputs(delta_metadata={"run_id": "run-1", "generated_at": "2026-04-26T12:00:00+00:00"})
        self.run_freshness()

        row = self.check_row("score_vs_evidence_delta_status_counters")
        self.assertEqual(row["artifact_freshness_status"], "FRESH")
        self.assertEqual(row["artifact_drift_status"], "PASS")
        self.assertIn("COUNTER_MATCH", row["reason_codes"])

    def test_counter_mismatch_with_comparable_metadata_is_blocked(self) -> None:
        self.write_base_inputs(
            delta_counts={"OK": 0, "REVIEW": 0, "MISSING_DATA": 2, "BLOCKED": 0},
            delta_metadata={"run_id": "run-1", "generated_at": "2026-04-26T12:00:00+00:00"},
        )
        self.run_freshness()

        row = self.check_row("score_vs_evidence_delta_status_counters")
        self.assertEqual(row["artifact_freshness_status"], "INCONSISTENT")
        self.assertEqual(row["artifact_drift_status"], "BLOCKED")
        self.assertIn("COUNTER_MISMATCH", row["reason_codes"])
        self.assertEqual(self.summary_value("artifact_drift_active"), "True")

    def test_counter_mismatch_with_missing_metadata_is_not_current_drift(self) -> None:
        self.write_base_inputs(delta_counts={"OK": 0, "REVIEW": 0, "MISSING_DATA": 2, "BLOCKED": 0})
        self.run_freshness()

        row = self.check_row("score_vs_evidence_delta_status_counters")
        self.assertEqual(row["artifact_freshness_status"], "MISSING_METADATA")
        self.assertEqual(row["artifact_drift_status"], "REVIEW")
        self.assertIn("MISSING_METADATA", row["reason_codes"])
        self.assertEqual(self.summary_value("artifact_drift_active"), "False")

    def test_run_id_mismatch_marks_stale(self) -> None:
        self.write_base_inputs(
            delta_counts={"OK": 0, "REVIEW": 0, "MISSING_DATA": 2, "BLOCKED": 0},
            delta_metadata={"run_id": "older-run", "generated_at": "2026-04-26T12:00:00+00:00"},
        )
        self.run_freshness()

        row = self.check_row("score_vs_evidence_delta_status_counters")
        self.assertEqual(row["artifact_freshness_status"], "STALE")
        self.assertIn("RUN_ID_MISMATCH", row["reason_codes"])

    def test_missing_artifact_is_not_available_without_crash(self) -> None:
        self.write_base_inputs()
        self.delta_summary.unlink()
        self.run_freshness()

        row = self.check_row("score_vs_evidence_delta_status_counters")
        self.assertEqual(row["artifact_freshness_status"], "MISSING")
        self.assertEqual(row["artifact_drift_status"], "NOT_AVAILABLE")
        self.assertIn("MISSING_ARTIFACT", row["reason_codes"])

    def test_deferred_artifact_is_classified_without_blocking_current_drift(self) -> None:
        self.write_base_inputs(delta_counts={"OK": 0, "REVIEW": 0, "MISSING_DATA": 2, "BLOCKED": 0})
        self.run_freshness(deferred={"evidence_delta_summary"})

        row = self.check_row("score_vs_evidence_delta_status_counters")
        self.assertEqual(row["artifact_freshness_status"], "DEFERRED")
        self.assertIn("DERIVED_ARTIFACT_DEFERRED", row["reason_codes"])
        self.assertEqual(self.summary_value("artifact_drift_active"), "False")

    def test_private_paths_are_sanitized_in_report(self) -> None:
        private_scores = self.tmp / "data" / "raw" / "private" / "scores.csv"
        self.write_base_inputs()
        run_personal_artifact_freshness(
            scores_input=str(private_scores),
            evidence_delta_summary_input=str(self.delta_summary),
            evidence_delta_holdings_input=str(self.delta_holdings),
            kpi_tier_input=str(self.kpi_tier),
            missing_kpi_summary_input=str(self.missing_summary),
            run_used_inputs_input=str(self.used_inputs),
            run_manifest_input=str(self.manifest),
            checks_output=str(self.checks),
            summary_output=str(self.summary),
            report_output=str(self.report),
        )
        report = self.report.read_text(encoding="utf-8")
        self.assertIn("<private_path>", report)
        self.assertNotIn("data/raw/private/scores.csv", report)


if __name__ == "__main__":
    unittest.main()
