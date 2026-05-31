import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

from src.audit_command_provenance import validate_manifest


EXAMPLE_PATH = Path("examples/audit_command_provenance/audit_run_manifest.example.json")
SCHEMA_PATH = Path("docs/schemas/audit_run_manifest.schema.json")
FEATURE_STATUS_PATH = Path("docs/architecture/CIOS_FEATURE_STATUS.yaml")
CONTRACT_PATH = Path("docs/contracts/AUDIT_COMMAND_PROVENANCE_CONTRACT.md")
HANDOFF_CONTRACT_PATH = Path("docs/HANDOFF_CONTRACT.md")


def _load_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_synthetic_example_manifest_validates() -> None:
    result = validate_manifest(_load_example())

    assert result.ok, result.errors
    assert result.entries_total == 4
    assert result.degraded_entries == 2


def test_invalid_paths_are_rejected() -> None:
    manifest = _load_example()

    invalid_paths = [
        "C:\\Users\\operator\\portfolio.csv",
        "/home/operator/portfolio.csv",
        "../outside.csv",
        "C:foo",
        "C:Users/operator/file.csv",
        "D:folder/file",
        "c:relative/path.csv",
    ]

    for invalid_path in invalid_paths:
        candidate = copy.deepcopy(manifest)
        candidate["entries"][0]["input_paths"] = [invalid_path]

        result = validate_manifest(candidate)

        assert not result.ok, invalid_path
        assert any("repo-relative" in error for error in result.errors)


def test_valid_repo_relative_paths_are_accepted() -> None:
    manifest = _load_example()
    manifest["entries"][0]["input_paths"] = [
        ".",
        "outputs/audit/report.md",
        "external_review_packet/AUDIT_VALIDATION_EVIDENCE.md",
        "examples/audit_command_provenance/audit_run_manifest.example.json",
    ]

    result = validate_manifest(manifest)

    assert result.ok, result.errors


def test_unknown_provenance_status_is_rejected() -> None:
    manifest = _load_example()
    manifest["entries"][0]["provenance_status"] = "READY_FOR_REVIEW"

    result = validate_manifest(manifest)

    assert not result.ok
    assert any("provenance_status" in error for error in result.errors)


def test_output_observed_without_command_is_accepted_but_degraded() -> None:
    manifest = _load_example()
    manifest["entries"] = [manifest["entries"][1]]

    result = validate_manifest(manifest)

    assert result.ok, result.errors
    assert result.degraded_entries == 1
    assert any("OUTPUT_OBSERVED_COMMAND_NOT_RECORDED" in warning for warning in result.warnings)


def test_output_observed_without_command_rejects_non_empty_command() -> None:
    manifest = _load_example()
    manifest["entries"] = [copy.deepcopy(manifest["entries"][1])]
    manifest["entries"][0]["command"] = "python -m pytest -q"

    result = validate_manifest(manifest)

    assert not result.ok
    assert any("OUTPUT_OBSERVED_COMMAND_NOT_RECORDED" in error for error in result.errors)


def test_command_reproduced_requires_execution_evidence() -> None:
    manifest = _load_example()
    manifest["entries"] = [copy.deepcopy(manifest["entries"][0])]
    manifest["entries"][0]["command"] = ""
    manifest["entries"][0]["exit_code"] = None

    result = validate_manifest(manifest)

    assert not result.ok
    assert any("COMMAND_REPRODUCED" in error for error in result.errors)


def test_command_reproduced_rejects_skipped_result_status() -> None:
    manifest = _load_example()
    manifest["entries"] = [copy.deepcopy(manifest["entries"][0])]
    manifest["entries"][0]["result_status"] = "SKIPPED"

    result = validate_manifest(manifest)

    assert not result.ok
    assert any("COMMAND_REPRODUCED" in error for error in result.errors)


def test_manifest_entry_run_id_and_repo_head_must_match_top_level() -> None:
    manifest = _load_example()
    manifest["entries"][0]["run_id"] = "different-run"
    manifest["entries"][1]["repo_head"] = "1111111111111111111111111111111111111111"

    result = validate_manifest(manifest)

    assert not result.ok
    assert any("run_id must match manifest.run_id" in error for error in result.errors)
    assert any("repo_head must match manifest.repo_head" in error for error in result.errors)


def test_invalid_timestamps_are_rejected() -> None:
    manifest = _load_example()
    manifest["created_at_utc"] = "2026-01-01 00:00:00"
    manifest["entries"][0]["recorded_at_utc"] = "2026-01-01T00:01:00+01:00"

    result = validate_manifest(manifest)

    assert not result.ok
    assert any("manifest.created_at_utc" in error for error in result.errors)
    assert any("recorded_at_utc" in error for error in result.errors)


def test_skipped_provenance_requires_empty_command_null_exit_and_skipped_result() -> None:
    manifest = _load_example()
    manifest["entries"] = [copy.deepcopy(manifest["entries"][3])]
    manifest["entries"][0]["command"] = "python -m pytest -q"
    manifest["entries"][0]["exit_code"] = 0
    manifest["entries"][0]["result_status"] = "PASS"

    result = validate_manifest(manifest)

    assert not result.ok
    assert any("command must be empty for skipped provenance" in error for error in result.errors)
    assert any("exit_code must be null for skipped provenance" in error for error in result.errors)
    assert any("result_status must be SKIPPED" in error for error in result.errors)


def test_cli_validates_synthetic_example_manifest() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.audit_command_provenance",
            "--manifest",
            str(EXAMPLE_PATH),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "validation_status=PASS" in completed.stdout
    assert "degraded_entries=2" in completed.stdout


def test_cli_returns_nonzero_for_invalid_manifest() -> None:
    manifest = _load_example()
    manifest["entries"][0]["working_directory"] = "C:relative"
    temp_root = Path("tests/_tmp_audit_command_provenance")
    temp_root.mkdir(exist_ok=True)
    try:
        invalid_manifest = temp_root / "invalid_manifest.json"
        invalid_manifest.write_text(json.dumps(manifest), encoding="utf-8")

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.audit_command_provenance",
                "--manifest",
                str(invalid_manifest),
            ],
            capture_output=True,
            text=True,
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    assert completed.returncode != 0
    assert "validation_status=FAIL" in completed.stdout


def test_json_schema_declares_required_fields_and_enums() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    entry_schema = schema["$defs"]["provenance_entry"]

    assert "entries" in schema["required"]
    assert entry_schema["properties"]["provenance_status"]["enum"] == [
        "COMMAND_RECORDED",
        "COMMAND_REPRODUCED",
        "OUTPUT_OBSERVED_COMMAND_NOT_RECORDED",
        "SKIPPED_NO_ENTRYPOINT",
        "SKIPPED_PRIVATE_INPUT_REQUIRED",
        "SKIPPED_DEFERRED",
    ]
    assert "command_kind" in entry_schema["required"]
    assert "result_status" in entry_schema["required"]


def test_example_manifest_matches_schema_required_fields_without_schema_dependency() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    manifest = _load_example()
    entry_required = set(schema["$defs"]["provenance_entry"]["required"])

    assert set(schema["required"]).issubset(manifest)
    for entry in manifest["entries"]:
        assert entry_required.issubset(entry)


def test_feature_status_declares_all_used_status_values() -> None:
    text = FEATURE_STATUS_PATH.read_text(encoding="utf-8")
    status_values_block = text.split("status_values:", 1)[1].split("status_semantics:", 1)[0]
    declared = {
        line.strip()[2:]
        for line in status_values_block.splitlines()
        if line.strip().startswith("- ")
    }
    used = {
        line.split("status:", 1)[1].strip()
        for line in text.splitlines()
        if line.startswith("    status: ")
    }

    assert "documented" in declared
    assert used.issubset(declared)
    assert "documented: \"Docs-only or contract-only capability status" in text


def test_governance_docs_define_validation_provenance_and_zip_policy() -> None:
    combined = (
        CONTRACT_PATH.read_text(encoding="utf-8")
        + "\n"
        + HANDOFF_CONTRACT_PATH.read_text(encoding="utf-8")
    )
    compact = " ".join(combined.split())

    for phrase in [
        "RECORDED_BY_CODEX",
        "EXECUTED_IN_CURRENT_RUN",
        "INDEPENDENTLY_REVIEWED",
        "NOT_AVAILABLE",
        "HANDOFF_LATEST.zip",
    ]:
        assert phrase in combined
    assert "upload and transport artifact" in compact
