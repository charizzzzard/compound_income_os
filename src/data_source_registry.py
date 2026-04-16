from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common import load_yaml_config, resolve_repo_path, write_csv_rows

DEFAULT_CONFIG_PATH = "configs/personal_run_data_sources.yaml"
DEFAULT_STATUS_OUTPUT = "data/processed/personal_data_source_status.csv"
DEFAULT_RESOLVED_OUTPUT = "data/processed/personal_data_source_registry_resolved.csv"

STATUS_FIELDS = [
    "source_key",
    "enabled",
    "required",
    "kind",
    "configured_path",
    "resolved_path",
    "exists",
    "status",
    "notes",
]

RESOLVED_FIELDS = [
    "source_key",
    "resolved_path",
    "status",
    "used_as_default_input",
]

VALID_SOURCE_KINDS = {"file", "directory"}
REQUIRED_SOURCE_FIELDS = ["enabled", "path", "required", "kind", "description"]
SUPPORTED_SOURCE_KEYS = {
    "benchmark_input",
    "cash_input",
    "cost_tax_ledger_input",
    "fundamentals_evidence_input",
    "fundamentals_master",
    "fundamentals_overlay_input",
    "fundamentals_snapshot_input",
    "fundamentals_snapshot_evidence_promoted_input",
    "fundamentals_snapshot_review_input",
    "positions_raw_input",
    "profile_review_input",
}


@dataclass(frozen=True)
class SourceRecord:
    source_key: str
    enabled: bool
    required: bool
    kind: str
    description: str
    configured_path: str
    resolved_path: str
    exists: bool
    status: str
    notes: str


def _validate_source_entry(source_key: str, raw_entry: Any) -> SourceRecord:
    if source_key not in SUPPORTED_SOURCE_KEYS:
        raise ValueError(f"personal data source registry contains unsupported source_key: {source_key}")
    if not isinstance(raw_entry, dict):
        raise ValueError(f"personal data source registry entry for {source_key} must be a mapping")

    missing_fields = [field for field in REQUIRED_SOURCE_FIELDS if field not in raw_entry]
    if missing_fields:
        missing_text = ", ".join(sorted(missing_fields))
        raise ValueError(f"personal data source registry entry for {source_key} missing required field(s): {missing_text}")

    kind = str(raw_entry.get("kind", "")).strip()
    if kind not in VALID_SOURCE_KINDS:
        raise ValueError(f"personal data source registry entry for {source_key} has unsupported kind: {raw_entry.get('kind')!r}")

    configured_path = str(raw_entry.get("path", "")).strip()
    if not configured_path:
        raise ValueError(f"personal data source registry entry for {source_key} requires non-blank path")

    description = str(raw_entry.get("description", "")).strip()
    if not description:
        raise ValueError(f"personal data source registry entry for {source_key} requires non-blank description")

    resolved_path = resolve_repo_path(configured_path)
    exists = resolved_path.is_dir() if kind == "directory" else resolved_path.is_file()
    enabled = bool(raw_entry.get("enabled"))
    required = bool(raw_entry.get("required"))

    if not enabled:
        status = "DISABLED"
        notes = "Source disabled via personal data source registry."
    elif exists:
        status = "OK"
        notes = "Configured source resolved successfully."
    elif required:
        status = "MISSING"
        notes = "Enabled required source is missing."
    else:
        status = "MISSING"
        notes = "Enabled optional source is missing."

    return SourceRecord(
        source_key=source_key,
        enabled=enabled,
        required=required,
        kind=kind,
        description=description,
        configured_path=configured_path,
        resolved_path=str(resolved_path),
        exists=exists,
        status=status,
        notes=notes,
    )


def load_personal_data_source_records(config_path: str = DEFAULT_CONFIG_PATH) -> dict[str, SourceRecord]:
    config = load_yaml_config(config_path)
    sources = config.get("sources")
    if not isinstance(sources, dict):
        raise ValueError("personal data source registry config requires a top-level sources mapping")
    return {source_key: _validate_source_entry(source_key, sources[source_key]) for source_key in sorted(sources)}


def build_status_rows(records: dict[str, SourceRecord]) -> list[dict[str, str]]:
    return [
        {
            "source_key": record.source_key,
            "enabled": str(record.enabled),
            "required": str(record.required),
            "kind": record.kind,
            "configured_path": record.configured_path,
            "resolved_path": record.resolved_path,
            "exists": str(record.exists),
            "status": record.status,
            "notes": record.notes,
        }
        for record in records.values()
    ]


def build_resolved_rows(
    records: dict[str, SourceRecord],
    used_as_default_source_keys: set[str] | None = None,
) -> list[dict[str, str]]:
    used_as_default_source_keys = used_as_default_source_keys or set()
    return [
        {
            "source_key": record.source_key,
            "resolved_path": record.resolved_path,
            "status": record.status,
            "used_as_default_input": str(record.source_key in used_as_default_source_keys and record.enabled and record.status == "OK"),
        }
        for record in records.values()
    ]


def missing_required_source_keys(records: dict[str, SourceRecord]) -> list[str]:
    return sorted(record.source_key for record in records.values() if record.enabled and record.required and record.status == "MISSING")


def write_data_source_outputs(
    records: dict[str, SourceRecord],
    *,
    status_output: str = DEFAULT_STATUS_OUTPUT,
    resolved_output: str = DEFAULT_RESOLVED_OUTPUT,
    used_as_default_source_keys: set[str] | None = None,
) -> dict[str, Path]:
    status_path = write_csv_rows(status_output, STATUS_FIELDS, build_status_rows(records))
    resolved_path = write_csv_rows(
        resolved_output,
        RESOLVED_FIELDS,
        build_resolved_rows(records, used_as_default_source_keys=used_as_default_source_keys),
    )
    return {"data_source_status": status_path, "data_source_registry_resolved": resolved_path}
