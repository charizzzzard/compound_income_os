from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.personal_decision_quality_state import FIELDNAMES, run_decision_quality_state

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


class PersonalDecisionQualityStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_personal_decision_quality_state"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.input_closure = self.tmp / "personal_input_closure_report.csv"
        self.decision_capture = self.tmp / "personal_decision_state_capture.csv"
        self.cash_refill = self.tmp / "personal_cash_refill_review.csv"
        self.rebalance = self.tmp / "personal_rebalance_review.csv"
        self.run_manifest = self.tmp / "personal_run_manifest.json"
        self.run_used_inputs = self.tmp / "personal_run_used_inputs.csv"
        self.monthly_ranking = self.tmp / "personal_monthly_buy_ranking.csv"
        self.score_audit = self.tmp / "personal_score_audit.csv"
        self.out_csv = self.tmp / "decision_quality_state.csv"
        self.out_json = self.tmp / "decision_quality_state.json"
        self.report = self.tmp / "decision_quality_report.md"
        self.write_ready_inputs()

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_ready_inputs(self) -> None:
        write_csv(
            self.input_closure,
            [
                "input_area",
                "artifact_path",
                "status",
                "blocker_severity",
                "missing_or_review_items_count",
                "sample_or_synthetic_flag",
                "reason_codes",
                "required_operator_action",
                "downstream_impact",
                "next_recommended_step",
            ],
            [
                {"input_area": "WATCHLIST", "artifact_path": "x", "status": "READY", "blocker_severity": "NONE", "missing_or_review_items_count": "0", "sample_or_synthetic_flag": "False", "reason_codes": "", "required_operator_action": "", "downstream_impact": "", "next_recommended_step": ""},
                {"input_area": "VALUATION", "artifact_path": "x", "status": "READY", "blocker_severity": "NONE", "missing_or_review_items_count": "0", "sample_or_synthetic_flag": "False", "reason_codes": "", "required_operator_action": "", "downstream_impact": "", "next_recommended_step": ""},
            ],
        )
        write_csv(
            self.decision_capture,
            ["decision_id", "decision_date", "decision_scope", "proposed_action", "human_decision", "decision_status", "reasoning_3_sentences", "dominant_uncertainty", "benchmark_alternative"],
            [{"decision_id": "DECISION_20260518_0001", "decision_date": "2026-05-18", "decision_scope": "MONTHLY_REVIEW", "proposed_action": "NO_ACTION", "human_decision": "NO_ACTION", "decision_status": "CLOSED", "reasoning_3_sentences": "Reviewed. No action. Continue.", "dominant_uncertainty": "UNKNOWN", "benchmark_alternative": "CASH"}],
        )
        write_csv(
            self.cash_refill,
            ["review_date", "status", "trigger", "data_quality_flag"],
            [{"review_date": "2026-05-18", "status": "CASH_REFILL_NOT_REQUIRED", "trigger": "NONE", "data_quality_flag": "OK"}],
        )
        write_csv(
            self.rebalance,
            ["review_date", "bucket", "band_status", "recommended_action", "data_quality_flag"],
            [{"review_date": "2026-05-18", "bucket": "CASH", "band_status": "WITHIN_BAND", "recommended_action": "HOLD", "data_quality_flag": "OK"}],
        )
        self.run_manifest.write_text(
            json.dumps(
                {
                    "run_id": "2026-05-18-monthly",
                    "run_started_at": "2026-05-18T08:00:00+00:00",
                    "source_commit_sha": "abc123",
                    "executed_stage_order": ["monthly_ranking", "score"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        write_csv(self.run_used_inputs, ["artifact_path", "status"], [{"artifact_path": "data/processed/x.csv", "status": "USED"}])
        write_csv(self.monthly_ranking, ["ticker", "rank"], [{"ticker": "MSFT", "rank": "1"}])
        write_csv(self.score_audit, ["ticker", "data_quality_flag"], [{"ticker": "MSFT", "data_quality_flag": "OK"}])

    def run_state(self, **overrides):
        params = {
            "input_closure": str(self.input_closure),
            "decision_capture": str(self.decision_capture),
            "cash_refill": str(self.cash_refill),
            "rebalance": str(self.rebalance),
            "run_manifest": str(self.run_manifest),
            "run_used_inputs": str(self.run_used_inputs),
            "monthly_ranking": str(self.monthly_ranking),
            "score_audit": str(self.score_audit),
            "out_csv": str(self.out_csv),
            "out_json": str(self.out_json),
            "report": str(self.report),
            "generated_at": "2026-05-18T12:00:00Z",
        }
        params.update(overrides)
        return run_decision_quality_state(**params)

    def test_contract_examples_do_not_use_python_booleans(self) -> None:
        text = (ROOT / "docs" / "contracts" / "DECISION_QUALITY_STATE_CONTRACT.md").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"(?m)^[a-zA-Z_]+=(True|False)$", text))
        self.assertIsNone(re.search(r"(?m)^[a-zA-Z_]+: (True|False)$", text))

    def test_csv_header_matches_contract_field_order_and_booleans_lowercase(self) -> None:
        result = self.run_state()
        lines = self.out_csv.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0].split(","), FIELDNAMES)
        row = read_csv(self.out_csv)[0]
        self.assertEqual(row["ranking_available"], "true")
        self.assertEqual(row["review_required"], "false")
        self.assertEqual(result.state["decision_confidence_level"], "MEDIUM")

    def test_csv_list_delimiter_is_semicolon(self) -> None:
        self.run_state()
        row = read_csv(self.out_csv)[0]
        self.assertIn("RANKING_STABILITY_NOT_EVALUATED;SENSITIVITY_NOT_EVALUATED", row["confidence_reason_codes"])

    def test_json_uses_native_types_and_is_deterministic(self) -> None:
        self.run_state()
        text = self.out_json.read_text(encoding="utf-8")
        data = json.loads(text)
        self.assertIs(data["review_required"], False)
        self.assertIsInstance(data["input_artifacts"], list)
        self.assertIsInstance(data["confidence_reason_codes"], list)
        self.assertIn('\n  "as_of_date":', text)
        self.assertTrue(text.endswith("\n"))

    def test_missing_critical_field_sets_review_and_evidence_missing(self) -> None:
        self.cash_refill.unlink()
        result = self.run_state()
        self.assertEqual(result.state["decision_confidence_level"], "REVIEW")
        self.assertIs(result.state["review_required"], True)
        self.assertIn("cash_refill_review", result.state["missing_critical_fields"])
        self.assertIn("EVIDENCE_MISSING", result.state["confidence_reason_codes"])
        self.assertIn("EVIDENCE_MISSING", result.state["review_reason_codes"])

    def test_input_closure_blocked_sets_review(self) -> None:
        write_csv(
            self.input_closure,
            ["input_area", "artifact_path", "status", "blocker_severity", "missing_or_review_items_count", "sample_or_synthetic_flag", "reason_codes", "required_operator_action", "downstream_impact", "next_recommended_step"],
            [{"input_area": "WATCHLIST", "artifact_path": "x", "status": "BLOCKED", "blocker_severity": "P0", "missing_or_review_items_count": "1", "sample_or_synthetic_flag": "true", "reason_codes": "WATCHLIST_SAMPLE_INPUT", "required_operator_action": "", "downstream_impact": "", "next_recommended_step": ""}],
        )
        result = self.run_state()
        self.assertEqual(result.state["decision_confidence_level"], "REVIEW")
        self.assertIs(result.state["review_required"], True)
        self.assertIn("INPUT_CLOSURE_BLOCKED", result.state["confidence_reason_codes"])
        self.assertIn("INPUT_CLOSURE_BLOCKED", result.state["review_reason_codes"])

    def test_missing_mandatory_input_sets_review_required(self) -> None:
        self.run_used_inputs.unlink()
        result = self.run_state()
        self.assertEqual(result.state["decision_confidence_level"], "REVIEW")
        self.assertIs(result.state["review_required"], True)
        self.assertIn("run_used_inputs", result.state["missing_critical_fields"])

    def test_real_monthly_stage_requires_monthly_ranking_output(self) -> None:
        self.run_manifest.write_text(
            json.dumps({"run_id": "2026-05-18-monthly", "as_of_date": "2026-05-18", "source_commit_sha": "abc123", "executed_stage_order": ["scoring", "monthly"]}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.monthly_ranking.unlink()
        result = self.run_state()
        self.assertEqual(result.state["decision_confidence_level"], "REVIEW")
        self.assertIs(result.state["review_required"], True)
        self.assertIn("monthly_ranking_output", result.state["missing_critical_fields"])
        self.assertTrue(result.state["review_reason_codes"])

    def test_real_scoring_stage_requires_score_audit_output(self) -> None:
        self.run_manifest.write_text(
            json.dumps({"run_id": "2026-05-18-monthly", "as_of_date": "2026-05-18", "source_commit_sha": "abc123", "executed_stage_order": ["scoring", "monthly"]}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.score_audit.unlink()
        result = self.run_state()
        self.assertEqual(result.state["decision_confidence_level"], "REVIEW")
        self.assertIs(result.state["review_required"], True)
        self.assertIn("score_audit_output", result.state["missing_critical_fields"])
        self.assertTrue(result.state["review_reason_codes"])

    def test_absolute_input_path_inside_repo_is_stored_relative(self) -> None:
        result = self.run_state(input_closure=str(self.input_closure.resolve()))
        artifact_text = ";".join(result.state["input_artifacts"])
        self.assertIn("tests/_tmp_personal_decision_quality_state/personal_input_closure_report.csv:AVAILABLE", artifact_text)
        self.assertNotIn(str(self.input_closure.resolve()), artifact_text)

    def test_external_absolute_mandatory_path_is_redacted_and_blocks_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            external_path = Path(directory) / "personal_cash_refill_review.csv"
            write_csv(external_path, ["review_date", "status", "trigger", "data_quality_flag"], [{"review_date": "2026-05-18", "status": "OK", "trigger": "NONE", "data_quality_flag": "OK"}])
            result = self.run_state(cash_refill=str(external_path))
        artifact_text = ";".join(result.state["input_artifacts"])
        self.assertIn("EXTERNAL_PATH_REDACTED:cash_refill_review", artifact_text)
        self.assertNotIn(str(external_path), artifact_text)
        self.assertEqual(result.state["decision_confidence_level"], "REVIEW")
        self.assertIs(result.state["review_required"], True)
        self.assertIn("LINEAGE_INCOMPLETE", result.state["review_reason_codes"])

    def test_empty_run_used_inputs_is_lineage_hard_blocker(self) -> None:
        write_csv(self.run_used_inputs, ["artifact_path", "status"], [])
        result = self.run_state()
        self.assertEqual(result.state["decision_confidence_level"], "REVIEW")
        self.assertIs(result.state["review_required"], True)
        self.assertIn("run_used_inputs", result.state["missing_critical_fields"])
        self.assertIn("LINEAGE_INCOMPLETE", result.state["review_reason_codes"])

    def test_run_used_inputs_without_path_column_is_lineage_hard_blocker(self) -> None:
        write_csv(self.run_used_inputs, ["role", "status"], [{"role": "processed", "status": "USED"}])
        result = self.run_state()
        self.assertEqual(result.state["decision_confidence_level"], "REVIEW")
        self.assertIs(result.state["review_required"], True)
        self.assertIn("run_used_inputs_lineage", result.state["missing_critical_fields"])
        self.assertIn("LINEAGE_INCOMPLETE", result.state["review_reason_codes"])

    def test_run_used_inputs_private_or_external_paths_are_not_emitted_raw(self) -> None:
        write_csv(self.run_used_inputs, ["artifact_path", "status"], [{"artifact_path": "data/raw/private/statement.csv", "status": "USED"}])
        result = self.run_state()
        output_text = self.out_json.read_text(encoding="utf-8") + self.out_csv.read_text(encoding="utf-8")
        self.assertEqual(result.state["decision_confidence_level"], "REVIEW")
        self.assertIs(result.state["review_required"], True)
        self.assertIn("run_used_inputs_private_or_external_path", result.state["missing_critical_fields"])
        self.assertNotIn("statement.csv", output_text)

    def test_not_evaluated_ranking_and_sensitivity_cap_medium_without_review(self) -> None:
        result = self.run_state()
        self.assertEqual(result.state["ranking_stability_status"], "NOT_EVALUATED")
        self.assertEqual(result.state["sensitivity_status"], "NOT_EVALUATED")
        self.assertEqual(result.state["decision_confidence_level"], "MEDIUM")
        self.assertIs(result.state["review_required"], False)

    def test_scenario_and_tail_risk_not_evaluated_are_not_hard_blockers(self) -> None:
        result = self.run_state()
        self.assertEqual(result.state["scenario_status"], "NOT_EVALUATED")
        self.assertEqual(result.state["tail_risk_status"], "NOT_EVALUATED")
        self.assertIs(result.state["review_required"], False)

    def test_evidence_pct_null_or_empty_only_when_missing_or_review(self) -> None:
        result = self.run_state()
        self.assertEqual(result.state["evidence_coverage_status"], "COVERED")
        self.assertEqual(result.state["evidence_coverage_pct"], 1.0)
        self.cash_refill.unlink()
        result = self.run_state()
        self.assertIn(result.state["evidence_coverage_status"], {"PARTIAL", "MISSING", "REVIEW", "COVERED"})
        if result.state["evidence_coverage_pct"] is None:
            self.assertIn(result.state["evidence_coverage_status"], {"MISSING", "REVIEW"})

    def test_no_forbidden_fields_are_emitted(self) -> None:
        result = self.run_state()
        forbidden = {"broker", "order_id", "execution_id", "filled_price", "tax_lot", "simulation", "backtest"}
        self.assertTrue(forbidden.isdisjoint(result.state.keys()))

    def test_cli_writes_csv_json_and_report(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.personal_decision_quality_state",
                "--input-closure",
                str(self.input_closure),
                "--decision-capture",
                str(self.decision_capture),
                "--cash-refill",
                str(self.cash_refill),
                "--rebalance",
                str(self.rebalance),
                "--run-manifest",
                str(self.run_manifest),
                "--run-used-inputs",
                str(self.run_used_inputs),
                "--monthly-ranking",
                str(self.monthly_ranking),
                "--score-audit",
                str(self.score_audit),
                "--out-csv",
                str(self.out_csv),
                "--out-json",
                str(self.out_json),
                "--report",
                str(self.report),
                "--generated-at",
                "2026-05-18T12:00:00Z",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(self.out_csv.exists())
        self.assertTrue(self.out_json.exists())
        self.assertTrue(self.report.exists())

    def test_default_report_path_uses_effective_as_of_date(self) -> None:
        self.run_manifest.write_text(
            json.dumps({"run_id": "2026-05-19-monthly", "as_of_date": "2026-05-19", "source_commit_sha": "abc123", "executed_stage_order": []}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result = self.run_state(report=None)
        self.assertEqual(result.report_output.as_posix(), (ROOT / "reports" / "2026-05-19" / "decision_quality_report.md").as_posix())
        self.assertTrue(result.report_output.exists())
        result.report_output.unlink()
        try:
            result.report_output.parent.rmdir()
        except OSError:
            pass

    def test_report_contains_full_non_scope_list(self) -> None:
        self.run_state()
        text = self.report.read_text(encoding="utf-8")
        for phrase in [
            "no broker/order/trading",
            "no score formula change",
            "no portfolio rule change",
            "no silent data enrichment",
            "no simulation/backtesting",
            "no outcome attribution",
            "no runtime LLM decisioning",
            "no tax quantification",
            "no portfolio event ledger",
            "no private raw data",
        ]:
            self.assertIn(phrase, text)

    def test_producer_does_not_mutate_inputs(self) -> None:
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in [self.input_closure, self.cash_refill, self.rebalance, self.run_manifest]}
        self.run_state()
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in before}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
