"""Read-only Data Freshness / Staleness summary producer."""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .common import ensure_parent_dir, load_yaml_config, read_csv_rows, resolve_repo_path


CONTRACT_VERSION = "v1"
DEFAULT_CONFIG = "configs/data_freshness_thresholds.yaml"
DEFAULT_OUT_JSON = "reports/latest/data_freshness_summary.json"
DEFAULT_REPORT = "reports/latest/data_freshness_summary.md"

STATUS_VALUES = {
    "FRESH",
    "STALE",
    "MISSING",
    "UNKNOWN",
    "REVIEW_REQUIRED",
    "NOT_APPLICABLE",
}

STATUS_PRIORITY = ["REVIEW_REQUIRED", "MISSING", "STALE", "UNKNOWN", "FRESH", "NOT_APPLICABLE"]
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
UNC_RE = re.compile(r"^(?:\\\\|//)")


@dataclass(frozen=True)
class FreshnessItemConfig:
    data_class: str
    source_path: str
    freshness_date_fields: tuple[str, ...]
    threshold_days: int
    required: bool
    missing_behavior: str
    unknown_behavior: str
    review_on_stale: bool
    review_on_missing: bool
    review_on_unknown: bool
    blocks_dashboard: bool
    blocks_replay: bool
    blocks_outcome_attribution: bool


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    normalized = raw[:10]
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _safe_source_path(raw_path: str, data_class: str) -> tuple[Path | None, str, bool]:
    raw = str(raw_path or "").strip()
    if not raw:
        return None, f"EXTERNAL_PATH_REDACTED:{data_class}", True
    if WINDOWS_ABSOLUTE_RE.match(raw) or UNC_RE.match(raw):
        return None, f"EXTERNAL_PATH_REDACTED:{data_class}", True

    repo_root = _repo_root()
    candidate = Path(raw)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (repo_root / candidate).resolve()

    try:
        relative = resolved.relative_to(repo_root)
    except ValueError:
        return None, f"EXTERNAL_PATH_REDACTED:{data_class}", True
    return resolved, relative.as_posix(), False


def _load_config(config_path: str | Path) -> tuple[str, list[FreshnessItemConfig]]:
    data = load_yaml_config(config_path)
    version = str(data.get("contract_version") or CONTRACT_VERSION)
    raw_items = data.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("data freshness config must define non-empty items")

    seen: set[str] = set()
    items: list[FreshnessItemConfig] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("each freshness config item must be a mapping")
        data_class = str(raw.get("data_class") or "").strip()
        if not data_class:
            raise ValueError("freshness config item missing data_class")
        if data_class in seen:
            raise ValueError(f"duplicate data_class: {data_class}")
        seen.add(data_class)

        fields = raw.get("freshness_date_fields")
        if not isinstance(fields, list) or not fields:
            raise ValueError(f"{data_class}: freshness_date_fields must be non-empty list")
        threshold = raw.get("threshold_days")
        if not isinstance(threshold, int) or threshold < 0:
            raise ValueError(f"{data_class}: threshold_days must be non-negative integer")

        missing_behavior = str(raw.get("missing_behavior") or "MISSING").strip()
        unknown_behavior = str(raw.get("unknown_behavior") or "UNKNOWN").strip()
        if missing_behavior not in STATUS_VALUES:
            raise ValueError(f"{data_class}: invalid missing_behavior {missing_behavior}")
        if unknown_behavior not in STATUS_VALUES:
            raise ValueError(f"{data_class}: invalid unknown_behavior {unknown_behavior}")

        items.append(
            FreshnessItemConfig(
                data_class=data_class,
                source_path=str(raw.get("source_path") or ""),
                freshness_date_fields=tuple(str(field) for field in fields),
                threshold_days=threshold,
                required=bool(raw.get("required", True)),
                missing_behavior=missing_behavior,
                unknown_behavior=unknown_behavior,
                review_on_stale=bool(raw.get("review_on_stale", True)),
                review_on_missing=bool(raw.get("review_on_missing", True)),
                review_on_unknown=bool(raw.get("review_on_unknown", True)),
                blocks_dashboard=bool(raw.get("blocks_dashboard", True)),
                blocks_replay=bool(raw.get("blocks_replay", True)),
                blocks_outcome_attribution=bool(raw.get("blocks_outcome_attribution", True)),
            )
        )
    return version, items


def _latest_date_from_records(
    records: Iterable[dict[str, Any]],
    fields: Iterable[str],
) -> tuple[date | None, str | None, str]:
    latest: date | None = None
    latest_field: str | None = None
    saw_invalid = False
    for row in records:
        for field in fields:
            if field not in row:
                continue
            raw_value = row.get(field)
            if raw_value in (None, ""):
                continue
            parsed = _parse_date(raw_value)
            if parsed is None:
                saw_invalid = True
                continue
            if latest is None or parsed > latest:
                latest = parsed
                latest_field = field
    if latest is not None:
        return latest, latest_field, "DATE_SIGNAL_FOUND"
    if saw_invalid:
        return None, None, "INVALID_DATE_SIGNAL"
    return None, None, "NO_DATE_SIGNAL"


def _read_date_signal(path: Path, fields: tuple[str, ...]) -> tuple[date | None, str | None, str]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None, None, "UNREADABLE_ARTIFACT"
        if isinstance(data, dict):
            return _latest_date_from_records([data], fields)
        if isinstance(data, list):
            dict_rows = [item for item in data if isinstance(item, dict)]
            return _latest_date_from_records(dict_rows, fields)
        return None, None, "UNSUPPORTED_JSON_SHAPE"

    try:
        rows = read_csv_rows(path)
    except (OSError, csv.Error, UnicodeDecodeError):
        return None, None, "UNREADABLE_ARTIFACT"
    return _latest_date_from_records(rows, fields)


def _item_status(
    config: FreshnessItemConfig,
    effective_as_of_date: date,
) -> dict[str, Any]:
    resolved_path, safe_path, redacted = _safe_source_path(config.source_path, config.data_class)
    if redacted:
        return {
            "data_class": config.data_class,
            "source_path": safe_path,
            "freshness_status": "REVIEW_REQUIRED",
            "age_days": None,
            "as_of_date": None,
            "threshold_days": config.threshold_days,
            "evidence_source": None,
            "reason": "EXTERNAL_PATH_REDACTED",
            "blocks_dashboard": config.blocks_dashboard,
            "blocks_replay": config.blocks_replay,
            "blocks_outcome_attribution": config.blocks_outcome_attribution,
            "review_required": True,
        }

    assert resolved_path is not None
    if not resolved_path.exists():
        status = config.missing_behavior if not config.required else "MISSING"
        review_required = config.review_on_missing and status != "NOT_APPLICABLE"
        return {
            "data_class": config.data_class,
            "source_path": safe_path,
            "freshness_status": status,
            "age_days": None,
            "as_of_date": None,
            "threshold_days": config.threshold_days,
            "evidence_source": None,
            "reason": "ARTIFACT_MISSING" if status != "NOT_APPLICABLE" else "NOT_APPLICABLE_MISSING_OPTIONAL_ARTIFACT",
            "blocks_dashboard": config.blocks_dashboard,
            "blocks_replay": config.blocks_replay,
            "blocks_outcome_attribution": config.blocks_outcome_attribution,
            "review_required": review_required,
        }

    signal_date, signal_field, signal_reason = _read_date_signal(resolved_path, config.freshness_date_fields)
    if signal_date is None:
        status = config.unknown_behavior
        review_required = config.review_on_unknown and status != "NOT_APPLICABLE"
        return {
            "data_class": config.data_class,
            "source_path": safe_path,
            "freshness_status": status,
            "age_days": None,
            "as_of_date": None,
            "threshold_days": config.threshold_days,
            "evidence_source": None,
            "reason": signal_reason,
            "blocks_dashboard": config.blocks_dashboard,
            "blocks_replay": config.blocks_replay,
            "blocks_outcome_attribution": config.blocks_outcome_attribution,
            "review_required": review_required,
        }

    age_days = (effective_as_of_date - signal_date).days
    if age_days < 0:
        status = "REVIEW_REQUIRED"
        reason = "SOURCE_DATE_AFTER_AS_OF"
        review_required = True
    elif age_days > config.threshold_days:
        status = "STALE"
        reason = "THRESHOLD_EXCEEDED"
        review_required = config.review_on_stale
    else:
        status = "FRESH"
        reason = "WITHIN_THRESHOLD"
        review_required = False

    return {
        "data_class": config.data_class,
        "source_path": safe_path,
        "freshness_status": status,
        "age_days": age_days,
        "as_of_date": signal_date.isoformat(),
        "threshold_days": config.threshold_days,
        "evidence_source": f"field:{signal_field}" if signal_field else None,
        "reason": reason,
        "blocks_dashboard": config.blocks_dashboard,
        "blocks_replay": config.blocks_replay,
        "blocks_outcome_attribution": config.blocks_outcome_attribution,
        "review_required": review_required,
    }


def _overall_status(items: list[dict[str, Any]]) -> str:
    statuses = {str(item["freshness_status"]) for item in items}
    if any(item.get("review_required") for item in items):
        if "REVIEW_REQUIRED" in statuses:
            return "REVIEW_REQUIRED"
        for status in STATUS_PRIORITY:
            if status in statuses and status not in {"FRESH", "NOT_APPLICABLE"}:
                return status
    if all(status in {"FRESH", "NOT_APPLICABLE"} for status in statuses):
        return "FRESH"
    for status in STATUS_PRIORITY:
        if status in statuses:
            return status
    return "UNKNOWN"


def build_data_freshness_summary(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    as_of_date: str,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    effective_as_of_date = date.fromisoformat(as_of_date)
    contract_version, configs = _load_config(config_path)
    items = [_item_status(config, effective_as_of_date) for config in configs]

    summary_counts = {status: 0 for status in STATUS_VALUES}
    for item in items:
        summary_counts[str(item["freshness_status"])] += 1

    overall_status = _overall_status(items)
    return {
        "contract_version": contract_version,
        "generated_at_utc": generated_at_utc
        or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "overall_status": overall_status,
        "review_required": any(bool(item.get("review_required")) for item in items),
        "summary_counts": dict(sorted(summary_counts.items())),
        "items": sorted(items, key=lambda item: str(item["data_class"])),
    }


def write_summary_json(summary: dict[str, Any], output_path: str | Path) -> None:
    path = resolve_repo_path(output_path)
    ensure_parent_dir(path)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Data Freshness / Staleness Summary",
        "",
        f"- contract_version: `{summary['contract_version']}`",
        f"- generated_at_utc: `{summary['generated_at_utc']}`",
        f"- overall_status: `{summary['overall_status']}`",
        f"- review_required: `{str(summary['review_required']).lower()}`",
        "",
        "## Items",
        "",
        "| data_class | status | age_days | as_of_date | threshold_days | evidence_source | reason | review_required |",
        "|---|---:|---:|---|---:|---|---|---:|",
    ]
    for item in summary["items"]:
        lines.append(
            "| {data_class} | {freshness_status} | {age_days} | {as_of_date} | {threshold_days} | {evidence_source} | {reason} | {review_required} |".format(
                data_class=item["data_class"],
                freshness_status=item["freshness_status"],
                age_days="" if item["age_days"] is None else item["age_days"],
                as_of_date=item["as_of_date"] or "",
                threshold_days=item["threshold_days"],
                evidence_source=item["evidence_source"] or "",
                reason=item["reason"],
                review_required=str(item["review_required"]).lower(),
            )
        )
    lines.extend(
        [
            "",
            "## Dashboard / Replay / Outcome Blockers",
            "",
        ]
    )
    blocking_items = [
        item
        for item in summary["items"]
        if item["review_required"]
        or item["freshness_status"] in {"STALE", "MISSING", "UNKNOWN", "REVIEW_REQUIRED"}
    ]
    if blocking_items:
        for item in blocking_items:
            lines.append(
                f"- `{item['data_class']}`: `{item['freshness_status']}` / `{item['reason']}` "
                f"(dashboard={str(item['blocks_dashboard']).lower()}, "
                f"replay={str(item['blocks_replay']).lower()}, "
                f"outcome={str(item['blocks_outcome_attribution']).lower()})"
            )
    else:
        lines.append("- No freshness blockers found.")
    lines.extend(
        [
            "",
            "## Non-Scope",
            "",
            "- no broker/order/trading",
            "- no score formula change",
            "- no portfolio rule change",
            "- no silent data enrichment",
            "- no simulation/backtesting",
            "- no outcome attribution",
            "- no runtime LLM decisioning",
            "- no tax quantification",
            "- no portfolio event ledger",
            "- no private raw data",
            "",
        ]
    )
    return "\n".join(lines)


def write_summary_markdown(summary: dict[str, Any], output_path: str | Path) -> None:
    path = resolve_repo_path(output_path)
    ensure_parent_dir(path)
    path.write_text(render_markdown(summary), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Data Freshness / Staleness summary")
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--out-json", default=DEFAULT_OUT_JSON)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    summary = build_data_freshness_summary(config_path=args.config, as_of_date=args.as_of_date)
    write_summary_json(summary, args.out_json)
    write_summary_markdown(summary, args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

