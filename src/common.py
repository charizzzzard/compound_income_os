from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent


def resolve_repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def ensure_parent_dir(path_value: str | Path) -> Path:
    path = resolve_repo_path(path_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_yaml_config(path_value: str | Path) -> dict[str, Any]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv_rows(path_value: str | Path) -> list[dict[str, str]]:
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(
    path_value: str | Path,
    fieldnames: Iterable[str],
    rows: Iterable[dict[str, Any]],
) -> Path:
    path = ensure_parent_dir(path_value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in writer.fieldnames})
    return path


def require_columns(rows: list[dict[str, Any]], required_columns: Iterable[str], source_name: str) -> None:
    if not rows:
        raise ValueError(f"{source_name} contains no rows.")
    available = set(rows[0].keys())
    missing = [column for column in required_columns if column not in available]
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"{source_name} missing required columns: {missing_text}")


def require_non_blank_fields(rows: list[dict[str, Any]], required_fields: Iterable[str], source_name: str) -> None:
    fields = list(required_fields)
    for index, row in enumerate(rows, start=2):
        missing = [field for field in fields if not str(row.get(field, "")).strip()]
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"{source_name} row {index} has blank required field(s): {missing_text}")


def canonicalize_ticker(value: Any) -> str:
    ticker = str(value or "").strip().upper()
    if not ticker:
        return ""
    return ticker.replace(" ", "")


def require_unique_tickers(rows: list[dict[str, Any]], source_name: str) -> None:
    require_non_blank_fields(rows, ["ticker"], source_name)
    duplicates: set[str] = set()
    seen: set[str] = set()
    for row in rows:
        ticker = canonicalize_ticker(row.get("ticker", ""))
        if not ticker:
            continue
        if ticker in seen:
            duplicates.add(ticker)
        seen.add(ticker)
    if duplicates:
        duplicate_text = ", ".join(sorted(duplicates))
        raise ValueError(f"{source_name} contains duplicate tickers: {duplicate_text}")


def validate_weight_block(
    config: dict[str, Any],
    block_name: str,
    required_keys: Iterable[str],
    tolerance: float = 1e-6,
) -> dict[str, float]:
    raw_weights = config.get(block_name)
    if not isinstance(raw_weights, dict):
        raise ValueError(f"scoring config missing {block_name} mapping")

    keys = tuple(required_keys)
    missing_keys = [key for key in keys if key not in raw_weights]
    if missing_keys:
        missing_text = ", ".join(sorted(missing_keys))
        raise ValueError(f"{block_name} missing keys: {missing_text}")

    weights: dict[str, float] = {}
    for key in keys:
        value = to_float(raw_weights.get(key), float("nan"))
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"{block_name} contains invalid value for {key}: {raw_weights.get(key)!r}")
        weights[key] = value

    total_weight = sum(weights.values())
    if not math.isclose(total_weight, 1.0, rel_tol=0.0, abs_tol=tolerance):
        raise ValueError(f"{block_name} must sum to 1.0, got {round2(total_weight)}")
    return weights


def normalize_number_text(text: str) -> str:
    cleaned = text.strip().replace(" ", "").replace("\u00a0", "")
    if not cleaned:
        return cleaned

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            return cleaned.replace(".", "").replace(",", ".")
        return cleaned.replace(",", "")

    if "," in cleaned:
        if cleaned.count(",") == 1:
            integer_part, fractional_part = cleaned.split(",", 1)
            if fractional_part.isdigit():
                return f"{integer_part}.{fractional_part}"
        return cleaned.replace(",", "")

    if cleaned.count(".") > 1:
        return cleaned.replace(".", "")
    return cleaned


def to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    text = normalize_number_text(text.replace("%", ""))
    try:
        return float(text)
    except ValueError:
        return default


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y"}


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def round2(value: float) -> float:
    return round(float(value), 2)


def safe_upper(value: Any) -> str:
    return str(value or "").strip().upper()


def mean(values: Iterable[float], default: float = 0.0) -> float:
    items = [float(value) for value in values]
    if not items:
        return default
    return sum(items) / len(items)


def score_linear(value: float, lower: float, upper: float) -> float:
    if upper == lower:
        return 0.0
    normalized = (value - lower) / (upper - lower)
    return clamp(normalized * 100.0)


def format_pct(value: float) -> str:
    return f"{round2(value)}%"


def format_eur(value: float) -> str:
    return f"{round2(value)} EUR"
