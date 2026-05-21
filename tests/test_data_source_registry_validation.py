from __future__ import annotations

import subprocess
import unittest
from copy import deepcopy
from pathlib import Path

from src.common import load_yaml_config
from src.data_source_registry_validation import DEFAULT_TEMPLATE_PATH, validate_registry_template, validate_registry_template_data


class DataSourceRegistryValidationTests(unittest.TestCase):
    def _template(self) -> dict[str, object]:
        return deepcopy(load_yaml_config(DEFAULT_TEMPLATE_PATH))

    def _first_source(self, **updates: object) -> dict[str, object]:
        template = self._template()
        source = deepcopy(template["sources"][0])
        source.update(updates)
        template["sources"] = [source]
        return template

    def _errors_for(self, data: dict[str, object]) -> str:
        result = validate_registry_template_data(data)
        self.assertEqual(result["status"], "ERROR")
        return "\n".join(result["errors"])

    def test_current_registry_template_is_valid(self) -> None:
        result = validate_registry_template(DEFAULT_TEMPLATE_PATH)
        self.assertEqual(result["status"], "OK")
        self.assertTrue(result["template_only"])
        self.assertEqual(result["source_templates"], 4)
        self.assertEqual(result["errors"], [])

    def test_missing_required_field_is_error(self) -> None:
        template = self._template()
        del template["sources"][0]["source_name"]
        self.assertIn("missing required field: source_name", self._errors_for(template))

    def test_invalid_enums_are_errors(self) -> None:
        template = self._first_source(
            license_classification="REAL_PROVIDER_APPROVED",
            usage_scope="PUBLIC_WORLDWIDE",
            review_status="APPROVED_FOR_PRODUCTION",
        )
        errors = self._errors_for(template)
        self.assertIn("invalid license_classification", errors)
        self.assertIn("invalid usage_scope", errors)
        self.assertIn("invalid review_status", errors)

    def test_template_only_invariant_is_required(self) -> None:
        template = self._template()
        template["template_only"] = False
        self.assertIn("template_only=true", self._errors_for(template))
        del template["template_only"]
        self.assertIn("template_only=true", self._errors_for(template))

    def test_unknown_license_cannot_claim_public_or_commercial_use(self) -> None:
        template = self._first_source(
            source_type="UNKNOWN_REVIEW_REQUIRED",
            license_classification="UNKNOWN_REVIEW_REQUIRED",
            usage_scope="PUBLIC_HANDOFF_DERIVED_ALLOWED",
            redistribution_allowed=True,
            commercial_use_allowed=True,
            review_status="UNKNOWN",
        )
        errors = self._errors_for(template)
        self.assertIn("unknown license cannot claim public", errors)
        self.assertIn("UNKNOWN review_status cannot accompany public", errors)

    def test_paid_broker_and_personal_raw_handoff_are_errors(self) -> None:
        for field in ["contains_paid_data", "contains_broker_data", "contains_personal_data"]:
            with self.subTest(field=field):
                template = self._first_source(**{field: True, "raw_data_handoff_allowed": True})
                self.assertIn("raw data must not be allowed", self._errors_for(template))

    def test_commercial_use_requires_review_status_and_license_evidence(self) -> None:
        template = self._first_source(
            commercial_use_allowed=True,
            review_status="APPROVED_FOR_TEST_FIXTURES",
            license_evidence_files=[],
        )
        self.assertIn("commercial_use_allowed requires", self._errors_for(template))

    def test_redistribution_requires_license_evidence(self) -> None:
        template = self._first_source(
            redistribution_allowed=True,
            evidence_files=[],
            license_evidence_files=[],
        )
        self.assertIn("redistribution_allowed requires explicit license evidence", self._errors_for(template))

    def test_freshness_evidence_is_not_license_evidence(self) -> None:
        template = self._first_source(
            redistribution_allowed=True,
            evidence_files=[],
            license_evidence_files=[],
            freshness_evidence_files=["configs/data_freshness_thresholds.yaml"],
        )
        errors = self._errors_for(template)
        self.assertIn("redistribution_allowed requires explicit license evidence", errors)
        self.assertIn("freshness evidence does not satisfy", errors)

    def test_provider_specific_sources_require_adapter_boundary(self) -> None:
        template = self._first_source(
            source_type="PAID_VENDOR",
            license_classification="PAID_VENDOR",
            adapter_required=False,
        )
        self.assertIn("requires an adapter boundary", self._errors_for(template))

    def test_validation_is_local_structure_only_and_cli_writes_json(self) -> None:
        result = subprocess.run(
            ["python", "-m", "src.data_source_registry_validation", DEFAULT_TEMPLATE_PATH],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"status": "OK"', result.stdout)
        self.assertNotIn("http://", result.stdout)
        self.assertNotIn("https://", result.stdout)


if __name__ == "__main__":
    unittest.main()
