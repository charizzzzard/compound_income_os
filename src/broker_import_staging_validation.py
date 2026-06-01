from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.common import load_yaml_config

DEFAULT_TEMPLATE_PATH = "docs/architecture/CIOS_BROKER_IMPORT_STAGING_TEMPLATE.yaml"

REQUIRED_STAGING_FIELDS = [
    "staging_row_id",
    "source_id",
    "source_document_ref",
    "source_row_ref",
    "broker_account_ref",
    "raw_event_type",
    "raw_asset_name",
    "raw_ticker",
    "raw_isin",
    "raw_wkn",
    "raw_currency",
    "raw_quantity",
    "raw_gross_amount",
    "raw_fee_amount",
    "raw_tax_amount",
    "trade_date",
    "settlement_date",
    "effective_date",
    "proposed_canonical_instrument_id",
    "instrument_match_status",
    "parse_status",
    "validation_status",
    "review_status",
    "review_reason_codes",
    "source_provenance",
    "created_at",
]

ALLOWED_RAW_EVENT_TYPES = {
    "BUY",
    "SELL",
    "DIVIDEND",
    "INTEREST",
    "DEPOSIT",
    "WITHDRAWAL",
    "FEE",
    "TAX",
    "TRANSFER",
    "FX_CONVERSION",
    "CORPORATE_ACTION_REVIEW_REQUIRED",
    "UNKNOWN_REVIEW_REQUIRED",
}

ALLOWED_INSTRUMENT_MATCH_STATUSES = {
    "MATCHED_SYNTHETIC",
    "MATCH_REVIEW_REQUIRED",
    "AMBIGUOUS_REVIEW_REQUIRED",
    "NO_MATCH_REVIEW_REQUIRED",
    "NOT_APPLICABLE",
}

ALLOWED_PARSE_STATUSES = {
    "PARSED_SYNTHETIC",
    "PARSE_REVIEW_REQUIRED",
    "PARSE_FAILED",
    "NOT_PARSED",
}

ALLOWED_VALIDATION_STATUSES = {
    "PASS",
    "REVIEW",
    "FAIL",
    "NOT_EVALUATED",
}

ALLOWED_REVIEW_STATUSES = {
    "READY_FOR_REVIEW",
    "OPERATOR_REVIEW_REQUIRED",
    "INSTRUMENT_REVIEW_REQUIRED",
    "BROKER_MAPPING_REVIEW_REQUIRED",
    "SOURCE_EVIDENCE_REQUIRED",
    "BLOCKED",
}

PROHIBITED_TEMPLATE_STATUSES = {
    "ACTIVE_PRODUCTION",
    "PRODUCTION_APPROVED",
    "BROKER_IMPORT_READY",
    "LEDGER_READY",
    "RUNTIME_APPROVED",
    "INVESTMENT_READY",
    "TRADING_APPROVED",
}

REVIEW_REQUIRED_MATCH_STATUSES = {
    "MATCH_REVIEW_REQUIRED",
    "AMBIGUOUS_REVIEW_REQUIRED",
    "NO_MATCH_REVIEW_REQUIRED",
}

FORBIDDEN_PATH_RE = re.compile(r"(^[a-zA-Z]:)|(^\\\\)|(^/)|(^~)|(^|/)\.\.(/|$)")
REAL_ACCOUNT_RE = re.compile(r"(^DE\d{20}$)|(\d{8,})|(^[A-Z]{2}\d{10,})")


def _string(value: Any) -> str:
    return str(value or "").strip()


def _label(row: dict[str, Any], index: int) -> str:
    return _string(row.get("staging_row_id")) or f"staging_rows[{index}]"


def _add_error(errors: list[str], label: str, message: str) -> None:
    errors.append(f"{label}: {message}")


def _is_neutral(value: Any) -> bool:
    return _string(value) in {"", "TO_BE_REVIEWED", "UNKNOWN", "NOT_APPLICABLE", "TEMPLATE_ONLY"}


def _looks_like_private_path(value: Any) -> bool:
    text = _string(value)
    if not text:
        return False
    normalized = text.replace("\\", "/").lower()
    return (
        bool(FORBIDDEN_PATH_RE.search(text))
        or "data/raw" in normalized
        or "private/" in normalized
        or "broker/" in normalized
        or "broker_statement" in normalized
    )


def _looks_like_real_account_ref(value: Any) -> bool:
    text = _string(value)
    if not text:
        return False
    if text.startswith(("TEMPLATE_", "SYNTHETIC_", "REDACTED_", "NOT_APPLICABLE", "TO_BE_REVIEWED")):
        return False
    return bool(REAL_ACCOUNT_RE.search(text)) or "account" in text.lower()


def _looks_like_real_document_ref(value: Any) -> bool:
    text = _string(value)
    if not text:
        return False
    if text.startswith(("TEMPLATE_", "SYNTHETIC_", "REDACTED_", "TO_BE_REVIEWED")):
        return False
    return bool(re.search(r"\d{6,}", text)) or _looks_like_private_path(text)


def _iter_text_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        values: list[str] = []
        for nested in value.values():
            values.extend(_iter_text_values(nested))
        return values
    if isinstance(value, list):
        values = []
        for nested in value:
            values.extend(_iter_text_values(nested))
        return values
    if isinstance(value, str):
        return [value]
    return []


def _validate_allowed_values(data: dict[str, Any], errors: list[str]) -> None:
    allowed_values = data.get("allowed_values")
    if not isinstance(allowed_values, dict):
        errors.append("template requires allowed_values mapping")
        return

    expected = {
        "raw_event_type": ALLOWED_RAW_EVENT_TYPES,
        "instrument_match_status": ALLOWED_INSTRUMENT_MATCH_STATUSES,
        "parse_status": ALLOWED_PARSE_STATUSES,
        "validation_status": ALLOWED_VALIDATION_STATUSES,
        "review_status": ALLOWED_REVIEW_STATUSES,
    }
    for key, allowed in expected.items():
        values = allowed_values.get(key)
        if not isinstance(values, list):
            errors.append(f"allowed_values.{key} must be a list")
            continue
        invalid = sorted(set(_string(value) for value in values) - allowed)
        missing = sorted(allowed - set(_string(value) for value in values))
        if invalid:
            errors.append(f"allowed_values.{key} contains invalid values: {', '.join(invalid)}")
        if missing:
            errors.append(f"allowed_values.{key} is missing contract values: {', '.join(missing)}")


def _validate_field_definitions(data: dict[str, Any], errors: list[str]) -> None:
    fields = data.get("field_definitions")
    if not isinstance(fields, dict):
        errors.append("template requires field_definitions mapping")
        return
    for field in REQUIRED_STAGING_FIELDS:
        if field not in fields:
            errors.append(f"field_definitions missing required field: {field}")


def _validate_row(row: dict[str, Any], index: int, errors: list[str]) -> str:
    label = _label(row, index)

    for field in REQUIRED_STAGING_FIELDS:
        if field not in row:
            _add_error(errors, label, f"missing required field: {field}")

    for field in ["review_reason_codes", "source_provenance"]:
        if field in row and not isinstance(row.get(field), list):
            _add_error(errors, label, f"{field} must be a list")

    raw_event_type = _string(row.get("raw_event_type"))
    instrument_match_status = _string(row.get("instrument_match_status"))
    parse_status = _string(row.get("parse_status"))
    validation_status = _string(row.get("validation_status"))
    review_status = _string(row.get("review_status"))

    if raw_event_type and raw_event_type not in ALLOWED_RAW_EVENT_TYPES:
        _add_error(errors, label, f"invalid raw_event_type: {raw_event_type}")
    if instrument_match_status and instrument_match_status not in ALLOWED_INSTRUMENT_MATCH_STATUSES:
        _add_error(errors, label, f"invalid instrument_match_status: {instrument_match_status}")
    if parse_status and parse_status not in ALLOWED_PARSE_STATUSES:
        _add_error(errors, label, f"invalid parse_status: {parse_status}")
    if validation_status and validation_status not in ALLOWED_VALIDATION_STATUSES:
        _add_error(errors, label, f"invalid validation_status: {validation_status}")
    if review_status and review_status not in ALLOWED_REVIEW_STATUSES:
        _add_error(errors, label, f"invalid review_status: {review_status}")

    if validation_status == "PASS" and instrument_match_status in REVIEW_REQUIRED_MATCH_STATUSES:
        _add_error(errors, label, "ambiguous or missing instrument match cannot use validation_status PASS")
    if instrument_match_status in REVIEW_REQUIRED_MATCH_STATUSES and review_status not in {
        "OPERATOR_REVIEW_REQUIRED",
        "INSTRUMENT_REVIEW_REQUIRED",
        "BROKER_MAPPING_REVIEW_REQUIRED",
        "SOURCE_EVIDENCE_REQUIRED",
        "BLOCKED",
    }:
        _add_error(errors, label, "ambiguous or missing instrument match requires explicit review status")

    proposed_id = _string(row.get("proposed_canonical_instrument_id"))
    if proposed_id and proposed_id not in {"TO_BE_REVIEWED", "NOT_APPLICABLE"} and not proposed_id.startswith("IM_TEMPLATE_"):
        _add_error(errors, label, "proposed_canonical_instrument_id must remain a template placeholder")
    if instrument_match_status in REVIEW_REQUIRED_MATCH_STATUSES and proposed_id.startswith("IM_TEMPLATE_") and review_status == "READY_FOR_REVIEW":
        _add_error(errors, label, "proposed canonical id is not authoritative when match status requires review")

    if _looks_like_real_account_ref(row.get("broker_account_ref")):
        _add_error(errors, label, "broker_account_ref must be synthetic, redacted or template-only")
    if _looks_like_real_document_ref(row.get("source_document_ref")):
        _add_error(errors, label, "source_document_ref must not look like a real private broker document")

    for text in _iter_text_values(row):
        if _looks_like_private_path(text):
            _add_error(errors, label, "staging sample rows must not contain private/raw/broker paths")
            break

    return _string(row.get("staging_row_id"))


def validate_broker_import_staging_template_data(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return {
            "status": "ERROR",
            "template_only": False,
            "staging_rows": 0,
            "errors": ["broker import staging template root must be a mapping"],
            "warnings": [],
            "non_claims": _non_claims(),
        }

    template_only = data.get("template_only")
    if template_only is not True:
        errors.append("broker import staging template requires template_only=true")

    if "schema_version" not in data:
        errors.append("template requires schema_version")
    if "contract" not in data:
        errors.append("template requires contract")

    maturity = _string(data.get("maturity") or data.get("registry_status") or data.get("current_status") or data.get("status"))
    if maturity in PROHIBITED_TEMPLATE_STATUSES:
        errors.append(f"template-level status must not imply production/runtime approval: {maturity}")
    elif maturity and maturity not in {"TEMPLATE_ONLY", "PREFLIGHT_ONLY", "REVIEW_REQUIRED"}:
        errors.append(f"template-level status is not allowed for staging preflight: {maturity}")

    _validate_allowed_values(data, errors)
    _validate_field_definitions(data, errors)

    rows = data.get("staging_rows")
    if not isinstance(rows, list):
        errors.append("template requires staging_rows list")
        rows = []

    seen_row_ids: dict[str, str] = {}
    for index, raw_row in enumerate(rows):
        if not isinstance(raw_row, dict):
            errors.append(f"staging_rows[{index}]: row must be a mapping")
            continue
        row = deepcopy(raw_row)
        label = _label(row, index)
        row_id = _validate_row(row, index, errors)
        if row_id:
            if row_id in seen_row_ids:
                _add_error(errors, label, f"duplicate staging_row_id also used by {seen_row_ids[row_id]}")
            seen_row_ids[row_id] = label

    return {
        "status": "OK" if not errors else "ERROR",
        "template_only": template_only is True,
        "staging_rows": len(rows),
        "errors": sorted(errors),
        "warnings": sorted(warnings),
        "non_claims": _non_claims(),
    }


def _non_claims() -> list[str]:
    return [
        "staging rows are not accepted ledger events",
        "staging rows are not order instructions",
        "staging rows do not update portfolio state",
        "staging rows do not feed scoring or ranking directly",
        "validation does not create broker import production readiness",
    ]


def validate_broker_import_staging_template(path: str = DEFAULT_TEMPLATE_PATH) -> dict[str, Any]:
    return validate_broker_import_staging_template_data(load_yaml_config(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the CIOS Broker Import Staging template without reading broker, provider or runtime data."
    )
    parser.add_argument("template_path", nargs="?", default=DEFAULT_TEMPLATE_PATH)
    args = parser.parse_args(argv)

    if not Path(args.template_path).exists():
        result = {
            "status": "ERROR",
            "template_only": False,
            "staging_rows": 0,
            "errors": ["template file does not exist"],
            "warnings": [],
            "non_claims": _non_claims(),
        }
    else:
        result = validate_broker_import_staging_template(args.template_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
