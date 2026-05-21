from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.common import load_yaml_config

DEFAULT_TEMPLATE_PATH = "docs/architecture/CIOS_DATA_SOURCE_REGISTRY_TEMPLATE.yaml"

ALLOWED_CLASSIFICATIONS = {
    "OFFICIAL_PUBLIC",
    "PUBLIC_COMPANY_FILINGS",
    "USER_PRIVATE_EXPORT",
    "MANUAL_OPERATOR_INPUT",
    "PAID_VENDOR",
    "WEB_SOURCE_REVIEW_REQUIRED",
    "COMMUNITY_DATASET_REVIEW_REQUIRED",
    "INTERNAL_DERIVED",
    "TEST_FIXTURE",
    "UNKNOWN_REVIEW_REQUIRED",
}

ALLOWED_SOURCE_TYPES = set(ALLOWED_CLASSIFICATIONS)

ALLOWED_USAGE_SCOPES = {
    "PRIVATE_LOCAL_ONLY",
    "INTERNAL_REVIEW",
    "TEST_ONLY",
    "PUBLIC_DOC_REFERENCE",
    "PUBLIC_HANDOFF_METADATA_ONLY",
    "PUBLIC_HANDOFF_DERIVED_ALLOWED",
    "DASHBOARD_LOCAL_ALLOWED",
    "COMMERCIAL_REVIEW_REQUIRED",
    "PROHIBITED",
}

ALLOWED_REVIEW_STATUSES = {
    "APPROVED_FOR_PRIVATE_LOCAL_USE",
    "APPROVED_FOR_TEST_FIXTURES",
    "APPROVED_FOR_PUBLIC_METADATA_ONLY",
    "APPROVED_FOR_DERIVED_HANDOFF",
    "COMMERCIAL_REVIEW_REQUIRED",
    "LEGAL_REVIEW_REQUIRED",
    "OPERATOR_REVIEW_REQUIRED",
    "PROHIBITED",
    "UNKNOWN",
}

ALLOWED_CURRENT_STATUSES = ALLOWED_REVIEW_STATUSES | {
    "TEMPLATE_ONLY",
    "REVIEW_REQUIRED",
}

REQUIRED_SOURCE_FIELDS = [
    "source_id",
    "source_name",
    "source_type",
    "provider_name",
    "provider_url_or_reference",
    "access_method",
    "license_classification",
    "usage_scope",
    "redistribution_allowed",
    "commercial_use_allowed",
    "attribution_required",
    "raw_data_handoff_allowed",
    "derived_data_handoff_allowed",
    "contains_personal_data",
    "contains_broker_data",
    "contains_paid_data",
    "requires_operator_review",
    "requires_external_review",
    "as_of_date_required",
    "snapshot_required",
    "freshness_policy_id",
    "provenance_required",
    "adapter_required",
    "current_status",
    "evidence_files",
    "license_evidence_files",
    "provenance_evidence_files",
    "freshness_evidence_files",
    "review_evidence_files",
    "known_limitations",
    "owner",
    "review_status",
]

BOOL_FIELDS = {
    "redistribution_allowed",
    "commercial_use_allowed",
    "attribution_required",
    "raw_data_handoff_allowed",
    "derived_data_handoff_allowed",
    "contains_personal_data",
    "contains_broker_data",
    "contains_paid_data",
    "requires_operator_review",
    "requires_external_review",
    "as_of_date_required",
    "snapshot_required",
    "provenance_required",
    "adapter_required",
}

LIST_FIELDS = {
    "evidence_files",
    "license_evidence_files",
    "provenance_evidence_files",
    "freshness_evidence_files",
    "review_evidence_files",
    "known_limitations",
}

PROVIDER_SPECIFIC_SOURCE_TYPES = {
    "OFFICIAL_PUBLIC",
    "PUBLIC_COMPANY_FILINGS",
    "PAID_VENDOR",
    "WEB_SOURCE_REVIEW_REQUIRED",
    "COMMUNITY_DATASET_REVIEW_REQUIRED",
}

TIME_SENSITIVE_SOURCE_TYPES = {
    "OFFICIAL_PUBLIC",
    "PUBLIC_COMPANY_FILINGS",
    "USER_PRIVATE_EXPORT",
    "MANUAL_OPERATOR_INPUT",
    "PAID_VENDOR",
    "WEB_SOURCE_REVIEW_REQUIRED",
    "COMMUNITY_DATASET_REVIEW_REQUIRED",
    "INTERNAL_DERIVED",
}

RISKY_USAGE_SCOPES = {
    "PUBLIC_DOC_REFERENCE",
    "PUBLIC_HANDOFF_METADATA_ONLY",
    "PUBLIC_HANDOFF_DERIVED_ALLOWED",
    "DASHBOARD_LOCAL_ALLOWED",
    "COMMERCIAL_REVIEW_REQUIRED",
}

PROHIBITED_PRODUCTION_APPROVAL_STATUSES = {
    "APPROVED_FOR_PRODUCTION",
    "PRODUCTION_APPROVED",
    "COMMERCIAL_APPROVED",
    "APPROVED_FOR_COMMERCIAL_USE",
    "PROVIDER_APPROVED",
    "LEGAL_APPROVED",
    "RUNTIME_APPROVED",
    "ACTIVE_PRODUCTION",
}


def _string(value: Any) -> str:
    return str(value or "").strip()


def _source_label(entry: dict[str, Any], index: int) -> str:
    return _string(entry.get("source_id")) or f"source[{index}]"


def _has_any(values: Any) -> bool:
    return isinstance(values, list) and any(_string(value) for value in values)


def _add_error(errors: list[str], source_id: str, message: str) -> None:
    errors.append(f"{source_id}: {message}")


def validate_registry_template_data(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return {
            "status": "ERROR",
            "template_only": False,
            "source_templates": 0,
            "errors": ["registry root must be a mapping"],
            "warnings": [],
        }

    template_only = data.get("template_only")
    if template_only is not True:
        errors.append("registry template requires template_only=true")

    registry_status = _string(data.get("registry_status") or data.get("current_status"))
    if registry_status in PROHIBITED_PRODUCTION_APPROVAL_STATUSES:
        errors.append(f"registry-level status must not imply production approval: {registry_status}")
    elif registry_status and registry_status not in ALLOWED_CURRENT_STATUSES:
        errors.append(f"registry-level status is not allowed for template preflight: {registry_status}")

    sources = data.get("sources")
    if not isinstance(sources, list):
        errors.append("registry template requires a top-level sources list")
        sources = []

    for index, raw_entry in enumerate(sources):
        if not isinstance(raw_entry, dict):
            errors.append(f"source[{index}]: source entry must be a mapping")
            continue

        entry = deepcopy(raw_entry)
        source_id = _source_label(entry, index)

        missing = [field for field in REQUIRED_SOURCE_FIELDS if field not in entry]
        for field in missing:
            _add_error(errors, source_id, f"missing required field: {field}")

        classification = _string(entry.get("license_classification"))
        usage_scope = _string(entry.get("usage_scope"))
        review_status = _string(entry.get("review_status"))
        source_type = _string(entry.get("source_type"))
        current_status = _string(entry.get("current_status"))

        if classification and classification not in ALLOWED_CLASSIFICATIONS:
            _add_error(errors, source_id, f"invalid license_classification: {classification}")
        if source_type and source_type not in ALLOWED_SOURCE_TYPES:
            _add_error(errors, source_id, f"invalid source_type: {source_type}")
        if source_type and classification and source_type != classification:
            _add_error(errors, source_id, "source_type must match license_classification in the registry template")
        if usage_scope and usage_scope not in ALLOWED_USAGE_SCOPES:
            _add_error(errors, source_id, f"invalid usage_scope: {usage_scope}")
        if review_status and review_status not in ALLOWED_REVIEW_STATUSES:
            _add_error(errors, source_id, f"invalid review_status: {review_status}")
        if current_status in PROHIBITED_PRODUCTION_APPROVAL_STATUSES:
            _add_error(errors, source_id, f"current_status must not imply production approval: {current_status}")
        elif current_status and current_status not in ALLOWED_CURRENT_STATUSES:
            _add_error(errors, source_id, f"invalid current_status: {current_status}")

        for field in BOOL_FIELDS:
            if field in entry and not isinstance(entry.get(field), bool):
                _add_error(errors, source_id, f"{field} must be boolean")

        for field in LIST_FIELDS:
            if field in entry and not isinstance(entry.get(field), list):
                _add_error(errors, source_id, f"{field} must be a list")

        boundary_source_type = source_type if source_type in ALLOWED_SOURCE_TYPES else classification
        is_test_fixture = classification == "TEST_FIXTURE" or boundary_source_type == "TEST_FIXTURE"
        has_license_evidence = _has_any(entry.get("license_evidence_files"))

        if classification == "UNKNOWN_REVIEW_REQUIRED":
            if usage_scope in RISKY_USAGE_SCOPES or entry.get("commercial_use_allowed") or entry.get("redistribution_allowed"):
                _add_error(errors, source_id, "unknown license cannot claim public, dashboard, commercial or redistribution use")

        if entry.get("contains_paid_data") and entry.get("raw_data_handoff_allowed"):
            _add_error(errors, source_id, "paid raw data must not be allowed in public handoff")
        if entry.get("contains_broker_data") and entry.get("raw_data_handoff_allowed"):
            _add_error(errors, source_id, "broker raw data must not be allowed in public handoff")
        if entry.get("contains_personal_data") and entry.get("raw_data_handoff_allowed"):
            _add_error(errors, source_id, "personal raw data must not be allowed in public handoff")

        if entry.get("commercial_use_allowed"):
            _add_error(errors, source_id, "commercial_use_allowed is not permitted in the template preflight; use review-required statuses without claiming approval")

        if entry.get("raw_data_handoff_allowed") and not has_license_evidence:
            _add_error(errors, source_id, "raw_data_handoff_allowed requires explicit license evidence")

        if (
            entry.get("derived_data_handoff_allowed")
            and usage_scope in {"PUBLIC_HANDOFF_METADATA_ONLY", "PUBLIC_HANDOFF_DERIVED_ALLOWED"}
            and not has_license_evidence
        ):
            _add_error(errors, source_id, "derived public handoff requires explicit license evidence")

        if entry.get("redistribution_allowed") and not has_license_evidence:
            _add_error(errors, source_id, "redistribution_allowed requires explicit license evidence")

        if review_status == "UNKNOWN" and usage_scope in RISKY_USAGE_SCOPES:
            _add_error(errors, source_id, "UNKNOWN review_status cannot accompany public, dashboard or commercial usage scope")

        if boundary_source_type in PROVIDER_SPECIFIC_SOURCE_TYPES and entry.get("adapter_required") is False:
            _add_error(errors, source_id, f"{boundary_source_type} requires an adapter boundary")

        if not is_test_fixture and entry.get("provenance_required") is False:
            _add_error(errors, source_id, "non-test sources require provenance")

        if boundary_source_type in TIME_SENSITIVE_SOURCE_TYPES and entry.get("as_of_date_required") is False:
            _add_error(errors, source_id, f"{boundary_source_type} requires as_of_date metadata")

        if boundary_source_type in TIME_SENSITIVE_SOURCE_TYPES and entry.get("snapshot_required") is False:
            _add_error(errors, source_id, f"{boundary_source_type} requires snapshot metadata")

        if _has_any(entry.get("freshness_evidence_files")) and not _has_any(entry.get("license_evidence_files")) and entry.get("redistribution_allowed"):
            _add_error(errors, source_id, "freshness evidence does not satisfy redistribution license evidence")

        if is_test_fixture and entry.get("commercial_use_allowed"):
            _add_error(errors, source_id, "test fixtures must not claim commercial use")

        if review_status in {"APPROVED_FOR_DERIVED_HANDOFF", "APPROVED_FOR_PUBLIC_METADATA_ONLY"} and not has_license_evidence:
            warnings.append(f"{source_id}: public handoff review status should retain license evidence before real use")

    return {
        "status": "OK" if not errors else "ERROR",
        "template_only": template_only is True,
        "source_templates": len(sources),
        "errors": sorted(errors),
        "warnings": sorted(warnings),
    }


def validate_registry_template(path: str = DEFAULT_TEMPLATE_PATH) -> dict[str, Any]:
    return validate_registry_template_data(load_yaml_config(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the CIOS data source registry template without reading providers or runtime data.")
    parser.add_argument("template_path", nargs="?", default=DEFAULT_TEMPLATE_PATH)
    args = parser.parse_args(argv)

    result = validate_registry_template(args.template_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
