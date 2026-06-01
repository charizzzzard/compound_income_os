from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.common import load_yaml_config

DEFAULT_TEMPLATE_PATH = "docs/architecture/CIOS_INSTRUMENT_MASTER_TEMPLATE.yaml"

ALLOWED_INSTRUMENT_TYPES = {
    "STOCK",
    "ETF",
    "FUND",
    "BOND",
    "CASH",
    "CURRENCY",
    "CRYPTO_ASSET",
    "DERIVATIVE",
    "OTHER_REVIEW_REQUIRED",
    "UNKNOWN_REVIEW_REQUIRED",
}

ALLOWED_ASSET_CLASSES = {
    "EQUITY",
    "FIXED_INCOME",
    "CASH_OR_CURRENCY",
    "CRYPTO",
    "MULTI_ASSET",
    "COMMODITY",
    "REAL_ESTATE",
    "DERIVATIVE",
    "OTHER_REVIEW_REQUIRED",
    "UNKNOWN_REVIEW_REQUIRED",
}

ALLOWED_LIFECYCLE_STATUSES = {
    "ACTIVE",
    "INACTIVE",
    "DELISTED",
    "MERGED",
    "ACQUIRED",
    "LIQUIDATED",
    "RENAMED",
    "SYMBOL_CHANGED",
    "REVIEW_REQUIRED",
    "UNKNOWN",
}

ALLOWED_IDENTITY_CONFIDENCE = {
    "HIGH",
    "MEDIUM",
    "LOW",
    "REVIEW_REQUIRED",
    "UNKNOWN",
}

ALLOWED_REVIEW_STATUSES = {
    "APPROVED_FOR_LOCAL_USE",
    "OPERATOR_REVIEW_REQUIRED",
    "EVIDENCE_REQUIRED",
    "CONFLICT_REVIEW_REQUIRED",
    "CORPORATE_ACTION_REVIEW_REQUIRED",
    "PROVIDER_MAPPING_REVIEW_REQUIRED",
    "BROKER_MAPPING_REVIEW_REQUIRED",
    "PROHIBITED",
    "UNKNOWN",
}

ALLOWED_PRIMARY_IDENTIFIER_TYPES = {
    "ISIN",
    "WKN",
    "CUSIP",
    "SEDOL",
    "FIGI",
    "LEI",
    "MIC",
    "EXCHANGE_CODE",
    "PROVIDER_ID",
    "BROKER_ID",
    "CURRENCY_CODE_REVIEW_REQUIRED",
    "TO_BE_REVIEWED",
    "UNKNOWN_REVIEW_REQUIRED",
    "NOT_APPLICABLE",
}

PROHIBITED_TEMPLATE_STATUSES = {
    "ACCEPTED",
    "VALIDATED",
    "ACTIVE_PRODUCTION",
    "PRODUCTION_APPROVED",
    "RUNTIME_APPROVED",
    "BROKER_IMPORT_READY",
    "INVESTMENT_READY",
    "TRADING_APPROVED",
}

REQUIRED_INSTRUMENT_FIELDS = [
    "canonical_instrument_id",
    "instrument_name",
    "instrument_type",
    "asset_class",
    "issuer_name",
    "primary_identifier_type",
    "primary_identifier_value",
    "identifiers",
    "listings",
    "broker_aliases",
    "provider_aliases",
    "currency",
    "domicile_or_country",
    "lifecycle_status",
    "identity_confidence",
    "review_status",
    "source_provenance",
    "evidence_files",
    "license_boundary_refs",
    "data_source_refs",
    "created_at",
    "updated_at",
    "effective_from",
    "effective_to",
    "predecessor_instrument_ids",
    "successor_instrument_ids",
    "known_limitations",
    "owner",
    "notes",
]

LIST_FIELDS = {
    "identifiers",
    "listings",
    "broker_aliases",
    "provider_aliases",
    "source_provenance",
    "evidence_files",
    "license_boundary_refs",
    "data_source_refs",
    "predecessor_instrument_ids",
    "successor_instrument_ids",
    "known_limitations",
}

FORBIDDEN_PATH_RE = re.compile(r"(^[a-zA-Z]:)|(^\\\\)|(^/)|(^~)|(^|/)\.\.(/|$)")
FORBIDDEN_TEXT_FRAGMENTS = (
    "data/raw",
    "data\\raw",
    "private/",
    "private\\",
    "broker_statement",
    "account_id",
    "secret",
    "credential",
    "api_key",
    "token",
)


def _string(value: Any) -> str:
    return str(value or "").strip()


def _label(entry: dict[str, Any], index: int) -> str:
    return _string(entry.get("template_id") or entry.get("canonical_instrument_id")) or f"instrument_template[{index}]"


def _add_error(errors: list[str], label: str, message: str) -> None:
    errors.append(f"{label}: {message}")


def _is_neutral(value: Any) -> bool:
    text = _string(value)
    return not text or text in {"TO_BE_REVIEWED", "UNKNOWN", "UNKNOWN_REVIEW_REQUIRED", "NOT_APPLICABLE", "TEMPLATE_ONLY"}


def _looks_like_forbidden_path_or_secret(value: Any) -> bool:
    text = _string(value)
    if not text:
        return False
    normalized = text.replace("\\", "/").lower()
    return bool(FORBIDDEN_PATH_RE.search(text)) or any(fragment in normalized for fragment in FORBIDDEN_TEXT_FRAGMENTS)


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
        "instrument_type": ALLOWED_INSTRUMENT_TYPES,
        "asset_class": ALLOWED_ASSET_CLASSES,
        "lifecycle_status": ALLOWED_LIFECYCLE_STATUSES,
        "identity_confidence": ALLOWED_IDENTITY_CONFIDENCE,
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


def _validate_entry(entry: dict[str, Any], index: int, errors: list[str]) -> tuple[str, tuple[str, str] | None, str | None]:
    label = _label(entry, index)

    for field in REQUIRED_INSTRUMENT_FIELDS:
        if field not in entry:
            _add_error(errors, label, f"missing required field: {field}")

    for field in LIST_FIELDS:
        if field in entry and not isinstance(entry.get(field), list):
            _add_error(errors, label, f"{field} must be a list")

    canonical_id = _string(entry.get("canonical_instrument_id"))
    if not canonical_id:
        _add_error(errors, label, "canonical_instrument_id is required")
    elif not canonical_id.startswith("IM_TEMPLATE_"):
        _add_error(errors, label, "template canonical_instrument_id must use IM_TEMPLATE_ placeholder")

    instrument_type = _string(entry.get("instrument_type"))
    asset_class = _string(entry.get("asset_class"))
    lifecycle_status = _string(entry.get("lifecycle_status"))
    identity_confidence = _string(entry.get("identity_confidence"))
    review_status = _string(entry.get("review_status"))
    primary_type = _string(entry.get("primary_identifier_type"))
    primary_value = _string(entry.get("primary_identifier_value"))

    if instrument_type and instrument_type not in ALLOWED_INSTRUMENT_TYPES:
        _add_error(errors, label, f"invalid instrument_type: {instrument_type}")
    if not asset_class:
        _add_error(errors, label, "asset_class is required")
    elif asset_class not in ALLOWED_ASSET_CLASSES:
        _add_error(errors, label, f"invalid asset_class: {asset_class}")
    if lifecycle_status and lifecycle_status not in ALLOWED_LIFECYCLE_STATUSES:
        _add_error(errors, label, f"invalid lifecycle_status: {lifecycle_status}")
    if identity_confidence and identity_confidence not in ALLOWED_IDENTITY_CONFIDENCE:
        _add_error(errors, label, f"invalid identity_confidence: {identity_confidence}")
    if review_status and review_status not in ALLOWED_REVIEW_STATUSES:
        _add_error(errors, label, f"invalid review_status: {review_status}")
    if primary_type and primary_type not in ALLOWED_PRIMARY_IDENTIFIER_TYPES:
        _add_error(errors, label, f"invalid primary_identifier_type: {primary_type}")

    if primary_type == "TICKER":
        _add_error(errors, label, "ticker alone is never sufficient primary identity evidence")
    if primary_type not in {"TO_BE_REVIEWED", "UNKNOWN_REVIEW_REQUIRED", "NOT_APPLICABLE", "CURRENCY_CODE_REVIEW_REQUIRED"} and _is_neutral(primary_value):
        _add_error(errors, label, "primary_identifier_value is required when primary_identifier_type is specific")

    if lifecycle_status in {"ACTIVE", "INACTIVE"} and review_status == "APPROVED_FOR_LOCAL_USE":
        _add_error(errors, label, "template entries must not claim approved local runtime identity")
    if identity_confidence == "HIGH" or review_status == "APPROVED_FOR_LOCAL_USE":
        _add_error(errors, label, "template entries must not claim high confidence or approved identity")

    identifiers = entry.get("identifiers")
    if isinstance(identifiers, list):
        for item_index, item in enumerate(identifiers):
            if not isinstance(item, dict):
                _add_error(errors, label, f"identifiers[{item_index}] must be a mapping")
                continue
            identifier_type = _string(item.get("identifier_type") or item.get("type"))
            identifier_value = _string(item.get("identifier_value") or item.get("value"))
            if identifier_type == "TICKER":
                _add_error(errors, label, "ticker identifiers are aliases/listing evidence, not sufficient canonical identity")
            if identifier_type and identifier_type not in ALLOWED_PRIMARY_IDENTIFIER_TYPES:
                _add_error(errors, label, f"invalid identifier_type: {identifier_type}")
            if identifier_type and not identifier_value:
                _add_error(errors, label, f"identifier {identifier_type} requires a value")

    for text in _iter_text_values(entry):
        if _looks_like_forbidden_path_or_secret(text):
            _add_error(errors, label, "template entries must not contain private paths, broker/account identifiers or secrets")
            break

    primary_key = None
    if primary_type and primary_value and primary_type not in {"TO_BE_REVIEWED", "UNKNOWN_REVIEW_REQUIRED", "NOT_APPLICABLE"}:
        primary_key = (primary_type, primary_value.upper())
    isin_value = primary_value.upper() if primary_type == "ISIN" and primary_value else None
    return canonical_id, primary_key, isin_value


def validate_instrument_master_template_data(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return {
            "status": "ERROR",
            "template_only": False,
            "instrument_templates": 0,
            "errors": ["instrument master template root must be a mapping"],
            "warnings": [],
            "non_claims": _non_claims(),
        }

    template_only = data.get("template_only")
    if template_only is not True:
        errors.append("instrument master template requires template_only=true")

    if "schema_version" not in data:
        errors.append("template requires schema_version")
    if "registry_purpose" not in data:
        errors.append("template requires registry_purpose")

    registry_status = _string(data.get("registry_status") or data.get("current_status") or data.get("status"))
    if registry_status in PROHIBITED_TEMPLATE_STATUSES:
        errors.append(f"registry-level status must not imply production/runtime approval: {registry_status}")

    _validate_allowed_values(data, errors)

    entries = data.get("instrument_templates")
    if not isinstance(entries, list):
        errors.append("template requires instrument_templates list")
        entries = []

    canonical_ids: dict[str, str] = {}
    primary_values: dict[tuple[str, str], str] = {}
    isin_values: dict[str, str] = {}

    for index, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, dict):
            errors.append(f"instrument_template[{index}]: template entry must be a mapping")
            continue

        entry = deepcopy(raw_entry)
        label = _label(entry, index)
        canonical_id, primary_key, isin_value = _validate_entry(entry, index, errors)

        if canonical_id:
            if canonical_id in canonical_ids:
                _add_error(errors, label, f"duplicate canonical_instrument_id also used by {canonical_ids[canonical_id]}")
            canonical_ids[canonical_id] = label
        if primary_key:
            if primary_key in primary_values:
                _add_error(errors, label, f"duplicate primary identifier also used by {primary_values[primary_key]}")
            primary_values[primary_key] = label
        if isin_value:
            if isin_value in isin_values:
                _add_error(errors, label, f"duplicate ISIN also used by {isin_values[isin_value]}")
            isin_values[isin_value] = label

    return {
        "status": "OK" if not errors else "ERROR",
        "template_only": template_only is True,
        "instrument_templates": len(entries),
        "errors": sorted(errors),
        "warnings": sorted(warnings),
        "non_claims": _non_claims(),
    }


def _non_claims() -> list[str]:
    return [
        "validation does not approve trading",
        "validation does not approve broker import",
        "validation does not create production readiness",
        "validation does not create investment readiness",
        "validation does not approve public redistribution",
    ]


def validate_instrument_master_template(path: str = DEFAULT_TEMPLATE_PATH) -> dict[str, Any]:
    return validate_instrument_master_template_data(load_yaml_config(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the CIOS Instrument Master template without reading broker, provider or runtime data."
    )
    parser.add_argument("template_path", nargs="?", default=DEFAULT_TEMPLATE_PATH)
    args = parser.parse_args(argv)

    if not Path(args.template_path).exists():
        result = {
            "status": "ERROR",
            "template_only": False,
            "instrument_templates": 0,
            "errors": ["template file does not exist"],
            "warnings": [],
            "non_claims": _non_claims(),
        }
    else:
        result = validate_instrument_master_template(args.template_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
