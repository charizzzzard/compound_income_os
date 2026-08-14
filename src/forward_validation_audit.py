from __future__ import annotations

import argparse
from datetime import date, datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping

from src.canonical_record import GENESIS_PREVIOUS_RECORD_HASH, HASH_SCHEMA_VERSION, verify_hash_chain
from src.common import ensure_parent_dir, resolve_repo_path
from src.personal_decision_trigger_capture import (
    DECIMAL_FIELDS as TRIGGER_DECIMAL_FIELDS,
    DEFAULT_LEDGER as DEFAULT_TRIGGER_LEDGER,
    load_trigger_ledger,
)
from src.personal_trigger_resolution import (
    DEFAULT_RESOLUTION_LEDGER,
    load_resolution_ledger,
    validate_resolution_ledger,
)


DEFAULT_ANCHOR_INDEX = "audit/forward_validation/ledger_anchors.jsonl"
TRIGGER_LEDGER_NAME = "personal_decision_triggers"
RESOLUTION_LEDGER_NAME = "personal_trigger_resolutions"
LEDGER_NAMES = {TRIGGER_LEDGER_NAME, RESOLUTION_LEDGER_NAME}
ANCHOR_FIELDS = {
    "anchor_date",
    "ledger_name",
    "row_count",
    "head_hash",
    "hash_schema_version",
    "git_head",
    "created_at",
}
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_HEAD_RE = re.compile(r"^[0-9a-f]{40}$")


def _parse_date(value: Any, field_name: str) -> date:
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO YYYY-MM-DD") from exc


def _parse_datetime(value: Any, field_name: str) -> datetime:
    text = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO timestamp with timezone") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone")
    return parsed


def _validated_anchor_path(path_value: str) -> Path:
    path = resolve_repo_path(path_value).resolve()
    root = resolve_repo_path(".").resolve()
    try:
        relative = path.relative_to(root).as_posix().lower()
    except ValueError as exc:
        raise ValueError("anchor index must be stored inside the repository") from exc
    if relative == "data/processed" or relative.startswith("data/processed/"):
        raise ValueError("tracked anchor index must not be stored under git-ignored data/processed/")
    return path


def _validate_anchor_record(raw: Mapping[str, Any], *, line_number: int) -> dict[str, Any]:
    actual_fields = set(raw)
    if actual_fields != ANCHOR_FIELDS:
        missing = sorted(ANCHOR_FIELDS - actual_fields)
        extra = sorted(actual_fields - ANCHOR_FIELDS)
        raise ValueError(f"anchor line {line_number} field mismatch; missing={missing}, extra={extra}")
    anchor_date = _parse_date(raw["anchor_date"], "anchor_date")
    created_at = _parse_datetime(raw["created_at"], "created_at")
    if created_at.date() < anchor_date:
        raise ValueError(f"anchor line {line_number} created_at must not be before anchor_date")
    ledger_name = str(raw["ledger_name"] or "").strip()
    if ledger_name not in LEDGER_NAMES:
        raise ValueError(f"anchor line {line_number} has unsupported ledger_name: {ledger_name}")
    row_count = raw["row_count"]
    if isinstance(row_count, bool) or not isinstance(row_count, int) or row_count < 0:
        raise ValueError(f"anchor line {line_number} row_count must be a non-negative integer")
    head_hash = str(raw["head_hash"] or "").strip().lower()
    if head_hash != GENESIS_PREVIOUS_RECORD_HASH.lower() and not HASH_RE.fullmatch(head_hash):
        raise ValueError(f"anchor line {line_number} head_hash is invalid")
    schema = str(raw["hash_schema_version"] or "").strip()
    if schema != HASH_SCHEMA_VERSION:
        raise ValueError(f"anchor line {line_number} hash_schema_version must be {HASH_SCHEMA_VERSION}")
    git_head = str(raw["git_head"] or "").strip().lower()
    if not GIT_HEAD_RE.fullmatch(git_head):
        raise ValueError(f"anchor line {line_number} git_head must be a full 40-character commit SHA")
    return {
        "anchor_date": anchor_date.isoformat(),
        "ledger_name": ledger_name,
        "row_count": row_count,
        "head_hash": head_hash.upper() if head_hash == GENESIS_PREVIOUS_RECORD_HASH.lower() else head_hash,
        "hash_schema_version": schema,
        "git_head": git_head,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
    }


def load_anchor_index(path_value: str = DEFAULT_ANCHOR_INDEX) -> list[dict[str, Any]]:
    path = _validated_anchor_path(path_value)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"anchor line {line_number} is not valid JSON") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"anchor line {line_number} must be a JSON object")
        rows.append(_validate_anchor_record(raw, line_number=line_number))
    identities = [
        (row["ledger_name"], row["row_count"], row["head_hash"], row["hash_schema_version"])
        for row in rows
    ]
    if len(set(identities)) != len(identities):
        raise ValueError("anchor index contains a duplicate ledger head")
    return rows


def verify_forward_validation_ledgers(
    *,
    trigger_ledger: str = DEFAULT_TRIGGER_LEDGER,
    resolution_ledger: str = DEFAULT_RESOLUTION_LEDGER,
    anchor_index: str = DEFAULT_ANCHOR_INDEX,
) -> dict[str, Any]:
    trigger_rows = load_trigger_ledger(trigger_ledger)
    resolution_rows = load_resolution_ledger(resolution_ledger)
    if trigger_rows:
        trigger_head = verify_hash_chain(trigger_rows, decimal_fields=TRIGGER_DECIMAL_FIELDS)
    else:
        trigger_head = GENESIS_PREVIOUS_RECORD_HASH
    if resolution_rows:
        if not trigger_rows:
            raise ValueError("resolution ledger cannot contain rows without a trigger ledger")
        resolution_head = validate_resolution_ledger(resolution_rows, trigger_rows=trigger_rows)
    else:
        resolution_head = GENESIS_PREVIOUS_RECORD_HASH

    anchors = load_anchor_index(anchor_index)
    latest_by_ledger: dict[str, dict[str, Any]] = {}
    for anchor in anchors:
        latest_by_ledger[anchor["ledger_name"]] = anchor

    ledgers = {
        TRIGGER_LEDGER_NAME: {"row_count": len(trigger_rows), "head_hash": trigger_head},
        RESOLUTION_LEDGER_NAME: {"row_count": len(resolution_rows), "head_hash": resolution_head},
    }
    ledger_rows = {
        TRIGGER_LEDGER_NAME: trigger_rows,
        RESOLUTION_LEDGER_NAME: resolution_rows,
    }
    for ledger_name, state in ledgers.items():
        latest = latest_by_ledger.get(ledger_name)
        if latest is None:
            state["anchor_status"] = "UNANCHORED"
        elif latest["row_count"] == state["row_count"] and latest["head_hash"] == state["head_hash"]:
            state["anchor_status"] = "MATCH"
        elif state["row_count"] > latest["row_count"]:
            prefix_matches = (
                latest["row_count"] == 0
                and latest["head_hash"] == GENESIS_PREVIOUS_RECORD_HASH
            ) or (
                latest["row_count"] > 0
                and ledger_rows[ledger_name][latest["row_count"] - 1]["record_hash"] == latest["head_hash"]
            )
            state["anchor_status"] = (
                "LEDGER_ADVANCED_SINCE_ANCHOR" if prefix_matches else "ANCHOR_MISMATCH"
            )
        else:
            state["anchor_status"] = "ANCHOR_MISMATCH"
    return {
        "verification_status": "PASS",
        "hash_schema_version": HASH_SCHEMA_VERSION,
        "tamper_evidence": "TAMPER_EVIDENT_NOT_TAMPER_PROOF",
        "anchor_index_row_count": len(anchors),
        "ledgers": ledgers,
    }


def append_ledger_anchor(
    *,
    ledger_name: str,
    anchor_date: str,
    created_at: str,
    git_head: str,
    trigger_ledger: str = DEFAULT_TRIGGER_LEDGER,
    resolution_ledger: str = DEFAULT_RESOLUTION_LEDGER,
    anchor_index: str = DEFAULT_ANCHOR_INDEX,
) -> tuple[bool, dict[str, Any]]:
    normalized_name = str(ledger_name or "").strip()
    if normalized_name not in LEDGER_NAMES:
        raise ValueError(f"ledger_name must be one of {sorted(LEDGER_NAMES)}")
    verification = verify_forward_validation_ledgers(
        trigger_ledger=trigger_ledger,
        resolution_ledger=resolution_ledger,
        anchor_index=anchor_index,
    )
    state = verification["ledgers"][normalized_name]
    candidate = _validate_anchor_record(
        {
            "anchor_date": anchor_date,
            "ledger_name": normalized_name,
            "row_count": state["row_count"],
            "head_hash": state["head_hash"],
            "hash_schema_version": HASH_SCHEMA_VERSION,
            "git_head": git_head,
            "created_at": created_at,
        },
        line_number=len(load_anchor_index(anchor_index)) + 1,
    )
    existing = load_anchor_index(anchor_index)
    identity = (
        candidate["ledger_name"],
        candidate["row_count"],
        candidate["head_hash"],
        candidate["hash_schema_version"],
    )
    for row in existing:
        row_identity = (row["ledger_name"], row["row_count"], row["head_hash"], row["hash_schema_version"])
        if row_identity == identity:
            return False, row

    path = _validated_anchor_path(anchor_index)
    ensure_parent_dir(path)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(candidate, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n")
    load_anchor_index(anchor_index)
    return True, candidate


def _current_git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=resolve_repo_path("."),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ValueError("unable to resolve current Git HEAD for anchor")
    return completed.stdout.strip()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify forward-validation hash chains or append a content-free tracked ledger anchor."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--trigger-ledger", default=DEFAULT_TRIGGER_LEDGER)
    verify.add_argument("--resolution-ledger", default=DEFAULT_RESOLUTION_LEDGER)
    verify.add_argument("--anchor-index", default=DEFAULT_ANCHOR_INDEX)

    anchor = subparsers.add_parser("anchor")
    anchor.add_argument("--ledger-name", choices=sorted(LEDGER_NAMES), required=True)
    anchor.add_argument("--anchor-date", required=True)
    anchor.add_argument("--created-at", required=True)
    anchor.add_argument("--git-head")
    anchor.add_argument("--trigger-ledger", default=DEFAULT_TRIGGER_LEDGER)
    anchor.add_argument("--resolution-ledger", default=DEFAULT_RESOLUTION_LEDGER)
    anchor.add_argument("--anchor-index", default=DEFAULT_ANCHOR_INDEX)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    try:
        if args.command == "verify":
            result = verify_forward_validation_ledgers(
                trigger_ledger=args.trigger_ledger,
                resolution_ledger=args.resolution_ledger,
                anchor_index=args.anchor_index,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return
        appended, anchor = append_ledger_anchor(
            ledger_name=args.ledger_name,
            anchor_date=args.anchor_date,
            created_at=args.created_at,
            git_head=args.git_head or _current_git_head(),
            trigger_ledger=args.trigger_ledger,
            resolution_ledger=args.resolution_ledger,
            anchor_index=args.anchor_index,
        )
        print(f"anchor_appended={str(appended).lower()}")
        print(json.dumps(anchor, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
