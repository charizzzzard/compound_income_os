from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.platform.artifact_io import read_csv_safe, write_csv_atomic, write_markdown_atomic


class PlatformArtifactIoTests(unittest.TestCase):
    def test_write_csv_atomic_sorts_headers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"

            write_csv_atomic(path, [{"b": "2", "a": "1"}], ["b", "a"])

            self.assertEqual(path.read_text(encoding="utf-8").splitlines()[0], "a,b")

    def test_write_csv_atomic_sorts_rows_when_identity_keys_are_given(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"

            write_csv_atomic(path, [{"ticker": "BBB"}, {"ticker": "AAA"}], ["ticker"], identity_keys=["ticker"])

            self.assertEqual(path.read_text(encoding="utf-8").splitlines(), ["ticker", "AAA", "BBB"])

    def test_read_csv_safe_uses_skipinitialspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "in.csv"
            path.write_text("ticker, score\nAAA, 90\n", encoding="utf-8")

            self.assertEqual(read_csv_safe(path), [{"ticker": "AAA", "score": "90"}])

    def test_write_markdown_atomic_writes_utf8_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"

            write_markdown_atomic(path, "# Report\n")

            self.assertEqual(path.read_text(encoding="utf-8"), "# Report\n")

    def test_atomic_write_failure_removes_temp_file_and_preserves_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            path.write_text("old\n", encoding="utf-8")
            before = set(os.listdir(tmp))

            with patch("src.platform.artifact_io.os.replace", side_effect=OSError("replace failed")):
                with self.assertRaisesRegex(OSError, "replace failed"):
                    write_csv_atomic(path, [{"ticker": "AAA"}], ["ticker"])

            self.assertEqual(path.read_text(encoding="utf-8"), "old\n")
            self.assertEqual(set(os.listdir(tmp)), before)


if __name__ == "__main__":
    unittest.main()
