from __future__ import annotations

import subprocess
import unittest
from copy import deepcopy
from pathlib import Path

from src.common import load_yaml_config
from src.instrument_master_validation import (
    DEFAULT_TEMPLATE_PATH,
    validate_instrument_master_template,
    validate_instrument_master_template_data,
)


class InstrumentMasterValidationTests(unittest.TestCase):
    def _template(self) -> dict[str, object]:
        return deepcopy(load_yaml_config(DEFAULT_TEMPLATE_PATH))

    def _first_instrument(self, **updates: object) -> dict[str, object]:
        template = self._template()
        entry = deepcopy(template["instrument_templates"][0])
        entry.update(updates)
        template["instrument_templates"] = [entry]
        return template

    def _errors_for(self, data: dict[str, object]) -> str:
        result = validate_instrument_master_template_data(data)
        self.assertEqual(result["status"], "ERROR")
        return "\n".join(result["errors"])

    def test_current_instrument_master_template_is_valid(self) -> None:
        result = validate_instrument_master_template(DEFAULT_TEMPLATE_PATH)
        self.assertEqual(result["status"], "OK")
        self.assertTrue(result["template_only"])
        self.assertEqual(result["instrument_templates"], 4)
        self.assertEqual(result["errors"], [])

    def test_duplicate_canonical_ids_are_errors(self) -> None:
        template = self._template()
        template["instrument_templates"][1]["canonical_instrument_id"] = template["instrument_templates"][0]["canonical_instrument_id"]
        self.assertIn("duplicate canonical_instrument_id", self._errors_for(template))

    def test_duplicate_primary_identifiers_are_errors(self) -> None:
        template = self._template()
        for entry in template["instrument_templates"][:2]:
            entry["primary_identifier_type"] = "ISIN"
            entry["primary_identifier_value"] = "XS0000000001"
        errors = self._errors_for(template)
        self.assertIn("duplicate primary identifier", errors)
        self.assertIn("duplicate ISIN", errors)

    def test_ticker_only_identity_is_rejected(self) -> None:
        template = self._first_instrument(
            primary_identifier_type="TICKER",
            primary_identifier_value="SYN",
            identifiers=[{"identifier_type": "TICKER", "identifier_value": "SYN"}],
        )
        errors = self._errors_for(template)
        self.assertIn("invalid primary_identifier_type", errors)
        self.assertIn("ticker alone is never sufficient", errors)
        self.assertIn("ticker identifiers are aliases", errors)

    def test_production_readiness_overclaims_are_rejected(self) -> None:
        template = self._template()
        template["registry_status"] = "ACTIVE_PRODUCTION"
        self.assertIn("must not imply production/runtime approval", self._errors_for(template))

        template = self._first_instrument(lifecycle_status="ACTIVE", identity_confidence="HIGH", review_status="APPROVED_FOR_LOCAL_USE")
        errors = self._errors_for(template)
        self.assertIn("must not claim high confidence", errors)
        self.assertIn("approved local runtime identity", errors)

    def test_local_absolute_and_private_paths_are_rejected(self) -> None:
        template = self._first_instrument(evidence_files=["C:/Users/operator/private/broker.csv"])
        self.assertIn("must not contain private paths", self._errors_for(template))

    def test_validation_non_claims_do_not_imply_runtime_or_advice(self) -> None:
        result = validate_instrument_master_template(DEFAULT_TEMPLATE_PATH)
        non_claims = "\n".join(result["non_claims"])
        self.assertIn("validation does not approve broker import", non_claims)
        self.assertIn("validation does not approve trading", non_claims)
        self.assertIn("validation does not create investment readiness", non_claims)
        self.assertIn("validation does not create production readiness", non_claims)

    def test_validation_is_local_structure_only_and_cli_writes_json(self) -> None:
        result = subprocess.run(
            ["python", "-m", "src.instrument_master_validation", DEFAULT_TEMPLATE_PATH],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"status": "OK"', result.stdout)
        self.assertNotIn("http://", result.stdout)
        self.assertNotIn("https://", result.stdout)

    def test_validator_module_uses_no_network_or_process_imports(self) -> None:
        source = Path("src/instrument_master_validation.py").read_text(encoding="utf-8")
        for forbidden in ["import requests", "import urllib", "import httpx", "import socket", "import subprocess"]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
