from __future__ import annotations

import subprocess
import unittest
from copy import deepcopy
from pathlib import Path

from src.common import load_yaml_config
from src.portfolio_event_ledger_validation import (
    DEFAULT_TEMPLATE_PATH,
    validate_portfolio_event_ledger_template,
    validate_portfolio_event_ledger_template_data,
)


class PortfolioEventLedgerValidationTests(unittest.TestCase):
    def _template(self) -> dict[str, object]:
        return deepcopy(load_yaml_config(DEFAULT_TEMPLATE_PATH))

    def _first_event(self, **updates: object) -> dict[str, object]:
        template = self._template()
        event = deepcopy(template["event_templates"][0])
        event.update(updates)
        template["event_templates"] = [event]
        return template

    def _event_by_type(self, event_type: str, **updates: object) -> dict[str, object]:
        template = self._template()
        for event in template["event_templates"]:
            if event["event_type"] == event_type:
                entry = deepcopy(event)
                entry.update(updates)
                template["event_templates"] = [entry]
                return template
        self.fail(f"missing event template type: {event_type}")

    def _errors_for(self, data: dict[str, object]) -> str:
        result = validate_portfolio_event_ledger_template_data(data)
        self.assertEqual(result["status"], "ERROR")
        return "\n".join(result["errors"])

    def test_current_portfolio_event_ledger_template_is_valid(self) -> None:
        result = validate_portfolio_event_ledger_template(DEFAULT_TEMPLATE_PATH)
        self.assertEqual(result["status"], "OK")
        self.assertTrue(result["template_only"])
        self.assertGreater(result["event_templates"], 0)
        self.assertEqual(result["errors"], [])

    def test_template_only_invariant_is_required(self) -> None:
        template = self._template()
        del template["template_only"]
        self.assertIn("template_only=true", self._errors_for(template))

        template = self._template()
        template["template_only"] = False
        self.assertIn("template_only=true", self._errors_for(template))

    def test_missing_required_field_is_error(self) -> None:
        template = self._template()
        del template["event_templates"][0]["event_id"]
        self.assertIn("missing required field: event_id", self._errors_for(template))

    def test_invalid_enums_are_errors(self) -> None:
        cases = [
            ("event_type", "BUY_REAL"),
            ("event_status", "APPROVED_FOR_PRODUCTION"),
            ("validation_status", "PRODUCTION_VALID"),
            ("review_status", "LEGALLY_APPROVED"),
            ("quantity_unit", "REAL_SHARES"),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                template = self._first_event(**{field: value})
                self.assertIn(f"invalid {field}", self._errors_for(template))

    def test_accepted_and_valid_template_statuses_are_errors(self) -> None:
        cases = [
            ("event_status", "ACCEPTED", "ACCEPTED or VALIDATED"),
            ("event_status", "VALIDATED", "ACCEPTED or VALIDATED"),
            ("validation_status", "VALID", "validation_status VALID"),
            ("review_status", "ACCEPTED_FOR_LOCAL_USE", "ACCEPTED_FOR_LOCAL_USE"),
        ]
        for field, value, expected in cases:
            with self.subTest(field=field, value=value):
                template = self._first_event(**{field: value})
                self.assertIn(expected, self._errors_for(template))

    def test_real_looking_broker_and_account_ids_are_errors(self) -> None:
        cases = [
            ("source_event_id", "TRX-123456789"),
            ("broker_or_source_account_id", "BROKER-ACCOUNT-1"),
            ("portfolio_id", "REAL_PORTFOLIO_1"),
            ("account_id", "REAL_ACCOUNT_1"),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                template = self._first_event(**{field: value})
                self.assertIn("must", self._errors_for(template))

    def test_real_numeric_amounts_are_errors(self) -> None:
        for field in ["gross_amount", "net_amount", "fee_amount", "tax_amount", "fx_rate"]:
            with self.subTest(field=field):
                template = self._first_event(**{field: 123.45})
                self.assertIn(f"{field} must be neutral", self._errors_for(template))

    def test_real_looking_canonical_instrument_id_is_error(self) -> None:
        template = self._first_event(canonical_instrument_id="US0378331005")
        self.assertIn("canonical_instrument_id must be neutral", self._errors_for(template))

    def test_buy_requires_quantity_and_instrument_placeholder(self) -> None:
        template = self._first_event(quantity=None)
        self.assertIn("BUY requires quantity", self._errors_for(template))

        template = self._first_event(canonical_instrument_id="NOT_APPLICABLE")
        self.assertIn("BUY requires canonical_instrument_id", self._errors_for(template))

    def test_deposit_requires_not_applicable_instrument_reference(self) -> None:
        template = self._event_by_type("DEPOSIT", canonical_instrument_id="TO_BE_REVIEWED")
        self.assertIn("DEPOSIT cash-only template requires canonical_instrument_id NOT_APPLICABLE", self._errors_for(template))

    def test_fx_conversion_requires_direction_and_review_boundary(self) -> None:
        template = self._event_by_type(
            "FX_CONVERSION",
            fx_from_currency=None,
            fx_to_currency=None,
            fx_rate_convention="NOT_APPLICABLE",
            fx_rate_direction="NOT_APPLICABLE",
            fx_rate_review_status="NOT_APPLICABLE",
        )
        errors = self._errors_for(template)
        self.assertIn("FX_CONVERSION requires fx_from_currency", errors)
        self.assertIn("FX_CONVERSION requires fx_to_currency", errors)
        self.assertIn("FX_CONVERSION requires rate convention/direction or FX review", errors)

    def test_transfer_requires_account_boundary_or_review(self) -> None:
        template = self._first_event(
            event_type="TRANSFER_IN",
            source_account_id="NOT_APPLICABLE",
            target_account_id="NOT_APPLICABLE",
            transfer_review_status="NOT_APPLICABLE",
            quantity_unit="UNITS",
        )
        self.assertIn("TRANSFER_IN requires source/target account boundary or transfer review", self._errors_for(template))

    def test_correction_reversal_and_supersession_require_structured_review(self) -> None:
        cases = [
            ("correction_of_event_id", "correction_reason", "correction_review_status"),
            ("reversal_of_event_id", "reversal_reason", "reversal_review_status"),
            ("supersedes_event_id", "supersession_reason", "supersession_review_status"),
        ]
        for event_field, reason_field, status_field in cases:
            with self.subTest(event_field=event_field):
                template = self._first_event(
                    **{
                        event_field: "PEL_TEMPLATE_PRIOR_EVENT",
                        reason_field: "NOT_APPLICABLE",
                        status_field: "NOT_APPLICABLE",
                    }
                )
                errors = self._errors_for(template)
                self.assertIn(f"{event_field} requires {reason_field}", errors)
                self.assertIn(f"{event_field} requires review-required {status_field}", errors)

    def test_license_or_freshness_evidence_is_not_event_evidence(self) -> None:
        template = self._first_event(
            evidence_files=[
                "docs/contracts/DATA_SOURCE_LICENSE_BOUNDARY_CONTRACT.md",
                "docs/contracts/DATA_FRESHNESS_STALENESS_CONTRACT.md",
            ]
        )
        result = validate_portfolio_event_ledger_template_data(template)
        self.assertEqual(result["status"], "OK")
        self.assertTrue(any("does not by itself satisfy event evidence" in warning for warning in result["warnings"]))

    def test_validation_is_local_structure_only_and_cli_writes_json(self) -> None:
        result = subprocess.run(
            ["python", "-m", "src.portfolio_event_ledger_validation", DEFAULT_TEMPLATE_PATH],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"status": "OK"', result.stdout)
        self.assertNotIn("http://", result.stdout)
        self.assertNotIn("https://", result.stdout)

    def test_validator_module_uses_no_network_or_process_imports(self) -> None:
        source = Path("src/portfolio_event_ledger_validation.py").read_text(encoding="utf-8")
        for forbidden in ["import requests", "import urllib", "import httpx", "import socket", "import subprocess"]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
