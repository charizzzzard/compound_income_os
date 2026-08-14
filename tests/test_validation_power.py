from __future__ import annotations

import math
from pathlib import Path
import subprocess
import sys
import unittest

from src.common import load_yaml_config
from src.validation_power import (
    POWER_PLANNING_APPROXIMATION,
    cluster_design_effect,
    effective_n_from_design_effect,
    minimum_detectable_mean_effect,
    required_n_correlation,
    required_n_mean,
)


class ValidationPowerTests(unittest.TestCase):
    def test_forward_validation_policy_is_json_compatible_and_confirmatory_disabled(self) -> None:
        policy = load_yaml_config("configs/forward_validation_policy.yaml")
        self.assertFalse(policy["confirmatory_registration_enabled"])
        self.assertEqual(policy["operational_forward_validation_status"], "READY_FOR_FIRST_REAL_DECISION")
        self.assertEqual(policy["trigger_policy"]["min_triggers_per_decision"], 2)
        self.assertEqual(policy["trigger_policy"]["max_triggers_per_decision"], 5)
        self.assertIsNone(policy["power_defaults"]["icc_default"])

    def test_contracts_preserve_exploratory_and_no_runtime_llm_boundaries(self) -> None:
        architecture = Path("docs/architecture/CIOS_FORWARD_VALIDATION_V1.md").read_text(encoding="utf-8")
        experiment = Path("docs/contracts/FORWARD_EXPERIMENT_CONTRACT_V1.md").read_text(encoding="utf-8")
        trigger = Path("docs/contracts/DECISION_FALSIFICATION_TRIGGER_CONTRACT_V1.md").read_text(encoding="utf-8")
        normalized_experiment = " ".join(experiment.split())
        self.assertIn("confirmatory_registration_enabled = false", architecture)
        self.assertIn("OUT_OF_SCOPE_V1", architecture)
        self.assertIn("primarily forward-only", architecture)
        self.assertIn("does not implement an experiment registry", normalized_experiment)
        self.assertIn("tamper-evident, not tamper-proof", trigger)

    def test_one_sample_mean_reference_values(self) -> None:
        expected = {0.30: 785, 0.34: 1008, 0.40: 1395}
        for sigma, reference in expected.items():
            with self.subTest(sigma=sigma):
                result = required_n_mean(0.03, sigma, test_type="one_sample")
                self.assertEqual(result["test_type"], "one_sample")
                self.assertNotIn("n_per_group", result)
                self.assertLessEqual(abs(result["n_total"] - reference), 1)

    def test_two_sample_mean_has_explicit_per_group_and_total_semantics(self) -> None:
        expected = {0.30: 1570, 0.40: 2791}
        for sigma, n_per_group in expected.items():
            with self.subTest(sigma=sigma):
                result = required_n_mean(0.03, sigma, test_type="two_sample")
                self.assertEqual(result["n_per_group"], n_per_group)
                self.assertEqual(result["n_total"], 2 * n_per_group)
                self.assertTrue(result["equal_group_sizes"])

    def test_mde_inverts_mean_planning_approximately(self) -> None:
        plan = required_n_mean(0.03, 0.30, test_type="one_sample")
        mde = minimum_detectable_mean_effect(plan["n_total"], 0.30, test_type="one_sample")
        self.assertLessEqual(mde["minimum_detectable_effect"], 0.03)
        self.assertGreater(mde["minimum_detectable_effect"], 0.0299)

        two_sample = minimum_detectable_mean_effect(3140, 0.30, test_type="two_sample")
        self.assertEqual(two_sample["n_per_group"], 1570)
        self.assertAlmostEqual(two_sample["minimum_detectable_effect"], 0.03, places=5)

    def test_two_sample_mde_rejects_odd_total(self) -> None:
        with self.assertRaisesRegex(ValueError, "even"):
            minimum_detectable_mean_effect(101, 0.30, test_type="two_sample")

    def test_correlation_methods_are_semantically_distinct(self) -> None:
        pearson = required_n_correlation(0.05, method="pearson")
        spearman = required_n_correlation(0.05, method="spearman")

        self.assertGreater(pearson["n_total"], 3100)
        self.assertGreaterEqual(spearman["n_total"], pearson["n_total"])
        self.assertEqual(pearson["variance_inflation"], 1.0)
        self.assertAlmostEqual(spearman["variance_inflation"], 1.0 + 0.05**2 / 2.0)
        self.assertEqual(pearson["planning_status"], POWER_PLANNING_APPROXIMATION)
        self.assertFalse(pearson["exact_inferential_test"])

    def test_cluster_design_effect_requires_explicit_valid_icc(self) -> None:
        with self.assertRaises(TypeError):
            cluster_design_effect(4)  # type: ignore[call-arg]
        self.assertAlmostEqual(cluster_design_effect(4, icc=0.3), 1.9)
        self.assertAlmostEqual(effective_n_from_design_effect(100, 1.9), 100 / 1.9)
        with self.assertRaises(ValueError):
            cluster_design_effect(4, icc=-0.1)
        with self.assertRaises(ValueError):
            effective_n_from_design_effect(100, 0.9)

    def test_invalid_inputs_fail_fast(self) -> None:
        invalid_calls = [
            lambda: required_n_mean(0.0, 0.3),
            lambda: required_n_mean(0.03, math.nan),
            lambda: required_n_mean(0.03, 0.3, alpha=1.0),
            lambda: required_n_mean(0.03, 0.3, power=0.0),
            lambda: required_n_mean(0.03, 0.3, test_type="paired"),
            lambda: required_n_correlation(0.0),
            lambda: required_n_correlation(1.0),
            lambda: required_n_correlation(0.1, method="kendall"),
        ]
        for call in invalid_calls:
            with self.subTest(call=call):
                with self.assertRaises(ValueError):
                    call()

    def test_cli_emits_structured_json(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.validation_power",
                "mean",
                "--effect",
                "0.03",
                "--sigma",
                "0.30",
                "--test-type",
                "two_sample",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('"n_per_group": 1570', completed.stdout)
        self.assertIn('"n_total": 3140', completed.stdout)


if __name__ == "__main__":
    unittest.main()
