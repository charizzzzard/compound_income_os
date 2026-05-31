"""Validate audit command provenance manifests."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any


REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "run_id",
    "repo_head",
    "created_at_utc",
    "entries",
}

REQUIRED_ENTRY_FIELDS = {
    "run_id",
    "repo_head",
    "capability_id",
    "capability_status_from_feature_registry",
    "execution_classification",
    "command",
    "command_kind",
    "working_directory",
    "input_paths",
    "output_paths",
    "exit_code",
    "recorded_at_utc",
    "result_status",
    "conservative_state",
    "provenance_status",
    "notes",
}

ALLOWED_COMMAND_KINDS = {
    "python_module",
    "pytest",
    "ruff",
    "inspection_only",
    "skipped",
    "not_executable",
}

ALLOWED_RESULT_STATUSES = {
    "PASS",
    "FAIL",
    "SKIPPED",
    "REVIEW",
    "NOT_EXECUTABLE_FROM_REPO_STATE",
}

ALLOWED_PROVENANCE_STATUSES = {
    "COMMAND_RECORDED",
    "COMMAND_REPRODUCED",
    "OUTPUT_OBSERVED_COMMAND_NOT_RECORDED",
    "SKIPPED_NO_ENTRYPOINT",
    "SKIPPED_PRIVATE_INPUT_REQUIRED",
    "SKIPPED_DEFERRED",
}

DEGRADED_PROVENANCE_STATUSES = {
    "OUTPUT_OBSERVED_COMMAND_NOT_RECORDED",
    "SKIPPED_NO_ENTRYPOINT",
    "SKIPPED_PRIVATE_INPUT_REQUIRED",
    "SKIPPED_DEFERRED",
}

FORBIDDEN_TEXT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bapi[_-]?key\b",
        r"\bsecret\b",
        r"\bpassword\b",
        r"\bcredential\b",
        r"\btoken\b",
        r"\.env\b",
        r"\baccount[_ -]?(?:id|number)\b",
    )
]


@dataclass(slots=True)
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    entries_total: int = 0
    degraded_entries: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def load_manifest(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Audit command provenance manifest must be a JSON object.")
    return data


def validate_manifest_file(path: str) -> ValidationResult:
    return validate_manifest(load_manifest(path))


def validate_manifest(manifest: dict[str, Any]) -> ValidationResult:
    result = ValidationResult()
    _validate_required_fields(
        manifest,
        REQUIRED_TOP_LEVEL_FIELDS,
        "manifest",
        result,
    )

    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        result.errors.append("manifest.entries must be a non-empty list.")
        return result

    result.entries_total = len(entries)
    for index, entry in enumerate(entries):
        _validate_entry(entry, index, result)
    return result


def _validate_entry(entry: Any, index: int, result: ValidationResult) -> None:
    label = f"entries[{index}]"
    if not isinstance(entry, dict):
        result.errors.append(f"{label} must be an object.")
        return

    _validate_required_fields(entry, REQUIRED_ENTRY_FIELDS, label, result)

    command_kind = entry.get("command_kind")
    if command_kind not in ALLOWED_COMMAND_KINDS:
        result.errors.append(f"{label}.command_kind has unsupported value: {command_kind!r}.")

    result_status = entry.get("result_status")
    if result_status not in ALLOWED_RESULT_STATUSES:
        result.errors.append(f"{label}.result_status has unsupported value: {result_status!r}.")

    provenance_status = entry.get("provenance_status")
    if provenance_status not in ALLOWED_PROVENANCE_STATUSES:
        result.errors.append(
            f"{label}.provenance_status has unsupported value: {provenance_status!r}."
        )
    elif provenance_status in DEGRADED_PROVENANCE_STATUSES:
        result.degraded_entries += 1
        result.warnings.append(f"{label} has degraded provenance: {provenance_status}.")

    _validate_path_value(entry.get("working_directory"), f"{label}.working_directory", result)
    _validate_path_list(entry.get("input_paths"), f"{label}.input_paths", result)
    _validate_path_list(entry.get("output_paths"), f"{label}.output_paths", result)
    _validate_forbidden_text_fields(entry, label, result)
    _validate_command_reproduced(entry, label, result)


def _validate_required_fields(
    data: dict[str, Any],
    required_fields: set[str],
    label: str,
    result: ValidationResult,
) -> None:
    missing = sorted(required_fields - set(data))
    for field_name in missing:
        result.errors.append(f"{label}.{field_name} is required.")


def _validate_path_list(value: Any, label: str, result: ValidationResult) -> None:
    if not isinstance(value, list):
        result.errors.append(f"{label} must be a list.")
        return
    for index, path_value in enumerate(value):
        _validate_path_value(path_value, f"{label}[{index}]", result)


def _validate_path_value(value: Any, label: str, result: ValidationResult) -> None:
    if not isinstance(value, str) or not value:
        result.errors.append(f"{label} must be a non-empty string.")
        return
    if not is_repo_relative_path(value):
        result.errors.append(f"{label} must be repo-relative or '.': {value!r}.")
    _validate_forbidden_text(value, label, result)


def is_repo_relative_path(value: str) -> bool:
    if value == ".":
        return True
    if "\x00" in value:
        return False
    if value.startswith(("~", "/", "\\", "//")):
        return False
    if PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute():
        return False
    parts = PurePosixPath(value.replace("\\", "/")).parts
    return ".." not in parts


def _validate_forbidden_text_fields(
    entry: dict[str, Any],
    label: str,
    result: ValidationResult,
) -> None:
    for field_name in ("command", "notes", "capability_id", "execution_classification"):
        value = entry.get(field_name)
        if isinstance(value, str):
            _validate_forbidden_text(value, f"{label}.{field_name}", result)


def _validate_forbidden_text(value: str, label: str, result: ValidationResult) -> None:
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(value):
            result.errors.append(f"{label} contains forbidden sensitive marker: {value!r}.")
            return


def _validate_command_reproduced(
    entry: dict[str, Any],
    label: str,
    result: ValidationResult,
) -> None:
    if entry.get("provenance_status") != "COMMAND_REPRODUCED":
        return
    command = entry.get("command")
    exit_code = entry.get("exit_code")
    recorded_at_utc = entry.get("recorded_at_utc")
    result_status = entry.get("result_status")

    if not isinstance(command, str) or not command.strip():
        result.errors.append(f"{label}.command is required for COMMAND_REPRODUCED.")
    if not isinstance(exit_code, int):
        result.errors.append(f"{label}.exit_code must be an integer for COMMAND_REPRODUCED.")
    if not isinstance(recorded_at_utc, str) or not recorded_at_utc.strip():
        result.errors.append(f"{label}.recorded_at_utc is required for COMMAND_REPRODUCED.")
    if result_status in {"SKIPPED", "NOT_EXECUTABLE_FROM_REPO_STATE"}:
        result.errors.append(
            f"{label}.result_status cannot be {result_status} for COMMAND_REPRODUCED."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to an audit command provenance JSON manifest.",
    )
    args = parser.parse_args(argv)

    result = validate_manifest_file(args.manifest)
    print(f"validation_status={'PASS' if result.ok else 'FAIL'}")
    print(f"entries_total={result.entries_total}")
    print(f"degraded_entries={result.degraded_entries}")
    for warning in result.warnings:
        print(f"warning={warning}")
    for error in result.errors:
        print(f"error={error}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
