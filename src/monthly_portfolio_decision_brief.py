"""Deterministic monthly portfolio decision brief producer.

The producer consolidates already-generated CIOS evidence into a compact
operator review surface. It does not recalculate scores, rankings, valuations or
portfolio rules.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from src.common import ensure_parent_dir, read_csv_rows, resolve_repo_path, write_csv_rows

SCHEMA_VERSION = 1
SOURCE_MODULE = "src.monthly_portfolio_decision_brief"

DEFAULT_MONTHLY_RANKING = "data/processed/personal_monthly_buy_ranking.csv"
DEFAULT_CASH_REFILL = "data/processed/personal_cash_refill_review.csv"
DEFAULT_REBALANCE = "data/processed/personal_rebalance_review.csv"
DEFAULT_DATA_FRESHNESS = "data/processed/data_freshness_summary.json"
DEFAULT_DECISION_QUALITY = "data/processed/decision_quality_state.json"
DEFAULT_DECISION_REVIEW_QUEUE = "data/processed/decision_review_queue.csv"
DEFAULT_OUT_JSON = "data/processed/monthly_portfolio_decision_brief.json"
DEFAULT_OUT_CSV = "data/processed/monthly_portfolio_decision_brief.csv"
DEFAULT_REPORT_PATTERN = "reports/{as_of_date}/monthly_portfolio_decision_brief.md"

WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
UNC_PATH_RE = re.compile(r"^(?:\\\\|//)[^\\/]+[\\/][^\\/]+")

RANKING_FIELDS = [
    "rank",
    "ticker",
    "target_action",
    "allocation_status",
    "suggested_buy_amount_eur",
    "rationale",
    "constraint_checks",
    "valuation_comment",
    "mandate_fit_comment",
]

CSV_FIELDS = ["section", "item", "status", "value", "source_artifact", "notes"]

NON_CLAIMS = [
    "no order execution",
    "no buy/sell automation",
    "no investment advice",
    "no valuation automation",
    "no scoring formula change",
    "no ranking formula change",
    "no portfolio rule change",
    "no broker/provider/API integration",
    "no replay/backtesting/outcome attribution",
]

DEGRADED_FRESHNESS_STATUSES = {"STALE", "MISSING", "UNKNOWN", "REVIEW_REQUIRED"}


@dataclass(frozen=True)
class ArtifactRead:
    label: str
    path: str
    mandatory: bool
    status: str
    rows: list[dict[str, str]]
    data: dict[str, Any]
    reason: str


@dataclass(frozen=True)
class MonthlyPortfolioDecisionBriefResult:
    json_output: Path
    csv_output: Path
    report_output: Path
    brief: dict[str, Any]


def _repo_root() -> Path:
    return resolve_repo_path(".").resolve()


def _is_external_syntax(raw: str) -> bool:
    return bool(WINDOWS_ABSOLUTE_RE.match(raw) or UNC_PATH_RE.match(raw))


def _redacted_path(label: str) -> str:
    return f"EXTERNAL_PATH_REDACTED:{label}"


def _safe_path_for_output(path_value: str | Path, label: str) -> tuple[str, bool]:
    raw = str(path_value or "").strip()
    if not raw:
        return "", False
    lowered = raw.replace("\\", "/").lower()
    if any(token in lowered for token in ("data/raw/private", ".env", "sec_user_agent", "provider", "broker")):
        return _redacted_path(label), True

    path = Path(raw)
    if _is_external_syntax(raw) or path.is_absolute():
        try:
            return path.resolve().relative_to(_repo_root()).as_posix(), False
        except ValueError:
            return _redacted_path(label), True
    try:
        return (_repo_root() / raw.replace("\\", "/")).resolve().relative_to(_repo_root()).as_posix(), False
    except ValueError:
        return _redacted_path(label), True


def _artifact_status(*, exists: bool, readable: bool, redacted: bool) -> str:
    if redacted:
        return "REVIEW"
    if readable:
        return "AVAILABLE"
    if exists:
        return "REVIEW"
    return "MISSING"


def _read_csv_artifact(
    label: str,
    path_value: str | Path,
    *,
    mandatory: bool,
    expected_fields: Iterable[str] = (),
) -> ArtifactRead:
    display_path, redacted = _safe_path_for_output(path_value, label)
    if redacted:
        return ArtifactRead(label, display_path, mandatory, "REVIEW", [], {}, "PRIVATE_OR_EXTERNAL_PATH_REDACTED")
    path = resolve_repo_path(path_value)
    if not path.exists():
        return ArtifactRead(label, display_path, mandatory, "MISSING", [], {}, "ARTIFACT_MISSING")
    try:
        rows = read_csv_rows(path)
    except Exception as exc:  # noqa: BLE001 - surfaced as deterministic operator evidence
        return ArtifactRead(label, display_path, mandatory, "REVIEW", [], {}, f"UNREADABLE:{type(exc).__name__}")
    fields = set(rows[0].keys()) if rows else set()
    missing_fields = [field for field in expected_fields if field not in fields]
    if rows and missing_fields:
        return ArtifactRead(label, display_path, mandatory, "REVIEW", rows, {}, f"MISSING_COLUMNS:{';'.join(missing_fields)}")
    return ArtifactRead(label, display_path, mandatory, "AVAILABLE", rows, {}, "READABLE")


def _read_json_artifact(label: str, path_value: str | Path, *, mandatory: bool) -> ArtifactRead:
    display_path, redacted = _safe_path_for_output(path_value, label)
    if redacted:
        return ArtifactRead(label, display_path, mandatory, "REVIEW", [], {}, "PRIVATE_OR_EXTERNAL_PATH_REDACTED")
    path = resolve_repo_path(path_value)
    if not path.exists():
        return ArtifactRead(label, display_path, mandatory, "MISSING", [], {}, "ARTIFACT_MISSING")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - surfaced as deterministic operator evidence
        return ArtifactRead(label, display_path, mandatory, "REVIEW", [], {}, f"UNREADABLE:{type(exc).__name__}")
    if not isinstance(data, dict):
        return ArtifactRead(label, display_path, mandatory, "REVIEW", [], {}, "JSON_ROOT_NOT_OBJECT")
    return ArtifactRead(label, display_path, mandatory, "AVAILABLE", [], data, "READABLE")


def _artifact_record(item: ArtifactRead, source_stage: str) -> dict[str, Any]:
    return {
        "expected_input_path": item.path,
        "exists": item.status in {"AVAILABLE", "REVIEW"} and item.reason != "ARTIFACT_MISSING",
        "label": item.label,
        "mandatory": item.mandatory,
        "reason": item.reason,
        "source_stage": source_stage,
        "status": item.status,
    }


def _top_ranking_rows(rows: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    return [{field: str(row.get(field, "") or "") for field in RANKING_FIELDS} for row in rows[:limit]]


def _status_count(summary_counts: dict[str, Any], status: str) -> int:
    try:
        return int(summary_counts.get(status, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _data_freshness_summary(item: ArtifactRead) -> dict[str, Any]:
    if item.status != "AVAILABLE":
        return {
            "artifact_status": item.status,
            "overall_status": "NOT_AVAILABLE",
            "reason": item.reason,
            "review_required": item.mandatory,
            "summary_counts": {
                "FRESH": 0,
                "MISSING": 0,
                "NOT_APPLICABLE": 0,
                "REVIEW_REQUIRED": 0,
                "STALE": 0,
                "UNKNOWN": 0,
            },
        }
    counts_raw = item.data.get("summary_counts")
    counts = counts_raw if isinstance(counts_raw, dict) else {}
    summary_counts = {
        status: _status_count(counts, status)
        for status in ("FRESH", "STALE", "MISSING", "UNKNOWN", "REVIEW_REQUIRED", "NOT_APPLICABLE")
    }
    degraded = [status for status in ("STALE", "MISSING", "UNKNOWN", "REVIEW_REQUIRED") if summary_counts[status] > 0]
    return {
        "artifact_status": item.status,
        "overall_status": str(item.data.get("overall_status") or "UNKNOWN"),
        "reason": item.reason,
        "review_required": bool(item.data.get("review_required")) or bool(degraded),
        "summary_counts": summary_counts,
        "degraded_state_indicators": degraded,
    }


def _decision_quality_summary(item: ArtifactRead) -> dict[str, Any]:
    if item.status != "AVAILABLE":
        return {
            "artifact_status": item.status,
            "decision_confidence_level": "NOT_AVAILABLE",
            "process_confidence_not_investment_confidence": True,
            "reason": item.reason,
            "review_required": item.mandatory,
        }
    return {
        "artifact_status": item.status,
        "decision_confidence_level": str(item.data.get("decision_confidence_level") or "UNKNOWN"),
        "process_confidence_not_investment_confidence": True,
        "reason": item.reason,
        "review_required": bool(item.data.get("review_required")),
        "review_reason_codes": item.data.get("review_reason_codes") if isinstance(item.data.get("review_reason_codes"), list) else [],
    }


def _portfolio_health_summary(cash_item: ArtifactRead, rebalance_item: ArtifactRead) -> dict[str, Any]:
    cash_status = "NOT_AVAILABLE"
    if cash_item.status == "AVAILABLE" and cash_item.rows:
        cash_status = str(cash_item.rows[0].get("status") or "UNKNOWN")
    rebalance_statuses = sorted({str(row.get("band_status") or "UNKNOWN") for row in rebalance_item.rows}) if rebalance_item.status == "AVAILABLE" else []
    rebalance_actions = sorted({str(row.get("recommended_action") or "UNKNOWN") for row in rebalance_item.rows}) if rebalance_item.status == "AVAILABLE" else []
    review_required = (
        cash_item.status != "AVAILABLE"
        or rebalance_item.status != "AVAILABLE"
        or cash_status in {"CASH_REFILL_REQUIRED", "CASH_REFILL_MARGINAL", "UNKNOWN"}
        or any(action not in {"HOLD", ""} for action in rebalance_actions)
    )
    return {
        "cash_refill_artifact_status": cash_item.status,
        "cash_refill_status": cash_status,
        "rebalance_artifact_status": rebalance_item.status,
        "rebalance_actions": rebalance_actions,
        "rebalance_statuses": rebalance_statuses,
        "review_required": review_required,
    }


def _review_queue_summary(item: ArtifactRead) -> dict[str, Any]:
    if item.status != "AVAILABLE":
        return {"artifact_status": item.status, "queue_items": 0, "reason": item.reason, "review_required": item.mandatory}
    priorities = [str(row.get("priority") or "").upper() for row in item.rows]
    return {
        "artifact_status": item.status,
        "queue_items": len(item.rows),
        "blocker_count": priorities.count("BLOCKER"),
        "high_count": priorities.count("HIGH"),
        "medium_count": priorities.count("MEDIUM"),
        "reason": item.reason,
        "review_required": bool(item.rows),
    }


def _brief_status(
    *,
    artifacts: list[ArtifactRead],
    data_freshness: dict[str, Any],
    decision_quality: dict[str, Any],
    portfolio_health: dict[str, Any],
    review_queue: dict[str, Any],
) -> str:
    if any(item.mandatory and item.status != "AVAILABLE" for item in artifacts):
        return "BLOCKED"
    if (
        data_freshness["review_required"]
        or decision_quality["review_required"]
        or portfolio_health["review_required"]
        or review_queue["review_required"]
        or any(item.status == "REVIEW" for item in artifacts)
    ):
        return "REVIEW"
    return "READY"


def build_monthly_portfolio_decision_brief(
    *,
    as_of_date: str,
    generated_at_utc: str | None = None,
    monthly_ranking: str | Path = DEFAULT_MONTHLY_RANKING,
    cash_refill: str | Path = DEFAULT_CASH_REFILL,
    rebalance: str | Path = DEFAULT_REBALANCE,
    data_freshness: str | Path = DEFAULT_DATA_FRESHNESS,
    decision_quality: str | Path = DEFAULT_DECISION_QUALITY,
    decision_review_queue: str | Path = DEFAULT_DECISION_REVIEW_QUEUE,
    top_n: int = 5,
) -> dict[str, Any]:
    ranking_artifact = _read_csv_artifact("monthly_ranking", monthly_ranking, mandatory=True, expected_fields=RANKING_FIELDS[:6])
    cash_artifact = _read_csv_artifact("cash_refill_review", cash_refill, mandatory=False)
    rebalance_artifact = _read_csv_artifact("rebalance_review", rebalance, mandatory=False)
    freshness_artifact = _read_json_artifact("data_freshness_summary", data_freshness, mandatory=False)
    decision_quality_artifact = _read_json_artifact("decision_quality_state", decision_quality, mandatory=False)
    review_queue_artifact = _read_csv_artifact("decision_review_queue", decision_review_queue, mandatory=False)

    artifacts = [
        ranking_artifact,
        cash_artifact,
        rebalance_artifact,
        freshness_artifact,
        decision_quality_artifact,
        review_queue_artifact,
    ]
    freshness_summary = _data_freshness_summary(freshness_artifact)
    quality_summary = _decision_quality_summary(decision_quality_artifact)
    health_summary = _portfolio_health_summary(cash_artifact, rebalance_artifact)
    queue_summary = _review_queue_summary(review_queue_artifact)
    status = _brief_status(
        artifacts=artifacts,
        data_freshness=freshness_summary,
        decision_quality=quality_summary,
        portfolio_health=health_summary,
        review_queue=queue_summary,
    )
    input_artifacts = [
        _artifact_record(ranking_artifact, "monthly"),
        _artifact_record(cash_artifact, "cash_refill_review"),
        _artifact_record(rebalance_artifact, "rebalance_review"),
        _artifact_record(freshness_artifact, "data_freshness"),
        _artifact_record(decision_quality_artifact, "decision_quality"),
        _artifact_record(review_queue_artifact, "decision_journal_validation"),
    ]
    return {
        "as_of_date": as_of_date,
        "decision_brief_status": status,
        "generated_at_utc": generated_at_utc or "NOT_RECORDED",
        "input_artifact_status": input_artifacts,
        "non_claims": NON_CLAIMS,
        "operator_acceptance_boundary": "Human Operator review required; this brief is evidence consolidation only.",
        "operator_checklist": [
            "Review missing, stale, unknown and review-required evidence states.",
            "Review top ranking rows as upstream evidence, not recalculated recommendations.",
            "Review cash-refill and rebalance evidence before any manual action.",
            "Review decision quality and open review queue items.",
            "Record the final human decision separately where required.",
        ],
        "portfolio_decision_readiness": {
            "conservative_rule": "Missing mandatory inputs result in BLOCKED; degraded or missing review evidence results in REVIEW.",
            "decision_brief_status": status,
        },
        "portfolio_health_summary": health_summary,
        "ranking_summary": {
            "artifact_status": ranking_artifact.status,
            "row_count": len(ranking_artifact.rows),
            "top_rows": _top_ranking_rows(ranking_artifact.rows, max(0, top_n)),
        },
        "data_freshness_summary": freshness_summary,
        "decision_quality_summary": quality_summary,
        "review_queue_summary": queue_summary,
        "schema_version": SCHEMA_VERSION,
        "source_module": SOURCE_MODULE,
    }


def _csv_rows(brief: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = [
        {
            "section": "identity",
            "item": "as_of_date",
            "status": "AVAILABLE",
            "value": str(brief["as_of_date"]),
            "source_artifact": "",
            "notes": "",
        },
        {
            "section": "portfolio_decision_readiness",
            "item": "decision_brief_status",
            "status": str(brief["decision_brief_status"]),
            "value": str(brief["decision_brief_status"]),
            "source_artifact": "",
            "notes": str(brief["portfolio_decision_readiness"]["conservative_rule"]),
        },
    ]
    for artifact in brief["input_artifact_status"]:
        rows.append(
            {
                "section": "input_artifact_status",
                "item": str(artifact["label"]),
                "status": str(artifact["status"]),
                "value": "exists" if artifact["exists"] else "missing",
                "source_artifact": str(artifact["expected_input_path"]),
                "notes": str(artifact["reason"]),
            }
        )
    for ranking_row in brief["ranking_summary"]["top_rows"]:
        rows.append(
            {
                "section": "ranking_summary",
                "item": str(ranking_row.get("rank") or ""),
                "status": str(ranking_row.get("allocation_status") or ranking_row.get("target_action") or ""),
                "value": str(ranking_row.get("ticker") or ""),
                "source_artifact": next(item["expected_input_path"] for item in brief["input_artifact_status"] if item["label"] == "monthly_ranking"),
                "notes": str(ranking_row.get("rationale") or ""),
            }
        )
    for section_name in ("data_freshness_summary", "decision_quality_summary", "portfolio_health_summary", "review_queue_summary"):
        for key, value in sorted(brief[section_name].items()):
            rows.append(
                {
                    "section": section_name,
                    "item": key,
                    "status": str(value) if key.endswith("status") else "",
                    "value": ";".join(str(item) for item in value) if isinstance(value, list) else str(value),
                    "source_artifact": "",
                    "notes": "",
                }
            )
    return rows


def write_brief_json(brief: dict[str, Any], path_value: str | Path) -> Path:
    path = ensure_parent_dir(path_value)
    path.write_text(json.dumps(brief, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path


def write_brief_csv(brief: dict[str, Any], path_value: str | Path) -> Path:
    return write_csv_rows(path_value, CSV_FIELDS, _csv_rows(brief))


def render_markdown(brief: dict[str, Any]) -> str:
    lines = [
        "# Monthly Portfolio Decision Brief",
        "",
        f"- as_of_date: `{brief['as_of_date']}`",
        f"- generated_at_utc: `{brief['generated_at_utc']}`",
        f"- decision_brief_status: `{brief['decision_brief_status']}`",
        f"- source_module: `{brief['source_module']}`",
        "",
        "## Input Artifact Status",
        "",
        "| Artifact | Status | Exists | Source stage | Path | Reason |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for artifact in brief["input_artifact_status"]:
        lines.append(
            f"| `{artifact['label']}` | `{artifact['status']}` | `{str(artifact['exists']).lower()}` | "
            f"`{artifact['source_stage']}` | `{artifact['expected_input_path']}` | `{artifact['reason']}` |"
        )
    lines.extend(
        [
            "",
            "## Portfolio Decision Readiness",
            "",
            f"- decision_brief_status: `{brief['portfolio_decision_readiness']['decision_brief_status']}`",
            f"- conservative_rule: `{brief['portfolio_decision_readiness']['conservative_rule']}`",
            "",
            "## Ranking Summary",
            "",
            "| Rank | Ticker | Target action | Allocation status | Amount EUR | Rationale |",
            "| --- | --- | --- | --- | ---: | --- |",
        ]
    )
    top_rows = brief["ranking_summary"]["top_rows"]
    if top_rows:
        for row in top_rows:
            lines.append(
                f"| {row.get('rank', '')} | `{row.get('ticker', '')}` | `{row.get('target_action', '')}` | "
                f"`{row.get('allocation_status', '')}` | {row.get('suggested_buy_amount_eur', '')} | {row.get('rationale', '')} |"
            )
    else:
        lines.append("|  | `NOT_AVAILABLE` | `MISSING` | `MISSING` |  | Monthly ranking unavailable. |")
    freshness = brief["data_freshness_summary"]
    quality = brief["decision_quality_summary"]
    health = brief["portfolio_health_summary"]
    queue = brief["review_queue_summary"]
    lines.extend(
        [
            "",
            "## Portfolio Health Summary",
            "",
            f"- cash_refill_status: `{health['cash_refill_status']}`",
            f"- cash_refill_artifact_status: `{health['cash_refill_artifact_status']}`",
            f"- rebalance_artifact_status: `{health['rebalance_artifact_status']}`",
            f"- rebalance_statuses: `{' ;'.join(health['rebalance_statuses']) if health['rebalance_statuses'] else 'NOT_AVAILABLE'}`",
            f"- rebalance_actions: `{' ;'.join(health['rebalance_actions']) if health['rebalance_actions'] else 'NOT_AVAILABLE'}`",
            "",
            "## Data Freshness Summary",
            "",
            f"- artifact_status: `{freshness['artifact_status']}`",
            f"- overall_status: `{freshness['overall_status']}`",
            f"- review_required: `{str(freshness['review_required']).lower()}`",
            f"- degraded_state_indicators: `{' ;'.join(freshness.get('degraded_state_indicators', [])) if freshness.get('degraded_state_indicators') else 'None'}`",
            "",
            "## Decision Quality Summary",
            "",
            f"- artifact_status: `{quality['artifact_status']}`",
            f"- decision_confidence_level: `{quality['decision_confidence_level']}`",
            f"- process_confidence_not_investment_confidence: `{str(quality['process_confidence_not_investment_confidence']).lower()}`",
            f"- review_required: `{str(quality['review_required']).lower()}`",
            "",
            "## Review Queue Summary",
            "",
            f"- artifact_status: `{queue['artifact_status']}`",
            f"- queue_items: `{queue['queue_items']}`",
            f"- blocker_count: `{queue.get('blocker_count', 0)}`",
            f"- high_count: `{queue.get('high_count', 0)}`",
            f"- medium_count: `{queue.get('medium_count', 0)}`",
            "",
            "## Operator Checklist",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in brief["operator_checklist"])
    lines.extend(["", "## Explicit Non-Claims", ""])
    lines.extend(f"- {claim}" for claim in brief["non_claims"])
    lines.extend(["", f"Operator acceptance boundary: {brief['operator_acceptance_boundary']}", ""])
    return "\n".join(lines)


def write_brief_markdown(brief: dict[str, Any], path_value: str | Path) -> Path:
    path = ensure_parent_dir(path_value)
    path.write_text(render_markdown(brief), encoding="utf-8", newline="\n")
    return path


def run_monthly_portfolio_decision_brief(
    *,
    as_of_date: str,
    generated_at_utc: str | None = None,
    monthly_ranking: str | Path = DEFAULT_MONTHLY_RANKING,
    cash_refill: str | Path = DEFAULT_CASH_REFILL,
    rebalance: str | Path = DEFAULT_REBALANCE,
    data_freshness: str | Path = DEFAULT_DATA_FRESHNESS,
    decision_quality: str | Path = DEFAULT_DECISION_QUALITY,
    decision_review_queue: str | Path = DEFAULT_DECISION_REVIEW_QUEUE,
    out_json: str | Path = DEFAULT_OUT_JSON,
    out_csv: str | Path = DEFAULT_OUT_CSV,
    report: str | Path | None = None,
    top_n: int = 5,
) -> MonthlyPortfolioDecisionBriefResult:
    brief = build_monthly_portfolio_decision_brief(
        as_of_date=as_of_date,
        generated_at_utc=generated_at_utc,
        monthly_ranking=monthly_ranking,
        cash_refill=cash_refill,
        rebalance=rebalance,
        data_freshness=data_freshness,
        decision_quality=decision_quality,
        decision_review_queue=decision_review_queue,
        top_n=top_n,
    )
    json_path = write_brief_json(brief, out_json)
    csv_path = write_brief_csv(brief, out_csv)
    report_path = write_brief_markdown(brief, report or DEFAULT_REPORT_PATTERN.format(as_of_date=as_of_date))
    return MonthlyPortfolioDecisionBriefResult(json_path, csv_path, report_path, brief)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a deterministic monthly portfolio decision brief from existing CIOS artifacts.")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--generated-at-utc")
    parser.add_argument("--monthly-ranking", default=DEFAULT_MONTHLY_RANKING)
    parser.add_argument("--cash-refill", default=DEFAULT_CASH_REFILL)
    parser.add_argument("--rebalance", default=DEFAULT_REBALANCE)
    parser.add_argument("--data-freshness", default=DEFAULT_DATA_FRESHNESS)
    parser.add_argument("--decision-quality", default=DEFAULT_DECISION_QUALITY)
    parser.add_argument("--decision-review-queue", default=DEFAULT_DECISION_REVIEW_QUEUE)
    parser.add_argument("--out-json", default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-csv", default=DEFAULT_OUT_CSV)
    parser.add_argument("--report")
    parser.add_argument("--top-n", type=int, default=5)
    return parser.parse_args()


def _display_output_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(_repo_root()).as_posix()
    except ValueError:
        return _redacted_path("output")


def main() -> None:
    args = parse_args()
    result = run_monthly_portfolio_decision_brief(
        as_of_date=args.as_of_date,
        generated_at_utc=args.generated_at_utc,
        monthly_ranking=args.monthly_ranking,
        cash_refill=args.cash_refill,
        rebalance=args.rebalance,
        data_freshness=args.data_freshness,
        decision_quality=args.decision_quality,
        decision_review_queue=args.decision_review_queue,
        out_json=args.out_json,
        out_csv=args.out_csv,
        report=args.report,
        top_n=args.top_n,
    )
    print(f"json_output={_display_output_path(result.json_output)}")
    print(f"csv_output={_display_output_path(result.csv_output)}")
    print(f"report_output={_display_output_path(result.report_output)}")
    print(f"decision_brief_status={result.brief['decision_brief_status']}")


if __name__ == "__main__":
    main()
