import copy
import json
import subprocess
import sys
from pathlib import Path

from src.audit_command_provenance import validate_manifest


EXAMPLE_PATH = Path("examples/audit_command_provenance/audit_run_manifest.example.json")


def _load_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_synthetic_example_manifest_validates() -> None:
    result = validate_manifest(_load_example())

    assert result.ok, result.errors
    assert result.entries_total == 3
    assert result.degraded_entries == 2


def test_absolute_local_path_is_rejected() -> None:
    manifest = _load_example()
    manifest["entries"][0]["input_paths"] = ["C:\\Users\\operator\\portfolio.csv"]

    result = validate_manifest(manifest)

    assert not result.ok
    assert any("repo-relative" in error for error in result.errors)


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


def test_command_reproduced_requires_execution_evidence() -> None:
    manifest = _load_example()
    manifest["entries"] = [copy.deepcopy(manifest["entries"][0])]
    manifest["entries"][0]["command"] = ""
    manifest["entries"][0]["exit_code"] = None

    result = validate_manifest(manifest)

    assert not result.ok
    assert any("COMMAND_REPRODUCED" in error for error in result.errors)


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
