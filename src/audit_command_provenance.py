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

SKIPPED_PROVENANCE_STATUSES = {
    "SKIPPED_NO_ENTRYPOINT",
    "SKIPPED_PRIVATE_INPUT_REQUIRED",
    "SKIPPED_DEFERRED",
}

SKIPPED_RESULT_STATUSES = {"SKIPPED", "NOT_EXECUTABLE_FROM_REPO_STATE"}

REPO_HEAD_RE = re.compile(r"^[0-9a-fA-F]{40}$")
RFC3339_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$"
)
WINDOWS_DRIVE_RELATIVE_RE = re.compile(r"^[A-Za-z]:(?![\\/])")

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
    _validate_repo_head(manifest.get("repo_head"), "manifest.repo_head", result)
    _validate_utc_timestamp(
        manifest.get("created_at_utc"),
        "manifest.created_at_utc",
        result,
    )

    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        result.errors.append("manifest.entries must be a non-empty list.")
        return result

    result.entries_total = len(entries)
    for index, entry in enumerate(entries):
        _validate_entry(entry, index, manifest, result)
    return result


def _validate_entry(
    entry: Any,
    index: int,
    manifest: dict[str, Any],
    result: ValidationResult,
) -> None:
    label = f"entries[{index}]"
    if not isinstance(entry, dict):
        result.errors.append(f"{label} must be an object.")
        return

    _validate_required_fields(entry, REQUIRED_ENTRY_FIELDS, label, result)
    _validate_entry_matches_manifest(entry, manifest, label, result)
    _validate_repo_head(entry.get("repo_head"), f"{label}.repo_head", result)
    _validate_utc_timestamp(entry.get("recorded_at_utc"), f"{label}.recorded_at_utc", result)
    _validate_exit_code(entry.get("exit_code"), f"{label}.exit_code", result)

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
    _validate_output_observed(entry, label, result)
    _validate_skipped_provenance(entry, label, result)
    _validate_command_kind_consistency(entry, label, result)


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
    if WINDOWS_DRIVE_RELATIVE_RE.match(value):
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
    command_kind = entry.get("command_kind")

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
    if command_kind in {"skipped", "not_executable"}:
        result.errors.append(
            f"{label}.command_kind cannot be {command_kind} for COMMAND_REPRODUCED."
        )


def _validate_entry_matches_manifest(
    entry: dict[str, Any],
    manifest: dict[str, Any],
    label: str,
    result: ValidationResult,
) -> None:
    if entry.get("run_id") != manifest.get("run_id"):
        result.errors.append(f"{label}.run_id must match manifest.run_id.")
    if entry.get("repo_head") != manifest.get("repo_head"):
        result.errors.append(f"{label}.repo_head must match manifest.repo_head.")


def _validate_repo_head(value: Any, label: str, result: ValidationResult) -> None:
    if not isinstance(value, str) or not REPO_HEAD_RE.match(value):
        result.errors.append(f"{label} must be a 40-character hexadecimal Git SHA.")


def _validate_utc_timestamp(value: Any, label: str, result: ValidationResult) -> None:
    if not isinstance(value, str) or not RFC3339_UTC_RE.match(value):
        result.errors.append(f"{label} must be RFC3339 UTC-like, ending in Z or +00:00.")


def _validate_exit_code(value: Any, label: str, result: ValidationResult) -> None:
    if value is not None and not isinstance(value, int):
        result.errors.append(f"{label} must be an integer or null.")


def _validate_output_observed(
    entry: dict[str, Any],
    label: str,
    result: ValidationResult,
) -> None:
    if entry.get("provenance_status") != "OUTPUT_OBSERVED_COMMAND_NOT_RECORDED":
        return
    if entry.get("command") != "":
        result.errors.append(
            f"{label}.command must be empty for OUTPUT_OBSERVED_COMMAND_NOT_RECORDED."
        )
    if entry.get("exit_code") is not None:
        result.errors.append(
            f"{label}.exit_code must be null for OUTPUT_OBSERVED_COMMAND_NOT_RECORDED."
        )
    if entry.get("result_status") == "PASS":
        result.errors.append(
            f"{label}.result_status cannot be PASS for OUTPUT_OBSERVED_COMMAND_NOT_RECORDED."
        )


def _validate_skipped_provenance(
    entry: dict[str, Any],
    label: str,
    result: ValidationResult,
) -> None:
    if entry.get("provenance_status") not in SKIPPED_PROVENANCE_STATUSES:
        return
    if entry.get("command") != "":
        result.errors.append(f"{label}.command must be empty for skipped provenance.")
    if entry.get("exit_code") is not None:
        result.errors.append(f"{label}.exit_code must be null for skipped provenance.")
    if entry.get("result_status") not in SKIPPED_RESULT_STATUSES:
        result.errors.append(
            f"{label}.result_status must be SKIPPED or NOT_EXECUTABLE_FROM_REPO_STATE for skipped provenance."
        )


def _validate_command_kind_consistency(
    entry: dict[str, Any],
    label: str,
    result: ValidationResult,
) -> None:
    command_kind = entry.get("command_kind")
    provenance_status = entry.get("provenance_status")
    command = entry.get("command")

    if command_kind == "skipped" and provenance_status not in SKIPPED_PROVENANCE_STATUSES:
        result.errors.append(f"{label}.command_kind skipped requires SKIPPED_* provenance.")
    if command_kind == "not_executable" and provenance_status != "SKIPPED_NO_ENTRYPOINT":
        result.errors.append(
            f"{label}.command_kind not_executable requires SKIPPED_NO_ENTRYPOINT provenance."
        )
    if provenance_status == "COMMAND_RECORDED" and (not isinstance(command, str) or not command.strip()):
        result.errors.append(f"{label}.command is required for COMMAND_RECORDED.")


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
