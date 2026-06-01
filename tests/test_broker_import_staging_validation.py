from __future__ import annotations

import json
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path

from src.broker_import_staging_validation import (
    DEFAULT_TEMPLATE_PATH,
    validate_broker_import_staging_template,
    validate_broker_import_staging_template_data,
)
from src.common import load_yaml_config


class BrokerImportStagingValidationTests(unittest.TestCase):
    def _template(self) -> dict[str, object]:
        return deepcopy(load_yaml_config(DEFAULT_TEMPLATE_PATH))

    def _first_row(self, **updates: object) -> dict[str, object]:
        template = self._template()
        row = deepcopy(template["staging_rows"][0])
        row.update(updates)
        template["staging_rows"] = [row]
        return template

    def _errors_for(self, data: dict[str, object]) -> str:
        result = validate_broker_import_staging_template_data(data)
        self.assertEqual(result["status"], "ERROR")
        return "\n".join(result["errors"])

    def test_current_broker_import_staging_template_is_valid(self) -> None:
        result = validate_broker_import_staging_template(DEFAULT_TEMPLATE_PATH)
        self.assertEqual(result["status"], "OK")
        self.assertTrue(result["template_only"])
        self.assertEqual(result["staging_rows"], 3)
        self.assertEqual(result["errors"], [])

    def test_production_readiness_overclaims_are_rejected(self) -> None:
        template = self._template()
        template["maturity"] = "BROKER_IMPORT_READY"
        self.assertIn("must not imply production/runtime approval", self._errors_for(template))

    def test_real_looking_private_broker_account_data_is_rejected(self) -> None:
        cases = [
            ("broker_account_ref", "DE12345678901234567890"),
            ("broker_account_ref", "123456789"),
            ("source_document_ref", "broker_statement_20240101123456.pdf"),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                self.assertIn("must", self._errors_for(self._first_row(**{field: value})))

    def test_unknown_raw_event_type_is_rejected(self) -> None:
        template = self._first_row(raw_event_type="BROKER_MAGIC_EVENT")
        self.assertIn("invalid raw_event_type", self._errors_for(template))

    def test_ambiguous_or_no_match_instrument_status_requires_review(self) -> None:
        template = self._first_row(
            instrument_match_status="AMBIGUOUS_REVIEW_REQUIRED",
            validation_status="PASS",
            review_status="READY_FOR_REVIEW",
        )
        errors = self._errors_for(template)
        self.assertIn("cannot use validation_status PASS", errors)
        self.assertIn("requires explicit review status", errors)

    def test_pass_instrument_bearing_rows_require_synthetic_match_id(self) -> None:
        cases = [
            (
                {
                    "raw_event_type": "BUY",
                    "validation_status": "PASS",
                    "instrument_match_status": "MATCHED_SYNTHETIC",
                    "proposed_canonical_instrument_id": "TO_BE_REVIEWED",
                },
                "require IM_TEMPLATE_ proposed_canonical_instrument_id",
            ),
            (
                {
                    "raw_event_type": "BUY",
                    "validation_status": "PASS",
                    "instrument_match_status": "NOT_APPLICABLE",
                    "proposed_canonical_instrument_id": "NOT_APPLICABLE",
                },
                "cannot use instrument_match_status NOT_APPLICABLE",
            ),
            (
                {
                    "raw_event_type": "BUY",
                    "validation_status": "PASS",
                    "instrument_match_status": "MATCHED_SYNTHETIC",
                    "proposed_canonical_instrument_id": "",
                },
                "require IM_TEMPLATE_ proposed_canonical_instrument_id",
            ),
        ]
        for updates, expected in cases:
            with self.subTest(updates=updates):
                self.assertIn(expected, self._errors_for(self._first_row(**updates)))

    def test_cli_returns_nonzero_for_weak_pass_match(self) -> None:
        template = self._first_row(
            validation_status="PASS",
            instrument_match_status="MATCHED_SYNTHETIC",
            proposed_canonical_instrument_id="TO_BE_REVIEWED",
        )
        fixture_path = Path("tests") / "broker_import_staging_invalid_fixture.json"
        fixture_path.write_text(json.dumps(template), encoding="utf-8")
        try:
            result = subprocess.run(
                ["python", "-m", "src.broker_import_staging_validation", str(fixture_path)],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )
        finally:
            fixture_path.unlink(missing_ok=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('"status": "ERROR"', result.stdout)

    def test_path_boundaries_are_rejected(self) -> None:
        cases = [
            "C:/Users/operator/broker.csv",
            "\\\\server\\share\\broker.csv",
            "C:relative/broker.csv",
            "../private/broker.csv",
            "data/raw/private/broker.csv",
        ]
        for value in cases:
            with self.subTest(value=value):
                template = self._first_row(source_provenance=[value])
                self.assertIn("must not contain private/raw/broker paths", self._errors_for(template))

    def test_staging_rows_do_not_become_accepted_ledger_events(self) -> None:
        result = validate_broker_import_staging_template(DEFAULT_TEMPLATE_PATH)
        non_claims = "\n".join(result["non_claims"])
        self.assertIn("staging rows are not accepted ledger events", non_claims)
        self.assertIn("staging rows are not order instructions", non_claims)
        self.assertIn("staging rows do not update portfolio state", non_claims)
        self.assertIn("staging rows do not feed scoring or ranking directly", non_claims)

    def test_contract_documents_non_scope_boundaries(self) -> None:
        contract = Path("docs/contracts/BROKER_IMPORT_STAGING_CONTRACT.md").read_text(encoding="utf-8")
        for phrase in [
            "broker writes",
            "order execution",
            "live trading",
            "buy/sell automation",
            "production Portfolio Event Ledger",
            "replay",
            "backtesting",
            "outcome attribution",
            "investment advice",
            "production readiness",
            "investment readiness",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, contract)

    def test_validation_is_local_structure_only_and_cli_writes_json(self) -> None:
        result = subprocess.run(
            ["python", "-m", "src.broker_import_staging_validation", DEFAULT_TEMPLATE_PATH],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"status": "OK"', result.stdout)
        self.assertNotIn("http://", result.stdout)
        self.assertNotIn("https://", result.stdout)

    def test_validator_module_uses_no_network_or_process_imports(self) -> None:
        source = Path("src/broker_import_staging_validation.py").read_text(encoding="utf-8")
        for forbidden in ["import requests", "import urllib", "import httpx", "import socket", "import subprocess"]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
