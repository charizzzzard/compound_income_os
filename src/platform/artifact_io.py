"""Deterministic CSV/Markdown IO with atomic writes. Stdlib-only."""

from __future__ import annotations

import csv
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def write_csv_atomic(
    path: str | Path,
    rows: list[dict[str, str]],
    headers: list[str],
    identity_keys: list[str] | None = None,
) -> None:
    """Write CSV via temp+replace; sort rows when ``identity_keys`` are set."""
    target = Path(path)
    ordered_headers = sorted(headers)
    ordered_rows = _ordered_rows(rows, identity_keys)

    def write(handle) -> None:
        writer = csv.DictWriter(handle, fieldnames=ordered_headers, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in ordered_rows:
            writer.writerow({header: row.get(header, "") for header in ordered_headers})

    _atomic_text_write(target, write, newline="")


def read_csv_safe(path: str | Path) -> list[dict[str, str]]:
    """Read CSV with explicit UTF-8 strict decoding and skipinitialspace."""
    with Path(path).open("r", encoding="utf-8", errors="strict", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        return [dict(row) for row in reader]


def write_markdown_atomic(path: str | Path, content: str) -> None:
    _atomic_text_write(Path(path), lambda handle: handle.write(content), newline=None)


def _ordered_rows(rows: list[dict[str, str]], identity_keys: list[str] | None) -> list[dict[str, str]]:
    if not identity_keys:
        return list(rows)
    return sorted(rows, key=lambda row: tuple(row.get(key, "") for key in identity_keys))


def _atomic_text_write(target: Path, writer, newline: str | None) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path: str | None = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", errors="strict", newline=newline, dir=target.parent, delete=False) as handle:
            temp_path = handle.name
            writer(handle)
        os.replace(temp_path, target)
        temp_path = None
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
