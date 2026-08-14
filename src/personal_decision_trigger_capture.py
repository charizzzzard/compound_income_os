from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import date, datetime
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from src.canonical_record import (
    GENESIS_PREVIOUS_RECORD_HASH,
    HASH_SCHEMA_VERSION,
    build_hashed_record,
    normalize_decimal_string,
    verify_hash_chain,
)
from src.common import ensure_parent_dir, load_yaml_config, read_csv_rows, resolve_repo_path
from src.personal_decision_state_capture import normalize_source_paths


DEFAULT_DECISION_JOURNAL = "data/processed/personal_decision_state_capture.csv"
DEFAULT_PROPOSALS = "data/processed/personal_decision_trigger_proposals.json"
DEFAULT_LEDGER = "data/processed/personal_decision_triggers.csv"
DEFAULT_POLICY = "configs/forward_validation_policy.yaml"

DECIMAL_FIELDS = ("threshold", "tolerance", "probability_holds")
OPERATORS = {">=", ">", "<=", "<", "==", "!="}
CLAIM_TYPE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
TRUE_TEXT = {"true", "1", "yes"}

PROPOSAL_FIELDS = [
    "trigger_id",
    "decision_id",
    "claim",
    "claim_type",
    "material",
    "decision_relevant",
    "future_facing",
    "falsifiable",
    "deterministically_resolvable",
    "tautological",
    "already_known",
    "purely_narrative_without_resolution_rule",
    "metric_name",
    "metric_definition_version",
    "source_document_type",
    "source_section",
    "line_item",
    "fallback_computation",
    "tolerance",
    "ambiguity_rule",
    "operator",
    "threshold",
    "unit",
    "probability_holds",
    "expected_resolution_date",
    "resolution_deadline",
    "policy_version",
    "created_at",
    "source_paths",
    "supersedes_trigger_id",
]

FIELDS = [
    *PROPOSAL_FIELDS,
    "locked_at",
    "hash_schema_version",
    "record_hash",
    "previous_record_hash",
]

REQUIRED_NON_BLANK_FIELDS = [
    field
    for field in PROPOSAL_FIELDS
    if field != "supersedes_trigger_id"
]


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


def _true_flag(value: Any, field_name: str) -> str:
    if value is True or str(value or "").strip().lower() in TRUE_TEXT:
        return "true"
    raise ValueError(f"{field_name} must be true for a locked trigger proposal")


def _false_flag(value: Any, field_name: str) -> str:
    if value is False or str(value or "").strip().lower() in {"false", "0", "no"}:
        return "false"
    raise ValueError(f"{field_name} must be false for a locked trigger proposal")


def _load_decision_ids(path_value: str) -> set[str]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        raise ValueError(f"decision journal is missing: {path_value}")
    rows = read_csv_rows(path)
    ids = [str(row.get("decision_id", "") or "").strip() for row in rows]
    if any(not decision_id for decision_id in ids):
        raise ValueError("decision journal contains a blank decision_id")
    duplicates = sorted(decision_id for decision_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"decision journal contains duplicate decision_id value(s): {', '.join(duplicates)}")
    return set(ids)


def _load_policy(path_value: str) -> dict[str, Any]:
    policy = load_yaml_config(path_value)
    if policy.get("confirmatory_registration_enabled") is not False:
        raise ValueError("forward validation v1 requires confirmatory_registration_enabled=false")
    return policy


def normalize_trigger_proposal(
    raw: Mapping[str, Any],
    *,
    decision_ids: set[str],
    policy_version: str,
) -> dict[str, str]:
    row = {field: raw.get(field, "") for field in PROPOSAL_FIELDS}
    missing = [
        field
        for field in REQUIRED_NON_BLANK_FIELDS
        if row.get(field) is None or (isinstance(row.get(field), str) and not str(row.get(field)).strip())
    ]
    if missing:
        raise ValueError(f"trigger proposal missing required field(s): {', '.join(missing)}")

    trigger_id = str(row["trigger_id"]).strip()
    decision_id = str(row["decision_id"]).strip()
    if decision_id not in decision_ids:
        raise ValueError(f"decision_id does not exist in Decision Capture: {decision_id}")
    claim_type = str(row["claim_type"]).strip().upper()
    if not CLAIM_TYPE_RE.fullmatch(claim_type):
        raise ValueError("claim_type must be an uppercase identifier")
    operator = str(row["operator"]).strip()
    if operator not in OPERATORS:
        raise ValueError(f"operator must be one of {sorted(OPERATORS)}")

    probability = normalize_decimal_string(row["probability_holds"], field_name="probability_holds")
    probability_number = _decimal_for_comparison(probability)
    if probability_number < 0 or probability_number > 1:
        raise ValueError("probability_holds must be between 0 and 1")
    threshold = normalize_decimal_string(row["threshold"], field_name="threshold")
    tolerance = normalize_decimal_string(row["tolerance"], field_name="tolerance")
    if _decimal_for_comparison(tolerance) < 0:
        raise ValueError("tolerance must be >= 0")

    created_at = _parse_datetime(row["created_at"], "created_at")
    expected = _parse_date(row["expected_resolution_date"], "expected_resolution_date")
    deadline = _parse_date(row["resolution_deadline"], "resolution_deadline")
    if expected <= created_at.date():
        raise ValueError("expected_resolution_date must be after created_at")
    if deadline < expected:
        raise ValueError("resolution_deadline must be on or after expected_resolution_date")
    stored_policy = str(row["policy_version"]).strip()
    if stored_policy != policy_version:
        raise ValueError(f"policy_version must be {policy_version}")

    normalized = {field: str(row.get(field, "") or "").strip() for field in PROPOSAL_FIELDS}
    normalized.update(
        {
            "trigger_id": trigger_id,
            "decision_id": decision_id,
            "claim_type": claim_type,
            "material": _true_flag(row["material"], "material"),
            "decision_relevant": _true_flag(row["decision_relevant"], "decision_relevant"),
            "future_facing": _true_flag(row["future_facing"], "future_facing"),
            "falsifiable": _true_flag(row["falsifiable"], "falsifiable"),
            "deterministically_resolvable": _true_flag(row["deterministically_resolvable"], "deterministically_resolvable"),
            "tautological": _false_flag(row["tautological"], "tautological"),
            "already_known": _false_flag(row["already_known"], "already_known"),
            "purely_narrative_without_resolution_rule": _false_flag(
                row["purely_narrative_without_resolution_rule"],
                "purely_narrative_without_resolution_rule",
            ),
            "operator": operator,
            "threshold": threshold,
            "tolerance": tolerance,
            "probability_holds": probability,
            "created_at": created_at.isoformat().replace("+00:00", "Z"),
            "source_paths": normalize_source_paths(str(row["source_paths"])),
        }
    )
    return normalized


def _decimal_for_comparison(value: str):
    from decimal import Decimal

    return Decimal(value)


def _read_proposal_input(path_value: str) -> list[dict[str, Any]]:
    data = json.loads(resolve_repo_path(path_value).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("proposals")
    if not isinstance(data, list):
        raise ValueError("proposal input must be a JSON list or an object with a proposals list")
    if not all(isinstance(item, dict) for item in data):
        raise ValueError("every proposal must be a JSON object")
    return [dict(item) for item in data]


def write_trigger_proposals(
    proposals: Iterable[Mapping[str, Any]],
    *,
    decision_journal: str = DEFAULT_DECISION_JOURNAL,
    output: str = DEFAULT_PROPOSALS,
    policy: str = DEFAULT_POLICY,
) -> Path:
    decision_ids = _load_decision_ids(decision_journal)
    config = _load_policy(policy)
    policy_version = str(config.get("policy_version", "") or "").strip()
    rows = [normalize_trigger_proposal(item, decision_ids=decision_ids, policy_version=policy_version) for item in proposals]
    trigger_ids = [row["trigger_id"] for row in rows]
    duplicates = sorted(trigger_id for trigger_id, count in Counter(trigger_ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate trigger_id proposal(s): {', '.join(duplicates)}")
    rows.sort(key=lambda row: (row["decision_id"], row["trigger_id"]))
    generated_at = max((row["created_at"] for row in rows), default="NOT_APPLICABLE")
    artifact = {
        "artifact_status": "NON_CANONICAL_REPLACEABLE_PROPOSAL",
        "generated_at": generated_at,
        "policy_version": policy_version,
        "schema_version": "1",
        "proposals": rows,
    }
    path = ensure_parent_dir(output)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    return path


def load_trigger_ledger(path_value: str = DEFAULT_LEDGER) -> list[dict[str, str]]:
    path = resolve_repo_path(path_value)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [field for field in FIELDS if field not in fieldnames]
        if missing:
            raise ValueError(f"trigger ledger missing required columns: {', '.join(missing)}")
        return [
            {field: str(row.get(field, "") or "").strip() for field in FIELDS}
            for row in reader
            if any(str(value or "").strip() for value in row.values())
        ]


def _write_trigger_ledger(path_value: str, rows: list[dict[str, str]]) -> Path:
    path = ensure_parent_dir(path_value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in FIELDS} for row in rows)
    return path


def active_trigger_rows(rows: Iterable[Mapping[str, str]], decision_id: str | None = None) -> list[dict[str, str]]:
    items = [dict(row) for row in rows if decision_id is None or row.get("decision_id") == decision_id]
    superseded = {row.get("supersedes_trigger_id", "") for row in items if row.get("supersedes_trigger_id", "")}
    return [row for row in items if row.get("trigger_id", "") not in superseded]


def validate_trigger_ledger(
    rows: list[dict[str, str]],
    *,
    decision_ids: set[str],
    policy_config: Mapping[str, Any],
) -> str:
    trigger_ids = [row.get("trigger_id", "") for row in rows]
    duplicates = sorted(trigger_id for trigger_id, count in Counter(trigger_ids).items() if trigger_id and count > 1)
    if duplicates:
        raise ValueError(f"duplicate trigger_id value(s): {', '.join(duplicates)}")
    policy_version = str(policy_config.get("policy_version", "") or "")
    for row in rows:
        normalize_trigger_proposal(row, decision_ids=decision_ids, policy_version=policy_version)
        created = _parse_datetime(row.get("created_at"), "created_at")
        locked = _parse_datetime(row.get("locked_at"), "locked_at")
        expected = _parse_date(row.get("expected_resolution_date"), "expected_resolution_date")
        if created > locked:
            raise ValueError("created_at must not be after locked_at")
        if expected <= locked.date():
            raise ValueError("expected_resolution_date must be after locked_at")
    by_id = {row["trigger_id"]: row for row in rows}
    row_index = {row["trigger_id"]: index for index, row in enumerate(rows)}
    for index, row in enumerate(rows):
        supersedes = row.get("supersedes_trigger_id", "")
        if not supersedes:
            continue
        if supersedes not in by_id:
            raise ValueError(f"supersedes_trigger_id does not exist: {supersedes}")
        if by_id[supersedes]["decision_id"] != row["decision_id"]:
            raise ValueError("supersedes_trigger_id must belong to the same decision_id")
        if row_index[supersedes] >= index:
            raise ValueError("supersedes_trigger_id must reference an earlier ledger row")
    limits = policy_config["trigger_policy"]
    for linked_decision_id in sorted({row["decision_id"] for row in rows}):
        active_count = len(active_trigger_rows(rows, linked_decision_id))
        if active_count < int(limits["min_triggers_per_decision"]) or active_count > int(limits["max_triggers_per_decision"]):
            raise ValueError(
                f"decision {linked_decision_id} must have {limits['min_triggers_per_decision']}-{limits['max_triggers_per_decision']} active triggers"
            )
    return verify_hash_chain(rows, decimal_fields=DECIMAL_FIELDS)


def lock_trigger_proposals(
    *,
    decision_id: str,
    trigger_ids: list[str],
    locked_at: str,
    proposal_path: str = DEFAULT_PROPOSALS,
    decision_journal: str = DEFAULT_DECISION_JOURNAL,
    ledger: str = DEFAULT_LEDGER,
    policy: str = DEFAULT_POLICY,
) -> list[dict[str, str]]:
    if not trigger_ids:
        raise ValueError("at least one --trigger-id is required")
    if len(set(trigger_ids)) != len(trigger_ids):
        raise ValueError("duplicate --trigger-id values are not allowed")
    lock_time = _parse_datetime(locked_at, "locked_at")
    decision_ids = _load_decision_ids(decision_journal)
    if decision_id not in decision_ids:
        raise ValueError(f"decision_id does not exist in Decision Capture: {decision_id}")
    config = _load_policy(policy)
    policy_version = str(config.get("policy_version", "") or "")
    proposals = [
        normalize_trigger_proposal(row, decision_ids=decision_ids, policy_version=policy_version)
        for row in _read_proposal_input(proposal_path)
    ]
    proposal_ids = [row["trigger_id"] for row in proposals]
    duplicate_proposals = sorted(trigger_id for trigger_id, count in Counter(proposal_ids).items() if count > 1)
    if duplicate_proposals:
        raise ValueError(f"duplicate trigger_id proposal(s): {', '.join(duplicate_proposals)}")
    proposal_by_id = {row["trigger_id"]: row for row in proposals}
    missing = [trigger_id for trigger_id in trigger_ids if trigger_id not in proposal_by_id]
    if missing:
        raise ValueError(f"trigger_id not found in proposal artifact: {', '.join(missing)}")
    selected = [proposal_by_id[trigger_id] for trigger_id in trigger_ids]
    if any(row["decision_id"] != decision_id for row in selected):
        raise ValueError("all selected proposals must belong to the supplied decision_id")

    existing = load_trigger_ledger(ledger)
    if existing:
        validate_trigger_ledger(existing, decision_ids=decision_ids, policy_config=config)
    existing_ids = {row["trigger_id"] for row in existing}
    duplicate_ids = sorted(existing_ids.intersection(trigger_ids))
    if duplicate_ids:
        raise ValueError(f"duplicate trigger_id value(s): {', '.join(duplicate_ids)}")

    existing_active = {row["trigger_id"]: row for row in active_trigger_rows(existing, decision_id)}
    superseded_in_batch: set[str] = set()
    for row in selected:
        created = _parse_datetime(row["created_at"], "created_at")
        expected = _parse_date(row["expected_resolution_date"], "expected_resolution_date")
        if created > lock_time:
            raise ValueError("created_at must not be after locked_at")
        if expected <= lock_time.date():
            raise ValueError("expected_resolution_date must be after locked_at")
        supersedes = row.get("supersedes_trigger_id", "")
        if supersedes:
            if supersedes not in existing_active:
                raise ValueError("supersedes_trigger_id must reference an active trigger for the same decision")
            if supersedes in superseded_in_batch:
                raise ValueError("the same active trigger cannot be superseded twice in one lock")
            superseded_in_batch.add(supersedes)

    final_active_count = len(existing_active) - len(superseded_in_batch) + len(selected)
    minimum = int(config["trigger_policy"]["min_triggers_per_decision"])
    maximum = int(config["trigger_policy"]["max_triggers_per_decision"])
    if not minimum <= final_active_count <= maximum:
        raise ValueError(f"decision {decision_id} must have {minimum}-{maximum} active triggers after lock")

    head = verify_hash_chain(existing, decimal_fields=DECIMAL_FIELDS) if existing else GENESIS_PREVIOUS_RECORD_HASH
    appended: list[dict[str, str]] = []
    canonical_locked_at = lock_time.isoformat().replace("+00:00", "Z")
    for proposal in selected:
        record = {**proposal, "locked_at": canonical_locked_at, "hash_schema_version": HASH_SCHEMA_VERSION}
        hashed = build_hashed_record(record, previous_record_hash=head, decimal_fields=DECIMAL_FIELDS)
        appended.append({field: hashed.get(field, "") for field in FIELDS})
        head = hashed["record_hash"]
    candidate_rows = existing + appended
    validate_trigger_ledger(candidate_rows, decision_ids=decision_ids, policy_config=config)
    _write_trigger_ledger(ledger, candidate_rows)
    return appended


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create replaceable trigger proposals or human-lock selected proposals. No LLM is called and no investment decision is created."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    proposal_parser = subparsers.add_parser("propose")
    proposal_parser.add_argument("--proposal-input", required=True)
    proposal_parser.add_argument("--decision-journal", default=DEFAULT_DECISION_JOURNAL)
    proposal_parser.add_argument("--output", default=DEFAULT_PROPOSALS)
    proposal_parser.add_argument("--policy", default=DEFAULT_POLICY)

    lock_parser = subparsers.add_parser("lock")
    lock_parser.add_argument("--decision-id", required=True)
    lock_parser.add_argument("--trigger-id", action="append", required=True)
    lock_parser.add_argument("--locked-at", required=True)
    lock_parser.add_argument("--proposal-file", default=DEFAULT_PROPOSALS)
    lock_parser.add_argument("--decision-journal", default=DEFAULT_DECISION_JOURNAL)
    lock_parser.add_argument("--ledger", default=DEFAULT_LEDGER)
    lock_parser.add_argument("--policy", default=DEFAULT_POLICY)

    validate_parser = subparsers.add_parser("validate-ledger")
    validate_parser.add_argument("--decision-journal", default=DEFAULT_DECISION_JOURNAL)
    validate_parser.add_argument("--ledger", default=DEFAULT_LEDGER)
    validate_parser.add_argument("--policy", default=DEFAULT_POLICY)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    try:
        if args.command == "propose":
            path = write_trigger_proposals(
                _read_proposal_input(args.proposal_input),
                decision_journal=args.decision_journal,
                output=args.output,
                policy=args.policy,
            )
            print(f"proposal_output={path}")
            print("artifact_status=NON_CANONICAL_REPLACEABLE_PROPOSAL")
            return
        if args.command == "lock":
            appended = lock_trigger_proposals(
                decision_id=args.decision_id,
                trigger_ids=args.trigger_id,
                locked_at=args.locked_at,
                proposal_path=args.proposal_file,
                decision_journal=args.decision_journal,
                ledger=args.ledger,
                policy=args.policy,
            )
            print(f"locked_trigger_count={len(appended)}")
            print(f"ledger={resolve_repo_path(args.ledger)}")
            return
        rows = load_trigger_ledger(args.ledger)
        head = validate_trigger_ledger(
            rows,
            decision_ids=_load_decision_ids(args.decision_journal),
            policy_config=_load_policy(args.policy),
        ) if rows else GENESIS_PREVIOUS_RECORD_HASH
        print(f"row_count={len(rows)}")
        print(f"head_hash={head}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
