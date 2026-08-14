from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid

from src.common import load_yaml_config, read_csv_rows
from src.personal_decision_trigger_capture import (
    load_trigger_ledger,
    lock_trigger_proposals,
    write_trigger_proposals,
)
from src.personal_forward_validation import (
    build_forward_validation_summary,
    wilson_interval,
    write_forward_validation_outputs,
)
from src.personal_trigger_resolution import append_trigger_resolution, load_resolution_ledger


class PersonalForwardValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_forward_validation_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.journal = self.tmp / "decisions.csv"
        self.proposals = self.tmp / "proposals.json"
        self.triggers = self.tmp / "triggers.csv"
        self.resolutions = self.tmp / "resolutions.csv"
        self.summary = self.tmp / "summary.json"
        self.report = self.tmp / "report.md"
        with self.journal.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["decision_id", "decision_date"])
            writer.writeheader()
            writer.writerow({"decision_id": "DECISION_20260814_0001", "decision_date": "2026-08-14"})
            writer.writerow({"decision_id": "DECISION_20260901_0002", "decision_date": "2026-09-01"})

        first = [
            self.proposal("TRIGGER_001", "DECISION_20260814_0001", "0.10", "MARGIN", "2026-08-14T10:00:00Z"),
            self.proposal("TRIGGER_002", "DECISION_20260814_0001", "0.40", "MARGIN", "2026-08-14T10:00:00Z"),
        ]
        write_trigger_proposals(first, decision_journal=str(self.journal), output=str(self.proposals))
        lock_trigger_proposals(
            decision_id="DECISION_20260814_0001",
            trigger_ids=["TRIGGER_001", "TRIGGER_002"],
            locked_at="2026-08-14T12:00:00Z",
            proposal_path=str(self.proposals),
            decision_journal=str(self.journal),
            ledger=str(self.triggers),
        )
        second = [
            self.proposal("TRIGGER_003", "DECISION_20260901_0002", "0.70", "GROWTH", "2026-09-01T10:00:00Z"),
            self.proposal("TRIGGER_004", "DECISION_20260901_0002", "0.95", "GROWTH", "2026-09-01T10:00:00Z"),
        ]
        write_trigger_proposals(second, decision_journal=str(self.journal), output=str(self.proposals))
        lock_trigger_proposals(
            decision_id="DECISION_20260901_0002",
            trigger_ids=["TRIGGER_003", "TRIGGER_004"],
            locked_at="2026-09-02T12:00:00Z",
            proposal_path=str(self.proposals),
            decision_journal=str(self.journal),
            ledger=str(self.triggers),
        )

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    @staticmethod
    def proposal(
        trigger_id: str,
        decision_id: str,
        probability: str,
        claim_type: str,
        created_at: str,
    ) -> dict[str, object]:
        return {
            "trigger_id": trigger_id,
            "decision_id": decision_id,
            "claim": f"Forward claim {trigger_id}",
            "claim_type": claim_type,
            "material": True,
            "decision_relevant": True,
            "future_facing": True,
            "falsifiable": True,
            "deterministically_resolvable": True,
            "tautological": False,
            "already_known": False,
            "purely_narrative_without_resolution_rule": False,
            "metric_name": "operating_metric",
            "metric_definition_version": "1",
            "source_document_type": "annual_report",
            "source_section": "Financial Review",
            "line_item": "Operating metric",
            "fallback_computation": "NOT_APPLICABLE",
            "tolerance": "0.001",
            "ambiguity_rule": "UNRESOLVABLE_DEFINITION_IF_ISSUER_DEFINITION_CHANGES",
            "operator": ">=",
            "threshold": "0.05",
            "unit": "ratio",
            "probability_holds": probability,
            "expected_resolution_date": "2026-12-15",
            "resolution_deadline": "2027-01-15",
            "policy_version": "FORWARD_VALIDATION_V1",
            "created_at": created_at,
            "source_paths": "reports/research.md",
            "supersedes_trigger_id": "",
        }

    def resolve(self, trigger_id: str, status: str, value: str) -> None:
        append_trigger_resolution(
            trigger_id=trigger_id,
            resolution_status=status,
            resolved_value=value,
            resolution_date="2027-01-16",
            resolution_source="issuer_annual_report",
            resolution_evidence_path=(
                "NOT_APPLICABLE" if status.startswith("UNRESOLVABLE_") else f"evidence/{trigger_id}.pdf"
            ),
            resolution_reason="Human-confirmed test fixture outcome.",
            created_at="2027-01-16T12:00:00Z",
            trigger_ledger=str(self.triggers),
            resolution_ledger=str(self.resolutions),
        )

    def generate_resolved_fixture(self) -> None:
        self.resolve("TRIGGER_001", "RESOLVED_TRUE", "0.06")
        self.resolve("TRIGGER_002", "RESOLVED_FALSE", "0.02")
        self.resolve("TRIGGER_003", "UNRESOLVABLE_DEFINITION", "NOT_APPLICABLE")

    def read_summary(self) -> dict[str, object]:
        return json.loads(self.summary.read_text(encoding="utf-8"))

    def write_outputs(self) -> None:
        write_forward_validation_outputs(
            as_of_date="2027-02-01",
            trigger_ledger=str(self.triggers),
            resolution_ledger=str(self.resolutions),
            decision_journal=str(self.journal),
            summary_output=str(self.summary),
            report_output=str(self.report),
        )

    def test_descriptive_counts_brier_attrition_and_clusters(self) -> None:
        self.generate_resolved_fixture()
        self.write_outputs()
        result = self.read_summary()

        self.assertEqual(result["resolved_trigger_count"], 3)
        self.assertEqual(result["binary_resolved_trigger_count"], 2)
        self.assertEqual(result["resolved_decision_count"], 2)
        self.assertEqual(result["decision_month_count"], 2)
        self.assertEqual(result["true_count"], 1)
        self.assertEqual(result["false_count"], 1)
        self.assertEqual(result["unresolvable_definition_count"], 1)
        self.assertEqual(result["unresolvable_corporate_count"], 0)
        self.assertAlmostEqual(result["unresolvable_rate"], 1 / 3, places=6)
        self.assertEqual(result["open_count"], 1)
        self.assertEqual(result["overdue_count"], 1)
        self.assertEqual(result["overdue_rate"], 1.0)
        self.assertEqual(
            result["rate_confidence_intervals"]["unresolvable_rate"],
            {"estimate": 0.333333, "lower_ci": 0.061492, "method": "WILSON", "n": 3, "upper_ci": 0.79234},
        )
        self.assertEqual(result["rate_confidence_intervals"]["overdue_rate"]["n"], 1)
        self.assertEqual(result["mean_brier_score"], 0.485)
        self.assertEqual(result["triggers_per_decision_distribution"], {"2": 2})
        self.assertEqual(result["cluster_counts"]["raw_trigger_n"], 4)
        self.assertEqual(result["cluster_counts"]["decision_count"], 2)
        self.assertEqual(result["cluster_counts"]["decision_month_count"], 2)
        self.assertEqual(result["cluster_counts"]["empirical_icc_status"], "NOT_ESTIMATED")
        self.assertIsNone(result["cluster_counts"]["effective_n"])

    def test_unresolvable_is_not_coerced_into_brier_or_binary_bins(self) -> None:
        self.generate_resolved_fixture()
        self.write_outputs()
        result = self.read_summary()
        self.assertEqual(sum(result["probability_bin_counts"].values()), 2)
        self.assertEqual(result["mean_brier_score"], 0.485)
        self.assertEqual(result["probability_bin_counts"]["0.50_to_0.75"], 0)

    def test_bins_include_predictions_observations_and_wilson_intervals(self) -> None:
        self.generate_resolved_fixture()
        self.write_outputs()
        result = self.read_summary()
        low = result["confidence_interval_by_bin"]["0.00_to_0.20"]
        middle = result["confidence_interval_by_bin"]["0.35_to_0.50"]
        empty = result["confidence_interval_by_bin"]["0.20_to_0.35"]
        self.assertEqual(low, {"estimate": 1.0, "lower_ci": 0.206549, "method": "WILSON", "n": 1, "upper_ci": 1.0})
        self.assertEqual(middle, {"estimate": 0.0, "lower_ci": 0.0, "method": "WILSON", "n": 1, "upper_ci": 0.793451})
        self.assertEqual(empty["n"], 0)
        self.assertIsNone(empty["estimate"])
        self.assertEqual(result["mean_predicted_probability_by_bin"]["0.00_to_0.20"], 0.1)
        self.assertEqual(result["observed_hold_rate_by_bin"]["0.35_to_0.50"], 0.0)

    def test_trigger_design_diagnostics_do_not_force_probability_mix(self) -> None:
        self.write_outputs()
        result = self.read_summary()
        self.assertEqual(result["share_p_above_0_90"], 0.25)
        self.assertEqual(result["share_p_between_0_35_and_0_75"], 0.5)
        self.assertEqual(result["claim_type_distribution"], {"GROWTH": 2, "MARGIN": 2})
        self.assertEqual(result["trigger_design_status"], "INSUFFICIENT_DATA_FOR_DESIGN_REVIEW")

    def test_persistent_high_probability_concentration_requests_design_review(self) -> None:
        policy = load_yaml_config("configs/forward_validation_policy.yaml")
        policy["reporting_rules"]["trigger_design_review_min_n"] = 4
        policy["reporting_rules"]["trigger_design_review_share_p_above_0_90"] = "0.20"
        result = build_forward_validation_summary(
            trigger_rows=load_trigger_ledger(str(self.triggers)),
            resolution_rows=load_resolution_ledger(str(self.resolutions)),
            decision_rows=read_csv_rows(self.journal),
            policy_config=policy,
            as_of_date="2027-02-01",
        )
        self.assertEqual(result["trigger_design_status"], "TRIGGER_DESIGN_REVIEW")

    def test_report_is_exploratory_and_not_confirmatory(self) -> None:
        self.generate_resolved_fixture()
        self.write_outputs()
        result = self.read_summary()
        report = self.report.read_text(encoding="utf-8")
        self.assertFalse(result["confirmatory_registration_enabled"])
        self.assertEqual(result["inference_mode"], "EXPLORATORY")
        self.assertEqual(result["evidence_status"], "DESCRIPTIVE_ONLY")
        self.assertEqual(result["confirmatory_status"], "INSUFFICIENT_FOR_CONFIRMATORY_INFERENCE")
        self.assertIn("Wilson lower", report)
        for forbidden in ["validated", "proven", "statistically confirmed", "predictive edge"]:
            self.assertNotIn(forbidden, report.lower())

    def test_same_inputs_produce_identical_json_and_markdown(self) -> None:
        self.generate_resolved_fixture()
        self.write_outputs()
        first_summary = self.summary.read_bytes()
        first_report = self.report.read_bytes()
        self.write_outputs()
        self.assertEqual(first_summary, self.summary.read_bytes())
        self.assertEqual(first_report, self.report.read_bytes())

    def test_empty_real_state_is_ready_for_first_real_decision(self) -> None:
        empty_journal = self.tmp / "empty-decisions.csv"
        with empty_journal.open("w", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=["decision_id"]).writeheader()
        missing_triggers = self.tmp / "missing-triggers.csv"
        write_forward_validation_outputs(
            as_of_date="2026-08-14",
            trigger_ledger=str(missing_triggers),
            resolution_ledger=str(self.tmp / "missing-resolutions.csv"),
            decision_journal=str(empty_journal),
            summary_output=str(self.summary),
            report_output=str(self.report),
        )
        result = self.read_summary()
        self.assertEqual(result["operational_forward_validation_status"], "READY_FOR_FIRST_REAL_DECISION")
        self.assertEqual(result["resolved_trigger_count"], 0)
        self.assertIsNone(result["mean_brier_score"])

        result_with_decisions = build_forward_validation_summary(
            trigger_rows=[],
            resolution_rows=[],
            decision_rows=read_csv_rows(self.journal),
            policy_config=load_yaml_config("configs/forward_validation_policy.yaml"),
            as_of_date="2026-08-14",
        )
        self.assertEqual(
            result_with_decisions["operational_forward_validation_status"],
            "READY_FOR_TRIGGER_CAPTURE",
        )

    def test_wilson_validation_and_policy_confirmatory_gate(self) -> None:
        with self.assertRaises(ValueError):
            wilson_interval(2, 1)
        policy = load_yaml_config("configs/forward_validation_policy.yaml")
        policy["confirmatory_registration_enabled"] = True
        with self.assertRaisesRegex(ValueError, "confirmatory_registration_enabled=false"):
            build_forward_validation_summary(
                trigger_rows=[],
                resolution_rows=[],
                decision_rows=[],
                policy_config=policy,
                as_of_date="2026-08-14",
            )

        with self.assertRaisesRegex(ValueError, "absent from Decision Capture"):
            build_forward_validation_summary(
                trigger_rows=load_trigger_ledger(str(self.triggers)),
                resolution_rows=[],
                decision_rows=[],
                policy_config=load_yaml_config("configs/forward_validation_policy.yaml"),
                as_of_date="2026-08-14",
            )

    def test_cli_and_source_have_no_runtime_llm_or_order_dependency(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "src.personal_forward_validation", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        source = Path("src/personal_forward_validation.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("openai", source)
        self.assertNotIn("anthropic", source)
        self.assertNotIn("broker", source)
        self.assertNotIn("order_id", source)


if __name__ == "__main__":
    unittest.main()
