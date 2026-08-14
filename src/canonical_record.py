from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
from typing import Any, Iterable, Mapping


HASH_SCHEMA_VERSION = "CIOS_CANONICAL_RECORD_V1"
GENESIS_PREVIOUS_RECORD_HASH = "GENESIS"


def normalize_decimal_string(value: Any, *, field_name: str) -> str:
    """Validate and normalize a persisted decimal string without using float."""

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be supplied as a decimal string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} must not be blank")
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{field_name} must be a valid decimal string") from exc
    if not number.is_finite():
        raise ValueError(f"{field_name} must be finite")
    normalized = format(number, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    if normalized in {"-0", ""}:
        return "0"
    return normalized


def _normalize_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _normalize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    if isinstance(value, str):
        return _normalize_text(value)
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        raise ValueError("native float values are not allowed in canonical records")
    raise ValueError(f"unsupported canonical record value type: {type(value).__name__}")


def normalize_record(
    record: Mapping[str, Any],
    *,
    decimal_fields: Iterable[str] = (),
    exclude_fields: Iterable[str] = ("record_hash",),
) -> dict[str, Any]:
    excluded = set(exclude_fields)
    normalized = {
        str(key): _normalize_value(value)
        for key, value in record.items()
        if str(key) not in excluded
    }
    for field in decimal_fields:
        if field not in normalized:
            raise ValueError(f"canonical record missing decimal field: {field}")
        normalized[field] = normalize_decimal_string(normalized[field], field_name=field)
    schema_version = str(normalized.get("hash_schema_version", "") or "").strip()
    if schema_version != HASH_SCHEMA_VERSION:
        raise ValueError(f"hash_schema_version must be {HASH_SCHEMA_VERSION}")
    return normalized


def canonical_record_bytes(
    record: Mapping[str, Any],
    *,
    decimal_fields: Iterable[str] = (),
    exclude_fields: Iterable[str] = ("record_hash",),
) -> bytes:
    normalized = normalize_record(record, decimal_fields=decimal_fields, exclude_fields=exclude_fields)
    return json.dumps(
        normalized,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")


def calculate_record_hash(record: Mapping[str, Any], *, decimal_fields: Iterable[str] = ()) -> str:
    return hashlib.sha256(canonical_record_bytes(record, decimal_fields=decimal_fields)).hexdigest()


def build_hashed_record(
    record: Mapping[str, Any],
    *,
    previous_record_hash: str,
    decimal_fields: Iterable[str] = (),
) -> dict[str, str]:
    candidate = {str(key): str(value) for key, value in record.items() if str(key) != "record_hash"}
    candidate["hash_schema_version"] = HASH_SCHEMA_VERSION
    candidate["previous_record_hash"] = str(previous_record_hash).strip()
    if not candidate["previous_record_hash"]:
        raise ValueError("previous_record_hash must not be blank")
    for field in decimal_fields:
        candidate[field] = normalize_decimal_string(candidate.get(field), field_name=field)
    candidate["record_hash"] = calculate_record_hash(candidate, decimal_fields=decimal_fields)
    return candidate


def verify_hash_chain(rows: Iterable[Mapping[str, Any]], *, decimal_fields: Iterable[str] = ()) -> str:
    previous = GENESIS_PREVIOUS_RECORD_HASH
    for index, row in enumerate(rows, start=1):
        schema = str(row.get("hash_schema_version", "") or "").strip()
        if schema != HASH_SCHEMA_VERSION:
            raise ValueError(f"row {index} has unsupported hash_schema_version: {schema}")
        linked = str(row.get("previous_record_hash", "") or "").strip()
        if linked != previous:
            raise ValueError(f"row {index} previous_record_hash does not match prior ledger head")
        stored = str(row.get("record_hash", "") or "").strip()
        calculated = calculate_record_hash(row, decimal_fields=decimal_fields)
        if stored != calculated:
            raise ValueError(f"row {index} record_hash mismatch")
        previous = stored
    return previous
