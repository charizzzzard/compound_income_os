"""Shared validation helpers. Stdlib-only."""

from __future__ import annotations


def validate_required_columns(rows: list[dict[str, str]], required: list[str]) -> list[tuple[int, list[str]]]:
    """Return ``(row_index, missing_columns)`` for rows lacking required keys."""
    missing_rows: list[tuple[int, list[str]]] = []
    for row_index, row in enumerate(rows):
        missing = [column for column in required if column not in row]
        if missing:
            missing_rows.append((row_index, missing))
    return missing_rows


def validate_enum(value: str, allowed: tuple[str, ...]) -> bool:
    return value in allowed


def validate_numeric_range(value: float, low: float, high: float) -> str | None:
    """Return an error message if ``value`` is outside ``low..high``."""
    if low > high:
        raise ValueError("low must be less than or equal to high")
    if value < low:
        return f"value {value} is below minimum {low}"
    if value > high:
        return f"value {value} is above maximum {high}"
    return None
