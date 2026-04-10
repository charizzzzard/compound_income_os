from __future__ import annotations

from typing import Any


def merge_company_records(*record_sets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for records in record_sets:
        for record in records:
            ticker = str(record.get("ticker", "")).strip()
            if not ticker:
                continue
            current = merged.setdefault(ticker, {})
            for key, value in record.items():
                if value not in ("", None):
                    current[key] = value
    return merged
