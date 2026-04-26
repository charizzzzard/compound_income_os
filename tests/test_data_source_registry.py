from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.data_source_registry import (
    RESOLVED_FIELDS,
    STATUS_FIELDS,
    build_resolved_rows,
    load_personal_data_source_records,
    missing_required_source_keys,
    write_data_source_outputs,
)


class DataSourceRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_paths: list[Path] = []

    def tearDown(self) -> None:
        for path in reversed(self.temp_paths):
            if path.exists():
                path.unlink()

    def _path(self, name: str) -> Path:
        path = Path("tests") / name
        self.temp_paths.append(path)
        return path

    def _write_text(self, path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")

    def _write_config(self, path: Path, sources: dict[str, dict[str, object]]) -> None:
        self._write_text(path, json.dumps({"sources": sources}, indent=2) + "\n")

    def test_registry_valid_happy_path_writes_status_and_resolved_outputs(self) -> None:
        config_path = self._path("_tmp_registry_config.yaml")
        master_path = self._path("_tmp_registry_master.csv")
        watchlist_path = self._path("_tmp_registry_watchlist.csv")
        status_output = self._path("_tmp_registry_status.csv")
        resolved_output = self._path("_tmp_registry_resolved.csv")
        self._write_text(master_path, "ticker,company_name\nMSFT,Microsoft\n")
        self._write_text(watchlist_path, "ticker,company_name\nMSFT,Microsoft\n")
        self._write_config(
            config_path,
            {
                "fundamentals_master": {
                    "enabled": True,
                    "path": str(master_path),
                    "required": True,
                    "kind": "file",
                    "description": "unit test fundamentals master",
                },
                "watchlist_input": {
                    "enabled": True,
                    "path": str(watchlist_path),
                    "required": False,
                    "kind": "file",
                    "description": "unit test watchlist input",
                }
            },
        )

        records = load_personal_data_source_records(str(config_path))
        outputs = write_data_source_outputs(
            records,
            status_output=str(status_output),
            resolved_output=str(resolved_output),
            used_as_default_source_keys={"fundamentals_master"},
        )

        self.assertEqual(set(records), {"fundamentals_master", "watchlist_input"})
        self.assertEqual(set(read_csv_rows(status_output)[0]), set(STATUS_FIELDS))
        self.assertEqual(set(read_csv_rows(resolved_output)[0]), set(RESOLVED_FIELDS))
        self.assertTrue(outputs["data_source_status"].exists())
        self.assertTrue(outputs["data_source_registry_resolved"].exists())
        status_rows = {row["source_key"]: row for row in read_csv_rows(status_output)}
        resolved_rows = {row["source_key"]: row for row in read_csv_rows(resolved_output)}
        self.assertEqual(status_rows["fundamentals_master"]["status"], "OK")
        self.assertEqual(status_rows["watchlist_input"]["status"], "OK")
        self.assertEqual(resolved_rows["fundamentals_master"]["used_as_default_input"], "True")
        self.assertEqual(resolved_rows["watchlist_input"]["used_as_default_input"], "False")

    def test_registry_marks_required_missing_sources(self) -> None:
        config_path = self._path("_tmp_registry_missing.yaml")
        missing_path = self._path("_tmp_registry_missing_master.csv")
        self._write_config(
            config_path,
            {
                "fundamentals_master": {
                    "enabled": True,
                    "path": str(missing_path),
                    "required": True,
                    "kind": "file",
                    "description": "missing required master",
                }
            },
        )

        records = load_personal_data_source_records(str(config_path))

        self.assertEqual(records["fundamentals_master"].status, "MISSING")
        self.assertEqual(missing_required_source_keys(records), ["fundamentals_master"])

    def test_registry_marks_disabled_sources_without_hard_failure(self) -> None:
        config_path = self._path("_tmp_registry_disabled.yaml")
        disabled_path = self._path("_tmp_registry_disabled_input.csv")
        self._write_config(
            config_path,
            {
                "fundamentals_overlay_input": {
                    "enabled": False,
                    "path": str(disabled_path),
                    "required": False,
                    "kind": "file",
                    "description": "disabled overlay input",
                }
            },
        )

        records = load_personal_data_source_records(str(config_path))
        resolved_rows = build_resolved_rows(records)

        self.assertEqual(records["fundamentals_overlay_input"].status, "DISABLED")
        self.assertEqual(resolved_rows[0]["status"], "DISABLED")
        self.assertEqual(resolved_rows[0]["used_as_default_input"], "False")

    def test_registry_rejects_unknown_kind(self) -> None:
        config_path = self._path("_tmp_registry_invalid_kind.yaml")
        self._write_config(
            config_path,
            {
                "fundamentals_master": {
                    "enabled": True,
                    "path": "data/raw/personal_fundamentals_master.csv",
                    "required": True,
                    "kind": "socket",
                    "description": "invalid kind",
                }
            },
        )

        with self.assertRaisesRegex(ValueError, "unsupported kind"):
            load_personal_data_source_records(str(config_path))


if __name__ == "__main__":
    unittest.main()
