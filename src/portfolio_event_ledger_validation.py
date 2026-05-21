from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.common import load_yaml_config

DEFAULT_TEMPLATE_PATH = "docs/architecture/CIOS_PORTFOLIO_EVENT_LEDGER_TEMPLATE.yaml"

ALLOWED_EVENT_TYPES = {
    "BUY",
    "SELL",
    "DIVIDEND",
    "INTEREST",
    "DEPOSIT",
    "WITHDRAWAL",
    "FEE",
    "TAX",
    "TRANSFER_IN",
    "TRANSFER_OUT",
    "CASH_ADJUSTMENT",
    "FX_CONVERSION",
    "SPLIT",
    "MERGER",
    "SPINOFF",
    "RETURN_OF_CAPITAL",
    "DISTRIBUTION",
    "CORPORATE_ACTION_REVIEW_REQUIRED",
    "MANUAL_ADJUSTMENT_REVIEW_REQUIRED",
    "UNKNOWN_REVIEW_REQUIRED",
}

ALLOWED_EVENT_STATUSES = {
    "DRAFT",
    "IMPORTED_UNREVIEWED",
    "OPERATOR_REVIEW_REQUIRED",
    "VALIDATED",
    "ACCEPTED",
    "SUPERSEDED",
    "CORRECTED",
    "REVERSED",
    "REJECTED",
    "UNKNOWN",
}

ALLOWED_VALIDATION_STATUSES = {
    "VALID",
    "WARNING",
    "REVIEW_REQUIRED",
    "ERROR",
    "NOT_EVALUATED",
}

ALLOWED_REVIEW_STATUSES = {
    "OPERATOR_REVIEW_REQUIRED",
    "EVIDENCE_REQUIRED",
    "INSTRUMENT_REVIEW_REQUIRED",
    "CASH_REVIEW_REQUIRED",
    "FX_REVIEW_REQUIRED",
    "CORPORATE_ACTION_REVIEW_REQUIRED",
    "TAX_REVIEW_REQUIRED",
    "BROKER_MAPPING_REVIEW_REQUIRED",
    "ACCEPTED_FOR_LOCAL_USE",
    "REJECTED",
    "UNKNOWN",
}

ALLOWED_QUANTITY_UNITS = {
    "SHARES",
    "UNITS",
    "CURRENCY",
    "CONTRACTS",
    "NOT_APPLICABLE",
    "UNKNOWN_REVIEW_REQUIRED",
}

ALLOWED_FX_REVIEW_STATUSES = ALLOWED_REVIEW_STATUSES | {"REVIEW_REQUIRED", "NOT_APPLICABLE"}
ALLOWED_TRANSFER_REVIEW_STATUSES = ALLOWED_REVIEW_STATUSES | {"REVIEW_REQUIRED", "NOT_APPLICABLE"}

REVIEW_REQUIRED_STATUSES = {
    "OPERATOR_REVIEW_REQUIRED",
    "EVIDENCE_REQUIRED",
    "INSTRUMENT_REVIEW_REQUIRED",
    "CASH_REVIEW_REQUIRED",
    "FX_REVIEW_REQUIRED",
    "CORPORATE_ACTION_REVIEW_REQUIRED",
    "TAX_REVIEW_REQUIRED",
    "BROKER_MAPPING_REVIEW_REQUIRED",
    "REVIEW_REQUIRED",
    "UNKNOWN",
}

REQUIRED_EVENT_FIELDS = [
    "event_id",
    "event_type",
    "event_status",
    "portfolio_id",
    "account_id",
    "broker_or_source_account_id",
    "canonical_instrument_id",
    "instrument_identity_status",
    "event_time",
    "trade_date",
    "settlement_date",
    "effective_date",
    "recorded_at",
    "as_of_date",
    "quantity",
    "quantity_unit",
    "gross_amount",
    "net_amount",
    "fee_amount",
    "tax_amount",
    "transaction_currency",
    "cash_currency",
    "base_currency",
    "fx_rate",
    "fx_rate_source",
    "fx_rate_as_of_date",
    "source_id",
    "source_event_id",
    "source_document_ref",
    "source_row_ref",
    "source_provenance",
    "evidence_files",
    "license_boundary_refs",
    "data_freshness_refs",
    "correction_of_event_id",
    "reversal_of_event_id",
    "supersedes_event_id",
    "predecessor_event_ids",
    "successor_event_ids",
    "validation_status",
    "review_status",
    "created_at",
    "updated_at",
    "owner",
    "known_limitations",
    "notes",
    "correction_reason",
    "reversal_reason",
    "supersession_reason",
    "correction_review_status",
    "reversal_review_status",
    "supersession_review_status",
    "correction_evidence_files",
    "reversal_evidence_files",
    "supersession_evidence_files",
    "fx_from_currency",
    "fx_to_currency",
    "fx_rate_convention",
    "fx_rate_direction",
    "fx_rate_includes_spread",
    "fx_rate_review_status",
    "source_account_id",
    "target_account_id",
    "transfer_direction",
    "transfer_pair_id",
    "transfer_review_status",
]

LIST_FIELDS = {
    "source_provenance",
    "evidence_files",
    "license_boundary_refs",
    "data_freshness_refs",
    "predecessor_event_ids",
    "successor_event_ids",
    "known_limitations",
    "correction_evidence_files",
    "reversal_evidence_files",
    "supersession_evidence_files",
}

AMOUNT_FIELDS = {"gross_amount", "net_amount", "fee_amount", "tax_amount", "fx_rate"}
CORPORATE_ACTION_EVENT_TYPES = {
    "SPLIT",
    "MERGER",
    "SPINOFF",
    "RETURN_OF_CAPITAL",
    "CORPORATE_ACTION_REVIEW_REQUIRED",
}
REQUIRED_MATRIX_SECTIONS = {
    "required_by_event_type",
    "review_required_by_event_type",
}

NEUTRAL_VALUES = {
    None,
    "",
    "TO_BE_REVIEWED",
    "REVIEW_REQUIRED",
    "UNKNOWN",
    "UNKNOWN_REVIEW_REQUIRED",
    "NOT_APPLICABLE",
    "TEMPLATE_ONLY",
}

ALLOWED_CANONICAL_PLACEHOLDERS = {"TO_BE_REVIEWED", "NOT_APPLICABLE", "TEMPLATE_ONLY"}


def _string(value: Any) -> str:
    return str(value or "").strip()


def _event_label(entry: dict[str, Any], index: int) -> str:
    return _string(entry.get("template_id") or entry.get("event_id")) or f"event_template[{index}]"


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _is_set(value: Any) -> bool:
    return not _is_missing(value) and value not in {"NOT_APPLICABLE", "UNKNOWN"}


def _is_neutral(value: Any) -> bool:
    if value in NEUTRAL_VALUES:
        return True
    if isinstance(value, str):
        return value.startswith(("TEMPLATE_", "PEL_TEMPLATE_", "IM_TEMPLATE_"))
    return False


def _add_error(errors: list[str], label: str, message: str) -> None:
    errors.append(f"{label}: {message}")


def _validate_allowed_values(data: dict[str, Any], errors: list[str]) -> None:
    allowed_values = data.get("allowed_values")
    if not isinstance(allowed_values, dict):
        errors.append("template requires allowed_values mapping")
        return

    expected = {
        "event_type": ALLOWED_EVENT_TYPES,
        "event_status": ALLOWED_EVENT_STATUSES,
        "validation_status": ALLOWED_VALIDATION_STATUSES,
        "review_status": ALLOWED_REVIEW_STATUSES,
        "quantity_unit": ALLOWED_QUANTITY_UNITS,
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


def _validate_matrix_sections(data: dict[str, Any], errors: list[str]) -> None:
    for section in REQUIRED_MATRIX_SECTIONS:
        value = data.get(section)
        if not isinstance(value, dict):
            errors.append(f"template requires {section} mapping")
            continue
        missing_event_types = sorted(ALLOWED_EVENT_TYPES - set(value.keys()))
        if missing_event_types:
            errors.append(f"{section} must cover all event types; missing: {', '.join(missing_event_types)}")

    if not isinstance(data.get("nullable_by_event_type"), dict) and not isinstance(data.get("not_applicable_by_event_type"), dict):
        errors.append("template requires nullable_by_event_type or not_applicable_by_event_type mapping")
        return
    for section in ["nullable_by_event_type", "not_applicable_by_event_type"]:
        value = data.get(section)
        if isinstance(value, dict):
            missing_event_types = sorted(ALLOWED_EVENT_TYPES - set(value.keys()))
            if missing_event_types:
                errors.append(f"{section} must cover all event types; missing: {', '.join(missing_event_types)}")


def _looks_like_real_identifier(value: Any, allowed_prefixes: tuple[str, ...]) -> bool:
    text = _string(value)
    if not text or text in {"TO_BE_REVIEWED", "UNKNOWN", "NOT_APPLICABLE", "TEMPLATE_ONLY", "REVIEW_REQUIRED"}:
        return False
    if text.startswith(allowed_prefixes):
        return False
    return True


def _validate_entry_safety(entry: dict[str, Any], label: str, errors: list[str]) -> None:
    if entry.get("event_status") in {"ACCEPTED", "VALIDATED"}:
        _add_error(errors, label, "template entries must not use ACCEPTED or VALIDATED event_status")
    if entry.get("validation_status") == "VALID":
        _add_error(errors, label, "template entries must not use validation_status VALID")
    if entry.get("review_status") == "ACCEPTED_FOR_LOCAL_USE":
        _add_error(errors, label, "template entries must not use ACCEPTED_FOR_LOCAL_USE")

    for field in AMOUNT_FIELDS:
        value = entry.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            _add_error(errors, label, f"{field} must be neutral in template entries")
        elif isinstance(value, str):
            try:
                float(value)
            except ValueError:
                pass
            else:
                _add_error(errors, label, f"{field} must be neutral in template entries")

    if _looks_like_real_identifier(entry.get("portfolio_id"), ("TEMPLATE_",)):
        _add_error(errors, label, "portfolio_id must be a template placeholder")
    if _looks_like_real_identifier(entry.get("account_id"), ("TEMPLATE_",)):
        _add_error(errors, label, "account_id must be a template placeholder")
    if _looks_like_real_identifier(entry.get("broker_or_source_account_id"), ("TEMPLATE_",)):
        _add_error(errors, label, "broker_or_source_account_id must be neutral or template-only")
    if _looks_like_real_identifier(entry.get("source_event_id"), ("PEL_TEMPLATE_", "TEMPLATE_")):
        _add_error(errors, label, "source_event_id must not look like a real broker/source event id")
    if _looks_like_real_identifier(entry.get("canonical_instrument_id"), ("IM_TEMPLATE_",)):
        _add_error(errors, label, "canonical_instrument_id must be neutral or an instrument template placeholder")

    for field in ["source_document_ref", "source_row_ref"]:
        text = _string(entry.get(field)).lower()
        if "data/raw" in text or "private" in text or "broker_statement" in text or "c:\\users" in text:
            _add_error(errors, label, f"{field} must not reference private/raw broker data")


def _validate_required_fields(entry: dict[str, Any], label: str, event_type: str, data: dict[str, Any], errors: list[str]) -> None:
    missing = [field for field in REQUIRED_EVENT_FIELDS if field not in entry]
    for field in missing:
        _add_error(errors, label, f"missing required field: {field}")

    required_by_type = data.get("required_by_event_type", {})
    if isinstance(required_by_type, dict):
        for field in required_by_type.get(event_type, []):
            if field not in entry or _is_missing(entry.get(field)):
                _add_error(errors, label, f"{event_type} requires {field}")

    for field in LIST_FIELDS:
        if field in entry and not isinstance(entry.get(field), list):
            _add_error(errors, label, f"{field} must be a list")


def _validate_entry_enums(entry: dict[str, Any], label: str, errors: list[str]) -> str:
    event_type = _string(entry.get("event_type"))
    if event_type not in ALLOWED_EVENT_TYPES:
        _add_error(errors, label, f"invalid event_type: {event_type}")

    event_status = _string(entry.get("event_status"))
    if event_status and event_status not in ALLOWED_EVENT_STATUSES:
        _add_error(errors, label, f"invalid event_status: {event_status}")

    validation_status = _string(entry.get("validation_status"))
    if validation_status and validation_status not in ALLOWED_VALIDATION_STATUSES:
        _add_error(errors, label, f"invalid validation_status: {validation_status}")

    review_status = _string(entry.get("review_status"))
    if review_status and review_status not in ALLOWED_REVIEW_STATUSES:
        _add_error(errors, label, f"invalid review_status: {review_status}")

    quantity_unit = _string(entry.get("quantity_unit"))
    if quantity_unit and quantity_unit not in ALLOWED_QUANTITY_UNITS:
        _add_error(errors, label, f"invalid quantity_unit: {quantity_unit}")

    fx_review_status = _string(entry.get("fx_rate_review_status"))
    if fx_review_status and fx_review_status not in ALLOWED_FX_REVIEW_STATUSES:
        _add_error(errors, label, f"invalid fx_rate_review_status: {fx_review_status}")

    transfer_review_status = _string(entry.get("transfer_review_status"))
    if transfer_review_status and transfer_review_status not in ALLOWED_TRANSFER_REVIEW_STATUSES:
        _add_error(errors, label, f"invalid transfer_review_status: {transfer_review_status}")

    return event_type


def _validate_event_type_rules(entry: dict[str, Any], label: str, event_type: str, errors: list[str]) -> None:
    if event_type in {"BUY", "SELL"}:
        if entry.get("canonical_instrument_id") == "NOT_APPLICABLE" or _is_missing(entry.get("canonical_instrument_id")):
            _add_error(errors, label, f"{event_type} requires canonical_instrument_id or TO_BE_REVIEWED")
        if _is_missing(entry.get("quantity")):
            _add_error(errors, label, f"{event_type} requires quantity or TO_BE_REVIEWED")
        if entry.get("quantity_unit") not in {"SHARES", "UNITS", "CONTRACTS", "UNKNOWN_REVIEW_REQUIRED"}:
            _add_error(errors, label, f"{event_type} requires share/unit/contract quantity_unit or review")
        if _is_missing(entry.get("trade_date")):
            _add_error(errors, label, f"{event_type} requires trade_date or TO_BE_REVIEWED")
        if _is_missing(entry.get("transaction_currency")):
            _add_error(errors, label, f"{event_type} requires transaction_currency or TO_BE_REVIEWED")

    if event_type in {"DIVIDEND", "INTEREST", "DISTRIBUTION"}:
        for field in ["cash_currency", "gross_amount", "net_amount", "tax_amount"]:
            if _is_missing(entry.get(field)):
                _add_error(errors, label, f"{event_type} requires visible {field} or a neutral review placeholder")
        if event_type != "INTEREST" and entry.get("canonical_instrument_id") == "NOT_APPLICABLE":
            _add_error(errors, label, f"{event_type} requires instrument identity or TO_BE_REVIEWED")

    if event_type in {"DEPOSIT", "WITHDRAWAL"}:
        if entry.get("canonical_instrument_id") != "NOT_APPLICABLE":
            _add_error(errors, label, f"{event_type} cash-only template requires canonical_instrument_id NOT_APPLICABLE")
        if entry.get("quantity_unit") not in {"CURRENCY", "NOT_APPLICABLE"}:
            _add_error(errors, label, f"{event_type} requires CURRENCY or NOT_APPLICABLE quantity_unit")
        if _is_missing(entry.get("account_id")) or _is_missing(entry.get("cash_currency")):
            _add_error(errors, label, f"{event_type} requires account and cash currency boundary")

    if event_type == "FEE" and _is_missing(entry.get("fee_amount")):
        _add_error(errors, label, "FEE requires visible fee_amount or review placeholder")
    if event_type == "TAX":
        if _is_missing(entry.get("tax_amount")):
            _add_error(errors, label, "TAX requires visible tax_amount or review placeholder")
        if entry.get("review_status") != "TAX_REVIEW_REQUIRED":
            _add_error(errors, label, "TAX requires TAX_REVIEW_REQUIRED when tax type is unknown")

    if event_type in {"TRANSFER_IN", "TRANSFER_OUT"}:
        has_accounts = _is_set(entry.get("source_account_id")) and _is_set(entry.get("target_account_id"))
        if not has_accounts and entry.get("transfer_review_status") not in REVIEW_REQUIRED_STATUSES:
            _add_error(errors, label, f"{event_type} requires source/target account boundary or transfer review")
        if _looks_like_real_identifier(entry.get("transfer_pair_id"), ("TEMPLATE_", "PEL_TEMPLATE_")):
            _add_error(errors, label, "transfer_pair_id must be neutral or template-only")

    if event_type == "FX_CONVERSION":
        for field in ["fx_from_currency", "fx_to_currency", "fx_rate_source", "fx_rate_as_of_date"]:
            if _is_missing(entry.get(field)):
                _add_error(errors, label, f"FX_CONVERSION requires {field} or review placeholder")
        has_convention = _is_set(entry.get("fx_rate_convention")) and _is_set(entry.get("fx_rate_direction"))
        if not has_convention and entry.get("fx_rate_review_status") not in REVIEW_REQUIRED_STATUSES:
            _add_error(errors, label, "FX_CONVERSION requires rate convention/direction or FX review")

    if event_type in CORPORATE_ACTION_EVENT_TYPES:
        if entry.get("review_status") not in {"CORPORATE_ACTION_REVIEW_REQUIRED", "OPERATOR_REVIEW_REQUIRED", "EVIDENCE_REQUIRED", "UNKNOWN"}:
            _add_error(errors, label, f"{event_type} must remain corporate-action or operator review-required")
        if entry.get("validation_status") == "VALID" or entry.get("event_status") in {"ACCEPTED", "VALIDATED"}:
            _add_error(errors, label, f"{event_type} must not be accepted or valid in the template")

    if event_type in {"UNKNOWN_REVIEW_REQUIRED", "MANUAL_ADJUSTMENT_REVIEW_REQUIRED"}:
        if entry.get("review_status") not in REVIEW_REQUIRED_STATUSES:
            _add_error(errors, label, f"{event_type} must remain review-required")


def _validate_correction_chain(entry: dict[str, Any], label: str, errors: list[str]) -> None:
    chain_rules = [
        ("correction_of_event_id", "correction_reason", "correction_review_status"),
        ("reversal_of_event_id", "reversal_reason", "reversal_review_status"),
        ("supersedes_event_id", "supersession_reason", "supersession_review_status"),
    ]
    for event_field, reason_field, status_field in chain_rules:
        event_ref = entry.get(event_field)
        if not _is_set(event_ref):
            continue
        if not _is_neutral(event_ref):
            _add_error(errors, label, f"{event_field} must be a template placeholder")
        if _is_missing(entry.get(reason_field)) or entry.get(reason_field) == "NOT_APPLICABLE":
            _add_error(errors, label, f"{event_field} requires {reason_field}")
        if entry.get(status_field) not in REVIEW_REQUIRED_STATUSES:
            _add_error(errors, label, f"{event_field} requires review-required {status_field}")


def _validate_event_evidence(entry: dict[str, Any], label: str, warnings: list[str]) -> None:
    evidence_files = entry.get("evidence_files")
    if not isinstance(evidence_files, list) or not evidence_files:
        return
    evidence_text = " ".join(_string(value).lower() for value in evidence_files)
    if "data_freshness" in evidence_text or "license_boundary" in evidence_text:
        warnings.append(f"{label}: freshness/license evidence does not by itself satisfy event evidence")


def validate_portfolio_event_ledger_template_data(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return {
            "status": "ERROR",
            "template_only": False,
            "event_templates": 0,
            "errors": ["event ledger template root must be a mapping"],
            "warnings": [],
        }

    template_only = data.get("template_only")
    if template_only is not True:
        errors.append("portfolio event ledger template requires template_only=true")

    if "schema_version" not in data:
        errors.append("template requires schema_version")
    if "registry_purpose" not in data and "template_purpose" not in data:
        errors.append("template requires registry_purpose or template_purpose")
    if "non_scope" not in data and "boundary_notes" not in data:
        errors.append("template requires non_scope or boundary_notes")

    registry_status = _string(data.get("registry_status") or data.get("current_status") or data.get("status"))
    if registry_status in {"ACCEPTED", "VALIDATED", "ACTIVE_PRODUCTION", "PRODUCTION_APPROVED", "RUNTIME_APPROVED"}:
        errors.append(f"registry-level status must not imply accepted production ledger: {registry_status}")

    _validate_allowed_values(data, errors)
    _validate_matrix_sections(data, errors)

    required_fields = data.get("required_fields")
    if not isinstance(required_fields, list):
        errors.append("template requires required_fields list")
    else:
        missing_contract_fields = [field for field in REQUIRED_EVENT_FIELDS if field not in required_fields]
        for field in missing_contract_fields:
            errors.append(f"required_fields missing contract field: {field}")

    entries = data.get("event_templates") if "event_templates" in data else data.get("templates")
    if not isinstance(entries, list):
        errors.append("template requires event_templates list")
        entries = []

    for index, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, dict):
            errors.append(f"event_template[{index}]: template entry must be a mapping")
            continue

        entry = deepcopy(raw_entry)
        label = _event_label(entry, index)
        event_type = _validate_entry_enums(entry, label, errors)
        _validate_required_fields(entry, label, event_type, data, errors)
        _validate_entry_safety(entry, label, errors)
        _validate_event_type_rules(entry, label, event_type, errors)
        _validate_correction_chain(entry, label, errors)
        _validate_event_evidence(entry, label, warnings)

    return {
        "status": "OK" if not errors else "ERROR",
        "template_only": template_only is True,
        "event_templates": len(entries),
        "errors": sorted(errors),
        "warnings": sorted(warnings),
    }


def validate_portfolio_event_ledger_template(path: str = DEFAULT_TEMPLATE_PATH) -> dict[str, Any]:
    return validate_portfolio_event_ledger_template_data(load_yaml_config(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the CIOS Portfolio Event Ledger template without reading broker, provider or runtime data."
    )
    parser.add_argument("template_path", nargs="?", default=DEFAULT_TEMPLATE_PATH)
    args = parser.parse_args(argv)

    if not Path(args.template_path).exists():
        result = {
            "status": "ERROR",
            "template_only": False,
            "event_templates": 0,
            "errors": [f"template file does not exist: {args.template_path}"],
            "warnings": [],
        }
    else:
        result = validate_portfolio_event_ledger_template(args.template_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
